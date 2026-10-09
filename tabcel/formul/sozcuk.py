"""Formül sözcükleyici: metin → `Sozcuk` listesi. Qt yok.

Boşluklar da sözcük olarak tutulur; böylece `metne(sozcukler)` özgün metni birebir geri verir.
Çeviri (TR ⇄ kanonik) ve başvuru kaydırma sözcük düzeyinde çalışır: kullanıcının yazımı korunur.

Formül metni baştaki '=' OLMADAN verilir.
"""
import re
from dataclasses import dataclass, replace
from typing import Any, List, Optional, Union

from ..model.adres import MAX_COL, MAX_ROW, harften_sutun, sutun_harfe
from .yerel import Yerel


class FormulHatasi(ValueError):
    """Sözdizimi hatası. `konum`: metindeki karakter indeksi (bilinmiyorsa -1)."""

    def __init__(self, ileti: str, konum: int = -1):
        super().__init__(ileti)
        self.konum = konum


# Sözcük türleri
SAYI, METIN, HATA, BASVURU, AD, FONK = "sayi", "metin", "hata", "basvuru", "ad", "fonk"
ISLEC, AYRAC, AC, KAPA = "islec", "ayrac", "ac", "kapa"
DIZI_AC, DIZI_KAPA, DIZI_SUTUN, DIZI_SATIR, BOSLUK = (
    "dizi_ac", "dizi_kapa", "dizi_sutun", "dizi_satir", "bosluk")


@dataclass(frozen=True)
class Basvuru:
    """Hücre/aralık başvurusu. Satır/sütun 1 tabanlı; aralık normalize (r1<=r2, c1<=c2).

    `sayfa`: None = formülün kendi sayfası; str = yazıldığı gibi sayfa adı (henüz bağlanmamış);
    int = sayfa kimliği (saklanan biçim).
    `tur`: 'hucre' | 'aralik' | 'sutun' (A:C) | 'satir' (2:5).
    """
    tur: str
    r1: int
    c1: int
    r2: int
    c2: int
    r1m: bool = False   # $ (mutlak) bayrakları
    c1m: bool = False
    r2m: bool = False
    c2m: bool = False
    sayfa: Union[None, str, int] = None

    def govde(self) -> str:
        """Sayfa öneki olmadan metin: A1, $A$1:B2, A:C, $2:5."""
        def hucre(r, c, rm, cm):
            return ("$" if cm else "") + sutun_harfe(c) + ("$" if rm else "") + str(r)
        if self.tur == "hucre":
            return hucre(self.r1, self.c1, self.r1m, self.c1m)
        if self.tur == "sutun":
            return (("$" if self.c1m else "") + sutun_harfe(self.c1) + ":"
                    + ("$" if self.c2m else "") + sutun_harfe(self.c2))
        if self.tur == "satir":
            return (("$" if self.r1m else "") + str(self.r1) + ":"
                    + ("$" if self.r2m else "") + str(self.r2))
        return (hucre(self.r1, self.c1, self.r1m, self.c1m) + ":"
                + hucre(self.r2, self.c2, self.r2m, self.c2m))

    def tek_hucre(self) -> bool:
        return self.r1 == self.r2 and self.c1 == self.c2


@dataclass(frozen=True)
class Sozcuk:
    tur: str
    metin: str            # yazıldığı gibi (başvuruda sayfa öneki dahil)
    deger: Any = None     # sayi: float · metin: str · hata: kanonik kod · basvuru: Basvuru · ad/fonk: ad
    konum: int = 0        # özgün metindeki başlangıç

    def yeni(self, **degisen) -> "Sozcuk":
        return replace(self, **degisen)


def metne(sozcukler: List[Sozcuk]) -> str:
    return "".join(s.metin for s in sozcukler)


# --- sayfa öneki ---
_AD_KARAKTER = re.compile(r"[\w.]", re.UNICODE)
_DUZ_SAYFA = re.compile(r"[^\W\d][\w.]*", re.UNICODE)
_HUCRE_GIBI = re.compile(r"[A-Za-z]{1,3}\d+|[Rr]\d*[Cc]\d*", re.UNICODE)


def sayfa_oneki(ad: str) -> str:
    """Sayfa adını başvuru önekine çevirir: Sayfa2 → 'Sayfa2!', Gelir Gider → "'Gelir Gider'!"."""
    if _DUZ_SAYFA.fullmatch(ad) and not _HUCRE_GIBI.fullmatch(ad):
        return ad + "!"
    return "'" + ad.replace("'", "''") + "'!"


# --- başvuru kalıpları ---
_H = r"(\$?)([A-Za-z]{1,3})(\$?)(\d{1,7})"
_C = r"(\$?)([A-Za-z]{1,3})"
_R = r"(\$?)(\d{1,7})"
_ARALIK_RE = re.compile(_H + ":" + _H)
_SUTUN_RE = re.compile(_C + ":" + _C)
_SATIR_RE = re.compile(_R + ":" + _R)
_HUCRE_RE = re.compile(_H)


