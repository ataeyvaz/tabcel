"""İşaretleme modu mantığı (Qt'siz): ekleme konumu, renkler, F4 döngüsü."""
import pytest

from tabcel.formul import isaretleme as i
from tabcel.model.adres import Aralik


@pytest.mark.parametrize("metin", ["=", "=(", "=TOPLA(", "=A1+", "=A1+ ", "=EĞER(A1>1;", "=-", "=A1*(", "=A1<="])
def test_eklenebilir_konumlar(metin):
    assert i.eklenebilir(metin, len(metin))


@pytest.mark.parametrize("metin", ["=A1", "=TOPLA(A1)", "=5", "=\"a", "=A1%", "=TOPLA", "metin", ""])
def test_eklenemez_konumlar(metin):
    assert not i.eklenebilir(metin, len(metin))


def test_eklenebilir_imlec_ortada():
    assert i.eklenebilir("=A1+B1", 4)          # '+' ten sonra
    assert not i.eklenebilir("=A1+B1", 3)      # A1 içinde/sonrasında


def test_basvuru_konumlari_ve_renkler():
    m = "=TOPLA(A1:B2;Sayfa2!C3)+A1"
    b = i.renkli_basvurular(m)
    assert [m[x:y] for x, y, _, _ in b] == ["A1:B2", "Sayfa2!C3", "A1"]
    assert len({r for *_, r in b}) == 3


def test_renk_paleti_doner():
    m = "=" + "+".join(f"A{n}" for n in range(1, 11))
    r = [x[3] for x in i.renkli_basvurular(m)]
    assert r[0] == r[8] and r[1] == r[9] and r[0] != r[1]


def test_hatali_formulde_bos():
    assert i.basvurular("=TOPLA(\"A1") == []
    assert i.basvurular("A1+B1") == []


def test_basvuru_metni():
    assert i.basvuru_metni(Aralik(1, 1, 1, 1)) == "A1"
    assert i.basvuru_metni(Aralik(1, 1, 3, 2)) == "A1:B3"
    assert i.basvuru_metni(Aralik(2, 3, 2, 3), "Sayfa 2") == "'Sayfa 2'!C2"
    assert i.basvuru_metni(Aralik(1, 1, 1048576, 3)) == "A:C"
    assert i.basvuru_metni(Aralik(2, 1, 5, 16384)) == "2:5"


def test_f4_dongusu():
    m, k = "=A1+B1", 3
    gorulen = []
    for _ in range(5):
        m, k = i.f4(m, k)
        gorulen.append(m)
    assert gorulen == ["=$A$1+B1", "=A$1+B1", "=$A1+B1", "=A1+B1", "=$A$1+B1"]


def test_f4_aralik_ve_sayfa_oneki_ve_imlec():
    assert i.f4("=TOPLA(A1:B2)", 8) == ("=TOPLA($A$1:$B$2)", 16)
    assert i.f4("=Sayfa2!A1", 10) == ("=Sayfa2!$A$1", 12)
    assert i.f4("=5+A1", 2) == ("=5+A1", 2)          # imleç başvuruda değil


def test_ad_oneki():
    assert i.ad_oneki("=TOP", 4) == (1, "TOP")
    assert i.ad_oneki("=A1+TO", 6) == (4, "TO")
    assert i.ad_oneki("=TOPLA(EĞ", 9) == (7, "EĞ")
    assert i.ad_oneki("=TOPLA(A1)", 10) is None    # ')' sonrası: ad konumu değil
    assert i.ad_oneki("=\"TO", 4) is None          # metin içinde


def test_oneriler_turkce_ad_ve_sirali():
    assert i.oneriler("topl") == ["TOPLA", "TOPLA.ÇARPIM", "TOPLAMA"]   # TOPLAMA (AGGREGATE) 2026-10-15 eklendi
    assert "EĞER" in i.oneriler("eğ") and i.oneriler("eğ") == sorted(i.oneriler("eğ"))
    assert i.oneriler("zzzz") == []
    assert len(i.oneriler("e", en_cok=3)) == 3


def test_ipucu():
    assert i.ipucu("=EĞER(", 6) == "EĞER(arg1; arg2; [arg3])"
    assert i.ipucu("=TOPLA(A1;", 10).startswith("TOPLA(arg1; [arg2]")
    assert i.ipucu("=EĞER(TOPLA(A1);", 16).startswith("EĞER(")     # kapanan iç çağrı atlanır
    assert i.ipucu("=(1+", 4) is None and i.ipucu("5", 1) is None
