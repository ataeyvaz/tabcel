"""Yerel ayar: formül metnindeki ayırıcılar ve sabit adları. Qt yok.

`EN` kanonik biçimdir (.xlsx ve `Hucre.formul`); `TR` kullanıcının gördüğü/yazdığı biçim.
Türkçe değerlerden doğrulanmamış olanlar surec.md §8b'de "belirsiz" listesindedir:
- dizi ayırıcıları `\\` (sütun) ve `;` (satır): Microsoft topluluk forumu + tr-tr "dizi sabitleri"
  belgesine göre; Excel web'de doğrulanacak (§8b-4)
- hata adları (§8b-5)
"""
from dataclasses import dataclass, field
from typing import Dict

from ..model.gosterim import HATA_TR


@dataclass(frozen=True)
class Yerel:
    arguman: str                 # fonksiyon argüman ayırıcısı
    ondalik: str                 # ondalık ayırıcı
    dizi_sutun: str              # dizi sabitinde aynı satırdaki öğeler arası
    dizi_satir: str              # dizi sabitinde satırlar arası
    dogru: str
    yanlis: str
    hatalar: Dict[str, str] = field(default_factory=dict)   # kanonik kod → bu yereldeki yazım
    kimlik_izinli: bool = False  # `[3]!A1` sayfa kimliği yazımı (yalnız saklanan biçimde)

    def hata_kanonik(self) -> Dict[str, str]:
        """Bu yereldeki yazım (büyük harf) → kanonik kod."""
        return {v.upper(): k for k, v in self.hatalar.items()}


_KANONIK_HATALAR = ("#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A",
                    "#GETTING_DATA", "#SPILL!", "#CALC!")

EN = Yerel(",", ".", ",", ";", "TRUE", "FALSE",
           {k: k for k in _KANONIK_HATALAR}, kimlik_izinli=False)

# Saklanan biçim: EN + sayfa kimliği
SAKLI = Yerel(",", ".", ",", ";", "TRUE", "FALSE",
              {k: k for k in _KANONIK_HATALAR}, kimlik_izinli=True)

# Hata adlarının tek kaynağı `model.gosterim.HATA_TR` (doğrulanmadı, §8b-5); listede olmayanlar
# (yeni sürüm hataları) kanonik yazımıyla kalır.
TR = Yerel(";", ",", "\\", ";", "DOĞRU", "YANLIŞ",
           {k: HATA_TR.get(k, k) for k in _KANONIK_HATALAR})


def tr_buyuk(metin: str) -> str:
    """Türkçe büyük harf: i → İ, ı → I."""
    return metin.replace("i", "İ").replace("ı", "I").upper()


def tr_kucuk(metin: str) -> str:
    return metin.replace("I", "ı").replace("İ", "i").lower()
