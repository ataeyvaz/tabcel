"""`.xlsx` grafik ve resim eşlemesi (Faz 6 / 6h; `faz6_tasarim.md` §8). Qt yok.

Yazma: `Grafik` → openpyxl grafik nesnesi (her seri/dilim için AÇIK `solidFill`, böylece Excel ile aynı görünür),
`Resim` → `openpyxl.drawing.image.Image` (baytlar kayıpsız). Hepsi `oneCellAnchor` (piksel × 9525 = EMU).
Okuma: `ws._charts` / `ws._images`; anlaşılmayan tür atlanır ve sayılır (arayüz uyarısı `xlsx_io.ac`'ta).
Z sırası dosyada grafikler önce, resimler sonra yazıldığı için karışık sıra gidiş-dönüşte korunmaz (bilinen sınır).
"""
import io
import re
from typing import List, Optional, Tuple

from openpyxl.chart import AreaChart, BarChart, DoughnutChart, LineChart, PieChart, ScatterChart
from openpyxl.chart.data_source import AxDataSource, NumDataSource, NumRef, StrRef
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.legend import Legend
from openpyxl.chart.marker import DataPoint, Marker
from openpyxl.chart.series import Series, SeriesLabel
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.packaging.custom import StringProperty
from xml.etree.ElementTree import Element

from .. import __version__
from ..model.adres import Aralik, sutun_harfe
from ..model.grafik import EN_KUCUK_BOYUT, Grafik, Konum, Referans, Resim, Seri
from ..model.grafik_cizim import palet_rengi
from ..model.grafik_islem import referans_coz
from ..model.resim_yukle import resim_coz

# openpyxl 3.1.x hatası: `AreaChart.__init__` `axId` parametresini `super()`e iletmez; dosya okunurken eksenler
# grafiğe bağlanmaz (eksen başlığı/sınırı kaybolur). Yalnız eksik kalan kimlikler burada tamamlanır.
_AREA_INIT = AreaChart.__init__


def _alan_init(self, axId=None, extLst=None, **kw):
    _AREA_INIT(self, extLst=extLst, **kw)
    if axId:
        self.axId = axId


AreaChart.__init__ = _alan_init

EMU = 9525
IM_ADI = "TabcelSurum"                       # belge özelliği: dosyayı bu uygulama yazdı (grafik/resim güvenilirliği)

_LEJANT_YAZ = {"sag": "r", "sol": "l", "ust": "t", "alt": "b"}
_LEJANT_OKU = {"r": "sag", "tr": "sag", "l": "sol", "t": "ust", "b": "alt"}
_GRUP_YAZ = {"kumelenmis": "clustered", "yigili": "stacked", "yuzde_yigili": "percentStacked"}
_PASTA = ("pasta", "halka")


# ------------------------------------------------------------------ im
def im_yaz(wb) -> None:
    wb.custom_doc_props.append(StringProperty(name=IM_ADI, value=str(__version__)))


def im_var_mi(zip_dosyasi) -> bool:
    try:
        return IM_ADI.encode() in zip_dosyasi.read("docProps/custom.xml")
    except KeyError:
        return False


# ------------------------------------------------------------------ yazma
def _hex(renk: Optional[str]) -> str:
    return (renk or "000000").lstrip("#").upper()


def _ref_f(kitap, ref: Optional[Referans]) -> Optional[str]:
    """`'Sayfa Adı'!$B$2:$B$5`; sayfası silinmiş başvuru → None. Ad her zaman tırnaklı (her ad güvenle yazılır)."""
    if ref is None:
        return None
    sayfa = kitap.sayfa_kimlikle(ref.sayfa_kimlik)
    if sayfa is None:
        return None
    a = ref.aralik
    bas = f"${sutun_harfe(a.ilk_sutun)}${a.ilk_satir}"
    adres = bas if (a.ilk_satir, a.ilk_sutun) == (a.son_satir, a.son_sutun) else \
        f"{bas}:${sutun_harfe(a.son_sutun)}${a.son_satir}"
    return "'" + sayfa.ad.replace("'", "''") + "'!" + adres


def _dolgu(renk: str) -> GraphicalProperties:
    return GraphicalProperties(solidFill=_hex(renk))


