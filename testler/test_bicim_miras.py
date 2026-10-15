"""Formül girilince Excel'in kendiliğinden verdiği sayı biçimi (`formul/bicim_miras.py`). Beklenenler gerçek Excel 16'da
(COM, 2026-10-15) ölçülmüştür: araclar dışı elle sınama — bkz. surec.md günlüğü."""
import pytest

from tabcel.formul.bicim_miras import (KISA_TARIH, PARA, SAAT_AMPM, TARIH_SAAT, YUZDE, onerilen_bicim)
from tabcel.model.adres import Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import StilYama
from tabcel.model.komutlar import bicim_komutu

TARIH, PARAKOD, SAAT = "dd.mm.yyyy", '"₺"#,##0.00', "hh:mm:ss"


@pytest.fixture
def kitap():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r, c, v, kod in [(1, 1, 45000.5, TARIH), (2, 1, 45001.0, TARIH), (1, 2, 3.0, None),
                         (1, 3, 5.5, PARAKOD), (2, 3, 7.25, PARAKOD), (1, 4, 0.25, SAAT), (2, 4, 0.5, SAAT),
                         (1, 5, 0.1, "0.00%")]:
        s.ata(r, c, Hucre(v))
        if kod:
            bicim_komutu(s, [Aralik(r, c, r, c)], StilYama(sayi_bicimi=kod)).yap()
    return k


def oner(kitap, formul):
    return onerilen_bicim(formul, kitap.sayfalar[0], kitap)


@pytest.mark.parametrize("formul,beklenen", [
    ("=TODAY()", KISA_TARIH), ("=NOW()", TARIH_SAAT), ("=DATE(2026,1,1)", KISA_TARIH), ("=TIME(1,2,3)", SAAT_AMPM),
    ("=PMT(0.01,12,-1000)", PARA), ("=FV(0.01,12,-100)", PARA), ("=PV(0.01,12,-100)", PARA), ("=NPV(0.1,100,200)", PARA),
    ("=SLN(1000,100,5)", PARA), ("=IPMT(0.01,1,12,-1000)", PARA), ("=IRR(B1:B2)", YUZDE), ("=RATE(12,-100,1000)", YUZDE),
    # biçim vermeyenler (Excel'de Genel kalır)
    ("=EDATE(45000,1)", None), ("=EOMONTH(45000,1)", None), ("=WORKDAY(45000,1)", None), ("=DATEVALUE(\"1.1.2026\")", None),
    ("=TIMEVALUE(\"12:30\")", None), ("=YEAR(45000)", None), ("=NPER(0.01,-100,1000)", None), ("=EFFECT(0.1,4)", None),
    ("=SUM(1,2)", None), ("=PI()", None), ("=ROUND(0.5,0)", None),
    # tarih aritmetiği
    ("=TODAY()+1", KISA_TARIH), ("=TODAY()-DATE(2026,1,1)", None), ("=NOW()-TODAY()", None), ("=EDATE(TODAY(),1)", None),
])
def test_islev_kaynakli(kitap, formul, beklenen):
    assert oner(kitap, formul) == beklenen


@pytest.mark.parametrize("formul,beklenen", [
    ("=A1", TARIH), ("=(A1)", TARIH), ("=-A1", TARIH), ("=+A1", TARIH), ("=A1+1", TARIH), ("=1+A1", TARIH), ("=B1+A1", TARIH),
    ("=A1+B1", TARIH), ("=A1-B1", TARIH), ("=A1-A2", None), ("=A1+A2", None),                  # tarih ± tarih → Genel
    ("=C1+C2", PARAKOD), ("=C2-C1", PARAKOD), ("=C1+B1", PARAKOD), ("=B1+C1", PARAKOD), ("=-C1", PARAKOD),
    ("=D1+D2", SAAT), ("=D2-D1", SAAT), ("=E1+E1", "0.00%"),                                    # saat/yüzde miras
    ("=SUM(C1:C2)", PARAKOD), ("=SUM(B1,C1)", PARAKOD), ("=SUM(B1:B2,C1:C2)", PARAKOD), ("=SUM(A1:A2)", TARIH),
    ("=SUM(D1:D2)", "[h]:mm:ss"), ("=AVERAGE(C1:C2)", PARAKOD), ("=AVERAGE(C1,C2)", PARAKOD), ("=MAX(C1:C2)", PARAKOD),
    ("=MIN(C1:C2)", PARAKOD), ("=MEDIAN(C1:C2)", PARAKOD), ("=ROUND(C1,0)", PARAKOD), ("=ROUNDUP(C1,0)", PARAKOD),
    ("=ROUNDDOWN(C1,0)", PARAKOD), ("=TRUNC(C1)", PARAKOD), ("=INT(C1)", PARAKOD), ("=MOD(C1,2)", PARAKOD),
    ("=C1+SUM(B1)", PARAKOD), ("=SUM(C1:C2)+B1", PARAKOD),
])
def test_miras(kitap, formul, beklenen):
    assert oner(kitap, formul) == beklenen


