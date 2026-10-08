import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import MAX_COL, MAX_ROW, Aralik
from tabcel.model.sayfa import Hucre, Sayfa
from tabcel.ui.grid import Izgara, goster


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def izgara(app):
    s = Sayfa("S")
    for r in range(1, 6):
        s.ata(r, 1, Hucre(float(r)))
    s.ata(10, 3, Hucre("x"))
    g = Izgara(s)
    g.resize(600, 400)
    g.show()
    return g


def tus(g, k, m=Qt.NoModifier):
    QTest.keyClick(g, k, m)


def test_goster():
    assert goster(None) == ""
    assert goster(3.0) == "3"
    assert goster(2.5) == "2,5"
    assert goster(True) == "DOĞRU"
    assert goster("a") == "a"


def test_baslangic(izgara):
    assert izgara.aktif == (1, 1)
    assert izgara.secim == Aralik(1, 1, 1, 1)


def test_ok_tuslari_sinirda_kalir(izgara):
    tus(izgara, Qt.Key_Up)
    tus(izgara, Qt.Key_Left)
    assert izgara.aktif == (1, 1)
    tus(izgara, Qt.Key_Down)
    tus(izgara, Qt.Key_Right)
    assert izgara.aktif == (2, 2)


def test_shift_ok_secimi_genisletir(izgara):
    tus(izgara, Qt.Key_Down, Qt.ShiftModifier)
    tus(izgara, Qt.Key_Right, Qt.ShiftModifier)
    assert izgara.aktif == (1, 1)
    assert izgara.secim == Aralik(1, 1, 2, 2)
    tus(izgara, Qt.Key_Down)
    assert izgara.secim == Aralik(2, 1, 2, 1)


def test_ctrl_ok_veri_blogu(izgara):
    tus(izgara, Qt.Key_Down, Qt.ControlModifier)
    assert izgara.aktif == (5, 1)             # bloğun sonu
    tus(izgara, Qt.Key_Down, Qt.ControlModifier)
    assert izgara.aktif == (MAX_ROW, 1)       # altında dolu yok → kenar
    tus(izgara, Qt.Key_Up, Qt.ControlModifier)
    assert izgara.aktif == (5, 1)
    tus(izgara, Qt.Key_Up, Qt.ControlModifier)
    assert izgara.aktif == (1, 1)


def test_ctrl_home_end(izgara):
    tus(izgara, Qt.Key_End, Qt.ControlModifier)
    assert izgara.aktif == (10, 3)
    tus(izgara, Qt.Key_Home, Qt.ControlModifier)
    assert izgara.aktif == (1, 1)
    assert izgara.ilk_satir == 1 and izgara.ilk_sutun == 1


def test_ctrl_a_ve_bosluk(izgara):
    tus(izgara, Qt.Key_A, Qt.ControlModifier)
    assert izgara.secim == Aralik(1, 1, MAX_ROW, MAX_COL)
    tus(izgara, Qt.Key_Space, Qt.ControlModifier)
    assert izgara.secim == Aralik(1, 1, MAX_ROW, 1)
    tus(izgara, Qt.Key_Space, Qt.ShiftModifier)
    assert izgara.secim == Aralik(1, 1, 1, MAX_COL)


def test_enter_tab(izgara):
    tus(izgara, Qt.Key_Return)
    assert izgara.aktif == (2, 1)
    tus(izgara, Qt.Key_Tab)
    assert izgara.aktif == (2, 2)
    tus(izgara, Qt.Key_Backtab)
    assert izgara.aktif == (2, 1)
    tus(izgara, Qt.Key_Return, Qt.ShiftModifier)
    assert izgara.aktif == (1, 1)


def test_asagi_inince_kayar(izgara):
    for _ in range(60):
        tus(izgara, Qt.Key_Down)
    assert izgara.aktif == (61, 1)
    assert izgara.ilk_satir > 1
    assert izgara.hucre_dikdortgeni(61, 1) is not None


