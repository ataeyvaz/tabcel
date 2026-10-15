"""Arama ve başvuru fonksiyonları. Qt yok."""
import math
from typing import List, Optional

from ...model import adres as A
from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, Dizi
from ..donustur import karsilastir, mantiga, metne, sayiya
from ..yerel import tr_kucuk
from . import fonksiyon
from .ortak import ham, joker_var, matris, metin_deseni

SINIR_DIZI = 100_000      # ROW/COLUMN çok hücreli aralıkta dizi üretmenin üst sınırı


def _tur(v) -> int:
    if isinstance(v, bool):
        return 2
    if isinstance(v, float):
        return 0
    if isinstance(v, str):
        return 1
    return -1


def _aranan(v):
    """Aranan değer: boş → 0; aralık → tek değer."""
    v = ham(v)
    return 0.0 if v is None else v


def _tam_esles(aranan):
    if isinstance(aranan, str):
        if joker_var(aranan):
            desen = metin_deseni(aranan)
            return lambda v: isinstance(v, str) and desen(v)
        h = tr_kucuk(aranan)
        return lambda v: isinstance(v, str) and tr_kucuk(v) == h
    return lambda v: _tur(v) == _tur(aranan) and v == aranan


def bul_tam(aranan, liste: List, joker=True, sondan=False) -> Optional[int]:
    if joker:
        sinama = _tam_esles(aranan)
    else:
        sinama = (lambda v, h=tr_kucuk(aranan): isinstance(v, str) and tr_kucuk(v) == h) \
            if isinstance(aranan, str) else _tam_esles(aranan)
    idx = range(len(liste) - 1, -1, -1) if sondan else range(len(liste))
    for i in idx:
        if sinama(liste[i]):
            return i
    return None


def bul_yaklasik(aranan, liste: List, artan=True) -> Optional[int]:
    """artan=True: aranandan küçük/eşit en büyük (artan sıralı varsayılır); False: büyük/eşit en küçük (azalan).
    Artan aramada Excel gibi İKİLİ ARAMA (COM, 2026-10-15): sırasız veride de Excel'in verdiği sonucu verir
    (DÜŞEYARA(6;{10;5;7}) → 5'in satırı); eşitler arasında sonuncuyu seçer. Karışık türlü/hatalı
    listede yalnız aynı türdeki öğeler karşılaştırılır (doğrusal tarama)."""
    t = _tur(aranan)
    saf = artan and all(_tur(v) == t and not isinstance(v, Hata) for v in liste)
    if saf:                      # azalan (KAÇINCI −1) için Excel doğrusal davranır (COM ile doğrulandı)
        alt, ust, en_iyi = 0, len(liste) - 1, None
        while alt <= ust:
            orta = (alt + ust) // 2
            k = karsilastir(liste[orta], aranan)
            if isinstance(k, Hata):
                return None
            if (k <= 0) if artan else (k >= 0):
                en_iyi, alt = orta, orta + 1
            else:
                ust = orta - 1
        return en_iyi
    en_iyi = None
    for i, v in enumerate(liste):
        if _tur(v) != t or isinstance(v, Hata):
            continue
        k = karsilastir(v, aranan)
        if isinstance(k, Hata):
            continue
        if (k <= 0) if artan else (k >= 0):
            en_iyi = i
        else:
            break
    return en_iyi


def _eslesen_yaklasik_yon(aranan, liste, yon):
    """XLOOKUP/XMATCH: yon=-1 → tam ya da bir küçük; yon=1 → tam ya da bir büyük (sırasız tarama)."""
    en_iyi, en_deger = None, None
    t = _tur(aranan)
    for i, v in enumerate(liste):
        if _tur(v) != t or isinstance(v, Hata):
            continue
        k = karsilastir(v, aranan)
        if k == 0:
            return i
        if (yon < 0 and k < 0) or (yon > 0 and k > 0):
            if en_deger is None or (karsilastir(v, en_deger) * yon < 0):
                en_iyi, en_deger = i, v
    return en_iyi


def _dogrusal(m):
    R, C, oku = m
    if R != 1 and C != 1:
        return None
    return [oku(i, j) for i in range(R) for j in range(C)]


