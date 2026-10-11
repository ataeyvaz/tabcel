"""Sözdizim ağacını değerlendirir. Qt yok.

Dizi semantiği Excel 365 gibidir (işleçler aralık/dizi üzerinde öğe öğe çalışır); taşma (spill)
olmadığından hücre sonucu `hucre_sonucu` ile tek değere indirgenir (faz2_tasarim.md §3).
"""
import math
from typing import Optional
from dataclasses import dataclass
from functools import lru_cache

from ..model import deger as D
from ..model.adres import MAX_COL, MAX_ROW
from ..model.deger import Hata
from . import fonksiyonlar
from .agac import (
    KESISIM, Ad, Bos, Cagri, DiziSabit, Dugum, Ikili, Ref, Sabit, Tekli, Yuzde, agac_kaydir,
    formul_ayristir,
)
from .degerler import BOS_ARG, AralikDeger, Dizi, _boyut, _okuyucu, _yay, skalere
from .donustur import karsilastir, metne, sayi_sonucu, sayiya
from .sozcuk import FormulHatasi

AD_DERINLIK = 64                   # iç içe tanımlı ad sınırı (özyineleme koruması)


@dataclass
class Baglam:
    """Formülün değerlendirildiği yer. `kitap` None olabilir (kitapsız sayfa: başka sayfa
    başvurusu #BAŞV!). Hücre değerleri sayfanın sonuç deposundan okunur; motor henüz
    hesaplanmamış hücreleri `BEKLIYOR` ile işaretler (okununca `Bekle` atılır)."""
    sayfa: object
    satir: int
    sutun: int
    kitap: object = None
    ad_yigini: tuple = ()          # değerlendirilmekte olan tanımlı adlar (özyineleme koruması)
    yerel: Optional[dict] = None   # LET değişkenleri: {ADI: değer} (Faz 8e); tanımlı adların içine geçmez

    def sayfa_bul(self, ref_sayfa):
        if ref_sayfa is None:
            return self.sayfa
        if self.kitap is None:
            return None
        if isinstance(ref_sayfa, int):
            return self.kitap.sayfa_kimlikle(ref_sayfa)
        ad = ref_sayfa.casefold()
        return next((s for s in self.kitap.sayfalar if s.ad.casefold() == ad), None)


def degerlendir(d: Dugum, b: Baglam):
    """Düğümün değeri: skaler, `AralikDeger` ya da `Dizi` (atlanmış argüman için `BOS_ARG`)."""
    t = type(d)
    if t is Sabit:
        return d.deger
    if t is Ref:
        br = d.basvuru
        sayfa = b.sayfa_bul(br.sayfa)
        if sayfa is None:
            return D.BASV
        return AralikDeger(sayfa, br.r1, br.c1, br.r2, br.c2)
    if t is Ikili:
        if d.islec == ":":
            return _aralik_islec(degerlendir(d.a, b), degerlendir(d.b, b))
        if d.islec == KESISIM:
            return _kesisim(degerlendir(d.a, b), degerlendir(d.b, b))
        return _ogeler(_IKILI[d.islec], degerlendir(d.a, b), degerlendir(d.b, b))
    if t is Tekli:
        x = degerlendir(d.x, b)
        return _ogeler1(_eksi if d.islec == "-" else _arti, x)
    if t is Yuzde:
        return _ogeler1(_yuzde, degerlendir(d.x, b))
    if t is Cagri:
        return _cagir(d, b)
    if t is DiziSabit:
        return Dizi([list(r) for r in d.satirlar])
    if t is Bos:
        return BOS_ARG
    if t is Ad:
        return _ad_degerle(d, b)
    raise TypeError(f"Bilinmeyen düğüm: {d!r}")


@lru_cache(maxsize=4096)
def ad_agaci(formul: str):
    """Tanımlı adın formül ağacı (çözümlenemezse None). Motor da aynı önbelleği kullanır."""
    try:
        return formul_ayristir(formul)
    except FormulHatasi:
        return None


def ad_coz(ad: str, b: "Baglam"):
    """Hücreye göre kaydırılmış ad ağacı ve ad kaydı; bulunamazsa (None, None). Göreli başvurular
    A1'e göre saklanır, bu yüzden (satır−1, sütun−1) kaydırılır."""
    if b.kitap is None:
        return None, None
    tanim = b.kitap.ad_bul(ad, getattr(b.sayfa, "kimlik", None))
    if tanim is None:
        return None, None
    agac = ad_agaci(tanim.formul)
    if agac is None:
        return None, tanim
    return agac_kaydir(agac, b.satir - 1, b.sutun - 1), tanim


