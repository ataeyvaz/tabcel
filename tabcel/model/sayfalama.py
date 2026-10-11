"""Yazdırma için sayfalara bölme (Faz 4 / 4d). Qt yok.

Excel gibi: sayfalar önce **aşağı**, sonra **sağa** doğru numaralanır; gizli satır/sütun yazdırılmaz; başlık
satırları ilk sayfa dışındaki satır dilimlerinin başına yinelenir; tek bir satır/sütun sayfadan büyükse
kendi sayfasına tek başına konur (kırpılır). Ölçüler 96 dpi pikseldir (ızgara pikseliyle aynı).
"""
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .adres import MAX_COL, MAX_ROW, Aralik
from .sayfa import Sayfa
from .sayfa_yapisi import SayfaYapisi


@dataclass(frozen=True)
class SayfaDilimi:
    satirlar: Tuple[int, ...]        # çizilecek satırlar (başlık satırları dahil, sırayla)
    sutunlar: Tuple[int, ...]
    olcek: float                     # uygulanan ölçek (1.0 = %100)
    no: int                          # 1'den
    toplam: int
    baslik_sayisi: int = 0           # `satirlar` başındaki yinelenen başlık satırı sayısı


def nesne_son_hucre(n, genislik: Callable[[int], float], yukseklik: Callable[[int], float]) -> Tuple[int, int]:
    """Nesnenin (grafik/resim) sağ alt ucunun düştüğü `(satır, sütun)`; ölçüler 100% pikseldir."""
    k = n.konum
    kalan = k.dx + n.boyut[0]
    c = k.sutun
    while c < MAX_COL and kalan > genislik(c):
        kalan -= genislik(c)
        c += 1
    kalan = k.dy + n.boyut[1]
    r = k.satir
    while r < MAX_ROW and kalan > yukseklik(r):
        kalan -= yukseklik(r)
        r += 1
    return r, c


def yazdirma_alani(sayfa: Sayfa, yapi: SayfaYapisi, genislik: Optional[Callable[[int], float]] = None,
                   yukseklik: Optional[Callable[[int], float]] = None) -> Optional[Aralik]:
    """Yazdırma alanı: ayarlanmışsa o, yoksa içerik + biçimli hücreleri **ve nesneleri** kapsayan alan; boşsa None.
    Nesne sınırı için ölçü işlevleri gerekir (verilmezse nesneler yok sayılır)."""
    if yapi.alan is not None:
        return yapi.alan
    k = sayfa.kullanilan_aralik(bicim_dahil=True)
    r1 = c1 = r2 = c2 = None
    if k is not None:
        r1, c1, r2, c2 = k
        # birleşimlerin taştığı uçlar da alana dahil olsun
        for b in sayfa.birlesimler:
            r2, c2 = max(r2, b.son_satir), max(c2, b.son_sutun)
    if genislik is not None and yukseklik is not None:
        for n in sayfa.nesneler:
            nr, nc = nesne_son_hucre(n, genislik, yukseklik)
            if r1 is None:
                r1, c1, r2, c2 = n.konum.satir, n.konum.sutun, nr, nc
            else:
                r1, c1 = min(r1, n.konum.satir), min(c1, n.konum.sutun)
                r2, c2 = max(r2, nr), max(c2, nc)
    if r1 is None:
        return None
    return Aralik(r1, c1, min(r2, MAX_ROW), min(c2, MAX_COL))


def _bol(boyutlar: List[Tuple[int, float]], sinir: float, ayrilan: float = 0.0,
         kesmeler: frozenset = frozenset()) -> List[List[int]]:
    """Sıralı (indeks, boyut) listesini `sinir` boyutlu dilimlere böler; ilk dilimden sonrakilerde `ayrilan`
    boyut (yinelenen başlık) düşülür. `kesmeler`: yeni dilimin BAŞLADIĞI indeksler (el ile sayfa sonu). Her
    dilimde en az bir öğe vardır."""
    dilimler: List[List[int]] = []
    sim: List[int] = []
    toplam = 0.0
    for i, b in boyutlar:
        kapasite = sinir - (ayrilan if dilimler else 0.0)
        if sim and (i in kesmeler or toplam + b > kapasite + 1e-6):
            dilimler.append(sim)
            sim, toplam = [], 0.0
        sim.append(i)
        toplam += b
    if sim:
        dilimler.append(sim)
    return dilimler


@dataclass(frozen=True)
class _Plan:
    alan: Aralik
    olcek: float
    satir_dilimleri: List[List[int]]
    sutun_dilimleri: List[List[int]]
    baslik: List[int]
    kesmeler_uygulandi: bool


