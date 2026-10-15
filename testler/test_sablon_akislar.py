"""Faz 10e: yerleşik akışlar (Cari hesap, Apartman aidat, Teklif formu, Çek-senet, Not çizelgesi). Her akış × TÜM cevap kombinasyonu:
geçerli kitap, Tablo Sağlık Kontrolü 0 bulgu (CLAUDE.md kural 22), hata değeri yok; ayrıca her akış için iş senaryosu hesapları."""
import itertools
from pathlib import Path

import pytest

from tabcel.formul import saglik
from tabcel.formul.motor import Hesaplayici
from tabcel.model import deger as D
from tabcel.model.sayfa import Hucre
from tabcel.model.tarihseri import ymd_seri
from tabcel.sablon import yukleyici
from tabcel.sablon.uretici import UretimHatasi, uret

DEPO = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor"))
AKISLAR = [s.ic_kimlik for s in DEPO.sablonlar]


def kombinasyonlar(sablon):
    kimlikler = [s.kimlik for s in sablon.akis.sorular]
    for kombo in itertools.product([False, True], repeat=len(kimlikler)):
        yield dict(zip(kimlikler, kombo))


def sayfa_(k, ad):
    return next(s for s in k.sayfalar if s.ad == ad)


def basliklar(s):
    kul = s.kullanilan_aralik()
    return [s.deger(1, c) for c in range(1, kul[3] + 1)]


def tarih(y, a, g):
    return float(ymd_seri(y, a, g))


def test_alti_akis_yuklenir():
    assert AKISLAR == ["yerlesik:apartman_aidat", "yerlesik:cari_hesap", "yerlesik:cek_senet", "yerlesik:not_cizelgesi",
                       "yerlesik:stok_takibi", "yerlesik:teklif_formu"]
    assert DEPO.rapor.temiz, DEPO.rapor.metin()
    assert {s.akis.kategori for s in DEPO.sablonlar} == {"Site ve Apartman", "Ticaret", "Finans", "Eğitim", "Satış"}
    for s in DEPO.sablonlar:
        assert 1 <= len(s.akis.sorular) <= 7 and s.akis.nasil_kullanilir and s.akis.ornek_veri


@pytest.mark.parametrize("ic_kimlik", AKISLAR)
def test_her_kombinasyonda_saglik_0_bulgu_ve_hata_yok(ic_kimlik):
    sablon = DEPO.bul(ic_kimlik)
    n = 0
    for cevap in kombinasyonlar(sablon):
        for ornek in (True, False):
            r = uret(sablon, cevap, ornek_veri=ornek)
            motor = Hesaplayici(r.kitap)
            bulgular = saglik.Tarayici(r.kitap, motor).tara()
            assert bulgular == [], (ic_kimlik, cevap, ornek, [(b.kontrol, b.sayfa_ad, b.baslik) for b in bulgular])
            for s in r.kitap.sayfalar:
                for (satir, sutun) in s._hucreler:
                    v = s.deger(satir, sutun)
                    assert not isinstance(v, D.Hata), (ic_kimlik, cevap, s.ad, satir, sutun, v)
                for h in s._hucreler.values():
                    assert h.formul is None or ("[" not in h.formul and "AYAR." not in h.formul), h.formul
            assert r.kitap.sablon is not None and r.kitap.sablon.akis_kimligi == sablon.akis.kimlik
            motor.kapat()
            n += 1
    assert n == 2 ** len(sablon.akis.sorular) * 2


@pytest.mark.parametrize("ic_kimlik", AKISLAR)
def test_xlsx_gidis_donus_her_akis(ic_kimlik, tmp_path):
    from tabcel.io import xlsx_io
    sablon = DEPO.bul(ic_kimlik)
    cevap = {s.kimlik: True for s in sablon.akis.sorular}                              # her şey açık (en kalabalık)
    r = uret(sablon, cevap, ornek_veri=True)
    yol = str(tmp_path / "x.xlsx")
    xlsx_io.kaydet(r.kitap, yol)
    k2, rapor = xlsx_io.ac(yol)
    assert not rapor.veri_kaybi
    assert [s.ad for s in k2.sayfalar] == [s.ad for s in r.kitap.sayfalar]
    assert k2.sablon_denetim.aktif and k2.sablon_denetim.bulgular == [], k2.sablon_denetim.metin()


