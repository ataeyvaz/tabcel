"""Otomatik filtre (faz5_tasarim.md §6). Qt yok.

Filtre sayfa başına bir tane; `aralik` başlık satırı dahil. Gizleme tek bittir (`Sayfa.gizli_satir`):
`gizlenecekler` hangi veri satırlarının koşulları sağlamadığını söyler, `komutlar.FiltreDegis` uygular.
Değer koşulları görünen metne (sayı biçimi uygulanmış) göre, Türkçe büyük/küçük harf duyarsız çalışır.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from .adres import Aralik
from .bul import gorunen_metin, joker_alt_dize
from .harmanla import metin_anahtari, tr_kucuk
from .sayfa import Sayfa

ISLECLER = ("esit", "esit_degil", "buyuk", "buyuk_esit", "kucuk", "kucuk_esit",
            "baslar", "baslamaz", "biter", "bitmez", "icerir", "icermez")
LISTE_SINIRI = 10_000          # açılır listede en çok benzersiz değer (Excel)


@dataclass(frozen=True)
class DegerKosulu:
    """Listeden işaretlenen görünen metinler (`bos`: "(Boş)" işaretli)."""
    metinler: frozenset
    bos: bool = False


@dataclass(frozen=True)
class OzelKosul:
    """`k1`/`k2` = `(işleç, değer)`; değer sayı (float) ya da metin. `ve`: iki koşul birlikte mi."""
    k1: Tuple[str, object]
    k2: Optional[Tuple[str, object]] = None
    ve: bool = True


@dataclass(frozen=True)
class IlkKosul:
    """İlk/Son `n` öğe (ya da yüzde); eşit değerler birlikte alınır (Excel)."""
    n: int = 10
    alt: bool = False
    yuzde: bool = False


@dataclass(frozen=True)
class OrtalamaKosulu:
    ustu: bool = True


@dataclass(frozen=True)
class RenkKosulu:
    """`tur`: "dolgu" | "yazi"; `renk` '#rrggbb' (None = renksiz/varsayılan)."""
    tur: str
    renk: Optional[str] = None


@dataclass(frozen=True)
class Filtre:
    aralik: Aralik
    kosullar: Dict[int, object] = field(default_factory=dict)     # mutlak sütun → koşul

    def kosullu_mu(self) -> bool:
        return bool(self.kosullar)


MetinAl = Callable[[Sayfa, int, int], Optional[str]]


def _sayi(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _metin_islec(islec: str, desen: str):
    tam = islec in ("esit", "esit_degil")
    if islec in ("esit", "esit_degil"):
        f = joker_alt_dize(desen, tam=True)
    elif islec in ("baslar", "baslamaz"):
        f = joker_alt_dize(desen + "*", tam=True)
    elif islec in ("biter", "bitmez"):
        f = joker_alt_dize("*" + desen, tam=True)
    else:
        f = joker_alt_dize(desen)
    olumsuz = islec in ("esit_degil", "baslamaz", "bitmez", "icermez")
    return (lambda s: not f(s)) if olumsuz else f


def _ozel_gecer(k, v, metin: Optional[str]) -> bool:
    islec, deger = k
    if _sayi(deger):
        if islec in ("esit_degil",):
            return not (_sayi(v) and v == deger)
        if not _sayi(v):
            return False
        return {"esit": v == deger, "buyuk": v > deger, "buyuk_esit": v >= deger,
                "kucuk": v < deger, "kucuk_esit": v <= deger}.get(islec, False)
    desen = str(deger)
    if islec in ("buyuk", "buyuk_esit", "kucuk", "kucuk_esit"):
        if v is None or _sayi(v):
            return False
        a, b = metin_anahtari(metin or ""), metin_anahtari(desen)
        return {"buyuk": a > b, "buyuk_esit": a >= b, "kucuk": a < b, "kucuk_esit": a <= b}[islec]
    if metin is None:                                   # boş hücre: yalnız olumsuz işleçler geçer
        return islec in ("esit_degil", "baslamaz", "bitmez", "icermez")
    return _metin_islec(islec, desen)(metin)


def _sutun_hazirla(sayfa: Sayfa, filtre: Filtre, c: int, kosul, metin_al: MetinAl):
    """Sütun koşulunu `(r) -> bool` işlevine çevirir (ilk/ortalama sütunun TÜM veri satırlarına göre)."""
    a = filtre.aralik
    satirlar = range(a.ilk_satir + 1, a.son_satir + 1)
    if isinstance(kosul, DegerKosulu):
        izinli = {tr_kucuk(m) for m in kosul.metinler}

        def f(r):
            m = metin_al(sayfa, r, c)
            return kosul.bos if m is None or m == "" else tr_kucuk(m) in izinli
        return f
    if isinstance(kosul, OzelKosul):
        def f(r):
            v, m = sayfa.deger(r, c), metin_al(sayfa, r, c)
            s1 = _ozel_gecer(kosul.k1, v, m)
            if kosul.k2 is None:
                return s1
            s2 = _ozel_gecer(kosul.k2, v, m)
            return (s1 and s2) if kosul.ve else (s1 or s2)
        return f
    if isinstance(kosul, (IlkKosul, OrtalamaKosulu)):
        sayilar = [v for r in satirlar if _sayi(v := sayfa.deger(r, c))]
        if isinstance(kosul, OrtalamaKosulu):
            ort = sum(sayilar) / len(sayilar) if sayilar else 0.0
            return lambda r: _sayi(v := sayfa.deger(r, c)) and (v > ort if kosul.ustu else v < ort)
        adet = max(1, int(len(sayilar) * kosul.n / 100)) if kosul.yuzde else kosul.n
        sirali = sorted(sayilar, reverse=not kosul.alt)
        esik = sirali[min(adet, len(sirali)) - 1] if sirali else None
        if esik is None:
            return lambda r: False
        return lambda r: _sayi(v := sayfa.deger(r, c)) and (v <= esik if kosul.alt else v >= esik)
    if isinstance(kosul, RenkKosulu):
        def f(r):
            st = sayfa.stil(r, c)
            renk = st.dolgu if kosul.tur == "dolgu" else st.yazi_rengi
            return (renk or "").lower() == (kosul.renk or "").lower()
        return f
    return lambda r: True


def gizlenecekler(sayfa: Sayfa, filtre: Filtre, metin_al: MetinAl = gorunen_metin) -> Set[int]:
    """Veri satırlarından (başlık hariç) koşullardan **en az birini** sağlamayanlar."""
    a = filtre.aralik
    if not filtre.kosullar or a.son_satir <= a.ilk_satir:
        return set()
    hazir = [_sutun_hazirla(sayfa, filtre, c, k, metin_al) for c, k in filtre.kosullar.items()]
    gizli = set()
    for r in range(a.ilk_satir + 1, a.son_satir + 1):
        if not all(f(r) for f in hazir):
            gizli.add(r)
    return gizli


def veri_satirlari(filtre: Filtre) -> range:
    a = filtre.aralik
    return range(a.ilk_satir + 1, a.son_satir + 1)


def aralik_genislet(sayfa: Sayfa, aralik: Aralik) -> Aralik:
    """Filtre aralığını, başlığın altındaki bitişik dolu satırlara kadar uzatır (Excel filtre aralığını
    kendiliğinden uzatır); gizli satırlar da sayılır."""
    r = aralik.son_satir
    while r < 1_048_576:
        if not any((r + 1, c) in sayfa._hucreler for c in range(aralik.ilk_sutun, aralik.son_sutun + 1)):
            break
        r += 1
    return aralik if r == aralik.son_satir else Aralik(aralik.ilk_satir, aralik.ilk_sutun, r, aralik.son_sutun)


def liste_degerleri(sayfa: Sayfa, filtre: Filtre, sutun: int,
                    metin_al: MetinAl = gorunen_metin) -> Tuple[List[str], bool, int]:
    """Açılır liste: DİĞER sütunların koşullarını sağlayan satırların benzersiz görünen metinleri
    (`metin_anahtari` sırasıyla). Döner: `(değerler, boş var mı, atlanan benzersiz sayısı)`; liste
    `LISTE_SINIRI`'nda kesilir."""
    diger = [_sutun_hazirla(sayfa, filtre, c, k, metin_al) for c, k in filtre.kosullar.items() if c != sutun]
    gorulen: Dict[str, str] = {}
    bos = False
    for r in veri_satirlari(filtre):
        if not all(f(r) for f in diger):
            continue
        m = metin_al(sayfa, r, sutun)
        if m is None or m == "":
            bos = True
        else:
            gorulen.setdefault(tr_kucuk(m), m)
    sirali = sorted(gorulen.values(), key=lambda m: metin_anahtari(m))
    atlanan = max(0, len(sirali) - LISTE_SINIRI)
    return sirali[:LISTE_SINIRI], bos, atlanan


def sutun_renkleri(sayfa: Sayfa, filtre: Filtre, sutun: int, tur: str) -> List[Optional[str]]:
    """Sütundaki benzersiz dolgu/yazı renkleri (renksiz = None, listenin sonunda)."""
    renkler: List[Optional[str]] = []
    for r in veri_satirlari(filtre):
        st = sayfa.stil(r, sutun)
        renk = st.dolgu if tur == "dolgu" else st.yazi_rengi
        renk = renk.lower() if renk else None
        if renk not in renkler:
            renkler.append(renk)
    return sorted(renkler, key=lambda x: (x is None, x or ""))
