"""Excel/Word ile pano sadakati (2026-10-15 elle test turunda gerçek Excel 16 ile denendi): dışarıya görünen metin + `x:num`/`x:fmla`/
`mso-number-format`, içeri Excel HTML'indeki CSS (kalın, dolgu, sayı biçimi) + akıllı tarih/yüzde çözümü."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from tabcel.model import pano
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil
from tabcel.ui.grid import Izgara

# Gerçek Excel 16'nın (Türkçe) panoya koyduğu HTML'in kısaltılmış hâli (CSS sınıfları, mso-number-format)
EXCEL_HTML = """<html xmlns:x="urn:schemas-microsoft-com:office:excel"><head><style><!--table
	{mso-displayed-decimal-separator:"\\,";}
td
	{color:black;font-weight:400;font-style:normal;mso-number-format:General;text-align:general;white-space:nowrap;}
.xl65
	{white-space:normal;}
.xl66
	{mso-number-format:Standard;}
.xl67
	{mso-number-format:"0\\.0%";}
.xl68
	{mso-number-format:"dd\\/mm\\/yyyy";}
.xl69
	{font-weight:700;
	background:#70B050;
	mso-pattern:black none;}
--></style></head><body><table>
 <tr><td class=xl69>Ürün</td><td class=xl69>Fiyat</td><td class=xl69>Oran</td><td class=xl69>Tarih</td><td class=xl69>Not</td></tr>
 <tr><td>Çay (İ,ı,Ş,ğ)</td><td class=xl66 align=right>1.234,50</td><td class=xl67 align=right>25,5%</td>
  <td class=xl68 align=right>15.10.2026</td><td align=right>1481,4</td></tr>
 <tr><td class=xl65>Satır<br>sonu</td><td class=xl66 align=right>10,00</td><td class=xl67 align=right>10,0%</td>
  <td class=xl68 align=right>16.10.2026</td><td x:num="12" x:fmla="=SUM(B2:B3)" align=right>12</td></tr>
