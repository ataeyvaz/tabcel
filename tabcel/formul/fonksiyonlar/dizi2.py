"""Dizi/matris/veritabanı işlevleri, 2. küme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok.
Kapsam dışı (bilinçli): LAMBDA ailesi (MAP, REDUCE, SCAN, MAKEARRAY), VDB, CELL, INFO — bkz. eksik_fonksiyonlar.md."""
import math

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, Dizi
from ..donustur import mantiga, metne, sayi_metninden, sayi_sonucu, sayiya
from . import fonksiyon
from .istatistik import _gorunen_dizi
from .ortak import duz, ham, kriter, matris


def _sayi_matris(v):
    """Aralık/dizi → sayı matrisi (satır listesi) ya da hata; metin/boş/mantıksal → #DEĞER!."""
    R, C, oku = matris(v)
    m = []
    for i in range(R):
        satir = []
        for j in range(C):
            x = oku(i, j)
            if isinstance(x, Hata):
                return x
            if not isinstance(x, float) or isinstance(x, bool):
                return D.DEGER_HATASI
            satir.append(x)
        m.append(satir)
    return m


@fonksiyon("MMULT", en_az=2, en_cok=2)
def _mmult(b, a, c):
    x, y = _sayi_matris(a), _sayi_matris(c)
    for m in (x, y):
        if isinstance(m, Hata):
            return m
    if len(x[0]) != len(y):
        return D.DEGER_HATASI
    return Dizi([[sayi_sonucu(math.fsum(x[i][k] * y[k][j] for k in range(len(y)))) for j in range(len(y[0]))]
                 for i in range(len(x))])


def _det(m):
    n = len(m)
    a = [r[:] for r in m]
    det = 1.0
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(a[r][i]))
        if a[p][i] == 0:
            return 0.0
        if p != i:
            a[i], a[p] = a[p], a[i]
            det = -det
        det *= a[i][i]
        for r in range(i + 1, n):
            f = a[r][i] / a[i][i]
            for c in range(i, n):
                a[r][c] -= f * a[i][c]
    return det


@fonksiyon("MDETERM", en_az=1, en_cok=1)
def _mdeterm(b, a):
    m = _sayi_matris(a)
    if isinstance(m, Hata):
        return m
    if len(m) != len(m[0]):
        return D.DEGER_HATASI
    return sayi_sonucu(_det(m))


