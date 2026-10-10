"""Veri doğrulama denetimi (Faz 5 / 5g; faz5_tasarim.md §7.2). Qt yok.

Formüller (`formul1/2`) kuralın çapa hücresine göre yazılır ve denetlenen hücreye `agac_kaydir` ile
kaydırılarak değerlendirilir. Yalnız elle girişte çağrılır (yapıştırma/doldurma/formül sonucu denetlenmez).
Koşullu biçim değerlendirmesi (5h) bu modüle eklenecektir.
"""
from typing import List, Optional

from ..model import deger as D
from ..model.deger import Hata
from ..model.dogrulama import IKI_DEGERLI, Dogrulama, liste_sabiti_ogeleri
from ..model.gosterim import goster
from ..model.harmanla import tr_kucuk
from ..model.sayfa import Hucre
from .agac import agac_kaydir
from .degerlendir import Baglam, ad_agaci, degerlendir, hucre_sonucu
from .degerler import AralikDeger, Dizi
from .donustur import sayiya


def _agac(dv: Dogrulama, formul: str, r: int, c: int):
    agac = ad_agaci(formul)
    if agac is None:
        return None
    cr, cc = dv.capa()
    return agac_kaydir(agac, r - cr, c - cc)


def _skaler(dv: Dogrulama, formul: Optional[str], sayfa, r: int, c: int, kitap):
    if formul is None:
        return D.DEGER_HATASI
    agac = _agac(dv, formul, r, c)
    if agac is None:
        return D.AD
    return hucre_sonucu(agac, Baglam(sayfa, r, c, kitap))


def _sayi_degeri(v):
    """Karşılaştırma uçları sayı olmalı: boş = 0, metin sayıya çevrilebilirse sayı, aksi hata."""
    if v is None:
        return 0.0
    s = sayiya(v)
    return s if isinstance(s, float) else None


def _karsilastir(islec: str, x: float, a: float, b: Optional[float]) -> bool:
    if islec == "arasinda":
        return b is not None and a <= x <= b
    if islec == "arasinda_degil":
        return b is not None and not (a <= x <= b)
    return {"esit": x == a, "esit_degil": x != a, "buyuk": x > a, "kucuk": x < a,
            "buyuk_esit": x >= a, "kucuk_esit": x <= a}[islec]


def liste_ogeleri(dv: Dogrulama, sayfa, r: int, c: int, kitap=None, bos_dahil: bool = False) -> Optional[List[str]]:
    """Liste doğrulamasının seçenekleri (görünen metin). Sabit listede öğeler olduğu gibi; aralıkta hücre
    değerleri (`goster`). `bos_dahil`: açılır listede boş hücre boş satır olur. Hesaplanamazsa None."""
    if dv.formul1 is None:
        return None
    if dv.liste_sabiti_mi():
        return liste_sabiti_ogeleri(dv.formul1)
    agac = _agac(dv, dv.formul1, r, c)
    if agac is None:
        return None
    v = degerlendir(agac, Baglam(sayfa, r, c, kitap))
    if isinstance(v, AralikDeger):
        r1, c1, r2, c2 = (v.r1, v.c1, v.r2, v.c2) if v.satir_sayisi * v.sutun_sayisi <= 10_000 else v.kirpilmis()
        degerler = [v.hucre_degeri(i, j) for i in range(r1, r2 + 1) for j in range(c1, c2 + 1)]
    elif isinstance(v, Dizi):
        degerler = list(v.degerler())
    elif isinstance(v, str):
        return v.split(",")
    else:
        return None
    if any(isinstance(x, Hata) for x in degerler):
        return None
    return [goster(x) if x is not None else "" for x in degerler if bos_dahil or x is not None]


def dogrula(sayfa, r: int, c: int, deger, kitap=None, dv: Optional[Dogrulama] = None) -> bool:
    """`deger` (float/str/bool/None/Hata), `(r, c)` hücresine elle girilirse kurala uyar mı? Kural yoksa
    ya da türü "her değer" ise True. Denetim hata verirse (bozuk formül) geçersiz sayılır."""
    if dv is None:
        dv = sayfa.dogrulama(r, c)
    if dv is None or dv.tur == "her_deger":
        return True
    if deger is None:
        return dv.bos_yoksay
    kitap = kitap if kitap is not None else sayfa.kitap
    try:
        return _denetle(dv, sayfa, r, c, deger, kitap)
    except RecursionError:
        return False
    except Exception:
        return False


