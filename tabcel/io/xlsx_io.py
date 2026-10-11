"""`.xlsx` aç/kaydet (Faz 4 / 4a). Qt yok.

Okuma/yazma openpyxl ile; biçim eşlemesi `model/stil.py`'ye, formül eşlemesi `formul/ceviri.py`'ye dayanır
(saklanan formül kanonik İngilizce + sayfa kimliği; dosyada İngilizce + sayfa adı).

Bilinen sınırlar (her açılışta `Rapor`'a yazılır, arayüz bilgi çubuğunda gösterir):
- openpyxl pivot/makro/şekil/dizili açıklamaları korumaz → `Rapor.veri_kaybi` (notlar korunur; kutu
  boyutu/konumu varsayılana döner). Grafik ve resimler `xlsx_grafik.py` ile okunur/yazılır (Faz 6 / 6h): Tabcel
  imi (`TabcelSurum`) olmayan dosyada "uyarlandı" bilgisi + kaydederken onay, desteklenmeyen grafik türü atlanır
- kaydedilen formüllerin önbellek değeri yazılmaz (Excel açınca yeniden hesaplar)
- tema renkleri varsayılan Office teması varsayımıyla RGB'ye çevrilir (§8b)
"""
import io
import math
import os
import re
import zipfile
from copy import copy
from xml.etree import ElementTree
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.worksheet.filters import (
    CustomFilter, CustomFilters, DynamicFilter, FilterColumn, Filters, Top10,
)
from openpyxl.worksheet.cell_range import CellRange
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.formatting.rule import ColorScale, DataBar, FormatObject, Rule
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.styles.colors import Color
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import COLOR_INDEX
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.utils.datetime import to_excel

from .. import APP_NAME
from ..formul import ceviri
from . import sifreleme, xlsx_grafik, xlsx_kayip
from ..formul.sozcuk import FormulHatasi
from ..model import olcu
from ..model.ad import AdHatasi, TanimliAd, ad_dogrula
from ..model.adres import MAX_COL, MAX_ROW, Aralik
from ..model.deger import Hata, hata_bul
from ..model.dogrulama import Dogrulama
from ..model.kosullu import KosulluKural
from ..model.filtre import DegerKosulu, Filtre, IlkKosul, OrtalamaKosulu, OzelKosul, RenkKosulu
from ..model.notlar import Not
from ..model.sayfa import CalismaKitabi, Hucre, Sayfa, TasmaHucre
from ..model.sayfa_yapisi import SayfaYapisi
from ..model.stil import Kenarlik, Stil, StilYama

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
_XLFN_OKU = re.compile(r"_xlfn\.(?:_xlws\.)?|_xlpm\.", re.IGNORECASE)      # `_xlpm.`: LET/LAMBDA değişken öneki
_LET_ARA = re.compile(r"(?<![\w.])(?:_xlfn\.)?LET\(", re.IGNORECASE)

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

_NOT_GENISLIK, _NOT_YUKSEKLIK = 200, 100         # not kutusu boyutu (nokta); Excel varsayılanına yakın

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
    (re.compile(r"^xl/pivot(Tables|Cache)/"), "pivot tablo", True),
    (re.compile(r"^xl/vbaProject\.bin$"), "makro (VBA)", True),
    (re.compile(r"^xl/externalLinks/"), "dış bağlantı", True),
    (re.compile(r"^xl/threadedComments"), "dizili açıklama (not olarak okunur, yanıtlar kaybolur)", True),
    (re.compile(r"^xl/slicers/|^xl/timelines/"), "dilimleyici", True),
    (re.compile(r"^xl/tables/"), "Excel tablosu", True),
)
# sayfa XML'inde aranan, openpyxl ile korunamayan/bozulan öğeler
_SAYFA_ISARETLERI = (
    (b"<hyperlinks", "köprü"), (b"outlineLevel=", "satır/sütun gruplama"),
    (b"<headerFooter", "üst/alt bilgi"), (b"<sheetProtection", "sayfa koruması"),
)                                                       # dizi formülleri (`t="array"`) Faz 8e'den beri desteklenir: taşan formül olur


_SEKIL_RE = re.compile(rb"<(?:xdr:)?(?:sp|grpSp|cxnSp)[ >]")


def _nesne_sayilari(yol: str):
    """Zip'te (grafik parçası, medya dosyası, Tabcel imi var mı); dosya açılamazsa (0, 0, False)."""
    try:
        with zipfile.ZipFile(yol) as z:
            adlar = z.namelist()
            medya = set()                                  # yalnız çizimlerin başvurduğu resimler (artık parça sayılmaz)
            for a in adlar:
                if re.match(r"^xl/drawings/_rels/drawing\d+\.xml\.rels$", a):
                    for hedef in re.findall(rb'Target="([^"]*media/[^"]+)"', z.read(a)):
                        medya.add(hedef.decode().rsplit("/", 1)[-1])
            return (sum(1 for a in adlar if re.match(r"^xl/charts/chart\d+\.xml$", a)), len(medya),
                    xlsx_grafik.im_var_mi(z))
    except (zipfile.BadZipFile, OSError):
        return 0, 0, False


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
                if re.match(r"^xl/drawings/drawing\d+\.xml$", ad) and _SEKIL_RE.search(z.read(ad)):
                    bulunan["şekil/SmartArt"] = True      # grafik ve resim artık korunur; şekiller korunmaz
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


def _tabcel_ozel_kullanimi(kitap) -> set:
    """Kitapta kullanılan Tabcel'e özgü (Excel'de olmayan) işlevlerin adları (T7)."""
    from ..formul.adlar import TABCEL_OZEL
    desen = re.compile(r"(?<![\w.])(" + "|".join(TABCEL_OZEL) + r")\(", re.IGNORECASE)
    bulunan = set()
    for sayfa in kitap.sayfalar:
        for _, _, h in sayfa.dolu_hucreler(False):
            f = h.formul
            if f is not None:
                bulunan.update(m.upper() for m in desen.findall(f))
        if len(bulunan) == len(TABCEL_OZEL):
            break
    return {TABCEL_OZEL[a] for a in bulunan}


