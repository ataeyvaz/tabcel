"""100.000 hücre performans ölçümü (surec.md §5b). Çalıştır:

    .venv\\Scripts\\python araclar\\performans_olcum.py [satir] [sutun]

Varsayılan 5000 x 20 = 100.000 dolu hücre. Gerçek yazı tipleri için QT_QPA_PLATFORM ayarlanmaz.
Sonuçlar tablo olarak yazdırılır; hedef: kaydırmada kare başına < 16 ms.
"""
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, __file__.rsplit("\\", 2)[0] if "\\" in __file__ else ".")

from tabcel.model.adres import Aralik  # noqa: E402
from tabcel.model.sayfa import CalismaKitabi, Hucre  # noqa: E402
from tabcel.ui.window import Pencere  # noqa: E402

SATIR = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
SUTUN = int(sys.argv[2]) if len(sys.argv) > 2 else 20
SATIRLAR = []


def olc(ad, fn, hedef_ms=None, tekrar=1):
    sure = []
    for _ in range(tekrar):
        t = time.perf_counter()
        fn()
        sure.append((time.perf_counter() - t) * 1000)
    ort, enb = statistics.mean(sure), max(sure)
    durum = ""
    if hedef_ms is not None:
        durum = "OK" if ort <= hedef_ms else "YAVAŞ"
    SATIRLAR.append((ad, ort, enb, hedef_ms, durum))
    print(f"{ad:<58} ort {ort:9.2f} ms   en çok {enb:9.2f} ms   "
          f"{'hedef ' + str(hedef_ms) + ' ms ' + durum if hedef_ms else ''}")
    return ort


