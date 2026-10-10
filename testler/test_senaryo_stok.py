"""Faz 5 gerçek iş senaryosu: stok listesi (CLAUDE.md "her faz sonunda gerçek iş senaryosu").

Kullanıcı gibi davranır: stok girer, adlandırılmış fiyat tablosundan fiyat çeker, kategoriyi doğrulamalı açılır
listeyle girer, kritik stoğu koşullu biçimle boyar, tutara göre sıralar, kategoriye göre süzer (ALTTOPLAM görünen
toplamı verir), not ekler, kaydeder, yeniden açar, geri alır, PDF'e basar. İkinci bölüm: başka bir programın
(openpyxl) yazdığı `testler/ornekler/stok.xlsx` — açılır, uyarısız yüklenir, kaydedilip yeniden açılınca aynıdır.
Gerçek Excel'de açma kullanıcıya kalır (`test.md` §15.4).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.io import xlsx_io
from tabcel.model.adres import Aralik
from tabcel.model.ad import TanimliAd
from tabcel.model.dogrulama import Dogrulama
from tabcel.model.filtre import DegerKosulu
from tabcel.model.komutlar import AdDegis
from tabcel.model.kosullu import KosulluKural
from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import StilYama
from tabcel.ui import yazdir
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere

ORNEKLER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ornekler")
URUNLER = [("Kulaklık", "Elektronik", 4, 350.0), ("Şarj aleti", "Elektronik", 25, 120.0), ("Çay", "Gıda", 60, 45.5),
           ("Kahve", "Gıda", 8, 210.0), ("Tişört", "Giyim", 30, 150.0), ("Çorap", "Giyim", 5, 35.0),
           ("Bisküvi", "Gıda", 90, 12.75), ("Mont", "Giyim", 12, 900.0)]


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def p(app):
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    fy = k.sayfa_ekle("Fiyatlar")
    for r, (u, _, _, f) in enumerate(URUNLER, start=2):
        fy.ata(r, 1, Hucre(u))
        fy.ata(r, 2, Hucre(f))
    pen = Pencere(k)
    pen.resize(1000, 600)
    pen.show()
    app.processEvents()
    pen.sekmeler.setCurrentIndex(0)
    app.processEvents()
    yield pen
    pen.hide()


def sut(g, c, ilk=2, son=9):
    return [g.sayfa.deger(r, c) for r in range(ilk, son + 1)]


def kur(p):
    """Başlık + ürünler + adlar + formüller; hepsi hücreye elle yazılmış gibi."""
    k, g = p.kitap, p.izgara()
    fy = k.sayfalar[1]
    p.yigin.calistir(AdDegis(k, None, TanimliAd("FiyatListesi", f"=[{fy.kimlik}]!$A$2:$B$9")))
    p.yigin.calistir(AdDegis(k, None, TanimliAd("KdvOrani", f"=[{k.sayfalar[0].kimlik}]!$G$2")))
    for c, b in enumerate(("Ürün", "Kategori", "Adet", "Birim fiyat", "Tutar", "KDV'li tutar"), start=1):
        assert g.hucre_gir(1, c, b)
    assert g.hucre_gir(1, 7, "KDV") and g.hucre_gir(2, 7, "0,2")
    for r, (u, kat, adet, _) in enumerate(URUNLER, start=2):
        assert g.hucre_gir(r, 1, u) and g.hucre_gir(r, 2, kat) and g.hucre_gir(r, 3, str(adet))
        assert g.hucre_gir(r, 4, f"=DÜŞEYARA(A{r};FiyatListesi;2;YANLIŞ)")
        assert g.hucre_gir(r, 5, f"=C{r}*D{r}")
        assert g.hucre_gir(r, 6, f"=E{r}*(1+KdvOrani)")
    assert g.hucre_gir(11, 1, "Görünen toplam") and g.hucre_gir(11, 5, "=ALTTOPLAM(109;E2:E9)")
    assert g.hucre_gir(12, 1, "Tüm toplam") and g.hucre_gir(12, 5, "=TOPLA(E2:E9)")
    return g


def toplam(g):
    return sum(a * f for _, _, a, f in URUNLER)


def test_formuller_adlar_ve_fiyat_tablosu(p):
    g = kur(p)
    assert sut(g, 4) == [f for *_, f in URUNLER]                                   # DÜŞEYARA + adlandırılmış aralık
    assert g.sayfa.deger(12, 5) == pytest.approx(toplam(g)) and g.sayfa.deger(11, 5) == pytest.approx(toplam(g))
    assert g.sayfa.deger(2, 6) == pytest.approx(4 * 350 * 1.2)                      # KdvOrani adı
    p.kitap.sayfalar[1].ata(2, 2, Hucre(400.0))                                      # fiyat tablosu değişince Stok güncellenir
    assert g.sayfa.deger(2, 4) == 400.0 and g.sayfa.deger(2, 5) == 1600.0


def test_dogrulamali_kategori_ve_adet(p):
    g = kur(p)
    g.sec((2, 2), (9, 2))
    assert p.dogrulama_ac(Dogrulama((), tur="liste", formul1="\"Elektronik,Gıda,Giyim\"",
                                    hata=(True, "durdur", "Kategori", "Listeden seçin")))
    g.sec((2, 3), (9, 3))
    assert p.dogrulama_ac(Dogrulama((), tur="tam_sayi", islec="arasinda", formul1="=0", formul2="=10000"))
    sorular = []
    g.dogrulama_soru = lambda dv: sorular.append(dv.hata[2]) or "iptal"
    assert g.hucre_gir(2, 2, "Oyuncak") and g.sayfa.deger(2, 2) == "Elektronik"      # geçersiz: yazılmadı
    assert g.hucre_gir(3, 3, "-5") and g.sayfa.deger(3, 3) == 25.0
    assert g.hucre_gir(3, 3, "7") and g.sayfa.deger(3, 3) == 7.0 and sorular == ["Kategori", ""]
    g.sec((4, 2))
    assert g.acilir_liste_ogeleri() == ["Elektronik", "Gıda", "Giyim"]
    assert g.acilir_liste_sec("giyim") and g.sayfa.deger(4, 2) == "giyim"             # büyük/küçük harf duyarsız


def test_kritik_stok_koşullu_biçim_ve_tutar_cubugu(p, app):
    g = kur(p)
    g.sec((2, 3), (9, 3))
    assert p.kosullu_kural_ac(sonuc=KosulluKural((), tur="hucre_degeri", islec="kucuk", formul1="=10",
                                                  bicim=StilYama(dolgu="#FFC7CE", yazi_rengi="#9C0006")))
    g.sec((2, 5), (9, 5))
    assert p.kosullu_hazir("veri_cubugu", "mavi")
    hesap = g._kosullu_hesap()
    boyali = [r for r in range(2, 10) if hesap.hucre(r, 3)[0] is not None]
    assert boyali == [2, 5, 7]                                                         # adet < 10: Kulaklık, Kahve, Çorap
    assert [r for r in range(2, 10) if hesap.hucre(r, 5)[1] is not None] == list(range(2, 10))
    g.hucre_gir(2, 3, "50")                                                            # stok girilince biçim kalkar
    assert g._kosullu_hesap().hucre(2, 3)[0] is None
    g.geri_al()
    assert g._kosullu_hesap().hucre(2, 3)[0] is not None


def test_sirala_filtrele_alttoplam_ve_notlar(p):
    g = kur(p)
    g.sec((9, 1))
    g.not_yaz({(9, 1): Not("Sezon sonu: fiyat güncellenecek", "Ata")})                  # Mont
    g.sec((2, 5))
    assert p.sirala_hizli(False)                                                       # Tutar azalan, başlık tahmini
    tutarlar = sut(g, 5)
    assert tutarlar == sorted(tutarlar, reverse=True) and g.sayfa.deger(1, 5) == "Tutar"
    assert g.sayfa.deger(2, 1) == "Mont" and g.sayfa.notlar == {(2, 1): Not("Sezon sonu: fiyat güncellenecek", "Ata")}
    assert g.sayfa.hucre(2, 5).formul == "=C2*D2"                                      # formül satırla birlikte kaydı
    assert g.sayfa.deger(12, 5) == pytest.approx(toplam(g))                            # sıralama toplamı değiştirmez
    # kategoriye göre süz: yalnız Gıda
    g.sec((2, 1))
    assert p.filtre_ac_kapat()
    assert p.filtre_kosulu_uygula(2, DegerKosulu(frozenset({"Gıda"})))
    gida = sum(a * f for _, kat, a, f in URUNLER if kat == "Gıda")
    assert sorted(g.sayfa.gizli_satir) and len(g.sayfa.gizli_satir) == 5
    assert g.sayfa.deger(11, 5) == pytest.approx(gida)                                 # ALTTOPLAM yalnız görünenleri toplar
    assert g.sayfa.deger(12, 5) == pytest.approx(toplam(g))                            # TOPLA hepsini
    g.sec((2, 5), (9, 5))
    p._ozet_guncelle()
    assert f"Toplam: {gida:g}".replace(".", ",") in p.ozet_etiketi.text() or "Toplam" in p.ozet_etiketi.text()
    assert p.filtre_kosulu_uygula(2, None)                                             # koşulu kaldır
    assert g.sayfa.gizli_satir == set() and g.sayfa.deger(11, 5) == pytest.approx(toplam(g))


def test_kaydet_yeniden_ac_geri_al_ve_pdf(p, tmp_path):
    g = kur(p)
    g.sec((2, 2), (9, 2))
    p.dogrulama_ac(Dogrulama((), tur="liste", formul1="\"Elektronik,Gıda,Giyim\""))
    g.sec((2, 3), (9, 3))
    p.kosullu_kural_ac(sonuc=KosulluKural((), tur="hucre_degeri", islec="kucuk", formul1="=10",
                                           bicim=StilYama(dolgu="#FFC7CE")))
    g.not_yaz({(9, 1): Not("Not", "Ata")})
    g.sec((2, 5))
    p.sirala_hizli(False)
    g.sec((2, 1))
    p.filtre_ac_kapat()
    p.filtre_kosulu_uygula(2, DegerKosulu(frozenset({"Gıda", "Giyim"})))
    yol = str(tmp_path / "stok.xlsx")
    assert not xlsx_io.kaydet(p.kitap, yol).uyarilar
    k2, rapor = xlsx_io.ac(yol)
    assert not rapor.uyarilar
    s1, s2 = p.kitap.sayfalar[0], k2.sayfalar[0]
    assert s2.filtre == s1.filtre and s2.gizli_satir == s1.gizli_satir and s2.notlar == s1.notlar
    assert s2.dogrulamalar == s1.dogrulamalar and s2.kosullu == s1.kosullu
    assert sorted(a[1] for a in k2.adlar) == ["fiyatlistesi", "kdvorani"]
    from tabcel.formul.motor import Hesaplayici
    Hesaplayici(k2)
    assert [s2.deger(r, 5) for r in range(2, 10)] == [s1.deger(r, 5) for r in range(2, 10)]
    assert s2.deger(11, 5) == pytest.approx(s1.deger(11, 5)) and s2.deger(2, 4) == s1.deger(2, 4)
    # geri al: filtre koşulu → filtre → sıralama (3 adım); not ve kurallar yerinde kalır
    for _ in range(3):
        g.geri_al()
    assert s1.filtre is None and s1.gizli_satir == set() and s1.notlar == {(9, 1): Not("Not", "Ata")}
    g.geri_al()
    assert s1.notlar == {}
    # PDF: filtreli, koşullu biçimli, notlu sayfa yazdırılır
    assert yazdir.pdf_yaz([g], str(tmp_path / "stok.pdf")) and os.path.getsize(tmp_path / "stok.pdf") > 1000


# ------------------------------------------------------------------ başka programın yazdığı örnek dosya
def test_ornek_dosya_stok_xlsx_gidis_donus(tmp_path):
    k, rapor = xlsx_io.ac(os.path.join(ORNEKLER, "stok.xlsx"))
    assert not rapor.uyarilar and not rapor.veri_kaybi                               # Faz 5 öğeleri artık korunuyor
    s = k.sayfalar[0]
    assert s.filtre.aralik == Aralik(1, 1, 9, 5) and s.filtre.kosullar == {
        2: DegerKosulu(frozenset({"Gıda", "Giyim"}), False)}
    assert s.gizli_satir == {2, 3} and s.notlar[(9, 1)].yazar == "Ata"
    assert {d.tur for d in s.dogrulamalar} == {"liste", "tam_sayi"}
    assert {x.tur for x in s.kosullu} == {"hucre_degeri", "veri_cubugu", "renk_olcegi"}
    assert s.dogrulama(3, 2).hata[2] == "Kategori" and s.dogrulama(3, 2).formul1 == '"Elektronik,Gıda,Giyim"'
    assert sorted(a[1] for a in k.adlar) == ["fiyatlistesi", "kdvorani"] and s.dondur == (2, 1)
    from tabcel.formul.motor import Hesaplayici
    Hesaplayici(k)
    assert s.deger(11, 5) == pytest.approx(sum(a * f for _, kat, a, f in URUNLER if kat != "Elektronik"))   # ALTTOPLAM(109)
    assert s.deger(12, 5) == pytest.approx(sum(a * f for _, _, a, f in URUNLER))
    assert s.deger(5, 8) == 210.0 and s.deger(2, 6) == pytest.approx(4 * 350 * 1.2)   # DÜŞEYARA + KdvOrani
    yol = str(tmp_path / "stok_kopya.xlsx")
    assert not xlsx_io.kaydet(k, yol).uyarilar
    k2, r2 = xlsx_io.ac(yol)
    s2 = k2.sayfalar[0]
    assert not r2.uyarilar and s2.filtre == s.filtre and s2.gizli_satir == s.gizli_satir
    assert s2.dogrulamalar == s.dogrulamalar and s2.kosullu == s.kosullu and s2.notlar == s.notlar
    assert k2.adlar.keys() == k.adlar.keys() and s2.dondur == s.dondur


def test_ornek_dosya_degismez(tmp_path):
    import hashlib
    yol = os.path.join(ORNEKLER, "stok.xlsx")
    once = hashlib.md5(open(yol, "rb").read()).hexdigest()
    k, _ = xlsx_io.ac(yol)
    xlsx_io.kaydet(k, str(tmp_path / "baska.xlsx"))
    assert hashlib.md5(open(yol, "rb").read()).hexdigest() == once
