"""Sözdizim ağacını değerlendirir. Qt yok.

Dizi semantiği Excel 365 gibidir (işleçler aralık/dizi üzerinde öğe öğe çalışır); taşma (spill)
olmadığından hücre sonucu `hucre_sonucu` ile tek değere indirgenir (faz2_tasarim.md §3).
"""
import math
from dataclasses import dataclass

from ..model import deger as D
from ..model.adres import MAX_COL, MAX_ROW
from ..model.deger import Hata
from . import fonksiyonlar
from .agac import (
    KESISIM, Ad, Bos, Cagri, DiziSabit, Dugum, Ikili, Ref, Sabit, Tekli, Yuzde,
)
from .degerler import BOS_ARG, AralikDeger, Dizi, skalere
from .donustur import karsilastir, metne, sayi_sonucu, sayiya


@dataclass
class Baglam:
    """Formülün değerlendirildiği yer. `kitap` None olabilir (kitapsız sayfa: başka sayfa
    başvurusu #BAŞV!). Hücre değerleri sayfanın sonuç deposundan okunur; motor henüz
    hesaplanmamış hücreleri `BEKLIYOR` ile işaretler (okununca `Bekle` atılır)."""
    sayfa: object
    satir: int
    sutun: int
    kitap: object = None

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
        return D.AD          # tanımlı adlar Faz 5
    raise TypeError(f"Bilinmeyen düğüm: {d!r}")


def hucre_sonucu(d: Dugum, b: Baglam):
    """Hücreye yazılacak tek değer. Boş hücreye başvuru 0 olur (Excel: `=A1`, A1 boşsa 0).
    Kök işlem toplama/çıkarmaysa Excel'in 'yakın sıfır' düzeltmesi uygulanır."""
    if type(d) is Ikili and d.islec in ("+", "-"):
        va, vb = degerlendir(d.a, b), degerlendir(d.b, b)
        v = skalere(_ogeler(_IKILI[d.islec], va, vb), b.satir, b.sutun)
        if isinstance(v, float) and v != 0:
            v = _yakin_sifir(v, skalere(va, b.satir, b.sutun), skalere(vb, b.satir, b.sutun))
    else:
        v = skalere(degerlendir(d, b), b.satir, b.sutun)
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
def _boyut(v):
    if isinstance(v, AralikDeger):
        r1, c1, r2, c2 = v.kirpilmis() if (v.r2 == MAX_ROW or v.c2 == MAX_COL) else (
            v.r1, v.c1, v.r2, v.c2)
        return r2 - r1 + 1, c2 - c1 + 1
    if isinstance(v, Dizi):
        return v.satir_sayisi, v.sutun_sayisi
    return None


def _okuyucu(v):
    if isinstance(v, AralikDeger):
        if v.tek_hucre():
            x = v.hucre_degeri(v.r1, v.c1)
            return lambda i, j: x
        if v.r2 == MAX_ROW or v.c2 == MAX_COL:
            r1, c1, _, _ = v.kirpilmis()
        else:
            r1, c1 = v.r1, v.c1
        return lambda i, j: v.hucre_degeri(r1 + i, c1 + j)
    if isinstance(v, Dizi):
        return v.deger
    x = None if v is BOS_ARG else v
    return lambda i, j: x


def _yay(okuyucu, boyut, R, C):
    """Excel 365 yayma kuralı: 1 satırlı/sütunlu taraf genişletilir; boyu yetmeyen yerde #YOK."""
    if boyut is None:
        return okuyucu
    r, c = boyut

    def oku(i, j):
        if (r != 1 and i >= r) or (c != 1 and j >= c):
            return D.YOK
        return okuyucu(0 if r == 1 else i, 0 if c == 1 else j)
    return oku


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
def _cagir(d: Cagri, b: Baglam):
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