@pytest.mark.parametrize("formul", [
    "=C1*B1", "=B1*C1", "=C1/B1", "=C1*2", "=C1^2", "=C1%", "=C1&B1", "=C1>1", "=A1*2",                  # işleç → Genel
    "=C1+B1*2", "=B1*2+C1", "=SUM(C1)/2", "=SUM(C1:C2)/COUNT(C1:C2)",                                   # * / içeren ifade
    "=ABS(C1)", "=IF(B1>1,C1,C2)", "=COUNT(C1:C2)", "=SUMIF(C1:C2,\">1\")", "=SUBTOTAL(9,C1:C2)", "=PRODUCT(C1:C2)",
    "=IFERROR(C1,0)", "=VLOOKUP(5.5,C1:C2,1,FALSE)", "=INDEX(C1:C2,2)", "=SUMPRODUCT(C1:C2,C1:C2)", "=LARGE(C1:C2,1)",
    "=SMALL(C1:C2,1)", "=CEILING(C1,1)", "=SQRT(C1)", "=N(C1)", "=TEXT(C1,\"0\")", "=XLOOKUP(5.5,C1:C2,C1:C2)",
    "=ROUND(C1/3,2)", "=CHOOSE(1,C1,C2)",
])
def test_miras_yok(kitap, formul):
    assert oner(kitap, formul) is None


def test_bozuk_ya_da_bos_formul_oneri_vermez(kitap):
    assert oner(kitap, "=A1+") is None and oner(kitap, "=#REF!") is None and oner(kitap, "=BILINMEYEN(1)") is None


def test_baska_sayfa_basvurusu(kitap):
    k = kitap
    s2 = k.sayfa_ekle("Sayfa2") if hasattr(k, "sayfa_ekle") else None
    if s2 is None:
        pytest.skip("sayfa ekleme API'si bulunamadı")
    s2.ata(1, 1, Hucre(2.0))
    bicim_komutu(s2, [Aralik(1, 1, 1, 1)], StilYama(sayi_bicimi=PARAKOD)).yap()
    assert onerilen_bicim(f"=[{s2.kimlik}]!A1+1", k.sayfalar[0], k) == PARAKOD


# ------------------------------------------------------------------ arayüz: formül yazınca biçim kendiliğinden gelir
def test_izgarada_formul_yazinca_bicim_gelir_ve_geri_alinir():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from tabcel.ui.window import Pencere
    app = QApplication.instance() or QApplication([])
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(45000.0))
    bicim_komutu(s, [Aralik(1, 1, 1, 1)], StilYama(sayi_bicimi=TARIH)).yap()
    p = Pencere(k)
    g = p.izgara()
    assert g.hucre_gir(2, 1, "=A1+1")                     # tarih mirası
    assert s.stil(2, 1).sayi_bicimi == TARIH
    assert g.hucre_gir(3, 1, "=BUGÜN()") and s.stil(3, 1).sayi_bicimi == KISA_TARIH
    assert g.hucre_gir(4, 1, "=DEVRESEL_ÖDEME(0,01;12;-1000)") and s.stil(4, 1).sayi_bicimi == PARA
    assert g.hucre_gir(5, 1, "=A1*2") and s.stil(5, 1).sayi_bicimi == "General"        # çarpma: biçim yok
    # Genel olmayan hücreye dokunulmaz
    bicim_komutu(s, [Aralik(6, 1, 6, 1)], StilYama(sayi_bicimi="0.0")).yap()
    assert g.hucre_gir(6, 1, "=BUGÜN()") and s.stil(6, 1).sayi_bicimi == "0.0"
    g.yigin.geri_al()                                     # tek adım: biçim + formül birlikte
    assert s.stil(6, 1).sayi_bicimi == "0.0" and s.hucre(6, 1) is None
    g.yigin.geri_al()                                     # =A1*2 girişi
    g.yigin.geri_al()                                     # =PMT girişi: biçim de geri gelir
    assert s.stil(4, 1).sayi_bicimi == "General" and s.hucre(4, 1) is None
    p.degisti_mi = lambda: False
    p.close()
