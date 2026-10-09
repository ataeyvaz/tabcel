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


def yazdirma_alani(sayfa: Sayfa, yapi: SayfaYapisi) -> Optional[Aralik]:
    """Yazdırma alanı: ayarlanmışsa o, yoksa içerik + biçimli hücreleri kapsayan alan; sayfa boşsa None."""
    if yapi.alan is not None:
        return yapi.alan
    k = sayfa.kullanilan_aralik(bicim_dahil=True)
    if k is None:
        return None
    # birleşimlerin taştığı uçlar da alana dahil olsun
    r1, c1, r2, c2 = k
    for b in sayfa.birlesimler:
        r2, c2 = max(r2, b.son_satir), max(c2, b.son_sutun)
    return Aralik(r1, c1, min(r2, MAX_ROW), min(c2, MAX_COL))


def _bol(boyutlar: List[Tuple[int, float]], sinir: float, ayrilan: float = 0.0) -> List[List[int]]:
    """Sıralı (indeks, boyut) listesini `sinir` boyutlu dilimlere böler; ilk dilimden sonrakilerde `ayrilan`
    boyut (yinelenen başlık) düşülür. Her dilimde en az bir öğe vardır."""
    dilimler: List[List[int]] = []
    sim: List[int] = []
    toplam = 0.0
    for i, b in boyutlar:
        kapasite = sinir - (ayrilan if dilimler else 0.0)
        if sim and toplam + b > kapasite + 1e-6:
            dilimler.append(sim)
            sim, toplam = [], 0.0
        sim.append(i)
        toplam += b
    if sim:
        dilimler.append(sim)
    return dilimler


def sayfala(sayfa: Sayfa, yapi: SayfaYapisi, genislik: Callable[[int], float],
            yukseklik: Callable[[int], float]) -> List[SayfaDilimi]:
    """Sayfa dilimlerini üretir. `genislik(c)` / `yukseklik(r)` 100% pikseldir (gizli → 0)."""
    alan = yazdirma_alani(sayfa, yapi)
    if alan is None:
        return []
    sutunlar = [(c, genislik(c)) for c in range(alan.ilk_sutun, alan.son_sutun + 1) if genislik(c) > 0]
    satirlar = [(r, yukseklik(r)) for r in range(alan.ilk_satir, alan.son_satir + 1) if yukseklik(r) > 0]
    if not sutunlar or not satirlar:
        return []
    pg, py = yapi.yazdirilabilir_px()
    if yapi.sigdir_genislik:
        toplam_g = sum(b for _, b in sutunlar)
        olcek = min(1.0, pg / toplam_g) if toplam_g > 0 else 1.0
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
    # başlık satırları alanın içindeyse ilk dilimde zaten vardır; yinelemede tekrar eklenmez
    satir_dilimleri = _bol(satirlar, sy, baslik_yuk)
    sutun_dilimleri = _bol(sutunlar, sg)
    toplam = len(satir_dilimleri) * len(sutun_dilimleri)
    sonuc: List[SayfaDilimi] = []
    no = 0
    for sut in sutun_dilimleri:                        # Excel varsayılanı: önce aşağı, sonra sağa
        for k, sat in enumerate(satir_dilimleri):
            cizilecek = list(sat)
            if k > 0 and baslik:
                cizilecek = [r for r in baslik if r not in sat] + cizilecek
            no += 1
            sonuc.append(SayfaDilimi(tuple(cizilecek), tuple(sut), olcek, no, toplam))
    return sonuc
