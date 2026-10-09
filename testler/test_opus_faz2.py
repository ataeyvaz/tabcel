"""Faz 2 Opus gözden geçirmesi (2026-10-09) bulgularının gerileme testleri. Her bölüm bir bulgu."""
import pytest

from tabcel.formul.motor import Hesaplayici
from tabcel.model import deger as D
from tabcel.model.sayfa import CalismaKitabi, Hucre


def F(metin):
    return Hucre(None, metin)


@pytest.fixture
def s():
    k = CalismaKitabi()
    Hesaplayici(k)
    return k.sayfalar[0]


def hesapla(s, formul, r=20, c=20):
    s.ata(r, c, F(formul))
    return s.deger(r, c)


# ------------------------------------------------------------ bulgu 3: EĞER/ÇOKEĞER dizi üzerinde öğe öğe
def test_if_dizi_kosulu_ogeye_ogeye(s):
    for r, v in enumerate([1.0, 2.0, 3.0], start=1):
        s.ata(r, 1, Hucre(v))
    assert hesapla(s, "=SUM(IF(A1:A3>1,A1:A3,0))") == 5.0           # Excel 365: 2+3
    assert hesapla(s, "=SUM(IF(A1:A3>1,1,0))") == 2.0
    assert hesapla(s, "=SUM(IF(A1:A3>5,A1:A3))") == 0.0             # yanlış dal yok → FALSE (sayılmaz)
    assert hesapla(s, "=COUNT(IF(A1:A3>1,A1:A3))") == 2.0          # 2 ve 3; FALSE sayı değil


def test_if_dizi_bos_hucre_ve_hata_ve_metin(s):
    s.ata(1, 1, Hucre(1.0))
    s.ata(3, 1, Hucre(None, "=1/0"))
    s.ata(4, 1, Hucre("a"))
    # A2 boş → koşul YANLIŞ; A3 hata → o öğe hata; A4 metin → #DEĞER!
    assert hesapla(s, "=SUM(IF(A1:A2>0,10,1))") == 11.0
    assert hesapla(s, "=SUM(IF(A1:A3>0,10,1))") == D.BOL0
    assert hesapla(s, "=SUM(IF(A4:A4>0,10,1))") == 10.0  # tek hücre: skaler yol; metin > sayı (Excel)


def test_if_dizi_kosul_sabit_dalli_ve_yayma(s):
    for r, v in enumerate([1.0, 2.0, 3.0], start=1):
        s.ata(r, 1, Hucre(v))
        s.ata(r, 2, Hucre(v * 10))
    assert hesapla(s, "=SUM(IF(A1:A3>1,B1:B3,A1:A3))") == 1 + 20 + 30
    assert hesapla(s, "=SUMPRODUCT(IF(A1:A3>1,1,0),B1:B3)") == 50.0
    # farklı boyutlu dal: yetmeyen yerde #YOK
    assert hesapla(s, "=SUM(IF(A1:A3>0,B1:B2,0))") == D.YOK


def test_if_skaler_davranis_degismedi(s):
    s.ata(1, 1, Hucre(5.0))
    assert hesapla(s, '=IF(A1>1,"b","k")') == "b"
    assert hesapla(s, "=IF(A1>9,1)") is False
    assert hesapla(s, "=IF(A1:A1>1,1,2)") == 1.0                    # 1 hücreli aralık skaler


def test_ifs_dizi(s):
    for r, v in enumerate([1.0, 2.0, 3.0], start=1):
        s.ata(r, 1, Hucre(v))
    assert hesapla(s, "=SUM(IFS(A1:A3>1,A1:A3,TRUE,0))") == 5.0
    assert hesapla(s, "=SUM(IFS(A1:A3=1,10,A1:A3=2,20,A1:A3=3,30))") == 60.0
    assert hesapla(s, "=SUM(IFS(A1:A3>1,A1:A3))") == D.YOK          # A1 için hiçbir koşul doğru değil
    # skaler koşullar eskisi gibi
    assert hesapla(s, "=IFS(FALSE,1,TRUE,2)") == 2.0


# ------------------------------------------------------------ bulgu 6: DATEDIF'in Türkçe adı ETARİHLİ
def tr(s, metin, r=20, c=20):
    from tabcel.formul.ceviri import hucre_girdisi
    s.ata(r, c, hucre_girdisi(metin, s.kitap))
    return s.deger(r, c)


