"""Faz 3 / 3g: akıllı giriş (yüzde, para, kesir, saat, tarih), Metin biçimli hücre, düzenleme metni
gidiş-dönüşü, `="1.1.2026"+1` ve METNEÇEVİR (TEXT)."""
import datetime as dt
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from _fonk import hesapla
from tabcel.model import deger as D
from tabcel.model.girdi import akilli_coz, duzenleme_metni, girdi_coz
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil
from tabcel.model.tarihseri import ymd_seri
from tabcel.ui.window import Pencere

BUGUN = dt.date(2026, 10, 9)
S_12_10_2026 = float(ymd_seri(2026, 10, 12))


def coz(metin):
    h, kod = akilli_coz(metin, BUGUN)
    return (None if h is None else (h.deger if h.formul is None else h.formul)), kod


# ------------------------------------------------------------------ desenler (her biri ≥ 4 vaka)
@pytest.mark.parametrize("metin,deger,kod", [
    ("15%", 0.15, "0%"), ("%15", 0.15, "0%"), ("15,5%", 0.155, "0.0%"), ("0%", 0.0, "0%"),
    ("-5%", -0.05, "0%"), ("1.234%", 12.34, "0%"),
])
def test_yuzde(metin, deger, kod):
    d, k = coz(metin)
    assert d == pytest.approx(deger) and k == kod


@pytest.mark.parametrize("metin,deger,kod", [
    ("₺100", 100.0, '"₺"#,##0'), ("100 ₺", 100.0, '"₺"#,##0'), ("$1.234,50", 1234.5, '"$"#,##0.00'),
    ("€5", 5.0, '#,##0 "€"'), ("-₺100", -100.0, '"₺"#,##0'), ("100€", 100.0, '#,##0 "€"'),
])
def test_para(metin, deger, kod):
    assert coz(metin) == (deger, kod)


@pytest.mark.parametrize("metin,deger,kod", [
    ("1 1/2", 1.5, "# ?/?"), ("0 3/4", 0.75, "# ?/?"), ("2 1/10", 2.1, "# ??/??"), ("-1 1/2", -1.5, "# ?/?"),
])
def test_kesir(metin, deger, kod):
    assert coz(metin) == (deger, kod)


def test_kesir_sifira_bolme_metin():
    assert coz("1 1/0") == ("1 1/0", None)


@pytest.mark.parametrize("metin,deger,kod", [
    ("14:30", 14.5 / 24, "hh:mm"), ("14:30:15", (14 * 3600 + 1815) / 86400, "hh:mm:ss"),
    ("2:30 ÖS", 14.5 / 24, "h:mm AM/PM"), ("12:00 AM", 0.0, "h:mm AM/PM"), ("12:30 PM", 12.5 / 24, "h:mm AM/PM"),
    ("0:00", 0.0, "hh:mm"),
])
def test_saat(metin, deger, kod):
    d, k = coz(metin)
    assert d == pytest.approx(deger) and k == kod


@pytest.mark.parametrize("metin", ["25:00", "12:60", "13:00 PM", "14:30:75", "1:2"])
def test_gecersiz_saat_metin(metin):
    assert coz(metin) == (metin, None)


@pytest.mark.parametrize("metin,seri,kod", [
    ("12.10.2026", S_12_10_2026, "d.mm.yyyy"), ("12/10/2026", S_12_10_2026, "d.mm.yyyy"),
    ("12-10-2026", S_12_10_2026, "d.mm.yyyy"), ("12.10.26", S_12_10_2026, "d.mm.yyyy"),
    ("12.10", S_12_10_2026, "d mmmm"), ("12 Ekim 2026", S_12_10_2026, "d mmmm yyyy"),
    ("12 Eki 2026", S_12_10_2026, "dd mmm yyyy"), ("12 Eki", S_12_10_2026, "d mmm"),
    ("12 ekim", S_12_10_2026, "d mmmm"), ("29.2.2024", float(ymd_seri(2024, 2, 29)), "d.mm.yyyy"),
    ("1.1.1900", 1.0, "d.mm.yyyy"), ("1.5", float(ymd_seri(2026, 5, 1)), "d mmmm"),
])
def test_tarih(metin, seri, kod):
    assert coz(metin) == (seri, kod)


def test_iki_haneli_yil_penceresi():
    assert coz("1.1.29")[0] == float(ymd_seri(2029, 1, 1))
    assert coz("1.1.30")[0] == float(ymd_seri(1930, 1, 1))


@pytest.mark.parametrize("metin", ["31.2.2026", "29.2.2025", "32.1.2026", "12.13.2026", "0.5.2026",
                                   "12.10/2026", "1.50", "12.34.56", "1.1.1899"])
def test_gecersiz_tarih_metin_kalir(metin):
    assert coz(metin) == (metin, None)


def test_tarih_ve_saat():
    d, k = coz("12.10.2026 14:30")
    assert d == pytest.approx(S_12_10_2026 + 14.5 / 24) and k == "d.mm.yyyy hh:mm"
    d, k = coz("12.10.2026 2:30:15 PM")
    assert d == pytest.approx(S_12_10_2026 + (14 * 3600 + 1815) / 86400) and k == "d.mm.yyyy hh:mm:ss"