@fonksiyon("MINVERSE", en_az=1, en_cok=1)
def _minverse(b, a):
    m = _sayi_matris(a)
    if isinstance(m, Hata):
        return m
    n = len(m)
    if n != len(m[0]):
        return D.DEGER_HATASI
    A = [m[i][:] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        if abs(A[p][i]) < 1e-300:
            return D.SAYI
        A[i], A[p] = A[p], A[i]
        d = A[i][i]
        A[i] = [x / d for x in A[i]]
        for r in range(n):
            if r != i and A[r][i] != 0:
                f = A[r][i]
                A[r] = [x - f * y for x, y in zip(A[r], A[i])]
    return Dizi([[A[i][n + j] + 0.0 for j in range(n)] for i in range(n)])


@fonksiyon("MUNIT", en_az=1, en_cok=1)
def _munit(b, n):
    n = sayiya(ham(n))
    if isinstance(n, Hata):
        return n
    n = math.trunc(n)
    if n < 1 or n > 1000:
        return D.DEGER_HATASI
    return Dizi([[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)])


@fonksiyon("FREQUENCY", en_az=2, en_cok=2)
def _frequency(b, veri, siniflar):
    v = [x for x in duz(veri) if isinstance(x, float) and not isinstance(x, bool)]
    for x in duz(veri) + duz(siniflar):
        if isinstance(x, Hata):
            return x
    s = [x for x in duz(siniflar) if isinstance(x, float) and not isinstance(x, bool)]
    if not s:
        return Dizi([[0.0]])                        # Excel (COM): boş sınıf aralığı tek sıfır döner
    sirali = sorted(set(s))
    sayim = {}
    onceki = -math.inf
    for k in sirali:
        sayim[k] = float(sum(1 for x in v if onceki < x <= k))
        onceki = k
    son = float(sum(1 for x in v if x > sirali[-1]))
    kullanildi = set()
    cikti = []
    for k in s:
        if k in kullanildi:
            cikti.append([0.0])
        else:
            kullanildi.add(k)
            cikti.append([sayim[k]])
    cikti.append([son])
    return Dizi(cikti)


# --- doğrusal / üstel regresyon (tek bağımsız değişken) ---
def _vektor(v):
    cikti = []
    for x in duz(v):
        if isinstance(x, Hata):
            return x
        if not isinstance(x, float) or isinstance(x, bool):
            return D.DEGER_HATASI
        cikti.append(x)
    return cikti


def _regres(y, x, sabit):
    n = len(y)
    if sabit:
        mx, my = math.fsum(x) / n, math.fsum(y) / n
        sxx = math.fsum((a - mx) ** 2 for a in x)
        if sxx == 0:
            return None
        egim = math.fsum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
        return egim, my - egim * mx
    sxx = math.fsum(a * a for a in x)
    if sxx == 0:
        return None
    return math.fsum(a * c for a, c in zip(x, y)) / sxx, 0.0


def _xy(y, x):
    yy = _vektor(y)
    if isinstance(yy, Hata):
        return yy, None
    if x is None or x is BOS_ARG:
        return yy, [float(i + 1) for i in range(len(yy))]
    xx = _vektor(x)
    if isinstance(xx, Hata):
        return xx, None
    if len(xx) != len(yy):
        return D.BASV, None
    return yy, xx


def _sabit_arg(v):
    if v is None or v is BOS_ARG:
        return True
    return mantiga(ham(v))


def _yeni_x(yeni, xx):
    if yeni is None or yeni is BOS_ARG:
        return xx
    return _vektor(yeni)


def _sekil(deger, yeni, y_sekli):
    R, C, _ = matris(yeni) if (yeni is not None and yeni is not BOS_ARG) else matris(y_sekli)
    return Dizi([[deger[i * C + j] for j in range(C)] for i in range(R)])


@fonksiyon("TREND", en_az=1, en_cok=4)
def _trend(b, y, x=None, yeni=None, sabit=None):
    yy, xx = _xy(y, x)
    if isinstance(yy, Hata):
        return yy
    s = _sabit_arg(sabit)
    if isinstance(s, Hata):
        return s
    r = _regres(yy, xx, s)
    nx = _yeni_x(yeni, xx)
    if isinstance(nx, Hata):
        return nx
    if r is None:
        return D.BOL0
    return _sekil([r[0] * a + r[1] for a in nx], yeni, x if (x is not None and x is not BOS_ARG) else y)


@fonksiyon("GROWTH", en_az=1, en_cok=4)
def _growth(b, y, x=None, yeni=None, sabit=None):
    yy, xx = _xy(y, x)
    if isinstance(yy, Hata):
        return yy
    if any(v <= 0 for v in yy):
        return D.SAYI
    s = _sabit_arg(sabit)
    if isinstance(s, Hata):
        return s
    r = _regres([math.log(v) for v in yy], xx, s)
    nx = _yeni_x(yeni, xx)
    if isinstance(nx, Hata):
        return nx
    if r is None:
        return D.BOL0
    try:
        return _sekil([math.exp(r[0] * a + r[1]) for a in nx], yeni, x if (x is not None and x is not BOS_ARG) else y)
    except OverflowError:
        return D.SAYI


@fonksiyon("LINEST", en_az=1, en_cok=4)
def _linest(b, y, x=None, sabit=None, istatistik=None):
    yy, xx = _xy(y, x)
    if isinstance(yy, Hata):
        return yy
    s = _sabit_arg(sabit)
    ist = False if istatistik is None or istatistik is BOS_ARG else mantiga(ham(istatistik))
    for v in (s, ist):
        if isinstance(v, Hata):
            return v
    r = _regres(yy, xx, s)
    if r is None:
        return D.BOL0
    egim, kesim = r
    if not ist:
        return Dizi([[egim, kesim]])
    n = len(yy)
    k = 1
    df = n - k - (1 if s else 0)
    ssres = math.fsum((c - (egim * a + kesim)) ** 2 for a, c in zip(xx, yy))
    my = math.fsum(yy) / n if s else 0.0
    sstop = math.fsum((c - my) ** 2 for c in yy)
    ssreg = sstop - ssres
    if df <= 0:
        return Dizi([[egim, kesim], [0.0, 0.0], [1.0, 0.0], [0.0, 0.0], [ssreg, ssres]])
    se_y = math.sqrt(ssres / df)
    mx = math.fsum(xx) / n
    sxx = math.fsum((a - mx) ** 2 for a in xx) if s else math.fsum(a * a for a in xx)
    se_m = se_y / math.sqrt(sxx)
    se_b = se_y * math.sqrt(1 / n + mx * mx / sxx) if s else 0.0
    r2 = ssreg / sstop if sstop else 1.0
    F = ssreg / (ssres / df) if ssres else 0.0
    return Dizi([[egim, kesim], [se_m, se_b], [r2, se_y], [F, float(df)], [ssreg, ssres]])


# --- sarma / bölme ---
def _sar(vektor, sayi, dolgu, satir_mi):
    v = duz(vektor)
    k = sayiya(ham(sayi))
    if isinstance(k, Hata):
        return k
    k = math.trunc(k)
    if k < 1:
        return D.SAYI
    d = D.YOK if dolgu is None or dolgu is BOS_ARG else ham(dolgu)
    k = min(k, max(len(v), 1))                      # sarma sayısı eleman sayısını aşarsa tek satır (Excel)
    bloklar = [v[i:i + k] + [d] * (k - len(v[i:i + k])) for i in range(0, len(v), k)] or [[d] * k]
    return Dizi(bloklar if satir_mi else [list(r) for r in zip(*bloklar)])


@fonksiyon("WRAPROWS", en_az=2, en_cok=3)
def _wraprows(b, v, k, dolgu=None):
    return _sar(v, k, dolgu, True)


@fonksiyon("WRAPCOLS", en_az=2, en_cok=3)
def _wrapcols(b, v, k, dolgu=None):
    return _sar(v, k, dolgu, False)


def _ayraclar(v):
    liste = []
    for x in duz(v):
        m = metne(x)
        if isinstance(m, Hata):
            return m
        liste.append(m)
    return liste


def _bol(metin, ayraclar, bos_atla, kucuk):
    from ..yerel import tr_kucuk
    if not ayraclar or any(a == "" for a in ayraclar):
        return [metin]
    kaynak = tr_kucuk(metin) if kucuk else metin
    aranan = [tr_kucuk(a) if kucuk else a for a in ayraclar]
    parcalar, bas, i = [], 0, 0
    while i < len(kaynak):
        uygun = [a for a in aranan if kaynak.startswith(a, i)]
        if uygun:
            a = max(uygun, key=len)
            parcalar.append(metin[bas:i])
            i += len(a)
            bas = i
        else:
            i += 1
    parcalar.append(metin[bas:])
    return [p for p in parcalar if p != ""] if bos_atla else parcalar


@fonksiyon("TEXTSPLIT", en_az=2, en_cok=6)
def _textsplit(b, metin, sutun_ay, satir_ay=None, bos_atla=None, esle=None, dolgu=None):
    m = metne(ham(metin))
    if isinstance(m, Hata):
        return m
    if m == "":
        return D.DEGER_HATASI
    sa = [] if sutun_ay is None or sutun_ay is BOS_ARG else _ayraclar(sutun_ay)
    if isinstance(sa, Hata):
        return sa
    ra = [] if satir_ay is None or satir_ay is BOS_ARG else _ayraclar(satir_ay)
    if isinstance(ra, Hata):
        return ra
    atla = False if bos_atla is None or bos_atla is BOS_ARG else mantiga(ham(bos_atla))
    kucuk = False if esle is None or esle is BOS_ARG else sayiya(ham(esle)) == 1
    for v in (atla,):
        if isinstance(v, Hata):
            return v
    d = D.YOK if dolgu is None or dolgu is BOS_ARG else ham(dolgu)
    if (not sa and not ra) or any(a == "" for a in sa + ra):
        return D.DEGER_HATASI
    satirlar = _bol(m, ra, atla, kucuk) if ra else [m]
    tablo = [_bol(s, sa, atla, kucuk) if sa else [s] for s in satirlar]
    genis = max(len(r) for r in tablo)
    return Dizi([r + [d] * (genis - len(r)) for r in tablo])


# --- veritabanı işlevleri ---
def _vt_eslesen(db, alan, olcut):
    """(değer listesi, hata) — DSUM… ailesi: `db` başlık satırlı aralık, `olcut` başlık + ölçüt satırları."""
    R, C, oku = matris(db)
    if R < 2:
        return None, D.DEGER_HATASI
    basliklar = [metne(oku(0, j)) for j in range(C)]
    from ..yerel import tr_kucuk
    ad = ham(alan)
    if isinstance(ad, Hata):
        return None, ad
    if isinstance(ad, str):
        hedef = [j for j, h in enumerate(basliklar) if isinstance(h, str) and tr_kucuk(h) == tr_kucuk(ad)]
        if not hedef:
            return None, D.DEGER_HATASI
        j0 = hedef[0]
    else:
        k = sayiya(ad)
        if isinstance(k, Hata):
            return None, k
        k = math.trunc(k)
        if k < 1 or k > C:
            return None, D.DEGER_HATASI
        j0 = k - 1
    cr, cc, co = matris(olcut)
    if cr < 2:
        return None, D.DEGER_HATASI
    ok_basliklar = [co(0, j) for j in range(cc)]
    kosullar = []
    for i in range(1, cr):
        satir = []
        for j in range(cc):
            hucre = co(i, j)
            if hucre is None or hucre == "":
                continue
            bh = ok_basliklar[j]
            if isinstance(bh, Hata):
                return None, bh
            sutunlar = [x for x, h in enumerate(basliklar) if isinstance(h, str) and isinstance(bh, str)
                        and tr_kucuk(h) == tr_kucuk(bh)]
            if not sutunlar:
                satir.append((None, kriter(hucre)))
            else:
                satir.append((sutunlar[0], kriter(hucre)))
        kosullar.append(satir)
    degerler = []
    for r in range(1, R):
        for satir in kosullar or [[]]:
            if all(c is not None and f(oku(r, c)) for c, f in satir):
                degerler.append(oku(r, j0))
                break
    return degerler, None


def _sayilar_vt(degerler):
    return [x for x in degerler if isinstance(x, float) and not isinstance(x, bool)]


def _db(ad, islev):
    @fonksiyon(ad, en_az=3, en_cok=3)
    def uygula(b, db, alan, olcut):
        d, h = _vt_eslesen(db, alan, olcut)
        if h is not None:
            return h
        for x in d:
            if isinstance(x, Hata):
                return x
        return islev(d)
    return uygula


_db("DSUM", lambda d: math.fsum(_sayilar_vt(d)))
_db("DCOUNT", lambda d: float(len(_sayilar_vt(d))))
_db("DCOUNTA", lambda d: float(len([x for x in d if x is not None and x != ""])))
_db("DMAX", lambda d: max(_sayilar_vt(d), default=0.0))
_db("DMIN", lambda d: min(_sayilar_vt(d), default=0.0))
_db("DAVERAGE", lambda d: (math.fsum(_sayilar_vt(d)) / len(_sayilar_vt(d))) if _sayilar_vt(d) else D.BOL0)
_db("DPRODUCT", lambda d: math.prod(_sayilar_vt(d)) if _sayilar_vt(d) else 0.0)
_db("DGET", lambda d: d[0] if len(d) == 1 else (D.DEGER_HATASI if not d else D.SAYI))


# --- AGGREGATE ---
_AGG = {1: "AVERAGE", 2: "COUNT", 3: "COUNTA", 4: "MAX", 5: "MIN", 6: "PRODUCT", 7: "STDEV.S", 8: "STDEV.P",
        9: "SUM", 10: "VAR.S", 11: "VAR.P", 12: "MEDIAN", 13: "MODE.SNGL", 14: "LARGE", 15: "SMALL",
        16: "PERCENTILE.INC", 17: "QUARTILE.INC", 18: "PERCENTILE.EXC", 19: "QUARTILE.EXC"}


@fonksiyon("AGGREGATE", en_az=3, en_cok=255, gizlilik=True)
def _aggregate(b, no, secenek, *args):
    from . import KAYIT
    n, o = sayiya(ham(no)), sayiya(ham(secenek))
    for x in (n, o):
        if isinstance(x, Hata):
            return x
    n, o = math.trunc(n), math.trunc(o)
    if n not in _AGG or o < 0 or o > 7:
        return D.DEGER_HATASI
    hata_atla = o in (2, 3, 6, 7)
    gizli_atla = o in (1, 3, 5, 7)

    def temizle(a):
        if isinstance(a, AralikDeger):
            a = _gorunen_dizi(a, True) if gizli_atla else a.diziye()
        if isinstance(a, Dizi):
            vals = [x for x in a.degerler() if not (hata_atla and isinstance(x, Hata))]
            return Dizi([vals]) if vals else Dizi([[]])
        return a
    if n >= 14:
        if len(args) != 2:
            return D.DEGER_HATASI
        return KAYIT[_AGG[n]].uygula(b, temizle(args[0]), args[1])
    return KAYIT[_AGG[n]].uygula(b, *[temizle(a) for a in args])


# --- bağlantı / formül metni / karmaşık sayı ---
@fonksiyon("HYPERLINK", en_az=1, en_cok=2)
def _hyperlink(b, adres, ad=None):
    if ad is None or ad is BOS_ARG:
        v = ham(adres)
        return metne(v) if not isinstance(v, Hata) else v
    v = ham(ad)
    return v if v is not None else 0.0


@fonksiyon("FORMULATEXT", en_az=1, en_cok=1)
def _formulatext(b, ref):
    if not isinstance(ref, AralikDeger):
        return D.YOK
    h = ref.sayfa.hucre(ref.r1, ref.c1)
    if h is None or not h.formul:
        return D.YOK
    from ..ceviri import gosterime
    return gosterime(h.formul, b.kitap)


@fonksiyon("IMAGINARY", en_az=1, en_cok=1)
def _imaginary(b, s):
    import re
    v = ham(s)
    if isinstance(v, Hata):
        return v
    if isinstance(v, float) and not isinstance(v, bool):
        return 0.0
    m = metne(v)
    if isinstance(m, Hata):
        return m
    m = m.replace(" ", "")
    if any(c in m for c in "eE"):
        return D.SAYI
    if m == "" or m[-1] not in "ij":
        return 0.0 if re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", m) else D.SAYI
    g = m[:-1]
    k = max((i for i, c in enumerate(g) if c in "+-" and i > 0 and g[i - 1] not in "eE"), default=-1)
    im = g[k:] if k >= 0 else g
    if not re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)?([eE][+-]?\d+)?", im):
        return D.SAYI
    return 1.0 if im in ("", "+") else -1.0 if im == "-" else float(im)
