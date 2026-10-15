"""Faz 10f: şablon kayıtları + kural motoru (Qt'siz). Alan kuralları tablodaki doğrulamayla, satır kuralları tanımdaki formülle."""
from pathlib import Path

import pytest

from tabcel.formul.motor import Hesaplayici
from tabcel.model.sayfa import Hucre
from tabcel.sablon import kayitlar, yukleyici
from tabcel.sablon.uretici import uret


@pytest.fixture(scope="module")
def depo():
    return yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor"))


def kur(depo, akis="yerlesik:stok_takibi", cevaplar=None):
    r = uret(depo.bul(akis), cevaplar)
    Hesaplayici(r.kitap).tumunu_hesapla()
    b = kayitlar.Baglam.kur(r.kitap)
    assert b is not None
    return r.kitap, b


def taslak(g, satir, **metinler):
    return {k: kayitlar.metinden_hucre(g, satir, k, m) for k, m in metinler.items()}


def kimlikler(ihlaller):
    return [i.kural for i in ihlaller]


# ---------------------------------------------------------------- bağlam / satırlar
def test_baglam_ve_kayit_satirlari(depo):
    kitap, b = kur(depo)
    assert b.modul_kimlikleri() == ["urunler", "stok_hareketleri", "stok_durumu"]
    g = b.gorunum("urunler")
    assert [s.kimlik for s in g.girdi_alanlari()][:2] == ["urun_kodu", "ad"]
    assert kayitlar.kayit_satirlari(g) == [2, 3]                 # 2 örnek ürün
    assert kayitlar.yeni_satir(g) == 4
    assert kayitlar.oku(g, 2)["urun_kodu"] == "U001"


def test_sablon_olmayan_kitapta_baglam_yok():
    from tabcel.model.sayfa import CalismaKitabi
    assert kayitlar.Baglam.kur(CalismaKitabi()) is None


def test_denetim_basarisizsa_baglam_yok(depo):
    kitap, _ = kur(depo)
    s = kitap.sayfalar[0]
    s.ata(1, 1, Hucre("Başka ad"))                               # “Ürün kodu” başlığı yok olur
    kitap.sablon_denetim = None
    assert kayitlar.Baglam.kur(kitap) is None


# ---------------------------------------------------------------- alan kuralları (tablo doğrulamasıyla aynı)
def test_zorunlu_alan(depo):
    _, b = kur(depo)
    g = b.gorunum("urunler")
    t = taslak(g, 4, urun_kodu="U100", ad="")
    i = kayitlar.kayit_denetle(b, g, 4, t)
    assert kimlikler(i) == ["alan:ad"] and "boş bırakılamaz" in i[0].ileti


def test_benzersiz_alan(depo):
    _, b = kur(depo)
    g = b.gorunum("urunler")
    i = kayitlar.kayit_denetle(b, g, 4, taslak(g, 4, urun_kodu="U001", ad="Yeni"))
    assert kimlikler(i) == ["alan:urun_kodu"] and "zaten var" in i[0].ileti
    assert kayitlar.kayit_denetle(b, g, 4, taslak(g, 4, urun_kodu="U100", ad="Yeni")) == []


def test_mevcut_kaydi_duzenlerken_kendisi_cakisma_sayilmaz(depo):
    _, b = kur(depo)
    g = b.gorunum("urunler")
    t = taslak(g, 2, urun_kodu="U001", ad="Değişmiş ad")
    assert kayitlar.kayit_denetle(b, g, 2, t) == []


def test_sayi_kisiti(depo):
    _, b = kur(depo)
    g = b.gorunum("urunler")
    i = kayitlar.kayit_denetle(b, g, 4, taslak(g, 4, urun_kodu="U100", ad="x", alis_fiyati="-5"))
    assert kimlikler(i) == ["alan:alis_fiyati"]
    assert kayitlar.kayit_denetle(b, g, 4, taslak(g, 4, urun_kodu="U100", ad="x", alis_fiyati="12,5")) == []


