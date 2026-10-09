import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
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
    Izgara._pano_durumu = None
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
    # Faz 2 (kural 3): kanonik İngilizce saklanır; F2'de yine Türkçe görünür
    assert izgara.sayfa.hucre(8, 1).formul == "=SUM(A1:A5)"
    izgara.sec((8, 1))
    tus(izgara, Qt.Key_F2)
    assert izgara.focusWidget().text() == "=TOPLA(A1:A5)"


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
    assert metinler == ["Kes", "Kopyala", "Yapıştır", "Ekle", "Sil", "Gizle", "Göster",
                        "Sütun genişliği…", "Otomatik sığdır"]
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


# --- pano ---
def panoya_metin(metin):
    from PySide6.QtCore import QMimeData
    md = QMimeData()
    md.setText(metin)
    QApplication.clipboard().setMimeData(md)


def panoya_html(html, metin=""):
    from PySide6.QtCore import QMimeData
    md = QMimeData()
    md.setHtml(html)
    if metin:
        md.setText(metin)
    QApplication.clipboard().setMimeData(md)


def test_kopyala_uc_bicimde_panoya_yazar(izgara):
    izgara.sayfa.ata(1, 2, Hucre(2.5))
    izgara.sec((1, 1), (2, 2))
    tus(izgara, Qt.Key_C, Qt.ControlModifier)
    md = QApplication.clipboard().mimeData()
    assert md.text() == "1\t2,5\r\n2\t\r\n"
    assert "<table>" in md.html() and "2,5" in md.html()
    assert md.hasFormat(Izgara.MIME_HUCRELER)
    assert Izgara._pano_durumu["sayfa"] is izgara.sayfa and not Izgara._pano_durumu["kesildi"]


def test_kopyala_yapistir_deger_ve_formul(izgara):
    izgara.sayfa.ata(2, 2, Hucre(None, "=A1+A2"))
    izgara.sec((1, 1), (2, 2))
    izgara.kopyala()
    izgara.sec((7, 3))
    tus(izgara, Qt.Key_V, Qt.ControlModifier)
    assert izgara.sayfa.deger(7, 3) == 1.0 and izgara.sayfa.deger(8, 3) == 2.0
    assert izgara.sayfa.hucre(8, 4).formul == "=C7+C8"      # göreli başvurular (6, 2) kayar (Faz 2, 6c)
    assert izgara.sayfa.deger(1, 1) == 1.0                  # kaynak yerinde
    assert izgara.secim == Aralik(7, 3, 8, 4)               # yapıştırılan bölge seçilir
    izgara.geri_al()
    assert izgara.sayfa.deger(7, 3) is None and izgara.sayfa.hucre(8, 4) is None


def test_kes_yapistir_kaynagi_bosaltir_ve_tek_adimda_geri_alinir(izgara):
    izgara.sec((1, 1), (3, 1))
    izgara.kes()
    assert izgara.sayfa.deger(1, 1) == 1.0                  # yapıştırana kadar yerinde
    assert Izgara._pano_durumu["kesildi"]
    izgara.sec((1, 5))
    izgara.yapistir()
    assert [izgara.sayfa.deger(r, 5) for r in (1, 2, 3)] == [1.0, 2.0, 3.0]
    assert [izgara.sayfa.deger(r, 1) for r in (1, 2, 3)] == [None, None, None]
    assert Izgara._pano_durumu is None                      # bir kez yapıştırılır
    izgara.geri_al()                                        # tek adım
    assert [izgara.sayfa.deger(r, 1) for r in (1, 2, 3)] == [1.0, 2.0, 3.0]
    assert izgara.sayfa.deger(1, 5) is None
    izgara.yinele()
    assert izgara.sayfa.deger(1, 1) is None and izgara.sayfa.deger(1, 5) == 1.0


def test_kes_ikinci_yapistirma_kaynagi_tekrar_bosaltmaz(izgara):
    izgara.sec((1, 1))
    izgara.kes()
    izgara.sec((1, 5))
    izgara.yapistir()
    izgara.sayfa.ata(1, 1, Hucre("yeni"))
    izgara.sec((1, 6))
    izgara.yapistir()                                       # pano hâlâ geçerli; artık sıradan kopya
    assert izgara.sayfa.deger(1, 6) == 1.0 and izgara.sayfa.deger(1, 1) == "yeni"


