"""pytest sonuçlarını test.md içindeki OTOMATİK bölüme yazar (her test ✅ olumlu / ❌ olumsuz).

    .venv\\Scripts\\python araclar\\test_raporu.py

Yalnızca `<!-- OTOMATIK:BASLA -->` ile `<!-- OTOMATIK:BITIR -->` arası yeniden yazılır;
test.md'nin geri kalanı (süreç, performans, elle test notları) elle bakılır.
"""
import datetime
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

DOSYA_ACIKLAMALARI = {
    "test_iskelet.py": "Proje iskeleti: ad/sürüm sabiti, kaynak klasörü, model/formül paketlerinin Qt'siz olması",
    "test_adres.py": "Adresleme: A1 ⇄ satır/sütun, $ mutlak, aralıklar, sınırlar (XFD, 1.048.576)",
    "test_sayfa.py": "Veri modeli: seyrek sayfa, satır/sütun ekle-sil, geri al yığını, sayfa adı kuralları, gizleme, kullanılan aralık önbelleği",
    "test_girdi.py": "Girdi çözümleyici: yazılan metin → sayı/mantıksal/formül/metin (Türkçe yerel ayar)",
    "test_olcu.py": "Excel ölçü birimleri: karakter/punto ⇄ piksel",
    "test_gosterim.py": "Genel sayı biçimi ve sığdırma (####, bilimsel)",
    "test_pano.py": "Pano: TSV/HTML okuma-yazma, kopyalanan veri, yapıştırma planı",
    "test_izgara.py": "Izgara arayüzü: çizim, gezinme, seçim, düzenleme, boyutlandırma, gizleme, pano, taşan metin, çoklu aralık, artımlı kaydırma",
    "test_pencere.py": "Ana pencere: ad kutusu, formül çubuğu, durum çubuğu, sayfa sekmeleri, yakınlaştırma",
}

BASLA, BITIR = "<!-- OTOMATIK:BASLA -->", "<!-- OTOMATIK:BITIR -->"


class Toplayici:
    def __init__(self):
        self.aciklama = {}      # nodeid → docstring ilk satırı
        self.sonuc = {}         # nodeid → 'gecti' | 'kaldi' | 'atlandi'
        self.sure = 0.0

    def pytest_collection_modifyitems(self, items):
        for it in items:
            doc = (getattr(it.obj, "__doc__", None) or "").strip().split("\n")[0]
            self.aciklama[it.nodeid] = doc

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            self.sonuc[report.nodeid] = {"passed": "gecti", "failed": "kaldi"}.get(report.outcome, "atlandi")
        elif report.outcome == "failed":                 # kurulum/temizlik hatası
            self.sonuc[report.nodeid] = "kaldi"
        elif report.outcome == "skipped":
            self.sonuc[report.nodeid] = "atlandi"
        self.sure += getattr(report, "duration", 0.0)


def okunur(ad: str) -> str:
    ad = re.sub(r"^test_", "", ad)
    return ad.replace("_", " ")


def main() -> int:
    t = Toplayici()
    kod = pytest.main([os.path.join(KOK, "testler"), "-q", "-p", "no:cacheprovider"], plugins=[t])
    dosyalar = {}
    for nodeid, sonuc in t.sonuc.items():
        dosya, _, ad = nodeid.partition("::")
        dosyalar.setdefault(os.path.basename(dosya), []).append((ad, sonuc, t.aciklama.get(nodeid, "")))
    toplam = sum(len(v) for v in dosyalar.values())
    gecen = sum(1 for v in dosyalar.values() for _, s, _ in v if s == "gecti")
    kalan = sum(1 for v in dosyalar.values() for _, s, _ in v if s == "kaldi")

    satirlar = [BASLA, ""]
    bugun = datetime.date.today().isoformat()
    ozet_simge = "✅" if kalan == 0 else "❌"
    satirlar.append(f"**Son çalıştırma: {bugun} — {ozet_simge} {gecen}/{toplam} test geçti, "
                    f"{kalan} olumsuz** (süre ≈ {t.sure:.1f} sn). Bu bölüm `araclar/test_raporu.py` ile üretilir; elle düzenlemeyin.")
    satirlar.append("")
    satirlar.append("| Dosya | Kapsam | Test | ✅ Olumlu | ❌ Olumsuz |")
    satirlar.append("|---|---|---|---|---|")
    for dosya in sorted(dosyalar):
        v = dosyalar[dosya]
        g = sum(1 for _, s, _ in v if s == "gecti")
        k = sum(1 for _, s, _ in v if s == "kaldi")
        satirlar.append(f"| `{dosya}` | {DOSYA_ACIKLAMALARI.get(dosya, '')} | {len(v)} | {g} | {k} |")
    satirlar.append(f"| **Toplam** | | **{toplam}** | **{gecen}** | **{kalan}** |")
    satirlar.append("")
    for dosya in sorted(dosyalar):
        v = dosyalar[dosya]
        g = sum(1 for _, s, _ in v if s == "gecti")
        satirlar.append(f"### `testler/{dosya}` — {g}/{len(v)} ✅")
        satirlar.append(f"*{DOSYA_ACIKLAMALARI.get(dosya, '')}*")
        satirlar.append("")
        for ad, sonuc, doc in v:
            simge = {"gecti": "✅", "kaldi": "❌", "atlandi": "⏭️"}[sonuc]
            gorunen = okunur(ad.split("[")[0]) + (f" `[{ad.split('[', 1)[1]}" if "[" in ad else "")
            satirlar.append(f"- {simge} {gorunen}" + (f" — {doc}" if doc else ""))
        satirlar.append("")
    satirlar.append(BITIR)
    blok = "\n".join(satirlar)

    yol = os.path.join(KOK, "test.md")
    mevcut = open(yol, encoding="utf-8").read() if os.path.exists(yol) else f"{BASLA}\n{BITIR}\n"
    if BASLA in mevcut and BITIR in mevcut:
        i, j = mevcut.index(BASLA), mevcut.index(BITIR) + len(BITIR)
        yeni = mevcut[:i] + blok + mevcut[j:]
    else:
        yeni = mevcut + "\n" + blok + "\n"
    open(yol, "w", encoding="utf-8").write(yeni)
    print(f"test.md güncellendi: {gecen}/{toplam} geçti, {kalan} olumsuz")
    return 0 if kod == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
