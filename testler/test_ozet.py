"""Faz 8d: Özet Tablo (model/ozet.py, ui/ozet_penceresi.py, Ekle sekmesi)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.deger import Hata
from tabcel.model.komutlar import GeriAlYigini, ana_sayfa
from tabcel.model.ozet import (BOS_ETIKET, GENEL_TOPLAM, DegerAlani, OzetEkle, OzetHatasi, OzetTanimi, baslik_oku,
                               hesapla)
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.ozet_penceresi import OzetPenceresi
from tabcel.ui.window import Pencere

VERI = [("Bölge", "Ürün", "Adet", "Tutar"),
        ("Kuzey", "Çay", 3, 30), ("Güney", "Şeker", 5, 25), ("Kuzey", "şeker", 2, 10),
        ("güney", "ÇAY", 4, 48), ("Kuzey", "Çay", 1, 10), (None, "Çay", 7, 70)]


def _sayfa(veri=VERI):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, satir in enumerate(veri, 1):
        for j, v in enumerate(satir, 1):
            if v is not None:
                s.ata(i, j, Hucre(float(v) if isinstance(v, int) and not isinstance(v, bool) else v))
    return k, s


def T(satir=None, sutun=None, *degerler, **kw):
    return OzetTanimi(satir, sutun, tuple(DegerAlani(a, f) for a, f in degerler), **kw)


def M(s, tanim, aralik=Aralik(1, 1, 7, 4)):
    return hesapla(s, aralik, tanim)


# ---------------------------------------------------------------- hesaplama
def test_satir_alani_toplam_sirali_genel_toplam():
    _, s = _sayfa()
    r = M(s, T("Bölge", None, ("Adet", "Toplam")))
    assert r.matris == [["Bölge", "Toplam - Adet"], ["Güney", 9.0], ["Kuzey", 6.0], [BOS_ETIKET, 7.0], [GENEL_TOPLAM, 22.0]]
    assert r.toplam_satiri and r.toplam_sutunlari == 0 and r.kayit_sayisi == 6


def test_turkce_buyuk_kucuk_harf_duyarsiz_gruplama():
    _, s = _sayfa()
    r = M(s, T("Ürün", None, ("Adet", "Sayı")))
    etiketler = [satir[0] for satir in r.matris[1:-1]]
    assert len(etiketler) == 2 and etiketler[0] == "Çay" and etiketler[1] == "Şeker"       # ÇAY=Çay, şeker=Şeker
    assert [satir[1] for satir in r.matris[1:3]] == [4.0, 2.0] or sum(satir[1] for satir in r.matris[1:3]) == 6.0


def test_sutun_alani_capraz_tablo():
    _, s = _sayfa()
    r = M(s, T("Bölge", "Ürün", ("Adet", "Toplam")))
    assert r.matris[0] == ["Bölge", "Çay", "Şeker", GENEL_TOPLAM]
    gov = {satir[0]: satir[1:] for satir in r.matris[1:]}
    assert gov["Güney"] == [4.0, 5.0, 9.0] and gov["Kuzey"] == [4.0, 2.0, 6.0]
    assert gov[BOS_ETIKET] == [7.0, None, 7.0]                      # kayıt olmayan kesişim boş
    assert gov[GENEL_TOPLAM] == [15.0, 7.0, 22.0]


def test_birden_cok_deger_alani_ve_sutun_alani():
    _, s = _sayfa()
    r = M(s, T("Bölge", "Ürün", ("Adet", "Toplam"), ("Tutar", "Maks")))
    assert r.matris[0] == ["Bölge", "Çay - Toplam - Adet", "Çay - Maks - Tutar", "Şeker - Toplam - Adet",
                           "Şeker - Maks - Tutar", f"{GENEL_TOPLAM} - Toplam - Adet", f"{GENEL_TOPLAM} - Maks - Tutar"]
    kuzey = next(x for x in r.matris if x[0] == "Kuzey")
    assert kuzey[1:] == [4.0, 30.0, 2.0, 10.0, 6.0, 30.0]
    assert r.toplam_sutunlari == 2


@pytest.mark.parametrize("islev, beklenen", [("Toplam", 22.0), ("Sayı", 6.0), ("Ortalama", 22 / 6), ("Maks", 7.0), ("Min", 1.0)])
def test_islevler_genel_toplam(islev, beklenen):
    _, s = _sayfa()
    r = M(s, T("Bölge", None, ("Adet", islev)))
    assert r.matris[-1][1] == pytest.approx(beklenen)


def test_genel_toplam_ortalamasi_hamdan_hesaplanir():
    """Ortalamaların ortalaması değil, tüm kayıtların ortalaması (Excel gibi)."""
    _, s = _sayfa([("G", "V"), ("a", 1), ("a", 1), ("a", 1), ("b", 10)])
    r = M(s, T("G", None, ("V", "Ortalama")), Aralik(1, 1, 5, 2))
    assert [x[1] for x in r.matris[1:]] == [1.0, 10.0, 13 / 4]


def test_metin_ve_bos_degerler():
    _, s = _sayfa([("G", "V"), ("a", "x"), ("a", 2), ("a", None), ("b", "y")])
    ar = Aralik(1, 1, 5, 2)
    assert [x[1] for x in M(s, T("G", None, ("V", "Toplam")), ar).matris[1:3]] == [2.0, 0.0]     # metin toplamaz
    assert [x[1] for x in M(s, T("G", None, ("V", "Sayı")), ar).matris[1:3]] == [2.0, 1.0]       # boş sayılmaz
    assert M(s, T("G", None, ("V", "Ortalama")), ar).matris[2][1] == Hata("#DIV/0!")             # sayı yok
    assert [x[1] for x in M(s, T("G", None, ("V", "Maks")), ar).matris[1:3]] == [2.0, 0.0]


def test_hata_degeri_sonuca_yayilir():
    _, s = _sayfa([("G", "V"), ("a", 1), ("a", Hata("#N/A")), ("b", 2)])
    r = M(s, T("G", None, ("V", "Toplam")), Aralik(1, 1, 4, 2))
    assert r.matris[1][1] == Hata("#N/A") and r.matris[2][1] == 2.0


def test_satir_alani_olmadan_tek_satir():
    _, s = _sayfa()
    r = M(s, T(None, None, ("Adet", "Toplam"), ("Tutar", "Toplam")))
    assert r.matris == [["Özet", "Toplam - Adet", "Toplam - Tutar"], ["Toplam", 22.0, 193.0]] and not r.toplam_satiri


def test_sayisal_ve_mantiksal_anahtarlar_sirali():
    _, s = _sayfa([("K", "V"), (10, 1), (2, 1), ("b", 1), (True, 1), ("a", 1), (2, 1)])
    r = M(s, T("K", None, ("V", "Toplam")), Aralik(1, 1, 7, 2))
    assert [x[0] for x in r.matris[1:-1]] == [2.0, 10.0, "a", "b", True]                # sayı < metin < mantıksal


def test_basliklar_bos_ve_yineleyen():
    _, s = _sayfa([("Ad", "ad", None), ("x", 1, 2)])
    assert baslik_oku(s, Aralik(1, 1, 2, 3)) == ["Ad", "ad2", "Sütun 3"]


def test_hatalar():
    _, s = _sayfa()
    with pytest.raises(OzetHatasi, match="değer alanı"):
        M(s, T("Bölge", None))
    with pytest.raises(OzetHatasi, match="aynı olamaz"):
        M(s, T("Bölge", "bölge", ("Adet", "Toplam")))
    with pytest.raises(OzetHatasi, match="kaynakta yok"):
        M(s, T("Yok", None, ("Adet", "Toplam")))
    with pytest.raises(OzetHatasi, match="veri yok"):
        M(s, T("Bölge", None, ("Adet", "Toplam")), Aralik(1, 1, 1, 4))
    _, bos = _sayfa([("G", "V"), (None, None)])                                  # başlık var, kayıtlar boş
    with pytest.raises(OzetHatasi, match="veri satırı yok"):
        M(bos, T("G", None, ("V", "Toplam")), Aralik(1, 1, 3, 2))
    with pytest.raises(OzetHatasi, match="işlevi"):
        DegerAlani("Adet", "Medyan")


def test_toplamlar_kapatilabilir():
    _, s = _sayfa()
    r = M(s, T("Bölge", "Ürün", ("Adet", "Toplam"), satir_toplami=False, sutun_toplami=False))
    assert r.matris[0] == ["Bölge", "Çay", "Şeker"] and r.matris[-1][0] != GENEL_TOPLAM


# ---------------------------------------------------------------- komut
def test_yeni_sayfaya_yaz_geri_al_yinele():
    k, s = _sayfa()
    y = GeriAlYigini()
    kmt = OzetEkle(k, s, Aralik(1, 1, 7, 4), T("Bölge", "Ürün", ("Adet", "Toplam")), None, (1, 1), "Özet Tablo")
    y.calistir(kmt)
    assert [x.ad for x in k.sayfalar] == ["Sayfa1", "Özet Tablo"] and ana_sayfa(kmt) is k.sayfalar[1]
    o = k.sayfalar[1]
    assert o.deger(1, 2) == "Çay" and o.deger(2, 1) == "Güney" and o.deger(2, 4) == 9.0 and o.deger(5, 1) == GENEL_TOPLAM
    assert o.stil(1, 1).kalin and o.stil(1, 1).dolgu and o.stil(2, 1).kalin and not o.stil(2, 2).kalin
    assert o.stil(5, 2).kalin and o.stil(2, 4).kalin                           # genel toplam satırı/sütunu
    y.geri_al()
    assert [x.ad for x in k.sayfalar] == ["Sayfa1"] and ana_sayfa(kmt, True) is s
    y.yinele()
    assert [x.ad for x in k.sayfalar] == ["Sayfa1", "Özet Tablo"] and k.sayfalar[1].deger(2, 4) == 9.0


def test_mevcut_sayfaya_yaz_geri_al():
    k, s = _sayfa()
    y = GeriAlYigini()
    s.ata(2, 8, Hucre("eski"))
    y.calistir(OzetEkle(k, s, Aralik(1, 1, 7, 4), T("Bölge", None, ("Adet", "Toplam")), s, (2, 8)))
    assert s.deger(2, 8) == "Bölge" and s.deger(3, 9) == 9.0 and len(k.sayfalar) == 1
    y.geri_al()
    assert s.deger(2, 8) == "eski" and s.hucre(3, 9) is None and s.stil(2, 8).kalin is False


def test_hedefe_sigmiyor():
    k, s = _sayfa()
    with pytest.raises(OzetHatasi, match="sığmıyor"):
        OzetEkle(k, s, Aralik(1, 1, 7, 4), T("Bölge", None, ("Adet", "Toplam")), s, (1_048_576, 1))


# ---------------------------------------------------------------- arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k, _ = _sayfa()
    p = Pencere(k)
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()


def test_pencere_varsayilanlar_ve_sonuc(pencere):
    d = OzetPenceresi(pencere.izgara().sayfa, Aralik(1, 1, 7, 4))
    assert [d.satir_kutusu.itemText(i) for i in range(d.satir_kutusu.count())] == ["(yok)", "Bölge", "Ürün", "Adet", "Tutar"]
    t = d.tanim()
    assert t.satir == "Bölge" and t.sutun is None and t.degerler == (DegerAlani("Tutar", "Toplam"),)
    d.sutun_kutusu.setCurrentText("Ürün")
    d.deger_alanlari[1].setCurrentText("Adet")
    d.deger_islevleri[1].setCurrentText("Ortalama")
    assert d.tanim().sutun == "Ürün" and d.tanim().degerler[1] == DegerAlani("Adet", "Ortalama")
    assert d.hedef() == (True, None)
    d.mevcut.setChecked(True)
    d.hedef_hucre.setText("J3")
    assert d.hedef() == (False, (3, 10))


def test_pencere_dogrulama(pencere, monkeypatch):
    iletiler = []
    monkeypatch.setattr(QMessageBox, "warning", lambda w, b, m, *a: iletiler.append(m))
    d = OzetPenceresi(pencere.izgara().sayfa, Aralik(1, 1, 7, 4))
    d.deger_alanlari[0].setCurrentIndex(0)
    d._onayla()
    assert "değer alanı" in iletiler[-1] and d.result() != QDialog.Accepted
    d.deger_alanlari[0].setCurrentText("Adet")
    d.sutun_kutusu.setCurrentText("Bölge")
    d._onayla()
    assert "aynı olamaz" in iletiler[-1]
    d.sutun_kutusu.setCurrentIndex(0)
    d.kaynak_kutusu.setText("zz")
    d._onayla()
    assert "Kaynak aralık" in iletiler[-1]
    d.kaynak_kutusu.setText("A1:D7")
    d.mevcut.setChecked(True)
    d.hedef_hucre.setText("!!")
    d._onayla()
    assert "Hedef hücre" in iletiler[-1]
    d.hedef_hucre.setText("H1")
    d._onayla()
    assert d.result() == QDialog.Accepted


def test_pencereden_ozet_tablo_olusturma(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((3, 2))                                                            # tek hücre → çevresindeki veri bölgesi
    gorulen = []

    def exec_(self):
        gorulen.append(self.kaynak_kutusu.text())
        self.satir_kutusu.setCurrentText("Bölge")
        self.sutun_kutusu.setCurrentText("Ürün")
        self.deger_alanlari[0].setCurrentText("Adet")
        return QDialog.Accepted
    monkeypatch.setattr(OzetPenceresi, "exec", exec_)
    assert pencere.ozet_tablo_ekle()
    assert gorulen == ["A1:D7"] and [s.ad for s in pencere.kitap.sayfalar] == ["Sayfa1", "Özet Tablo"]
    assert pencere.izgara().sayfa.ad == "Özet Tablo" and pencere.izgara().sayfa.deger(2, 4) == 9.0
    assert pencere.ozet_tablo_ekle()                                         # aynı adla çakışmaz
    assert [s.ad for s in pencere.kitap.sayfalar][-1] == "Özet Tablo2"
    pencere.geri_al() if hasattr(pencere, "geri_al") else pencere.yigin.geri_al()
    assert [s.ad for s in pencere.kitap.sayfalar] == ["Sayfa1", "Özet Tablo"]


def test_iptal_ve_hata(pencere, monkeypatch):
    monkeypatch.setattr(OzetPenceresi, "exec", lambda self: QDialog.Rejected)
    assert pencere.ozet_tablo_ekle() is False and len(pencere.kitap.sayfalar) == 1
    iletiler = []
    monkeypatch.setattr(QMessageBox, "warning", lambda w, b, m, *a: iletiler.append(m))

    def exec_(self):
        self.kaynak_kutusu.setText("A1:D7")
        self.mevcut.setChecked(True)
        self.hedef_hucre.setText("XFD1048576")                              # dar hedef: sığmaz
        self.deger_alanlari[0].setCurrentText("Adet")
        self.satir_kutusu.setCurrentText("Bölge")
        self.sutun_kutusu.setCurrentText("Ürün")
        return QDialog.Accepted
    monkeypatch.setattr(OzetPenceresi, "exec", exec_)
    assert pencere.ozet_tablo_ekle() is False and iletiler and "sığmıyor" in iletiler[-1]


def test_ekle_sekmesinde_eylem(pencere):
    a = pencere.eylemler["ozet_tablo"]
    assert a.text() == "Özet Tablo…" and a in pencere.serit.eylemler()
