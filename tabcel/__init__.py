"""Tabcel — Excel'e sade, Türkçe, yerel alternatif.

Kullanıcıya görünen ad yalnızca APP_NAME'den okunur (CLAUDE.md kural 1).
"""
import os
import sys
from pathlib import Path

APP_NAME = "Tabcel"
__version__ = "0.1"
DEVELOPERS = "Developed By Usta ve Ata"
KUNYE = f"{APP_NAME} {__version__}"


def resource_dir() -> Path:
    """Kaynak dosyaların klasörü (PyInstaller paketinde _MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parent.parent


def veri_klasoru() -> Path:
    """Kullanıcı verisi (son dosyalar, kurtarma kopyaları): `%APPDATA%/<APP_NAME>`. `TABCEL_VERI_KLASORU`
    ortam değişkeni ile değiştirilebilir (testler gerçek klasöre yazmasın). `setOrganizationName`
    kullanılmaz (CLAUDE.md kural 1)."""
    ozel = os.environ.get("TABCEL_VERI_KLASORU")
    if ozel:
        return Path(ozel)
    taban = os.environ.get("APPDATA") or str(Path.home())
    return Path(taban) / APP_NAME
