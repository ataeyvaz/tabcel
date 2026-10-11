"""T10 (t10_xlsx_kayip_tasarim.md): Excel'de eklenen eğilim çizgisi/ikincil eksen/gradyan… sessizce kaybolmaz; Tabcel'in kendi
yazdığı ve Excel'den aç-kaydet geçmiş dosya UYARISIZ kalır. Örnekler `testler/ornekler/excel/` (gerçek Excel, COM)."""
import os
import zipfile

import pytest
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.trendline import Trendline

from tabcel.io import xlsx_io
from tabcel.io.xlsx_kayip import grafik_basligi, grafik_ozellikleri, grafik_parcalari
from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Konum, Referans, Seri
from tabcel.model.grafik_cizim import palet_rengi
from tabcel.model.sayfa import CalismaKitabi, Hucre

KLASOR = os.path.join(os.path.dirname(__file__), "ornekler")
EXCEL = os.path.join(KLASOR, "excel")
GENEL = "uyarlandı"                                    # imsiz dosyadaki genel ileti


def _kayip(rapor):
    return [u for u in rapor.uyarilar if "desteklemediği öğeler" in u or "varsayılanına döner" in u]


# ---------------------------------------------------------------- (a) Tabcel yazdı → uyarısız
def test_tabcel_ornegi_uyarisiz():
    _, r = xlsx_io.ac(os.path.join(KLASOR, "grafikler.xlsx"))
    assert r.uyarilar == [] and not r.veri_kaybi


def test_tum_alanlari_dolu_tabcel_grafigi_uyarisiz(tmp_path):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, (ad, v) in enumerate([("a", 3.0), ("b", 5.0), ("c", 4.0)], start=1):
        s.ata(i, 1, Hucre(ad))
        s.ata(i, 2, Hucre(v))
    kim = s.kimlik
    for tur in ("sutun", "cizgi", "pasta", "dagilim"):
        g = Grafik(tur=tur, baslik=f"Başlık {tur}", x_baslik="X", y_baslik="Y", deger_etiketi=True, gosterge="alt",
                   y_min=0.0, y_max=10.0,
                   seriler=(Seri(deger=Referans(kim, Aralik(1, 2, 3, 2)), kategori=Referans(kim, Aralik(1, 1, 3, 1)),
                                 ad="Seri", renk="#FF0000"),), konum=Konum(2, 4))
        s.nesne_ekle(g)
    xlsx_io.kaydet(k, str(tmp_path / "t.xlsx"))
    _, r = xlsx_io.ac(str(tmp_path / "t.xlsx"))
    assert r.uyarilar == [] and not r.veri_kaybi


# ---------------------------------------------------------------- (b) Excel aç-kaydet → uyarısız
@pytest.mark.parametrize("ad", ["gecis.xlsx", "gecis_gecis.xlsx"])
def test_excel_ac_kaydet_uyarisiz(ad):
    _, r = xlsx_io.ac(os.path.join(EXCEL, ad))
    assert r.uyarilar == [] and not r.veri_kaybi


# ---------------------------------------------------------------- (c) Excel ile özellik eklenmiş → uyarılı
BEKLENEN = [
    ("trend.xlsx", ["eğilim çizgisi"]), ("hata.xlsx", ["hata çubukları"]),
    ("eksen2.xlsx", ["ikincil eksen"]), ("birlesik.xlsx", ["birleşik grafik"]),
    ("gradyan.xlsx", ["gradyan/desen/resim dolgusu"]), ("desen.xlsx", ["gradyan/desen/resim dolgusu"]),
    ("nokta.xlsx", ["tek tek biçimlendirilmiş veri noktası"]), ("etiket.xlsx", ["veri etiketi ayrıntıları"]),
    ("log.xlsx", ["eksen ölçeği (logaritmik/ters)"]), ("bos.xlsx", ["boş hücre gösterimi"]),
    ("yumusak.xlsx", ["düzgünleştirilmiş çizgi"]), ("isaret.xlsx", ["çizgi işaretçileri"]),
    ("baslikyazi.xlsx", ["yazı biçimi"]), ("bosluk.xlsx", ["çubuk aralığı"]),
    ("stil.xlsx", ["gradyan/desen/resim dolgusu", "gizlenmiş eksen", "tema rengi", "çubuk aralığı", "yazı biçimi",
                   "alan/çerçeve biçimi", "grafik stili"]),
]


