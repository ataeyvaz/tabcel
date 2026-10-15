"""Faz 11: Şablon Düzenleyici çekirdeği (sablon/duzenleme.py, Qt'siz): taslak, doğrulama, kopya, kaydet/yükle/sil, kural 22 denetimi,
kitaptan şablon."""
import json
from pathlib import Path

import pytest

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.sablon import duzenleme, sema, yukleyici
from tabcel.sablon.uretici import uret


@pytest.fixture(scope="module")
def depo():
    return yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor"))


# ---------------------------------------------------------------- kimlik / boş taslak
@pytest.mark.parametrize("ad,beklenen", [("Çalışan Listesi", "calisan_listesi"), ("Stok  Takibi!", "stok_takibi"), ("1 Test", "k_1_test"),
                                         ("", "kayit"), ("ĞÜŞİÖÇ", "gusioc"), ("a" * 60, "a" * 40)])
def test_kimlik_uret(ad, beklenen):
    k = duzenleme.kimlik_uret(ad)
    assert k == beklenen and sema.KIMLIK_RE.match(k)


def test_kimlik_cakisinca_numara_ekler():
    assert duzenleme.kimlik_uret("Stok", {"stok", "stok_2"}) == "stok_3"
    assert len(duzenleme.kimlik_uret("a" * 60, {"a" * 40})) <= 40


def test_bos_taslak_gecerli_ve_saglik_temiz():
    t = duzenleme.bos_taslak("Benim Stokum")
    assert duzenleme.dogrula(t) == [] and duzenleme.uretim_denetimi(t) == []
    assert t.kimlik == "benim_stokum" and t.modul_kimlikleri() == ["benim_stokum"]


# ---------------------------------------------------------------- doğrulama (Faz 10a doğrulayıcısı)
def test_dogrulama_hatalari_turkce_ve_konumlu():
    t = duzenleme.bos_taslak("Deneme")
    m = t.moduller["deneme"]
    m["sutunlar"].append({"kimlik": "ad", "ad": "Yinelenen", "tur": "metin"})                 # çakışan sütun kimliği
    m["sutunlar"].append({"kimlik": "x", "ad": "Hatalı tür", "tur": "uzaylı"})
    h = duzenleme.dogrula(t)
    assert duzenleme.ciddi_mi(h)
    metin = "\n".join(str(x) for x in h)
    assert "modül deneme" in metin and "uzaylı" in metin


def test_akis_bayrak_ve_modul_hatasi():
    t = duzenleme.bos_taslak("Deneme")
    t.akis["moduller"].append({"modul": "yok_modul"})
    assert any("yok_modul" in str(x) for x in duzenleme.dogrula(t))
    t = duzenleme.bos_taslak("Deneme")
    t.akis["sorular"] = [{"kimlik": f"s{i}", "metin": "?", "tur": "evet_hayir"} for i in range(8)]       # en çok 7 soru
    assert any("en çok 7" in str(x) for x in duzenleme.dogrula(t))


def test_kullanilmayan_modul_uyaridir_hata_degil():
    t = duzenleme.bos_taslak("Deneme")
    t.moduller["fazla"] = dict(t.moduller["deneme"], kimlik="fazla", sayfa_adi="Fazla")
    h = duzenleme.dogrula(t)
    assert not duzenleme.ciddi_mi(h) and any(x.uyari and "kullanılmıyor" in x.mesaj for x in h)


# ---------------------------------------------------------------- kural 22: sağlık kontrolü
def test_saglik_kontrolu_sorunlu_sablonu_engeller(tmp_path):
    t = duzenleme.bos_taslak("Sorunlu")
    m = t.moduller["sorunlu"]
    m["sutunlar"].append({"kimlik": "fiyat", "ad": "Fiyat", "tur": "para"})
    m["sutunlar"].append({"kimlik": "toplam", "ad": "Toplam", "tur": "hesaplanan", "formul": "=[@fiyat]*1.18", "bicim": "para"})   # sabit sayı
    sorunlar = duzenleme.uretim_denetimi(t)
    assert sorunlar and "sabit sayı" in " ".join(sorunlar).lower()
    with pytest.raises(duzenleme.KayitHatasi):
        duzenleme.kaydet(t, tmp_path)
    assert not list(tmp_path.rglob("*.json"))                          # hiçbir şey yazılmadı


def test_uretim_denetimi_kombinasyonlari_dener():
    t = duzenleme.bos_taslak("Soru Var")
    t.akis["sorular"] = [{"kimlik": "ek", "metin": "Ek alan?", "tur": "evet_hayir", "varsayilan": False}]
    t.moduller["soru_var"]["sutunlar"].append({"kimlik": "notum", "ad": "Not", "tur": "metin", "eger": "ek"})
    assert duzenleme.dogrula(t) == [] and duzenleme.uretim_denetimi(t) == []


