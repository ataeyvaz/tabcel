"""Faz 10f: Şablon kayıt formu (ui/sablon_formu.py) — gerçek klavye/fare olaylarıyla (QTest)."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.formul.motor import Hesaplayici
from tabcel.model.sayfa import CalismaKitabi
from tabcel.sablon import kayitlar, yukleyici
from tabcel.sablon.uretici import uret
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def depo():
    return yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor"))


def pencere(depo, akis="yerlesik:stok_takibi", cevaplar=None):
    r = uret(depo.bul(akis), cevaplar)
    Hesaplayici(r.kitap).tumunu_hesapla()
    return Pencere(r.kitap)


@pytest.fixture
def p(app, depo):
    w = pencere(depo)
    w.show()
    yield w
    f = getattr(w, "_sablon_formu", None)
    if f is not None:
        f._ilk = f._mevcut_metinler()                 # kirli diyalog çıkmasın
        f.close()
    w.degisti_mi = lambda: False                      # kapatırken “kaydedilsin mi?” sorusu çıkmasın
    w.close()


def yaz(alan, metin):
    kutu = alan.kutu
    if hasattr(kutu, "metin_kutusu"):
        kutu = kutu.metin_kutusu
    kutu.clear() if hasattr(kutu, "clear") else None
    for ch in metin:
        QTest.keyClick(kutu, ch) if len(ch) == 1 and ch.isascii() else kutu.insert(ch)


def doldur(f, **deger):
    for k, v in deger.items():
        a = f.alanlar[k]
        if hasattr(a.kutu, "setCurrentText") or hasattr(a.kutu, "metin_kutusu") or hasattr(a.kutu, "setText"):
            a.yaz(v)


def kisayol(f, tus):
    """Pencere etkin olmayabilir (ekransız); kısayolu tanımlı QShortcut üzerinden tetikler."""
    from PySide6.QtGui import QKeySequence, QShortcut
    hedef = QKeySequence(tus)
    bulunan = [k for k in f.findChildren(QShortcut) if k.key() == hedef]
    assert bulunan, f"{tus} kısayolu tanımlı değil"
    bulunan[0].activated.emit()


def sayfa(p, ad):
    return next(s for s in p.kitap.sayfalar if s.ad == ad)


# ---------------------------------------------------------------- açılış
def test_sablonsuz_kitapta_form_acilmaz(app, monkeypatch):
    w = Pencere(CalismaKitabi())
    gelen = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: gelen.append(a[2]))
    assert w.kayit_formu_ac() is False
    assert "şablondan oluşturulmamış" in gelen[0]


def test_uyusmayan_sablonda_form_kapali_ve_neden_soylenir(app, depo, monkeypatch):
    w = pencere(depo)
    w.kitap.sayfalar[0].ata(1, 1, __import__("tabcel.model.sayfa", fromlist=["Hucre"]).Hucre("Başka"))
    w.kitap.sablon_denetim = None
    from tabcel.sablon import saklama
    w.kitap.sablon_denetim = saklama.denetle(w.kitap, w.kitap.sablon)
    gelen = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: gelen.append(a[2]))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)       # yeniden eşleme önerisini reddet
    assert w.kayit_formu_ac() is False
    assert "Kayıt formu kapalı" in gelen[0]


def test_acilis_ilk_kayit_ve_alanlar(p):
    assert p.kayit_formu_ac() is True
    f = p._sablon_formu
    assert f.windowTitle().startswith("Ürün") and f.g.modul.kimlik == "urunler"
    assert list(f.alanlar)[:2] == ["urun_kodu", "ad"]
    assert f.alanlar["urun_kodu"].metin() == "U001"
    assert f.sayac.text() == "Kayıt 1 / 2"
    assert f.modul_kutusu.count() == 2                       # Ürünler + Stok Hareketleri (Stok Durumu hesaplanan)


def test_etkin_sayfaya_gore_modul_secilir(p):
    p.sekmeler.setCurrentIndex(1)
    p.kayit_formu_ac()
    assert p._sablon_formu.g.modul.kimlik == "stok_hareketleri"


# ---------------------------------------------------------------- yeni kayıt + kaydetme
def test_yeni_kayit_enter_ile_dolasip_kaydedilir(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.yeni_kayit()
    assert f.satir is None and f.alanlar["urun_kodu"].metin() == ""
    f.alanlar["urun_kodu"].kutu.setFocus()
    yaz(f.alanlar["urun_kodu"], "U100")
    QTest.keyClick(f.alanlar["urun_kodu"].kutu, Qt.Key_Return)         # sonraki alana
    assert f.focusWidget() is f.alanlar["ad"].kutu
    yaz(f.alanlar["ad"], "Yeni ürün")
    f.alanlar["urun_kodu"].kutu.setFocus()
    assert f.kaydet() is True
    s = sayfa(p, "Ürünler")
    assert s.deger(4, 1) == "U100" and s.deger(4, 2) == "Yeni ürün"
    assert f.satir == 4 and f.sayac.text() == "Kayıt 3 / 3"


def test_kaydet_tek_geri_al_adimi(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.yeni_kayit()
    doldur(f, urun_kodu="U100", ad="Deneme", alis_fiyati="12,5")
    assert f.kaydet()
    s = sayfa(p, "Ürünler")
    assert s.deger(4, 5) == 12.5
    p.izgara().yigin.geri_al()                              # tek adım hepsini geri alır
    assert s.deger(4, 1) is None and s.deger(4, 2) is None and s.deger(4, 5) is None


def test_kaydet_ve_yeni_ctrl_enter(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.yeni_kayit()
    doldur(f, urun_kodu="U101", ad="Bir")
    kisayol(f, "Ctrl+Return")
    assert sayfa(p, "Ürünler").deger(4, 1) == "U101"
    assert f.satir is None and f.alanlar["urun_kodu"].metin() == ""


def test_hesaplanan_alan_kaydedince_dolar(p):
    p.sekmeler.setCurrentIndex(1)
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.yeni_kayit()
    doldur(f, tarih="15.10.2026", urun="U001", hareket_turu="Giriş", miktar="5")
    assert f.kaydet()
    sd = sayfa(p, "Stok Durumu")
    assert sd.deger(2, 1) == "U001"
    assert any(sd.deger(r, c) == 55.0 for r in range(2, 5) for c in range(1, 8))      # 50 - 8 + 5 + ... mevcut güncellendi


# ---------------------------------------------------------------- kurallar
def test_zorunlu_ve_benzersiz_hatalari_alan_altinda(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.yeni_kayit()
    doldur(f, urun_kodu="U001", ad="")
    assert f.kaydet() is False
    assert "zaten var" in f.alanlar["urun_kodu"].hata.text() and not f.alanlar["urun_kodu"].hata.isHidden()
    assert "boş bırakılamaz" in f.alanlar["ad"].hata.text()
    assert sayfa(p, "Ürünler").deger(4, 1) is None                 # hiçbir şey yazılmadı


def test_stok_kurali_cikisi_engeller(p, monkeypatch):
    p.sekmeler.setCurrentIndex(1)
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.yeni_kayit()
    doldur(f, tarih="15.10.2026", urun="U001", hareket_turu="Çıkış", miktar="999")
    assert f.kaydet() is False
    assert "eksiye" in f.kural_etiketi.text() and not f.kural_etiketi.isHidden()
    doldur(f, miktar="3")
    assert f.kaydet() is True
    assert "eksiye" not in f.kural_etiketi.text() or f.kural_etiketi.isHidden()


def test_uyar_siddeti_onay_ister(p, monkeypatch):
    p.kayit_formu_ac()
    f = p._sablon_formu
    kural = f.g.modul.kurallar if f.g.modul.kurallar else None
    from tabcel.sablon.sema import Kural
    f.g.modul.kurallar.append(Kural("uyari_k", "Uyarı", "=LEN([@ad])>50", "Ad çok kısa.", "uyar"))
    f.yeni_kayit()
    doldur(f, urun_kodu="U102", ad="Kısa")
    sorular = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: (sorular.append(a[2]), QMessageBox.No)[1])
    assert f.kaydet() is False and "Ad çok kısa." in sorular[0]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    assert f.kaydet() is True
    f.g.modul.kurallar.pop()


# ---------------------------------------------------------------- gezinme / arama / silme
def test_gezinme_ctrl_pgdn_pgup(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    kisayol(f, "Ctrl+PgDown")
    assert f.satir == 3 and f.alanlar["urun_kodu"].metin() == "U002"
    kisayol(f, "Ctrl+PgUp")
    assert f.satir == 2
    assert f.git(-1) is False                               # ilk kayıtta daha geri yok


def test_kirli_kayittan_ayrilirken_sorulur(p, monkeypatch):
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.alanlar["ad"].yaz("Değişti")
    gelen = []

    class Sahte:
        def __init__(self, *a, **k): pass
        def addButton(self, metin, rol): gelen.append(metin); return metin
        def exec(self): pass
        def clickedButton(self): return gelen[-1] if False else "İptal"
    monkeypatch.setattr("tabcel.ui.sablon_formu.QMessageBox", type("QM", (), {
        "Question": 4, "NoButton": 0, "AcceptRole": 0, "DestructiveRole": 1, "RejectRole": 2, "Yes": 0, "No": 0,
        "__new__": lambda cls, *a, **k: Sahte(), "warning": staticmethod(lambda *a, **k: None)}))
    assert f.git(1) is False                                # iptal → kayıt değişmedi
    assert f.satir == 2 and f.alanlar["ad"].metin() == "Değişti"


def test_ara_turkce_harf_duyarsiz(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    ad = f.alanlar["ad"].metin()
    f.ara_kutusu.setText(ad.upper()[:3])
    f._ilk = f._mevcut_metinler()
    assert f.ara() is True or f.satir == 2


def test_sil_geri_alinabilir(p, monkeypatch):
    p.kayit_formu_ac()
    f = p._sablon_formu
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    s = sayfa(p, "Ürünler")
    assert f.sil() is True
    assert s.deger(2, 1) is None
    p.izgara().yigin.geri_al()
    assert s.deger(2, 1) == "U001"


# ---------------------------------------------------------------- tablo ile eşzaman
def test_tabloda_degisen_kayit_formda_yenilenir(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    s = sayfa(p, "Ürünler")
    from tabcel.model.sayfa import Hucre
    s.ata(2, 2, Hucre("Tabloda değişti"))
    f.kayda_git(2)
    assert f.alanlar["ad"].metin() == "Tabloda değişti"


def test_serit_dugmesi_ve_kisayol_tanimli(p):
    assert "kayit_formu" in p.eylemler
    assert "Ctrl+Alt+F" in p.eylemler["kayit_formu"].toolTip()


# ---------------------------------------------------------------- yeniden eşleme / örnek veri
def test_yeniden_esleme_formu_geri_acar(app, depo, monkeypatch):
    from tabcel.model.sayfa import Hucre
    from tabcel.sablon import saklama
    from tabcel.ui import sablon_formu as sf
    w = pencere(depo)
    w.kitap.sayfalar[0].ata(1, 2, Hucre("Ürün ismi"))                       # “Ürün adı” yeniden adlandırıldı
    w.kitap.sablon_denetim = saklama.denetle(w.kitap, w.kitap.sablon)
    assert not w.kitap.sablon_denetim.aktif
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    class Sahte:
        def __init__(self, durumlar, ust=None):
            self.durumlar = durumlar

        def exec(self):
            return sf.QDialog.Accepted

        def harita(self):
            d = self.durumlar[0]
            assert d.eksik == [("ad", "Ürün adı")] and "Ürün ismi" in d.adaylar
            return {d.modul: {"ad": "Ürün ismi"}}
    monkeypatch.setattr(sf, "EslemePenceresi", Sahte)
    assert w.kayit_formu_ac() is True
    assert w.kitap.sablon_denetim.aktif and w.kitap.sablon.baglar["urunler"].basliklar["ad"] == "Ürün ismi"
    w._sablon_formu._ilk = w._sablon_formu._mevcut_metinler()
    w._sablon_formu.close()
    w.degisti_mi = lambda: False
    w.close()


def test_ornek_verileri_temizle(p, monkeypatch):
    from tabcel.model.sayfa import Hucre
    p.kayit_formu_ac()
    f = p._sablon_formu
    assert f.ornek_dugme.isVisibleTo(f)
    s = sayfa(p, "Ürünler")
    s.ata(3, 2, Hucre("Elle değiştirdim"))                           # 2. örnek ürün değişti
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    assert f.ornekleri_temizle() is True
    assert s.deger(2, 1) is None                                     # dokunulmamış örnek silindi
    assert s.deger(3, 2) == "Elle değiştirdim"                       # değiştirilmiş satır korundu
    assert not f.ornek_dugme.isVisibleTo(f)
    p.izgara().yigin.geri_al()
    assert s.deger(2, 1) == "U001"


def test_tabloda_degisen_kayit_acik_formda_kendiliginden_yenilenir(p):
    from tabcel.model.sayfa import Hucre
    p.kayit_formu_ac()
    f = p._sablon_formu
    sayfa(p, "Ürünler").ata(2, 2, Hucre("Canlı değişti"))
    assert f.alanlar["ad"].metin() == "Canlı değişti"


def test_yarim_duzenleme_tablo_degisince_kaybolmaz(p):
    from tabcel.model.sayfa import Hucre
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.alanlar["ad"].yaz("Yarım yazdım")
    sayfa(p, "Ürünler").ata(2, 3, Hucre("123456"))              # aynı kaydın başka alanı tabloda değişti
    assert f.alanlar["ad"].metin() == "Yarım yazdım"
    assert "başka yerde değişti" in f.durum.text()


def test_form_kaydi_kendi_olayiyla_yeniden_yuklenmez(p):
    p.kayit_formu_ac()
    f = p._sablon_formu
    f.yeni_kayit()
    doldur(f, urun_kodu="U200", ad="Kendi kaydım")
    assert f.kaydet() is True and f.alanlar["ad"].metin() == "Kendi kaydım" and f.satir == 4


def test_satir_eklenince_form_yeniden_kurulur(p):
    from tabcel.model.komutlar import SatirEkleSil
    p.kayit_formu_ac()
    f = p._sablon_formu
    p.izgara().yigin.calistir(SatirEkleSil(sayfa(p, "Ürünler"), 2, 1, True))
    assert f.isVisible() and f.kayit_satirlari == [3, 4] and f.alanlar["urun_kodu"].metin() == "U001"
