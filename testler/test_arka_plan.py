"""Faz 4 / 4f: arka plan çalıştırıcı — sonuç, istisna, ana iş parçacığı canlı, pencere kilidi."""
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.arka_plan import arka_planda
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


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


def test_sonuc_ve_ayri_is_parcacigi(app):
    ana = threading.get_ident()
    sonuc = arka_planda(None, "x", lambda: (threading.get_ident(), 42))
    assert sonuc[1] == 42 and sonuc[0] != ana


def test_istisna_ana_is_parcacigina_aktarilir(app):
    def patla():
        raise ValueError("kötü")
    with pytest.raises(ValueError, match="kötü"):
        arka_planda(None, "x", patla)


def test_olay_dongusu_calismaya_devam_eder(app):
    """İşlem sürerken ana iş parçacığının zamanlayıcıları işler (arayüz donmaz)."""
    vurus = []
    t = QTimer()
    t.timeout.connect(lambda: vurus.append(1))
    t.start(20)
    arka_planda(None, "x", lambda: time.sleep(0.4))
    t.stop()
    assert len(vurus) >= 5


def test_uzun_islemde_pencere_kilitlenir_ve_acilir(app):
    p = Pencere(CalismaKitabi())
    p.show()
    durumlar = []
    t = QTimer()
    t.timeout.connect(lambda: durumlar.append(p.isEnabled()))
    t.start(30)
    arka_planda(p, "Bekleyin", lambda: time.sleep(0.9), gecikme_ms=100)
    t.stop()
    assert False in durumlar and p.isEnabled()                 # sürerken devre dışı, bitince açık


def test_kisa_islemde_pencere_hic_kilitlenmez(app):
    p = Pencere(CalismaKitabi())
    p.show()
    durumlar = []
    t = QTimer()
    t.timeout.connect(lambda: durumlar.append(p.isEnabled()))
    t.start(10)
    arka_planda(p, "Bekleyin", lambda: time.sleep(0.1), gecikme_ms=5000)
    t.stop()
    assert all(durumlar) and p.isEnabled()


def test_hata_sonrasi_pencere_acik_kalir(app):
    p = Pencere(CalismaKitabi())
    p.show()

    def patla():
        time.sleep(0.3)
        raise OSError("x")
    with pytest.raises(OSError):
        arka_planda(p, "x", patla, gecikme_ms=50)
    assert p.isEnabled()


def test_buyuk_dosya_arka_planda_acilir_ve_kaydedilir(tmp_path, monkeypatch):
    """Gerçek akış: 20.000 hücre kaydet → aç, ana iş parçacığı olay işler."""
    from tabcel.model.sayfa import Hucre
    p = Pencere(CalismaKitabi())
    p.show()
    s = p.izgara().sayfa
    s.toplu_yaz({(r, c): Hucre(float(r * c)) for r in range(1, 1001) for c in range(1, 21)})
    hedef = str(tmp_path / "buyuk.xlsx")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    assert p.farkli_kaydet()
    p.yol = None                                                # aynı dosya "zaten açık" kısayolunu atla
    q = p.dosya_ac(hedef)
    assert q.izgara().sayfa.deger(1000, 20) == 20000.0

