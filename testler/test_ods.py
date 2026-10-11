"""Faz 8c: OpenDocument Hesap Tablosu (.ods) aç/kaydet. Örnek dosya gerçek Excel'de üretildi (araclar/xls_ornek_uret.ps1);
yazılan dosyanın Excel'de açılması gerçek Excel'le (COM) denendi (surec.md)."""
import os
import shutil
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.formul.motor import Hesaplayici
from tabcel.io import ods_io, xlsx_io
from tabcel.io.xlsx_io import XlsxHatasi
from tabcel.model.adres import Aralik
from tabcel.model.deger import Hata
from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Kenarlik, Stil
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere

ORNEKLER = os.path.join(os.path.dirname(__file__), "ornekler")
ORNEK = os.path.join(ORNEKLER, "ornek.ods")


# ---------------------------------------------------------------- formül çevirisi
@pytest.mark.parametrize("odf, excel", [
    ("of:=SUM([.A1:.A3])", "=SUM(A1:A3)"),
    ("of:=[.B2]*[.C2]", "=B2*C2"),
    ('of:=IF([.B2]>1;"a;b";"c")', '=IF(B2>1,"a;b","c")'),
    ("of:=SUM([$Sayfa1.A1:.B2])", "=SUM(Sayfa1!A1:B2)"),
    ("of:=[$'Ay lık'.$A$1]+1", "='Ay lık'!$A$1+1"),
    ("of:=1/0", "=1/0"),
])
def test_formul_oku(odf, excel):
    assert ods_io.formul_oku(odf) == excel


@pytest.mark.parametrize("excel, odf", [
    ("=SUM(A1:A3)", "of:=SUM([.A1:.A3])"),
    ("=B2*C2", "of:=[.B2]*[.C2]"),
    ('=IF(B2>1,"a,b","c")', 'of:=IF([.B2]>1;"a,b";"c")'),
    ("=SUM(Sayfa1!A1:B2)", "of:=SUM([$Sayfa1.A1:.B2])"),
    ("=LOG10(100)+A1", "of:=LOG10(100)+[.A1]"),                    # LOG10 hücre başvurusu sanılmaz
    ("=$A$1+Z99", "of:=[.$A$1]+[.Z99]"),
    ("=İkinci!A1+1", "of:=[$İkinci.A1]+1"),                          # ASCII olmayan sayfa adı, tırnaksız
    ("='İkinci'!A1", "of:=[$İkinci.A1]"),                            # gereksiz tırnak atılır (Excel bozuyordu)
    ("='Ay lık'!A1", "of:=[$'Ay lık'.A1]"),                         # boşluklu ad tırnaklı kalır
])
def test_formul_yaz(excel, odf):
    assert ods_io.formul_yaz(excel) == odf


# ---------------------------------------------------------------- Excel'in ürettiği dosyayı okuma
@pytest.fixture(scope="module")
def ornek():
    return ods_io.ac(ORNEK)


def test_excel_dosyasi_degerler_formuller(ornek):
    k, r = ornek
    assert [s.ad for s in k.sayfalar] == ["Satış", "İkinci"]
    s = k.sayfalar[0]
    assert [s.deger(1, c) for c in range(1, 5)] == ["Ürün", "Adet", "Fiyat", "Tarih"]
    assert [s.deger(2, c) for c in range(1, 4)] == ["Çay", 3.0, 12.5] and s.deger(3, 1) == "Şeker"
    assert s.deger(2, 4) == 46307.0 and s.deger(4, 1) is True
    assert s.hucre(4, 3).formul == "=B2*C2" and s.hucre(5, 3).formul.startswith("=SUM(B2:B3)")
    assert s.hucre(5, 4).formul == '=IF(B2>1,"çok","az")'
    assert s.hucre(4, 2).formul == "=1/0"


def test_excel_dosyasi_bicimler(ornek):
    k, _ = ornek
    s = k.sayfalar[0]
    b = s.stil(1, 1)
    assert b.kalin and b.dolgu == "#4FAF50" and b.kenar.ust is not None and b.sayi_bicimi == "General"
    assert s.stil(2, 3).sayi_bicimi == "0.00" and s.stil(2, 4).sayi_bicimi == "dd.mm.yyyy"
    a = s.birlesim(6, 1)
    assert (a.ilk_satir, a.ilk_sutun, a.son_satir, a.son_sutun) == (6, 1, 6, 3) and s.stil(6, 1).yatay == "orta"
    assert s.sutun_genislik[1] > 100
    s2 = k.sayfalar[1]
    assert s2.stil(1, 1).italik and s2.stil(1, 1).yazi_rengi == "#FF0000" and s2.stil(2, 1).sayi_bicimi == "0%"


