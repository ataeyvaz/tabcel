"""Yerelleştirme katmanı: kullanıcının yazdığı formül ⇄ saklanan biçim (`Hucre.formul`). Qt yok.

- Saklanan biçim: kanonik İngilizce (`,` ayırıcı, `.` ondalık, İngilizce ad/hata) + başka sayfa
  başvurusu kimlikle (`[3]!A1`) — faz2_tasarim.md §2.
- `girdiden`: TR (ya da .xlsx için EN) metin → saklanan biçim. Sözdizimi denetlenir.
- `gosterime`: saklanan biçim → TR (ekran) ya da EN (.xlsx/pano dışa).
Çeviri sözcük düzeyindedir: boşluklar, metin sabitleri ve kullanıcının yazımı korunur.
"""
from dataclasses import replace
from typing import List, Optional

from . import adlar, fonksiyonlar
from .agac import Cagri, Dugum, ayristir
from .sozcuk import (
    AD, AYRAC, BASVURU, DIZI_SATIR, DIZI_SUTUN, FONK, HATA, SAYI, FormulHatasi, Sozcuk,
    metne, sayfa_oneki, sozcukle,
)
from .yerel import EN, SAKLI, TR, Yerel, tr_buyuk


def _sayfa_bul(kitap, ad: str):
    if kitap is None:
        return None
    k = ad.casefold()
    return next((s for s in kitap.sayfalar if s.ad.casefold() == k), None)


def _fonksiyon_adi(yazilan: str, kaynak: Yerel) -> str:
    """Yazılan fonksiyon adının kanonik hali. Türkçe ad → İngilizce; İngilizce ad olduğu gibi
    (büyük harf); bilinmeyen ad büyük harfle kalır (değerlendirmede #AD?)."""
    if yazilan.upper().startswith("_XLFN."):            # .xlsx'teki yeni fonksiyon öneki
        yazilan = yazilan[6:]
    if kaynak is TR:
        en = adlar.ingilizcesi(yazilan)
        if en:
            return en
    ust = yazilan.upper()
    if yazilan.isascii() and (ust in fonksiyonlar.KAYIT or ust in adlar.EN_TR or kaynak is not TR):
        return ust
    return tr_buyuk(yazilan)


def _arguman_denetle(d: Dugum) -> None:
    """Bilinen fonksiyonların argüman sayısını denetler (Excel girişte reddeder)."""
    yigin = [d]
    while yigin:
        x = yigin.pop()
        if isinstance(x, Cagri):
            t = fonksiyonlar.bul(x.ad)
            n = len(x.argumanlar)
            if t is not None:
                if n < t.en_az:
                    raise FormulHatasi(f"{adlar.turkcesi(x.ad)} için argüman sayısı çok az")
                if t.en_cok is not None and n > t.en_cok:
                    raise FormulHatasi(f"{adlar.turkcesi(x.ad)} için argüman sayısı çok fazla")
            yigin.extend(x.argumanlar)
        elif hasattr(x, "__dataclass_fields__"):
            for alan in x.__dataclass_fields__:
                v = getattr(x, alan)
                if isinstance(v, Dugum):
                    yigin.append(v)


def girdiden(metin: str, kitap=None, kaynak: Yerel = TR) -> str:
    """'=' ile başlayan kullanıcı formülünü saklanan biçime çevirir. Hata → `FormulHatasi`
    (iletisi kullanıcıya gösterilebilir, `konum` gövde içindeki karakter indeksidir)."""
    if not metin.startswith("="):
        raise FormulHatasi("Formül '=' ile başlamalı", 0)
    sozcukler = sozcukle(metin[1:], kaynak)
    cikti: List[Sozcuk] = []
    for s in sozcukler:
        t = s.tur
        if t == FONK:
            s = s.yeni(metin=_fonksiyon_adi(s.metin, kaynak))
        elif t == AD:
            ust = tr_buyuk(s.metin) if kaynak is TR else s.metin.upper()
            if ust == kaynak.dogru or s.metin.upper() == "TRUE":
                s = s.yeni(metin="TRUE")
            elif ust == kaynak.yanlis or s.metin.upper() == "FALSE":
                s = s.yeni(metin="FALSE")
        elif t == SAYI:
            s = s.yeni(metin=s.metin.replace(kaynak.ondalik, ".").replace("e", "E"))
        elif t == AYRAC:
            s = s.yeni(metin=",")
        elif t == DIZI_SUTUN:
            s = s.yeni(metin=",")
        elif t == DIZI_SATIR:
            s = s.yeni(metin=";")
        elif t == HATA:
            s = s.yeni(metin=s.deger)
        elif t == BASVURU:
            b = s.deger
            onek = ""
            if isinstance(b.sayfa, str):
                sayfa = _sayfa_bul(kitap, b.sayfa)
                if sayfa is None:
                    raise FormulHatasi(f"Başvurulan sayfa bulunamadı: {b.sayfa}", s.konum)
                b = replace(b, sayfa=sayfa.kimlik)
                onek = f"[{sayfa.kimlik}]!"
            s = s.yeni(metin=onek + b.govde(), deger=b)
        cikti.append(s)
    saklanan = metne(cikti)
    agac = ayristir(sozcukle(saklanan, SAKLI))   # sözdizimi denetimi (kanonik biçimde)
    _arguman_denetle(agac)
    return "=" + saklanan


