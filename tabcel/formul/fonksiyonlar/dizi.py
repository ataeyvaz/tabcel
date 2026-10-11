"""Dinamik dizi işlevleri (Faz 8e): SORT, SORTBY, FILTER, UNIQUE, SEQUENCE, TAKE, DROP, VSTACK, HSTACK, TOCOL, TOROW,
CHOOSECOLS, CHOOSEROWS, EXPAND, TRANSPOSE, RANDARRAY. Hepsi `Dizi` döndürür; hücreye taşma (spill) motor katmanındadır.

Excel 365 davranışı: sıralama Excel sırasıyla (`harmanla.deger_anahtari`, kararlı), hata değerleri dizide yayılmaz
(yalnız argüman hatası dönüşü etkiler), boş hücre dizide boş (taşarken 0 görünür), eşleşme yoksa FILTER `#HESAPLAMA!`
(`#CALC!`) verir. Türkçe adlar Excel 365'ten (COM `Formula2Local`) doğrulandı — surec.md Faz 8e."""
import random
from typing import Callable, List, Optional

from ...model import deger as D
from ...model.deger import Hata
from ...model.harmanla import deger_anahtari, tr_kucuk
from ..degerler import BOS_ARG, AralikDeger, Dizi
from ..donustur import mantiga, sayiya
from . import fonksiyon
from .ortak import ham, matris

HESAPLAMA = D.HESAPLA
SINIR = 2_000_000                       # sonuç hücre sayısı üst sınırı


def _mat(v) -> List[list]:
    """Aralık/dizi/skaler → satır listeleri (kopya)."""
    R, C, oku = matris(v)
    return [[oku(i, j) for j in range(C)] for i in range(R)]


def _argumanlar_hata(*v) -> Optional[Hata]:
    for x in v:
        if isinstance(x, Hata):
            return x
    return None


def _int(v, varsayilan: Optional[int] = None):
    """Tamsayı argüman: atlanmış/None → varsayılan; sayı olmayan → #DEĞER!."""
    v = ham(v)
    if v is None:
        return varsayilan
    n = sayiya(v)
    if isinstance(n, Hata):
        return n
    return int(n)                                            # Excel kesir kısmını atar


def _mantik(v, varsayilan: bool = False):
    v = ham(v)
    if v is None:
        return varsayilan
    m = mantiga(v)
    return m


def _dizi(satirlar: List[list]):
    if not satirlar or not satirlar[0]:
        return HESAPLAMA                                     # boş dizi: Excel #CALC!
    if len(satirlar) * len(satirlar[0]) > SINIR:
        return D.SAYI
    return Dizi(satirlar)


def _devrik(m: List[list]) -> List[list]:
    return [list(s) for s in zip(*m)] if m and m[0] else []


# --- SORT / SORTBY ---------------------------------------------------------------------------------
def _sirala_sec(m: List[list], anahtarlar: List[tuple], satir_sirala: bool):
    """`anahtarlar`: [(değer listesi, artan)]; satırları (satir_sirala) ya da sütunları kararlı sıralar."""
    sira = list(range(len(anahtarlar[0][0])))
    for degerler, artan in reversed(anahtarlar):
        sira.sort(key=lambda i: deger_anahtari(degerler[i], artan))
    return [m[i] for i in sira] if satir_sirala else [[s[i] for i in sira] for s in m]


def _duzen(v):
    n = _int(v, 1)
    if isinstance(n, Hata):
        return n
    if n not in (1, -1):
        return D.DEGER_HATASI
    return n == 1


@fonksiyon("SORT", en_az=1, en_cok=4)
def _sort(b, dizi, indis=BOS_ARG, duzen=BOS_ARG, sutun_bazli=BOS_ARG):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    m = _mat(dizi)
    sutunla = _mantik(sutun_bazli)
    if isinstance(sutunla, Hata):
        return sutunla
    i = _int(indis, 1)
    artan = _duzen(duzen)
    for x in (i, artan):
        if isinstance(x, Hata):
            return x
    boyut = len(m) if sutunla else len(m[0])
    if not 1 <= i <= boyut:
        return D.DEGER_HATASI
    if sutunla:                                              # satır ölçütüne göre sütunları sırala
        return _dizi(_sirala_sec(m, [(m[i - 1], artan)], False))
    return _dizi(_sirala_sec(m, [([s[i - 1] for s in m], artan)], True))


