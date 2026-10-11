"""T6 (arayüz): sütun türü, ondalık ayırıcı, koruma kutusu."""
import pytest

from tabcel.io import csv_io


def test_sutun_turu_metin_ve_cevir():
    k, _ = csv_io.kitap_olustur([["007", "007", "1-2"]], sutun_turleri={1: "cevir", 3: "metin"})
    s = k.sayfalar[0]
    assert s.deger(1, 1) == 7.0 and s.deger(1, 2) == "007" and s.deger(1, 3) == "1-2"


@pytest.mark.parametrize("a,b", [("3.14", "3,14"), ("1,234.56", "1234,56"), ("-0.5", "-0,5"), ("1.2.3", "1.2.3"),
                                 ("01.02.2024", "01.02.2024"), ("abc", "abc"), ("12", "12")])
def test_ondalik_nokta(a, b):
    assert csv_io.ondalik_noktali_cevir(a) == b


def test_ondalik_nokta_kitapta():
    k, _ = csv_io.kitap_olustur([["3.14", "1,234.56"]], ondalik="nokta")
    s = k.sayfalar[0]
    assert s.deger(1, 1) == 3.14 and s.deger(1, 2) == 1234.56


def test_pencere_sutun_turu_ve_ondalik():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from tabcel.ui.csv_penceresi import CsvAlmaPenceresi
    d = CsvAlmaPenceresi("x.csv", "a;b\n00123;3.14\n".encode("utf-8"))
    d.sutun.setCurrentIndex(1)
    d.tur.setCurrentIndex(d.tur.findData("metin"))
    d.ondalik.setCurrentIndex(d.ondalik.findData("nokta"))
    assert d.sutun_turleri() == {2: "metin"} and d.secili_ondalik() == "nokta" and d.koru_mu()
    assert d.tablo.horizontalHeaderItem(1).text() == "B (metin)"


@pytest.mark.parametrize("ad", ["banka_ekstre", "kimlik_virgul", "sekme_ingilizce", "kod_tarih_benzeri", "uzun_sayi",
                                "bom_noktalivirgul", "satis_tr", "satis_utf8"])
def test_ornek_csv_acilir(ad):
    import pathlib
    yol = pathlib.Path(__file__).parent / "ornekler" / f"{ad}.csv"
    satirlar, _, _ = csv_io.dosya_oku(str(yol))
    k, _ = csv_io.kitap_olustur(satirlar)
    assert k.sayfalar[0].deger(1, 1) is not None


def test_ornek_banka_iban_ve_tutar():
    import pathlib
    yol = pathlib.Path(__file__).parent / "ornekler" / "banka_ekstre.csv"
    satirlar, kod, ayrac = csv_io.dosya_oku(str(yol))
    assert kod == "cp1254" and ayrac == ";"
    s = csv_io.kitap_olustur(satirlar)[0].sayfalar[0]
    assert s.deger(2, 3) == "TR330006100519786457841326" and s.deger(2, 4) == 12500.75
