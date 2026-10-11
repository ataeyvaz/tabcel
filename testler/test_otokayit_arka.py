"""T4b: otomatik kaydın arka planda yazılması — anlık görüntü (Qt'siz) + pencere akışı ve yarışlar.
Tasarım: t4_arkaplan_tasarim.md. Süre ölçütleri burada değil, ölçüm betiğinde (kırılgan zamanlama testi yok)."""
import os
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.io import kurtarma, xlsx_io
from tabcel.model.adres import Aralik
from tabcel.model.anlik import kitap_anligi
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


# ---------------------------------------------------------------- anlık görüntü (Qt'siz)
def _dolu_kitap():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(1.0))
    s.ata(2, 1, Hucre(None, "=A1*2"))
    s.sonuc_ata(2, 1, 2.0)
    s.birlesimler.append(Aralik(5, 1, 5, 2))
    s.gizli_satir.add(9)
    k.sayfa_ekle("İkinci")
    return k


def test_anlik_kaplar_kopya_degerler_paylasilir():
    k = _dolu_kitap()
    a = kitap_anligi(k)
    assert a.sayfalar is not k.sayfalar and a._dinleyiciler == []
    for s, y in zip(k.sayfalar, a.sayfalar):
        assert y is not s and y.kitap is a
        for ad, v in vars(s).items():
            if isinstance(v, (dict, list, set)):
                assert getattr(y, ad) is not v and getattr(y, ad) == v, ad      # bekçi: yeni kap alanı da kopyalanır
        assert y.havuz is s.havuz                                                # yalnız büyür: paylaşılır
    assert a.adlar is not k.adlar and a.stil_havuzu is k.stil_havuzu


def test_anlik_sonradan_degisiklikten_etkilenmez():
    k = _dolu_kitap()
    a = kitap_anligi(k)
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("yeni"))
    s.ata(3, 3, Hucre(7.0))
    s.gizli_satir.add(10)
    k.sayfa_ekle("Üçüncü")
    y = a.sayfalar[0]
    assert y.deger(1, 1) == 1.0 and y.hucre(3, 3) is None and 10 not in y.gizli_satir
    assert [x.ad for x in a.sayfalar] == ["Sayfa1", "İkinci"]


def test_model_degerleri_degismez():
    """Anlık görüntünün doğruluğu buna dayanır: kaplardaki değerler yerinde değiştirilemez."""
    from tabcel.model.ad import TanimliAd
    from tabcel.model.dogrulama import Dogrulama
    from tabcel.model.filtre import Filtre
    from tabcel.model.grafik import Grafik, Resim
    from tabcel.model.notlar import Not
    from tabcel.model.sayfa_yapisi import SayfaYapisi
    from tabcel.model.stil import Kenarlik, Stil
    for tur in (Hucre, Stil, Kenarlik, SayfaYapisi, Not, Dogrulama, Filtre, Grafik, Resim, TanimliAd):
        assert tur.__dataclass_params__.frozen, tur


def test_anliktan_yazilan_kopya_anlik_ani_icerir(tmp_path):
    k = _dolu_kitap()
    a = kitap_anligi(k)
    k.sayfalar[0].ata(1, 1, Hucre("sonradan"))
    yol = str(tmp_path / "a.xlsx")
    xlsx_io.kaydet(a, yol)
    k2, _ = xlsx_io.ac(yol)
    assert k2.sayfalar[0].deger(1, 1) == 1.0 and [s.ad for s in k2.sayfalar] == ["Sayfa1", "İkinci"]


# ---------------------------------------------------------------- pencere akışı
@pytest.fixture(scope="module")
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


@pytest.fixture
def yavas(monkeypatch):
    """kopya_yaz'ı serbest bırakılana dek bekleten sahte (arka plan iş parçacığında)."""
    basladi, birak = threading.Event(), threading.Event()
    gercek = kurtarma.kopya_yaz

    def kopya(*a, **k):
        basladi.set()
        assert birak.wait(10)
        return gercek(*a, **k)
    monkeypatch.setattr(kurtarma, "kopya_yaz", kopya)
    return basladi, birak


def _dosyalar(p):
    return [os.path.exists(kurtarma._dosya(p.kurtarma_kimligi, u)) for u in (".xlsx", ".json")]


def test_arka_plan_yazar_ve_sonuc_islenir(yavas):
    basladi, birak = yavas
    p = pencere()
    p.izgara().hucre_gir(1, 1, "a")
    assert p.otokayit_yap(arka_plan=True)
    assert basladi.wait(10) and p._otokayit_isi is not None
    assert not p.otokayit_yap(arka_plan=True)                  # sürerken ikinci yazım başlamaz
    assert not p.otokayit_yap()
    birak.set()
    p.otokayit_bekle()
    assert p._otokayit_isi is None and p._son_otokayit is not None and _dosyalar(p) == [True, True]
    assert not p.otokayit_yap(arka_plan=True)                  # değişiklik yok


def test_yazim_surerken_duzenleme_kopyaya_girmez(yavas):
    basladi, birak = yavas
    p = pencere()
    p.izgara().hucre_gir(1, 1, "once")
    assert p.otokayit_yap(arka_plan=True) and basladi.wait(10)
    p.izgara().hucre_gir(1, 1, "sonra")                        # arayüz donmadan düzenleme sürer
    birak.set()
    p.otokayit_bekle()
    dosya = kurtarma._dosya(p.kurtarma_kimligi, ".xlsx")
    kitap, _ = kurtarma.ac(kurtarma.Kurtarilabilir(p.kurtarma_kimligi, "", None, 0, dosya))
    assert kitap.sayfalar[0].deger(1, 1) == "once"
    assert p.otokayit_yap()                                     # yeni değişiklik: sonraki tur yazar


def test_kaydedince_suren_yazim_beklenir_dosya_kalmaz(tmp_path, monkeypatch, yavas):
    basladi, birak = yavas
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "k.xlsx"), ""))
    p = pencere()
    p.izgara().hucre_gir(1, 1, "a")
    assert p.otokayit_yap(arka_plan=True) and basladi.wait(10)
    threading.Timer(0.3, birak.set).start()                    # kaydet beklerken yazım biter
    assert p.kaydet()
    assert _dosyalar(p) == [False, False]                       # silme yazımdan SONRA: sahte kurtarma yok


def test_kapanista_suren_yazim_beklenir(yavas):
    basladi, birak = yavas
    p = pencere()
    p.izgara().hucre_gir(1, 1, "a")
    assert p.otokayit_yap(arka_plan=True) and basladi.wait(10)
    threading.Timer(0.3, birak.set).start()
    p.degisti_mi = lambda: False
    p.close()
    assert _dosyalar(p) == [False, False] and p._otokayit_isi is None


def test_arka_plan_hatasi_sessiz(monkeypatch):
    def bozuk(*a, **k):
        raise OSError("disk dolu")
    monkeypatch.setattr(kurtarma, "kopya_yaz", bozuk)
    p = pencere()
    p.izgara().hucre_gir(1, 1, "a")
    assert p.otokayit_yap(arka_plan=True)                       # başlatıldı
    p.otokayit_bekle()
    assert p._son_otokayit is None and p._otokayit_isi is None  # yazılmadı: sonraki turda yeniden denenir


def test_zamanlayici_arka_plan_yolunu_kullanir(monkeypatch):
    p = pencere()
    cagri = []
    monkeypatch.setattr(p, "otokayit_yap", lambda arka_plan=False: cagri.append(arka_plan))
    p._otokayit_zamanlayici.timeout.emit()
    assert cagri == [True]
