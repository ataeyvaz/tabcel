"""Faz 9d ölçümü: Paylaşım Temizleyici büyük tabloda — tarama (en uzun kesintisiz dilim), temiz kopya (derin kopya + yeniden hesap),
yazma + dosya doğrulaması. Veri yalnız sentetik. Kullanım: .venv\Scripts\python araclar\temizle_olcum.py [satır_sayısı]"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "testler"))

from sentetik import iban_uret, tc_uret
from tabcel.formul.motor import Hesaplayici
from tabcel.io import temiz_dosya, xlsx_io
from tabcel.model import temizle
from tabcel.model.sayfa import CalismaKitabi, Hucre
import random


def kur(satir: int):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    r_ = random.Random(5)
    s.ata(1, 1, Hucre("Ad Soyad"))
    for r in range(2, satir + 2):
        s.ata(r, 1, Hucre(f"Ad{r % 500} Soyad{r % 300}"))
        s.ata(r, 2, Hucre(tc_uret(rnd=r_) if r % 20 == 0 else f"{r % 300}"))
        s.ata(r, 3, Hucre(float(r)))
        s.ata(r, 4, Hucre(f"kisi{r}@ornek.com" if r % 25 == 0 else "-"))
        s.ata(r, 5, Hucre(formul=f"=C{r}*2"))
    s.ata(satir + 3, 3, Hucre(formul=f"=SUM(C2:C{satir + 1})"))
    return k


def main():
    satir = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    k = kur(satir)
    t0 = time.perf_counter()
    Hesaplayici(k)
    print(f"motor kurulumu {time.perf_counter() - t0:.1f} sn")
    tar = temizle.Tarayici(k)
    bas = son = time.perf_counter()
    en_uzun = 0.0
    for olay in tar.calistir():
        simdi = time.perf_counter()
        en_uzun = max(en_uzun, simdi - son)
        son = time.perf_counter()
    print(f"{satir * 5:,} hücre: tarama {time.perf_counter() - bas:.2f} sn, en uzun kesintisiz dilim {en_uzun * 1000:.0f} ms, "
          f"{len(tar.kayitlar)} bulgu")
    t1 = time.perf_counter()
    tk = temizle.temiz_kopya(k, tar.kayitlar, temizle.Plan())
    print(f"temiz kopya (derin kopya + maske + yeniden hesap): {time.perf_counter() - t1:.2f} sn, {len(tk.etkiler)} etkilenen formül")
    t2 = time.perf_counter()
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "t.xlsx")
        xlsx_io.kaydet(tk.kitap, yol)
        t3 = time.perf_counter()
        print(f"yazma: {t3 - t2:.2f} sn")
        kalan = temiz_dosya.dosya_dogrula(yol, tk.yasak)
        print(f"doğrulama: {time.perf_counter() - t3:.2f} sn, kalan özgün değer: {len(kalan)}")
    tk.kapat()


if __name__ == "__main__":
    main()