def _sinir_mi(metin: str, i: int) -> bool:
    """i konumu bir başvurunun bitebileceği yer mi (ad karakteri, '(' ya da '!' gelmiyor)?"""
    if i >= len(metin):
        return True
    ch = metin[i]
    return not (_AD_KARAKTER.match(ch) or ch in "(!$")


def _sutun(harf: str) -> Optional[int]:
    try:
        return harften_sutun(harf)
    except ValueError:
        return None


def _satir(rakam: str) -> Optional[int]:
    n = int(rakam)
    return n if 1 <= n <= MAX_ROW else None


def basvuru_oku(metin: str, i: int) -> Optional[tuple]:
    """i konumunda (sayfa öneki sonrası) başvuru varsa (Basvuru, bitiş) döner."""
    m = _ARALIK_RE.match(metin, i)
    if m and _sinir_mi(metin, m.end()):
        c1m, ch1, r1m, rr1, c2m, ch2, r2m, rr2 = m.groups()
        c1, c2, r1, r2 = _sutun(ch1), _sutun(ch2), _satir(rr1), _satir(rr2)
        if None not in (c1, c2, r1, r2):
            a = (r1, bool(r1m)), (r2, bool(r2m))
            b = (c1, bool(c1m)), (c2, bool(c2m))
            (r1, r1m), (r2, r2m) = sorted(a, key=lambda t: t[0])
            (c1, c1m), (c2, c2m) = sorted(b, key=lambda t: t[0])
            return Basvuru("aralik", r1, c1, r2, c2, r1m, c1m, r2m, c2m), m.end()
    m = _SUTUN_RE.match(metin, i)
    if m and _sinir_mi(metin, m.end()):
        c1m, ch1, c2m, ch2 = m.groups()
        c1, c2 = _sutun(ch1), _sutun(ch2)
        if None not in (c1, c2):
            (c1, c1m), (c2, c2m) = sorted(((c1, bool(c1m)), (c2, bool(c2m))), key=lambda t: t[0])
            return Basvuru("sutun", 1, c1, MAX_ROW, c2, False, c1m, False, c2m), m.end()
    m = _SATIR_RE.match(metin, i)
    if m and _sinir_mi(metin, m.end()):
        r1m, rr1, r2m, rr2 = m.groups()
        r1, r2 = _satir(rr1), _satir(rr2)
        if None not in (r1, r2):
            (r1, r1m), (r2, r2m) = sorted(((r1, bool(r1m)), (r2, bool(r2m))), key=lambda t: t[0])
            return Basvuru("satir", r1, 1, r2, MAX_COL, r1m, False, r2m, False), m.end()
    m = _HUCRE_RE.match(metin, i)
    if m and _sinir_mi(metin, m.end()):
        cm, ch, rm, rr = m.groups()
        c, r = _sutun(ch), _satir(rr)
        if c is not None and r is not None:
            return Basvuru("hucre", r, c, r, c, bool(rm), bool(cm), bool(rm), bool(cm)), m.end()
    return None


def _sayfa_oneki_oku(metin: str, i: int, yerel: Yerel) -> Optional[tuple]:
    """i konumunda sayfa öneki ('Ad'!, Ad!, [3]!) varsa (sayfa, bitiş) döner; bitiş '!' sonrasıdır."""
    n = len(metin)
    if metin[i] == "'":
        j, parca = i + 1, []
        while j < n:
            if metin[j] == "'":
                if j + 1 < n and metin[j + 1] == "'":
                    parca.append("'")
                    j += 2
                    continue
                break
            parca.append(metin[j])
            j += 1
        if j < n and j + 1 < n and metin[j + 1] == "!":
            return "".join(parca), j + 2
        return None
    if metin[i] == "[" and yerel.kimlik_izinli:
        m = _KIMLIK_RE.match(metin, i)
        if m:
            return int(m.group(1)), m.end()
        return None
    m = _DUZ_ONEK_RE.match(metin, i)
    if m:
        return m.group(0)[:-1], m.end()
    return None


_KIMLIK_RE = re.compile(r"\[(\d+)\]!")
_DUZ_ONEK_RE = re.compile(r"[\w.]+!", re.UNICODE)
_YEREL_ONB: dict = {}


def _yerel_hazirla(yerel: Yerel):
    """Yerele bağlı, her formülde yeniden kurulması pahalı parçalar (önbellekli)."""
    h = _YEREL_ONB.get(id(yerel))
    if h is None or h[0] is not yerel:
        hata_adlari = sorted(yerel.hata_kanonik().items(), key=lambda t: -len(t[0]))
        sayi_re = re.compile(
            r"(?:\d+(?:{d}\d*)?|{d}\d+)(?:[eE][+-]?\d+)?".format(d=re.escape(yerel.ondalik)))
        h = _YEREL_ONB[id(yerel)] = (yerel, hata_adlari, sayi_re)
    return h[1], h[2]