# --- DÜŞEYARA / YATAYARA ---
def _vh(dikey, aranan, tablo, indis, yaklasik):
    a = _aranan(aranan)
    if isinstance(a, Hata):
        return a
    if not isinstance(tablo, (AralikDeger, Dizi)):
        return D.DEGER_HATASI
    R, C, oku = matris(tablo)
    i = sayiya(ham(indis))
    if isinstance(i, Hata):
        return i
    i = math.trunc(i)
    if yaklasik is None or yaklasik is BOS_ARG:
        yak = yaklasik is None
    else:
        yak = mantiga(ham(yaklasik))
        if isinstance(yak, Hata):
            return yak
    if i < 1:
        return D.DEGER_HATASI
    if i > (C if dikey else R):
        return D.BASV
    anahtar = [oku(k, 0) for k in range(R)] if dikey else [oku(0, k) for k in range(C)]
    p = bul_yaklasik(a, anahtar, True) if yak else bul_tam(a, anahtar)
    if p is None:
        return D.YOK
    return oku(p, i - 1) if dikey else oku(i - 1, p)


@fonksiyon("VLOOKUP", en_az=3, en_cok=4)
def _vlookup(b, aranan, tablo, indis, yaklasik=None):
    return _vh(True, aranan, tablo, indis, yaklasik)


@fonksiyon("HLOOKUP", en_az=3, en_cok=4)
def _hlookup(b, aranan, tablo, indis, yaklasik=None):
    return _vh(False, aranan, tablo, indis, yaklasik)


# --- KAÇINCI / ÇAPRAZEŞLEŞTİR ---
@fonksiyon("MATCH", en_az=2, en_cok=3)
def _match(b, aranan, dizi, tur=None):
    a = _aranan(aranan)
    if isinstance(a, Hata):
        return a
    if not isinstance(dizi, (AralikDeger, Dizi)):
        return D.YOK
    t = 1.0
    if tur is not None and tur is not BOS_ARG:
        t = sayiya(ham(tur))
        if isinstance(t, Hata):
            return t
    elif tur is BOS_ARG:
        t = 0.0
    liste = _dogrusal(matris(dizi))
    if liste is None:
        return D.YOK
    if t == 0:
        p = bul_tam(a, liste)
    else:
        p = bul_yaklasik(a, liste, t > 0)
    return D.YOK if p is None else float(p + 1)


@fonksiyon("LOOKUP", en_az=2, en_cok=3)
def _lookup(b, aranan, vektor, sonuc=None):
    """ARA: vektör biçimi LOOKUP(x; arama_vektörü; [sonuç_vektörü]) ve dizi biçimi LOOKUP(x; dizi)
    (geniş dizide ilk satırda arar, son satırı; değilse ilk sütunda arar, son sütunu döndürür). Hep yaklaşık eşleşme."""
    a = _aranan(aranan)
    if isinstance(a, Hata):
        return a
    if not isinstance(vektor, (AralikDeger, Dizi)):
        return D.YOK
    R, C, oku = matris(vektor)
    if sonuc is None or sonuc is BOS_ARG:
        if C > R:
            anahtar, getir = [oku(0, k) for k in range(C)], (lambda p: oku(R - 1, p))
        else:
            anahtar, getir = [oku(k, 0) for k in range(R)], (lambda p: oku(p, C - 1))
    else:
        anahtar = _dogrusal((R, C, oku))
        if anahtar is None or not isinstance(sonuc, (AralikDeger, Dizi)):
            return D.YOK
        R2, C2, oku2 = matris(sonuc)
        sonuc_listesi = _dogrusal((R2, C2, oku2))
        if sonuc_listesi is None:
            return D.YOK
        getir = lambda p: sonuc_listesi[p] if p < len(sonuc_listesi) else D.YOK    # noqa: E731
    p = bul_yaklasik(a, anahtar, True)
    return D.YOK if p is None else getir(p)


def _arama_konumu(aranan, liste, eslesme, arama):
    """XLOOKUP/XMATCH ortak konum bulucu (sıfır tabanlı ya da None)."""
    sondan = arama in (-1,)
    if eslesme == 0:
        return bul_tam(aranan, liste, joker=False, sondan=sondan)
    if eslesme == 2:
        return bul_tam(aranan, liste, joker=True, sondan=sondan)
    if eslesme in (-1, 1):
        p = bul_tam(aranan, liste, joker=False, sondan=sondan)
        return p if p is not None else _eslesen_yaklasik_yon(aranan, liste, eslesme)
    return None


