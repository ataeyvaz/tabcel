"""KVKK Temizleyici dosya düzeyi (Faz 9d): özgün .xlsx'in meta verisi / üst-alt bilgisi taraması (salt okunur), temiz kopyanın
yazılması (özgün yola yazma engelli) ve **yazılan dosyanın tüm parçalarında** özgün değer kalmadığının doğrulanması.

Temiz kopya Tabcel'in kendi yazıcısıyla sıfırdan üretilir (`xlsx_io.kaydet`): özgün dosyanın yazarı, son kaydeden, şirket, üst/alt
bilgi, dizili yorum yazarları, özel özellikler gibi parçalar dosyaya HİÇ taşınmaz; bu modül onları yalnız kullanıcıya bildirmek için okur."""
import html
import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple
from xml.etree import ElementTree

from ..model import kimlik
from ..model.temizle import TemizKopya
from . import xlsx_io

_META_PARCALARI = {
    "docProps/core.xml": {"creator": "Yazar", "lastModifiedBy": "Son kaydeden", "title": "Başlık", "subject": "Konu",
                          "keywords": "Anahtar sözcükler", "description": "Açıklama", "category": "Kategori"},
    "docProps/app.xml": {"Company": "Şirket", "Manager": "Yönetici"},
}
_UST_ALT = re.compile(rb"<(?:oddHeader|oddFooter|evenHeader|evenFooter|firstHeader|firstFooter)>(.*?)</", re.S)


@dataclass
class DosyaMeta:
    """Özgün dosyadaki, kitap modelinde bulunmayan ve temiz kopyaya taşınmayacak içerik."""
    alanlar: List[Tuple[str, str]] = field(default_factory=list)      # (alan adı, değer) — meta veri
    ust_alt: List[str] = field(default_factory=list)                   # üst/alt bilgi metinleri
    ozel_ozellik: int = 0
    resim: int = 0                                                     # taranamaz
    bulgular: List[kimlik.Bulgu] = field(default_factory=list)         # üst/alt bilgi ve meta değerlerinde bulunan kişisel veri


def _yerel(etiket: str) -> str:
    return etiket.rsplit("}", 1)[-1]


def meta_tara(yol: str) -> DosyaMeta:
    """`yol` bir .xlsx ise meta veri/üst-alt bilgi/özel özellik/resim sayısını okur (okunamazsa boş). Dosyaya yazmaz."""
    m = DosyaMeta()
    try:
        with zipfile.ZipFile(yol) as z:
            for ad in z.namelist():
                if ad in _META_PARCALARI:
                    try:
                        kok = ElementTree.fromstring(z.read(ad))
                    except ElementTree.ParseError:
                        continue
                    for e in kok:
                        alan = _META_PARCALARI[ad].get(_yerel(e.tag))
                        if alan and (e.text or "").strip():
                            m.alanlar.append((alan, e.text.strip()))
                elif ad == "docProps/custom.xml":
                    try:
                        kok = ElementTree.fromstring(z.read(ad))
                    except ElementTree.ParseError:
                        continue
                    for e in kok:
                        ozel = e.get("name", "")
                        if not ozel.startswith("Tabcel"):
                            m.ozel_ozellik += 1
                elif ad.startswith("xl/worksheets/sheet") and ad.endswith(".xml"):
                    for h in _UST_ALT.findall(z.read(ad)):
                        t = h.decode("utf-8", "replace").replace("&amp;", "&").strip()
                        if t:
                            m.ust_alt.append(t)
                elif ad.startswith("xl/media/"):
                    m.resim += 1
    except (OSError, zipfile.BadZipFile):
        return DosyaMeta()
    for _, v in m.alanlar:
        m.bulgular += kimlik.tara_metin(v)
    for t in m.ust_alt:
        m.bulgular += kimlik.tara_metin(t)
    return m


class OzgunYolaYazmaHatasi(Exception):
    """Hedef, özgün dosyanın kendisi (ya da aynı dosyaya işaret ediyor)."""


def ayni_dosya_mi(a: str, b: Optional[str]) -> bool:
    if not b:
        return False
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


_PARCA = re.compile(r"[>\"]([^<>\"]{6,})(?=[<\"])")           # XML metin düğümleri ve öznitelik değerleri
_ADAY_ON = re.compile(r"\d{6,}|@|[Tt][Rr]\s?\d|\d[\d\s().\-]{8,}\d")   # kişisel veri adayı olabilecek parça (ön süzgeç)


def _bicimler(m: str) -> Set[str]:
    sade = re.sub(r"[\s\-().]", "", m)
    return {m, m.strip(), sade, re.sub(r"\D", "", m)}


def dosya_dogrula(yol: str, yasak: Set[str]) -> List[str]:
    """Dosyanın TÜM parçalarında (açılmış zip içeriği) yasak değer arar; bulunanların (kısaltılmış) listesi döner, boşsa temiz.
    Her XML metin düğümü/öznitelik değeri için: (1) değerin kendisi ve boşluksuz/yalnız rakam biçimi yasak kümesinde mi,
    (2) düğüm içinde `kimlik.tara_metin` ile bulunan her veri yasak kümesinde mi. (Büyük kümede tüm metni her değerle taramak
    saatler sürer; düğüm düğüm bakmak doğrusaldır.) Düğümün içine gömülü, kişisel veri biçimine uymayan (ör. cümle içindeki ad)
    özgün metinler bu yolla bulunamaz — bunlar zaten taranmaz/maskelenmez."""
    bulunan: List[str] = []
    if not yasak:
        return bulunan
    with zipfile.ZipFile(yol) as z:
        for ad in z.namelist():
            veri = z.read(ad).decode("utf-8", "ignore")
            goruldu: Set[str] = set()
            for m in _PARCA.finditer(veri):
                parca = m.group(1)
                if parca in goruldu:
                    continue
                goruldu.add(parca)
                if "&" in parca:
                    parca = html.unescape(parca)
                aday = [parca] if parca in yasak or _bicimler(parca) & yasak else []
                if not aday and _ADAY_ON.search(parca):
                    for b in kimlik.tara_metin(parca):
                        if _bicimler(b.metin) & yasak:
                            aday.append(b.metin)
                for a in aday:
                    bulunan.append(f"{ad}: {a[:2]}…{a[-2:]}")
    return bulunan


class DogrulamaHatasi(Exception):
    """Yazılan temiz dosyada özgün değer bulundu; dosya silindi."""


def temiz_yaz(tk: TemizKopya, yol: str, ozgun_yol: Optional[str] = None, parola: Optional[str] = None):
    """Temiz kopyayı `yol`a yazar; ardından dosyayı doğrular. Özgün yola yazılamaz (`OzgunYolaYazmaHatasi`). Doğrulama
    başarısızsa dosya silinir ve `DogrulamaHatasi` fırlar. Döner: yazma raporu."""
    if ayni_dosya_mi(yol, ozgun_yol):
        raise OzgunYolaYazmaHatasi("Temiz kopya özgün dosyanın üzerine yazılamaz; başka bir ad ya da klasör seçin.")
    if os.path.exists(yol) and os.path.isdir(yol):
        raise xlsx_io.XlsxHatasi("Hedef bir klasör.")
    rapor = xlsx_io.kaydet(tk.kitap, yol, parola)
    if not parola:
        kalan = dosya_dogrula(yol, tk.yasak)
        if kalan:
            try:
                os.remove(yol)
            except OSError:
                pass
            raise DogrulamaHatasi("Temiz dosyada özgün veri bulundu, dosya silindi: " + "; ".join(kalan[:5]))
    return rapor
