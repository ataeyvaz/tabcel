"""Şerit yerleşim ölçütlerini GERÇEK platformda (gerçek yazı tipiyle) denetler (5j-4; faz5j_tasarim.md §3.1/§9):
  - 1100 px: Giriş sekmesinde hiçbir grup durum 2'ye (tek açılır düğme) inmez
  - 800 px: hiçbir grup sayfa dışına taşmaz
Kullanım: .venv\Scripts\python araclar/serit_olcum.py [ekran_goruntusu_klasoru]
Pencere kısa süre ekranda görünür (ekransız Qt yazıyı kutu ölçtüğü için offscreen kullanılmaz)."""
import os
import sys
import tempfile

kok = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, kok)
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ.setdefault("TABCEL_VERI_KLASORU", os.path.join(tempfile.gettempdir(), "tabcel_olcum"))

from PySide6.QtWidgets import QApplication

from tabcel.ui.window import Pencere


def main() -> int:
    app = QApplication.instance() or QApplication([])
    klasor = sys.argv[1] if len(sys.argv) > 1 else None
    p = Pencere()
    hata = 0
    for genislik in (1100, 800, 1400):
        p.resize(genislik, 600)
        p.show()
        app.processEvents()
        app.processEvents()
        sayfa = p.bicim_cubugu
        durumlar = [(g.ad, g.durum) for g in sayfa.gruplar]
        tasan = [g.ad for g in sayfa.gruplar
                 if g.mapTo(sayfa, g.rect().topRight()).x() > sayfa.width() + 1]
        print(f"{genislik} px: {durumlar}  sizeHint={sayfa.sizeHint().width()}  taşan={tasan}")
        if genislik == 1100 and any(d == 2 for _a, d in durumlar):
            print("  ❌ 1100 px'te açılır düğmeye inen grup var")
            hata = 1
        if genislik == 800 and tasan:
            print("  ❌ 800 px'te taşan grup var")
            hata = 1
        if klasor:
            p.grab().save(os.path.join(klasor, f"serit_{genislik}.png"))
    print("TAMAM" if not hata else "BAŞARISIZ")
    return hata


if __name__ == "__main__":
    sys.exit(main())
