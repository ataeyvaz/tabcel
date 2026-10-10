"""Koşullu biçim çizim ölçümü (Faz 5 / 5h; faz5_tasarim.md §8.3 ölçütleri).

100.000 hücre (5.000 x 20), 3 kural tüm sütunlarda (hücre değeri, yinelenen, renk ölçeği). Çalıştır:
    QT_QPA_PLATFORM=offscreen .venv\\Scripts\\python araclar\\kosullu_olcum.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.kosullu import KosulluKural, RENK_OLCEKLERI
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import StilYama
from tabcel.ui.window import Pencere


def ms(t0):
    return round((time.perf_counter() - t0) * 1000, 1)


def main():
    app = QApplication([])
    k = CalismaKitabi()
    s = k.sayfalar[0]
    n = 5000
    s.toplu_yaz({(r, c): Hucre(float((r * 7 + c * 13) % 997)) for r in range(1, n + 1) for c in range(1, 21)})
    kutu = (Aralik(1, 1, n, 20),)
    s.kosullulari_yaz([
        KosulluKural(kutu, tur="hucre_degeri", islec="buyuk", formul1="=900", bicim=StilYama(dolgu="#FFC7CE")),
        KosulluKural(kutu, tur="yinelenen", bicim=StilYama(italik=True)),
        KosulluKural(kutu, tur="renk_olcegi", bicim=None, noktalar=RENK_OLCEKLERI["yesil_sari_kirmizi"]),
    ])
    p = Pencere(k)
    p.resize(1280, 800)
    p.show()
    app.processEvents()
    g = p.izgara()
    vp = g.viewport()
    g._kosullu_gecersiz()
    t0 = time.perf_counter()
    vp.grab()
    print("ilk çizim (istatistikler dahil):", ms(t0), "ms   (ölçüt <= 60)")
    t0 = time.perf_counter()
    vp.grab()
    print("ikinci çizim (önbellek sıcak):", ms(t0), "ms")
    sb = g.verticalScrollBar()
    sure = []
    for i in range(20):
        sb.setValue(sb.value() + 1)
        t0 = time.perf_counter()
        vp.grab()
        sure.append((time.perf_counter() - t0) * 1000)
    print("1 satır kaydırma + çizim (ort):", round(sum(sure) / len(sure), 1), "ms   (ölçüt <= 16)")
    sure = []
    for i in range(10):
        s.ata(10 + i, 3, Hucre(float(i)))
        g._kosullu_gecersiz()
        t0 = time.perf_counter()
        vp.grab()
        sure.append((time.perf_counter() - t0) * 1000)
    print("hücre değişince yeniden çizim (istatistik yeniden):", round(sum(sure) / len(sure), 1),
          "ms   (ölçüt <= 50)")
    s.kosullulari_yaz([])
    g._kosullu_gecersiz()
    t0 = time.perf_counter()
    vp.grab()
    print("kural yokken çizim (referans):", ms(t0), "ms")


if __name__ == "__main__":
    main()