_YOKSAY_ADI = "TabcelSaglikYoksay"            # belge özelliği öneki; değer ≤ 240 karakterlik parçalara bölünür (Excel özellik sınırı)


def _yoksay_yaz(wb, kitap) -> None:
    """Sağlık Kontrolü'nde “yoksay” denen bulguların anahtarlarını (kontrol|sayfa|adres — kişisel veri içermez) belge özelliği olarak yazar."""
    import json
    from openpyxl.packaging.custom import StringProperty
    if not getattr(kitap, "saglik_yoksay", None):
        return
    metin = json.dumps(sorted(kitap.saglik_yoksay), ensure_ascii=False)
    for i in range(0, len(metin), 240):
        wb.custom_doc_props.append(StringProperty(name=f"{_YOKSAY_ADI}{i // 240 + 1}", value=metin[i:i + 240]))


def _yoksay_oku(wb, kitap) -> None:
    import json
    parcalar = {}
    for p in wb.custom_doc_props.props:
        if p.name.startswith(_YOKSAY_ADI) and p.name[len(_YOKSAY_ADI):].isdigit():
            parcalar[int(p.name[len(_YOKSAY_ADI):])] = str(p.value)
    if not parcalar:
        return
    try:
        liste = json.loads("".join(parcalar[i] for i in sorted(parcalar)))
    except ValueError:
        return
    if isinstance(liste, list):
        kitap.saglik_yoksay = {x for x in liste if isinstance(x, str)}


def _let_xlpm_yaz(m: str) -> str:
    """LET değişken adlarına dosyadaki `_xlpm.` önekini ekler (`LET(x,1,x+1)` → `LET(_xlpm.x,1,_xlpm.x+1)`; Excel öneksiz
    adı #AD? sayar). İç içe LET'ler de işlenir; çift tırnaklı metin sabitlerine dokunulmaz."""
    if "LET(" not in m.upper():
        return m
    pos = 0
    while True:
        mm = _LET_ARA.search(m, pos)
        if mm is None:
            return m
        bas, derinlik, i, arg_basi, in_str, args = mm.end(), 1, mm.end(), mm.end(), False, []
        while i < len(m):
            ch = m[i]
            if ch == '"':
                in_str = not in_str
            elif not in_str:
                if ch == "(":
                    derinlik += 1
                elif ch == ")":
                    derinlik -= 1
                    if derinlik == 0:
                        args.append((arg_basi, i))
                        break
                elif ch == "," and derinlik == 1:
                    args.append((arg_basi, i))
                    arg_basi = i + 1
            i += 1
        if len(args) < 3 or len(args) % 2 == 0 or derinlik:
            pos = mm.end()
            continue
        adlar = [m[a:b].strip() for a, b in args[0:-1:2]]
        adlar = [x for x in adlar if re.fullmatch(r"[A-Za-z_][\w.]*", x)]
        if adlar:
            desen = re.compile(r"(?<![\w.!'])(" + "|".join(map(re.escape, adlar)) + r")(?![\w.(!'])", re.IGNORECASE)
            govde = m[bas:i].split('"')
            for k in range(0, len(govde), 2):
                govde[k] = desen.sub(lambda g: "_xlpm." + g.group(1), govde[k])
            m = m[:bas] + '"'.join(govde) + m[i:]
        pos = bas


def _formul_yaz(formul: str, kitap) -> str:
    """Saklanan formül → dosyadaki metin (İngilizce, sayfa adlı, gerekli `_xlfn.` önekleriyle)."""
    m = ceviri.disa(formul, kitap)
    parcalar = m.split('"')               # çift tırnaklı metin sabitlerine dokunma (çift sayı = dışarıda)
    for i in range(0, len(parcalar), 2):
        parcalar[i] = _FN_ADI.sub(_oneki_ekle, parcalar[i])
    return _let_xlpm_yaz('"'.join(parcalar))


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
    sigdir = y.sigdir_genislik or y.sigdir_yukseklik
    ws.page_setup.scale = None if sigdir else y.olcek
    if sigdir:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1 if y.sigdir_genislik else 0
        ws.page_setup.fitToHeight = 1 if y.sigdir_yukseklik else 0
    if y.sayfa_sirasi == "sag_sonra_asagi":
        ws.page_setup.pageOrder = "overThenDown"
    # el ile sayfa sonları: Excel `id` = kesmeden ÖNCEKİ satır/sütun (yeni sayfa id+1'de başlar); yalnız el ile yazılır
    for k in y.satir_kesmeleri:
        ws.row_breaks.append(Break(id=k - 1, man=True, max=16383))
    for k in y.sutun_kesmeleri:
        ws.col_breaks.append(Break(id=k - 1, man=True, max=1048575))
    m = ws.page_margins
    m.top, m.bottom, m.left, m.right = (round(v / CM_INC, 4) for v in (y.ust, y.alt, y.sol, y.sag))
    ws.print_options.gridLines = y.kilavuz or None
    ws.print_options.horizontalCentered = y.yatay_ortala or None
    if y.alan is not None:
        ws.print_area = f"{get_column_letter(y.alan.ilk_sutun)}{y.alan.ilk_satir}:" \
                        f"{get_column_letter(y.alan.son_sutun)}{y.alan.son_satir}"
    if y.baslik_satirlari is not None:
        ws.print_title_rows = f"{y.baslik_satirlari[0]}:{y.baslik_satirlari[1]}"


