"""Değerlendirici: işleçler, tür dönüşümleri, başvurular, dizi semantiği (Qt yok, motor yok)."""
import pytest

from tabcel.formul.agac import formul_ayristir
from tabcel.formul.degerlendir import Baglam, degerlendir, hucre_sonucu
from tabcel.formul.degerler import AralikDeger, Dizi
from tabcel.formul.donustur import karsilastir, metne, sayi_metni, sayiya
from tabcel.formul.yerel import EN
from tabcel.model import deger as D
from tabcel.model.sayfa import CalismaKitabi, Hucre


@pytest.fixture
def kitap():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(1.0))        # A1
    s.ata(2, 1, Hucre(2.0))        # A2
    s.ata(3, 1, Hucre(3.0))        # A3
    s.ata(1, 2, Hucre("3"))        # B1 metin "3"
    s.ata(2, 2, Hucre(True))       # B2
    s.ata(3, 2, Hucre("abc"))      # B3
    s.ata(4, 1, Hucre(D.BOL0))     # A4 hata sabiti
    return k


def hesapla(kitap, formul, satir=10, sutun=10, sayfa=None):
    s = sayfa or kitap.sayfalar[0]
    return hucre_sonucu(formul_ayristir(formul, EN), Baglam(s, satir, sutun, kitap))


@pytest.mark.parametrize("formul,beklenen", [
    ("1+2*3", 7.0), ("(1+2)*3", 9.0), ("-2^2", 4.0), ("0-2^2", -4.0), ("2^3^2", 64.0),
    ("10/4", 2.5), ("50%", 0.5), ("2*50%", 1.0), ("--3", 3.0), ('"a"&"b"', "ab"),
    ("1&2", "12"), ("2.5&\"\"", "2,5"), ("TRUE&\"\"", "DOĞRU"), ("1=1", True), ("1<>1", False),
    ('"a"="A"', True), ('"b">"a"', True), ('1<"a"', True), ('"z"<TRUE', True),
    ("3>2", True), ("2>=2", True), ("1<=0", False),
])
def test_isleçler(kitap, formul, beklenen):
    assert hesapla(kitap, formul) == beklenen


@pytest.mark.parametrize("formul,beklenen", [
    ("1/0", D.BOL0), ("0^0", D.SAYI), ("(-8)^(0.5)", D.SAYI), ("(-8)^(2/3)", D.SAYI), ('"a"+1', D.DEGER_HATASI),
    ("#N/A+1", D.YOK), ("1+#N/A", D.YOK), ("#REF!", D.BASV), ("10^400", D.SAYI),
    ("#DIV/0!&#N/A", D.BOL0),             # soldaki hata önce
    ("TANIMSIZ(1)", D.AD), ("Satislar", D.AD),
])
def test_hatalar(kitap, formul, beklenen):
    assert hesapla(kitap, formul) == beklenen


def test_tur_donusumleri(kitap):
    assert hesapla(kitap, '"3"+1') == 4.0
    assert hesapla(kitap, '"2,5"+1') == 3.5           # Türkçe yerel ayar
    assert hesapla(kitap, '"50%"*2') == 1.0
    assert hesapla(kitap, "TRUE+1") == 2.0
    assert hesapla(kitap, "B1+1") == 4.0              # hücredeki sayı gibi metin de dönüşür
    assert hesapla(kitap, "B2*2") == 2.0
    assert hesapla(kitap, "B3+1") == D.DEGER_HATASI
    assert hesapla(kitap, "A4+1") == D.BOL0


def test_bos_hucre(kitap):
    assert hesapla(kitap, "Z99") == 0.0              # =Z99 (boş) → 0
    assert hesapla(kitap, "Z99+1") == 1.0
    assert hesapla(kitap, 'Z99&"x"') == "x"
    assert hesapla(kitap, 'Z99=""') is True
    assert hesapla(kitap, "Z99=0") is True
    assert hesapla(kitap, "Z99=FALSE") is True


def test_ortuk_kesisim(kitap):
    # B2'de =A1:A3 → aynı satırdaki A2
    assert hesapla(kitap, "A1:A3", satir=2, sutun=2) == 2.0
    assert hesapla(kitap, "A1:A3", satir=9, sutun=2) == D.DEGER_HATASI
    assert hesapla(kitap, "A1:A3*10", satir=3, sutun=5) == 10.0   # dizi → sol üst (taşma yok)


def test_dizi_ogeler(kitap):
    b = Baglam(kitap.sayfalar[0], 10, 10, kitap)
    v = degerlendir(formul_ayristir("A1:A3*2", EN), b)
    assert v == Dizi([[2.0], [4.0], [6.0]])
    v = degerlendir(formul_ayristir("{1,2,3}+{10;20}", EN), b)      # satır × sütun yayılır
    assert v == Dizi([[11.0, 12.0, 13.0], [21.0, 22.0, 23.0]])
    v = degerlendir(formul_ayristir("{1,2,3}+{10,20}", EN), b)      # boyu yetmeyen #YOK
    assert v == Dizi([[11.0, 22.0, D.YOK]])