def _nokta_sayisi(ref: Referans) -> int:
    a = ref.aralik
    return min(1000, (a.son_satir - a.ilk_satir + 1) * (a.son_sutun - a.ilk_sutun + 1))


def _grafik_nesnesi(g: Grafik):
    if g.tur in ("sutun", "cubuk"):
        c = BarChart()
        c.type = "col" if g.tur == "sutun" else "bar"
        c.grouping = _GRUP_YAZ[g.alt_tur]
        if g.alt_tur != "kumelenmis":
            c.overlap = 100
        return c
    if g.tur == "cizgi":
        c = LineChart()
        c.grouping = "stacked" if g.alt_tur == "yigili" else "standard"
        return c
    if g.tur == "alan":
        c = AreaChart()
        c.grouping = "stacked" if g.alt_tur == "yigili" else "standard"
        return c
    if g.tur == "pasta":
        return PieChart()
    if g.tur == "halka":
        c = DoughnutChart()
        c.holeSize = 50
        return c
    c = ScatterChart()
    c.scatterStyle = "lineMarker"
    return c


def _seri_yaz(kitap, g: Grafik, s: Seri, i: int) -> Optional[Series]:
    deger = _ref_f(kitap, s.deger)
    if deger is None:                                  # değeri/sayfası olmayan seri yazılmaz
        return None
    ser = Series(idx=i, order=i)
    kat = _ref_f(kitap, s.kategori)
    if g.tur == "dagilim":
        ser.yVal = NumDataSource(numRef=NumRef(f=deger))
        if kat:
            ser.xVal = AxDataSource(numRef=NumRef(f=kat))
    else:
        ser.val = NumDataSource(numRef=NumRef(f=deger))
        if kat:
            ser.cat = AxDataSource(strRef=StrRef(f=kat))
    ad_f = _ref_f(kitap, s.ad_ref)
    if ad_f:
        ser.tx = SeriesLabel(strRef=StrRef(f=ad_f))
    elif s.ad:
        ser.tx = SeriesLabel(v=s.ad)
    renk = s.renk or palet_rengi(i)
    if g.tur in _PASTA:
        for j in range(_nokta_sayisi(s.deger)):          # her dilime açık renk (Excel ve Tabcel aynı görünür)
            nokta = DataPoint(idx=j)
            nokta.graphicalProperties = _dolgu(palet_rengi(j))
            ser.dPt.append(nokta)
    elif g.tur in ("cizgi", "dagilim"):
        ser.graphicalProperties = GraphicalProperties()
        if g.tur == "cizgi":
            ser.graphicalProperties.line.solidFill = _hex(renk)
            ser.graphicalProperties.line.width = 28575          # 2,25 pt (çizimle aynı)
            ser.smooth = False
        else:
            ser.marker = Marker(symbol="circle", size=7)
            ser.marker.graphicalProperties = _dolgu(renk)
            ser.marker.graphicalProperties.line.solidFill = _hex(renk)
            ser.graphicalProperties.line.noFill = True
    else:
        ser.graphicalProperties = _dolgu(renk)
    return ser


def _baslik_gizle_ekle(chart) -> None:
    """Başlıksız grafikte Excel tek seride seri adını başlık yapar; `autoTitleDeleted=1` bunu engeller
    (openpyxl bu öğeyi yazdırmıyor → ağaç yazılırken eklenir)."""
    orijinal = chart._write

    def yaz():
        agac = orijinal()
        kap = agac.find("chart")                      # openpyxl ağacında etiketler ad alanı almaz (xmlns kökte)
        if kap is not None and kap.find("autoTitleDeleted") is None:
            kap.insert(0, Element("autoTitleDeleted", {"val": "1"}))
        return agac
    chart._write = yaz


def _ankraj(konum: Konum, boyut: Tuple[int, int]) -> OneCellAnchor:
    return OneCellAnchor(_from=AnchorMarker(col=konum.sutun - 1, colOff=konum.dx * EMU,
                                            row=konum.satir - 1, rowOff=konum.dy * EMU),
                         ext=XDRPositiveSize2D(cx=boyut[0] * EMU, cy=boyut[1] * EMU))