# ---------------------------------------------------------------- iş senaryoları
def test_cari_hesap_bakiye():
    r = uret(DEPO.bul("yerlesik:cari_hesap"), {"vade": True, "iletisim": True, "vergi": True}, ornek_veri=True)
    Hesaplayici(r.kitap)
    b = sayfa_(r.kitap, "Cari Bakiye")
    assert basliklar(b) == ["Cari adı", "Toplam borç", "Toplam alacak", "Bakiye", "Durum"]
    assert [b.deger(2, c) for c in range(1, 6)] == ["Örnek Ticaret Ltd.", 1500.0, 500.0, 1000.0, "Cari size borçlu"]
    assert [b.deger(3, c) for c in range(1, 6)] == ["Örnek Tedarik A.Ş.", 0.0, 0.0, 0.0, "Hesap kapalı"]
    hareket = sayfa_(r.kitap, "Cari Hareketler")
    hareket.ata(5, 2, Hucre("Örnek Tedarik A.Ş."))
    hareket.ata(5, 6, Hucre(2000.0))                                                  # tedarikçiye ödeme/alacak
    assert b.deger(3, 4) == -2000.0 and b.deger(3, 5) == "Siz cariye borçlusunuz"
    assert basliklar(sayfa_(r.kitap, "Cari Kartlar")) == ["Cari adı", "Türü", "Telefon", "E-posta", "Vergi no"]
    kapali = uret(DEPO.bul("yerlesik:cari_hesap"), {"vade": False, "iletisim": False, "vergi": False})
    assert basliklar(sayfa_(kapali.kitap, "Cari Kartlar")) == ["Cari adı", "Türü"]
    assert "Vade tarihi" not in basliklar(sayfa_(kapali.kitap, "Cari Hareketler"))


def test_aidat_durumu_ve_gecikme():
    r = uret(DEPO.bul("yerlesik:apartman_aidat"), {"ek_odeme": True, "gecikme": True, "iletisim": False}, ornek_veri=True)
    Hesaplayici(r.kitap)
    d = sayfa_(r.kitap, "Aidat Durumu")
    basl = basliklar(d)
    assert basl == ["Daire no", "Daire sahibi", "Aylık aidat", "Aylık ek ödeme", "Beklenen", "Ödenen", "Kalan borç", "Gecikme zammı", "Durum"]
    # daire 1: (500+150)×1 = 650, ödenen 650 → güncel; daire 2: 650 beklenen, 300 ödenen → kalan 350, zam 17,5
    assert [d.deger(2, c) for c in range(5, 10)] == [650.0, 650.0, 0.0, 0.0, "Güncel"]
    assert [d.deger(3, c) for c in range(5, 10)] == [650.0, 300.0, 350.0, 17.5, "Borçlu"]
    ayar = sayfa_(r.kitap, "Ayarlar")
    ayar.ata(3, 2, Hucre(3.0))                                                        # İşlenen ay sayısı: 3
    assert d.deger(3, 5) == 1950.0 and d.deger(3, 7) == 1650.0 and d.deger(2, 9) == "Borçlu"
    sade = uret(DEPO.bul("yerlesik:apartman_aidat"), {"ek_odeme": False, "gecikme": False, "iletisim": False}, ornek_veri=True)
    Hesaplayici(sade.kitap)
    ds = sayfa_(sade.kitap, "Aidat Durumu")
    assert basliklar(ds) == ["Daire no", "Daire sahibi", "Aylık aidat", "Beklenen", "Ödenen", "Kalan borç", "Durum"]
    assert [ds.deger(3, c) for c in range(4, 8)] == [500.0, 300.0, 200.0, "Borçlu"]      # ek ödeme kapalı: 0 sayılır
    assert [s.ad for s in sade.kitap.sayfalar][-2:] == ["Ayarlar", "Nasıl Kullanılır"]
    assert [ayar_adi for ayar_adi in (sayfa_(sade.kitap, "Ayarlar").deger(i, 1) for i in (2, 3, 4))] == ["Para birimi", "İşlenen ay sayısı", None]