def main():
    app = QApplication(sys.argv)
    kitap = CalismaKitabi()
    sayfa = kitap.sayfalar[0]

    # Referans: boş sayfada aynı pencere/grab maliyeti (ölçümün kendi yükünü ayırmak için)
    bos = Pencere(CalismaKitabi())
    bos.resize(1280, 800)
    bos.show()
    app.processEvents()
    bvp, bvs = bos.izgara().viewport(), bos.izgara().verticalScrollBar()
    olc("REFERANS: boş sayfa kaydırma (60 kare, toplam)",
        lambda: [(bvs.setValue(i), bvp.grab()) for i in range(60)])
    print(f"   -> boş sayfada kare başına {SATIRLAR[-1][1] / 60:.2f} ms (grab + pencere yükü)")
    bos.close()

    print(f"\n=== {SATIR} x {SUTUN} = {SATIR * SUTUN} dolu hücre ===")
    def doldur():
        for r in range(1, SATIR + 1):
            for c in range(1, SUTUN + 1):
                sayfa.ata(r, c, Hucre(f"Satır {r}" if c == 1 else float(r * c) + 0.25))
    olc("Veri yükleme (Sayfa.ata x N)", doldur)

    pencere = Pencere(kitap)
    pencere.resize(1280, 800)
    pencere.show()
    g = pencere.izgara()
    app.processEvents()
    vp = g.viewport()

    olc("İlk çizim (viewport.grab)", lambda: vp.grab(), 16)

    vs = g.verticalScrollBar()
    hs = g.horizontalScrollBar()

    def kare_olc(ad, adim, n, hedef=16):
        """Gerçek kaydırma akışı: değeri değiştir, olayları işle (artımlı çizim dahil); kare başına ms."""
        t = time.perf_counter()
        for i in range(n):
            adim(i)
            app.processEvents()
        ms = (time.perf_counter() - t) * 1000 / n
        durum = "OK" if ms <= hedef else "YAVAŞ"
        SATIRLAR.append((ad, ms, ms, hedef, durum))
        print(f"{ad:<58} kare başına {ms:8.2f} ms   hedef {hedef} ms {durum}")

    n = 60
    olc("Tam çizim (viewport.grab, artımlı yol YOK)", lambda: [vp.grab() for _ in range(5)], 16 * 5 * 3)
    SATIRLAR[-1] = (*SATIRLAR[-1][:1], SATIRLAR[-1][1] / 5, SATIRLAR[-1][2] / 5, 48, "bilgi")
    print(f"   -> tam çizim {SATIRLAR[-1][1]:.2f} ms/kare (bilgi; tek seferlik yollarda kullanılır)")
    kare_olc(f"Dikey kaydırma 1 satır/kare — başta ({n} kare)", lambda i: vs.setValue(i), n)
    orta = SATIR // 2
    kare_olc(f"Dikey kaydırma 1 satır/kare — ortada ({n} kare)", lambda i: vs.setValue(orta + i), n)
    kare_olc(f"Dikey kaydırma 3 satır/kare ({n} kare)", lambda i: vs.setValue(orta + 100 + 3 * i), n)
    kare_olc(f"Dikey sıçrama (500 satır/kare, tam çizim) ({n} kare)", lambda i: vs.setValue(100 + 500 * (i % 8)), n)
    kare_olc(f"Yatay kaydırma ({SUTUN} kare)", lambda i: hs.setValue(i), SUTUN)
    hs.setValue(0)
    vs.setValue(0)
    app.processEvents()
    g.sec((1, 1))

    # gezinme
    kare_olc("Ok tuşu ile hücre değiştirme + boyama (60 basış)", lambda i: QTest.keyClick(g, Qt.Key_Down), 60)
    kare_olc("Shift+Ok ile seçim genişletme + boyama (60 basış)", lambda i: QTest.keyClick(g, Qt.Key_Right if i % 2 else Qt.Key_Down, Qt.ShiftModifier), 60)
    g.sec((1, 1))
    app.processEvents()
    g.sec((1, 1))
    olc("Ctrl+Aşağı (veri bloğunun sonuna)", lambda: QTest.keyClick(g, Qt.Key_Down, Qt.ControlModifier), 100)
    olc("Ctrl+Yukarı (başa)", lambda: QTest.keyClick(g, Qt.Key_Up, Qt.ControlModifier), 100)
    olc("Ctrl+End (kullanılan alanın sonu)", lambda: QTest.keyClick(g, Qt.Key_End, Qt.ControlModifier), 100)
    g.sec((1, 1))
    olc("kullanilan_aralik()", lambda: sayfa.kullanilan_aralik(), 50, tekrar=5)

    # seçim + durum çubuğu özeti
    olc("Ctrl+A (tümünü seç) + durum çubuğu özeti", lambda: QTest.keyClick(g, Qt.Key_A, Qt.ControlModifier), 100)
    g.sec((1, 1), (SATIR, SUTUN))
    olc("Durum çubuğu özeti, 100.000 hücre seçili", lambda: pencere._ozet_guncelle(), 100, tekrar=3)
    g.sec((1, 1))

    # düzenleme
    olc("Tek hücre düzenleme (yaz + Enter)", lambda: (g.sec((10, 3)), g.hucre_gir(10, 3, "123,5")), 50, tekrar=5)
    olc("Geri al (tek hücre)", lambda: g.geri_al(), 50)
    olc("Yinele (tek hücre)", lambda: g.yinele(), 50)

    # toplu işlemler
    g.sec((1, 1), (SATIR, SUTUN))
    olc("Seçimi sil (100.000 hücre)", lambda: g.secimi_temizle(), 2000)
    olc("Geri al (100.000 hücre silme)", lambda: g.geri_al(), 2000)
    olc("Kopyala (100.000 hücre; TSV + HTML + JSON)", lambda: g.kopyala(), 3000)
    g.sec((SATIR + 10, 1))
    olc("Yapıştır (100.000 hücre)", lambda: g.yapistir(), 3000)
    olc("Geri al (100.000 hücre yapıştırma)", lambda: g.geri_al(), 3000)
    g._pano_isareti_temizle()
    g.sec((1, 1))
    g._satir_sec(1, False)
    olc("Satır ekle (en üste, 100.000 hücre kayar)", lambda: g.satirlari_ekle(), 1000)
    olc("Geri al (satır ekleme)", lambda: g.geri_al(), 1000)
    g._sutun_sec(2, False)
    olc("Sütun otomatik sığdır (5000 hücre)", lambda: g.sutun_otomatik_sigdir(), 500)
    olc("Sütun silme", lambda: g.sutunlari_sil(), 1000)
    olc("Geri al (sütun silme)", lambda: g.geri_al(), 1000)

    yavas = [s for s in SATIRLAR if s[4] == "YAVAŞ"]
    print(f"\nÖzet: {len(SATIRLAR)} ölçüm, hedefi aşan: {len(yavas)}")
    for s in yavas:
        print(f"  YAVAŞ: {s[0]} — {s[1]:.2f} ms (hedef {s[3]} ms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
