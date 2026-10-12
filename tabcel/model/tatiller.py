"""Türkiye resmî tatil verisi (`tabcel/veri/resmi_tatiller.json`). Qt yok.

Veri dosyada durur (kural 22 ruhu: tanım kodda değil dosyada; `surum` + `aciklama`). Hafta sonları dosyada yoktur;
iş günü hesabı onları ayrıca eler. Dini bayram tarihleri kullanıcı tarafından doğrulanana dek `dogrulandi=False`.
"""
import datetime as dt
import json
from functools import lru_cache
from typing import FrozenSet, Tuple

from .. import resource_dir
from .tarihseri import ymd_seri

DOSYA = "resmi_tatiller.json"


def _yol():
    return resource_dir() / "tabcel" / "veri" / DOSYA


@lru_cache(maxsize=1)
def yukle() -> dict:
    with open(_yol(), encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _kume() -> Tuple[FrozenSet[int], int, int]:
    veri = yukle()
    seriler = set()
    for yil, ic in veri["yillar"].items():
        for t in ic["tatiller"]:
            d = dt.date.fromisoformat(t["tarih"])
            seriler.add(ymd_seri(d.year, d.month, d.day))
    yillar = sorted(int(y) for y in veri["yillar"])
    return frozenset(seriler), yillar[0], yillar[-1]


def yil_araligi() -> Tuple[int, int]:
    """Verisi bulunan ilk ve son yıl (dahil)."""
    _, a, z = _kume()
    return a, z


def tatiller() -> FrozenSet[int]:
    """Tüm resmî tatiller (tarih seri sayısı)."""
    return _kume()[0]


def dogrulandi_mi() -> bool:
    return bool(yukle().get("dogrulandi"))


def kapsiyor_mu(seri_bas: int, seri_son: int) -> bool:
    """[seri_bas, seri_son] aralığının yılları veri kapsamında mı."""
    from .tarihseri import seri_ymd
    a, z = yil_araligi()
    y1, y2 = seri_ymd(min(seri_bas, seri_son))[0], seri_ymd(max(seri_bas, seri_son))[0]
    return a <= y1 and y2 <= z
