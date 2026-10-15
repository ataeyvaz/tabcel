"""Faz 10d: Şablon Sihirbazı penceresi (ui/sablon_sihirbazi.py): serbest metinden öneri, kategori düğmeleri, sorular, emin değilim,
önizleme, Oluştur, Şablonlar penceresi (yükleme raporu), Dosya menüsünden yeni pencere."""
import json
import os
import shutil
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from tabcel.formul.motor import Hesaplayici
from tabcel.sablon import saklama, yukleyici
from tabcel.ui import sablon_sihirbazi as ss
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere
from tabcel.model.sayfa import CalismaKitabi


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def depo():
    return yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor"))


@pytest.fixture
def d(app, depo):
    p = ss.SihirbazPenceresi(depo)
    p.show()
    p.sec_sablon("yerlesik:stok_takibi")                      # 6 yerleşik akış var; testlerin çoğu Stok takibi üzerinden
    yield p
    p.close()


def gorunen(liste):
    return [liste.item(i).text() for i in range(liste.count())]


def test_acilis_tum_sablonlar_listelenir(app, depo):
    p = ss.SihirbazPenceresi(depo)
    p.show()
    assert p.liste.count() == 6
    assert gorunen(p.liste)[0].startswith("Apartman / site aidat takibi  —  ")               # ad sırası: yerleşik akışlar
    assert any(t.startswith("Stok takibi  —  Ürünlerin giriş-çıkışını") for t in gorunen(p.liste))
    assert p.secili is not None and p.secili.ic_kimlik == "yerlesik:apartman_aidat"          # ilki seçili
    assert p.yigin.currentIndex() == ss.SAYFA_SECIM and p.ileri.isEnabled() and not p.geri.isVisible() and not p.olustur.isVisible()
    assert set(p.kategori_dugmeleri) == {None, "Eğitim", "Finans", "Satış", "Site ve Apartman", "Ticaret"}
    p.close()


def test_serbest_metin_oneri(d):
    d.girdi.setText("stoklarımı takip etmek istiyorum")
    assert gorunen(d.liste) == ["Stok takibi  —  Ürünlerin giriş-çıkışını ve anlık stok durumunu izleyin."]
    assert d.liste_basligi.text().startswith("Size uygun") and d.secili.ic_kimlik == "yerlesik:stok_takibi"
    d.girdi.setText("sitemizin aidatlarını takip etmek istiyorum")
    assert d.secili.ic_kimlik == "yerlesik:apartman_aidat"
    d.girdi.setText("müşterilere teklif hazırlamak istiyorum")
    assert d.secili.ic_kimlik == "yerlesik:teklif_formu"
    d.girdi.setText("bugün hava güzel")
    assert d.liste_basligi.text().startswith("Eşleşen şablon bulunamadı") and d.liste.count() == 6
    d.girdi.setText("")
    assert not d.liste_basligi.isVisible()


def test_kategori_dugmeleri(d):
    d.kategori_sec("Ticaret")
    assert d.kategori_dugmeleri["Ticaret"].isChecked() and not d.kategori_dugmeleri[None].isChecked()
    assert d.liste_basligi.text() == "Ticaret şablonları:" and d.liste.count() == 2            # Stok takibi + Cari hesap
    d.kategori_dugmeleri[None].click()
    assert d.kategori_dugmeleri[None].isChecked() and not d.kategori_dugmeleri["Ticaret"].isChecked() and d.liste.count() == 6


def test_sorular_varsayilan_ve_emin_degilim(d):
    d.ileri.click()
    assert d.yigin.currentIndex() == ss.SAYFA_SORULAR and d.geri.isVisible()
    assert list(d.soru_kutulari) == ["varyant", "depo", "fiyat", "cari"]
    assert d.cevaplar() == {"varyant": False, "depo": False, "fiyat": True, "cari": False}
    assert list(d.emin_kutulari) == ["fiyat"]                                              # yalnız emin_degilim:true olan soruda
    d.soru_kutulari["fiyat"].setChecked(False)
    d.emin_kutulari["fiyat"].setChecked(True)                                             # "siz seçin" → önerilen cevap (Evet)
    assert d.cevaplar()["fiyat"] is True and not d.soru_kutulari["fiyat"].isEnabled()
    d.emin_kutulari["fiyat"].setChecked(False)
    assert d.soru_kutulari["fiyat"].isEnabled()