@fonksiyon("SORTBY", en_az=2, en_cok=255)
def _sortby(b, dizi, *cift):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    m = _mat(dizi)
    anahtarlar = []
    satir_sirala = None
    i = 0
    while i < len(cift):
        by = cift[i]
        h = _argumanlar_hata(by)
        if h:
            return h
        duzen = _duzen(cift[i + 1]) if i + 1 < len(cift) else True
        if isinstance(duzen, Hata):
            return duzen
        v = _mat(by)
        if len(v[0]) == 1 and len(v) == len(m):
            yon = True
            deg = [s[0] for s in v]
        elif len(v) == 1 and len(v[0]) == len(m[0]):
            yon = False
            deg = v[0]
        else:
            return D.DEGER_HATASI
        if satir_sirala is None:
            satir_sirala = yon
        elif satir_sirala != yon:
            return D.DEGER_HATASI
        anahtarlar.append((deg, duzen))
        i += 2
    return _dizi(_sirala_sec(m, anahtarlar, satir_sirala))


# --- FILTER / UNIQUE -------------------------------------------------------------------------------
@fonksiyon("FILTER", en_az=2, en_cok=3)
def _filter(b, dizi, dahil, bos_ise=BOS_ARG):
    h = _argumanlar_hata(dizi, dahil)
    if h:
        return h
    m, k = _mat(dizi), _mat(dahil)
    if len(k[0]) == 1 and len(k) == len(m):                  # sütun vektörü: satırları süz
        bayrak, satir_mi = [s[0] for s in k], True
    elif len(k) == 1 and len(k[0]) == len(m[0]):             # satır vektörü: sütunları süz
        bayrak, satir_mi = k[0], False
    else:
        return D.DEGER_HATASI
    secim = []
    for v in bayrak:
        if isinstance(v, Hata):
            return v
        if v is None:
            secim.append(False)
            continue
        mv = mantiga(v)
        if isinstance(mv, Hata):
            return mv
        secim.append(bool(mv))
    if satir_mi:
        sonuc = [s for s, ok in zip(m, secim) if ok]
    else:
        idx = [j for j, ok in enumerate(secim) if ok]
        sonuc = [[s[j] for j in idx] for s in m] if idx else []
    if not sonuc or not sonuc[0]:
        return HESAPLAMA if bos_ise is BOS_ARG else bos_ise
    return Dizi(sonuc)


def _benzersiz_anahtar(v):
    if v is None:
        return ("b",)
    if isinstance(v, bool):
        return ("l", v)
    if isinstance(v, float):
        return ("n", v)
    if isinstance(v, Hata):
        return ("h", v.kod)
    return ("s", tr_kucuk(str(v)))


@fonksiyon("UNIQUE", en_az=1, en_cok=3)
def _unique(b, dizi, sutun_bazli=BOS_ARG, bir_kez=BOS_ARG):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    m = _mat(dizi)
    sutunla = _mantik(sutun_bazli)
    tek = _mantik(bir_kez)
    for x in (sutunla, tek):
        if isinstance(x, Hata):
            return x
    if sutunla:
        m = _devrik(m)
    sayac, ilk = {}, []
    for satir in m:
        a = tuple(_benzersiz_anahtar(v) for v in satir)
        if a not in sayac:
            sayac[a] = 0
            ilk.append((a, satir))
        sayac[a] += 1
    sonuc = [s for a, s in ilk if (sayac[a] == 1 if tek else True)]
    if not sonuc:
        return HESAPLAMA
    return _dizi(_devrik(sonuc) if sutunla else sonuc)


