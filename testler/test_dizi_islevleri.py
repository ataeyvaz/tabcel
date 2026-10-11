"""Faz 8e: dinamik dizi işlevleri (SORT, SORTBY, FILTER, UNIQUE, SEQUENCE, TAKE, DROP, VSTACK, HSTACK, TOCOL, TOROW, CHOOSECOLS,
CHOOSEROWS, EXPAND, TRANSPOSE, RANDARRAY) ve LET. Kural 11: her işlev için normal, boş, hata girdisi ve metin/sayı karışımı
vakaları. Beklenen değerler gerçek Excel 365'ten (COM, 2026-10-11) alındı; sonuçlar INDEX/SUM/ROWS ile skalere sarılarak
karşılaştırılır (taşma ayrı testte: test_tasma.py)."""
import pytest

from tabcel.formul import adlar, ceviri
from tabcel.formul.motor import Hesaplayici
from tabcel.model.deger import Hata
from tabcel.model.sayfa import CalismaKitabi, Hucre

# A1:B4  c 3 / a 1 / b 2 / a 5 ; D1:D3 karışık (sayı, metin, boş) ; F1:F3 hata içeren
VERI = {(1, 1): "c", (1, 2): 3.0, (2, 1): "a", (2, 2): 1.0, (3, 1): "b", (3, 2): 2.0, (4, 1): "a", (4, 2): 5.0,
        (1, 4): 5.0, (2, 4): "x", (4, 4): 7.0}


@pytest.fixture(scope="module")
def sayfa():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for (r, c), v in VERI.items():
        s.ata(r, c, Hucre(v))
    s.ata(1, 6, Hucre(1.0))
    s.ata(2, 6, Hucre(formul="=1/0"))
    s.ata(3, 6, Hucre(3.0))
    Hesaplayici(k)
    return s


def h(sayfa, formul):
    """Formülü sayfanın uzak bir hücresinde (Z sütunu, sayaçla) hesaplayıp sonucunu döner."""
    h.n = getattr(h, "n", 100) + 1
    sayfa.ata(h.n, 26, Hucre(formul=formul))
    return sayfa.deger(h.n, 26)


# (formül, beklenen) — Excel 365 ile doğrulanmış değerler
EXCEL = [
    # SORT
    ("=INDEX(SORT(A1:B4),1,1)", "a"), ("=INDEX(SORT(A1:B4),4,1)", "c"), ("=INDEX(SORT(A1:B4,2,-1),1,2)", 5.0),
    ("=INDEX(SORT(A1:A4,1,-1),1)", "c"), ("=INDEX(SORT(A1:B4,2),1,2)", 1.0),
    ("=ROWS(SORT(A1:B4))", 4.0),
    # SORT: metin/sayı karışımı (sayı < metin < mantıksal; boş en sonda) ve boş hücre
    ("=INDEX(SORT(D1:D4),1)", 5.0), ("=INDEX(SORT(D1:D4),2)", 7.0), ("=INDEX(SORT(D1:D4),3)", "x"),
    ("=INDEX(SORT(D1:D4,1,-1),1)", "x"),
    # SORTBY
    ("=INDEX(SORTBY(A1:A4,B1:B4,-1),1)", "a"), ("=INDEX(SORTBY(A1:A4,B1:B4),1)", "a"),
    ("=INDEX(SORTBY(A1:A4,A1:A4,1,B1:B4,-1),1)", "a"), ("=INDEX(SORTBY(A1:A4,A1:A4,1,B1:B4,-1),2)", "a"),
    # FILTER
    ('=SUM(FILTER(B1:B4,A1:A4="a"))', 6.0), ("=ROWS(FILTER(A1:B4,B1:B4>1))", 3.0),
    ('=ROWS(FILTER(B1:B4,B1:B4>99,"yok"))', 1.0), ('=INDEX(FILTER(B1:B4,B1:B4>99,"yok"),1)', "yok"),
    ('=IFERROR(FILTER(B1:B4,B1:B4>99),"bos")', "bos"), ("=ROWS(FILTER(D1:D4,ISNUMBER(D1:D4)))", 2.0),
    # UNIQUE
    ("=ROWS(UNIQUE(A1:A4))", 3.0), ("=ROWS(UNIQUE(A1:A4,FALSE,TRUE))", 2.0), ("=INDEX(UNIQUE(A1:A4,FALSE,TRUE),1)", "c"),
    ("=COLUMNS(UNIQUE(A1:B1,TRUE))", 2.0), ("=ROWS(UNIQUE(D1:D4))", 4.0),
    # SEQUENCE
    ("=SUM(SEQUENCE(4))", 10.0), ("=INDEX(SEQUENCE(2,3,10,5),2,3)", 35.0), ("=SUM(SEQUENCE(3,1,5,-2))", 9.0),
    ("=COLUMNS(SEQUENCE(1,4))", 4.0),
    # TAKE / DROP
    ("=SUM(TAKE(B1:B4,2))", 4.0), ("=SUM(TAKE(B1:B4,-2))", 7.0), ("=SUM(TAKE(A1:B4,2,-1))", 4.0),
    ("=SUM(DROP(B1:B4,1))", 8.0), ("=SUM(DROP(B1:B4,-1))", 6.0), ("=COLUMNS(DROP(A1:B4,0,1))", 1.0),
    # VSTACK / HSTACK
    ("=ROWS(VSTACK(A1:B2,A3:B4))", 4.0), ("=COLUMNS(HSTACK(A1:B2,A3:B4))", 4.0), ("=INDEX(VSTACK(A1:A2,B1:B3),4,1)", 1.0),
    ("=COLUMNS(VSTACK(A1:A2,A1:B2))", 2.0),
    # TOCOL / TOROW
    ("=SUM(TOCOL(B1:B4))", 11.0), ("=ROWS(TOCOL(A1:B4))", 8.0), ("=COLUMNS(TOROW(A1:B4))", 8.0),
    ("=ROWS(TOCOL(D1:D4,1))", 3.0),                                       # boşları yoksay
    # CHOOSECOLS / CHOOSEROWS
    ("=SUM(CHOOSECOLS(A1:B4,2))", 11.0), ("=INDEX(CHOOSEROWS(A1:B4,-1),1,2)", 5.0), ("=COLUMNS(CHOOSECOLS(A1:B4,2,1,2))", 3.0),
    # EXPAND
    ("=ROWS(EXPAND(A1:B2,4))", 4.0), ("=INDEX(EXPAND(A1:B2,3,3,0),3,3)", 0.0), ("=INDEX(EXPAND(A1:B2,3,3,\"-\"),3,3)", "-"),
    # TRANSPOSE
    ("=INDEX(TRANSPOSE(A1:B2),2,1)", 3.0), ("=COLUMNS(TRANSPOSE(A1:A4))", 4.0),
    # LET
    ("=LET(x,2,x*3)", 6.0), ("=LET(x,A1:B4,y,SUM(INDEX(x,0,2)),y*2)", 22.0), ("=LET(a,5,b,a+1,a*b)", 30.0),
    ('=LET(x,SUM(B1:B4),IF(x>5,"büyük","küçük"))', "büyük"), ("=LET(x,2,LET(y,x+1,x*y))", 6.0),
    ("=SUM(LET(v,SEQUENCE(3),v*2))", 12.0),
]