def grafik_yaz(ws, g: Grafik, kitap) -> bool:
    """Grafiği `ws`e ekler; hiç yazılabilir seri yoksa False (grafik yazılmaz)."""
    c = _grafik_nesnesi(g)
    for i, s in enumerate(g.seriler):
        ser = _seri_yaz(kitap, g, s, i)
        if ser is not None:
            c.series.append(ser)
    if not c.series:
        return False
    if g.baslik:
        c.title = g.baslik
        c.title.overlay = False                        # başlık grafik alanının üstüne binmesin (Excel'de denendi)
    else:
        c.title = None
        _baslik_gizle_ekle(c)
    c.legend = Legend(legendPos=_LEJANT_YAZ[g.gosterge], overlay=False) if g.gosterge else None
    if g.deger_etiketi:
        c.dataLabels = DataLabelList(showVal=g.tur not in _PASTA, showPercent=g.tur in _PASTA, showSerName=False,
                                     showCatName=False, showLegendKey=False)
    if g.tur not in _PASTA:
        c.x_axis.delete = False
        c.y_axis.delete = False
        yatay_baslik, dikey_baslik = g.x_baslik, g.y_baslik
        if g.tur == "cubuk":                            # dosyada kategori ekseni dikey: başlıklar yer değiştirir
            c.x_axis.title, c.y_axis.title = dikey_baslik, yatay_baslik
        else:
            c.x_axis.title, c.y_axis.title = yatay_baslik, dikey_baslik
        for eksen in (c.x_axis, c.y_axis):
            if eksen.title is not None:
                eksen.title.overlay = False
        for eksen in (c.x_axis, c.y_axis):                 # varsayılan siyah ızgara çizgileri yerine çizimdeki açık gri
            if eksen.majorGridlines is not None:
                eksen.majorGridlines.spPr = GraphicalProperties()
                eksen.majorGridlines.spPr.line.solidFill = "D9D9D9"
        c.y_axis.scaling.min, c.y_axis.scaling.max = g.y_min, g.y_max
        if g.tur == "dagilim":
            c.x_axis.scaling.min, c.x_axis.scaling.max = g.x_min, g.x_max
    c.anchor = _ankraj(g.konum, g.boyut)
    ws.add_chart(c)
    return True


def resim_yaz(ws, r: Resim) -> bool:
    try:
        im = Image(io.BytesIO(r.veri))
    except Exception:
        return False
    im.anchor = _ankraj(r.konum, r.boyut)
    ws.add_image(im)
    return True


def nesneleri_yaz(ws, sayfa, kitap) -> Tuple[int, int]:
    """Sayfanın nesnelerini yazar. Döner: `(yazılamayan grafik, yazılamayan resim)` — grafik yazılamaz: hiç yazılabilir
    serisi kalmadı (verisi silindi / silinen sayfaya bağlı); resim yazılamaz: bozuk. Kayıt raporu bunları bildirir."""
    grafik_yok = resim_yok = 0
    for n in sayfa.nesneler:
        if isinstance(n, Grafik):
            grafik_yok += 0 if grafik_yaz(ws, n, kitap) else 1
        elif isinstance(n, Resim):
            resim_yok += 0 if resim_yaz(ws, n) else 1
    return grafik_yok, resim_yok


# ------------------------------------------------------------------ okuma
def _renk_cevir(gp, i: int) -> Optional[str]:
    """Seri rengi: `solidFill` (grafik dolgusu) → çizgi → işaretçi sırasıyla; palet rengiyse None (açık renk yok)."""
    adaylar = []
    if gp is not None:
        adaylar.append(getattr(gp, "solidFill", None))
        adaylar.append(getattr(getattr(gp, "line", None), "solidFill", None))
    for dolgu in adaylar:
        rgb = getattr(dolgu, "srgbClr", None)
        deger = getattr(rgb, "val", rgb) if rgb is not None else None
        if isinstance(deger, str) and re.fullmatch(r"[0-9A-Fa-f]{6}", deger):
            renk = "#" + deger.upper()
            return None if renk == palet_rengi(i).upper() else renk
    return None


def _metin(baslik) -> Optional[str]:
    """Başlık nesnesinden düz metin (zengin metin paragrafları satır sonuyla)."""
    try:
        paragraflar = baslik.tx.rich.p
    except AttributeError:
        return None
    satirlar = ["".join((r.t or "") for r in (p.r or [])) for p in paragraflar]
    metin = "\n".join(satirlar).strip()
    return metin or None


