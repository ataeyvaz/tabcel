"""Her grafik türünü örnek veriyle tek PNG'ye çizer (Faz 6 görsel denetimi; gerçek platform, gerçek yazı tipi).

Kullanım: .venv\\Scripts\\python araclar/grafik_onizleme.py [çıktı.png]
"""
import os
import sys

kok = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, kok)
os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from tabcel.model.grafik import Grafik
from tabcel.model.grafik_verisi import GrafikVerisi, SeriVerisi
from tabcel.ui.grafik_boyayici import grafik_ciz

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"]


def veri_cok():
    return GrafikVerisi((SeriVerisi("Gelir", (120.0, 150.0, 90.0, 180.0, 160.0, 210.0), AYLAR, None, None),
                         SeriVerisi("Gider", (80.0, 95.0, 100.0, 110.0, 90.0, 120.0), AYLAR, None, None)))


def veri_tek():
    return GrafikVerisi((SeriVerisi("Pay", (45.0, 25.0, 20.0, 10.0), ["Kuzey", "Güney", "Doğu", "Batı"], None, None),))


def veri_xy():
    xs = [1, 2, 3, 4, 5, 6, 7, 8]
    ys = [2.0, 3.5, 3.0, 5.5, 6.0, 8.5, 8.0, 11.0]
    return GrafikVerisi((SeriVerisi("Ölçüm", tuple(ys), [""] * 8, tuple(float(x) for x in xs), None),))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    ornekler = [
        ("sutun", "kumelenmis", veri_cok(), dict(baslik="Gelir ve gider", y_baslik="Bin ₺", x_baslik="Ay")),
        ("sutun", "yigili", veri_cok(), dict(baslik="Yığılı sütun")),
        ("sutun", "yuzde_yigili", veri_cok(), dict(baslik="%100 yığılı", gosterge="alt")),
        ("cubuk", "kumelenmis", veri_cok(), dict(baslik="Çubuk", deger_etiketi=True)),
        ("cizgi", "kumelenmis", veri_cok(), dict(baslik="Çizgi", gosterge="ust")),
        ("alan", "yigili", veri_cok(), dict(baslik="Yığılı alan")),
        ("pasta", "kumelenmis", veri_tek(), dict(baslik="Pasta", deger_etiketi=True)),
        ("halka", "kumelenmis", veri_tek(), dict(baslik="Halka", gosterge="alt")),
        ("dagilim", "kumelenmis", veri_xy(), dict(baslik="Dağılım", gosterge=None, x_baslik="X", y_baslik="Y")),
    ]
    w, h = 480, 288
    sutun = 3
    satir = (len(ornekler) + sutun - 1) // sutun
    img = QImage(sutun * (w + 12) + 12, satir * (h + 12) + 12, QImage.Format_RGB32)
    img.fill(QColor("#F3F3F3"))
    p = QPainter(img)
    for i, (tur, alt, veri, kw) in enumerate(ornekler):
        kw.setdefault("gosterge", "sag")
        p.save()
        p.translate(12 + (i % sutun) * (w + 12), 12 + (i // sutun) * (h + 12))
        grafik_ciz(p, veri, Grafik(tur=tur, alt_tur=alt, **kw), (w, h))
        p.restore()
    p.end()
    yol = sys.argv[1] if len(sys.argv) > 1 else "grafik_onizleme.png"
    img.save(yol)
    print(f"{len(ornekler)} grafik -> {yol}")


if __name__ == "__main__":
    main()
