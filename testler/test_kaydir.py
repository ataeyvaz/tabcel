"""Başvuru kaydırma: kopyala, satır/sütun ekle-sil, taşı + komut entegrasyonu (Qt yok)."""
import pytest

from tabcel.formul.kaydir import kopyala, tasi, yapi
from tabcel.formul.motor import Hesaplayici
from tabcel.model import deger as D
from tabcel.model.komutlar import GeriAlYigini, HucreTasi, SatirEkleSil, SutunEkleSil
from tabcel.model.sayfa import CalismaKitabi, Hucre


# --- kopyala ---
@pytest.mark.parametrize("formul,dr,dc,beklenen", [
    ("=A1+B2", 1, 0, "=A2+B3"),
    ("=$A$1+A$1+$A1", 2, 3, "=$A$1+D$1+$A3"),
    ("=SUM(A1:B2)", 0, 1, "=SUM(B1:C2)"),
    ("=SUM(A:A)", 5, 1, "=SUM(B:B)"),           # tam sütun: satır kaymaz
    ("=SUM(2:3)", 1, 9, "=SUM(3:4)"),
    ("=A1", -1, 0, "=#REF!"),                    # sayfa dışı
    ("=[2]!A1 + \"A1\"", 1, 0, "=[2]!A2 + \"A1\""),   # metin sabiti ve boşluk korunur
    ("=SUM($A$1:A1)", 4, 0, "=SUM($A$1:A5)"),   # birikimli toplam deseni
    ("=SUM(A$5:A1)", 9, 0, "=SUM(A$5:A10)"),     # normalize: A1:A$5 → kayınca A$5:A10
])
def test_kopyala(formul, dr, dc, beklenen):
    assert kopyala(formul, dr, dc) == beklenen


def test_kopyala_sinir():
    assert kopyala("=XFD1", 0, 1) == "=#REF!"
    assert kopyala("=A1048576", 1, 0) == "=#REF!"


# --- satır/sütun ---
@pytest.mark.parametrize("formul,eksen,nerede,fark,beklenen", [
    ("=A5", "satir", 3, 2, "=A7"),
    ("=A2", "satir", 3, 2, None),                 # üstte kalan değişmez
    ("=$A$5", "satir", 5, 1, "=$A$6"),           # mutlak da kayar
    ("=SUM(A2:A6)", "satir", 4, 1, "=SUM(A2:A7)"),   # içine ekleme genişletir
    ("=SUM(A2:A6)", "satir", 2, 1, "=SUM(A3:A7)"),   # üst sınıra ekleme taşır
    ("=SUM(A:A)", "satir", 1, 3, None),           # tam sütun satır eklemeden etkilenmez
    ("=A5", "satir", 5, -1, "=#REF!"),            # silinen hücre
    ("=A5", "satir", 2, -2, "=A3"),
    ("=SUM(A2:A6)", "satir", 3, -2, "=SUM(A2:A4)"),  # içten silme daraltır
    ("=SUM(A2:A6)", "satir", 1, -3, "=SUM(A1:A3)"),  # üst uç silinir
    ("=SUM(A2:A6)", "satir", 2, -5, "=SUM(#REF!)"),  # tamamı silindi
    ("=SUM(A2:A6)", "satir", 5, -10, "=SUM(A2:A4)"), # alt uç silinir
    ("=C1", "sutun", 2, 1, "=D1"),
    ("=SUM(1:1)", "sutun", 1, 5, None),
    ("=SUM(B:D)", "sutun", 3, -1, "=SUM(B:C)"),
])
def test_yapi(formul, eksen, nerede, fark, beklenen):
    assert yapi(formul, 1, 1, eksen, nerede, fark) == beklenen


def test_yapi_baska_sayfa():
    # formül 1. sayfada; 2. sayfada satır eklendi
    assert yapi("=A5+[2]!A5", 1, 2, "satir", 1, 1) == "=A5+[2]!A6"
    # formül 2. sayfada, niteliksiz başvuru kendi sayfasına
    assert yapi("=A5", 2, 2, "satir", 1, 1) == "=A6"
    assert yapi("=A5", 3, 2, "satir", 1, 1) is None


# --- taşı ---
def test_tasi_kurallari():
    kutu = (1, 1, 2, 2)                           # A1:B2 → C5'e (dr=4, dc=2)
    assert tasi("=A1+B2", 1, 1, 1, kutu, 1, 4, 2) == "=C5+D6"
    assert tasi("=SUM(A1:B2)", 1, 1, 1, kutu, 1, 4, 2) == "=SUM(C5:D6)"
    assert tasi("=SUM(A1:B3)", 1, 1, 1, kutu, 1, 4, 2) is None     # kısmen içerde: değişmez
    assert tasi("=C5", 1, 1, 1, kutu, 1, 4, 2) == "=#REF!"        # üzerine yazılan hedef
    # başka sayfaya taşıma: dışarıdan işaret eden formül nitelendirilir
    assert tasi("=A1", 1, 1, 1, kutu, 2, 0, 0) == "=[2]!A1"
    # taşınan formül (sayfa 1 → 2), dışarıya işaret eden niteliksiz başvuru eski sayfaya bağlanır
    assert tasi("=Z9", 1, 2, 1, kutu, 2, 0, 0) == "=[1]!Z9"


