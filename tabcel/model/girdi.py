"""Kullanıcının yazdığı metni hücre değerine çevirir (Excel, Türkçe yerel ayar). Qt yok.

Kurallar:
- Boş metin → hücre silinir.
- Başta kesme işareti (') → kalan kısım metindir.
- '=' ile başlayıp devamı olan → formül. Şimdilik yazıldığı gibi saklanır; kanonik
  İngilizce biçime çeviri Faz 2'de formul/ yerelleştirme katmanında yapılacak.
- DOĞRU/YANLIŞ (TRUE/FALSE de) → mantıksal.
- Sayı: ondalık ayırıcı virgül, binlik ayırıcı nokta (yalnızca 3'lü gruplarla).
  "1.5" gibi noktalı ondalık Excel'de tarih olabilir; tarih çözümü Faz 3'te,
  şimdilik metin kalır.
- Yüzde, para birimi, kesir, saat, tarih: `akilli_coz` (Faz 3 / 3g; hücreye elle yazarken). `girdi_coz`
  bunlara dokunmaz: dışarıdan yapıştırılan metin biçimsiz kalacağından tarihi seri sayı olarak
  göstermemek için düz çözümleyici olarak durur.
"""
import datetime as _dt
import math
import re
from decimal import Decimal as _Ondalik, InvalidOperation as _Ondalik_Hata
from typing import Optional, Tuple

from .sayfa import Hucre
from .sayi_bicimi import AY_KISA, AYLAR, _tr_kucuk
from .tarihseri import ay_gun_sayisi, ymd_seri

_SAYI_RE = re.compile(
    r"^[+-]?(?:\d{1,3}(?:\.\d{3})+|\d*)(?:,\d*)?(?:[eE][+-]?\d+)?$")

_MANTIKSAL = {"DOĞRU": True, "YANLIŞ": False, "TRUE": True, "FALSE": False}


def sayi_coz(metin: str) -> Optional[float]:
    m = metin.strip()
    if not _SAYI_RE.match(m) or not any(ch.isdigit() for ch in m):
        return None
    try:
        v = float(m.replace(".", "").replace(",", "."))
    except ValueError:
        return None
    return v if math.isfinite(v) else None       # 1E400 → inf saklanmaz, metin kalır


def _mantiksal_coz(metin: str) -> Optional[bool]:
    m = metin.strip()
    # Türkçe büyük harf: 'i' → 'İ' için önce kendi dönüşümümüzü yapıyoruz
    return _MANTIKSAL.get(m.replace("i", "İ").replace("ı", "I").upper())


def girdi_coz(metin: str) -> Optional[Hucre]:
    if metin == "":
        return None
    if metin.startswith("'"):
        return Hucre(metin[1:]) if len(metin) > 1 else None
    if metin.startswith("=") and len(metin) > 1:
        return Hucre(None, metin)
    b = _mantiksal_coz(metin)
    if b is not None:
        return Hucre(b)
    n = sayi_coz(metin)
    if n is not None:
        return Hucre(n)
    return Hucre(metin)


# ------------------------------------------------------------------ akıllı giriş (3g)
_SAYI = r"[+-]?(?:\d{1,3}(?:\.\d{3})+|\d*)(?:,\d*)?"
_YUZDE_SON = re.compile(rf"^({_SAYI})\s*%$")
_YUZDE_ON = re.compile(rf"^%\s*({_SAYI})$")
_PARA_ON = re.compile(rf"^([+-]?)\s*([₺$€])\s*([+-]?)\s*((?:\d{{1,3}}(?:\.\d{{3}})+|\d*)(?:,\d*)?)$")
_PARA_SON = re.compile(rf"^({_SAYI})\s*([₺$€])$")
_KESIR = re.compile(r"^([+-]?\d+)\s+(\d+)/(\d+)$")
_SAAT = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*(AM|PM|ÖÖ|ÖS))?$", re.IGNORECASE)
_SAAT_SON = re.compile(r"\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|ÖÖ|ÖS))?)$", re.IGNORECASE)
_TARIH_SAYISAL = re.compile(r"^(\d{1,2})([./-])(\d{1,2})(?:\2(\d{4}|\d{2}))?$")
_TARIH_AD = re.compile(r"^(\d{1,2})\s+([^\W\d_]+)(?:\s+(\d{4}|\d{2}))?$")
_AY_ADLARI = {_tr_kucuk(a): i + 1 for i, a in enumerate(AYLAR)}
_AY_KISA = {_tr_kucuk(a): i + 1 for i, a in enumerate(AY_KISA)}


def _ondalik_sayisi(metin: str) -> int:
    return len(metin.split(",")[1]) if "," in metin else 0


