"""Tanımlı ad (adlandırılmış aralık/sabit/formül) veri türü. Qt yok. Kurallar: faz5_tasarim.md §4.1.

Doğrulama (`ad_dogrula`), komutlar ve arayüz 5d'dedir; burada yalnız değişmez kayıt ve anahtar.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

from .harmanla import tr_kucuk


@dataclass(frozen=True)
class TanimliAd:
    """`formul` saklanan biçimdedir (`=[1]!$A$1:$B$10`, kanonik İngilizce, başka sayfa kimlikle),
    sabit (`=0.18`) ya da herhangi bir formül olabilir; göreli başvurular A1'e göre saklanır.
    `kapsam`: sayfa kimliği ya da None (çalışma kitabı)."""
    ad: str
    formul: str
    kapsam: Optional[int] = None
    aciklama: str = ""
    gizli: bool = False

    def anahtar(self) -> Tuple[Optional[int], str]:
        return ad_anahtari(self.kapsam, self.ad)


def ad_anahtari(kapsam: Optional[int], ad: str) -> Tuple[Optional[int], str]:
    """`CalismaKitabi.adlar` anahtarı: kapsam + büyük/küçük harf duyarsız (Türkçe) ad."""
    return kapsam, tr_kucuk(ad)
