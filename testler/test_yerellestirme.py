"""Yerelleştirme katmanı: TR ⇄ saklanan biçim ⇄ EN (plan.md Faz 2, ayrı test dosyası şartı)."""
import pytest

from tabcel.formul.ceviri import disa, girdiden, gosterime, iceri
from tabcel.formul.sozcuk import FormulHatasi
from tabcel.model.sayfa import CalismaKitabi


@pytest.fixture
def kitap():
    k = CalismaKitabi()
    k.sayfa_ekle("Gelir Gider")       # kimlik 2
    k.sayfa_ekle("Şubat")             # kimlik 3
    return k


@pytest.mark.parametrize("tr,sakli", [
    ("=TOPLA(A1:A3;2,5)", "=SUM(A1:A3,2.5)"),
    ("=topla(a1:a3; 2,5)", "=SUM(A1:A3, 2.5)"),                 # boşluk korunur, büyük harf
    ("=EĞER(A1>0;\"a;b,c\";YANLIŞ)", '=IF(A1>0,"a;b,c",FALSE)'),   # metin içindeki ; , çevrilmez
    ("=eğer(doğru;1;2)", "=IF(TRUE,1,2)"),
    ("=TOPLA(EĞER(A1;1;2);3)", "=SUM(IF(A1,1,2),3)"),            # iç içe
    ("={1\\2;3\\4}", "={1,2;3,4}"),                              # dizi ayırıcıları (doğrulanacak §8b-4)
    ("=#BÖL/0!", "=#DIV/0!"),
    ("=#yok", "=#N/A"),
    ("=$b$2*c3", "=$B$2*C3"),
    ("=B2:A1", "=A1:B2"),                                        # aralık normalize (Excel gibi)
    ("=1,5E3", "=1.5E3"),
    ("=SUM(1;2)", "=SUM(1,2)"),                                  # İngilizce ad da kabul
    ("=if(1;2;3)", "=IF(1,2,3)"),                                # İngilizce küçük harf (i/İ tuzağı)
])
def test_tr_den_sakliya(kitap, tr, sakli):
    assert girdiden(tr, kitap) == sakli


@pytest.mark.parametrize("tr", [
    "=TOPLA(A1:A3;2,5)", "=EĞER(A1>0;\"a;b,c\";YANLIŞ)", "={1\\2;3\\4}", "=#BÖL/0!+#YOK",
    "=TOPLA( A1 ; B2 )", "='Gelir Gider'!A1:B2*2", "=Şubat!$C$5", "=-2^2%", "=A:A", "=2:3",
])
def test_gidis_donus(kitap, tr):
    assert gosterime(girdiden(tr, kitap), kitap) == tr


def test_sayfa_kimlikle_saklanir(kitap):
    s = girdiden("='Gelir Gider'!A1+şubat!B2", kitap)
    assert s == "=[2]!A1+[3]!B2"
    assert gosterime(s, kitap) == "='Gelir Gider'!A1+Şubat!B2"


def test_yeniden_adlandirma_formulu_degistirmez(kitap):
    s = girdiden("='Gelir Gider'!A1", kitap)
    kitap.yeniden_adlandir(kitap.sayfalar[1], "Bütçe 2026")
    assert gosterime(s, kitap) == "='Bütçe 2026'!A1"


def test_silinen_sayfa_basv(kitap):
    s = girdiden("=1+Şubat!A1", kitap)
    sayfa = kitap.sayfalar[2]
    i = kitap.sayfa_sil(sayfa)
    assert gosterime(s, kitap) == "=1+#BAŞV!"
    kitap.sayfa_geri_koy(sayfa, i)
    assert gosterime(s, kitap) == "=1+Şubat!A1"


def test_olmayan_sayfa_reddedilir(kitap):
    with pytest.raises(FormulHatasi, match="sayfa bulunamadı"):
        girdiden("=Mart!A1", kitap)


@pytest.mark.parametrize("hatali", ["=TOPLA(", "=1+", "=EĞER(1)", "=\"abc", "=1;2", "=TOPLA()"])
def test_hatali_girdi(kitap, hatali):
    with pytest.raises(FormulHatasi):
        girdiden(hatali, kitap)


def test_bilinmeyen_fonksiyon_kalir(kitap):
    # Excel bilinmeyen adı kabul eder, sonuç #AD? olur
    assert girdiden("=fonksiyonum(1)", kitap) == "=FONKSİYONUM(1)"


def test_ingilizce_disa_ve_iceri(kitap):
    s = girdiden("=TOPLA('Gelir Gider'!A1;2,5;DOĞRU)", kitap)
    assert disa(s, kitap) == "=SUM('Gelir Gider'!A1,2.5,TRUE)"
    assert iceri("=SUM('Gelir Gider'!A1,2.5,TRUE)", kitap) == s
    assert iceri("=_xlfn.SUM(1)", kitap) == "=SUM(1)"


def test_turkcesi_olmayan_fonksiyon_ingilizce_gorunur(kitap):
    assert gosterime("=ROUND(1.25,1)", kitap) == "=ROUND(1,25;1)"
