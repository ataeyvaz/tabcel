"""Sayfa üzerinde yüzen nesneler: grafik ve resim (Faz 6 / 6a; `faz6_tasarim.md` §1–2). Qt yok.

Hepsi **değişmez** nesnelerdir (`dataclass(frozen=True)`); değişiklik `degistir(**alanlar)` ile yeni nesne
üretir ve komutla (`komutlar.NesneEkle/NesneSil/NesneDegis/NesneSirala`) uygulanır. Sayfa başvuruları
**kimlikle** tutulur (formüllerdeki K6 düzeni): sayfa silinip geri gelince başvuru kendiliğinden düzelir.
"""
from dataclasses import dataclass, field, replace
from typing import Any, List, Optional, Tuple

from .adres import MAX_COL, MAX_ROW, Aralik, aralik_kaydir

TURLER = ("sutun", "cubuk", "cizgi", "pasta", "halka", "alan", "dagilim")
ALT_TURLER = ("kumelenmis", "yigili", "yuzde_yigili")
GOSTERGELER = ("sag", "alt", "ust", "sol")
VARSAYILAN_BOYUT = (480, 288)
EN_KUCUK_BOYUT = (40, 30)


@dataclass(frozen=True)
class Referans:
    """Bir sayfadaki aralık. `sayfa_kimlik`: `Sayfa.kimlik` (ad değil)."""
    sayfa_kimlik: int
    aralik: Aralik


@dataclass(frozen=True)
class Seri:
    """Bir veri serisi. `ad_ref` varsa görünen ad o hücreden gelir, yoksa `ad` (sabit metin), yoksa "Seri{n}".
    `kategori`: kategori etiketleri (dağılımda X değerleri). `renk`: '#rrggbb' ya da None (palet sırası)."""
    ad: Optional[str] = None
    ad_ref: Optional[Referans] = None
    deger: Optional[Referans] = None
    kategori: Optional[Referans] = None
    renk: Optional[str] = None


@dataclass(frozen=True)
class Konum:
    """Sol üst çapa hücresi + o hücreden piksel kayması (%100 yakınlaştırmada, 96 dpi). `dx, dy ≥ 0`."""
    satir: int = 1
    sutun: int = 1
    dx: int = 0
    dy: int = 0

    def __post_init__(self):
        if not (1 <= self.satir <= MAX_ROW and 1 <= self.sutun <= MAX_COL):
            raise ValueError("çapa hücresi sayfa dışında")
        if self.dx < 0 or self.dy < 0:
            raise ValueError("hücre içi kayma negatif olamaz")


def _boyut_dogrula(boyut) -> None:
    g, y = boyut
    if g < 1 or y < 1:
        raise ValueError("boyut en az 1 × 1 piksel olmalı")


@dataclass(frozen=True)
class Grafik:
    kimlik: int = 0                              # 0 = henüz sayfaya eklenmedi (`Sayfa.nesne_ekle` atar)
    tur: str = "sutun"
    alt_tur: str = "kumelenmis"
    seriler: Tuple[Seri, ...] = ()
    baslik: Optional[str] = None
    gosterge: Optional[str] = "sag"
    x_baslik: Optional[str] = None
    y_baslik: Optional[str] = None
    deger_etiketi: bool = False
    y_min: Optional[float] = None
    y_max: Optional[float] = None
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    konum: Konum = field(default_factory=Konum)
    boyut: Tuple[int, int] = VARSAYILAN_BOYUT

    def __post_init__(self):
        if self.tur not in TURLER:
            raise ValueError(f"grafik türü şunlardan biri olmalı: {TURLER}")
        if self.alt_tur not in ALT_TURLER:
            raise ValueError(f"alt tür şunlardan biri olmalı: {ALT_TURLER}")
        if self.gosterge is not None and self.gosterge not in GOSTERGELER:
            raise ValueError(f"gösterge şunlardan biri ya da None olmalı: {GOSTERGELER}")
        _boyut_dogrula(self.boyut)
        object.__setattr__(self, "seriler", tuple(self.seriler))

    def degistir(self, **alanlar) -> "Grafik":
        return replace(self, **alanlar)

    @property
    def etiket(self) -> str:
        return f"Grafik {self.kimlik}"


@dataclass(frozen=True)
class Resim:
    kimlik: int = 0
    veri: bytes = field(default=b"", repr=False)         # PNG/JPEG/GIF/BMP baytları aynen (xlsx'e kayıpsız yazılsın)
    ad: str = ""
    konum: Konum = field(default_factory=Konum)
    boyut: Tuple[int, int] = (200, 150)

    def __post_init__(self):
        _boyut_dogrula(self.boyut)

    def degistir(self, **alanlar) -> "Resim":
        return replace(self, **alanlar)

    @property
    def etiket(self) -> str:
        return f"Resim {self.kimlik}"