def _yapi_oku(ws, rapor=None) -> SayfaYapisi:
    ps, m = ws.page_setup, ws.page_margins
    kw = {}
    if ps.orientation == "landscape":
        kw["yon"] = "yatay"
    kw["kagit"] = _KAGIT_ADI.get(ps.paperSize or 9, "A4")
    fit = bool(ws.sheet_properties.pageSetUpPr and ws.sheet_properties.pageSetUpPr.fitToPage)
    if fit:                                             # fitToWidth/Height yoksa 1, 0 = serbest (Excel)
        g = 1 if ps.fitToWidth is None else int(ps.fitToWidth)
        h = 1 if ps.fitToHeight is None else int(ps.fitToHeight)
        kw["sigdir_genislik"], kw["sigdir_yukseklik"] = g != 0, h != 0
        if rapor is not None and (g > 1 or h > 1):                  # Tabcel yalnız "tek sayfaya" sığdırır
            rapor.ekle(f"“{ws.title}” sayfasında yazdırma {g} sayfa genişliğine × {h} sayfa yüksekliğine sığdırılıyor; "
                       "Tabcel bunu tek sayfaya sığdırma olarak uygular.")
        if g == 0 and h == 0:                           # ikisi de serbest: "sığdır" fiilen kapalı
            kw["sigdir_genislik"] = kw["sigdir_yukseklik"] = False
    elif ps.scale and 10 <= int(ps.scale) <= 400:
        kw["olcek"] = int(ps.scale)
    for ad, v in (("ust", m.top), ("alt", m.bottom), ("sol", m.left), ("sag", m.right)):
        if v is not None and 0 <= v * CM_INC <= 10:
            kw[ad] = round(v * CM_INC, 2)
    if ps.pageOrder == "overThenDown":
        kw["sayfa_sirasi"] = "sag_sonra_asagi"
    for ad, brk, sinir in (("satir_kesmeleri", ws.row_breaks, 1048576), ("sutun_kesmeleri", ws.col_breaks, 16384)):
        liste = sorted({int(b.id) + 1 for b in brk.brk if b.man and b.id is not None and 1 <= int(b.id) < sinir})
        if liste:
            kw[ad] = tuple(liste)
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


def kaydet(kitap: CalismaKitabi, yol: str, parola: Optional[str] = None) -> Rapor:
    """Kitabı `yol`a yazar (önce geçici dosya, sonra yerine koyma: yarıda kalan kayıt dosyayı bozmaz). `parola` verilirse
    dosya parolayla şifrelenir (paket yalnız bellekte; yazılan şifreli veri geri çözülerek doğrulanır, Faz 8b)."""
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
        if sayfa.gizli and any(not x.gizli for x in kitap.sayfalar):   # en az bir görünür sayfa şart
            ws.sheet_state = "hidden"
        for (r, c), h in sayfa._hucreler.items():
            if type(h) is TasmaHucre:                    # taşma hücreleri türetilmiştir; sahibi dizi formülü olarak yazılır
                continue
            deger, formul = _hucre_degeri(h, kitap, r, c, formul_onb)
            if deger is None:
                continue
            deger = _guvenli_deger(deger, rapor, sayac)
            hc = ws.cell(row=r, column=c)
            hc.value = deger
            alan = sayfa.tasma.get((r, c)) if h.formul is not None else None
            if alan is not None:                         # dinamik dizi → `<f t="array" ref=…>` (Excel eski tür dizi olarak açar)
                hc.value = ArrayFormula(f"{get_column_letter(alan.ilk_sutun)}{alan.ilk_satir}:"
                                        f"{get_column_letter(alan.son_sutun)}{alan.son_satir}", deger)
                sayac["tasma"] = sayac.get("tasma", 0) + 1
            if isinstance(h.deger, str) and h.formul is None:
                hc.data_type = "s"           # '=' ile başlayan düz metin formül sanılmasın
        for (r, c), k in sayfa._stil.items():
            if k:
                uygula(ws.cell(row=r, column=c), k)
        for (r, c), n in sayfa.notlar.items():
            yorum = Comment(ILLEGAL_CHARACTERS_RE.sub("", n.metin), ILLEGAL_CHARACTERS_RE.sub("", n.yazar))
            yorum.width, yorum.height = _NOT_GENISLIK, _NOT_YUKSEKLIK
            ws.cell(row=r, column=c).comment = yorum
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
        if sayfa.filtre is not None:
            _filtre_yaz(ws, sayfa.filtre, rapor)
        if sayfa.dogrulamalar:
            _dogrulamalari_yaz(ws, sayfa, kitap, rapor)
        if sayfa.kosullu:
            _kosullulari_yaz(ws, sayfa, kitap, rapor)
        if sayfa.nesneler:
            g_yok, r_yok = xlsx_grafik.nesneleri_yaz(ws, sayfa, kitap)
            sayac["grafik_yok"] = sayac.get("grafik_yok", 0) + g_yok
            sayac["resim_yok"] = sayac.get("resim_yok", 0) + r_yok

    xlsx_grafik.im_yaz(wb)
    _yoksay_yaz(wb, kitap)
    _adlari_yaz(wb, kitap)
    ozel = _tabcel_ozel_kullanimi(kitap)
    if ozel:
        rapor.ekle(f"{', '.join(sorted(ozel))} işlev(ler)i yalnızca {APP_NAME}'e özgüdür; Excel ve diğer programlarda "
                   "#AD? verir (değerler dosyada saklanır, formül çalışmaz).", True)
    if sayac.get("tasma"):
        rapor.ekle(f"{sayac['tasma']} dinamik dizi formülü Excel'de eski tür dizi formülü ({{=…}}) olarak açılır: alanı sabittir, "
                   "kaynak veri büyürse kendiliğinden genişlemez.")
    if sayac.get("grafik_yok"):
        rapor.ekle(f"{sayac['grafik_yok']} grafik dosyaya yazılamadı (verisi silinmiş ya da silinen bir sayfaya bağlı); "
                   "kaydedilen dosyada yok.", True)
    if sayac.get("resim_yok"):
        rapor.ekle(f"{sayac['resim_yok']} resim dosyaya yazılamadı; kaydedilen dosyada yok.", True)
    if sayac.get("karakter"):
        rapor.ekle(f"{sayac['karakter']} hücrede dosyada geçersiz olan denetim karakterleri silindi.")
    if sayac.get("uzun"):
        rapor.ekle(f"{sayac['uzun']} hücrede 32.767 karakterden uzun metin kırpıldı.")
    if sayac.get("sonsuz"):
        rapor.ekle(f"{sayac['sonsuz']} hücredeki sonsuz/geçersiz sayı #SAYI! olarak yazıldı.")
    gecici = f"{yol}.{os.getpid()}.tmp"
    try:
        if parola:
            tampon = io.BytesIO()
            wb.save(tampon)
            paket = tampon.getvalue()
            veri = sifreleme.sifrele(paket, parola)
            if not sifreleme.dogrula(veri, parola, paket):
                raise XlsxHatasi(sifreleme.DOGRULAMA_BASARISIZ)
            with open(gecici, "wb") as h:
                h.write(veri)
        else:
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
def _not_oku(yorum) -> Optional[Not]:
    """openpyxl yorumunu nota çevirir. Excel notun metnine yazarı `Yazar:\\n` önekiyle (kalın) yazar;
    önek atılır (yazar ayrı tutulur ve kutuda yeniden üretilir)."""
    metin = (yorum.text or "").replace("\r\n", "\n").replace("\r", "\n")
    yazar = (yorum.author or "").strip()
    for onek in ((f"{yazar}:\n", f"{yazar}:") if yazar else ()):
        if metin.startswith(onek):
            metin = metin[len(onek):]
            break
    if metin == "" and yazar == "":
        return None
    return Not(metin, yazar)


