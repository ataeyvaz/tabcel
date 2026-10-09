"""Faz 3 gerçek iş senaryosu: biçimli aylık bütçe (CLAUDE.md "her faz sonunda gerçek iş senaryosu").

Kullanıcı gibi davranır: başlık satırı biçimlendirir, birleşik başlık atar, para/yüzde biçimi verir,
tarih yazar, ay adlarını sürükleyip doldurur, biçim boyacısıyla biçim taşır, dondurur, kopyala-yapıştır
ile biçimi taşır, hepsini geri alır. Gerçek Excel'de açma/karşılaştırma kullanıcıya kalır.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.model import bicim_islem as bi
from tabcel.model.adres import Aralik
from tabcel.model.sayi_bicimi import bicimle
from tabcel.model.stil import StilYama
from tabcel.ui import window
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere

GIDERLER = [("Kira", 15000.0), ("Market", 8200.5), ("Fatura", 2300.0), ("Ulaşım", 1800.0)]


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def p(app, monkeypatch):
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: None)
    Izgara._pano_durumu = None
    pen = Pencere()
    pen.show()
    return pen


def gorunen(g, r, c):
    """Hücrenin kanonik biçimle görünen metni."""
    s = g.sayfa
    return bicimle(s.deger(r, c) if s.hucre(r, c) is None or s.hucre(r, c).formul is None
                   else s.sonuc(r, c), s.stil(r, c).sayi_bicimi).metin


def kur(p):
    g = p.izgara()
    g.hucre_gir(1, 1, "Aylık Bütçe 2026")
    g.sec((1, 1), (1, 4))
    g.birlestir("ortala")
    g.bicim_uygula(StilYama(kalin=True, boyut=14.0))
    for c, b in enumerate(["Kalem", "Tutar", "Pay", "Vade"], start=1):
        g.hucre_gir(2, c, b)
    g.sec((2, 1), (2, 4))
    g.bicim_uygula(StilYama(kalin=True, dolgu="#217346", yazi_rengi="#FFFFFF"))
    for r, (ad, tutar) in enumerate(GIDERLER, start=3):
        g.hucre_gir(r, 1, ad)
        g.hucre_gir(r, 2, str(tutar).replace(".", ","))
        g.hucre_gir(r, 3, f"=B{r}/TOPLA($B$3:$B$6)")
    g.sec((3, 2), (6, 2))
    g.bicim_uygula(bi.sayi_bicimi_yamasi(bi.PARA))
    g.sec((3, 3), (6, 3))
    g.bicim_uygula(bi.sayi_bicimi_yamasi(bi.YUZDE))
    return g


def test_baslik_birlesim_ve_biçim(p):
    g = kur(p)
    s = g.sayfa
    assert s.birlesim(1, 3) is not None and s.birlesim(1, 1).son_sutun == 4
    assert s.stil(1, 1).kalin and s.stil(1, 1).boyut == 14.0
    assert s.stil(2, 3).dolgu == "#217346" and s.stil(2, 3).yazi_rengi == "#FFFFFF"
    assert g.sayfa.yukseklik(1) >= g.sayfa.yukseklik(3)      # büyük yazı satırı uzatmış olmalı


def test_para_ve_yuzde_gorunumu(p):
    g = kur(p)
    assert gorunen(g, 3, 2) == "₺15.000,00"
    assert gorunen(g, 4, 2) == "₺8.200,50"
    toplam = sum(t for _, t in GIDERLER)
    assert g.sayfa.sonuc(3, 3) == pytest.approx(15000.0 / toplam)
    assert gorunen(g, 3, 3).endswith("%")
    assert sum(g.sayfa.sonuc(r, 3) for r in range(3, 7)) == pytest.approx(1.0)


def test_tarih_girisi_ve_ay_doldurma(p):
    g = kur(p)
    g.hucre_gir(3, 4, "15.01.2026")
    assert g.sayfa.stil(3, 4).sayi_bicimi != "General"
    assert g.sayfa.deger(3, 4) == 46037.0                    # 15.01.2026 seri sayısı
    g.hucre_gir(8, 1, "Ocak")
    g.hucre_gir(8, 2, "Şubat")
    assert g.doldur(Aralik(8, 1, 8, 2), Aralik(8, 3, 8, 6))
    assert [g.sayfa.deger(8, c) for c in range(1, 7)] == ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"]
    g.geri_al()
    assert g.sayfa.hucre(8, 3) is None


def test_boyaci_ile_biçim_tasima_ve_geri_al(p):
    g = kur(p)
    g.sec((2, 1))
    g.boyaci_baslat()
    g.sec((8, 1), (8, 4))
    g._boyaci_uygula()
    for c in range(1, 5):
        assert g.sayfa.stil(8, c).dolgu == "#217346" and g.sayfa.stil(8, c).kalin
    g.geri_al()
    assert g.sayfa.stil(8, 1).dolgu != "#217346"
    assert g.sayfa.stil(2, 1).dolgu == "#217346"             # kaynak yerinde


def test_kopyala_yapistir_biçim_ve_formul_tasir(p):
    g = kur(p)
    g.sec((3, 2), (6, 3))
    g.kopyala()
    g.sec((11, 2))
    g.yapistir()
    assert g.sayfa.stil(11, 2).sayi_bicimi == bi.PARA and g.sayfa.stil(11, 3).sayi_bicimi == bi.YUZDE
    # formül göreli kaydı: B11/TOPLA($B$3:$B$6) — mutlak aralık sabit kalır
    assert g.sayfa.hucre(11, 3).formul == "=B11/SUM($B$3:$B$6)"
    g.geri_al()
    assert g.sayfa.hucre(11, 3) is None and g.sayfa.stil(11, 2).sayi_bicimi != bi.PARA


def test_dondur_ve_gorunum_sayfaya_ozel(p):
    g = kur(p)
    g.sec((3, 2))
    assert g.dondur_ayarla("bolme")
    assert g.sayfa.dondur == (3, 2)
    p.sayfa_ekle()
    assert p.izgara().sayfa.dondur is None


def test_hucreleri_degistirince_para_biçimi_degeri_bozmaz(p):
    g = kur(p)
    g.hucre_gir(3, 2, "20000")
    assert g.sayfa.deger(3, 2) == 20000.0                    # biçim korunur, değer sayı
    assert g.sayfa.stil(3, 2).sayi_bicimi == bi.PARA
    assert g.sayfa.sonuc(3, 3) == pytest.approx(20000.0 / (20000.0 + 8200.5 + 2300.0 + 1800.0))


def test_metni_kaydir_otomatik_satir_yuksekligi(p):
    g = kur(p)
    g.sec((7, 1))
    g.bicim_uygula(StilYama(kaydir=True))
    g.hucre_gir(7, 1, "Uzun bir açıklama metni burada\nikinci satır")
    varsayilan = g.sayfa.yukseklik(3)
    assert g._yuk(7) > varsayilan
