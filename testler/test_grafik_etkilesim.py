"""Faz 6 / 6e: yüzen nesne etkileşimi — seçme, taşıma, boyutlandırma, klavye, z sırası, dahili pano, menü."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.grafik import EN_KUCUK_BOYUT, Grafik, Konum, Referans, Resim, Seri
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.grid_nesne_etkilesim import SURUKLEME_ESIGI
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    from tabcel.ui import grafik_eylemleri

    class _AyarPenceresiYok:                         # 6f: `nesneAyarIstendi` artık gerçek (modal) pencereyi açar; burada yalnız sinyal denenir
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return 0
    monkeypatch.setattr(grafik_eylemleri, "GrafikAyarlariPenceresi", _AyarPenceresiYok)
    from tabcel.ui.grid import Izgara
    Izgara._nesne_panosu = None
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
    return Grafik(seriler=(Seri(deger=Referans(sayfa.kimlik, Aralik(1, 2, 5, 2))),), konum=konum, boyut=boyut,
                  gosterge=None, **kw)


def QSignalSpy(sinyal):
    """Sinyalin aldığı argüman demetlerini toplar (PySide6 QSignalSpy dizinlenemez)."""
    liste = []
    sinyal.connect(lambda *a: liste.append(a))
    return liste


def tikla(g, p, ctrl=False):
    QTest.mouseClick(g.viewport(), Qt.LeftButton, Qt.ControlModifier if ctrl else Qt.NoModifier, p)


def hareket(g, p, mod=Qt.NoModifier):
    """Sol düğme basılıyken fare hareketi; `QTest.mouseMove` değiştirici tuş taşımadığından olay elle gönderilir."""
    ev = QMouseEvent(QEvent.MouseMove, QPointF(p), QPointF(g.viewport().mapToGlobal(p)), Qt.NoButton,
                     Qt.LeftButton, mod)
    QApplication.sendEvent(g.viewport(), ev)
    QApplication.processEvents()


def surukle(g, p0, p1, shift=False, adim=6):
    """Fare ile p0 → p1 sürükler (ara hareketlerle)."""
    mod = Qt.ShiftModifier if shift else Qt.NoModifier
    QTest.mousePress(g.viewport(), Qt.LeftButton, mod, p0)
    for i in range(1, adim + 1):
        hareket(g, QPoint(p0.x() + (p1.x() - p0.x()) * i // adim, p0.y() + (p1.y() - p0.y()) * i // adim), mod)
    QTest.mouseRelease(g.viewport(), Qt.LeftButton, mod, p1)
    QApplication.processEvents()


def orta(r):
    return r.center()


def tus(g, anahtar, mod=Qt.NoModifier):
    QTest.keyClick(g, anahtar, mod)


@pytest.fixture
def ig(pencere):
    g = pencere.izgara()
    g.n = g.sayfa.nesne_ekle(grafik(g.sayfa))
    return g


# ------------------------------------------------------------------ seçme
def test_tik_nesneyi_secer_hucre_secimi_degismez(ig):
    ig.sec((2, 2))
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    spy = QSignalSpy(ig.nesneSecimiDegisti)
    tikla(ig, orta(r))
    assert ig.secili_nesne == ig.n.kimlik and ig.aktif == (2, 2) and list(spy[0]) == [ig.n.kimlik]


def test_nesne_disi_tik_secimi_birakir_ve_hucreyi_secer(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    h = ig.hucre_dikdortgeni(2, 1)
    tikla(ig, orta(h))
    assert ig.secili_nesne is None and ig.aktif == (2, 1)


def test_ust_uste_nesnelerde_en_ustteki_secilir(ig):
    ust = ig.sayfa.nesne_ekle(grafik(ig.sayfa, Konum(8, 4, 100, 50)))
    kesisim = ig.nesne_dikdortgeni(ig.n.kimlik).intersected(ig.nesne_dikdortgeni(ust.kimlik))
    tikla(ig, orta(kesisim))
    assert ig.secili_nesne == ust.kimlik


def test_hucre_klik_hucre_seciliyken_nesne_secimi_yok(ig):
    tikla(ig, orta(ig.hucre_dikdortgeni(2, 1)))
    assert ig.secili_nesne is None


def test_ad_kutusu_nesne_adini_gosterir(pencere, ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    assert pencere.ad_kutusu.text() == f"Grafik {ig.n.kimlik}"
    tus(ig, Qt.Key_Escape)
    assert pencere.ad_kutusu.text() == "A1"


# ------------------------------------------------------------------ taşıma
def test_surukleme_esikten_azsa_tasima_yok(ig):
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    once = ig.sayfa.nesne(ig.n.kimlik)
    surukle(ig, orta(r), orta(r) + QPoint(SURUKLEME_ESIGI - 1, 0))
    assert ig.sayfa.nesne(ig.n.kimlik) == once and ig.secili_nesne == ig.n.kimlik


def test_tasima_konumu_hucre_sinirlariyla_hesaplar_tek_geri_al(ig):
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    h = ig.hucre_dikdortgeni(8, 4)
    gen4, yuk8 = ig._gen(4), ig._yuk(8)
    surukle(ig, orta(r), orta(r) + QPoint(gen4 + 10, 2 * yuk8 + 3))
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert n.konum == Konum(10, 5, 10, 3) and n.boyut == (300, 200)
    r2 = ig.nesne_dikdortgeni(ig.n.kimlik)
    assert (r2.x(), r2.y()) == (h.x() + gen4 + 10, h.y() + 2 * yuk8 + 3)
    assert ig.yigin.geri_al() is True
    assert ig.sayfa.nesne(ig.n.kimlik).konum == Konum(8, 4)                    # tek adımda eski konum
    assert ig.yigin.yinele()


def test_tasima_sola_yukari_ve_sayfa_basindan_oteye_gitmez(ig):
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    surukle(ig, orta(r), orta(r) - QPoint(5000, 5000))
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert (n.konum.satir, n.konum.sutun, n.konum.dx, n.konum.dy) == (1, 1, 0, 0)


def test_shift_baskin_eksene_kilitler(ig):
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    surukle(ig, orta(r), orta(r) + QPoint(2 * ig._gen(1) + 5, 15), shift=True)
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert n.konum.satir == 8 and n.konum.dy == 0                              # dikey hareket kilitlendi
    assert n.konum.sutun == 6


def test_surukleme_sirasinda_model_degismez_onizleme_var(ig):
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    p0 = orta(r)
    QTest.mousePress(ig.viewport(), Qt.LeftButton, Qt.NoModifier, p0)
    QTest.mouseMove(ig.viewport(), p0 + QPoint(60, 40))
    assert ig.sayfa.nesne(ig.n.kimlik).konum == Konum(8, 4)                    # komut yok
    assert ig._nesne_onizleme is not None and ig.nesne_dikdortgeni(ig.n.kimlik) == r
    QTest.mouseRelease(ig.viewport(), Qt.LeftButton, Qt.NoModifier, p0 + QPoint(60, 40))
    assert ig._nesne_onizleme is None and ig.sayfa.nesne(ig.n.kimlik).konum != Konum(8, 4)


def test_yakinlastirmada_tasima_model_pikseli_olcekler(ig):
    ig.yakinlastir(2.0)
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    surukle(ig, orta(r), orta(r) + QPoint(20, 0))                              # 20 ekran px = 10 model px
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert (n.konum.sutun, n.konum.dx) == (4, 10)


# ------------------------------------------------------------------ boyutlandırma
def tutamac(ig, ad):
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    return {"se": QPoint(r.right(), r.bottom()), "e": QPoint(r.right(), r.center().y()),
            "s": QPoint(r.center().x(), r.bottom()), "nw": r.topLeft(), "n": QPoint(r.center().x(), r.top()),
            "w": QPoint(r.left(), r.center().y())}[ad]


def test_sag_alt_kose_boyutlandirir_konum_ayni(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    p = tutamac(ig, "se")
    surukle(ig, p, p + QPoint(60, 40))
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert n.boyut == (360, 240) and n.konum == Konum(8, 4)
    assert ig.yigin.geri_al() and ig.sayfa.nesne(ig.n.kimlik).boyut == (300, 200)


def test_sol_ust_kose_konumu_ve_boyutu_degistirir(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    p = tutamac(ig, "nw")
    surukle(ig, p, p + QPoint(30, 20))
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert n.boyut == (270, 180) and n.konum == Konum(9, 4, 30, 0)             # üst kenar 20 px (1 satır) aşağı
    assert ig.nesne_dikdortgeni(ig.n.kimlik).right() == tutamac_sag(ig)


def tutamac_sag(ig):
    return ig.nesne_dikdortgeni(ig.n.kimlik).right()


def test_kenar_tutamaci_tek_eksen(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    p = tutamac(ig, "e")
    surukle(ig, p, p + QPoint(50, 30))
    assert ig.sayfa.nesne(ig.n.kimlik).boyut == (350, 200)
    p = tutamac(ig, "s")
    surukle(ig, p, p + QPoint(30, -40))
    assert ig.sayfa.nesne(ig.n.kimlik).boyut == (350, 160)


def test_en_kucuk_boyut(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    p = tutamac(ig, "se")
    surukle(ig, p, p - QPoint(5000, 5000))
    assert ig.sayfa.nesne(ig.n.kimlik).boyut == EN_KUCUK_BOYUT


def test_grafik_shift_koseden_orani_korur_resim_varsayilan_orani_korur(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    p = tutamac(ig, "se")
    surukle(ig, p, p + QPoint(60, 5), shift=True)                              # grafik + Shift: oran korunur
    g1, y1 = ig.sayfa.nesne(ig.n.kimlik).boyut
    assert g1 == 360 and y1 == pytest.approx(240, abs=1)
    ig.sayfa.nesne_sil(ig.n.kimlik)
    r = ig.sayfa.nesne_ekle(Resim(veri=b"x", konum=Konum(3, 4), boyut=(200, 100)))   # görünür alanın içinde kalsın
    rr = ig.nesne_dikdortgeni(r.kimlik)
    tikla(ig, orta(rr))
    p = QPoint(rr.right(), rr.bottom())
    surukle(ig, p, p + QPoint(100, 3))                                         # resim: Shift'siz oran korunur
    assert ig.sayfa.nesne(r.kimlik).boyut == (300, 150)
    rr = ig.nesne_dikdortgeni(r.kimlik)
    p = QPoint(rr.right(), rr.bottom())
    surukle(ig, p, p + QPoint(40, 0), shift=True)                              # Shift: serbest
    assert ig.sayfa.nesne(r.kimlik).boyut == (340, 150)


def test_boyutlandirmada_onizleme_gerilir_sonra_gercek_boyut(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    p = tutamac(ig, "se")
    QTest.mousePress(ig.viewport(), Qt.LeftButton, Qt.NoModifier, p)
    QTest.mouseMove(ig.viewport(), p + QPoint(80, 60))
    assert ig._nesne_onizleme[1].size().width() == 380 and ig._onizleme_gercek_boyut is None
    bekle_kosul(lambda: ig._onizleme_gercek_boyut == ig._nesne_onizleme[1].size())      # 60 ms durulunca gerçek boyut
    assert ig._onizleme_gercek_boyut == ig._nesne_onizleme[1].size()
    QTest.mouseRelease(ig.viewport(), Qt.LeftButton, Qt.NoModifier, p + QPoint(80, 60))
    assert ig.sayfa.nesne(ig.n.kimlik).boyut == (380, 260)


def bekle_kosul(kosul, en_cok_ms: int = 3000) -> None:
    """Sabit `qWait` yerine koşul gerçekleşene dek (en çok `en_cok_ms`) bekler: yükte boyama zamanlayıcıyı geciktirir."""
    import time
    bitis = time.monotonic() + en_cok_ms / 1000
    while not kosul() and time.monotonic() < bitis:
        QTest.qWait(10)


# ------------------------------------------------------------------ klavye
def test_delete_nesneyi_siler_geri_alinir_hucre_silinmez(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    ig.sec((2, 1))                                                            # hücre seçimi (nesne seçimi sürer mi?)
    ig.nesne_sec(ig.n.kimlik)
    tus(ig, Qt.Key_Delete)
    assert ig.sayfa.nesne(ig.n.kimlik) is None and ig.secili_nesne is None
    assert ig.sayfa.hucre(2, 1).deger == "K2"                                  # hücre içeriği silinmedi
    ig.yigin.geri_al()
    assert ig.sayfa.nesne(ig.n.kimlik) is not None


def test_escape_secimi_birakir(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    tus(ig, Qt.Key_Escape)
    assert ig.secili_nesne is None and ig.sayfa.nesne(ig.n.kimlik) is not None


def test_ok_tuslari_nesneyi_1_px_ctrl_10_px_oteler(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    tus(ig, Qt.Key_Right)
    tus(ig, Qt.Key_Down)
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert (n.konum.dx, n.konum.dy) == (1, 1) and ig.aktif == (1, 1)           # hücre gezinmedi
    tus(ig, Qt.Key_Right, Qt.ControlModifier)
    assert ig.sayfa.nesne(ig.n.kimlik).konum.dx == 11
    tus(ig, Qt.Key_Left, Qt.ControlModifier)
    tus(ig, Qt.Key_Left)
    assert ig.sayfa.nesne(ig.n.kimlik).konum.dx == 0
    tus(ig, Qt.Key_Left)                                                      # sol hücreye geçer, kayma negatif kalmaz
    n = ig.sayfa.nesne(ig.n.kimlik)
    assert n.konum.sutun == 3 and n.konum.dx == round(ig._gen(3) / ig.yakinlastirma) - 1


def test_baska_tus_secimi_birakir_ve_hucrede_islenir(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    ig.sec((3, 1))
    ig.nesne_sec(ig.n.kimlik)
    tus(ig, Qt.Key_F2)
    assert ig.secili_nesne is None and ig.duzenleniyor()


def test_nesne_seciliyken_ok_hucre_gezinmesi_degil(ig):
    ig.sec((3, 3))
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    tus(ig, Qt.Key_Down)
    assert ig.aktif == (3, 3)


# ------------------------------------------------------------------ z sırası + pano + menü
def test_z_sirasi_komutlari_geri_alinir(ig):
    b = ig.sayfa.nesne_ekle(grafik(ig.sayfa, Konum(8, 4, 100, 50)))
    ig.nesne_sec(ig.n.kimlik)                                                 # alttaki
    assert ig.nesne_sirala("one_getir") and [n.kimlik for n in ig.sayfa.nesneler] == [b.kimlik, ig.n.kimlik]
    assert not ig.nesne_sirala("one_getir")                                   # zaten en üstte
    ig.yigin.geri_al()
    assert [n.kimlik for n in ig.sayfa.nesneler] == [ig.n.kimlik, b.kimlik]


def test_dahili_pano_kopyala_yapistir_etkin_hucreye(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    tus(ig, Qt.Key_C, Qt.ControlModifier)
    ig.nesne_sec(None)
    ig.sec((20, 3))
    tus(ig, Qt.Key_V, Qt.ControlModifier)
    assert len(ig.sayfa.nesneler) == 2
    yeni = ig.sayfa.nesneler[-1]
    assert yeni.kimlik != ig.n.kimlik and yeni.konum == Konum(20, 3) and yeni.seriler == ig.n.seriler
    assert ig.secili_nesne == yeni.kimlik
    ig.yigin.geri_al()
    assert len(ig.sayfa.nesneler) == 1


def test_kes_yapistir_tek_geri_al_adimi_ve_baska_sayfa(pencere, ig):
    k = pencere.kitap
    s2 = k.sayfa_ekle()
    QApplication.processEvents()
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    tus(ig, Qt.Key_X, Qt.ControlModifier)
    assert ig.sayfa.nesne(ig.n.kimlik) is not None                            # kes: yapıştırılana kadar yerinde
    g2 = pencere._izgaralar[s2]
    g2.sec((5, 5))
    g2.yapistir()
    assert ig.sayfa.nesne(ig.n.kimlik) is None and len(s2.nesneler) == 1
    pencere.yigin.geri_al()                                                   # tek adım: taşıma geri alınır
    assert ig.sayfa.nesne(ig.n.kimlik) is not None and s2.nesneler == []


def test_hucre_kopyasi_nesne_panosunun_yerini_alir(ig):
    from tabcel.ui.grid import Izgara
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    ig.kopyala()
    assert Izgara._nesne_panosu is not None
    ig.nesne_sec(None)
    ig.sec((1, 1))
    ig.kopyala()                                                              # hücre kopyası: nesne panosu temizlenir
    assert Izgara._nesne_panosu is None
    n = len(ig.sayfa.nesneler)
    ig.sec((9, 9))
    ig.yapistir()
    assert len(ig.sayfa.nesneler) == n                                        # nesne yapıştırılmadı


def test_katalog_eylemleri_secili_nesneye_uygulanir(pencere, ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    pencere.eylemler["kopyala"].trigger()
    pencere.eylemler["yapistir"].trigger()
    assert len(ig.sayfa.nesneler) == 2


def test_sag_tik_menusu_ve_ayar_istegi(ig):
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    m = ig.nesne_menusu(orta(r))
    assert ig.secili_nesne == ig.n.kimlik
    metinler = [a.text() for a in m.actions() if a.text()]
    assert metinler[:3] == ["Kes", "Kopyala", "Sil"] and "Öne Getir" in metinler and "Arkaya Gönder" in metinler
    assert {"Veriyi Seç…", "Grafik Türünü Değiştir…", "Grafik Ayarları…"} <= set(metinler)
    spy = QSignalSpy(ig.nesneAyarIstendi)
    [a for a in m.actions() if a.text() == "Grafik Ayarları…"][0].trigger()
    assert list(spy[0]) == [ig.n.kimlik, "ayarlar"]
    assert ig.nesne_menusu(orta(ig.hucre_dikdortgeni(2, 1))) is None            # nesne dışı: hücre menüsü


def test_resim_menusunde_grafik_ayarlari_yok(ig):
    r = ig.sayfa.nesne_ekle(Resim(veri=b"x", konum=Konum(20, 4), boyut=(200, 100)))
    m = ig.nesne_menusu(orta(ig.nesne_dikdortgeni(r.kimlik)))
    assert "Grafik Ayarları…" not in [a.text() for a in m.actions()]


def test_cift_tik_grafik_ayarlarini_ister(ig):
    spy = QSignalSpy(ig.nesneAyarIstendi)
    QTest.mouseDClick(ig.viewport(), Qt.LeftButton, Qt.NoModifier, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    assert list(spy[0]) == [ig.n.kimlik, "ayarlar"] and ig.secili_nesne == ig.n.kimlik
    assert not ig.duzenleniyor()                                              # hücre düzenleme açılmadı


def test_imlec_sekilleri(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    assert ig._nesne_imleci(orta(ig.nesne_dikdortgeni(ig.n.kimlik))) == Qt.SizeAllCursor
    assert ig._nesne_imleci(tutamac(ig, "se")) == Qt.SizeFDiagCursor
    assert ig._nesne_imleci(tutamac(ig, "e")) == Qt.SizeHorCursor
    assert ig._nesne_imleci(tutamac(ig, "n")) == Qt.SizeVerCursor
    assert ig._nesne_imleci(orta(ig.hucre_dikdortgeni(2, 1))) is None


def test_secili_nesne_silinince_secim_duser(ig):
    tikla(ig, orta(ig.nesne_dikdortgeni(ig.n.kimlik)))
    spy = QSignalSpy(ig.nesneSecimiDegisti)
    ig.sayfa.nesne_sil(ig.n.kimlik)                                           # model doğrudan (ör. geri al)
    assert ig.secili_nesne is None and list(spy[-1]) == [0]


def test_donuk_bolmede_secili_nesneyi_surukleme_cokmez(pencere, ig):
    ig.sec((3, 3))
    pencere.eylemler["bolme"].trigger()
    QApplication.processEvents()
    r = ig.nesne_dikdortgeni(ig.n.kimlik)
    if r is not None:
        tikla(ig, orta(r))
        surukle(ig, orta(r), orta(r) + QPoint(10, 10))
    assert ig.sayfa.nesne(ig.n.kimlik) is not None