_DV_TUR_YAZ = {"tam_sayi": "whole", "ondalik": "decimal", "liste": "list", "tarih": "date", "saat": "time",
               "metin_uzunlugu": "textLength", "ozel": "custom", "her_deger": None}
_DV_TUR_OKU = {v: k for k, v in _DV_TUR_YAZ.items() if v}
_DV_ISLEC_YAZ = {"arasinda": "between", "arasinda_degil": "notBetween", "esit": "equal", "esit_degil": "notEqual",
                 "buyuk": "greaterThan", "kucuk": "lessThan", "buyuk_esit": "greaterThanOrEqual",
                 "kucuk_esit": "lessThanOrEqual"}
_DV_ISLEC_OKU = {v: k for k, v in _DV_ISLEC_YAZ.items()}
_DV_STIL_YAZ = {"durdur": "stop", "uyari": "warning", "bilgi": "information"}
_DV_STIL_OKU = {v: k for k, v in _DV_STIL_YAZ.items()}


def _dv_formul_yaz(f, kitap):
    """Saklanan doğrulama formülü → dosyadaki metin ('=' yok; liste sabiti tırnaklı olduğu gibi)."""
    if f is None:
        return None
    return f if not f.startswith("=") else ceviri.disa(f, kitap)[1:]


def _dv_formul_oku(f, kitap):
    if f is None:
        return None
    f = str(f)
    if f.startswith('"'):
        return f
    return ceviri.iceri("=" + f, kitap)


def _dogrulamalari_yaz(ws, sayfa, kitap, rapor: Rapor) -> None:
    for dv in sayfa.dogrulamalar:
        try:
            x = DataValidation(
                type=_DV_TUR_YAZ[dv.tur], operator=_DV_ISLEC_YAZ[dv.islec] if dv.tur not in ("liste", "ozel", "her_deger") else None,
                formula1=_dv_formul_yaz(dv.formul1, kitap), formula2=_dv_formul_yaz(dv.formul2, kitap)
                if dv.islec in ("arasinda", "arasinda_degil") and dv.tur not in ("liste", "ozel") else None,
                allowBlank=dv.bos_yoksay, showDropDown=None if dv.acilir_liste else True,
                showInputMessage=dv.giris[0], promptTitle=dv.giris[1] or None, prompt=dv.giris[2] or None,
                showErrorMessage=dv.hata[0], errorStyle=_DV_STIL_YAZ[dv.hata[1]],
                errorTitle=dv.hata[2] or None, error=dv.hata[3] or None)
            for a in dv.araliklar:
                x.add(f"{get_column_letter(a.ilk_sutun)}{a.ilk_satir}:{get_column_letter(a.son_sutun)}{a.son_satir}")
            ws.add_data_validation(x)
        except (FormulHatasi, KeyError, ValueError):
            rapor.ekle(f"'{sayfa.ad}' sayfasındaki bir veri doğrulama kuralı yazılamadı.")


def _dogrulamalari_oku(ws, s: Sayfa, kitap, rapor: Rapor) -> None:
    kurallar = []
    atlanan = 0
    for x in ws.data_validations.dataValidation:
        try:
            tur = _DV_TUR_OKU.get(x.type, "her_deger")
            if x.type not in (None, "none") and x.type not in _DV_TUR_OKU:
                raise ValueError("tür")
            araliklar = tuple(_aralik(r) for r in x.sqref.ranges)
            if not araliklar:
                continue
            islec = _DV_ISLEC_OKU.get(x.operator or "between", "arasinda")
            kurallar.append(Dogrulama(
                araliklar, tur=tur, islec=islec,
                formul1=_dv_formul_oku(x.formula1, kitap), formul2=_dv_formul_oku(x.formula2, kitap),
                bos_yoksay=bool(x.allow_blank), acilir_liste=not x.showDropDown,
                giris=(bool(x.showInputMessage), x.promptTitle or "", x.prompt or ""),
                hata=(bool(x.showErrorMessage), _DV_STIL_OKU.get(x.errorStyle or "stop", "durdur"),
                      x.errorTitle or "", x.error or "")))
        except (FormulHatasi, ValueError, KeyError):
            atlanan += 1
    if atlanan:
        rapor.ekle(f"'{ws.title}' sayfasında {atlanan} veri doğrulama kuralı çevrilemedi; atlandı.")
    if kurallar:
        s.dogrulamalari_yaz(kurallar)


