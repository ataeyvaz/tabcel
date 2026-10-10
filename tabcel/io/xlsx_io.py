"""`.xlsx` aç/kaydet (Faz 4 / 4a). Qt yok.

Okuma/yazma openpyxl ile; biçim eşlemesi `model/stil.py`'ye, formül eşlemesi `formul/ceviri.py`'ye dayanır
(saklanan formül kanonik İngilizce + sayfa kimliği; dosyada İngilizce + sayfa adı).

Bilinen sınırlar (her açılışta `Rapor`'a yazılır, arayüz bilgi çubuğunda gösterir):
- openpyxl grafik/resim/pivot/makro/koşullu biçim/veri doğrulama/yorumları korumaz → `Rapor.veri_kaybi`
- kaydedilen formüllerin önbellek değeri yazılmaz (Excel açınca yeniden hesaplar)
- tema renkleri varsayılan Office teması varsayımıyla RGB'ye çevrilir (§8b)
"""
import math
import os
import re
import zipfile
from copy import copy
from xml.etree import ElementTree
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import COLOR_INDEX
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.utils.datetime import to_excel

from ..formul import ceviri
from ..formul.sozcuk import FormulHatasi
from ..model import olcu
from ..model.ad import AdHatasi, TanimliAd, ad_dogrula
from ..model.adres import MAX_COL, MAX_ROW, Aralik
from ..model.deger import Hata, hata_bul
from ..model.sayfa import CalismaKitabi, Hucre, Sayfa
from ..model.sayfa_yapisi import SayfaYapisi
from ..model.stil import Kenarlik, Stil

# --- eşleme tabloları -------------------------------------------------------------------------
_CIZGI_YAZ = {"ince": "thin", "orta": "medium", "kalin": "thick", "kesikli": "dashed", "noktali": "dotted",
              "cift": "double", "sac": "hair"}
_CIZGI_OKU = {v: k for k, v in _CIZGI_YAZ.items()}
_CIZGI_OKU.update({"mediumDashed": "kesikli", "dashDot": "kesikli", "mediumDashDot": "kesikli",
                   "dashDotDot": "kesikli", "mediumDashDotDot": "kesikli", "slantDashDot": "kesikli"})
_YATAY_YAZ = {"genel": "general", "sol": "left", "orta": "center", "sag": "right", "doldur": "fill",
              "iki_yana": "justify", "secim_ortasi": "centerContinuous"}
_YATAY_OKU = {v: k for k, v in _YATAY_YAZ.items()}
_YATAY_OKU["distributed"] = "iki_yana"
_DIKEY_YAZ = {"ust": "top", "orta": "center", "alt": "bottom"}
_DIKEY_OKU = {v: k for k, v in _DIKEY_YAZ.items()}
_DIKEY_OKU.update({"justify": "orta", "distributed": "orta"})
_ALTI_YAZ = {"tek": "single", "cift": "double"}
_ALTI_OKU = {"single": "tek", "double": "cift", "singleAccounting": "tek", "doubleAccounting": "cift"}

# Dosyada `_xlfn.` öneki isteyen (Excel 2010+ ile gelen) işlevler. Motor kayıtlı olmayanlar da buradadır:
# `_xlfn.STDEV.S` dosyadan okununca ön ek motorda düşer (`formul/ceviri.py`), yazarken geri eklenmezse Excel
# işlevi tanımaz (#AD?). Liste Microsoft'un "_xlfn. öneki görünüyor" belgesinden; tam doğrulanmadı (§8b).
_XLFN = {
    "CONCAT", "DAYS", "IFNA", "IFS", "MAXIFS", "MINIFS", "SWITCH", "TEXTJOIN", "XLOOKUP", "XMATCH", "XOR",
    "ACOT", "ACOTH", "ARABIC", "BASE", "BETA.DIST", "BETA.INV", "BINOM.DIST", "BINOM.DIST.RANGE", "BINOM.INV",
    "BITAND", "BITLSHIFT", "BITOR", "BITRSHIFT", "BITXOR", "CEILING.MATH", "CEILING.PRECISE", "CHISQ.DIST",
    "CHISQ.DIST.RT", "CHISQ.INV", "CHISQ.INV.RT", "CHISQ.TEST", "CONFIDENCE.NORM", "CONFIDENCE.T", "COT", "COTH",
    "COVARIANCE.P", "COVARIANCE.S", "CSC", "CSCH", "DECIMAL", "ERF.PRECISE", "ERFC.PRECISE", "EXPON.DIST",
    "F.DIST", "F.DIST.RT", "F.INV", "F.INV.RT", "F.TEST", "FLOOR.MATH", "FLOOR.PRECISE", "FORECAST.LINEAR",
    "FORMULATEXT", "GAMMA", "GAMMA.DIST", "GAMMA.INV", "GAMMALN.PRECISE", "GAUSS", "HYPGEOM.DIST", "ISFORMULA",
    "ISOWEEKNUM", "LOGNORM.DIST", "LOGNORM.INV", "MODE.MULT", "MODE.SNGL", "MUNIT", "NEGBINOM.DIST", "NORM.DIST",
    "NORM.INV", "NORM.S.DIST", "NORM.S.INV", "NUMBERVALUE", "PDURATION", "PERCENTILE.EXC", "PERCENTILE.INC",
    "PERCENTRANK.EXC", "PERCENTRANK.INC", "PERMUTATIONA", "PHI", "POISSON.DIST", "QUARTILE.EXC", "QUARTILE.INC",
    "RANK.AVG", "RANK.EQ", "RRI", "SEC", "SECH", "SHEET", "SHEETS", "SKEW.P", "STDEV.P", "STDEV.S", "T.DIST",
    "T.DIST.2T", "T.DIST.RT", "T.INV", "T.INV.2T", "T.TEST", "UNICHAR", "UNICODE", "VAR.P", "VAR.S",
    "WEIBULL.DIST", "Z.TEST", "UNIQUE", "SEQUENCE", "RANDARRAY", "SORTBY", "LET", "LAMBDA", "TEXTBEFORE",
    "TEXTAFTER", "TEXTSPLIT", "VSTACK", "HSTACK", "TAKE", "DROP", "CHOOSECOLS", "CHOOSEROWS", "TOCOL", "TOROW",
    "EXPAND", "WRAPCOLS", "WRAPROWS", "XMATCH", "BYROW", "BYCOL", "MAP", "REDUCE", "SCAN", "MAKEARRAY",
}
_XLWS = {"SORT", "FILTER"}                      # dosyada `_xlfn._xlws.` önekiyle
_FN_ADI = re.compile(r"\b([A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*)\(")
_XLFN_OKU = re.compile(r"_xlfn\.(?:_xlws\.)?", re.IGNORECASE)

