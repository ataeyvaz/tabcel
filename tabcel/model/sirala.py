"""Sıralama planı (faz5_tasarim.md §3.1). Qt yok.

`siralama_plani` hangi kaynak satırın (sütunun) hangi konuma gideceğini hesaplar; hücreleri taşıyan
komut `komutlar.Sirala`'dır.
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .adres import Aralik
from .harmanla import deger_anahtari

HATA_BIRLESIM = "Bunu yapmak için tüm birleştirilmiş hücrelerin aynı boyutta olması gerekir."


@dataclass(frozen=True)
class SiralamaAnahtari:
    """`sutun`: mutlak sütun (`yon="sutun"` sıralamasında mutlak satır). `olcut`: "deger" | "dolgu" |
    "yazi_rengi"; renk ölçütünde `renk` ('#rrggbb') olan hücreler `artan` ise üstte, değilse altta."""
    sutun: int
    artan: bool = True
    olcut: str = "deger"
    renk: Optional[str] = None


def veri_kutusu(sayfa, aralik: Aralik) -> Optional[Aralik]:
    """Aralığı sayfanın kullanılan alanıyla kırpar (tam sütun/satır seçimi 1 milyon satır olmasın)."""
    kul = sayfa.kullanilan_aralik()
    if kul is None:
        return None
    r1, c1 = max(aralik.ilk_satir, kul[0]), max(aralik.ilk_sutun, kul[1])
    r2, c2 = min(aralik.son_satir, kul[2]), min(aralik.son_sutun, kul[3])
    if r1 > r2 or c1 > c2:
        return None
    return Aralik(r1, c1, r2, c2)


def baslik_tahmin(sayfa, aralik: Aralik) -> bool:
    """Excel'in "Verilerim üst bilgi içeriyor" sezgisi (yaklaşık; §8b-60): ilk satır bir sütunda metin,
    altındaki hücre metin değil dolu ise ya da ilk satırın biçimi (kalın/dolgu) ikinci satırdan farklıysa."""
    if aralik.son_satir <= aralik.ilk_satir:
        return False
    r1, r2 = aralik.ilk_satir, aralik.ilk_satir + 1
    for c in range(aralik.ilk_sutun, aralik.son_sutun + 1):
        a, b = sayfa.deger(r1, c), sayfa.deger(r2, c)
        if isinstance(a, str) and b is not None and not isinstance(b, str):
            return True
        sa, sb = sayfa.stil(r1, c), sayfa.stil(r2, c)
        if sayfa.hucre(r1, c) is not None and (sa.kalin != sb.kalin or sa.dolgu != sb.dolgu):
            return True
    return False


def _renk(sayfa, r: int, c: int, olcut: str) -> Optional[str]:
    st = sayfa.stil(r, c)
    return st.dolgu if olcut == "dolgu" else st.yazi_rengi


def siralama_plani(sayfa, aralik: Aralik, anahtarlar: Sequence[SiralamaAnahtari], baslik: bool = False,
                   buyuk_kucuk: bool = False, yon: str = "satir") -> List[int]:
    """Sıralama sonrası konum → kaynak eşlemesi: `plan[i]` = veri aralığının `i`. konumuna (başlık
    atlanır) gelecek KAYNAK satırın (yon="sutun" ise sütunun) mutlak numarası. Sıralama kararlıdır;
    çok düzey tek bileşik anahtardır. Gizli satırlar (sütunlar) yerinde kalır, yalnız görünenler yer
    değiştirir. Aralık birleşim kesiyorsa ValueError. Anahtar sütunu aralık dışındaysa ValueError."""
    if not anahtarlar:
        raise ValueError("Sıralama ölçütü yok")
    if sayfa.birlesim_kesisen(aralik):
        raise ValueError(HATA_BIRLESIM)
    satir_yonu = yon == "satir"
    ilk, son = (aralik.ilk_satir, aralik.son_satir) if satir_yonu else (aralik.ilk_sutun, aralik.son_sutun)
    if baslik:
        ilk += 1
    if ilk > son:
        return []
    diger_ilk, diger_son = (aralik.ilk_sutun, aralik.son_sutun) if satir_yonu else (aralik.ilk_satir, aralik.son_satir)
    for a in anahtarlar:
        if not diger_ilk <= a.sutun <= diger_son:
            raise ValueError("Sıralama ölçütü seçili aralığın dışında")
    gizli = sayfa.gizli_satir if satir_yonu else sayfa.gizli_sutun
    gorunen = [k for k in range(ilk, son + 1) if k not in gizli]

    def hucre_degeri(k: int, a: SiralamaAnahtari):
        return sayfa.deger(k, a.sutun) if satir_yonu else sayfa.deger(a.sutun, k)

    def anahtar(k: int):
        parca = []
        for a in anahtarlar:
            if a.olcut == "deger":
                parca.append(deger_anahtari(hucre_degeri(k, a), a.artan, buyuk_kucuk))
            else:
                r, c = (k, a.sutun) if satir_yonu else (a.sutun, k)
                renk = _renk(sayfa, r, c, a.olcut)
                eslesti = renk is not None and a.renk is not None and renk.upper() == a.renk.upper()
                parca.append(0 if eslesti == a.artan else 1)      # artan: seçilen renk üstte; azalan: altta
        return tuple(parca)

    sirali = sorted(gorunen, key=anahtar)
    plan = list(range(ilk, son + 1))
    for hedef, kaynak in zip(gorunen, sirali):
        plan[hedef - ilk] = kaynak
    return plan