def test_kes_ust_uste_biner_alan(izgara):
    izgara.sec((1, 1), (3, 1))
    izgara.kes()
    izgara.sec((2, 1))
    izgara.yapistir()
    assert [izgara.sayfa.deger(r, 1) for r in (1, 2, 3, 4)] == [None, 1.0, 2.0, 3.0]


def test_kes_sayfalar_arasi(izgara):
    s2 = Sayfa("S2")
    g2 = Izgara(s2, yigin=izgara.yigin)
    izgara.sec((1, 1), (2, 1))
    izgara.kes()
    g2.sec((4, 4))
    g2.yapistir()
    assert s2.deger(4, 4) == 1.0 and s2.deger(5, 4) == 2.0
    assert izgara.sayfa.deger(1, 1) is None
    izgara.geri_al()                                        # ortak yığın: ikisi birden geri gelir
    assert izgara.sayfa.deger(1, 1) == 1.0 and s2.deger(4, 4) is None


def test_baska_kaynaktan_metin_yapistir(izgara):
    izgara.sec((1, 1))
    izgara.kopyala()
    panoya_metin("Ürün\tFiyat\n\"Kalem\nİki\"\t1.234,5\n")
    assert Izgara._pano_durumu is None                      # dış değişiklik işareti kaldırır
    izgara.sec((10, 1))
    izgara.yapistir()
    assert izgara.sayfa.deger(10, 1) == "Ürün" and izgara.sayfa.deger(10, 2) == "Fiyat"
    assert izgara.sayfa.deger(11, 1) == "Kalem\nİki"
    assert izgara.sayfa.deger(11, 2) == 1234.5              # elle yazılmış gibi çözülür


def test_html_tablo_yapistir(izgara):
    panoya_html("<table><tr><td>a</td><td>1,5</td></tr><tr><td>b</td><td></td></tr></table>",
                "yanlış\tmetin")
    izgara.sec((10, 1))
    izgara.yapistir()                                       # tablo varsa HTML tercih edilir
    assert izgara.sayfa.deger(10, 1) == "a" and izgara.sayfa.deger(10, 2) == 1.5
    assert izgara.sayfa.deger(11, 1) == "b"


def test_tek_hucre_secime_yayilir(izgara):
    izgara.sec((1, 1))
    izgara.kopyala()
    izgara.sec((10, 5), (12, 6))
    izgara.yapistir()
    assert all(izgara.sayfa.deger(r, c) == 1.0 for r in (10, 11, 12) for c in (5, 6))


def test_bos_pano_yapistirma_bir_sey_yapmaz(izgara):
    panoya_metin("")
    izgara.sec((10, 1))
    izgara.yapistir()
    assert not izgara.yigin.geri_alinabilir()


def test_yapistirma_sinir_asimi_uyari(izgara):
    from tabcel.model.adres import MAX_ROW
    izgara.sec((1, 1), (3, 1))
    izgara.kopyala()
    izgara.sec((MAX_ROW - 1, 1))
    uyarilar = []
    izgara.uyari.connect(uyarilar.append)
    izgara.yapistir()
    assert uyarilar and izgara.sayfa.deger(MAX_ROW - 1, 1) is None


def test_tam_sutun_kopyalama_sinirli(izgara):
    izgara._sutun_sec(1, False)
    izgara.kopyala()
    assert Izgara._pano_durumu["aralik"] == Aralik(1, 1, 10, 1)
    assert QApplication.clipboard().text().count("\r\n") == 10


def test_esc_isareti_kaldirir(izgara):
    izgara.sec((1, 1))
    izgara.kopyala()
    tus(izgara, Qt.Key_Escape)
    assert Izgara._pano_durumu is None


def test_karinca_cercevesi_cizilir(izgara, tmp_path):
    izgara.sec((1, 1), (3, 1))
    izgara.kes()
    izgara.sec((8, 8))
    img = izgara.viewport().grab()
    assert not img.isNull()