_ISLEC_YAZ = {"esit": "equal", "esit_degil": "notEqual", "buyuk": "greaterThan", "buyuk_esit": "greaterThanOrEqual",
              "kucuk": "lessThan", "kucuk_esit": "lessThanOrEqual"}
_ISLEC_OKU = {v: k for k, v in _ISLEC_YAZ.items()}
# metin işleçleri dosyada joker deseniyle yazılır: (işleç, desen öneki, sonek, olumsuz mu)
_METIN_YAZ = {"baslar": ("equal", "", "*"), "baslamaz": ("notEqual", "", "*"), "biter": ("equal", "*", ""),
              "bitmez": ("notEqual", "*", ""), "icerir": ("equal", "*", "*"), "icermez": ("notEqual", "*", "*")}


def _ozel_yaz(k):
    islec, deger = k
    if isinstance(deger, (int, float)) and not isinstance(deger, bool):
        return CustomFilter(operator=_ISLEC_YAZ.get(islec, "equal"), val=repr(float(deger)).removesuffix(".0"))
    if islec in _METIN_YAZ:
        op, on, son = _METIN_YAZ[islec]
        return CustomFilter(operator=op, val=f"{on}{deger}{son}")
    return CustomFilter(operator=_ISLEC_YAZ.get(islec, "equal"), val=str(deger))


def _ozel_oku(cf):
    """Dosyadaki özel süzgeç → `(işleç, değer)`; çevrilemezse None."""
    op, val = cf.operator or "equal", cf.val
    if val is None or op not in _ISLEC_OKU:
        return None
    try:
        return _ISLEC_OKU[op], float(val)
    except (TypeError, ValueError):
        pass
    val = str(val)
    if op in ("equal", "notEqual"):
        olumsuz = op == "notEqual"
        if len(val) >= 3 and val.startswith("*") and val.endswith("*"):
            return ("icermez" if olumsuz else "icerir"), val[1:-1]
        if val.endswith("*") and not val.startswith("*") and len(val) >= 2:
            return ("baslamaz" if olumsuz else "baslar"), val[:-1]
        if val.startswith("*") and not val.endswith("*") and len(val) >= 2:
            return ("bitmez" if olumsuz else "biter"), val[1:]
    return _ISLEC_OKU[op], val


def _filtre_yaz(ws, f: Filtre, rapor: Rapor) -> None:
    a = f.aralik
    ws.auto_filter.ref = f"{get_column_letter(a.ilk_sutun)}{a.ilk_satir}:{get_column_letter(a.son_sutun)}{a.son_satir}"
    for c, k in sorted(f.kosullar.items()):
        fc = FilterColumn(colId=c - a.ilk_sutun)
        if isinstance(k, DegerKosulu):
            fc.filters = Filters(blank=True if k.bos else None, filter=sorted(k.metinler))
        elif isinstance(k, OzelKosul):
            fc.customFilters = CustomFilters(_and=True if (k.k2 is not None and k.ve) else None,
                                             customFilter=[_ozel_yaz(x) for x in (k.k1, k.k2) if x is not None])
        elif isinstance(k, IlkKosul):
            fc.top10 = Top10(top=not k.alt, percent=True if k.yuzde else None, val=k.n)
        elif isinstance(k, OrtalamaKosulu):
            fc.dynamicFilter = DynamicFilter(type="aboveAverage" if k.ustu else "belowAverage")
        else:                                           # renk süzgeci: dosyada dxf gerekir (yazılmaz)
            rapor.ekle("Renge göre filtre dosyaya yazılamadı; süzülen satırlar gizli kalır ama koşul kaybolur.")
            continue
        ws.auto_filter.filterColumn.append(fc)


def _filtre_oku(ws, s: Sayfa, rapor: Rapor) -> None:
    af = ws.auto_filter
    if not af.ref:
        return
    try:
        a = _aralik(CellRange(af.ref))
    except Exception:
        rapor.ekle(f"'{ws.title}' sayfasındaki filtre aralığı okunamadı; filtre atlandı.")
        return
    kosullar = {}
    atlanan = 0
    for fc in af.filterColumn:
        c = a.ilk_sutun + (fc.colId or 0)
        if fc.filters is not None and (fc.filters.filter or fc.filters.blank) and not fc.filters.dateGroupItem:
            kosullar[c] = DegerKosulu(frozenset(str(x) for x in fc.filters.filter), bool(fc.filters.blank))
        elif fc.customFilters is not None and fc.customFilters.customFilter:
            ks = [_ozel_oku(x) for x in fc.customFilters.customFilter]
            if None in ks:
                atlanan += 1
            else:
                kosullar[c] = OzelKosul(ks[0], ks[1] if len(ks) > 1 else None,
                                    bool(fc.customFilters._and) if len(ks) > 1 else True)
        elif fc.top10 is not None and fc.top10.val is not None:
            kosullar[c] = IlkKosul(int(fc.top10.val), fc.top10.top in (False, 0), bool(fc.top10.percent))
        elif fc.dynamicFilter is not None and fc.dynamicFilter.type in ("aboveAverage", "belowAverage"):
            kosullar[c] = OrtalamaKosulu(fc.dynamicFilter.type == "aboveAverage")
        else:
            atlanan += 1
    if atlanan:
        rapor.ekle(f"'{ws.title}' sayfasında {atlanan} filtre koşulu (renk/tarih grubu vb.) desteklenmiyor; "
                   "satırlar gizli kalır ama koşul kaybolur.")
    s.filtre_yaz(Filtre(a, kosullar))


_KB_ISLEC_YAZ = {"arasinda": "between", "arasinda_degil": "notBetween", "esit": "equal", "esit_degil": "notEqual",
                 "buyuk": "greaterThan", "kucuk": "lessThan", "buyuk_esit": "greaterThanOrEqual",
                 "kucuk_esit": "lessThanOrEqual"}
_KB_ISLEC_OKU = {v: k for k, v in _KB_ISLEC_YAZ.items()}
_KB_NOKTA_YAZ = {"min": "min", "max": "max", "sayi": "num", "yuzde": "percent", "yuzdebirlik": "percentile",
                 "formul": "formula"}
