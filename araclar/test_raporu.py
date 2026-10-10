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
    "test_olay.py": "Olay katmanı (K5): hücre/sonuç/yapı/boyut/sayfa olayları, toplu işlem tek olay",
    "test_pencere_sayfa.py": "Sayfa sekmeleri ve sayfa komutları arayüzde (ekle/sil/yeniden adlandır/taşı, geri al)",
    "test_sayfa_komutlari.py": "Geri alınabilir sayfa komutları (K6)",
    "test_toplu_ve_sonuc.py": "Toplu yazım ve girdi/sonuç ayrımı (K4)",
    "test_formul_ayristir.py": "Formül sözcükleyici ve ayrıştırıcı: öncelik, kesişim, dizi sabiti, hatalar",
    "test_degerlendir.py": "Formül değerlendirici: tür dönüşümleri, dizi yayma, hata yayılımı, 15 basamak",
    "test_yerellestirme.py": "TR ⇄ kanonik çeviri: ayırıcılar, fonksiyon/hata adları, sayfa başvuruları",
    "test_motor.py": "Hesaplayıcı: bağımlılık, yeniden hesaplama, döngü, sayfa işlemleri",
    "test_kaydir.py": "Başvuru kaydırma: kopyala, ekle-sil, taşı ($'lılar, #BAŞV!)",
    "test_fonk_sayisal.py": "115 fonksiyonun sayısal/mantık/istatistik/arama/finans grupları (kural 11: 4+ vaka)",
    "test_fonk_metin_tarih.py": "Metin ve tarih fonksiyonları (1900 sistemi)",
    "test_formul_arayuz.py": "Formül motorunun arayüze bağlanması: hesap, Türkçe görünüm, hatalı formülde düzenleme açık kalır",
    "test_pano_formul.py": "Pano ve formül (6c): kopyada başvuru kayması, kes-yapıştır taşıma, dış formül çevirisi",
    "test_isaretleme.py": "İşaretleme mantığı (Qt'siz): ekleme konumu, renkler, F4, öneriler, ipucu",
    "test_isaretleme_arayuz.py": "İşaretleme modu arayüzde (6d): tıklama/ok, F4, odak kaybı, formül çubuğu, sekmeler arası, Alt+=, öneri listesi, renkli metin",
    "test_dongu_arayuz.py": "Döngüsel başvuru uyarısı (6e): durum çubuğu etiketi, tek uyarı",
    "test_gecmis_sayfa_gecisi.py": "Geri al/yinele sayfa geçişi (6f): yalnız asıl değişikliğin sayfasına",
    "test_sayi_bicimi.py": "Excel sayı biçimi kodu çözümleyici/biçimleyici (Faz 3 çekirdeği): Genel, 0#?, yüzde, bilimsel, kesir, bölümler, renk, tarih/saat, kanonik⇄yerel",
    "test_stil.py": "Stil modeli (3a): Stil/StilYama/havuz, etkin stil önceliği, bicim olayı, BicimDegis, bicim_komutu, ekle-sil + geri al",
    "test_pano_bicim.py": "Pano biçim taşıma (3b): PanoVerisi.stiller, JSON, HTML CSS, yapıştır/kes-taşı, Temizle menüsü, Delete biçimi korur",
    "test_senaryo_butce.py": "Faz 2 gerçek iş senaryosu: aylık bütçe çizelgesi (iki sayfa, kopyalama, ekle-sil, geri al, döngü, taşıma)",
    "test_faz5_altyapi.py": "Faz 5 ortak altyapı (5a): aralık yardımcıları, ek veri depoları + ekle-sil, harmanlama, ağaç kaydırma, ek/ad olayları, menü iskeleti",
    "test_bul.py": "Bul/Değiştir modeli (5b): joker, büyük/küçük harf, formül/değer/not arama, Tümünü Değiştir",
    "test_bul_arayuz.py": "Bul/Değiştir/Git penceresi ve kısayollar (5b)",
    "test_sirala.py": "Sırala (5c): Türkçe harmanlama, karışık tür, çok düzey, renk, gizli satır, formül kayması, geri al",
    "test_sirala_arayuz.py": "Sırala arayüzü (5c): A→Z/Z→A, Sıralama Uyarısı, Özel Sıralama penceresi",
    "test_adlar.py": "Adlandırılmış aralıklar (5d): doğrulama, kapsam, göreli ad, yeniden adlandırma, ekle-sil, .xlsx",
    "test_adlar_arayuz.py": "Ad Tanımla/Ad Yöneticisi/Ad Kutusu/Git (5d)",
    "test_notlar.py": "Notlar (5e): model, komut, ekle-sil, sırala, kes-yapıştır, pano, .xlsx",
    "test_notlar_arayuz.py": "Not arayüzü (5e): üçgen, fare üstü kutu, Shift+F2, menü, temizle",
    "test_filtre.py": "Filtre + ALTTOPLAM (5f): her koşul türü, komut, ALTTOPLAM 1–11/101–111, motor yeniden hesap, .xlsx",
    "test_filtre_arayuz.py": "Filtre arayüzü (5f): düğmeler, panel, özel filtre, özet, Delete",
    "test_dogrulama.py": "Veri doğrulama (5g): model, komut, denetim (tür × işleç, liste, özel), ekle-sil, .xlsx",
    "test_dogrulama_arayuz.py": "Veri doğrulama arayüzü (5g): pencere, giriş denetimi, açılır liste, giriş iletisi",
    "test_kosullu.py": "Koşullu biçim (5h): 12 kural türü, öncelik+dur, ölçek/çubuk, ekle-sil, komut",
    "test_kosullu_arayuz.py": "Koşullu biçim arayüzü (5h): çizim pikselleri, menü, pencereler, yönetici, yazdırma, .xlsx",
    "test_senaryo_stok.py": "Faz 5 gerçek iş senaryosu: stok listesi (ad+DÜŞEYARA, doğrulama, koşullu biçim, sırala, filtre, ALTTOPLAM, not) + stok.xlsx örnek dosya gidiş-dönüşü",
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
