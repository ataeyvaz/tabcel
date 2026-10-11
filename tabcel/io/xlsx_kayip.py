"""Excel'de değiştirilmiş grafiklerde Tabcel'in modelleyemediği öğelerin TESPİTİ (T10; `t10_xlsx_kayip_tasarim.md`).
Qt yok. Her grafik parçası (`xl/charts/chartN.xml`) Tabcel imi ne olursa olsun doğrudan taranır; kural listesi kapalıdır.

- **A (yapısal kayıp):** her dosyada uyarılır (eğilim çizgisi, ikincil eksen, gradyan…).
- **B (biçim):** yalnız Tabcel imi VARKEN uyarılır (imsiz dosyada genel "uyarlandı" iletisi zaten kapsar).
Sahte uyarı olmaması esastır: Tabcel'in yazdığı ve Excel'den aç-kaydet geçmiş dosya uyarısız kalmalı (Excel aç-kaydette
`showBubbleSize=1`, dağılım serisine `smooth=1`, `schemeClr` pasta dilimleri yazar → kurallar buna göre kurulmuştur).
"""
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Dict, List, Optional, Tuple

from .. import APP_NAME
from ..model.grafik_cizim import palet_rengi

_C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_C15 = "{http://schemas.microsoft.com/office/drawing/2012/chart}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_SS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

_DESTEKLENEN = {"barChart", "lineChart", "pieChart", "doughnutChart", "areaChart", "scatterChart"}
_TUM_GRUPLAR = _DESTEKLENEN | {"bar3DChart", "line3DChart", "pie3DChart", "area3DChart", "radarChart", "bubbleChart",
                               "stockChart", "surfaceChart", "surface3DChart", "ofPieChart"}
_EKSENLER = {"valAx", "catAx", "dateAx", "serAx"}
_ACIK = ("1", "true")
_EN_COK_SATIR = 3
_EN_BUYUK_PARCA = 40 * 1024 * 1024               # bu kadar büyük grafik XML'i taranmaz (bozuk/kötü niyetli)


# Excel her seriye değer/etiket ÖNBELLEĞİ yazar (100.000 noktalı grafikte MB'larca `pt`): kurallar bunlara bakmaz →
# ayrıştırmadan önce ayıklanır (1,5 sn → onlarca ms).
_ONBELLEK = re.compile(rb"<((?:\w+:)?(?:numCache|strCache|multiLvlStrCache|dlblRangeCache))\b[^>]*?(?:/>|>.*?</\1\s*>)", re.S)


def _sadelestir(xml: bytes) -> bytes:
    return _ONBELLEK.sub(b"", xml) if len(xml) > 65536 else xml


def _yerel(e) -> str:
    return e.tag.rsplit("}", 1)[-1]


def _val(e, ad: str, varsayilan: Optional[str] = None) -> Optional[str]:
    x = e.find(_C + ad) if e is not None else None
    return x.get("val", "1") if x is not None else varsayilan


def _ekle(liste: List[str], ad: str) -> None:
    if ad not in liste:
        liste.append(ad)


