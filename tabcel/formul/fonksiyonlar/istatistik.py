"""İstatistik fonksiyonları. Qt yok."""
import math
from collections import Counter

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, Dizi
from ..donustur import sayi_metninden
from . import fonksiyon
from .matematik import eslesen_konumlar, sayilari_topla
from .ortak import kriter, olcut_yayar
from .temel import sayilar


def _liste(args):
    """sayilar(args) → (liste, ilk hata | None)."""
    cikti = []
    for v in sayilar(args):
        if isinstance(v, Hata):
            return None, v
        cikti.append(v)
    return cikti, None


@fonksiyon("AVERAGE", en_az=1, en_cok=255)
def _average(b, *args):
    if len(args) == 1 and isinstance(args[0], AralikDeger):          # sıcak yol
        t, n, hata = args[0].toplam()
        if hata is not None:
            return hata
        return t / n if n else D.BOL0
    liste, hata = _liste(args)
    if hata is not None:
        return hata
    return math.fsum(liste) / len(liste) if liste else D.BOL0


@fonksiyon("MAX", en_az=1, en_cok=255)
def _max(b, *args):
    liste, hata = _liste(args)
    return hata if hata is not None else (max(liste) if liste else 0.0)


@fonksiyon("MIN", en_az=1, en_cok=255)
def _min(b, *args):
    liste, hata = _liste(args)
    return hata if hata is not None else (min(liste) if liste else 0.0)


