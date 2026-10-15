"""Faz 4 / 4c: .csv — kodlama/ayraç tanıma, okuma, yazma, gidiş-dönüş."""
import pytest

from tabcel.io import csv_io
from tabcel.model.deger import BOL0
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import StilYama
from tabcel.model.adres import Aralik
from tabcel.model.komutlar import bicim_komutu


# ---- kodlama
def test_kodlama_tani():
    assert csv_io.kodlama_tani("a;b".encode("utf-8-sig")) == "utf-8-sig"
    assert csv_io.kodlama_tani("Şişli;İzmir".encode("utf-8")) == "utf-8"
    assert csv_io.kodlama_tani("Şişli;İzmir;ğüçöı".encode("cp1254")) == "cp1254"
    assert csv_io.kodlama_tani(b"") == "utf-8"


def test_cp1254_dosya_dogru_okunur(tmp_path):
    y = tmp_path / "a.csv"
    y.write_bytes("Ad;Şehir\nAyşe;İstanbul\n".encode("cp1254"))
    satirlar, kod, ayrac = csv_io.dosya_oku(str(y))
    assert kod == "cp1254" and ayrac == ";" and satirlar == [["Ad", "Şehir"], ["Ayşe", "İstanbul"]]


# ---- ayraç
@pytest.mark.parametrize("metin,beklenen", [
    ("a;b;c\n1;2;3\n", ";"),
    ("a,b,c\n1,2,3\n", ","),
    ("a\tb\tc\n1\t2\t3\n", "\t"),
    ("a|b|c\n1|2|3\n", "|"),
    ("ad;fiyat\nkalem;1,5\nsilgi;2,25\n", ";"),               # ondalık virgül ; ayracı yanıltmaz
    ('ad,not\n"Ali, Veli",5\n"Ayşe, Fatma",6\n', ","),         # tırnak içindeki virgül sayılmaz
    ("tek sütun\nbaşka\n", ";"),                              # ayraç yok → varsayılan
    ("", ";"),
])
def test_ayrac_tani(metin, beklenen):
    assert csv_io.ayrac_tani(metin) == beklenen


def test_tirnakli_cok_satirli_alan():
    s = csv_io.satirlari_oku('a;b\n"satır1\nsatır2";x\n', ";")
    assert s == [["a", "b"], ["satır1\nsatır2", "x"]]
    assert csv_io.ayrac_tani('a;b\n"x\ny";z\n') == ";"


# ---- kitap oluşturma
def test_alanlar_elle_yazilmis_gibi_cozulur():
    k, uyari = csv_io.kitap_olustur([["Ad", "Tutar", "Oran", "Tarih", "Formül"],
                                     ["x", "1.234,5", "%15", "12.10.2026", "=A2&B2"]], "Veri")
    s = k.sayfalar[0]
    assert s.ad == "Veri" and uyari == []
    assert s.deger(1, 1) == "Ad" and s.deger(2, 2) == 1234.5 and s.deger(2, 3) == 0.15
    assert s.deger(2, 4) == 46307.0 and s.stil(2, 4).sayi_bicimi != "General"
    assert s.stil(2, 3).sayi_bicimi.endswith("%")
    assert s.hucre(2, 5).formul == "=A2&B2"


def test_metin_olarak_hicbir_sey_cevrilmez():
    k, _ = csv_io.kitap_olustur([["007", "12.10.2026", "=1+1", "%5"]], metin_olarak=True)
    s = k.sayfalar[0]
    assert [s.deger(1, c) for c in range(1, 5)] == ["007", "12.10.2026", "=1+1", "%5"]
    assert all(s.hucre(1, c).formul is None for c in range(1, 5))


def test_bozuk_formul_metin_kalir():
    k, _ = csv_io.kitap_olustur([["=TOPLA(("]])
    assert k.sayfalar[0].deger(1, 1) == "=TOPLA(("


def test_bos_alan_ve_kisa_satir():
    k, _ = csv_io.kitap_olustur([["a", "", "c"], ["d"], []])
    s = k.sayfalar[0]
    assert s.hucre(1, 2) is None and s.deger(1, 3) == "c" and s.deger(2, 1) == "d"


def test_sayfa_adi_uret():
    assert csv_io.sayfa_adi_uret(r"C:\x\Satış: Ocak?.csv") == "Satış_ Ocak_"
    assert csv_io.sayfa_adi_uret("C:/x/" + "u" * 50 + ".csv") == "u" * 31


# ---- yazma
def test_yaz_gorunen_metin_ve_tirnaklama():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("Ali; Veli"))
    s.ata(1, 2, Hucre('tırnak "x"'))
    s.ata(1, 3, Hucre("iki\nsatır"))
    s.ata(2, 1, Hucre(1234.5))
    s.ata(2, 2, Hucre(0.25))
    bicim_komutu(s, [Aralik(2, 2, 2, 2)], StilYama(sayi_bicimi="0%")).yap()
    s.ata(2, 3, Hucre(True))
    s.ata(3, 1, Hucre(BOL0))
    metin = csv_io.metin_yaz(s)
    assert metin == ('"Ali; Veli";"tırnak ""x""";"iki\nsatır"\r\n'
                     '1234,5;25%;DOĞRU\r\n'
                     '#SAYI/0!;;\r\n')


def test_yaz_formul_sonucu_ve_bos_sayfa():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    assert csv_io.metin_yaz(s) == ""
    from tabcel.formul import ceviri
    from tabcel.formul.motor import Hesaplayici
    Hesaplayici(k)
    s.ata(1, 1, Hucre(2.0))
    s.ata(1, 2, Hucre(None, ceviri.iceri("=A1*4", k)))
    assert csv_io.metin_yaz(s) == "2;8\r\n"
    assert csv_io.metin_yaz(s, ",") == "2,8\r\n"


def test_gidis_donus_dosya(tmp_path):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    veri = [["Ürün", "Fiyat", "Not"], ["Çay, siyah", "12,5", "iyi; güzel"], ["Şeker", "8", 'ağır "ürün"']]
    for r, satir in enumerate(veri, start=1):
        for c, a in enumerate(satir, start=1):
            s.ata(r, c, Hucre(a))
    yol = str(tmp_path / "o.csv")
    csv_io.dosya_yaz(s, yol)
    assert open(yol, "rb").read().startswith(b"\xef\xbb\xbf")        # BOM: Türkçe Excel doğru açar
    satirlar, kod, ayrac = csv_io.dosya_oku(yol)
    assert satirlar == veri and kod == "utf-8-sig" and ayrac == ";"
    assert [p.name for p in tmp_path.iterdir()] == ["o.csv"]          # geçici dosya kalmadı


def test_yazma_hatasinda_eski_dosya_bozulmaz(tmp_path, monkeypatch):
    k = CalismaKitabi()
    k.sayfalar[0].ata(1, 1, Hucre("a"))
    yol = str(tmp_path / "e.csv")
    csv_io.dosya_yaz(k.sayfalar[0], yol)
    eski = open(yol, "rb").read()
    import os
    monkeypatch.setattr(os, "replace", lambda *a: (_ for _ in ()).throw(PermissionError()))
    with pytest.raises(csv_io.CsvHatasi):
        csv_io.dosya_yaz(k.sayfalar[0], yol)
    assert open(yol, "rb").read() == eski and [p.name for p in tmp_path.iterdir()] == ["e.csv"]


def test_eksik_dosya():
    with pytest.raises(csv_io.CsvHatasi):
        csv_io.dosya_oku(r"C:\yok\yok.csv")