def _plan(sayfa: Sayfa, yapi: SayfaYapisi, genislik: Callable[[int], float],
          yukseklik: Callable[[int], float]) -> Optional[_Plan]:
    alan = yazdirma_alani(sayfa, yapi, genislik, yukseklik)
    if alan is None:
        return None
    sutunlar = [(c, genislik(c)) for c in range(alan.ilk_sutun, alan.son_sutun + 1) if genislik(c) > 0]
    satirlar = [(r, yukseklik(r)) for r in range(alan.ilk_satir, alan.son_satir + 1) if yukseklik(r) > 0]
    if not sutunlar or not satirlar:
        return None
    pg, py = yapi.yazdirilabilir_px()
    sigdir = yapi.sigdir_genislik or yapi.sigdir_yukseklik
    if sigdir:
        olcek = 1.0
        if yapi.sigdir_genislik:
            toplam_g = sum(b for _, b in sutunlar)
            olcek = min(olcek, pg / toplam_g) if toplam_g > 0 else olcek
        if yapi.sigdir_yukseklik:
            toplam_y = sum(b for _, b in satirlar)
            olcek = min(olcek, py / toplam_y) if toplam_y > 0 else olcek
        olcek = max(olcek, 0.1)
    else:
        olcek = yapi.olcek / 100.0
    sg, sy = pg / olcek, py / olcek                    # sayfa üzerindeki sayfa-alanı boyutu (ölçeksiz piksel)
    baslik: List[int] = []
    baslik_yuk = 0.0
    if yapi.baslik_satirlari is not None:
        a, b = yapi.baslik_satirlari
        baslik = [r for r in range(a, b + 1) if yukseklik(r) > 0]
        baslik_yuk = sum(yukseklik(r) for r in baslik)
        if baslik_yuk >= sy:                           # başlık sayfayı doldurur: yinelenmez
            baslik, baslik_yuk = [], 0.0
    # Excel: "sığdır" seçiliyse el ile sayfa sonları yok sayılır
    kesme_var = not sigdir and bool(yapi.satir_kesmeleri or yapi.sutun_kesmeleri)
    satir_k = frozenset(yapi.satir_kesmeleri) if not sigdir else frozenset()
    sutun_k = frozenset(yapi.sutun_kesmeleri) if not sigdir else frozenset()
    # başlık satırları alanın içindeyse ilk dilimde zaten vardır; yinelemede tekrar eklenmez
    return _Plan(alan, olcek, _bol(satirlar, sy, baslik_yuk, satir_k), _bol(sutunlar, sg, 0.0, sutun_k),
                 baslik, kesme_var)


def sayfala(sayfa: Sayfa, yapi: SayfaYapisi, genislik: Callable[[int], float],
            yukseklik: Callable[[int], float]) -> List[SayfaDilimi]:
    """Sayfa dilimlerini üretir. `genislik(c)` / `yukseklik(r)` 100% pikseldir (gizli → 0)."""
    pl = _plan(sayfa, yapi, genislik, yukseklik)
    if pl is None:
        return []
    toplam = len(pl.satir_dilimleri) * len(pl.sutun_dilimleri)
    sonuc: List[SayfaDilimi] = []

    def dilim(sut, sat, k, no):
        cizilecek = list(sat)
        if k > 0 and pl.baslik:
            cizilecek = [r for r in pl.baslik if r not in sat] + cizilecek
        return SayfaDilimi(tuple(cizilecek), tuple(sut), pl.olcek, no, toplam, len(cizilecek) - len(sat))

    no = 0
    if yapi.sayfa_sirasi == "sag_sonra_asagi":         # önce sağa, sonra aşağı
        for k, sat in enumerate(pl.satir_dilimleri):
            for sut in pl.sutun_dilimleri:
                no += 1
                sonuc.append(dilim(sut, sat, k, no))
    else:                                              # Excel varsayılanı: önce aşağı, sonra sağa
        for sut in pl.sutun_dilimleri:
            for k, sat in enumerate(pl.satir_dilimleri):
                no += 1
                sonuc.append(dilim(sut, sat, k, no))
    return sonuc


@dataclass(frozen=True)
class SayfaSinirlari:
    """Ekranda gösterilecek sayfa sınırları: `satirlar`/`sutunlar` = ((indeks, el_ile), …); çizgi ilgili
    satırın/sütunun ÖNÜNDEDİR (yeni sayfa o satırda/sütunda başlar). `alan`: çizgilerin uzanacağı yazdırma alanı."""
    satirlar: Tuple[Tuple[int, bool], ...]
    sutunlar: Tuple[Tuple[int, bool], ...]
    alan: Aralik


def sayfa_sinirlari(sayfa: Sayfa, yapi: SayfaYapisi, genislik: Callable[[int], float],
                    yukseklik: Callable[[int], float]) -> Optional[SayfaSinirlari]:
    """`sayfala` ile AYNI bölme kodundan: ekran çizgileri ile yazdırma çıktısı tutarsız olamaz."""
    pl = _plan(sayfa, yapi, genislik, yukseklik)
    if pl is None:
        return None
    sk, uk = set(yapi.satir_kesmeleri), set(yapi.sutun_kesmeleri)
    sat = tuple((d[0], d[0] in sk and pl.kesmeler_uygulandi) for d in pl.satir_dilimleri[1:])
    sut = tuple((d[0], d[0] in uk and pl.kesmeler_uygulandi) for d in pl.sutun_dilimleri[1:])
    return SayfaSinirlari(sat, sut, pl.alan)