def grafik_ozellikleri(xml: bytes) -> Tuple[List[str], List[str]]:
    """`(A, B)` etiket listeleri (kural sırasıyla, yinelenmesiz). Bozuk XML ya da desteklenmeyen grafik türü → boş."""
    xml_k = _sadelestir(xml)
    try:
        k = ET.fromstring(xml_k)
    except ET.ParseError:
        return [], []
    pa = k.find(f"{_C}chart/{_C}plotArea")
    if pa is None:
        return [], []
    gruplar = [e for e in pa if _yerel(e) in _TUM_GRUPLAR]
    if not gruplar or any(_yerel(g) not in _DESTEKLENEN for g in gruplar):
        return [], []                                    # desteklenmeyen tür: zaten "N grafik desteklenmiyor" uyarısı var
    a: List[str] = []
    b: List[str] = []
    eksenler = [e for e in pa if _yerel(e) in _EKSENLER]
    # A1/A2
    if k.find(f".//{_C}ser/{_C}trendline") is not None:
        _ekle(a, "eğilim çizgisi")
    if k.find(f".//{_C}ser/{_C}errBars") is not None:
        _ekle(a, "hata çubukları")
    # A3/A4
    if len(eksenler) > 2:
        _ekle(a, "ikincil eksen")
    if len(gruplar) > 1:
        _ekle(a, "birleşik grafik")
    # A5
    if any(k.find(f".//{_A}{t}") is not None for t in ("gradFill", "pattFill", "blipFill")):
        _ekle(a, "gradyan/desen/resim dolgusu")
    # A6/A7
    for ax in eksenler:
        sc = ax.find(_C + "scaling")
        if sc is not None and (sc.find(_C + "logBase") is not None or _val(sc, "orientation") == "maxMin"):
            _ekle(a, "eksen ölçeği (logaritmik/ters)")
        if any(ax.find(_C + t) is not None for t in ("majorUnit", "minorUnit", "dispUnits")):
            _ekle(a, "eksen ölçeği (birim)")
        if len(eksenler) <= 2 and _val(ax, "delete") in _ACIK:
            _ekle(a, "gizlenmiş eksen")
    # grup/seri kuralları
    for g in gruplar:
        t = _yerel(g)
        pasta = t in ("pieChart", "doughnutChart")
        if any(g.find(_C + x) is not None for x in ("upDownBars", "dropLines", "hiLowLines", "serLines")):
            _ekle(a, "yardımcı çizgiler")
        dl_grup = g.find(_C + "dLbls")
        etiketli: List[bool] = []
        for s in g.findall(_C + "ser"):
            for dp in s.findall(_C + "dPt"):
                idx = int(_val(dp, "idx", "0") or 0)
                if not pasta:
                    _ekle(a, "tek tek biçimlendirilmiş veri noktası")
                else:
                    dolgu = dp.find(f"{_C}spPr/{_A}solidFill")
                    if dolgu is not None:
                        rgb, tema = dolgu.find(_A + "srgbClr"), dolgu.find(_A + "schemeClr")
                        if rgb is not None:
                            if len(rgb) or ("#" + rgb.get("val", "").upper()) != palet_rengi(idx).upper():
                                _ekle(a, "tek tek biçimlendirilmiş veri noktası")
                        elif tema is not None and not len(tema) and tema.get("val") == f"accent{idx % 6 + 1}":
                            _ekle(b, "tema rengi")       # Excel'in sıfırdan çizdiği pasta: A değil, B4
                        else:
                            _ekle(a, "tek tek biçimlendirilmiş veri noktası")
                    if _val(dp, "explosion", "0") != "0":
                        _ekle(a, "ayrık pasta dilimi")
            if s.find(_C + "explosion") is not None and _val(s, "explosion", "0") != "0":
                _ekle(a, "ayrık pasta dilimi")
            sd = s.find(_C + "dLbls")
            for dl in (d for d in (dl_grup, sd) if d is not None):
                if (any(_val(dl, x) in _ACIK for x in ("showCatName", "showSerName", "showLegendKey"))
                        or dl.find(_C + "dLbl") is not None or (pasta and _val(dl, "showVal") in _ACIK)):
                    _ekle(a, "veri etiketi ayrıntıları")
            etiketli.append(sd is not None and _val(sd, "showVal") in _ACIK)
            if s.find(f".//{_C15}datalabelsRange") is not None:
                _ekle(a, "veri etiketi ayrıntıları")
            if t == "lineChart":
                if _val(s, "smooth") in _ACIK:
                    _ekle(a, "düzgünleştirilmiş çizgi")
                sym = s.find(f"{_C}marker/{_C}symbol")
                if ((sym is not None and sym.get("val") != "none")
                        or (s.find(_C + "marker") is None and _val(g, "marker") in _ACIK)):
                    _ekle(a, "çizgi işaretçileri")
            if t == "scatterChart":
                ln = s.find(f"{_C}spPr/{_A}ln")
                if ln is None or ln.find(_A + "noFill") is None:
                    _ekle(a, "dağılım grafiğinde çizgi")
            for yol in (f"{_C}spPr/{_A}solidFill", f"{_C}spPr/{_A}ln/{_A}solidFill",
                        f"{_C}marker/{_C}spPr/{_A}solidFill"):
                f = s.find(yol)
                if f is not None and (f.find(_A + "srgbClr") is None or len(f.find(_A + "srgbClr"))):
                    _ekle(b, "tema rengi")
        if any(etiketli) and not all(etiketli) and not (dl_grup is not None and _val(dl_grup, "showVal") in _ACIK):
            _ekle(a, "veri etiketi ayrıntıları")             # etiket yalnız bazı serilerde
        if t == "barChart" and (_val(g, "gapWidth", "150") != "150" or _val(g, "overlap", "0") not in ("0", "100")):
            _ekle(b, "çubuk aralığı")
    # A13/A14/A16/A17
    ch = k.find(_C + "chart")
    if _val(ch, "dispBlanksAs", "gap") != "gap":
        _ekle(a, "boş hücre gösterimi")
    if _val(ch, "plotVisOnly", "1") in ("0", "false"):
        _ekle(a, "gizli hücre verisi")
    if pa.find(_C + "dTable") is not None:
        _ekle(a, "veri tablosu")
    if re.search(rb"filtered\w*Series", xml_k):
        _ekle(a, "filtrelenmiş (gizli) seri")                # öğe adları Excel'de denenmedi (belirsiz)
    # B1/B2/B3
    if k.find(f".//{_C}txPr") is not None or any(r.get("sz") or r.get("b") == "1"
                                                   for r in k.iter() if _yerel(r) in ("defRPr", "rPr")):
        _ekle(b, "yazı biçimi")
    for yol in (f"{_C}spPr", f"{_C}chart/{_C}plotArea/{_C}spPr", f"{_C}chart/{_C}title/{_C}spPr",
                f"{_C}chart/{_C}legend/{_C}spPr"):
        if k.find(yol) is not None:
            _ekle(b, "alan/çerçeve biçimi")
    if k.find(f".//{_MC}AlternateContent") is not None:
        _ekle(b, "grafik stili")
    # A5 notu: grafik stili (ChartStyle) gradyan da ekler; yukarıdaki gradFill kuralı onu yakalar
    return a, b