def test_duz_sayi_ve_bilimsel():
    assert coz("12") == (12.0, None) and coz("1.500") == (1500.0, None)       # 3 haneli grup = binlik
    assert coz("1,5") == (1.5, None)
    assert coz("1,5E3") == (1500.0, "0.00E+00") and coz("1E3") == (1000.0, "0.00E+00")


def test_diger_kurallar_degismez():
    assert coz("") == (None, None) and coz("'12.10.2026") == ("12.10.2026", None)
    assert coz("=1+1") == ("=1+1", None) and coz("DOĞRU") == (True, None)
    assert coz("abc") == ("abc", None) and coz("3. kat") == ("3. kat", None)
    assert coz("-") == ("-", None) and coz("%") == ("%", None) and coz("₺") == ("₺", None)


def test_girdi_coz_degismedi_dis_yapistirma_icin():
    assert girdi_coz("12.10.2026") == Hucre("12.10.2026")
    assert girdi_coz("15%") == Hucre("15%") and girdi_coz("1.5") == Hucre("1.5")


# ------------------------------------------------------------------ düzenleme metni gidiş-dönüşü
@pytest.mark.parametrize("deger,kod,metin", [
    (S_12_10_2026, "d.mm.yyyy", "12.10.2026"),
    (S_12_10_2026, "d mmmm yyyy dddd", "12.10.2026"),
    (S_12_10_2026 + 14.5 / 24, "d.mm.yyyy hh:mm", "12.10.2026 14:30:00"),
    (14.5 / 24, "hh:mm", "14:30:00"),
    (0.15, "0%", "15%"), (0.155, "0.0%", "15,5%"),
])
def test_duzenleme_metni_bicimli(deger, kod, metin):
    assert duzenleme_metni(Hucre(deger), kod) == metin
    assert coz(metin)[0] == pytest.approx(deger)               # geri çözülür


def test_duzenleme_metni_bicimsiz_ve_diger():
    assert duzenleme_metni(Hucre(1500.0), "General") == "1500"
    assert duzenleme_metni(Hucre(1500.0), '"₺"#,##0') == "1500"
    assert duzenleme_metni(Hucre(-3.0), "d.mm.yyyy") == "-3"          # negatif tarih gösterilemez
    assert duzenleme_metni(Hucre("m"), "d.mm.yyyy") == "m"
    assert duzenleme_metni(Hucre(None, "=A1"), "d.mm.yyyy") == "=A1"
    assert duzenleme_metni(Hucre(1.0), "bozuk[") == "1"


# ------------------------------------------------------------------ arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    p = Pencere(CalismaKitabi())
    p.show()
    return p


def yaz(p, adres, metin):
    from tabcel.model.adres import hucre_coz
    h = hucre_coz(adres)
    p.izgara().hucre_gir(h.satir, h.sutun, metin)
    return h.satir, h.sutun


def test_hucreye_tarih_yazinca_deger_ve_bicim(pencere):
    g = pencere.izgara()
    r, c = yaz(pencere, "B2", "12.10.2026")
    assert g.sayfa.hucre(r, c) == Hucre(S_12_10_2026)
    assert g.sayfa.stil(r, c).sayi_bicimi == "d.mm.yyyy"
    g.geri_al()                                                 # değer + biçim tek adım
    assert g.sayfa.hucre(r, c) is None and g.sayfa.stil(r, c) == Stil()


def test_yuzde_para_saat_yaziminda_bicim_onerilir(pencere):
    g = pencere.izgara()
    for adres, metin, kod in (("A1", "15%", "0%"), ("A2", "₺100", '"₺"#,##0'), ("A3", "14:30", "hh:mm"),
                              ("A4", "1 1/2", "# ?/?")):
        r, c = yaz(pencere, adres, metin)
        assert g.sayfa.stil(r, c).sayi_bicimi == kod


def test_dolu_bicimli_hucrede_bicim_degismez(pencere):
    g = pencere.izgara()
    g.sayfa.bicim_yaz({(1, 1): g.sayfa.havuz.kimlik(Stil(sayi_bicimi="0.00"))})
    yaz(pencere, "A1", "15%")
    assert g.sayfa.hucre(1, 1) == Hucre(0.15) and g.sayfa.stil(1, 1).sayi_bicimi == "0.00"   # Genel değil → dokunma


def test_metin_bicimli_hucre_her_girdiyi_metin_tutar(pencere):
    g = pencere.izgara()
    g.sayfa.bicim_yaz({(1, 1): g.sayfa.havuz.kimlik(Stil(sayi_bicimi="@"))})
    for metin, beklenen in (("123", "123"), ("12.10.2026", "12.10.2026"), ("=1+1", "=1+1"),
                            ("DOĞRU", "DOĞRU"), ("15%", "15%"), ("'x", "x")):
        yaz(pencere, "A1", metin)
        assert g.sayfa.hucre(1, 1) == Hucre(beklenen), metin
    yaz(pencere, "A1", "")
    assert g.sayfa.hucre(1, 1) is None
    assert g.sayfa.sonuc(1, 1) is None