</table></body></html>"""


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def g(app):
    k = CalismaKitabi()
    izgara = Izgara(k.sayfalar[0])
    yield izgara


def panoya_html(html: str, text: str = "x"):
    md = QMimeData()
    md.setHtml(html)
    md.setText(text)
    QApplication.clipboard().setMimeData(md)


# ---------------------------------------------------------------- model: dışarıya
def _veri_tarihli():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(46310.0))                       # 15.10.2026
    s.ata(1, 2, Hucre(0.255))
    s.ata(1, 3, Hucre(1234.5))
    s.ata(1, 4, Hucre(None, "=C1*2"))
    s.bicim_yaz(hucreler={(1, 1): k.stil_havuzu.kimlik(Stil(sayi_bicimi="dd.mm.yyyy")),
                          (1, 2): k.stil_havuzu.kimlik(Stil(sayi_bicimi="0.0%")),
                          (1, 3): k.stil_havuzu.kimlik(Stil(sayi_bicimi='#,##0.00', kalin=True, dolgu="#C6E0B4"))})
    from tabcel.model.adres import Aralik
    v = pano.pano_verisi_al(s, Aralik(1, 1, 1, 4))
    v.en_formul[(0, 3)] = "=C1*2"
    return v


def test_gorunen_satirlar_biçimli_metin_verir():
    v = _veri_tarihli()
    assert pano.gorunen_satirlar(v)[0][:3] == ["15.10.2026", "25,5%", "1.234,50"]
    assert pano.metin_satirlari(v)[0][:3] == ["46310", "0,255", "1234,5"]        # eski davranış (biçimsiz) korunur


def test_html_excel_ozellikleri():
    v = _veri_tarihli()
    h = pano.html_yaz_excel(pano.gorunen_satirlar(v), v.stiller, pano.html_ayrintilari(v))
    assert 'xmlns:x="urn:schemas-microsoft-com:office:excel"' in h
    assert 'x:num="46310.0"' in h and 'x:num="0.255"' in h
    assert "mso-number-format:&quot;dd\\.mm\\.yyyy&quot;" in h                        # Excel'in kaçış biçimi
    assert 'x:fmla="=C1*2"' in h
    assert "font-weight:bold" in h and "background:#C6E0B4" in h
    assert pano.html_tablo_coz(h)[0][:3] == ["15.10.2026", "25,5%", "1.234,50"]      # eski ayrıştırıcı hâlâ okur


def test_html_stilli_ayristirici_excel_ciktisi():
    satirlar, oz = pano.html_tablo_stilli(EXCEL_HTML)
    assert satirlar[1] == ["Çay (İ,ı,Ş,ğ)", "1.234,50", "25,5%", "15.10.2026", "1481,4"]
    assert satirlar[2][0] == "Satır\nsonu"
    assert oz[(0, 0)]["stil"].kalin and oz[(0, 0)]["stil"].dolgu == "#70B050"
    assert oz[(1, 1)]["kod"] == "#,##0.00" and oz[(1, 2)]["kod"] == "0.0%" and oz[(1, 3)]["kod"] == "dd/mm/yyyy"
    assert oz[(2, 0)]["stil"].kaydir is True                                        # white-space:normal
    assert oz[(2, 4)]["fmla"] == "=SUM(B2:B3)" and oz[(2, 4)]["num"] == 12.0
    assert oz[(1, 0)]["stil"] is None and oz[(1, 4)]["stil"] is None               # düz hücre: varsayılan


@pytest.mark.parametrize("deger,beklenen", [('"\\#\\,\\#\\#0\\.00"', "#,##0.00"), ("Standard", "#,##0.00"), ("Percent", "0%"),
                                            ("General", None), ('"0\\.0%"', "0.0%"), ('"dd\\/mm\\/yyyy"', "dd/mm/yyyy"), ("@", "@")])
def test_mso_sayi_bicimi_cozumu(deger, beklenen):
    assert pano._kod_coz(deger) == beklenen


def test_bozuk_html_cokmez():
    assert pano.html_tablo_stilli("<p>yok</p>") == ([], {})
    assert pano.html_tablo_stilli("")[0] == []
    assert pano.html_tablo_stilli("<table><tr><td class=x style='font-weight:700'>a")[0] == []


# ---------------------------------------------------------------- ızgara: dışarıdan içeri
def test_excel_html_yapistirma_deger_biçim_ve_stil(g):
    panoya_html(EXCEL_HTML)
    g.sec((10, 1))
    g.yapistir()
    s = g.sayfa
    assert s.deger(10, 1) == "Ürün" and s.stil(10, 1).kalin and s.stil(10, 1).dolgu == "#70B050"
    assert s.deger(11, 1) == "Çay (İ,ı,Ş,ğ)" and s.deger(12, 1) == "Satır\nsonu"
    assert s.deger(11, 2) == 1234.5 and s.stil(11, 2).sayi_bicimi == "#,##0.00"
    assert s.deger(11, 3) == 0.255 and s.stil(11, 3).sayi_bicimi == "0.0%"
    assert s.deger(11, 4) == 46310.0 and s.stil(11, 4).sayi_bicimi == "dd/mm/yyyy"      # tarih sayıdır, metin değil
    assert isinstance(s.deger(12, 4), float)
    assert s.hucre(12, 5).formul == "=SUM(B11:B12)" or s.hucre(12, 5).formul == "=SUM(B2:B3)"   # x:fmla içeri alındı


def test_duz_metin_tsv_akilli_tarih_yuzde(g):
    md = QMimeData()
    md.setText("Ad\tTarih\tOran\nA\t15.10.2026\t%25\nB\t1.234,50\t")
    QApplication.clipboard().setMimeData(md)
    g.sec((1, 1))
    g.yapistir()
    s = g.sayfa
    assert s.deger(2, 2) == 46310.0 and s.stil(2, 2).sayi_bicimi != "General"
    assert s.deger(2, 3) == 0.25 and "%" in s.stil(2, 3).sayi_bicimi
    assert s.deger(3, 2) == 1234.5
    assert s.stil(2, 1).sayi_bicimi == "General"                                   # metin hücreye biçim verilmez


def test_biçimsiz_dis_metin_hedef_bicime_dokunmaz(g):
    g.hucre_gir(1, 1, "x")
    from tabcel.model.stil import StilYama
    g.sec((2, 1))
    g.bicim_uygula(StilYama(kalin=True))
    md = QMimeData()
    md.setText("metin")
    QApplication.clipboard().setMimeData(md)
    g.sec((2, 1))
    g.yapistir()
    assert g.sayfa.deger(2, 1) == "metin" and g.sayfa.stil(2, 1).kalin is True       # eski davranış: biçimsiz dış metin biçime dokunmaz


# ---------------------------------------------------------------- ızgara: dışarıya
def test_kopyalama_panoya_gorunen_metin_ve_excel_html(g):
    s = g.sayfa
    k = s.kitap
    s.ata(1, 1, Hucre(46310.0))
    s.ata(1, 2, Hucre(None, "=A1+1"))
    s.sonuc_ata(1, 2, 46311.0)                       # motor çalıştırılmadan hesaplanmış sonuç
    s.bicim_yaz(hucreler={(1, 1): k.stil_havuzu.kimlik(Stil(sayi_bicimi="dd.mm.yyyy"))})
    g.sec((1, 1), (1, 2))
    g.kopyala()
    md = QApplication.clipboard().mimeData()
    assert md.text().split("\r\n")[0] == "15.10.2026\t46311"
    h = md.html()
    assert 'x:num="46310.0"' in h and 'x:fmla="=A1+1"' in h and "mso-number-format" in h