@fonksiyon("MEDIAN", en_az=1, en_cok=255)
def _median(b, *args):
    liste, hata = _liste(args)
    if hata is not None:
        return hata
    if not liste:
        return D.SAYI
    liste.sort()
    n = len(liste)
    return liste[n // 2] if n % 2 else (liste[n // 2 - 1] + liste[n // 2]) / 2


@fonksiyon("MODE", en_az=1, en_cok=255)
def _mode(b, *args):
    liste, hata = _liste(args)
    if hata is not None:
        return hata
    if not liste:
        return D.YOK
    sayac = Counter(liste)
    en = max(sayac.values())
    if en < 2:
        return D.YOK
    return next(x for x in liste if sayac[x] == en)           # ilk görünen


def _varyans(args, ornek=True):
    liste, hata = _liste(args)
    if hata is not None:
        return hata
    n = len(liste)
    if n < (2 if ornek else 1):
        return D.BOL0
    ort = math.fsum(liste) / n
    return math.fsum((x - ort) ** 2 for x in liste) / (n - 1 if ornek else n)


@fonksiyon("VAR", en_az=1, en_cok=255)
def _var(b, *args):
    return _varyans(args)


@fonksiyon("STDEV", en_az=1, en_cok=255)
def _stdev(b, *args):
    v = _varyans(args)
    return v if isinstance(v, Hata) else math.sqrt(v)


def _sirali_k(dizi, k, buyuk):
    liste, hata = _liste([dizi])
    if hata is not None:
        return hata
    k = ham_sayi(k)
    if isinstance(k, Hata):
        return k
    k = math.ceil(k)
    if not liste or k < 1 or k > len(liste):
        return D.SAYI
    liste.sort(reverse=buyuk)
    return liste[k - 1]


def ham_sayi(v):
    from ..donustur import sayiya
    from .ortak import ham
    return sayiya(ham(v))


@fonksiyon("LARGE", en_az=2, en_cok=2)
def _large(b, dizi, k):
    return _sirali_k(dizi, k, True)


@fonksiyon("SMALL", en_az=2, en_cok=2)
def _small(b, dizi, k):
    return _sirali_k(dizi, k, False)


@fonksiyon("RANK", en_az=2, en_cok=3)
def _rank(b, sayi, baslik, sira=None):
    x = ham_sayi(sayi)
    if isinstance(x, Hata):
        return x
    if not isinstance(baslik, (AralikDeger, Dizi)):
        return D.DEGER_HATASI
    liste, hata = _liste([baslik])
    if hata is not None:
        return hata
    artan = False
    if sira is not None and sira is not BOS_ARG:
        sr = ham_sayi(sira)
        if isinstance(sr, Hata):
            return sr
        artan = sr != 0
    if x not in liste:
        return D.YOK
    return float(1 + sum(1 for v in liste if (v < x if artan else v > x)))


# --- sayma ---
def _sayidir(v) -> bool:
    return isinstance(v, float) and not isinstance(v, bool)


@fonksiyon("COUNT", en_az=1, en_cok=255)
def _count(b, *args):
    n = 0
    for a in args:
        if isinstance(a, AralikDeger):
            n += sum(1 for v in a.dolu_degerler() if _sayidir(v))
        elif isinstance(a, Dizi):
            n += sum(1 for v in a.degerler() if _sayidir(v))
        elif a is BOS_ARG or isinstance(a, bool):
            n += 1
        elif _sayidir(a):
            n += 1
        elif isinstance(a, str) and sayi_metninden(a) is not None:
            n += 1
    return float(n)


@fonksiyon("COUNTA", en_az=1, en_cok=255)
def _counta(b, *args):
    n = 0
    for a in args:
        if isinstance(a, AralikDeger):
            n += sum(1 for v in a.dolu_degerler() if v is not None)
        elif isinstance(a, Dizi):
            n += sum(1 for v in a.degerler() if v is not None)
        else:
            n += 1
    return float(n)


@fonksiyon("COUNTBLANK", en_az=1, en_cok=1)
def _countblank(b, aralik):
    if not isinstance(aralik, AralikDeger):
        return D.DEGER_HATASI
    toplam = aralik.satir_sayisi * aralik.sutun_sayisi
    dolu = sum(1 for v in aralik.dolu_degerler() if v is not None and v != "")
    return float(toplam - dolu)


@fonksiyon("COUNTIF", en_az=2, en_cok=2)
@olcut_yayar(lambda n: range(1, 2))
def _countif(b, aralik, olcut):
    if not isinstance(aralik, AralikDeger):
        return D.DEGER_HATASI
    s = kriter(olcut)
    if not s(None):                                     # boş hücreler eşleşmez → yalnız dolulara bak
        return float(sum(1 for v in aralik.dolu_degerler() if s(v)))
    k = eslesen_konumlar([aralik], [olcut])
    return float(len(k))


@fonksiyon("COUNTIFS", en_az=2, en_cok=254)
@olcut_yayar(lambda n: range(1, n, 2))
def _countifs(b, *cift):
    if len(cift) % 2:
        return D.DEGER_HATASI
    k = eslesen_konumlar(list(cift[0::2]), list(cift[1::2]))
    return k if isinstance(k, Hata) else float(len(k))


@fonksiyon("AVERAGEIF", en_az=2, en_cok=3)
@olcut_yayar(lambda n: range(1, 2))
def _averageif(b, aralik, olcut, ortalama=None):
    if ortalama is BOS_ARG:
        ortalama = None
    if not isinstance(aralik, AralikDeger) or (
            ortalama is not None and not isinstance(ortalama, AralikDeger)):
        return D.DEGER_HATASI
    k = eslesen_konumlar([aralik], [olcut])
    if isinstance(k, Hata):
        return k
    s = sayilari_topla(ortalama or aralik, k)
    if isinstance(s, Hata):
        return s
    return math.fsum(s) / len(s) if s else D.BOL0


@fonksiyon("AVERAGEIFS", en_az=3, en_cok=255)
@olcut_yayar(lambda n: range(2, n, 2))
def _averageifs(b, ortalama, *cift):
    if len(cift) % 2:
        return D.DEGER_HATASI
    k = eslesen_konumlar(list(cift[0::2]), list(cift[1::2]), ortalama)
    if isinstance(k, Hata):
        return k
    s = sayilari_topla(ortalama, k)
    if isinstance(s, Hata):
        return s
    return math.fsum(s) / len(s) if s else D.BOL0


def _ifs_uc(ad, islev):
    @fonksiyon(ad, en_az=3, en_cok=255)
    @olcut_yayar(lambda n: range(2, n, 2))
    def _f(b, hedef, *cift):
        if len(cift) % 2:
            return D.DEGER_HATASI
        k = eslesen_konumlar(list(cift[0::2]), list(cift[1::2]), hedef)
        if isinstance(k, Hata):
            return k
        s = sayilari_topla(hedef, k)
        if isinstance(s, Hata):
            return s
        return islev(s) if s else 0.0
    return _f


_ifs_uc("MAXIFS", max)
_ifs_uc("MINIFS", min)


# --- ALTTOPLAM (SUBTOTAL) — faz5_tasarim.md §6.4 ---------------------------------------------
def _gizli_dislanir(sayfa, r: int, tum_gizli: bool) -> bool:
    """101–111: her gizli satır dışlanır. 1–11: yalnız filtreyle gizlenenler (filtre veri aralığında
    gizli satır; model gizliliği tek bit tutar — Excel gibi)."""
    if r not in sayfa.gizli_satir:
        return False
    if tum_gizli:
        return True
    f = sayfa.filtre
    return f is not None and f.aralik.ilk_satir < r <= f.aralik.son_satir


def _gorunen_dizi(a: AralikDeger, tum_gizli: bool) -> Dizi:
    """Aralığın dışlanmayan satırlarındaki değerler (başka ALTTOPLAM hücreleri sayılmaz)."""
    r1, c1, r2, c2 = a.kirpilmis()
    sayfa, hucreler = a.sayfa, a.sayfa._hucreler
    degerler = []
    for r in range(r1, r2 + 1):
        if _gizli_dislanir(sayfa, r, tum_gizli):
            continue
        for c in range(c1, c2 + 1):
            h = hucreler.get((r, c))
            if h is not None and h.formul is not None and "SUBTOTAL(" in h.formul.upper():
                continue
            degerler.append(a.hucre_degeri(r, c))
    return Dizi([degerler]) if degerler else Dizi([[]])


_ALTTOPLAM_ISLEV = {1: "AVERAGE", 2: "COUNT", 3: "COUNTA", 4: "MAX", 5: "MIN", 6: "PRODUCT",
                    7: "STDEV", 8: "STDEVP", 9: "SUM", 10: "VAR", 11: "VARP"}


@fonksiyon("SUBTOTAL", en_az=2, en_cok=255, gizlilik=True)
def _subtotal(b, no, *args):
    from ..donustur import sayiya
    from ..degerler import skalere
    n = sayiya(skalere(no, b.satir, b.sutun))
    if isinstance(n, Hata):
        return n
    n = int(n)
    tum_gizli = 101 <= n <= 111
    ad = _ALTTOPLAM_ISLEV.get(n - 100 if tum_gizli else n)
    if ad is None:
        return D.DEGER_HATASI
    veri = [_gorunen_dizi(a, tum_gizli) if isinstance(a, AralikDeger) else a for a in args]
    if ad == "STDEVP":
        v = _varyans(veri, ornek=False)
        return v if isinstance(v, Hata) else math.sqrt(v)
    if ad == "VARP":
        return _varyans(veri, ornek=False)
    from . import KAYIT
    return KAYIT[ad].uygula(b, *veri)
