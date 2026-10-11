"""Faz 8f: “Ne yapmak istiyorsun?” asistanı (formul/asistan.py, ui/asistan_penceresi.py). Cümle → öneri → komut; uygulanan
sonuçlar motorla hesaplatılıp doğrulanır."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from tabcel.formul import asistan
from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import Aralik
from tabcel.model.komutlar import GeriAlYigini
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.asistan_penceresi import AsistanPenceresi
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere

VERI = [("Bölge", "Ürün", "Adet", "Tutar"),
        ("Kuzey", "Çay", 3, 30), ("Güney", "Şeker", 5, 25), ("Kuzey", "Şeker", 2, 10),
        ("Güney", "Çay", 4, 48), ("Kuzey", "Çay", 1, 10), ("Doğu", "Çay", 7, 70)]


def kur(veri=VERI):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, satir in enumerate(veri, 1):
        for j, v in enumerate(satir, 1):
            if v is not None:
                s.ata(i, j, Hucre(float(v) if isinstance(v, int) else v))
    m = Hesaplayici(k)
    return k, s, m, asistan.tablo_oku(s, Aralik(2, 2, 2, 2))


def anla(tablo, cumle, etkin=(1, 9)):
    return asistan.anla(cumle, tablo, etkin)


def tek(tablo, cumle):
    r = anla(tablo, cumle)
    assert len(r.oneriler) == 1, (cumle, r.mesaj)
    return r.oneriler[0]


def uygula(k, s, o):
    y = GeriAlYigini()
    y.calistir(o.komut(k, s))
    return y


# ---------------------------------------------------------------- tablo okuma
def test_tablo_tek_hucreden_veri_bolgesi_ve_turler():
    _, _, _, t = kur()
    assert t.aralik == Aralik(1, 1, 7, 4) and t.basliklar == ["Bölge", "Ürün", "Adet", "Tutar"]
    assert t.sayisal == [False, False, True, True]
    assert set(t.metin_degerleri[0]) == {"kuzey", "guney", "dogu"}
    assert t.kol(3) == "$D$2:$D$7" and t.veri() == "$A$2:$D$7"


def test_tablo_secimden():
    k, s, _, _ = kur()
    t = asistan.tablo_oku(s, Aralik(1, 2, 4, 3))
    assert t.basliklar == ["Ürün", "Adet"] and t.aralik == Aralik(1, 2, 4, 3)


# ---------------------------------------------------------------- cümle → formül (Türkçe görünüm + hesaplanan değer)
TEK_DEGER = [
    ("Tutar sütununun toplamı", "=TOPLA($D$2:$D$7)", 193.0),
    ("tutarların toplamı", "=TOPLA($D$2:$D$7)", 193.0),                       # çoğul/ek, küçük harf
    ("TUTAR TOPLAMI", "=TOPLA($D$2:$D$7)", 193.0),
    ("Adet ortalaması", "=ORTALAMA($C$2:$C$7)", 22 / 6),
    ("En yüksek tutar", "=MAK($D$2:$D$7)", 70.0),
    ("en düşük tutar", "=MİN($D$2:$D$7)", 10.0),
    ("Kuzey bölgesinin toplam tutarı", '=ETOPLA($A$2:$A$7;"Kuzey";$D$2:$D$7)', 50.0),
    ("Kuzey ve çay için adet toplamı", '=ÇOKETOPLA($C$2:$C$7;$A$2:$A$7;"Kuzey";$B$2:$B$7;"Çay")', 4.0),
    ("Çay ürününün adet toplamı", '=ETOPLA($B$2:$B$7;"Çay";$C$2:$C$7)', 15.0),   # `Adet` sütun adı “adet” (say) sayılmaz
    ("Kaç tane çay var", '=EĞERSAY($B$2:$B$7;"Çay")', 4.0),
    ("Tutarı 20'den büyük satış sayısı", '=EĞERSAY($D$2:$D$7;">20")', 4.0),
    ("Kaç kayıt var", "=BAĞ_DEĞ_DOLU_SAY($A$2:$A$7)", 6.0),
    ("Güney bölgesinde en yüksek tutar", '=MAK(FİLTRE($D$2:$D$7;($A$2:$A$7="Güney")))', 48.0),
    ("Güney bölgesi tutar ortalaması", '=EĞERORTALAMA($A$2:$A$7;"Güney";$D$2:$D$7)', 36.5),
]


@pytest.mark.parametrize("cumle, formul, deger", TEK_DEGER)
def test_tek_deger_onerileri(cumle, formul, deger):
    k, s, m, t = kur()
    o = tek(t, cumle)
    assert o.onizleme == formul and o.hedef == (1, 9)
    uygula(k, s, o)
    assert s.deger(*o.hedef) == pytest.approx(deger)


# ---------------------------------------------------------------- listeleme / sıralama / en yüksek N / benzersiz / tekrar
def blok(s, r1, c1, r2, c2):
    return [[s.deger(r, c) for c in range(c1, c2 + 1)] for r in range(r1, r2 + 1)]


def test_filtre_listeleme():
    k, s, m, t = kur()
    o = tek(t, "Tutarı 20'den büyük olanları listele")
    assert o.onizleme == '=FİLTRE($A$2:$D$7;($D$2:$D$7>20);"Sonuç yok")'
    uygula(k, s, o)
    assert [r[0] for r in blok(s, 1, 9, 3, 12)] == ["Kuzey", "Güney", "Güney"] and s.deger(4, 9) is not None
    o2 = tek(t, "Güney bölgesindekileri göster")
    assert 'FİLTRE' in o2.onizleme and '"Güney"' in o2.onizleme


def test_en_yuksek_n_ve_siralama():
    k, s, m, t = kur()
    o = tek(t, "En yüksek 3 tutarı göster")
    assert o.onizleme == "=AL(SIRALA($A$2:$D$7;4;-1);3)"
    uygula(k, s, o)
    assert [r[3] for r in blok(s, 1, 9, 3, 12)] == [70.0, 48.0, 30.0]
    o = tek(t, "Tutara göre büyükten küçüğe sırala")                       # “göre” gruplama sanılmaz
    assert o.onizleme == "=SIRALA($A$2:$D$7;4;-1)"
    o = tek(t, "ürüne göre sırala")
    assert o.onizleme == "=SIRALA($A$2:$D$7;2;1)"
    o = tek(t, "En düşük 2 adet")
    assert o.onizleme == "=AL(SIRALA($A$2:$D$7;3;1);2)"


def test_benzersiz_ve_tekrar():
    k, s, m, t = kur()
    uygula(k, s, tek(t, "Ürünlerin benzersiz listesi"))
    assert [s.deger(r, 9) for r in (1, 2, 3)] == ["Çay", "Şeker", None]
    k, s, m, t = kur()
    uygula(k, s, tek(t, "Tekrar eden bölgeler"))
    assert [s.deger(r, 9) for r in (1, 2, 3)] == ["Kuzey", "Güney", None]


def test_ortalamanin_ustu():
    k, s, m, t = kur()
    o = tek(t, "Ortalamanın üstünde olan tutarlar")
    uygula(k, s, o)
    assert [r[3] for r in blok(s, 1, 9, 2, 12)] == [48.0, 70.0]               # ortalama 32,17


# ---------------------------------------------------------------- gruplama → Özet Tablo
def test_gruplama_ozet_tablo():
    k, s, m, t = kur()
    o = tek(t, "Bölgeye göre toplam satış tutarı")
    assert o.hedef is None and "Satırlar: Bölge" in o.onizleme and "Toplam - Tutar" in o.onizleme
    uygula(k, s, o)
    ozet = k.sayfalar[1]
    assert ozet.ad == "Özet Tablo" and ozet.deger(2, 1) == "Doğu" and ozet.deger(2, 2) == 70.0
    o = tek(t, "Bölge ve ürüne göre ortalama tutar")
    assert "Sütunlar: Ürün" in o.onizleme and "Ortalama - Tutar" in o.onizleme
    o = tek(t, "Her bölge için toplam tutar")
    assert "Satırlar: Bölge" in o.onizleme
    o = tek(t, "Ürüne göre kaç adet var")
    assert "Sayı - Adet" in o.onizleme
    o = tek(t, "Bölge bazında en yüksek tutar")
    assert "Maks - Tutar" in o.onizleme


def test_gruplama_ikinci_kez_yeni_sayfa_adi():
    k, s, m, t = kur()
    uygula(k, s, tek(t, "Bölgeye göre toplam tutar"))
    uygula(k, s, tek(t, "Ürüne göre toplam tutar"))
    assert [x.ad for x in k.sayfalar] == ["Sayfa1", "Özet Tablo", "Özet Tablo2"]


# ---------------------------------------------------------------- yeni sütun
def test_yeni_sutun_pay_degisim_kumulatif():
    k, s, m, t = kur()
    uygula(k, s, tek(t, "Her ürünün toplamdaki payı tutar"))
    assert s.deger(1, 5) == "Tutar Payı" and s.deger(2, 5) == pytest.approx(30 / 193) and s.stil(2, 5).sayi_bicimi == "0.0%"
    assert s.stil(1, 5).kalin
    k, s, m, t = kur()
    uygula(k, s, tek(t, "Tutarın değişimi"))
    assert s.deger(1, 5) == "Tutar Değişimi" and s.hucre(2, 5) is None and s.deger(3, 5) == pytest.approx(-5 / 30)
    k, s, m, t = kur()
    uygula(k, s, tek(t, "Kümülatif tutar"))
    assert [s.deger(r, 5) for r in (2, 3, 7)] == [30.0, 55.0, 193.0]


def test_geri_al_tek_adim():
    k, s, m, t = kur()
    y = uygula(k, s, tek(t, "Kümülatif tutar"))
    y.geri_al()
    assert s.hucre(1, 5) is None and s.hucre(7, 5) is None


# ---------------------------------------------------------------- hedef
def test_hedef_secimi():
    k, s, m, t = kur()
    assert asistan.hedef_bul(s, t, (3, 8)) == (3, 8)                       # etkin hücre boş ve tablo dışı
    assert asistan.hedef_bul(s, t, (3, 2)) == (1, 6)                       # tablonun içinde: sağındaki ilk boş sütun
    s.ata(1, 6, Hucre("dolu"))
    assert asistan.hedef_bul(s, t, None) == (1, 7)
    assert asistan.hedef_bul(s, t, (1, 6)) == (1, 7)                       # etkin hücre dolu


# ---------------------------------------------------------------- anlaşılmayanlar tahmin edilmez
@pytest.mark.parametrize("cumle", ["hava nasıl", "Adet", "   ", "Şeker sütununu topla ama", "xyzzy"])
def test_anlasilmayan_cumle_mesaj_verir(cumle):
    _, _, _, t = kur()
    r = anla(t, cumle)
    assert not r.oneriler and r.mesaj


def test_mesajlar_sutunlari_ve_ornekleri_soyler():
    _, _, _, t = kur()
    m = anla(t, "bir şey yap").mesaj
    assert "Bölge, Ürün, Adet, Tutar" in m and "Örnek" in m
    assert "Hangi sütuna göre sıralanacağını" in anla(t, "sırala").mesaj
    assert "Neye göre gruplanacağını" in anla(t, "göre toplam").mesaj
    assert asistan.ORNEKLER[0] in anla(t, "").mesaj


def test_ornek_cumleler_hepsi_anlasilir():
    """Örnek listesindeki her cümle, örneklerin varsaydığı başlıklara sahip bir tabloda öneri üretir (örnekler yalan söylemesin)."""
    _, _, _, t = kur([("Bölge", "Ürün", "Müşteri", "Satış", "Tutar"),
                      ("Kuzey", "Çay", "Ali", 3, 3000), ("Güney", "Şeker", "Ayşe", 5, 2500), ("Kuzey", "Şeker", "Ali", 2, 1000),
                      ("Güney", "Çay", "Veli", 4, 4800), ("Kuzey", "Çay", "Ali", 1, 1000)])
    for c in asistan.ORNEKLER:
        assert anla(t, c).oneriler, c


def test_turkce_harf_ve_ek_toleransi():
    _, _, _, t = kur()
    assert tek(t, "SATIŞ tutarlarının TOPLAMINI bul").onizleme == "=TOPLA($D$2:$D$7)"
    assert tek(t, "bolgeye gore toplam tutar").hedef is None                 # aksansız yazım
    assert "Doğu" not in tek(t, "kuzey bolgesinin toplam tutari").onizleme
    assert '"Kuzey"' in tek(t, "kuzey bolgesinin toplam tutari").onizleme


def test_bos_ve_tek_satirli_tablo():
    k, s, m, t = kur([("A", "B"), (1, 2)])
    assert tek(t, "B toplamı").onizleme == "=TOPLA($B$2:$B$2)"


# ---------------------------------------------------------------- arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k, _, _, _ = kur()
    p = Pencere(k)
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()
    DosyaIslemleri._tutulan.clear()


def test_pencere_oneri_ayrinti_uygula(app):
    k, s, m, t = kur()
    d = AsistanPenceresi(t, (1, 9))
    assert not d.uygula.isEnabled() and "Ne yapmak istediğinizi yazın" in d.ayrinti.text()
    d.girdi.setText("Tutar toplamı")
    d.sor()
    assert d.liste.count() == 1 and d.uygula.isEnabled()
    assert "=TOPLA($D$2:$D$7)" in d.ayrinti.text() and "Yazılacak yer: I1" in d.ayrinti.text()
    d.girdi.setText("hava nasıl")
    d.sor()
    assert d.liste.count() == 0 and not d.uygula.isEnabled() and "anlayamadım" in d.ayrinti.text()


def test_penceredeki_eylem_uygular_ve_secer(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((3, 2))

    def exec_(self):
        self.girdi.setText("Kuzey bölgesinin toplam tutarı")
        self.sor()
        return QDialog.Accepted
    monkeypatch.setattr(AsistanPenceresi, "exec", exec_)
    assert pencere.asistan_ac()
    assert g.sayfa.deger(1, 6) == 50.0 and g._aktif == (1, 6)           # seçim tablonun içinde: sağındaki ilk boş sütun
    g.geri_al()
    assert g.sayfa.hucre(1, 6) is None


def test_ozet_tablo_oneri_uygulaninca_yeni_sayfa(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((3, 2))
    monkeypatch.setattr(AsistanPenceresi, "exec", lambda self: (self.girdi.setText("Bölgeye göre toplam tutar"),
                                                                 self.sor(), QDialog.Accepted)[2])
    assert pencere.asistan_ac()
    assert [s.ad for s in pencere.kitap.sayfalar] == ["Sayfa1", "Özet Tablo"]


def test_tablo_yoksa_ileti_ve_iptal(app, monkeypatch):
    p = Pencere(CalismaKitabi())
    p.show()
    iletiler = []
    monkeypatch.setattr(QMessageBox, "information", lambda w, b, m, *a: iletiler.append(m))
    assert p.asistan_ac() is False and iletiler and "başlıklı bir tablo" in iletiler[0]
    p.degisti_mi = lambda: False
    p.close()


def test_eylem_ve_kisayol(pencere):
    a = pencere.eylemler["asistan"]
    assert a.text() == "Ne yapmak istiyorsun?" and "Alt+Q" in a.toolTip() and a in pencere.serit.eylemler()
