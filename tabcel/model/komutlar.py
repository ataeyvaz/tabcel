"""Geri al / yinele (komut deseni). Qt yok.

Aralık işlemleri tek adımdır: tek komut ya da `Grup`.
"""
from typing import Dict, List, Optional, Protocol

from .sayfa import Anahtar, Hucre, Sayfa


class Komut(Protocol):
    def yap(self) -> None: ...
    def geri_al(self) -> None: ...


class HucrelerDegis:
    """Birden çok hücreyi tek adımda değiştirir. `yeni`: {(satır, sütun): Hucre | None}."""

    def __init__(self, sayfa: Sayfa, yeni: Dict[Anahtar, Optional[Hucre]]):
        self.sayfa = sayfa
        self.yeni = dict(yeni)
        self.eski: Dict[Anahtar, Optional[Hucre]] = {}

    def yap(self) -> None:
        self.eski = {}
        for (s, c), h in self.yeni.items():
            self.eski[(s, c)] = self.sayfa.ata(s, c, h)

    def geri_al(self) -> None:
        for (s, c), h in self.eski.items():
            self.sayfa.ata(s, c, h)


class _SatirSutun:
    eksen = 0

    def __init__(self, sayfa: Sayfa, nerede: int, adet: int, ekle: bool):
        self.sayfa, self.nerede, self.adet, self.ekle = sayfa, nerede, adet, ekle
        self._silinen: Dict[Anahtar, Hucre] = {}
        self._olcu_once = None

    def _ekle(self) -> None:
        (self.sayfa.sutun_ekle if self.eksen else self.sayfa.satir_ekle)(self.nerede, self.adet)

    def _sil(self) -> Dict[Anahtar, Hucre]:
        return (self.sayfa.sutun_sil if self.eksen else self.sayfa.satir_sil)(
            self.nerede, self.adet)

    def yap(self) -> None:
        self._olcu_once = self.sayfa.boyut_durumu()
        if self.ekle:
            self._ekle()
        else:
            self._silinen = self._sil()

    def geri_al(self) -> None:
        if self.ekle:
            self._sil()
        else:
            self._ekle()
            for (s, c), h in self._silinen.items():
                self.sayfa.ata(s, c, h)
        self.sayfa.boyut_durumu_yukle(self._olcu_once)


class SatirEkleSil(_SatirSutun):
    eksen = 0


class SutunEkleSil(_SatirSutun):
    eksen = 1


class OlcuDegis:
    """Sütun genişliği / satır yüksekliği / gizleme değişikliği (tek adım).

    İki kullanım: `uygula(sayfa)` işlevi verilir (yap() çağırır), ya da değişiklik zaten
    uygulanmışsa (fare sürüklemesi) `eski` ve `yeni` durumlar verilir.
    """

    def __init__(self, sayfa: Sayfa, uygula=None, eski=None, yeni=None):
        self.sayfa, self.uygula, self.eski, self.yeni = sayfa, uygula, eski, yeni

    def yap(self) -> None:
        if self.yeni is not None:
            self.sayfa.boyut_durumu_yukle(self.yeni)
            return
        self.eski = self.sayfa.boyut_durumu()
        self.uygula(self.sayfa)
        self.yeni = self.sayfa.boyut_durumu()

    def geri_al(self) -> None:
        self.sayfa.boyut_durumu_yukle(self.eski)


class Grup:
    """Birden çok komutu geri al yığınında tek adım yapar."""

    def __init__(self, komutlar: List[Komut]):
        self.komutlar = list(komutlar)

    def yap(self) -> None:
        for k in self.komutlar:
            k.yap()

    def geri_al(self) -> None:
        for k in reversed(self.komutlar):
            k.geri_al()


class GeriAlYigini:
    def __init__(self, sinir: int = 100):
        self.sinir = sinir
        self._geri: List[Komut] = []
        self._ileri: List[Komut] = []

    def calistir(self, komut: Komut) -> None:
        komut.yap()
        self._geri.append(komut)
        if len(self._geri) > self.sinir:
            del self._geri[0]
        self._ileri.clear()

    def geri_alinabilir(self) -> bool:
        return bool(self._geri)

    def yinelenebilir(self) -> bool:
        return bool(self._ileri)

    def geri_al(self) -> bool:
        if not self._geri:
            return False
        k = self._geri.pop()
        k.geri_al()
        self._ileri.append(k)
        return True

    def yinele(self) -> bool:
        if not self._ileri:
            return False
        k = self._ileri.pop()
        k.yap()
        self._geri.append(k)
        return True

    def temizle(self) -> None:
        self._geri.clear()
        self._ileri.clear()
