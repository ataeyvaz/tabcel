"""Başvuru kaydırma (saklanan biçimde, sözcük düzeyinde — boşluk/yazım korunur). Qt yok.

- `kopyala`: formül kopyalanınca/doldurulunca göreli başvurular kayar ($'lılar sabit)
- `yapi`: satır/sütun ekle-sil sonrası başvurular düzelir; silinen hedef #REF! olur
- `tasi`: kes-yapıştırda taşınan bölgeye işaret eden başvurular yeni yere gider
- `yapi_duzeltmeleri`: kitap genelinde `yapi` uygulanacak hücre listesi (komutlar kullanır)
- `ek_duzeltmeleri`: aynısı doğrulama / koşullu biçim formülleri ve tanımlı adlar için (Faz 5)
Kurallar: faz2_tasarim.md §5.
"""
from dataclasses import is_dataclass, replace
from typing import Callable, Optional, Tuple, Union

from ..model.adres import MAX_COL, MAX_ROW
from .sozcuk import BASVURU, Basvuru, FormulHatasi, sayfa_oneki, sozcukle
from .yerel import SAKLI

_SIL = object()        # dönüştürücü bu değeri verirse başvuru #REF! olur

Donusturucu = Callable[[Basvuru], Union[Basvuru, object]]


def _onek(b: Basvuru) -> str:
    if b.sayfa is None:
        return ""
    if isinstance(b.sayfa, int):
        return f"[{b.sayfa}]!"
    return sayfa_oneki(b.sayfa)


def _donustur(formul: str, f: Donusturucu) -> Optional[str]:
    """Her başvuruya `f` uygular. Değişiklik yoksa None, varsa yeni formül metni."""
    if not formul.startswith("="):
        return None
    try:
        sozcukler = sozcukle(formul[1:], SAKLI)
    except FormulHatasi:
        return None
    degisti = False
    parcalar = []
    for s in sozcukler:
        if s.tur == BASVURU:
            yeni = f(s.deger)
            if yeni is _SIL:
                parcalar.append("#REF!")
                degisti = True
                continue
            if yeni != s.deger:
                parcalar.append(_onek(yeni) + yeni.govde())
                degisti = True
                continue
        parcalar.append(s.metin)
    return "=" + "".join(parcalar) if degisti else None


# ------------------------------------------------------------------ kopyala
def basvuru_kaydir(b: Basvuru, dr: int, dc: int):
    """Tek başvuruyu (dr, dc) uzağa kaydırır: göreli uçlar kayar, `$`'lılar sabit. Sayfa dışına
    çıkarsa `_SIL`. (`kopyala` ve `agac.agac_kaydir` ortak kullanır.)"""
    r1, r2, c1, c2 = b.r1, b.r2, b.c1, b.c2
    if b.tur != "sutun":                 # tam sütunun satırları kaymaz
        r1 = r1 if b.r1m else r1 + dr
        r2 = r2 if b.r2m else r2 + dr
    if b.tur != "satir":
        c1 = c1 if b.c1m else c1 + dc
        c2 = c2 if b.c2m else c2 + dc
    if not (1 <= r1 <= MAX_ROW and 1 <= r2 <= MAX_ROW and 1 <= c1 <= MAX_COL
            and 1 <= c2 <= MAX_COL):
        return _SIL
    # $'lı ve göreli uç farklı kayınca sıra bozulabilir: normalize et (Excel de öyle)
    if r1 > r2:
        r1, r2 = r2, r1
        b = replace(b, r1m=b.r2m, r2m=b.r1m)
    if c1 > c2:
        c1, c2 = c2, c1
        b = replace(b, c1m=b.c2m, c2m=b.c1m)
    return replace(b, r1=r1, r2=r2, c1=c1, c2=c2)


def kopyala(formul: str, dr: int, dc: int) -> str:
    """Formülü (dr, dc) uzağa kopyalar: göreli satır/sütunlar kayar. Sayfa dışı → #REF!."""
    if dr == 0 and dc == 0:
        return formul
    return _donustur(formul, lambda b: basvuru_kaydir(b, dr, dc)) or formul