# ---------------------------------------------------------------- kaydet / yükle / sil
def test_kaydet_yukle_gidis_donus(tmp_path):
    t = duzenleme.bos_taslak("Gidiş Dönüş")
    yollar = duzenleme.kaydet(t, tmp_path)
    assert {p.name for p in yollar} == {"gidis_donus.json"} and (tmp_path / "akislar" / "gidis_donus.json").is_file()
    assert not list(tmp_path.rglob("*.tmp"))                           # geçici dosya kalmadı
    d = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), tmp_path)
    s = d.bul("kullanici:gidis_donus")
    assert s is not None and s.akis.ad == "Gidiş Dönüş" and d.rapor.temiz
    t2 = duzenleme.taslak_yukle(tmp_path / "akislar" / "gidis_donus.json", tmp_path)
    assert t2.akis == t.akis and t2.moduller == t.moduller
    r = uret(s)                                                         # kullanılabilir şablon
    assert r.kitap.sayfalar[0].ad == "Gidiş Dönüş"


def test_ayni_kimlik_uzerine_yazma_onay_ister(tmp_path):
    t = duzenleme.bos_taslak("Tekrar")
    duzenleme.kaydet(t, tmp_path)
    with pytest.raises(duzenleme.KayitHatasi, match="zaten var"):
        duzenleme.kaydet(duzenleme.bos_taslak("Tekrar"), tmp_path)
    t.akis["aciklama"] = "Güncel açıklama"
    duzenleme.kaydet(t, tmp_path, uzerine_yaz=True)
    assert json.loads((tmp_path / "akislar" / "tekrar.json").read_text(encoding="utf-8"))["aciklama"] == "Güncel açıklama"


def test_baska_sablonun_modulunu_ezmez(tmp_path):
    a = duzenleme.bos_taslak("Birinci")
    duzenleme.kaydet(a, tmp_path)
    b = duzenleme.bos_taslak("İkinci")
    b.akis["moduller"] = [{"modul": "birinci"}]
    b.moduller = {"birinci": dict(a.moduller["birinci"])}
    with pytest.raises(duzenleme.KayitHatasi, match="başka|da kullanılıyor"):
        duzenleme.kaydet(b, tmp_path)


def test_sil_yalniz_kendi_modullerini_siler(tmp_path):
    a, b = duzenleme.bos_taslak("Birinci"), duzenleme.bos_taslak("İkinci")
    duzenleme.kaydet(a, tmp_path)
    duzenleme.kaydet(b, tmp_path)
    silinen = duzenleme.kullanici_sablonu_sil("birinci", tmp_path)
    assert {p.name for p in silinen} == {"birinci.json"} and len(silinen) == 2
    assert (tmp_path / "akislar" / "ikinci.json").is_file() and (tmp_path / "moduller" / "ikinci.json").is_file()
    assert duzenleme.kullanici_sablonu_sil("yok", tmp_path) == []


def test_hatali_taslak_kaydedilmez(tmp_path):
    t = duzenleme.bos_taslak("Hatalı")
    t.moduller["hatali"]["sutunlar"][0]["tur"] = "uzaylı"
    with pytest.raises(duzenleme.KayitHatasi, match="hata var"):
        duzenleme.kaydet(t, tmp_path)


# ---------------------------------------------------------------- kopya (yerleşik şablonu düzenlemek)
def test_yerlesik_sablonun_kopyasi_gecerli_ve_modulleri_onekli(depo):
    s = depo.bul("yerlesik:stok_takibi")
    t = duzenleme.kopya(s, "Benim Stokum")
    assert t.kimlik == "benim_stokum" and t.kaynak == "yerlesik:stok_takibi"
    assert all(k.startswith("benim_stokum_") for k in t.moduller)               # yerleşik modülleri ezmesin
    assert duzenleme.dogrula(t) == []
    # bağlantılar ve formül yer tutucuları yeni modül kimliklerine çevrildi
    hareket = t.moduller["benim_stokum_stok_hareketleri"]
    urun_baglanti = next(x for x in hareket["sutunlar"] if x["kimlik"] == "urun")["baglanti"]
    assert urun_baglanti["modul"] == "benim_stokum_urunler"
    assert "[benim_stokum_stok_durumu." in hareket["kurallar"][0]["formul"]
    assert s.akis.ham["kimlik"] == "stok_takibi"                                   # özgün sözlük bozulmadı


def test_kopya_uretilir_ve_saglik_temiz(depo):
    t = duzenleme.kopya(depo.bul("yerlesik:cari_hesap"), "Cari Kopyam")
    assert duzenleme.uretim_denetimi(t) == []