def _xarg(v, varsayilan):
    if v is None or v is BOS_ARG:
        return varsayilan
    x = sayiya(ham(v))
    return x if isinstance(x, Hata) else math.trunc(x)


@fonksiyon("XMATCH", en_az=2, en_cok=4)
def _xmatch(b, aranan, dizi, eslesme=None, arama=None):
    a = _aranan(aranan)
    if isinstance(a, Hata):
        return a
    e, s = _xarg(eslesme, 0), _xarg(arama, 1)
    for x in (e, s):
        if isinstance(x, Hata):
            return x
    if e not in (-1, 0, 1, 2) or s not in (1, -1, 2, -2) or not isinstance(dizi, (AralikDeger, Dizi)):
        return D.DEGER_HATASI
    liste = _dogrusal(matris(dizi))
    if liste is None:
        return D.DEGER_HATASI
    p = _arama_konumu(a, liste, e, s)
    return D.YOK if p is None else float(p + 1)


@fonksiyon("XLOOKUP", en_az=3, en_cok=6)
def _xlookup(b, aranan, arama_dizisi, donus, bulunamazsa=None, eslesme=None, arama=None):
    a = _aranan(aranan)
    if isinstance(a, Hata):
        return a
    e, s = _xarg(eslesme, 0), _xarg(arama, 1)
    for x in (e, s):
        if isinstance(x, Hata):
            return x
    if e not in (-1, 0, 1, 2) or s not in (1, -1, 2, -2):
        return D.DEGER_HATASI
    if not isinstance(arama_dizisi, (AralikDeger, Dizi)) or not isinstance(donus, (AralikDeger, Dizi)):
        return D.DEGER_HATASI
    R, C, _ = matris(arama_dizisi)
    liste = _dogrusal(matris(arama_dizisi))
    if liste is None:
        return D.DEGER_HATASI
    dr, dc, doku = matris(donus)
    satirlar = C == 1                                # arama sütunsa satır döner
    if (satirlar and dr != R) or (not satirlar and dc != C):
        return D.DEGER_HATASI
    p = _arama_konumu(a, liste, e, s)
    if p is None:
        if bulunamazsa is not None and bulunamazsa is not BOS_ARG:
            return bulunamazsa
        return D.YOK
    if satirlar:
        if dc == 1:
            return doku(p, 0)
        return Dizi([[doku(p, j) for j in range(dc)]])
    if dr == 1:
        return doku(0, p)
    return Dizi([[doku(i, p)] for i in range(dr)])


# --- İNDİS / ELEMAN / SATIR / SÜTUN ---
@fonksiyon("INDEX", en_az=2, en_cok=3)
def _index(b, dizi, satir, sutun=None):
    if not isinstance(dizi, (AralikDeger, Dizi)):
        dizi = Dizi([[None if dizi is BOS_ARG else dizi]])
    R, C, oku = matris(dizi)
    r = sayiya(ham(satir))
    if isinstance(r, Hata):
        return r
    r = math.trunc(r)
    if sutun is None:
        if R == 1 and C > 1:                           # tek satır: tek indis sütundur
            c, r = r, 1
        else:
            c = 0
    else:
        c = sayiya(ham(sutun))
        if isinstance(c, Hata):
            return c
        c = math.trunc(c)
    if r < 0 or c < 0:
        return D.DEGER_HATASI
    if r > R or c > C:
        return D.BASV
    r1, r2 = (1, R) if r == 0 else (r, r)
    c1, c2 = (1, C) if c == 0 else (c, c)
    if isinstance(dizi, AralikDeger):
        return AralikDeger(dizi.sayfa, dizi.r1 + r1 - 1, dizi.c1 + c1 - 1,
                           dizi.r1 + r2 - 1, dizi.c1 + c2 - 1)
    if r1 == r2 and c1 == c2:
        return oku(r1 - 1, c1 - 1)
    return Dizi([[oku(i, j) for j in range(c1 - 1, c2)] for i in range(r1 - 1, r2)])


@fonksiyon("CHOOSE", en_az=2, en_cok=255)
def _choose(b, indis, *secenekler):
    i = sayiya(ham(indis))
    if isinstance(i, Hata):
        return i
    i = math.trunc(i)
    if i < 1 or i > len(secenekler):
        return D.DEGER_HATASI
    v = secenekler[i - 1]
    return 0.0 if v is BOS_ARG else v