def test_teklif_toplamlari_ve_yaziyla():
    r = uret(DEPO.bul("yerlesik:teklif_formu"), {"kdv": True, "iskonto": True, "yaziyla": True}, ornek_veri=True)
    Hesaplayici(r.kitap)
    t, k = sayfa_(r.kitap, "Teklifler"), sayfa_(r.kitap, "Teklif Kalemleri")
    assert basliklar(t) == ["Teklif no", "Tarih", "Müşteri", "Son geçerlilik", "Ara toplam", "KDV", "Genel toplam", "Yazıyla"]
    assert t.deger(2, 4) == tarih(2026, 2, 17)                                          # 2 Şubat + 15 gün
    assert [t.deger(2, c) for c in (5, 6, 7)] == [3700.0, 740.0, 4440.0]
    assert t.deger(2, 8) == "dört bin dört yüz kırk"
    k.ata(2, 6, Hucre(0.1))                                                             # ilk kaleme %10 iskonto: 2250 + 1200
    assert t.deger(2, 5) == 3450.0 and t.deger(2, 7) == 4140.0
    sade = uret(DEPO.bul("yerlesik:teklif_formu"), {"kdv": False, "iskonto": False, "yaziyla": False}, ornek_veri=True)
    Hesaplayici(sade.kitap)
    ts = sayfa_(sade.kitap, "Teklifler")
    assert basliklar(ts) == ["Teklif no", "Tarih", "Müşteri", "Son geçerlilik", "Ara toplam", "Genel toplam"]
    assert ts.deger(2, 6) == 3700.0                                                      # KDV kapalı: genel = ara
    assert "KDV oranı" not in [sayfa_(sade.kitap, "Ayarlar").deger(i, 1) for i in range(2, 5)]


def test_cek_senet_hesaplari():
    sb = DEPO.bul("yerlesik:cek_senet")
    r = uret(sb, {"yon": True, "banka": True, "uyari": True, "tatil": True}, ornek_veri=True)
    Hesaplayici(r.kitap)
    c = sayfa_(r.kitap, "Çek ve Senetler")
    basl = basliklar(c)
    assert basl[-3:] == ["Kalan gün", "Vade (iş günü)", "Uyarı"]
    i = basl.index("Vade tarihi") + 1
    # vade 2026-03-15 (Pazar) → ilk iş günü 16 Mart Pazartesi; 2026-04-20 Pazartesi → aynı gün
    assert c.deger(2, basl.index("Vade (iş günü)") + 1) == tarih(2026, 3, 16)
    assert c.deger(3, basl.index("Vade (iş günü)") + 1) == tarih(2026, 4, 20)
    assert c.deger(2, basl.index("Kalan gün") + 1) == c.deger(2, i) - float(__import__("datetime").date.today().toordinal()
                                                                           - __import__("datetime").date(1899, 12, 30).toordinal())
    # tatil verisi dışındaki vade: hata yerine vade günü
    c.ata(4, 1, Hucre("Ç-099"))
    c.ata(4, i, Hucre(tarih(2031, 5, 5)))
    assert c.deger(4, basl.index("Vade (iş günü)") + 1) == tarih(2031, 5, 5)
    # ödenmiş/tahsil edilmiş için uyarı yok
    j = basl.index("Durum") + 1
    c.ata(2, j, Hucre("Tahsil edildi"))
    assert c.deger(2, basl.index("Uyarı") + 1) == ""
    c.ata(3, j, Hucre("Portföyde"))
    c.ata(3, i, Hucre(tarih(2020, 1, 1)))
    assert c.deger(3, basl.index("Uyarı") + 1) == "Vadesi geçti"
    sade = uret(sb, {"yon": False, "banka": False, "uyari": False, "tatil": False}, ornek_veri=True)
    assert basliklar(sayfa_(sade.kitap, "Çek ve Senetler")) == ["Çek / senet no", "Türü", "Kimden / kime", "Düzenleme tarihi",
                                                                 "Vade tarihi", "Tutar", "Durum", "Kalan gün"]
    assert [sayfa_(sade.kitap, "Ayarlar").deger(i, 1) for i in (2, 3)] == ["Para birimi", None]       # uyarı süresi ayarı kapalı


