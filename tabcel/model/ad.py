"""Tanımlı ad (adlandırılmış aralık/sabit/formül) veri türü. Qt yok. Kurallar: faz5_tasarim.md §4.1.

Doğrulama (`ad_dogrula`), komutlar ve arayüz 5d'dedir; burada yalnız değişmez kayıt ve anahtar.
"""
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from .adres import MAX_COL, MAX_ROW, AdresHatasi, harften_sutun
from .harmanla import tr_kucuk

_HUCRE_BENZERI = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d+)$")
_RC_BENZERI = re.compile(r"^([Rr]\d*([Cc]\d*)?|[Cc]\d*)$")      # R, C, R5, C5, R1C1
_AD_BASI = re.compile(r"^[^\W\d]|^\\", re.UNICODE)               # harf, _ ya da ters eğik çizgi
_AD_GOVDE = re.compile(r"^[\w.\\]*$", re.UNICODE)                 # harf, rakam, _, ., ters eğik çizgi


class AdHatasi(ValueError):
    """Geçersiz tanımlı ad; iletisi kullanıcıya gösterilebilir."""


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


def ad_dogrula(ad: str) -> None:
    """Excel'in ad kuralları (faz5_tasarim.md §4.1); geçersizse `AdHatasi`. Kapsamda benzersizlik
    denetimi çağıranındır (`CalismaKitabi.adlar`)."""
    gecersiz = AdHatasi("Girdiğiniz ad geçerli değil.")
    if not ad or len(ad) > 255 or ad != ad.strip():
        raise gecersiz
    if not (_AD_BASI.match(ad) and _AD_GOVDE.match(ad)):
        raise gecersiz
    if ad.upper() in ("TRUE", "FALSE", "DOĞRU", "YANLIŞ", "DOGRU", "YANLIS") or tr_kucuk(ad) in ("doğru", "yanlış"):
        raise gecersiz
    if _RC_BENZERI.match(ad):
        raise gecersiz
    m = _HUCRE_BENZERI.match(ad)
    if m and 1 <= int(m.group(2)) <= MAX_ROW:
        try:
            harften_sutun(m.group(1).upper())
        except AdresHatasi:
            return                                  # sütun XFD'yi aşıyor: hücre başvurusu değil
        raise gecersiz


def ad_kontrol(kitap, tanim: "TanimliAd", eski_anahtar: Optional[Tuple[Optional[int], str]] = None) -> None:
    """Yeni/düzenlenen ad için: geçerli ad, var olan kapsam, geçerli başvurur (`=` ile başlar) ve
    kapsamda benzersizlik (`eski_anahtar` düzenlenen adın kendisidir). Geçersizse `AdHatasi`."""
    ad_dogrula(tanim.ad)
    if tanim.kapsam is not None and kitap.sayfa_kimlikle(tanim.kapsam) is None:
        raise AdHatasi("Ad kapsamı geçerli değil.")
    if not tanim.formul.startswith("=") or len(tanim.formul) < 2:
        raise AdHatasi("Başvurur alanı geçerli bir formül olmalı.")
    anahtar = tanim.anahtar()
    if anahtar in kitap.adlar and anahtar != eski_anahtar:
        raise AdHatasi("Bu ad zaten var. Başka bir ad girin.")
