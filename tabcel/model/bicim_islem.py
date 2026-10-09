"""Biçim araç çubuğunun Qt'siz mantığı (Faz 3 / 3d): seçimden `StilYama` planları üretir.

Plan = `[(araliklar, StilYama), ...]`; ızgara her birini `bicim_komutu` ile komuta çevirir, hepsi tek
geri al adımı olur. Düğmelerin hangi yamayı ürettiği burada sınanır (ekransız).
"""
from typing import List, Optional, Sequence, Tuple

from .adres import Aralik
from .sayi_bicimi import HAZIR, BicimHatasi, ondalik_degistir
from .stil import Stil, StilYama

Plan = List[Tuple[Sequence[Aralik], StilYama]]

# Excel'in Yazı Tipi Boyutunu Büyüt/Küçült düğmelerinin kullandığı sıra
BOYUTLAR = (8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72)
VARSAYILAN_BOYUT = 11.0

# Sayı biçimi düğmeleri (kanonik kod). Binlik: Excel Ctrl+Shift+1 = "#,##0.00"; yüzde "0%"; para "₺"
YUZDE = "0%"
PARA = HAZIR["Para Birimi"]
BINLIK = HAZIR["Sayı (binlik ayraçlı)"]

KENAR_SECENEKLERI = ("alt", "ust", "sol", "sag", "tum", "dis", "kalin_dis", "cift_alt", "yok")
_SIYAH = "#000000"


def etkin_boyut(stil: Stil) -> float:
    return stil.boyut if stil.boyut else VARSAYILAN_BOYUT


def sonraki_boyut(boyut: float, yon: int) -> float:
    """Büyüt (+1) / Küçült (−1): listedeki bir sonraki / bir önceki boyut; uçlarda yerinde kalır."""
    if yon > 0:
        for b in BOYUTLAR:
            if b > boyut:
                return float(b)
        return float(BOYUTLAR[-1])
    for b in reversed(BOYUTLAR):
        if b < boyut:
            return float(b)
    return float(BOYUTLAR[0])


def boyut_coz(metin: str) -> Optional[float]:
    """Boyut kutusuna yazılan metin (`10,5` ya da `10.5`) → punto; geçersizse None (1–409)."""
    try:
        v = float(metin.strip().replace(",", "."))
    except ValueError:
        return None
    return v if 1 <= v <= 409 else None


def kalin_yamasi(stil: Stil) -> StilYama:
    return StilYama(kalin=not stil.kalin)


def italik_yamasi(stil: Stil) -> StilYama:
    return StilYama(italik=not stil.italik)


def alti_cizili_yamasi(stil: Stil) -> StilYama:
    return StilYama(alti_cizili="yok" if stil.alti_cizili != "yok" else "tek")


def ustu_cizili_yamasi(stil: Stil) -> StilYama:
    return StilYama(ustu_cizili=not stil.ustu_cizili)


def kaydir_yamasi(stil: Stil) -> StilYama:
    return StilYama(kaydir=not stil.kaydir)


def yatay_yamasi(stil: Stil, hiza: str) -> StilYama:
    """Sola/ortaya/sağa hiza düğmesi; etkin hücrede zaten o hizaysa `genel`e döner (Excel gibi)."""
    return StilYama(yatay="genel" if stil.yatay == hiza else hiza)


def dikey_yamasi(stil: Stil, hiza: str) -> StilYama:
    """Üst/orta/alt: etkinse varsayılan `alt`a döner."""
    return StilYama(dikey="alt" if stil.dikey == hiza else hiza)


def girinti_yamasi(stil: Stil, fark: int) -> Optional[StilYama]:
    """Girintiyi Artır/Azalt. Genel hizalı hücre artırılırken sola hizalanır (Excel gibi).
    Değişmeyecekse (0'dan azaltma, 15'ten artırma) None."""
    yeni = max(0, min(15, stil.girinti + fark))
    if yeni == stil.girinti:
        return None
    if fark > 0 and stil.yatay in ("genel", "orta", "secim_ortasi"):
        return StilYama(girinti=yeni, yatay="sol")
    return StilYama(girinti=yeni)


