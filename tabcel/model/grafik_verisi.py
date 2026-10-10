"""Grafik verisi: başvurulardan sayı/etiket çözümleme ve seçili aralıktan seri tahmini (Faz 6 / 6b;
`faz6_tasarim.md` §3). Qt yok.

Kurallar (Excel'e göre; Excel'de doğrulanacak olanlar `surec.md` §8b'de):
- değer: sayı → float; boş hücre → None (çizgide boşluk); metin/mantıksal → 0; hata değeri → None
- **gizli satır/sütun çizilmez** (filtreyle gizlenenler dahil)
- kategori etiketi = hücrenin görünen metni (sayı biçimi uygulanmış); tarihler metin kategorisidir
"""
import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from .adres import Aralik, bitisik_bolge
from .bul import gorunen_metin
from .deger import Hata
from .grafik import Grafik, Referans, Seri
from .sayi_bicimi import BicimHatasi, kod_coz


# ------------------------------------------------------------------ veri nesneleri
class EtiketDizisi(Sequence):
    """Kategori etiketleri, **tembel**: 100.000 noktalı seride yalnızca çizimde gerekenler biçimlenir
    (sayı biçimi çözümü pahalıdır). Erişilen etiket önbelleğe alınır."""

    def __init__(self, uretici: Callable[[int], str], n: int):
        self._uretici, self._n, self._onb = uretici, n, {}

    def __len__(self) -> int:
        return self._n

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[k] for k in range(*i.indices(self._n))]
        if i < 0:
            i += self._n
        if not 0 <= i < self._n:
            raise IndexError(i)
        e = self._onb.get(i)
        if e is None:
            e = self._onb[i] = self._uretici(i)
        return e

    def __eq__(self, diger) -> bool:
        try:
            return list(self) == list(diger)
        except TypeError:
            return NotImplemented

    __hash__ = None


@dataclass(frozen=True)
class SeriVerisi:
    ad: str
    degerler: Tuple[Optional[float], ...]
    kategoriler: Sequence                      # `n` etiket (EtiketDizisi ya da liste); dağılımda boş metinler
    x: Optional[Tuple[Optional[float], ...]]   # yalnız dağılım: X değerleri (kategori yoksa 1, 2, 3…)
    renk: Optional[str]


@dataclass(frozen=True)
class GrafikVerisi:
    seriler: Tuple[SeriVerisi, ...]
    sayi_bicimi: str = "General"               # değer ekseni/etiketler için ("kaynağa bağlı": ilk biçimli hücre)

    @property
    def bos(self) -> bool:
        return not self.seriler or all(all(v is None for v in s.degerler) for s in self.seriler)


# ------------------------------------------------------------------ aralık → hücre listesi
def hucre_listesi(sayfa, aralik: Aralik, gizliyi_atla: bool = True) -> List[Tuple[int, int]]:
    """Aralığın hücreleri çizim sırasıyla: tek satırsa soldan sağa, aksi halde satır satır (tek sütun yukarıdan
    aşağı). Aralık kullanılan alanın dışına taşıyorsa (tam sütun/satır) kullanılan alana kırpılır; gizli satır/
    sütun atlanır."""
    kul = sayfa.kullanilan_aralik()
    if kul is None:
        return []
    r1, c1 = aralik.ilk_satir, aralik.ilk_sutun
    r2, c2 = min(aralik.son_satir, kul[2]), min(aralik.son_sutun, kul[3])
    if r2 < r1 or c2 < c1:
        return []
    satirlar = [r for r in range(r1, r2 + 1) if not (gizliyi_atla and r in sayfa.gizli_satir)]
    sutunlar = [c for c in range(c1, c2 + 1) if not (gizliyi_atla and c in sayfa.gizli_sutun)]
    return [(r, c) for r in satirlar for c in sutunlar]


def _sayiya(v) -> Optional[float]:
    """Grafik değeri: sayı → float, boş/hata → None, metin/mantıksal → 0."""
    if v is None or isinstance(v, Hata):
        return None
    if isinstance(v, bool) or isinstance(v, str):
        return 0.0
    if isinstance(v, (int, float)):
        f = float(v)
        return f if math.isfinite(f) else None
    return 0.0


