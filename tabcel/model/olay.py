"""Değişiklik olayları (Qt'siz). Formül motoru, arayüz ve ileride kaydet/otomatik kaydet dinler.

Sayfa üzerindeki her yazım (`Sayfa.ata`, satır/sütun ekle-sil, boyut) ve kitaptaki sayfa işlemleri
(ekle/sil/yeniden adlandır/taşı) bir `Olay` yayar. Böylece geri al da, doğrudan yazım da, ileride
dosyadan yükleme de aynı yoldan görülür.

Türler ve `ayrinti` anahtarları:
- ``hucre``  : `degisiklikler` {(satır, sütun): (eski Hucre|None, yeni Hucre|None)} — yalnızca gerçekten
  değişen hücreler; toplu işlemler (geri al, yapıştır, silme) TEK olayla gelir
- ``sonuc``  : `degisiklikler` {(satır, sütun): değer} — formül sonuçları yazıldı (geri al yığınına
  girmez; motor toplu yazar: TEK olay). Tek hücrelik `sonuc_ata` ayrıca `anahtar`, `deger` verir
- ``yapi``   : `eksen` ('satir'|'sutun'), `nerede`, `fark` (+ekleme / −silme), `silinen` {anahtar: Hucre}
- ``boyut``  : sütun genişliği / satır yüksekliği / gizleme değişti
- ``sayfa``  : `islem` ('ekle'|'sil'|'ad'|'tasi'), `indeks`; 'ad' için `eski_ad`, 'tasi' için `eski_indeks`
  (bu tür olaylarda `sayfa` ilgili sayfadır; kitap düzeyinde olduğundan tüm dinleyicilere gider)
"""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class Olay:
    tur: str
    sayfa: Any                                   # Sayfa (döngüsel içe aktarma olmasın diye Any)
    ayrinti: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, anahtar: str):
        return self.ayrinti[anahtar]
