"""Koşullu biçim kuralları (faz5_tasarim.md §8). Qt yok; değerlendirme `formul/kosul.py`'dedir.

Kural listesi sırası = öncelik (0 en yüksek). `bicim` yalnız Excel `dxf` alanlarını taşır: yazı rengi,
kalın, italik, altı/üstü çizili, dolgu, kenarlık, sayı biçimi — yazı tipi adı/boyutu değiştirmez.
Yapılmayanlar (açılışta uyarı): simge kümeleri, tarih oluşumu, Excel 2010 veri çubuğu uzantıları.
"""
from dataclasses import dataclass, replace
from typing import List, Optional, Sequence, Tuple

from .adres import Aralik, aralik_cikar
from .stil import StilYama

TURLER = ("hucre_degeri", "metin", "bos", "bos_degil", "hata", "hata_degil", "yinelenen", "ilk_son",
          "ortalama", "formul", "renk_olcegi", "veri_cubugu")
ISLECLER = ("arasinda", "arasinda_degil", "esit", "esit_degil", "buyuk", "kucuk", "buyuk_esit", "kucuk_esit")
METIN_ISLECLERI = ("icerir", "icermez", "baslar", "biter")
NOKTA_TURLERI = ("min", "max", "sayi", "yuzde", "yuzdebirlik", "formul")
VERI_CUBUGU_RENKLERI = {"mavi": "#638EC6", "yesil": "#63BE7B", "kirmizi": "#F8696B", "turuncu": "#FFB628",
                        "acik_mavi": "#008AEF", "mor": "#D6007B"}
RENK_OLCEKLERI = {                       # (ad -> noktalar: 3 nokta [min, yüzdebirlik 50, max])
    "yesil_sari_kirmizi": (("min", None, "#F8696B"), ("yuzdebirlik", "=50", "#FFEB84"), ("max", None, "#63BE7B")),
    "kirmizi_sari_yesil": (("min", None, "#63BE7B"), ("yuzdebirlik", "=50", "#FFEB84"), ("max", None, "#F8696B")),
    "yesil_beyaz": (("min", None, "#FCFCFF"), ("max", None, "#63BE7B")),
    "beyaz_kirmizi": (("min", None, "#FCFCFF"), ("max", None, "#F8696B")),
}


@dataclass(frozen=True)
class KosulluKural:
    """Değişmez kural. Formül alanları saklanan biçimde (`=...`), göreli başvurular `araliklar[0]`'ın sol üst
    hücresine göre. Nokta = `(tur, deger, renk)` (`deger` None ya da formül/sayı `"=50"`); min/max noktası
    `(tur, deger)`. Alanların hangisinin kullanıldığı `tur`a bağlıdır."""
    araliklar: Tuple[Aralik, ...]
    tur: str = "hucre_degeri"
    bicim: Optional[StilYama] = None
    dur: bool = False
    islec: str = "buyuk"
    formul1: Optional[str] = None
    formul2: Optional[str] = None
    metin: str = ""
    benzersiz: bool = False
    n: int = 10
    alt: bool = False
    yuzde: bool = False
    ustu: bool = True
    esit: bool = False
    std: int = 0
    noktalar: Tuple[Tuple[str, Optional[str], str], ...] = ()
    renk: str = "#638EC6"
    min_nokta: Tuple[str, Optional[str]] = ("min", None)
    max_nokta: Tuple[str, Optional[str]] = ("max", None)
    yalniz_cubuk: bool = False
    gradyan: bool = True

    def __post_init__(self):
        if self.tur not in TURLER:
            raise ValueError(f"Bilinmeyen koşullu biçim türü: {self.tur}")
        if self.tur == "hucre_degeri" and self.islec not in ISLECLER:
            raise ValueError(f"Bilinmeyen işleç: {self.islec}")
        if self.tur == "metin" and self.islec not in METIN_ISLECLERI:
            raise ValueError(f"Bilinmeyen metin işleci: {self.islec}")
        if self.tur == "renk_olcegi" and len(self.noktalar) not in (2, 3):
            raise ValueError("Renk ölçeği 2 ya da 3 nokta ister")
        for n in tuple(self.noktalar) + (self.min_nokta, self.max_nokta):
            if n[0] not in NOKTA_TURLERI:
                raise ValueError(f"Bilinmeyen nokta türü: {n[0]}")

    def capa(self) -> Tuple[int, int]:
        a = self.araliklar[0]
        return a.ilk_satir, a.ilk_sutun

    def bicimsiz_mu(self) -> bool:
        """Görsel etkisi olmayan kural (biçimi boş ve renk ölçeği/veri çubuğu değil)."""
        return self.tur not in ("renk_olcegi", "veri_cubugu") and (self.bicim is None or self.bicim.bos_mu())


def kural_ekle(eski: Sequence[KosulluKural], kural: KosulluKural, basa: bool = True) -> List[KosulluKural]:
    """Yeni kural varsayılan olarak EN YÜKSEK önceliğe eklenir (Excel); `basa=False` sona."""
    return [kural] + list(eski) if basa else list(eski) + [kural]


def aralik_temizle(eski: Sequence[KosulluKural], araliklar: Sequence[Aralik]) -> List[KosulluKural]:
    """`araliklar` hücrelerinden kuralların etkisini kaldırır (Kuralları Temizle ▸ Seçili Hücrelerden);
    aralıksız kalan kural düşer, öncelik sırası korunur."""
    sonuc: List[KosulluKural] = []
    for k in eski:
        kalan = list(k.araliklar)
        for a in araliklar:
            kalan = [p for x in kalan for p in aralik_cikar(x, a)]
        if not kalan:
            continue
        sonuc.append(k if tuple(kalan) == tuple(k.araliklar) else replace(k, araliklar=tuple(kalan)))
    return sonuc
