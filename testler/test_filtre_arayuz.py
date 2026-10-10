"""Faz 5 / 5f: filtre arayüzü (menü, düğmeler, panel, özel filtre, özet, Delete) — ekransız."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.filtre import DegerKosulu, Filtre, IlkKosul, OzelKosul
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.filtre_paneli import FiltrePaneli, IlkOnPenceresi, OzelFiltrePenceresi
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    s = k.sayfalar[0]
    veri = [("Ad", "Puan"), ("Ali", 10.0), ("Çağla", 20.0), ("Ali", 30.0), ("Zeynep", 40.0), (None, 50.0)]
    for r, satir in enumerate(veri, start=1):
        for c, v in enumerate(satir, start=1):
            if v is not None:
                s.ata(r, c, Hucre(v))
    p = Pencere(k)
    p.resize(900, 500)
    p.show()
    app.processEvents()
    yield p
    p.hide()


def hucreler(p, c, n=6):
    s = p.kitap.sayfalar[0]
    return [r for r in range(1, n + 1) if r not in s.gizli_satir]


def test_menu_eylemleri_acik(pencere):
    for ad in ("filtre", "filtre_temizle", "filtre_yeniden"):
        assert pencere.veri_eylemleri[ad].isEnabled()


def test_ac_kapat_bitisik_bolge_ve_geri_al(pencere):
    g = pencere.izgara()
    g.sec((3, 1))
    assert pencere.filtre_ac_kapat()
    assert g.sayfa.filtre == Filtre(Aralik(1, 1, 6, 2))
    assert g._filtre_dugmesi_dikdortgeni(1) is not None and g._filtre_dugmesi_dikdortgeni(3) is None
    assert pencere.filtre_ac_kapat()                                  # ikinci basış kaldırır
    assert g.sayfa.filtre is None
    g.geri_al()
    assert g.sayfa.filtre is not None


def test_dugmeye_tiklama_sinyal_secimi_degistirmez(pencere, app):
    g = pencere.izgara()
    g.sec((3, 2))
    pencere.filtre_ac_kapat()
    alinan = []
    g.filtreDugmesi.connect(alinan.append)
    d = g._filtre_dugmesi_dikdortgeni(2)
    QTest.mouseClick(g.viewport(), Qt.LeftButton, Qt.NoModifier, d.center())
    assert alinan == [2] and g.aktif == (3, 2)
    assert g.filtre_dugmesi_sutunu(d.center()) == 2


def test_alt_asagi_baslik_hucresinde_listeyi_acar(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    alinan = []
    g.filtreDugmesi.connect(alinan.append)
    g.sec((1, 2))
    g.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.AltModifier))
    assert alinan == [2]
    g.sec((3, 1))
    g.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.AltModifier))
    assert alinan == [2]                                              # başlık dışında yok


def test_cizim_dugme_ve_mavi_satir_hatasiz(pencere, app):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pencere.filtre_kosulu_uygula(2, IlkKosul(1))
    app.processEvents()
    img = g.viewport().grab().toImage()
    d = g._filtre_dugmesi_dikdortgeni(2)
    assert img.pixelColor(d.x(), d.y() + 1).blue() > 150                # koşullu düğme mavi çerçeve


def test_panel_listesi_degerler_bos_ve_tumu(pencere, app):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pan = pencere.filtre_paneli_ac(1)
    metinler = [o.text() for o in pan._ogeler]
    assert metinler == ["(Tümünü Seç)", "Ali", "Çağla", "Zeynep", "(Boş)"]
    assert pan.liste_kosulu() is None                                  # hepsi işaretli = süzme yok
    pan._ogeler[0].setCheckState(Qt.Unchecked)                         # Tümünü Seç kapat → hepsi kapanır
    assert all(o.checkState() == Qt.Unchecked for o in pan._ogeler)
    pan._ogeler[2].setCheckState(Qt.Checked)                           # yalnız Çağla
    assert pan._ogeler[0].checkState() == Qt.PartiallyChecked
    assert pan.liste_kosulu() == DegerKosulu(frozenset({"Çağla"}), False)
    pan.close()


def test_panel_tamam_satirlari_gizler_ve_ileti(pencere, app):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pan = pencere.filtre_paneli_ac(1)
    for o in pan._ogeler[1:]:
        o.setCheckState(Qt.Checked if o.text() == "Ali" else Qt.Unchecked)
    pan._tamam()
    assert g.sayfa.gizli_satir == {3, 5, 6}
    assert pencere.statusBar().currentMessage() == "5 kayıttan 2 kayıt bulundu"
    g.geri_al()
    assert g.sayfa.gizli_satir == set()


def test_panel_arama_ve_diger_sutun_filtresi(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pencere.filtre_kosulu_uygula(2, OzelKosul(("buyuk", 25.0)))          # Ali(30), Zeynep, boş(50)
    pan = pencere.filtre_paneli_ac(1)
    assert [o.text() for o in pan._ogeler] == ["(Tümünü Seç)", "Ali", "Zeynep", "(Boş)"]
    pan.ara.setText("zey")
    gorunen = [o.text() for o in pan._ogeler[1:] if not o.isHidden()]
    assert gorunen == ["Zeynep"]
    pan.close()


def test_sutun_filtresini_temizle_digerleri_kalir(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pencere.filtre_kosulu_uygula(2, OzelKosul(("buyuk", 25.0)))
    pencere.filtre_kosulu_uygula(1, DegerKosulu(frozenset({"Ali"})))
    assert g.sayfa.gizli_satir == {2, 3, 5, 6}
    pencere.filtre_kosulu_uygula(1, None)
    assert set(g.sayfa.filtre.kosullar) == {2} and g.sayfa.gizli_satir == {2, 3}


def test_filtreyi_temizle_ve_yeniden_uygula(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pencere.filtre_kosulu_uygula(2, OzelKosul(("kucuk", 25.0)))
    assert g.sayfa.gizli_satir == {4, 5, 6}
    g.sayfa.ata(7, 1, Hucre("Yeni"))
    g.sayfa.ata(7, 2, Hucre(5.0))                                         # veri değişti: filtre kendiliğinden uygulanmaz
    assert g.sayfa.gizli_satir == {4, 5, 6}
    assert pencere.filtre_yeniden_uygula()
    assert g.sayfa.filtre.aralik.son_satir == 7 and g.sayfa.gizli_satir == {4, 5, 6}   # satır 7 (5 < 25) görünür
    assert pencere.filtre_temizle()
    assert g.sayfa.gizli_satir == set() and g.sayfa.filtre.kosullar == {}
    assert not pencere.filtre_temizle()                                   # zaten temiz


def test_ozel_filtre_penceresi_kosulu():
    pen = OzelFiltrePenceresi("Puan")
    pen.ayarla("buyuk_esit", "2,5", "kucuk", "10")
    pen.veya_dugmesi.setChecked(True)
    assert pen.kosul() == OzelKosul(("buyuk_esit", 2.5), ("kucuk", 10.0), False)
    bos = OzelFiltrePenceresi("Ad")
    assert bos.kosul() is None
    bos.ayarla("icerir", "ğl")
    assert bos.kosul() == OzelKosul(("icerir", "ğl"), None, True)


def test_ilk_on_penceresi():
    pen = IlkOnPenceresi(kosul=IlkKosul(3, alt=True, yuzde=True))
    assert pen.kosul() == IlkKosul(3, True, True)


def test_panel_metin_sayi_menusu_sutun_turune_gore(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    metin = pencere.filtre_paneli_ac(1)
    sayi = pencere.filtre_paneli_ac(2)
    assert "Büyüktür…" not in [a.text() for a in metin.ozel_menu.actions()]
    adlar = [a.text() for a in sayi.ozel_menu.actions()]
    assert "Büyüktür…" in adlar and "Arasında…" in adlar and "Ortalamanın Üstünde" in adlar
    metin.close()
    sayi.close()


def test_delete_ve_ozet_filtreyle_gizlileri_atlar(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pencere.filtre_kosulu_uygula(2, OzelKosul(("kucuk", 25.0)))          # görünen: 2, 3
    g.sec((2, 2), (6, 2))
    pencere._ozet_guncelle()
    assert "Toplam: 30" in pencere.ozet_etiketi.text()                   # 10 + 20
    g.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier))
    s = g.sayfa
    assert s.hucre(2, 2) is None and s.hucre(3, 2) is None
    assert s.deger(4, 2) == 30.0 and s.deger(5, 2) == 40.0               # gizli satırlar silinmedi
    g.geri_al()
    assert s.deger(2, 2) == 10.0


def test_panelden_siralama_baslik_sabit(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.filtre_ac_kapat()
    pencere._filtre_sirala(2, False)
    assert [g.sayfa.deger(r, 2) for r in range(1, 7)] == ["Puan", 50.0, 40.0, 30.0, 20.0, 10.0]