# Varsayılan Office teması (belirsiz: yeni Excel 365 teması farklı olabilir — surec.md §8b)
_TEMA = ["FFFFFF", "000000", "E7E6E6", "44546A", "4472C4", "ED7D31", "A5A5A5", "FFC000", "5B9BD5", "70AD47",
         "0563C1", "954F72"]                                       # son ikisi: köprü / izlenmiş köprü
_TEMA_SIRA = ("lt1", "dk1", "lt2", "dk2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
              "hlink", "folHlink")


def _tema_oku(wb) -> list:
    """Dosyanın kendi temasından (`xl/theme/theme1.xml`) 12 renk; okunamayan varsayılan Office temasıyla kalır."""
    tema = list(_TEMA)
    kaynak = getattr(wb, "loaded_theme", None)
    if not kaynak:
        return tema
    try:
        xml = kaynak.decode("utf-8", errors="replace") if isinstance(kaynak, bytes) else str(kaynak)
        for i, ad in enumerate(_TEMA_SIRA):
            m = re.search(rf"<a:{ad}>\s*<a:(?:srgbClr val=\"([0-9A-Fa-f]{{6}})\"|sysClr [^>]*lastClr=\"([0-9A-Fa-f]{{6}})\")",
                          xml)
            if m:
                tema[i] = (m.group(1) or m.group(2)).upper()
    except Exception:                                            # bozuk tema: varsayılan
        pass
    return tema

_KAGIT_KODU = {"Letter": 1, "Legal": 5, "A3": 8, "A4": 9, "A5": 11}
_KAGIT_ADI = {v: k for k, v in _KAGIT_KODU.items()}
CM_INC = 2.54

VARSAYILAN_YAZI_TIPI = "Calibri"
VARSAYILAN_BOYUT = 11.0


@dataclass
class Rapor:
    """Açma/kaydetme sonucu: kullanıcıya bildirilecek uyarılar."""
    uyarilar: List[str] = field(default_factory=list)
    veri_kaybi: bool = False          # kaydedilirse dosyadan çıkacak öğe var (grafik, resim, makro…)

    def ekle(self, metin: str, kayip: bool = False) -> None:
        if metin not in self.uyarilar:
            self.uyarilar.append(metin)
        self.veri_kaybi = self.veri_kaybi or kayip


class XlsxHatasi(Exception):
    """Dosya açılamadı/yazılamadı (kullanıcıya gösterilecek Türkçe ileti)."""


# --- tarama (zip; openpyxl'e güvenmeden) ----------------------------------------------------------
_TARA = (
    (re.compile(r"^xl/charts/"), "grafik", True),
    (re.compile(r"^xl/(drawings/|media/)"), "resim/şekil", True),
    (re.compile(r"^xl/pivot(Tables|Cache)/"), "pivot tablo", True),
    (re.compile(r"^xl/vbaProject\.bin$"), "makro (VBA)", True),
    (re.compile(r"^xl/externalLinks/"), "dış bağlantı", True),
    (re.compile(r"^xl/(comments|threadedComments)"), "yorum/not", True),
    (re.compile(r"^xl/slicers/|^xl/timelines/"), "dilimleyici", True),
    (re.compile(r"^xl/tables/"), "Excel tablosu", True),
)
# sayfa XML'inde aranan, openpyxl ile korunamayan/bozulan öğeler
_SAYFA_ISARETLERI = (
    (b"<conditionalFormatting", "koşullu biçim"), (b"<dataValidations", "veri doğrulama"),
    (b"<autoFilter", "filtre"), (b"<hyperlinks", "köprü"), (b"outlineLevel=", "satır/sütun gruplama"),
    (b"<headerFooter", "üst/alt bilgi"), (b"<sheetProtection", "sayfa koruması"),
    (b't="array"', "dizi formülü (normal formüle dönüştürülür)"),
)


