"""Grafik geometrisi: Qt'siz **çizim listesi** (Faz 6 / 6c; `faz6_tasarim.md` §4).

`cizim_listesi(veri, grafik, boyut, olcer)` eksen ölçeğini, düzeni ve her türün şeklini hesaplar; sonuç, ilkellerden
(dikdörtgen, çizgi, kırık çizgi, çokgen, dilim, işaret, metin) oluşan bir listedir. Ekran boyayıcısı (`ui`), yazdırma/PDF ve
testler aynı listeyi kullanır — geometri sayısal olarak doğrulanır (piksel karşılaştırması yok).

Koordinatlar piksel, y aşağı doğru. `olcer(metin, pt) -> (genişlik, yükseklik)` dışarıdan verilir (arayüz `QFontMetrics`,
testler sahte ölçer). `olcek`: yakınlaştırma/yazıcı çarpanı; `boyut` zaten ölçeklenmiş piksel olmalı, boşluklar ve yazı
boyları (`pt`) `olcek` ile çarpılır.
"""
import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple, Union

from .gosterim import goster
from .grafik import Grafik
from .grafik_verisi import GrafikVerisi

PALET = ("#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47")   # Office 2013+ vurguları
YAZI_RENGI = "#595959"
IZGARA_RENGI = "#D9D9D9"
EKSEN_RENGI = "#BFBFBF"
ARKA_PLAN = "#FFFFFF"
VERI_YOK = "Grafik için veri yok"
KUME_BOSLUGU = 1.5            # Excel varsayılanı: boşluk genişliği %150 (§8b-79: %219 olabilir), çakışma %0

Olcer = Callable[[str, float], Tuple[float, float]]


# ------------------------------------------------------------------ çizim ilkelleri
@dataclass(frozen=True)
class Dikdortgen:
    x: float
    y: float
    w: float
    h: float
    dolgu: Optional[str] = None
    kenar: Optional[str] = None


@dataclass(frozen=True)
class Cizgi:
    x1: float
    y1: float
    x2: float
    y2: float
    renk: str = EKSEN_RENGI
    kalinlik: float = 1.0


@dataclass(frozen=True)
class Dizi:
    """Kırık çizgi; `noktalar` içinde `None` çizgiyi koparır (boş değer)."""
    noktalar: Tuple[Optional[Tuple[float, float]], ...]
    renk: str = PALET[0]
    kalinlik: float = 2.25


@dataclass(frozen=True)
class Cokgen:
    noktalar: Tuple[Tuple[float, float], ...]
    dolgu: str = PALET[0]


@dataclass(frozen=True)
class Dilim:
    """Pasta/halka dilimi. Açılar **derece**, 12 yönünden **saat yönünde** ölçülür; `r_ic` > 0 ise halka."""
    cx: float
    cy: float
    r_ic: float
    r_dis: float
    aci0: float
    aci1: float
    dolgu: str = PALET[0]


@dataclass(frozen=True)
class Isaret:
    x: float
    y: float
    boyut: float
    sekil: str = "daire"
    dolgu: str = PALET[0]


@dataclass(frozen=True)
class Metin:
    """(x, y) çapa noktası; `hiza` yatay (sol/orta/sag), `dikey` (ust/orta/alt) çapanın metne göre yeri; `aci` derece
    (−90: aşağıdan yukarı okunur, çapa metnin ortası)."""
    x: float
    y: float
    metin: str
    hiza: str = "orta"
    dikey: str = "orta"
    pt: float = 9.0
    renk: str = YAZI_RENGI
    kalin: bool = False
    aci: float = 0.0


Cizim = Union[Dikdortgen, Cizgi, Dizi, Cokgen, Dilim, Isaret, Metin]


class CizimListesi(list):
    """Çizim ilkelleri; `grafik_alani` = (x, y, w, h) çizim (eksenlerin içindeki) alanı."""
    grafik_alani: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


# ------------------------------------------------------------------ renk
def _rgb(renk: str) -> Tuple[int, int, int]:
    renk = renk.lstrip("#")
    return int(renk[0:2], 16), int(renk[2:4], 16), int(renk[4:6], 16)


