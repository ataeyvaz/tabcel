"""Fonksiyon kaydı. Qt yok.

Yeni fonksiyon eklemek (Sonnet'e sözleşme, faz2_tasarim.md §7):

    @fonksiyon("SUM", en_az=1, en_cok=255)
    def _sum(baglam, *args): ...

- Ad kanonik İngilizcedir; Türkçe ad `formul/adlar.py`'ye (doğrulanarak) yazılır.
- `args`: değerlendirilmiş argümanlar — skaler (None/float/str/bool/Hata), `AralikDeger`, `Dizi`
  ya da atlanmış argüman için `BOS_ARG`.
- `tembel=True`: argümanlar değerlendirilmeden, sıfır argümanlı işlevler olarak gelir
  (`args[0]()` değerlendirir) — EĞER, EĞERHATA gibi yalnız seçilen dalı hesaplayanlar için.
- `degisken=True`: her yeniden hesaplamada hesaplanır (BUGÜN, ŞİMDİ, S_SAYI_ÜRET).
- `dinamik=True`: başvurusu çalışma anında belirlenir (DOLAYLI, KAYDIR) → değişken sayılır.
- `gizlilik=True`: sonuç satırların gizli olup olmamasına bağlı (ALTTOPLAM); motor bu hücreleri
  `boyut` olayında (gizle/göster/filtre) yeniden hesaplar.
- Dönüş: skaler, `AralikDeger` (başvuru döndürenler: İNDİS, KAYDIR, DOLAYLI) ya da `Dizi`.
- Her fonksiyon için en az 4 test vakası (CLAUDE.md kural 11).
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class Tanim:
    ad: str
    uygula: Callable
    en_az: int = 0
    en_cok: Optional[int] = None      # None = sınırsız (en çok 255)
    tembel: bool = False
    degisken: bool = False
    dinamik: bool = False
    gizlilik: bool = False            # satır gizliliğine bağlı (ALTTOPLAM): `boyut` olayında yeniden hesaplanır


KAYIT: Dict[str, Tanim] = {}


def fonksiyon(ad: str, en_az: int = 0, en_cok: Optional[int] = None, tembel: bool = False,
              degisken: bool = False, dinamik: bool = False, gizlilik: bool = False):
    def kaydet(f):
        KAYIT[ad.upper()] = Tanim(ad.upper(), f, en_az, en_cok, tembel, degisken, dinamik, gizlilik)
        return f
    return kaydet


def bul(ad: str) -> Optional[Tanim]:
    return KAYIT.get(ad.upper())


# Gruplar içe aktarılınca kayda girer
from . import temel  # noqa: E402,F401
from . import matematik, istatistik, mantik, bilgi, metin  # noqa: E402,F401
from . import tarih, arama, finans, turkiye  # noqa: E402,F401
from . import dizi  # noqa: E402,F401  (Faz 8e)
from . import matematik2, istatistik2, tarih2, bilgi2, finans2, metin2, dizi2, birim  # noqa: E402,F401  (işlev kitaplığı genişletmesi)