@pytest.mark.parametrize("formul, beklenen", EXCEL)
def test_excel_degerleri(sayfa, formul, beklenen):
    assert h(sayfa, formul) == beklenen


def test_hata_girdisi_yayilir(sayfa):
    # argüman hatası dönüşü etkiler; dizi içindeki hata öğesi olduğu gibi kalır
    assert h(sayfa, "=SORT(1/0)") == Hata("#DIV/0!")
    assert h(sayfa, "=FILTER(A1:A4,1/0)") == Hata("#DIV/0!")
    assert h(sayfa, "=UNIQUE(1/0)") == Hata("#DIV/0!")
    assert h(sayfa, "=INDEX(SORT(F1:F3),3,1)") == Hata("#DIV/0!")        # hata sıralamada sondan bir önce (boş yok)
    assert h(sayfa, "=SUM(FILTER(F1:F3,F1:F3<>1))") == Hata("#DIV/0!")
    assert h(sayfa, "=ROWS(TOCOL(F1:F3,2))") == 2.0                      # hataları yoksay
    assert h(sayfa, "=ROWS(TOCOL(F1:F3))") == 3.0


def test_gecersiz_argumanlar(sayfa):
    assert h(sayfa, "=SORT(A1:B4,3)") == Hata("#VALUE!")                 # sıra indisi sütun sayısını aşar
    assert h(sayfa, "=SORT(A1:B4,1,2)") == Hata("#VALUE!")               # düzen yalnız 1/-1
    assert h(sayfa, "=FILTER(A1:A4,B1:B3>1)") == Hata("#VALUE!")         # boyut uyuşmuyor
    assert h(sayfa, "=SEQUENCE(0)") == Hata("#NUM!")
    assert h(sayfa, "=SEQUENCE(1000000,3)") == Hata("#NUM!")             # üst sınır
    assert h(sayfa, "=CHOOSECOLS(A1:B4,3)") == Hata("#VALUE!")
    assert h(sayfa, "=EXPAND(A1:B2,1)") == Hata("#VALUE!")               # küçültemez
    assert h(sayfa, "=TAKE(A1:B4,0)") == Hata("#CALC!")                  # boş sonuç
    assert h(sayfa, "=INDEX(VSTACK(A1:A2,A1:B2),1,2)") == Hata("#N/A")             # dar dizi #YOK ile tamamlanır


