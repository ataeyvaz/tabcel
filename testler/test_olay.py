"""K5: kitap düzeyinde değişiklik olayları ve kalıcı sayfa kimliği (Qt'siz)."""
import pytest

from tabcel.model.komutlar import GeriAlYigini, HucrelerDegis, OlcuDegis, SatirEkleSil
from tabcel.model.sayfa import CalismaKitabi, Hucre, Sayfa


@pytest.fixture
def kitap():
    k = CalismaKitabi()
    olaylar = []
    k.dinle(olaylar.append)
    k.olaylar = olaylar
    return k


def turler(k):
    return [o.tur for o in k.olaylar]


def test_hucre_olayi_eski_ve_yeni_tasir(kitap):
    s = kitap.sayfalar[0]
    s.ata(2, 3, Hucre(5.0))
    o = kitap.olaylar[-1]
    assert (o.tur, o.sayfa) == ("hucre", s)
    assert o["degisiklikler"] == {(2, 3): (None, Hucre(5.0))}
    s.ata(2, 3, Hucre("a"))
    assert kitap.olaylar[-1]["degisiklikler"] == {(2, 3): (Hucre(5.0), Hucre("a"))}
    s.ata(2, 3, Hucre())                                 # boş hücre = silme; yeni None olarak bildirilir
    assert kitap.olaylar[-1]["degisiklikler"] == {(2, 3): (Hucre("a"), None)}


def test_degismeyen_yazim_olay_yaymaz(kitap):
    s = kitap.sayfalar[0]
    s.ata(1, 1, Hucre(1.0))
    n = len(kitap.olaylar)
    s.ata(1, 1, Hucre(1.0))                              # aynı girdi
    s.ata(9, 9, None)                                    # zaten boş
    assert len(kitap.olaylar) == n
    s.ata(1, 1, Hucre(True))                             # 1.0 → DOĞRU gerçek değişiklik (K1)
    assert len(kitap.olaylar) == n + 1


def test_sonuc_olayi(kitap):
    s = kitap.sayfalar[0]
    s.ata(1, 1, Hucre(None, "=1+1"))
    s.sonuc_ata(1, 1, 2.0)
    o = kitap.olaylar[-1]
    assert o.tur == "sonuc" and o["anahtar"] == (1, 1) and o["deger"] == 2.0


def test_yapi_olayi_ekle_ve_sil(kitap):
    s = kitap.sayfalar[0]
    s.ata(3, 1, Hucre(1.0))
    kitap.olaylar.clear()
    s.satir_ekle(2, 2)
    o = kitap.olaylar[-1]
    assert (o.tur, o["eksen"], o["nerede"], o["fark"], o["silinen"]) == ("yapi", "satir", 2, 2, {})
    s.sutun_sil(1, 1)
    o = kitap.olaylar[-1]
    assert (o["eksen"], o["nerede"], o["fark"]) == ("sutun", 1, -1)
    assert list(o["silinen"].values()) == [Hucre(1.0)]


def test_reddedilen_ekleme_olay_yaymaz(kitap):
    from tabcel.model.adres import MAX_ROW, AdresHatasi
    s = kitap.sayfalar[0]
    s.ata(MAX_ROW, 1, Hucre("son"))
    kitap.olaylar.clear()
    with pytest.raises(AdresHatasi):
        s.satir_ekle(1, 1)
    assert kitap.olaylar == []


def test_boyut_olayi_komut_ve_geri_al(kitap):
    s = kitap.sayfalar[0]
    y = GeriAlYigini()
    y.calistir(OlcuDegis(s, lambda sy: sy.sutun_genislik.update({1: 99})))
    assert "boyut" in turler(kitap)
    kitap.olaylar.clear()
    y.geri_al()
    assert turler(kitap) == ["boyut"]
    y.yinele()
    assert turler(kitap) == ["boyut", "boyut"]


def test_geri_al_da_olay_yayar(kitap):
    s = kitap.sayfalar[0]
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(s, {(1, 1): Hucre(1.0), (1, 2): Hucre(2.0)}))
    kitap.olaylar.clear()
    y.geri_al()
    assert len(kitap.olaylar) == 1                       # toplu işlem TEK olay
    d = kitap.olaylar[0]["degisiklikler"]
    assert sorted(d) == [(1, 1), (1, 2)] and all(yeni is None for _, yeni in d.values())
    kitap.olaylar.clear()
    y.calistir(SatirEkleSil(s, 1, 1, ekle=True))
    y.geri_al()
    assert [o.tur for o in kitap.olaylar if o.tur == "yapi"] == ["yapi", "yapi"]


def test_dinlemeyi_birakma(kitap):
    gelen = []
    birak = kitap.dinle(gelen.append)
    kitap.sayfalar[0].ata(1, 1, Hucre(1.0))
    assert len(gelen) == 1
    birak()
    birak()                                              # ikinci çağrı zararsız
    kitap.sayfalar[0].ata(1, 2, Hucre(1.0))
    assert len(gelen) == 1