def gosterime(formul: str, kitap=None, hedef: Yerel = TR) -> str:
    """Saklanan formülü kullanıcıya (TR) ya da dışarıya (EN: .xlsx, pano) gösterilecek metne
    çevirir. Silinmiş sayfaya başvuru `#BAŞV!` olur. Çözümlenemeyen metin olduğu gibi döner."""
    if not formul.startswith("="):
        return formul
    try:
        sozcukler = sozcukle(formul[1:], SAKLI)
    except FormulHatasi:
        return formul
    cikti: List[str] = []
    for s in sozcukler:
        t = s.tur
        if t == FONK:
            cikti.append(adlar.turkcesi(s.metin) if hedef is TR else s.metin.upper())
        elif t == AD and s.metin.upper() in ("TRUE", "FALSE"):
            cikti.append(hedef.dogru if s.metin.upper() == "TRUE" else hedef.yanlis)
        elif t == SAYI:
            cikti.append(s.metin.replace(".", hedef.ondalik))
        elif t == AYRAC:
            cikti.append(hedef.arguman)
        elif t == DIZI_SUTUN:
            cikti.append(hedef.dizi_sutun)
        elif t == DIZI_SATIR:
            cikti.append(hedef.dizi_satir)
        elif t == HATA:
            cikti.append(hedef.hatalar.get(s.deger, s.deger))
        elif t == BASVURU:
            b = s.deger
            if isinstance(b.sayfa, int):
                sayfa = kitap.sayfa_kimlikle(b.sayfa) if kitap is not None else None
                if sayfa is None:
                    cikti.append(hedef.hatalar["#REF!"])
                    continue
                cikti.append(sayfa_oneki(sayfa.ad) + b.govde())
            elif isinstance(b.sayfa, str):
                cikti.append(sayfa_oneki(b.sayfa) + b.govde())
            else:
                cikti.append(b.govde())
        else:
            cikti.append(s.metin)
    return "=" + "".join(cikti)


def disa(formul: str, kitap=None) -> str:
    """Saklanan → .xlsx/pano (İngilizce, sayfa adlı)."""
    return gosterime(formul, kitap, EN)


def iceri(metin: str, kitap=None) -> str:
    """.xlsx'teki İngilizce formül → saklanan biçim."""
    return girdiden(metin, kitap, EN)


def formul_mu(metin: Optional[str]) -> bool:
    return bool(metin) and metin.startswith("=") and len(metin) > 1


def hucre_girdisi(metin: str, kitap=None):
    """Kullanıcının hücreye yazdığı metin → `Hucre` (formülse saklanan biçime çevrilmiş).
    Formül hatalıysa `FormulHatasi` (arayüz iletiyi gösterir, düzenleme açık kalır)."""
    from ..model.girdi import girdi_coz
    from ..model.sayfa import Hucre
    h = girdi_coz(metin)
    if h is not None and h.formul is not None:
        return Hucre(None, girdiden(h.formul, kitap))
    return h


def hucre_metni(hucre, kitap=None) -> str:
    """Düzenleme kutusu/formül çubuğu metni: formül Türkçe gösterilir, değilse `duzenleme_metni`."""
    from ..model.girdi import duzenleme_metni
    if hucre is not None and hucre.formul is not None:
        return gosterime(hucre.formul, kitap)
    return duzenleme_metni(hucre)