def _x_sayisi(v) -> Optional[float]:
    """Dağılım X değeri: yalnız gerçek sayılar (metin → None; hepsi None ise 1, 2, 3…'e dönülür)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def _sayfa(kitap, ref: Optional[Referans]):
    if ref is None or kitap is None:
        return None
    return kitap.sayfa_kimlikle(ref.sayfa_kimlik)


def _ad(kitap, seri: Seri, n: int) -> str:
    sayfa = _sayfa(kitap, seri.ad_ref)
    if sayfa is not None:
        a = seri.ad_ref.aralik
        m = gorunen_metin(sayfa, a.ilk_satir, a.ilk_sutun)      # gizli olsa da başlık hücresi okunur
        if m:
            return m
    if seri.ad:
        return seri.ad
    return f"Seri{n}"


def grafik_verisi(kitap, grafik: Grafik) -> GrafikVerisi:
    """Grafiğin başvurularını çözer. Değer başvurusu olmayan ya da sayfası silinmiş seri atlanır."""
    cikan: List[SeriVerisi] = []
    bicim = "General"
    for sira, s in enumerate(grafik.seriler, start=1):
        sayfa = _sayfa(kitap, s.deger)
        if sayfa is None:
            continue
        hucreler = hucre_listesi(sayfa, s.deger.aralik)
        degerler = tuple(_sayiya(sayfa.deger(r, c)) for r, c in hucreler)
        if bicim == "General":
            for r, c in hucreler:
                kod = sayfa.stil(r, c).sayi_bicimi
                if kod and kod != "General" and sayfa.deger(r, c) is not None:
                    bicim = kod
                    break
        n = len(degerler)
        kat_sayfa = _sayfa(kitap, s.kategori)
        kat_hucreler = hucre_listesi(kat_sayfa, s.kategori.aralik) if kat_sayfa is not None else []
        x = None
        if grafik.tur == "dagilim":
            xs = tuple(_x_sayisi(kat_sayfa.deger(r, c)) for r, c in kat_hucreler[:n]) if kat_sayfa else ()
            if not xs or all(v is None for v in xs):
                x = tuple(float(i) for i in range(1, n + 1))                # X yoksa / sayısal değilse 1, 2, 3…
            else:
                x = tuple(xs) + tuple(None for _ in range(n - len(xs)))     # eksik X → nokta çizilmez
            kategoriler: Sequence = [""] * n
        elif kat_hucreler:
            def uret(i, sayfa_=kat_sayfa, liste=kat_hucreler):
                if i < len(liste):
                    m = gorunen_metin(sayfa_, *liste[i])
                    return m if m is not None else ""
                return str(i + 1)
            kategoriler = EtiketDizisi(uret, n)
        else:
            kategoriler = EtiketDizisi(lambda i: str(i + 1), n)
        cikan.append(SeriVerisi(_ad(kitap, s, sira), degerler, kategoriler, x, s.renk))
    return GrafikVerisi(tuple(cikan), bicim)


# ------------------------------------------------------------------ seri tahmini
def _sayi_mi(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _tarih_bicimi_mi(kod: str) -> bool:
    try:
        return bool(kod and kod != "General" and kod_coz(kod).tarih_mi)
    except BicimHatasi:
        return False


def seriler_tahmin(sayfa, aralik: Aralik, tur: str = "sutun",
                   satirda_seri: Optional[bool] = None) -> Tuple[List[Seri], bool]:
    """Seçili aralıktan seri başvurularını Excel sezgisiyle çıkarır; döner `(seriler, satirda_seri)`.

    - tek hücre seçiliyse bitişik bölge alınır; kullanılan alana kırpılır
    - **boyutu küçük olan eksen seridir** (sütun sayısı ≤ satır sayısı → seriler sütunlarda); `satirda_seri`
      verilirse o kullanılır ("Satır/Sütun Değiştir")
    - ilk sütun (serilerin yönünde) **kategori**: sol üst hücre boşsa, ilk sütunda metin varsa ya da tarih biçimliyse
      (dağılımda ilk sütun sayısalsa X değerleri)
    - ilk satır **başlık**: sol üst hücre boşsa ya da (kategori sütunu hariç) dolu hücrelerin hepsi metinse
    - hiç sayısal seri yoksa `ValueError("Seçili alanda çizilebilecek sayısal veri yok")`; pasta/halka yalnız ilk seri
    """
    yok = ValueError("Seçili alanda çizilebilecek sayısal veri yok")
    if (aralik.ilk_satir, aralik.ilk_sutun) == (aralik.son_satir, aralik.son_sutun):
        aralik = bitisik_bolge(sayfa, aralik.ilk_satir, aralik.ilk_sutun)
    kul = sayfa.kullanilan_aralik()
    if kul is None:
        raise yok
    r1, c1 = max(aralik.ilk_satir, kul[0]), max(aralik.ilk_sutun, kul[1])
    r2, c2 = min(aralik.son_satir, kul[2]), min(aralik.son_sutun, kul[3])
    if r2 < r1 or c2 < c1:
        raise yok
    nr, nc = r2 - r1 + 1, c2 - c1 + 1
    if satirda_seri is None:
        satirda_seri = nc > nr

    def hucre(i: int, j: int) -> Tuple[int, int]:
        """Görünüm (i. kategori satırı, j. seri sütunu) → sayfa hücresi; satırda seride eksenler yer değiştirir."""
        return (r1 + j, c1 + i) if satirda_seri else (r1 + i, c1 + j)

    n_kat = nc if satirda_seri else nr           # görünümdeki satır sayısı (kategori yönü)
    n_ser = nr if satirda_seri else nc           # görünümdeki sütun sayısı (seri yönü)

    def v(i, j):
        return sayfa.deger(*hucre(i, j))

    ust_bos = v(0, 0) is None
    ilk_sutun = [v(i, 0) for i in range(n_kat)]
    kat_var = False
    if n_ser > 1:
        if ust_bos or any(isinstance(x, str) for x in ilk_sutun[1:] or ilk_sutun):
            kat_var = True
        elif tur == "dagilim" and all(_sayi_mi(x) or x is None for x in ilk_sutun[1:]) and any(
                _sayi_mi(x) for x in ilk_sutun):
            kat_var = True                         # X değerleri
        elif all(_sayi_mi(x) or x is None for x in ilk_sutun[1:]) and any(
                _tarih_bicimi_mi(sayfa.stil(*hucre(i, 0)).sayi_bicimi) for i in range(1, n_kat) if _sayi_mi(ilk_sutun[i])):
            kat_var = True                         # tarih sütunu kategori (metin ekseni)
    j0 = 1 if kat_var else 0
    ilk_satir = [v(0, j) for j in range(j0, n_ser)]
    dolu = [x for x in ilk_satir if x is not None]
    altta_sayi = any(_sayi_mi(v(i, j)) for i in range(1, n_kat) for j in range(j0, n_ser))
    baslik = n_kat > 1 and altta_sayi and (
        (ust_bos and kat_var) or (bool(dolu) and all(isinstance(x, str) for x in dolu)))
    i0 = 1 if baslik else 0
    if i0 >= n_kat:
        raise yok

    def ref(i_a, i_b, j_a, j_b) -> Referans:
        (ra, ca), (rb, cb) = hucre(i_a, j_a), hucre(i_b, j_b)
        return Referans(sayfa.kimlik, Aralik(min(ra, rb), min(ca, cb), max(ra, rb), max(ca, cb)))

    kategori = ref(i0, n_kat - 1, 0, 0) if kat_var else None
    seriler: List[Seri] = []
    for j in range(j0, n_ser):
        if not any(_sayi_mi(v(i, j)) for i in range(i0, n_kat)):
            continue                               # sayısal değeri olmayan sütun/satır seri olmaz
        seriler.append(Seri(ad_ref=ref(0, 0, j, j) if baslik and v(0, j) is not None else None,
                            deger=ref(i0, n_kat - 1, j, j), kategori=kategori))
    if not seriler:
        raise yok
    if tur in ("pasta", "halka"):
        seriler = seriler[:1]
    return seriler, bool(satirda_seri)