def test_hucre_menusu(izgara):
    izgara.kopyala()
    d = izgara.hucre_dikdortgeni(4, 2)
    m = izgara.hucre_menusu(d.center())
    assert [a.text() for a in m.actions() if not a.isSeparator()] == \
        ["Kes", "Kopyala", "Yapıştır", "İçeriği temizle"]
    assert izgara.aktif == (4, 2)                           # seçim dışına tıklayınca seçilir
    izgara.sec((1, 1), (5, 1))
    izgara.hucre_menusu(izgara.hucre_dikdortgeni(3, 1).center())
    assert izgara.secim == Aralik(1, 1, 5, 1)               # seçim içindeyse bozulmaz
    assert izgara.hucre_menusu(QPoint(5, 5)) is None


def test_hucre_menusu_temizle(izgara):
    izgara.sec((1, 1), (2, 1))
    m = izgara.hucre_menusu(izgara.hucre_dikdortgeni(1, 1).center())
    next(a for a in m.actions() if a.text() == "İçeriği temizle").trigger()
    assert izgara.sayfa.deger(1, 1) is None and izgara.sayfa.deger(2, 1) is None


def test_duzenleyicide_ctrl_c_metin_kopyalar_ve_isareti_kaldirir(izgara):
    izgara.sec((1, 1))
    izgara.kopyala()
    izgara.duzenle_baslat(None)
    e = izgara.focusWidget()
    e.selectAll()
    QTest.keyClick(e, Qt.Key_C, Qt.ControlModifier)         # düzenleyicinin kendi kopyalaması
    izgara.duzenlemeyi_bitir(False)
    assert QApplication.clipboard().text() == "1"
    assert Izgara._pano_durumu is None                      # hücre panosu artık geçerli değil


# --- taşan metin, #### ---
def yerlesim(g):
    from PySide6.QtGui import QFontMetrics
    sut = list(g._gorunen_sutunlar())
    sat = list(g._gorunen_satirlar())
    return g._yerlesim(sut, sat, QFontMetrics(g._yazi_tipi()), g._z(4))


def metin_bul(metinler, metin):
    return next(m for m in metinler if m[3] == metin)


def test_uzun_metin_bos_komsuya_tasar(izgara):
    izgara.sayfa.ata(12, 1, Hucre("çok uzun bir metin burada taşıyor"))
    metinler, tasma = yerlesim(izgara)
    kirp = metin_bul(metinler, "çok uzun bir metin burada taşıyor")[0]
    assert kirp.width() > izgara.sayfa.genislik(1) * 2
    assert (12, 1) in tasma and (12, 2) in tasma


def test_dolu_komsu_tasmayi_keser(izgara):
    izgara.sayfa.ata(12, 1, Hucre("çok uzun bir metin burada taşıyor"))
    izgara.sayfa.ata(12, 3, Hucre("engel"))
    metinler, tasma = yerlesim(izgara)
    kirp = metin_bul(metinler, "çok uzun bir metin burada taşıyor")[0]
    assert kirp.width() == izgara.sayfa.genislik(1) * 2 - 1       # yalnızca B'ye kadar
    assert (12, 2) not in tasma and (12, 1) in tasma


def test_kisa_metin_tasmaz(izgara):
    izgara.sayfa.ata(12, 1, Hucre("kısa"))
    metinler, tasma = yerlesim(izgara)
    assert (12, 1) not in tasma
    assert metin_bul(metinler, "kısa")[0].width() == izgara.sayfa.genislik(1) - 1


def test_sayi_tasmaz_sigmazsa_kisaltilir_ya_da_diyez(izgara):
    izgara.sayfa.sutun_genislik[1] = 30
    izgara.sayfa.ata(12, 1, Hucre(3.14159265))
    izgara.sayfa.ata(13, 1, Hucre(123456789.0))
    izgara.sayfa.ata(14, 1, Hucre(1.0))
    metinler, tasma = yerlesim(izgara)
    kisa = [m[3] for m in metinler if m[1].top() == izgara.hucre_dikdortgeni(12, 1).top()]
    assert kisa and kisa[0] != "3,14159265" and kisa[0].startswith("3")
    diyez = [m[3] for m in metinler if m[1].top() == izgara.hucre_dikdortgeni(13, 1).top()]
    assert diyez and set(diyez[0]) <= set("#E+0123456789,")
    assert "1" in [m[3] for m in metinler if m[1].top() == izgara.hucre_dikdortgeni(14, 1).top()]
    assert not any(r in (12, 13, 14) for r, _ in tasma)            # sayılar taşmaz


