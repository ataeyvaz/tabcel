"""Faz 9c ölçümü: Tablo Sağlığı taraması büyük tabloda — toplam süre ve en uzun kesintisiz dilim (arayüz donması).
Kullanım: .venv\\Scripts\\python araclar\\saglik_olcum.py [satır_sayısı]"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabcel.formul import saglik
from tabcel.formul.motor import Hesaplayici
from tabcel.model.sayfa import CalismaKitabi, Hucre


def kur(satir: int):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(2, satir + 2):
        s.ata(r, 1, Hucre(float(r)))
        s.ata(r, 2, Hucre(float(r % 97)))
        s.ata(r, 3, Hucre(formul=f"=A{r}*B{r}"))
        s.ata(r, 4, Hucre(f"Ad{r % 500}"))
        s.ata(r, 5, Hucre(f"{r % 300}"))
    s.ata(satir + 3, 3, Hucre(formul=f"=SUM(C2:C{satir + 1})"))
    return k, Hesaplayici(k)


def main():
    satir = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    k, m = kur(satir)
    t = saglik.Tarayici(k, m, saglik.Ayarlar(), set())
    g = t.calistir()
    bas = time.perf_counter()
    son = bas
    en_uzun = 0.0
    bulgu = 0
    for olay in g:
        simdi = time.perf_counter()
        en_uzun = max(en_uzun, simdi - son)
        son = time.perf_counter()
        if olay[0] == "bulgu":
            bulgu += 1
    toplam = time.perf_counter() - bas
    print(f"{satir * 5:,} hücre: toplam {toplam:.2f} sn, en uzun kesintisiz dilim {en_uzun * 1000:.0f} ms, {bulgu} bulgu")


if __name__ == "__main__":
    main()
