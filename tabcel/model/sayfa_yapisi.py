"""Yazdırma/sayfa yapısı ayarları (Faz 4 / 4d). Qt yok. Sayfa başına saklanır (`Sayfa.sayfa_yapisi`)."""
from dataclasses import dataclass, replace
from typing import Optional, Tuple

from .adres import Aralik

# Kağıt boyutları (cm, dikey: genişlik × yükseklik)
KAGITLAR = {
    "A3": (29.7, 42.0), "A4": (21.0, 29.7), "A5": (14.8, 21.0),
    "Letter": (21.59, 27.94), "Legal": (21.59, 35.56),
}
YONLER = ("dikey", "yatay")
CM_INC = 2.54
PX_CM = 96 / CM_INC          # 96 dpi: 1 cm ≈ 37,8 px (ızgara pikseli ile aynı birim)


@dataclass(frozen=True)
class SayfaYapisi:
    """Excel'in "Sayfa Düzeni" ayarlarının çekirdeği; varsayılanlar Excel'inki (A4, dikey, %100,
    kenar boşlukları 1,91 / 1,78 cm)."""
    yon: str = "dikey"
    kagit: str = "A4"
    ust: float = 1.91
    alt: float = 1.91
    sol: float = 1.78
    sag: float = 1.78
    olcek: int = 100                                   # % (10–400); `sigdir_genislik` açıkken yok sayılır
    sigdir_genislik: bool = False                      # tüm sütunlar tek sayfa genişliğine sığsın
    alan: Optional[Aralik] = None                      # yazdırma alanı; None = kullanılan alan
    baslik_satirlari: Optional[Tuple[int, int]] = None  # her sayfada yinelenen satırlar (ilk, son)
    kilavuz: bool = False                              # kılavuz çizgilerini yazdır
    yatay_ortala: bool = False

    def __post_init__(self):
        if self.yon not in YONLER:
            raise ValueError(f"yön şunlardan biri olmalı: {YONLER}")
        if self.kagit not in KAGITLAR:
            raise ValueError(f"bilinmeyen kağıt: {self.kagit}")
        if not 10 <= int(self.olcek) <= 400:
            raise ValueError("ölçek %10–%400 arasında olmalı")
        for ad in ("ust", "alt", "sol", "sag"):
            if not 0 <= getattr(self, ad) <= 10:
                raise ValueError("kenar boşluğu 0–10 cm olmalı")
        if self.baslik_satirlari is not None:
            a, b = self.baslik_satirlari
            if not 1 <= a <= b:
                raise ValueError("başlık satırları geçersiz")

    def degistir(self, **alanlar) -> "SayfaYapisi":
        return replace(self, **alanlar)

    def kagit_px(self) -> Tuple[float, float]:
        """(genişlik, yükseklik) 96 dpi piksel; yöne göre."""
        g, y = KAGITLAR[self.kagit]
        if self.yon == "yatay":
            g, y = y, g
        return g * PX_CM, y * PX_CM

    def yazdirilabilir_px(self) -> Tuple[float, float]:
        """Kenar boşlukları düşülmüş yazdırılabilir alan (genişlik, yükseklik) 96 dpi piksel."""
        g, y = self.kagit_px()
        return g - (self.sol + self.sag) * PX_CM, y - (self.ust + self.alt) * PX_CM


VARSAYILAN = SayfaYapisi()