def tara(yol: str) -> Rapor:
    """Dosyada bu sürümün korumadığı öğe var mı (zip içindeki yollara ve sayfa XML'ine bakar)."""
    r = Rapor()
    try:
        with zipfile.ZipFile(yol) as z:
            adlar = z.namelist()
            bulunan = {}
            for ad in adlar:
                for rx, ne, kayip in _TARA:
                    if rx.search(ad):
                        bulunan[ne] = kayip
            for ad in adlar:
                if re.match(r"^xl/worksheets/sheet\d+\.xml$", ad):
                    xml = z.read(ad)
                    for isaret, ne in _SAYFA_ISARETLERI:
                        if isaret in xml and (isaret != b't="array"' or re.search(rb'<f[^>]*t="array"', xml)):
                            bulunan[ne] = True
    except (zipfile.BadZipFile, KeyError, OSError):
        return r
    for ne in bulunan:
        r.ekle(f"Bu dosyada {ne} var; kaydederseniz dosyadan çıkarılır.", True)
    return r


# --- renk ---------------------------------------------------------------------------------------
def _renk_oku(c, tema=_TEMA) -> Optional[str]:
    """openpyxl `Color` → '#RRGGBB' (tema/indeksli renkler çözülür); belirsizse None."""
    if c is None:
        return None
    try:
        if c.type == "rgb" and isinstance(c.rgb, str) and len(c.rgb) in (6, 8):
            return "#" + c.rgb[-6:].upper()
        if c.type == "indexed" and isinstance(c.indexed, int) and 0 <= c.indexed < len(COLOR_INDEX):
            return "#" + COLOR_INDEX[c.indexed][-6:].upper()
        if c.type == "theme" and isinstance(c.theme, int) and 0 <= c.theme < len(tema):
            return _renk_ton("#" + tema[c.theme], c.tint or 0.0)
    except (AttributeError, TypeError, ValueError):
        pass
    return None


