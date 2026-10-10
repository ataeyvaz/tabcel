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
- ``bicim``  : stil (biçim) kayıtları değişti: `degisiklikler` {(satır, sütun): (eski kimlik|None, yeni
  kimlik|None)}, `satir` {satır: (eski, yeni)}, `sutun` {sütun: (eski, yeni)} — yalnız gerçekten değişenler;
  toplu işlem TEK olay; birleşim değişince ayrıca `birlesim` (eklenen, kaldırılan) aralık listeleri; dondurma/kılavuz değişince `gorunum` {'dondur': (satır, sütun)|None, 'kilavuz': bool} (yalnız değişenler; geri al yığınına girmez). Kimlikler `Sayfa.havuz`daki stillerin numaralarıdır (None = kayıt yok). Formül
  motoru yok sayar; ızgara ilgili satırları yeniden çizer
- ``boyut``  : sütun genişliği / satır yüksekliği / gizleme değişti
- ``ek``     : sayfaya bağlı ek veriler değişti (Faz 5): `alan` ('not'|'dogrulama'|'kosullu'|'filtre'|
  'hepsi' — geri al/yinele anlık görüntüyü yüklediğinde), isteğe bağlı `anahtarlar` (değişen hücreler;
  'not' için). Formül motoru yok sayar; ızgara 'not' için ilgili hücreleri, diğerleri için tam yeniden çizer
- ``ad``     : kitap düzeyi tanımlı ad değişti. `sayfa` None'dır (ad kitaba aittir); `eski`, `yeni`
  (`TanimliAd` | None). Dinleyiciler `olay.sayfa`ya erişmeden önce None denetlemelidir
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