def test_sola_donunce_kayar(izgara):
    izgara.sec((200, 30))
    assert izgara.ilk_sutun > 1
    izgara.sec((1, 1))
    assert izgara.ilk_sutun == 1 and izgara.ilk_satir == 1


def test_fare_tiklama_ve_surukleme(izgara):
    d = izgara.hucre_dikdortgeni(3, 2)
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, d.center())
    assert izgara.aktif == (3, 2)
    d2 = izgara.hucre_dikdortgeni(5, 4)
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.ShiftModifier, d2.center())
    assert izgara.secim == Aralik(3, 2, 5, 4)


def test_baslik_tiklama(izgara):
    d = izgara.hucre_dikdortgeni(1, 3)
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(d.center().x(), 5))
    assert izgara.secim == Aralik(1, 3, MAX_ROW, 3)
    d = izgara.hucre_dikdortgeni(4, 1)
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(5, d.center().y()))
    assert izgara.secim == Aralik(4, 1, 4, MAX_COL)
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(5, 5))
    assert izgara.secim == Aralik(1, 1, MAX_ROW, MAX_COL)


def test_sinyaller(izgara):
    aktifler, secimler = [], []
    izgara.aktifDegisti.connect(lambda r, c: aktifler.append((r, c)))
    izgara.secimDegisti.connect(secimler.append)
    tus(izgara, Qt.Key_Down)
    tus(izgara, Qt.Key_Right, Qt.ShiftModifier)
    assert aktifler == [(2, 1)]
    assert secimler == [Aralik(2, 1, 2, 1), Aralik(2, 1, 2, 2)]


def test_cizim_hatasiz_ve_goruntu(izgara, tmp_path):
    izgara.sec((2, 1), (4, 3))
    img = izgara.viewport().grab()
    assert not img.isNull()
    img.save(str(tmp_path / "izgara.png"))


# --- düzenleme ---
def yaz(g, metin):
    """İlk karakter ızgaraya gider ve düzenleyiciyi açar; gerisi odaktaki düzenleyiciye."""
    QTest.keyClicks(g, metin[0])
    if len(metin) > 1:
        QTest.keyClicks(g.focusWidget(), metin[1:])


def test_yazarak_duzenle_enter(izgara):
    izgara.sec((8, 2))
    yaz(izgara, "12,5")
    assert izgara.duzenleniyor()
    tus(izgara.focusWidget(), Qt.Key_Return)
    assert not izgara.duzenleniyor()
    assert izgara.sayfa.deger(8, 2) == 12.5
    assert izgara.aktif == (9, 2)


def test_tab_ve_ok_onaylar(izgara):
    izgara.sec((8, 2))
    yaz(izgara, "a")
    tus(izgara.focusWidget(), Qt.Key_Tab)
    assert izgara.sayfa.deger(8, 2) == "a" and izgara.aktif == (8, 3)
    yaz(izgara, "b")
    tus(izgara.focusWidget(), Qt.Key_Up)
    assert izgara.sayfa.deger(8, 3) == "b" and izgara.aktif == (7, 3)


def test_esc_iptal(izgara):
    izgara.sec((1, 1))
    yaz(izgara, "zzz")
    tus(izgara.focusWidget(), Qt.Key_Escape)
    assert izgara.sayfa.deger(1, 1) == 1.0 and not izgara.duzenleniyor()


def test_f2_mevcut_icerik_ve_ok_imlec(izgara):
    izgara.sec((10, 3))
    tus(izgara, Qt.Key_F2)
    e = izgara.focusWidget()
    assert e.text() == "x"
    tus(e, Qt.Key_Left)                     # Düzenle modu: hücre değişmez
    assert izgara.aktif == (10, 3) and izgara.duzenleniyor()
    QTest.keyClicks(e, "y")
    tus(e, Qt.Key_Return)
    assert izgara.sayfa.deger(10, 3) == "yx"


def test_formul_saklanir(izgara):
    izgara.sec((8, 1))
    yaz(izgara, "=TOPLA(A1:A5)")
    tus(izgara.focusWidget(), Qt.Key_Return)
    assert izgara.sayfa.hucre(8, 1).formul == "=TOPLA(A1:A5)"