def test_duzenleme_acilinca_tarih_gosterilir_ve_ayni_deger_kalir(pencere):
    g = pencere.izgara()
    r, c = yaz(pencere, "B2", "12.10.2026")
    g.sec((r, c))
    assert g.aktif_duzenleme_metni() == "12.10.2026"
    assert pencere.formul.text() == "12.10.2026"
    n = len(pencere.yigin._geri)
    yaz(pencere, "B2", g.aktif_duzenleme_metni())                # düzenlemeyi değiştirmeden onayla
    assert len(pencere.yigin._geri) == n                         # yeni komut yok
    assert g.sayfa.hucre(r, c) == Hucre(S_12_10_2026)


def test_formul_ve_duz_sayi_etkilenmez(pencere):
    g = pencere.izgara()
    yaz(pencere, "A1", "5")
    yaz(pencere, "A2", "=A1*2")
    assert g.sayfa.sonuc(2, 1) == 10.0 and g.sayfa.stil(1, 1) == Stil()
    yaz(pencere, "A3", "1,5E3")
    assert g.sayfa.hucre(3, 1) == Hucre(1500.0) and g.sayfa.stil(3, 1).sayi_bicimi == "0.00E+00"


def test_tarih_hucresi_ekranda_bicimli_gorunur(pencere):
    from tabcel.model import sayi_bicimi
    g = pencere.izgara()
    r, c = yaz(pencere, "A1", "12 Ekim 2026")
    assert sayi_bicimi.bicimle(g.sayfa.hucre(r, c).deger, g.sayfa.stil(r, c).sayi_bicimi).metin == "12 Ekim 2026"


# ------------------------------------------------------------------ formülde metin tarihleri
def test_metin_tarihi_aritmetikte_sayiya_cevrilir():
    assert hesapla('="1.1.2026"+1') == float(ymd_seri(2026, 1, 1)) + 1
    assert hesapla('="12.10.2026"-"11.10.2026"') == 1.0
    assert hesapla('="14:30"*24') == pytest.approx(14.5)
    assert hesapla('="15%"+1') == pytest.approx(1.15)
    assert hesapla('="abc"+1') == D.DEGER_HATASI
    assert hesapla('=VALUE("12.10.2026")') == S_12_10_2026
    assert hesapla('=VALUE("31.2.2026")') == D.DEGER_HATASI


# ------------------------------------------------------------------ METNEÇEVİR / TEXT (kural 11: 4 vaka türü)
TEXT = [
    # normal (biçim argümanı Türkçe yazım)
    ('=TEXT(1234.5,"#.##0,00")', "1.234,50", None), ('=TEXT(46307,"gg.aa.yyyy")', "12.10.2026", None),
    ('=TEXT(0.256,"0,0%")', "25,6%", None), ('=TEXT(12,"000")', "012", None),
    ('=TEXT(46307,"g aaaa yyyy gggg")', "12 Ekim 2026 Pazartesi", None), ('=TEXT(0.5,"ss:dd")', "12:00", None),
    ('=TEXT(46307.5+30/1440,"gg.aa.yyyy ss:dd")', "12.10.2026 12:30", None),   # Türkçe Excel: saat s, dakika d (COM ile doğrulandı)
    ('=TEXT(1234.5,"Genel")', "1234,5", None), ('=TEXT(-5,"0,00")', "-5,00", None),
    ('=TEXT(1234.5,"#.##0,00 ""TL""")', "1.234,50 TL", None),
    # boş hücre / boş biçim
    ('=TEXT(A1,"0,00")', "0,00", {"A1": None}), ('=TEXT(5,"")', "", None), ('=TEXT(,"0")', "0", None),
    # hata girdisi
    ('=TEXT(#N/A,"0")', D.YOK, None), ('=TEXT(1/0,"0")', D.BOL0, None), ('=TEXT(1,"[x")', D.DEGER_HATASI, None),
    ('=TEXT(A1,"0")', D.YOK, {"A1": D.YOK}),
    # metin / sayı karışımı
    ('=TEXT("abc","0")', "abc", None), ('=TEXT("12","0,0")', "12,0", None), ('=TEXT(TRUE,"0")', "DOĞRU", None),
    ('=TEXT("12.10.2026","gg.aa.yy")', "12.10.26", None), ('=TEXT(A1,"0,0")', "10,0", {"A1": 10}),
    ('=TEXT(-1,"gg.aa.yyyy")', D.DEGER_HATASI, None),
]


@pytest.mark.parametrize("formul,beklenen,veri", TEXT)
def test_text(formul, beklenen, veri):
    assert hesapla(formul, veri) == beklenen


def test_text_dizi_yayilir():
    veri = {"A1": 1, "A2": 2.5}
    assert hesapla('=SUM(LEN(TEXT(A1:A2,"0,00")))', veri) == 8.0     # "1,00" + "2,50"