def test_modul_yeniden_adlandirma_referanslari_gunceller():
    t = duzenleme.bos_taslak("Ref")
    t.moduller["ref"]["sutunlar"].append({"kimlik": "kendi", "ad": "Kendi", "tur": "hesaplanan", "formul": "=COUNTA([ref.ad])", "bicim": "tam_sayi"})
    duzenleme.modul_yeniden_adlandir(t, "ref", "yeni_ad")
    assert t.modul_kimlikleri() == ["yeni_ad"] and t.moduller["yeni_ad"]["kimlik"] == "yeni_ad"
    assert "[yeni_ad.ad]" in t.moduller["yeni_ad"]["sutunlar"][-1]["formul"]
    assert duzenleme.dogrula(t) == []
    with pytest.raises(ValueError):
        duzenleme.modul_yeniden_adlandir(t, "yok", "x")


# ---------------------------------------------------------------- kitaptan şablon
def _kitap():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    k.yeniden_adlandir(s, "Siparişler")
    for c, b in enumerate(["Müşteri", "Sipariş tarihi", "Adet", "Birim fiyat", "Tutar", "Durum", "Telefon"], 1):
        s.ata(1, c, Hucre(b))
    durumlar = ["Yeni", "Hazır", "Yeni", "Yeni", "Hazır", "Yeni", "Hazır", "Yeni"]
    for i in range(8):
        r = i + 2
        s.ata(r, 1, Hucre(f"Müşteri {i}"))
        s.ata(r, 2, Hucre(float(46000 + i)))
        s.ata(r, 3, Hucre(float(i + 1)))
        s.ata(r, 4, Hucre(10.5 + i))
        s.ata(r, 5, Hucre(None, f"=C{r}*D{r}"))
        s.ata(r, 6, Hucre(durumlar[i]))
        s.ata(r, 7, Hucre(f"0532 111 22 {30 + i}"))
    s.bicim_yaz(sutunlar={2: k.stil_havuzu.kimlik(__import__("tabcel.model.stil", fromlist=["Stil"]).Stil(sayi_bicimi="dd.mm.yyyy"))})
    return k


def test_kitaptan_sablon_turleri_tahmin_eder():
    k = _kitap()
    r = duzenleme.kitaptan_taslak(k, k.sayfalar, "Sipariş Takibi", ornek_veri=True)
    m = r.taslak.moduller["siparisler"]
    tur = {s["kimlik"]: s["tur"] for s in m["sutunlar"]}
    assert tur["musteri"] == "metin" and tur["siparis_tarihi"] == "tarih" and tur["adet"] == "tam_sayi"
    assert tur["birim_fiyat"] == "ondalik" and tur["durum"] == "liste" and tur["telefon"] == "telefon"
    assert tur["tutar"] == "hesaplanan"
    tutar = next(s for s in m["sutunlar"] if s["kimlik"] == "tutar")
    assert tutar["formul"] == "=[@adet]*[@birim_fiyat]"
    assert next(s for s in m["sutunlar"] if s["kimlik"] == "durum")["secenekler"] == ["Hazır", "Yeni"]
    assert len(m["ornek_veri"]) == 8 and m["ornek_veri"][0]["siparis_tarihi"] == "2025-12-09" and "tutar" not in m["ornek_veri"][0]
    assert duzenleme.dogrula(r.taslak) == []
    assert duzenleme.uretim_denetimi(r.taslak) == []


def test_kitaptan_sablon_donusmeyen_formul_uyari_verir():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("Sayı"))
    s.ata(1, 2, Hucre("Toplam"))
    for r in range(2, 6):
        s.ata(r, 1, Hucre(float(r)))
        s.ata(r, 2, Hucre(None, "=SUM($A$2:$A$5)"))                  # aralık: dönüştürülemez
    r = duzenleme.kitaptan_taslak(k, k.sayfalar, "Aralık")
    assert any("dönüştürülemedi" in u for u in r.uyarilar)
    assert next(x for x in r.taslak.moduller["sayfa1"]["sutunlar"] if x["kimlik"] == "toplam")["tur"] != "hesaplanan"


def test_kitaptan_sablon_bos_kitapta_hata():
    with pytest.raises(duzenleme.KayitHatasi):
        duzenleme.kitaptan_taslak(CalismaKitabi(), CalismaKitabi().sayfalar, "Boş")


def test_kitaptan_sablon_sonrasi_uretilen_kitap_calisir(tmp_path):
    k = _kitap()
    r = duzenleme.kitaptan_taslak(k, k.sayfalar, "Sipariş Takibi")
    duzenleme.kaydet(r.taslak, tmp_path)
    d = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), tmp_path)
    s = d.bul("kullanici:siparis_takibi")
    assert s is not None
    sonuc = uret(s)
    assert [x.ad for x in sonuc.kitap.sayfalar][0] == "Siparişler"