def _renk_ton(renk: str, ton: float) -> str:
    """Excel `tint`: HLS açıklığı üzerinden aç/koyulaştır."""
    if not ton:
        return renk
    import colorsys
    r, g, b = (int(renk[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l * (1 + ton) if ton < 0 else l * (1 - ton) + ton
    r, g, b = colorsys.hls_to_rgb(h, min(max(l, 0.0), 1.0), s)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


# --- stil ⇄ openpyxl ------------------------------------------------------------------------------
def _stil_yaz(st: Stil):
    font = Font(name=st.yazi_tipi or VARSAYILAN_YAZI_TIPI, sz=st.boyut or VARSAYILAN_BOYUT,
                b=st.kalin, i=st.italik, strike=st.ustu_cizili,
                u=_ALTI_YAZ.get(st.alti_cizili), color=st.yazi_rengi[1:] if st.yazi_rengi else None)
    fill = PatternFill("solid", fgColor=st.dolgu[1:], bgColor=st.dolgu[1:]) if st.dolgu else PatternFill()

    def kenar(c):
        return Side(style=_CIZGI_YAZ[c[0]], color=c[1][1:]) if c else Side()
    border = Border(top=kenar(st.kenar.ust), bottom=kenar(st.kenar.alt),
                    left=kenar(st.kenar.sol), right=kenar(st.kenar.sag))
    align = Alignment(horizontal=_YATAY_YAZ[st.yatay], vertical=_DIKEY_YAZ[st.dikey],
                      indent=st.girinti, wrap_text=st.kaydir or None)
    return font, fill, border, align, st.sayi_bicimi


def _stil_oku(font, fill, border, align, sayi_bicimi: str, tema=_TEMA) -> Stil:
    yazi_tipi = font.name if font and font.name and font.name != VARSAYILAN_YAZI_TIPI else None
    boyut = float(font.sz) if font and font.sz and float(font.sz) != VARSAYILAN_BOYUT else None
    if boyut is not None and not 1 <= boyut <= 409:
        boyut = None
    dolgu = None
    if fill is not None and fill.fill_type == "solid":
        dolgu = _renk_oku(fill.fgColor, tema)
    k = {}
    if border is not None:
        for yon, kn in (("ust", border.top), ("alt", border.bottom), ("sol", border.left), ("sag", border.right)):
            if kn is not None and kn.style:
                k[yon] = (_CIZGI_OKU.get(kn.style, "ince"), _renk_oku(kn.color, tema) or "#000000")
    yatay = _YATAY_OKU.get(getattr(align, "horizontal", None) or "general", "genel")
    dikey = _DIKEY_OKU.get(getattr(align, "vertical", None) or "bottom", "alt")
    girinti = int(getattr(align, "indent", 0) or 0)
    return Stil(
        yazi_tipi=yazi_tipi, boyut=boyut,
        kalin=bool(font and font.b), italik=bool(font and font.i), ustu_cizili=bool(font and font.strike),
        alti_cizili=_ALTI_OKU.get(font.u, "yok") if font and font.u else "yok",
        yazi_rengi=_renk_oku(font.color, tema) if font else None, dolgu=dolgu, kenar=Kenarlik(**k),
        yatay=yatay, dikey=dikey, girinti=min(max(girinti, 0), 15),
        kaydir=bool(getattr(align, "wrap_text", False)), sayi_bicimi=sayi_bicimi or "General")


# --- formül ---------------------------------------------------------------------------------------
def _oneki_ekle(g) -> str:
    ad = g.group(1).upper()
    if ad in _XLWS:
        return "_xlfn._xlws." + ad + "("
    if ad in _XLFN:
        return "_xlfn." + ad + "("
    return g.group(0)


def _formul_yaz(formul: str, kitap) -> str:
    """Saklanan formül → dosyadaki metin (İngilizce, sayfa adlı, gerekli `_xlfn.` önekleriyle)."""
    m = ceviri.disa(formul, kitap)
    parcalar = m.split('"')               # çift tırnaklı metin sabitlerine dokunma (çift sayı = dışarıda)
    for i in range(0, len(parcalar), 2):
        parcalar[i] = _FN_ADI.sub(_oneki_ekle, parcalar[i])
    return '"'.join(parcalar)


def _formul_oku(metin: str, kitap) -> str:
    parcalar = metin.split('"')
    for i in range(0, len(parcalar), 2):
        parcalar[i] = _XLFN_OKU.sub("", parcalar[i])
    return ceviri.iceri('"'.join(parcalar), kitap)


# --- tanımlı adlar ---------------------------------------------------------------------------------
def _adlari_yaz(wb, kitap) -> None:
    """Tanımlı adlar: kitap kapsamlı `wb.defined_names`, sayfa kapsamlı `ws.defined_names`.
    Göreli başvurular A1'e göre saklanır (dosyadaki gibi)."""
    for tanim in kitap.adlar.values():
        d = DefinedName(tanim.ad, attr_text=_formul_yaz(tanim.formul, kitap)[1:],
                        hidden=True if tanim.gizli else None, comment=tanim.aciklama or None)
        if tanim.kapsam is None:
            wb.defined_names[tanim.ad] = d
            continue
        sayfa = kitap.sayfa_kimlikle(tanim.kapsam)
        if sayfa is not None:                        # kapsamı silinmiş sayfa olan ad yazılmaz
            wb[sayfa.ad].defined_names[tanim.ad] = d


def _adlari_oku(wb, kitap, sayfalar, rapor) -> None:
    """Dosyadaki tanımlı adları kitaba alır; çevrilemeyen (dış kitap başvurusu vb.) ya da geçersiz adlar
    atlanır ve raporlanır. `_xlnm.*` (yazdırma alanı vb.) sayfa yapısında işlenir."""
    kaynaklar = [(None, wb.defined_names)] + [(s.kimlik, ws.defined_names) for ws, s in sayfalar]
    atlanan = []
    for kapsam, depo in kaynaklar:
        for ad, d in depo.items():
            if ad.startswith("_xlnm.") or not d.attr_text:
                continue
            try:
                ad_dogrula(ad)
                formul = _formul_oku("=" + d.attr_text, kitap)
            except (AdHatasi, FormulHatasi):
                atlanan.append(ad)
                continue
            kitap.ad_yaz(TanimliAd(ad, formul, kapsam, d.comment or "", bool(d.hidden)))
    if atlanan:
        rapor.ekle(f"Çevrilemeyen tanımlı adlar atlandı: {', '.join(atlanan[:5])}"
                   f"{' …' if len(atlanan) > 5 else ''}; kaydederseniz dosyadan çıkarılır.", True)


# --- sayfa yapısı ----------------------------------------------------------------------------------
def _yapi_yaz(ws, y: SayfaYapisi) -> None:
    ws.page_setup.orientation = "landscape" if y.yon == "yatay" else "portrait"
    ws.page_setup.paperSize = _KAGIT_KODU[y.kagit]
    ws.page_setup.scale = None if y.sigdir_genislik else y.olcek
    if y.sigdir_genislik:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
    m = ws.page_margins
    m.top, m.bottom, m.left, m.right = (round(v / CM_INC, 4) for v in (y.ust, y.alt, y.sol, y.sag))
    ws.print_options.gridLines = y.kilavuz or None
    ws.print_options.horizontalCentered = y.yatay_ortala or None
    if y.alan is not None:
        ws.print_area = f"{get_column_letter(y.alan.ilk_sutun)}{y.alan.ilk_satir}:" \
                        f"{get_column_letter(y.alan.son_sutun)}{y.alan.son_satir}"
    if y.baslik_satirlari is not None:
        ws.print_title_rows = f"{y.baslik_satirlari[0]}:{y.baslik_satirlari[1]}"


def _yapi_oku(ws) -> SayfaYapisi:
    ps, m = ws.page_setup, ws.page_margins
    kw = {}
    if ps.orientation == "landscape":
        kw["yon"] = "yatay"
    kw["kagit"] = _KAGIT_ADI.get(ps.paperSize or 9, "A4")
    fit = bool(ws.sheet_properties.pageSetUpPr and ws.sheet_properties.pageSetUpPr.fitToPage)
    if fit:
        kw["sigdir_genislik"] = True
    elif ps.scale and 10 <= int(ps.scale) <= 400:
        kw["olcek"] = int(ps.scale)
    for ad, v in (("ust", m.top), ("alt", m.bottom), ("sol", m.left), ("sag", m.right)):
        if v is not None and 0 <= v * CM_INC <= 10:
            kw[ad] = round(v * CM_INC, 2)
    kw["kilavuz"] = bool(ws.print_options.gridLines)
    kw["yatay_ortala"] = bool(ws.print_options.horizontalCentered)
    try:
        pa = ws.print_area
        if pa:
            ilk = (pa if isinstance(pa, str) else pa[0]).split(",")[0].split("!")[-1].replace("$", "")
            a, _, b = ilk.partition(":")
            (s1, r1), (s2, r2) = coordinate_from_string(a), coordinate_from_string(b or a)
            kw["alan"] = Aralik(r1, column_index_from_string(s1), r2, column_index_from_string(s2))
        pt = ws.print_title_rows
        if pt:
            a, _, b = pt.split("!")[-1].replace("$", "").partition(":")
            kw["baslik_satirlari"] = (int(a), int(b or a))
    except Exception:
        pass                                                # bozuk yazdırma alanı: yok sayılır
    try:
        return SayfaYapisi(**kw)
    except ValueError:
        return SayfaYapisi()


# --- hızlı formül çevirisi ------------------------------------------------------------------------
# Büyük dosyada aynı sütunun formülleri yalnız satırı değişir (`=A5+B5*3`, `=A6+B6*3`…); her birini baştan
# ayrıştırmak açılışın yarısını yiyordu. Yalnız basit (sayı, işleç, hücre başvurusu, işlev çağrısı) formüller
# için, hücre konumuna göre bağıl (R1C1 benzeri) bir anahtar çıkarılır; ilk örnek tam çevrilir ve sonuç
# metne ÖZDEŞ çıkarsa (sayfa başvurusu/ad/küçük harf yok) aynı anahtarlı diğerleri çevrilmeden kabul edilir.
_BASIT = re.compile(r"(?:\s+|(?:0|[1-9]\d*)(?:\.\d+)?(?!\d)|[-+*/^&=<>(),:%]|\$?[A-Z]{1,3}\$?[1-9]\d*|[A-Z][A-Z0-9.]*(?=\())+")
_BASV = re.compile(r"(?<![A-Z0-9.$])(\$?)([A-Z]{1,3})(\$?)([1-9]\d*)(?![\w(.])")


def _sutun_no(harf: str) -> int:
    n = 0
    for ch in harf:
        n = n * 26 + ord(ch) - 64
    return n


def _formul_anahtari(metin: str, r: int, c: int) -> Optional[str]:
    if "!" in metin or '"' in metin or not _BASIT.fullmatch(metin[1:] if metin.startswith("=") else metin):
        return None

    def bag(m):
        sm, sh, rm, rn = m.group(1), m.group(2), m.group(3), int(m.group(4))
        col = _sutun_no(sh)
        return (f"C{col}" if sm else f"C[{col - c}]") + (f"R{rn}" if rm else f"R[{rn - r}]")
    return _BASV.sub(bag, metin)


class _FormulOnbellek:
    def __init__(self):
        self._ozdes: Dict[str, bool] = {}

    def cevir(self, metin: str, r: int, c: int, yavas):
        """`yavas(metin)` tam çeviridir; özdeşlik bilinen anahtarlarda atlanır."""
        anahtar = _formul_anahtari(metin, r, c)
        if anahtar is not None and self._ozdes.get(anahtar):
            return metin
        sonuc = yavas(metin)
        if anahtar is not None and anahtar not in self._ozdes:
            self._ozdes[anahtar] = (sonuc == metin)
        return sonuc


# --- yazma ----------------------------------------------------------------------------------------
def _hucre_degeri(h: Hucre, kitap, r: int = 0, c: int = 0, onb: Optional[_FormulOnbellek] = None):
    """(değer, formül mü) — değer openpyxl'e verilecek biçimde."""
    if h.formul is not None:
        if onb is not None:
            return onb.cevir(h.formul, r, c, lambda m: _formul_yaz(m, kitap)), True
        return _formul_yaz(h.formul, kitap), True
    v = h.deger
    if isinstance(v, Hata):
        return v.kod, False
    return v, False


MAKS_METIN = 32767


def _guvenli_deger(deger, rapor: Rapor, sayac: dict):
    """openpyxl'in/Excel'in kabul etmediği değerleri düzeltir: XML'de geçersiz denetim karakterleri silinir,
    32767 karakterden uzun metin kırpılır, NaN/sonsuz `#NUM!` olur. Düzeltme sayıları `sayac`ta."""
    if isinstance(deger, str):
        if ILLEGAL_CHARACTERS_RE.search(deger):
            deger = ILLEGAL_CHARACTERS_RE.sub("", deger)
            sayac["karakter"] = sayac.get("karakter", 0) + 1
        if len(deger) > MAKS_METIN:
            deger = deger[:MAKS_METIN]
            sayac["uzun"] = sayac.get("uzun", 0) + 1
    elif isinstance(deger, float) and not math.isfinite(deger):
        deger = "#NUM!"
        sayac["sonsuz"] = sayac.get("sonsuz", 0) + 1
    return deger


def kaydet(kitap: CalismaKitabi, yol: str) -> Rapor:
    """Kitabı `yol`a yazar (önce geçici dosya, sonra yerine koyma: yarıda kalan kayıt dosyayı bozmaz)."""
    rapor = Rapor()
    wb = Workbook()
    wb.remove(wb.active)
    havuz = kitap.stil_havuzu
    onbellek: Dict[int, tuple] = {}
    stil_dizisi: Dict[int, object] = {}          # stil kimliği → openpyxl `StyleArray` (hücre başına 5 atama yerine kopya)
    formul_onb = _FormulOnbellek()
    sayac: dict = {}

    def stil_nesneleri(kimlik: int):
        t = onbellek.get(kimlik)
        if t is None:
            t = onbellek[kimlik] = _stil_yaz(havuz.stil(kimlik))
        return t

    def uygula(nesne, kimlik: int):
        if kimlik == 0:
            return
        dizi = stil_dizisi.get(kimlik)
        if dizi is None:
            f, fi, b, a, nf = stil_nesneleri(kimlik)
            nesne.font, nesne.fill, nesne.border, nesne.alignment, nesne.number_format = f, fi, b, a, nf
            stil_dizisi[kimlik] = copy(nesne._style)
        else:
            nesne._style = copy(dizi)

    for sayfa in kitap.sayfalar:
        ws = wb.create_sheet(sayfa.ad)
        if sayfa.sekme_rengi:
            ws.sheet_properties.tabColor = sayfa.sekme_rengi[1:]
        for (r, c), h in sayfa._hucreler.items():
            deger, formul = _hucre_degeri(h, kitap, r, c, formul_onb)
            if deger is None:
                continue
            deger = _guvenli_deger(deger, rapor, sayac)
            hc = ws.cell(row=r, column=c)
            hc.value = deger
            if isinstance(h.deger, str) and h.formul is None:
                hc.data_type = "s"           # '=' ile başlayan düz metin formül sanılmasın
        for (r, c), k in sayfa._stil.items():
            if k:
                uygula(ws.cell(row=r, column=c), k)
        for r, k in sayfa.satir_stil.items():
            uygula(ws.row_dimensions[r], k)
        # sütun bilgisi: aynı özellikli ardışık sütunlar tek `<col min max>` olur ("K:XFD gizli" 16 bin kayıt olmaz)
        sutunlar = sorted(set(sayfa.sutun_stil) | set(sayfa.sutun_genislik) | sayfa.gizli_sutun)

        def sutun_bilgisi(c):
            return (sayfa.sutun_stil.get(c, 0), sayfa.sutun_genislik.get(c), c in sayfa.gizli_sutun)
        i = 0
        while i < len(sutunlar):
            c1 = c2 = sutunlar[i]
            b = sutun_bilgisi(c1)
            i += 1
            while i < len(sutunlar) and sutunlar[i] == c2 + 1 and sutun_bilgisi(sutunlar[i]) == b:
                c2 = sutunlar[i]
                i += 1
            cd = ws.column_dimensions[get_column_letter(c1)]
            cd.min, cd.max = c1, c2
            uygula(cd, b[0])
            if b[1] is not None:
                cd.width = olcu.px_karakter(b[1])
            elif b[2]:
                cd.width = olcu.px_karakter(Sayfa.VARSAYILAN_SUTUN_GENISLIGI)
            if b[2]:
                cd.hidden = True
        for r, px in sayfa.satir_yukseklik.items():
            ws.row_dimensions[r].height = olcu.px_punto(px)
        for r in sayfa.gizli_satir:
            ws.row_dimensions[r].hidden = True
        for b in sayfa.birlesimler:
            ws.merge_cells(start_row=b.ilk_satir, start_column=b.ilk_sutun,
                           end_row=b.son_satir, end_column=b.son_sutun)
        if sayfa.dondur:
            ws.freeze_panes = f"{get_column_letter(sayfa.dondur[1])}{sayfa.dondur[0]}"
        ws.sheet_view.showGridLines = sayfa.kilavuz
        _yapi_yaz(ws, sayfa.sayfa_yapisi)

    _adlari_yaz(wb, kitap)
    if sayac.get("karakter"):
        rapor.ekle(f"{sayac['karakter']} hücrede dosyada geçersiz olan denetim karakterleri silindi.")
    if sayac.get("uzun"):
        rapor.ekle(f"{sayac['uzun']} hücrede 32.767 karakterden uzun metin kırpıldı.")
    if sayac.get("sonsuz"):
        rapor.ekle(f"{sayac['sonsuz']} hücredeki sonsuz/geçersiz sayı #SAYI! olarak yazıldı.")
    gecici = f"{yol}.{os.getpid()}.tmp"
    try:
        wb.save(gecici)
        os.replace(gecici, yol)
    except PermissionError as e:
        raise XlsxHatasi("Dosya başka bir uygulamada açık olabilir; kapatıp yeniden deneyin.") from e
    except OSError as e:
        raise XlsxHatasi(f"Dosya kaydedilemedi: {e.strerror or e}") from e
    finally:
        if os.path.exists(gecici):
            try:
                os.remove(gecici)
            except OSError:
                pass
    return rapor


# --- okuma ----------------------------------------------------------------------------------------
def _aralik(hucre_araligi) -> Aralik:
    return Aralik(hucre_araligi.min_row, hucre_araligi.min_col, hucre_araligi.max_row, hucre_araligi.max_col)


def _ozel_yukseklikler(yol: str) -> Optional[Dict[str, set]]:
    """Sayfa adı → elle ayarlanmış (`customHeight`) satırlar; Excel'in otomatik ayarladığı satırlar da `ht`
    taşır ama özel değildir (openpyxl bu ayrımı atar). Okunamazsa None (hepsi elle sayılır)."""
    try:
        with zipfile.ZipFile(yol) as z:
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                  "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
            wbx = ElementTree.fromstring(z.read("xl/workbook.xml"))
            rels = ElementTree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            hedef = {r.get("Id"): r.get("Target") for r in rels}
            sonuc: Dict[str, set] = {}
            for sh in wbx.find("m:sheets", ns):
                h = hedef.get(sh.get("{%s}id" % ns["r"]))
                if not h:
                    return None
                p = h.lstrip("/") if h.startswith("/") else "xl/" + h
                xml = z.read(p)
                satirlar = set()
                for m in re.finditer(rb"<row\b[^>]*>", xml):
                    etiket = m.group(0)
                    if re.search(rb'customHeight="(?:1|true)"', etiket):
                        n = re.search(rb'\br="(\d+)"', etiket)
                        if n:
                            satirlar.add(int(n.group(1)))
                sonuc[sh.get("name")] = satirlar
            return sonuc
    except Exception:
        return None


def ac(yol: str) -> "tuple[CalismaKitabi, Rapor]":
    """`yol`daki .xlsx dosyasını yeni bir kitaba okur. Dönen rapor desteklenmeyen öğeleri listeler.
    Formül sonuçları dosyadan alınmaz; motor yeniden hesaplar."""
    rapor = tara(yol)
    try:
        wb = load_workbook(yol, data_only=False)
    except zipfile.BadZipFile as e:
        raise XlsxHatasi("Dosya geçerli bir .xlsx değil (bozuk ya da farklı biçim).") from e
    except PermissionError as e:
        raise XlsxHatasi("Dosya okunamadı: başka bir uygulama kullanıyor olabilir.") from e
    except OSError as e:
        raise XlsxHatasi(f"Dosya açılamadı: {e.strerror or e}") from e
    except Exception as e:                       # openpyxl çeşitli ayrıştırma hataları verir
        raise XlsxHatasi(f"Dosya okunamadı: {e}") from e

    kitap = CalismaKitabi()
    havuz = kitap.stil_havuzu
    sayfalar = []
    for i, ws in enumerate(wb.worksheets):
        s = kitap.sayfalar[0] if i == 0 else None
        ad = ws.title
        if s is None:
            s = kitap.sayfa_ekle(ad)
        else:
            kitap.yeniden_adlandir(s, ad)
        if ws.sheet_state != "visible":
            rapor.ekle(f"Gizli sayfa '{ad}' görünür yapıldı; kaydederseniz gizlilik kaybolur.", True)
        sayfalar.append((ws, s))

    stil_onb: Dict[tuple, int] = {}
    tema = _tema_oku(wb)
    ozel_yuk = _ozel_yukseklikler(yol)
    if wb.epoch.year == 1904:
        rapor.ekle("Bu dosya 1904 tarih sistemini kullanıyor; tarih biçimli hücreler doğru çevrildi, ancak tarih "
                   "biçimi olmayıp tarih olarak kullanılan sayılar 1.462 gün kayabilir.")

    def kimlik_al(hc_veya_boyut) -> int:
        t = hc_veya_boyut
        anahtar = tuple(t._style)
        k = stil_onb.get(anahtar)
        if k is None:
            st = _stil_oku(t.font, t.fill, t.border, t.alignment, t.number_format, tema)
            k = stil_onb[anahtar] = havuz.kimlik(st)
        return k

    bozuk_formul = 0
    formul_onb = _FormulOnbellek()
    for ws, s in sayfalar:
        yeni, stiller = {}, {}
        for (r, c), hc in ws._cells.items():          # yalnız var olan hücreler (iter_rows seyrek dosyada tüm kutuyu gezer)
            if type(hc).__name__ == "MergedCell":
                continue
            v = hc.value
            if v is not None:
                if hc.data_type == "f" or (isinstance(v, str) and hc.data_type == "f"):
                    metin = v if isinstance(v, str) else getattr(v, "text", None)
                    if not isinstance(metin, str):            # veri tablosu vb.: desteklenmez
                        rapor.ekle("Desteklenmeyen formül türleri (veri tablosu) değere çevrilemedi.")
                        continue
                    if not metin.startswith("="):
                        metin = "=" + metin
                    try:
                        yeni[(r, c)] = Hucre(None, formul_onb.cevir(
                            metin, r, c, lambda m: _formul_oku(m, kitap)))
                    except FormulHatasi:
                        bozuk_formul += 1
                        yeni[(r, c)] = Hucre(metin)
                elif hc.data_type == "e":
                    yeni[(r, c)] = Hucre(hata_bul(str(v)) or Hata(str(v)))
                elif isinstance(v, bool):
                    yeni[(r, c)] = Hucre(v)
                elif isinstance(v, (int, float)):
                    yeni[(r, c)] = Hucre(float(v))
                elif isinstance(v, str):
                    yeni[(r, c)] = Hucre(v)
                else:                                         # tarih/saat/süre → seri sayı
                    try:
                        yeni[(r, c)] = Hucre(float(to_excel(v)))
                    except (TypeError, ValueError, OverflowError):
                        rapor.ekle(f"'{ws.title}' sayfasında okunamayan tarih değerleri atlandı.")
            if hc.has_style:
                k = kimlik_al(hc)
                if k:
                    stiller[(r, c)] = k
        s.toplu_yaz(yeni)
        satir_st, sutun_st = {}, {}
        for r, rd in ws.row_dimensions.items():
            if rd.has_style and getattr(rd, "customFormat", True):
                k = kimlik_al(rd)
                if k:
                    satir_st[r] = k
            if rd.height is not None and (ozel_yuk is None or r in ozel_yuk.get(ws.title, ())):
                s.satir_yukseklik[r] = olcu.yukseklik_sinirla(olcu.punto_px(rd.height))
            if rd.hidden:
                s.gizli_satir.add(r)
        for harf, cd in ws.column_dimensions.items():
            try:
                c1 = cd.min or column_index_from_string(harf)
                c2 = min(cd.max or c1, MAX_COL)
            except ValueError:
                continue
            kim = kimlik_al(cd) if cd.has_style else 0
            for c in range(c1, c2 + 1):
                if kim:
                    sutun_st[c] = kim
                if cd.width is not None and cd.width != 13:       # 13: openpyxl'in genişliksiz `<col>` varsayılanı
                    s.sutun_genislik[c] = olcu.genislik_sinirla(olcu.karakter_px(cd.width))
                if cd.hidden:
                    s.gizli_sutun.add(c)
        s.bicim_yaz(stiller, satir_st, sutun_st)
        birlesimler = []
        for b in ws.merged_cells.ranges:
            a = _aralik(b)
            if (a.ilk_satir, a.ilk_sutun) == (a.son_satir, a.son_sutun):
                continue
            if any(not (a.son_satir < x.ilk_satir or a.ilk_satir > x.son_satir or a.son_sutun < x.ilk_sutun
                        or a.ilk_sutun > x.son_sutun) for x in birlesimler):
                rapor.ekle("Çakışan birleşimler (dosya bozuk) atlandı.")
                continue
            birlesimler.append(a)
        s.birlesim_yukle(birlesimler)
        fp = ws.freeze_panes
        dondur = None
        if fp:
            try:
                sut, sat = coordinate_from_string(fp)
                dondur = (sat, column_index_from_string(sut))
                if dondur == (1, 1) or sat > MAX_ROW:
                    dondur = None
            except Exception:
                dondur = None
        s.gorunum_yaz(dondur=dondur, kilavuz=bool(ws.sheet_view.showGridLines is not False))
        s.sayfa_yapisi = _yapi_oku(ws)
        tab = ws.sheet_properties.tabColor
        if tab is not None:
            s.sekme_rengi = _renk_oku(tab, tema)
    _adlari_oku(wb, kitap, sayfalar, rapor)
    if bozuk_formul:
        rapor.ekle(f"{bozuk_formul} formül çevrilemedi, metin olarak bırakıldı.")
    return kitap, rapor
