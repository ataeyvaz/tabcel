"""Faz 3 / 3j: metni kaydır (sarılmış çizim) + elle ayarlanmamış satırın içeriğe göre otomatik yüksekliği."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil
from tabcel.ui.window import Pencere

UZUN = "Bu oldukça uzun bir cümledir ve dar sütuna sığmayacağı için satırlara bölünmelidir"


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    p = Pencere(CalismaKitabi())
    p.resize(1000, 600)
    p.show()
    return p


def kaydir_ac(g, r, c, **ek):
    k = g.sayfa.havuz.kimlik(Stil(kaydir=True, **ek))
    g.sayfa.bicim_yaz({(r, c): k})
    g._guncelle()


def yuk(g, r):
    return g._yuk(r)


def render(g):
    img = QImage(g.viewport().size(), QImage.Format_RGB32)
    p = QPainter(img)
    g._boya(p, g.viewport().rect())
    p.end()
    return img


def koyu_satirlar(img, d):
    """Hücre dikdörtgeni içinde koyu piksel bulunan yatay bantların sayısı (≈ metin satırı sayısı)."""
    bant, onceki, say = [], False, 0
    for y in range(d.y() + 1, d.y() + d.height() - 1):
        var = any(QColor(img.pixel(x, y)).lightness() < 110 for x in range(d.x() + 2, d.x() + d.width() - 2))
        if var and not onceki:
            say += 1
        onceki = var
    return say


# ------------------------------------------------------------------ otomatik yükseklik
def test_kaydirilmis_metin_satiri_uzatir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    varsayilan = yuk(g, 2)
    assert varsayilan == g._z(20)
    kaydir_ac(g, 2, 1)
    assert yuk(g, 2) > 2 * varsayilan                       # birkaç satıra bölündü
    assert yuk(g, 1) == g._z(20) and yuk(g, 3) == g._z(20)  # komşu satırlar aynı


def test_sutun_genisleyince_satir_kisalir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1)
    dar = yuk(g, 2)
    g.sec((1, 1))
    g.sutun_genisligi_ayarla(500)
    assert yuk(g, 2) < dar
    g.geri_al()
    assert yuk(g, 2) == dar                                 # geri al yüksekliği de geri getirir


def test_elle_yukseklik_kazanir_ve_otomatik_sigdir_geri_acar(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1)
    g.sec((2, 1))
    g.satir_yuksekligi_ayarla(30)
    assert yuk(g, 2) == g._z(30)                            # elle ayarlandı: içeriğe bakmaz
    g.satir_otomatik_sigdir()
    assert yuk(g, 2) > g._z(40)                             # otomatik sığdır: tekrar içeriğe göre


def test_kaydirma_kapatilinca_satir_eski_haline_doner(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1)
    assert yuk(g, 2) > g._z(20)
    g.sec((2, 1))
    pencere.bicim_cubugu.kaydir.click()
    assert not g.sayfa.stil(2, 1).kaydir and yuk(g, 2) == g._z(20)
    pencere.bicim_cubugu.kaydir.click()
    assert yuk(g, 2) > g._z(20)


def test_metin_degisince_yukseklik_izler(pencere):
    g = pencere.izgara()
    kaydir_ac(g, 2, 1)
    g.hucre_gir(2, 1, UZUN)
    uzun = yuk(g, 2)
    assert uzun > g._z(20)
    g.hucre_gir(2, 1, "kısa")
    assert yuk(g, 2) == g._z(20)
    g.hucre_gir(2, 1, UZUN + UZUN)
    assert yuk(g, 2) > uzun


def test_alt_enter_kaydirmayi_acar_ve_satir_uzar(pencere):
    g = pencere.izgara()
    g.hucre_gir(3, 2, "birinci\nikinci\nüçüncü")
    assert g.sayfa.stil(3, 2).kaydir
    assert yuk(g, 3) >= 3 * g.fontMetrics().height()
    g.geri_al()                                              # metin + biçim tek adım
    assert g.sayfa.hucre(3, 2) is None and not g.sayfa.stil(3, 2).kaydir and yuk(g, 3) == g._z(20)
    g.hucre_gir(4, 2, "tek satır")
    assert not g.sayfa.stil(4, 2).kaydir


def test_sayilar_kaydirilmaz(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(123456789012.0))
    kaydir_ac(g, 2, 1)
    assert yuk(g, 2) == g._z(20)


def test_formul_sonucu_metin_kaydirilir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 3, Hucre(UZUN))
    g.sayfa.ata(2, 1, Hucre(None, "=C1"))
    kaydir_ac(g, 2, 1)
    assert yuk(g, 2) > g._z(40)
    g.hucre_gir(1, 3, "k")                                   # kaynağı değiştirince (sonuç olayı) kısalır
    assert yuk(g, 2) == g._z(20)


def test_satir_stili_ile_kaydirma(pencere):
    g = pencere.izgara()
    g.sayfa.ata(5, 1, Hucre(UZUN))
    k = g.sayfa.havuz.kimlik(Stil(kaydir=True))
    g.sayfa.bicim_yaz(satirlar={5: k})
    g._guncelle()
    assert yuk(g, 5) > g._z(40)


def test_gizli_satir_ve_birlesik_hucre_katilmaz(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1)
    g.sayfa.gizli_satir.add(2)
    g._guncelle()
    assert yuk(g, 2) == 0
    g.sayfa.gizli_satir.discard(2)
    g.sayfa.birlesimleri_yaz([Aralik(2, 1, 2, 2)], [])
    g._guncelle()
    assert yuk(g, 2) == g._z(20)                             # birleşik hücre satırı büyütmez


def test_buyuk_yazi_boyutu_satiri_buyutur(pencere):
    g = pencere.izgara()
    g.sayfa.ata(3, 1, Hucre("Başlık"))
    k = g.sayfa.havuz.kimlik(Stil(boyut=36.0))
    g.sayfa.bicim_yaz({(3, 1): k})
    g._guncelle()
    buyuk = yuk(g, 3)
    assert buyuk > g._z(30)
    g.sec((3, 1))
    g.satir_yuksekligi_ayarla(20)
    assert yuk(g, 3) == g._z(20)                             # elle ayar kazanır
    g.satir_otomatik_sigdir()
    assert yuk(g, 3) == buyuk


def test_yakinlastirmada_yukseklik_olcekli(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1)
    y100 = yuk(g, 2)
    g.yakinlastir(2.0)
    assert yuk(g, 2) > 1.5 * y100
    g.yakinlastir(1.0)
    assert yuk(g, 2) == y100


def test_satir_ust_alti_konumlari_ve_kaydirma_sonraki_satirlari_iter(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1)
    g.sayfa.satir_yukseklik[2] = 20
    g._guncelle()
    d3_once = g.hucre_dikdortgeni(3, 1).y()
    del g.sayfa.satir_yukseklik[2]
    g._guncelle()
    assert g.hucre_dikdortgeni(3, 1).y() > d3_once           # alt satırlar aşağı kaydı


# ------------------------------------------------------------------ çizim
def test_metin_satirlara_bolunur_ve_hucre_icinde_kalir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1)
    g.sec((9, 9))
    d = g.hucre_dikdortgeni(2, 1)
    img = render(g)
    assert koyu_satirlar(img, d) >= 3                        # birden çok satır çizildi
    # hücrenin sağındaki komşuya taşma yok
    kom = g.hucre_dikdortgeni(2, 2)
    assert all(QColor(img.pixel(x, y)).lightness() > 200
               for x in range(kom.x() + 2, kom.x() + kom.width() - 2) for y in range(kom.y() + 2, kom.y() + kom.height() - 2))


def test_kaydirma_kapaliyken_tek_satir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    g.sec((9, 9))
    assert koyu_satirlar(render(g), g.hucre_dikdortgeni(2, 1)) == 1


def test_uzun_kelime_hucre_genisliginde_boyunca_boler(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre("x" * 60))
    kaydir_ac(g, 2, 1)
    assert yuk(g, 2) > g._z(40)                              # tek kelime bile birden çok satır
    g.sec((9, 9))
    d, kom = g.hucre_dikdortgeni(2, 1), g.hucre_dikdortgeni(2, 2)
    img = render(g)
    assert all(QColor(img.pixel(x, y)).lightness() > 200
               for x in range(kom.x() + 2, kom.x() + 20) for y in range(kom.y() + 2, kom.y() + kom.height() - 2))


def test_acik_satir_sonu_satir_sayisini_belirler(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre("a\nb\nc\nd"))
    kaydir_ac(g, 2, 1)
    g.sec((9, 9))
    assert koyu_satirlar(render(g), g.hucre_dikdortgeni(2, 1)) == 4


def test_dikey_hiza_ust_ve_alt(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre("a b"))
    g.sayfa.satir_yukseklik[2] = 60                          # elle yüksek satır
    kaydir_ac(g, 2, 1, dikey="ust")
    g.sec((9, 9))
    d = g.hucre_dikdortgeni(2, 1)
    img = render(g)
    ust_y = next(y for y in range(d.y() + 1, d.y() + d.height()) if
                 any(QColor(img.pixel(x, y)).lightness() < 110 for x in range(d.x() + 2, d.x() + d.width() - 2)))
    assert ust_y - d.y() < 8
    kaydir_ac(g, 2, 1, dikey="alt")
    img = render(g)
    alt_y = max(y for y in range(d.y() + 1, d.y() + d.height()) if
                any(QColor(img.pixel(x, y)).lightness() < 110 for x in range(d.x() + 2, d.x() + d.width() - 2)))
    assert d.y() + d.height() - alt_y < 12


def test_yatay_ortalama_sarilmis_metinde(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre("ab cd"))
    g.sayfa.sutun_genislik[1] = 120
    kaydir_ac(g, 2, 1, yatay="orta")
    g.sec((9, 9))
    d = g.hucre_dikdortgeni(2, 1)
    img = render(g)
    xs = [x for x in range(d.x() + 2, d.x() + d.width() - 2) for y in range(d.y() + 2, d.y() + d.height() - 2)
          if QColor(img.pixel(x, y)).lightness() < 110]
    assert abs((min(xs) + max(xs)) / 2 - (d.x() + d.width() / 2)) < 8


def test_birlesik_hucrede_kaydirilmis_metin_cok_satirli(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    g.sayfa.birlesimleri_yaz([Aralik(2, 1, 5, 2)], [])
    kaydir_ac(g, 2, 1)
    g.sec((9, 9))
    d = g.hucre_dikdortgeni(2, 1)
    assert d.height() == sum(g._yuk(r) for r in range(2, 6))
    assert koyu_satirlar(render(g), d) >= 2


def test_stilli_kaydirilmis_hucre_yazi_rengi_ve_dolgu(pencere):
    g = pencere.izgara()
    g.sayfa.ata(2, 1, Hucre(UZUN))
    kaydir_ac(g, 2, 1, dolgu="#FFFF00", yazi_rengi="#FF0000")
    g.sec((9, 9))
    d = g.hucre_dikdortgeni(2, 1)
    img = render(g)
    assert img.pixelColor(d.x() + 1, d.y() + 1).name().upper() == "#FFFF00"
    assert any(img.pixelColor(x, y).red() > 200 and img.pixelColor(x, y).green() < 80
               for x in range(d.x() + 2, d.x() + d.width() - 2) for y in range(d.y() + 2, d.y() + d.height() - 2))