# ---------------------------------------------------------------- yaz → oku gidiş-dönüş
def _kitap():
    k = CalismaKitabi()
    m = Hesaplayici(k)
    s = k.sayfalar[0]
    k.yeniden_adlandir(s, "Veri & Ay")
    s2 = k.sayfa_ekle("İkinci")
    s.ata(1, 1, Hucre('Ad <"x">'))
    s.ata(1, 2, Hucre(12.5))
    s.ata(1, 3, Hucre(True))
    s.ata(1, 4, Hucre(Hata("#N/A")))
    s.ata(2, 1, Hucre("satır1\nsatır2\t  boşluk"))
    s.ata(2, 2, Hucre(formul="=B1*2"))
    s.ata(2, 3, Hucre(formul="=SUM(B1:B2)+'İkinci'!A1"))
    s.ata(2, 4, Hucre(formul='=IF(B1>1,"a;b","c")'))
    s2.ata(1, 1, Hucre(5.0))
    s.ata(20, 5, Hucre("uzak hücre"))
    s.birlesim_yukle([Aralik(4, 1, 5, 3)])
    s.sutun_genislik[2] = 150
    s.gizli_sutun.add(3)
    s.satir_yukseklik[3] = 40
    s.gizli_satir.add(6)
    st = Stil(kalin=True, italik=True, ustu_cizili=True, alti_cizili="tek", yazi_rengi="#FF0000", dolgu="#FFFF00",
              kenar=Kenarlik(ust=("ince", "#000000"), alt=("orta", "#0000FF")), yatay="sag", dikey="orta",
              girinti=2, kaydir=True, sayi_bicimi="#,##0.00", yazi_tipi="Arial", boyut=14.0)
    s.bicim_yaz({(1, 2): k.stil_havuzu.kimlik(st)}, {}, {})
    m.tumunu_hesapla()
    return k


def test_gidis_donus(tmp_path):
    k = _kitap()
    y = str(tmp_path / "a.ods")
    r = ods_io.kaydet(k, y)
    assert not r.uyarilar
    z = zipfile.ZipFile(y)
    assert z.namelist()[0] == "mimetype" and z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
    assert z.read("mimetype") == b"application/vnd.oasis.opendocument.spreadsheet"
    k2, r2 = ods_io.ac(y)
    assert [s.ad for s in k2.sayfalar] == ["Veri & Ay", "İkinci"]
    s = k2.sayfalar[0]
    assert s.deger(1, 1) == 'Ad <"x">' and s.deger(1, 2) == 12.5 and s.deger(1, 3) is True
    assert s.deger(2, 1) == "satır1\nsatır2\t  boşluk"
    assert getattr(s.deger(1, 4), "kod", s.deger(1, 4)) == "#N/A"
    assert s.hucre(2, 2).formul == "=B1*2" and "SUM(B1:B2)" in s.hucre(2, 3).formul
    assert s.hucre(2, 4).formul == '=IF(B1>1,"a;b","c")'
    assert s.deger(20, 5) == "uzak hücre"
    assert s.birlesim(4, 1) == Aralik(4, 1, 5, 3)
    assert s.sutun_genislik[2] == 150 and 3 in s.gizli_sutun
    assert s.satir_yukseklik[3] == 40 and 6 in s.gizli_satir
    st = s.stil(1, 2)
    assert (st.kalin, st.italik, st.ustu_cizili, st.alti_cizili, st.yazi_rengi, st.dolgu) == \
        (True, True, True, "tek", "#FF0000", "#FFFF00")
    assert (st.yatay, st.dikey, st.girinti, st.kaydir, st.sayi_bicimi) == ("sag", "orta", 2, True, "#,##0.00")
    assert st.yazi_tipi == "Arial" and st.boyut == 14.0
    assert st.kenar.ust is not None and st.kenar.alt[1] == "#0000FF"
    assert k2.sayfalar[1].deger(1, 1) == 5.0


@pytest.mark.parametrize("kod", ["0", "0.00", "#,##0", "#,##0.00", "0%", "0.00%", '"₺"#,##0.00', "dd.mm.yyyy", "yyyy-mm-dd",
                                 "hh:mm:ss", "dd.mm.yyyy hh:mm", "d mmmm yyyy", "@", "dddd"])
def test_sayi_bicimleri_gidis_donus(tmp_path, kod):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(46307.5))
    s.bicim_yaz({(1, 1): k.stil_havuzu.kimlik(Stil(sayi_bicimi=kod))}, {}, {})
    y = str(tmp_path / "b.ods")
    assert not ods_io.kaydet(k, y).uyarilar
    assert ods_io.ac(y)[0].sayfalar[0].stil(1, 1).sayi_bicimi == kod


def test_desteklenmeyen_sayi_bicimi_uyarir(tmp_path):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(1.0))
    s.bicim_yaz({(1, 1): k.stil_havuzu.kimlik(Stil(sayi_bicimi="[Red]0.0;(0.0)"))}, {}, {})
    r = ods_io.kaydet(k, str(tmp_path / "c.ods"))
    assert any("sayı biçimi" in u for u in r.uyarilar)


