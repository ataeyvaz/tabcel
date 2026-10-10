"""Test paketini 3 AYRI süreçte, süreç başına zaman aşımıyla koşar (RAM 7,9 GB: tek süreçte Qt pencereleri birikir;
bir test takılırsa yalnız o grup beklenir ve hangisi olduğu görünür).

Gruplar (dosya adına göre otomatik):
  1. model   — Qt kullanmayan testler (model, formül, io, fonksiyonlar)
  2. arayuz  — Qt/Pencere kullanan testler, A–K arası dosya adları
  3. arayuz2 — Qt/Pencere kullanan testler, L–Z arası dosya adları

Kullanım: .venv\\Scripts\\python araclar/test_parcali.py [zaman_asimi_sn=900] [pytest argümanları…]
Çıkış kodu: tüm gruplar geçtiyse 0."""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
TESTLER = KOK / "testler"
QT_IZI = re.compile(r"PySide6|ui\.window|QApplication")


def gruplar():
    model, ui = [], []
    for f in sorted(TESTLER.glob("test_*.py")):
        (ui if QT_IZI.search(f.read_text(encoding="utf-8", errors="ignore")) else model).append(f.name)
    ortada = next((i for i, n in enumerate(ui) if n[5:] >= "l"), len(ui))
    return [("model", model), ("arayuz", ui[:ortada]), ("arayuz2", ui[ortada:])]


def main() -> int:
    zaman_asimi = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 900
    ek = [a for a in sys.argv[1:] if not a.isdigit()]
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    hata = 0
    for ad, dosyalar in gruplar():
        if not dosyalar:
            continue
        t0 = time.time()
        komut = [sys.executable, "-u", "-m", "pytest", "-q", "-p", "no:cacheprovider", *ek,
                 *[str(TESTLER / d) for d in dosyalar]]
        try:
            p = subprocess.run(komut, cwd=KOK, env=env, timeout=zaman_asimi, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            son = (p.stdout.strip().splitlines() or ["(çıktı yok)"])[-1]
            print(f"[{ad}] {len(dosyalar)} dosya, {time.time() - t0:.0f} sn: {son}")
            if p.returncode != 0:
                hata = 1
                print("\n".join(l for l in p.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))))
        except subprocess.TimeoutExpired:
            print(f"[{ad}] ❌ {zaman_asimi} sn içinde bitmedi (TAKILDI): {len(dosyalar)} dosya")
            hata = 1
    return hata


if __name__ == "__main__":
    sys.exit(main())