def test_cok_dar_sutunda_diyez(izgara):
    izgara.sayfa.sutun_genislik[1] = 14
    izgara.sayfa.ata(12, 1, Hucre(123456789.0))
    metinler, _ = yerlesim(izgara)
    t = [m[3] for m in metinler if m[1].top() == izgara.hucre_dikdortgeni(12, 1).top()][0]
    assert t and set(t) == {"#"}


def test_satir_sonu_tek_satir_gorunur(izgara):
    izgara.sayfa.ata(12, 1, Hucre("a\nb"))
    metinler, _ = yerlesim(izgara)
    assert metin_bul(metinler, "ab")


def test_mantiksal_ortalanir(izgara):
    izgara.sayfa.ata(12, 1, Hucre(True))
    metinler, _ = yerlesim(izgara)
    m = metin_bul(metinler, "DOĞRU")
    assert m[2] == Qt.AlignHCenter


def test_gizli_sutun_tasmada_atlanir(izgara):
    izgara.sayfa.ata(12, 1, Hucre("çok uzun bir metin burada taşıyor"))
    izgara.sayfa.gizli_sutun.add(2)
    metinler, tasma = yerlesim(izgara)
    kirp = metin_bul(metinler, "çok uzun bir metin burada taşıyor")[0]
    assert kirp.width() > 64                                       # C'ye kadar taşar


def test_alt_enter_hucre_icinde_yeni_satir(izgara):
    izgara.sec((12, 1))
    yaz(izgara, "ilk")
    e = izgara.focusWidget()
    QTest.keyClick(e, Qt.Key_Return, Qt.AltModifier)
    QTest.keyClicks(e, "ikinci")
    assert izgara.duzenleniyor()                                   # onaylanmadı
    QTest.keyClick(e, Qt.Key_Return)
    assert izgara.sayfa.deger(12, 1) == "ilk\nikinci"
    izgara.sec((12, 1))
    tus(izgara, Qt.Key_F2)
    assert izgara.focusWidget().text() == "ilk\nikinci"            # düzenlemede korunur
    izgara.duzenlemeyi_bitir(False)


def test_taşma_ile_cizim_hatasiz(izgara):
    izgara.sayfa.ata(12, 1, Hucre("çok uzun bir metin burada taşıyor"))
    izgara.sayfa.sutun_genislik[2] = 14
    izgara.sayfa.ata(13, 1, Hucre(123456789.0))
    assert not izgara.viewport().grab().isNull()


# --- çoklu aralık (Ctrl+tık) ---
def tikla(g, satir, sutun, mod=Qt.NoModifier):
    QTest.mouseClick(g.viewport(), Qt.LeftButton, mod, g.hucre_dikdortgeni(satir, sutun).center())


def test_ctrl_tik_aralik_ekler(izgara):
    tikla(izgara, 2, 1)
    tikla(izgara, 4, 3, Qt.ControlModifier)
    tikla(izgara, 6, 2, Qt.ControlModifier)
    assert izgara.secimler == [Aralik(2, 1, 2, 1), Aralik(4, 3, 4, 3), Aralik(6, 2, 6, 2)]
    assert izgara.aktif == (6, 2)
    assert izgara.secili_mi(2, 1) and izgara.secili_mi(4, 3) and not izgara.secili_mi(3, 1)


def test_ctrl_surukleme_aralik_ekler(izgara):
    tikla(izgara, 1, 1)
    w = izgara.viewport()
    bas = izgara.hucre_dikdortgeni(4, 3).center()
    bit = izgara.hucre_dikdortgeni(6, 4).center()
    QTest.mousePress(w, Qt.LeftButton, Qt.ControlModifier, bas)
    QTest.mouseMove(w, bit)
    QTest.mouseRelease(w, Qt.LeftButton, Qt.ControlModifier, bit)
    assert izgara.secimler == [Aralik(1, 1, 1, 1), Aralik(4, 3, 6, 4)]