def test_delete_ve_geri_al(izgara):
    izgara.sec((1, 1), (5, 1))
    tus(izgara, Qt.Key_Delete)
    assert izgara.sayfa.kullanilan_aralik() == (10, 3, 10, 3)
    tus(izgara, Qt.Key_Z, Qt.ControlModifier)
    assert izgara.sayfa.deger(3, 1) == 3.0
    tus(izgara, Qt.Key_Y, Qt.ControlModifier)
    assert izgara.sayfa.deger(3, 1) is None


def test_tum_secim_delete_hizli(izgara):
    tus(izgara, Qt.Key_A, Qt.ControlModifier)
    tus(izgara, Qt.Key_Delete)
    assert izgara.sayfa.kullanilan_aralik() is None


def test_duzenleme_geri_al_tek_adim(izgara):
    izgara.sec((8, 2))
    yaz(izgara, "5")
    tus(izgara.focusWidget(), Qt.Key_Return)
    tus(izgara, Qt.Key_Z, Qt.ControlModifier)
    assert izgara.sayfa.deger(8, 2) is None


def test_degismeyen_giris_yigina_girmez(izgara):
    izgara.sec((1, 1))
    tus(izgara, Qt.Key_F2)
    tus(izgara.focusWidget(), Qt.Key_Return)
    assert not izgara.yigin.geri_alinabilir()


def test_duzenlerken_tiklama_dogru_hucreye_yazar(izgara):
    izgara.sec((8, 2))
    yaz(izgara, "q")
    d = izgara.hucre_dikdortgeni(12, 4)
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, d.center())
    assert izgara.sayfa.deger(8, 2) == "q"
    assert izgara.sayfa.deger(12, 4) is None and izgara.aktif == (12, 4)


def test_cift_tik_duzenler(izgara):
    d = izgara.hucre_dikdortgeni(10, 3)
    QTest.mouseDClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, d.center())
    assert izgara.duzenleniyor()
    izgara.duzenlemeyi_bitir(False)


def test_backspace_bos_baslatir(izgara):
    izgara.sec((1, 1))
    tus(izgara, Qt.Key_Backspace)
    assert izgara.duzenleniyor() and izgara.focusWidget().text() == ""
    tus(izgara.focusWidget(), Qt.Key_Return)
    assert izgara.sayfa.deger(1, 1) is None


def test_duzenleyici_yazdikca_genisler(izgara):
    izgara.sec((8, 2))
    yaz(izgara, "a")
    e = izgara.focusWidget()
    onceki = e.width()
    QTest.keyClicks(e, "uzun bir metin girildi")
    assert e.width() > onceki
    izgara.duzenlemeyi_bitir(False)


# --- boyutlandırma, ekle/sil, gizle ---
def sutun_kenari(g, sutun):
    d = g.hucre_dikdortgeni(1, sutun)
    return QPoint(d.right() + 1, 5)


def satir_kenari(g, satir):
    d = g.hucre_dikdortgeni(satir, 1)
    return QPoint(5, d.bottom() + 1)


def surukle(g, bas, bit):
    w = g.viewport()
    QTest.mousePress(w, Qt.LeftButton, Qt.NoModifier, bas)
    QTest.mouseMove(w, bit)
    QTest.mouseRelease(w, Qt.LeftButton, Qt.NoModifier, bit)


def test_sutun_kenarindan_boyutlandir_ve_geri_al(izgara):
    kenar = sutun_kenari(izgara, 2)
    surukle(izgara, kenar, kenar + QPoint(40, 0))
    assert izgara.sayfa.genislik(2) == 104
    izgara.geri_al()
    assert izgara.sayfa.genislik(2) == 64
    izgara.yinele()
    assert izgara.sayfa.genislik(2) == 104


def test_satir_kenarindan_boyutlandir(izgara):
    kenar = satir_kenari(izgara, 3)
    surukle(izgara, kenar, kenar + QPoint(0, 30))
    assert izgara.sayfa.yukseklik(3) == 50