# ------------------------------------------------------------------ satır/sütun ekle-sil
def _eksen_esle(k1: int, k2: int, nerede: int, fark: int, sinir: int):
    """Bir eksendeki [k1, k2] uçlarının ekle/sil sonrası hali; tamamen silindiyse None."""
    if fark > 0:
        y1 = k1 + fark if k1 >= nerede else k1
        y2 = k2 + fark if k2 >= nerede else k2
        if y2 > sinir:
            if y1 > sinir:
                return None
            y2 = sinir                       # aralığın sonu sayfa sınırına dayanır
        return y1, y2
    d = -fark
    son = nerede + d - 1
    y1 = k1 if k1 < nerede else (nerede if k1 <= son else k1 - d)
    y2 = k2 if k2 < nerede else (nerede - 1 if k2 <= son else k2 - d)
    if y1 > y2:
        return None
    return y1, y2


def yapi(formul: str, kendi: int, hedef: int, eksen: str, nerede: int, fark: int) -> Optional[str]:
    """`hedef` sayfada `eksen` ('satir'|'sutun') boyunca `nerede`den itibaren `fark` kadar ekleme
    (+) ya da silme (−) yapıldı. `kendi`: formülün bulunduğu sayfanın kimliği.
    Değişiklik yoksa None."""
    satir_ekseni = eksen == "satir"

    def f(b: Basvuru):
        sayfa = kendi if b.sayfa is None else b.sayfa
        if sayfa != hedef:
            return b
        if satir_ekseni:
            if b.tur == "sutun":
                return b
            e = _eksen_esle(b.r1, b.r2, nerede, fark, MAX_ROW)
            if e is None:
                return _SIL
            return replace(b, r1=e[0], r2=e[1])
        if b.tur == "satir":
            return b
        e = _eksen_esle(b.c1, b.c2, nerede, fark, MAX_COL)
        if e is None:
            return _SIL
        return replace(b, c1=e[0], c2=e[1])
    return _donustur(formul, f)


def yapi_duzeltmeleri(kitap, sayfa, eksen: str, nerede: int, fark: int):
    """Kitaptaki (kitapsızsa yalnız `sayfa`daki) tüm formüllerin yeni metinleri.
    Döner: {Sayfa: {(satır, sütun): (eski formül, yeni formül)}} (yalnız değişenler).
    Satır/sütun KAYDIRILDIKTAN SONRA çağrılır (anahtarlar yeni konumlardır)."""
    sayfalar = kitap.sayfalar if kitap is not None else [sayfa]
    hedef = sayfa.kimlik
    sonuc = {}
    for s in sayfalar:
        degisen = {}
        for r, c, h in s.dolu_hucreler(sirali=False):
            if h.formul is None:
                continue
            yeni = yapi(h.formul, s.kimlik, hedef, eksen, nerede, fark)
            if yeni is not None:
                degisen[(r, c)] = (h.formul, yeni)
        if degisen:
            sonuc[s] = degisen
    return sonuc


_EK_FORMUL_ALANLARI = ("formul", "formul1", "formul2")      # doğrulama / koşullu biçim kuralı alanları


def _kural_duzelt(kural, kendi: int, hedef: int, eksen: str, nerede: int, fark: int):
    """Kuralın formül alanlarını `yapi` ile düzeltir; değişen yoksa aynı nesne."""
    if not is_dataclass(kural):
        return kural
    degisen = {}
    for alan in _EK_FORMUL_ALANLARI:
        f = getattr(kural, alan, None)
        if isinstance(f, str) and f.startswith("="):
            yeni = yapi(f, kendi, hedef, eksen, nerede, fark)
            if yeni is not None:
                degisen[alan] = yeni
    return replace(kural, **degisen) if degisen else kural