def _hex(r: float, g: float, b: float) -> str:
    return "#%02X%02X%02X" % (round(r), round(g), round(b))


def ton(renk: str, oran: float) -> str:
    """`oran` < 0: siyaha doğru koyulaştır, > 0: beyaza doğru aç (|oran| ≤ 1)."""
    r, g, b = _rgb(renk)
    if oran < 0:
        k = 1 + oran
        return _hex(r * k, g * k, b * k)
    return _hex(r + (255 - r) * oran, g + (255 - g) * oran, b + (255 - b) * oran)


_TONLAR = (0.0, -0.25, 0.4, -0.5, 0.6)


def palet_rengi(i: int) -> str:
    """i. seri/dilim rengi: ilk 6 Office vurgusu, sonra aynı renklerin koyu/açık tonları (Excel sırasına yakın; §8b-81)."""
    return ton(PALET[i % 6], _TONLAR[(i // 6) % len(_TONLAR)])


# ------------------------------------------------------------------ eksen ölçeği
def _yuvarla(x: float) -> float:
    return float(f"{x:.12g}")


def guzel_olcek(en_kucuk: float, en_buyuk: float, hedef: int = 5) -> Tuple[float, float, float]:
    """"Güzel sayılar" ölçeği (1, 2, 2,5, 5 × 10ⁿ adım): `(alt, ust, adim)`; alt ≤ en_kucuk, ust ≥ en_buyuk."""
    if en_kucuk > en_buyuk:
        en_kucuk, en_buyuk = en_buyuk, en_kucuk
    if en_kucuk == en_buyuk:
        if en_kucuk == 0:
            return 0.0, 1.0, 0.2
        pay = abs(en_kucuk) * 0.1
        en_kucuk, en_buyuk = en_kucuk - pay, en_buyuk + pay
    ham = (en_buyuk - en_kucuk) / max(1, hedef)
    us = math.floor(math.log10(ham))
    mag = 10.0 ** us
    adim = 10 * mag
    for c in (1, 2, 2.5, 5, 10):
        if c * mag >= ham * (1 - 1e-9):
            adim = c * mag
            break
    alt = math.floor(en_kucuk / adim + 1e-9) * adim
    ust = math.ceil(en_buyuk / adim - 1e-9) * adim
    return _yuvarla(alt), _yuvarla(ust), _yuvarla(adim)


def etiket_metni(v: float, kod: str = "General") -> str:
    """Eksen/etiket sayı metni: kaynağın sayı biçimi (Genel ise Türkçe sayı gösterimi)."""
    v = _yuvarla(v)
    if kod and kod != "General":
        try:
            from .sayi_bicimi import bicimle
            return bicimle(v, kod).metin
        except Exception:
            pass
    return goster(v)


# ------------------------------------------------------------------ yardımcılar
def _yigin_serileri(veri: GrafikVerisi) -> List[List[Optional[float]]]:
    n = max((len(s.degerler) for s in veri.seriler), default=0)
    return [list(s.degerler) + [None] * (n - len(s.degerler)) for s in veri.seriler]


def _nokta_sayisi(veri: GrafikVerisi) -> int:
    return max((len(s.degerler) for s in veri.seriler), default=0)


def _deger_araligi(veri: GrafikVerisi, grafik: Grafik) -> Tuple[float, float]:
    """Değer ekseni için ham (en küçük, en büyük). Sütun/çubuk/alan sıfırı içerir; çizgi/dağılım Excel kuralı:
    veri aralığı dar değilse (alt ≥ üstün 5/6'sı) eksen verinin altından başlar, aksi halde sıfırdan."""
    m = _yigin_serileri(veri)
    tur, alt = grafik.tur, grafik.alt_tur
    if tur in ("sutun", "cubuk", "alan", "cizgi") and alt == "yuzde_yigili" and tur != "cizgi":
        return 0.0, 1.0
    if alt in ("yigili", "yuzde_yigili") and tur in ("sutun", "cubuk", "alan", "cizgi"):
        pozitif = [sum(v for v in kol if v is not None and v > 0) for kol in zip(*m)] if m else []
        negatif = [sum(v for v in kol if v is not None and v < 0) for kol in zip(*m)] if m else []
        if tur == "cizgi":
            toplamlar = [sum(v or 0.0 for v in kol) for kol in zip(*m)]
            lo, hi = (min(toplamlar), max(toplamlar)) if toplamlar else (0.0, 1.0)
        else:
            lo, hi = min([0.0] + negatif), max([0.0] + pozitif)
    else:
        tum = [v for kol in m for v in kol if v is not None]
        if not tum:
            return 0.0, 1.0
        lo, hi = min(tum), max(tum)
        if tur in ("sutun", "cubuk", "alan"):
            lo, hi = min(lo, 0.0), max(hi, 0.0)
    if tur in ("cizgi", "dagilim"):
        lo, hi = _excel_sifir_kurali(lo, hi)
    return lo, hi


def _excel_sifir_kurali(lo: float, hi: float) -> Tuple[float, float]:
    if lo >= 0 and hi > 0 and (hi - lo) / hi > 1 / 6:
        lo = 0.0
    elif hi <= 0 and lo < 0 and (hi - lo) / -lo > 1 / 6:
        hi = 0.0
    return lo, hi


def _eksen(lo: float, hi: float, hedef: int, kullanici_alt: Optional[float], kullanici_ust: Optional[float]):
    """Döner `(alt, ust, adim, isaretler)`; kullanıcı sınırı verilmişse eksen onu kullanır."""
    if kullanici_alt is not None or kullanici_ust is not None:
        a = kullanici_alt if kullanici_alt is not None else lo
        u = kullanici_ust if kullanici_ust is not None else hi
        if u <= a:
            u = a + 1
        _, _, adim = guzel_olcek(a, u, hedef)
        alt, ust = a, u
    else:
        alt, ust, adim = guzel_olcek(lo, hi, hedef)
    isaretler = []
    k = 0
    while True:
        v = _yuvarla(alt + k * adim)
        if v > ust + adim * 1e-6:
            break
        isaretler.append(v)
        k += 1
        if k > 200:
            break
    return alt, ust, adim, isaretler


def min_max_bosalt(xs: Sequence[float], ys: Sequence[Optional[float]],
                   kova: float = 1.0) -> List[Optional[Tuple[float, float]]]:
    """Çok noktalı serileri piksel kovası başına en küçük/en büyük değere indirger (sıra korunur, boşluk `None`).
    Çıktı ≤ ~ 2 × kova sayısı + boşluklar."""
    out: List[Optional[Tuple[float, float]]] = []
    kova_no = None
    en_az = en_cok = None            # (idx, x, y)
    son_bos = False

    def bosalt():
        nonlocal en_az, en_cok
        if en_az is None:
            return
        a, b = sorted((en_az, en_cok), key=lambda t: t[0])
        out.append((a[1], a[2]))
        if a[0] != b[0]:
            out.append((b[1], b[2]))
        en_az = en_cok = None

    for i, (x, y) in enumerate(zip(xs, ys)):
        if y is None:
            bosalt()
            kova_no = None
            if not son_bos:
                out.append(None)
            son_bos = True
            continue
        son_bos = False
        k = math.floor(x / kova)
        if k != kova_no:
            bosalt()
            kova_no = k
        t = (i, x, y)
        if en_az is None:
            en_az = en_cok = t
        else:
            if y < en_az[2]:
                en_az = t
            if y > en_cok[2]:
                en_cok = t
    bosalt()
    while out and out[-1] is None:
        out.pop()
    return out


# ------------------------------------------------------------------ ana işlev
def cizim_listesi(veri: GrafikVerisi, grafik: Grafik, boyut: Tuple[float, float], olcer: Olcer,
                  olcek: float = 1.0) -> CizimListesi:
    return _Ciz(veri, grafik, boyut, olcer, olcek).uret()


class _Ciz:
    def __init__(self, veri, grafik, boyut, olcer, olcek):
        self.veri, self.g, (self.W, self.H), self.olcer, self.s = veri, grafik, boyut, olcer, olcek
        self.liste = CizimListesi()
        self.pt_eksen = 9.0 * olcek
        self.pad = 8.0 * olcek

    # --- metin
    def olc(self, metin: str, pt: float) -> Tuple[float, float]:
        return self.olcer(metin, pt)

    def metin(self, x, y, m, hiza="orta", dikey="orta", pt=None, kalin=False, aci=0.0, renk=YAZI_RENGI):
        self.liste.append(Metin(x, y, m, hiza, dikey, pt if pt is not None else self.pt_eksen, renk, kalin, aci))

    def seri_rengi(self, i: int) -> str:
        r = self.veri.seriler[i].renk
        return r if r else palet_rengi(i)

    # --- üst düzey
    def uret(self) -> CizimListesi:
        g, v, W, H, pad = self.g, self.veri, self.W, self.H, self.pad
        self.liste.append(Dikdortgen(0, 0, W, H, ARKA_PLAN, IZGARA_RENGI))
        alan = [pad, pad, W - pad, H - pad]            # sol, üst, sağ, alt
        if g.baslik:
            tw, th = self.olc(g.baslik, 14 * self.s)
            self.metin(W / 2, alan[1], g.baslik, "orta", "ust", 14 * self.s, True)
            alan[1] += th + pad * 0.75
        bos = v.bos or (g.tur in ("pasta", "halka") and sum(self._pasta_degerleri()) <= 0)
        if bos:
            self.metin((alan[0] + alan[2]) / 2, (alan[1] + alan[3]) / 2, VERI_YOK, "orta", "orta", 11 * self.s)
            self.liste.grafik_alani = (alan[0], alan[1], alan[2] - alan[0], alan[3] - alan[1])
            return self.liste
        legend = self._gosterge_yerlestir(alan)
        if g.x_baslik and g.tur not in ("pasta", "halka"):
            tw, th = self.olc(g.x_baslik, 10 * self.s)
            self.metin((alan[0] + alan[2]) / 2, alan[3], g.x_baslik, "orta", "alt", 10 * self.s, True)
            alan[3] -= th + pad * 0.5
        if g.y_baslik and g.tur not in ("pasta", "halka"):
            tw, th = self.olc(g.y_baslik, 10 * self.s)
            self.metin(alan[0] + th / 2, (alan[1] + alan[3]) / 2, g.y_baslik, "orta", "orta", 10 * self.s, True, -90.0)
            alan[0] += th + pad * 0.5
        if g.tur in ("pasta", "halka"):
            self._pasta(alan)
        elif g.tur == "dagilim":
            self._dagilim(alan)
        elif g.tur == "cubuk":
            self._eksenli(alan, yatay=True)
        else:
            self._eksenli(alan, yatay=False)
        if legend is not None:
            legend()
        return self.liste

    # --- gösterge
    def _gosterge_girdileri(self) -> List[Tuple[str, str]]:
        g, v = self.g, self.veri
        if g.tur in ("pasta", "halka"):
            kat = v.seriler[0].kategoriler
            n = len(v.seriler[0].degerler)
            return [(str(kat[i]), palet_rengi(i)) for i in range(min(n, 60))]
        return [(s.ad, self.seri_rengi(i)) for i, s in enumerate(v.seriler)]

    def _gosterge_yerlestir(self, alan):
        g = self.g
        if g.gosterge is None:
            return None
        girdiler = self._gosterge_girdileri()
        if not girdiler:
            return None
        pt, pad = self.pt_eksen, self.pad
        kutu, bosluk = 10.0 * self.s, 6.0 * self.s
        olc = [self.olc(m, pt) for m, _ in girdiler]
        satir_h = max(h for _, h in olc) + 4 * self.s
        yatay = g.gosterge in ("ust", "alt")
        if yatay:
            toplam = sum(kutu + bosluk + w + 2 * bosluk for w, _ in olc)
            w_, h_ = min(toplam, alan[2] - alan[0]), satir_h
        else:
            w_ = max(w for w, _ in olc) + kutu + bosluk
            h_ = satir_h * len(girdiler)
        if g.gosterge == "sag":
            x0, y0 = alan[2] - w_, (alan[1] + alan[3]) / 2 - h_ / 2
            alan[2] -= w_ + pad
        elif g.gosterge == "sol":
            x0, y0 = alan[0], (alan[1] + alan[3]) / 2 - h_ / 2
            alan[0] += w_ + pad
        elif g.gosterge == "ust":
            x0, y0 = (alan[0] + alan[2]) / 2 - w_ / 2, alan[1]
            alan[1] += h_ + pad * 0.5
        else:
            x0, y0 = (alan[0] + alan[2]) / 2 - w_ / 2, alan[3] - h_
            alan[3] -= h_ + pad * 0.5
        cizgi_mi = g.tur == "cizgi"

        def ciz():
            x, y = x0, y0
            for (m, renk), (w, h) in zip(girdiler, olc):
                if cizgi_mi:
                    self.liste.append(Cizgi(x, y + satir_h / 2, x + kutu, y + satir_h / 2, renk, 2.25 * self.s))
                else:
                    self.liste.append(Dikdortgen(x, y + (satir_h - kutu) / 2, kutu, kutu, renk, None))
                self.metin(x + kutu + bosluk, y + satir_h / 2, m, "sol", "orta")
                if yatay:
                    x += kutu + bosluk + w + 2 * bosluk
                else:
                    y += satir_h
        return ciz

    # --- kategori etiketleri (seyreltilmiş)
    def _kategori_etiket_yazi(self, i: int) -> str:
        kat = self.veri.seriler[0].kategoriler
        return str(kat[i]) if i < len(kat) else str(i + 1)

    def _etiket_adimi(self, n: int, kullanilabilir: float, yatay_olcu) -> int:
        """Her k'inci etiketi çiz: örnek etiket genişliklerinden k hesaplanır."""
        ornek = range(0, n, max(1, n // 50))
        en_uzun = max((yatay_olcu(self._kategori_etiket_yazi(i)) for i in ornek), default=0.0)
        adim = n and kullanilabilir / n
        if adim <= 0:
            return max(1, n)
        return max(1, math.ceil(en_uzun * 1.2 / adim))

    # --- eksenli türler (sütun, çubuk, çizgi, alan)
    def _eksenli(self, alan, yatay: bool):
        g, v, s, pad, pt = self.g, self.veri, self.s, self.pad, self.pt_eksen
        n = _nokta_sayisi(v)
        lo, hi = _deger_araligi(v, g)
        yuzde = g.alt_tur == "yuzde_yigili" and g.tur in ("sutun", "cubuk", "alan")
        kod = "0%" if yuzde else v.sayi_bicimi
        _, lh = self.olc("Ag", pt)
        w_tum, h_tum = alan[2] - alan[0], alan[3] - alan[1]
        hedef = max(2, min(10, int((w_tum if yatay else h_tum) / (lh * (4.0 if yatay else 2.2)))))
        alt, ust, adim, isaretler = _eksen(lo, hi, hedef, g.y_min, g.y_max)
        etiketler = [etiket_metni(t, kod) for t in isaretler]
        en_genis = max(self.olc(e, pt)[0] for e in etiketler)
        if yatay:                                    # çubuk: kategoriler solda, değerler altta
            kat_gen = min(max((self.olc(self._kategori_etiket_yazi(i), pt)[0]
                               for i in range(0, n, max(1, n // 50))), default=0.0), w_tum * 0.3)
            x0 = alan[0] + kat_gen + 6 * s
            y0 = alan[1] + lh / 2
            pw, ph = alan[2] - x0 - en_genis / 2, alan[3] - y0 - lh - 6 * s
        else:
            x0 = alan[0] + en_genis + 6 * s
            y0 = alan[1] + lh / 2
            pw, ph = alan[2] - x0, alan[3] - y0 - lh - 6 * s
        pw, ph = max(pw, 1.0), max(ph, 1.0)
        self.liste.grafik_alani = (x0, y0, pw, ph)

        def dm(val):                                 # değer → piksel (dikey: y; yatay: x)
            f = (val - alt) / (ust - alt) if ust > alt else 0.0
            return x0 + f * pw if yatay else y0 + ph - f * ph
        # ızgara + değer etiketleri
        for t, e in zip(isaretler, etiketler):
            p = dm(t)
            if yatay:
                self.liste.append(Cizgi(p, y0, p, y0 + ph, IZGARA_RENGI))
                self.metin(p, y0 + ph + 6 * s, e, "orta", "ust")
            else:
                self.liste.append(Cizgi(x0, p, x0 + pw, p, IZGARA_RENGI))
                self.metin(x0 - 6 * s, p, e, "sag", "orta")
        taban = dm(min(max(0.0, alt), ust))
        # kategori konumları
        kat_g = (ph if yatay else pw) / max(1, n)

        def kat_orta(k):                              # kategori k'nin ortası (alan türü hariç)
            return (y0 + ph - (k + 0.5) * kat_g) if yatay else (x0 + (k + 0.5) * kat_g)
        if g.tur in ("sutun", "cubuk"):
            self._cubuklar(n, dm, taban, kat_g, kat_orta, x0, y0, pw, ph, yatay, alt, ust)
        elif g.tur == "cizgi":
            self._cizgiler(n, dm, kat_orta, pw, alt, ust)
        else:
            self._alanlar(n, dm, x0, y0, pw, ph, taban, alt, ust)
        # eksen çizgisi (kategori ekseni) + kategori etiketleri
        if yatay:
            self.liste.append(Cizgi(taban, y0, taban, y0 + ph, EKSEN_RENGI))
        else:
            self.liste.append(Cizgi(x0, taban, x0 + pw, taban, EKSEN_RENGI))
        alan_turu = g.tur == "alan"
        if n:
            if yatay:
                adim_k = self._etiket_adimi(n, ph, lambda m: self.olc(m, pt)[1])
            else:
                adim_k = self._etiket_adimi(n, pw, lambda m: self.olc(m, pt)[0])
            for k in range(0, n, adim_k):
                m = self._kategori_etiket_yazi(k)
                if yatay:
                    self.metin(x0 - 6 * s, kat_orta(k), m, "sag", "orta")
                else:
                    kx = (x0 + (k * pw / (n - 1) if n > 1 else pw / 2)) if alan_turu else kat_orta(k)
                    self.metin(kx, y0 + ph + 6 * s, m, "orta", "ust")

    def _cubuklar(self, n, dm, taban, kat_g, kat_orta, x0, y0, pw, ph, yatay, alt, ust):
        g, v, s = self.g, self.veri, self.s
        m = _yigin_serileri(v)
        ns = len(m)
        yigili = g.alt_tur in ("yigili", "yuzde_yigili")
        yuzde = g.alt_tur == "yuzde_yigili"
        genis = kat_g / ((1 if yigili else ns) + KUME_BOSLUGU)
        sinirli = kat_g < 1.0                       # kategori pikselden küçük: kovaya göre en büyük değer
        bucket = max(1, int(math.ceil(1.0 / kat_g))) if sinirli else 1
        for k0 in range(0, n, bucket):
            ks = range(k0, min(n, k0 + bucket))
            k = k0
            orta = kat_orta(k0)
            if yigili:
                poz = neg = 0.0
                toplam = sum(abs(m[i][k] or 0.0) for i in range(ns)) if yuzde else 1.0
                for i in range(ns):
                    d = m[i][k]
                    if d is None or d == 0:
                        continue
                    d = d / toplam if yuzde and toplam else d
                    a, b = (poz, poz + d) if d > 0 else (neg + d, neg)
                    if d > 0:
                        poz += d
                    else:
                        neg += d
                    self._cubuk(i, orta - genis / 2, genis, dm(a), dm(b), yatay)
            else:
                bas = orta - ns * genis / 2 if not yatay else orta + ns * genis / 2
                for i in range(ns):
                    degerler = [m[i][q] for q in ks if m[i][q] is not None]
                    if not degerler:
                        continue
                    d = max(degerler, key=abs)
                    pos = (bas + i * genis) if not yatay else (bas - (i + 1) * genis)
                    self._cubuk(i, pos, genis, taban, dm(d), yatay)
                    if g.deger_etiketi and not sinirli:
                        self._cubuk_etiketi(i, pos, genis, dm(d), d, yatay, taban)
        if g.deger_etiketi and yigili and not sinirli:
            pass                                     # yığılı değer etiketleri sonra (kapsam dışı)

    def _cubuk(self, i, pos, genis, d1, d2, yatay):
        r = self.seri_rengi(i)
        a, b = min(d1, d2), max(d1, d2)
        if yatay:
            self.liste.append(Dikdortgen(a, pos, b - a, genis, r, None))
        else:
            self.liste.append(Dikdortgen(pos, a, genis, b - a, r, None))

    def _cubuk_etiketi(self, i, pos, genis, uc, d, yatay, taban):
        kod = self.veri.sayi_bicimi
        e = etiket_metni(d, kod)
        if yatay:
            self.metin(uc + (4 * self.s if d >= 0 else -4 * self.s), pos + genis / 2, e,
                       "sol" if d >= 0 else "sag", "orta")
        else:
            self.metin(pos + genis / 2, uc - (3 * self.s if d >= 0 else -3 * self.s), e, "orta",
                       "alt" if d >= 0 else "ust")

    def _cizgiler(self, n, dm, kat_orta, pw, alt, ust):
        g, v, s = self.g, self.veri, self.s
        m = _yigin_serileri(v)
        yigili = g.alt_tur == "yigili"
        toplam = [0.0] * n
        for i, kol in enumerate(m):
            ys = []
            for k, d in enumerate(kol):
                if yigili:
                    toplam[k] += d or 0.0
                    ys.append(toplam[k])
                else:
                    ys.append(d)
            xs = [kat_orta(k) for k in range(n)]
            pikseller = [(x, dm(y) if y is not None else None) for x, y in zip(xs, ys)]
            if n > 2 * max(pw, 1.0):                  # çok nokta: piksel kovası başına en küçük/en büyük
                nokta = min_max_bosalt(xs, [None if p[1] is None else p[1] for p in pikseller])
            else:
                nokta = [(x, y) if y is not None else None for x, y in pikseller]
            renk = self.seri_rengi(i)
            self.liste.append(Dizi(tuple(nokta), renk, 2.25 * s))
            if n <= pw / 6:                           # seyrek: işaretçiler
                for x, y in pikseller:
                    if y is not None:
                        self.liste.append(Isaret(x, y, 5.0 * s, "daire", renk))
            if g.deger_etiketi and n <= pw / 20:
                for (x, y), d in zip(pikseller, kol):
                    if y is not None and d is not None:
                        self.metin(x, y - 6 * s, etiket_metni(d, v.sayi_bicimi), "orta", "alt")

    def _alanlar(self, n, dm, x0, y0, pw, ph, taban, alt, ust):
        g, v, s = self.g, self.veri, self.s
        m = _yigin_serileri(v)
        yigili = g.alt_tur in ("yigili", "yuzde_yigili")
        yuzde = g.alt_tur == "yuzde_yigili"

        def px(k):
            return x0 + (k * pw / (n - 1) if n > 1 else pw / 2)
        xs = [px(k) for k in range(n)]
        alt_cizgi = [0.0] * n
        sirala = range(len(m))
        for i in sirala:
            kol = [d if d is not None else 0.0 for d in m[i]]
            if yigili:
                if yuzde:
                    tp = [sum(abs((m[j][k] or 0.0)) for j in range(len(m))) or 1.0 for k in range(n)]
                    kol = [kol[k] / tp[k] for k in range(n)]
                ust_c = [alt_cizgi[k] + kol[k] for k in range(n)]
                onceki = alt_cizgi
                alt_cizgi = ust_c
            else:
                ust_c, onceki = kol, [0.0] * n
            if n > 2 * max(pw, 1.0):
                ust_n = min_max_bosalt(xs, [dm(y) for y in ust_c])
                alt_n = min_max_bosalt(xs, [dm(y) for y in onceki])
                ust_pts = [p for p in ust_n if p is not None]
                alt_pts = [p for p in alt_n if p is not None]
            else:
                ust_pts = [(x, dm(y)) for x, y in zip(xs, ust_c)]
                alt_pts = [(x, dm(y)) for x, y in zip(xs, onceki)]
            self.liste.append(Cokgen(tuple(ust_pts + alt_pts[::-1]), self.seri_rengi(i)))

    # --- pasta / halka
    def _pasta_degerleri(self) -> List[float]:
        if not self.veri.seriler:
            return []
        return [d if d is not None and d > 0 else 0.0 for d in self.veri.seriler[0].degerler]

    def _pasta(self, alan):
        g, s = self.g, self.s
        d = self._pasta_degerleri()
        toplam = sum(d)
        cx, cy = (alan[0] + alan[2]) / 2, (alan[1] + alan[3]) / 2
        r = max(1.0, min(alan[2] - alan[0], alan[3] - alan[1]) / 2 - 4 * s)
        r_ic = r * 0.5 if g.tur == "halka" else 0.0
        self.liste.grafik_alani = (cx - r, cy - r, 2 * r, 2 * r)
        aci = 0.0
        for i, deger in enumerate(d):
            if deger <= 0:
                continue
            son = aci + 360.0 * deger / toplam
            self.liste.append(Dilim(cx, cy, r_ic, r, aci, son, palet_rengi(i)))
            if g.deger_etiketi:
                orta = math.radians((aci + son) / 2)
                rr = (r + r_ic) / 2 if g.tur == "halka" else r * 0.65
                self.metin(cx + rr * math.sin(orta), cy - rr * math.cos(orta), f"{round(100 * deger / toplam)}%",
                           "orta", "orta", renk="#FFFFFF")
            aci = son

    # --- dağılım
    def _dagilim(self, alan):
        g, v, s, pt, pad = self.g, self.veri, self.s, self.pt_eksen, self.pad
        xs_t = [x for sr in v.seriler for x in (sr.x or ()) if x is not None]
        ys_t = [y for sr in v.seriler for y in sr.degerler if y is not None]
        xlo, xhi = _excel_sifir_kurali(min(xs_t), max(xs_t)) if xs_t else (0.0, 1.0)
        ylo, yhi = _excel_sifir_kurali(min(ys_t), max(ys_t)) if ys_t else (0.0, 1.0)
        _, lh = self.olc("Ag", pt)
        w_tum, h_tum = alan[2] - alan[0], alan[3] - alan[1]
        ha = max(2, min(10, int(h_tum / (lh * 2.2))))
        wa = max(2, min(10, int(w_tum / (lh * 6.0))))
        ya, yu, _, yi = _eksen(ylo, yhi, ha, g.y_min, g.y_max)
        xa, xu, _, xi = _eksen(xlo, xhi, wa, g.x_min, g.x_max)
        kod = v.sayi_bicimi
        yet = [etiket_metni(t, kod) for t in yi]
        xet = [etiket_metni(t) for t in xi]
        yw = max(self.olc(e, pt)[0] for e in yet)
        x0, y0 = alan[0] + yw + 6 * s, alan[1] + lh / 2
        sag_pay = max(self.olc(xet[-1], pt)[0] / 2, 6 * s)           # son etiket ve kenardaki işaretçi kırpılmasın
        pw, ph = max(alan[2] - x0 - sag_pay, 1.0), max(alan[3] - y0 - lh - 6 * s, 1.0)
        self.liste.grafik_alani = (x0, y0, pw, ph)

        def xm(val):
            return x0 + ((val - xa) / (xu - xa) if xu > xa else 0.0) * pw

        def ym(val):
            return y0 + ph - ((val - ya) / (yu - ya) if yu > ya else 0.0) * ph
        for t, e in zip(yi, yet):
            self.liste.append(Cizgi(x0, ym(t), x0 + pw, ym(t), IZGARA_RENGI))
            self.metin(x0 - 6 * s, ym(t), e, "sag", "orta")
        for t, e in zip(xi, xet):
            self.liste.append(Cizgi(xm(t), y0, xm(t), y0 + ph, IZGARA_RENGI))
            self.metin(xm(t), y0 + ph + 6 * s, e, "orta", "ust")
        self.liste.append(Cizgi(x0, ym(max(ya, min(0.0, yu))), x0 + pw, ym(max(ya, min(0.0, yu))), EKSEN_RENGI))
        for i, sr in enumerate(v.seriler):
            renk = self.seri_rengi(i)
            goruldu = set()
            for x, y in zip(sr.x or (), sr.degerler):
                if x is None or y is None:
                    continue
                px_, py_ = xm(x), ym(y)
                anahtar = (round(px_), round(py_))
                if anahtar in goruldu:                # aynı pikseldeki noktalar tek işaret
                    continue
                goruldu.add(anahtar)
                self.liste.append(Isaret(px_, py_, 7.0 * s, "daire", renk))
