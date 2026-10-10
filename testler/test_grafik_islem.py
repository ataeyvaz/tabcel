"""Faz 6 / 6f: grafik işlemleri (Qt'siz) — kurma, tür değiştirme, satır/sütun, renk şeması, aralık başvurusu."""
import pytest

from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Referans, Seri, referans_metni
from tabcel.model.grafik_islem import (
    GALERI, alt_tur_gecerli, grafik_kur, referans_coz, referans_yaz, renk_sema_renkleri, renk_sema_uygula,
    satir_sutun_degistir, seri_rengi, tur_degistir,
)
from tabcel.model.grafik_verisi import grafik_verisi
from tabcel.model.sayfa import CalismaKitabi, Hucre


@pytest.fixture
def kitap():
    k = CalismaKitabi()
    Hesaplayici(k)
    return k


@pytest.fixture
def sayfa(kitap):
    s = kitap.sayfalar[0]
    for i, satir in enumerate([[None, "Ocak", "Şubat"], ["Elma", 1, 2], ["Armut", 3, 4], ["Kiraz", 5, 6]], 1):
        for j, v in enumerate(satir, 1):
            if v is not None:
                s.ata(i, j, Hucre(v))
    return s


def test_grafik_kur_secimden(sayfa):
    g = grafik_kur(sayfa, Aralik(1, 1, 4, 3), "sutun")
    assert g.tur == "sutun" and len(g.seriler) == 2
    assert g.seriler[0].deger.aralik == Aralik(2, 2, 4, 2) and g.seriler[1].deger.aralik == Aralik(2, 3, 4, 3)
    assert g.seriler[0].kategori.aralik == Aralik(2, 1, 4, 1)


def test_grafik_kur_tek_hucre_bitisik_bolge(sayfa):
    g = grafik_kur(sayfa, Aralik(2, 2, 2, 2), "cizgi")
    assert len(g.seriler) == 2


def test_grafik_kur_bos_ve_metin_hata(kitap):
    with pytest.raises(ValueError, match="sayısal veri yok"):
        grafik_kur(kitap.sayfalar[0], Aralik(1, 1, 3, 3), "sutun")
    s = kitap.sayfalar[0]
    s.ata(1, 1, Hucre("a"))
    s.ata(2, 1, Hucre("b"))
    with pytest.raises(ValueError):
        grafik_kur(s, Aralik(1, 1, 2, 1), "sutun")


def test_grafik_kur_alt_tur_gecersizse_kumelenmis(sayfa):
    assert grafik_kur(sayfa, Aralik(1, 1, 4, 3), "pasta", "yigili").alt_tur == "kumelenmis"
    assert grafik_kur(sayfa, Aralik(1, 1, 4, 3), "sutun", "yigili").alt_tur == "yigili"
    assert len(grafik_kur(sayfa, Aralik(1, 1, 4, 3), "pasta").seriler) == 1


def test_galeri_her_tur_icin_kumelenmis_var():
    for tur, ogeler in GALERI.items():
        assert ogeler[0][0] == "kumelenmis"
        assert alt_tur_gecerli(tur, "yuzde_yigili") in {a for a, _ in ogeler} | {"kumelenmis"}


def test_tur_degistir(sayfa):
    g = grafik_kur(sayfa, Aralik(1, 1, 4, 3), "sutun")
    p = tur_degistir(g, "pasta", "yigili")
    assert p.tur == "pasta" and p.alt_tur == "kumelenmis" and len(p.seriler) == 1
    c = tur_degistir(g, "cizgi", "yigili")
    assert c.alt_tur == "yigili" and len(c.seriler) == 2


def test_satir_sutun_degistir_sutundan_satira(kitap, sayfa):
    g = grafik_kur(sayfa, Aralik(1, 1, 4, 3), "sutun")
    t = satir_sutun_degistir(g)
    assert len(t.seriler) == 3                                   # Elma, Armut, Kiraz
    assert t.seriler[0].deger.aralik == Aralik(2, 2, 2, 3)
    assert t.seriler[0].ad_ref.aralik == Aralik(2, 1, 2, 1)
    assert t.seriler[0].kategori.aralik == Aralik(1, 2, 1, 3)    # Ocak, Şubat
    v = grafik_verisi(kitap, t)
    assert [s.ad for s in v.seriler] == ["Elma", "Armut", "Kiraz"]
    assert list(v.seriler[0].degerler) == [1.0, 2.0]
    assert list(v.seriler[0].kategoriler) == ["Ocak", "Şubat"]