def _ref_oku(kitap, f, varsayilan) -> Optional[Referans]:
    return referans_coz(kitap, f, varsayilan) if f else None


def _seri_oku(kitap, s, ser, i: int, dagilim: bool) -> Optional[Seri]:
    """openpyxl serisi → `Seri`; değeri okunamıyorsa None (çok aralıklı, ad tabanlı, sabit dizi…)."""
    try:
        if dagilim:
            deger = _ref_oku(kitap, getattr(getattr(ser.yVal, "numRef", None), "f", None), s)
            kat_kaynak = ser.xVal
        else:
            deger = _ref_oku(kitap, getattr(getattr(ser.val, "numRef", None), "f", None), s)
            kat_kaynak = ser.cat
        if deger is None:
            return None
        kat = None
        if kat_kaynak is not None:
            f = (getattr(getattr(kat_kaynak, "numRef", None), "f", None)
                 or getattr(getattr(kat_kaynak, "strRef", None), "f", None))
            try:
                kat = _ref_oku(kitap, f, s)
            except ValueError:
                kat = None                                   # kategori okunamadı: seri kategorisiz kalır
        ad, ad_ref = None, None
        if ser.tx is not None:
            if ser.tx.strRef is not None and ser.tx.strRef.f:
                try:
                    ad_ref = _ref_oku(kitap, ser.tx.strRef.f, s)
                except ValueError:
                    ad_ref = None
            elif ser.tx.v:
                ad = ser.tx.v
        gp = ser.marker.graphicalProperties if dagilim and ser.marker is not None else ser.graphicalProperties
        return Seri(ad=ad, ad_ref=ad_ref, deger=deger, kategori=kat, renk=_renk_cevir(gp, i))
    except ValueError:
        return None


def _tur_coz(c) -> Optional[Tuple[str, str]]:
    """openpyxl grafik sınıfı → (tür, alt tür); desteklenmeyen (3B, radar, borsa, kabarcık, yüzde yığılı çizgi…) None."""
    t = type(c)
    if t is BarChart:
        alt = {"clustered": "kumelenmis", "stacked": "yigili", "percentStacked": "yuzde_yigili"}.get(c.grouping)
        return ("sutun" if c.type == "col" else "cubuk", alt) if alt else None
    if t in (LineChart, AreaChart):
        alt = {"standard": "kumelenmis", "stacked": "yigili"}.get(c.grouping)
        return ("cizgi" if t is LineChart else "alan", alt) if alt else None
    if t is PieChart:
        return "pasta", "kumelenmis"
    if t is DoughnutChart:
        return "halka", "kumelenmis"
    if t is ScatterChart:
        return "dagilim", "kumelenmis"
    return None


def _piksel_olcusu(s, bas_sutun: int, bas_ofset: int, bit_sutun: int, bit_ofset: int,
                   bas_satir: int, bas_sofset: int, bit_satir: int, bit_sofset: int) -> Tuple[int, int]:
    w = sum(s.genislik(c) for c in range(bas_sutun, bit_sutun)) - bas_ofset + bit_ofset
    h = sum(s.yukseklik(r) for r in range(bas_satir, bit_satir)) - bas_sofset + bit_sofset
    return w, h


def _ankraj_oku(s, anchor, varsayilan: Tuple[int, int]) -> Optional[Tuple[Konum, Tuple[int, int]]]:
    """oneCell / twoCell / absolute çapa → (`Konum`, boyut px). Tanınmayan çapa → None."""
    if anchor is None or isinstance(anchor, str):
        return None
    ad = type(anchor).__name__
    try:
        if ad in ("OneCellAnchor", "TwoCellAnchor"):
            f = anchor._from
            konum = Konum(f.row + 1, f.col + 1, max(0, round(f.colOff / EMU)), max(0, round(f.rowOff / EMU)))
            if ad == "OneCellAnchor":
                boyut = (round(anchor.ext.width / EMU), round(anchor.ext.height / EMU))
            else:
                t = anchor.to
                boyut = _piksel_olcusu(s, f.col + 1, round(f.colOff / EMU), t.col + 1, round(t.colOff / EMU),
                                       f.row + 1, round(f.rowOff / EMU), t.row + 1, round(t.rowOff / EMU))
        elif ad == "AbsoluteAnchor":
            x, y = round(anchor.pos.x / EMU), round(anchor.pos.y / EMU)
            sutun, kalan_x = 1, x
            while kalan_x >= max(1, s.genislik(sutun)) and sutun < 16384:
                kalan_x -= max(1, s.genislik(sutun))
                sutun += 1
            satir, kalan_y = 1, y
            while kalan_y >= max(1, s.yukseklik(satir)) and satir < 1048576:
                kalan_y -= max(1, s.yukseklik(satir))
                satir += 1
            konum = Konum(satir, sutun, kalan_x, kalan_y)
            boyut = (round(anchor.ext.width / EMU), round(anchor.ext.height / EMU))
        else:
            return None
    except (AttributeError, ValueError, TypeError):
        return None
    g, y = boyut if boyut[0] > 0 and boyut[1] > 0 else varsayilan
    return konum, (max(EN_KUCUK_BOYUT[0], g), max(EN_KUCUK_BOYUT[1], y))