def test_etarihli_turkce_ad_ve_microsoft_ornekleri(s):
    """Microsoft tr-tr ETARİHLİ sayfasının örnekleri: 1.1.2001–1.1.2003 "Y" = 2; 1.6.2001–15.8.2002
    "G" = 440, "YG" = 75."""
    assert tr(s, '=ETARİHLİ(TARİH(2001;1;1);TARİH(2003;1;1);"Y")') == 2.0
    assert tr(s, '=ETARİHLİ(TARİH(2001;6;1);TARİH(2002;8;15);"G")') == 440.0
    assert tr(s, '=ETARİHLİ(TARİH(2001;6;1);TARİH(2002;8;15);"YG")') == 75.0
    assert tr(s, '=ETARİHLİ(TARİH(2001;6;1);TARİH(2002;8;15);"D")') == 440.0     # İngilizce birim de çalışır
    assert tr(s, '=ETARİHLİ(TARİH(2003;1;1);TARİH(2001;1;1);"Y")') == D.SAYI       # başlangıç > bitiş
    assert tr(s, '=ETARİHLİ(TARİH(2001;1;1);TARİH(2002;1;1);"X")') == D.SAYI


def test_eski_yanlis_ad_tanimsiz(s):
    from tabcel.formul import adlar
    assert adlar.ingilizcesi("ETARİHLİ") == "DATEDIF"
    assert adlar.ingilizcesi("TARİHFARKI") is None


# ------------------------------------------------------------ bulgu 4: ölçüt dizi/aralık olunca öğe öğe
def test_eğersay_olcut_araligi_benzersiz_sayma_deyimi(s):
    for r, v in enumerate(["a", "b", "a", "c"], start=1):
        s.ata(r, 1, Hucre(v))
    # Excel: =TOPLA.ÇARPIM(1/EĞERSAY(A1:A4;A1:A4)) = benzersiz değer sayısı = 3
    assert hesapla(s, "=SUMPRODUCT(1/COUNTIF(A1:A4,A1:A4))") == pytest.approx(3.0)
    assert hesapla(s, "=SUM(COUNTIF(A1:A4,A1:A4))") == 2 + 1 + 2 + 1
    # tek ölçüt: eskisi gibi
    assert hesapla(s, '=COUNTIF(A1:A4,"a")') == 2.0


def test_etopla_ve_cokolcutlu_olcut_dizisi(s):
    for r, (k, v) in enumerate([("a", 1.0), ("b", 2.0), ("a", 3.0)], start=1):
        s.ata(r, 1, Hucre(k))
        s.ata(r, 2, Hucre(v))
    s.ata(1, 4, Hucre("a"))
    s.ata(2, 4, Hucre("b"))
    assert hesapla(s, "=SUM(SUMIF(A1:A3,D1:D2,B1:B3))") == 4.0 + 2.0
    assert hesapla(s, "=SUM(SUMIFS(B1:B3,A1:A3,D1:D2))") == 4.0 + 2.0
    assert hesapla(s, "=SUM(COUNTIFS(A1:A3,D1:D2,B1:B3,\">1\"))") == 1.0 + 1.0
    assert hesapla(s, "=SUM(AVERAGEIF(A1:A3,D1:D2,B1:B3))") == pytest.approx(2.0 + 2.0)
    assert hesapla(s, "=SUM(MAXIFS(B1:B3,A1:A3,D1:D2))") == 3.0 + 2.0


# ------------------------------------------------------------ bulgu 5: ölçütte Türkçe hata adı
def test_olcutte_turkce_hata_adi(s):
    s.ata(1, 1, Hucre(1.0))
    s.ata(2, 1, F("=1/0"))
    s.ata(3, 1, F("=NA()"))
    assert s.deger(3, 1) == D.YOK
    from tabcel.formul.ceviri import hucre_girdisi
    for formul, beklenen in [('=EĞERSAY(A1:A3;"#BÖL/0!")', 1.0), ('=EĞERSAY(A1:A3;"#YOK")', 1.0),
                             ('=EĞERSAY(A1:A3;"#DIV/0!")', 1.0), ('=EĞERSAY(A1:A3;"<>#BÖL/0!")', 2.0)]:
        s.ata(20, 20, hucre_girdisi(formul, s.kitap))
        assert s.deger(20, 20) == beklenen, formul


def test_na_fonksiyonu_yoksay(s):
    """NA() → #YOK; Türkçe adı YOKSAY (Microsoft tr-tr NA sayfası sözdizimi satırı: YOKSAY())."""
    assert tr(s, "=YOKSAY()") == D.YOK
    assert tr(s, "=EYOKSA(YOKSAY())") is True
    assert tr(s, '=EĞERHATA(YOKSAY();"x")') == "x"
    assert tr(s, "=YOKSAY()+1") == D.YOK
    assert tr(s, "=EĞERSAY(A1:A2;YOKSAY())") == 0.0