def _ad_degerle(d: Ad, b: "Baglam"):
    if b.yerel:
        v = b.yerel.get(d.ad.upper())
        if v is not None:
            return v[0]
    agac, tanim = ad_coz(d.ad, b)
    if agac is None:
        return D.AD
    anahtar = tanim.anahtar()
    if anahtar in b.ad_yigini or len(b.ad_yigini) >= AD_DERINLIK:
        return D.AD                         # döngüsel / çok derin ad (Excel de hata verir)
    return degerlendir(agac, Baglam(b.sayfa, b.satir, b.sutun, b.kitap, b.ad_yigini + (anahtar,)))


def _cok_hucreli(v) -> bool:
    return type(v) is Dizi and v.satir_sayisi * v.sutun_sayisi > 1


def hucre_sonucu(d: Dugum, b: Baglam, dizi_koru: bool = False):
    """Hücreye yazılacak tek değer. Boş hücreye başvuru 0 olur (Excel: `=A1`, A1 boşsa 0).
    Kök işlem toplama/çıkarmaysa Excel'in 'yakın sıfır' düzeltmesi uygulanır.

    `dizi_koru=True` (motor; Faz 8e): sonuç ÇOK HÜCRELİ bir `Dizi` ise (hesaplanmış dizi: SIRALA, A1:A3*2 …) skalere
    indirilmeden döner — hücreye taşar. Düz aralık başvurusu (`=A1:A3`) taşmaz, örtük kesişimle tek değer verir
    (Excel 365'ten bilinçli fark)."""
    if type(d) is Ikili and d.islec in ("+", "-"):
        va, vb = degerlendir(d.a, b), degerlendir(d.b, b)
        v = _ogeler(_IKILI[d.islec], va, vb)
        if dizi_koru and _cok_hucreli(v):
            return v
        v = skalere(v, b.satir, b.sutun)
        if isinstance(v, float) and v != 0:
            v = _yakin_sifir(v, skalere(va, b.satir, b.sutun), skalere(vb, b.satir, b.sutun))
    else:
        v = degerlendir(d, b)
        if dizi_koru and _cok_hucreli(v):
            return v
        v = skalere(v, b.satir, b.sutun)
    if v is None or v is BOS_ARG:
        return 0.0
    return v


def _yakin_sifir(v: float, a, c) -> float:
    """Excel, formülün SON işlemi toplama/çıkarmaysa ve sonuç işlenenlere göre çift duyarlık
    hatası mertebesindeyse 0 döndürür: `=0,5-0,4-0,1` → 0 ama `=1*(0,5-0,4-0,1)` → -2,78E-17
    (Microsoft: "Floating-point arithmetic may give inaccurate results"). Eşik doğrulanmadı
    (surec.md §8b-7)."""
    a, c = sayiya(a), sayiya(c)
    if isinstance(a, Hata) or isinstance(c, Hata):
        return v
    if abs(v) <= max(abs(a), abs(c)) * 2.0 ** -49:
        return 0.0
    return v


# --- öğe öğe işlemler ---
def _ogeler(islem, a, b):
    ba, bb = _boyut(a), _boyut(b)
    if ba is None and bb is None:
        return islem(None if a is BOS_ARG else a, None if b is BOS_ARG else b)
    if ba == (1, 1) and bb is None and isinstance(a, AralikDeger):
        return islem(a.hucre_degeri(a.r1, a.c1), None if b is BOS_ARG else b)
    if bb == (1, 1) and ba is None and isinstance(b, AralikDeger):
        return islem(None if a is BOS_ARG else a, b.hucre_degeri(b.r1, b.c1))
    if ba == (1, 1) and bb == (1, 1) and isinstance(a, AralikDeger) and isinstance(b, AralikDeger):
        return islem(a.hucre_degeri(a.r1, a.c1), b.hucre_degeri(b.r1, b.c1))
    R = max(x[0] for x in (ba, bb) if x)
    C = max(x[1] for x in (ba, bb) if x)
    oa, ob = _yay(_okuyucu(a), ba, R, C), _yay(_okuyucu(b), bb, R, C)
    return Dizi([[islem(oa(i, j), ob(i, j)) for j in range(C)] for i in range(R)])


def _ogeler1(islem, x):
    bx = _boyut(x)
    if bx is None:
        return islem(None if x is BOS_ARG else x)
    if bx == (1, 1) and isinstance(x, AralikDeger):
        return islem(x.hucre_degeri(x.r1, x.c1))
    R, C = bx
    o = _okuyucu(x)
    return Dizi([[islem(o(i, j)) for j in range(C)] for i in range(R)])


def _aritmetik(f):
    def islem(a, b):
        x = sayiya(a)
        if isinstance(x, Hata):
            return x
        y = sayiya(b)
        if isinstance(y, Hata):
            return y
        return f(x, y)
    return islem


