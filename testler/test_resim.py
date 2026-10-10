"""Faz 6 / 6g: resim ekleme (Pillow ile doğrulama, ızgarada çizim, Ekle → Resim…)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from tabcel.model.grafik import Konum, Resim
from tabcel.model.resim_yukle import EN_BUYUK_BAYT, resim_coz, resim_olustur, resim_yukle
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.window import Pencere


def yaz(yol, boyut=(100, 80), renk=(255, 0, 0), bicim="PNG"):
    Image.new("RGB", boyut, renk).save(yol, bicim)
    return str(yol)


# ------------------------------------------------------------------ model
@pytest.mark.parametrize("bicim,uzanti", [("PNG", "png"), ("JPEG", "jpg"), ("GIF", "gif"), ("BMP", "bmp")])
def test_desteklenen_bicimler_okunur(tmp_path, bicim, uzanti):
    r = resim_yukle(yaz(tmp_path / f"a.{uzanti}", (120, 60), bicim=bicim))
    assert isinstance(r, Resim) and r.ad == f"a.{uzanti}" and r.boyut == (120, 60) and r.veri
    assert r.kimlik == 0


def test_baytlar_aynen_saklanir(tmp_path):
    yol = yaz(tmp_path / "a.png")
    assert resim_yukle(yol).veri == open(yol, "rb").read()


def test_buyuk_resim_600_pikselde_oran_korunarak_kisaltilir(tmp_path):
    r = resim_yukle(yaz(tmp_path / "b.png", (1200, 800)))
    assert r.boyut == (600, 400)


def test_konum_verilir(tmp_path):
    assert resim_yukle(yaz(tmp_path / "a.png"), Konum(3, 4)).konum == Konum(3, 4)


@pytest.mark.parametrize("icerik", [b"", b"bu resim degil", b"\x89PNG\r\n\x1a\nbozuk"])
def test_bozuk_icerik_reddedilir(icerik):
    with pytest.raises(ValueError, match="resim olarak açılamadı"):
        resim_coz(icerik)


def test_desteklenmeyen_tur_reddedilir(tmp_path):
    yol = tmp_path / "a.tiff"
    Image.new("RGB", (10, 10)).save(yol, "TIFF")
    with pytest.raises(ValueError, match="PNG, JPEG, GIF, BMP"):
        resim_yukle(str(yol))


def test_yok_dosya_ve_cok_buyuk(tmp_path):
    with pytest.raises(ValueError, match="resim olarak açılamadı"):
        resim_yukle(str(tmp_path / "yok.png"))
    with pytest.raises(ValueError, match="25 MB"):
        resim_coz(b"x" * (EN_BUYUK_BAYT + 1))


def test_resim_olustur_bayttan():
    import io
    b = io.BytesIO()
    Image.new("RGB", (30, 20)).save(b, "PNG")
    assert resim_olustur(b.getvalue(), "x.png").boyut == (30, 20)


# ------------------------------------------------------------------ arayüz
@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    from tabcel.ui.grid import Izgara
    Izgara._nesne_panosu = None
    p = Pencere(CalismaKitabi())
    p.resize(1000, 800)
    p.show()
    p.uyarilar = []
    monkeypatch.setattr(p, "_uyari", lambda metin: p.uyarilar.append(metin))
    QApplication.processEvents()
    return p


def test_ekle_sekmesinde_resim_dugmesi(pencere):
    assert pencere.eylemler["resim_ekle"] in pencere.serit.eylemler()


def test_resim_eklenir_secilir_ortada_tek_geri_al(pencere, tmp_path):
    assert pencere.grafik_eylemleri.resim_ekle_dosya(yaz(tmp_path / "a.png"))
    g = pencere.izgara()
    assert len(g.sayfa.nesneler) == 1 and g.secili_nesne == g.sayfa.nesneler[0].kimlik
    r = g.nesne_dikdortgeni(g.secili_nesne)
    merkez = g.viewport().rect().center()
    assert abs(r.center().x() - merkez.x()) < 80 and abs(r.center().y() - merkez.y()) < 60
    assert not pencere.serit.sekme_gorunur_mu("Grafik")                  # resimde bağlamsal sekme yok
    g.geri_al()
    assert g.sayfa.nesneler == []
    g.yinele()
    assert len(g.sayfa.nesneler) == 1 and isinstance(g.sayfa.nesneler[0], Resim)


def test_resim_izgarada_cizilir(pencere, tmp_path):
    pencere.grafik_eylemleri.resim_ekle_dosya(yaz(tmp_path / "a.png", (100, 80), (255, 0, 0)))
    g = pencere.izgara()
    g.nesne_sec(None)
    QApplication.processEvents()
    c = g.nesne_dikdortgeni(g.sayfa.nesneler[0].kimlik).center()
    renk = g.viewport().grab().toImage().pixelColor(c)
    assert (renk.red(), renk.green(), renk.blue()) == (255, 0, 0)


def test_resim_tasininca_yeniden_cozulmez(pencere, tmp_path):
    pencere.grafik_eylemleri.resim_ekle_dosya(yaz(tmp_path / "a.png"))
    g = pencere.izgara()
    kimlik = g.secili_nesne
    g.viewport().grab()
    ilk = g._resim_onb[kimlik][1]
    g.nesne_oteleme(30, 20)
    g.viewport().grab()
    assert g._resim_onb[kimlik][1] is ilk


def test_silinince_cozulmus_resim_birakilir(pencere, tmp_path):
    pencere.grafik_eylemleri.resim_ekle_dosya(yaz(tmp_path / "a.png"))
    g = pencere.izgara()
    kimlik = g.secili_nesne
    g.viewport().grab()
    assert kimlik in g._resim_onb
    g.nesne_sil()
    assert kimlik not in g._resim_onb


def test_bozuk_dosya_uyari_verir_resim_eklenmez(pencere, tmp_path):
    yol = tmp_path / "bozuk.png"
    yol.write_bytes(b"resim degil")
    assert not pencere.grafik_eylemleri.resim_ekle_dosya(str(yol))
    assert pencere.uyarilar and "resim olarak açılamadı" in pencere.uyarilar[0]
    assert pencere.izgara().sayfa.nesneler == []


def test_resim_dosya_iletisimi_iptalinde_bir_sey_olmaz(pencere, monkeypatch):
    from tabcel.ui import grafik_eylemleri
    monkeypatch.setattr(grafik_eylemleri.QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    assert not pencere.grafik_eylemleri.resim_sec()
    assert pencere.izgara().sayfa.nesneler == []


def test_resim_dosya_iletisiminden_eklenir(pencere, monkeypatch, tmp_path):
    from tabcel.ui import grafik_eylemleri
    yol = yaz(tmp_path / "a.png")
    monkeypatch.setattr(grafik_eylemleri.QFileDialog, "getOpenFileName", lambda *a, **k: (yol, ""))
    pencere.eylemler["resim_ekle"].trigger()
    assert len(pencere.izgara().sayfa.nesneler) == 1


def test_resim_boyutlandirilinca_orani_korur_ve_pano(pencere, tmp_path):
    pencere.grafik_eylemleri.resim_ekle_dosya(yaz(tmp_path / "a.png", (200, 100)))
    g = pencere.izgara()
    n = g.sayfa.nesne(g.secili_nesne)
    assert n.boyut == (200, 100)
    assert g.nesne_kopyala(False) and g.nesne_yapistir()
    assert len(g.sayfa.nesneler) == 2 and g.sayfa.nesneler[1].veri == n.veri