def test_not_ortalamasi_ve_gecme():
    r = uret(DEPO.bul("yerlesik:not_cizelgesi"), {"devamsizlik": True, "gecme": True}, ornek_veri=True)
    Hesaplayici(r.kitap)
    n, o = sayfa_(r.kitap, "Notlar"), sayfa_(r.kitap, "Öğrenciler")
    assert basliklar(n) == ["Okul no", "Ders", "1. sınav", "2. sınav", "Sözlü / ödev", "Ortalama", "Durum"]
    assert [n.deger(2, c) for c in (6, 7)] == [81.0, "Geçti"]                           # 80×0,3 + 70×0,3 + 90×0,4
    assert [n.deger(3, c) for c in (6, 7)] == [44.5, "Kaldı"]                           # 45×0,3 + 50×0,3 + 40×0,4
    n.ata(3, 5, Hucre(None))
    assert n.deger(3, 6) == "" and n.deger(3, 7) == ""                                  # eksik not: ortalama yok
    assert [o.deger(2, 5), o.deger(3, 5)] == ["", "Sınırı aştı"]                        # 2 gün / 12 gün, sınır 10
    kapali = uret(DEPO.bul("yerlesik:not_cizelgesi"), {"devamsizlik": False, "gecme": False})
    assert basliklar(sayfa_(kapali.kitap, "Notlar"))[-1] == "Ortalama"
    assert basliklar(sayfa_(kapali.kitap, "Öğrenciler")) == ["Okul no", "Ad soyad", "Sınıf"]


def test_ad_soyad_sutunu_temizleyici_tarar():
    """Not çizelgesindeki 'Ad soyad' başlığı Paylaşım Temizleyici'nin ad-soyad önerisine girer (kural 18–20 ile uyum)."""
    from tabcel.model import kimlik, temizle
    r = uret(DEPO.bul("yerlesik:not_cizelgesi"), {"devamsizlik": False, "gecme": True}, ornek_veri=True)
    kay = temizle.Tarayici(r.kitap).tara()
    adlar = [k for k in kay if k.tur == kimlik.AD and k.yer.tur == temizle.HUCRE]
    assert sorted(k.metin for k in adlar) == ["Örnek Öğrenci A", "Örnek Öğrenci B"]


# ---------------------------------------------------------------- şema genişletmeleri
def test_formul_satiri_modul_duzeyinde():
    r = uret(DEPO.bul("yerlesik:teklif_formu"))
    assert r.yerler["teklif_kalemleri"].formul_satiri == 1000 and r.yerler["teklifler"].formul_satiri == 500
    k = sayfa_(r.kitap, "Teklif Kalemleri")
    tutar = r.yerler["teklif_kalemleri"].sutunlar["tutar"]
    assert k._hucreler.get((1001, tutar)) is not None and k._hucreler.get((1002, tutar)) is None
    r2 = uret(DEPO.bul("yerlesik:teklif_formu"), formul_satiri=50, kapasite=300)
    assert r2.yerler["teklif_kalemleri"].formul_satiri == 300                           # kapasiteyi aşamaz


def test_opsiyonel_yer_tutucu_ve_kapali_ayar():
    from copy import deepcopy
    sb = deepcopy(DEPO.bul("yerlesik:teklif_formu"))
    d = next(s for s in sb.moduller["teklifler"].sutunlar if s.kimlik == "genel_toplam")
    d.formul = "=[@kdv_tutari]"                                                       # ? yok: kapalıyken hata
    with pytest.raises(UretimHatasi, match="kapalı ya da olmayan"):
        uret(sb, {"kdv": False})
    d.formul = "=[@ara_toplam]+AYAR.kdv_orani"                                        # kapalı ayara başvuru
    with pytest.raises(UretimHatasi, match="ayarı bu çalıştırmada kapalı"):
        uret(sb, {"kdv": False})
    uret(sb, {"kdv": True})