def test_filter_eslesme_yok_hesapla_hatasi(sayfa):
    assert h(sayfa, "=FILTER(B1:B4,B1:B4>99)") == Hata("#CALC!")
    assert h(sayfa, "=UNIQUE(A1:A4,FALSE,TRUE)") != Hata("#CALC!")
    assert h(sayfa, "=INDEX(UNIQUE(A1:A1,FALSE,TRUE),1)") == "c"
    assert h(sayfa, "=UNIQUE(FILTER(A1:A4,A1:A4=\"zz\"))") == Hata("#CALC!")


def test_unique_turkce_buyuk_kucuk_duyarsiz():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, v in enumerate(["Çay", "ÇAY", "çay", "Şeker", "şeker"], 1):
        s.ata(i, 1, Hucre(v))
    Hesaplayici(k)
    s.ata(1, 3, Hucre(formul="=ROWS(UNIQUE(A1:A5))"))
    assert s.deger(1, 3) == 2.0
    s.ata(2, 3, Hucre(formul="=INDEX(SORT(A1:A5),1)"))
    assert s.deger(2, 3) == "Çay"                                         # Türkçe sıra: ç < ş


def test_sort_kararli_ve_coklu_anahtar():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, (a, b) in enumerate([("x", 2.0), ("y", 1.0), ("z", 2.0), ("w", 1.0)], 1):
        s.ata(i, 1, Hucre(a))
        s.ata(i, 2, Hucre(b))
    Hesaplayici(k)
    s.ata(1, 4, Hucre(formul="=INDEX(SORT(A1:B4,2),1,1)"))
    s.ata(2, 4, Hucre(formul="=INDEX(SORT(A1:B4,2),2,1)"))
    s.ata(3, 4, Hucre(formul="=INDEX(SORT(A1:B4,2),3,1)"))
    assert [s.deger(i, 4) for i in (1, 2, 3)] == ["y", "w", "x"]          # eşitlerde özgün sıra korunur


def test_randarray_degisken_ve_sinirlari(sayfa):
    assert h(sayfa, "=SUM(RANDARRAY(3,3,5,5))") == 45.0
    assert h(sayfa, "=ROWS(RANDARRAY(4))") == 4.0
    v = h(sayfa, "=MAX(RANDARRAY(20,1,1,3,TRUE))")
    assert v in (1.0, 2.0, 3.0)
    assert h(sayfa, "=RANDARRAY(1,1,5,1)") == Hata("#NUM!")


def test_let_hatalari(sayfa):
    assert h(sayfa, "=LET(x,1)") == Hata("#VALUE!")                      # çift sayıda argüman
    assert h(sayfa, "=LET(x,1,y,2)") == Hata("#VALUE!")
    assert h(sayfa, "=LET(x,1/0,x+1)") == Hata("#DIV/0!")
    assert h(sayfa, "=LET(x,5,y,x*2,x+y)") == 15.0
    assert h(sayfa, "=LET(x,5,LET(x,6,x)+x)") == 11.0                    # iç ad dışarıdakini gölgeler, dışarıya sızmaz


# ---------------------------------------------------------------- Türkçe adlar (Excel 365'ten doğrulandı)
@pytest.mark.parametrize("en, tr", [
    ("FILTER", "FİLTRE"), ("SORT", "SIRALA"), ("SORTBY", "SIRALAÖLÇÜT"), ("UNIQUE", "BENZERSİZ"), ("SEQUENCE", "SIRALI"),
    ("RANDARRAY", "RASGDİZİ"), ("TAKE", "AL"), ("DROP", "BIRAK"), ("VSTACK", "DÜŞEYYIĞ"), ("HSTACK", "YATAYYIĞ"),
    ("TOCOL", "SÜTUNA"), ("TOROW", "SATIRA"), ("CHOOSECOLS", "SÜTUNSEÇ"), ("CHOOSEROWS", "SATIRSEÇ"),
    ("EXPAND", "GENİŞLET"), ("TRANSPOSE", "DEVRİK_DÖNÜŞÜM"), ("LET", "LET")])
def test_turkce_adlar(en, tr):
    assert adlar.turkcesi(en) == tr and adlar.ingilizcesi(tr) == en


def test_turkce_formul_gidis_donus():
    k = CalismaKitabi()
    kanonik = ceviri.hucre_girdisi('=SIRALA(FİLTRE(A1:B4;B1:B4>1);2;-1)', k).formul
    assert kanonik == "=SORT(FILTER(A1:B4,B1:B4>1),2,-1)"
    assert ceviri.gosterime(kanonik, k) == "=SIRALA(FİLTRE(A1:B4;B1:B4>1);2;-1)"
    assert ceviri.hucre_girdisi("=LET(x;2;x*3)", k).formul == "=LET(x,2,x*3)"