def test_yazilamayanlar_uyarilir(tmp_path):
    k = _kitap()
    k.sayfalar[0].notlari_yaz({(1, 1): Not("n", "y")})
    r = ods_io.kaydet(k, str(tmp_path / "d.ods"))
    assert r.veri_kaybi and any("notlar" in u for u in r.uyarilar)


def test_bos_ve_buyuk_seyrek_sayfa(tmp_path):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(500, 30, Hucre("ucta"))
    s.ata(1, 1, Hucre(1.0))
    y = str(tmp_path / "e.ods")
    ods_io.kaydet(k, y)
    assert os.path.getsize(y) < 5000                                  # boş satır/sütunlar tekrarla sıkıştırıldı
    s2 = ods_io.ac(y)[0].sayfalar[0]
    assert s2.deger(500, 30) == "ucta" and s2.deger(1, 1) == 1.0 and s2.deger(250, 5) is None


def test_bozuk_dosyalar(tmp_path):
    kotu = tmp_path / "bozuk.ods"
    kotu.write_bytes(b"zip degil")
    with pytest.raises(XlsxHatasi, match="geçerli bir .ods değil"):
        ods_io.ac(str(kotu))
    xlsx = tmp_path / "x.ods"
    shutil.copy(os.path.join(ORNEKLER, "butce.xlsx"), xlsx)
    with pytest.raises(XlsxHatasi, match="content.xml yok"):
        ods_io.ac(str(xlsx))
    odt = tmp_path / "belge.ods"
    with zipfile.ZipFile(odt, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        z.writestr("content.xml", "<a/>")
    with pytest.raises(XlsxHatasi, match="hesap tablosu değil"):
        ods_io.ac(str(odt))
    with pytest.raises(XlsxHatasi):
        ods_io.ac(str(tmp_path / "yok.ods"))


def test_xlsx_ods_ayni_veri(tmp_path):
    """.xlsx → .ods → okunan kitap, özgün .xlsx kitabıyla hücre değerlerinde aynı."""
    k, _ = xlsx_io.ac(os.path.join(ORNEKLER, "butce.xlsx"))
    Hesaplayici(k).tumunu_hesapla()
    y = str(tmp_path / "f.ods")
    ods_io.kaydet(k, y)
    k2, _ = ods_io.ac(y)
    Hesaplayici(k2).tumunu_hesapla()
    for a, b in zip(k.sayfalar, k2.sayfalar):
        assert a.ad == b.ad
        for (r, c), h in a._hucreler.items():
            assert a.deger(r, c) == b.deger(r, c), (a.ad, r, c)


# ---------------------------------------------------------------- arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _temiz(app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)
    yield
    for p in list(DosyaIslemleri._tutulan):
        p.degisti_mi = lambda: False
        p.close()
    DosyaIslemleri._tutulan.clear()


def test_pencerede_ac_degistir_kaydet(tmp_path, monkeypatch):
    monkeypatch.setattr(DosyaIslemleri, "_veri_kaybi_sorusu", lambda self: "kaydet")   # örnekte not var: okunmaz → soru çıkar
    hedef = str(tmp_path / "k.ods")
    shutil.copy(ORNEK, hedef)
    p = Pencere(CalismaKitabi())
    p.show()
    q = p.dosya_ac(hedef)
    assert q.izgara().sayfa.deger(2, 1) == "Çay" and q.yol == os.path.abspath(hedef)
    q.izgara().hucre_gir(8, 1, "yeni")
    assert q.kaydet() and not q.degisti_mi()
    k2, _ = ods_io.ac(hedef)
    assert k2.sayfalar[0].deger(8, 1) == "yeni"


def test_farkli_kaydet_ods_uzantisi(tmp_path, monkeypatch):
    p = Pencere(CalismaKitabi())
    p.show()
    p.izgara().hucre_gir(1, 1, "7")
    ad = str(tmp_path / "yeni")                                         # uzantısız + ODS filtresi
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (ad, "OpenDocument Hesap Tablosu (*.ods)"))
    assert p.farkli_kaydet() and os.path.exists(ad + ".ods")


def test_parolali_belge_ods_kaydinda_sorar(tmp_path, monkeypatch):
    p = Pencere(CalismaKitabi())
    p.show()
    p.parola = "x"
    iletiler = []
    monkeypatch.setattr(QMessageBox, "warning", lambda w, b, m, *a: iletiler.append(m) or QMessageBox.Cancel)
    assert not p._kaydet_yola(str(tmp_path / "p.ods")) and iletiler and p.parola == "x"
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Yes)
    assert p._kaydet_yola(str(tmp_path / "p.ods")) and p.parola is None
