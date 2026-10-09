"""Geri al / yinele (komut deseni). Qt yok.

Aralık işlemleri tek adımdır: tek komut ya da `Grup`.
"""
from typing import Dict, List, Optional, Protocol

from .adres import Aralik
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
        self.eski = self.sayfa.toplu_yaz(self.yeni)

    def geri_al(self) -> None:
        self.sayfa.toplu_yaz(self.eski)


class _SatirSutun:
    """Satır/sütun ekle-sil + kitaptaki formül başvurularının düzeltilmesi (tek geri al adımı).

    yap: kaydır → formül metinlerini yeniden yaz (eskileri sakla).
    geri_al: önce formül metinlerini geri yükle → sonra kaydırmayı geri al.
    """
    eksen = 0

    def __init__(self, sayfa: Sayfa, nerede: int, adet: int, ekle: bool):
        self.sayfa, self.nerede, self.adet, self.ekle = sayfa, nerede, adet, ekle
        self._silinen: Dict[Anahtar, Hucre] = {}
        self._olcu_once = None
        self._duzeltmeler = {}           # {Sayfa: {anahtar: (eski formül, yeni formül)}}

    def _formulleri_duzelt(self) -> None:
        from ..formul.kaydir import yapi_duzeltmeleri    # model → formul yalnız burada
        self._duzeltmeler = yapi_duzeltmeleri(
            self.sayfa.kitap, self.sayfa, "sutun" if self.eksen else "satir", self.nerede,
            self.adet if self.ekle else -self.adet)
        for s, degisen in self._duzeltmeler.items():
            s.toplu_yaz({k: Hucre(None, yeni) for k, (_, yeni) in degisen.items()})

    def _formulleri_geri_yukle(self) -> None:
        for s, degisen in self._duzeltmeler.items():
            s.toplu_yaz({k: Hucre(None, eski) for k, (eski, _) in degisen.items()})

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
        self._formulleri_duzelt()

    def geri_al(self) -> None:
        self._formulleri_geri_yukle()
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


class HucreTasi:
    """Kes-yapıştır = taşıma (tek geri al adımı). `kaynak` sayfadaki `kutu` (r1, c1, r2, c2)
    `hedef` sayfada sol üst köşesi `hedef_konum` olacak biçimde taşınır. Kitaptaki tüm formüllerin
    taşınan bölgeye işaret eden başvuruları yeni yere kayar (`formul.kaydir.tasi`); taşınan
    formüllerin kendi başvuruları kaymaz."""

    def __init__(self, kaynak: Sayfa, kutu, hedef: Sayfa, hedef_konum: Anahtar):
        self.kaynak, self.kutu, self.hedef, self.hedef_konum = kaynak, tuple(kutu), hedef, hedef_konum
        self._eski: List = []            # [(Sayfa, {anahtar: eski Hucre})] uygulama sırasıyla

    def _plan(self) -> Dict[Sayfa, Dict[Anahtar, Optional[Hucre]]]:
        from ..formul.kaydir import tasi                  # model → formul yalnız burada
        r1, c1, r2, c2 = self.kutu
        dr, dc = self.hedef_konum[0] - r1, self.hedef_konum[1] - c1
        ki, hi = self.kaynak.kimlik, self.hedef.kimlik
        kitap = self.kaynak.kitap
        sayfalar = kitap.sayfalar if kitap is not None else list({self.kaynak, self.hedef})

        def hedefte(s, r, c):
            return s is self.hedef and r1 + dr <= r <= r2 + dr and c1 + dc <= c <= c2 + dc

        plan: Dict[Sayfa, Dict[Anahtar, Optional[Hucre]]] = {s: {} for s in sayfalar}
        # 1) taşınan hücreler: kaynak boşalır, hedefe (formülü düzeltilmiş) yazılır
        tasinan = list(self.kaynak.aralikta(Aralik(r1, c1, r2, c2)))
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                plan[self.kaynak][(r, c)] = None
        for r in range(r1 + dr, r2 + dr + 1):
            for c in range(c1 + dc, c2 + dc + 1):
                plan[self.hedef][(r, c)] = None
        for r, c, h in tasinan:
            if h.formul is not None:
                yeni = tasi(h.formul, ki, hi, ki, self.kutu, hi, dr, dc)
                if yeni is not None:
                    h = Hucre(None, yeni)
            plan[self.hedef][(r + dr, c + dc)] = h
        # 2) diğer formüller: taşınan bölgeye işaret edenler kayar
        for s in sayfalar:
            for r, c, h in s.dolu_hucreler(sirali=False):
                if h.formul is None:
                    continue
                if s is self.kaynak and r1 <= r <= r2 and c1 <= c <= c2:
                    continue                              # taşınan formül (yukarıda)
                if hedefte(s, r, c):
                    continue                              # üzerine yazılıyor
                yeni = tasi(h.formul, s.kimlik, s.kimlik, ki, self.kutu, hi, dr, dc)
                if yeni is not None:
                    plan[s][(r, c)] = Hucre(None, yeni)
        return {s: d for s, d in plan.items() if d}

    def yap(self) -> None:
        self._eski = [(s, s.toplu_yaz(yeni)) for s, yeni in self._plan().items()]

    def geri_al(self) -> None:
        for s, eski in reversed(self._eski):
            s.toplu_yaz(eski)


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
        self.sayfa.boyut_degisti()

    def geri_al(self) -> None:
        self.sayfa.boyut_durumu_yukle(self.eski)


class SayfaEkle:
    """Kitabın sonuna yeni sayfa ekler. Geri alınca sayfa (verisiyle) kitaptan çıkar; yinelenince
    aynı nesne/kimlikle geri gelir."""

    def __init__(self, kitap, ad=None):
        self.kitap, self.ad = kitap, ad
        self.sayfa = None
        self.indeks = None

    def yap(self) -> None:
        if self.sayfa is None:
            self.sayfa = self.kitap.sayfa_ekle(self.ad)
        else:
            self.kitap.sayfa_geri_koy(self.sayfa, self.indeks)

    def geri_al(self) -> None:
        self.indeks = self.kitap.sayfa_sil(self.sayfa)


class SayfaSil:
    """Sayfayı kitaptan çıkarır; nesnesi ve verisi komutta saklanır, geri alınca aynı yere döner."""

    def __init__(self, kitap, sayfa):
        self.kitap, self.sayfa = kitap, sayfa
        self.indeks = None

    def yap(self) -> None:
        self.indeks = self.kitap.sayfa_sil(self.sayfa)

    def geri_al(self) -> None:
        self.kitap.sayfa_geri_koy(self.sayfa, self.indeks)


class SayfaYenidenAdlandir:
    def __init__(self, kitap, sayfa, ad: str):
        self.kitap, self.sayfa, self.ad = kitap, sayfa, ad
        self.eski_ad = None

    def yap(self) -> None:
        self.eski_ad = self.sayfa.ad
        self.kitap.yeniden_adlandir(self.sayfa, self.ad)

    def geri_al(self) -> None:
        self.kitap.yeniden_adlandir(self.sayfa, self.eski_ad)


class SayfaTasi:
    def __init__(self, kitap, sayfa, yeni_indeks: int):
        self.kitap, self.sayfa, self.yeni_indeks = kitap, sayfa, yeni_indeks
        self.eski_indeks = None

    def yap(self) -> None:
        self.eski_indeks = self.kitap.sayfalar.index(self.sayfa)
        self.kitap.sayfa_tasi(self.sayfa, self.yeni_indeks)

    def geri_al(self) -> None:
        self.kitap.sayfa_tasi(self.sayfa, self.eski_indeks)


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
