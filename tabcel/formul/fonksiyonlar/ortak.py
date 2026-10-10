"""Fonksiyon gruplarının ortak yardımcıları: öğe öğe yayma, ölçüt çözümleme, aralık hizalama.

`skaler(...)` ile kaydedilen fonksiyon her argümanı tek değer bekler; aralık/dizi gelirse Excel 365
gibi öğe öğe uygulanır (`=YUVARLA(A1:A3;0)` → dizi). Tek hücreli aralık değerine indirilir.
"""
import functools
import re
from typing import Callable, List, Optional, Tuple

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import (
    BOS_ARG, AralikDeger, Dizi, _boyut, _okuyucu, _yay,
)
from ..donustur import karsilastir, mantiga, metne, sayi_metninden, sayiya
from ..yerel import tr_kucuk
from . import fonksiyon

TIPLER = {
    "s": sayiya,        # sayı (boş → 0, metin sayıya, değilse #DEĞER!)
    "m": metne,         # metin
    "b": mantiga,       # mantıksal
    "h": None,          # ham değer; hata da fonksiyona ulaşır; atlanmış argüman None olur
}


def _donustur(tip: str, v):
    if v is BOS_ARG:
        v = None
    if isinstance(v, Hata):
        return v
    f = TIPLER[tip]
    return v if f is None else f(v)


def skaler(ad: str, tipler: str, en_az: Optional[int] = None, **kw):
    """Tek değerli fonksiyonu kaydeder. `tipler`: her argüman için 's' sayı, 'm' metin, 'b' mantık,
    'h' ham (son harfler isteğe bağlı olabilir: `en_az` ile). Hata girdisi (ilk soldan) olduğu gibi
    döner; dönüştürme hatası da öyle. Fonksiyon `f(baglam, *donusmus)` biçimindedir."""
    en_az = len(tipler) if en_az is None else en_az

    def kaydet(f):
        def uygula(b, *args):
            if any(_boyut(a) not in (None, (1, 1)) for a in args):
                return _yay_uygula(f, b, tipler, args)
            return _tek(f, b, tipler, args)
        fonksiyon(ad, en_az=en_az, en_cok=len(tipler), **kw)(uygula)
        return f
    return kaydet


def _tek(f, b, tipler, args):
    vals = []
    for t, a in zip(tipler, args):
        if isinstance(a, AralikDeger):
            a = a.hucre_degeri(a.r1, a.c1)
        elif isinstance(a, Dizi):
            a = a.satirlar[0][0]
        v = _donustur(t, a)
        if isinstance(v, Hata) and t != "h":
            return v
        vals.append(v)
    return f(b, *vals)


def _yay_uygula(f, b, tipler, args):
    boyutlar = [_boyut(a) for a in args]
    R = max(x[0] for x in boyutlar if x)
    C = max(x[1] for x in boyutlar if x)
    oku = [_yay(_okuyucu(a), bo, R, C) for a, bo in zip(args, boyutlar)]
    return Dizi([[_tek(f, b, tipler, [o(i, j) for o in oku]) for j in range(C)]
                 for i in range(R)])


# --- değer yardımcıları ---
def ham(v):
    """Atlanmış argüman → None; tek hücreli aralık → değeri."""
    if v is BOS_ARG:
        return None
    if isinstance(v, AralikDeger) and v.tek_hucre():
        return v.hucre_degeri(v.r1, v.c1)
    return v


def matris(v) -> Tuple[int, int, Callable]:
    """Her değeri (R, C, oku(i,j)) matrisine çevirir (skaler → 1×1)."""
    bo = _boyut(v)
    if bo is None:
        x = None if v is BOS_ARG else v
        return 1, 1, (lambda i, j: x)
    return bo[0], bo[1], _okuyucu(v)


def duz(v) -> List:
    """Aralık/dizi/skaler → değer listesi (satır sırasıyla)."""
    R, C, o = matris(v)
    return [o(i, j) for i in range(R) for j in range(C)]


def aralik_mi(v) -> bool:
    return isinstance(v, AralikDeger)


def hizala(araliklar) -> Optional[Tuple[int, int]]:
    """Aynı boyutlu aralıkların (kırpılmış) boyutu; boyutlar uyuşmuyorsa ya da aralık değilse None."""
    if not all(isinstance(a, AralikDeger) for a in araliklar):
        return None
    ham_boyut = {(a.satir_sayisi, a.sutun_sayisi) for a in araliklar}
    if len(ham_boyut) != 1:
        return None
    return _boyut(araliklar[0])


# --- ölçüt (EĞERSAY, ETOPLA …) ---
_OP = re.compile(r"^(<=|>=|<>|<|>|=)?(.*)$", re.S)


def _joker_regex(desen: str):
    cikti, i = [], 0
    while i < len(desen):
        c = desen[i]
        if c == "~" and i + 1 < len(desen) and desen[i + 1] in "*?~":
            cikti.append(re.escape(desen[i + 1]))
            i += 2
            continue
        cikti.append(".*" if c == "*" else "." if c == "?" else re.escape(c))
        i += 1
    return re.compile("^" + "".join(cikti) + "$", re.S)


def joker_var(metin: str) -> bool:
    return any(c in metin for c in "*?~")