def test_bicim_alani_semasi():
    from tabcel.sablon import sema
    import json
    ham = json.loads((yukleyici.yerlesik_klasor() / "moduller" / "cari_bakiye.json").read_text(encoding="utf-8"))
    ham["sutunlar"][1]["bicim"] = "renk"
    assert any("geçersiz biçim" in str(h) for h in sema.modul_ayristir(ham)[1])
    ham["sutunlar"][1]["bicim"] = "para"
    ham["sutunlar"][0]["bicim"] = "para"
    assert any('yalnız "hesaplanan"' not in str(h) and "bicim" in h.yol for h in sema.modul_ayristir(ham)[1]) is False
    ham = json.loads((yukleyici.yerlesik_klasor() / "moduller" / "urunler.json").read_text(encoding="utf-8"))
    ham["sutunlar"][0]["bicim"] = "para"
    assert any('yalnız "hesaplanan"' in str(h) for h in sema.modul_ayristir(ham)[1])
    ham = json.loads((yukleyici.yerlesik_klasor() / "moduller" / "urunler.json").read_text(encoding="utf-8"))
    ham["formul_satiri"] = 0
    assert any("1 ile 20000" in str(h) for h in sema.modul_ayristir(ham)[1])
    a = json.loads((yukleyici.yerlesik_klasor() / "akislar" / "teklif_formu.json").read_text(encoding="utf-8"))
    a["ayarlar"][1]["eger"] = "yok_bayrak"
    assert any("bilinmeyen bayrak" in str(h) for h in sema.akis_ayristir(a)[1])
    tut, hata = sema.yer_tutucular("=[@a?]+[m.b?]+[m.c]+AYAR.d")
    assert tut == [("sutun", "a", True), ("modul", "m", "b", True), ("modul", "m", "c", False), ("ayar", "d")] and hata == []
    assert sema.yer_tutucular("=[m?]")[1] == ["geçersiz yer tutucu [m?]"]


# ---------------------------------------------------------------- anahtar kelime eşleştirme (altı akış)
@pytest.mark.parametrize("metin, beklenen", [
    ("stok takibi yapmak istiyorum", "stok_takibi"), ("depodaki ürünleri saymak istiyorum", "stok_takibi"),
    ("müşterilerin borç alacak durumunu görmek istiyorum", "cari_hesap"), ("cari hesap tutmak istiyorum", "cari_hesap"),
    ("veresiye defteri lazım", "cari_hesap"), ("tedarikçilere ödeme takibi yapacağım", "cari_hesap"),
    ("apartman aidatlarını takip etmek istiyorum", "apartman_aidat"), ("site yönetimi için aidat tablosu", "apartman_aidat"),
    ("dairelerin borcunu görmek istiyorum", "apartman_aidat"), ("kat malikleri listesi", "apartman_aidat"),
    ("müşterilere teklif hazırlamak istiyorum", "teklif_formu"), ("proforma fatura hazırla", "teklif_formu"),
    ("fiyat teklifi vereceğim", "teklif_formu"),
    ("çek ve senet takibi", "cek_senet"), ("vadesi gelen çekleri görmek istiyorum", "cek_senet"),
    ("senetlerimi takip etmek istiyorum", "cek_senet"), ("portföydeki çekler", "cek_senet"),
    ("öğrenci notlarını girmek istiyorum", "not_cizelgesi"), ("sınav sonuçları ortalaması", "not_cizelgesi"),
    ("karne hazırlamak istiyorum", "not_cizelgesi"), ("sınıf listesi ve notlar", "not_cizelgesi"),
])
def test_anahtar_kelime_altı_akis(metin, beklenen):
    from tabcel.sablon import eslestirici
    oneriler = eslestirici.oneri(metin, DEPO.akislar())
    assert oneriler and oneriler[0].akis.kimlik == beklenen, [(e.akis.kimlik, e.puan) for e in oneriler]


@pytest.mark.parametrize("metin", ["", "   ", "bugün hava çok güzel", "kira ödemesi", "ab", "yemek tarifi", "tatil planı"])
def test_anahtar_kelime_eslesmez(metin):
    from tabcel.sablon import eslestirici
    assert eslestirici.oneri(metin, DEPO.akislar()) == []


def test_ifade_oneki_eslesmesi():
    from tabcel.sablon import eslestirici
    assert eslestirici._ifade_var(["teklif", "hazirla"], ["teklif", "hazirlamak", "istiyorum"])
    assert not eslestirici._ifade_var(["teklif", "hazirla"], ["hazirlamak", "teklif"])             # sıra önemli
    assert not eslestirici._ifade_var(["teklif", "hazirla"], ["teklif"])
