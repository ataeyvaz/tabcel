"""Testler gerçek kullanıcı verisi klasörüne (son dosyalar, kurtarma) yazmasın."""
import pytest


@pytest.fixture(autouse=True)
def _veri_klasoru(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("TABCEL_VERI_KLASORU", str(tmp_path_factory.mktemp("veri")))
