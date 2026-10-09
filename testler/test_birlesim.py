"""Faz 3 / 3f: birleştirilmiş hücreler — model, komut, ekle-sil, olay, geri al (Qt'siz)."""
import pytest

from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import AdresHatasi, Aralik
from tabcel.model.komutlar import (
    BirlesimDegis, GeriAlYigini, SatirEkleSil, SutunEkleSil, birlesim_komutu, birlesim_veri_kaybi,
)
from tabcel.model.sayfa import CalismaKitabi, Hucre


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def sayfa(kitap):
    return kitap.sayfalar[0]


def A(r1, c1, r2, c2):
    return Aralik(r1, c1, r2, c2)


def test_yaz_ve_sorgula(sayfa):
    sayfa.birlesimleri_yaz([A(2, 2, 3, 4)], [])
    assert sayfa.birlesim(2, 2) == A(2, 2, 3, 4) and sayfa.birlesim(3, 4) == A(2, 2, 3, 4)
    assert sayfa.birlesim(4, 2) is None and sayfa.birlesim(1, 1) is None
    assert sayfa.birlesim_kesisen(A(1, 1, 2, 2)) == [A(2, 2, 3, 4)]
    assert sayfa.birlesim_kesisen(A(5, 5, 6, 6)) == []
    sayfa.birlesimleri_yaz([], [A(2, 2, 3, 4)])
    assert sayfa.birlesim(2, 2) is None and sayfa.birlesimler == []


def test_gecersiz_birlesimler(sayfa):
    sayfa.birlesimleri_yaz([A(2, 2, 3, 3)], [])
    with pytest.raises(ValueError):
        sayfa.birlesimleri_yaz([A(3, 3, 4, 4)], [])           # çakışır
    with pytest.raises(ValueError):
        sayfa.birlesimleri_yaz([A(5, 5, 5, 5)], [])           # tek hücre
    with pytest.raises(ValueError):
        sayfa.birlesimleri_yaz([], [A(9, 9, 9, 10)])          # yok
    with pytest.raises(AdresHatasi):
        sayfa.birlesimleri_yaz([A(1, 1, 2000000, 2)], [])
    assert sayfa.birlesimler == [A(2, 2, 3, 3)]                # hatada değişmedi
    sayfa.birlesimleri_yaz([A(3, 3, 4, 4)], [A(2, 2, 3, 3)])  # aynı çağrıda eskisi kalkarsa çakışma yok
    assert sayfa.birlesimler == [A(3, 3, 4, 4)]


def test_olay_birlesim_bilgisi(kitap, sayfa):
    olaylar = []
    kitap.dinle(olaylar.append)
    sayfa.birlesimleri_yaz([A(1, 1, 1, 2)], [])
    o = [e for e in olaylar if e.tur == "bicim"]
    assert len(o) == 1 and o[0]["birlesim"] == ([A(1, 1, 1, 2)], []) and o[0]["degisiklikler"] == {}


def test_birlestir_icerik_siler_sol_ust_kalir(sayfa):
    sayfa.ata(1, 1, Hucre("a"))
    sayfa.ata(1, 2, Hucre("b"))
    sayfa.ata(2, 2, Hucre(5.0))
    y = GeriAlYigini()
    assert birlesim_veri_kaybi(sayfa, A(1, 1, 2, 2), "birlestir")
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 2, 2)], "birlestir"))
    assert sayfa.hucre(1, 1) == Hucre("a") and sayfa.hucre(1, 2) is None and sayfa.hucre(2, 2) is None
    assert sayfa.birlesimler == [A(1, 1, 2, 2)]
    y.geri_al()                                                 # tek adım: içerik + birleşim
    assert sayfa.hucre(1, 2) == Hucre("b") and sayfa.hucre(2, 2) == Hucre(5.0) and sayfa.birlesimler == []
    y.yinele()
    assert sayfa.birlesimler == [A(1, 1, 2, 2)] and sayfa.hucre(1, 2) is None


def test_veri_kaybi_yalniz_sol_ust_doluysa_yok(sayfa):
    sayfa.ata(1, 1, Hucre("a"))
    assert not birlesim_veri_kaybi(sayfa, A(1, 1, 2, 2), "birlestir")
    assert not birlesim_veri_kaybi(sayfa, A(1, 1, 1, 1), "birlestir")


def test_birlestir_ve_ortala_stil(sayfa):
    sayfa.ata(1, 1, Hucre("a"))
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 1, 3)], "ortala"))
    assert sayfa.stil(1, 1).yatay == "orta" and sayfa.birlesim(1, 3) == A(1, 1, 1, 3)
    y.geri_al()
    assert sayfa.stil(1, 1).yatay == "genel" and sayfa.birlesimler == []


def test_satirlar_boyunca(sayfa):
    sayfa.ata(1, 1, Hucre("x"))
    sayfa.ata(2, 1, Hucre("y"))
    sayfa.ata(2, 2, Hucre("z"))
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 3, 3)], "satirlar"))
    assert sayfa.birlesimler == [A(1, 1, 1, 3), A(2, 1, 2, 3), A(3, 1, 3, 3)]
    assert sayfa.hucre(2, 1) == Hucre("y") and sayfa.hucre(2, 2) is None
    assert birlesim_komutu(sayfa, [A(1, 1, 3, 1)], "satirlar") is None       # tek sütun: iş yok


def test_tek_hucre_ve_cozulecek_yoksa_none(sayfa):
    assert birlesim_komutu(sayfa, [A(1, 1, 1, 1)], "birlestir") is None
    assert birlesim_komutu(sayfa, [A(1, 1, 3, 3)], "coz") is None