_KB_NOKTA_OKU = {v: k for k, v in _KB_NOKTA_YAZ.items()}
_KB_METIN_TUR = {"icerir": "containsText", "icermez": "notContainsText", "baslar": "beginsWith", "biter": "endsWith"}
_KB_METIN_OKU = {v: k for k, v in _KB_METIN_TUR.items()}
_KB_METIN_OPERATOR = {"icerir": "containsText", "icermez": "notContains", "baslar": "beginsWith", "biter": "endsWith"}


def _kb_formul_yaz(f, kitap) -> str:
    return f if not f.startswith("=") else ceviri.disa(f, kitap)[1:]


def _kb_formul_oku(f, kitap) -> str:
    return ceviri.iceri("=" + str(f), kitap)


def _kb_dxf_yaz(yama):
    """`StilYama` → openpyxl `DifferentialStyle` (yazı rengi/kalın/italik/çizgiler, dolgu `bgColor`, kenarlık)."""
    if yama is None or yama.bos_mu():
        return None
    a = yama._alanlar
    font = fill = border = None
    if any(k in a for k in ("yazi_rengi", "kalin", "italik", "ustu_cizili", "alti_cizili")):
        font = Font(color=a["yazi_rengi"][1:] if a.get("yazi_rengi") else None, b=a.get("kalin") or None,
                    i=a.get("italik") or None, strike=a.get("ustu_cizili") or None,
                    u=_ALTI_YAZ.get(a.get("alti_cizili", "yok")))
    if a.get("dolgu"):
        fill = PatternFill(bgColor=a["dolgu"][1:], fill_type="solid")       # dxf: düz dolgu rengi bgColor'dadır
    kenar = a.get("kenar")
    if kenar is not None:
        d = kenar if isinstance(kenar, dict) else {y: getattr(kenar, y) for y in ("ust", "alt", "sol", "sag")}

        def yan(c):
            return Side(style=_CIZGI_YAZ[c[0]], color=c[1][1:]) if c else None
        border = Border(top=yan(d.get("ust")), bottom=yan(d.get("alt")), left=yan(d.get("sol")), right=yan(d.get("sag")))
    return DifferentialStyle(font=font, fill=fill, border=border)


def _kb_dxf_oku(dxf, tema):
    """`DifferentialStyle` → `StilYama` (yok sayılan: sayı biçimi, yazı tipi adı/boyutu)."""
    if dxf is None:
        return None
    a = {}
    f = dxf.font
    if f is not None:
        renk = _renk_oku(f.color, tema)
        if renk:
            a["yazi_rengi"] = renk
        if f.b:
            a["kalin"] = True
        if f.i:
            a["italik"] = True
        if f.strike:
            a["ustu_cizili"] = True
        if f.u in _ALTI_OKU:
            a["alti_cizili"] = _ALTI_OKU[f.u]
        elif f.u:
            a["alti_cizili"] = "tek"
    fi = dxf.fill
    if fi is not None:
        renk = _renk_oku(fi.bgColor, tema) or _renk_oku(fi.fgColor, tema)
        if renk and renk != "#000000":
            a["dolgu"] = renk
    b = dxf.border
    if b is not None:
        d = {}
        for yon, taraf in (("ust", b.top), ("alt", b.bottom), ("sol", b.left), ("sag", b.right)):
            if taraf is not None and taraf.style:
                d[yon] = (_CIZGI_OKU.get(taraf.style, "ince"), _renk_oku(taraf.color, tema) or "#000000")
        if d:
            a["kenar"] = d
    return StilYama(**a) if a else None


def _kb_kural_yaz(k, ust_sol: str, kitap):
    """`KosulluKural` → openpyxl `Rule` (öncelik/`stopIfTrue` çağıranda); yazılamayan türde None."""
    dxf = _kb_dxf_yaz(k.bicim)
    f = lambda x: _kb_formul_yaz(x, kitap)
    t = k.tur
    if t == "hucre_degeri":
        formul = [f(k.formul1)] + ([f(k.formul2)] if k.islec in ("arasinda", "arasinda_degil") else [])
        return Rule(type="cellIs", operator=_KB_ISLEC_YAZ[k.islec], formula=formul, dxf=dxf)
    if t == "metin":
        tirnak = '"' + k.metin.replace('"', '""') + '"'
        govde = {"icerir": f"NOT(ISERROR(SEARCH({tirnak},{ust_sol})))", "icermez": f"ISERROR(SEARCH({tirnak},{ust_sol}))",
                 "baslar": f"LEFT({ust_sol},LEN({tirnak}))={tirnak}", "biter": f"RIGHT({ust_sol},LEN({tirnak}))={tirnak}"}
        return Rule(type=_KB_METIN_TUR[k.islec], operator=_KB_METIN_OPERATOR[k.islec], text=k.metin,
                    formula=[govde[k.islec]], dxf=dxf)
    if t == "bos":
        return Rule(type="containsBlanks", formula=[f"LEN(TRIM({ust_sol}))=0"], dxf=dxf)
    if t == "bos_degil":
        return Rule(type="notContainsBlanks", formula=[f"LEN(TRIM({ust_sol}))>0"], dxf=dxf)
    if t == "hata":
        return Rule(type="containsErrors", formula=[f"ISERROR({ust_sol})"], dxf=dxf)
    if t == "hata_degil":
        return Rule(type="notContainsErrors", formula=[f"NOT(ISERROR({ust_sol}))"], dxf=dxf)
    if t == "yinelenen":
        return Rule(type="uniqueValues" if k.benzersiz else "duplicateValues", dxf=dxf)
    if t == "ilk_son":
        return Rule(type="top10", rank=k.n, percent=True if k.yuzde else None, bottom=True if k.alt else None, dxf=dxf)
    if t == "ortalama":
        return Rule(type="aboveAverage", aboveAverage=None if k.ustu else False, equalAverage=True if k.esit else None,
                    stdDev=k.std or None, dxf=dxf)
    if t == "formul":
        return Rule(type="expression", formula=[f(k.formul1)], dxf=dxf)
    if t == "renk_olcegi":
        cfvo = [FormatObject(type=_KB_NOKTA_YAZ[n[0]], val=None if n[1] is None else f(n[1])) for n in k.noktalar]
        renkler = [Color(rgb="FF" + n[2][1:]) for n in k.noktalar]
        return Rule(type="colorScale", colorScale=ColorScale(cfvo=cfvo, color=renkler))
    if t == "veri_cubugu":
        cfvo = [FormatObject(type=_KB_NOKTA_YAZ[n[0]], val=None if n[1] is None else f(n[1]))
                for n in (k.min_nokta, k.max_nokta)]
        return Rule(type="dataBar", dataBar=DataBar(cfvo=cfvo, color=Color(rgb="FF" + k.renk[1:]),
                                                    showValue=None if not k.yalniz_cubuk else False))
    return None