def _bol(x, y):
    if y == 0:
        return D.BOL0
    return sayi_sonucu(x / y)


def _us(x, y):
    if x == 0 and y == 0:
        return D.SAYI                      # Excel: 0^0 = #SAYI!
    if x == 0 and y < 0:
        return D.BOL0
    try:
        r = math.pow(x, y)
    except (OverflowError, ValueError):
        return D.SAYI                      # negatif tabanın kesirli üssü, taşma
    return sayi_sonucu(r)


def _birlestir(a, b):
    x = metne(a)
    if isinstance(x, Hata):
        return x
    y = metne(b)
    if isinstance(y, Hata):
        return y
    return x + y


def _karsilastirma(kosul):
    def islem(a, b):
        k = karsilastir(a, b)
        if isinstance(k, Hata):
            return k
        return kosul(k)
    return islem


_IKILI = {
    "+": _aritmetik(lambda x, y: sayi_sonucu(x + y)),
    "-": _aritmetik(lambda x, y: sayi_sonucu(x - y)),
    "*": _aritmetik(lambda x, y: sayi_sonucu(x * y)),
    "/": _aritmetik(_bol),
    "^": _aritmetik(_us),
    "&": _birlestir,
    "=": _karsilastirma(lambda k: k == 0),
    "<>": _karsilastirma(lambda k: k != 0),
    "<": _karsilastirma(lambda k: k < 0),
    ">": _karsilastirma(lambda k: k > 0),
    "<=": _karsilastirma(lambda k: k <= 0),
    ">=": _karsilastirma(lambda k: k >= 0),
}


def _eksi(x):
    v = sayiya(x)
    return v if isinstance(v, Hata) else -v + 0.0


def _arti(x):
    return x                               # Excel: tekli artı değeri değiştirmez (=+"a" → "a")


def _yuzde(x):
    v = sayiya(x)
    return v if isinstance(v, Hata) else v / 100


# --- başvuru işleçleri ---
def _aralik_islec(a, b):
    """`A1:B2` dışındaki biçimler: `A1:INDEX(...)`, `(A1):(C3)` → iki başvuruyu kapsayan aralık."""
    for v in (a, b):
        if isinstance(v, Hata):
            return v
    if not (isinstance(a, AralikDeger) and isinstance(b, AralikDeger)) or a.sayfa is not b.sayfa:
        return D.DEGER_HATASI
    return AralikDeger(a.sayfa, min(a.r1, b.r1), min(a.c1, b.c1), max(a.r2, b.r2),
                       max(a.c2, b.c2))


def _kesisim(a, b):
    for v in (a, b):
        if isinstance(v, Hata):
            return v
    if not (isinstance(a, AralikDeger) and isinstance(b, AralikDeger)):
        return D.DEGER_HATASI
    if a.sayfa is not b.sayfa:
        return D.BOS
    r1, c1, r2, c2 = max(a.r1, b.r1), max(a.c1, b.c1), min(a.r2, b.r2), min(a.c2, b.c2)
    if r1 > r2 or c1 > c2:
        return D.BOS                       # #BOŞ!: kesişim yok
    return AralikDeger(a.sayfa, r1, c1, r2, c2)


# --- fonksiyon çağrısı ---
def _let(d: Cagri, b: Baglam):
    """LET(ad1, değer1, [ad2, değer2, …], hesaplama): adlar sırayla bağlanır, sonraki değerler öncekileri görür."""
    n = len(d.argumanlar)
    if n < 3 or n % 2 == 0:
        return D.DEGER_HATASI
    yerel = dict(b.yerel or {})
    iç = Baglam(b.sayfa, b.satir, b.sutun, b.kitap, b.ad_yigini, yerel)
    for i in range(0, n - 1, 2):
        ad = d.argumanlar[i]
        if type(ad) is not Ad:
            return D.AD
        yerel[ad.ad.upper()] = (degerlendir(d.argumanlar[i + 1], iç),)     # demet: değer None olsa da var sayılır
    return degerlendir(d.argumanlar[-1], iç)


def _cagir(d: Cagri, b: Baglam):
    if d.ad.upper() == "LET":
        return _let(d, b)
    tanim = fonksiyonlar.bul(d.ad)
    if tanim is None:
        return D.AD
    n = len(d.argumanlar)
    if n < tanim.en_az or (tanim.en_cok is not None and n > tanim.en_cok):
        return D.DEGER_HATASI
    if tanim.tembel:
        args = [(lambda a=a: degerlendir(a, b)) for a in d.argumanlar]
    else:
        args = [degerlendir(a, b) for a in d.argumanlar]
    return tanim.uygula(b, *args)
