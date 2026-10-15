"""Formül girilince hücreye önerilen sayı biçimi (Excel'in "biçim mirası"; Qt yok).

Excel, GENEL biçimli bir hücreye formül yazıldığında bazı durumlarda sonucun biçimini kendiliğinden ayarlar
(`=TODAY()` → tarih, `=PMT(…)` → para, `=A1+1` ve A1 tarihse → tarih). Kurallar gerçek Excel 16'da (COM,
2026-10-15) ölçüldü; ölçülmeyen her şey "biçim yok" (Genel) sayılır:

- İşlev kaynaklı: TODAY/DATE → kısa tarih; NOW → tarih+saat; TIME → saat (AM/PM); PMT, FV, PV, NPV, IPMT, PPMT, SLN,
  DB, DDB, SYD → para (eksi kırmızı); IRR, RATE, MIRR → yüzde. EDATE/EOMONTH/WORKDAY/DATEVALUE/… biçim vermez.
- Miras: başvuru, +x, -x ve parantez başvurulan hücrenin biçimini taşır; `+`/`-` iki işlenenden ilk biçimlisini alır
  (iki işlenen de tarihse sonuç Genel: tarih−tarih = gün). SUM/AVERAGE/MAX/MIN/MEDIAN/ROUND/ROUNDUP/ROUNDDOWN/TRUNC/INT/MOD
  ilk biçimli argümanın biçimini taşır (süre toplamı `[h]:mm:ss`). `*`, `/`, `^`, `&`, `%`, karşılaştırma ve diğer
  işlevler (ABS, IF, COUNT, SUMIF…) biçim taşımaz; ifadenin herhangi bir yerinde bulunmaları `+`/`-` mirasını da keser.
"""
from __future__ import annotations

from typing import Optional, Tuple

from . import agac as A
from .agac import formul_ayristir
from ..model.sayi_bicimi import kod_coz

KISA_TARIH = "d.mm.yyyy"
TARIH_SAAT = "d.mm.yyyy hh:mm"
SAAT_AMPM = "h:mm AM/PM"
PARA = '"₺"#,##0.00;[Red]-"₺"#,##0.00'
YUZDE = "0%"

_ISLEV_BICIMI = {
    "TODAY": KISA_TARIH, "DATE": KISA_TARIH, "NOW": TARIH_SAAT, "TIME": SAAT_AMPM,
    "PMT": PARA, "FV": PARA, "PV": PARA, "NPV": PARA, "IPMT": PARA, "PPMT": PARA, "SLN": PARA, "DB": PARA,
    "DDB": PARA, "SYD": PARA,
    "IRR": YUZDE, "RATE": YUZDE, "MIRR": YUZDE,
}
_MIRAS_ISLEVLERI = {"SUM", "AVERAGE", "MAX", "MIN", "MEDIAN", "ROUND", "ROUNDUP", "ROUNDDOWN", "TRUNC", "INT", "MOD"}

# (sürer_mi, biçim): sürer_mi=False → ifade biçim taşımayan işleç/işlev içeriyor, + / - mirası da kesilir
_Sonuc = Tuple[bool, Optional[str]]


def _tarih_mi(kod: Optional[str]) -> bool:
    """Biçim gün/ay/yıl bileşeni içeriyor mu (yalnız saat değil)."""
    if not kod:
        return False
    try:
        for b in kod_coz(kod).sayi_bolumleri[:1]:
            if b.tur == "tarih" and any(t[0] == "t" and t[1] in "YDM" for t in b.ogeler):
                return True
    except Exception:                                  # noqa: BLE001 — bozuk kod: tarih sayılmaz
        pass
    return False


def _saat_mi(kod: Optional[str]) -> bool:
    if not kod:
        return False
    try:
        for b in kod_coz(kod).sayi_bolumleri[:1]:
            if b.tur == "tarih" and any(t[0] == "t" and t[1] in "HNS" for t in b.ogeler) and not _tarih_mi(kod):
                return True
    except Exception:                                  # noqa: BLE001
        pass
    return False


def _hucre_bicimi(sayfa, kitap, ref) -> Optional[str]:
    """Başvurunun (ilk hücresinin) sayı biçimi; Genel → None."""
    hedef = sayfa
    if ref.sayfa is not None:
        if isinstance(ref.sayfa, int) and kitap is not None:
            hedef = kitap.sayfa_kimlikle(ref.sayfa)
        else:
            return None
    if hedef is None or ref.tur not in ("hucre", "aralik"):
        return None
    kod = hedef.stil(ref.r1, ref.c1).sayi_bicimi
    return None if kod == "General" else kod


def _incele(d, sayfa, kitap) -> _Sonuc:
    if isinstance(d, A.Ref):
        return True, _hucre_bicimi(sayfa, kitap, d.basvuru)
    if isinstance(d, (A.Sabit, A.Bos, A.Ad, A.DiziSabit)):
        return True, None
    if isinstance(d, A.Tekli):
        return _incele(d.x, sayfa, kitap)
    if isinstance(d, A.Yuzde):
        return False, None
    if isinstance(d, A.Ikili):
        if d.islec not in ("+", "-"):
            return False, None
        sa, fa = _incele(d.a, sayfa, kitap)
        sb, fb = _incele(d.b, sayfa, kitap)
        if not (sa and sb):
            return False, None
        if _tarih_mi(fa) and _tarih_mi(fb):            # tarih ± tarih: gün sayısı / anlamsız → Genel
            return True, None
        return True, fa or fb
    if isinstance(d, A.Cagri):
        if d.ad in _ISLEV_BICIMI:
            return True, _ISLEV_BICIMI[d.ad]
        if d.ad in _MIRAS_ISLEVLERI:
            sonuclar = [_incele(x, sayfa, kitap) for x in d.argumanlar]
            if not all(s for s, _ in sonuclar):
                return False, None
            kod = next((f for _, f in sonuclar if f), None)
            if d.ad == "SUM" and _saat_mi(kod):
                kod = "[h]:mm:ss"
            return True, kod
        return False, None
    return False, None


def onerilen_bicim(formul: str, sayfa, kitap=None) -> Optional[str]:
    """Kanonik formül (`=…`) için önerilen sayı biçimi kodu (kanonik); öneri yoksa None.
    Yalnız hücrenin biçimi Genel iken çağıran uygular."""
    try:
        agac = formul_ayristir(formul)
    except Exception:                                  # noqa: BLE001 — çözümlenemeyen formül: öneri yok
        return None
    surer, kod = _incele(agac, sayfa, kitap)
    return kod if surer else None