@pytest.mark.parametrize("ad,etiketler", BEKLENEN)
def test_excel_ile_eklenen_ozellik_uyarilir(ad, etiketler):
    _, r = xlsx_io.ac(os.path.join(EXCEL, ad))
    kayip = _kayip(r)
    assert r.veri_kaybi and len(kayip) == 1, r.uyarilar
    for e in etiketler:
        assert e in kayip[0], (e, kayip[0])
    assert "(Sayfa1)" in kayip[0] and "grafi" in kayip[0]                  # grafik ve sayfa adı geçer
    assert "'" in kayip[0]                                                 # başlıklı grafik: 'Başlık' grafiğinde


def test_eksen2_ikincil_eksen_gizlenmis_eksen_demez():
    _, r = xlsx_io.ac(os.path.join(EXCEL, "eksen2.xlsx"))
    assert "gizlenmiş eksen" not in _kayip(r)[0]                          # A7: yalnız ≤ 2 eksende


def test_b_sinifi_imsiz_dosyada_gosterilmez_yalniz_genel_ileti(tmp_path):
    """İm yok: aynı Excel dosyasından im kaldırılınca B (biçim) satırı çıkmaz, genel 'uyarlandı' iletisi kalır."""
    kaynak = os.path.join(EXCEL, "baslikyazi.xlsx")
    hedef = str(tmp_path / "imsiz.xlsx")
    with zipfile.ZipFile(kaynak) as zi, zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in zi.namelist():
            veri = zi.read(n)
            if n == "docProps/custom.xml":
                veri = veri.replace(b"TabcelSurum", b"BaskaAd")
            zo.writestr(n, veri)
    _, r = xlsx_io.ac(hedef)
    assert any(GENEL in u for u in r.uyarilar) and _kayip(r) == []


# ---------------------------------------------------------------- (d)(e) imsiz dosyalar
def _opx(trend: bool, n: int = 1):
    wb = Workbook()
    ws = wb.active
    ws.append(["Ay", "S"])
    for i in range(1, 5):
        ws.append([f"m{i}", i * 10])
    for j in range(n):
        g = BarChart()
        g.add_data(Reference(ws, min_col=2, min_row=1, max_row=5), titles_from_data=True)
        g.set_categories(Reference(ws, min_col=1, min_row=2, max_row=5))
        if trend:
            g.series[0].trendline = Trendline()
        ws.add_chart(g, f"D{2 + j * 16}")
    return wb


def test_openpyxl_egilim_cizgisi_genel_ileti_ve_satir(tmp_path):
    _opx(True).save(tmp_path / "a.xlsx")
    _, r = xlsx_io.ac(str(tmp_path / "a.xlsx"))
    assert any(GENEL in u for u in r.uyarilar)
    assert len(_kayip(r)) == 1 and "eğilim çizgisi" in _kayip(r)[0] and "1. grafikte (Sheet)" in _kayip(r)[0]


def test_openpyxl_duz_grafik_yalniz_genel_ileti(tmp_path):
    _opx(False).save(tmp_path / "b.xlsx")
    _, r = xlsx_io.ac(str(tmp_path / "b.xlsx"))
    assert len(r.uyarilar) == 1 and GENEL in r.uyarilar[0]


def test_excel_sifirdan_grafikler_yalniz_genel_ileti():
    """Excel'de sıfırdan çizilmiş sütun/çizgi/pasta (im yok): sahte A uyarısı yok (pasta `schemeClr accentN` istisnası)."""
    _, r = xlsx_io.ac(os.path.join(EXCEL, "excel_yeni.xlsx"))
    assert len(r.uyarilar) == 1 and GENEL in r.uyarilar[0]


def test_uc_grafikten_fazlasinda_ozet_satiri(tmp_path):
    _opx(True, n=5).save(tmp_path / "c.xlsx")
    _, r = xlsx_io.ac(str(tmp_path / "c.xlsx"))
    assert len(_kayip(r)) == 3
    assert any("…ve 2 grafikte daha desteklenmeyen öğe var" in u for u in r.uyarilar)


def test_tabcel_kaydedince_ogeler_gider_yeniden_acinca_uyari_yok(tmp_path):
    k, r = xlsx_io.ac(os.path.join(EXCEL, "trend.xlsx"))
    assert r.veri_kaybi
    xlsx_io.kaydet(k, str(tmp_path / "k.xlsx"))
    _, r2 = xlsx_io.ac(str(tmp_path / "k.xlsx"))
    assert r2.uyarilar == [] and not r2.veri_kaybi


# ---------------------------------------------------------------- birim: kural kural küçük XML
NS = ('xmlns="http://schemas.openxmlformats.org/drawingml/2006/chart" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"')


