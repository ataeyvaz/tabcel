"""Faz 4 / 4e: otomatik kurtarma kopyaları — Qt'siz katman + pencere akışı + çökme simülasyonu."""
import json
import os
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.io import kurtarma
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.kurtarma_penceresi import KurtarmaPenceresi
from tabcel.ui.window import Pencere


def _olu_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def _kitap():
    k = CalismaKitabi()
    k.sayfalar[0].ata(1, 1, Hucre("veri"))
    return k


def _sahibi_olu_yap(kimlik: str) -> None:
    y = kurtarma._dosya(kimlik, ".json")
    m = json.load(open(y, encoding="utf-8"))
    m["pid"] = _olu_pid()
    json.dump(m, open(y, "w", encoding="utf-8"))


# ---------------------------------------------------------------- Qt'siz
def test_surec_canli_mi():
    assert kurtarma.surec_canli_mi(os.getpid())
    assert not kurtarma.surec_canli_mi(_olu_pid())


def test_kopya_yaz_ve_bekleyenler():
    kid = kurtarma.yeni_kimlik()
    kurtarma.kopya_yaz(_kitap(), kid, "defter.xlsx", r"C:\x\defter.xlsx")
    assert os.path.exists(kurtarma._dosya(kid, ".xlsx")) and os.path.exists(kurtarma._dosya(kid, ".json"))
    assert kurtarma.bekleyenler() == []                       # sahibi (bu süreç) canlı: kurtarma önerilmez
    _sahibi_olu_yap(kid)
    b = kurtarma.bekleyenler()
    assert len(b) == 1 and (b[0].kimlik, b[0].ad, b[0].yol) == (kid, "defter.xlsx", r"C:\x\defter.xlsx")
    kitap, _ = kurtarma.ac(b[0])
    assert kitap.sayfalar[0].deger(1, 1) == "veri"
    kurtarma.sil(kid)
    assert kurtarma.bekleyenler() == [] and os.listdir(kurtarma.klasor()) == []


def test_en_yeni_once_ve_bozuklar_atlanir():
    a, b = kurtarma.yeni_kimlik(), kurtarma.yeni_kimlik()
    kurtarma.kopya_yaz(_kitap(), a, "a", None)
    kurtarma.kopya_yaz(_kitap(), b, "b", None)
    for k in (a, b):
        _sahibi_olu_yap(k)
    m = json.load(open(kurtarma._dosya(a, ".json"), encoding="utf-8"))
    m["zaman"] = 1.0
    json.dump(m, open(kurtarma._dosya(a, ".json"), "w", encoding="utf-8"))
    assert [k.ad for k in kurtarma.bekleyenler()] == ["b", "a"]
    open(os.path.join(kurtarma.klasor(), "bozuk.json"), "w").write("{yok")             # bozuk üst veri
    json.dump({"pid": _olu_pid(), "ad": "yetim"}, open(os.path.join(kurtarma.klasor(), "yetim.json"), "w"))
    assert [k.ad for k in kurtarma.bekleyenler()] == ["b", "a"]                          # xlsx'i olmayan / bozuk atlanır
    assert os.path.exists(os.path.join(kurtarma.klasor(), "bozuk.json"))                # dosyalara dokunulmaz


def test_klasor_yoksa_bos():
    assert kurtarma.bekleyenler() == []


# ---------------------------------------------------------------- pencere
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _sessiz(app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)
    yield
    for p in list(DosyaIslemleri._tutulan):
        p.degisti_mi = lambda: False
        p.close()
    DosyaIslemleri._tutulan.clear()


def pencere():
    p = Pencere(CalismaKitabi())
    p.show()
    return p


def test_zamanlayici_iki_dakika():
    p = pencere()
    assert p._otokayit_zamanlayici.interval() == 120_000 and p._otokayit_zamanlayici.isActive()


