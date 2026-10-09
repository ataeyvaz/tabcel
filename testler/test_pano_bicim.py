"""Faz 3 / 3b: pano biçim taşıma, HucreTasi stil, Temizle menüsü, Delete biçimi korur."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from tabcel.model import pano
from tabcel.model.adres import MAX_COL, Aralik
from tabcel.model.komutlar import GeriAlYigini, HucreTasi, bicim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Kenarlik, Stil, StilYama
from tabcel.ui.grid import Izgara

KALIN = StilYama(kalin=True)
SARI = StilYama(dolgu="#FFFF00")


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def g(app):
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 4):
        s.ata(r, 1, Hucre(float(r)))
    return Izgara(s)


def bicimle(g, aralik, yama):
    g.yigin.calistir(bicim_komutu(g.sayfa, [aralik], yama))


# ------------------------------------------------------------ model: PanoVerisi
def test_pano_verisi_stil_ve_bos_bicimli_hucre(g):
    s = g.sayfa
    bicimle(g, Aralik(1, 1, 1, 1), KALIN)
    bicimle(g, Aralik(2, 3, 2, 3), SARI)                    # içeriksiz ama biçimli
    ar = pano.pano_araligi(s, Aralik(1, 1, 5, 5))
    assert ar == Aralik(1, 1, 3, 3)                          # biçimli boş hücre aralığa dahil
    v = pano.pano_verisi_al(s, ar)
    assert v.stiller[(0, 0)].kalin and v.stiller[(1, 2)].dolgu == "#FFFF00"
    assert (1, 0) not in v.stiller and len(v.stiller) == 2   # varsayılan stiller yok
    assert v.kaynak_satir == 1


def test_pano_json_stil_gidis_donus_kenar_dahil(g):
    st = Stil(kalin=True, yazi_rengi="#FF0000", kenar=Kenarlik(ust=("kalin", "#000000")),
              yatay="orta", sayi_bicimi="0.00")
    v = pano.PanoVerisi(1, 2, {(0, 0): Hucre(1.0)}, stiller={(0, 1): st})
    v2 = pano.PanoVerisi.json_oku(v.json_yaz())
    assert v2.stiller == {(0, 1): st}
    eski = pano.PanoVerisi.json_oku('{"s":1,"c":1,"h":[[0,0,2.0,null,null]]}')   # stilsiz eski biçim
    assert eski.stiller == {}


def test_html_dis_aktarim_satir_ici_css():
    st = Stil(kalin=True, italik=True, dolgu="#ffff00", yazi_rengi="#ff0000", yatay="sag", alti_cizili="tek")
    h = pano.html_yaz([["a", "b"]], {(0, 1): st})
    assert "<td>a</td>" in h and "font-weight:bold" in h and "background:#FFFF00" in h
    assert "color:#FF0000" in h and "text-align:right" in h and "underline" in h


def test_yapistirma_stilleri_desen_yinelenir(g):
    v = pano.PanoVerisi(1, 2, {}, stiller={(0, 0): Stil(kalin=True)}, kaynak_satir=1, kaynak_sutun=1)
    pl = pano.yapistirma_stilleri(v, 5, 5, Aralik(5, 5, 6, 8), g.sayfa.havuz)
    k = g.sayfa.havuz.kimlik(Stil(kalin=True))
    assert pl[(5, 5)] == pl[(5, 7)] == pl[(6, 5)] == k and pl[(5, 6)] == 0 and len(pl) == 8


# ------------------------------------------------------------ ızgara: kopyala / yapıştır
def test_kopyala_yapistir_icerik_ve_bicim(g):
    s = g.sayfa
    bicimle(g, Aralik(1, 1, 2, 1), KALIN)
    g.sec((1, 1), (3, 1)); g.kopyala()
    g.sec((6, 4)); g.yapistir()
    assert s.deger(6, 4) == 1.0 and s.stil(6, 4).kalin and s.stil(7, 4).kalin and not s.stil(8, 4).kalin
    assert s.stil(1, 1).kalin                                # kaynak yerinde
    g.geri_al()                                              # içerik + biçim TEK adım
    assert s.deger(6, 4) is None and s.stil_kimligi(6, 4) == 0


def test_bicimsiz_kaynak_hedefin_bicimini_siler_tumu(g):
    s = g.sayfa
    bicimle(g, Aralik(10, 10, 10, 10), SARI)
    g.sec((2, 1)); g.kopyala()                               # biçimsiz kaynak
    g.sec((10, 10)); g.yapistir()
    assert s.deger(10, 10) == 2.0 and s.stil(10, 10) == Stil()


def test_disaridan_metin_yapistirma_bicime_dokunmaz(g):
    s = g.sayfa
    bicimle(g, Aralik(10, 10, 10, 10), SARI)
    md = QMimeData(); md.setText("42\r\n")
    QApplication.clipboard().setMimeData(md)
    g.sec((10, 10)); g.yapistir()
    assert s.deger(10, 10) == 42.0 and s.stil(10, 10).dolgu == "#FFFF00"


def test_bicim_baska_oturumdan_stil_nesnesiyle_tasinir(g):
    """Pano JSON'u Stil alanlarını taşır (kimlik değil): başka havuz/oturum güvenli."""
    bicimle(g, Aralik(1, 1, 1, 1), SARI)
    g.sec((1, 1)); g.kopyala()
    md = QApplication.clipboard().mimeData()
    v = pano.PanoVerisi.json_oku(bytes(md.data(g.MIME_HUCRELER)).decode("utf-8"))
    yeni = Izgara(CalismaKitabi().sayfalar[0])
    yeni.sec((2, 2))
    v.oturum = "baska"
    md2 = QMimeData(); md2.setData(g.MIME_HUCRELER, v.json_yaz().encode("utf-8"))
    QApplication.clipboard().setMimeData(md2)
    yeni.yapistir()
    assert yeni.sayfa.stil(2, 2).dolgu == "#FFFF00"