# --- komutlar + motor ---
@pytest.fixture
def kitap():
    return CalismaKitabi()


def F(m):
    return Hucre(None, m)


def test_satir_ekle_formulleri_duzeltir_geri_alinir(kitap):
    s = kitap.sayfalar[0]
    s2 = kitap.sayfa_ekle("Diger")
    Hesaplayici(kitap)
    s.ata(5, 1, Hucre(7.0))
    s.ata(1, 2, F("=A5*2"))
    s2.ata(1, 1, F(f"=[{s.kimlik}]!A5+1"))
    yigin = GeriAlYigini()
    yigin.calistir(SatirEkleSil(s, 3, 2, ekle=True))
    assert s.hucre(1, 2).formul == "=A7*2"
    assert s2.hucre(1, 1).formul == f"=[{s.kimlik}]!A7+1"
    assert s.deger(1, 2) == 14.0 and s2.deger(1, 1) == 8.0
    yigin.geri_al()
    assert s.hucre(1, 2).formul == "=A5*2"
    assert s2.hucre(1, 1).formul == f"=[{s.kimlik}]!A5+1"
    assert s.deger(1, 2) == 14.0
    yigin.yinele()
    assert s.hucre(1, 2).formul == "=A7*2"


def test_satir_sil_ref_ve_geri_al(kitap):
    s = kitap.sayfalar[0]
    Hesaplayici(kitap)
    s.ata(3, 1, Hucre(4.0))
    s.ata(10, 2, F("=A3+1"))
    yigin = GeriAlYigini()
    yigin.calistir(SatirEkleSil(s, 3, 1, ekle=False))
    assert s.hucre(9, 2).formul == "=#REF!+1"
    assert s.deger(9, 2) == D.BASV
    yigin.geri_al()
    assert s.hucre(10, 2).formul == "=A3+1"
    assert s.deger(10, 2) == 5.0


def test_silinen_satirdaki_formul_geri_gelir(kitap):
    s = kitap.sayfalar[0]
    Hesaplayici(kitap)
    s.ata(1, 1, Hucre(2.0))
    s.ata(2, 1, F("=A1*3"))
    yigin = GeriAlYigini()
    yigin.calistir(SatirEkleSil(s, 2, 1, ekle=False))
    assert s.hucre(2, 1) is None
    yigin.geri_al()
    assert s.hucre(2, 1).formul == "=A1*3" and s.deger(2, 1) == 6.0


def test_sutun_sil(kitap):
    s = kitap.sayfalar[0]
    Hesaplayici(kitap)
    s.ata(1, 4, Hucre(1.0))
    s.ata(2, 1, F("=SUM(B1:D1)"))
    GeriAlYigini().calistir(SutunEkleSil(s, 2, 1, ekle=False))
    assert s.hucre(2, 1).formul == "=SUM(B1:C1)"
    assert s.deger(2, 1) == 1.0


def test_hucre_tasi(kitap):
    s = kitap.sayfalar[0]
    Hesaplayici(kitap)
    s.ata(1, 1, Hucre(5.0))                  # A1
    s.ata(1, 2, F("=A1*2"))                  # B1 (taşınacak bölgede)
    s.ata(1, 4, F("=A1+B1"))                 # D1 (dışarıda, taşınana işaret ediyor)
    s.ata(1, 5, F("=SUM(A1:C1)"))            # kısmen içerde: değişmez
    yigin = GeriAlYigini()
    yigin.calistir(HucreTasi(s, (1, 1, 1, 2), s, (3, 1)))   # A1:B1 → A3
    assert s.hucre(1, 1) is None and s.hucre(1, 2) is None
    assert s.hucre(3, 1).deger == 5.0
    assert s.hucre(3, 2).formul == "=A3*2"   # bölge içine işaret ettiği için kaydı
    assert s.hucre(1, 4).formul == "=A3+B3"
    assert s.hucre(1, 5).formul == "=SUM(A1:C1)"
    assert s.deger(1, 4) == 15.0
    yigin.geri_al()
    assert s.hucre(1, 2).formul == "=A1*2" and s.hucre(1, 4).formul == "=A1+B1"
    assert s.hucre(3, 1) is None
    assert s.deger(1, 4) == 15.0


def test_hucre_tasi_baska_sayfaya(kitap):
    s = kitap.sayfalar[0]
    s2 = kitap.sayfa_ekle("Hedef")
    Hesaplayici(kitap)
    s.ata(9, 9, Hucre(1.0))
    s.ata(1, 1, F("=I9+1"))                   # taşınacak; dışarıya (I9) işaret ediyor
    s.ata(2, 2, F("=A1*10"))                  # taşınana işaret ediyor
    GeriAlYigini().calistir(HucreTasi(s, (1, 1, 1, 1), s2, (1, 1)))
    assert s2.hucre(1, 1).formul == f"=[{s.kimlik}]!I9+1"
    assert s.hucre(2, 2).formul == f"=[{s2.kimlik}]!A1*10"
    assert s.deger(2, 2) == 20.0