def _xml(grup="<barChart><ser><idx val='0'/>{ser}</ser>{grup}</barChart>", ser="", grup_ek="",
         eksenler="<catAx><delete val='0'/></catAx><valAx><delete val='0'/></valAx>", chart_ek="", kok_ek=""):
    g = grup.format(ser=ser, grup=grup_ek) if "{ser}" in grup else grup
    return f"<chartSpace {NS}><chart>{chart_ek}<plotArea>{g}{eksenler}</plotArea></chart>{kok_ek}</chartSpace>".encode()


def test_birim_bos_ve_temiz():
    assert grafik_ozellikleri(_xml()) == ([], [])


def test_birim_bozuk_xml_ve_desteklenmeyen_tur_bos():
    assert grafik_ozellikleri(b"<c/>") == ([], [])
    assert grafik_ozellikleri(b"<bozuk") == ([], [])
    assert grafik_ozellikleri(_xml(grup="<radarChart><ser/></radarChart>")) == ([], [])
    assert grafik_ozellikleri(_xml(grup="<bar3DChart><ser/></bar3DChart>")) == ([], [])


@pytest.mark.parametrize("ser,beklenen", [
    ("<trendline/>", "eğilim çizgisi"), ("<errBars/>", "hata çubukları"),
    ("<dPt><idx val='0'/></dPt>", "tek tek biçimlendirilmiş veri noktası"),
    ("<dLbls><showCatName val='1'/></dLbls>", "veri etiketi ayrıntıları"),
    ("<dLbls><dLbl><idx val='0'/></dLbl></dLbls>", "veri etiketi ayrıntıları"),
])
def test_birim_seri_kurallari(ser, beklenen):
    assert beklenen in grafik_ozellikleri(_xml(ser=ser))[0]


def test_birim_showbubblesize_sahte_uyari_vermez():
    """Excel aç-kaydette `showBubbleSize=1` yazar: kural DEĞİL."""
    assert grafik_ozellikleri(_xml(ser="<dLbls><showVal val='1'/><showBubbleSize val='1'/></dLbls>")) == ([], [])


def test_birim_dagilim_smooth_sahte_uyari_vermez_cizgide_verir():
    sk = "<scatterChart><ser><smooth val='1'/><spPr><a:ln><a:noFill/></a:ln></spPr></ser></scatterChart>"
    assert grafik_ozellikleri(_xml(grup=sk, eksenler="<valAx/><valAx/>")) == ([], [])
    ck = "<lineChart><ser><smooth val='1'/><marker><symbol val='none'/></marker></ser></lineChart>"
    assert grafik_ozellikleri(_xml(grup=ck))[0] == ["düzgünleştirilmiş çizgi"]


def test_birim_eksen_kurallari():
    log = "<catAx/><valAx><scaling><logBase val='10'/></scaling></valAx>"
    assert "eksen ölçeği (logaritmik/ters)" in grafik_ozellikleri(_xml(eksenler=log))[0]
    ters = "<catAx/><valAx><scaling><orientation val='maxMin'/></scaling></valAx>"
    assert "eksen ölçeği (logaritmik/ters)" in grafik_ozellikleri(_xml(eksenler=ters))[0]
    assert "eksen ölçeği (birim)" in grafik_ozellikleri(_xml(eksenler="<catAx/><valAx><majorUnit val='5'/></valAx>"))[0]
    gizli = "<catAx><delete val='1'/></catAx><valAx/>"
    assert "gizlenmiş eksen" in grafik_ozellikleri(_xml(eksenler=gizli))[0]
    uc = "<catAx><delete val='1'/></catAx><valAx/><valAx/>"
    a = grafik_ozellikleri(_xml(eksenler=uc))[0]
    assert "ikincil eksen" in a and "gizlenmiş eksen" not in a


def test_birim_birlesik_ve_chart_duzeyi():
    iki = "<barChart><ser/></barChart><lineChart><ser/></lineChart>"
    assert "birleşik grafik" in grafik_ozellikleri(_xml(grup=iki))[0]
    assert "boş hücre gösterimi" in grafik_ozellikleri(_xml(chart_ek="<dispBlanksAs val='zero'/>"))[0]
    assert grafik_ozellikleri(_xml(chart_ek="<dispBlanksAs val='gap'/>")) == ([], [])
    assert "gizli hücre verisi" in grafik_ozellikleri(_xml(chart_ek="<plotVisOnly val='0'/>"))[0]
    assert "yardımcı çizgiler" in grafik_ozellikleri(_xml(grup_ek="<dropLines/>"))[0]
    assert "gradyan/desen/resim dolgusu" in grafik_ozellikleri(_xml(ser="<spPr><a:gradFill/></spPr>"))[0]


