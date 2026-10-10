"""Faz 6 / 6d: ızgarada nesne katmanı — konum, kaydırma, yakınlaştırma, dondurma, önbellek, canlı güncelleme."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Konum, Referans, Resim, Seri
from tabcel.model.grafik_cizim import PALET
from tabcel.model.komutlar import GeriAlYigini, NesneDegis, NesneEkle, NesneSil, SatirEkleSil
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 6):
        s.ata(r, 1, Hucre(f"K{r}"))
        s.ata(r, 2, Hucre(float(r * 10)))
    p = Pencere(k)
    p.resize(1000, 800)
    p.show()
    QApplication.processEvents()
    return p


def grafik(sayfa, konum=Konum(8, 4), boyut=(300, 200), **kw):
    return Grafik(seriler=(Seri(deger=Referans(sayfa.kimlik, Aralik(1, 2, 5, 2)),
                                kategori=Referans(sayfa.kimlik, Aralik(1, 1, 5, 1))),),
                  konum=konum, boyut=boyut, gosterge=None, **kw)


def render(g):
    img = QImage(g.viewport().size(), QImage.Format_RGB32)
    p = QPainter(img)
    g._boya(p, g.viewport().rect())
    p.end()
    return img


def renk_sayisi(img, rect, renk):
    n = 0
    for y in range(max(0, rect.top()), min(img.height(), rect.bottom())):
        for x in range(max(0, rect.left()), min(img.width(), rect.right())):
            if img.pixelColor(x, y).name().upper() == renk:
                n += 1
    return n


def kirpma(img, rect):
    return rect.intersected(QRect(0, 0, img.width(), img.height()))


# ------------------------------------------------------------------ konum
def test_nesne_capa_hucresine_gore_konumlanir(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 4, 5, 7)))
    r = g.nesne_dikdortgeni(n.kimlik)
    h = g.hucre_dikdortgeni(8, 4)
    assert (r.x(), r.y()) == (h.x() + 5, h.y() + 7) and (r.width(), r.height()) == (300, 200)


def test_grafik_ciziliyor_cubuk_rengi_var(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa))
    img = render(g)
    r = g.nesne_dikdortgeni(n.kimlik)
    assert renk_sayisi(img, kirpma(img, r), PALET[0]) > 200                  # çubuklar
    assert img.pixelColor(r.x() + 2, r.y() + r.height() - 3).name().upper() == "#FFFFFF"   # grafik alanı beyaz


def test_nesne_yoksa_onbellek_bos(pencere):
    g = pencere.izgara()
    render(g)
    assert g._nesne_onb == {}


def test_kaydirinca_konum_hucreyle_birlikte_kayar(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 4)))
    y0 = g.nesne_dikdortgeni(n.kimlik).y()
    satir_h = g._yuk(1)
    g.verticalScrollBar().setValue(3)
    QApplication.processEvents()
    assert g.nesne_dikdortgeni(n.kimlik).y() == y0 - 3 * satir_h
    img = render(g)
    assert renk_sayisi(img, kirpma(img, g.nesne_dikdortgeni(n.kimlik)), PALET[0]) > 200


def test_ustten_kismen_tasan_nesne_ve_tamamen_cikan_nesne(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 4), boyut=(300, 200)))
    g.verticalScrollBar().setValue(10)                                        # çapa satırı (8) yukarı çıktı
    QApplication.processEvents()
    r = g.nesne_dikdortgeni(n.kimlik)
    assert r is not None and r.y() < g._baslik_y() + 1 and r.bottom() > g._baslik_y()   # kısmen görünür
    img = render(g)
    # başlık bandına (üst başlık) nesne taşmaz: başlık bandı sütun harfleri için ayrılmıştır
    assert img.pixelColor(r.x() + 20, 2).name().upper() != PALET[0]
    g.verticalScrollBar().setValue(60)                                        # tamamen yukarıda
    QApplication.processEvents()
    assert g.nesne_dikdortgeni(n.kimlik) is None


def test_asagida_pencere_disi_nesne_none(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(5000, 4)))
    assert g.nesne_dikdortgeni(n.kimlik) is None
    n2 = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(5, 400)))
    assert g.nesne_dikdortgeni(n2.kimlik) is None
    img = render(g)                                                           # çizim hata vermez
    assert img.width() > 0


def test_yatay_kaydirma(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 6)))
    x0 = g.nesne_dikdortgeni(n.kimlik).x()
    g.horizontalScrollBar().setValue(2)
    QApplication.processEvents()
    assert g.nesne_dikdortgeni(n.kimlik).x() == x0 - 2 * g._gen(1)


def test_yakinlastirma_olcekler(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 4, 10, 10)))
    g.yakinlastir(2.0)
    r = g.nesne_dikdortgeni(n.kimlik)
    h = g.hucre_dikdortgeni(8, 4)
    assert (r.width(), r.height()) == (600, 400) and (r.x() - h.x(), r.y() - h.y()) == (20, 20)
    img = render(g)
    assert renk_sayisi(img, kirpma(img, r), PALET[0]) > 800
    g.yakinlastir(0.5)
    assert g.nesne_dikdortgeni(n.kimlik).width() == 150


def test_dondurma_nesneyi_kayan_bolmeye_kirpar(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 4), boyut=(500, 300)))
    g.sec((3, 3))
    pencere.eylemler["bolme"].trigger()                                       # 2 satır + 2 sütun dondur
    QApplication.processEvents()
    g.verticalScrollBar().setValue(g.verticalScrollBar().value() + 5)
    QApplication.processEvents()
    sonuc = g._nesne_dikdortgeni(g.sayfa.nesne(n.kimlik))
    assert sonuc is not None
    dik, pencere_ = sonuc
    donuk_g, donuk_y = g._donuk_olcu()
    assert pencere_.left() == g._baslik_g() + donuk_g and pencere_.top() == g._baslik_y() + donuk_y
    img = render(g)
    # donmuş bandın içine nesne taşmaz
    assert img.pixelColor(g._baslik_g() + 2, g._baslik_y() + donuk_y - 3).name().upper() != PALET[0]


def test_donuk_bolmedeki_capa_kaymaz(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(1, 4), boyut=(200, 60)))     # 1. satır donacak
    g.sec((3, 3))
    pencere.eylemler["bolme"].trigger()
    QApplication.processEvents()
    y1 = g.nesne_dikdortgeni(n.kimlik).y()
    g.verticalScrollBar().setValue(g.verticalScrollBar().value() + 20)
    QApplication.processEvents()
    assert g.nesne_dikdortgeni(n.kimlik).y() == y1


# ------------------------------------------------------------------ önbellek ve canlı güncelleme
def test_onbellek_ayni_boyutta_yeniden_kullanilir(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa))
    render(g)
    pm1 = g._nesne_onb[n.kimlik][1]
    render(g)
    assert g._nesne_onb[n.kimlik][1] is pm1                                   # ikinci çizimde yeniden kurulmadı
    g.yakinlastir(1.5)
    render(g)
    assert g._nesne_onb[n.kimlik][1] is not pm1                               # boyut değişti: yeni görüntü


def test_veri_degisince_grafik_ertelemeyle_guncellenir(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa))
    img = render(g)
    r = kirpma(img, g.nesne_dikdortgeni(n.kimlik))
    once = renk_sayisi(img, r, PALET[0])
    pm1 = g._nesne_onb[n.kimlik][1]
    g.sayfa.ata(5, 2, Hucre(500.0))                                           # son çubuk çok yükselir, ölçek değişir
    assert n.kimlik in g._nesne_kirli and g._nesne_onb[n.kimlik][1] is pm1    # hemen değil: 30 ms ertelenir
    render(g)
    assert g._nesne_onb[n.kimlik][1] is pm1                                   # kirli iken eski görüntü kullanılır
    QTest.qWait(80)
    assert n.kimlik not in g._nesne_kirli                                      # zamanlayıcı önbelleği düşürdü
    assert n.kimlik not in g._nesne_onb or g._nesne_onb[n.kimlik][1] is not pm1   # (yeniden boyama yenisini kurmuş olabilir)
    img2 = render(g)
    assert renk_sayisi(img2, r, PALET[0]) != once                             # yeni çubuk yükseklikleri


def test_ilgisiz_hucre_degisimi_grafigi_kirletmez(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa))
    render(g)
    g.sayfa.ata(20, 20, Hucre(1.0))                                           # grafik aralığıyla kesişmiyor
    assert n.kimlik not in g._nesne_kirli


def test_toplu_degisim_tek_zamanlayici_ve_formul_sonucu(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa))
    render(g)
    g.sayfa.ata(1, 3, Hucre(None, "=B1*2"))                                   # grafik dışı sütun: kirletmez
    assert n.kimlik not in g._nesne_kirli
    g.sayfa.ata(6, 2, Hucre(None, "=B1+B2"))                                  # aralığın hemen altı: kesişmez
    assert n.kimlik not in g._nesne_kirli
    g.sayfa.ata(2, 2, Hucre(None, "=B1+1"))                                   # aralık içi formül: kirletir
    assert n.kimlik in g._nesne_kirli


def test_baska_sayfadaki_veri_degisince_grafik_guncellenir(pencere):
    k = pencere.kitap
    s2 = k.sayfa_ekle()
    QApplication.processEvents()
    g2 = pencere._izgaralar[s2]
    veri_sayfa = k.sayfalar[0]
    n = s2.nesne_ekle(grafik(veri_sayfa))                                    # grafik Sayfa2'de, veri Sayfa1'de
    render(g2)
    assert n.kimlik in g2._nesne_onb
    veri_sayfa.ata(3, 2, Hucre(99.0))
    assert n.kimlik in g2._nesne_kirli
    pm1 = g2._nesne_onb[n.kimlik][1]
    QTest.qWait(80)
    assert n.kimlik not in g2._nesne_kirli
    assert n.kimlik not in g2._nesne_onb or g2._nesne_onb[n.kimlik][1] is not pm1


def test_yapi_degisimi_tum_grafikleri_kirletir_ve_geri_al(pencere):
    g = pencere.izgara()
    n = g.sayfa.nesne_ekle(grafik(g.sayfa))
    render(g)
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(g.sayfa, 1, 2, True))
    assert n.kimlik not in g._nesne_onb and n.kimlik not in g._nesne_kirli     # başvurular güncellendi (`hepsi` olayı): önbellek düştü
    QTest.qWait(80)
    assert g.sayfa.nesne(n.kimlik).seriler[0].deger.aralik == Aralik(3, 2, 7, 2)
    assert g.sayfa.nesne(n.kimlik).konum == Konum(10, 4)                       # çapa da kaydı
    r = g.nesne_dikdortgeni(n.kimlik)
    h = g.hucre_dikdortgeni(10, 4)
    assert (r.x(), r.y()) == (h.x(), h.y())


def test_nesne_olaylari_onbellegi_gunceller(pencere):
    g = pencere.izgara()
    y = GeriAlYigini()
    y.calistir(NesneEkle(g.sayfa, grafik(g.sayfa)))
    n = g.sayfa.nesneler[0]
    render(g)
    assert n.kimlik in g._nesne_onb
    y.calistir(NesneDegis(g.sayfa, n.degistir(baslik="Yeni")))
    assert n.kimlik not in g._nesne_onb                                       # değişiklik hemen düşürür
    render(g)
    assert n.kimlik in g._nesne_onb
    y.calistir(NesneSil(g.sayfa, n.kimlik))
    assert n.kimlik not in g._nesne_onb and g.nesne_dikdortgeni(n.kimlik) is None
    y.geri_al()
    assert g.nesne_dikdortgeni(n.kimlik) is not None


def test_z_sirasi_ustteki_alttakini_ortuyor(pencere):
    g = pencere.izgara()
    alt = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 4), boyut=(300, 200)))
    ust = g.sayfa.nesne_ekle(grafik(g.sayfa, Konum(8, 4, 100, 50), boyut=(300, 200), baslik="ÜST"))
    img = render(g)
    ra = g.nesne_dikdortgeni(alt.kimlik)
    ru = g.nesne_dikdortgeni(ust.kimlik)
    kesisim = ra.intersected(ru)
    # üstteki grafiğin arka planı (beyaz) alttakinin çubuklarını örter: kesişimin sol üst köşesi ÜST'ün zemini
    assert img.pixelColor(ru.x() + 2, ru.y() + 2).name().upper() == "#FFFFFF"
    assert kesisim.width() > 100 and kesisim.height() > 100


def test_resim_nesnesi_cizimi_bozmaz(pencere):
    g = pencere.izgara()
    g.sayfa.nesne_ekle(Resim(veri=b"x", konum=Konum(3, 3)))
    assert render(g).width() > 0                                              # 6g'ye dek yok sayılır, çökmez
