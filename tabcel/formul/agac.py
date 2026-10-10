"""Ayrıştırıcı: sözcükler → sözdizim ağacı. Qt yok.

Öncelik (yüksekten alçağa, Excel): `:` aralık → boşluk (kesişim) → tekli `-`/`+` → `%` → `^`
→ `* /` → `+ -` → `&` → karşılaştırmalar. Tüm ikili işleçler soldan birleşir (`2^3^2` = 64).
Ağaç kanonik (İngilizce) sözcüklerden kurulur; çeviri `ceviri.py`'dedir.
"""
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Tuple

from ..model.deger import Hata
from .sozcuk import (
    AC, AD, AYRAC, BASVURU, BOSLUK, DIZI_AC, DIZI_KAPA, DIZI_SATIR, DIZI_SUTUN, FONK, HATA,
    ISLEC, KAPA, METIN, SAYI, Basvuru, FormulHatasi, Sozcuk, sozcukle,
)
from .kaydir import _SIL as KAYDIR_SIL, basvuru_kaydir
from .yerel import SAKLI, Yerel


# --- düğümler ---
class Dugum:
    __slots__ = ()


@dataclass(frozen=True)
class Sabit(Dugum):
    deger: Any                     # float | str | bool | Hata


@dataclass(frozen=True)
class Ref(Dugum):
    basvuru: Basvuru


@dataclass(frozen=True)
class Ad(Dugum):
    ad: str                        # tanımlı ad (Faz 5); şimdilik #NAME?


@dataclass(frozen=True)
class Tekli(Dugum):
    islec: str                     # '-' | '+'
    x: Dugum


@dataclass(frozen=True)
class Yuzde(Dugum):
    x: Dugum


@dataclass(frozen=True)
class Ikili(Dugum):
    islec: str                     # + - * / ^ & = <> < > <= >= : ' ' (kesişim)
    a: Dugum
    b: Dugum


@dataclass(frozen=True)
class Bos(Dugum):
    """Atlanmış argüman: EĞER(A1;;1)."""


@dataclass(frozen=True)
class Cagri(Dugum):
    ad: str                        # büyük harf kanonik ad
    argumanlar: Tuple[Dugum, ...]


@dataclass(frozen=True)
class DiziSabit(Dugum):
    satirlar: Tuple[Tuple[Any, ...], ...]


KESISIM = " "
_KARSILASTIRMA = ("=", "<>", "<", ">", "<=", ">=")
_DUZEYLER = (_KARSILASTIRMA, ("&",), ("+", "-"), ("*", "/"), ("^",))
_BITEN = (BASVURU, KAPA, AD)                 # bir işlenenin bitebileceği sözcükler
_BASLAYAN = (BASVURU, AC, FONK, AD)          # kesişimin sağ işleneni başlayabilir


def _kesisimleri_isle(sozcukler: List[Sozcuk]) -> List[Sozcuk]:
    """Boşlukları atar; iki başvuru-benzeri işlenen arasındaki boşluk kesişim işlecine dönüşür."""
    sonuc: List[Sozcuk] = []
    for i, s in enumerate(sozcukler):
        if s.tur != BOSLUK:
            sonuc.append(s)
            continue
        onceki = sonuc[-1] if sonuc else None
        sonraki = sozcukler[i + 1] if i + 1 < len(sozcukler) else None
        if (onceki is not None and sonraki is not None and onceki.tur in _BITEN
                and sonraki.tur in _BASLAYAN):
            sonuc.append(Sozcuk(ISLEC, s.metin, KESISIM, s.konum))
    return sonuc