def _satir_sutun(b, ref, satir_mi):
    if ref is None:
        return float(b.satir if satir_mi else b.sutun)
    if isinstance(ref, Hata):
        return ref
    if isinstance(ref, AralikDeger):
        bas, son = (ref.r1, ref.r2) if satir_mi else (ref.c1, ref.c2)
        if bas == son or son - bas + 1 > SINIR_DIZI:
            return float(bas)
        degerler = [float(k) for k in range(bas, son + 1)]
        return Dizi([[x] for x in degerler]) if satir_mi else Dizi([degerler])
    return D.DEGER_HATASI


@fonksiyon("ROW", en_az=0, en_cok=1)
def _row(b, ref=None):
    return _satir_sutun(b, None if ref is BOS_ARG else ref, True)


@fonksiyon("COLUMN", en_az=0, en_cok=1)
def _column(b, ref=None):
    return _satir_sutun(b, None if ref is BOS_ARG else ref, False)


@fonksiyon("ROWS", en_az=1, en_cok=1)
def _rows(b, dizi):
    if isinstance(dizi, Hata):
        return dizi
    if isinstance(dizi, AralikDeger):
        return float(dizi.satir_sayisi)
    if isinstance(dizi, Dizi):
        return float(dizi.satir_sayisi)
    return D.DEGER_HATASI if dizi is BOS_ARG else 1.0


@fonksiyon("COLUMNS", en_az=1, en_cok=1)
def _columns(b, dizi):
    if isinstance(dizi, Hata):
        return dizi
    if isinstance(dizi, AralikDeger):
        return float(dizi.sutun_sayisi)
    if isinstance(dizi, Dizi):
        return float(dizi.sutun_sayisi)
    return D.DEGER_HATASI if dizi is BOS_ARG else 1.0


# --- DOLAYLI / KAYDIR ---
@fonksiyon("INDIRECT", en_az=1, en_cok=2, dinamik=True)
def _indirect(b, metin, a1=None):
    m = metne(ham(metin))
    if isinstance(m, Hata):
        return m
    if a1 is not None and a1 is not BOS_ARG:
        k = mantiga(ham(a1))
        if isinstance(k, Hata):
            return k
        if not k:
            return D.BASV                              # R1C1 gösterimi desteklenmez
    sayfa_adi, _, ref = m.rpartition("!")
    sayfa = b.sayfa
    if sayfa_adi:
        if sayfa_adi.startswith("'") and sayfa_adi.endswith("'") and len(sayfa_adi) >= 2:
            sayfa_adi = sayfa_adi[1:-1].replace("''", "'")
        sayfa = b.sayfa_bul(sayfa_adi)
        if sayfa is None:
            return D.BASV
    try:
        ar = A.aralik_coz(ref.replace("$", ""))
    except A.AdresHatasi:
        return D.BASV
    return AralikDeger(sayfa, ar.ilk_satir, ar.ilk_sutun, ar.son_satir, ar.son_sutun)


@fonksiyon("OFFSET", en_az=3, en_cok=5, dinamik=True)
def _offset(b, ref, satirlar, sutunlar, yukseklik=None, genislik=None):
    if not isinstance(ref, AralikDeger):
        return D.DEGER_HATASI
    sayilar_ = []
    for v in (satirlar, sutunlar):
        x = sayiya(ham(v))
        if isinstance(x, Hata):
            return x
        sayilar_.append(math.trunc(x))
    h, w = ref.satir_sayisi, ref.sutun_sayisi
    for ad, v in (("h", yukseklik), ("w", genislik)):
        if v is not None and v is not BOS_ARG:
            x = sayiya(ham(v))
            if isinstance(x, Hata):
                return x
            if ad == "h":
                h = math.trunc(x)
            else:
                w = math.trunc(x)
    r1, c1 = ref.r1 + sayilar_[0], ref.c1 + sayilar_[1]
    r2, c2 = r1 + h - 1, c1 + w - 1
    if h < 1 or w < 1 or r1 < 1 or c1 < 1 or r2 > A.MAX_ROW or c2 > A.MAX_COL:
        return D.BASV
    return AralikDeger(ref.sayfa, r1, c1, r2, c2)
