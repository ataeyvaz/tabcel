"""Bilgi fonksiyonları (E… işlevleri). Qt yok."""
from ...model import deger as D
from ...model.deger import Hata
from . import fonksiyon
from .ortak import skaler


@skaler("ISNUMBER", "h")
def _isnumber(b, v):
    return isinstance(v, float) and not isinstance(v, bool)


@skaler("ISTEXT", "h")
def _istext(b, v):
    return isinstance(v, str)


@skaler("ISBLANK", "h")
def _isblank(b, v):
    return v is None


@skaler("ISERROR", "h")
def _iserror(b, v):
    return isinstance(v, Hata)


@fonksiyon("NA", en_az=0, en_cok=0)
def _na(b):
    return D.YOK


@skaler("ISNA", "h")
def _isna(b, v):
    return v == D.YOK


@skaler("ISLOGICAL", "h")
def _islogical(b, v):
    return isinstance(v, bool)