def _kosullulari_yaz(ws, sayfa, kitap, rapor: Rapor) -> None:
    for i, k in enumerate(sayfa.kosullu):
        a0 = k.araliklar[0]
        ust_sol = f"{get_column_letter(a0.ilk_sutun)}{a0.ilk_satir}"
        try:
            kural = _kb_kural_yaz(k, ust_sol, kitap)
        except (FormulHatasi, KeyError, ValueError):
            kural = None
        if kural is None:
            rapor.ekle(f"'{sayfa.ad}' sayfasındaki bir koşullu biçim kuralı yazılamadı.")
            continue
        kural.priority = i + 1
        if k.dur:
            kural.stopIfTrue = True
        sqref = " ".join(f"{get_column_letter(a.ilk_sutun)}{a.ilk_satir}:{get_column_letter(a.son_sutun)}{a.son_satir}"
                         for a in k.araliklar)
        ws.conditional_formatting.add(sqref, kural)


def _nokta_oku(cfvo, renk, kitap, tema):
    tur = _KB_NOKTA_OKU.get(cfvo.type)
    if tur is None:
        raise ValueError("nokta türü")
    val = cfvo.val
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        val = format(float(val), ".15g")                    # openpyxl sayısal değeri float okur
    deger = None if val is None or tur in ("min", "max") else _kb_formul_oku(val, kitap)
    return (tur, deger) if renk is None else (tur, deger, _renk_oku(renk, tema) or "#000000")


def _kb_kural_oku(r, araliklar, kitap, tema) -> Optional[KosulluKural]:
    """openpyxl `Rule` → `KosulluKural`; desteklenmeyen tür None, bozuk içerik ValueError/FormulHatasi."""
    t = r.type
    bicim = _kb_dxf_oku(r.dxf, tema)
    dur = bool(r.stopIfTrue)
    kw = dict(bicim=bicim, dur=dur)
    f = lambda i: _kb_formul_oku(r.formula[i], kitap)
    if t == "cellIs":
        islec = _KB_ISLEC_OKU.get(r.operator or "equal")
        if islec is None or not r.formula:
            raise ValueError("işleç")
        iki = islec in ("arasinda", "arasinda_degil")
        return KosulluKural(araliklar, tur="hucre_degeri", islec=islec, formul1=f(0),
                            formul2=f(1) if iki else None, **kw)
    if t in _KB_METIN_OKU:
        if r.text is None:
            raise ValueError("metin")
        return KosulluKural(araliklar, tur="metin", islec=_KB_METIN_OKU[t], metin=r.text, **kw)
    if t in ("containsBlanks", "notContainsBlanks", "containsErrors", "notContainsErrors"):
        return KosulluKural(araliklar, tur={"containsBlanks": "bos", "notContainsBlanks": "bos_degil",
                                            "containsErrors": "hata", "notContainsErrors": "hata_degil"}[t], **kw)
    if t in ("duplicateValues", "uniqueValues"):
        return KosulluKural(araliklar, tur="yinelenen", benzersiz=t == "uniqueValues", **kw)
    if t == "top10":
        return KosulluKural(araliklar, tur="ilk_son", n=int(r.rank or 10), alt=bool(r.bottom),
                            yuzde=bool(r.percent), **kw)
    if t == "aboveAverage":
        return KosulluKural(araliklar, tur="ortalama", ustu=r.aboveAverage is not False,
                            esit=bool(r.equalAverage), std=int(r.stdDev or 0), **kw)
    if t == "expression":
        if not r.formula:
            raise ValueError("formül")
        return KosulluKural(araliklar, tur="formul", formul1=f(0), **kw)
    if t == "colorScale":
        cs = r.colorScale
        if cs is None or len(cs.cfvo) not in (2, 3) or len(cs.color) != len(cs.cfvo):
            raise ValueError("renk ölçeği")
        return KosulluKural(araliklar, tur="renk_olcegi", bicim=None, dur=dur,
                            noktalar=tuple(_nokta_oku(c, k, kitap, tema) for c, k in zip(cs.cfvo, cs.color)))
    if t == "dataBar":
        db = r.dataBar
        if db is None or len(db.cfvo) != 2:
            raise ValueError("veri çubuğu")
        mn, mx = (_nokta_oku(c, None, kitap, tema) for c in db.cfvo)
        return KosulluKural(araliklar, tur="veri_cubugu", bicim=None, dur=dur,
                            renk=_renk_oku(db.color, tema) or "#638EC6", min_nokta=mn, max_nokta=mx,
                            yalniz_cubuk=db.showValue is False)
    return None


