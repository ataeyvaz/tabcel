"""Faz 7b: Hakkında penceresi, künye, ikon dosyası."""
import os
import struct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from tabcel import APP_NAME, DEVELOPERS, __version__, resource_dir
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.hakkinda_penceresi import BILESENLER, HakkindaPenceresi, hakkinda_metni
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_hakkinda_metni_ad_surum_kunye_lisans():
    m = hakkinda_metni()
    assert APP_NAME in m and __version__ in m and DEVELOPERS == "Developed By Usta ve Ata" and DEVELOPERS in m
    for ad, _, lisans in BILESENLER:
        assert ad in m and lisans in m
    assert not any("GPL" in l and "LGPL" not in l for _, _, l in BILESENLER)          # kural 5


def test_pencere_icerigi(app):
    d = HakkindaPenceresi()
    assert d.windowTitle() == f"{APP_NAME} Hakkında"
    metin = " ".join(l.text() for l in d.findChildren(QLabel))
    assert APP_NAME in metin and DEVELOPERS in metin and "PySide6" in metin and "sunucuya gönderilmez" in metin


def test_yardim_sekmesinde_hakkinda_eylemi(app, monkeypatch):
    p = Pencere(CalismaKitabi())
    a = p.eylemler["hakkinda"]
    assert a.text() == f"{APP_NAME} Hakkında"
    acilan = []
    monkeypatch.setattr(HakkindaPenceresi, "exec", lambda self: acilan.append(self.windowTitle()) or 0)
    a.trigger()
    assert acilan == [f"{APP_NAME} Hakkında"]


def test_ikon_dosyasi_cok_boyutlu_ico():
    ico = resource_dir() / "tabcel.ico"
    ham = ico.read_bytes()
    sifir, tur, adet = struct.unpack("<HHH", ham[:6])
    assert (sifir, tur) == (0, 1) and adet >= 6
    boyutlar = {(ham[6 + 16 * i] or 256) for i in range(adet)}
    assert {16, 32, 48, 256} <= boyutlar