def test_birden_cok_dinleyici_sirayla_cagrilir():
    k = CalismaKitabi()
    sira = []
    k.dinle(lambda o: sira.append("a"))
    k.dinle(lambda o: sira.append("b"))
    k.sayfalar[0].ata(1, 1, Hucre(1.0))
    assert sira == ["a", "b"]


def test_kitapsiz_sayfa_olay_yaymadan_calisir():
    s = Sayfa("Bağımsız")
    s.ata(1, 1, Hucre(1.0))
    s.satir_ekle(1, 1)
    assert s.deger(2, 1) == 1.0 and s.kitap is None


# --- sayfa olayları ve kimlik ---
def test_sayfa_olaylari(kitap):
    a = kitap.sayfalar[0]
    b = kitap.sayfa_ekle()
    o = kitap.olaylar[-1]
    assert (o.tur, o.sayfa, o["islem"], o["indeks"]) == ("sayfa", b, "ekle", 1)
    kitap.yeniden_adlandir(b, "Özet")
    o = kitap.olaylar[-1]
    assert (o["islem"], o["eski_ad"], o["indeks"]) == ("ad", "Sayfa2", 1)
    kitap.sayfa_tasi(b, 0)
    o = kitap.olaylar[-1]
    assert (o["islem"], o["indeks"], o["eski_indeks"]) == ("tasi", 0, 1)
    assert kitap.sayfalar == [b, a]
    kitap.sayfa_sil(b)
    o = kitap.olaylar[-1]
    assert (o["islem"], o["indeks"], o.sayfa) == ("sil", 0, b)


def test_degismeyen_sayfa_islemleri_olay_yaymaz(kitap):
    a = kitap.sayfalar[0]
    kitap.sayfa_ekle()
    n = len(kitap.olaylar)
    kitap.yeniden_adlandir(a, a.ad)                      # aynı ad
    kitap.sayfa_tasi(a, 0)                               # zaten orada
    assert len(kitap.olaylar) == n


def test_kimlikler_benzersiz_ve_kalici(kitap):
    a = kitap.sayfalar[0]
    b = kitap.sayfa_ekle()
    c = kitap.sayfa_ekle()
    assert len({a.kimlik, b.kimlik, c.kimlik}) == 3 and 0 not in (a.kimlik, b.kimlik, c.kimlik)
    k_b = b.kimlik
    kitap.yeniden_adlandir(b, "Yeni Ad")
    kitap.sayfa_tasi(b, 0)
    assert b.kimlik == k_b and kitap.sayfa_kimlikle(k_b) is b
    assert kitap.sayfa_kimlikle(9999) is None


def test_silinen_sayfa_geri_konunca_ayni_kimlik_ve_veri(kitap):
    a = kitap.sayfalar[0]
    b = kitap.sayfa_ekle("Veri")
    b.ata(4, 4, Hucre("kalıcı"))
    kim = b.kimlik
    indeks = kitap.sayfa_sil(b)
    assert indeks == 1 and kitap.sayfa_kimlikle(kim) is None
    c = kitap.sayfa_ekle()                               # yeni sayfa eski kimliği yeniden kullanmaz
    assert c.kimlik != kim
    kitap.sayfa_sil(c)
    kitap.sayfa_geri_koy(b, indeks)
    assert kitap.sayfalar == [a, b] and b.kimlik == kim and b.deger(4, 4) == "kalıcı"
    assert kitap.olaylar[-1]["islem"] == "ekle" and kitap.olaylar[-1]["indeks"] == 1
    kitap.olaylar.clear()
    b.ata(5, 5, Hucre(1.0))                              # geri konan sayfa yeniden olay yayar
    assert turler(kitap) == ["hucre"]


def test_silinmis_sayfa_olay_yaymaz(kitap):
    b = kitap.sayfa_ekle("Gecici")
    kitap.sayfa_sil(b)
    kitap.olaylar.clear()
    b.ata(1, 1, Hucre(1.0))                              # kitaptan çıkmış; sessiz
    assert kitap.olaylar == [] and b.kitap is None


def test_geri_koyma_hatalari(kitap):
    a = kitap.sayfalar[0]
    with pytest.raises(ValueError):
        kitap.sayfa_geri_koy(a, 0)                       # zaten kitapta
    b = kitap.sayfa_ekle("B")
    kitap.sayfa_sil(b)
    kitap.sayfa_ekle("b")                                # aynı ad (büyük/küçük harf duyarsız) alındı
    with pytest.raises(ValueError):
        kitap.sayfa_geri_koy(b, 1)


def test_sayfa_silme_son_sayfa_ve_olay(kitap):
    with pytest.raises(ValueError):
        kitap.sayfa_sil(kitap.sayfalar[0])
    assert kitap.olaylar == []


def test_kitap_kimlikleri_1den_baslar():
    k = CalismaKitabi()
    assert k.sayfalar[0].kimlik == 1 and k.sayfalar[0].kitap is k