def _kosullulari_oku(ws, s, kitap, tema, rapor: Rapor) -> None:
    kurallar = []
    atlanan = 0
    for cf in ws.conditional_formatting:
        try:
            araliklar = tuple(_aralik(x) for x in cf.sqref.ranges)
        except Exception:
            atlanan += len(cf.rules)
            continue
        for r in cf.rules:
            try:
                k = _kb_kural_oku(r, araliklar, kitap, tema) if araliklar else None
            except (FormulHatasi, ValueError, KeyError, TypeError):
                k = None
            if k is None:
                atlanan += 1
            else:
                kurallar.append((r.priority or 1_000_000, len(kurallar), k))
    if atlanan:
        rapor.ekle(f"'{ws.title}' sayfasında {atlanan} koşullu biçim kuralı (simge kümesi, tarih oluşumu vb.) "
                   "desteklenmiyor; atlandı.")
    if kurallar:
        s.kosullulari_yaz([k for _, _, k in sorted(kurallar, key=lambda x: (x[0], x[1]))])


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


def _nesne_uyarilari(yol: str, rapor: Rapor, grafik: int, resim: int, atlanan_seri: int) -> None:
    """Grafik/resim uyarı mantığı (`faz6_tasarim.md` §8.3): Tabcel imi varsa ve hepsi okunduysa uyarı yok;
    im yoksa (Excel/başka program) "uyarlandı" bilgisi + kaydederken onay; okunamayan her şey kaybolur uyarısıyla."""
    zip_grafik, zip_medya, im = _nesne_sayilari(yol)
    if zip_grafik > grafik:
        rapor.ekle(f"Bu dosyadaki {zip_grafik - grafik} grafik desteklenmiyor (3B, radar, borsa, kabarcık gibi); "
                   "kaydederseniz dosyadan çıkarılır.", True)
    if zip_medya > resim:
        rapor.ekle(f"Bu dosyadaki {zip_medya - resim} resim okunamadı; kaydederseniz dosyadan çıkarılır.", True)
    if atlanan_seri:
        rapor.ekle(f"{atlanan_seri} grafik serisi okunamadı (çok aralıklı ya da ad tabanlı başvuru); "
                   "kaydederseniz kaybolur.", True)
    if (grafik or resim) and not im:
        ne = "grafikler ve resimler" if grafik and resim else ("grafikler" if grafik else "resimler")
        rapor.ekle(f"Bu dosyadaki {ne} {APP_NAME}'e uyarlandı; 3B, eğilim çizgisi, ikincil eksen, gradyan gibi "
                   "Excel'e özgü biçimler kaydedince kaybolabilir.", True)
    if zip_grafik:                                       # T10: Excel'de eklenen eğilim çizgisi/ikincil eksen/gradyan… (im varsa da)
        for metin in xlsx_kayip.kayip_uyarilari(yol, im):
            rapor.ekle(metin, True)


def ac(yol, parola: Optional[str] = None) -> "tuple[CalismaKitabi, Rapor]":
    """`yol`daki .xlsx dosyasını yeni bir kitaba okur (`yol` bellekteki paket de olabilir). Parolayla şifreliyse `parola`
    verilmelidir (yanlışsa `sifreleme.YanlisParola`, verilmediyse XlsxHatasi); çözülmüş paket yalnız bellekte tutulur. Dönen rapor desteklenmeyen öğeleri listeler.
    Formül sonuçları dosyadan alınmaz; motor yeniden hesaplar."""
    if isinstance(yol, (str, os.PathLike)) and sifreleme.sifreli_mi(yol):
        if not parola:
            raise XlsxHatasi("Bu dosya parolayla korunuyor; açmak için parola gerekir.")
        try:
            yol = sifreleme.coz(yol, parola)
        except sifreleme.SifrelemeHatasi as e:
            raise XlsxHatasi(str(e)) from e
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
    _yoksay_oku(wb, kitap)
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
            s.gizli = True
            rapor.ekle(f"Gizli sayfa '{ad}' {APP_NAME}'te görünür gösterilir; kaydederseniz dosyada yine gizli kalır.")
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
    nesne_toplam = [0, 0, 0]                         # okunan grafik, okunan resim, okunamayan seri
    for ws, s in sayfalar:
        yeni, stiller, notlar = {}, {}, {}
        kapsanan = set()                              # dizi formülünün (taşmanın) kapsadığı diğer hücreler: yeniden üretilir
        for (r, c), hc in ws._cells.items():
            va = hc.value
            if type(va).__name__ == "ArrayFormula" and va.ref:
                try:
                    cr = CellRange(va.ref)
                except (ValueError, TypeError):
                    continue
                if cr.max_row > cr.min_row or cr.max_col > cr.min_col:
                    for rr in range(cr.min_row, cr.max_row + 1):
                        for cc in range(cr.min_col, cr.max_col + 1):
                            if (rr, cc) != (r, c):
                                kapsanan.add((rr, cc))
        for (r, c), hc in ws._cells.items():          # yalnız var olan hücreler (iter_rows seyrek dosyada tüm kutuyu gezer)
            if type(hc).__name__ == "MergedCell":
                continue
            v = None if ((r, c) in kapsanan and hc.data_type != "f") else hc.value
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
            if hc.comment is not None:
                n = _not_oku(hc.comment)
                if n is not None:
                    notlar[(r, c)] = n          # dizili açıklama da düz kopyasıyla not olur (uyarı `tara`dan)
        s.toplu_yaz(yeni)
        if notlar:
            s.notlari_yaz(notlar)
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
        s.sayfa_yapisi = _yapi_oku(ws, rapor)
        _filtre_oku(ws, s, rapor)
        _dogrulamalari_oku(ws, s, kitap, rapor)
        _kosullulari_oku(ws, s, kitap, tema, rapor)
        tab = ws.sheet_properties.tabColor
        if tab is not None:
            s.sekme_rengi = _renk_oku(tab, tema)
        for i, n in enumerate(xlsx_grafik.nesneleri_oku(ws, s, kitap)):
            nesne_toplam[i] += n
    _adlari_oku(wb, kitap, sayfalar, rapor)
    _nesne_uyarilari(yol, rapor, *nesne_toplam)
    if bozuk_formul:
        rapor.ekle(f"{bozuk_formul} formül çevrilemedi, metin olarak bırakıldı.")
    return kitap, rapor
