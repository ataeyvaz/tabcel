"""Faz 6 / 6f: Ekle sekmesi, "Grafik" bağlamsal sekmesi, Grafik Ayarları penceresi, ikonlar."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Konum, Referans, Resim, Seri
from tabcel.model.grafik_islem import GALERI, RENK_SEMALARI
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import grafik_eylemleri
from tabcel.ui.grafik_pencereleri import GrafikAyarlariPenceresi, sayi_coz, sayi_yaz
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    from tabcel.ui.grid import Izgara
    Izgara._nesne_panosu = None
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, satir in enumerate([[None, "Ocak", "Şubat"], ["Elma", 1, 2], ["Armut", 3, 4], ["Kiraz", 5, 6]], 1):
        for j, v in enumerate(satir, 1):
            if v is not None:
                s.ata(i, j, Hucre(v))
    p = Pencere(k)
    p.resize(1100, 700)
    p.show()
    p.uyarilar = []
    monkeypatch.setattr(p, "_uyari", lambda metin: p.uyarilar.append(metin))
    QApplication.processEvents()
    return p


def grafik_ekle(p, tur="sutun", alt="kumelenmis"):
    p.ad_kutusu.setText("A1:C4")
    p._ad_kutusundan_git()
    p.eylemler[f"grafik_ekle.{tur}.{alt}"].trigger()
    QApplication.processEvents()
    g = p.izgara()
    return g, g.sayfa.nesne(g.secili_nesne)


# ------------------------------------------------------------------ Ekle sekmesi
def test_ekle_sekmesi_galeri_eylemleri_serite_bagli(pencere):
    sr = pencere.serit.eylemler()
    for tur, ogeler in GALERI.items():
        for alt, _ in ogeler:
            assert pencere.eylemler[f"grafik_ekle.{tur}.{alt}"] in sr, (tur, alt)
    assert "Ekle" in pencere.serit.sekme_adlari()
    assert pencere.serit.sekme_adlari()[2] == "Ekle"


@pytest.mark.parametrize("tur,alt", [(t, a) for t, o in GALERI.items() for a, _ in o])
def test_her_galeri_ogesi_tek_geri_alinir_grafik_ekler(pencere, tur, alt):
    g, n = grafik_ekle(pencere, tur, alt)
    assert isinstance(n, Grafik) and n.tur == tur and n.alt_tur == alt
    assert len(g.sayfa.nesneler) == 1 and g.secili_nesne == n.kimlik
    g.geri_al()
    assert g.sayfa.nesneler == []
    g.yinele()
    assert len(g.sayfa.nesneler) == 1


def test_yeni_grafik_gorunen_alanin_ortasinda_ve_secili(pencere):
    g, n = grafik_ekle(pencere)
    r = g.nesne_dikdortgeni(n.kimlik)
    assert r is not None and g.viewport().rect().intersects(r)
    merkez = g.viewport().rect().center()
    assert abs(r.center().x() - merkez.x()) < 80 and abs(r.center().y() - merkez.y()) < 60


def test_grafik_eklenince_baglamsal_sekme_gorunur_ve_secilir(pencere):
    assert not pencere.serit.sekme_gorunur_mu("Grafik")
    grafik_ekle(pencere)
    assert pencere.serit.sekme_gorunur_mu("Grafik")
    assert pencere.serit.sekmeler.tabText(pencere.serit.sekmeler.currentIndex()) == "Grafik"


def test_nesne_secimi_birakilinca_sekme_gizlenir_ve_giris_acilir(pencere):
    g, n = grafik_ekle(pencere)
    g.nesne_sec(None)
    QApplication.processEvents()
    assert not pencere.serit.sekme_gorunur_mu("Grafik")
    assert pencere.serit.sekmeler.tabText(pencere.serit.sekmeler.currentIndex()) == "Giriş"


def test_geri_alinca_grafik_gidince_sekme_gizlenir(pencere):
    g, n = grafik_ekle(pencere)
    g.geri_al()
    QApplication.processEvents()
    assert not pencere.serit.sekme_gorunur_mu("Grafik")


def test_resim_secili_iken_grafik_sekmesi_yok(pencere):
    g = pencere.izgara()
    g.nesne_ekle(Resim(veri=b"x", ad="r", konum=Konum(2, 2), boyut=(50, 40)))
    QApplication.processEvents()
    assert not pencere.serit.sekme_gorunur_mu("Grafik")


def test_sayisal_veri_yoksa_uyari_grafik_eklenmez(pencere):
    pencere.ad_kutusu.setText("A20:B22")
    pencere._ad_kutusundan_git()
    pencere.eylemler["grafik_ekle.sutun.kumelenmis"].trigger()
    assert pencere.uyarilar and "sayısal veri yok" in pencere.uyarilar[0]
    assert pencere.izgara().sayfa.nesneler == []
    assert not pencere.serit.sekme_gorunur_mu("Grafik")


def test_tek_hucre_secimi_bitisik_bolgeyi_kullanir(pencere):
    pencere.ad_kutusu.setText("B2")
    pencere._ad_kutusundan_git()
    pencere.eylemler["grafik_ekle.cizgi.kumelenmis"].trigger()
    g = pencere.izgara()
    assert len(g.sayfa.nesne(g.secili_nesne).seriler) == 2


# ------------------------------------------------------------------ bağlamsal komutlar
def test_baslik_eksen_etiket_gosterge_eylemleri(pencere):
    g, n = grafik_ekle(pencere)
    e = pencere.eylemler
    assert n.baslik is None and not e["grafik_baslik"].isChecked()
    e["grafik_baslik"].trigger()
    assert g.sayfa.nesne(n.kimlik).baslik == "Grafik Başlığı" and e["grafik_baslik"].isChecked()
    e["grafik_baslik"].trigger()
    assert g.sayfa.nesne(n.kimlik).baslik is None
    e["grafik_eksen_basliklari"].trigger()
    assert g.sayfa.nesne(n.kimlik).x_baslik == g.sayfa.nesne(n.kimlik).y_baslik == "Eksen Başlığı"
    e["grafik_veri_etiketleri"].trigger()
    assert g.sayfa.nesne(n.kimlik).deger_etiketi
    for anahtar, beklenen in (("grafik_gosterge.alt", "alt"), ("grafik_gosterge.yok", None), ("grafik_gosterge.sol", "sol")):
        e[anahtar].trigger()
        assert g.sayfa.nesne(n.kimlik).gosterge == beklenen
    g.geri_al()                                                   # her ayar TEK geri al adımı
    assert g.sayfa.nesne(n.kimlik).gosterge is None
    assert e["grafik_gosterge.yok"].isChecked()


def test_pasta_icin_eksen_ve_satir_sutun_kapali(pencere):
    g, n = grafik_ekle(pencere, "pasta")
    e = pencere.eylemler
    assert not e["grafik_eksen_basliklari"].isEnabled() and not e["grafik_satir_sutun"].isEnabled()
    assert e["grafik_ekle.pasta.kumelenmis"].isEnabled()
    grafik_ekle(pencere, "sutun")
    assert e["grafik_eksen_basliklari"].isEnabled() and e["grafik_satir_sutun"].isEnabled()


def test_satir_sutun_degistir_ve_geri_al(pencere):
    g, n = grafik_ekle(pencere)
    assert len(n.seriler) == 2
    pencere.eylemler["grafik_satir_sutun"].trigger()
    assert len(g.sayfa.nesne(n.kimlik).seriler) == 3
    g.geri_al()
    assert len(g.sayfa.nesne(n.kimlik).seriler) == 2


def test_satir_sutun_hata_uyari_verir(pencere):
    g = pencere.izgara()
    k = Grafik(seriler=(Seri(deger=Referans(g.sayfa.kimlik, Aralik(2, 2, 4, 2))),
                        Seri(deger=Referans(g.sayfa.kimlik, Aralik(2, 3, 3, 3)))))
    g.nesne_ekle(k)
    pencere.eylemler["grafik_satir_sutun"].trigger()
    assert pencere.uyarilar


@pytest.mark.parametrize("sema", list(RENK_SEMALARI))
def test_renk_semalari(pencere, sema):
    g, n = grafik_ekle(pencere)
    pencere.eylemler[f"grafik_renk.{sema}"].trigger()
    renkler = [s.renk for s in g.sayfa.nesne(n.kimlik).seriler]
    assert (renkler == [None, None]) if sema == "Office" else all(renkler)


def test_z_sirasi_ve_sil(pencere):
    g, a = grafik_ekle(pencere)
    _, b = grafik_ekle(pencere, "cizgi")
    e = pencere.eylemler
    e["grafik_arkaya_gonder"].trigger()
    assert [x.kimlik for x in g.sayfa.nesneler] == [b.kimlik, a.kimlik]
    e["grafik_one_getir"].trigger()
    assert [x.kimlik for x in g.sayfa.nesneler] == [a.kimlik, b.kimlik]
    e["grafik_sil"].trigger()
    assert [x.kimlik for x in g.sayfa.nesneler] == [a.kimlik]
    assert not pencere.serit.sekme_gorunur_mu("Grafik")


def test_grafik_eylemleri_secim_yokken_hicbir_sey_yapmaz(pencere):
    for k in ("grafik_baslik", "grafik_satir_sutun", "grafik_sil", "grafik_renk.Mavi Tonları", "grafik_ayarlar"):
        pencere.eylemler[k].trigger()
    assert pencere.izgara().sayfa.nesneler == [] and not pencere.uyarilar


# ------------------------------------------------------------------ pencere açılışı
class _SahtePencere:
    cagrilar = []
    sonuc = None

    def __init__(self, kitap, sayfa, grafik, parent=None, odak=None):
        self.grafik, self.odak, self.sonuc = grafik, odak, _SahtePencere.sonuc
        _SahtePencere.cagrilar.append(odak)

    def exec(self):
        return 1 if self.sonuc is not None else 0


@pytest.mark.parametrize("istek,odak", [("ayarlar", None), ("veri", "veri"), ("tur", "tur")])
def test_nesne_ayar_istegi_pencereyi_acar(pencere, monkeypatch, istek, odak):
    monkeypatch.setattr(grafik_eylemleri, "GrafikAyarlariPenceresi", _SahtePencere)
    _SahtePencere.cagrilar = []
    g, n = grafik_ekle(pencere)
    g.nesne_sec(None)
    g.nesneAyarIstendi.emit(n.kimlik, istek)
    assert _SahtePencere.cagrilar == [odak] and g.secili_nesne == n.kimlik


def test_pencere_tamam_nesneyi_tek_adimda_gunceller(pencere, monkeypatch):
    monkeypatch.setattr(grafik_eylemleri, "GrafikAyarlariPenceresi", _SahtePencere)
    g, n = grafik_ekle(pencere)
    _SahtePencere.sonuc = n.degistir(baslik="Satışlar")
    try:
        pencere.eylemler["grafik_ayarlar"].trigger()
    finally:
        _SahtePencere.sonuc = None
    assert g.sayfa.nesne(n.kimlik).baslik == "Satışlar"
    g.geri_al()
    assert g.sayfa.nesne(n.kimlik).baslik is None


def test_resim_icin_ayar_istegi_yok_sayilir(pencere, monkeypatch):
    monkeypatch.setattr(grafik_eylemleri, "GrafikAyarlariPenceresi", _SahtePencere)
    _SahtePencere.cagrilar = []
    g = pencere.izgara()
    kimlik = g.nesne_ekle(Resim(veri=b"x", konum=Konum(2, 2), boyut=(50, 40)))
    g.nesneAyarIstendi.emit(kimlik, "ayarlar")
    assert _SahtePencere.cagrilar == []


# ------------------------------------------------------------------ Grafik Ayarları penceresi
@pytest.fixture
def ayar(pencere):
    g, n = grafik_ekle(pencere)
    return GrafikAyarlariPenceresi(pencere.kitap, g.sayfa, n), n, g


def test_pencere_mevcut_grafigi_gosterir_degismeden_tamam_ayni_sonuc(ayar):
    d, n, g = ayar
    assert d.tablo.rowCount() == 2
    assert d.tablo.item(0, 1).text() == "Sayfa1!$B$2:$B$4" and d.tablo.item(0, 0).text() == "=Sayfa1!$B$1"
    assert d.tablo.item(0, 2).text() == "Sayfa1!$A$2:$A$4"
    d.accept()
    assert d.sonuc == n


def test_pencere_alanlari_sonuca_yazilir(ayar):
    d, n, g = ayar
    d.tur.setCurrentIndex(d.tur.findData("cizgi"))
    d.alt_tur.setCurrentIndex(d.alt_tur.findData("yigili"))
    d.baslik.setText("  Satışlar ")
    d.gosterge.setCurrentIndex(d.gosterge.findData("alt"))
    d.x_baslik.setText("Ay")
    d.y_baslik.setText("Adet")
    d.deger_etiketi.setChecked(True)
    d.y_min.setText("0")
    d.y_max.setText("12,5")
    d.accept()
    s = d.sonuc
    assert (s.tur, s.alt_tur, s.baslik, s.gosterge, s.x_baslik, s.y_baslik) == (
        "cizgi", "yigili", "Satışlar", "alt", "Ay", "Adet")
    assert s.deger_etiketi and s.y_min == 0 and s.y_max == 12.5
    assert (s.kimlik, s.konum, s.boyut) == (n.kimlik, n.konum, n.boyut)


def test_pencere_alt_tur_turle_degisir(ayar):
    d, n, g = ayar
    d.tur.setCurrentIndex(d.tur.findData("pasta"))
    assert d.alt_tur.count() == 1 and not d.alt_tur.isEnabled()
    d.tur.setCurrentIndex(d.tur.findData("sutun"))
    assert d.alt_tur.count() == 3 and d.alt_tur.isEnabled()


def test_pencere_gecersiz_aralik_acik_kalir(ayar):
    d, n, g = ayar
    d.tablo.item(0, 1).setText("Yok!A1:A3")
    d.accept()
    assert d.sonuc is None and "1. seri" in d.ileti.text() and "sayfa yok" in d.ileti.text()
    d.tablo.item(0, 1).setText("Sayfa1!ZZZ")
    d.accept()
    assert d.sonuc is None and "Geçersiz aralık" in d.ileti.text()
    d.tablo.item(0, 1).setText("")
    d.accept()
    assert d.sonuc is None and "boş" in d.ileti.text()


def test_pencere_pasta_birden_cok_seri_reddeder_eksen_sinirlari(pencere, ayar):
    d, n, g = ayar
    d.tur.setCurrentIndex(d.tur.findData("pasta"))
    d.accept()
    assert d.sonuc is None and "yalnız bir seri" in d.ileti.text()
    d.tablo.removeRow(1)
    d.accept()
    assert d.sonuc is not None
    d2 = GrafikAyarlariPenceresi(pencere.kitap, g.sayfa, n)
    d2.y_min.setText("5")
    d2.y_max.setText("5")
    d2.accept()
    assert d2.sonuc is None and "küçük olmalı" in d2.ileti.text()
    d2.y_max.setText("abc")
    d2.accept()
    assert d2.sonuc is None and "sayı değil" in d2.ileti.text()


def test_pencere_seri_ekle_sil_tasi(ayar):
    d, n, g = ayar
    d.tablo.setCurrentCell(0, 1)
    d._tasi(1)
    assert d.tablo.item(0, 1).text().endswith("$C$4") and d.tablo.item(1, 1).text().endswith("$B$4")
    d._seri_ekle()
    assert d.tablo.rowCount() == 3
    d.tablo.item(2, 1).setText("C2:C4")                      # sayfa adı yoksa bu sayfa
    d.tablo.item(2, 0).setText("Toplam")                     # sabit ad
    d.accept()
    s = d.sonuc.seriler
    assert s[0].deger.aralik == Aralik(2, 3, 4, 3) and s[1].deger.aralik == Aralik(2, 2, 4, 2)
    assert s[2].ad == "Toplam" and s[2].ad_ref is None and s[2].deger.aralik == Aralik(2, 3, 4, 3)
    assert s[0].ad_ref is not None and s[0].ad is None
    d._seri_sil()
    assert d.tablo.rowCount() == 2


def test_pencere_renk_secimi_sonuca_yazilir(ayar):
    d, n, g = ayar
    d._renk_yaz(d.tablo.item(0, 3), "#FF0000")
    d.accept()
    assert d.sonuc.seriler[0].renk == "#FF0000" and d.sonuc.seriler[1].renk is None


def test_sayi_yardimcilari():
    assert sayi_coz("", "x") is None and sayi_coz(" 1 250,5 ", "x") == 1250.5 and sayi_coz("-3", "x") == -3
    assert sayi_yaz(None) == "" and sayi_yaz(5.0) == "5" and sayi_yaz(2.5) == "2,5"
    with pytest.raises(ValueError):
        sayi_coz("a", "x")


# ------------------------------------------------------------------ yerleşim
@pytest.mark.parametrize("genislik", [1100, 800])
@pytest.mark.parametrize("sekme", ["Ekle", "Grafik"])
def test_sekmelerde_tasma_yok(pencere, sekme, genislik):
    grafik_ekle(pencere)
    pencere.resize(genislik, 600)
    pencere.serit.sec(sekme)
    QApplication.processEvents()
    sayfa = pencere.serit.sayfa(sekme)
    assert sayfa.gruplar
    for g in sayfa.gruplar:
        assert g.mapTo(sayfa, g.rect().topRight()).x() <= sayfa.width() + 1, (sekme, g.ad)


def test_baglam_sekmesi_son_sekme_ve_ayri_renkte(pencere):
    from tabcel.ui import theme
    assert pencere.serit.sekme_adlari()[-1] == "Grafik"
    assert 'baglam="true"' in theme.serit_stil() and theme.BAGLAM in theme.serit_stil()
    assert pencere.serit.sekmeler.property("baglam") != "true"
    grafik_ekle(pencere)
    assert pencere.serit.sekmeler.property("baglam") == "true"
    pencere.izgara().nesne_sec(None)
    assert pencere.serit.sekmeler.property("baglam") == "false"


def test_yerlesim_konumu_gecerli(pencere):
    g = pencere.izgara()
    k = g.nesne_yerlesim_konumu((300, 200))
    assert k.satir >= 1 and k.sutun >= 1 and k.dx >= 0 and k.dy >= 0
