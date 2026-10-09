"""Faz 2 gerçek iş senaryosu: aylık bütçe çizelgesi (CLAUDE.md "her faz sonunda gerçek iş senaryosu").

Kullanıcı gibi davranır: Türkçe formülleri yazar, aşağı kopyalar, iki sayfa arası başvuru kurar,
satır ekler, geri alır, döngü yapar. Beklenen değerler testte Python ile bağımsız hesaplanır.
Gerçek Excel'de açma/karşılaştırma kullanıcıya kalır (surec.md → elle test bekliyor).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.model.deger import Hata
from tabcel.model.komutlar import SatirEkleSil
from tabcel.ui import window
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere

# (kategori, tür, ocak, şubat, mart)
VERI = [
    ("Maaş", "Gelir", 42000.0, 42000.0, 45000.0),
    ("Kira geliri", "Gelir", 9000.0, 9000.0, 9000.0),
    ("Kira", "Gider", 15000.0, 15000.0, 15000.0),
    ("Market", "Gider", 8200.5, 7900.25, 9100.0),
    ("Fatura", "Gider", 2300.0, 2650.75, 2100.0),
    ("Ulaşım", "Gider", 1800.0, 1750.0, 1900.0),
    ("Eğlence", "Gider", 1500.0, 2200.0, 1250.0),
    ("Yatırım", "Gider", 5000.0, 5000.0, 5000.0),
]


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: None)
    Izgara._pano_durumu = None
    p = Pencere()
    p.show()
    return p


def sayi_metni(x: float) -> str:
    return str(x).replace(".", ",")


def kur(p):
    """Bütçe sayfasını yazar (başlık, veri, F sütunu toplamları aşağı kopyalanır, alt toplam satırı)."""
    k = p.kitap
    g = p.izgara()
    g.sayfa.ad = "Bütçe"
    for c, b in enumerate(["Kategori", "Tür", "Ocak", "Şubat", "Mart", "Toplam"], start=1):
        g.hucre_gir(1, c, b)
    for r, satir in enumerate(VERI, start=2):
        g.hucre_gir(r, 1, satir[0])
        g.hucre_gir(r, 2, satir[1])
        for c, v in enumerate(satir[2:], start=3):
            g.hucre_gir(r, c, sayi_metni(v))
    g.hucre_gir(2, 6, "=TOPLA(C2:E2)")
    g.sec((2, 6))
    g.kopyala()
    g.sec((3, 6), (9, 6))
    g.yapistir()                                       # F3:F9: =TOPLA(C3:E3) … göreli kayma
    g.hucre_gir(11, 1, "Toplam")
    g.hucre_gir(11, 3, "=TOPLA(C2:C9)")
    g.sec((11, 3))
    g.kopyala()
    g.sec((11, 4), (11, 6))
    g.yapistir()                                       # D11:F11
    return g


def ozet_kur(p, g):
    p.sayfa_ekle()
    o = p.izgara()
    o.sayfa.ad = "Özet"
    o.hucre_gir(1, 1, "Gelir")
    o.hucre_gir(1, 2, "=ETOPLA(Bütçe!B2:B9;\"Gelir\";Bütçe!F2:F9)")
    o.hucre_gir(2, 1, "Gider")
    o.hucre_gir(2, 2, "=ETOPLA(Bütçe!B2:B9;\"Gider\";Bütçe!F2:F9)")
    o.hucre_gir(3, 1, "Net")
    o.hucre_gir(3, 2, "=B1-B2")
    o.hucre_gir(4, 1, "Tasarruf oranı")
    o.hucre_gir(4, 2, "=EĞER(B1=0;0;YUVARLA(B3/B1;4))")
    o.hucre_gir(5, 1, "En büyük gider (Ocak)")
    o.hucre_gir(5, 2, "=MAK(Bütçe!C4:C9)")
    return o


def bekle():
    gelir = sum(sum(v[2:]) for v in VERI if v[1] == "Gelir")
    gider = sum(sum(v[2:]) for v in VERI if v[1] == "Gider")
    return gelir, gider


def test_satir_toplamlari_asagi_kopyalanir(pencere):
    g = kur(pencere)
    for r, satir in enumerate(VERI, start=2):
        assert g.sayfa.hucre(r, 6).formul == f"=SUM(C{r}:E{r})"
        assert g.sayfa.deger(r, 6) == pytest.approx(sum(satir[2:]))


def test_sutun_toplamlari(pencere):
    g = kur(pencere)
    for c in (3, 4, 5):
        assert g.sayfa.deger(11, c) == pytest.approx(sum(v[c - 1] for v in VERI))
    assert g.sayfa.deger(11, 6) == pytest.approx(sum(sum(v[2:]) for v in VERI))


def test_ozet_sayfasi_sayfalar_arasi_basvuru(pencere):
    g = kur(pencere)
    o = ozet_kur(pencere, g)
    gelir, gider = bekle()
    assert o.sayfa.deger(1, 2) == pytest.approx(gelir)
    assert o.sayfa.deger(2, 2) == pytest.approx(gider)
    assert o.sayfa.deger(3, 2) == pytest.approx(gelir - gider)
    assert o.sayfa.deger(4, 2) == pytest.approx(round((gelir - gider) / gelir, 4))
    assert o.sayfa.deger(5, 2) == pytest.approx(max(v[2] for v in VERI[2:]))
    # Türkçe görünüm, İngilizce/kimlikli saklama
    assert o.sayfa.hucre(1, 2).formul.startswith("=SUMIF([")
    from tabcel.formul.ceviri import hucre_metni
    assert hucre_metni(o.sayfa.hucre(1, 2), pencere.kitap) == "=ETOPLA(Bütçe!B2:B9;\"Gelir\";Bütçe!F2:F9)"


def test_veri_degisince_ozet_yeniden_hesaplanir(pencere):
    g = kur(pencere)
    o = ozet_kur(pencere, g)
    g.hucre_gir(2, 3, "50000")                          # Ocak maaşı arttı
    gelir, gider = bekle()
    gelir += 50000 - 42000
    assert g.sayfa.deger(2, 6) == pytest.approx(50000 + 42000 + 45000)
    assert o.sayfa.deger(1, 2) == pytest.approx(gelir)
    assert o.sayfa.deger(3, 2) == pytest.approx(gelir - gider)


def test_satir_ekleyince_formuller_ve_araliklar_genisler_ve_geri_alinir(pencere):
    g = kur(pencere)
    o = ozet_kur(pencere, g)
    gelir, gider = bekle()
    pencere.yigin.calistir(SatirEkleSil(g.sayfa, 6, 1, True))      # Market–Fatura arasına satır
    assert g.sayfa.hucre(10, 6).formul == "=SUM(C10:E10)"           # eski 9. satır 10'a kaydı, formülü de
    assert g.sayfa.hucre(12, 3).formul == "=SUM(C2:C10)"            # alt toplam aralığı genişledi
    from tabcel.formul.ceviri import hucre_metni
    assert "B2:B10" in hucre_metni(o.sayfa.hucre(2, 2), pencere.kitap)   # özet aralıkları da genişledi
    g.hucre_gir(6, 1, "Sigorta")
    g.hucre_gir(6, 2, "Gider")
    g.hucre_gir(6, 3, "1000")
    g.hucre_gir(6, 6, "=TOPLA(C6:E6)")
    assert o.sayfa.deger(2, 2) == pytest.approx(gider + 1000)       # yeni satır yalnız Ocak sütununda
    assert g.sayfa.deger(12, 3) == pytest.approx(sum(v[2] for v in VERI) + 1000)
    for _ in range(4):                                              # dört hücre girişi geri
        pencere.izgara().geri_al()
    assert g.sayfa.hucre(6, 1) is None and o.sayfa.deger(2, 2) == pytest.approx(gider)
    pencere.izgara().geri_al()                                      # satır eklemesi geri
    assert g.sayfa.hucre(9, 6).formul == "=SUM(C9:E9)"
    assert "B2:B9" in hucre_metni(o.sayfa.hucre(2, 2), pencere.kitap)
    assert o.sayfa.deger(2, 2) == pytest.approx(gider)


def test_sifira_bolme_ve_hata_yayilimi(pencere):
    g = kur(pencere)
    o = ozet_kur(pencere, g)
    for r in range(2, 4):                               # tüm gelirleri sil
        for c in range(3, 6):
            g.hucre_gir(r, c, "")
    assert o.sayfa.deger(1, 2) == 0.0
    assert o.sayfa.deger(4, 2) == 0.0                   # EĞER(B1=0;0;…) hatayı önler
    o.hucre_gir(8, 2, "=B3/B1")
    assert isinstance(o.sayfa.deger(8, 2), Hata)        # sıfıra bölme → Hata değeri
    o.hucre_gir(9, 2, "=EĞERHATA(B3/B1;\"yok\")")
    assert o.sayfa.deger(9, 2) == "yok"


def test_dongu_senaryosu_uyari_ve_cozum(pencere, monkeypatch):
    g = kur(pencere)
    uyarilar = []
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: uyarilar.append(a[2]))
    g.hucre_gir(13, 3, "=C14+1")
    g.hucre_gir(14, 3, "=C13+1")
    assert len(uyarilar) == 1 and pencere.dongu_etiketi.text() == "Döngüsel Başvurular: C13"
    g.hucre_gir(14, 3, "5")
    assert g.sayfa.deger(13, 3) == 6.0 and not pencere.dongu_etiketi.isVisible()


def test_kes_yapistir_sutunu_tasiyinca_basvurular_izler(pencere):
    g = kur(pencere)
    o = ozet_kur(pencere, g)
    gelir, gider = bekle()
    g.sec((1, 6), (11, 6))                              # Toplam sütunu → H sütununa taşı
    g.kes()
    g.sec((1, 8))
    g.yapistir()
    assert g.sayfa.deger(2, 8) == pytest.approx(sum(VERI[0][2:]))
    assert g.sayfa.deger(2, 6) is None
    from tabcel.formul.ceviri import hucre_metni
    assert "H2:H9" in hucre_metni(o.sayfa.hucre(1, 2), pencere.kitap)
    assert o.sayfa.deger(1, 2) == pytest.approx(gelir)  # özet bozulmadı
    pencere.izgara().geri_al()
    assert g.sayfa.deger(2, 6) == pytest.approx(sum(VERI[0][2:]))
    assert o.sayfa.deger(1, 2) == pytest.approx(gelir)
