"""Faz 7c: yazım denetimi — oturum mantığı (Qt'siz, sahte motorla), pencere, F7/şerit bağlantısı, gerçek Windows motoru."""
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.yazim import YazimOturumu, hucre_sirasi
from tabcel.ui.window import Pencere
from tabcel.ui.yazim_penceresi import YazimPenceresi

SOZLUK = {"merhaba", "dünya", "kitap", "çay", "ev", "var", "bir"}
ONERI = {"merhba": ["merhaba"], "kitapp": ["kitap"], "evv": ["ev", "evi"]}


class SahteMotor:
    def errors(self, metin):
        return [(m.start(), len(m.group()), 1, "") for m in re.finditer(r"[^\W\d_]+", metin)
                if m.group().lower() not in SOZLUK]

    def suggest(self, sozcuk, limit=6):
        return ONERI.get(sozcuk, [])[:limit]


def _sayfa(**hucreler):
    s = CalismaKitabi().sayfalar[0]
    for ad, d in hucreler.items():
        r, c = int(ad[1:]), ord(ad[0]) - 64
        s.ata(r, c, d if isinstance(d, Hucre) else Hucre(d))
    return s


def _oturum(sayfa, hucreler=None, uygulananlar=None):
    sira = hucreler if hucreler is not None else hucre_sirasi(sayfa, [], True)
    return YazimOturumu(sayfa, sira, SahteMotor(),
                        lambda s, yeni: (s.toplu_yaz(yeni), uygulananlar is not None and uygulananlar.append(yeni)))


# ---------------------------------------------------------------- model
def test_yalniz_sabit_metin_hucreleri_denetlenir():
    s = _sayfa(A1="merhba", A2=5.0, A3=Hucre(formul='="kitapp"'), A4=True, A5="  ")
    assert hucre_sirasi(s, [], True) == [(1, 1)]


def test_secim_kapsami_ve_siralama():
    s = _sayfa(A1="kitapp", B1="evv", A2="ev", C3="merhba")
    assert hucre_sirasi(s, [Aralik(1, 1, 2, 2)], False) == [(1, 1), (1, 2), (2, 1)]
    ters = [Aralik(1, 1, 1, 1), Aralik(1, 1, 1, 2)]               # çakışan seçim yinelenmez
    assert hucre_sirasi(s, ters, False) == [(1, 1), (1, 2)]


def test_bulgu_ve_oneri():
    s = _sayfa(A1="bir merhba dünya")
    o = _oturum(s)
    b = o.ara()
    assert (b.satir, b.sutun, b.sozcuk, b.baslangic) == (1, 1, "merhba", 4)
    assert o.oneriler() == ["merhaba"]


def test_degistir_ve_ayni_hucredeki_sonraki_hata():
    s = _sayfa(A1="merhba kitapp")
    o = _oturum(s)
    o.ara()
    b = o.degistir("merhaba")                                    # metin uzadı: konum kaymamalı
    assert s.deger(1, 1) == "merhaba kitapp" and b.sozcuk == "kitapp"
    assert o.degistir("kitap") is None
    assert s.deger(1, 1) == "merhaba kitap" and o.degistirilen == 2


def test_yoksay_ve_tumunu_yoksay():
    s = _sayfa(A1="xyz kitap xyz", A2="xyz", A3="qqq")
    o = _oturum(s)
    assert o.ara().sozcuk == "xyz"
    assert o.yoksay().sozcuk == "xyz"                            # aynı hücredeki ikinci
    assert o.tumunu_yoksay().sozcuk == "qqq"                     # A2'deki xyz atlandı
    assert o.yoksay() is None and s.deger(1, 1) == "xyz kitap xyz"


def test_tumunu_degistir_sonrakileri_kendiliginden_duzeltir():
    s = _sayfa(A1="kitapp", A2="bir kitapp", A3="evv", B1="Kitapp")
    o = _oturum(s)
    b = o.ara()
    b = o.tumunu_degistir("kitap")
    assert s.deger(1, 1) == "kitap" and s.deger(2, 1) == "bir kitap" and b.sozcuk == "evv"
    assert s.deger(1, 2) == "kitap"                              # büyük/küçük harf duyarsız eşleşme (Türkçe)


def test_turkce_buyuk_kucuk_i():
    s = _sayfa(A1="Iyi", A2="ıyi")
    sozluk = SOZLUK | {"ıyi"}
    class M(SahteMotor):
        def errors(self, metin):
            return [(0, len(metin), 1, "")] if metin.lower() == "iyi" or metin == "Iyi" else []
    o = YazimOturumu(s, [(1, 1), (2, 1)], M(), lambda sy, y: sy.toplu_yaz(y))
    assert o.ara().sozcuk == "Iyi"
    assert sozluk