def _yil(y: Optional[str], bugun: _dt.date) -> Optional[int]:
    """Yıl metni → yıl (iki hane: 00–29 → 20xx, 30–99 → 19xx; yoksa içinde bulunulan yıl)."""
    if y is None:
        return bugun.year
    n = int(y)
    if len(y) == 2:
        return 2000 + n if n < 30 else 1900 + n
    return n if 1900 <= n <= 9999 else None


def _tarih_seri(g: int, a: int, y: Optional[int]) -> Optional[int]:
    if y is None or not 1 <= a <= 12 or not 1 <= g <= ay_gun_sayisi(y, a):
        return None
    return ymd_seri(y, a, g)


def _saat_coz(metin: str) -> Optional[Tuple[float, str]]:
    """`14:30`, `14:30:15`, `2:30 ÖS` → (günün kesri, kod)."""
    m = _SAAT.match(metin.strip())
    if not m:
        return None
    sa, dk, sn, ek = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    sn_i = int(sn) if sn is not None else 0
    if dk > 59 or sn_i > 59:
        return None
    if ek:
        if not 1 <= sa <= 12:
            return None
        pm = ek.upper() in ("PM", "ÖS")
        sa = (sa % 12) + (12 if pm else 0)
        kod = "h:mm:ss AM/PM" if sn is not None else "h:mm AM/PM"
    else:
        if sa > 23:
            return None
        kod = "hh:mm:ss" if sn is not None else "hh:mm"
    return (sa * 3600 + dk * 60 + sn_i) / 86400.0, kod


def _tarih_coz(metin: str, bugun: _dt.date) -> Optional[Tuple[int, str]]:
    m = _TARIH_SAYISAL.match(metin)
    if m:
        g, a, y = int(m.group(1)), int(m.group(3)), m.group(4)
        seri = _tarih_seri(g, a, _yil(y, bugun))
        return None if seri is None else (seri, "d.mm.yyyy" if y else "d mmmm")
    m = _TARIH_AD.match(metin)
    if m:
        ad = _tr_kucuk(m.group(2))
        a = _AY_ADLARI.get(ad) or _AY_KISA.get(ad)
        if a is None:
            return None
        y = m.group(3)
        seri = _tarih_seri(int(m.group(1)), a, _yil(y, bugun))
        if seri is None:
            return None
        uzun = ad in _AY_ADLARI
        kod = ("d mmmm yyyy" if uzun else "dd mmm yyyy") if y else ("d mmmm" if uzun else "d mmm")
        return seri, kod
    return None


def sayisal_akilli(metin: str, bugun: Optional[_dt.date] = None) -> Optional[Tuple[float, Optional[str]]]:
    """Yüzde, para, kesir, saat, tarih (isteğe bağlı saatle) ve bilimsel yazımı → (sayı, önerilen kanonik
    sayı biçimi). Sayıya benzemiyorsa None. Düz sayı (`12`) burada DEĞİL `sayi_coz`dadır."""
    m = metin.strip()
    if not m:
        return None
    bugun = bugun or _dt.date.today()
    c0 = m[0]
    if not (c0.isdigit() or c0 in "+-%₺$€,"):
        return None
    for rx in (_YUZDE_SON, _YUZDE_ON):
        g = rx.match(m)
        if g and any(ch.isdigit() for ch in g.group(1)):
            n = sayi_coz(g.group(1))
            if n is not None:
                d = _ondalik_sayisi(g.group(1))
                return _yuzde_bol(g.group(1), n), "0" + ("." + "0" * d if d else "") + "%"
    g = _PARA_ON.match(m)
    if g and g.group(4) and not (g.group(1) and g.group(3)):     # `-₺-5` çift işaret: metin kalır
        n = sayi_coz(g.group(3) + g.group(4))
        if n is not None:
            if g.group(1) == "-":
                n = -n
            return n, _para_kodu(g.group(2), g.group(4))
    g = _PARA_SON.match(m)
    if g and any(ch.isdigit() for ch in g.group(1)):
        n = sayi_coz(g.group(1))
        if n is not None:
            return n, _para_kodu(g.group(2), g.group(1))
    g = _KESIR.match(m)
    if g and int(g.group(3)) > 0:
        tam = int(g.group(1))
        oran = int(g.group(2)) / int(g.group(3))
        isaret = -1 if g.group(1).startswith("-") else 1
        return tam + isaret * oran, ("# ??/??" if int(g.group(3)) > 9 else "# ?/?")
    s = _saat_coz(m)
    if s is not None:
        return s
    t = _tarih_coz(m, bugun)
    if t is not None:
        return float(t[0]), t[1]
    k = _SAAT_SON.search(m)
    if k:
        sa = _saat_coz(k.group(1))
        t = _tarih_coz(m[:k.start()].strip(), bugun)
        if sa is not None and t is not None:
            return t[0] + sa[0], ("d.mm.yyyy hh:mm:ss" if "ss" in sa[1] else "d.mm.yyyy hh:mm")
    return None


