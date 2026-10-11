"""Faz 6 / 6i: yazdırma ve PDF'te grafik + resim (dilime kırpılır, alan nesneyi kapsar, vektör grafik)."""
import io
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Konum, Referans, Resim, Seri
from tabcel.model.grafik_cizim import PALET
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sayfa_yapisi import SayfaYapisi
from tabcel.model.sayfalama import nesne_son_hucre, sayfala, yazdirma_alani
from tabcel.ui import yazdir as yz
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _png(renk=(255, 0, 0), boyut=(40, 30)):
    b = io.BytesIO()
    Image.new("RGB", boyut, renk).save(b, "PNG")
    return b.getvalue()


def _pencere(app, veri=True):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    if veri:
        for r in range(1, 6):
            s.ata(r, 1, Hucre(f"K{r}"))
            s.ata(r, 2, Hucre(float(r * 10)))
    p = Pencere(k)
    p.resize(1000, 800)
    p.show()
    QApplication.processEvents()
    return p


def _grafik(sayfa, konum, boyut=(300, 200)):
    return Grafik(seriler=(Seri(deger=Referans(sayfa.kimlik, Aralik(1, 2, 5, 2)),
                                kategori=Referans(sayfa.kimlik, Aralik(1, 1, 5, 1))),),
                  konum=konum, boyut=boyut, gosterge=None)


def _cizici(p):
    g = p.izgara()
    return g, yz.SayfaCizici(g.sayfa, g.yazdirma_yuksekligi, g.font())


def _ciz(c, d, boyut=(900, 700)):
    img = QImage(boyut[0], boyut[1], QImage.Format_RGB32)
    img.fill(QColor("white"))
    pt = QPainter(img)
    c.ciz(pt, d, QRectF(0, 0, boyut[0], boyut[1]), 96.0)
    pt.end()
    return img


def _say(img, renk, rect=None):
    x1, y1, x2, y2 = rect or (0, 0, img.width(), img.height())
    return sum(1 for y in range(max(0, y1), min(img.height(), y2)) for x in range(max(0, x1), min(img.width(), x2))
               if img.pixelColor(x, y).name().upper() == renk.upper())


# ---------------------------------------------------------------- model (Qt'siz)
def test_nesne_son_hucre_ve_alan_nesneyi_kapsar():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("x"))
    s.nesne_ekle(Resim(veri=_png(), konum=Konum(3, 2), boyut=(200, 100)))
    gen = lambda c: 64.0
    yuk = lambda r: 20.0
    n = s.nesneler[0]
    assert nesne_son_hucre(n, gen, yuk) == (3 + 4, 2 + 3)           # 100 px = 5 satır (3..7), 200 px = 4 sütun (2..5)
    a = yazdirma_alani(s, SayfaYapisi(), gen, yuk)
    assert (a.ilk_satir, a.ilk_sutun) == (1, 1) and a.son_satir >= 7 and a.son_sutun >= 5
    assert yazdirma_alani(s, SayfaYapisi()).son_satir == 1          # ölçü verilmezse nesneler yok sayılır


def test_yalniz_nesneli_sayfa_yazdirilir():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.nesne_ekle(Resim(veri=_png(), konum=Konum(2, 2), boyut=(100, 60)))
    gen, yuk = (lambda c: 64.0), (lambda r: 20.0)
    assert sayfala(s, SayfaYapisi(), gen, yuk) != []
    assert sayfala(s, SayfaYapisi(), lambda c: 64.0, lambda r: 20.0)[0].satirlar[0] == 2
    k2 = CalismaKitabi()
    assert sayfala(k2.sayfalar[0], SayfaYapisi(), gen, yuk) == []


def test_ayarli_yazdirma_alani_nesneyle_genislemez():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.nesne_ekle(Resim(veri=_png(), konum=Konum(2, 2), boyut=(1000, 600)))
    y = SayfaYapisi(alan=Aralik(1, 1, 3, 3))
    assert yazdirma_alani(s, y, lambda c: 64.0, lambda r: 20.0) == Aralik(1, 1, 3, 3)


