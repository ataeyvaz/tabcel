"""Fonksiyon testleri için ortak düzen (Qt yok): küçük veri ızgarası + formül değerlendirme."""
import pytest

from tabcel.formul.agac import formul_ayristir
from tabcel.formul.degerlendir import Baglam, hucre_sonucu
from tabcel.formul.yerel import EN
from tabcel.model import deger as D
from tabcel.model.adres import hucre_coz
from tabcel.model.sayfa import CalismaKitabi, Hucre

HATA = {"#DIV/0!": D.BOL0, "#N/A": D.YOK, "#VALUE!": D.DEGER_HATASI, "#NUM!": D.SAYI,
        "#REF!": D.BASV, "#NAME?": D.AD}


def kitap_kur(veri=None):
    """veri: {"A1": 10, "A2": "abc", "A3": True, "A4": D.YOK, "B1": "=A1*2"}"""
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for adres, v in (veri or {}).items():
        h = hucre_coz(adres)
        if isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if isinstance(v, str) and v.startswith("="):
            s.ata(h.satir, h.sutun, Hucre(None, v))
        elif v is not None:
            s.ata(h.satir, h.sutun, Hucre(v))
    return k


def hesapla(formul, veri=None, satir=20, sutun=20):
    k = kitap_kur(veri)
    s = k.sayfalar[0]
    return hucre_sonucu(formul_ayristir(formul, EN), Baglam(s, satir, sutun, k))


def kontrol(formul, beklenen, veri=None):
    sonuc = hesapla(formul, veri)
    if isinstance(beklenen, float) and isinstance(sonuc, float):
        assert sonuc == pytest.approx(beklenen, rel=1e-9, abs=1e-9), (formul, sonuc)
    else:
        assert sonuc == beklenen and type(sonuc) is type(beklenen), (formul, sonuc, beklenen)
