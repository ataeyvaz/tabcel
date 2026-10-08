"""K6: sayfa ekle/sil/yeniden adlandır/taşı geri alınabilir komutlar (Qt'siz)."""
import pytest

from tabcel.model.komutlar import (
    GeriAlYigini, HucrelerDegis, SayfaEkle, SayfaSil, SayfaTasi, SayfaYenidenAdlandir,
)
from tabcel.model.sayfa import CalismaKitabi, Hucre


@pytest.fixture
def kitap():
    k = CalismaKitabi()
    k.olaylar = []
    k.dinle(k.olaylar.append)
    return k


def adlar(k):
    return [s.ad for s in k.sayfalar]


def test_sayfa_ekle_geri_al_yinele_ayni_nesne(kitap):
    y = GeriAlYigini()
    y.calistir(SayfaEkle(kitap, "Yeni"))
    b = kitap.sayfalar[1]
    kim = b.kimlik
    b.ata(2, 2, Hucre("veri"))
    y.geri_al()
    assert adlar(kitap) == ["Sayfa1"]
    y.yinele()
    assert kitap.sayfalar[1] is b and b.kimlik == kim and b.deger(2, 2) == "veri"


def test_sayfa_sil_geri_al_veri_ve_sira_korunur(kitap):
    a = kitap.sayfalar[0]
    b = kitap.sayfa_ekle("B")
    c = kitap.sayfa_ekle("C")
    b.ata(1, 1, Hucre("b-verisi"))
    y = GeriAlYigini()
    y.calistir(SayfaSil(kitap, b))
    assert kitap.sayfalar == [a, c]
    y.geri_al()
    assert kitap.sayfalar == [a, b, c] and b.deger(1, 1) == "b-verisi"
    y.yinele()
    assert kitap.sayfalar == [a, c]


def test_sayfa_yeniden_adlandir_ve_tasi_geri_al(kitap):
    a = kitap.sayfalar[0]
    b = kitap.sayfa_ekle("B")
    y = GeriAlYigini()
    y.calistir(SayfaYenidenAdlandir(kitap, b, "Özet"))
    y.calistir(SayfaTasi(kitap, b, 0))
    assert adlar(kitap) == ["Özet", "Sayfa1"]
    y.geri_al()
    assert adlar(kitap) == ["Sayfa1", "Özet"]
    y.geri_al()
    assert adlar(kitap) == ["Sayfa1", "B"]
    y.yinele()
    y.yinele()
    assert adlar(kitap) == ["Özet", "Sayfa1"] and a.kimlik == 1


def test_gecersiz_yeniden_adlandirma_yigina_girmez(kitap):
    b = kitap.sayfa_ekle("B")
    y = GeriAlYigini()
    for kotu in ("a/b", "", "sayfa1"):
        with pytest.raises(ValueError):
            y.calistir(SayfaYenidenAdlandir(kitap, b, kotu))
    assert not y.geri_alinabilir() and b.ad == "B"


def test_karisik_gecmis_sayfa_silme_dahil_tutarli_geri_alinir(kitap):
    """Sayfadaki yazım → sayfa silme → ikisi de sırayla geri alınır (geçmiş silinmez)."""
    b = kitap.sayfa_ekle("B")
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(b, {(1, 1): Hucre("x")}))
    y.calistir(SayfaSil(kitap, b))
    assert adlar(kitap) == ["Sayfa1"]
    y.geri_al()
    assert adlar(kitap) == ["Sayfa1", "B"] and b.deger(1, 1) == "x"
    y.geri_al()
    assert b.deger(1, 1) is None
    y.yinele()
    y.yinele()
    assert adlar(kitap) == ["Sayfa1"] and b.deger(1, 1) == "x"        # silinmiş sayfada veri saklı


def test_sayfa_komutlari_sayfa_olaylari_yayar(kitap):
    y = GeriAlYigini()
    y.calistir(SayfaEkle(kitap, "B"))
    y.geri_al()
    y.yinele()
    assert [o["islem"] for o in kitap.olaylar if o.tur == "sayfa"] == ["ekle", "sil", "ekle"]


def test_silme_geri_al_sayfa_sirasi_birden_cok_silmede(kitap):
    a = kitap.sayfalar[0]
    b = kitap.sayfa_ekle("B")
    c = kitap.sayfa_ekle("C")
    d = kitap.sayfa_ekle("D")
    y = GeriAlYigini()
    y.calistir(SayfaSil(kitap, b))
    y.calistir(SayfaSil(kitap, d))
    assert kitap.sayfalar == [a, c]
    y.geri_al()
    y.geri_al()
    assert kitap.sayfalar == [a, b, c, d]