def _denetle(dv: Dogrulama, sayfa, r: int, c: int, deger, kitap) -> bool:
    tur = dv.tur
    if tur == "liste":
        ogeler = liste_ogeleri(dv, sayfa, r, c, kitap)
        if ogeler is None:
            return False
        aranan = tr_kucuk(goster(deger))
        return any(tr_kucuk(o) == aranan for o in ogeler)
    if tur == "ozel":
        hucreler = sayfa._hucreler
        eski = hucreler.get((r, c))
        hucreler[(r, c)] = Hucre(deger)                 # formül hücrenin YENİ değeriyle değerlendirilir
        try:
            v = _skaler(dv, dv.formul1, sayfa, r, c, kitap)
        finally:
            if eski is None:
                hucreler.pop((r, c), None)
            else:
                hucreler[(r, c)] = eski
        if isinstance(v, bool):
            return v
        return isinstance(v, float) and v != 0
    if tur == "metin_uzunlugu":
        x = float(len(goster(deger)))
    else:
        if isinstance(deger, (bool, Hata)) or not isinstance(deger, (int, float)):
            return False
        x = float(deger)
        if tur == "tam_sayi" and x != int(x):
            return False
    a = _sayi_degeri(_skaler(dv, dv.formul1, sayfa, r, c, kitap))
    if a is None:
        return False
    b = None
    if dv.islec in IKI_DEGERLI:
        b = _sayi_degeri(_skaler(dv, dv.formul2, sayfa, r, c, kitap))
        if b is None:
            return False
    return _karsilastir(dv.islec, x, a, b)


# =============================================================================== koşullu biçim (5h)
from collections import Counter                                      # noqa: E402
from ..model.adres import aralik_icinde                              # noqa: E402
from ..model.kosullu import KosulluKural                             # noqa: E402
from ..model.stil import StilYama                                    # noqa: E402
from .donustur import karsilastir                                    # noqa: E402

CUBUK_MIN, CUBUK_MAX = 0.1, 0.9          # Excel 2007 veri çubuğu: en kısa %10, en uzun %90


def _formul_degeri(formul, capa, sayfa, r: int, c: int, kitap):
    """Kuralın formülü çapaya göre yazılmıştır; (r, c) hücresine kaydırılıp tek değere değerlendirilir."""
    agac = ad_agaci(formul)
    if agac is None:
        return D.AD
    agac = agac_kaydir(agac, r - capa[0], c - capa[1])
    return hucre_sonucu(agac, Baglam(sayfa, r, c, kitap))