def test_satir_sutun_iki_kez_eski_haline_doner(kitap, sayfa):
    g = grafik_kur(sayfa, Aralik(1, 1, 4, 3), "sutun")
    cift = satir_sutun_degistir(satir_sutun_degistir(g))
    assert [(s.deger, s.ad_ref, s.kategori) for s in cift.seriler] == [(s.deger, s.ad_ref, s.kategori) for s in g.seriler]


def test_satir_sutun_satirda_seri(kitap, sayfa):
    g = grafik_kur(sayfa, Aralik(1, 1, 4, 3), "sutun", satirda_seri=True)
    assert len(g.seriler) == 3 and g.seriler[0].deger.aralik == Aralik(2, 2, 2, 3)
    t = satir_sutun_degistir(g)
    assert len(t.seriler) == 2 and t.seriler[0].deger.aralik == Aralik(2, 2, 4, 2)


def test_satir_sutun_reddedilir(sayfa):
    with pytest.raises(ValueError, match="Pasta"):
        satir_sutun_degistir(grafik_kur(sayfa, Aralik(1, 1, 4, 3), "pasta"))
    with pytest.raises(ValueError):
        satir_sutun_degistir(Grafik())
    parcali = Grafik(seriler=(Seri(deger=Referans(sayfa.kimlik, Aralik(2, 2, 4, 2))),
                              Seri(deger=Referans(sayfa.kimlik, Aralik(2, 4, 4, 4)))))
    with pytest.raises(ValueError, match="bitişik"):
        satir_sutun_degistir(parcali)
    kayik = Grafik(seriler=(Seri(deger=Referans(sayfa.kimlik, Aralik(2, 2, 4, 2))),
                            Seri(deger=Referans(sayfa.kimlik, Aralik(2, 3, 3, 3)))))
    with pytest.raises(ValueError, match="aynı satırları"):
        satir_sutun_degistir(kayik)


def test_renk_semalari(sayfa):
    assert renk_sema_renkleri("Office", 3) == [None, None, None]
    m = renk_sema_renkleri("Mavi Tonları", 3)
    assert len(set(m)) == 3 and all(c.startswith("#") and len(c) == 7 for c in m)
    assert renk_sema_renkleri("Gri Tonları", 1) == ["#7F7F7F"]
    with pytest.raises(ValueError):
        renk_sema_renkleri("Pembe", 2)
    g = renk_sema_uygula(grafik_kur(sayfa, Aralik(1, 1, 4, 3), "sutun"), "Yeşil Tonları")
    assert all(s.renk for s in g.seriler)
    assert seri_rengi(g, 0) == g.seriler[0].renk
    ofis = renk_sema_uygula(g, "Office")
    assert [s.renk for s in ofis.seriler] == [None, None] and seri_rengi(ofis, 0) == "#4472C4"


def test_referans_coz_bicimleri(kitap, sayfa):
    s2 = kitap.sayfa_ekle("Satış Özeti")
    ref = referans_coz(kitap, "Sayfa1!$B$2:$B$5", sayfa)
    assert ref == Referans(sayfa.kimlik, Aralik(2, 2, 5, 2))
    assert referans_coz(kitap, "=b2:b5", sayfa) == ref
    assert referans_coz(kitap, "sayfa1!B2", sayfa) == Referans(sayfa.kimlik, Aralik(2, 2, 2, 2))
    assert referans_coz(kitap, "   ", sayfa) is None
    assert referans_coz(kitap, "'Satış Özeti'!A1:A3", sayfa).sayfa_kimlik == s2.kimlik
    assert referans_coz(kitap, "'SATIŞ ÖZETİ'!A1", sayfa).sayfa_kimlik == s2.kimlik


def test_referans_coz_hatalar(kitap, sayfa):
    with pytest.raises(ValueError, match="sayfa yok"):
        referans_coz(kitap, "Yok!A1:A3", sayfa)
    with pytest.raises(ValueError, match="Geçersiz aralık"):
        referans_coz(kitap, "Sayfa1!ZZZ", sayfa)


def test_referans_yaz_gidis_donus(kitap, sayfa):
    ref = Referans(sayfa.kimlik, Aralik(2, 2, 5, 2))
    metin = referans_yaz(kitap, ref)
    assert metin == referans_metni(ref, "Sayfa1") == "Sayfa1!$B$2:$B$5"
    assert referans_coz(kitap, metin, sayfa) == ref
    assert referans_yaz(kitap, None) == ""
    assert referans_yaz(kitap, Referans(99999, Aralik(1, 1, 1, 1))) == ""