# ---------------------------------------------------------------- çizim
def test_resim_sayfada_dogru_yerde_cizilir(app):
    p = _pencere(app, veri=False)
    g, c = _cizici(p)
    g.sayfa.nesne_ekle(Resim(veri=_png((255, 0, 0), (40, 30)), konum=Konum(2, 2, 5, 3), boyut=(80, 40)))
    d = c.dilimler()[0]
    img = _ciz(c, d)
    assert d.satirlar[0] == 2 and d.sutunlar[0] == 2             # boş sayfada alan nesnenin çapasından başlar
    x0, y0 = 5, 3
    assert img.pixelColor(int(x0 + 40), int(y0 + 20)).name().upper() == "#FF0000"
    assert img.pixelColor(int(x0 - 2), int(y0 + 20)).name().upper() == "#FFFFFF"
    assert _say(img, "#FF0000") == pytest.approx(80 * 40, rel=0.1)


def test_grafik_vektor_cizilir_ve_renk_var(app):
    p = _pencere(app)
    g, c = _cizici(p)
    g.sayfa.nesne_ekle(_grafik(g.sayfa, Konum(8, 4)))
    img = _ciz(c, c.dilimler()[0], (900, 900))
    assert _say(img, PALET[0]) > 200
    # 2× yazıcı çözünürlüğünde aynı grafik daha çok piksel (vektör: yeniden kurulur, bulanıklaşmaz)
    img2 = QImage(1800, 1800, QImage.Format_RGB32)
    img2.fill(QColor("white"))
    pt = QPainter(img2)
    c.ciz(pt, c.dilimler()[0], QRectF(0, 0, 1800, 1800), 192.0)
    pt.end()
    assert _say(img2, PALET[0]) == pytest.approx(4 * _say(img, PALET[0]), rel=0.15)


def test_nesne_iki_dilimde_kendi_parcasiyla_cizilir(app):
    p = _pencere(app, veri=False)
    g = p.izgara()
    s = g.sayfa
    for r in range(1, 121):
        s.ata(r, 1, Hucre(f"s{r}"))
    c = yz.SayfaCizici(s, g.yazdirma_yuksekligi, g.font())
    d = c.dilimler()
    assert len(d) >= 2
    son = d[0].satirlar[-1]
    # resim ilk dilimin son 30 px'inden başlar, 100 px yüksekliğinde → alt 70 px'i ikinci dilimde
    s.nesne_ekle(Resim(veri=_png((255, 0, 0)), konum=Konum(son - 1, 3, 0, int(g.yazdirma_yuksekligi(son - 1)
                                                                           + g.yazdirma_yuksekligi(son)) - 30),
                       boyut=(60, 100)))
    c = yz.SayfaCizici(s, g.yazdirma_yuksekligi, g.font())
    d = c.dilimler()
    on, arka = _ciz(c, d[0], (900, 1300)), _ciz(c, d[1], (900, 1300))
    k1, k2 = _say(on, "#FF0000"), _say(arka, "#FF0000")
    assert k1 == pytest.approx(60 * 30, rel=0.15) and k2 == pytest.approx(60 * 70, rel=0.15)


def test_yinelenen_baslikta_govde_nesnesi_basligi_ezmez(app):
    p = _pencere(app, veri=False)
    g = p.izgara()
    s = g.sayfa
    for r in range(1, 121):
        s.ata(r, 1, Hucre(f"s{r}"))
    s.sayfa_yapisi = SayfaYapisi(baslik_satirlari=(1, 1))
    c = yz.SayfaCizici(s, g.yazdirma_yuksekligi, g.font())
    d = c.dilimler()
    assert len(d) >= 2 and d[1].baslik_sayisi == 1 and d[0].baslik_sayisi == 0
    bas = d[0].satirlar[-1]
    s.nesne_ekle(Resim(veri=_png((255, 0, 0)), konum=Konum(bas, 3, 0, 0), boyut=(60, int(g.yazdirma_yuksekligi(bas)) + 50)))
    c = yz.SayfaCizici(s, g.yazdirma_yuksekligi, g.font())
    d = c.dilimler()
    img = _ciz(c, d[1], (900, 1300))
    h1 = int(g.yazdirma_yuksekligi(1))
    assert _say(img, "#FF0000", (0, 0, 900, h1)) == 0              # yinelenen başlık bandı boş
    assert _say(img, "#FF0000") > 0