def test_duz_tik_ve_klavye_coklu_secimi_kaldirir(izgara):
    tikla(izgara, 2, 1)
    tikla(izgara, 4, 3, Qt.ControlModifier)
    assert len(izgara.secimler) == 2
    tus(izgara, Qt.Key_Down)
    assert len(izgara.secimler) == 1
    tikla(izgara, 2, 1)
    tikla(izgara, 4, 3, Qt.ControlModifier)
    tikla(izgara, 5, 5)
    assert izgara.secimler == [Aralik(5, 5, 5, 5)]


def test_shift_tik_son_araligi_genisletir_oncekiler_kalir(izgara):
    tikla(izgara, 1, 1)
    tikla(izgara, 4, 3, Qt.ControlModifier)
    tikla(izgara, 6, 4, Qt.ShiftModifier)
    assert izgara.secimler == [Aralik(1, 1, 1, 1), Aralik(4, 3, 6, 4)]


def test_ctrl_baslik_tik_sutun_ekler(izgara):
    d1 = izgara.hucre_dikdortgeni(1, 1)
    d3 = izgara.hucre_dikdortgeni(1, 3)
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(d1.center().x(), 5))
    QTest.mouseClick(izgara.viewport(), Qt.LeftButton, Qt.ControlModifier, QPoint(d3.center().x(), 5))
    assert izgara.secimler == [Aralik(1, 1, MAX_ROW, 1), Aralik(1, 3, MAX_ROW, 3)]
    assert izgara.secili_mi(7, 3) and not izgara.secili_mi(7, 2)


def test_delete_tum_secili_araliklari_temizler(izgara):
    tikla(izgara, 1, 1)
    tikla(izgara, 3, 1, Qt.ControlModifier)
    tus(izgara, Qt.Key_Delete)
    assert izgara.sayfa.deger(1, 1) is None and izgara.sayfa.deger(3, 1) is None
    assert izgara.sayfa.deger(2, 1) == 2.0                  # arada seçilmeyen kalır
    izgara.geri_al()                                        # tek adım
    assert izgara.sayfa.deger(1, 1) == 1.0 and izgara.sayfa.deger(3, 1) == 3.0


def test_coklu_secimde_kopyalama_reddedilir(izgara):
    from PySide6.QtCore import QMimeData
    md = QMimeData()
    md.setText("onceki")
    QApplication.clipboard().setMimeData(md)
    tikla(izgara, 1, 1)
    tikla(izgara, 3, 1, Qt.ControlModifier)
    uyarilar = []
    izgara.uyari.connect(uyarilar.append)
    izgara.kopyala()
    izgara.kes()
    assert len(uyarilar) == 2
    assert QApplication.clipboard().text() == "onceki" and Izgara._pano_durumu is None


def test_coklu_secim_sinyali_ve_cizim(izgara):
    secimler = []
    izgara.secimDegisti.connect(secimler.append)
    tikla(izgara, 1, 1)
    tikla(izgara, 1, 1, Qt.ControlModifier)                 # aynı hücre: birincil değişmez ama ek eklendi
    assert len(secimler) >= 1
    tikla(izgara, 5, 5, Qt.ControlModifier)
    assert not izgara.viewport().grab().isNull()


def test_ozet_tum_araliklari_kapsar(izgara):
    from tabcel.ui.window import Pencere
    from tabcel.model.sayfa import CalismaKitabi
    k = CalismaKitabi()
    for r in range(1, 6):
        k.sayfalar[0].ata(r, 1, Hucre(float(r)))
    p = Pencere(k)
    p.show()
    g = p.izgara()
    g.sec((1, 1))
    tikla(g, 5, 1, Qt.ControlModifier)
    t = p.ozet_etiketi.text()
    assert "Sayım: 2" in t and "Toplam: 6" in t and "Ortalama: 3" in t
    g.sec((1, 1), (3, 1))
    tikla(g, 2, 1, Qt.ControlModifier)                      # üst üste binen: hücre bir kez sayılır
    assert "Sayım: 3" in p.ozet_etiketi.text()


