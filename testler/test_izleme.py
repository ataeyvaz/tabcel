"""Faz 9b: Hesap İzleme (formul/izleme.py çekirdeği + ui/izleme_paneli.py). Salt okunur; tembel ağaç; aralıklar tek düğüm; döngü ve hata."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.formul import izleme as iz
from tabcel.formul.izleme import Izleme
from tabcel.formul.motor import Hesaplayici
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


def kur():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    m = Hesaplayici(k)
    return k, s, m, Izleme(k, m)


def butce():
    k, s, m, i = kur()
    for r in range(2, 10):
        s.ata(r, 2, Hucre(float(r * 1000)))
        s.ata(r, 3, Hucre(float(r * 100)))
    s.ata(10, 2, Hucre(formul="=SUM(B2:B9)"))
    s.ata(10, 3, Hucre(formul="=SUM(C2:C9)"))
    s.ata(10, 4, Hucre(formul="=B10-C10"))
    return k, s, m, i


# ---------------------------------------------------------------- çekirdek
def test_basit_zincir_formul_deger_ve_aralik_tek_dugum():
    k, s, m, i = butce()
    kok = i.kok(s, 10, 4)
    assert kok.etiket == "D10" and kok.formul == "=B10-C10" and kok.deger == 39600.0 and kok.cocuk_var
    cocuklar = i.cocuklar(kok).dugumler
    assert [c.etiket for c in cocuklar] == ["B10", "C10"]
    assert cocuklar[0].formul == "=TOPLA(B2:B9)" and cocuklar[0].deger == 44000.0
    aralik = i.cocuklar(cocuklar[0], (kok.anahtar,)).dugumler
    assert len(aralik) == 1 and aralik[0].tur == "aralik" and aralik[0].etiket == "B2:B9"
    assert aralik[0].ozet == "8 hücre, 8 dolu, toplam 44.000"                      # tek düğüm + özet
    yapraklar = i.cocuklar(aralik[0]).dugumler
    assert len(yapraklar) == 8 and yapraklar[0].formul is None and not yapraklar[0].cocuk_var     # sabit değer = yaprak


def test_deger_hucrenin_sayi_bicimiyle():
    from tabcel.model.adres import Aralik
    from tabcel.model.komutlar import bicim_komutu
    from tabcel.model.stil import StilYama
    k, s, m, i = butce()
    bicim_komutu(s, [Aralik(10, 4, 10, 4)], StilYama(sayi_bicimi='#,##0 "₺"')).yap()
    assert i.kok(s, 10, 4).deger_metni == "39.600 ₺"


def test_derin_zincir_tembel_ve_yol_boyunca_yurunur():
    k, s, m, i = kur()
    s.ata(1, 1, Hucre(1.0))
    for r in range(2, 301):
        s.ata(r, 1, Hucre(formul=f"=A{r - 1}+1"))
    d = i.kok(s, 300, 1)
    assert d.deger == 300.0
    derinlik, yol = 0, ()
    while d.cocuk_var:
        c = i.cocuklar(d, yol).dugumler
        assert len(c) == 1
        yol, d = yol + (d.anahtar,), c[0]
        derinlik += 1
    assert derinlik == 299 and d.deger == 1.0 and d.formul is None          # yaprak: sabit 1


def test_buyuk_aralik_sayfali_listelenir():
    k, s, m, i = kur()
    for r in range(1, 10_001):
        s.ata(r, 1, Hucre(float(r)))
    s.ata(1, 3, Hucre(formul="=SUM(A1:A10000)"))
    kok = i.kok(s, 1, 3)
    (aralik,) = i.cocuklar(kok).dugumler
    assert aralik.ozet == "10.000 hücre" and aralik.ozet_bekliyor                 # büyük aralıkta özet tembel
    assert i.ozet_tamamla(aralik).ozet == "10.000 hücre, 10.000 dolu, toplam 50.005.000"
    p0 = i.cocuklar(aralik)
    assert len(p0.dugumler) == iz.SAYFA_BOYUTU and p0.toplam == 10_000 and p0.sonraki
    p1 = i.cocuklar(aralik, (), 1)
    assert p1.dugumler[0].etiket == f"A{iz.SAYFA_BOYUTU + 1}"
    son = i.cocuklar(aralik, (), 99)
    assert len(son.dugumler) == iz.SAYFA_BOYUTU and not son.sonraki


def test_bos_hucreler_aralikta_listelenmez_ama_sayilir():
    k, s, m, i = kur()
    s.ata(1, 1, Hucre(5.0))
    s.ata(1, 3, Hucre(formul="=SUM(A1:A50)"))
    (a,) = i.cocuklar(i.kok(s, 1, 3)).dugumler
    assert a.ozet == "50 hücre, 1 dolu, toplam 5"
    assert [c.etiket for c in i.cocuklar(a).dugumler] == ["A1"]


def test_sayfalar_arasi_basvuru_sayfa_adiyla():
    k, s, m, i = kur()
    v = k.sayfa_ekle("Veri Sayfası")
    v.ata(2, 2, Hucre(7.0))
    s.ata(1, 1, Hucre(formul="='Veri Sayfası'!B2*2"))
    kok = i.kok(s, 1, 1)
    (c,) = i.cocuklar(kok).dugumler
    assert c.etiket == "'Veri Sayfası'!B2" and c.deger == 7.0 and c.sayfa is v


def test_dongu_isaretlenir_sonsuza_gitmez():
    k, s, m, i = kur()
    s.ata(1, 1, Hucre(formul="=B1+1"))
    s.ata(1, 2, Hucre(formul="=A1+1"))
    kok = i.kok(s, 1, 1)
    assert kok.dongu and not kok.cocuk_var                                    # döngüdeki hücre açılmaz
    k2, s2, m2, i2 = kur()
    s2.ata(1, 1, Hucre(1.0))
    s2.ata(2, 1, Hucre(formul="=A1+A3"))
    s2.ata(3, 1, Hucre(formul="=A2+1"))
    d = i2.kok(s2, 2, 1)
    yol, adim = (), 0
    while d.cocuk_var and adim < 10:                                          # sonsuz döngüye girmemeli
        (c, *_) = i2.cocuklar(d, yol).dugumler
        yol, d, adim = yol + (d.anahtar,), c, adim + 1
    assert adim < 10 and d.dongu


def test_hata_yayilimi_ve_kaynak_isareti():
    k, s, m, i = kur()
    s.ata(3, 2, Hucre(formul="=1/0"))
    s.ata(1, 3, Hucre(formul="=B3+1"))
    s.ata(1, 4, Hucre(formul="=C1*2"))
    kok = i.kok(s, 1, 4)
    assert kok.hata and not kok.hata_kaynagi
    assert i.hata_kaynagi_metni() and "B3" in i.hata_kaynagi_metni()
    (c,) = i.cocuklar(kok).dugumler
    assert c.etiket == "C1" and c.hata and not c.hata_kaynagi
    (b,) = i.cocuklar(c, (kok.anahtar,)).dugumler
    assert b.etiket == "B3" and b.hata_kaynagi                                # hatanın asıl doğduğu hücre
    assert i.kok(s, 3, 2).hata_kaynagi                                         # hücrenin kendisi kaynaksa kökte de işaretli
    ok = i.kok(s, 3, 3)
    assert not ok.hata and i.hata_kaynagi_metni() is None


def test_ters_yon_bagimlilar():
    k, s, m, i = butce()
    s.ata(12, 4, Hucre(formul="=D10*2"))
    b = i.bagimli_kok(s, 10, 2)
    assert i.bagimli_sayisi(b) == 1
    (d10,) = i.bagimli_cocuklar(b).dugumler
    assert d10.etiket == "D10" and d10.cocuk_var
    (d12,) = i.bagimli_cocuklar(d10, (b.anahtar,)).dugumler
    assert d12.etiket == "D12" and not d12.cocuk_var
    assert i.bagimli_sayisi(i.bagimli_kok(s, 3, 2)) == 1                       # aralık içindeki hücre: SUM(B2:B9) bağımlısı
    assert i.bagimli_sayisi(i.bagimli_kok(s, 20, 20)) == 0


def test_ters_yon_cok_bagimli_sayfali():
    k, s, m, i = kur()
    s.ata(1, 1, Hucre(2.0))
    for r in range(1, 251):
        s.ata(r, 3, Hucre(formul=f"=$A$1*{r}"))
    b = i.bagimli_kok(s, 1, 1)
    p = i.bagimli_cocuklar(b)
    assert p.toplam == 250 and len(p.dugumler) == iz.SAYFA_BOYUTU and p.sonraki
    assert len(i.bagimli_cocuklar(b, (), 2).dugumler) == 50 and not i.bagimli_cocuklar(b, (), 2).sonraki


def test_tasan_hucre_sahibine_baglanir():
    k, s, m, i = kur()
    s.ata(1, 1, Hucre(formul="=SEQUENCE(3)"))
    d = i.kok(s, 2, 1)
    assert d.tasma_sahibi == (1, 1) and d.cocuk_var
    (sahip,) = i.cocuklar(d).dugumler
    assert sahip.etiket == "A1" and sahip.formul == "=SIRALI(3)"


def test_guncelle_degeri_tazeler_ve_izleme_salt_okunur():
    k, s, m, i = butce()
    once = dict(s._hucreler)
    d = i.kok(s, 10, 4)
    s.ata(2, 2, Hucre(9000.0))
    assert d.deger == 39600.0 and i.guncelle(d).deger == 46600.0              # B2 2000 → 9000
    sonra = dict(s._hucreler)
    i.cocuklar(d), i.bagimli_cocuklar(i.bagimli_kok(s, 2, 2)), i.kok(s, 10, 4)
    assert dict(s._hucreler) == sonra and once.keys() == sonra.keys()          # okuma hiçbir hücreyi değiştirmedi


# ---------------------------------------------------------------- panel (arayüz)
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k, s, m, _ = butce()
    p = Pencere(k)
    p.resize(1200, 700)
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()
    DosyaIslemleri._tutulan.clear()


def _bekle(p):
    p.izleme._zamanlayici.stop()
    p.izleme._calis()


def kok_metni(p):
    return p.izleme.agac.topLevelItem(0)


def test_panel_varsayilan_kapali_ve_acilir(pencere):
    assert not pencere.izleme.isVisible() and not pencere.eylemler["izleme"].isChecked()
    pencere.eylemler["izleme"].trigger()
    assert pencere.izleme.isVisible() and pencere.eylemler["izleme"].isChecked()
    pencere.eylemler["izleme"].trigger()
    assert not pencere.izleme.isVisible()


def test_panel_secili_hucreyi_gosterir_tembel_acar(pencere):
    pencere.izleme_ac()
    g = pencere.izgara()
    g.sec((10, 4))
    _bekle(pencere)
    kok = kok_metni(pencere)
    assert "D10" in pencere.izleme.baslik.text() and "=B10-C10" in pencere.izleme.baslik.text()
    assert kok.text(0) == "D10" and kok.text(1) == "=B10-C10" and kok.childCount() == 2
    b10 = kok.child(0)
    assert b10.text(0) == "B10" and b10.isExpanded() and b10.child(0).text(0) == "B2:B9"          # 2. seviye açık
    aralik = b10.child(0)
    assert aralik.text(2).startswith("8 hücre") and aralik.child(0).text(0) == "…"                # yer tutucu: henüz yüklenmedi
    aralik.setExpanded(True)
    assert aralik.childCount() == 8 and aralik.child(0).text(0) == "B2"


def test_panel_tiklayinca_hucreye_gider_ve_kok_degismez(pencere):
    pencere.izleme_ac()
    g = pencere.izgara()
    g.sec((10, 4))
    _bekle(pencere)
    b10 = kok_metni(pencere).child(0)
    pencere.izleme._tikla(b10, 0)
    assert g._aktif == (10, 2) and g._vurgu == (10, 2)                         # gidildi + vurgulandı
    _bekle(pencere)
    assert kok_metni(pencere).text(0) == "D10"                                  # panel kendi gezintisinde kökü değiştirmez
    from PySide6.QtTest import QTest
    QTest.qWait(20)
    g.sec((10, 3))                                                              # kullanıcı ızgarada başka hücre seçince kök değişir
    _bekle(pencere)
    assert kok_metni(pencere).text(0) == "C10"


def test_panel_baska_sayfaya_gider(pencere):
    pencere.izleme_ac()
    v = pencere.kitap.sayfa_ekle("Veri")
    v.ata(1, 1, Hucre(5.0))
    pencere.sekmeler.setCurrentIndex(0)                                        # yeni sayfa seçilmişti
    g = pencere.izgara()
    g.sayfa.ata(1, 5, Hucre(formul="=Veri!A1*2"))
    g.sec((1, 5))
    _bekle(pencere)
    c = kok_metni(pencere).child(0)
    assert c.text(0) == "Veri!A1"
    pencere.izleme._tikla(c, 0)
    assert pencere.izgara().sayfa is v and pencere.izgara()._aktif == (1, 1)


def test_panel_deger_degisince_gunceller(pencere):
    pencere.izleme_ac()
    g = pencere.izgara()
    g.sec((10, 4))
    _bekle(pencere)
    onceki = kok_metni(pencere).text(2)
    g.hucre_gir(2, 2, "9000")
    _bekle(pencere)
    kok = kok_metni(pencere)
    assert kok.text(2) != onceki and kok.text(2) == "46600"
    assert kok.child(0).text(2) == "51000"                                      # zincir da güncellendi


def test_panel_hata_kaynagi_etiketi_ve_isareti(pencere):
    pencere.izleme_ac()
    g = pencere.izgara()
    g.sayfa.ata(3, 6, Hucre(formul="=1/0"))
    g.sayfa.ata(1, 7, Hucre(formul="=F3+1"))
    g.sec((1, 7))
    _bekle(pencere)
    assert not pencere.izleme.hata_etiketi.isHidden() and "F3" in pencere.izleme.hata_etiketi.text()
    kaynak = kok_metni(pencere).child(0)
    assert kaynak.text(0).startswith("⚠") and "F3" in kaynak.text(0)
    g.sec((10, 4))
    _bekle(pencere)
    assert pencere.izleme.hata_etiketi.isHidden()


def test_panel_sayfalama_dugmesi(pencere):
    pencere.izleme_ac()
    g = pencere.izgara()
    for r in range(1, 301):
        g.sayfa.ata(r, 9, Hucre(float(r)))
    g.sayfa.ata(1, 10, Hucre(formul="=SUM(I1:I300)"))
    g.sec((1, 10))
    _bekle(pencere)
    aralik = kok_metni(pencere).child(0)
    aralik.setExpanded(True)
    assert aralik.childCount() == iz.SAYFA_BOYUTU + 1 and aralik.child(iz.SAYFA_BOYUTU).text(0).startswith("… 200")
    pencere.izleme._tikla(aralik.child(iz.SAYFA_BOYUTU), 0)
    assert aralik.childCount() == 2 * iz.SAYFA_BOYUTU + 1


def test_ters_sekme(pencere):
    pencere.izleme_ac()
    g = pencere.izgara()
    g.sec((10, 2))
    _bekle(pencere)
    kok = pencere.izleme.ters.topLevelItem(0)
    assert "1 formül" in kok.text(1) and kok.child(0).text(0) == "D10"
    g.sec((20, 20))
    _bekle(pencere)
    assert "kullanan formül yok" in pencere.izleme.ters.topLevelItem(0).text(1)


def test_kapali_panel_hesaplama_yapmaz(pencere):
    g = pencere.izgara()
    g.sec((10, 4))
    assert pencere.izleme.agac.topLevelItemCount() == 0                          # kapalıyken kök kurulmaz