def test_yazdirma_alani_disi_nesne_kismi_cizilmez(app):
    p = _pencere(app)
    g = p.izgara()
    s = g.sayfa
    s.sayfa_yapisi = SayfaYapisi(alan=Aralik(1, 1, 3, 3))
    s.nesne_ekle(Resim(veri=_png((255, 0, 0)), konum=Konum(1, 1), boyut=(2000, 2000)))
    c = yz.SayfaCizici(s, g.yazdirma_yuksekligi, g.font())
    d = c.dilimler()[0]
    img = _ciz(c, d, (900, 700))
    toplam_g = sum(c.genislik(x) for x in d.sutunlar)
    toplam_y = sum(g.yazdirma_yuksekligi(r) for r in d.satirlar)
    assert _say(img, "#FF0000", (int(toplam_g) + 3, 0, 900, 700)) == 0
    assert _say(img, "#FF0000", (0, int(toplam_y) + 3, 900, 700)) == 0
    assert _say(img, "#FF0000") > 1000


def test_pdf_nesneli_sayfa_uretilir(app, tmp_path):
    p = _pencere(app)
    g = p.izgara()
    g.sayfa.nesne_ekle(_grafik(g.sayfa, Konum(8, 4)))
    g.sayfa.nesne_ekle(Resim(veri=_png(), konum=Konum(2, 5), boyut=(80, 60)))
    yol = str(tmp_path / "n.pdf")
    assert yz.pdf_yaz([g], yol) is True
    veri = open(yol, "rb").read()
    assert veri.startswith(b"%PDF") and len(veri) > 2000
    # nesnesiz sayfadan belirgin büyük (grafik + resim içeriği PDF'e girdi)
    g.sayfa.nesne_sil(g.sayfa.nesneler[0].kimlik)
    g.sayfa.nesne_sil(g.sayfa.nesneler[0].kimlik)
    yol2 = str(tmp_path / "bos.pdf")
    assert yz.pdf_yaz([g], yol2) is True
    assert len(veri) > os.path.getsize(yol2)


def test_nesne_yoksa_cizim_degismez(app):
    p = _pencere(app)
    g, c = _cizici(p)
    a = _ciz(c, c.dilimler()[0])
    g.sayfa.nesne_ekle(Resim(veri=_png(), konum=Konum(20, 20), boyut=(50, 50)))
    g.sayfa.nesne_sil(g.sayfa.nesneler[0].kimlik)
    assert a == _ciz(c, c.dilimler()[0])


def test_nesne_konumu_kumulatif_hesaplanir_dilim_basina_baslan_toplanmaz(app):
    """Opus bulgusu: `_nesneleri_ciz` her nesne×dilim için çapadan dilim başına tüm satırları topluyordu
    (30.000 satır/625 dilim: 6 sn). Artık kümülatif liste bir kez kurulur: nesne yüzünden EK ölçü sorgusu
    en çok satır sayısı kadar (süre değil çağrı sayısı sınanır: zamanlama testleri yükte kırılgan)."""
    p = _pencere(app, veri=False)
    g = p.izgara()
    s = g.sayfa
    n = 6000
    for r in range(1, n + 1):
        s.ata(r, 1, Hucre(float(r)))

    def say(nesneli):
        for x in list(s.nesneler):
            s.nesne_sil(x.kimlik)
        if nesneli:
            s.nesne_ekle(Resim(veri=_png(), konum=Konum(n - 5, 3), boyut=(60, 40)))
        cagri = [0]

        def yuk(r):
            cagri[0] += 1
            return g.yazdirma_yuksekligi(r)
        c = yz.SayfaCizici(s, yuk, g.font())
        dil = c.dilimler()
        cagri[0] = 0
        img = QImage(50, 50, QImage.Format_RGB32)
        pt = QPainter(img)
        for d in dil:
            ys, y = {}, 0.0
            for r in d.satirlar:
                ys[r] = y
                y += yuk(r)
            c._nesneleri_ciz(pt, d, ys, 500.0, y)
        pt.end()
        return cagri[0], len(dil)

    temel, dilim_say = say(False)
    nesneli, _ = say(True)
    assert dilim_say >= 50                                      # çok dilimli: eski kod burada satır×dilim çağırırdı
    assert nesneli - temel <= n + 10, (nesneli, temel)
