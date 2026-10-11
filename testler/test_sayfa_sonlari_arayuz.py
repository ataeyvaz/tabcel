"""T9: sayfa sonu eylemleri, ızgarada sayfa sınırı çizgileri, şerit, Sayfa Yapısı penceresi, PDF."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sayfa_yapisi import SayfaYapisi
from tabcel.ui import yazdir as yz
from tabcel.ui.sayfa_yapisi_penceresi import SayfaYapisiPenceresi
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 101):
        for c in range(1, 4):
            s.ata(r, c, Hucre(float(r)))
    p = Pencere(k)
    p.resize(1100, 800)
    p.show()
    QApplication.processEvents()
    yield p
    p.degisti_mi = lambda: False
    p.close()


def _git(p, r, c):
    p.izgara().sec((r, c))
    p._eylem_durumlari()


def _resim(g):
    img = QImage(g.viewport().size(), QImage.Format_RGB32)
    pt = QPainter(img)
    g._boya(pt, g.viewport().rect())
    pt.end()
    return img


def _kesme(p):
    y = p.izgara().sayfa.sayfa_yapisi
    return y.satir_kesmeleri, y.sutun_kesmeleri


# ---------------------------------------------------------------- eylem kuralları
def test_a1de_ekle_kapali_b2de_iki_yone(pencere):
    e = pencere.eylemler
    _git(pencere, 1, 1)
    assert not e["sayfa_sonu_ekle"].isEnabled() and not e["sayfa_sonu_kaldir"].isEnabled()
    _git(pencere, 11, 1)                                      # A sütunu: yalnız satır sonu
    e["sayfa_sonu_ekle"].trigger()
    assert _kesme(pencere) == ((11,), ())
    _git(pencere, 1, 3)                                       # 1. satır: yalnız sütun sonu
    e["sayfa_sonu_ekle"].trigger()
    assert _kesme(pencere) == ((11,), (3,))
    _git(pencere, 21, 2)
    e["sayfa_sonu_ekle"].trigger()
    assert _kesme(pencere) == ((11, 21), (2, 3))


def test_kaldir_etkin_hucrenin_ustundeki_ve_solundakini(pencere):
    e = pencere.eylemler
    _git(pencere, 11, 2)
    e["sayfa_sonu_ekle"].trigger()
    assert not e["sayfa_sonu_ekle"].isEnabled() and e["sayfa_sonu_kaldir"].isEnabled()
    _git(pencere, 12, 2)                                      # kesme 11'de: 12. satır için kaldırılacak satır yok, sütun 2 var
    e["sayfa_sonu_kaldir"].trigger()
    assert _kesme(pencere) == ((11,), ())
    _git(pencere, 11, 5)
    e["sayfa_sonu_kaldir"].trigger()
    assert _kesme(pencere) == ((), ())


def test_sifirla_ve_geri_al_yinele(pencere):
    e = pencere.eylemler
    _git(pencere, 11, 2)
    e["sayfa_sonu_ekle"].trigger()
    _git(pencere, 31, 1)
    e["sayfa_sonu_ekle"].trigger()
    assert e["sayfa_sonu_sifirla"].isEnabled()
    e["sayfa_sonu_sifirla"].trigger()
    assert _kesme(pencere) == ((), ())
    assert not e["sayfa_sonu_sifirla"].isEnabled()
    pencere.yigin.geri_al()
    assert _kesme(pencere) == ((11, 31), (2,))
    pencere.yigin.yinele()
    assert _kesme(pencere) == ((), ())


def test_ekleyince_cizgiler_acilir_ve_belge_degismis_sayilmaz_yalniz_gostermede(pencere):
    g = pencere.izgara()
    assert g.sayfa.sayfa_sonlari is False
    pencere.eylemler["sayfa_sonlari"].setChecked(True)          # yalnız gösterme: dosyaya yazılmaz
    assert g.sayfa.sayfa_sonlari is True and not pencere.degisti_mi()
    pencere.eylemler["sayfa_sonlari"].setChecked(False)
    _git(pencere, 11, 1)
    pencere.eylemler["sayfa_sonu_ekle"].trigger()
    assert g.sayfa.sayfa_sonlari is True                        # ekleyince açılır
    assert pencere.degisti_mi()                                 # kesme belgeyi değiştirir (dosyaya yazılır)


# ---------------------------------------------------------------- çizim
def test_cizgi_yalniz_acikken_ve_el_ile_koyu(pencere):
    g = pencere.izgara()
    g.kilavuz_goster(False)
    _git(pencere, 11, 1)
    pencere.eylemler["sayfa_sonu_ekle"].trigger()               # çizgiler açıldı
    _git(pencere, 5, 2)                                         # etkin hücre çerçevesi çizgiyi örtmesin
    dik = g.hucre_dikdortgeni(11, 1)
    y = dik.y() - 1
    x = dik.x() + 20
    img = _resim(g)
    assert img.pixelColor(x, y) == QColor("#404040")            # el ile: düz koyu
    assert img.pixelColor(x, y - 5) != QColor("#404040")
    g.sayfa_sonlari_goster(False)
    assert _resim(g).pixelColor(x, y) != QColor("#404040")


def test_otomatik_sinir_kesikli_gri_ve_sayfala_ile_ayni_yerde(pencere):
    g = pencere.izgara()
    g.kilavuz_goster(False)
    pencere.sayfa_yapisi_degistir(olcek=400)                    # sayfa başına ≈ 12 satır: ilk sınır ekranda
    g.sayfa_sonlari_goster(True)
    sn = g.sayfa_sinirlari_ver()
    assert sn is not None and sn.satirlar and not sn.satirlar[0][1]
    r = sn.satirlar[0][0]
    _git(pencere, 1, 1)
    dik = g.hucre_dikdortgeni(r, 1)
    assert dik is not None
    img = _resim(g)
    gri = [img.pixelColor(dik.x() + dx, dik.y() - 1) for dx in range(0, 40)]
    assert QColor("#7f7f7f") in gri and any(c != QColor("#7f7f7f") for c in gri)             # kesik: çizgi + boşluk


def test_sutun_sonu_dikey_cizgi(pencere):
    g = pencere.izgara()
    g.kilavuz_goster(False)
    _git(pencere, 1, 3)
    pencere.eylemler["sayfa_sonu_ekle"].trigger()
    dik = g.hucre_dikdortgeni(5, 3)
    img = _resim(g)
    assert img.pixelColor(dik.x() - 1, dik.y() + 5) == QColor("#404040")


def test_kesme_ekle_sil_ile_kayar_cizgi_de_kayar(pencere):
    g = pencere.izgara()
    _git(pencere, 11, 1)
    pencere.eylemler["sayfa_sonu_ekle"].trigger()
    from tabcel.model.komutlar import SatirEkleSil
    pencere.yigin.calistir(SatirEkleSil(g.sayfa, 3, 2, True))
    assert _kesme(pencere)[0] == (13,)
    assert g.sayfa_sinirlari_ver().satirlar[0] == (13, True)    # önbellek olayla düştü


def test_sayfa_sonlari_kapaliyken_hesap_yapilmaz(pencere, monkeypatch):
    g = pencere.izgara()
    cagri = []
    import tabcel.model.sayfalama as sl
    gercek = sl.sayfa_sinirlari
    monkeypatch.setattr(sl, "sayfa_sinirlari", lambda *a, **k: cagri.append(1) or gercek(*a, **k))
    _resim(g)
    assert cagri == []                                          # kapalı: 100.000 satırda boşa hesap yok
    g.sayfa_sonlari_goster(True)
    _resim(g)
    _resim(g)
    assert len(cagri) == 1                                      # açık: önbellekten


# ---------------------------------------------------------------- şerit ve pencere
def test_serit_kesmeler_menusu_ve_sigdir_kutulari(pencere):
    e = pencere.eylemler
    pencere.sayfa_yapisi_degistir(sigdir_yukseklik=True)
    assert pencere.izgara().sayfa.sayfa_yapisi.sigdir_yukseklik
    pencere.sayfa_yapisi_degistir(sayfa_sirasi="sag_sonra_asagi")
    pencere._eylem_durumlari()
    assert e["sira_sag"].isChecked() and not e["sira_asagi"].isChecked()


def test_sayfa_yapisi_penceresi_yeni_alanlar(app):
    y = SayfaYapisi(sigdir_yukseklik=True, sayfa_sirasi="sag_sonra_asagi", satir_kesmeleri=(5,))
    d = SayfaYapisiPenceresi(y)
    assert d.sigdir_yuk.isChecked() and d.sira.currentData() == "sag_sonra_asagi" and not d.olcek.isEnabled()
    d.sigdir_yuk.setChecked(False)
    assert d.olcek.isEnabled()
    d._tamam()
    s = d.sonuc()
    assert not s.sigdir_yukseklik and s.sayfa_sirasi == "sag_sonra_asagi" and s.satir_kesmeleri == (5,)   # kesmeler korunur


def test_pdf_kesmeyi_uygular(pencere, tmp_path):
    g = pencere.izgara()
    onceki = yz.SayfaCizici(g.sayfa, g.yazdirma_yuksekligi, g.font()).dilimler()
    _git(pencere, 3, 1)
    pencere.eylemler["sayfa_sonu_ekle"].trigger()
    sonra = yz.SayfaCizici(g.sayfa, g.yazdirma_yuksekligi, g.font()).dilimler()
    assert len(sonra) == len(onceki) + 1 and sonra[0].satirlar == (1, 2)
    assert yz.pdf_yaz([g], str(tmp_path / "k.pdf")) is True


# ---------------------------------------------------------------- Opus bulguları (performans / çizim)
def test_baska_sayfanin_olayi_sinirlari_dusurmez(pencere):
    g = pencere.izgara()
    g.sayfa_sonlari_goster(True)
    ilk = g.sayfa_sinirlari_ver()
    pencere.kitap.sayfa_ekle()
    diger = pencere.kitap.sayfalar[-1]
    diger.ata(1, 1, Hucre("x"))                                 # başka sayfada düzenleme
    assert g._sb is not None and g.sayfa_sinirlari_ver() is ilk


def test_hucre_duzenleme_sinirlari_ertelenmis_yeniler(pencere):
    from PySide6.QtTest import QTest
    g = pencere.izgara()
    g.sayfa_sonlari_goster(True)
    g.sayfa_sinirlari_ver()
    onceki = g._sb
    g.hucre_gir(2, 1, "yeni")                                   # yazarken her tuşta hesap yok: eski değer kalır
    assert g._sb is onceki and g._sb_zamanlayici.isActive()
    QTest.qWait(g._SB_ERTELEME_MS + 150)
    assert g._sb is None or g._sb is not onceki                 # boşta kalınca yenilendi (ya da yeniden istenene dek düşmüş)
    g.sayfa_sinirlari_ver()
    assert g._sb is not None


def test_sayfa_sonlari_kapaliyken_hucre_olayi_zamanlayici_baslatmaz(pencere):
    g = pencere.izgara()
    g.hucre_gir(2, 1, "x")
    assert not g._sb_zamanlayici.isActive()


def test_cizgi_birlesik_hucrenin_ustunden_gecer(pencere):
    g = pencere.izgara()
    g.kilavuz_goster(False)
    g.sec((10, 1), (11, 2))                                    # 10-11. satır × A-B birleşimi; sayfa sonu 11. satırın önünde
    assert g.birlestir("birlestir", onayli=True)
    _git(pencere, 11, 3)
    pencere.eylemler["sayfa_sonu_ekle"].trigger()
    _git(pencere, 3, 3)                                         # etkin hücre çerçevesi çizgiyi örtmesin, kaydırma olmasın
    ust11 = g.hucre_dikdortgeni(12, 1).y() - g._yuk(11)         # 11. satırın üst kenarı (birleşimin içinde)
    x = g.hucre_dikdortgeni(10, 1).x() + 10
    assert _resim(g).pixelColor(x, ust11 - 1) == QColor("#404040")


def test_sigdir_acikken_sayfa_sonu_eklenince_durum_cubugunda_bilgi(pencere):
    pencere.sayfa_yapisi_degistir(sigdir_yukseklik=True)
    _git(pencere, 11, 1)
    pencere.eylemler["sayfa_sonu_ekle"].trigger()
    assert _kesme(pencere) == ((11,), ())                         # eklenir ama
    assert "yok sayılır" in pencere.statusBar().currentMessage()  # kullanıcı bilgilendirilir
