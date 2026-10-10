"""Veri doğrulama kuralları (faz5_tasarim.md §7). Qt yok; denetim `formul/kosul.py`'dedir.

Her hücrede en çok bir kural vardır: yeni kural eski kuralların o hücrelerdeki aralıklarını düşürür
(Excel yeni doğrulamayla eskisinin yerini alır).
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .adres import Aralik, aralik_cikar, aralik_icinde

TURLER = ("her_deger", "tam_sayi", "ondalik", "liste", "tarih", "saat", "metin_uzunlugu", "ozel")
ISLECLER = ("arasinda", "arasinda_degil", "esit", "esit_degil", "buyuk", "kucuk", "buyuk_esit", "kucuk_esit")
STILLER = ("durdur", "uyari", "bilgi")
IKI_DEGERLI = ("arasinda", "arasinda_degil")


@dataclass(frozen=True)
class Dogrulama:
    """`formul1/2` saklanan biçimde: formül ya da sayı/tarih (`=10`), liste sabiti `"Evet,Hayır"` (tırnaklı,
    virgüllü — .xlsx gibi). Göreli başvurular `araliklar[0]`'ın sol üst hücresine göre.
    `giris` = (göster, başlık, ileti); `hata` = (göster, stil, başlık, ileti)."""
    araliklar: Tuple[Aralik, ...]
    tur: str = "her_deger"
    islec: str = "arasinda"
    formul1: Optional[str] = None
    formul2: Optional[str] = None
    bos_yoksay: bool = True
    acilir_liste: bool = True
    giris: Tuple[bool, str, str] = (False, "", "")
    hata: Tuple[bool, str, str, str] = (True, "durdur", "", "")

    def __post_init__(self):
        if self.tur not in TURLER:
            raise ValueError(f"Bilinmeyen doğrulama türü: {self.tur}")
        if self.islec not in ISLECLER:
            raise ValueError(f"Bilinmeyen doğrulama işleci: {self.islec}")
        if self.hata[1] not in STILLER:
            raise ValueError(f"Bilinmeyen hata stili: {self.hata[1]}")

    def capa(self) -> Tuple[int, int]:
        """Göreli başvuruların bağlandığı hücre (ilk aralığın sol üstü)."""
        a = self.araliklar[0]
        return a.ilk_satir, a.ilk_sutun

    def liste_sabiti_mi(self) -> bool:
        return self.tur == "liste" and self.formul1 is not None and not self.formul1.startswith("=")

    def etkisiz_mi(self) -> bool:
        """Kısıt yok ve ileti de gösterilmiyor (kaydedilecek bir şey yok)."""
        return self.tur == "her_deger" and (not self.giris[0] or (self.giris[1] == "" and self.giris[2] == ""))


def liste_sabiti_ogeleri(formul: str) -> List[str]:
    """`"Evet,Hayır"` → ['Evet', 'Hayır'] (tırnaklar atılır; boş öğeler korunur)."""
    govde = formul[1:-1] if len(formul) >= 2 and formul[0] == '"' and formul[-1] == '"' else formul
    return govde.split(",")


def liste_sabiti_yaz(ogeler: Sequence[str]) -> str:
    return '"' + ",".join(ogeler) + '"'


def kural_ara(liste: Sequence[Dogrulama], satir: int, sutun: int) -> Optional[Dogrulama]:
    for dv in liste:
        for a in dv.araliklar:
            if aralik_icinde(a, satir, sutun):
                return dv
    return None


def yeni_liste(eski: Sequence[Dogrulama], araliklar: Sequence[Aralik],
               dv: Optional[Dogrulama]) -> List[Dogrulama]:
    """`araliklar` hücrelerinden eski kuralların etkisini kaldırır; `dv` verildiyse (aralıkları
    `araliklar`) en sona eklenir. Aralıksız kalan kural düşer."""
    from dataclasses import replace
    sonuc: List[Dogrulama] = []
    for kural in eski:
        kalan = list(kural.araliklar)
        for yeni in araliklar:
            kalan = [p for a in kalan for p in aralik_cikar(a, yeni)]
        if not kalan:
            continue
        sonuc.append(kural if tuple(kalan) == tuple(kural.araliklar) else replace(kural, araliklar=tuple(kalan)))
    if dv is not None:
        sonuc.append(dv)
    return sonuc
