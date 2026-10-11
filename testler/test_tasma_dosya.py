"""Faz 8e: taşma (dinamik dizi) + dosya biçimleri (.xlsx dizi formülü, LET `_xlpm.`, .ods, .csv), pano/kopya güvenliği, hata
açıklaması ve arayüzden giriş."""
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.formul import hata_neden
from tabcel.formul.motor import Hesaplayici
from tabcel.io import csv_io, ods_io, xlsx_io
from tabcel.io.xlsx_io import _formul_oku, _let_xlpm_yaz
from tabcel.model.deger import TASMA
from tabcel.model.komutlar import GeriAlYigini, HucrelerDegis
from tabcel.model.sayfa import CalismaKitabi, Hucre, TasmaHucre
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


def kur():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, (a, b) in enumerate([("c", 3.0), ("a", 1.0), ("b", 2.0), ("a", 5.0)], 1):
        s.ata(i, 1, Hucre(a))
        s.ata(i, 2, Hucre(b))
    m = Hesaplayici(k)
    s.ata(1, 4, Hucre(formul="=SORT(A1:B4,2,-1)"))
    s.ata(1, 7, Hucre(formul="=LET(x,SUM(B1:B4),y,x*2,y+1)"))
    s.ata(2, 7, Hucre(formul="=SUM(E1:E4)"))
    return k, s, m


# ---------------------------------------------------------------- LET adları
@pytest.mark.parametrize("girdi, beklenen", [
    ("=_xlfn.LET(x,2,x*3)", "=_xlfn.LET(_xlpm.x,2,_xlpm.x*3)"),
    ("=_xlfn.LET(x,A1:A3,y,SUM(x),y*2)", "=_xlfn.LET(_xlpm.x,A1:A3,_xlpm.y,SUM(_xlpm.x),_xlpm.y*2)"),
    ('=_xlfn.LET(x,"x (y)",x&"x")', '=_xlfn.LET(_xlpm.x,"x (y)",_xlpm.x&"x")'),                  # tırnak içine dokunulmaz
    ("=_xlfn.LET(a,5,_xlfn.LET(b,a+1,a*b))", "=_xlfn.LET(_xlpm.a,5,_xlfn.LET(_xlpm.b,_xlpm.a+1,_xlpm.a*_xlpm.b))"),
    ("=SUM(A1:A3)", "=SUM(A1:A3)"),
])
def test_let_xlpm_yaz(girdi, beklenen):
    assert _let_xlpm_yaz(girdi) == beklenen


def test_let_xlpm_okuma_oneki_atar():
    k = CalismaKitabi()
    assert _formul_oku("=_xlfn.LET(_xlpm.x,2,_xlpm.x*3)", k) == "=LET(x,2,x*3)"


# ---------------------------------------------------------------- .xlsx
def test_xlsx_gidis_donus_tasma_ve_let(tmp_path):
    k, s, _ = kur()
    y = str(tmp_path / "t.xlsx")
    rapor = xlsx_io.kaydet(k, y)
    assert any("dinamik dizi formülü" in u for u in rapor.uyarilar) and not rapor.veri_kaybi
    with zipfile.ZipFile(y) as z:
        xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert 't="array"' in xml and 'ref="D1:E4"' in xml and "_xlfn._xlws.SORT" in xml and "_xlpm.x" in xml
    assert xml.count("<f") == 3                                            # 3 formül (SORT, LET, SUM); taşan hücreler yazılmaz
    k2, r2 = xlsx_io.ac(y)
    s2 = k2.sayfalar[0]
    Hesaplayici(k2)
    assert [[s2.deger(i, j) for j in (4, 5)] for i in range(1, 5)] == [["a", 5.0], ["c", 3.0], ["b", 2.0], ["a", 1.0]]
    assert s2.hucre(1, 4).formul == "=SORT(A1:B4,2,-1)" and s2.hucre(1, 7).formul == "=LET(x,SUM(B1:B4),y,x*2,y+1)"
    assert s2.deger(1, 7) == 23.0 and s2.deger(2, 7) == 11.0 and s2.tasma[(1, 4)] == s.tasma[(1, 4)]
    assert type(s2.hucre(2, 5)) is TasmaHucre                              # taşan hücreler dosyadan değil motordan gelir


def test_xlsx_dosyadaki_onbellek_degerleri_tasmayi_engellemez(tmp_path):
    k, s, _ = kur()
    y = str(tmp_path / "t.xlsx")
    xlsx_io.kaydet(k, y)
    import re
    with zipfile.ZipFile(y) as z:
        xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert len(re.findall(r'<c r="E[2-4]"', xml)) == 0                    # taşan hücreler dosyaya yazılmaz
    k2, _ = xlsx_io.ac(y)
    Hesaplayici(k2)
    assert k2.sayfalar[0].deger(1, 4) != TASMA