def test_sum_ve_if(kitap):
    assert hesapla(kitap, "SUM(A1:A3)") == 6.0
    assert hesapla(kitap, "SUM(A1:B3)") == 6.0                       # aralıktaki metin/mantıksal atlanır
    assert hesapla(kitap, 'SUM("3",TRUE,1)') == 5.0                  # doğrudan yazılanlar dönüşür
    assert hesapla(kitap, 'SUM("x")') == D.DEGER_HATASI
    assert hesapla(kitap, "SUM(A1:A4)") == D.BOL0
    assert hesapla(kitap, "SUM(A1:A3*{1;2;3})") == 14.0             # 365 dizi semantiği
    assert hesapla(kitap, "SUM(A:A)") == D.BOL0
    assert hesapla(kitap, "SUM(1,)") == 1.0
    assert hesapla(kitap, 'IF(A1>0,"evet","hayır")') == "evet"
    assert hesapla(kitap, "IF(A1>5,1)") is False
    assert hesapla(kitap, "IF(A1>0,,1)") == 0.0
    assert hesapla(kitap, "IF(TRUE,1,1/0)") == 1.0                  # seçilmeyen dal hesaplanmaz
    assert hesapla(kitap, "IF(#N/A,1,2)") == D.YOK
    assert hesapla(kitap, 'IF("abc",1,2)') == D.DEGER_HATASI
    assert hesapla(kitap, "SUM()") == D.DEGER_HATASI                # argüman sayısı


def test_baska_sayfa(kitap):
    s2 = kitap.sayfa_ekle("Gelir Gider")
    s2.ata(1, 1, Hucre(5.0))
    assert hesapla(kitap, "'Gelir Gider'!A1*2") == 10.0
    assert hesapla(kitap, "Yok!A1") == D.BASV


def test_kimlikli_basvuru(kitap):
    from tabcel.formul.yerel import SAKLI
    s2 = kitap.sayfa_ekle("Veri")
    s2.ata(1, 1, Hucre(7.0))
    d = formul_ayristir(f"=[{s2.kimlik}]!A1+1", SAKLI)
    b = Baglam(kitap.sayfalar[0], 1, 5, kitap)
    assert hucre_sonucu(d, b) == 8.0
    kitap.yeniden_adlandir(s2, "Başka")            # ad değişti: kimlik aynı
    assert hucre_sonucu(d, b) == 8.0
    kitap.sayfa_sil(s2)
    assert hucre_sonucu(d, b) == D.BASV


def test_kesisim_ve_aralik_islec(kitap):
    assert hesapla(kitap, "SUM(A1:A3 A2:B2)") == 2.0
    assert hesapla(kitap, "SUM(A1:A2 B1:B2)") == D.BOS
    assert hesapla(kitap, "SUM(A1:A2:A3)") == 6.0


def test_yakin_sifir(kitap):
    assert hesapla(kitap, "0.5-0.4-0.1") == 0.0
    assert hesapla(kitap, "1*(0.5-0.4-0.1)") != 0.0     # son işlem çarpma: düzeltme yok
    assert hesapla(kitap, "0.1+0.2-0.3") == 0.0
    assert hesapla(kitap, "(0.1+0.2)=0.3") is True       # 15 basamakta karşılaştırma


# --- dönüşüm birimleri ---
def test_sayi_metni():
    assert sayi_metni(2.5) == "2,5"
    assert sayi_metni(1 / 3) == "0,333333333333333"
    assert sayi_metni(-0.0) == "0"
    assert sayi_metni(1e20) == "1E+20"
    assert sayi_metni(123456789012345.0) == "123456789012345"


def test_sayiya_ve_metne():
    assert sayiya(None) == 0.0 and sayiya(False) == 0.0
    assert sayiya(" 12 ") == 12.0
    assert sayiya("") == D.DEGER_HATASI
    assert metne(None) == "" and metne(False) == "YANLIŞ"


def test_karsilastir_turkce():
    assert karsilastir("ılık", "ILIK") == 0
    assert karsilastir("istanbul", "İSTANBUL") == 0
    assert karsilastir(D.YOK, 1.0) == D.YOK


def test_aralik_deger_buyuk_aralik(kitap):
    s = kitap.sayfalar[0]
    a = AralikDeger(s, 1, 1, 1_048_576, 1)
    assert sorted(v for _, _, v in a.dolu() if isinstance(v, float)) == [1.0, 2.0, 3.0]