# --- SEQUENCE / RANDARRAY --------------------------------------------------------------------------
@fonksiyon("SEQUENCE", en_az=1, en_cok=4)
def _sequence(b, satir, sutun=BOS_ARG, baslangic=BOS_ARG, adim=BOS_ARG):
    r, c = _int(satir, 1), _int(sutun, 1)
    for x in (r, c):
        if isinstance(x, Hata):
            return x
    bas, ad = sayiya(ham(baslangic) if ham(baslangic) is not None else 1.0), \
        sayiya(ham(adim) if ham(adim) is not None else 1.0)
    for x in (bas, ad):
        if isinstance(x, Hata):
            return x
    if r < 1 or c < 1:
        return D.SAYI                                        # Excel: #HESAPLAMA! değil #SAYI! (0/negatif boyut)
    if r * c > SINIR:
        return D.SAYI
    return Dizi([[float(bas + (i * c + j) * ad) for j in range(c)] for i in range(r)])


@fonksiyon("RANDARRAY", en_az=0, en_cok=5, degisken=True)
def _randarray(b, satir=BOS_ARG, sutun=BOS_ARG, en_az=BOS_ARG, en_cok=BOS_ARG, tamsayi=BOS_ARG):
    r, c = _int(satir, 1), _int(sutun, 1)
    lo = sayiya(ham(en_az) if ham(en_az) is not None else 0.0)
    hi = sayiya(ham(en_cok) if ham(en_cok) is not None else 1.0)
    tam = _mantik(tamsayi)
    for x in (r, c, lo, hi, tam):
        if isinstance(x, Hata):
            return x
    if r < 1 or c < 1 or r * c > SINIR or lo > hi:
        return D.SAYI if lo > hi or r * c > SINIR else D.DEGER_HATASI

    def bir():
        return float(random.randint(int(lo), int(hi))) if tam else lo + random.random() * (hi - lo)
    return Dizi([[bir() for _ in range(c)] for _ in range(r)])


# --- TAKE / DROP -----------------------------------------------------------------------------------
def _dilim(n: int, adet) -> Optional[slice]:
    """Başından (+) ya da sonundan (−) `adet` öğe; 0 → boş (Excel #HESAPLAMA!)."""
    if adet is None:
        return slice(0, n)
    if adet == 0:
        return None
    return slice(0, min(adet, n)) if adet > 0 else slice(max(n + adet, 0), n)


@fonksiyon("TAKE", en_az=2, en_cok=3)
def _take(b, dizi, satirlar, sutunlar=BOS_ARG):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    m = _mat(dizi)
    r, c = _int(satirlar, None), _int(sutunlar, None)
    for x in (r, c):
        if isinstance(x, Hata):
            return x
    rs, cs = _dilim(len(m), r), _dilim(len(m[0]), c)
    if rs is None or cs is None:
        return HESAPLAMA
    return _dizi([s[cs] for s in m[rs]])


@fonksiyon("DROP", en_az=2, en_cok=3)
def _drop(b, dizi, satirlar, sutunlar=BOS_ARG):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    m = _mat(dizi)
    r, c = _int(satirlar, 0), _int(sutunlar, 0)
    for x in (r, c):
        if isinstance(x, Hata):
            return x

    def kalan(n, adet):
        return slice(min(adet, n), n) if adet >= 0 else slice(0, max(n + adet, 0))
    kalan_satirlar = m[kalan(len(m), r)]
    return _dizi([s[kalan(len(m[0]), c)] for s in kalan_satirlar])


# --- VSTACK / HSTACK / TOCOL / TOROW / CHOOSE* / EXPAND / TRANSPOSE --------------------------------
@fonksiyon("VSTACK", en_az=1, en_cok=254)
def _vstack(b, *diziler):
    h = _argumanlar_hata(*diziler)
    if h:
        return h
    ms = [_mat(d) for d in diziler]
    genislik = max(len(m[0]) for m in ms)
    sonuc = []
    for m in ms:
        for s in m:
            sonuc.append(s + [D.YOK] * (genislik - len(s)))      # dar diziler #YOK ile tamamlanır (Excel)
    return _dizi(sonuc)


@fonksiyon("HSTACK", en_az=1, en_cok=254)
def _hstack(b, *diziler):
    h = _argumanlar_hata(*diziler)
    if h:
        return h
    ms = [_mat(d) for d in diziler]
    yukseklik = max(len(m) for m in ms)
    sonuc = [[] for _ in range(yukseklik)]
    for m in ms:
        for i in range(yukseklik):
            sonuc[i] += m[i] if i < len(m) else [D.YOK] * len(m[0])
    return _dizi(sonuc)