def test_onizleme_ve_olustur(d):
    d.ileri.click()
    d.soru_kutulari["depo"].setChecked(True)
    d.ileri.click()
    assert d.yigin.currentIndex() == ss.SAYFA_ONIZLEME and d.olustur.isVisible() and not d.ileri.isVisible()
    adlar = [d.sayfa_secici.itemText(i) for i in range(d.sayfa_secici.count())]
    assert adlar == ["Ürünler", "Stok Hareketleri", "Stok Durumu", "Depolar", "Ayarlar", "Nasıl Kullanılır"]
    assert "6 sayfa oluşturulacak" in d.onizleme_basligi.text()
    assert d.onizleme_tablosu.horizontalHeaderItem(0).text() == "Ürün kodu" and d.onizleme_tablosu.item(0, 0).text() == "U001"
    d.sayfa_secici.setCurrentIndex(2)                                                    # Stok Durumu: formüller ƒ
    assert d.onizleme_tablosu.item(0, 1).text() == "ƒ"
    assert d.ornek_kutusu.isChecked()
    d.ornek_kutusu.setChecked(False)
    d.olustur.click()
    assert d.result() == QDialog.Accepted and d.sonuc is not None
    k = d.sonuc.kitap
    assert [s.ad for s in k.sayfalar][:4] == ["Ürünler", "Stok Hareketleri", "Stok Durumu", "Depolar"]
    assert k.sayfalar[0].deger(2, 1) is None                                              # örnek veri kapalı
    assert k.sablon is not None and k.sablon.cevaplar["depo"] is True


def test_geri_gezinme(d):
    d.ileri.click(); d.ileri.click()
    d.geri.click()
    assert d.yigin.currentIndex() == ss.SAYFA_SORULAR
    d.geri.click()
    assert d.yigin.currentIndex() == ss.SAYFA_SECIM and d.secili is not None


def test_eger_ile_gizlenen_soru(app, depo):
    from copy import deepcopy
    sb = deepcopy(depo.bul("yerlesik:stok_takibi"))
    sb.akis.sorular[3].eger = "depo"                                                      # cari sorusu yalnız depo=Evet iken
    d2 = ss.SihirbazPenceresi(type(depo)([sb], depo.rapor))
    d2.show()
    d2.ileri.click()
    assert d2.soru_satirlari["cari"].isHidden()
    d2.soru_kutulari["depo"].setChecked(True)
    assert not d2.soru_satirlari["cari"].isHidden()
    d2.soru_kutulari["cari"].setChecked(True)
    d2.soru_kutulari["depo"].setChecked(False)                                            # depo kapanınca cari gizlenir, cevabı sayılmaz
    assert d2.soru_satirlari["cari"].isHidden()
    d2.ileri.click()
    d2.olustur.click()
    assert d2.sonuc.bayraklar["cari_takibi"] is False
    d2.close()


def test_uretim_hatasi_kullaniciya_gosterilir(d, monkeypatch):
    iletiler = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: iletiler.append(a[2]))
    monkeypatch.setattr(ss, "uret", lambda *a, **k: (_ for _ in ()).throw(ss.UretimHatasi("kapalı sütun")))
    d.ileri.click()
    d.ileri.click()
    assert iletiler == ["kapalı sütun"] and d.yigin.currentIndex() == ss.SAYFA_SORULAR


