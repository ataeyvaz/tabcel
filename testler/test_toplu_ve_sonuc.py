"""Toplu yazım (tek olay) ve K4'ün arayüz tarafı: formül sonucu çizilir, girdi çizilmez."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import MAX_ROW, AdresHatasi
from tabcel.model.deger import BASV, BOL0
from tabcel.model.sayfa import CalismaKitabi, Hucre, Sayfa
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


# --- toplu_yaz ---
def test_toplu_yaz_tek_olay_ve_eskiler():
    k = CalismaKitabi()
    olaylar = []
    k.dinle(olaylar.append)
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(1.0))
    olaylar.clear()
    eski = s.toplu_yaz({(1, 1): Hucre(2.0), (1, 2): Hucre("a"), (5, 5): None, (1, 3): Hucre(1.0)})
    assert eski == {(1, 1): Hucre(1.0), (1, 2): None, (5, 5): None, (1, 3): None}
    assert len(olaylar) == 1 and olaylar[0].tur == "hucre"
    d = olaylar[0]["degisiklikler"]
    assert set(d) == {(1, 1), (1, 2), (1, 3)}                # (5,5) zaten boştu: değişmedi
    assert d[(1, 1)] == (Hucre(1.0), Hucre(2.0))


def test_toplu_yaz_hic_degisiklik_yoksa_olay_yok():
    k = CalismaKitabi()
    olaylar = []
    k.dinle(olaylar.append)
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(1.0))
    olaylar.clear()
    s.toplu_yaz({(1, 1): Hucre(1.0), (2, 2): None})
    assert olaylar == []


def test_toplu_yaz_sinir_disi_hata_verir():
    s = Sayfa("S")
    with pytest.raises(AdresHatasi):
        s.toplu_yaz({(MAX_ROW + 1, 1): Hucre(1.0)})


def test_toplu_yaz_kullanilan_aralik_ve_sonuclari_gunceller():
    s = Sayfa("S")
    s.toplu_yaz({(2, 2): Hucre(None, "=1"), (9, 9): Hucre(1.0)})
    s.sonuc_ata(2, 2, 1.0)
    assert s.kullanilan_aralik() == (2, 2, 9, 9)
    s.toplu_yaz({(2, 2): Hucre(None, "=2"), (9, 9): None})
    assert s.kullanilan_aralik() == (2, 2, 2, 2) and s.sonuc(2, 2) is None


# --- arayüz: sonuç çizilir ---
@pytest.fixture
def izgara(app):
    Izgara._pano_durumu = None
    s = Sayfa("S")
    g = Izgara(s)
    g.resize(600, 300)
    g.show()
    return g


def yerlesim(g):
    sut, sat = list(g._gorunen_sutunlar()), list(g._gorunen_satirlar())
    return g._yerlesim(sut, sat, QFontMetrics(g._yazi_tipi()), g._z(4))[0]


def metinler(g):
    return [m[3] for m in yerlesim(g)]


def test_formul_hucresi_sonuc_gelene_kadar_bos_gorunur(izgara):
    izgara.sayfa.ata(1, 1, Hucre(None, "=A2*2"))
    assert metinler(izgara) == []                            # girdi (formül metni) hücreye çizilmez
    izgara.sayfa.sonuc_ata(1, 1, 10.0)
    assert metinler(izgara) == ["10"]


def test_hata_sonucu_turkce_ve_ortali(izgara):
    izgara.sayfa.ata(1, 1, Hucre(None, "=1/0"))
    izgara.sayfa.sonuc_ata(1, 1, BOL0)
    izgara.sayfa.ata(2, 1, Hucre(None, "=X"))
    izgara.sayfa.sonuc_ata(2, 1, BASV)
    m = yerlesim(izgara)
    assert [x[3] for x in m] == ["#SAYI/0!", "#BAŞV!"]
    from PySide6.QtCore import Qt
    assert all(x[2] == Qt.AlignHCenter for x in m)


def test_metin_sonucu_soldan_tasar(izgara):
    izgara.sayfa.ata(1, 1, Hucre(None, '=A&"x"'))
    izgara.sayfa.sonuc_ata(1, 1, "çok uzun bir metin sonucu burada taşıyor olmalı")
    kirp = yerlesim(izgara)[0][0]
    assert kirp.width() > izgara.sayfa.genislik(1)


def test_otomatik_sigdir_sonucu_olcer(izgara):
    izgara.sayfa.ata(1, 1, Hucre(None, "=A2"))
    izgara.sayfa.sonuc_ata(1, 1, "çok uzun bir sonuç metni")
    izgara.sec((1, 1))
    izgara.sutun_otomatik_sigdir([1])
    assert izgara.sayfa.genislik(1) > 100
    izgara.sayfa.ata(2, 2, Hucre(None, "=bos"))               # sonucu olmayan formül ölçüye girmez
    izgara.sutun_otomatik_sigdir([2])
    assert izgara.sayfa.genislik(2) == 64


def test_ozet_formul_sonuclarini_toplar(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(4.0))
    s.ata(2, 1, Hucre(None, "=A1*2"))
    s.sonuc_ata(2, 1, 8.0)
    s.ata(3, 1, Hucre(None, "=bos"))                          # sonuçsuz formül: dolu sayılır, toplama girmez
    p = Pencere(k)
    p.show()
    p.izgara().sec((1, 1), (3, 1))
    t = p.ozet_etiketi.text()
    assert "Toplam: 12" in t and "Sayım: 3" in t and "Ortalama: 6" in t


def test_ozet_ust_uste_binen_araliklar_bir_kez_sayilir(app):
    k = CalismaKitabi()
    for r in range(1, 5):
        k.sayfalar[0].ata(r, 1, Hucre(float(r)))
    p = Pencere(k)
    p.show()
    g = p.izgara()
    g.sec((1, 1), (3, 1))
    g._ekler.append(g.secim)                                  # Ctrl+tık gibi: önceki aralık kalır
    g._koru = True
    g.sec((2, 1), (4, 1))                                     # 1-3 ile 2-4 üst üste biner
    g._koru = False
    assert len(g.secimler) == 2
    p._ozet_guncelle()
    assert "Sayım: 4" in p.ozet_etiketi.text() and "Toplam: 10" in p.ozet_etiketi.text()


def test_toplu_yaz_kullanilan_aralik_onbellegi_rastgele_islemlerle_eslesir():
    import random
    rnd = random.Random(11)
    s = Sayfa("S")
    for tur in range(60):
        adet = rnd.choice([1, 3, 40, 300])                    # 256 üstü: önbellek tamamen geçersiz kılınır
        yeni = {}
        for _ in range(adet):
            anahtar = (rnd.randint(1, 60), rnd.randint(1, 20))
            yeni[anahtar] = Hucre(float(tur)) if rnd.random() < 0.55 else None
        s.toplu_yaz(yeni)
        gercek = None
        if s._hucreler:
            rs = [k[0] for k in s._hucreler]
            cs = [k[1] for k in s._hucreler]
            gercek = (min(rs), min(cs), max(rs), max(cs))
        assert s.kullanilan_aralik() == gercek


def test_toplu_yaz_ata_ile_ayni_sonucu_verir():
    import random
    rnd = random.Random(5)
    a, b = Sayfa("A"), Sayfa("B")
    for tur in range(30):
        yeni = {(rnd.randint(1, 30), rnd.randint(1, 8)):
                (Hucre(None, f"=X{tur}") if rnd.random() < 0.3 else Hucre(rnd.random()) if rnd.random() < 0.6 else None)
                for _ in range(25)}
        a.toplu_yaz(yeni)
        for anahtar, h in yeni.items():
            b.ata(*anahtar, h)
        assert dict(a._hucreler) == dict(b._hucreler)
        assert a.kullanilan_aralik() == b.kullanilan_aralik()