def test_birim_b_kurallari():
    a, b = grafik_ozellikleri(_xml(grup_ek="<gapWidth val='50'/>"))
    assert a == [] and b == ["çubuk aralığı"]
    assert grafik_ozellikleri(_xml(grup_ek="<gapWidth val='150'/><overlap val='100'/>")) == ([], [])
    assert "yazı biçimi" in grafik_ozellikleri(_xml(kok_ek="<txPr/>"))[1]
    assert "alan/çerçeve biçimi" in grafik_ozellikleri(_xml(kok_ek="<spPr/>"))[1]
    renkli = "<spPr><a:solidFill><a:schemeClr val='accent1'/></a:solidFill></spPr>"
    assert "tema rengi" in grafik_ozellikleri(_xml(ser=renkli))[1]
    duz = "<spPr><a:solidFill><a:srgbClr val='FF0000'/></a:solidFill></spPr>"
    assert grafik_ozellikleri(_xml(ser=duz)) == ([], [])


def _pasta(dp):
    return _xml(grup=f"<pieChart><ser>{dp}</ser></pieChart>", eksenler="")


def test_birim_pasta_dilim_istisnasi():
    palet = (f"<dPt><idx val='1'/><spPr><a:solidFill><a:srgbClr val='{palet_rengi(1)[1:]}'/></a:solidFill>"
             "</spPr></dPt>")
    assert grafik_ozellikleri(_pasta(palet)) == ([], [])                                 # Tabcel'in kendi rengi
    tema = "<dPt><idx val='1'/><spPr><a:solidFill><a:schemeClr val='accent2'/></a:solidFill></spPr></dPt>"
    a, b = grafik_ozellikleri(_pasta(tema))
    assert a == [] and b == ["tema rengi"]                                               # Excel'in sıfırdan pastası: A değil
    baska = "<dPt><idx val='1'/><spPr><a:solidFill><a:srgbClr val='123456'/></a:solidFill></spPr></dPt>"
    assert "tek tek biçimlendirilmiş veri noktası" in grafik_ozellikleri(_pasta(baska))[0]
    ayrik = "<dPt><idx val='0'/><explosion val='20'/></dPt>"
    assert "ayrık pasta dilimi" in grafik_ozellikleri(_pasta(ayrik))[0]


def test_birim_baslik_ve_parcalar():
    xml = (f"<chartSpace {NS}><chart><title><tx><rich><a:p><a:r><a:t>Aylık </a:t></a:r><a:r><a:t>satış</a:t></a:r></a:p>"
           "</rich></tx></title><plotArea><barChart/></plotArea></chart></chartSpace>").encode()
    assert grafik_basligi(xml) == "Aylık satış"
    assert grafik_basligi(_xml()) is None and grafik_basligi(b"<bozuk") is None
    with zipfile.ZipFile(os.path.join(KLASOR, "grafikler.xlsx")) as z:
        p = grafik_parcalari(z)
    assert len(p) == 13 and all(x[0] == "Sayfa1" for x in p)
    assert [x[1] for x in p] == list(range(1, 14))


def test_onbellekler_ayiklanir_buyuk_grafikte_tarama_hizli_kalir():
    """100.000 noktalı grafikte Excel'in `numCache/strCache` blokları ayrıştırılmadan atılır (süre değil boyut sınanır:
    zamanlama testleri yükte kırılgan; ölçüm: 9,3 MB XML ≈ 200 ms)."""
    from tabcel.io.xlsx_kayip import _sadelestir
    n = 3000
    pts = "".join(f"<c:pt idx='{i}'><c:v>{i}</c:v></c:pt>" for i in range(n))
    xml = (f"<c:chartSpace xmlns:c='http://schemas.openxmlformats.org/drawingml/2006/chart' "
           "xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'><c:chart><c:plotArea><c:barChart>"
           f"<c:ser><c:trendline/><c:val><c:numRef><c:f>x</c:f><c:numCache><c:ptCount val='{n}'/>{pts}</c:numCache>"
           f"</c:numRef></c:val></c:ser></c:barChart><c:catAx/><c:valAx/></c:plotArea></c:chart></c:chartSpace>").encode()
    assert len(xml) > 65536 and len(_sadelestir(xml)) < 1000
    assert grafik_ozellikleri(xml)[0] == ["eğilim çizgisi"]                  # ayıklama kuralları bozmaz
