"""Hücre değer türleri. Qt yok.

Bir hücrenin **girdisi** (kullanıcının yazdığı sabit değer ya da formül metni) `Hucre`'de durur;
formülün **hesaplanmış sonucu** `Sayfa`'da ayrı bir depoda tutulur (bkz. `Sayfa.sonuc_ata`).
Sonuç şunlardan biri olabilir: None (boş), metin, sayı (float), mantıksal (bool) ya da `Hata`.
"""
from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class Hata:
    """Excel hata değeri. `kod` kanonik (.xlsx'teki) İngilizce biçimdir; ekranda Türkçesi gösterilir."""
    kod: str

    def __str__(self) -> str:
        return self.kod


# Kanonik kodlar (.xlsx dosyasındaki yazım). Türkçe karşılıklar `gosterim.py` içindedir ve
# Microsoft'un resmî listesiyle henüz doğrulanmadı (surec.md §8b-5).
BOL0 = Hata("#DIV/0!")
YOK = Hata("#N/A")
AD = Hata("#NAME?")
BOS = Hata("#NULL!")
SAYI = Hata("#NUM!")
BASV = Hata("#REF!")
DEGER_HATASI = Hata("#VALUE!")
TASMA = Hata("#SPILL!")          # dinamik dizi hedefe sığmıyor / hedef dolu (Excel: #TAŞMA!)
HESAPLA = Hata("#CALC!")         # boş dizi sonucu (Excel: #HESAPLA!)

HATALAR = {h.kod: h for h in (BOL0, YOK, AD, BOS, SAYI, BASV, DEGER_HATASI, TASMA, HESAPLA)}


def hata_bul(kod: str) -> Optional[Hata]:
    """Kanonik kodtan hata değeri (bilinmiyorsa None)."""
    return HATALAR.get(kod.strip().upper())


Deger = Union[None, str, float, bool, Hata]
