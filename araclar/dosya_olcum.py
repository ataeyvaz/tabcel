"""Dosya G/Ç ölçümü (Faz 4 / 4f): 100.000 hücrelik .xlsx / .csv açma-kaydetme süreleri.

Çalıştır: .venv\\Scripts\\python araclar\\dosya_olcum.py [satir] [sutun]
Varsayılan 5000 x 20; 3 sütunda formül, 4 sütunda biçim vardır. Hedef: açılış < 10 sn.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from tabcel.formul import ceviri  # noqa: E402
from tabcel.formul.motor import Hesaplayici  # noqa: E402
from tabcel.io import csv_io, xlsx_io  # noqa: E402
from tabcel.model.adres import Aralik  # noqa: E402
from tabcel.model.komutlar import bicim_komutu  # noqa: E402
from tabcel.model.sayfa import CalismaKitabi, Hucre  # noqa: E402
from tabcel.model.stil import StilYama  # noqa: E402

SATIR = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
SUTUN = int(sys.argv[2]) if len(sys.argv) > 2 else 20


def olc(ad, f):
    t = time.perf_counter()
    sonuc = f()
    print(f"{ad:<52} {(time.perf_counter() - t):8.2f} sn")
    return sonuc


def kitap_uret():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    yeni = {}
    for r in range(1, SATIR + 1):
        for c in range(1, SUTUN + 1):
            if c in (SUTUN - 2, SUTUN - 1, SUTUN):
                yeni[(r, c)] = Hucre(None, f"=A{r}+B{r}*{c}")
            elif c % 3 == 0:
                yeni[(r, c)] = Hucre(f"Metin {r}-{c}")
            else:
                yeni[(r, c)] = Hucre(float(r * c) / 7)
    s.toplu_yaz(yeni)
    for c, kw in ((1, {"kalin": True}), (2, {"sayi_bicimi": "0.00"}), (4, {"dolgu": "#FFFF00"}),
                  (5, {"sayi_bicimi": "0%", "italik": True})):
        bicim_komutu(s, [Aralik(1, c, SATIR, c)], StilYama(**kw)).yap()
    return k


def main():
    print(f"{SATIR} x {SUTUN} = {SATIR * SUTUN:,} hücre")
    k = olc("Kitap kurma (veri + biçim)", kitap_uret)
    klasor = tempfile.mkdtemp()
    xl = os.path.join(klasor, "o.xlsx")
    cs = os.path.join(klasor, "o.csv")
    olc("xlsx kaydet", lambda: xlsx_io.kaydet(k, xl))
    print(f"   dosya boyutu: {os.path.getsize(xl) / 1e6:.1f} MB")
    k2, _ = olc("xlsx aç (model)", lambda: xlsx_io.ac(xl))
    olc("xlsx aç + motor tüm hesap (Pencere açılışı)", lambda: Hesaplayici(k2))
    olc("csv yaz", lambda: csv_io.dosya_yaz(k.sayfalar[0], cs))
    satirlar = olc("csv oku (ayrıştırma)", lambda: csv_io.dosya_oku(cs)[0])
    olc("csv kitap oluştur (akıllı çözümleme)", lambda: csv_io.kitap_olustur(satirlar))
    olc("kurtarma kopyası yaz (= xlsx kaydet)", lambda: xlsx_io.kaydet(k, xl))


if __name__ == "__main__":
    main()
