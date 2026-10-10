"""İşaretleme modu mantığı (K7): formül yazarken başvuru eklenebilir mi, başvuruların metin
konumları (renkli vurgu), F4 döngüsü. Qt yok; metin kullanıcının gördüğü Türkçe biçimdedir
(baştaki '=' dahil). Kurallar: faz2_tasarim.md §6."""
from dataclasses import replace
from typing import List, Optional, Tuple

from ..model.adres import Aralik
from .sozcuk import (AC, AYRAC, BASVURU, BOSLUK, ISLEC, FormulHatasi, Basvuru, Sozcuk,
                     sayfa_oneki, sozcukle)
from .yerel import TR

# Excel'in başvuru renk paleti (sırayla döner)
RENKLER = ("#0070C0", "#C00000", "#7030A0", "#00A650", "#ED7D31", "#00B0F0", "#808000", "#FF00FF")


def _sozcukler(metin: str) -> Optional[List[Sozcuk]]:
    if not metin.startswith("="):
        return None
    try:
        return sozcukle(metin[1:], TR)
    except FormulHatasi:
        return None


def basvurular(metin: str) -> List[Tuple[int, int, Basvuru]]:
    """Formüldeki başvuruların (başlangıç, son, Basvuru) listesi; konumlar `metin` içindedir.
    Formül çözümlenemiyorsa boş."""
    soz = _sozcukler(metin)
    if soz is None:
        return []
    return [(s.konum + 1, s.konum + 1 + len(s.metin), s.deger) for s in soz if s.tur == BASVURU]


def renkli_basvurular(metin: str):
    """[(bas, son, Basvuru, renk)]: her başvuru sırayla paletten renk alır."""
    return [(b, s, bv, RENKLER[i % len(RENKLER)]) for i, (b, s, bv) in enumerate(basvurular(metin))]


def eklenebilir(metin: str, imlec: int) -> bool:
    """İmleç, yeni bir başvuru eklenebilecek konumda mı? (imleçten önceki anlamlı sözcük '=' ya da
    '(' , argüman ayracı ya da işleç)"""
    if not metin.startswith("=") or imlec < 1:
        return False
    soz = _sozcukler(metin[:imlec])
    if soz is None:
        return False
    for s in reversed(soz):
        if s.tur == BOSLUK:
            continue
        return s.tur in (AC, AYRAC) or (s.tur == ISLEC and s.metin != "%")
    return True                       # yalnızca '='


def basvuru_metni(aralik: Aralik, sayfa_adi: Optional[str] = None) -> str:
    """Seçimden başvuru metni: tek hücre `A1`, aralık `A1:B3`, tam sütun/satır `A:C` / `2:5`."""
    from ..model.adres import MAX_COL, MAX_ROW
    r1, c1, r2, c2 = aralik.ilk_satir, aralik.ilk_sutun, aralik.son_satir, aralik.son_sutun
    if r1 == 1 and r2 == MAX_ROW:
        b = Basvuru("sutun", 1, c1, MAX_ROW, c2)
    elif c1 == 1 and c2 == MAX_COL:
        b = Basvuru("satir", r1, 1, r2, MAX_COL)
    elif (r1, c1) == (r2, c2):
        b = Basvuru("hucre", r1, c1, r1, c1)
    else:
        b = Basvuru("aralik", r1, c1, r2, c2)
    return (sayfa_oneki(sayfa_adi) if sayfa_adi else "") + b.govde()


_DONGU = {(False, False): (True, True), (True, True): (True, False),
          (True, False): (False, True), (False, True): (False, False)}


def f4(metin: str, imlec: int) -> Tuple[str, int]:
    """İmlecin yanındaki (içinde ya da hemen sonunda) hücre/aralık başvurusunda
    A1 → $A$1 → A$1 → $A1 → A1 döngüsü. Başvuru yoksa değişmez."""
    for bas, son, b in basvurular(metin):
        if bas <= imlec <= son and b.tur in ("hucre", "aralik"):
            satir_m, sutun_m = _DONGU[(b.r1m, b.c1m)]
            yeni = replace(b, r1m=satir_m, c1m=sutun_m,
                           r2m=satir_m if b.tur == "aralik" else b.r2m,
                           c2m=sutun_m if b.tur == "aralik" else b.c2m)
            onek = metin[bas:son][: len(metin[bas:son]) - len(b.govde())]    # sayfa öneki aynen kalır
            parca = onek + yeni.govde()
            return metin[:bas] + parca + metin[son:], bas + len(parca)
    return metin, imlec


# ------------------------------------------------------------------ otomatik tamamlama ve ipucu
def ad_oneki(metin: str, imlec: int) -> Optional[Tuple[int, str]]:
    """İmleçten önceki, bir fonksiyon adı olabilecek yazı: (başlangıç, önek). Başvuru eklenebilir
    bir konumda başlamalı (`=`, `(`, `;`, işleç sonrası) ve harfle başlamalı; yoksa None."""
    if not metin.startswith("=") or imlec < 2:
        return None
    i = imlec
    while i > 1 and (metin[i - 1].isalnum() or metin[i - 1] in "._"):
        i -= 1
    onek = metin[i:imlec]
    if not onek or not (onek[0].isalpha() or onek[0] == "_") or not eklenebilir(metin, i):
        return None
    return i, onek


def oneriler(onek: str, en_cok: int = 12, tanimli_adlar=()) -> List[str]:
    """Önekle başlayan fonksiyon adları (Türkçe Excel adı; Türkçesi olmayan İngilizce), alfabetik;
    ardından (en çok 4) tanımlı ad. Aynı adlı tanımlı ad fonksiyonu gölgelemez (listede bir kez)."""
    from . import adlar, fonksiyonlar
    from .yerel import tr_buyuk
    ara = tr_buyuk(onek)
    adlar_ = {adlar.turkcesi(en) for en in fonksiyonlar.KAYIT}
    fon = sorted((a for a in adlar_ if tr_buyuk(a).startswith(ara)), key=tr_buyuk)
    ek = sorted({a for a in tanimli_adlar if tr_buyuk(a).startswith(ara) and tr_buyuk(a) not in
                 {tr_buyuk(f) for f in fon}}, key=tr_buyuk)[:4]
    return fon[:max(en_cok - len(ek), 0)] + ek


def ipucu(metin: str, imlec: int) -> Optional[str]:
    """İmleç bir fonksiyon çağrısının içindeyse `ADI(arg1; [arg2]; …)` (argüman sayısı sınırlarından)."""
    from . import adlar, fonksiyonlar
    soz = _sozcukler(metin[:imlec])
    if not soz:
        return None
    acik = []                                # açık parantezlerin fonksiyon adı (ya da None)
    onceki = None
    for s in soz:
        if s.tur == AC:
            acik.append(onceki.metin if onceki is not None and onceki.tur == "fonk" else None)
        elif s.tur == "kapa" and acik:
            acik.pop()
        if s.tur != BOSLUK:
            onceki = s
    ad = next((a for a in reversed(acik) if a), None)
    if ad is None:
        return None
    en = adlar.ingilizcesi(ad) or ad.upper()
    t = fonksiyonlar.KAYIT.get(en)
    if t is None:
        return None
    sinir = 255 if t.en_cok is None else t.en_cok
    parcalar = [f"arg{k}" if k <= t.en_az else f"[arg{k}]" for k in range(1, min(max(sinir, t.en_az), 3) + 1)]
    if sinir > 3:
        parcalar.append("…")
    return f"{adlar.turkcesi(en)}({'; '.join(parcalar)})"