def test_hepsi_dogruysa_none():
    s = _sayfa(A1="merhaba dünya")
    o = _oturum(s)
    assert o.ara() is None and o.denetlenen_hucre == 1


def test_degistirme_bos_olursa_hucre_silinir():
    s = _sayfa(A1="xyz")
    o = _oturum(s)
    o.ara()
    o.degistir("")
    assert s.hucre(1, 1) is None


def test_oneri_hatasi_denetimi_bozmaz():
    class Bozuk(SahteMotor):
        def suggest(self, sozcuk, limit=6):
            raise RuntimeError("com")
    s = _sayfa(A1="xyz")
    o = YazimOturumu(s, [(1, 1)], Bozuk(), lambda *a: None)
    o.ara()
    assert o.oneriler() == []


# ---------------------------------------------------------------- arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    monkeypatch.setattr(Pencere, "_yazim_motoru", lambda self: SahteMotor())
    p = Pencere(CalismaKitabi())
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()


def test_pencere_degistirir_ve_geri_alinir(pencere, app, monkeypatch):
    g = pencere.izgara()
    g.hucre_gir(1, 1, "merhba dünya")
    g.hucre_gir(2, 1, "kitapp")
    kutular = []
    monkeypatch.setattr(YazimPenceresi, "exec", lambda self: kutular.append(self) or 0)
    g.sec((1, 1), (2, 1))
    assert pencere.yazim_denetle()
    d = kutular[0]
    assert d.konum.text() == "A1 hücresinde" and d.yerine.text() == "merhaba" and "merhba" in d.baglam.text()
    d.dugmeler["Değiştir"].click()
    assert g.sayfa.deger(1, 1) == "merhaba dünya" and d.konum.text() == "A2 hücresinde"
    d.dugmeler["Değiştir"].click()
    assert d.bitti and g.sayfa.deger(2, 1) == "kitap"
    assert "tamamlandı" in d.baglam.text() and not d.dugmeler["Değiştir"].isEnabled()
    g.geri_al()
    assert g.sayfa.deger(2, 1) == "kitapp" and g.sayfa.deger(1, 1) == "merhaba dünya"   # her düzeltme ayrı adım


def test_tek_hucre_secili_tum_sayfa_denetlenir(pencere, monkeypatch):
    g = pencere.izgara()
    g.hucre_gir(5, 3, "evv")
    g.sec((1, 1))
    kutular = []
    monkeypatch.setattr(YazimPenceresi, "exec", lambda self: kutular.append(self) or 0)
    pencere.yazim_denetle()
    assert kutular[0].konum.text() == "C5 hücresinde"


def test_hata_yoksa_ileti(pencere, monkeypatch):
    pencere.izgara().hucre_gir(1, 1, "merhaba")
    iletiler = []
    monkeypatch.setattr(QMessageBox, "information", lambda w, b, m, *a: iletiler.append(m))
    pencere.yazim_denetle()
    assert iletiler and "yanlış sözcük bulunamadı" in iletiler[0]


def test_motor_yoksa_denetim_baslamaz(app, monkeypatch):
    monkeypatch.setattr(Pencere, "_yazim_motoru", lambda self: None)
    p = Pencere(CalismaKitabi())
    assert p.yazim_denetle() is False
    p.close()


def test_f7_ve_serit_eylemi(pencere, monkeypatch):
    cagrilar = []
    monkeypatch.setattr(Pencere, "yazim_denetle", lambda self: cagrilar.append(1) or True)
    a = pencere.eylemler["yazim"]
    assert "F7" in a.toolTip()
    a.trigger()
    assert cagrilar == [1]


# ---------------------------------------------------------------- gerçek Windows motoru
def _gercek_motor():
    from tabcel.io.yazim_motoru import SpellEngine, SpellEngineUnavailable
    try:
        return SpellEngine()
    except SpellEngineUnavailable:
        return None


def test_gercek_motor_turkce():
    m = _gercek_motor()
    if m is None:
        pytest.skip("Windows Türkçe yazım denetimi bileşeni yok")
    assert m.errors("merhaba dünya kitap") == []
    hatalar = m.errors("bu kitapp çok güzzel")
    assert [("bu kitapp çok güzzel")[b:b + u] for b, u, *_ in hatalar] == ["kitapp", "güzzel"]
    assert "kitap" in m.suggest("kitapp")