def sayi_bicimi_yamasi(kod: str) -> StilYama:
    return StilYama(sayi_bicimi=kod)


def ondalik_yamasi(stil: Stil, fark: int, deger=None) -> Optional[StilYama]:
    """Ondalık Artır/Azalt: etkin hücrenin koduna göre yeni kod, tüm seçime uygulanır. Kod
    çözülemezse (bozuk özel biçim) None."""
    try:
        yeni = ondalik_degistir(stil.sayi_bicimi, fark, deger)
    except (BicimHatasi, ValueError):
        return None
    return None if yeni == stil.sayi_bicimi else StilYama(sayi_bicimi=yeni)


def hazir_adi(kod: str) -> str:
    """Kanonik kodun hazır biçim adı; hazır değilse "Özel"."""
    for ad, k in HAZIR.items():
        if k == kod:
            return ad
    return "Özel"


# ------------------------------------------------------------------ kenarlık
def _satir(a: Aralik, satir: int) -> Aralik:
    return Aralik(satir, a.ilk_sutun, satir, a.son_sutun)


def _sutun(a: Aralik, sutun: int) -> Aralik:
    return Aralik(a.ilk_satir, sutun, a.son_satir, sutun)


def kenarlik_plani(araliklar: Sequence[Aralik], secenek: str,
                   renk: str = _SIYAH) -> Plan:
    """Kenarlık menüsü seçeneği → plan. Her aralık ayrı ele alınır (Excel: çoklu seçimde her
    bölgenin kendi dış çerçevesi).

    - `alt/ust/sol/sag`: aralığın o dış kenarındaki hücrelerin o kenarı (ince)
    - `tum`: her hücrenin dört kenarı (iç çizgiler dahil)
    - `dis` / `kalin_dis`: yalnız dış çerçeve (ince / kalın)
    - `cift_alt`: alt kenar çift çizgi
    - `yok`: seçimdeki tüm kenarlıklar kalkar
    """
    if secenek not in KENAR_SECENEKLERI:
        raise ValueError(f"Bilinmeyen kenarlık seçeneği: {secenek!r}")
    plan: Plan = []
    for a in araliklar:
        if secenek == "yok":
            plan.append(([a], StilYama(kenar={y: None for y in ("ust", "alt", "sol", "sag")})))
        elif secenek == "tum":
            c = ("ince", renk)
            plan.append(([a], StilYama(kenar={"ust": c, "alt": c, "sol": c, "sag": c})))
        elif secenek in ("dis", "kalin_dis"):
            c = ("kalin" if secenek == "kalin_dis" else "ince", renk)
            plan.append(([_satir(a, a.ilk_satir)], StilYama(kenar={"ust": c})))
            plan.append(([_satir(a, a.son_satir)], StilYama(kenar={"alt": c})))
            plan.append(([_sutun(a, a.ilk_sutun)], StilYama(kenar={"sol": c})))
            plan.append(([_sutun(a, a.son_sutun)], StilYama(kenar={"sag": c})))
        elif secenek in ("alt", "cift_alt"):
            plan.append(([_satir(a, a.son_satir)],
                         StilYama(kenar={"alt": ("cift" if secenek == "cift_alt" else "ince", renk)})))
        elif secenek == "ust":
            plan.append(([_satir(a, a.ilk_satir)], StilYama(kenar={"ust": ("ince", renk)})))
        elif secenek == "sol":
            plan.append(([_sutun(a, a.ilk_sutun)], StilYama(kenar={"sol": ("ince", renk)})))
        else:
            plan.append(([_sutun(a, a.son_sutun)], StilYama(kenar={"sag": ("ince", renk)})))
    return plan