# ------------------------------------------------------------ kes-yapıştır = taşıma (biçim dahil)
def test_kes_yapistir_bicimi_tasir_kaynak_varsayilana_doner(g):
    s = g.sayfa
    bicimle(g, Aralik(1, 1, 2, 1), KALIN)
    g.sec((1, 1), (3, 1)); g.kes()
    g.sec((1, 5)); g.yapistir()
    assert s.stil(1, 5).kalin and s.stil(2, 5).kalin and not s.stil(3, 5).kalin
    assert s.stil_kimligi(1, 1) == 0 and s.stil_kimligi(2, 1) == 0
    g.geri_al()                                              # tek adım
    assert s.stil(1, 1).kalin and s.stil_kimligi(1, 5) == 0


def test_hucre_tasi_sayfalar_arasi_ve_satir_stili_altinda(app):
    k = CalismaKitabi(); k.sayfa_ekle()
    s1, s2 = k.sayfalar
    y = GeriAlYigini()
    s1.ata(1, 1, Hucre(5.0))
    y.calistir(bicim_komutu(s1, [Aralik(1, 1, 1, 1)], KALIN))
    y.calistir(bicim_komutu(s2, [Aralik(4, 1, 4, MAX_COL)], SARI))      # hedefte satır biçimi var
    y.calistir(HucreTasi(s1, (1, 1, 1, 1), s2, (4, 2)))
    assert s2.stil(4, 2) == Stil(kalin=True) and s2.stil(4, 3).dolgu == "#FFFF00"   # taşınan stil satır stilini ezer
    assert s1.stil_kimligi(1, 1) == 0
    y.geri_al()
    assert s1.stil(1, 1).kalin and s2.stil(4, 2).dolgu == "#FFFF00" and s2.ham_stil_kimligi(4, 2) is None


def test_hucre_tasi_ust_uste_biner_alan_ayni_sayfa(g):
    s = g.sayfa
    bicimle(g, Aralik(1, 1, 3, 1), KALIN)
    g.sec((1, 1), (3, 1)); g.kes()
    g.sec((2, 1)); g.yapistir()
    assert [s.stil(r, 1).kalin for r in (1, 2, 3, 4)] == [False, True, True, True]


# ------------------------------------------------------------ Temizle menüsü, Delete
def test_delete_bicimi_korur(g):
    s = g.sayfa
    bicimle(g, Aralik(1, 1, 3, 1), KALIN)
    g.sec((1, 1), (3, 1)); g.secimi_temizle()
    assert s.deger(1, 1) is None and s.stil(1, 1).kalin


def test_bicimleri_temizle_icerik_kalir_tek_adim(g):
    s = g.sayfa
    bicimle(g, Aralik(1, 1, 3, 1), KALIN)
    g.sec((1, 1), (2, 1)); g.bicimleri_temizle()
    assert s.deger(1, 1) == 1.0 and not s.stil(1, 1).kalin and not s.stil(2, 1).kalin and s.stil(3, 1).kalin
    g.geri_al()
    assert s.stil(1, 1).kalin and s.stil(2, 1).kalin


def test_tumunu_temizle_icerik_ve_bicim_tek_adim(g):
    s = g.sayfa
    bicimle(g, Aralik(1, 1, 3, 1), KALIN)
    g.sec((1, 1), (3, 1)); g.tumunu_temizle()
    assert s.deger(1, 1) is None and s.deger(3, 1) is None and not s._stil
    g.geri_al()
    assert s.deger(2, 1) == 2.0 and s.stil(2, 1).kalin


def test_bicimleri_temizle_tam_satir_satir_stilini_kaldirir(g):
    s = g.sayfa
    g.yigin.calistir(bicim_komutu(s, [Aralik(2, 1, 2, MAX_COL)], KALIN))
    assert s.satir_stil
    g.sec((2, 1), (2, MAX_COL)); g.bicimleri_temizle()
    assert not s.satir_stil and not s.stil(2, 5).kalin


def test_bicim_temizle_satir_bicimliyken_hucreyi_varsayilana_alir(g):
    s = g.sayfa
    g.yigin.calistir(bicim_komutu(s, [Aralik(2, 1, 2, MAX_COL)], KALIN))
    g.sec((2, 3)); g.bicimleri_temizle()
    assert not s.stil(2, 3).kalin and s.stil(2, 4).kalin