def test_coz(sayfa):
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 2, 2)], "birlestir"))
    y.calistir(birlesim_komutu(sayfa, [A(4, 4, 5, 5)], "birlestir"))
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 1, 1)], "coz"))   # tek hücre bile birleşimi çözer
    assert sayfa.birlesimler == [A(4, 4, 5, 5)]
    y.geri_al()
    assert len(sayfa.birlesimler) == 2
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 9, 9)], "coz"))
    assert sayfa.birlesimler == []


def test_eski_birlesimi_kapsayan_yeni_birlesim(sayfa):
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(2, 2, 3, 3)], "birlestir"))
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 4, 4)], "birlestir"))
    assert sayfa.birlesimler == [A(1, 1, 4, 4)]
    y.geri_al()
    assert sayfa.birlesimler == [A(2, 2, 3, 3)]


def test_kismen_kesen_ve_coklu_aralik_reddedilir(sayfa):
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(2, 2, 3, 3)], "birlestir"))
    with pytest.raises(ValueError):
        birlesim_komutu(sayfa, [A(3, 3, 5, 5)], "birlestir")
    with pytest.raises(ValueError):
        birlesim_komutu(sayfa, [A(1, 1, 1, 2), A(5, 5, 5, 6)], "birlestir")
    with pytest.raises(ValueError):
        birlesim_komutu(sayfa, [A(1, 1, 1, 2)], "bilinmeyen")


def test_birlestirme_formul_motorunu_gunceller(kitap, sayfa):
    motor = Hesaplayici(kitap)
    y = GeriAlYigini()
    sayfa.ata(1, 1, Hucre(1.0))
    sayfa.ata(1, 2, Hucre(10.0))
    sayfa.ata(3, 1, Hucre(None, "=B1*2"))
    assert sayfa.sonuc(3, 1) == 20.0
    y.calistir(birlesim_komutu(sayfa, [A(1, 1, 1, 2)], "birlestir"))    # B1 silinir
    assert sayfa.sonuc(3, 1) == 0.0                                      # kapsanan hücre boş okunur
    y.geri_al()
    assert sayfa.sonuc(3, 1) == 20.0


def test_satir_ekle_birlesimi_kaydirir_buyutur(sayfa):
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(3, 2, 5, 3)], "birlestir"))
    y.calistir(SatirEkleSil(sayfa, 1, 2, True))                # üstüne: kayar
    assert sayfa.birlesimler == [A(5, 2, 7, 3)]
    y.calistir(SatirEkleSil(sayfa, 6, 1, True))                # içine: büyür
    assert sayfa.birlesimler == [A(5, 2, 8, 3)]
    y.calistir(SatirEkleSil(sayfa, 9, 1, True))                # altına: değişmez
    assert sayfa.birlesimler == [A(5, 2, 8, 3)]
    y.calistir(SatirEkleSil(sayfa, 5, 1, True))                # tam üst satırda ekleme: kayar
    assert sayfa.birlesimler == [A(6, 2, 9, 3)]
    for _ in range(4):
        y.geri_al()
    assert sayfa.birlesimler == [A(3, 2, 5, 3)]
    assert sayfa.birlesim(4, 3) == A(3, 2, 5, 3)


def test_satir_sil_birlesimi_kucultur_ya_da_kaldirir(sayfa):
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(3, 1, 6, 2)], "birlestir"))
    y.calistir(SatirEkleSil(sayfa, 4, 1, False))               # içinden bir satır
    assert sayfa.birlesimler == [A(3, 1, 5, 2)]
    y.calistir(SatirEkleSil(sayfa, 1, 2, False))               # üstteki iki satır
    assert sayfa.birlesimler == [A(1, 1, 3, 2)]
    y.calistir(SatirEkleSil(sayfa, 2, 5, False))               # alt kısım + ötesi: tek satır × 2 sütun kalır
    assert sayfa.birlesimler == [A(1, 1, 1, 2)]
    y.calistir(SutunEkleSil(sayfa, 2, 1, False))               # sütun silinince tek hücreye iner: kalkar
    assert sayfa.birlesimler == []
    y.geri_al()
    assert sayfa.birlesimler == [A(1, 1, 1, 2)]
    for _ in range(3):
        y.geri_al()
    assert sayfa.birlesimler == [A(3, 1, 6, 2)]


def test_sutun_ekle_sil_birlesimi(sayfa):
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(sayfa, [A(1, 3, 2, 5)], "birlestir"))
    y.calistir(SutunEkleSil(sayfa, 1, 1, True))
    assert sayfa.birlesimler == [A(1, 4, 2, 6)]
    y.calistir(SutunEkleSil(sayfa, 5, 2, True))
    assert sayfa.birlesimler == [A(1, 4, 2, 8)]
    y.calistir(SutunEkleSil(sayfa, 4, 5, False))               # tüm sütunlar silinir
    assert sayfa.birlesimler == []
    y.geri_al()
    assert sayfa.birlesimler == [A(1, 4, 2, 8)]


def test_birlesim_degis_komutu_geri_al(sayfa):
    k = BirlesimDegis(sayfa, [A(1, 1, 2, 2)], [])
    k.yap()
    assert sayfa.birlesim(2, 2) == A(1, 1, 2, 2)
    k.geri_al()
    assert sayfa.birlesimler == []
    assert BirlesimDegis(sayfa, [], []).bos_mu()