# --- artımlı (piksel kaydırmalı) dikey kaydırma ---
def kaydirma_kaydedici(g):
    cagrilar = []
    g.viewport().scroll = lambda dx, dy, ar: cagrilar.append((dx, dy, ar))
    return cagrilar


def test_kucuk_kaydirma_pikselleri_kaydirir(izgara):
    cagrilar = kaydirma_kaydedici(izgara)
    vs = izgara.verticalScrollBar()
    vs.setValue(3)
    assert len(cagrilar) == 1
    dx, dy, ar = cagrilar[0]
    assert (dx, dy) == (0, -3 * 20)                       # 3 satır yukarı
    assert ar.top() == izgara._baslik_y()                  # sütun başlıkları kaymaz
    vs.setValue(1)
    assert cagrilar[-1][:2] == (0, 2 * 20)                 # 2 satır geri: aşağı


def test_kaydirma_gizli_satirlari_piksel_hesabina_katmaz(izgara):
    izgara.sayfa.gizli_satir.update({2, 3})
    cagrilar = kaydirma_kaydedici(izgara)
    izgara.verticalScrollBar().setValue(4)                 # satır 1,2,3,4 geçildi; 2 ve 3 gizli
    assert cagrilar[-1][1] == -(20 + 0 + 0 + 20)


def test_kaydirma_yakinlastirmada_piksel_carpanli(izgara):
    izgara.yakinlastir(2.0)
    cagrilar = kaydirma_kaydedici(izgara)
    izgara.verticalScrollBar().setValue(2)
    assert cagrilar[-1][1] == -2 * 40


def test_buyuk_sicrama_piksel_kaydirmaz_tam_boyar(izgara):
    cagrilar = kaydirma_kaydedici(izgara)
    izgara.verticalScrollBar().setValue(5000)
    assert cagrilar == []                                  # görünen satır sayısından büyük adım


def test_ayni_deger_kaydirma_yapmaz(izgara):
    cagrilar = kaydirma_kaydedici(izgara)
    izgara.verticalScrollBar().setValue(0)
    assert cagrilar == []


def test_scroll_contents_by_tum_viewport_yenilemez(izgara):
    izgara.scrollContentsBy(0, 10)          # Qt varsayılanı tüm viewport'u geçersiz kılardı; boş olmalı
    izgara.scrollContentsBy(7, 0)


def test_seçim_boyama_baslik_ekran_disi_satir_olsa_da_guncellenir(izgara):
    """Seçili aralığın satırları ekran dışına kaydığında sütun başlığı vurgusu yine temizlenmeli."""
    izgara.sec((1, 2))
    izgara.verticalScrollBar().setValue(30)               # (1,2) artık görünmüyor
    guncellenen = []
    vp = izgara.viewport()
    vp.update = lambda *a: guncellenen.append(a)
    izgara.sec((35, 4))
    sutun_basligi_icin = [a[0] for a in guncellenen if a and hasattr(a[0], "top") and a[0].top() == 0]
    assert sutun_basligi_icin, "eski seçimin sütun başlığı yeniden boyanmadı"


def test_boyutlu_viewport_secim_boyama_hatasiz_ve_tam_cizimle_ayni(izgara):
    izgara.sec((2, 1), (5, 3))
    izgara.sec((8, 2))
    izgara.sec((1, 1), (2, 2))
    assert not izgara.viewport().grab().isNull()


# --- ek kısayol / klavye kapsamı ---
def test_page_down_up_sayfa_kadar_gider(izgara):
    sayfa = izgara.verticalScrollBar().pageStep()
    assert sayfa >= 5
    tus(izgara, Qt.Key_PageDown)
    assert izgara.aktif == (1 + sayfa, 1)
    assert izgara.ilk_satir > 1                               # görünüm de kaydı
    tus(izgara, Qt.Key_PageUp)
    assert izgara.aktif == (1, 1)
    assert izgara.ilk_satir == 1


