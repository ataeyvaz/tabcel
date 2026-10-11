"""Yardım ve Nasıl Kullanılır: içerik bütünlüğü, arama, pencere, şerit sekmesi, F1."""
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from tabcel import APP_NAME
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui import yardim as y
from tabcel.ui.window import Pencere

# Izgara/düzenleyici `keyPressEvent`inde işlenen (QShortcut/eylem olmayan) kısayollar; yardımda geçerler.
IZGARA_TUSLARI = {"Ctrl+Enter", "F2", "Alt+Enter", "F4", "Ctrl+Boşluk", "Shift+Boşluk", "Ctrl+A", "Ctrl+Home", "Ctrl+End",
                  "Delete", "Esc", "Ctrl+F1", "F1", "Ctrl+Z", "Ctrl+Y", "Ctrl+C", "Ctrl+X", "Ctrl+V"}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    p = Pencere(CalismaKitabi())
    p.show()
    return p


def test_konular_yuklenir_anahtarlar_benzersiz():
    konular = y.konulari_yukle()
    anahtarlar = [k.anahtar for k in konular]
    assert len(anahtarlar) == len(set(anahtarlar)) >= 12
    assert y.ILK_KONU in anahtarlar
    for k in konular:
        assert k.baslik and len(k.govde) > 100, k.anahtar


def test_baglantilar_gecerli_konuya_gider():
    konular = y.konulari_yukle()
    anahtarlar = {k.anahtar for k in konular}
    for k in konular:
        for hedef in re.findall(r"\]\(konu:([\w-]+)\)", k.govde):
            assert hedef in anahtarlar, (k.anahtar, hedef)


def test_uygulama_adi_yer_tutucudan_gelir():
    ham = y.YARDIM_DOSYASI.read_text(encoding="utf-8")
    govde = ham.split("-->", 1)[1]                              # baştaki yazım kuralları yorumundan sonrası
    assert "Tabcel" not in govde                                # ad elle yazılmaz (CLAUDE.md kural 1)
    assert "{APP_NAME}" in govde
    assert all("{APP_NAME}" not in k.govde and "{APP_NAME}" not in k.baslik for k in y.konulari_yukle())
    assert APP_NAME in y.konulari_yukle()[0].govde


def test_arama_turkce_harf_duyarsiz_ve_siralama():
    konular = y.konulari_yukle()
    assert [k.anahtar for k in y.ara(konular, "")] == [k.anahtar for k in konular]
    assert y.ara(konular, "GRAFİK")[0].anahtar == "grafikler"          # başlıkta geçen öne
    assert "siralafiltre" in [k.anahtar for k in y.ara(konular, "sırala")]
    assert "siralafiltre" in [k.anahtar for k in y.ara(konular, "SIRALA")]
    assert y.ara(konular, "xqzvw") == []
    assert y.ara(konular, "grafik sütun")                              # tüm sözcükler birlikte aranır


def test_yardimdaki_kisayollar_uygulamada_tanimli(pencere):
    tanimli = set(IZGARA_TUSLARI)
    for s in pencere.findChildren(QShortcut):
        tanimli.add(s.key().toString())
    for a in pencere.eylemler.values():
        tanimli.update(re.findall(r"\(([^()]*\+[^()]*|F\d+)\)", a.toolTip()))
    # eylem ipuçlarında "(Ctrl+Z)" biçimi; Türkçe adlı tuşları ("Boşluk") çevir
    eksik = sorted(k for k in y.kisayollar(y.konulari_yukle()) if k not in tanimli)
    assert not eksik, f"yardımda geçen ama uygulamada bulunamayan kısayollar: {eksik}"


def test_pencere_acilir_konu_gezinir_arama_vurgular(pencere):
    w = pencere.yardim_ac()
    assert w.isVisible() and w.acik == y.ILK_KONU and w.liste.count() == len(w.konular)
    w.konu_ac("kisayollar")
    assert w.acik == "kisayollar" and "Ctrl+B" in w.tarayici.toPlainText()
    w.arama.setText("filtre")
    assert w.liste.count() < len(w.konular) and "konu bulundu" in w.sonuc_etiketi.text()
    assert w.tarayici.extraSelections()
    w.arama.setText("xqzvw")
    assert w.sonuc_etiketi.text() == "Sonuç bulunamadı" and w.liste.count() == 0
    w.arama.clear()
    assert w.liste.count() == len(w.konular)


def test_konu_baglantisi_konuyu_acar(pencere):
    from PySide6.QtCore import QUrl
    w = pencere.yardim_ac()
    w._baglanti(QUrl("konu:grafikler"))
    assert w.acik == "grafikler"
    w._baglanti(QUrl("konu:yok_boyle"))                                 # bilinmeyen konu sessizce yok sayılır
    assert w.acik == "grafikler"


def test_tek_ornek_ve_baslik_adi_APP_NAME(pencere):
    a = pencere.yardim_ac()
    b = pencere.yardim_ac("farklar")
    assert a is b and b.acik == "farklar" and APP_NAME in b.windowTitle()


def test_f1_ve_serit_sekmesi(pencere):
    assert "Yardım" in pencere.serit.sekme_adlari()
    assert pencere.serit.sekme_adlari().index("Yardım") < pencere.serit.sekme_adlari().index("Grafik")
    assert pencere.eylemler["yardim_kisayollar"] in pencere.serit.eylemler()
    pencere.eylemler["yardim_kisayollar"].trigger()
    assert pencere._yardim_penceresi.acik == "kisayollar"
    pencere._yardim_penceresi.close()
    pencere.activateWindow()
    QApplication.processEvents()
    QTest.keyClick(pencere, Qt.Key_F1)
    assert pencere._yardim_penceresi.isVisible()


def test_tablolar_ve_basliklar_belgede_olusur(pencere):
    w = pencere.yardim_ac("kisayollar")
    from PySide6.QtGui import QTextTable
    assert any(isinstance(c, QTextTable) for c in w.tarayici.document().rootFrame().childFrames())