def test_boyut_sinirlari(izgara):
    kenar = sutun_kenari(izgara, 2)
    surukle(izgara, kenar, kenar + QPoint(-500, 0))
    assert izgara.sayfa.genislik(2) == 3          # alt sınır, gizleme değil


def test_secili_sutunlar_birlikte_boyutlanir(izgara):
    izgara.sec((1, 2), (1, 4))
    izgara._sutun_sec(2, False)
    izgara.sec((1, 2), (1048576, 4), kaydir=False)
    kenar = sutun_kenari(izgara, 3)
    surukle(izgara, kenar, kenar + QPoint(20, 0))
    assert [izgara.sayfa.genislik(c) for c in (2, 3, 4, 5)] == [84, 84, 84, 64]


def test_baslik_disinda_boyutlandirma_olmaz(izgara):
    d = izgara.hucre_dikdortgeni(2, 2)
    surukle(izgara, QPoint(d.right() + 1, d.center().y()), QPoint(d.right() + 50, d.center().y()))
    assert izgara.sayfa.genislik(2) == 64


def test_cift_tik_otomatik_sigdir(izgara):
    izgara.sayfa.ata(1, 2, Hucre("çok uzun bir metin burada"))
    kenar = sutun_kenari(izgara, 2)
    QTest.mouseDClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, kenar)
    assert izgara.sayfa.genislik(2) > 100
    izgara.geri_al()
    assert izgara.sayfa.genislik(2) == 64


def test_otomatik_sigdir_bos_sutun_varsayilana_doner(izgara):
    izgara.sayfa.sutun_genislik[6] = 200
    izgara.sutun_otomatik_sigdir([6])
    assert izgara.sayfa.genislik(6) == 64


def test_genislik_yukseklik_ayarla(izgara):
    izgara.sec((1, 2), (1, 3))
    izgara.sutun_genisligi_ayarla(100)
    assert izgara.sayfa.genislik(2) == 100 and izgara.sayfa.genislik(3) == 100
    izgara.sec((2, 1), (4, 1))
    izgara.satir_yuksekligi_ayarla(30)
    assert [izgara.sayfa.yukseklik(r) for r in (2, 3, 4, 5)] == [30, 30, 30, 20]


def test_satir_ekle_sil(izgara):
    izgara._satir_sec(2, False)
    izgara.satirlari_ekle()
    assert izgara.sayfa.deger(3, 1) == 2.0 and izgara.sayfa.deger(2, 1) is None
    izgara.satirlari_sil()
    assert izgara.sayfa.deger(2, 1) == 2.0
    izgara.geri_al()
    assert izgara.sayfa.deger(3, 1) == 2.0


def test_secili_kadar_satir_eklenir(izgara):
    izgara.sec((2, 1), (4, 1))
    izgara._satir_sec(2, False)
    izgara.sec((2, 1), (4, MAX_COL), kaydir=False)
    izgara.satirlari_ekle()
    assert izgara.sayfa.deger(5, 1) == 2.0


def test_sutun_ekle_sil(izgara):
    izgara.sayfa.ata(1, 2, Hucre("b"))
    izgara._sutun_sec(2, False)
    izgara.sutunlari_ekle()
    assert izgara.sayfa.deger(1, 3) == "b" and izgara.sayfa.deger(1, 2) is None
    izgara.sutunlari_sil()
    assert izgara.sayfa.deger(1, 2) == "b"


def test_sayfa_sonunda_ekleme_reddedilir(izgara):
    from tabcel.model.adres import MAX_ROW
    izgara.sayfa.ata(MAX_ROW, 1, Hucre("son"))
    uyarilar = []
    izgara.uyari.connect(uyarilar.append)
    izgara._satir_sec(1, False)
    izgara.satirlari_ekle()
    assert uyarilar and izgara.sayfa.deger(MAX_ROW, 1) == "son"