_ISLECLER = ("<>", "<=", ">=", "<", ">", "=", "+", "-", "*", "/", "^", "&", "%", ":")


def sozcukle(metin: str, yerel: Yerel) -> List[Sozcuk]:
    """Formül metnini (baştaki '=' olmadan) sözcüklere ayırır. Hatalıysa `FormulHatasi`."""
    sonuc: List[Sozcuk] = []
    n = len(metin)
    i = 0
    dizi_ici = False
    hata_adlari, sayi_re = _yerel_hazirla(yerel)

    def ekle(tur, bas, son, deger=None):
        sonuc.append(Sozcuk(tur, metin[bas:son], deger, bas))

    while i < n:
        ch = metin[i]
        if ch.isspace():
            j = i
            while j < n and metin[j].isspace():
                j += 1
            ekle(BOSLUK, i, j)
            i = j
            continue
        if ch == '"':
            j, parca = i + 1, []
            while True:
                if j >= n:
                    raise FormulHatasi("Kapanmamış tırnak", i)
                if metin[j] == '"':
                    if j + 1 < n and metin[j + 1] == '"':
                        parca.append('"')
                        j += 2
                        continue
                    break
                parca.append(metin[j])
                j += 1
            ekle(METIN, i, j + 1, "".join(parca))
            i = j + 1
            continue
        if ch == "#":
            ust = metin[i:].upper()
            for yazim, kod in hata_adlari:
                if ust.startswith(yazim):
                    ekle(HATA, i, i + len(yazim), kod)
                    i += len(yazim)
                    break
            else:
                raise FormulHatasi("Bilinmeyen hata değeri", i)
            continue
        if dizi_ici:
            if ch == yerel.dizi_sutun:
                ekle(DIZI_SUTUN, i, i + 1)
                i += 1
                continue
            if ch == yerel.dizi_satir:
                ekle(DIZI_SATIR, i, i + 1)
                i += 1
                continue
            if ch == "}":
                ekle(DIZI_KAPA, i, i + 1)
                dizi_ici = False
                i += 1
                continue
        if ch == "{":
            if dizi_ici:
                raise FormulHatasi("İç içe dizi sabiti", i)
            ekle(DIZI_AC, i, i + 1)
            dizi_ici = True
            i += 1
            continue
        if ch == "}":
            raise FormulHatasi("Fazladan '}'", i)
        if ch == yerel.arguman:
            ekle(AYRAC, i, i + 1)
            i += 1
            continue
        if ch == "(":
            ekle(AC, i, i + 1)
            i += 1
            continue
        if ch == ")":
            ekle(KAPA, i, i + 1)
            i += 1
            continue
        # sayfa önekli başvuru
        if ch in "'[" or _AD_KARAKTER.match(ch):
            onek = _sayfa_oneki_oku(metin, i, yerel)
            if onek is not None:
                sayfa, j = onek
                if metin[j:j + 5].upper() == "#REF!" or (
                        "#REF!" in yerel.hatalar and
                        metin[j:].upper().startswith(yerel.hatalar["#REF!"].upper())):
                    yazim = "#REF!" if metin[j:j + 5].upper() == "#REF!" else yerel.hatalar["#REF!"]
                    ekle(HATA, i, j + len(yazim), "#REF!")
                    i = j + len(yazim)
                    continue
                b = basvuru_oku(metin, j)
                if b is None:
                    raise FormulHatasi("Sayfa adından sonra başvuru bekleniyordu", j)
                bas, son = b
                ekle(BASVURU, i, son, replace(bas, sayfa=sayfa))
                i = son
                continue
            if ch == "'":
                raise FormulHatasi("Geçersiz sayfa adı", i)
        if ch == "$" or ch.isascii() and ch.isalnum():
            b = basvuru_oku(metin, i)
            if b is not None:
                ekle(BASVURU, i, b[1], b[0])
                i = b[1]
                continue
        if ch.isdigit() or (ch == yerel.ondalik and i + 1 < n and metin[i + 1].isdigit()):
            m = sayi_re.match(metin, i)
            if m:
                yazim = m.group(0)
                ekle(SAYI, i, m.end(), float(yazim.replace(yerel.ondalik, ".")))
                i = m.end()
                continue
        if ch == "_" or ch == "\\" or ch.isalpha():
            j = i + 1
            while j < n and _AD_KARAKTER.match(metin[j]):
                j += 1
            ad = metin[i:j]
            ekle(FONK if j < n and metin[j] == "(" else AD, i, j, ad)
            i = j
            continue
        for isl in _ISLECLER:
            if metin.startswith(isl, i):
                ekle(ISLEC, i, i + len(isl), isl)
                i += len(isl)
                break
        else:
            raise FormulHatasi(f"Beklenmeyen karakter: {ch!r}", i)
    if dizi_ici:
        raise FormulHatasi("Kapanmamış dizi sabiti '{'", n)
    return sonuc
