"""Tabcel — Excel'e sade, Türkçe, yerel alternatif.

Kullanıcıya görünen ad yalnızca APP_NAME'den okunur (CLAUDE.md kural 1).
"""
import sys
from pathlib import Path

APP_NAME = "Tabcel"
__version__ = "0.1"
KUNYE = f"{APP_NAME} {__version__}"


def resource_dir() -> Path:
    """Kaynak dosyaların klasörü (PyInstaller paketinde _MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parent.parent