def test_otokayit_yalniz_degisince_ve_yalniz_yeni_degisiklikte():
    p = pencere()
    assert not p.otokayit_yap()                               # değişiklik yok
    p.izgara().hucre_gir(1, 1, "a")
    assert p.otokayit_yap()
    dosya = kurtarma._dosya(p.kurtarma_kimligi, ".xlsx")
    assert os.path.exists(dosya)
    assert not p.otokayit_yap()                               # son kopyadan beri değişiklik yok
    p.izgara().hucre_gir(2, 1, "b")
    assert p.otokayit_yap()
    kitap, _ = kurtarma.ac(kurtarma.Kurtarilabilir(p.kurtarma_kimligi, "", None, 0, dosya))
    assert kitap.sayfalar[0].deger(2, 1) == "b"


def test_otokayit_ozgun_dosyaya_dokunmaz(tmp_path, monkeypatch):
    hedef = str(tmp_path / "gercek.xlsx")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    p = pencere()
    p.izgara().hucre_gir(1, 1, "kayitli")
    assert p.kaydet()
    boyut, zaman = os.path.getsize(hedef), os.path.getmtime(hedef)
    p.izgara().hucre_gir(2, 1, "kayitsiz")
    assert p.otokayit_yap()
    assert os.path.getsize(hedef) == boyut and os.path.getmtime(hedef) == zaman


def test_kaydedince_kurtarma_kopyasi_silinir(tmp_path, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "k.xlsx"), ""))
    p = pencere()
    p.izgara().hucre_gir(1, 1, "a")
    p.otokayit_yap()
    assert os.path.exists(kurtarma._dosya(p.kurtarma_kimligi, ".xlsx"))
    assert p.kaydet()
    assert not os.path.exists(kurtarma._dosya(p.kurtarma_kimligi, ".xlsx"))
    assert not os.path.exists(kurtarma._dosya(p.kurtarma_kimligi, ".json"))


def test_bilerek_kapatinca_kopya_silinir(monkeypatch):
    monkeypatch.setattr(DosyaIslemleri, "_kapatma_sorusu", lambda self: "kaydetme")
    p = pencere()
    p.izgara().hucre_gir(1, 1, "a")
    p.otokayit_yap()
    kid = p.kurtarma_kimligi
    p.close()
    assert not os.path.exists(kurtarma._dosya(kid, ".xlsx")) and not p._otokayit_zamanlayici.isActive()


def test_kapatma_iptal_edilirse_kopya_kalir(monkeypatch):
    monkeypatch.setattr(DosyaIslemleri, "_kapatma_sorusu", lambda self: "iptal")
    p = pencere()
    p.izgara().hucre_gir(1, 1, "a")
    p.otokayit_yap()
    p.close()
    assert p.isVisible() and os.path.exists(kurtarma._dosya(p.kurtarma_kimligi, ".xlsx"))
    p.degisti_mi = lambda: False


def _cokme_simule(metin="onemli"):
    """Bir pencerede değişiklik yapılır, kopya yazılır, sonra 'çöker' (pid ölü yapılır, pencere atılır)."""
    p = pencere()
    p.izgara().hucre_gir(1, 1, metin)
    p.izgara().hucre_gir(2, 2, "=A1&\"!\"")
    assert p.otokayit_yap()
    kid = p.kurtarma_kimligi
    _sahibi_olu_yap(kid)
    p._otokayit_zamanlayici.stop()
    p.degisti_mi = lambda: False                            # teardown kopyayı silmesin diye çıkış sorusu yok
    DosyaIslemleri._acik_pencereler.discard(p)
    if p in DosyaIslemleri._tutulan:
        DosyaIslemleri._tutulan.remove(p)
    p.hide()
    p._pencere_kapandi = lambda: None                       # çökme: temiz kapanış yolu çalışmaz
    return kid


