"""T1: Türkçe büyük/küçük harf — tek modül (`tabcel/metin_tr.py`). Önceki dört kopyayla aynı davranış, örnek sözcükler,
"yeni kopya açılmasın" bekçisi."""
import pathlib
import random
import re

import pytest

from tabcel import metin_tr
from tabcel.metin_tr import buyuk, esit_mi, kucuk

# Kullanıcının istediği örnek sözcükler (İstanbul, Izmir, ılık, Çorum, Şile, Ödemiş, Ünye) ve beklenen çıktılar
KUCUK = [("İstanbul", "istanbul"), ("Izmir", "ızmir"), ("ılık", "ılık"), ("ILIK", "ılık"), ("Çorum", "çorum"),
         ("Şile", "şile"), ("Ödemiş", "ödemiş"), ("Ünye", "ünye"), ("DİYARBAKIR", "diyarbakır"), ("IĞDIR", "ığdır"),
         ("ÇĞİÖŞÜ", "çğiöşü"), ("", ""), ("abc XYZ 123", "abc xyz 123")]
BUYUK = [("istanbul", "İSTANBUL"), ("ızmir", "IZMİR"), ("ılık", "ILIK"), ("Izmir", "IZMİR"), ("çorum", "ÇORUM"),
         ("şile", "ŞİLE"), ("ödemiş", "ÖDEMİŞ"), ("ünye", "ÜNYE"), ("iyi", "İYİ"), ("ığdır", "IĞDIR"),
         ("çğıiöşü", "ÇĞIİÖŞÜ"), ("", ""), ("abc xyz 123", "ABC XYZ 123")]


@pytest.mark.parametrize("girdi,beklenen", KUCUK)
def test_kucuk(girdi, beklenen):
    assert kucuk(girdi) == beklenen


@pytest.mark.parametrize("girdi,beklenen", BUYUK)
def test_buyuk(girdi, beklenen):
    assert buyuk(girdi) == beklenen


def test_noktali_i_birlesik_nokta_uretmez():
    """Python `'İ'.lower()` = 'i' + U+0307 (birleşik nokta) üretir; Türkçe modül düz 'i' verir."""
    assert "İ".lower() != "i" and kucuk("İ") == "i" and len(kucuk("İSTİKLAL")) == 8


def test_esit_mi_buyuk_kucuk_duyarsiz_turkce():
    assert esit_mi("ISPARTA", "ısparta") and esit_mi("İzmir", "izmir") and esit_mi("ılık", "ILIK")
    assert not esit_mi("Izmir", "izmir")                       # I ≠ i (Türkçe: I → ı)
    assert not esit_mi("ISPARTA", "isparta")


def test_gidis_donus():
    for s in ("İstanbul", "ılık", "Çorum", "ŞİLE", "ünye"):
        assert kucuk(buyuk(s)) == kucuk(s)


# ---------------------------------------------------------------- "davranış değişmedi": eski dört kopyayla birebir
def _eski_kucuk(s):                                            # harmanla / yerel / doldur / sayi_bicimi kopyaları
    return s.replace("I", "ı").replace("İ", "i").lower()


def _eski_buyuk(s):                                            # yerel / doldur / girdi satır içi kopyası
    return s.replace("i", "İ").replace("ı", "I").upper()


def test_eski_kopyalarla_birebir_ayni():
    rnd = random.Random(7)
    havuz = "abcçdefgğhıijklmnoöpqrsştuüvwxyzABCÇDEFGĞHIİJKLMNOÖPQRSŞTUÜVWXYZ0123456789 -'.,é É ß ǅ ΐ Ω ω"
    for _ in range(3000):
        s = "".join(rnd.choice(havuz) for _ in range(rnd.randint(0, 12)))
        assert kucuk(s) == _eski_kucuk(s) and buyuk(s) == _eski_buyuk(s)


def test_eski_ice_aktarma_yollari_ayni_nesneyi_verir():
    """Başka modüllerin kullandığı adlar tek kaynağa bağlı (kopya değil)."""
    from tabcel.formul import yerel
    from tabcel.model import doldur, harmanla, sayi_bicimi
    assert yerel.tr_buyuk is metin_tr.buyuk and yerel.tr_kucuk is metin_tr.kucuk
    assert harmanla.tr_kucuk is metin_tr.kucuk and harmanla.tr_buyuk is metin_tr.buyuk
    assert doldur._tr_kucuk is metin_tr.kucuk and doldur._tr_buyuk is metin_tr.buyuk
    assert sayi_bicimi._tr_kucuk is metin_tr.kucuk


# ---------------------------------------------------------------- bekçi: yeni kopya açılmasın
KOK = pathlib.Path(__file__).resolve().parent.parent / "tabcel"
KOPYA_DESENI = re.compile(r"""replace\(\s*["'](?:I|i|İ|ı)["']\s*,\s*["'](?:ı|İ|i|I)["']\s*\)""")


def test_baska_modulde_yerel_donusum_kopyasi_yok():
    """Büyük/küçük harf dönüşümünün satır içi kopyası yalnız `metin_tr.py`de olabilir (I/ı, İ/i)."""
    kopyalar = []
    for dosya in KOK.rglob("*.py"):
        if dosya.name == "metin_tr.py":
            continue
        if KOPYA_DESENI.search(dosya.read_text(encoding="utf-8")):
            kopyalar.append(str(dosya.relative_to(KOK)))
    assert kopyalar == [], f"Türkçe harf dönüşümü kopyası: {kopyalar} → `tabcel.metin_tr` kullanın"


def test_model_ve_formul_qt_icermez():
    """Kural 2: yeni modül dahil model/ ve formul/ Qt içe aktarmaz."""
    assert "PySide6" not in (KOK / "metin_tr.py").read_text(encoding="utf-8")
