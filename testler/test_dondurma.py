"""Faz 3 / 3i: dondurulmuş bölmeler ve kılavuz çizgisi — model, kaydırma, seçim, çizim (piksel)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.adres import AdresHatasi, Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import theme
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 60):
        for c in range(1, 8):
            s.ata(r, c, Hucre(f"{chr(64 + c)}{r}"))
    p = Pencere(k)
    p.resize(1000, 600)
    p.show()
    return p


def A(r1, c1, r2, c2):
    return Aralik(r1, c1, r2, c2)


def hizalar(g):
    return [c for c, _, _ in g._gorunen_sutunlar()], [r for r, _, _ in g._gorunen_satirlar()]


def render(g):
    img = QImage(g.viewport().size(), QImage.Format_RGB32)
    p = QPainter(img)
    g._boya(p, g.viewport().rect())
    p.end()
    return img


# ------------------------------------------------------------------ model
def test_model_gorunum_yaz_ve_olay():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    olaylar = []
    k.dinle(olaylar.append)
    assert s.dondur is None and s.kilavuz is True
    assert s.gorunum_yaz(dondur=(3, 2)) and s.dondur == (3, 2)
    assert olaylar[-1].tur == "bicim" and olaylar[-1]["gorunum"] == {"dondur": (3, 2)}
    assert not s.gorunum_yaz(dondur=(3, 2))                    # aynı: olay yok
    n = len(olaylar)
    assert not s.gorunum_yaz() and len(olaylar) == n            # hiçbir şey verilmedi
    assert s.gorunum_yaz(kilavuz=False) and s.kilavuz is False
    assert olaylar[-1]["gorunum"] == {"kilavuz": False}
    assert s.gorunum_yaz(dondur=(1, 1)) and s.dondur is None    # (1,1) = dondurma yok
    assert s.gorunum_yaz(dondur=(4, 1), kilavuz=True) and olaylar[-1]["gorunum"] == {"dondur": (4, 1), "kilavuz": True}
    assert s.gorunum_yaz(dondur=None) and s.dondur is None
    with pytest.raises(AdresHatasi):
        s.gorunum_yaz(dondur=(0, 3))
    with pytest.raises(AdresHatasi):
        s.gorunum_yaz(dondur=(2, 99999))


def test_gorunum_geri_al_yigininda_degil(pencere):
    g = pencere.izgara()
    n = len(pencere.yigin._geri)
    g.sec((3, 3))
    g.dondur_ayarla("bolme")
    g.kilavuz_goster(False)
    assert len(pencere.yigin._geri) == n                       # geri alınamaz (Excel gibi)


# ------------------------------------------------------------------ düzen / kaydırma
def test_ust_satir_donar_ve_kaydirilirken_gorunur_kalir(pencere):
    g = pencere.izgara()
    assert g.dondur_ayarla("ust_satir")
    g.verticalScrollBar().setValue(20)
    _, satirlar = hizalar(g)
    assert satirlar[0] == 1 and satirlar[1] == 21               # 1. satır sabit, sonra kayan bölge
    assert 2 not in satirlar and 20 not in satirlar
    assert g.verticalScrollBar().minimum() == 1                 # kayan bölge 2. satırdan başlar


def test_ilk_sutun_donar(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ilk_sutun")
    g.horizontalScrollBar().setValue(3)
    sutunlar, _ = hizalar(g)
    assert sutunlar[0] == 1 and sutunlar[1] == 4 and 2 not in sutunlar
    g.horizontalScrollBar().setValue(0)
    assert g.horizontalScrollBar().value() == 1                 # alt sınır dondurmaya göre


def test_bolme_etkin_hucrenin_ustu_ve_solu(pencere):
    g = pencere.izgara()
    g.sec((4, 3))
    assert g.dondur_ayarla("bolme") and g.sayfa.dondur == (4, 3)
    g.verticalScrollBar().setValue(30)
    g.horizontalScrollBar().setValue(5)
    sutunlar, satirlar = hizalar(g)
    assert sutunlar[:3] == [1, 2, 6] and satirlar[:4] == [1, 2, 3, 31]


def test_etkin_hucre_ilk_hucredeyse_dondurma_olmaz(pencere):
    g = pencere.izgara()
    g.sec((1, 1))
    g.dondur_ayarla("bolme")
    assert g.sayfa.dondur is None


def test_dondurmayi_kaldir(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ust_satir")
    g.verticalScrollBar().setValue(10)
    g.dondur_ayarla("coz")
    assert g.sayfa.dondur is None and g.verticalScrollBar().minimum() == 0
    _, satirlar = hizalar(g)
    assert satirlar[0] == 11                                    # kaydırma konumu korunur


def test_bilinmeyen_tur(pencere):
    with pytest.raises(ValueError):
        pencere.izgara().dondur_ayarla("yarim")


def test_pencereyi_dolduran_dondurma_reddedilir(pencere, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: QMessageBox.Ok)
    g = pencere.izgara()
    g.sec((500, 1))
    assert g.dondur_ayarla("bolme") is False and g.sayfa.dondur is None


# ------------------------------------------------------------------ seçim ve gezinme
def test_nokta_hucre_eslemesi_dondurmayla(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ust_satir")
    g.verticalScrollBar().setValue(20)
    d1, d21 = g.hucre_dikdortgeni(1, 1), g.hucre_dikdortgeni(21, 1)
    assert g._noktadan(d1.center()) == (1, 1) and g._noktadan(d21.center()) == (21, 1)
    assert g.hucre_dikdortgeni(5, 1) is None                    # kaydırılıp çıkmış satır
    assert d21.y() == d1.y() + d1.height()                      # dondurulmuş satırın hemen altı


def test_gezinme_dondurulmus_bolgeye_ve_kayan_bolgeye(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ilk_sutun")
    g.sec((1, 2))
    QTest.keyClick(g, Qt.Key_Left)
    assert g.aktif == (1, 1)                                    # dondurulmuş sütuna geçiş
    assert g.horizontalScrollBar().value() == 1                 # kaydırma kaymadı
    g.sec((1, 7))
    g.horizontalScrollBar().setValue(6)
    g.sec((1, 3))
    assert g.horizontalScrollBar().value() == 2                 # kayan bölgedeki sola gitme kaydırır
    g.sec((1, 1))
    assert g.horizontalScrollBar().value() == 2                 # dondurulmuş hücre kaydırma istemez


def test_secim_dondurma_siniri_boyunca(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ust_satir")
    g.verticalScrollBar().setValue(20)
    g.sec((1, 1), (22, 2))
    assert g.secim == A(1, 1, 22, 2)
    img = render(g)                                             # gizli aradaki satırlarla çizilebilir
    assert not img.isNull()


def test_pano_ve_ozet_dondurmadan_etkilenmez(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ust_satir")
    g.sec((1, 1), (3, 1))
    g.kopyala()
    g.sec((10, 1))
    g.yapistir()
    assert g.sayfa.hucre(12, 1) == Hucre("A3")


# ------------------------------------------------------------------ çizim
def test_dondurma_cizgisi_cizilir(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ust_satir")
    img = render(g)
    d1 = g.hucre_dikdortgeni(1, 1)
    y = d1.y() + d1.height() - 1
    x = g._baslik_g() + 3 * g._gen(1) + 5
    assert img.pixelColor(x, y).name().lower() == "#7f7f7f"
    g.dondur_ayarla("coz")
    assert render(g).pixelColor(x, y).name().lower() == QColor(theme.GRID_LINE).name().lower()


def test_dondurulmus_bolme_kaydirilinca_ayni_pikselleri_verir(pencere):
    g = pencere.izgara()
    g.dondur_ayarla("ust_satir")
    g.verticalScrollBar().setValue(15)
    ust = render(g).copy(0, 0, g.viewport().width(), g._baslik_y() + g._yuk(1))
    g.verticalScrollBar().setValue(30)
    ust2 = render(g).copy(0, 0, g.viewport().width(), g._baslik_y() + g._yuk(1))
    assert ust == ust2                                          # sabit satır hiç değişmez


def test_artimli_kaydirma_dondurmada_tam_cizimle_ayni(pencere):
    g = pencere.izgara()
    g.sec((3, 3))
    g.dondur_ayarla("bolme")
    g.verticalScrollBar().setValue(10)
    g.horizontalScrollBar().setValue(4)
    gorunen = g.viewport().grab().toImage()
    tam = render(g)
    farkli = sum(1 for x in range(0, gorunen.width(), 7) for y in range(0, gorunen.height(), 5)
                 if gorunen.pixel(x, y) != tam.pixel(x, y))
    assert farkli == 0


def test_metin_dondurma_cizgisini_asmaz(pencere):
    g = pencere.izgara()
    g.sayfa.ata(30, 1, Hucre("çok uzun bir metin " * 6))
    g.dondur_ayarla("ilk_sutun")
    g.horizontalScrollBar().setValue(4)
    g.verticalScrollBar().setValue(25)
    metinler, _ = g._yerlesim(list(g._gorunen_sutunlar()), list(g._gorunen_satirlar()),
                              g.fontMetrics(), 4)
    m = [x for x in metinler if "çok uzun" in x[3]]
    assert m and m[0][0].width() <= g._gen(1)                    # taşma yok: kırpma kutusu 1. sütun kadar


def test_kilavuz_gizle_goster_piksel(pencere):
    g = pencere.izgara()
    d = g.hucre_dikdortgeni(5, 3)
    x, y = d.x() + d.width() - 1, d.y() + 4                     # sağ kılavuz çizgisi
    cizgi = QColor(theme.GRID_LINE).name().lower()
    assert render(g).pixelColor(x, y).name().lower() == cizgi
    g.kilavuz_goster(False)
    assert g.sayfa.kilavuz is False
    assert render(g).pixelColor(x, y).name().lower() == QColor(theme.SURFACE).name().lower()
    # başlık çizgileri durur
    assert render(g).pixelColor(g._baslik_g() - 1, 40).name().lower() == cizgi
    g.kilavuz_goster(True)
    assert render(g).pixelColor(x, y).name().lower() == cizgi


def test_kilavuz_gizliyken_dolgu_ve_kenarlik_gorunur(pencere):
    from tabcel.model.stil import Kenarlik, Stil
    g = pencere.izgara()
    g.kilavuz_goster(False)
    g.sayfa.bicim_yaz({(3, 3): g.sayfa.havuz.kimlik(Stil(dolgu="#FFFF00", kenar=Kenarlik(alt=("ince", "#000000"))))})
    d = g.hucre_dikdortgeni(3, 3)
    img = render(g)
    assert img.pixelColor(d.x() + 2, d.y() + 2).name().upper() == "#FFFF00"
    assert img.pixelColor(d.x() + 2, d.y() + d.height() - 1).name() == "#000000"


# ------------------------------------------------------------------ pencere menüsü
def test_gorunum_menusu(pencere, monkeypatch):
    g = pencere.izgara()
    e = pencere.gorunum_eylemleri
    assert set(e) == {"bolme", "ust_satir", "ilk_sutun", "coz"}
    g.sec((3, 2))
    e["bolme"].trigger()
    assert g.sayfa.dondur == (3, 2)
    pencere._gorunum_menusu_hazirla()
    assert e["coz"].isEnabled() and pencere.kilavuz_eylemi.isChecked()
    pencere.kilavuz_eylemi.setChecked(False)
    assert g.sayfa.kilavuz is False
    e["coz"].trigger()
    assert g.sayfa.dondur is None
    pencere._gorunum_menusu_hazirla()
    assert not e["coz"].isEnabled() and not pencere.kilavuz_eylemi.isChecked()


def test_gorunum_sayfaya_ozel(pencere):
    pencere.sayfa_ekle()
    g2 = pencere.izgara()
    assert g2.sayfa.dondur is None and g2.sayfa.kilavuz is True
    pencere.kitap.sayfalar[0].gorunum_yaz(dondur=(2, 1), kilavuz=False)
    pencere._gorunum_menusu_hazirla()
    assert pencere.kilavuz_eylemi.isChecked()                    # etkin sayfanın durumu


def test_acilista_kayitli_dondurma_uygulanir(app):
    k = CalismaKitabi()
    k.sayfalar[0].gorunum_yaz(dondur=(3, 2))
    p = Pencere(k)
    p.show()
    g = p.izgara()
    assert g.verticalScrollBar().minimum() == 2 and g.horizontalScrollBar().minimum() == 1