def test_baglanti_listesi_ve_liste(depo):
    _, b = kur(depo)
    g = b.gorunum("stok_hareketleri")
    ok = taslak(g, 5, tarih="15.10.2026", urun="U001", hareket_turu="Giriş", miktar="3")
    assert kayitlar.kayit_denetle(b, g, 5, ok) == []
    kotu = taslak(g, 5, tarih="15.10.2026", urun="YOK", hareket_turu="Bilinmeyen", miktar="3")
    assert set(kimlikler(kayitlar.kayit_denetle(b, g, 5, kotu))) == {"alan:urun", "alan:hareket_turu"}


def test_kimlik_dogrulayici(depo):
    _, b = kur(depo, "yerlesik:cari_hesap", {"iletisim": True, "vergi": True})
    g = next(x for x in (b.gorunum(m) for m in b.modul_kimlikleri()) if "vergi_no" in x.sutunlar)
    a = {"cari_adi": "Deneme Ltd", "vergi_no": "1234567891", "eposta": "yanlis"}
    t = {k: kayitlar.metinden_hucre(g, 5, k, v) for k, v in a.items()}
    assert set(kimlikler(kayitlar.kayit_denetle(b, g, 5, t))) == {"alan:vergi_no", "alan:eposta"}
    assert t["vergi_no"].deger == "1234567891"                   # metin kalır (kural 15)


# ---------------------------------------------------------------- satır kuralları
def test_stok_kurali_cikis_eksiye_dusemez(depo):
    _, b = kur(depo)
    g = b.gorunum("stok_hareketleri")
    t = taslak(g, 5, tarih="15.10.2026", urun="U001", hareket_turu="Çıkış", miktar="500")
    i = kayitlar.kayit_denetle(b, g, 5, t)
    assert kimlikler(i) == ["stok_negatif_olmasin"] and i[0].siddet == "durdur"
    t = taslak(g, 5, tarih="15.10.2026", urun="U001", hareket_turu="Çıkış", miktar="5")
    assert kayitlar.kayit_denetle(b, g, 5, t) == []


def test_ne_zaman_giris_icin_kural_calismaz(depo):
    _, b = kur(depo)
    g = b.gorunum("stok_hareketleri")
    t = taslak(g, 5, tarih="15.10.2026", urun="U001", hareket_turu="Giriş", miktar="500")
    assert kayitlar.kayit_denetle(b, g, 5, t) == []


def test_giris_ani_kurali_tablo_taramasinda_atlanir(depo):
    kitap, b = kur(depo)
    g = b.gorunum("stok_hareketleri")
    kural = g.modul.kurallar[0]
    assert kayitlar.giris_ani_mi(kural)
    assert kayitlar.tablo_ihlalleri(b) == []                      # örnek veri temiz


# ---------------------------------------------------------------- tablo taraması
def test_yapistirilan_hatali_kayit_yakalanir(depo):
    kitap, b = kur(depo)
    g = b.gorunum("urunler")
    s = g.sayfa
    s.ata(4, 1, Hucre("U001"))                                    # benzersizlik ihlali (yapıştırma doğrulamayı atlar)
    s.ata(4, 2, Hucre(None))                                      # zorunlu ad boş
    s.ata(4, 5, Hucre(-3.0))                                      # eksi fiyat
    Hesaplayici(kitap).tumunu_hesapla()
    ih = kayitlar.tablo_ihlalleri(b, "urunler")
    assert sorted((r, i.alan) for _, r, i in ih) == [(2, "urun_kodu"), (4, "ad"), (4, "alis_fiyati"), (4, "urun_kodu")]   # U001 iki satırda


def test_satir_kurali_yerel_ise_kayitli_satirda_denetlenir(depo):
    kitap, b = kur(depo, "yerlesik:not_cizelgesi")
    from tabcel.sablon.sema import Kural
    g = b.gorunum(b.modul_kimlikleri()[0])
    kimlik = g.girdi_alanlari()[0].kimlik
    # tanıma yerel (yalnız [@x] içeren) bir kural eklenir
    g.modul.kurallar.append(Kural("test_kural", "Test", f'=LEN([@{kimlik}])>100', "Çok kısa", "uyar"))
    for r in kayitlar.kayit_satirlari(g)[:1]:
        i = kayitlar.kural_denetle(b, g, g.modul.kurallar[-1], kayitlar.oku(g, r), satir=r)
        assert i is not None and i.siddet == "uyar" and i.satir == r


