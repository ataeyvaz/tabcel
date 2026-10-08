import pytest

from tabcel.model.adres import (
    MAX_COL, MAX_ROW, AdresHatasi, Aralik, aralik_coz, aralik_icinde,
    aralik_yaz, harften_sutun, hucre_coz, hucre_yaz, sutun_harfe,
)


@pytest.mark.parametrize("n,h", [(1, "A"), (26, "Z"), (27, "AA"), (52, "AZ"),
                                 (53, "BA"), (702, "ZZ"), (703, "AAA"),
                                 (16384, "XFD")])
def test_sutun_cevrimi(n, h):
    assert sutun_harfe(n) == h
    assert harften_sutun(h) == n
    assert harften_sutun(h.lower()) == n


def test_tum_sutunlar_gidis_donus():
    for n in range(1, MAX_COL + 1):
        assert harften_sutun(sutun_harfe(n)) == n


@pytest.mark.parametrize("kotu", ["XFE", "", "A1", "Ş", "AAAA"])
def test_kotu_sutun(kotu):
    with pytest.raises(AdresHatasi):
        harften_sutun(kotu)


def test_sutun_sinir_disi():
    for n in (0, MAX_COL + 1):
        with pytest.raises(AdresHatasi):
            sutun_harfe(n)


def test_hucre_coz_ve_yaz():
    h = hucre_coz("$B$3")
    assert (h.satir, h.sutun, h.satir_mutlak, h.sutun_mutlak) == (3, 2, True, True)
    assert hucre_yaz(3, 2, True, True) == "$B$3"
    h = hucre_coz("c10")
    assert (h.satir, h.sutun, h.satir_mutlak, h.sutun_mutlak) == (10, 3, False, False)
    assert hucre_yaz(10, 3) == "C10"
    h = hucre_coz("A$1")
    assert h.satir_mutlak and not h.sutun_mutlak


def test_hucre_sinirlari():
    assert hucre_coz(f"XFD{MAX_ROW}") [:2] == (MAX_ROW, MAX_COL)
    for kotu in ("A0", f"A{MAX_ROW + 1}", "XFE1", "1A", "A", "A1B", "$$A1"):
        with pytest.raises(AdresHatasi):
            hucre_coz(kotu)


def test_aralik_normalize():
    assert aralik_coz("B2:A1") == Aralik(1, 1, 2, 2)
    assert aralik_coz("C3") == Aralik(3, 3, 3, 3)
    assert aralik_coz("$A$1:$B$2") == Aralik(1, 1, 2, 2)


def test_tam_sutun_ve_satir():
    assert aralik_coz("A:C") == Aralik(1, 1, MAX_ROW, 3)
    assert aralik_coz("C:A") == Aralik(1, 1, MAX_ROW, 3)
    assert aralik_coz("2:5") == Aralik(2, 1, 5, MAX_COL)
    assert aralik_yaz(aralik_coz("A:C")) == "A:C"
    assert aralik_yaz(aralik_coz("2:5")) == "2:5"


def test_aralik_yaz():
    assert aralik_yaz(aralik_coz("B2:A1")) == "A1:B2"
    assert aralik_yaz(aralik_coz("C3")) == "C3"


@pytest.mark.parametrize("kotu", ["A1:B2:C3", "A1:", ":B2", "A:5", f"1:{MAX_ROW + 1}"])
def test_kotu_aralik(kotu):
    with pytest.raises(AdresHatasi):
        aralik_coz(kotu)


def test_aralik_icinde():
    ar = aralik_coz("B2:D4")
    assert aralik_icinde(ar, 3, 3)
    assert aralik_icinde(ar, 2, 2) and aralik_icinde(ar, 4, 4)
    assert not aralik_icinde(ar, 1, 3) and not aralik_icinde(ar, 3, 5)
