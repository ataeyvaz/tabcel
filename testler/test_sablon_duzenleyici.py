"""Faz 11: Şablon Düzenleyici arayüzü (ui/sablon_duzenleyici.py) + Şablonlar penceresi düğmeleri + Dosya ▸ Kitaptan Şablon Oluştur."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.sablon import duzenleme, yukleyici
from tabcel.ui import sablon_duzenleyici as sd
from tabcel.ui import sablon_sihirbazi as ss


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def klasor(tmp_path):
    return tmp_path / "kullanici"


@pytest.fixture
def ed(app, klasor):
    p = sd.DuzenleyiciPenceresi(duzenleme.bos_taslak("Deneme Takibi"), klasor)
    p.show()
    yield p
    p.close()


def hucre_yaz(tablo, r, c, metin):
    tablo.tablo.item(r, c).setText(metin)


def sutun_c(ed, anahtar):
    return next(i for i, k in enumerate(ed.sutunlar.kolonlar) if k.yol[-1] == anahtar and (anahtar != "min" or True))


# ---------------------------------------------------------------- açılış / tablolar
def test_acilis_taslagi_gosterir(ed):
    assert ed.windowTitle().endswith("Deneme Takibi") and ed.kimlik_etiketi.text() == "deneme_takibi"
    assert ed.modul_listesi.count() == 1 and ed.sutunlar.tablo.rowCount() == 2
    assert ed.sutunlar.tablo.item(0, 0).text() == "ad" and ed.sutunlar.tablo.cellWidget(0, 2).currentText() == "metin"
    assert "geçerli" in ed.rapor.toPlainText() and ed.kaydet_dugme.isEnabled()


def test_hucre_duzenleme_taslaga_yazilir(ed):
    m = ed.taslak.moduller["deneme_takibi"]
    hucre_yaz(ed.sutunlar, 1, 1, "Notlar")
    assert m["sutunlar"][1]["ad"] == "Notlar"
    ed.sutunlar.tablo.item(0, 3).setCheckState(Qt.Unchecked)                 # zorunlu kapat → anahtar silinir
    assert "zorunlu" not in m["sutunlar"][0]
    ed.sutunlar.tablo.item(0, 3).setCheckState(Qt.Checked)
    assert m["sutunlar"][0]["zorunlu"] is True


def test_tur_secimi_ve_kisit_sayisi(ed):
    m = ed.taslak.moduller["deneme_takibi"]
    ed.sutunlar.satir_ekle()
    r = ed.sutunlar.tablo.rowCount() - 1
    ed.sutunlar.tablo.cellWidget(r, 2).setCurrentText("tam_sayi")
    assert m["sutunlar"][r]["tur"] == "tam_sayi"
    hucre_yaz(ed.sutunlar, r, 5, "0")
    hucre_yaz(ed.sutunlar, r, 6, "100")
    assert m["sutunlar"][r]["kisit"] == {"min": 0, "max": 100}
    hucre_yaz(ed.sutunlar, r, 5, "")
    hucre_yaz(ed.sutunlar, r, 6, "")
    assert "kisit" not in m["sutunlar"][r]                                   # boşalan iç içe kap de silinir


def test_liste_ve_baglanti_hucreleri(ed):
    m = ed.taslak.moduller["deneme_takibi"]
    ed.sutunlar.satir_ekle()
    r = ed.sutunlar.tablo.rowCount() - 1
    ed.sutunlar.tablo.cellWidget(r, 2).setCurrentText("liste")
    hucre_yaz(ed.sutunlar, r, 8, "Yeni; Hazır, Teslim")
    assert m["sutunlar"][r]["secenekler"] == ["Yeni", "Hazır", "Teslim"]
    ed.sutunlar.tablo.cellWidget(r, 2).setCurrentText("baglanti")
    hucre_yaz(ed.sutunlar, r, 9, "deneme_takibi.ad")
    assert m["sutunlar"][r]["baglanti"] == {"modul": "deneme_takibi", "alan": "ad"}


# ---------------------------------------------------------------- doğrulama / kaydetme
def test_hatali_tanim_kaydi_engeller_duzelince_acilir(ed):
    m = ed.taslak.moduller["deneme_takibi"]
    ed.sutunlar.satir_ekle()
    r = ed.sutunlar.tablo.rowCount() - 1
    hucre_yaz(ed.sutunlar, r, 0, "ad")                                        # yinelenen kimlik
    h = ed.dogrulama_yenile()
    assert duzenleme.ciddi_mi(h) and not ed.kaydet_dugme.isEnabled() and "yinelen" in ed.rapor.toPlainText()
    hucre_yaz(ed.sutunlar, r, 0, "baska")
    ed.dogrulama_yenile()
    assert ed.kaydet_dugme.isEnabled()


def test_kaydet_kullanici_klasorune_yazar(ed, klasor):
    assert ed.kaydet() is True
    assert (klasor / "akislar" / "deneme_takibi.json").is_file() and (klasor / "moduller" / "deneme_takibi.json").is_file()
    assert [p.name for p in ed.yazilan] == ["deneme_takibi.json", "deneme_takibi.json"]
    ed.taslak.akis["aciklama"] = "Sonraki kayıt aynı şablonu günceller."
    assert ed.kaydet() is True                                               # aynı pencerede ikinci kayıt: uyarı yok
    d = json.loads((klasor / "akislar" / "deneme_takibi.json").read_text(encoding="utf-8"))
    assert d["aciklama"].startswith("Sonraki")


def test_saglik_kontrolu_sorunu_kaydi_engeller(ed, klasor):
    m = ed.taslak.moduller["deneme_takibi"]
    m["sutunlar"].append({"kimlik": "fiyat", "ad": "Fiyat", "tur": "para"})
    m["sutunlar"].append({"kimlik": "kdvli", "ad": "KDV'li", "tur": "hesaplanan", "formul": "=[@fiyat]*1.18", "bicim": "para"})
    ed.tablolari_yukle()
    assert ed.kaydet() is False and "Sağlık Kontrolü" in ed.rapor.toPlainText()
    assert not (klasor / "akislar").exists()
    assert ed.denetle()                                                       # sorun listesi döner


def test_denetle_temiz(ed):
    assert ed.denetle() == [] and "0 bulgu" in ed.rapor.toPlainText()


# ---------------------------------------------------------------- genel / sorular / ayarlar
def test_genel_alanlari_akisa_yazilir(ed):
    ed.ad_kutusu.setText("Yeni Adım")
    ed.kategori_kutusu.setCurrentText("Ticaret")
    ed.kokler_kutusu.setText("adım, takip")
    ed.ornek_kutusu.setChecked(True)
    a = ed.taslak.akis
    assert a["ad"] == "Yeni Adım" and a["kategori"] == "Ticaret" and a["anahtar_kelimeler"]["kokler"] == ["adım", "takip"]
    assert a["ornek_veri"] is True and "Yeni Adım" in ed.windowTitle()


def test_sorular_en_cok_yedi(ed):
    for _ in range(7):
        ed.sorular.satir_ekle()
    assert len(ed.taslak.akis["sorular"]) == 7 and not ed.sorular.ekle_dugme.isEnabled()
    ed.sorular.satir_ekle()
    assert len(ed.taslak.akis["sorular"]) == 7
    hucre_yaz(ed.sorular, 0, 0, "depo")
    hucre_yaz(ed.sorular, 1, 0, "depo")                                        # yinelenen soru kimliği → doğrulama hatası
    assert duzenleme.ciddi_mi(ed.dogrulama_yenile())


def test_soru_bayragi_sutunu_kosullar(ed, klasor):
    ed.sorular.satir_ekle()
    hucre_yaz(ed.sorular, 0, 0, "ek")
    hucre_yaz(ed.sorular, 0, 1, "Ek alan ister misiniz?")
    ed.sutunlar.satir_ekle()
    r = ed.sutunlar.tablo.rowCount() - 1
    hucre_yaz(ed.sutunlar, r, 0, "ek_alan")
    hucre_yaz(ed.sutunlar, r, 12, "ek")                                        # Koşul (bayrak)
    assert ed.taslak.moduller["deneme_takibi"]["sutunlar"][r]["eger"] == "ek"
    assert ed.dogrulama_yenile() == [] and ed.denetle() == [] and ed.kaydet()


def test_ayarlar_tablosu(ed):
    ed.ayarlar.satir_ekle()
    hucre_yaz(ed.ayarlar, 0, 0, "kdv")
    hucre_yaz(ed.ayarlar, 0, 1, "KDV oranı")
    ed.ayarlar.tablo.cellWidget(0, 2).setCurrentText("yuzde")
    hucre_yaz(ed.ayarlar, 0, 3, "0.2")
    assert ed.taslak.akis["ayarlar"][0] == {"kimlik": "kdv", "ad": "KDV oranı", "tur": "yuzde", "varsayilan": "0.2"} or \
        ed.taslak.akis["ayarlar"][0]["tur"] == "yuzde"


# ---------------------------------------------------------------- modüller
def test_modul_ekle_sil_kimlik_degistir(ed):
    mk = ed.modul_ekle("Müşteriler")
    assert mk == "musteriler" and ed.modul_listesi.count() == 2 and mk in ed.taslak.moduller
    assert ed.dogrulama_yenile() == []
    ed.modul_listesi.setCurrentRow(1)
    ed.sutunlar.satir_ekle()
    ed.sutunlar.tablo.cellWidget(1, 2).setCurrentText("baglanti")
    hucre_yaz(ed.sutunlar, 1, 9, "deneme_takibi.ad")
    ed.modul_listesi.setCurrentRow(0)
    assert ed.modul_kimligi_degistir("takip") is True
    assert ed.taslak.modul_kimlikleri() == ["takip", "musteriler"]
    assert ed.taslak.moduller["musteriler"]["sutunlar"][1]["baglanti"]["modul"] == "takip"        # bağlantı güncellendi
    assert ed.dogrulama_yenile() == []
    ed.modul_listesi.setCurrentRow(1)
    assert ed.modul_sil() is True and ed.taslak.modul_kimlikleri() == ["takip"]


def test_modul_kimligi_gecersiz_reddedilir(ed, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    assert ed.modul_kimligi_degistir("Geçersiz Kimlik") is False
    assert ed.modul_kimligi_degistir("deneme_takibi") is False               # aynı kimlik zaten var


def test_modul_bilgi_ve_matris_yazilir(ed):
    ed.m_tekil.setText("Deneme")
    ed.m_sayfa.setText("Denemeler")
    ed.m_gorunen.setText("ad")
    m = ed.taslak.moduller["deneme_takibi"]
    assert m["tekil_ad"] == "Deneme" and m["sayfa_adi"] == "Denemeler" and m["gorunen"] == ["ad"]
    ed.m_matris_satir.setText("ad")
    ed.m_matris_sutun.setText("aciklama")
    ed.m_matris_deger.setText("ad")
    assert m["matris"] == {"satir": "ad", "sutun": "aciklama", "deger": "ad"}


def test_kurallar_tablosu_kuraldan_ihlal_uretir(ed, klasor):
    m = ed.taslak.moduller["deneme_takibi"]
    ed.kurallar.satir_ekle()
    hucre_yaz(ed.kurallar, 0, 0, "kisa_ad")
    hucre_yaz(ed.kurallar, 0, 2, "=LEN([@ad])>=3")
    hucre_yaz(ed.kurallar, 0, 4, "Ad en az 3 harf olmalı.")
    assert m["kurallar"][0]["formul"] == "=LEN([@ad])>=3" and m["kurallar"][0]["siddet"] == "durdur"
    assert ed.dogrulama_yenile() == [] and ed.kaydet()
    # kayıtlı şablon bir kitap üretir; kural motoru bu kuralı uygular
    from tabcel.sablon import kayitlar
    from tabcel.sablon.uretici import uret
    d = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), klasor)
    r = uret(d.bul("kullanici:deneme_takibi"))
    b = kayitlar.Baglam.kur(r.kitap)
    g = b.gorunum("deneme_takibi")
    i = kayitlar.kayit_denetle(b, g, 2, {"ad": Hucre("ab")})
    assert [x.kural for x in i] == ["kisa_ad"] and "en az 3" in i[0].ileti


# ---------------------------------------------------------------- JSON
def test_json_sekmesi_uygula(ed):
    ed.json_hedef.setCurrentIndex(1)                                          # modül
    d = json.loads(ed.json_metin.toPlainText())
    d["tekil_ad"] = "JSON'dan"
    ed.json_metin.setPlainText(json.dumps(d, ensure_ascii=False))
    assert ed.json_uygula() is True
    assert ed.taslak.moduller["deneme_takibi"]["tekil_ad"] == "JSON'dan" and ed.m_tekil.text() == "JSON'dan"


def test_json_bozuk_ya_da_kimlik_degisimi_reddedilir(ed):
    ed.json_hedef.setCurrentIndex(1)
    ed.json_metin.setPlainText("{bozuk")
    assert ed.json_uygula() is False and "bozuk" in ed.json_iletisi.text()
    d = json.loads(json.dumps(ed.taslak.moduller["deneme_takibi"]))
    d["kimlik"] = "baska"
    ed.json_metin.setPlainText(json.dumps(d))
    assert ed.json_uygula() is False and "Kimlik" in ed.json_iletisi.text()
    ed.json_metin.setPlainText("[1]")
    assert ed.json_uygula() is False


# ---------------------------------------------------------------- Şablonlar penceresi
@pytest.fixture
def depo_ve_pencere(app):
    depo = yukleyici.depo_yukle()
    p = ss.SablonlarPenceresi(depo, yukleyici.depo_yukle)
    return p


@pytest.fixture
def duzenleyiciyi_otomatik_kaydet(monkeypatch):
    """`DuzenleyiciPenceresi.exec` modal döngüsü yerine hemen Kaydet çalıştırır (testte pencere beklemesin)."""
    kayit = []

    def exec_(self):
        kayit.append(self)
        self.kaydet()
        return 1
    monkeypatch.setattr(sd.DuzenleyiciPenceresi, "exec", exec_)
    return kayit


def test_sablonlar_penceresi_yeni_duzenle_kopya_sil(depo_ve_pencere, duzenleyiciyi_otomatik_kaydet):
    p = depo_ve_pencere
    sayi = len(p.depo.sablonlar)
    assert not p.duzenle_dugme.isEnabled() and not p.sil_dugme.isEnabled() and p.kopya_dugme.isEnabled()   # yerleşik seçili
    assert p.yeni_sablon("Benim Defterim") is True
    assert len(p.depo.sablonlar) == sayi + 1 and p.depo.bul("kullanici:benim_defterim") is not None
    i = next(i for i, s in enumerate(p.depo.sablonlar) if s.ic_kimlik == "kullanici:benim_defterim")
    p.liste.setCurrentRow(i)
    assert p.duzenle_dugme.isEnabled() and p.sil_dugme.isEnabled()
    assert p.duzenle() is True                                                # düzenleyici açılır, kayıt yenilenir
    # yerleşik şablonun kopyası
    p.liste.setCurrentRow(next(i for i, s in enumerate(p.depo.sablonlar) if s.ic_kimlik == "yerlesik:not_cizelgesi"))
    assert p.kopyasini_duzenle("Not Çizelgem") is True
    k = p.depo.bul("kullanici:not_cizelgem")
    assert k is not None and p.depo.rapor.temiz
    assert all(m.startswith("not_cizelgem_") for m in k.moduller)
    # silme
    p.liste.setCurrentRow(next(i for i, s in enumerate(p.depo.sablonlar) if s.ic_kimlik == "kullanici:not_cizelgem"))
    assert p.sil(onay=True) is True and p.depo.bul("kullanici:not_cizelgem") is None
    assert p.depo.bul("yerlesik:not_cizelgesi") is not None                   # yerleşik dokunulmadı


def test_yerlesik_sablon_silinemez_duzenlenemez(depo_ve_pencere):
    p = depo_ve_pencere
    p.liste.setCurrentRow(0)
    assert p.sil(onay=True) is False and p.duzenle() is False


# ---------------------------------------------------------------- Dosya ▸ Kitaptan Şablon Oluştur
def test_kitaptan_sablon_olustur_duzenleyicide_acilir(app, monkeypatch):
    from tabcel.ui.window import Pencere
    k = CalismaKitabi()
    s = k.sayfalar[0]
    k.yeniden_adlandir(s, "Ürünlerim")
    s.ata(1, 1, Hucre("Ürün"))
    s.ata(1, 2, Hucre("Adet"))
    for r in range(2, 6):
        s.ata(r, 1, Hucre(f"Ürün {r}"))
        s.ata(r, 2, Hucre(float(r)))
    w = Pencere(k)
    ed = w.kitaptan_sablon_olustur("Ürün Listem", [s])
    assert ed is not None and ed.taslak.kimlik == "urun_listem" and "urunlerim" in ed.taslak.moduller
    assert ed.sutunlar.tablo.rowCount() == 2 and ed.dogrulama_yenile() == []
    assert ed.kaydet() is True
    ed.close()
    w.degisti_mi = lambda: False
    w.close()


def test_kitaptan_sablon_penceresi_secimi(app):
    k = CalismaKitabi()
    k.sayfalar[0].ata(1, 1, Hucre("Başlık"))
    k.sayfalar[0].ata(2, 1, Hucre("Değer"))
    pen = sd.KitaptanSablonPenceresi(k)
    pen.ad_kutusu.setText("")
    assert pen.olustur() is False and "ad" in pen.ileti.text().lower()
    pen.ad_kutusu.setText("Bir Şablon")
    pen.liste.clearSelection()
    assert pen.olustur() is False and "sayfa" in pen.ileti.text()
    pen.liste.item(0).setSelected(True)
    assert pen.olustur() is True and pen.sonuc.taslak.kimlik == "bir_sablon"