def test_shift_page_down_secimi_genisletir(izgara):
    sayfa = izgara.verticalScrollBar().pageStep()
    tus(izgara, Qt.Key_PageDown, Qt.ShiftModifier)
    assert izgara.aktif == (1, 1)
    assert izgara.secim == Aralik(1, 1, 1 + sayfa, 1)


def test_home_satir_basina_gider(izgara):
    izgara.sec((5, 4))
    tus(izgara, Qt.Key_Home)
    assert izgara.aktif == (5, 1)
    tus(izgara, Qt.Key_Right, Qt.ShiftModifier)
    tus(izgara, Qt.Key_Home, Qt.ShiftModifier)                # Shift+Home: satır başına kadar seçer
    assert izgara.secim.ilk_sutun == 1


def test_ctrl_shift_rakam_gizli_satir_sutun_gosterir(izgara):
    izgara.sayfa.gizli_satir.add(2)
    izgara.sayfa.gizli_sutun.add(2)
    izgara.sec((1, 1), (3, 3))
    tus(izgara, Qt.Key_ParenLeft, Qt.ControlModifier | Qt.ShiftModifier)
    assert 2 not in izgara.sayfa.gizli_satir and 2 in izgara.sayfa.gizli_sutun
    tus(izgara, Qt.Key_ParenRight, Qt.ControlModifier | Qt.ShiftModifier)
    assert not izgara.sayfa.gizli_sutun
    izgara.geri_al(); izgara.geri_al()
    assert 2 in izgara.sayfa.gizli_satir and 2 in izgara.sayfa.gizli_sutun


def test_ctrl_artı_tam_satir_secimde_satir_ekler(izgara):
    izgara._satir_sec(2, False)
    tus(izgara, Qt.Key_Plus, Qt.ControlModifier | Qt.ShiftModifier)
    assert izgara.sayfa.deger(2, 1) is None and izgara.sayfa.deger(3, 1) == 2.0


def test_ctrl_eksi_hucre_seciliyken_hicbir_sey_silmez(izgara):
    izgara.sec((2, 1))
    tus(izgara, Qt.Key_Minus, Qt.ControlModifier)
    assert izgara.sayfa.deger(2, 1) == 2.0 and izgara.sayfa.deger(3, 1) == 3.0


def test_alternatif_pano_kisayollari(izgara):
    izgara.sec((1, 1), (2, 1))
    tus(izgara, Qt.Key_Insert, Qt.ControlModifier)             # Ctrl+Insert = kopyala
    izgara.sec((8, 5))
    tus(izgara, Qt.Key_Insert, Qt.ShiftModifier)               # Shift+Insert = yapıştır
    assert izgara.sayfa.deger(8, 5) == 1.0 and izgara.sayfa.deger(9, 5) == 2.0
    izgara.sec((3, 1))
    tus(izgara, Qt.Key_Delete, Qt.ShiftModifier)               # Shift+Delete = kes
    assert Izgara._pano_durumu["kesildi"] and izgara.sayfa.deger(3, 1) == 3.0   # yapıştırılana dek yerinde
    izgara.sec((12, 5))
    tus(izgara, Qt.Key_Insert, Qt.ShiftModifier)
    assert izgara.sayfa.deger(12, 5) == 3.0 and izgara.sayfa.deger(3, 1) is None


def test_shift_delete_hucreyi_silmez_ctrl_delete_gibi_davranmaz(izgara):
    izgara.sec((2, 1))
    tus(izgara, Qt.Key_Delete, Qt.ShiftModifier)
    assert izgara.sayfa.deger(2, 1) == 2.0                    # silinmedi; yalnızca kesildi


def test_satir_otomatik_sigdir_varsayilana_dondurur(izgara):
    izgara.sayfa.satir_yukseklik[2] = 55
    izgara.sec((2, 1))
    izgara.satir_otomatik_sigdir()
    assert izgara.sayfa.yukseklik(2) == 20
    izgara.geri_al()
    assert izgara.sayfa.yukseklik(2) == 55