def metin_deseni(desen: str) -> Callable[[str], bool]:
    """Joker (`*`, `?`, `~`) destekli, büyük/küçük harf duyarsız tam eşleşme."""
    r = _joker_regex(tr_kucuk(desen))
    return lambda s: r.match(tr_kucuk(s)) is not None


def olcut_yayar(konumlar: Callable[[int], range]):
    """Ölçütlü fonksiyon (EĞERSAY/ETOPLA/…) için Excel 365 yayması: bir ölçüt argümanı çok hücreli
    aralık/dizi ise her öğe için ayrı hesaplanıp dizi döner (`=TOPLA.ÇARPIM(1/EĞERSAY(A1:A9;A1:A9))`
    benzersiz sayma deyimi). `konumlar(argüman_sayısı)`: ölçüt argümanlarının indeksleri."""
    def dekor(f):
        @functools.wraps(f)
        def sar(b, *args):
            idx = [i for i in konumlar(len(args)) if i < len(args)]
            cok = [i for i in idx if (bt := _boyut(args[i])) is not None and bt != (1, 1)]
            if not cok:
                return f(b, *args)
            R = max(_boyut(args[i])[0] for i in cok)
            C = max(_boyut(args[i])[1] for i in cok)
            okuyucular = {i: _yay(_okuyucu(args[i]), _boyut(args[i]), R, C) for i in cok}
            satirlar = []
            for i in range(R):
                satir = []
                for j in range(C):
                    yeni = list(args)
                    for k, oku in okuyucular.items():
                        yeni[k] = oku(i, j)
                    satir.append(f(b, *yeni))
                satirlar.append(satir)
            return Dizi(satirlar)
        return sar
    return dekor


def kriter(olcut) -> Callable[[object], bool]:
    """Ölçüt değerinden hücre sınama işlevi üretir (Excel EĞERSAY kuralları)."""
    olcut = ham(olcut)
    if isinstance(olcut, Hata):
        return lambda v: v == olcut
    if olcut is None:
        olcut = 0.0
    if isinstance(olcut, bool):
        return lambda v: isinstance(v, bool) and v == olcut
    if isinstance(olcut, float):
        return lambda v: _sayi_esit(v, olcut)
    if not isinstance(olcut, str):
        return lambda v: False
    op, geri = _OP.match(olcut).groups()
    op = op or "="
    hedef_sayi = sayi_metninden(geri) if geri.strip() else None
    if geri.upper() in ("TRUE", "DOĞRU") and op in ("=", "<>"):
        esit = lambda v: isinstance(v, bool) and v is True     # noqa: E731
        return esit if op == "=" else (lambda v: not esit(v))
    if geri.upper() in ("FALSE", "YANLIŞ") and op in ("=", "<>"):
        esit = lambda v: isinstance(v, bool) and v is False    # noqa: E731
        return esit if op == "=" else (lambda v: not esit(v))
    if geri == "":
        bos = lambda v: v is None or v == ""                    # noqa: E731
        if op == "=":
            return bos
        if op == "<>":
            return lambda v: not bos(v)
        return lambda v: False
    hata = _hata_adindan(geri) if geri.startswith("#") else None
    if hata is not None and op in ("=", "<>"):
        return (lambda v: v == hata) if op == "=" else (lambda v: v != hata)
    if hedef_sayi is not None:
        if op == "=":
            return lambda v: _sayi_esit(v, hedef_sayi)
        if op == "<>":
            return lambda v: not _sayi_esit(v, hedef_sayi)
        k = {"<": lambda a, c: a < c, ">": lambda a, c: a > c,
             "<=": lambda a, c: a <= c, ">=": lambda a, c: a >= c}[op]
        return lambda v: isinstance(v, float) and not isinstance(v, bool) and k(v, hedef_sayi)
    # metin
    if op in ("=", "<>"):
        eslesir = metin_deseni(geri) if joker_var(geri) else (
            lambda s, h=tr_kucuk(geri): tr_kucuk(s) == h)
        if op == "=":
            return lambda v: isinstance(v, str) and eslesir(v)
        return lambda v: not (isinstance(v, str) and eslesir(v))
    # sıra karşılaştırması Türkçe harmanlamayla (`"<m"` ölçütü ç, ğ, ı, ö, ş, ü'yü doğru yere koyar)
    k = {"<": lambda a, c: a < c, ">": lambda a, c: a > c,
         "<=": lambda a, c: a <= c, ">=": lambda a, c: a >= c}[op]
    return lambda v: isinstance(v, str) and k(karsilastir(v, geri), 0)


def _hata_adindan(metin: str):
    """Ölçütteki hata adı: kanonik (`#DIV/0!`) ya da Türkçe görünümü (`#BÖL/0!`)."""
    from ...model.gosterim import HATA_TR
    h = D.hata_bul(metin)
    if h is not None:
        return h
    ust = tr_kucuk(metin.strip())
    for kod, tr in HATA_TR.items():
        if tr_kucuk(tr) == ust:
            return D.hata_bul(kod)
    return None


def _sayi_esit(v, hedef: float) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, float):
        return v == hedef
    if isinstance(v, str):                     # EĞERSAY(…;5) "5" metnini de sayar (Excel davranışı)
        n = sayi_metninden(v)
        return n is not None and n == hedef
    return False


def ilk_hata(*vals):
    for v in vals:
        if isinstance(v, Hata):
            return v
    return None