def grafik_basligi(xml: bytes) -> Optional[str]:
    """Grafik başlığının düz metni; yoksa/ayrıştırılamıyorsa None."""
    try:
        k = ET.fromstring(_sadelestir(xml))
    except ET.ParseError:
        return None
    t = k.find(f"{_C}chart/{_C}title")
    if t is None:
        return None
    metin = "".join(x.text or "" for x in t.iter(_A + "t")).strip()
    return metin or None


def _rels(z: zipfile.ZipFile, yol: str) -> Dict[str, str]:
    """`yol` parçasının ilişki dosyası: kimlik → hedef (parça yolu, `xl/…` mutlak)."""
    klasor, ad = posixpath.split(yol)
    rels = posixpath.join(klasor, "_rels", ad + ".rels")
    try:
        k = ET.fromstring(z.read(rels))
    except (KeyError, ET.ParseError):
        return {}
    sonuc = {}
    for r in k.iter(_PKG + "Relationship"):
        hedef = r.get("Target", "")
        if r.get("TargetMode") == "External":
            continue
        sonuc[r.get("Id", "")] = (hedef.lstrip("/") if hedef.startswith("/")
                                  else posixpath.normpath(posixpath.join(klasor, hedef)))
    return sonuc


def grafik_parcalari(z: zipfile.ZipFile) -> List[Tuple[Optional[str], int, str]]:
    """Dosyadaki her grafik parçası: `(sayfa adı | None, sayfadaki sırası [1'den], parça yolu)`. Sayfa → çizim →
    grafik ilişki zinciri izlenir; zincirde bulunamayan parça `sayfa adı None` ile sonda gelir."""
    adlar = set(z.namelist())
    tum = sorted((n for n in adlar if re.match(r"^xl/charts/chart\d+\.xml$", n)),
                 key=lambda n: int(re.findall(r"\d+", n)[-1]))
    bulunan: List[Tuple[Optional[str], int, str]] = []
    gorulen = set()
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        wb_rels = _rels(z, "xl/workbook.xml")
        for sh in wb.iter(_SS + "sheet"):
            sayfa_yolu = wb_rels.get(sh.get(_R + "id", ""))
            if not sayfa_yolu or sayfa_yolu not in adlar:
                continue                                    # grafik sayfası vb.: atlanır
            sira = 0
            for _, hedef in _rels(z, sayfa_yolu).items():
                if not re.match(r"^xl/drawings/drawing\d+\.xml$", hedef) or hedef not in adlar:
                    continue
                cizim = ET.fromstring(z.read(hedef))
                cizim_rels = _rels(z, hedef)
                for ch in cizim.iter(_C + "chart"):
                    parca = cizim_rels.get(ch.get(_R + "id", ""))
                    if parca in tum and parca not in gorulen:
                        sira += 1
                        gorulen.add(parca)
                        bulunan.append((sh.get("name"), sira, parca))
    except (KeyError, ET.ParseError):
        pass
    for n in tum:
        if n not in gorulen:
            bulunan.append((None, 0, n))
    return bulunan


