"""Faz 5 / 5j-2: şerit ikonları — her ikon kendi ızgarasında çizilir, 32 px'ler boş değildir."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from tabcel.ui import icons

TASARIM_20 = ("cut copy autosum fill clear sort_az sort_za filter_clear reapply define_name "
              "note_delete save").split()
TASARIM_32 = ("paste32 cond_format32 insert32 delete32 format32 sort_filter32 find32 sort32 filter32 "
              "validation32 name_manager32 margins32 orientation32 paper32 print_area32 print_titles32 "
              "note32 freeze32 zoom100_32 autosum32").split()


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_tasarimdaki_ikonlar_var():
    for ad in TASARIM_20 + TASARIM_32:
        assert ad in icons.ICONS, ad


def test_buyuk_ikonlar_32_izgarada_kucukler_20de():
    for ad in TASARIM_32:
        assert icons.ICONS[ad].get("grid") == 32, ad
    for ad in TASARIM_20:
        assert icons.ICONS[ad].get("grid", icons.GRID) == 20, ad


@pytest.mark.parametrize("ad", TASARIM_20 + TASARIM_32)
def test_ikon_cizilir_bos_degil_ve_yakinlastirmada_olceklenir(app, ad):
    g = icons.ICONS[ad].get("grid", icons.GRID)
    for boyut in (g, round(g * 1.5), g * 2):
        pm = icons.icon(ad).pixmap(QSize(boyut, boyut))
        img = pm.toImage()
        assert img.width() == boyut
        assert any(img.pixelColor(x, y).alpha() > 0 for x in range(boyut) for y in range(boyut)), (ad, boyut)


def test_mevcut_ikonlar_ayni_cizilir(app):
    """20'lik ızgara varsayılanı değişmedi: Kalın ikonu 20 px'te çizilir ve boş değildir."""
    img = icons.icon("align_left").pixmap(QSize(20, 20)).toImage()
    assert img.pixelColor(10, 4).alpha() > 0           # üst çizgi M3.5 4.5H16.5 → y=4 satırı dolu