# ---------------------------------------------------------------- .ods ve .csv
def test_ods_tasan_formul_deger_olarak_yazilir(tmp_path):
    k, s, _ = kur()
    y = str(tmp_path / "t.ods")
    r = ods_io.kaydet(k, y)
    assert any("dinamik dizi" in u for u in r.uyarilar) and r.veri_kaybi
    k2, _ = ods_io.ac(y)
    Hesaplayici(k2)
    s2 = k2.sayfalar[0]
    assert s2.deger(1, 4) == "a" and s2.deger(2, 4) == "c" and s2.deger(2, 5) == 3.0       # değerler yerinde, #TAŞMA! yok
    assert s2.hucre(1, 4).formul is None and s2.hucre(1, 7).formul == "=LET(x,SUM(B1:B4),y,x*2,y+1)"


def test_csv_tasan_degerleri_yazar(tmp_path):
    k, s, _ = kur()
    y = str(tmp_path / "t.csv")
    csv_io.dosya_yaz(s, y)
    satirlar = open(y, encoding="utf-8-sig").read().splitlines()
    assert satirlar == ["c;3;;a;5;;23", "a;1;;c;3;;11", "b;2;;b;2;;", "a;5;;a;1;;"]            # D:E taşan değerler dahil


# ---------------------------------------------------------------- kopya / geri al güvenliği
def test_tasma_hucresi_kopyalaninca_sade_sabit_olur():
    _, s, _ = kur()
    t = s.hucre(2, 4)
    assert type(t) is TasmaHucre
    s.ata(8, 1, t)
    assert type(s.hucre(8, 1)) is Hucre and s.deger(8, 1) == "c"
    s.toplu_yaz({(9, 1): t})
    assert type(s.hucre(9, 1)) is Hucre


def test_geri_al_taşma_hucresini_boş_geri_yukler():
    _, s, _ = kur()
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(s, {(3, 4): Hucre("kullanıcı")}))             # taşan hücrenin üzerine yazıldı
    assert s.deger(1, 4) == TASMA
    y.geri_al()
    assert s.deger(1, 4) == "a" and type(s.hucre(3, 4)) is TasmaHucre and (1, 4) in s.tasma


# ---------------------------------------------------------------- hata açıklaması
def test_hata_aciklamasi_engel_hucresini_soyler():
    k, s, m = kur()
    s.ata(3, 5, Hucre("engel"))
    assert s.deger(1, 4) == TASMA
    metin = hata_neden.metin(hata_neden.acikla(s, 1, 4, motor=m))
    assert "#TAŞMA!" in metin and "E3" in metin and "dolu" in metin
    s.ata(1, 12, Hucre(formul="=FILTER(A1:A4,A1:A4>\"z\")"))
    assert "boş" in hata_neden.metin(hata_neden.acikla(s, 1, 12, motor=m))


# ---------------------------------------------------------------- arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for i, v in enumerate([3.0, 1.0, 2.0], 1):
        s.ata(i, 1, Hucre(v))
    p = Pencere(k)
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()
    DosyaIslemleri._tutulan.clear()


def test_arayuzden_formul_girince_tasar_ve_geri_alinir(pencere):
    g = pencere.izgara()
    assert g.hucre_gir(1, 3, "=SIRALA(A1:A3)")                              # Türkçe adla
    assert [g.sayfa.deger(r, 3) for r in (1, 2, 3)] == [1.0, 2.0, 3.0]
    assert g.sayfa.hucre(1, 3).formul == "=SORT(A1:A3)"
    assert g.hucre_gir(1, 5, "=TOPLA(C1:C3)") and g.sayfa.deger(1, 5) == 6.0
    g.geri_al()                                                              # TOPLA'yı geri al
    g.geri_al()                                                              # SIRALA'yı geri al: taşan hücreler de gider
    assert [g.sayfa.deger(r, 3) for r in (1, 2, 3)] == [None, None, None]
    g.yinele()
    assert [g.sayfa.deger(r, 3) for r in (1, 2, 3)] == [1.0, 2.0, 3.0]


def test_arayuzde_tasan_hucreler_secilir_ve_kullanilan_aralik_genisler(pencere):
    g = pencere.izgara()
    g.hucre_gir(1, 3, "=SIRALI(3;2)")
    assert g.sayfa.kullanilan_aralik() == (1, 1, 3, 4)
    pencere.izgara().sec((2, 4))
    assert g.sayfa.deger(2, 4) == 4.0
