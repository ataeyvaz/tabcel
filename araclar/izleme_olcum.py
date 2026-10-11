"""Hesap İzleme (Faz 9b) performans ölçümü: 100.000 hücrelik tabloda kök kurma, aralık düğümü, sayfalama, ters yön ve panelin
açılması. Kullanım: .venv\Scripts\python araclar\izleme_olcum.py   (sonuçlar surec.md'ye yazılır)."""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from tabcel.formul.izleme import Izleme
from tabcel.formul.motor import Hesaplayici
from tabcel.model.sayfa import CalismaKitabi, Hucre

N = 100_000


def olc(ad, islev, tekrar=1):
    t0 = time.perf_counter()
    for _ in range(tekrar):
        sonuc = islev()
    ms = (time.perf_counter() - t0) / tekrar * 1000
    print(f"{ad:<58} {ms:9.1f} ms")
    return sonuc


def main():
    app = QApplication.instance() or QApplication([])
    k = CalismaKitabi()
    s = k.sayfalar[0]
    t0 = time.perf_counter()
    yeni = {}
    for r in range(1, N + 1):
        yeni[(r, 1)] = Hucre(float(r))                       # A: sabit
        yeni[(r, 2)] = Hucre(formul=f"=A{r}*2")              # B: formül
        yeni[(r, 3)] = Hucre(formul=f"=A{r}+$F$1")           # C: tek hücreye bağımlı (F1'i 100.000 formül okur)
    yeni[(1, 6)] = Hucre(10.0)                               # F1
    yeni[(1, 4)] = Hucre(formul=f"=SUM(B1:B{N})")            # D1: büyük aralık
    yeni[(1, 5)] = Hucre(formul="=D1+1")                     # E1: zincir
    s.toplu_yaz(yeni)
    print(f"{len(yeni):,} hücre yazıldı: {(time.perf_counter() - t0):.1f} sn")
    t0 = time.perf_counter()
    m = Hesaplayici(k)
    print(f"motor kuruldu + tümü hesaplandı: {(time.perf_counter() - t0):.1f} sn")
    iz = Izleme(k, m)
    kok = olc("kök (E1 = D1+1)", lambda: iz.kok(s, 1, 5), 5)
    d1 = olc("E1 çocukları (D1)", lambda: iz.cocuklar(kok).dugumler[0], 5)
    aralik = olc("D1 çocukları (B1:B100000 tek düğüm + 100.000 hücre özeti)", lambda: iz.cocuklar(d1).dugumler[0])
    print("   özet:", aralik.ozet)
    olc("aralık düğümü: ilk sayfa (100 hücre; 100.000 dolu hücre sıralanır)", lambda: iz.cocuklar(aralik))
    olc("aralık düğümü: 500. sayfa", lambda: iz.cocuklar(aralik, (), 500))
    b = olc("ters yön: A1'in bağımlıları (kök)", lambda: iz.bagimli_kok(s, 1, 1))
    olc("   A1 bağımlı sayısı + ilk sayfa", lambda: iz.bagimli_cocuklar(b))
    f1 = olc("ters yön: F1 (100.000 formül okuyor) kök", lambda: iz.bagimli_kok(s, 1, 6))
    p = olc("   F1 bağımlıları: ilk sayfa (100.000 bağımlı sıralanır)", lambda: iz.bagimli_cocuklar(f1))
    print("   toplam bağımlı:", f"{p.toplam:,}")
    olc("hata kaynağı yok (sayısal hücre) kök", lambda: iz.kok(s, 50_000, 2), 20)
    # panel: pencerede aç
    from tabcel.ui.window import Pencere
    t0 = time.perf_counter()
    pen = Pencere(k)
    pen.show()
    print(f"pencere kuruldu: {(time.perf_counter() - t0):.1f} sn")
    def degis(deger):
        pen.izgara().hucre_gir(1, 6, deger)
        pen.izleme._zamanlayici.stop()
        pen.izleme._calis()
    olc("F1 değişti, panel KAPALI: yeniden hesap (motor)", lambda: degis("15"))
    pen.izgara().sec((1, 5))
    pen.izleme_ac()
    olc("panel: _kur (E1 seçili; arayüz öğeleri dahil)", lambda: pen.izleme._kur())
    pen.izgara().sec((1, 6))
    olc("panel: _kur (F1 seçili; 100.000 bağımlı)", lambda: pen.izleme._kur())
    pen.izgara().sec((1, 1))
    olc("panel: _kur (A1 seçili)", lambda: pen.izleme._kur())
    # değişiklik sonrası yeniden hesap + panel tazeleme (F1 değişince 100.000 formül)
    olc("F1 değişti, panel AÇIK: yeniden hesap + panel güncelleme", lambda: degis("20"))
    pen.degisti_mi = lambda: False
    pen.close()


if __name__ == "__main__":
    main()
