"""Faz 9c: Tablo Sağlığı paneli (ui/saglik_paneli.py): donmadan tarama, iptal, gruplu rapor, tıkla→git, Düzelt (geri alınır), Yoksay (kalıcı)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.formul import saglik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def kirli_kitap():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(2, 10):
        s.ata(r, 1, Hucre(float(r)))
    s.ata(11, 1, Hucre(formul="=SUM(A2:A9)"))
    s.ata(12, 1, Hucre(formul="=1/0"))                       # hata değeri (kritik)
    s.ata(2, 3, Hucre("123"))                                # tek başına metin-sayı: sütun karışık değil → bulgu yok
    for r in range(3, 8):
        s.ata(r, 3, Hucre(float(r)))
    return k, s


@pytest.fixture
def pencere(app, tmp_path, monkeypatch):
    monkeypatch.setattr(saglik, "ayarlari_oku", lambda: saglik.Ayarlar())
    k, _ = kirli_kitap()
    p = Pencere(k)
    p.resize(1200, 700)
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()
    DosyaIslemleri._tutulan.clear()


def tara_bitir(p):
    p.saglik.tara()
    for _ in range(2000):
        if p.saglik._uretec is None:
            break
        QTest.qWait(5)
    assert p.saglik._uretec is None


def tum_bulgular(p):
    return list(p.saglik._bulgular)


def test_panel_tarar_ve_gruplar(pencere):
    tara_bitir(pencere)
    b = tum_bulgular(pencere)
    assert any(x.kontrol == "hata" for x in b)
    ust = [pencere.saglik.agac.topLevelItem(i).text(0) for i in range(pencere.saglik.agac.topLevelItemCount())]
    assert ust and ust[0].startswith("Kritik (")
    assert pencere.saglik.tara_dugmesi.isEnabled() and not pencere.saglik.iptal_dugmesi.isEnabled()
    assert "Kritik" in pencere.saglik.ozet.text()


def test_eylem_paneli_acar_ve_tarar(pencere):
    pencere.eylemler["saglik"].trigger()
    assert pencere.saglik.isVisible()
    for _ in range(2000):
        if pencere.saglik._uretec is None:
            break
        QTest.qWait(5)
    assert tum_bulgular(pencere)


def test_iptal_taramayi_durdurur(pencere):
    pencere.saglik.tara()
    pencere.saglik.iptal()
    assert pencere.saglik._uretec is None and pencere.saglik.tara_dugmesi.isEnabled()
    assert "iptal" in pencere.saglik.ozet.text()


def test_bulguya_tiklayinca_hucreye_gider(pencere):
    tara_bitir(pencere)
    gidilen = []
    pencere.saglik.hucreyeGit.connect(lambda s, r, c: gidilen.append((r, c)))
    kok = pencere.saglik.agac.topLevelItem(0)
    kok.child(0).setSelected(True)
    pencere.saglik._git(kok.child(0))
    assert gidilen == [(12, 1)]


def test_secince_aciklama_gorunur_ve_duzeltme_dugmesi(pencere):
    tara_bitir(pencere)
    ag = pencere.saglik.agac
    ag.setCurrentItem(ag.topLevelItem(0).child(0))
    assert "Neden sorun olabilir" in pencere.saglik.ayrinti.text()
    assert pencere.saglik.yoksay_dugmesi.isEnabled()
    assert not pencere.saglik.duzelt_dugmesi.isEnabled()          # hata değerinin otomatik düzeltmesi yok
    assert pencere.kitap.sayfalar[0].hucre(12, 1).formul == "=1/0"  # denetçi hiçbir şeyi değiştirmedi


def test_duzelt_onayla_degistirir_ve_geri_alinir(pencere):
    s = pencere.kitap.sayfalar[0]
    for r in range(2, 10):
        s.ata(r, 5, Hucre(float(r)))
    s.ata(14, 5, Hucre(formul="=SUM(E2:E8)"))                    # E9 kapsam dışı
    tara_bitir(pencere)
    eksik = [b for b in tum_bulgular(pencere) if b.kontrol == "eksik_aralik"]
    assert eksik
    ag = pencere.saglik.agac
    for i in range(ag.topLevelItemCount()):
        g = ag.topLevelItem(i)
        for j in range(g.childCount()):
            if pencere.saglik._bulgu(g.child(j)) is eksik[0]:
                ag.setCurrentItem(g.child(j))
    assert pencere.saglik.duzelt_dugmesi.isEnabled()
    oncesi = s.hucre(14, 5).formul
    pencere.saglik.duzelt()
    assert s.hucre(14, 5).formul != oncesi
    pencere.yigin.geri_al()
    assert s.hucre(14, 5).formul == oncesi


def test_yoksay_kalici_ve_geri_alinir(pencere):
    tara_bitir(pencere)
    ag = pencere.saglik.agac
    ag.setCurrentItem(ag.topLevelItem(0).child(0))
    b = pencere.saglik._bulgu(ag.currentItem())
    pencere.saglik.yoksay()
    assert b.anahtar in pencere.kitap.saglik_yoksay
    tara_bitir(pencere)
    assert all(x.anahtar != b.anahtar for x in tum_bulgular(pencere))
    assert "yoksayılan" in pencere.saglik.ozet.text()
    pencere.saglik.yoksayilanlari_geri_al()
    for _ in range(2000):
        if pencere.saglik._uretec is None:
            break
        QTest.qWait(5)
    assert any(x.anahtar == b.anahtar for x in tum_bulgular(pencere))


def test_kitap_degisince_eski_sonuc_etiketi(pencere):
    tara_bitir(pencere)
    assert not pencere.saglik.eski_etiketi.isVisibleTo(pencere.saglik)
    pencere.kitap.sayfalar[0].ata(30, 1, Hucre(5.0))
    pencere.saglik.olay(type("O", (), {"tur": "hucre"})())
    assert pencere.saglik.eski_etiketi.isVisibleTo(pencere.saglik)


def test_yoksay_xlsx_gidis_donus(pencere, tmp_path):
    from tabcel.io import xlsx_io
    tara_bitir(pencere)
    ag = pencere.saglik.agac
    ag.setCurrentItem(ag.topLevelItem(0).child(0))
    b = pencere.saglik._bulgu(ag.currentItem())
    pencere.saglik.yoksay()
    dosya = str(tmp_path / "y.xlsx")
    xlsx_io.kaydet(pencere.kitap, dosya)
    k2 = xlsx_io.ac(dosya)[0]
    assert b.anahtar in k2.saglik_yoksay


def test_cok_uzun_yoksay_kumesi_parcalanir(pencere, tmp_path):
    from tabcel.io import xlsx_io
    pencere.kitap.saglik_yoksay.update(f"hata|1|A{i}" for i in range(1, 800))
    dosya = str(tmp_path / "u.xlsx")
    xlsx_io.kaydet(pencere.kitap, dosya)
    assert xlsx_io.ac(dosya)[0].saglik_yoksay == pencere.kitap.saglik_yoksay