def referans_metni(ref: Optional[Referans], sayfa_adi: str) -> str:
    """Ekranda gösterilen/yazılan Excel biçimi: `Sayfa1!$B$2:$B$5` (adda boşluk/özel karakter varsa tırnaklı)."""
    from .adres import sutun_harfe
    if ref is None:
        return ""
    a = ref.aralik
    ad = f"'{sayfa_adi}'" if not sayfa_adi.replace("_", "").isalnum() else sayfa_adi
    bas = f"${sutun_harfe(a.ilk_sutun)}${a.ilk_satir}"
    if (a.ilk_satir, a.ilk_sutun) == (a.son_satir, a.son_sutun):
        return f"{ad}!{bas}"
    return f"{ad}!{bas}:${sutun_harfe(a.son_sutun)}${a.son_satir}"


# ------------------------------------------------------------------ ekle-sil kaydırması
def konum_kaydir(konum: Konum, eksen: int, nerede: int, fark: int, sinir: int) -> Konum:
    """Çapa hücresini satır (`eksen`=0) / sütun (1) ekle-sil sonrası kaydırır (`faz6_tasarim.md` §2.2).
    Silinen bandın içindeki çapa nesneyi silmez: bandın hemen ötesine (`nerede`) iner, o eksendeki hücre içi
    kayma sıfırlanır. Sayfa sınırının dışına itilen çapa son hücreye sıkıştırılır."""
    k = konum.sutun if eksen else konum.satir
    kayma_sifirla = False
    if k >= nerede:
        if fark < 0 and k < nerede - fark:
            k = nerede
            kayma_sifirla = True
        else:
            k = min(k + fark, sinir)
    if eksen:
        return Konum(konum.satir, k, 0 if kayma_sifirla else konum.dx, konum.dy)
    return Konum(k, konum.sutun, konum.dx, 0 if kayma_sifirla else konum.dy)


def referans_kaydir(ref: Optional[Referans], hedef_kimlik: int, eksen: int, nerede: int, fark: int,
                    sinir: int) -> Optional[Referans]:
    """`hedef_kimlik` sayfasındaki ekle-sil sonrası başvurunun yeni hali (tamamen silinen aralık → None)."""
    if ref is None or ref.sayfa_kimlik != hedef_kimlik:
        return ref
    yeni = aralik_kaydir(ref.aralik, eksen, nerede, fark, sinir)
    if yeni is None:
        return None
    return ref if yeni == ref.aralik else Referans(ref.sayfa_kimlik, yeni)


def grafik_referanslarini_kaydir(g: Grafik, hedef_kimlik: int, eksen: int, nerede: int, fark: int,
                                 sinir: int) -> Grafik:
    """Grafiğin tüm başvurularını kaydırır. Değeri kalmayan seri düşer; kategori ya da ad başvurusu
    kaybolan seri kalır (kategorisiz / adsız). Hiç seri kalmasa da grafik silinmez (boş görünür)."""
    yeniler: List[Seri] = []
    degisti = False
    for s in g.seriler:
        deger = referans_kaydir(s.deger, hedef_kimlik, eksen, nerede, fark, sinir)
        kat = referans_kaydir(s.kategori, hedef_kimlik, eksen, nerede, fark, sinir)
        ad_ref = referans_kaydir(s.ad_ref, hedef_kimlik, eksen, nerede, fark, sinir)
        if deger is None and s.deger is not None:
            degisti = True                                   # değeri tamamen silindi: seri düşer
            continue
        if deger is not s.deger or kat is not s.kategori or ad_ref is not s.ad_ref:
            degisti = True
            s = replace(s, deger=deger, kategori=kat, ad_ref=ad_ref)
        yeniler.append(s)
    return replace(g, seriler=tuple(yeniler)) if degisti else g


def nesne_baslangic_olcusu(genislik: int, yukseklik: int, en_cok: int = 600) -> Tuple[int, int]:
    """Resim için varsayılan boyut: doğal boyut, en çok `en_cok` piksel genişlik, oran korunur."""
    if genislik <= 0 or yukseklik <= 0:
        return VARSAYILAN_BOYUT
    if genislik > en_cok:
        yukseklik = max(1, round(yukseklik * en_cok / genislik))
        genislik = en_cok
    return genislik, yukseklik


def kesisir(a: Aralik, b: Aralik) -> bool:
    return not (a.son_satir < b.ilk_satir or a.ilk_satir > b.son_satir
                or a.son_sutun < b.ilk_sutun or a.ilk_sutun > b.son_sutun)


def grafik_aralik_kesisir(g: Grafik, sayfa_kimlik: int, aralik: Aralik) -> bool:
    """Grafiğin herhangi bir başvurusu `sayfa_kimlik` sayfasındaki `aralik` ile kesişiyor mu
    (canlı güncelleme: yalnız ilgili grafikler yeniden kurulur)."""
    for s in g.seriler:
        for ref in (s.ad_ref, s.deger, s.kategori):
            if ref is not None and ref.sayfa_kimlik == sayfa_kimlik and kesisir(ref.aralik, aralik):
                return True
    return False
