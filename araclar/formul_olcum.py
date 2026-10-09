"""Formül motoru ölçümü (plan.md Faz 2): 50.000 formüllük zincir ve tipik çizelge.

Çalıştır: .venv\\Scripts\\python araclar\\formul_olcum.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabcel.formul.motor import Hesaplayici  # noqa: E402
from tabcel.model.sayfa import CalismaKitabi, Hucre  # noqa: E402


def olc(ad, f):
    t = time.perf_counter()
    f()
    ms = (time.perf_counter() - t) * 1000
    print(f"{ad:<55} {ms:9.1f} ms")
    return ms


def main():
    n = 50_000
    k = CalismaKitabi()
    s = k.sayfalar[0]
    Hesaplayici(k)
    yeni = {(1, 1): Hucre(1.0)}
    yeni.update({(r, 1): Hucre(None, f"=A{r - 1}+1") for r in range(2, n + 1)})
    olc("Zincir: 50.000 formül toplu yazım + hesaplama", lambda: s.toplu_yaz(yeni))
    assert s.deger(n, 1) == float(n)
    olc("Zincir: baştaki hücre değişti (50.000 yeniden hesap)", lambda: s.ata(1, 1, Hucre(2.0)))
    assert s.deger(n, 1) == float(n + 1)
    olc("Zincir: sondaki hücreye bağlı tek değişiklik", lambda: s.ata(n, 2, Hucre(None, f"=A{n}*2")))

    # tipik çizelge: 5.000 satır × (3 değer + satır toplamı + birikimli toplam)
    k2 = CalismaKitabi()
    s2 = k2.sayfalar[0]
    Hesaplayici(k2)
    m = 5_000
    veri = {}
    for r in range(1, m + 1):
        for c in range(1, 4):
            veri[(r, c)] = Hucre(float(r + c))
        veri[(r, 4)] = Hucre(None, f"=SUM(A{r}:C{r})")
        veri[(r, 5)] = Hucre(None, f"=SUM($D$1:D{r})")
    olc("Çizelge 5.000 satır (SUM satır + birikimli) yazım", lambda: s2.toplu_yaz(veri))
    olc("Çizelge: A1 değişti (birikimli 5.000 yeniden)", lambda: s2.ata(1, 1, Hucre(100.0)))
    olc("Çizelge: A5000 değişti", lambda: s2.ata(m, 1, Hucre(100.0)))


if __name__ == "__main__":
    main()