class _Ayristirici:
    def __init__(self, sozcukler: List[Sozcuk]):
        self.s = _kesisimleri_isle(sozcukler)
        self.i = 0

    def bak(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def al(self) -> Sozcuk:
        s = self.bak()
        if s is None:
            raise FormulHatasi("Formül beklenmedik biçimde bitti")
        self.i += 1
        return s

    def islec_mi(self, *islecler) -> bool:
        s = self.bak()
        return s is not None and s.tur == ISLEC and s.deger in islecler

    def ayristir(self) -> Dugum:
        if not self.s:
            raise FormulHatasi("Boş formül")
        d = self.ifade()
        s = self.bak()
        if s is not None:
            raise FormulHatasi(f"Beklenmeyen: {s.metin!r}", s.konum)
        return d

    def ifade(self, duzey: int = 0) -> Dugum:
        if duzey == len(_DUZEYLER):
            return self.tekli()
        sol = self.ifade(duzey + 1)
        while self.islec_mi(*_DUZEYLER[duzey]):
            isl = self.al().deger
            sol = Ikili(isl, sol, self.ifade(duzey + 1))
        return sol

    def tekli(self) -> Dugum:
        if self.islec_mi("-", "+"):
            isl = self.al().deger
            return Tekli(isl, self.tekli())
        return self.yuzde()

    def yuzde(self) -> Dugum:
        d = self.kesisim()
        while self.islec_mi("%"):
            self.al()
            d = Yuzde(d)
        return d

    def kesisim(self) -> Dugum:
        d = self.aralik()
        while self.islec_mi(KESISIM):
            self.al()
            d = Ikili(KESISIM, d, self.aralik())
        return d

    def aralik(self) -> Dugum:
        d = self.birincil()
        while self.islec_mi(":"):
            self.al()
            d = Ikili(":", d, self.birincil())
        return d

    def birincil(self) -> Dugum:
        s = self.al()
        t = s.tur
        if t in (SAYI, METIN):
            return Sabit(s.deger)
        if t == HATA:
            return Sabit(Hata(s.deger))
        if t == BASVURU:
            return Ref(s.deger)
        if t == AD:
            ust = s.deger.upper()
            if ust in ("TRUE", "FALSE"):
                return Sabit(ust == "TRUE")
            return Ad(s.deger)
        if t == FONK:
            return self.cagri(s)
        if t == AC:
            d = self.ifade()
            self.bekle(KAPA, "')' eksik")
            return d
        if t == DIZI_AC:
            return self.dizi(s)
        raise FormulHatasi(f"Beklenmeyen: {s.metin!r}", s.konum)

    def bekle(self, tur: str, ileti: str) -> Sozcuk:
        s = self.bak()
        if s is None or s.tur != tur:
            raise FormulHatasi(ileti, s.konum if s else -1)
        return self.al()

    def cagri(self, ad: Sozcuk) -> Dugum:
        self.bekle(AC, "'(' eksik")
        args: List[Dugum] = []
        s = self.bak()
        if s is not None and s.tur == KAPA:
            self.al()
            return Cagri(ad.deger.upper(), ())
        while True:
            s = self.bak()
            if s is not None and s.tur in (AYRAC, KAPA):
                args.append(Bos())
            else:
                args.append(self.ifade())
            s = self.bak()
            if s is None:
                raise FormulHatasi("')' eksik")
            if s.tur == KAPA:
                self.al()
                break
            if s.tur != AYRAC:
                raise FormulHatasi(f"Beklenmeyen: {s.metin!r}", s.konum)
            self.al()
        if len(args) > 255:
            raise FormulHatasi("Bir fonksiyona en çok 255 argüman verilebilir", ad.konum)
        return Cagri(ad.deger.upper(), tuple(args))

    def dizi(self, ac: Sozcuk) -> Dugum:
        satirlar, satir = [], []
        while True:
            satir.append(self.dizi_ogesi())
            s = self.al()
            if s.tur == DIZI_SUTUN:
                continue
            if s.tur == DIZI_SATIR:
                satirlar.append(tuple(satir))
                satir = []
                continue
            if s.tur == DIZI_KAPA:
                satirlar.append(tuple(satir))
                break
            raise FormulHatasi(f"Dizi sabitinde beklenmeyen: {s.metin!r}", s.konum)
        if len({len(r) for r in satirlar}) != 1:
            raise FormulHatasi("Dizi sabitinin satırları eşit uzunlukta olmalı", ac.konum)
        return DiziSabit(tuple(satirlar))

    def dizi_ogesi(self):
        s = self.al()
        isaret = 1.0
        if s.tur == ISLEC and s.deger in ("-", "+"):
            isaret = -1.0 if s.deger == "-" else 1.0
            s = self.al()
            if s.tur != SAYI:
                raise FormulHatasi("Dizi sabitinde işaretten sonra sayı bekleniyordu", s.konum)
        if s.tur == SAYI:
            return isaret * s.deger
        if s.tur == METIN:
            return s.deger
        if s.tur == HATA:
            return Hata(s.deger)
        if s.tur == AD and s.deger.upper() in ("TRUE", "FALSE"):
            return s.deger.upper() == "TRUE"
        raise FormulHatasi("Dizi sabitinde yalnız sabit değerler olabilir", s.konum)


def ayristir(sozcukler: List[Sozcuk]) -> Dugum:
    return _Ayristirici(sozcukler).ayristir()


def formul_ayristir(formul: str, yerel: Yerel = SAKLI) -> Dugum:
    """'=' ile başlayan (ya da başlamayan) saklanan biçimdeki formülü ağaca çevirir."""
    govde = formul[1:] if formul.startswith("=") else formul
    return ayristir(sozcukle(govde, yerel))


# --- ağaç kaydırma (koşullu biçim / doğrulama / göreli ad: çapa hücreye göre yazılıp başka hücrede
# göreli kısımları kaydırılarak değerlendirilir; faz5_tasarim.md §1.5) ---
_KAYDIR_ONBELLEK: "OrderedDict[Tuple[int, int, int], Tuple[Dugum, Dugum]]" = OrderedDict()
_KAYDIR_ONBELLEK_BOYUT = 4096


def _kaydir_dugum(d: Dugum, dr: int, dc: int) -> Dugum:
    """Düğümü (dr, dc) kaydırır; değişmeyen alt ağaçlar paylaşılır (aynı nesne)."""
    if isinstance(d, Ref):
        yeni = basvuru_kaydir(d.basvuru, dr, dc)
        if yeni is KAYDIR_SIL:
            return Sabit(Hata("#REF!"))
        return d if yeni == d.basvuru else Ref(yeni)
    if isinstance(d, (Sabit, Ad, Bos, DiziSabit)):
        return d
    if isinstance(d, (Tekli, Yuzde)):
        x = _kaydir_dugum(d.x, dr, dc)
        return d if x is d.x else replace(d, x=x)
    if isinstance(d, Ikili):
        a, b = _kaydir_dugum(d.a, dr, dc), _kaydir_dugum(d.b, dr, dc)
        return d if (a is d.a and b is d.b) else Ikili(d.islec, a, b)
    if isinstance(d, Cagri):
        args = tuple(_kaydir_dugum(x, dr, dc) for x in d.argumanlar)
        return d if all(y is x for y, x in zip(args, d.argumanlar)) else Cagri(d.ad, args)
    return d


def agac_kaydir(agac: Dugum, dr: int, dc: int) -> Dugum:
    """`kaydir.kopyala` ile aynı sonucu metne dönmeden ağaç üzerinde verir: `$`'sız uçlar (dr, dc)
    kayar, sayfa dışına çıkan başvuru `Sabit(#REF!)` olur. Sonuç `(id(ağaç), dr, dc)` anahtarlı
    LRU önbellekte (4096); kaydırma yoksa aynı ağaç döner."""
    if dr == 0 and dc == 0:
        return agac
    anahtar = (id(agac), dr, dc)
    giris = _KAYDIR_ONBELLEK.get(anahtar)
    if giris is not None and giris[0] is agac:           # id yeniden kullanımına karşı kimlik denetimi
        _KAYDIR_ONBELLEK.move_to_end(anahtar)
        return giris[1]
    sonuc = _kaydir_dugum(agac, dr, dc)
    _KAYDIR_ONBELLEK[anahtar] = (agac, sonuc)
    if len(_KAYDIR_ONBELLEK) > _KAYDIR_ONBELLEK_BOYUT:
        _KAYDIR_ONBELLEK.popitem(last=False)
    return sonuc
