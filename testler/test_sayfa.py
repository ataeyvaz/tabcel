import pytest

from tabcel.model.adres import MAX_ROW, AdresHatasi
from tabcel.model.komutlar import (
    GeriAlYigini, Grup, HucrelerDegis, SatirEkleSil, SutunEkleSil,
)
from tabcel.model.sayfa import CalismaKitabi, Hucre, Sayfa


def H(d):
    return Hucre(d)


def dolu(s):
    return {(a, b): h.deger for a, b, h in s.dolu_hucreler()}


def test_ata_oku_sil():
    s = Sayfa("S")
    assert s.hucre(1, 1) is None and s.deger(1, 1) is None
    assert s.ata(1, 1, H(5.0)) is None
    assert s.deger(1, 1) == 5.0
    assert s.ata(1, 1, Hucre()) == H(5.0)      # boş hücre = silme
    assert s.hucre(1, 1) is None
    assert s.kullanilan_aralik() is None


def test_aralik_disi():
    s = Sayfa("S")
    with pytest.raises(AdresHatasi):
        s.ata(MAX_ROW + 1, 1, H(1.0))
    with pytest.raises(AdresHatasi):
        s.ata(1, 0, H(1.0))


def test_kullanilan_aralik_ve_formul():
    s = Sayfa("S")
    s.ata(2, 3, H("a"))
    s.ata(5, 1, Hucre(7.0, "=SUM(A1:A3)"))
    assert s.kullanilan_aralik() == (2, 1, 5, 3)
    assert s.hucre(5, 1).formul == "=SUM(A1:A3)"


def test_satir_ekle_sil():
    s = Sayfa("S")
    for r in (1, 2, 3, 4):
        s.ata(r, 1, H(float(r)))
    s.satir_yukseklik[3] = 40
    s.satir_ekle(2, 2)
    assert dolu(s) == {(1, 1): 1.0, (4, 1): 2.0, (5, 1): 3.0, (6, 1): 4.0}
    assert s.yukseklik(5) == 40
    silinen = s.satir_sil(4, 2)
    assert {k: h.deger for k, h in silinen.items()} == {(4, 1): 2.0, (5, 1): 3.0}
    assert dolu(s) == {(1, 1): 1.0, (4, 1): 4.0}


def test_sutun_sil_olcu():
    s = Sayfa("S")
    s.ata(1, 1, H("a")); s.ata(1, 2, H("b")); s.ata(1, 3, H("c"))
    s.sutun_genislik[2] = 100
    s.sutun_genislik[3] = 120
    s.sutun_sil(2)
    assert dolu(s) == {(1, 1): "a", (1, 2): "c"}
    assert s.sutun_genislik == {2: 120}


def test_kitap_sayfalari():
    k = CalismaKitabi()
    assert [s.ad for s in k.sayfalar] == ["Sayfa1"]
    s2 = k.sayfa_ekle()
    assert s2.ad == "Sayfa2"
    with pytest.raises(ValueError):
        k.sayfa_ekle("sayfa1")                 # büyük/küçük harf duyarsız
    k.yeniden_adlandir(s2, "Özet")
    with pytest.raises(ValueError):
        k.yeniden_adlandir(s2, "SAYFA1")
    k.sayfa_sil(s2)
    with pytest.raises(ValueError):
        k.sayfa_sil(k.sayfalar[0])             # son sayfa silinemez


def test_geri_al_yinele_hucre():
    s = Sayfa("S")
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(s, {(1, 1): H(1.0), (1, 2): H(2.0)}))
    y.calistir(HucrelerDegis(s, {(1, 1): H(9.0), (1, 2): None}))
    assert dolu(s) == {(1, 1): 9.0}
    assert y.geri_al() and dolu(s) == {(1, 1): 1.0, (1, 2): 2.0}
    assert y.geri_al() and dolu(s) == {}
    assert not y.geri_al()
    assert y.yinele() and y.yinele() and dolu(s) == {(1, 1): 9.0}
    assert not y.yinele()


def test_yeni_komut_yinele_yiginini_temizler():
    s = Sayfa("S")
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(s, {(1, 1): H(1.0)}))
    y.geri_al()
    y.calistir(HucrelerDegis(s, {(2, 2): H(2.0)}))
    assert not y.yinelenebilir()


def test_satir_sil_geri_al():
    s = Sayfa("S")
    for r in (1, 2, 3):
        s.ata(r, 1, H(float(r)))
    s.satir_yukseklik[2] = 50
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(s, 2, 1, ekle=False))
    assert dolu(s) == {(1, 1): 1.0, (2, 1): 3.0} and s.satir_yukseklik == {}
    y.geri_al()
    assert dolu(s) == {(1, 1): 1.0, (2, 1): 2.0, (3, 1): 3.0}
    assert s.satir_yukseklik == {2: 50}
    y.yinele()
    assert dolu(s) == {(1, 1): 1.0, (2, 1): 3.0}