def test_sablonlar_penceresi_hatali_dosya_raporu(app, tmp_path, monkeypatch):
    kul = tmp_path / "kul"
    (kul / "akislar").mkdir(parents=True)
    (kul / "akislar" / "bozuk.json").write_text("{kapanmamis", encoding="utf-8")
    monkeypatch.setattr(yukleyici, "kullanici_klasoru", lambda: kul)
    depo = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), kul)
    p = ss.SablonlarPenceresi(depo, lambda: yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), kul))
    assert p.liste.count() == 6 and "yerleşik" in p.liste.item(0).text()
    assert "kullanici/akislar/bozuk.json — JSON bozuk" in p.rapor.toPlainText()
    # kullanıcı hatayı düzeltip Yenile'ye basar
    shutil.copy(yukleyici.yerlesik_klasor() / "akislar" / "stok_takibi.json", kul / "akislar" / "bozuk.json")
    shutil.copytree(yukleyici.yerlesik_klasor() / "moduller", kul / "moduller")
    p.yenile.click()
    assert p.liste.count() == 7 and "(benim sürümüm)" in p.liste.item(6).text() and "sizin" in p.liste.item(6).text()
    assert "sorun yok" in p.rapor.toPlainText() or "yüklendi" in p.rapor.toPlainText() or p.rapor.toPlainText() == ""


def test_sihirbaz_kullanici_sablonunu_gosterir(app, tmp_path, monkeypatch):
    kul = tmp_path / "kul"
    shutil.copytree(yukleyici.yerlesik_klasor(), kul)
    a = json.loads((kul / "akislar" / "stok_takibi.json").read_text(encoding="utf-8"))
    a["kimlik"], a["kategori"], a["ad"] = "benim_stok", "Benim", "Benim stoğum"
    (kul / "akislar" / "stok_takibi.json").unlink()
    (kul / "akislar" / "benim.json").write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(yukleyici, "kullanici_klasoru", lambda: kul)
    monkeypatch.setattr(yukleyici, "yerlesik_klasor", lambda: yukleyici.resource_dir() / "tabcel" / "sablonlar")
    d = ss.SihirbazPenceresi(None)
    assert {"Benim", "Ticaret"} <= set(d.kategori_dugmeleri)
    assert d.sec_sablon("kullanici:benim_stok") and d.secili.etiket == "Benim stoğum"
    d.close()


# ---------------------------------------------------------------- Dosya menüsü: yeni pencere
@pytest.fixture
def ana(app):
    p = Pencere(CalismaKitabi())
    p.resize(1200, 700)
    p.show()
    yield p
    for x in list(DosyaIslemleri._tutulan) + [p]:
        x.degisti_mi = lambda: False
        x.close()
    DosyaIslemleri._tutulan.clear()


def test_dosya_menusunde_sablondan_yeni(ana, monkeypatch):
    assert "dosya.sablondan_yeni" in ana.eylemler and ana.eylemler["dosya.sablondan_yeni"].text() == "Şablondan Yeni…"
    depo = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor"))
    d = ss.SihirbazPenceresi(depo, ana)
    d.sec_sablon("yerlesik:stok_takibi")
    d.ileri.click(); d.ileri.click(); d.olustur.click()
    monkeypatch.setattr(ana, "_sihirbaz_olustur", lambda: type("S", (), {"exec": lambda self: QDialog.Accepted, "sonuc": d.sonuc,
                                                                           "secili": d.secili})())
    p = ana.sablondan_yeni()
    try:
        assert p is not None and p.belge_adi == "Stok takibi" and p.degisti_mi() and p.yol is None
        assert [s.ad for s in p.kitap.sayfalar][:3] == ["Ürünler", "Stok Hareketleri", "Stok Durumu"]
        assert p.windowTitle().startswith("Stok takibi *")
        assert p.kitap.sablon.akis_kimligi == "stok_takibi"
        sd = p.kitap.sayfalar[2]
        assert sd.deger(2, 4) == 42.0                                                     # örnek veriyle hesaplar çalışır
    finally:
        p.degisti_mi = lambda: False
        p.close()


def test_iptal_pencere_acmaz(ana, monkeypatch):
    monkeypatch.setattr(ana, "_sihirbaz_olustur", lambda: type("S", (), {"exec": lambda self: QDialog.Rejected, "sonuc": None})())
    n = len(DosyaIslemleri._tutulan)
    assert ana.sablondan_yeni() is None and len(DosyaIslemleri._tutulan) == n