def test_fare_surukleme_alt_kenarin_otesinde_secimi_uzatir(izgara):
    w = izgara.viewport()
    bas = izgara.hucre_dikdortgeni(2, 1).center()
    QTest.mousePress(w, Qt.LeftButton, Qt.NoModifier, bas)
    QTest.mouseMove(w, QPoint(bas.x(), w.height() + 30))      # görünür alanın altı
    QTest.mouseRelease(w, Qt.LeftButton, Qt.NoModifier, QPoint(bas.x(), w.height() + 30))
    assert izgara.secim.son_satir > 2 and izgara.aktif == (2, 1)


def test_yakinlastirma_sinyali(izgara):
    degerler = []
    izgara.yakinlastirmaDegisti.connect(degerler.append)
    izgara.yakinlastir(1.5)
    izgara.yakinlastir(1.5)                                   # aynı değer: sinyal yok
    izgara.yakinlastir(0.05)                                  # alt sınır 0.1
    assert degerler == [1.5, 0.1]


# --- Opus gözden geçirmesi: K1 (DOĞRU ↔ 1), K3 (kes + yapısal değişiklik) ---
def test_k1_bire_dogru_yazilabilir(izgara):
    izgara.sayfa.ata(12, 1, Hucre(1.0))
    izgara.hucre_gir(12, 1, "DOĞRU")
    assert izgara.sayfa.deger(12, 1) is True
    izgara.hucre_gir(12, 1, "0")
    izgara.hucre_gir(12, 1, "YANLIŞ")
    assert izgara.sayfa.deger(12, 1) is False


def test_k3_kes_sonra_satir_ekle_isareti_iptal_eder(izgara):
    izgara.sayfa.ata(1, 6, Hucre("v1")); izgara.sayfa.ata(2, 6, Hucre("v2")); izgara.sayfa.ata(3, 6, Hucre("v3"))
    izgara.sec((1, 6), (3, 6))
    izgara.kes()
    izgara._satir_sec(1, False)
    izgara.satirlari_ekle()                                   # kaynağın yeri kaydı
    assert Izgara._pano_durumu is None                        # kes modu iptal
    izgara.sec((1, 8))
    izgara.yapistir()                                         # artık sıradan kopya: hiçbir hücre silinmez
    assert [izgara.sayfa.deger(r, 6) for r in (2, 3, 4)] == ["v1", "v2", "v3"]
    assert [izgara.sayfa.deger(r, 8) for r in (1, 2, 3)] == ["v1", "v2", "v3"]


def test_k3_kes_sonra_kaynak_duzenlenirse_iptal(izgara):
    izgara.sec((1, 1))
    izgara.kes()
    izgara.hucre_gir(4, 4, "baska bir hucre")
    assert Izgara._pano_durumu is None


def test_k3_kes_sonra_boyutlandirma_kes_modunu_bozmaz(izgara):
    izgara.sec((1, 1))
    izgara.kes()
    izgara.sec((1, 2))
    izgara.sutun_genisligi_ayarla(90)
    assert Izgara._pano_durumu is not None and Izgara._pano_durumu["kesildi"]
    izgara.sec((8, 5))
    izgara.yapistir()
    assert izgara.sayfa.deger(8, 5) == 1.0 and izgara.sayfa.deger(1, 1) is None


def test_k3_kopya_isareti_birden_cok_yapistirmada_kalir(izgara):
    izgara.sec((1, 1))
    izgara.kopyala()
    izgara.sec((8, 5)); izgara.yapistir()
    assert Izgara._pano_durumu is not None                    # Excel gibi: kopya işareti kalır
    izgara.sec((9, 5)); izgara.yapistir()
    assert izgara.sayfa.deger(8, 5) == 1.0 and izgara.sayfa.deger(9, 5) == 1.0


def test_k3_geri_al_pano_isaretini_iptal_eder(izgara):
    izgara.hucre_gir(4, 4, "x")
    izgara.sec((1, 1))
    izgara.kes()
    izgara.geri_al()
    assert Izgara._pano_durumu is None


def test_koru_odak_kaybinda_sifirlanir(izgara):
    from PySide6.QtGui import QFocusEvent
    izgara._koru = True
    izgara.focusOutEvent(QFocusEvent(QEvent.FocusOut))
    assert izgara._koru is False
