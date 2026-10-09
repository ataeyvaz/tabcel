"""Faz 3 / 3e: Hücreleri Biçimlendir penceresi — başlangıç değerleri, yalnız değişenler, sayı sekmesi,
kenarlık planı, Özel kod doğrulama, Ctrl+1 ile uçtan uca."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.bicim_kodlari import KATEGORILER
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sayi_bicimi import HAZIR
from tabcel.model.stil import Stil
from tabcel.ui.bicim_penceresi import BicimPenceresi
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 5):
        s.ata(r, 1, Hucre(r * 1000.5))
    p = Pencere(k)
    p.show()
    return p


def stil(p, r, c):
    return p.izgara().sayfa.stil(r, c)


def kategori_sec(d, ad):
    d.kategori.setCurrentRow(KATEGORILER.index(ad))


def test_baslangic_degerleri(app):
    s = Stil(kalin=True, boyut=14, yatay="sag", dikey="ust", girinti=2, kaydir=True,
             sayi_bicimi="0.0%", dolgu="#FFFF00", alti_cizili="cift")
    d = BicimPenceresi(s, 0.256)
    assert d.kalin.isChecked() and not d.italik.isChecked() and d.boyut.currentText() == "14"
    assert d.yatay.currentText() == "Sağa (Girinti)" and d.dikey.currentText() == "Üst"
    assert d.girinti.value() == 2 and d.kaydir.isChecked()
    assert d.alti_cizili.currentText() == "Çift"
    assert d.dolgu.deger() == "#FFFF00" and d.yazi_rengi.deger() is None
    assert d.kategori.currentItem().text() == "Yüzde" and d.ondalik.value() == 1
    assert d.onizleme.text() == "25,6%"
    assert d.ozel.text() == "0,0%"                    # yerel yazım gösterilir, kanonik saklanır
    assert d.yama().bos_mu() and d.plan([Aralik(1, 1, 1, 1)]) == []


def test_yalniz_degisen_alanlar(app):
    d = BicimPenceresi(Stil(kalin=True, boyut=14), None)
    d.italik.setChecked(True)
    assert d.yama()._alanlar == {"italik": True}
    d.kalin.setChecked(False)
    assert d.yama()._alanlar == {"italik": True, "kalin": False}


def test_alanlar_toplu(app):
    d = BicimPenceresi(Stil(), None)
    d.yatay.setCurrentIndex(2)
    d.dikey.setCurrentIndex(0)
    d.girinti.setValue(3)
    d.kaydir.setChecked(True)
    d.boyut.setEditText("18")
    d.alti_cizili.setCurrentIndex(1)
    d.ustu_cizili.setChecked(True)
    d.yazi_rengi.renk_ata("#00b050")
    d.dolgu.renk_ata("#ffc000")
    assert d.yama()._alanlar == {
        "yatay": "orta", "dikey": "ust", "girinti": 3, "kaydir": True, "boyut": 18.0,
        "alti_cizili": "tek", "ustu_cizili": True, "yazi_rengi": "#00B050", "dolgu": "#FFC000"}
    d.dolgu.yok.setChecked(True)
    assert "dolgu" not in d.yama()._alanlar            # başlangıçta da yoktu: değişiklik değil


def test_sayi_sekmesi_kategoriler(app):
    d = BicimPenceresi(Stil(), 1234.5)
    kategori_sec(d, "Sayı")
    d.ondalik.setValue(3)
    d.binlik.setChecked(True)
    assert d._kod == "#,##0.000" and d.onizleme.text() == "1.234,500" and d.ozel.text() == "#.##0,000"
    kategori_sec(d, "Para Birimi")
    d.sembol.setCurrentText("$")
    assert d._kod == '"$"#,##0.000'
    kategori_sec(d, "Yüzde")
    d.ondalik.setValue(0)
    assert d._kod == "0%"
    kategori_sec(d, "Tarih")
    assert d.tip.count() > 3
    d.tip.setCurrentRow(3)
    assert d._kod == "d mmmm yyyy"
    kategori_sec(d, "Saat")
    kategori_sec(d, "Genel")
    assert d._kod == "General"
    assert d.yama()._alanlar == {} and d.plan([Aralik(1, 1, 1, 1)]) == []


def test_ozel_kod_yerel_yazilir_kanonik_saklanir(app):
    d = BicimPenceresi(Stil(), 1234.5)
    d.ozel.setText('#.##0,00 "TL"')
    d.ozel.textEdited.emit(d.ozel.text())
    assert d.kategori.currentItem().text() == "Özel"
    assert d._kod == '#,##0.00 "TL"' and d.onizleme.text() == "1.234,50 TL"
    assert d.yama()._alanlar == {"sayi_bicimi": '#,##0.00 "TL"'}
    d2 = BicimPenceresi(Stil(), 1.0)
    d2.ozel.setText("gg.aa.yyyy")
    d2.ozel.textEdited.emit("gg.aa.yyyy")
    assert d2._kod == "dd.mm.yyyy"


def test_gecersiz_ozel_kod_uyarir_kapanmaz(app, monkeypatch):
    mesajlar = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: mesajlar.append(a[2]))
    d = BicimPenceresi(Stil(), 1.0)
    d.ozel.setText("[>x]0")
    d.ozel.textEdited.emit("[>x]0")
    d.dugmeler.accepted.emit()
    assert len(mesajlar) == 1 and "geçerli değil" in mesajlar[0]
    assert d.result() != QDialog.Accepted
    d.ozel.setText("0,00")
    d.ozel.textEdited.emit("0,00")
    d.dugmeler.accepted.emit()
    assert d.result() == QDialog.Accepted


def test_gecersiz_boyut_uyarir(app, monkeypatch):
    mesajlar = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: mesajlar.append(a[2]))
    d = BicimPenceresi(Stil(), 1.0)
    d.boyut.setEditText("500")
    d.dugmeler.accepted.emit()
    assert len(mesajlar) == 1 and d.result() != QDialog.Accepted


def test_kenarlik_plani_pencereden(app):
    d = BicimPenceresi(Stil(), None)
    d.cizgi.setCurrentIndex(2)                         # kalın
    d.on_ayar_uygula("dis")
    plan = d.plan([Aralik(2, 2, 3, 3)])
    assert len(plan) == 4                              # dört dış kenar, iç dokunulmadı
    assert plan[0][1]._alanlar["kenar"]["ust"] == ("kalin", "#000000")
    d.ic.click()
    assert len(d.plan([Aralik(2, 2, 3, 3)])) == 5      # + iç çizgiler
    d2 = BicimPenceresi(Stil(), None)
    d2.kenar["alt"].setChecked(True)
    p2 = d2.plan([Aralik(2, 2, 3, 3)])
    assert len(p2) == 1 and p2[0][1]._alanlar["kenar"]["alt"] == ("ince", "#000000")


def test_ctrl1_uctan_uca(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((1, 1), (4, 1))
    ornek = {}

    def exec_(self):
        ornek["onizleme"] = self.onizleme.text()
        kategori_sec(self, "Para Birimi")
        self.italik.setChecked(True)
        self.on_ayar_uygula("dis")
        self.dolgu.renk_ata("#ffff00")
        return QDialog.Accepted
    monkeypatch.setattr(BicimPenceresi, "exec", exec_)
    pencere.activateWindow()
    QTest.qWaitForWindowActive(pencere)
    g.setFocus()
    QTest.keyClick(g, Qt.Key_1, Qt.ControlModifier)
    assert ornek["onizleme"] == "1000,5"
    for r in range(1, 5):
        s = stil(pencere, r, 1)
        assert s.sayi_bicimi == HAZIR["Para Birimi"] and s.italik and s.dolgu == "#FFFF00"
    assert stil(pencere, 1, 1).kenar.ust and stil(pencere, 4, 1).kenar.alt
    assert stil(pencere, 2, 1).kenar.ust is None
    g.geri_al()                                         # tek adım
    assert all(stil(pencere, r, 1) == Stil() for r in range(1, 5))


def test_iptal_degistirmez(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((1, 1))

    def exec_(self):
        self.kalin.setChecked(True)
        return QDialog.Rejected
    monkeypatch.setattr(BicimPenceresi, "exec", exec_)
    assert pencere.bicim_cubugu.penceresi_ac() is False
    assert not stil(pencere, 1, 1).kalin


def test_coklu_secimde_dokunulmayan_alan_korunur(pencere, monkeypatch):
    g = pencere.izgara()
    s = g.sayfa
    s.bicim_yaz({(1, 1): s.havuz.kimlik(Stil(kalin=True, dolgu="#FF0000")),
                 (2, 1): s.havuz.kimlik(Stil(italik=True, dolgu="#00FF00"))})
    g.sec((1, 1), (2, 1))

    def exec_(self):
        self.girinti.setValue(2)
        return QDialog.Accepted
    monkeypatch.setattr(BicimPenceresi, "exec", exec_)
    assert pencere.bicim_cubugu.penceresi_ac() is True
    a, b = stil(pencere, 1, 1), stil(pencere, 2, 1)
    assert (a.kalin, a.dolgu, a.girinti) == (True, "#FF0000", 2)
    assert (b.italik, b.dolgu, b.girinti) == (True, "#00FF00", 2)


def test_pencere_dugmesi_ve_formul_degismez(pencere, monkeypatch):
    g = pencere.izgara()
    g.sayfa.ata(1, 2, Hucre("=A1*2"))
    g.sec((1, 2))
    onceki = (g.sayfa.hucre(1, 2), g.sayfa.sonuc(1, 2))

    def exec_(self):
        kategori_sec(self, "Yüzde")
        return QDialog.Accepted
    monkeypatch.setattr(BicimPenceresi, "exec", exec_)
    pencere.bicim_cubugu.pencere_dugmesi.click()
    assert stil(pencere, 1, 2).sayi_bicimi == "0.00%"
    assert (g.sayfa.hucre(1, 2), g.sayfa.sonuc(1, 2)) == onceki
