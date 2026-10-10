"""Veri doğrulama denetimi (Faz 5 / 5g; faz5_tasarim.md §7.2). Qt yok.

Formüller (`formul1/2`) kuralın çapa hücresine göre yazılır ve denetlenen hücreye `agac_kaydir` ile
kaydırılarak değerlendirilir. Yalnız elle girişte çağrılır (yapıştırma/doldurma/formül sonucu denetlenmez).
Koşullu biçim değerlendirmesi (5h) bu modüle eklenecektir.
"""
from typing import List, Optional

from ..model import deger as D
from ..model.deger import Hata
from ..model.dogrulama import IKI_DEGERLI, Dogrulama, liste_sabiti_ogeleri
from ..model.gosterim import goster
from ..model.harmanla import tr_kucuk
from ..model.sayfa import Hucre
from .agac import agac_kaydir
from .degerlendir import Baglam, ad_agaci, degerlendir, hucre_sonucu
from .degerler import AralikDeger, Dizi
from .donustur import sayiya


def _agac(dv: Dogrulama, formul: str, r: int, c: int):
    agac = ad_agaci(formul)
    if agac is None:
        return None
    cr, cc = dv.capa()
    return agac_kaydir(agac, r - cr, c - cc)


def _skaler(dv: Dogrulama, formul: Optional[str], sayfa, r: int, c: int, kitap):
    if formul is None:
        return D.DEGER_HATASI
    agac = _agac(dv, formul, r, c)
    if agac is None:
        return D.AD
    return hucre_sonucu(agac, Baglam(sayfa, r, c, kitap))


def _sayi_degeri(v):
    """Karşılaştırma uçları sayı olmalı: boş = 0, metin sayıya çevrilebilirse sayı, aksi hata."""
    if v is None:
        return 0.0
    s = sayiya(v)
    return s if isinstance(s, float) else None


def _karsilastir(islec: str, x: float, a: float, b: Optional[float]) -> bool:
    if islec == "arasinda":
        return b is not None and a <= x <= b
    if islec == "arasinda_degil":
        return b is not None and not (a <= x <= b)
    return {"esit": x == a, "esit_degil": x != a, "buyuk": x > a, "kucuk": x < a,
            "buyuk_esit": x >= a, "kucuk_esit": x <= a}[islec]


def liste_ogeleri(dv: Dogrulama, sayfa, r: int, c: int, kitap=None, bos_dahil: bool = False) -> Optional[List[str]]:
    """Liste doğrulamasının seçenekleri (görünen metin). Sabit listede öğeler olduğu gibi; aralıkta hücre
    değerleri (`goster`). `bos_dahil`: açılır listede boş hücre boş satır olur. Hesaplanamazsa None."""
    if dv.formul1 is None:
        return None
    if dv.liste_sabiti_mi():
        return liste_sabiti_ogeleri(dv.formul1)
    agac = _agac(dv, dv.formul1, r, c)
    if agac is None:
        return None
    v = degerlendir(agac, Baglam(sayfa, r, c, kitap))
    if isinstance(v, AralikDeger):
        r1, c1, r2, c2 = (v.r1, v.c1, v.r2, v.c2) if v.satir_sayisi * v.sutun_sayisi <= 10_000 else v.kirpilmis()
        degerler = [v.hucre_degeri(i, j) for i in range(r1, r2 + 1) for j in range(c1, c2 + 1)]
    elif isinstance(v, Dizi):
        degerler = list(v.degerler())
    elif isinstance(v, str):
        return v.split(",")
    else:
        return None
    if any(isinstance(x, Hata) for x in degerler):
        return None
    return [goster(x) if x is not None else "" for x in degerler if bos_dahil or x is not None]


def dogrula(sayfa, r: int, c: int, deger, kitap=None, dv: Optional[Dogrulama] = None) -> bool:
    """`deger` (float/str/bool/None/Hata), `(r, c)` hücresine elle girilirse kurala uyar mı? Kural yoksa
    ya da türü "her değer" ise True. Denetim hata verirse (bozuk formül) geçersiz sayılır."""
    if dv is None:
        dv = sayfa.dogrulama(r, c)
    if dv is None or dv.tur == "her_deger":
        return True
    if deger is None:
        return dv.bos_yoksay
    kitap = kitap if kitap is not None else sayfa.kitap
    try:
        return _denetle(dv, sayfa, r, c, deger, kitap)
    except RecursionError:
        return False
    except Exception:
        return False


def _denetle(dv: Dogrulama, sayfa, r: int, c: int, deger, kitap) -> bool:
    tur = dv.tur
    if tur == "liste":
        ogeler = liste_ogeleri(dv, sayfa, r, c, kitap)
        if ogeler is None:
            return False
        aranan = tr_kucuk(goster(deger))
        return any(tr_kucuk(o) == aranan for o in ogeler)
    if tur == "ozel":
        hucreler = sayfa._hucreler
        eski = hucreler.get((r, c))
        hucreler[(r, c)] = Hucre(deger)                 # formül hücrenin YENİ değeriyle değerlendirilir
        try:
            v = _skaler(dv, dv.formul1, sayfa, r, c, kitap)
        finally:
            if eski is None:
                hucreler.pop((r, c), None)
            else:
                hucreler[(r, c)] = eski
        if isinstance(v, bool):
            return v
        return isinstance(v, float) and v != 0
    if tur == "metin_uzunlugu":
        x = float(len(goster(deger)))
    else:
        if isinstance(deger, (bool, Hata)) or not isinstance(deger, (int, float)):
            return False
        x = float(deger)
        if tur == "tam_sayi" and x != int(x):
            return False
    a = _sayi_degeri(_skaler(dv, dv.formul1, sayfa, r, c, kitap))
    if a is None:
        return False
    b = None
    if dv.islec in IKI_DEGERLI:
        b = _sayi_degeri(_skaler(dv, dv.formul2, sayfa, r, c, kitap))
        if b is None:
            return False
    return _karsilastir(dv.islec, x, a, b)