def _ad(baslik: Optional[str], sira: int, sayfa: Optional[str], tamlama: str) -> str:
    """`'Aylık satış' grafiğinde (Sayfa1)` / `3. grafikte (Sayfa1)`; `tamlama` 'de' ya da 'in'."""
    ek = {"de": ("grafiğinde", "grafikte"), "in": ("grafiğinin", "grafiğin")}[tamlama]
    ad = f"'{baslik}' {ek[0]}" if baslik else (f"{sira}. {ek[1]}" if sira else f"bir {ek[1]}")
    return ad + (f" ({sayfa})" if sayfa else "")


def kayip_uyarilari(yol: str, im: bool) -> List[str]:
    """Dosyadaki grafiklerde Tabcel'in desteklemediği öğeler için uyarı satırları (en çok 3 + özet satırı).
    `im`: dosyada Tabcel imi var mı (B sınıfı yalnız o zaman). Dosya açılamazsa boş."""
    satirlar: List[str] = []
    try:
        with zipfile.ZipFile(yol) as z:
            for sayfa, sira, parca in grafik_parcalari(z):
                if z.getinfo(parca).file_size > _EN_BUYUK_PARCA:
                    continue
                xml = z.read(parca)
                a, b = grafik_ozellikleri(xml)
                b = b if im else []
                if not a and not b:
                    continue
                baslik = grafik_basligi(xml)
                if a:
                    metin = (f"{_ad(baslik, sira, sayfa, 'de')} {APP_NAME}'in desteklemediği öğeler var: {', '.join(a)}"
                             + (f"; Excel biçimi: {', '.join(b)}" if b else "") + ". Kaydederseniz bunlar kaybolur.")
                else:
                    metin = (f"{_ad(baslik, sira, sayfa, 'in')} Excel'de değiştirilen biçimi ({', '.join(b)}) kaydedince "
                             f"{APP_NAME} varsayılanına döner.")
                satirlar.append(metin)
    except (zipfile.BadZipFile, OSError, KeyError):
        return []
    if len(satirlar) > _EN_COK_SATIR:
        fazla = len(satirlar) - _EN_COK_SATIR
        satirlar = satirlar[:_EN_COK_SATIR] + [f"…ve {fazla} grafikte daha desteklenmeyen öğe var; kaydederseniz kaybolur."]
    return satirlar