def _sayi_mi(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _hex_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _renk_karisimi(a: str, b: str, t: float) -> str:
    ra, rb = _hex_rgb(a), _hex_rgb(b)
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def yuzdebirlik(sirali, p: float) -> float:
    """`sirali` (artan) sayı listesinin p. yüzdebirliği (0–100), doğrusal aradeğer (Excel YÜZDEBİRLİK)."""
    n = len(sirali)
    if n == 1:
        return sirali[0]
    k = (n - 1) * p / 100.0
    i = min(int(k), n - 2)
    return sirali[i] + (sirali[i + 1] - sirali[i]) * (k - i)


class KosulluHesap:
    """Bir sayfanın koşullu biçim değerlendirmesi: `hucre(r, c) -> (yama | None, çubuk | None)`; çubuk =
    `(oran 0–1, renk, yalnız_çubuk, gradyan)`. Kural başına istatistikler tembel ve önbellekli; hücre sonucu
    `(r, c)` anahtarlı. Kitapta içerik/sonuç/yapı/ek değişince çağıran `gecersiz()` der (tüm önbellek boşalır)."""

    def __init__(self, sayfa, kitap=None):
        self.sayfa = sayfa
        self.kitap = kitap if kitap is not None else sayfa.kitap
        self.gecersiz()

    def gecersiz(self) -> None:
        self._kurallar = list(self.sayfa.kosullu)
        self._kutular = []
        for k in self._kurallar:
            self._kutular.append((min(a.ilk_satir for a in k.araliklar), min(a.ilk_sutun for a in k.araliklar),
                                  max(a.son_satir for a in k.araliklar), max(a.son_sutun for a in k.araliklar)))
        self._onb = {}
        self._ist = {}
        self._ham = {}

    def var_mi(self) -> bool:
        return bool(self._kurallar)

    def hucre(self, r: int, c: int):
        if not self._kurallar:
            return None, None
        sonuc = self._onb.get((r, c))
        if sonuc is not None:
            return sonuc
        alanlar, cubuk = {}, None
        for i, k in enumerate(self._kurallar):
            kt = self._kutular[i]
            if not (kt[0] <= r <= kt[2] and kt[1] <= c <= kt[3]):
                continue
            if not any(aralik_icinde(a, r, c) for a in k.araliklar):
                continue
            try:
                eslesti, yama, cb = self._uygula(i, k, r, c)
            except Exception:                              # bozuk formül vb.: kural bu hücrede uygulanmaz
                continue
            if not eslesti:
                continue
            for ad, v in ((yama._alanlar if yama is not None else None) or {}).items():
                alanlar.setdefault(ad, v)
            if cb is not None and cubuk is None:
                cubuk = cb
            if k.dur:
                break
        sonuc = (StilYama(**alanlar) if alanlar else None, cubuk)
        self._onb[(r, c)] = sonuc
        return sonuc

    # --- kural türleri ---
    def _uygula(self, i: int, k: KosulluKural, r: int, c: int):
        sayfa, kitap = self.sayfa, self.kitap
        v = sayfa.deger(r, c)
        t = k.tur
        yama = k.bicim
        if t == "hucre_degeri":
            a = _formul_degeri(k.formul1, k.capa(), sayfa, r, c, kitap)
            ka = karsilastir(v, a)
            if isinstance(ka, Hata):
                return False, None, None
            if k.islec in ("arasinda", "arasinda_degil"):
                b = _formul_degeri(k.formul2, k.capa(), sayfa, r, c, kitap)
                kb = karsilastir(v, b)
                if isinstance(kb, Hata):
                    return False, None, None
                ic = ka >= 0 and kb <= 0
                return (ic if k.islec == "arasinda" else not ic), yama, None
            return {"esit": ka == 0, "esit_degil": ka != 0, "buyuk": ka > 0, "kucuk": ka < 0,
                    "buyuk_esit": ka >= 0, "kucuk_esit": ka <= 0}[k.islec], yama, None
        if t == "metin":
            metin = tr_kucuk(k.metin)
            if v is None:
                return k.islec == "icermez" and metin != "", yama, None
            s = tr_kucuk(goster(v))
            return {"icerir": metin in s, "icermez": metin not in s,
                    "baslar": s.startswith(metin), "biter": s.endswith(metin)}[k.islec], yama, None
        if t in ("bos", "bos_degil"):
            bos = v is None or (isinstance(v, str) and v.strip() == "")
            return (bos if t == "bos" else not bos), yama, None
        if t in ("hata", "hata_degil"):
            h = isinstance(v, Hata)
            return (h if t == "hata" else not h), yama, None
        if t == "formul":
            x = _formul_degeri(k.formul1, k.capa(), sayfa, r, c, kitap)
            if isinstance(x, bool):
                return x, yama, None
            return _sayi_mi(x) and x != 0, yama, None
        if v is None:
            return False, None, None
        if t == "yinelenen":
            sayac = self._istatistik(i, k, "yinelenen")
            anahtar = v if type(v) is float else self._anahtar(v)
            if anahtar is None:
                return False, None, None
            n = sayac.get(anahtar, 0)
            return (n == 1 if k.benzersiz else n > 1), yama, None
        if not _sayi_mi(v):
            return False, None, None                      # kalan türler yalnız sayılara bakar
        v = float(v)
        if t == "ilk_son":
            esik = self._istatistik(i, k, "ilk_son")
            if esik is None:
                return False, None, None
            return (v <= esik if k.alt else v >= esik), yama, None
        if t == "ortalama":
            ort, sd = self._istatistik(i, k, "ortalama")
            sinir = ort + (k.std * sd if k.ustu else -k.std * sd)
            if k.ustu:
                return (v >= sinir if k.esit else v > sinir), yama, None
            return (v <= sinir if k.esit else v < sinir), yama, None
        if t == "renk_olcegi":
            noktalar = self._istatistik(i, k, "olcek")
            if noktalar is None:
                return False, None, None
            return True, StilYama(dolgu=self._olcek_rengi(noktalar, v)), None
        if t == "veri_cubugu":
            ucler = self._istatistik(i, k, "cubuk")
            if ucler is None:
                return False, None, None
            lo, hi = ucler
            t_ = 1.0 if hi == lo else min(1.0, max(0.0, (v - lo) / (hi - lo)))
            return True, yama, (CUBUK_MIN + (CUBUK_MAX - CUBUK_MIN) * t_, k.renk, k.yalniz_cubuk, k.gradyan)
        return False, None, None

    @staticmethod
    def _anahtar(v):
        if v is None or (isinstance(v, str) and v == ""):
            return None
        if isinstance(v, str):
            return ("s", tr_kucuk(v))
        if isinstance(v, bool):
            return ("b", v)
        if isinstance(v, Hata):
            return ("e", str(v))
        return float(v)                                    # sayı: düz float anahtar (bool/metinle çakışmaz)

    def _ham_degerler(self, k: KosulluKural) -> list:
        """Kuralın aralıklarındaki dolu hücre değerleri (boş değerler hariç; aynı hücre bir kez). Aynı aralığa
        bakan kurallar taramayı paylaşır (100.000 hücrede tek geçiş)."""
        anahtar = k.araliklar
        liste = self._ham.get(anahtar)
        if liste is not None:
            return liste
        hucreler, sonuc = self.sayfa._hucreler, self.sayfa._sonuc
        liste, gorulen = [], set()
        coklu = len(k.araliklar) > 1
        for a in k.araliklar:
            r1, c1, r2, c2 = a.ilk_satir, a.ilk_sutun, a.son_satir, a.son_sutun
            if (r2 - r1 + 1) * (c2 - c1 + 1) * 4 <= len(hucreler):         # küçük aralık: hücreleri adresle
                ogeler = [(rc, hucreler[rc]) for rc in ((r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1))
                          if rc in hucreler]
            else:                                                           # büyük aralık: sözlüğü bir kez gez
                ogeler = [(rc, h) for rc, h in hucreler.items() if r1 <= rc[0] <= r2 and c1 <= rc[1] <= c2]
            for rc, h in ogeler:
                if coklu:
                    if rc in gorulen:
                        continue
                    gorulen.add(rc)
                v = h.deger if h.formul is None else sonuc.get(rc)
                if v is not None:
                    liste.append(v)
        self._ham[anahtar] = liste
        return liste

    def _istatistik(self, i: int, k: KosulluKural, tur: str):
        anahtar = (i, tur)
        if anahtar in self._ist:
            return self._ist[anahtar]
        sonuc = self._ist_hesapla(k, tur)
        self._ist[anahtar] = sonuc
        return sonuc

    def _ist_hesapla(self, k: KosulluKural, tur: str):
        ham = self._ham_degerler(k)
        if tur == "yinelenen":
            sayac = Counter()
            anahtar = self._anahtar
            for v in ham:
                sayac[v if type(v) is float else anahtar(v)] += 1      # float anahtarı doğrudan: hızlı yol
            sayac.pop(None, None)
            return sayac
        sayilar = sorted([v for v in ham if type(v) is float or (_sayi_mi(v))])
        if tur == "ilk_son":
            if not sayilar:
                return None
            adet = max(1, int(len(sayilar) * k.n / 100)) if k.yuzde else k.n
            sirali = sayilar if k.alt else sayilar[::-1]
            return sirali[min(adet, len(sirali)) - 1]
        if tur == "ortalama":
            if not sayilar:
                return 0.0, 0.0
            ort = sum(sayilar) / len(sayilar)
            sd = (sum((x - ort) ** 2 for x in sayilar) / (len(sayilar) - 1)) ** 0.5 if len(sayilar) > 1 else 0.0
            return ort, sd
        if not sayilar:
            return None
        capa = k.capa()
        if tur == "cubuk":
            return (self._nokta_degeri(k.min_nokta, sayilar, capa), self._nokta_degeri(k.max_nokta, sayilar, capa))
        if tur == "olcek":
            noktalar = [(self._nokta_degeri(n[:2], sayilar, capa), n[2]) for n in k.noktalar]
            return sorted(noktalar, key=lambda x: x[0])
        return None

    def _nokta_degeri(self, nokta, sayilar, capa) -> float:
        tur, deger = nokta[0], nokta[1]
        if tur == "min":
            return sayilar[0]
        if tur == "max":
            return sayilar[-1]
        x = 0.0
        if deger is not None:
            v = _formul_degeri(deger if deger.startswith("=") else "=" + deger, capa, self.sayfa, capa[0], capa[1],
                               self.kitap)
            x = float(v) if _sayi_mi(v) else 0.0
        if tur == "yuzde":
            return sayilar[0] + (sayilar[-1] - sayilar[0]) * x / 100.0
        if tur == "yuzdebirlik":
            return yuzdebirlik(sayilar, x)
        return x                                           # "sayi" ve "formul"

    @staticmethod
    def _olcek_rengi(noktalar, v: float) -> str:
        if v <= noktalar[0][0]:
            return noktalar[0][1]
        for (x0, r0), (x1, r1) in zip(noktalar, noktalar[1:]):
            if v <= x1:
                return r1 if x1 == x0 else _renk_karisimi(r0, r1, (v - x0) / (x1 - x0))
        return noktalar[-1][1]