def ek_duzeltmeleri(kitap, sayfa, eksen: str, nerede: int, fark: int) -> bool:
    """`sayfa`da satır/sütun ekle-sil yapıldıktan SONRA, kitaptaki tüm sayfaların doğrulama ve
    koşullu biçim kurallarının formüllerini ve kitaptaki tüm tanımlı adların formüllerini yerinde
    düzeltir (kuralların `formul`/`formul1`/`formul2` alanları, `TanimliAd.formul`). Aralıkların
    kendisi `Sayfa._kaydir`da kayar. Geri almak için çağıran önce `Sayfa.ek_durumu` /
    `CalismaKitabi.ad_durumu` görüntülerini alır. Döner: bir şey değişti mi."""
    degisti = False
    hedef = sayfa.kimlik
    sayfalar = kitap.sayfalar if kitap is not None else [sayfa]
    for s in sayfalar:
        for depo in ("dogrulamalar", "kosullu"):
            liste = getattr(s, depo)
            yeni = [_kural_duzelt(k, s.kimlik, hedef, eksen, nerede, fark) for k in liste]
            if any(a is not b for a, b in zip(yeni, liste)):
                setattr(s, depo, yeni)
                s._bildir("ek", alan="dogrulama" if depo == "dogrulamalar" else "kosullu")
                degisti = True
    if kitap is not None:
        for anahtar, tanim in list(kitap.adlar.items()):
            # ad formülünde niteliksiz başvuru, adın kapsamındaki sayfaya (kitap kapsamında: ilk
            # sayfaya değil, kendi sayfasız bağlama) aittir; kapsamı olmayan ad için kendi=None
            yeni = yapi(tanim.formul, tanim.kapsam if tanim.kapsam is not None else -1,
                        hedef, eksen, nerede, fark)
            if yeni is not None:
                kitap.ad_yaz(replace(tanim, formul=yeni), anahtar)
                degisti = True
    return degisti


# ------------------------------------------------------------------ taşı (kes-yapıştır)
def tasi(formul: str, kendi_eski: int, kendi_yeni: int, kaynak: int,
         kutu: Tuple[int, int, int, int], hedef: int, dr: int, dc: int) -> Optional[str]:
    """`kaynak` sayfadaki `kutu` (r1, c1, r2, c2) bölgesi `hedef` sayfaya (dr, dc) kaydırılarak
    taşındı. Formül `kendi_eski` sayfasından `kendi_yeni`ye geçmiş olabilir (taşınan formül).
    Bölgenin tamamen içindeki başvurular yeni yere gider; kısmen içerdekiler değişmez.
    Formül başka sayfaya taşındıysa niteliksiz başvurular eski sayfaya nitelendirilir.
    Taşınanın üzerine yazdığı hücrelere (hedef bölge) tamamen işaret eden başvurular #REF! olur
    (Excel gibi)."""
    r1k, c1k, r2k, c2k = kutu
    h1, g1, h2, g2 = r1k + dr, c1k + dc, r2k + dr, c2k + dc

    def f(b: Basvuru):
        sayfa = kendi_eski if b.sayfa is None else b.sayfa
        hucre_turu = b.tur in ("hucre", "aralik")
        icinde = (sayfa == kaynak and hucre_turu
                  and r1k <= b.r1 and b.r2 <= r2k and c1k <= b.c1 and b.c2 <= c2k)
        if icinde:
            yeni_sayfa = None if hedef == kendi_yeni else hedef
            return replace(b, r1=b.r1 + dr, r2=b.r2 + dr, c1=b.c1 + dc, c2=b.c2 + dc,
                           sayfa=yeni_sayfa)
        if (sayfa == hedef and hucre_turu
                and h1 <= b.r1 and b.r2 <= h2 and g1 <= b.c1 and b.c2 <= g2):
            return _SIL
        if b.sayfa is None and kendi_eski != kendi_yeni:
            return replace(b, sayfa=kendi_eski)
        return b
    return _donustur(formul, f)
