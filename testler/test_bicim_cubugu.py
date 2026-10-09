"""Faz 3 / 3d: biçim araç çubuğu — her düğme ekransız; etkin hücreyi yansıtma, geri al, kısayollar."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 5):
        s.ata(r, 1, Hucre(float(r) + 0.5))
        s.ata(r, 2, Hucre("m"))
    p = Pencere(k)
    p.show()
    return p


def stil(p, r, c):
    return p.izgara().sayfa.stil(r, c)


def sec(p, a, b=None):
    p.izgara().sec(a, b)


def test_cubuk_pencerede_ve_sozlesme(pencere):
    c = pencere.bicim_cubugu
    assert c.isVisible()
    for ad in ("kalin", "italik", "altcizili", "yazi_rengi", "dolgu", "kenarlik", "kaydir",
               "girinti_artir", "girinti_azalt", "para", "yuzde", "binlik", "ondalik_artir",
               "ondalik_azalt", "buyut", "kucult", "yazi_tipi", "boyut", "sayi_bicimi"):
        assert getattr(c, ad) is not None


def test_kalin_italik_alti_cizili_tum_secime(pencere):
    sec(pencere, (1, 1), (3, 2))
    pencere.bicim_cubugu.kalin.click()
    pencere.bicim_cubugu.italik.click()
    pencere.bicim_cubugu.altcizili.click()
    for r in (1, 2, 3):
        for c in (1, 2):
            s = stil(pencere, r, c)
            assert s.kalin and s.italik and s.alti_cizili == "tek"
    assert not stil(pencere, 4, 1).kalin                       # seçim dışı
    assert pencere.bicim_cubugu.kalin.isChecked()
    pencere.bicim_cubugu.kalin.click()                          # ikinci tık kapatır
    assert not stil(pencere, 2, 2).kalin and not pencere.bicim_cubugu.kalin.isChecked()


def test_dugme_etkin_hucreye_bakar(pencere):
    """Etkin hücre kalın, diğerleri değil: düğme kapatır ve hepsini kalın-dışı yapar (Excel gibi)."""
    sec(pencere, (1, 1))
    pencere.bicim_cubugu.kalin.click()
    sec(pencere, (1, 1), (2, 1))                                # etkin = (1,1), kalın
    assert pencere.bicim_cubugu.kalin.isChecked()
    pencere.bicim_cubugu.kalin.click()
    assert not stil(pencere, 1, 1).kalin and not stil(pencere, 2, 1).kalin


def test_cubuk_etkin_hucreyi_yansitir(pencere):
    sec(pencere, (1, 1))
    pencere.bicim_cubugu.kalin.click()
    pencere.bicim_cubugu.yatay["sag"].click()
    sec(pencere, (3, 1))
    c = pencere.bicim_cubugu
    assert not c.kalin.isChecked() and not c.yatay["sag"].isChecked() and c.dikey["alt"].isChecked()
    sec(pencere, (1, 1))
    assert c.kalin.isChecked() and c.yatay["sag"].isChecked()


def test_geri_al_cubugu_gunceller(pencere):
    sec(pencere, (1, 1))
    pencere.bicim_cubugu.kalin.click()
    assert pencere.bicim_cubugu.kalin.isChecked()
    pencere.izgara().geri_al()
    assert not pencere.bicim_cubugu.kalin.isChecked() and not stil(pencere, 1, 1).kalin
    pencere.izgara().yinele()
    assert pencere.bicim_cubugu.kalin.isChecked()


def test_tek_geri_al_adimi(pencere):
    sec(pencere, (1, 1), (4, 2))
    pencere.bicim_cubugu.kalin.click()
    pencere.izgara().geri_al()
    assert all(not stil(pencere, r, c).kalin for r in range(1, 5) for c in (1, 2))


def test_yazi_boyutu_kutusu_ve_buyut_kucult(pencere):
    sec(pencere, (1, 1), (2, 1))
    c = pencere.bicim_cubugu
    assert c.boyut.currentText() == "11"
    c.buyut.click()
    assert stil(pencere, 1, 1).boyut == 12.0 and stil(pencere, 2, 1).boyut == 12.0
    assert c.boyut.currentText() == "12"
    c.kucult.click()
    c.kucult.click()
    assert stil(pencere, 1, 1).boyut == 10.0
    c.boyut.setEditText("18")
    c.boyut.lineEdit().editingFinished.emit()
    assert stil(pencere, 2, 1).boyut == 18.0
    c.boyut.setEditText("abc")                                  # geçersiz: eski değere döner, stil aynı
    c.boyut.lineEdit().editingFinished.emit()
    assert stil(pencere, 1, 1).boyut == 18.0 and c.boyut.currentText() == "18"
    c.boyut.setEditText("0")
    c.boyut.lineEdit().editingFinished.emit()
    assert stil(pencere, 1, 1).boyut == 18.0


def test_yazi_tipi_secimi(pencere):
    sec(pencere, (1, 1))
    c = pencere.bicim_cubugu
    from PySide6.QtGui import QFont
    c.yazi_tipi.setCurrentFont(QFont("Arial"))
    c.yazi_tipi.activated.emit(c.yazi_tipi.currentIndex())
    assert stil(pencere, 1, 1).yazi_tipi == c.yazi_tipi.currentFont().family()
    assert stil(pencere, 2, 1).yazi_tipi is None


def test_yazi_ve_dolgu_rengi(pencere):
    sec(pencere, (1, 1), (2, 2))
    c = pencere.bicim_cubugu
    c.yazi_rengi.click()                                        # varsayılan kırmızı
    assert stil(pencere, 2, 2).yazi_rengi == "#FF0000"
    c.dolgu.click()                                             # varsayılan sarı
    assert stil(pencere, 1, 2).dolgu == "#FFFF00"
    c.dolgu.sec(QColor("#00b050"))
    assert stil(pencere, 1, 1).dolgu == "#00B050" and c.dolgu.simdiki == "#00B050"
    c.dolgu.click()                                             # son seçilen renk
    c.dolgu.sec(None)                                           # Dolgu Yok
    assert stil(pencere, 1, 1).dolgu is None and stil(pencere, 2, 2).dolgu is None
    c.yazi_rengi.sec(None)                                      # Otomatik
    assert stil(pencere, 2, 2).yazi_rengi is None


def test_renk_paleti_menusu_var(pencere):
    c = pencere.bicim_cubugu
    assert c.yazi_rengi.menu() is not None and c.dolgu.menu() is not None


def test_kenarlik_menusu(pencere):
    sec(pencere, (2, 2), (3, 3))
    c = pencere.bicim_cubugu
    assert set(c.kenar_eylemleri) == {"alt", "ust", "sol", "sag", "tum", "dis", "kalin_dis", "cift_alt", "yok"}
    c.kenar_eylemleri["dis"].trigger()
    assert stil(pencere, 2, 2).kenar.ust and stil(pencere, 2, 2).kenar.sol
    assert stil(pencere, 3, 3).kenar.alt and stil(pencere, 3, 3).kenar.sag
    assert stil(pencere, 2, 2).kenar.alt is None
    pencere.izgara().geri_al()                                  # tek adım
    assert all(stil(pencere, r, cc).kenar.bos_mu() for r in (2, 3) for cc in (2, 3))
    c.kenar_eylemleri["tum"].trigger()
    assert stil(pencere, 2, 3).kenar.sol and stil(pencere, 2, 3).kenar.alt
    c.kenar_eylemleri["yok"].trigger()
    assert all(stil(pencere, r, cc).kenar.bos_mu() for r in (2, 3) for cc in (2, 3))
    # menüde ayırıcılarla toplam 11 öğe
    assert len(c.kenarlik.menu().actions()) == 11


def test_kenarlik_tam_sutunda(pencere):
    g = pencere.izgara()
    sec(pencere, (1, 3), (1048576, 3))                          # C sütununun tamamı
    pencere.bicim_cubugu.kenar_eylemleri["dis"].trigger()
    assert stil(pencere, 5000, 3).kenar.sol and stil(pencere, 5000, 3).kenar.sag
    assert stil(pencere, 1, 3).kenar.ust and stil(pencere, 1048576, 3).kenar.alt
    assert stil(pencere, 5000, 3).kenar.ust is None


def test_hizalama_dugmeleri(pencere):
    sec(pencere, (1, 1), (2, 2))
    c = pencere.bicim_cubugu
    c.yatay["orta"].click()
    assert stil(pencere, 2, 2).yatay == "orta" and c.yatay["orta"].isChecked()
    c.yatay["orta"].click()                                     # tekrar: genel
    assert stil(pencere, 2, 2).yatay == "genel" and not c.yatay["orta"].isChecked()
    c.yatay["sol"].click()
    c.yatay["sag"].click()
    assert stil(pencere, 1, 1).yatay == "sag" and not c.yatay["sol"].isChecked()
    c.dikey["ust"].click()
    assert stil(pencere, 1, 2).dikey == "ust"
    c.dikey["orta"].click()
    assert stil(pencere, 1, 2).dikey == "orta"
    c.dikey["orta"].click()
    assert stil(pencere, 1, 2).dikey == "alt"


def test_metni_kaydir_ve_girinti(pencere):
    sec(pencere, (1, 2), (2, 2))
    c = pencere.bicim_cubugu
    c.kaydir.click()
    assert stil(pencere, 1, 2).kaydir and stil(pencere, 2, 2).kaydir
    c.kaydir.click()
    assert not stil(pencere, 1, 2).kaydir
    c.girinti_artir.click()
    c.girinti_artir.click()
    assert stil(pencere, 1, 2).girinti == 2 and stil(pencere, 1, 2).yatay == "sol"
    c.girinti_azalt.click()
    assert stil(pencere, 2, 2).girinti == 1
    c.girinti_azalt.click()
    n = pencere.yigin._geri.__len__()
    c.girinti_azalt.click()                                     # 0'dan azaltma: komut eklemez
    assert stil(pencere, 2, 2).girinti == 0 and len(pencere.yigin._geri) == n


def test_sayi_dugmeleri(pencere):
    sec(pencere, (1, 1), (4, 1))
    c = pencere.bicim_cubugu
    c.yuzde.click()
    assert stil(pencere, 3, 1).sayi_bicimi == "0%" and c.sayi_bicimi.currentText() == "Özel"
    c.para.click()
    assert stil(pencere, 3, 1).sayi_bicimi == '"₺"#,##0.00' and c.sayi_bicimi.currentText() == "Para Birimi"
    c.binlik.click()
    assert stil(pencere, 4, 1).sayi_bicimi == "#,##0.00"
    c.ondalik_artir.click()
    assert stil(pencere, 4, 1).sayi_bicimi == "#,##0.000"
    c.ondalik_azalt.click()
    c.ondalik_azalt.click()
    c.ondalik_azalt.click()
    assert stil(pencere, 1, 1).sayi_bicimi == "#,##0"
    c.ondalik_azalt.click()                                     # 0'ın altına inmez, komut yok
    assert stil(pencere, 1, 1).sayi_bicimi == "#,##0"


def test_ondalik_genel_bicimde_gorunen_ondaliktan_baslar(pencere):
    sec(pencere, (1, 1))                                        # 1,5
    pencere.bicim_cubugu.ondalik_artir.click()
    assert stil(pencere, 1, 1).sayi_bicimi == "0.00"


def test_sayi_bicimi_listesi(pencere):
    sec(pencere, (1, 1), (2, 1))
    c = pencere.bicim_cubugu
    from tabcel.model.sayi_bicimi import HAZIR
    assert [c.sayi_bicimi.itemText(i) for i in range(c.sayi_bicimi.count() - 1)] == list(HAZIR)
    for ad, kod in HAZIR.items():
        c.sayi_bicimi.setCurrentText(ad)
        c.sayi_bicimi.activated.emit(c.sayi_bicimi.currentIndex())
        assert stil(pencere, 2, 1).sayi_bicimi == kod
        assert c.sayi_bicimi.currentText() == ad
    c.sayi_bicimi.setCurrentText("Özel")                         # Özel seçmek biçimi bozmaz
    c.sayi_bicimi.activated.emit(c.sayi_bicimi.currentIndex())
    assert stil(pencere, 2, 1).sayi_bicimi == HAZIR["Metin"]


def test_sayi_bicimi_ekranda_gorunur(pencere):
    sec(pencere, (1, 1))
    pencere.bicim_cubugu.yuzde.click()
    from tabcel.model import sayi_bicimi
    assert sayi_bicimi.bicimle(1.5, stil(pencere, 1, 1).sayi_bicimi).metin == "150%"


def test_kisayollar(pencere):
    sec(pencere, (1, 1), (2, 1))
    g = pencere.izgara()
    pencere.activateWindow()
    QTest.qWaitForWindowActive(pencere)       # pencere kısayolları yalnız etkin pencerede çalışır
    g.setFocus()
    QTest.keyClick(g, Qt.Key_B, Qt.ControlModifier)
    assert stil(pencere, 2, 1).kalin
    QTest.keyClick(g, Qt.Key_I, Qt.ControlModifier)
    assert stil(pencere, 2, 1).italik
    QTest.keyClick(g, Qt.Key_U, Qt.ControlModifier)
    assert stil(pencere, 1, 1).alti_cizili == "tek"
    QTest.keyClick(g, Qt.Key_5, Qt.ControlModifier)
    assert stil(pencere, 1, 1).ustu_cizili
    QTest.keyClick(g, Qt.Key_B, Qt.ControlModifier)             # aç/kapat
    assert not stil(pencere, 1, 1).kalin
    QTest.keyClick(g, Qt.Key_5, Qt.ControlModifier | Qt.ShiftModifier)
    assert stil(pencere, 1, 1).sayi_bicimi == "0%"
    QTest.keyClick(g, Qt.Key_4, Qt.ControlModifier | Qt.ShiftModifier)
    assert stil(pencere, 1, 1).sayi_bicimi == '"₺"#,##0.00'
    QTest.keyClick(g, Qt.Key_1, Qt.ControlModifier | Qt.ShiftModifier)
    assert stil(pencere, 1, 1).sayi_bicimi == "#,##0.00"


def test_biçim_formulleri_ve_icerigi_degistirmez(pencere):
    s = pencere.izgara().sayfa
    s.ata(1, 3, Hucre("=A1*2"))
    sec(pencere, (1, 1), (1, 3))
    onceki = (s.hucre(1, 3), s.sonuc(1, 3))
    pencere.bicim_cubugu.kalin.click()
    pencere.bicim_cubugu.yuzde.click()
    assert (s.hucre(1, 3), s.sonuc(1, 3)) == onceki


def test_duzenleme_sirasinda_odak_calinmaz(pencere):
    g = pencere.izgara()
    pencere.activateWindow()
    QTest.qWaitForWindowActive(pencere)
    sec(pencere, (1, 1))
    QTest.keyClick(g, Qt.Key_F2)
    assert g.duzenleniyor()
    QTest.keyClick(g, Qt.Key_B, Qt.ControlModifier)
    assert g.duzenleniyor()


def test_cubuk_baska_sayfada(pencere):
    pencere.sayfa_ekle()
    g2 = pencere.izgara()
    g2.sec((1, 1))
    pencere.bicim_cubugu.kalin.click()
    assert g2.sayfa.stil(1, 1).kalin
    assert not pencere.kitap.sayfalar[0].stil(1, 1).kalin


def test_ekran_goruntusu_boyutlari(pencere):
    """Çubuk 1100 px pencerede tek satırda sığar."""
    c = pencere.bicim_cubugu
    assert c.sizeHint().width() <= 1100