def test_sutun_ekle_geri_al_ve_grup():
    s = Sayfa("S")
    s.ata(1, 1, H("a")); s.ata(1, 2, H("b"))
    y = GeriAlYigini()
    y.calistir(Grup([SutunEkleSil(s, 2, 1, ekle=True),
                     HucrelerDegis(s, {(1, 2): H("yeni")})]))
    assert dolu(s) == {(1, 1): "a", (1, 2): "yeni", (1, 3): "b"}
    y.geri_al()                                 # grup tek adım
    assert dolu(s) == {(1, 1): "a", (1, 2): "b"}


def test_yigin_siniri():
    s = Sayfa("S")
    y = GeriAlYigini(sinir=2)
    for i in range(5):
        y.calistir(HucrelerDegis(s, {(1, 1): H(float(i))}))
    assert y.geri_al() and y.geri_al() and not y.geri_al()
    assert s.deger(1, 1) == 2.0


def test_sayfa_adi_dogrulama():
    from tabcel.model.sayfa import sayfa_adi_dogrula
    sayfa_adi_dogrula("Gelir Gider")
    sayfa_adi_dogrula("A" * 31)
    for kotu in ("", "   ", "A" * 32, "a/b", "a\\b", "a?b", "a*b", "a[b", "a]b", "a:b",
                 "'ab", "ab'"):
        with pytest.raises(ValueError):
            sayfa_adi_dogrula(kotu)
    k = CalismaKitabi()
    with pytest.raises(ValueError):
        k.sayfa_ekle("a/b")
    with pytest.raises(ValueError):
        k.yeniden_adlandir(k.sayfalar[0], "x:y")


def test_sayfa_tasi():
    k = CalismaKitabi()
    a = k.sayfalar[0]
    b = k.sayfa_ekle()
    c = k.sayfa_ekle()
    k.sayfa_tasi(c, 0)
    assert k.sayfalar == [c, a, b]
    k.sayfa_tasi(c, 2)
    assert k.sayfalar == [a, b, c]
    with pytest.raises(ValueError):
        k.sayfa_tasi(a, 3)


def test_gizli_satir_sutun_genislik_sifir():
    s = Sayfa("S")
    s.gizli_sutun.add(2)
    s.gizli_satir.add(3)
    s.sutun_genislik[2] = 100
    assert s.genislik(2) == 0 and s.yukseklik(3) == 0
    s.gizli_sutun.clear()
    assert s.genislik(2) == 100          # özgün genişlik korunur


def test_gizli_ekle_sil_ile_kayar():
    s = Sayfa("S")
    s.gizli_satir.update({2, 5, 6})
    s.satir_ekle(3, 2)
    assert s.gizli_satir == {2, 7, 8}
    s.satir_sil(7, 1)
    assert s.gizli_satir == {2, 7}
    s.gizli_sutun.update({1, 4})
    s.sutun_sil(1, 1)
    assert s.gizli_sutun == {3}


def test_olcu_degis_geri_al_yinele():
    from tabcel.model.komutlar import OlcuDegis
    s = Sayfa("S")
    y = GeriAlYigini()
    y.calistir(OlcuDegis(s, lambda sy: sy.sutun_genislik.update({2: 120})))
    y.calistir(OlcuDegis(s, lambda sy: sy.gizli_satir.add(4)))
    assert s.genislik(2) == 120 and s.yukseklik(4) == 0
    y.geri_al()
    assert s.yukseklik(4) == 20 and s.genislik(2) == 120
    y.geri_al()
    assert s.genislik(2) == 64
    y.yinele(); y.yinele()
    assert s.genislik(2) == 120 and s.yukseklik(4) == 0


def test_olcu_degis_onceden_uygulanmis_durum():
    from tabcel.model.komutlar import OlcuDegis
    s = Sayfa("S")
    eski = s.boyut_durumu()
    s.sutun_genislik[1] = 90                    # fare sürüklemesi sırasında doğrudan değişti
    y = GeriAlYigini()
    y.calistir(OlcuDegis(s, eski=eski, yeni=s.boyut_durumu()))
    y.geri_al()
    assert s.genislik(1) == 64
    y.yinele()
    assert s.genislik(1) == 90


def test_satir_sil_geri_al_gizli_doner():
    s = Sayfa("S")
    s.gizli_satir.update({2, 3})
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(s, 2, 1, ekle=False))
    assert s.gizli_satir == {2}
    y.geri_al()
    assert s.gizli_satir == {2, 3}