# ---------------------------------------------------------------- kaydetme
def test_yazim_haritasi_formulleri_tamamlar(depo):
    kitap, b = kur(depo)
    g = b.gorunum("urunler")
    t = taslak(g, 4, urun_kodu="U100", ad="Yeni ürün")
    yeni = kayitlar.yazim_haritasi(b, g, 4, t)
    assert yeni[(4, 1)].deger == "U100" and yeni[(4, 2)].deger == "Yeni ürün"
    assert not kayitlar.formul_eksik_mi(g, 4)


def test_bos_alan_yazilirken_hucre_silinir(depo):
    _, b = kur(depo)
    g = b.gorunum("urunler")
    t = taslak(g, 2, urun_kodu="U001", ad="")
    assert kayitlar.yazim_haritasi(b, g, 2, t)[(2, 2)] is None


def test_metinden_hucre_tur_cevirir(depo):
    _, b = kur(depo)
    g = b.gorunum("stok_hareketleri")
    assert kayitlar.metinden_hucre(g, 5, "tarih", "01.02.2026").deger == 46054.0
    assert kayitlar.metinden_hucre(g, 5, "miktar", "1.500").deger == 1500.0
    assert kayitlar.metinden_hucre(g, 5, "aciklama", "  ") is None
    assert kayitlar.metinden_hucre(g, 5, "aciklama", "=1+1").deger == "=1+1"   # alanlara formül yazılmaz


# ---------------------------------------------------------------- Sağlık Kontrolü
def test_saglik_kontrolu_kural_ihlalini_bildirir(depo):
    from tabcel.formul import saglik
    kitap, b = kur(depo)
    g = b.gorunum("urunler")
    g.sayfa.ata(4, 1, Hucre("U001"))
    g.sayfa.ata(4, 5, Hucre(-3.0))
    Hesaplayici(kitap).tumunu_hesapla()
    motor = Hesaplayici(kitap)
    bulgular = [x for x in saglik.Tarayici(kitap, motor).tara() if x.kontrol == "kural_ihlali"]
    assert bulgular and all(x.onem == saglik.UYARI for x in bulgular)
    assert any("zaten var" in x.aciklama for x in bulgular)


def test_saglik_temiz_sablonda_kural_ihlali_yok(depo):
    from tabcel.formul import saglik
    kitap, _ = kur(depo)
    assert [x for x in saglik.Tarayici(kitap, Hesaplayici(kitap)).tara() if x.kontrol == "kural_ihlali"] == []


# ---------------------------------------------------------------- barkod (10g)
def _barkodlu(depo):
    kitap, b = kur(depo)
    g = b.gorunum("urunler")
    g.sayfa.ata(2, g.sutunlar["barkod"], Hucre("0123456789012"))        # baştaki sıfır korunur
    g.sayfa.ata(3, g.sutunlar["barkod"], Hucre("8690000000011"))
    return kitap, b


def test_barkod_sutunlari_ve_tam_eslesme(depo):
    _, b = _barkodlu(depo)
    g = b.gorunum("urunler")
    assert [s.kimlik for s in kayitlar.barkod_sutunlari(g)] == ["barkod"]
    assert kayitlar.barkod_ara(g, "0123456789012") == 2
    assert kayitlar.barkod_ara(g, " 8690000000011 ") == 3            # boşluk kırpılır
    assert kayitlar.barkod_ara(g, "123456789012") is None            # sıfırsız ≠ eşleşme
    assert kayitlar.barkod_ara(g, "0123456789012", haric=2) is None
    assert kayitlar.barkod_ara(g, "") is None


def test_baglanti_degeri_barkoddan_urun_kodu(depo):
    _, b = _barkodlu(depo)
    gh = b.gorunum("stok_hareketleri")
    urun = next(s for s in gh.girdi_alanlari() if s.kimlik == "urun")
    assert kayitlar.barkodlu_baglantilar(b, gh) == [urun]
    assert kayitlar.baglanti_degeri(b, urun, "8690000000011") == "U002"
    assert kayitlar.baglanti_degeri(b, urun, "u001") == "U001"       # ürün kodu da kabul (Türkçe harf duyarsız)
    assert kayitlar.baglanti_degeri(b, urun, "0000") is None


