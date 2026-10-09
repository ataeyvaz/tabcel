"""Faz 3 / 3c: ızgara çizimi stili uygular (dolgu, kenarlık, yazı tipi, hizalama, sayı biçimi),
yatay artımlı kaydırma tam çizimle aynı pikselleri verir, büyük seçimde özet ertelenir."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.sayfa import CalismaKitabi, Hucre, Sayfa
from tabcel.model.stil import Kenarlik, Stil
from tabcel.ui.grid import Izgara


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def izgara(app):
    Izgara._pano_durumu = None
    g = Izgara(Sayfa("S"))
    g.resize(640, 360)
    g.show()
    return g


def uygula(g, anahtar, **alan):
    k = g.sayfa.havuz.kimlik(Stil(**alan))
    g.sayfa.bicim_yaz({anahtar: k})


def yerlesim(g):
    sut, sat = list(g._gorunen_sutunlar()), list(g._gorunen_satirlar())
    return g._yerlesim(sut, sat, QFontMetrics(g._yazi_tipi()), g._z(4))[0]


def metin_bul(g, metin):
    return next(m for m in yerlesim(g) if m[3] == metin)


def piksel(g, x, y) -> str:
    return g.viewport().grab().toImage().pixelColor(x, y).name()


def ic_nokta(g, r, c):
    ar = g.hucre_dikdortgeni(r, c)
    return ar.left() + 3, ar.top() + 3


# --- dolgu ---
def test_dolgu_rengi_cizilir(izgara):
    uygula(izgara, (3, 2), dolgu="#FFFF00")
    x, y = ic_nokta(izgara, 3, 2)
    assert piksel(izgara, x, y) == "#ffff00"
    x2, y2 = ic_nokta(izgara, 3, 3)
    assert piksel(izgara, x2, y2) != "#ffff00"


def test_bos_hucrede_dolgu_ve_stilli_liste(izgara):
    uygula(izgara, (2, 2), dolgu="#00FF00")
    yerlesim(izgara)
    assert [g_[4].dolgu.lower() for g_ in izgara._stilli] == ["#00ff00"]


def test_satir_stili_dolgusu_tum_satira_uygulanir(izgara):
    k = izgara.sayfa.havuz.kimlik(Stil(dolgu="#AABBCC"))
    izgara.sayfa.bicim_yaz(satirlar={4: k})
    for c in (1, 5):
        x, y = ic_nokta(izgara, 4, c)
        assert piksel(izgara, x, y) == "#aabbcc"


# --- kenarlık ---
def test_kenarlik_cizilir_kalin_komsuyu_ezer(izgara):
    ar = izgara.hucre_dikdortgeni(3, 2)
    uygula(izgara, (3, 2), kenar=Kenarlik(alt=("ince", "#FF0000")))
    assert piksel(izgara, ar.left() + 5, ar.bottom()) == "#ff0000"
    # komşunun üstü kalın mavi: aynı çizgide kalın olan kazanır
    uygula(izgara, (4, 2), kenar=Kenarlik(ust=("kalin", "#0000FF")))
    assert piksel(izgara, ar.left() + 5, ar.bottom()) == "#0000ff"


# --- yazı tipi ---
def test_kalin_italik_boyut(izgara):
    izgara.sayfa.ata(1, 1, Hucre("Başlık"))
    uygula(izgara, (1, 1), kalin=True, italik=True, boyut=22.0)
    m = metin_bul(izgara, "Başlık")
    _, fe, stil = m[5]
    assert fe.font.bold() and fe.font.italic()
    temel = izgara._yazi_tipi().pointSizeF()
    assert fe.font.pointSizeF() == pytest.approx(temel * 2)          # 22 / 11
    assert m[4] > 0


def test_yazi_rengi_ve_font_ailesi(izgara):
    izgara.sayfa.ata(1, 1, Hucre("x"))
    uygula(izgara, (1, 1), yazi_rengi="#FF0000", yazi_tipi="Courier New")
    _, fe, stil = metin_bul(izgara, "x")[5]
    assert stil.yazi_rengi.lower() == "#ff0000"
    assert fe.font.family() == "Courier New"


# --- hizalama ---
def test_hizalama_metin_sag_orta_girinti(izgara):
    izgara.sayfa.ata(1, 1, Hucre("a"))
    izgara.sayfa.ata(2, 1, Hucre("b"))
    izgara.sayfa.ata(3, 1, Hucre("c"))
    uygula(izgara, (1, 1), yatay="sag")
    uygula(izgara, (2, 1), yatay="orta")
    uygula(izgara, (3, 1), girinti=2)
    assert metin_bul(izgara, "a")[2] == Qt.AlignRight
    assert metin_bul(izgara, "b")[2] == Qt.AlignHCenter
    c = metin_bul(izgara, "c")
    assert c[2] == Qt.AlignLeft
    assert c[1].left() - izgara.hucre_dikdortgeni(3, 1).left() == izgara._z(4) + 2 * izgara._z(9)


def test_sayi_sola_hizali_ve_metin_sagda_taşmaz(izgara):
    izgara.sayfa.ata(1, 1, Hucre(5.0))
    uygula(izgara, (1, 1), yatay="sol")
    assert metin_bul(izgara, "5")[2] == Qt.AlignLeft
    izgara.sayfa.ata(2, 1, Hucre("çok uzun bir metin burada taşıyor"))
    uygula(izgara, (2, 1), yatay="sag")
    m = metin_bul(izgara, "çok uzun bir metin burada taşıyor")
    assert m[0].width() == izgara.sayfa.genislik(1) - 1                # sağa hizalı metin taşmaz


def test_dikey_hizalama_konumu(izgara):
    izgara.sayfa.satir_yukseklik[1] = 60
    izgara.sayfa.ata(1, 1, Hucre("üst"))
    izgara.sayfa.ata(1, 2, Hucre("alt"))
    uygula(izgara, (1, 1), dikey="ust")
    m_ust, m_alt = metin_bul(izgara, "üst"), metin_bul(izgara, "alt")
    assert m_ust[5][2].dikey == "ust" and m_alt[5][2].dikey == "alt"


# --- sayı biçimi ---
def test_sayi_bicimi_metne_yansir(izgara):
    izgara.sayfa.sutun_genislik[1] = 120
    izgara.sayfa.ata(1, 1, Hucre(0.256))
    uygula(izgara, (1, 1), sayi_bicimi="0.0%")
    assert metin_bul(izgara, "25,6%")
    izgara.sayfa.ata(2, 1, Hucre(1234.5))
    uygula(izgara, (2, 1), sayi_bicimi="#,##0.00")
    assert metin_bul(izgara, "1.234,50")


def test_tarih_bicimi_ve_renk(izgara):
    izgara.sayfa.sutun_genislik[1] = 220
    izgara.sayfa.ata(1, 1, Hucre(46000.0))
    uygula(izgara, (1, 1), sayi_bicimi="dd.mm.yyyy")
    metin = [m for m in yerlesim(izgara)][0][3]
    assert metin.count(".") == 2 and len(metin) == 10
    izgara.sayfa.ata(2, 1, Hucre(-5.0))
    uygula(izgara, (2, 1), sayi_bicimi="0;[Red]-0")
    m = metin_bul(izgara, "-5")
    assert m[5][0] is not None                                        # biçimin rengi


def test_bicim_siginca_diyez_ve_gecersiz_kod_genel(izgara):
    izgara.sayfa.sutun_genislik[1] = 20
    izgara.sayfa.ata(1, 1, Hucre(1234567.891))
    uygula(izgara, (1, 1), sayi_bicimi="#,##0.00")
    assert set(yerlesim(izgara)[0][3]) == {"#"}
    izgara.sayfa.ata(2, 1, Hucre(7.0))
    uygula(izgara, (2, 1), sayi_bicimi='0"yarım')                     # kapanmamış tırnak
    assert any(m[3] for m in yerlesim(izgara) if m[1].top() > izgara.hucre_dikdortgeni(1, 1).top())


def test_metin_bicimli_sayi_degeri_degisince_onbellek_tazelenir(izgara):
    izgara.sayfa.ata(1, 1, Hucre(2.0))
    uygula(izgara, (1, 1), sayi_bicimi="0.00")
    assert metin_bul(izgara, "2,00")
    uygula(izgara, (1, 1), sayi_bicimi="0.0")
    assert metin_bul(izgara, "2,0")
    izgara.sayfa.ata(1, 1, Hucre(3.0))
    assert metin_bul(izgara, "3,0")


# --- stil yoksa eski davranış ---
def test_stilsiz_sayfada_stilli_liste_bos(izgara):
    izgara.sayfa.ata(1, 1, Hucre(1.0))
    yerlesim(izgara)
    assert izgara._stilli == []


# --- artımlı yatay kaydırma tam çizimle aynı ---
def _ornek_sayfa():
    s = Sayfa("S")
    for r in range(1, 40):
        for c in range(1, 30):
            s.ata(r, c, Hucre(f"m{r}-{c}" if c == 1 else float(r * c) + 0.5))
    s.ata(5, 3, Hucre("bu uzun metin sağdaki boş hücrelere taşıyor ve devam ediyor"))
    uygula_s = lambda k, **a: s.bicim_yaz({k: s.havuz.kimlik(Stil(**a))})
    uygula_s((6, 4), dolgu="#FFFF00", kalin=True)
    uygula_s((7, 5), kenar=Kenarlik(sol=("orta", "#FF0000"), ust=("ince", "#0000FF")))
    uygula_s((8, 6), sayi_bicimi="0.0%", yatay="orta")
    return s


@pytest.mark.parametrize("adim", [1, 2, 3, -1])
def test_yatay_artimli_kaydirma_tam_ciziminle_ayni(app, adim):
    s = _ornek_sayfa()
    g = Izgara(s)
    g.resize(640, 360)
    g.show()
    QTest.qWait(30)
    hs = g.horizontalScrollBar()
    baslangic = 6
    hs.setValue(baslangic)
    app.processEvents()
    g.viewport().repaint()                    # başlangıç durumu tam çizildi
    hs.setValue(baslangic + adim)
    app.processEvents()
    artimli = g.viewport().grab().toImage()   # grab tam çizim yapar; artımlı yol repaint ile sınanır
    g.viewport().update()
    taze = Izgara(s)
    taze.resize(640, 360)
    taze.show()
    taze.horizontalScrollBar().setValue(baslangic + adim)
    app.processEvents()
    assert taze.viewport().grab().toImage() == artimli


def test_yatay_kaydirma_scroll_cagirir_ve_son_degeri_izler(izgara):
    izgara.horizontalScrollBar().setValue(3)
    assert izgara._yatay_son == 3
    izgara.horizontalScrollBar().setValue(1)
    assert izgara._yatay_son == 1


# --- özet ertelenir ---
def test_buyuk_secimde_ozet_ertelenir_kucukte_aninda(app):
    from tabcel.ui.window import Pencere
    k = CalismaKitabi()
    for r in range(1, 101):
        for c in range(1, 81):
            k.sayfalar[0].ata(r, c, Hucre(1.0))
    p = Pencere(k)
    p.show()
    g = p.izgara()
    g.sec((1, 1), (3, 3))
    assert "Toplam: 9" in p.ozet_etiketi.text()                       # küçük: hemen
    g.sec((1, 1), (100, 80))                                          # 8000 hücre > eşik
    assert "Toplam: 9" in p.ozet_etiketi.text()                       # henüz eski metin
    QTest.qWait(120)
    assert "Toplam: 8000" in p.ozet_etiketi.text()


# --- kısmi boyama: yalnız değişen bölge ---
def _boyanan_dikdortgenler(app, g, islem):
    kayit = []
    asil = g._boya

    def boya(p, kirp):
        kayit.append(kirp)
        return asil(p, kirp)
    g._boya = boya
    try:
        islem()
        app.processEvents()
    finally:
        del g._boya
    return kayit


def test_shift_ok_yalniz_fark_bolgesini_boyar(app):
    s = Sayfa("S")
    for r in range(1, 30):
        for c in range(1, 12):
            s.ata(r, c, Hucre(float(r * c)))
    g = Izgara(s)
    g.resize(900, 600)
    g.show()
    g.sec((2, 2), (12, 8))
    app.processEvents()
    kayit = _boyanan_dikdortgenler(app, g, lambda: g.sec((2, 2), (13, 8)))
    boyanan = sum(r.width() * r.height() for r in kayit)
    secim_alani = (g.hucre_dikdortgeni(12, 8).right() - g.hucre_dikdortgeni(2, 2).left()) * \
        (g.hucre_dikdortgeni(12, 8).bottom() - g.hucre_dikdortgeni(2, 2).top())
    assert kayit and boyanan < secim_alani / 2          # seçimin iç alanı yeniden boyanmaz


def test_ok_tusu_tum_izgarayi_yeniden_boyamaz(app):
    from tabcel.ui.window import Pencere
    k = CalismaKitabi()
    for r in range(1, 30):
        for c in range(1, 12):
            k.sayfalar[0].ata(r, c, Hucre(float(r * c)))
    p = Pencere(k)
    p.resize(1000, 600)
    p.show()
    g = p.izgara()
    g.sec((1, 1))
    app.processEvents()
    vp_alani = g.viewport().width() * g.viewport().height()
    kayit = _boyanan_dikdortgenler(app, g, lambda: QTest.keyClick(g, Qt.Key_Down))
    assert sum(r.width() * r.height() for r in kayit) < vp_alani / 4


def test_kalin_ust_kenarlik_ustteki_satirin_piksellerine_tasar(app):
    s = Sayfa("S")
    s.ata(2, 2, Hucre(1.0))
    s.bicim_yaz({(2, 2): s.havuz.kimlik(Stil(kenar=Kenarlik(ust=("kalin", "#FF0000"))))})
    g = Izgara(s)
    g.resize(400, 200)
    g.show()
    app.processEvents()
    ar = g.hucre_dikdortgeni(2, 2)
    # (parçalı boyamadaki taşma payı için gerçek pencere denetimi: araclar/cizim_dogrula.py)
    assert piksel(g, ar.left() + 10, ar.top() - 2) == "#ff0000"