def grafik_oku(c, s, kitap) -> Tuple[Optional[Grafik], int]:
    """Bir openpyxl grafiği → (`Grafik` ya da None, okunamayan seri sayısı). None = grafik desteklenmiyor."""
    tur_alt = _tur_coz(c)
    if tur_alt is None:
        return None, 0
    tur, alt = tur_alt                  # birleşik grafikte yalnız ilk grafik okunur (ikincil eksen/tür kaybolur)
    konum = _ankraj_oku(s, c.anchor, (480, 288))
    if konum is None:
        return None, 0
    seriler, atlanan = [], 0
    for i, ser in enumerate(c.series):
        yeni = _seri_oku(kitap, s, ser, i, tur == "dagilim")
        if yeni is None:
            atlanan += 1
        else:
            seriler.append(yeni)
    if tur in _PASTA:
        seriler = seriler[:1]
    if not seriler:
        return None, atlanan
    etiket = bool(c.dataLabels is not None and (c.dataLabels.showVal or c.dataLabels.showPercent)) or any(
        d.dLbls is not None and (d.dLbls.showVal or d.dLbls.showPercent) for d in c.series)
    x_baslik = y_baslik = x_min = x_max = y_min = y_max = None
    if tur not in _PASTA:
        kat_baslik, deger_baslik = _metin(c.x_axis.title), _metin(c.y_axis.title)
        x_baslik, y_baslik = (deger_baslik, kat_baslik) if tur == "cubuk" else (kat_baslik, deger_baslik)
        y_min, y_max = c.y_axis.scaling.min, c.y_axis.scaling.max
        if tur == "dagilim":
            x_min, x_max = c.x_axis.scaling.min, c.x_axis.scaling.max
    gosterge = _LEJANT_OKU.get(c.legend.legendPos, "sag") if c.legend is not None else None
    return Grafik(tur=tur, alt_tur=alt, seriler=tuple(seriler), baslik=_metin(c.title), gosterge=gosterge,
                  x_baslik=x_baslik, y_baslik=y_baslik, deger_etiketi=etiket, y_min=y_min, y_max=y_max,
                  x_min=x_min, x_max=x_max, konum=konum[0], boyut=konum[1]), atlanan


def resim_oku(im, s) -> Optional[Resim]:
    try:
        veri = im._data()
        g, y = resim_coz(veri)
    except Exception:
        return None
    konum = _ankraj_oku(s, im.anchor, (g, y))
    if konum is None:
        return None
    return Resim(veri=veri, konum=konum[0], boyut=konum[1])


def nesneleri_oku(ws, s, kitap) -> Tuple[int, int, int]:
    """Sayfadaki grafik/resimleri `s`e ekler (komutsuz; kitap yüklenirken). Döner: (okunan grafik, okunan resim,
    okunamayan seri)."""
    grafik = resim = atlanan_seri = 0
    for c in list(getattr(ws, "_charts", [])):
        g, atl = grafik_oku(c, s, kitap)
        atlanan_seri += atl
        if g is not None:
            s.nesne_ekle(g)
            grafik += 1
    for im in list(getattr(ws, "_images", [])):
        r = resim_oku(im, s)
        if r is not None:
            s.nesne_ekle(r)
            resim += 1
    return grafik, resim, atlanan_seri