def _duzlestir(m: List[list], yoksay: int, sutun_sirasi: bool) -> list:
    ogeler = [m[i][j] for j in range(len(m[0])) for i in range(len(m))] if sutun_sirasi else \
        [v for s in m for v in s]
    if yoksay in (1, 3):
        ogeler = [v for v in ogeler if v is not None]
    if yoksay in (2, 3):
        ogeler = [v for v in ogeler if not isinstance(v, Hata)]
    return ogeler


def _tocol_row(dizi, yoksay, sutun_sirasi, sutuna: bool):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    y, s = _int(yoksay, 0), _mantik(sutun_sirasi)
    for x in (y, s):
        if isinstance(x, Hata):
            return x
    if y not in (0, 1, 2, 3):
        return D.DEGER_HATASI
    ogeler = _duzlestir(_mat(dizi), y, s)
    if not ogeler:
        return HESAPLAMA
    return _dizi([[v] for v in ogeler] if sutuna else [ogeler])


@fonksiyon("TOCOL", en_az=1, en_cok=3)
def _tocol(b, dizi, yoksay=BOS_ARG, sutun_sirasi=BOS_ARG):
    return _tocol_row(dizi, yoksay, sutun_sirasi, True)


@fonksiyon("TOROW", en_az=1, en_cok=3)
def _torow(b, dizi, yoksay=BOS_ARG, sutun_sirasi=BOS_ARG):
    return _tocol_row(dizi, yoksay, sutun_sirasi, False)


def _sec(n: int, indisler) -> Optional[List[int]]:
    sonuc = []
    for v in indisler:
        k = _int(v, None)
        if isinstance(k, Hata) or k is None:
            return None
        if k == 0 or abs(k) > n:
            return None
        sonuc.append(k - 1 if k > 0 else n + k)
    return sonuc


@fonksiyon("CHOOSEROWS", en_az=2, en_cok=255)
def _chooserows(b, dizi, *indisler):
    h = _argumanlar_hata(dizi, *indisler)
    if h:
        return h
    m = _mat(dizi)
    idx = _sec(len(m), indisler)
    return D.DEGER_HATASI if idx is None else _dizi([m[i] for i in idx])


@fonksiyon("CHOOSECOLS", en_az=2, en_cok=255)
def _choosecols(b, dizi, *indisler):
    h = _argumanlar_hata(dizi, *indisler)
    if h:
        return h
    m = _mat(dizi)
    idx = _sec(len(m[0]), indisler)
    return D.DEGER_HATASI if idx is None else _dizi([[s[j] for j in idx] for s in m])


@fonksiyon("EXPAND", en_az=2, en_cok=4)
def _expand(b, dizi, satirlar, sutunlar=BOS_ARG, doldur=BOS_ARG):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    m = _mat(dizi)
    r, c = _int(satirlar, len(m)), _int(sutunlar, len(m[0]))
    for x in (r, c):
        if isinstance(x, Hata):
            return x
    if r < len(m) or c < len(m[0]):
        return D.DEGER_HATASI
    dolgu = D.YOK if doldur is BOS_ARG else ham(doldur)
    sonuc = []
    for i in range(r):
        satir = list(m[i]) if i < len(m) else []
        sonuc.append(satir + [dolgu] * (c - len(satir)))
    return _dizi(sonuc)


@fonksiyon("TRANSPOSE", en_az=1, en_cok=1)
def _transpose(b, dizi):
    h = _argumanlar_hata(dizi)
    if h:
        return h
    return _dizi(_devrik(_mat(dizi)))


@fonksiyon("LET", en_az=3, en_cok=253, tembel=True)
def _let_kaydi(b, *args):
    """Yalnız kayıt (adı/argüman sayısı bilinsin, `#AD?` çıkmasın): gerçek değerlendirme `degerlendir._let`te çünkü ad
    düğümlerinin ham halini ister."""
    return D.DEGER_HATASI