# ---------------------------------------------------------------- varyant matrisi (10h)
def _varyant(depo):
    kitap, b = kur(depo, cevaplar={"varyant": True})
    return kitap, b, b.gorunum("varyantlar")


def _h(v):
    return Hucre(v)


def test_matris_tanimi_ve_ortak_alanlar(depo):
    _, b, g = _varyant(depo)
    sa, su, de = kayitlar.matris_tanimi(g)
    assert (sa.kimlik, su.kimlik, de.kimlik) == ("beden", "renk", "miktar")
    assert [s.kimlik for s in kayitlar.matris_ortak_alanlari(g)] == ["urun"]      # barkod benzersiz → matrisle girilmez
    _, b2 = kur(depo)
    assert kayitlar.matris_tanimi(b2.gorunum("urunler")) is None


def test_matris_plani_dolu_hucreler_ayri_satir_bos_hucre_yazilmaz(depo):
    kitap, b, g = _varyant(depo)
    ortak = {"urun": _h("U001")}
    plan = kayitlar.matris_plani(b, g, ortak, {("S", "Kırmızı"): _h(5.0), ("S", "Mavi"): _h(3.0), ("M", "Kırmızı"): _h(2.0),
                                              ("M", "Mavi"): None})
    assert plan.tamam and plan.yeni == 3 and plan.guncellenen == 0
    assert sorted({r for r, _ in plan.yazimlar}) == [2, 3, 4]                    # üç ayrı satır
    for (r, c), h in plan.yazimlar.items():
        if c == g.sutunlar["urun"]:
            assert h.deger == "U001"


def test_matris_ikinci_giriste_degeri_gunceller_yeni_satir_acmaz(depo):
    from tabcel.model.komutlar import HucrelerDegis
    kitap, b, g = _varyant(depo)
    ortak = {"urun": _h("U001")}
    plan = kayitlar.matris_plani(b, g, ortak, {("S", "Kırmızı"): _h(5.0), ("M", "Mavi"): _h(3.0)})
    HucrelerDegis(g.sayfa, plan.yazimlar).yap()
    g.sayfa.ata(2, g.sutunlar["barkod"], Hucre("111"))
    plan2 = kayitlar.matris_plani(b, g, ortak, {("s", "kırmızı"): _h(9.0), ("M", "Mavi"): _h(3.0), ("L", "Mavi"): _h(1.0)})
    assert (plan2.yeni, plan2.guncellenen, plan2.degismeyen) == (1, 1, 1)         # Türkçe harf duyarsız eşleşme
    HucrelerDegis(g.sayfa, plan2.yazimlar).yap()
    assert g.sayfa.deger(2, g.sutunlar["miktar"]) == 9.0
    assert g.sayfa.deger(2, g.sutunlar["barkod"]) == "111"                        # güncellemede diğer alanlara dokunulmadı
    assert kayitlar.matris_mevcut(g, ortak)[("S", "Kırmızı")][0] == 2
    assert g.sayfa.deger(4, g.sutunlar["beden"]) == "L"


def test_matris_ihlalde_hicbir_sey_yazilmaz(depo):
    kitap, b, g = _varyant(depo)
    plan = kayitlar.matris_plani(b, g, {"urun": _h("U001")}, {("S", "Kırmızı"): _h(5.0), ("M", "Mavi"): _h(-2.0)})
    assert not plan.tamam and plan.yazimlar == {} and plan.yeni == 0
    assert plan.ihlaller[0][0] == "Beden M / Renk Mavi" and plan.ihlaller[0][1].alan == "miktar"


def test_matris_zorunlu_ortak_alan_bos_ya_da_gecersiz(depo):
    _, b, g = _varyant(depo)
    plan = kayitlar.matris_plani(b, g, {"urun": None}, {("S", "Kırmızı"): _h(1.0)})
    assert not plan.tamam and plan.ihlaller[0][1].alan == "urun"
    plan = kayitlar.matris_plani(b, g, {"urun": _h("YOK")}, {("S", "Kırmızı"): _h(1.0)})
    assert not plan.tamam                                                         # listede olmayan ürün
