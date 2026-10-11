"""T2: klavye kısayolları — her biri için EXCEL davranışı (tablo). Gerçek klavye olayıyla (QTest) pencere/ızgara üzerinden.
Excel'den bilerek farklı olanlar `surec.md` → Kararlar'da ve `yardim.md` → "Excel'den Farklar"da; burada `FARK_` önekli testlerde
mevcut davranış sabitlenir."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.adres import MAX_COL, MAX_ROW, Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere

CTRL, SHIFT, ALT, YOK = Qt.ControlModifier, Qt.ShiftModifier, Qt.AltModifier, Qt.NoModifier


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def p(app, monkeypatch):
    for ad in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, ad, lambda *a, **k: QMessageBox.Ok)
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 6):                       # A1:C5 dolu blok
        for c in range(1, 4):
            s.ata(r, c, Hucre(float(r * 10 + c)))
    s.ata(1, 7, Hucre("uzak"))                  # G1: blokun ötesinde
    s.ata(9, 1, Hucre("alt"))                   # A9: blokun altında
    pencere = Pencere(k)
    pencere.resize(1000, 700)
    pencere.show()
    pencere.activateWindow()
    QTest.qWaitForWindowActive(pencere)
    pencere.izgara().setFocus()
    QApplication.processEvents()
    yield pencere
    pencere.degisti_mi = lambda: False
    pencere.close()


def tus(p, k, m=YOK):
    """Klavye olayı odaktaki öğeye gider (düzenleme açıksa hücre düzenleyicisine, değilse ızgaraya)."""
    g = p.izgara()
    QTest.keyClick(g.focusWidget() if g.duzenleniyor() and g.focusWidget() else g, k, m)
    QApplication.processEvents()


FARK = ("Excel'den fark: Tabcel'de etkin hücre seçim çapasıyla AYNI alan (`_aktif`); Excel'de ayrı. "
        "surec.md → T2 bulguları. Düzelince strict xfail kendiliğinden uyarır.")


def git(p, r, c):
    p.izgara().sec((r, c))


def aktif(p):
    return p.izgara().aktif


def secim(p):
    return p.izgara().secim


# ---------------------------------------------------------------- gezinme
@pytest.mark.parametrize("baslangic,tus_,beklenen", [
    ((1, 1), Qt.Key_Right, (1, 3)),               # blok sonu
    ((1, 3), Qt.Key_Right, (1, 7)),               # sonraki dolu hücre
    ((1, 7), Qt.Key_Right, (1, MAX_COL)),         # başka yok: sayfa kenarı
    ((1, 1), Qt.Key_Down, (5, 1)),
    ((5, 1), Qt.Key_Down, (9, 1)),
    ((9, 1), Qt.Key_Down, (MAX_ROW, 1)),
    ((5, 3), Qt.Key_Left, (5, 1)),
    ((5, 1), Qt.Key_Up, (1, 1)),
    ((3, 2), Qt.Key_Left, (3, 1)),                # blok içinden bloğun başına
    ((7, 5), Qt.Key_Down, (MAX_ROW, 5)),          # boş hücreden: sonraki dolu yok → kenar
    ((7, 1), Qt.Key_Up, (5, 1)),                  # boş hücreden yukarı: ilk dolu hücre
    ((1, 2), Qt.Key_Up, (1, 2)),                  # zaten kenarda
])
def test_ctrl_ok(p, baslangic, tus_, beklenen):
    git(p, *baslangic)
    tus(p, tus_, CTRL)
    assert aktif(p) == beklenen


def test_ctrl_shift_ok_secimi_blok_sonuna_genisletir_capa_sabit(p):
    git(p, 1, 1)
    tus(p, Qt.Key_Right, CTRL | SHIFT)
    assert secim(p) == Aralik(1, 1, 1, 3) and aktif(p) == (1, 1)
    tus(p, Qt.Key_Down, CTRL | SHIFT)                         # genişletme çapadan sürer: 1,1 → 5,3
    assert secim(p) == Aralik(1, 1, 5, 3) and aktif(p) == (1, 1)
    tus(p, Qt.Key_Right, CTRL | SHIFT)                        # uç (5,3)'ten sürer: 5. satırda sağda dolu yok → kenar
    assert secim(p) == Aralik(1, 1, 5, MAX_COL)


def test_ctrl_shift_yukari_sola(p):
    git(p, 5, 3)
    tus(p, Qt.Key_Up, CTRL | SHIFT)
    assert secim(p) == Aralik(1, 3, 5, 3) and aktif(p) == (5, 3)
    tus(p, Qt.Key_Left, CTRL | SHIFT)
    assert secim(p) == Aralik(1, 1, 5, 3)


def test_shift_ok_bir_hucre_genisletir(p):
    git(p, 2, 2)
    tus(p, Qt.Key_Right, SHIFT)
    tus(p, Qt.Key_Down, SHIFT)
    assert secim(p) == Aralik(2, 2, 3, 3) and aktif(p) == (2, 2)


def test_ctrl_home_ctrl_end(p):
    git(p, 4, 2)
    tus(p, Qt.Key_End, CTRL)
    assert aktif(p) == (9, 7)                                 # kullanılan alanın son satırı × son sütunu
    tus(p, Qt.Key_Home, CTRL)
    assert aktif(p) == (1, 1)


def test_ctrl_shift_home_end_secer(p):
    git(p, 3, 2)
    tus(p, Qt.Key_End, CTRL | SHIFT)
    assert secim(p) == Aralik(3, 2, 9, 7)
    git(p, 3, 2)
    tus(p, Qt.Key_Home, CTRL | SHIFT)
    assert secim(p) == Aralik(1, 1, 3, 2)


def test_home_satir_basina(p):
    git(p, 4, 3)
    tus(p, Qt.Key_Home)
    assert aktif(p) == (4, 1)


def test_ok_tuslari_ve_tab_enter_gezinmesi(p):
    git(p, 2, 2)
    tus(p, Qt.Key_Tab)
    assert aktif(p) == (2, 3)
    tus(p, Qt.Key_Tab, SHIFT)
    assert aktif(p) == (2, 2)
    tus(p, Qt.Key_Return)
    assert aktif(p) == (3, 2)
    tus(p, Qt.Key_Return, SHIFT)
    assert aktif(p) == (2, 2)


@pytest.mark.xfail(strict=True, reason=FARK)
def test_enter_secim_icinde_dolasir(p):
    """Excel: çok hücreli seçim varken Enter/Tab seçimin İÇİNDE ilerler."""
    git(p, 1, 1)
    p.izgara().sec((1, 1), (2, 2))
    tus(p, Qt.Key_Return)
    assert aktif(p) == (2, 1) and secim(p) == Aralik(1, 1, 2, 2)
    tus(p, Qt.Key_Return)                                     # sütun sonu: bir sonraki sütunun başı
    assert aktif(p) == (1, 2)
    p.izgara().sec((1, 1), (2, 2))
    tus(p, Qt.Key_Tab)
    assert aktif(p) == (1, 2) and secim(p) == Aralik(1, 1, 2, 2)


# ---------------------------------------------------------------- seçim
@pytest.mark.xfail(strict=True, reason=FARK)
def test_ctrl_bosluk_sutunu_shift_bosluk_satiri_secer_etkin_hucre_kalir(p):
    git(p, 3, 2)
    tus(p, Qt.Key_Space, CTRL)
    assert secim(p) == Aralik(1, 2, MAX_ROW, 2) and aktif(p) == (3, 2)
    git(p, 3, 2)
    tus(p, Qt.Key_Space, SHIFT)
    assert secim(p) == Aralik(3, 1, 3, MAX_COL) and aktif(p) == (3, 2)


@pytest.mark.xfail(strict=True, reason=FARK)
def test_ctrl_a_once_veri_bolgesi_sonra_tum_sayfa(p):
    """Excel: veri bölgesindeyken Ctrl+A önce bölgeyi, ikinci basış tüm sayfayı seçer."""
    git(p, 2, 2)
    tus(p, Qt.Key_A, CTRL)
    assert secim(p) == Aralik(1, 1, 5, 3)
    tus(p, Qt.Key_A, CTRL)
    assert secim(p) == Aralik(1, 1, MAX_ROW, MAX_COL)


def test_ctrl_a_bos_hucrede_tum_sayfa(p):
    git(p, 20, 20)
    tus(p, Qt.Key_A, CTRL)
    assert secim(p) == Aralik(1, 1, MAX_ROW, MAX_COL)


# ---------------------------------------------------------------- düzenleme
def test_f2_duzenlemeyi_acar_imlec_sonda_esc_vazgecer(p):
    g = p.izgara()
    git(p, 1, 1)
    tus(p, Qt.Key_F2)
    assert g.duzenleniyor()
    e = g.focusWidget()
    assert e.text() == "11" and e.cursorPosition() == 2
    QTest.keyClicks(e, "9")
    tus(p, Qt.Key_Escape)                                     # Esc: vazgeç
    assert not g.duzenleniyor() and g.sayfa.hucre(1, 1).deger == 11.0


def test_yazarak_baslayinca_enter_asagi_tab_saga_gider(p):
    g = p.izgara()
    git(p, 12, 1)
    QTest.keyClicks(g, "7")
    QTest.keyClick(g.focusWidget(), Qt.Key_Return)
    assert g.sayfa.hucre(12, 1).deger == 7.0 and aktif(p) == (13, 1)
    git(p, 12, 1)
    QTest.keyClicks(g, "8")
    QTest.keyClick(g.focusWidget(), Qt.Key_Tab)
    assert g.sayfa.hucre(12, 1).deger == 8.0 and aktif(p) == (12, 2)


def test_delete_icerigi_siler_biçimi_korur(p):
    g = p.izgara()
    git(p, 1, 1)
    tus(p, Qt.Key_B, CTRL)
    tus(p, Qt.Key_Delete)
    assert g.sayfa.hucre(1, 1) is None and g.sayfa.stil(1, 1).kalin          # içerik gitti, biçim kaldı


def test_ctrl_enter_girisi_tum_secime_yazar(p):
    g = p.izgara()
    g.sec((12, 1), (13, 2))
    QTest.keyClicks(g, "5")
    QTest.keyClick(g.focusWidget(), Qt.Key_Return, CTRL)
    assert [g.sayfa.hucre(r, c).deger for r in (12, 13) for c in (1, 2)] == [5.0] * 4


def test_alt_enter_hucre_icinde_satir_sonu(p):
    g = p.izgara()
    git(p, 12, 1)
    QTest.keyClicks(g, "a")
    QTest.keyClick(g.focusWidget(), Qt.Key_Return, ALT)
    QTest.keyClicks(g.focusWidget(), "b")
    QTest.keyClick(g.focusWidget(), Qt.Key_Return)
    assert g.sayfa.hucre(12, 1).deger == "a\nb"


# ---------------------------------------------------------------- F4 başvuru döngüsü
@pytest.mark.parametrize("ilk,sonra", [("=A1", "=$A$1"), ("=$A$1", "=A$1"), ("=A$1", "=$A1"), ("=$A1", "=A1")])
def test_f4_dongusu_bes_durumun_hepsi(p, ilk, sonra):
    g = p.izgara()
    git(p, 12, 4)
    tus(p, Qt.Key_F2)
    e = g.focusWidget()
    e.setText(ilk)
    e.setCursorPosition(len(ilk))                             # imleç başvurunun sonunda
    QTest.keyClick(e, Qt.Key_F4)
    assert e.text() == sonra
    tus(p, Qt.Key_Escape)


def test_f4_aralikta_ve_formul_ortasinda(p):
    g = p.izgara()
    git(p, 12, 4)
    tus(p, Qt.Key_F2)
    e = g.focusWidget()
    e.setText("=TOPLA(A1:B2)+C3")
    e.setCursorPosition(len("=TOPLA(A1:B2"))                  # imleç aralığın sonunda: iki ucu birlikte döner
    QTest.keyClick(e, Qt.Key_F4)
    assert e.text() == "=TOPLA($A$1:$B$2)+C3"
    tus(p, Qt.Key_Escape)


# ---------------------------------------------------------------- doldurma / geri al
def test_ctrl_d_asagi_ctrl_r_saga_kopyalar(p):
    g = p.izgara()
    g.sec((1, 1), (3, 1))
    tus(p, Qt.Key_D, CTRL)
    assert [g.sayfa.hucre(r, 1).deger for r in (1, 2, 3)] == [11.0, 11.0, 11.0]
    g.sec((1, 1), (1, 3))
    tus(p, Qt.Key_R, CTRL)
    assert [g.sayfa.hucre(1, c).deger for c in (1, 2, 3)] == [11.0, 11.0, 11.0]


def test_ctrl_z_ve_ctrl_y_ve_ctrl_shift_z(p):
    g = p.izgara()
    git(p, 12, 1)
    QTest.keyClicks(g, "3")
    QTest.keyClick(g.focusWidget(), Qt.Key_Return)
    assert g.sayfa.hucre(12, 1).deger == 3.0
    tus(p, Qt.Key_Z, CTRL)
    assert g.sayfa.hucre(12, 1) is None
    tus(p, Qt.Key_Y, CTRL)
    assert g.sayfa.hucre(12, 1).deger == 3.0


# ---------------------------------------------------------------- pencere düzeyi
def test_ctrl_f_bul_ctrl_h_degistir_penceresini_acar(p, monkeypatch):
    acilan = []
    monkeypatch.setattr(type(p), "bul_ac", lambda self, degistir=False: acilan.append(degistir))
    tus(p, Qt.Key_F, CTRL)
    tus(p, Qt.Key_H, CTRL)
    assert acilan == [False, True]


def test_ctrl_pgdn_pgup_sayfa_degistirir(p):
    p.sayfa_ekle()
    p.sekmeler.setCurrentIndex(0)
    tus(p, Qt.Key_PageDown, CTRL)
    assert p.sekmeler.currentIndex() == 1
    tus(p, Qt.Key_PageUp, CTRL)
    assert p.sekmeler.currentIndex() == 0


def test_ctrl_eksi_satiri_siler_ctrl_arti_ekler(p):
    g = p.izgara()
    git(p, 2, 1)
    tus(p, Qt.Key_Space, SHIFT)                               # tüm satır
    tus(p, Qt.Key_Minus, CTRL)
    assert g.sayfa.hucre(2, 1).deger == 31.0                  # alt satır yukarı çıktı
    git(p, 2, 1)
    tus(p, Qt.Key_Space, SHIFT)
    tus(p, Qt.Key_Plus, CTRL | SHIFT)
    assert g.sayfa.hucre(2, 1) is None and g.sayfa.hucre(3, 1).deger == 31.0


def test_ctrl_9_ve_ctrl_0_gizler_shift_ile_gosterir(p):
    g = p.izgara()
    git(p, 2, 2)
    tus(p, Qt.Key_9, CTRL)
    assert 2 in g.sayfa.gizli_satir
    tus(p, Qt.Key_0, CTRL)
    assert 2 in g.sayfa.gizli_sutun
    g.sec((1, 1), (3, 3))
    tus(p, Qt.Key_ParenLeft, CTRL | SHIFT)                    # Ctrl+Shift+9
    tus(p, Qt.Key_ParenRight, CTRL | SHIFT)                   # Ctrl+Shift+0
    assert 2 not in g.sayfa.gizli_satir and 2 not in g.sayfa.gizli_sutun


def test_ctrl_b_i_u_biçimi_uygular(p):
    g = p.izgara()
    git(p, 1, 1)
    tus(p, Qt.Key_B, CTRL)
    tus(p, Qt.Key_I, CTRL)
    tus(p, Qt.Key_U, CTRL)
    st = g.sayfa.stil(1, 1)
    assert st.kalin and st.italik and st.alti_cizili != "yok"
    tus(p, Qt.Key_B, CTRL)
    assert not g.sayfa.stil(1, 1).kalin


def test_alt_esittir_otomatik_toplam(p):
    g = p.izgara()
    git(p, 6, 1)
    tus(p, Qt.Key_Equal, ALT)
    assert g.duzenleniyor() or (g.sayfa.hucre(6, 1) is not None and g.sayfa.hucre(6, 1).formul is not None)