def _para_kodu(simge: str, sayi_metni: str) -> str:
    from .bicim_kodlari import kod_olustur
    return kod_olustur("Para Birimi", 2 if "," in sayi_metni and _ondalik_sayisi(sayi_metni) else 0,
                       True, simge)


def akilli_coz(metin: str, bugun: Optional[_dt.date] = None) -> Tuple[Optional[Hucre], Optional[str]]:
    """Elle yazılan metin → (hücre, önerilen sayı biçimi kodu | None). Sıra: `girdi_coz` kuralları (boş,
    `'`, formül, mantıksal, düz sayı), sonra yüzde/para/kesir/saat/tarih. Önerilen kod yalnız hücrenin
    biçimi Genel iken uygulanır (arayüz karar verir)."""
    if metin == "" or metin.startswith("'") or (metin.startswith("=") and len(metin) > 1):
        return girdi_coz(metin), None
    if _mantiksal_coz(metin) is not None:
        return girdi_coz(metin), None
    n = sayi_coz(metin)
    if n is not None:
        return Hucre(n), ("0.00E+00" if ("e" in metin or "E" in metin) else None)
    a = sayisal_akilli(metin, bugun)
    if a is not None:
        return Hucre(a[0]), a[1]
    return Hucre(metin), None


def sayi_yaz(n: float) -> str:
    """Düzenleme kutusu için sayı metni (binlik ayırıcısız, ondalık virgül)."""
    if n == int(n) and abs(n) < 1e15:
        return str(int(n))
    return repr(n).replace(".", ",").replace("e", "E")


def _yuzde_bol(metin: str, n: float) -> float:
    """`metin` sayısının %100'e bölümü, ondalık aritmetikle (n/100 kayan nokta artığı bırakır;
    düzenleme metniyle gidiş-dönüş birebir olsun)."""
    try:
        d = _Ondalik(metin.strip().replace(".", "").replace(",", "."))
        return float(d / 100)
    except (_Ondalik_Hata, ValueError):
        return n / 100


def _yuzde_yaz(v: float) -> str:
    """Yüzde biçimli hücrenin düzenleme metni: v×100, tam duyarlıklı, bilimsel gösterimsiz, `%` olmadan."""
    d = _Ondalik(repr(v)) * 100
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _bicimli_duzenleme(v: float, kod: str) -> Optional[str]:
    """Tarih/saat ve yüzde biçimli hücrenin düzenleme metni (Excel gibi: tarih `gg.aa.yyyy`, yüzde `15%`).
    Biçim buna uymuyorsa None."""
    from .sayi_bicimi import bicimle, kod_coz, BicimHatasi
    try:
        k = kod_coz(kod)
    except BicimHatasi:
        return None
    if k.tarih_mi:
        tam, kesir = divmod(v, 1.0)
        if v < 0:
            return None
        if tam == 0:
            return bicimle(v, "hh:mm:ss").metin
        if kesir == 0:
            return bicimle(v, "dd.mm.yyyy").metin
        return bicimle(v, "dd.mm.yyyy hh:mm:ss").metin
    if kod.endswith("%") and "E" not in kod and ";" not in kod:
        return _yuzde_yaz(v) + "%"
    return None


def duzenleme_metni(hucre: Optional[Hucre], kod: Optional[str] = None) -> str:
    """Hücreyi düzenlerken görünen metin; girdi_coz ile gidiş-dönüş yapar. `kod`: hücrenin sayı biçimi
    (tarih/yüzde ise değer o yazımla gösterilir; `akilli_coz` aynı değere geri çözer)."""
    if hucre is None:
        return ""
    if kod and kod != "General" and hucre.formul is None and isinstance(hucre.deger, float):
        m = _bicimli_duzenleme(hucre.deger, kod)
        if m is not None:
            return m
    if hucre.formul is not None:
        return hucre.formul
    v = hucre.deger
    if v is None:
        return ""
    if isinstance(v, bool):
        return "DOĞRU" if v else "YANLIŞ"
    if isinstance(v, float):
        return sayi_yaz(v)
    if isinstance(v, str):
        # Metin başka türe çözülecekse (sayı gibi görünen metin) başına ' konur.
        yeni = akilli_coz(v)[0]        # hucre_gir ile aynı çözümleyici (yüzde/tarih/para… da ' gerektirir)
        if v == "" or v.startswith(("'", "=")) or yeni is None or yeni.deger != v:
            return "'" + v
        return v
    return str(v)