def test_cokme_sonrasi_kurtarilir_ve_kaydedince_silinir(tmp_path, monkeypatch):
    kid = _cokme_simule()
    yeni = pencere()
    gorulen = []
    monkeypatch.setattr(DosyaIslemleri, "_kurtarma_sorusu",
                        lambda self, liste: (gorulen.append(liste) or ("ac", liste)))
    assert yeni.kurtarma_denetle() == 1 and gorulen[0][0].kimlik == kid
    k = [p for p in DosyaIslemleri._tutulan if p.kurtarma_kimligi == kid][0]
    s = k.izgara().sayfa
    assert s.deger(1, 1) == "onemli" and s.sonuc(2, 2) == "onemli!"
    assert k.degisti_mi() and k.yol is None                    # kaydedilmemiş sayılır; kayıt yolu yok
    assert k.bilgi_cubugu.isVisible() and "kurtarma" in k.bilgi_etiketi.text()
    assert os.path.exists(kurtarma._dosya(kid, ".xlsx"))       # kaydedilene dek kopya durur
    assert kurtarma.bekleyenler() == []                        # artık bu süreç sahibi: tekrar önerilmez
    hedef = str(tmp_path / "kurtarilan.xlsx")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k2: (hedef, ""))
    assert k.kaydet() and not k.degisti_mi()
    assert not os.path.exists(kurtarma._dosya(kid, ".xlsx"))
    assert os.path.exists(hedef)


def test_kurtarma_sil_ve_sonra(monkeypatch):
    kid = _cokme_simule()
    yeni = pencere()
    monkeypatch.setattr(DosyaIslemleri, "_kurtarma_sorusu", lambda self, liste: ("sonra", liste))
    assert yeni.kurtarma_denetle() == 0 and os.path.exists(kurtarma._dosya(kid, ".xlsx"))
    monkeypatch.setattr(DosyaIslemleri, "_kurtarma_sorusu", lambda self, liste: ("sil", liste))
    assert yeni.kurtarma_denetle() == 0 and not os.path.exists(kurtarma._dosya(kid, ".xlsx"))
    assert yeni.kurtarma_denetle() == 0                         # artık soru yok (yamayı bozacak soru çağrılmaz)


def test_bozuk_kurtarma_kopyasi_silinmez(monkeypatch):
    kid = _cokme_simule()
    open(kurtarma._dosya(kid, ".xlsx"), "wb").write(b"bozuk")
    iletiler = []
    monkeypatch.setattr(QMessageBox, "critical", lambda w, b, m, *a: iletiler.append(m))
    monkeypatch.setattr(DosyaIslemleri, "_kurtarma_sorusu", lambda self, liste: ("ac", liste))
    assert pencere().kurtarma_denetle() == 0
    assert iletiler and "silinmedi" in iletiler[0] and os.path.exists(kurtarma._dosya(kid, ".xlsx"))


def test_kurtarma_penceresi_listesi():
    liste = [kurtarma.Kurtarilabilir("1", "a.xlsx", None, 1.0, "x"),
             kurtarma.Kurtarilabilir("2", "b.xlsx", r"C:\b.xlsx", 2.0, "y")]
    d = KurtarmaPenceresi(liste)
    assert d.liste_kutusu.count() == 2 and [k.kimlik for k in d.secilenler()] == ["1", "2"]
    d.liste_kutusu.clearSelection()
    d.liste_kutusu.item(1).setSelected(True)
    assert [k.kimlik for k in d.secilenler()] == ["2"]
    d.sil_dugmesi.click()
    assert d.eylem() == "sil"


def test_gercek_surec_cokmesi(monkeypatch):
    """Ayrı bir süreç değişiklik yapıp kopya yazar ve ölürse (os._exit) kopya bu süreçte önerilir."""
    kod = (
        "import os, sys\n"
        "os.environ['QT_QPA_PLATFORM']='offscreen'\n"
        "from PySide6.QtWidgets import QApplication\n"
        "app = QApplication([])\n"
        "from tabcel.ui.window import Pencere\n"
        "p = Pencere(); p.izgara().hucre_gir(1, 1, 'cokmeden_once')\n"
        "assert p.otokayit_yap()\n"
        "os._exit(3)\n"
    )
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, "-c", kod], cwd=kok, env=dict(os.environ), timeout=120)
    assert r.returncode != 0                                  # os._exit Qt ile segfault verir: gerçek çökme gibi
    b = kurtarma.bekleyenler()
    assert len(b) == 1
    kitap, _ = kurtarma.ac(b[0])
    assert kitap.sayfalar[0].deger(1, 1) == "cokmeden_once"
