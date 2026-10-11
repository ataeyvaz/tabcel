"""T6: CSV'de bilgi kaybettiren alanlar otomatik metin kalır."""
import pytest

from tabcel.io import csv_io

KORUNUR = ["00123", "0123456789", "12345678901", "1234567890123456789", "TR330006100519786457841326",
           "TR33 0006 1005 1978 6457 8413 26", "1-2", "3/4", "12-05"]
KORUNMAZ = ["123", "0", "1234", "123456789012", "1,5", "0,5", "01/02/2024", "2024-01-02", "abc", "-5", "1234567890123456"[:15]]


@pytest.mark.parametrize("a", KORUNUR)
def test_korunur(a):
    assert csv_io.korunmali_mi(a)
    k, _ = csv_io.kitap_olustur([[a]])
    assert k.sayfalar[0].deger(1, 1) == a


@pytest.mark.parametrize("a", KORUNMAZ)
def test_korunmaz(a):
    assert not csv_io.korunmali_mi(a)


def test_sayi_hala_sayi_olur():
    k, _ = csv_io.kitap_olustur([["123", "1,5"]])
    s = k.sayfalar[0]
    assert s.deger(1, 1) == 123.0 and s.deger(1, 2) == 1.5


def test_koru_kapali_eski_davranis():
    k, _ = csv_io.kitap_olustur([["00123"]], koru=False)
    assert k.sayfalar[0].deger(1, 1) == 123.0
