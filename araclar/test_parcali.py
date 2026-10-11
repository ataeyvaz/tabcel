"""Test paketini N (varsayılan 5) EŞİT parçada, parça başına AYRI süreçte ve ART ARDA koşar (RAM 7,9 GB: tek süreçte
Qt pencereleri birikir; bir test takılırsa yalnız o parça beklenir ve hangisi olduğu görünür). Parçalar dosya adı
sırasındaki test dosyalarının eşit sayıda dilimleridir.

Kullanım: .venv\Scripts\python araclar/test_parcali.py [zaman_asimi_sn=900] [--parca=5] [--sadece=K] [pytest argümanları…]
  --parca=N   kaç parçaya bölüneceği; --sadece=K  yalnız K. parçayı koş (1..N)
Çıkış kodu: tüm parçalar geçtiyse 0."""
import os
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
TESTLER = KOK / "testler"


def gruplar(n: int = 5):
    dosyalar = [f.name for f in sorted(TESTLER.glob("test_*.py"))]
    boyut, artan = divmod(len(dosyalar), n)
    sonuc, i = [], 0
    for k in range(n):
        j = i + boyut + (1 if k < artan else 0)
        sonuc.append((f"parca{k + 1}/{n}", dosyalar[i:j]))
        i = j
    return sonuc


def main() -> int:
    argv = sys.argv[1:]
    zaman_asimi = int(argv[0]) if argv and argv[0].isdigit() else 900
    parca = next((int(a.split("=")[1]) for a in argv if a.startswith("--parca=")), 5)
    sadece = next((int(a.split("=")[1]) for a in argv if a.startswith("--sadece=")), None)
    ek = [a for a in argv if not a.isdigit() and not a.startswith(("--parca=", "--sadece="))]
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    hata = 0
    for sira, (ad, dosyalar) in enumerate(gruplar(parca), 1):
        if not dosyalar or (sadece is not None and sira != sadece):
            continue
        t0 = time.time()
        komut = [sys.executable, "-u", "-m", "pytest", "-q", "-p", "no:cacheprovider", *ek,
                 *[str(TESTLER / d) for d in dosyalar]]
        try:
            p = subprocess.run(komut, cwd=KOK, env=env, timeout=zaman_asimi, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            son = (p.stdout.strip().splitlines() or ["(çıktı yok)"])[-1]
            print(f"[{ad}] {len(dosyalar)} dosya, {time.time() - t0:.0f} sn: {son}", flush=True)
            if p.returncode != 0:
                hata = 1
                print("\n".join(l for l in p.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))), flush=True)
        except subprocess.TimeoutExpired:
            print(f"[{ad}] ❌ {zaman_asimi} sn içinde bitmedi (TAKILDI): {len(dosyalar)} dosya", flush=True)
            hata = 1
    return hata


if __name__ == "__main__":
    sys.exit(main())