def test_gizle_goster(izgara):
    izgara._sutun_sec(2, False)
    izgara.sutunlari_gizle()
    assert 2 in izgara.sayfa.gizli_sutun
    assert izgara.hucre_dikdortgeni(1, 2) is None        # çizilmez
    assert izgara.hucre_dikdortgeni(1, 3) is not None
    izgara.sec((1, 1), (1, 3))
    izgara.sutunlari_goster()
    assert not izgara.sayfa.gizli_sutun
    izgara._satir_sec(3, False)
    izgara.satirlari_gizle()
    assert izgara.hucre_dikdortgeni(3, 1) is None
    izgara.geri_al()
    assert izgara.hucre_dikdortgeni(3, 1) is not None


def test_gizli_hucreler_gezinmede_atlanir(izgara):
    izgara.sayfa.gizli_satir.add(2)
    izgara.sayfa.gizli_sutun.add(2)
    izgara.sec((1, 1))
    tus(izgara, Qt.Key_Down)
    assert izgara.aktif == (3, 1)
    tus(izgara, Qt.Key_Right)
    assert izgara.aktif == (3, 3)
    tus(izgara, Qt.Key_Left)
    assert izgara.aktif == (3, 1)
    tus(izgara, Qt.Key_Left)                       # kenarda kalır
    assert izgara.aktif == (3, 1)


def test_klavye_kisayollari_gizle_sil(izgara):
    izgara.sec((2, 1))
    tus(izgara, Qt.Key_9, Qt.ControlModifier)
    assert 2 in izgara.sayfa.gizli_satir
    tus(izgara, Qt.Key_0, Qt.ControlModifier)
    assert 1 in izgara.sayfa.gizli_sutun
    izgara._satir_sec(4, False)
    tus(izgara, Qt.Key_Minus, Qt.ControlModifier)
    assert izgara.sayfa.deger(4, 1) == 5.0          # 4. satır silindi, 5. yukarı kaydı


def test_baslik_menusu(izgara):
    d = izgara.hucre_dikdortgeni(1, 3)
    m = izgara.baslik_menusu(QPoint(d.center().x(), 5))
    metinler = [a.text() for a in m.actions() if not a.isSeparator()]
    assert metinler == ["Ekle", "Sil", "Gizle", "Göster", "Sütun genişliği…", "Otomatik sığdır"]
    assert izgara.secim.ilk_sutun == izgara.secim.son_sutun == 3     # tıklanan sütun seçildi
    goster_ = next(a for a in m.actions() if a.text() == "Göster")
    assert not goster_.isEnabled()
    d = izgara.hucre_dikdortgeni(2, 1)
    m = izgara.baslik_menusu(QPoint(5, d.center().y()))
    assert "Satır yüksekliği…" in [a.text() for a in m.actions()]
    assert izgara.baslik_menusu(izgara.hucre_dikdortgeni(2, 2).center()) is None


def test_baslik_menusu_ekle_calisir(izgara):
    d = izgara.hucre_dikdortgeni(4, 1)
    m = izgara.baslik_menusu(QPoint(5, d.center().y()))
    next(a for a in m.actions() if a.text() == "Ekle").trigger()
    assert izgara.sayfa.deger(4, 1) is None and izgara.sayfa.deger(5, 1) == 4.0


def test_secili_baslik_menusu_secimi_bozmaz(izgara):
    izgara.sec((1, 2), (1048576, 4), kaydir=False)
    d = izgara.hucre_dikdortgeni(1, 3)
    izgara.baslik_menusu(QPoint(d.center().x(), 5))
    assert (izgara.secim.ilk_sutun, izgara.secim.son_sutun) == (2, 4)


def test_imlec_kenarda_degisir(izgara):
    izgara._imlec_guncelle(sutun_kenari(izgara, 2))
    assert izgara.viewport().cursor().shape() == Qt.SplitHCursor
    izgara._imlec_guncelle(satir_kenari(izgara, 2))
    assert izgara.viewport().cursor().shape() == Qt.SplitVCursor
    izgara._imlec_guncelle(izgara.hucre_dikdortgeni(2, 2).center())
    assert izgara.viewport().cursor().shape() == Qt.ArrowCursor
