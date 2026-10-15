# Tabcel — Test planı, süreci ve sonuçları

Bu dosya: **neyin nasıl test edildiği** ve **her testin sonucu**. Güncel durum için `surec.md`, kurallar için `CLAUDE.md` (kural 11 fonksiyon test şablonu, kural 12 regresyon kuralı).

**İşaretler:** ✅ olumlu geçti · ❌ olumsuz (geçmedi / hedefi aşmadı) · ⏳ bekliyor (elle ya da başka kişi) · ⏭️ atlandı · ➖ henüz kapsam dışı (ilgili faz gelmedi)

*Son güncelleme: 2026-10-08 (Faz 1 sonu, Faz 2'ye geçmeden önceki denetim).*

---

## 1. Test süreci

**Her iş parçası için sıra (CLAUDE.md):** kod yaz → testleri çalıştır → arayüz değiştiyse ekran görüntüsü al ve incele → `surec.md`'yi güncelle → (kullanıcı isterse) commit. Bir değişiklik mevcut bir testi/özelliği bozarsa devam etmeden kullanıcıya bildirilir; test silinerek/gevşetilerek geçirilmez (kural 12).

**Katmanlar**

| Katman | Ne sınar | Nasıl çalışır | Ortam |
|---|---|---|---|
| A. Birim (model) | `tabcel/model/` (adresleme, sayfa, geri al, girdi, pano, ölçü, gösterim) — Qt'siz | `pytest`, saf Python | her yerde |
| B. Arayüz (ekransız) | `Izgara`, `Pencere`: gezinme, seçim, düzenleme, pano, boyutlandırma… | `pytest` + `QT_QPA_PLATFORM=offscreen`, `QTest` ile tuş/fare | ekran gerekmez; **yazı tipi yok** (metin kutu görünür) |
| C. Gerçek pencere (piksel) | Artımlı çizimin (kaydırma, kısmi boyama) tam çizimle aynı piksel olması | `araclar/cizim_dogrula.py` — ekran görüntüsü alır | **ekran gerekir**, pencere görünür |
| D. Performans | 100.000 hücrede kare süresi, toplu işlemler | `araclar/performans_olcum.py` | gerçek yazı tipi, pencere görünür |
| E. Görsel denetim | Ekran görüntüsünü gözle incelemek | `widget.grab()` → PNG (platformsuz) | gerçek yazı tipleriyle |
| F. Elle / Excel | Excel uyumu, gerçek kullanım | Kullanıcı (Excel web, `Tabcel.bat`) | bu bilgisayarda Excel yok |
| G. Gözden geçirme | Faz sonu mimari/doğruluk denetimi | Opus 5.5 (plan.md → Model kullanımı) | — |

**Komutlar**

| Ne | Komut |
|---|---|
| Tüm otomatik testler | `.venv\Scripts\python -m pytest testler -q` |
| Tek dosya | `.venv\Scripts\python -m pytest testler\test_izgara.py -q` |
| Bu dosyadaki otomatik listeyi yenile | `.venv\Scripts\python araclar\test_raporu.py` |
| Piksel doğrulama (gerçek pencere) | `.venv\Scripts\python araclar\cizim_dogrula.py` |
| 100.000 hücre ölçümü | `.venv\Scripts\python araclar\performans_olcum.py [satır] [sütun]` |

**Yazım kuralları ve tuzaklar (öğrenilenler)**
- Qt'siz paketler (`model/`, `formul/`) Qt içe aktarmaz; bu **ayrı süreçte** sınanır (başka testler Qt'yi yüklemiş olabilir).
- `QMenu.exec` testte çalıştırılmaz (gerçek menü açılıp testi kilitler); menüler `*_olustur` / `baslik_menusu` / `hucre_menusu` yöntemlerinde kurulup incelenir.
- Düzenleyiciye yazı: ilk karakter ızgaraya, gerisi `focusWidget()`'e gönderilir (gerçek davranış). Tab tuşu Qt'de odak gezintisi olarak yakalanır → `event()` içinde ele alınır.
- Ekransız ortamda yazı tipi yok → metinli ekran görüntüsü için `QT_QPA_PLATFORM` ayarsız `grab()`.
- `viewport().grab()` her zaman **tam çizim** yapar; artımlı yolu ölçmek için gerçek akış kullanılır (değer değiştir → `processEvents`).
- Sanal yöntem (örn. `paintEvent`) sınıfa yama yapılarak izlenemez; profil (`cProfile`) ya da gerçek ekran görüntüsü kullanılır.
- Her fonksiyon için (Faz 2+) en az 4 vaka: normal, boş, hata girdisi, metin/sayı karışımı.

---

## 2. Kapsam matrisi (neyi sınıyoruz)

| Alan | Katman | Durum | Not |
|---|---|---|---|
| Adresleme (A1 ⇄ satır/sütun, `$`, `A:C`, `2:5`, XFD/1.048.576 sınırı) | A | ✅ | 26 test, tüm 16.384 sütun gidiş-dönüş |
| Seyrek sayfa, `Hucre`, kullanılan aralık (+önbellek), `aralikta` | A | ✅ | rastgele işlemlerle önbellek doğrulaması dahil |
| Satır/sütun ekle-sil + boyut/gizleme kayması, geri al/yinele, grup, yığın sınırı | A | ✅ | sayfa sonu itme reddi (K2) dahil; **sayfa işlemlerinin (ekle/sil/taşı/ad) geri alınması yok** (K6) |
| Sayfa adı kuralları, sayfa sıralama, çalışma kitabı | A | ✅ | Excel kuralları (≤31, `\ / ? * [ ] :`) |
| Girdi çözümleme (sayı/mantıksal/formül/metin, TR yerel ayar) | A | ✅ | `1.5` tarih çözümü Faz 3 |
| Ölçü birimleri (karakter/punto ⇄ px) | A | ✅ | yaklaşık; kesin sınama Faz 4 |
| Genel sayı biçimi, sığdırma (`####`, bilimsel, yarım değer yuvarlama) | A | ✅ | eşikler tahmin → Excel web (§8b-11) |
| Pano: TSV/HTML yaz-çöz, kopyalanan veri, yapıştırma planı, JSON | A | ✅ | |
| Izgara gezinme (ok, Ctrl+ok, Home/End, PageUp/Down, Tab/Enter, Ctrl+A…) | B | ✅ | gizli satır/sütun atlama dahil |
| Seçim (tek/aralık/satır/sütun/tümü, çoklu aralık, sinyaller) | B | ✅ | |
| Düzenleme (yazarak, F2, çift tık, Esc, Alt+Enter, onay yönleri) | B | ✅ | |
| Boyutlandırma (sürükle, çift tık sığdır, çoklu), ekle/sil/gizle/göster, başlık menüsü | B | ✅ | |
| Pano arayüzü (Ctrl+C/X/V, alternatif kısayollar, karınca çerçevesi, sayfalar arası kes) | B | ✅ | kes + yapı değişikliği/düzenleme/geri al işareti iptal eder (K3) |
| Taşan metin, `####`, sayı kısaltma | B | ✅ | `_yerlesim` testleri |
| Artımlı kaydırma (piksel kaydırma geometrisi, yakınlaştırma çarpanı, gizli satır) | B | ✅ | |
| Ana pencere: ad kutusu, formül çubuğu, durum çubuğu, özet, sekmeler, yakınlaştırma | B | ✅ | |
| Artımlı çizim = tam çizim (piksel eşitliği) | C | ✅ (1 px tolerans) | bkz. §5 |
| 100.000 hücre performansı | D | ❌ kısmen | bkz. §4 — 6 ölçüm hedefin üstünde |
| Görsel görünüm (şerit, ızgara, seçim, karınca, taşma) | E | ✅ | ekran görüntüleriyle incelendi |
| Fare sürüklemede kenarda otomatik kaydırma (sürekli) | B | ➖ | tek adım sınanıyor; zamanlayıcılı sürekli kaydırma yok |
| Dosya menüsü, aç/kaydet, .xlsx/.csv | — | ➖ | Faz 4 |
| Formül motoru, yerelleştirme, fonksiyon kütüphanesi, işaretleme modu, döngü uyarısı | A/B | ✅ | bkz. §9 (Faz 2) |
| Biçimlendirme, sayı biçimleri, birleştirme, dondurma | — | ➖ | Faz 3 |
| Windows başlık çubuğu rengi (DWM) | F | ⏳ | yalnız Win11'de görünür; kullanıcı gözle doğrular |
| Gerçek kullanım (`Tabcel.bat`) | F | ⏳ | kullanıcı elle deneyecek |
| Excel uyumu (§8b listesi: 11 madde) | F | ⏳ | kullanıcı Excel web'de doğrulayacak (`surec.md`) |

---

## 3. Otomatik testler (pytest) — her testin sonucu

<!-- OTOMATIK:BASLA -->

**Son çalıştırma: 2026-10-10 — ✅ 2518/2518 test geçti, 0 olumsuz** (süre ≈ 201.0 sn). Bu bölüm `araclar/test_raporu.py` ile üretilir; elle düzenlemeyin.

| Dosya | Kapsam | Test | ✅ Olumlu | ❌ Olumsuz |
|---|---|---|---|---|
| `test_adlar.py` | Adlandırılmış aralıklar (5d): doğrulama, kapsam, göreli ad, yeniden adlandırma, ekle-sil, .xlsx | 74 | 74 | 0 |
| `test_adlar_arayuz.py` | Ad Tanımla/Ad Yöneticisi/Ad Kutusu/Git (5d) | 17 | 17 | 0 |
| `test_adres.py` | Adresleme: A1 ⇄ satır/sütun, $ mutlak, aralıklar, sınırlar (XFD, 1.048.576) | 26 | 26 | 0 |
| `test_akilli_giris.py` |  | 92 | 92 | 0 |
| `test_arka_plan.py` |  | 7 | 7 | 0 |
| `test_bicim_boyaci.py` |  | 14 | 14 | 0 |
| `test_bicim_cubugu.py` |  | 23 | 23 | 0 |
| `test_bicim_islem.py` |  | 23 | 23 | 0 |
| `test_bicim_kodlari.py` |  | 6 | 6 | 0 |
| `test_bicim_penceresi.py` |  | 12 | 12 | 0 |
| `test_birlesim.py` |  | 16 | 16 | 0 |
| `test_birlesim_arayuz.py` |  | 17 | 17 | 0 |
| `test_birlesim_pano.py` |  | 12 | 12 | 0 |
| `test_bul.py` | Bul/Değiştir modeli (5b): joker, büyük/küçük harf, formül/değer/not arama, Tümünü Değiştir | 29 | 29 | 0 |
| `test_bul_arayuz.py` | Bul/Değiştir/Git penceresi ve kısayollar (5b) | 12 | 12 | 0 |
| `test_csv_io.py` |  | 21 | 21 | 0 |
| `test_csv_menu.py` |  | 8 | 8 | 0 |
| `test_degerlendir.py` | Formül değerlendirici: tür dönüşümleri, dizi yayma, hata yayılımı, 15 basamak | 46 | 46 | 0 |
| `test_dogrulama.py` | Veri doğrulama (5g): model, komut, denetim (tür × işleç, liste, özel), ekle-sil, .xlsx | 45 | 45 | 0 |
| `test_dogrulama_arayuz.py` | Veri doğrulama arayüzü (5g): pencere, giriş denetimi, açılır liste, giriş iletisi | 21 | 21 | 0 |
| `test_doldur.py` |  | 29 | 29 | 0 |
| `test_doldur_arayuz.py` |  | 17 | 17 | 0 |
| `test_dondurma.py` |  | 22 | 22 | 0 |
| `test_dongu_arayuz.py` | Döngüsel başvuru uyarısı (6e): durum çubuğu etiketi, tek uyarı | 5 | 5 | 0 |
| `test_dosya_menusu.py` |  | 17 | 17 | 0 |
| `test_faz5_altyapi.py` | Faz 5 ortak altyapı (5a): aralık yardımcıları, ek veri depoları + ekle-sil, harmanlama, ağaç kaydırma, ek/ad olayları, menü iskeleti | 65 | 65 | 0 |
| `test_filtre.py` | Filtre + ALTTOPLAM (5f): her koşul türü, komut, ALTTOPLAM 1–11/101–111, motor yeniden hesap, .xlsx | 60 | 60 | 0 |
| `test_filtre_arayuz.py` | Filtre arayüzü (5f): düğmeler, panel, özel filtre, özet, Delete | 15 | 15 | 0 |
| `test_fonk_metin_tarih.py` | Metin ve tarih fonksiyonları (1900 sistemi) | 356 | 356 | 0 |
| `test_fonk_sayisal.py` | 115 fonksiyonun sayısal/mantık/istatistik/arama/finans grupları (kural 11: 4+ vaka) | 306 | 306 | 0 |
| `test_formul_arayuz.py` | Formül motorunun arayüze bağlanması: hesap, Türkçe görünüm, hatalı formülde düzenleme açık kalır | 7 | 7 | 0 |
| `test_formul_ayristir.py` | Formül sözcükleyici ve ayrıştırıcı: öncelik, kesişim, dizi sabiti, hatalar | 37 | 37 | 0 |
| `test_gecmis_sayfa_gecisi.py` | Geri al/yinele sayfa geçişi (6f): yalnız asıl değişikliğin sayfasına | 4 | 4 | 0 |
| `test_girdi.py` | Girdi çözümleyici: yazılan metin → sayı/mantıksal/formül/metin (Türkçe yerel ayar) | 42 | 42 | 0 |
| `test_gosterim.py` | Genel sayı biçimi ve sığdırma (####, bilimsel) | 8 | 8 | 0 |
| `test_isaretleme.py` | İşaretleme mantığı (Qt'siz): ekleme konumu, renkler, F4, öneriler, ipucu | 27 | 27 | 0 |
| `test_isaretleme_arayuz.py` | İşaretleme modu arayüzde (6d): tıklama/ok, F4, odak kaybı, formül çubuğu, sekmeler arası, Alt+=, öneri listesi, renkli metin | 28 | 28 | 0 |
| `test_iskelet.py` | Proje iskeleti: ad/sürüm sabiti, kaynak klasörü, model/formül paketlerinin Qt'siz olması | 3 | 3 | 0 |
| `test_izgara.py` | Izgara arayüzü: çizim, gezinme, seçim, düzenleme, boyutlandırma, gizleme, pano, taşan metin, çoklu aralık, artımlı kaydırma | 108 | 108 | 0 |
| `test_izgara_stil.py` |  | 23 | 23 | 0 |
| `test_kaydir.py` | Başvuru kaydırma: kopyala, ekle-sil, taşı ($'lılar, #BAŞV!) | 33 | 33 | 0 |
| `test_kaydir_metin.py` |  | 21 | 21 | 0 |
| `test_kosullu.py` | Koşullu biçim (5h): 12 kural türü, öncelik+dur, ölçek/çubuk, ekle-sil, komut | 41 | 41 | 0 |
| `test_kosullu_arayuz.py` | Koşullu biçim arayüzü (5h): çizim pikselleri, menü, pencereler, yönetici, yazdırma, .xlsx | 26 | 26 | 0 |
| `test_kurtarma.py` |  | 15 | 15 | 0 |
| `test_motor.py` | Hesaplayıcı: bağımlılık, yeniden hesaplama, döngü, sayfa işlemleri | 20 | 20 | 0 |
| `test_notlar.py` | Notlar (5e): model, komut, ekle-sil, sırala, kes-yapıştır, pano, .xlsx | 26 | 26 | 0 |
| `test_notlar_arayuz.py` | Not arayüzü (5e): üçgen, fare üstü kutu, Shift+F2, menü, temizle | 12 | 12 | 0 |
| `test_olay.py` | Olay katmanı (K5): hücre/sonuç/yapı/boyut/sayfa olayları, toplu işlem tek olay | 18 | 18 | 0 |
| `test_olcu.py` | Excel ölçü birimleri: karakter/punto ⇄ piksel | 3 | 3 | 0 |
| `test_opus_faz2.py` |  | 11 | 11 | 0 |
| `test_opus_faz3.py` |  | 54 | 54 | 0 |
| `test_opus_faz4.py` |  | 36 | 36 | 0 |
| `test_pano.py` | Pano: TSV/HTML okuma-yazma, kopyalanan veri, yapıştırma planı | 25 | 25 | 0 |
| `test_pano_bicim.py` | Pano biçim taşıma (3b): PanoVerisi.stiller, JSON, HTML CSS, yapıştır/kes-taşı, Temizle menüsü, Delete biçimi korur | 16 | 16 | 0 |
| `test_pano_formul.py` | Pano ve formül (6c): kopyada başvuru kayması, kes-yapıştır taşıma, dış formül çevirisi | 6 | 6 | 0 |
| `test_pencere.py` | Ana pencere: ad kutusu, formül çubuğu, durum çubuğu, sayfa sekmeleri, yakınlaştırma | 21 | 21 | 0 |
| `test_pencere_sayfa.py` | Sayfa sekmeleri ve sayfa komutları arayüzde (ekle/sil/yeniden adlandır/taşı, geri al) | 16 | 16 | 0 |
| `test_sayfa.py` | Veri modeli: seyrek sayfa, satır/sütun ekle-sil, geri al yığını, sayfa adı kuralları, gizleme, kullanılan aralık önbelleği | 33 | 33 | 0 |
| `test_sayfa_komutlari.py` | Geri alınabilir sayfa komutları (K6) | 7 | 7 | 0 |
| `test_sayfalama.py` |  | 19 | 19 | 0 |
| `test_sayi_bicimi.py` | Excel sayı biçimi kodu çözümleyici/biçimleyici (Faz 3 çekirdeği): Genel, 0#?, yüzde, bilimsel, kesir, bölümler, renk, tarih/saat, kanonik⇄yerel | 179 | 179 | 0 |
| `test_senaryo_bicimli.py` |  | 8 | 8 | 0 |
| `test_senaryo_butce.py` | Faz 2 gerçek iş senaryosu: aylık bütçe çizelgesi (iki sayfa, kopyalama, ekle-sil, geri al, döngü, taşıma) | 8 | 8 | 0 |
| `test_senaryo_stok.py` | Faz 5 gerçek iş senaryosu: stok listesi (ad+DÜŞEYARA, doğrulama, koşullu biçim, sırala, filtre, ALTTOPLAM, not) + stok.xlsx örnek dosya gidiş-dönüşü | 7 | 7 | 0 |
| `test_sirala.py` | Sırala (5c): Türkçe harmanlama, karışık tür, çok düzey, renk, gizli satır, formül kayması, geri al | 28 | 28 | 0 |
| `test_sirala_arayuz.py` | Sırala arayüzü (5c): A→Z/Z→A, Sıralama Uyarısı, Özel Sıralama penceresi | 12 | 12 | 0 |
| `test_stil.py` | Stil modeli (3a): Stil/StilYama/havuz, etkin stil önceliği, bicim olayı, BicimDegis, bicim_komutu, ekle-sil + geri al | 26 | 26 | 0 |
| `test_toplu_ve_sonuc.py` | Toplu yazım ve girdi/sonuç ayrımı (K4) | 12 | 12 | 0 |
| `test_xlsx_io.py` |  | 17 | 17 | 0 |
| `test_xlsx_ornekler.py` |  | 9 | 9 | 0 |
| `test_yazdir.py` |  | 16 | 16 | 0 |
| `test_yerellestirme.py` | TR ⇄ kanonik çeviri: ayırıcılar, fonksiyon/hata adları, sayfa başvuruları | 37 | 37 | 0 |
| **Toplam** | | **2518** | **2518** | **0** |

### `testler/test_adlar.py` — 74/74 ✅
*Adlandırılmış aralıklar (5d): doğrulama, kapsam, göreli ad, yeniden adlandırma, ekle-sil, .xlsx*

- ✅ TestDogrulama::test gecerli `[Fiyat]
- ✅ TestDogrulama::test gecerli `[KDV.Oran\u0131]
- ✅ TestDogrulama::test gecerli `[_x]
- ✅ TestDogrulama::test gecerli `[\xc7eyrek_1]
- ✅ TestDogrulama::test gecerli `[\\x]
- ✅ TestDogrulama::test gecerli `[XFE1]
- ✅ TestDogrulama::test gecerli `[a1b]
- ✅ TestDogrulama::test gecerli `[Rate]
- ✅ TestDogrulama::test gecersiz `[]
- ✅ TestDogrulama::test gecersiz `[A1]
- ✅ TestDogrulama::test gecersiz `[XFD1048576]
- ✅ TestDogrulama::test gecersiz `[KDV2]
- ✅ TestDogrulama::test gecersiz `[R]
- ✅ TestDogrulama::test gecersiz `[C]
- ✅ TestDogrulama::test gecersiz `[r]
- ✅ TestDogrulama::test gecersiz `[c]
- ✅ TestDogrulama::test gecersiz `[R1C1]
- ✅ TestDogrulama::test gecersiz `[R5]
- ✅ TestDogrulama::test gecersiz `[C5]
- ✅ TestDogrulama::test gecersiz `[RC]
- ✅ TestDogrulama::test gecersiz `[Toplam 1]
- ✅ TestDogrulama::test gecersiz `[1x]
- ✅ TestDogrulama::test gecersiz `[a-b]
- ✅ TestDogrulama::test gecersiz `[DO\u011eRU]
- ✅ TestDogrulama::test gecersiz `[YANLI\u015e]
- ✅ TestDogrulama::test gecersiz `[true]
- ✅ TestDogrulama::test gecersiz `[False]
- ✅ TestDogrulama::test gecersiz `[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]
- ✅ TestDogrulama::test gecersiz `[ x]
- ✅ TestDogrulama::test 255 karakter gecerli
- ✅ TestDogrulama::test kontrol yinelenen buyuk kucuk duyarsiz
- ✅ TestDogrulama::test kontrol kapsam yok ve formul yok
- ✅ TestDegerlendirme::test aralik adi
- ✅ TestDegerlendirme::test sabit ad
- ✅ TestDegerlendirme::test buyuk kucuk harf duyarsiz
- ✅ TestDegerlendirme::test turkce buyuk i
- ✅ TestDegerlendirme::test tanimsiz ad hata
- ✅ TestDegerlendirme::test ad sonradan tanimlaninca hesaplanir
- ✅ TestDegerlendirme::test silinen ad hata formul metni korunur
- ✅ TestDegerlendirme::test degisen hucre yeniden hesaplanir
- ✅ TestDegerlendirme::test ad formulu degisince yeniden hesaplanir
- ✅ TestDegerlendirme::test baska sayfa adi
- ✅ TestDegerlendirme::test ad baska adi kullanir
- ✅ TestDegerlendirme::test ozyinelemeli ad
- ✅ TestDegerlendirme::test kendine basvuran ad
- ✅ TestDegerlendirme::test hucre dongusu ad uzerinden
- ✅ TestDegerlendirme::test hata degeri ad
- ✅ TestDegerlendirme::test metin ve bos
- ✅ TestDegerlendirme::test bozuk ad formulu
- ✅ TestKapsam::test sayfa kapsami kitabi golgeler
- ✅ TestKapsam::test sayfa kapsami baska sayfada gorunmez
- ✅ TestKapsam::test ayni ad iki sayfada
- ✅ TestKapsam::test sayfa silinince ad kalir geri alinca doner
- ✅ TestGoreli::test goreli ad a1e gore — Ad A1'e göre saklanır: `=[1]!A1` (göreli) hücrenin kendi konumundan aynı kayma uygulanır.
- ✅ TestGoreli::test goreli ad motor bagimliligi
- ✅ TestGoreli::test goreli ad baska hucrede
- ✅ TestKomut::test ekle geri al yinele
- ✅ TestKomut::test duzenle
- ✅ TestKomut::test sil
- ✅ TestKomut::test yeniden adlandir formulleri duzeltir
- ✅ TestKomut::test yeniden adlandir golgelenen sayfaya dokunmaz
- ✅ TestKomut::test yeniden adlandir yalniz buyuk kucuk formul degismez
- ✅ TestKomut::test adi degistir metin ve baska sozcuk
- ✅ TestKomut::test yinelenen ad komutu kurulamaz
- ✅ TestEkleSilTasi::test satir ekle ad formulunu duzeltir
- ✅ TestEkleSilTasi::test satir sil aralik kuculur ve tamamen silinen ref
- ✅ TestEkleSilTasi::test kes yapistir adi kaydirir
- ✅ TestEkleSilTasi::test kes yapistir kismen tasinan ad degismez
- ✅ TestEkleSilTasi::test kopyala yapistir ad etkilemez
- ✅ TestPerformans::test ad eklemek 50000 formullu kitapta hizli
- ✅ TestXlsx::test gidis donus
- ✅ TestXlsx::test dosya icinde ingilizce metin
- ✅ TestXlsx::test cevrilemeyen ad atlanir ve raporlanir
- ✅ TestXlsx::test yazdirma alani ad sayilmaz

### `testler/test_adlar_arayuz.py` — 17/17 ✅
*Ad Tanımla/Ad Yöneticisi/Ad Kutusu/Git (5d)*

- ✅ ad kutusu secimi adlandirir ve geri alinir
- ✅ ad kutusu ada gider
- ✅ ad kutusu baska sayfadaki ada gider
- ✅ ad kutusu gecersiz ad uyarir
- ✅ git mevcut olmayan ad tanimlamaz
- ✅ sabit ad aralik degil uyarir
- ✅ git penceresi adlari listeler
- ✅ tamamlayici adlari gunceller
- ✅ ad tanimla penceresi secimden
- ✅ ad tanimla penceresi hatalar
- ✅ ad tanimla turkce formul ve sayfaya baglama
- ✅ ad tanimla pencere komutu ve duzenleme
- ✅ ad yoneticisi listeler ve siler
- ✅ ad yoneticisi kisayolu acar
- ✅ formul oneri listesi tanimli adlari icerir
- ✅ duzenleyici ad onerisi kabul parantez eklemez
- ✅ ad formulde otomatik cozulur ve ad silinince hata

### `testler/test_adres.py` — 26/26 ✅
*Adresleme: A1 ⇄ satır/sütun, $ mutlak, aralıklar, sınırlar (XFD, 1.048.576)*

- ✅ sutun cevrimi `[1-A]
- ✅ sutun cevrimi `[26-Z]
- ✅ sutun cevrimi `[27-AA]
- ✅ sutun cevrimi `[52-AZ]
- ✅ sutun cevrimi `[53-BA]
- ✅ sutun cevrimi `[702-ZZ]
- ✅ sutun cevrimi `[703-AAA]
- ✅ sutun cevrimi `[16384-XFD]
- ✅ tum sutunlar gidis donus
- ✅ kotu sutun `[XFE]
- ✅ kotu sutun `[]
- ✅ kotu sutun `[A1]
- ✅ kotu sutun `[\u015e]
- ✅ kotu sutun `[AAAA]
- ✅ sutun sinir disi
- ✅ hucre coz ve yaz
- ✅ hucre sinirlari
- ✅ aralik normalize
- ✅ tam sutun ve satir
- ✅ aralik yaz
- ✅ kotu aralik `[A1:B2:C3]
- ✅ kotu aralik `[A1:]
- ✅ kotu aralik `[:B2]
- ✅ kotu aralik `[A:5]
- ✅ kotu aralik `[1:1048577]
- ✅ aralik icinde

### `testler/test_akilli_giris.py` — 92/92 ✅
**

- ✅ yuzde `[15%-0.15-0%]
- ✅ yuzde `[%15-0.15-0%]
- ✅ yuzde `[15,5%-0.155-0.0%]
- ✅ yuzde `[0%-0.0-0%]
- ✅ yuzde `[-5%--0.05-0%]
- ✅ yuzde `[1.234%-12.34-0%]
- ✅ para `[\u20ba100-100.0-"\u20ba"#,##0]
- ✅ para `[100 \u20ba-100.0-"\u20ba"#,##0]
- ✅ para `[$1.234,50-1234.5-"$"#,##0.00]
- ✅ para `[\u20ac5-5.0-#,##0 "\u20ac"]
- ✅ para `[-\u20ba100--100.0-"\u20ba"#,##0]
- ✅ para `[100\u20ac-100.0-#,##0 "\u20ac"]
- ✅ kesir `[1 1/2-1.5-# ?/?]
- ✅ kesir `[0 3/4-0.75-# ?/?]
- ✅ kesir `[2 1/10-2.1-# ??/??]
- ✅ kesir `[-1 1/2--1.5-# ?/?]
- ✅ kesir sifira bolme metin
- ✅ saat `[14:30-0.6041666666666666-hh:mm]
- ✅ saat `[14:30:15-0.6043402777777778-hh:mm:ss]
- ✅ saat `[2:30 \xd6S-0.6041666666666666-h:mm AM/PM]
- ✅ saat `[12:00 AM-0.0-h:mm AM/PM]
- ✅ saat `[12:30 PM-0.5208333333333334-h:mm AM/PM]
- ✅ saat `[0:00-0.0-hh:mm]
- ✅ gecersiz saat metin `[25:00]
- ✅ gecersiz saat metin `[12:60]
- ✅ gecersiz saat metin `[13:00 PM]
- ✅ gecersiz saat metin `[14:30:75]
- ✅ gecersiz saat metin `[1:2]
- ✅ tarih `[12.10.2026-46307.0-d.mm.yyyy]
- ✅ tarih `[12/10/2026-46307.0-d.mm.yyyy]
- ✅ tarih `[12-10-2026-46307.0-d.mm.yyyy]
- ✅ tarih `[12.10.26-46307.0-d.mm.yyyy]
- ✅ tarih `[12.10-46307.0-d mmmm]
- ✅ tarih `[12 Ekim 2026-46307.0-d mmmm yyyy]
- ✅ tarih `[12 Eki 2026-46307.0-dd mmm yyyy]
- ✅ tarih `[12 Eki-46307.0-d mmm]
- ✅ tarih `[12 ekim-46307.0-d mmmm]
- ✅ tarih `[29.2.2024-45351.0-d.mm.yyyy]
- ✅ tarih `[1.1.1900-1.0-d.mm.yyyy]
- ✅ tarih `[1.5-46143.0-d mmmm]
- ✅ iki haneli yil penceresi
- ✅ gecersiz tarih metin kalir `[31.2.2026]
- ✅ gecersiz tarih metin kalir `[29.2.2025]
- ✅ gecersiz tarih metin kalir `[32.1.2026]
- ✅ gecersiz tarih metin kalir `[12.13.2026]
- ✅ gecersiz tarih metin kalir `[0.5.2026]
- ✅ gecersiz tarih metin kalir `[12.10/2026]
- ✅ gecersiz tarih metin kalir `[1.50]
- ✅ gecersiz tarih metin kalir `[12.34.56]
- ✅ gecersiz tarih metin kalir `[1.1.1899]
- ✅ tarih ve saat
- ✅ duz sayi ve bilimsel
- ✅ diger kurallar degismez
- ✅ girdi coz degismedi dis yapistirma icin
- ✅ duzenleme metni bicimli `[46307.0-d.mm.yyyy-12.10.2026]
- ✅ duzenleme metni bicimli `[46307.0-d mmmm yyyy dddd-12.10.2026]
- ✅ duzenleme metni bicimli `[46307.604166666664-d.mm.yyyy hh:mm-12.10.2026 14:30:00]
- ✅ duzenleme metni bicimli `[0.6041666666666666-hh:mm-14:30:00]
- ✅ duzenleme metni bicimli `[0.15-0%-15%]
- ✅ duzenleme metni bicimli `[0.155-0.0%-15,5%]
- ✅ duzenleme metni bicimsiz ve diger
- ✅ hucreye tarih yazinca deger ve bicim
- ✅ yuzde para saat yaziminda bicim onerilir
- ✅ dolu bicimli hucrede bicim degismez
- ✅ metin bicimli hucre her girdiyi metin tutar
- ✅ duzenleme acilinca tarih gosterilir ve ayni deger kalir
- ✅ formul ve duz sayi etkilenmez
- ✅ tarih hucresi ekranda bicimli gorunur
- ✅ metin tarihi aritmetikte sayiya cevrilir
- ✅ text `[=TEXT(1234.5,"#.##0,00")-1.234,50-None]
- ✅ text `[=TEXT(46307,"gg.aa.yyyy")-12.10.2026-None]
- ✅ text `[=TEXT(0.256,"0,0%")-25,6%-None]
- ✅ text `[=TEXT(12,"000")-012-None]
- ✅ text `[=TEXT(46307,"d mmmm yyyy dddd")-12 Ekim 2026 Pazartesi-None]
- ✅ text `[=TEXT(0.5,"hh:mm")-12:00-None]
- ✅ text `[=TEXT(1234.5,"Genel")-1234,5-None]
- ✅ text `[=TEXT(-5,"0,00")--5,00-None]
- ✅ text `[=TEXT(1234.5,"#.##0,00 ""TL""")-1.234,50 TL-None]
- ✅ text `[=TEXT(A1,"0,00")-0,00-veri9]
- ✅ text `[=TEXT(5,"")--None]
- ✅ text `[=TEXT(,"0")-0-None]
- ✅ text `[=TEXT(#N/A,"0")-beklenen12-None]
- ✅ text `[=TEXT(1/0,"0")-beklenen13-None]
- ✅ text `[=TEXT(1,"[x")-beklenen14-None]
- ✅ text `[=TEXT(A1,"0")-beklenen15-veri15]
- ✅ text `[=TEXT("abc","0")-abc-None]
- ✅ text `[=TEXT("12","0,0")-12,0-None]
- ✅ text `[=TEXT(TRUE,"0")-DO\u011eRU-None]
- ✅ text `[=TEXT("12.10.2026","gg.aa.yy")-12.10.26-None]
- ✅ text `[=TEXT(A1,"0,0")-10,0-veri20]
- ✅ text `[=TEXT(-1,"gg.aa.yyyy")-beklenen21-None]
- ✅ text dizi yayilir

### `testler/test_arka_plan.py` — 7/7 ✅
**

- ✅ sonuc ve ayri is parcacigi
- ✅ istisna ana is parcacigina aktarilir
- ✅ olay dongusu calismaya devam eder — İşlem sürerken ana iş parçacığının zamanlayıcıları işler (arayüz donmaz).
- ✅ uzun islemde pencere kilitlenir ve acilir
- ✅ kisa islemde pencere hic kilitlenmez
- ✅ hata sonrasi pencere acik kalir
- ✅ buyuk dosya arka planda acilir ve kaydedilir — Gerçek akış: 20.000 hücre kaydet → aç, ana iş parçacığı olay işler.

### `testler/test_bicim_boyaci.py` — 14/14 ✅
**

- ✅ tek hucre kaynak tek hucre hedef
- ✅ tek hucre kaynak buyuk hedefe yayilir
- ✅ cok hucreli kaynak tek hucreye tum deseni boyar
- ✅ desen buyuk hedefe yinelenir ve kirpilir
- ✅ hedef sayfa sonunda kirpilir
- ✅ satir stili kaynak hucrede okunur
- ✅ cok buyuk hedef reddedilir
- ✅ tek tik bir kez boyar
- ✅ surukleyerek aralik boyar tek geri al
- ✅ cift tik kalici esc bitirir
- ✅ dugmeye yeniden basmak kapatir
- ✅ coklu secimde alinamaz
- ✅ kaynak kendine boyanirsa komut eklenmez
- ✅ sayfa degisince boyaci biter

### `testler/test_bicim_cubugu.py` — 23/23 ✅
**

- ✅ cubuk pencerede ve sozlesme
- ✅ kalin italik alti cizili tum secime
- ✅ dugme etkin hucreye bakar — Etkin hücre kalın, diğerleri değil: düğme kapatır ve hepsini kalın-dışı yapar (Excel gibi).
- ✅ cubuk etkin hucreyi yansitir
- ✅ geri al cubugu gunceller
- ✅ tek geri al adimi
- ✅ yazi boyutu kutusu ve buyut kucult
- ✅ yazi tipi secimi
- ✅ yazi ve dolgu rengi
- ✅ renk paleti menusu var
- ✅ kenarlik menusu
- ✅ kenarlik tam sutunda
- ✅ hizalama dugmeleri
- ✅ metni kaydir ve girinti
- ✅ sayi dugmeleri
- ✅ ondalik genel bicimde gorunen ondaliktan baslar
- ✅ sayi bicimi listesi
- ✅ sayi bicimi ekranda gorunur
- ✅ kisayollar
- ✅ biçim formulleri ve icerigi degistirmez
- ✅ duzenleme sirasinda odak calinmaz
- ✅ cubuk baska sayfada
- ✅ ekran goruntusu boyutlari — Çubuk 1100 px pencerede tek satırda sığar.

### `testler/test_bicim_islem.py` — 23/23 ✅
**

- ✅ boyut adimlari
- ✅ boyut coz
- ✅ acma kapama dugmeleri `[kalin_yamasi-kalin-True-False]
- ✅ acma kapama dugmeleri `[italik_yamasi-italik-True-False]
- ✅ acma kapama dugmeleri `[ustu_cizili_yamasi-ustu_cizili-True-False]
- ✅ acma kapama dugmeleri `[kaydir_yamasi-kaydir-True-False]
- ✅ alti cizili
- ✅ yatay ve dikey hiza tekrar basinca geri doner
- ✅ girinti
- ✅ sayi dugmeleri kodlari
- ✅ ondalik artir azalt
- ✅ ondalik bozuk kod none
- ✅ hazir adi
- ✅ dis kenarlik yalniz cerceve
- ✅ tek hucrede dis kenarlik dort kenar
- ✅ kalin dis
- ✅ tum kenarliklar ic cizgiler dahil
- ✅ tek kenar secenekleri
- ✅ kenarlik yok hepsini kaldirir diger stili korur
- ✅ kenarlik yok sinir hucrelerde dis kenarligi da siler
- ✅ coklu secimde her bolge kendi cercevesi
- ✅ kenarlik grubu tek adimda geri alinir
- ✅ gecersiz secenek

### `testler/test_bicim_kodlari.py` — 6/6 ✅
**

- ✅ kod olustur temel
- ✅ hazir kodlar kategoriye gidis donus
- ✅ bilinmeyen kod ozel
- ✅ muhasebe ondalik
- ✅ ozel kod yerel yazim
- ✅ onizleme

### `testler/test_bicim_penceresi.py` — 12/12 ✅
**

- ✅ baslangic degerleri
- ✅ yalniz degisen alanlar
- ✅ alanlar toplu
- ✅ sayi sekmesi kategoriler
- ✅ ozel kod yerel yazilir kanonik saklanir
- ✅ gecersiz ozel kod uyarir kapanmaz
- ✅ gecersiz boyut uyarir
- ✅ kenarlik plani pencereden
- ✅ ctrl1 uctan uca
- ✅ iptal degistirmez
- ✅ coklu secimde dokunulmayan alan korunur
- ✅ pencere dugmesi ve formul degismez

### `testler/test_birlesim.py` — 16/16 ✅
**

- ✅ yaz ve sorgula
- ✅ gecersiz birlesimler
- ✅ olay birlesim bilgisi
- ✅ birlestir icerik siler sol ust kalir
- ✅ veri kaybi yalniz sol ust doluysa yok
- ✅ birlestir ve ortala stil
- ✅ satirlar boyunca
- ✅ tek hucre ve cozulecek yoksa none
- ✅ coz
- ✅ eski birlesimi kapsayan yeni birlesim
- ✅ kismen kesen ve coklu aralik reddedilir
- ✅ birlestirme formul motorunu gunceller
- ✅ satir ekle birlesimi kaydirir buyutur
- ✅ satir sil birlesimi kucultur ya da kaldirir
- ✅ sutun ekle sil birlesimi
- ✅ birlesim degis komutu geri al

### `testler/test_birlesim_arayuz.py` — 17/17 ✅
**

- ✅ tiklama birlesimi secer etkin sol ust
- ✅ secim birlesimi kesiyorsa genisler
- ✅ ok tuslari birlesimi tek hucre gibi gezer
- ✅ shift ok birlesimi atlamaz kapsar
- ✅ enter birlesimden cikar
- ✅ cizim ic cizgiler gorunmez
- ✅ metin birlesimde ortalanir
- ✅ dolgu birlesimin tamamini boyar
- ✅ cizim birlesim kismen gorunurken
- ✅ duzenleme birlesim alaninda
- ✅ cubuk dugmesi ve menu
- ✅ veri kaybi uyarisi
- ✅ uyari gerektirmeyen birlestirme sormaz
- ✅ coklu secim birlestirmez
- ✅ satir ekle sil birlesim gorunur kalir
- ✅ formul birlesik hucreyi okur
- ✅ gizli sutunlu birlesim boyutu

### `testler/test_birlesim_pano.py` — 12/12 ✅
**

- ✅ pano verisi tam kapsanan birlesimi alir
- ✅ pano araligi bos birlesimi kirpmaz
- ✅ yapistirma birlesimleri yinelemede cogalir
- ✅ birlesim kismen kesiyor
- ✅ hucre tasi birlesimi tasir ve geri alir
- ✅ hucre tasi ust uste binen alan
- ✅ hucre tasi hedefteki eski birlesim kalkar
- ✅ hucre tasi sayfalar arasi
- ✅ kopyala yapistir birlesimi tasir
- ✅ yapistirma eski birlesimi kaldirir
- ✅ yapistirma birlesimi kismen keserse reddedilir
- ✅ kes yapistir birlesimi tasir

### `testler/test_bul.py` — 29/29 ✅
*Bul/Değiştir modeli (5b): joker, büyük/küçük harf, formül/değer/not arama, Tümünü Değiştir*

- ✅ TestJoker::test alt dize ve buyuk kucuk turkce
- ✅ TestJoker::test buyuk kucuk duyarli
- ✅ TestJoker::test jokerler
- ✅ TestJoker::test tam hucre
- ✅ TestJoker::test ortak modulle ayni kurallar
- ✅ TestEslesmeler::test sonraki hucreden baslar ve sarar
- ✅ TestEslesmeler::test satir ve sutun sirasi
- ✅ TestEslesmeler::test secimde ara
- ✅ TestEslesmeler::test buyuk kucuk ve tam hucre
- ✅ TestEslesmeler::test bos aranan bir sey bulmaz
- ✅ TestEslesmeler::test formul modu turkce formul metninde arar
- ✅ TestEslesmeler::test deger modu gorunen metin
- ✅ TestEslesmeler::test not modu
- ✅ TestEslesmeler::test birlesim kapsanan hucreler atlanir
- ✅ TestEslesmeler::test kitap kapsami sayfa sirasi
- ✅ TestEslesmeler::test yuz bin hucrede hizli
- ✅ TestYeniMetin::test her eslesme degisir buyuk kucuk duyarsiz
- ✅ TestYeniMetin::test buyuk kucuk duyarli
- ✅ TestYeniMetin::test tam hucre tumunu degistirir
- ✅ TestYeniMetin::test joker ve bos yeni metin
- ✅ TestYeniMetin::test yeni metin oldugu gibi joker islenmez
- ✅ TestDegistir::test tumunu degistir tek geri al
- ✅ TestDegistir::test sayiya donusur elle yazilmis gibi
- ✅ TestDegistir::test tarih genel hucreye sayi bicimi oner
- ✅ TestDegistir::test formulde degistirir ve hesaplanir
- ✅ TestDegistir::test gecersiz formul atlanir ve sayilir
- ✅ TestDegistir::test not ve deger modunda degistirilmez
- ✅ TestDegistir::test degisim yoksa komut yok
- ✅ TestDegistir::test coklu sayfa tek adim

### `testler/test_bul_arayuz.py` — 12/12 ✅
*Bul/Değiştir/Git penceresi ve kısayollar (5b)*

- ✅ menu eylemleri ve pencere
- ✅ sonrakini bul hucreye gider ve sarar
- ✅ onceki bul
- ✅ secim icinde arama kisiti korur
- ✅ tumunu bul listesi ve tiklayinca gider
- ✅ sayfa degistirerek bulur
- ✅ tumunu degistir tek geri al
- ✅ degistir etkin hucre eslesirse degistirir sonrakine gecer
- ✅ degerler ve notlar modunda degistir kapali
- ✅ formul icinde degistir turkce metinde
- ✅ git adrese
- ✅ sonrakini bul kisayolu pencere kapaliyken

### `testler/test_csv_io.py` — 21/21 ✅
**

- ✅ kodlama tani
- ✅ cp1254 dosya dogru okunur
- ✅ ayrac tani `[a;b;c\n1;2;3\n-;]
- ✅ ayrac tani `[a,b,c\n1,2,3\n-,]
- ✅ ayrac tani `[a\tb\tc\n1\t2\t3\n-\t]
- ✅ ayrac tani `[a|b|c\n1|2|3\n-|]
- ✅ ayrac tani `[ad;fiyat\nkalem;1,5\nsilgi;2,25\n-;]
- ✅ ayrac tani `[ad,not\n"Ali, Veli",5\n"Ay\u015fe, Fatma",6\n-,]
- ✅ ayrac tani `[tek s\xfctun\nba\u015fka\n-;]
- ✅ ayrac tani `[-;]
- ✅ tirnakli cok satirli alan
- ✅ alanlar elle yazilmis gibi cozulur
- ✅ metin olarak hicbir sey cevrilmez
- ✅ bozuk formul metin kalir
- ✅ bos alan ve kisa satir
- ✅ sayfa adi uret
- ✅ yaz gorunen metin ve tirnaklama
- ✅ yaz formul sonucu ve bos sayfa
- ✅ gidis donus dosya
- ✅ yazma hatasinda eski dosya bozulmaz
- ✅ eksik dosya

### `testler/test_csv_menu.py` — 8/8 ✅
**

- ✅ csv ac yeni pencerede xlsx onerir
- ✅ csv iptal
- ✅ csv penceresi gercek onizleme
- ✅ csv olarak kaydet
- ✅ csv filtresiyle uzantisiz kaydet
- ✅ csv cok sayfa uyarisi
- ✅ ayni csv iki kez acilmaz
- ✅ gercek csv penceresi yolu — Önizleme penceresi `exec` yamalanıp Tamam'a basılmış gibi: dosya → kitap tüm zinciri.

### `testler/test_degerlendir.py` — 46/46 ✅
*Formül değerlendirici: tür dönüşümleri, dizi yayma, hata yayılımı, 15 basamak*

- ✅ isleçler `[1+2*3-7.0]
- ✅ isleçler `[(1+2)*3-9.0]
- ✅ isleçler `[-2^2-4.0]
- ✅ isleçler `[0-2^2--4.0]
- ✅ isleçler `[2^3^2-64.0]
- ✅ isleçler `[10/4-2.5]
- ✅ isleçler `[50%-0.5]
- ✅ isleçler `[2*50%-1.0]
- ✅ isleçler `[--3-3.0]
- ✅ isleçler `["a"&"b"-ab]
- ✅ isleçler `[1&2-12]
- ✅ isleçler `[2.5&""-2,5]
- ✅ isleçler `[TRUE&""-DO\u011eRU]
- ✅ isleçler `[1=1-True]
- ✅ isleçler `[1<>1-False]
- ✅ isleçler `["a"="A"-True]
- ✅ isleçler `["b">"a"-True]
- ✅ isleçler `[1<"a"-True]
- ✅ isleçler `["z"<TRUE-True]
- ✅ isleçler `[3>2-True]
- ✅ isleçler `[2>=2-True]
- ✅ isleçler `[1<=0-False]
- ✅ hatalar `[1/0-beklenen0]
- ✅ hatalar `[0^0-beklenen1]
- ✅ hatalar `[(-8)^(1/3)-beklenen2]
- ✅ hatalar `["a"+1-beklenen3]
- ✅ hatalar `[#N/A+1-beklenen4]
- ✅ hatalar `[1+#N/A-beklenen5]
- ✅ hatalar `[#REF!-beklenen6]
- ✅ hatalar `[10^400-beklenen7]
- ✅ hatalar `[#DIV/0!&#N/A-beklenen8]
- ✅ hatalar `[TANIMSIZ(1)-beklenen9]
- ✅ hatalar `[Satislar-beklenen10]
- ✅ tur donusumleri
- ✅ bos hucre
- ✅ ortuk kesisim
- ✅ dizi ogeler
- ✅ sum ve if
- ✅ baska sayfa
- ✅ kimlikli basvuru
- ✅ kesisim ve aralik islec
- ✅ yakin sifir
- ✅ sayi metni
- ✅ sayiya ve metne
- ✅ karsilastir turkce
- ✅ aralik deger buyuk aralik

### `testler/test_dogrulama.py` — 45/45 ✅
*Veri doğrulama (5g): model, komut, denetim (tür × işleç, liste, özel), ekle-sil, .xlsx*

- ✅ TestKuralModeli::test gecersiz alanlar
- ✅ TestKuralModeli::test yeni kural eskinin ustune gelir
- ✅ TestKuralModeli::test kaldirma ve tamamen ortulen kural duser
- ✅ TestKuralModeli::test sayfa dogrulama arama ve olay
- ✅ TestKuralModeli::test liste sabiti
- ✅ TestKomut::test yap geri al yinele ve bos
- ✅ TestSayisalTurler::test tam sayi arasinda
- ✅ TestSayisalTurler::test metin bool hata gecersiz
- ✅ TestSayisalTurler::test bos girdi bos yoksay
- ✅ TestSayisalTurler::test islecler `[arasinda_degil-1.0-3.0-gecen0-gecmeyen0]
- ✅ TestSayisalTurler::test islecler `[esit-2.0-None-gecen1-gecmeyen1]
- ✅ TestSayisalTurler::test islecler `[esit_degil-2.0-None-gecen2-gecmeyen2]
- ✅ TestSayisalTurler::test islecler `[buyuk-2.0-None-gecen3-gecmeyen3]
- ✅ TestSayisalTurler::test islecler `[kucuk-2.0-None-gecen4-gecmeyen4]
- ✅ TestSayisalTurler::test islecler `[buyuk_esit-2.0-None-gecen5-gecmeyen5]
- ✅ TestSayisalTurler::test islecler `[kucuk_esit-2.0-None-gecen6-gecmeyen6]
- ✅ TestSayisalTurler::test tarih ve saat seri sayi
- ✅ TestSayisalTurler::test metin uzunlugu
- ✅ TestSayisalTurler::test baska hucreye bakan formul
- ✅ TestSayisalTurler::test goreli basvuru hucreye gore kayar
- ✅ TestSayisalTurler::test bozuk formul gecersiz
- ✅ TestListe::test sabit liste buyuk kucuk duyarsiz turkce
- ✅ TestListe::test sayi ve metin ayni gorunumde eslesir
- ✅ TestListe::test aralik listesi ve degisince
- ✅ TestListe::test ogeler bos hucre acilir listede bos satir
- ✅ TestListe::test tanimli ad ve baska sayfa
- ✅ TestListe::test hatali kaynak gecersiz ve bos
- ✅ TestOzel::test formul yeni degerle degerlenir
- ✅ TestOzel::test hucre degeri geri konur
- ✅ TestOzel::test baska hucre ve sifir degil sayi
- ✅ TestEkleSil::test satir ekle aralik ve formul kayar geri al
- ✅ TestEkleSil::test liste sabiti ekle silde degismez
- ✅ TestEkleSil::test aralik silinince kural duser
- ✅ TestXlsx::test gidis donus `[dv0]
- ✅ TestXlsx::test gidis donus `[dv1]
- ✅ TestXlsx::test gidis donus `[dv2]
- ✅ TestXlsx::test gidis donus `[dv3]
- ✅ TestXlsx::test gidis donus `[dv4]
- ✅ TestXlsx::test gidis donus `[dv5]
- ✅ TestXlsx::test gidis donus `[dv6]
- ✅ TestXlsx::test gidis donus `[dv7]
- ✅ TestXlsx::test gidis donus `[dv8]
- ✅ TestXlsx::test liste sayfa adi cevrilir
- ✅ TestXlsx::test tara uyari vermez
- ✅ TestXlsx::test dogrulamasiz dosya

### `testler/test_dogrulama_arayuz.py` — 21/21 ✅
*Veri doğrulama arayüzü (5g): pencere, giriş denetimi, açılır liste, giriş iletisi*

- ✅ menu acik
- ✅ pencereden uygula geri al temizle
- ✅ etkisiz kural kaldirir
- ✅ karisik secimde soru
- ✅ ayni kuralla tamamen kapli secimde soru yok
- ✅ geri yonlu secimde goreli formul capaya kayar
- ✅ gecersiz giris durdur tekrar ve iptal
- ✅ uyari stili devam yazar
- ✅ hata uyarisi kapaliysa sessizce izin
- ✅ formul girisi ve silme denetlenmez
- ✅ yapistirma denetlenmez kopya notu
- ✅ bos girdi bos yoksay
- ✅ acilir liste ogeleri ve secim
- ✅ acilir liste kapali ya da baska tur
- ✅ dugme dikdortgeni tiklama ve alt asagi
- ✅ giris iletisi gosterilir ve kapanir
- ✅ tumunu temizle kurali da kaldirir
- ✅ pencere liste ve sayi donusumu
- ✅ pencere ozel ve formul hatasi ve tarih
- ✅ pencere yukle ve yeniden olustur
- ✅ pencere duzen alanlari

### `testler/test_doldur.py` — 29/29 ✅
**

- ✅ tek sayi kopyalanir
- ✅ iki sayi sabit adim
- ✅ uc sayi dogrusal egilim
- ✅ sayi serisi geri
- ✅ ondalik adim artik birakmaz
- ✅ tek tarih gun artar
- ✅ iki tarih gun adimi
- ✅ aylik tarih serisi ayni gun
- ✅ yillik ve ay sonu kisaltma
- ✅ tarih biçimsiz sayi gun degil sayi
- ✅ tarih geri
- ✅ ay adlari
- ✅ ad buyuk kucuk harf korunur
- ✅ ad geri ve duzensiz
- ✅ metin sayi
- ✅ metin sayi adim ve geri
- ✅ formul kayar
- ✅ formul geri ve yatay
- ✅ metin mantiksal desen yinelenir
- ✅ bos hucre hedefi bosaltir
- ✅ bicim desen olarak kopyalanir
- ✅ coklu serit ayri seri
- ✅ yatay doldurma
- ✅ gecersiz hedef
- ✅ ctrl d ilk satir kopyalanir
- ✅ ctrl d tek hucre ustten
- ✅ ctrl r
- ✅ ctrl d bicim gelir
- ✅ bitisik son satir

### `testler/test_doldur_arayuz.py` — 17/17 ✅
**

- ✅ ctrl d ve ctrl r
- ✅ ctrl d tek hucre ustten ve ilk satir bos
- ✅ ctrl d bicim gelir ve tam sutun sinirlanir
- ✅ ctrl d coklu secimde uyarir
- ✅ ctrl enter girdiyi tum secime yazar
- ✅ ctrl enter tek hucrede olagan ve deger sabit
- ✅ tutamac secimin sag altinda ve coklu secimde yok
- ✅ tutamac gorunur ve imlec
- ✅ surukle asagi seri
- ✅ surukle yukari sola saga
- ✅ surukle asagi formul kayar ve bicim
- ✅ surukle kaynak icine degisiklik yok
- ✅ onizleme cerceve cizilir
- ✅ cift tik komsu veri sonuna doldurur
- ✅ cift tik komsu yoksa bir sey yapmaz
- ✅ birlesik hucrelere doldurma reddedilir
- ✅ doldurma formul motorunu gunceller

### `testler/test_dondurma.py` — 22/22 ✅
**

- ✅ model gorunum yaz ve olay
- ✅ gorunum geri al yigininda degil
- ✅ ust satir donar ve kaydirilirken gorunur kalir
- ✅ ilk sutun donar
- ✅ bolme etkin hucrenin ustu ve solu
- ✅ etkin hucre ilk hucredeyse dondurma olmaz
- ✅ dondurmayi kaldir
- ✅ bilinmeyen tur
- ✅ pencereyi dolduran dondurma reddedilir
- ✅ nokta hucre eslemesi dondurmayla
- ✅ gezinme dondurulmus bolgeye ve kayan bolgeye
- ✅ secim dondurma siniri boyunca
- ✅ pano ve ozet dondurmadan etkilenmez
- ✅ dondurma cizgisi cizilir
- ✅ dondurulmus bolme kaydirilinca ayni pikselleri verir
- ✅ artimli kaydirma dondurmada tam cizimle ayni
- ✅ metin dondurma cizgisini asmaz
- ✅ kilavuz gizle goster piksel
- ✅ kilavuz gizliyken dolgu ve kenarlik gorunur
- ✅ gorunum menusu
- ✅ gorunum sayfaya ozel
- ✅ acilista kayitli dondurma uygulanir

### `testler/test_dongu_arayuz.py` — 5/5 ✅
*Döngüsel başvuru uyarısı (6e): durum çubuğu etiketi, tek uyarı*

- ✅ dongu yoksa etiket gizli
- ✅ dongu olusunca etiket ve tek uyari
- ✅ dongu cozulunce etiket kalkar
- ✅ kendine basvuru ve geri al uyarmaz
- ✅ baska sayfadaki dongu adressiz etiket

### `testler/test_dosya_menusu.py` — 17/17 ✅
**

- ✅ degisti isareti ve baslik
- ✅ farkli kaydet ve kaydet
- ✅ farkli kaydet iptal
- ✅ ac yeni pencerede ve bos pencere kapanir
- ✅ dolu pencere kapanmaz
- ✅ ayni dosya iki kez acilmaz
- ✅ ac penceresi diyalogdan
- ✅ bozuk ve eksik dosya iletisi
- ✅ veri kaybi bilgi cubugu ve onay
- ✅ yine de kaydet
- ✅ kapatirken sorma `[kaydetme-True-False]
- ✅ kapatirken sorma `[iptal-False-False]
- ✅ kapatirken sorma `[kaydet-True-True]
- ✅ degismemis pencere sormadan kapanir
- ✅ son dosyalar
- ✅ son dosyalar bozuk json
- ✅ sayfa yapisi gidis donus pencereden — Pencereden kaydedilen dosya yeniden açılınca aynı: biçim + formül + ikinci sayfa.

### `testler/test_faz5_altyapi.py` — 65/65 ✅
*Faz 5 ortak altyapı (5a): aralık yardımcıları, ek veri depoları + ekle-sil, harmanlama, ağaç kaydırma, ek/ad olayları, menü iskeleti*

- ✅ TestAralikKaydir::test ekleme oncesi kaydirir icine buyutur sonrasi dokunmaz
- ✅ TestAralikKaydir::test silme kucultur kaydirir tamamen silineni kaldirir
- ✅ TestAralikKaydir::test sayfa sinirina itilen
- ✅ TestAralikKaydir::test tam sutun satir korunur
- ✅ TestAralikCikar::test kesisim yoksa aynen
- ✅ TestAralikCikar::test tamamen ortulurse bos
- ✅ TestAralikCikar::test ortadan delik dort parca
- ✅ TestAralikCikar::test alan esitligi `[a0-b0]
- ✅ TestAralikCikar::test alan esitligi `[a1-b1]
- ✅ TestAralikCikar::test alan esitligi `[a2-b2]
- ✅ TestAralikCikar::test alan esitligi `[a3-b3]
- ✅ TestAralikCikar::test alan esitligi `[a4-b4]
- ✅ TestBitisikBolge::test tek hucre
- ✅ TestBitisikBolge::test bos hucre komsusuz kendisi
- ✅ TestBitisikBolge::test dikdortgen tablo
- ✅ TestBitisikBolge::test capraz komsu dahil
- ✅ TestBitisikBolge::test bosluk ayirir
- ✅ TestBitisikBolge::test sayfa kenarinda
- ✅ TestBitisikBolge::test bos hucre icinden baslayinca
- ✅ TestMetinAnahtari::test turkce alfabe sirasi
- ✅ TestMetinAnahtari::test ozel harfler komsu harflerin arasinda
- ✅ TestMetinAnahtari::test noktali noktasiz i buyuk harfler
- ✅ TestMetinAnahtari::test buyuk kucuk harf birincil olarak esit
- ✅ TestMetinAnahtari::test buyuk kucuk duyarli kucuk once
- ✅ TestMetinAnahtari::test rakam harften once noktalama rakamdan once
- ✅ TestMetinAnahtari::test rakamlar metin olarak karakter karakter
- ✅ TestMetinAnahtari::test kisa cizgi ve kesme birincil yok sayilir
- ✅ TestMetinAnahtari::test aksanli yabanci harf temel harfle esit sonra
- ✅ TestMetinAnahtari::test onek kisa once
- ✅ TestMetinAnahtari::test gercek isimler
- ✅ TestDegerAnahtari::test artan duzen
- ✅ TestDegerAnahtari::test azalan duzen
- ✅ TestDegerAnahtari::test hatalar birbirine esit kararli
- ✅ TestDegerAnahtari::test metin turkce harmanla
- ✅ TestDegerAnahtari::test sayi onbes basamak
- ✅ TestDegerAnahtari::test sayi metinden once bool sayidan ayri
- ✅ TestDegerAnahtari::test buyuk kucuk duyarli metin
- ✅ agac kaydir kopyala ile ayni rastgele formuller
- ✅ agac kaydir sayfa disina cikan ref hatasi
- ✅ agac kaydir degismeyeni paylasir ve onbellekler
- ✅ agac kaydir hiz
- ✅ TestEkVeriKaydirma::test notlar satir ekle sil
- ✅ TestEkVeriKaydirma::test notlar sutun ekle sil
- ✅ TestEkVeriKaydirma::test dogrulama ve kosullu araliklari kayar buyur kuculur duser
- ✅ TestEkVeriKaydirma::test araligi kalmayan kural duser
- ✅ TestEkVeriKaydirma::test filtre araligi kayar baslik silinirse kalkar
- ✅ TestEkVeriKaydirma::test filtre tamamen silinirse kalkar
- ✅ TestEkVeriKaydirma::test ek veri yoksa maliyetsiz ve hatasiz
- ✅ TestEkDurumu::test gidis donus
- ✅ TestEkDurumu::test durum kopyadir
- ✅ TestEkDurumu::test yukle tek ek olayi degismediyse olay yok
- ✅ TestAdDeposu::test kapsam onceligi ve buyuk kucuk duyarsiz
- ✅ TestAdDeposu::test turkce buyuk kucuk
- ✅ TestAdDeposu::test silinen sayfanin kapsamli adi gorunmez geri gelince doner
- ✅ TestAdDeposu::test ad olaylari
- ✅ TestAdDeposu::test yeniden adlandirma eski anahtari kaldirir
- ✅ TestAdDeposu::test durum yukle
- ✅ TestAdDeposu::test ad olayi motoru yeniden hesaplatir ve ek yok sayilir
- ✅ TestEkKomutlari::test satir ekle geri al yinele
- ✅ TestEkKomutlari::test satir sil geri al silinen notu ve kurali geri getirir
- ✅ TestEkKomutlari::test sutun komutu ad formullerini duzeltir ve geri alir
- ✅ TestEkKomutlari::test baska sayfadaki dogrulama formulu de duzelir
- ✅ TestEkKomutlari::test ek duzeltmeleri degisiklik yoksa false
- ✅ birlesim davranisi degismedi — `_birlesimleri_kaydir` artık `aralik_kaydir` kullanır; mevcut davranış aynı.
- ✅ duzen ve veri menu iskeleti ve olaylar pencereyi bozmaz

### `testler/test_filtre.py` — 60/60 ✅
*Filtre + ALTTOPLAM (5f): her koşul türü, komut, ALTTOPLAM 1–11/101–111, motor yeniden hesap, .xlsx*

- ✅ TestDegerKosulu::test normal buyuk kucuk duyarsiz
- ✅ TestDegerKosulu::test turkce i
- ✅ TestDegerKosulu::test bos
- ✅ TestDegerKosulu::test hata degeri gorunen metin
- ✅ TestDegerKosulu::test sayi ve metin karisimi
- ✅ TestOzelKosul::test sayi buyuk
- ✅ TestOzelKosul::test arasinda ve veya
- ✅ TestOzelKosul::test esit degil metin ve bos gecer
- ✅ TestOzelKosul::test metin islecleri ve joker
- ✅ TestOzelKosul::test metin karsilastirma turkce siralama
- ✅ TestIlkOrtalamaRenk::test ilk ve son
- ✅ TestIlkOrtalamaRenk::test yuzde
- ✅ TestIlkOrtalamaRenk::test ortalama
- ✅ TestIlkOrtalamaRenk::test ilk diger sutun filtresinden bagimsiz
- ✅ TestIlkOrtalamaRenk::test renk
- ✅ TestListe::test degerler sirali benzersiz bos
- ✅ TestListe::test diger sutun filtresi listeyi daraltir
- ✅ TestListe::test kendi sutun filtresi listeyi daraltmaz
- ✅ TestListe::test renkler
- ✅ aralik genislet
- ✅ TestKomut::test uygula geri al yinele
- ✅ TestKomut::test kaldirinca satirlar gorunur
- ✅ TestKomut::test filtre disindaki gizli satir korunur
- ✅ TestKomut::test elle gizlenen filtre araliginda yeniden hesaplanir
- ✅ TestKomut::test olaylar ek ve boyut
- ✅ TestKomut::test ana sayfa ve ekle sil filtreyi kaydirir
- ✅ TestAlttoplam::test ad cevirisi
- ✅ TestAlttoplam::test filtre yokken tum satirlar
- ✅ TestAlttoplam::test filtreyle gizli iki grupta da dislanir
- ✅ TestAlttoplam::test elle gizli yalniz 101 den sonra dislanir
- ✅ TestAlttoplam::test elle gizli filtre araligi disinda 9da sayilir
- ✅ TestAlttoplam::test alttoplam hucreleri sayilmaz
- ✅ TestAlttoplam::test islev numaralari `[1-3.5]
- ✅ TestAlttoplam::test islev numaralari `[2-6.0]
- ✅ TestAlttoplam::test islev numaralari `[3-6.0]
- ✅ TestAlttoplam::test islev numaralari `[4-6.0]
- ✅ TestAlttoplam::test islev numaralari `[5-1.0]
- ✅ TestAlttoplam::test islev numaralari `[6-720.0]
- ✅ TestAlttoplam::test islev numaralari `[7-1.8708286933869707]
- ✅ TestAlttoplam::test islev numaralari `[8-1.707825127659933]
- ✅ TestAlttoplam::test islev numaralari `[9-21.0]
- ✅ TestAlttoplam::test islev numaralari `[10-3.5]
- ✅ TestAlttoplam::test islev numaralari `[11-2.9166666666666665]
- ✅ TestAlttoplam::test bos metin karisim ve hata
- ✅ TestAlttoplam::test birden cok aralik
- ✅ TestAlttoplam::test filtre kalkinca geri hesaplanir
- ✅ TestXlsx::test gidis donus `[kosul0]
- ✅ TestXlsx::test gidis donus `[kosul1]
- ✅ TestXlsx::test gidis donus `[kosul2]
- ✅ TestXlsx::test gidis donus `[kosul3]
- ✅ TestXlsx::test gidis donus `[kosul4]
- ✅ TestXlsx::test gidis donus `[kosul5]
- ✅ TestXlsx::test gidis donus `[kosul6]
- ✅ TestXlsx::test gidis donus `[kosul7]
- ✅ TestXlsx::test gidis donus `[kosul8]
- ✅ TestXlsx::test gidis donus `[kosul9]
- ✅ TestXlsx::test gidis donus `[kosul10]
- ✅ TestXlsx::test ortalama ve filtresiz dosya
- ✅ TestXlsx::test kosulsuz filtre dugmesi korunur
- ✅ TestXlsx::test renk filtresi uyarisi gizlilik kalir

### `testler/test_filtre_arayuz.py` — 15/15 ✅
*Filtre arayüzü (5f): düğmeler, panel, özel filtre, özet, Delete*

- ✅ menu eylemleri acik
- ✅ ac kapat bitisik bolge ve geri al
- ✅ dugmeye tiklama sinyal secimi degistirmez
- ✅ alt asagi baslik hucresinde listeyi acar
- ✅ cizim dugme ve mavi satir hatasiz
- ✅ panel listesi degerler bos ve tumu
- ✅ panel tamam satirlari gizler ve ileti
- ✅ panel arama ve diger sutun filtresi
- ✅ sutun filtresini temizle digerleri kalir
- ✅ filtreyi temizle ve yeniden uygula
- ✅ ozel filtre penceresi kosulu
- ✅ ilk on penceresi
- ✅ panel metin sayi menusu sutun turune gore
- ✅ delete ve ozet filtreyle gizlileri atlar
- ✅ panelden siralama baslik sabit

### `testler/test_fonk_metin_tarih.py` — 356/356 ✅
*Metin ve tarih fonksiyonları (1900 sistemi)*

- ✅ averageif `[=AVERAGEIF(A1:A3,">15")-25.0-veri0]
- ✅ averageif `[=AVERAGEIF(A1:A3,">15",C1:C3)-2.5-veri1]
- ✅ averageif `[=AVERAGEIF(E1:E3,">1")-beklenen2-None]
- ✅ averageif `[=AVERAGEIF(A1:A3,">5",B1:B3)-beklenen3-veri3]
- ✅ averageif `[=AVERAGEIF(A1:A3,"a",C1:C3)-2.0-veri4]
- ✅ averageif `[=AVERAGEIF(A1:A3,"z",C1:C3)-beklenen5-veri5]
- ✅ averageif `[=AVERAGEIFS(C1:C3,A1:A3,"a",C1:C3,">1")-3.0-veri6]
- ✅ averageif `[=AVERAGEIFS(E1:E3,F1:F3,">1")-beklenen7-None]
- ✅ averageif `[=AVERAGEIFS(B1:B3,A1:A3,">5")-beklenen8-veri8]
- ✅ averageif `[=AVERAGEIFS(C1:C3,A1:A2,"a")-beklenen9-veri9]
- ✅ metin `[=CONCATENATE("a","b",1)-ab1-None]
- ✅ metin `[=CONCATENATE(B1,"x")-x-None]
- ✅ metin `[=CONCATENATE(#N/A,"x")-beklenen2-None]
- ✅ metin `[=CONCATENATE(1,TRUE,"a")-1DO\u011eRUa-None]
- ✅ metin `[=CONCATENATE(1.5,"")-1,5-None]
- ✅ metin `[=CONCAT(A1:A4)-102030x-veri5]
- ✅ metin `[=CONCAT(B1:B3)--veri6]
- ✅ metin `[=CONCAT(A1:A3)-beklenen7-veri7]
- ✅ metin `[=CONCAT("a",A6)-aDO\u011eRU-veri8]
- ✅ metin `[=TEXTJOIN(",",TRUE,"a","","b")-a,b-None]
- ✅ metin `[=TEXTJOIN(",",FALSE,"a","","b")-a,,b-None]
- ✅ metin `[=TEXTJOIN("-",TRUE,B1:B3)--None]
- ✅ metin `[=TEXTJOIN("-",TRUE,A1:A3)-beklenen12-veri12]
- ✅ metin `[=TEXTJOIN("-",TRUE,A1:A4)-10-20-30-x-veri13]
- ✅ metin `[=LEFT("abc")-a-None]
- ✅ metin `[=LEFT("abc",2)-ab-None]
- ✅ metin `[=LEFT(B1)--None]
- ✅ metin `[=LEFT(#N/A)-beklenen17-None]
- ✅ metin `[=LEFT(12345,2)-12-None]
- ✅ metin `[=LEFT("abc",-1)-beklenen19-None]
- ✅ metin `[=LEFT("abc",10)-abc-None]
- ✅ metin `[=RIGHT("abc",2)-bc-None]
- ✅ metin `[=RIGHT("abc")-c-None]
- ✅ metin `[=RIGHT("abc",0)--None]
- ✅ metin `[=RIGHT(123,2)-23-None]
- ✅ metin `[=RIGHT("abc",10)-abc-None]
- ✅ metin `[=RIGHT(B1,2)--None]
- ✅ metin `[=RIGHT(#N/A,2)-beklenen27-None]
- ✅ metin `[=MID("abcdef",2,3)-bcd-None]
- ✅ metin `[=MID("abc",5,2)--None]
- ✅ metin `[=MID("abc",0,1)-beklenen30-None]
- ✅ metin `[=MID(B1,1,1)--None]
- ✅ metin `[=MID(#N/A,1,1)-beklenen32-None]
- ✅ metin `[=MID(12345,2,2)-23-None]
- ✅ metin `[=LEN("abc")-3.0-None]
- ✅ metin `[=LEN(B1)-0.0-None]
- ✅ metin `[=LEN(12.5)-4.0-None]
- ✅ metin `[=LEN(#N/A)-beklenen37-None]
- ✅ metin `[=LEN(TRUE)-5.0-None]
- ✅ metin `[=UPPER("abc i")-ABC \u0130-None]
- ✅ metin `[=UPPER("\u0131")-I-None]
- ✅ metin `[=UPPER(B1)--None]
- ✅ metin `[=UPPER(#N/A)-beklenen42-None]
- ✅ metin `[=UPPER(1)-1-None]
- ✅ metin `[=LOWER("ABC I")-abc \u0131-None]
- ✅ metin `[=LOWER("\u0130")-i-None]
- ✅ metin `[=LOWER(B1)--None]
- ✅ metin `[=LOWER(#N/A)-beklenen47-None]
- ✅ metin `[=PROPER("hello wORLD")-Hello World-None]
- ✅ metin `[=PROPER("ilk i\u015flem")-\u0130lk \u0130\u015flem-None]
- ✅ metin `[=PROPER("2cats")-2Cats-None]
- ✅ metin `[=PROPER(B1)--None]
- ✅ metin `[=PROPER(#N/A)-beklenen52-None]
- ✅ metin `[=TRIM("  a   b  ")-a b-None]
- ✅ metin `[=TRIM(B1)--None]
- ✅ metin `[=TRIM(#N/A)-beklenen55-None]
- ✅ metin `[=TRIM(12)-12-None]
- ✅ metin `[=FIND("b","abc")-2.0-None]
- ✅ metin `[=FIND("B","abc")-beklenen58-None]
- ✅ metin `[=FIND("","abc")-1.0-None]
- ✅ metin `[=FIND("a","abca",2)-4.0-None]
- ✅ metin `[=FIND("a",B1)-beklenen61-None]
- ✅ metin `[=FIND("a",#N/A)-beklenen62-None]
- ✅ metin `[=SEARCH("B","abc")-2.0-None]
- ✅ metin `[=SEARCH("a*c","xabc")-2.0-None]
- ✅ metin `[=SEARCH("?b","abc")-1.0-None]
- ✅ metin `[=SEARCH("z","abc")-beklenen66-None]
- ✅ metin `[=SEARCH("a",#N/A)-beklenen67-None]
- ✅ metin `[=SEARCH("1",123)-1.0-None]
- ✅ metin `[=SUBSTITUTE("a-b-c","-","+")-a+b+c-None]
- ✅ metin `[=SUBSTITUTE("a-b-c","-","+",2)-a-b+c-None]
- ✅ metin `[=SUBSTITUTE(B1,"a","b")--None]
- ✅ metin `[=SUBSTITUTE(#N/A,"a","b")-beklenen72-None]
- ✅ metin `[=SUBSTITUTE(123,2,9)-193-None]
- ✅ metin `[=SUBSTITUTE("abc","","x")-abc-None]
- ✅ metin `[=SUBSTITUTE("Aa","a","x")-Ax-None]
- ✅ metin `[=REPLACE("abcdef",2,3,"X")-aXef-None]
- ✅ metin `[=REPLACE("abc",5,1,"Z")-abcZ-None]
- ✅ metin `[=REPLACE("abc",0,1,"Z")-beklenen78-None]
- ✅ metin `[=REPLACE(#N/A,1,1,"x")-beklenen79-None]
- ✅ metin `[=REPLACE(12345,2,2,"")-145-None]
- ✅ metin `[=REPLACE(B1,1,1,"x")-x-None]
- ✅ metin `[=VALUE("12")-12.0-None]
- ✅ metin `[=VALUE("1,5")-1.5-None]
- ✅ metin `[=VALUE("abc")-beklenen84-None]
- ✅ metin `[=VALUE(B1)-0.0-None]
- ✅ metin `[=VALUE(#N/A)-beklenen86-None]
- ✅ metin `[=VALUE(TRUE)-beklenen87-None]
- ✅ metin `[=VALUE("50%")-0.5-None]
- ✅ metin `[=REPT("ab",3)-ababab-None]
- ✅ metin `[=REPT("a",0)--None]
- ✅ metin `[=REPT("a",-1)-beklenen91-None]
- ✅ metin `[=REPT(B1,3)--None]
- ✅ metin `[=REPT(#N/A,3)-beklenen93-None]
- ✅ metin `[=REPT(1,3)-111-None]
- ✅ metin `[=EXACT("a","a")-True-None]
- ✅ metin `[=EXACT("a","A")-False-None]
- ✅ metin `[=EXACT(1,"1")-True-None]
- ✅ metin `[=EXACT(B1,"")-True-None]
- ✅ metin `[=EXACT(#N/A,"a")-beklenen99-None]
- ✅ tarih `[=DATE(2024,2,29)-45351.0-None]
- ✅ tarih `[=DATE(2000,1,1)-36526.0-None]
- ✅ tarih `[=DATE(2024,14,1)-45689.0-None]
- ✅ tarih `[=DATE(2024,1,0)-45291.0-None]
- ✅ tarih `[=DATE(B1,1,1)-1.0-None]
- ✅ tarih `[=DATE(#N/A,1,1)-beklenen5-None]
- ✅ tarih `[=DATE("2024","2","29")-45351.0-None]
- ✅ tarih `[=DATE(-1,1,1)-beklenen7-None]
- ✅ tarih `[=DATE(1900,2,29)-60.0-None]
- ✅ tarih `[=DATE(1900,3,0)-60.0-None]
- ✅ tarih `[=DATE(10000,1,1)-beklenen10-None]
- ✅ tarih `[=TODAY()>=46304-True-None]
- ✅ tarih `[=TODAY()=INT(TODAY())-True-None]
- ✅ tarih `[=TODAY()+#N/A-beklenen13-None]
- ✅ tarih `[=TODAY()-B1>46000-True-None]
- ✅ tarih `[=NOW()>=TODAY()-True-None]
- ✅ tarih `[=INT(NOW())=TODAY()-True-None]
- ✅ tarih `[=NOW()+#N/A-beklenen17-None]
- ✅ tarih `[=NOW()*0+"2"-2.0-None]
- ✅ tarih `[=TIME(12,0,0)-0.5-None]
- ✅ tarih `[=TIME(24,0,0)-0.0-None]
- ✅ tarih `[=TIME(B1,B1,B1)-0.0-None]
- ✅ tarih `[=TIME(#N/A,0,0)-beklenen22-None]
- ✅ tarih `[=TIME("6","0","0")-0.25-None]
- ✅ tarih `[=TIME(-1,0,0)-beklenen24-None]
- ✅ tarih `[=TIME(0,90,0)-0.0625-None]
- ✅ tarih `[=YEAR(45351)-2024.0-None]
- ✅ tarih `[=MONTH(45351)-2.0-None]
- ✅ tarih `[=DAY(45351)-29.0-None]
- ✅ tarih `[=YEAR(B1)-1900.0-None]
- ✅ tarih `[=MONTH(B1)-1.0-None]
- ✅ tarih `[=DAY(B1)-0.0-None]
- ✅ tarih `[=YEAR(#N/A)-beklenen32-None]
- ✅ tarih `[=MONTH(#N/A)-beklenen33-None]
- ✅ tarih `[=DAY(#N/A)-beklenen34-None]
- ✅ tarih `[=YEAR("45351")-2024.0-None]
- ✅ tarih `[=YEAR(-1)-beklenen36-None]
- ✅ tarih `[=YEAR(60)-1900.0-None]
- ✅ tarih `[=MONTH(60)-2.0-None]
- ✅ tarih `[=DAY(60)-29.0-None]
- ✅ tarih `[=MONTH(61)-3.0-None]
- ✅ tarih `[=HOUR(0.75)-18.0-None]
- ✅ tarih `[=HOUR(B1)-0.0-None]
- ✅ tarih `[=HOUR(#N/A)-beklenen43-None]
- ✅ tarih `[=HOUR("0,5")-12.0-None]
- ✅ tarih `[=HOUR(45351.5)-12.0-None]
- ✅ tarih `[=MINUTE(0.0625)-30.0-None]
- ✅ tarih `[=MINUTE(B1)-0.0-None]
- ✅ tarih `[=MINUTE(#N/A)-beklenen48-None]
- ✅ tarih `[=MINUTE("0,0625")-30.0-None]
- ✅ tarih `[=SECOND(TIME(0,0,45))-45.0-None]
- ✅ tarih `[=SECOND(B1)-0.0-None]
- ✅ tarih `[=SECOND(#N/A)-beklenen52-None]
- ✅ tarih `[=SECOND("0,5")-0.0-None]
- ✅ tarih `[=WEEKDAY(45351)-5.0-None]
- ✅ tarih `[=WEEKDAY(45351,2)-4.0-None]
- ✅ tarih `[=WEEKDAY(45351,3)-3.0-None]
- ✅ tarih `[=WEEKDAY(45351,11)-4.0-None]
- ✅ tarih `[=WEEKDAY(45352)-6.0-None]
- ✅ tarih `[=WEEKDAY(1)-1.0-None]
- ✅ tarih `[=WEEKDAY(B1)-7.0-None]
- ✅ tarih `[=WEEKDAY(#N/A)-beklenen61-None]
- ✅ tarih `[=WEEKDAY(45351,99)-beklenen62-None]
- ✅ tarih `[=WEEKDAY("45351")-5.0-None]
- ✅ tarih `[=WEEKNUM(45292)-1.0-None]
- ✅ tarih `[=WEEKNUM(45657)-53.0-None]
- ✅ tarih `[=WEEKNUM(45657,2)-53.0-None]
- ✅ tarih `[=WEEKNUM(45298,1)-2.0-None]
- ✅ tarih `[=WEEKNUM(45656,21)-1.0-None]
- ✅ tarih `[=WEEKNUM(#N/A)-beklenen69-None]
- ✅ tarih `[=WEEKNUM("45292")-1.0-None]
- ✅ tarih `[=WEEKNUM(45292,5)-beklenen71-None]
- ✅ tarih `[=EDATE(45322,1)-45351.0-None]
- ✅ tarih `[=EDATE(45351,-12)-44985.0-None]
- ✅ tarih `[=EDATE(#N/A,1)-beklenen74-None]
- ✅ tarih `[=EDATE("45351","1")-45380.0-None]
- ✅ tarih `[=EDATE(45351,B1)-45351.0-None]
- ✅ tarih `[=EOMONTH(45351,0)-45351.0-None]
- ✅ tarih `[=EOMONTH(45306,1)-45351.0-None]
- ✅ tarih `[=EOMONTH(45306,2)-45382.0-None]
- ✅ tarih `[=EOMONTH(45351,-1)-45322.0-None]
- ✅ tarih `[=EOMONTH(#N/A,0)-beklenen81-None]
- ✅ tarih `[=EOMONTH("45351","0")-45351.0-None]
- ✅ tarih `[=DATEDIF(43845,45361,"Y")-4.0-None]
- ✅ tarih `[=DATEDIF(43845,45361,"M")-49.0-None]
- ✅ tarih `[=DATEDIF(43845,45361,"D")-1516.0-None]
- ✅ tarih `[=DATEDIF(43845,45361,"MD")-24.0-None]
- ✅ tarih `[=DATEDIF(43845,45361,"YM")-1.0-None]
- ✅ tarih `[=DATEDIF(43845,45361,"YD")-55.0-None]
- ✅ tarih `[=DATEDIF(45361,43845,"Y")-beklenen89-None]
- ✅ tarih `[=DATEDIF(#N/A,45361,"Y")-beklenen90-None]
- ✅ tarih `[=DATEDIF(43845,45361,"Q")-beklenen91-None]
- ✅ tarih `[=DATEDIF("43845","45361","y")-4.0-None]
- ✅ tarih `[=DAYS(45381,45351)-30.0-None]
- ✅ tarih `[=DAYS(B1,B1)-0.0-None]
- ✅ tarih `[=DAYS(#N/A,1)-beklenen95-None]
- ✅ tarih `[=DAYS("45352","45351")-1.0-None]
- ✅ tarih `[=NETWORKDAYS(45292,45298)-5.0-None]
- ✅ tarih `[=NETWORKDAYS(45292,45298,45292)-4.0-None]
- ✅ tarih `[=NETWORKDAYS(45298,45292)--5.0-None]
- ✅ tarih `[=NETWORKDAYS(45292,45298,B1:B3)-5.0-None]
- ✅ tarih `[=NETWORKDAYS(#N/A,45298)-beklenen101-None]
- ✅ tarih `[=NETWORKDAYS("45292","45298")-5.0-None]
- ✅ tarih `[=WORKDAY(45296,1)-45299.0-None]
- ✅ tarih `[=WORKDAY(45292,5)-45299.0-None]
- ✅ tarih `[=WORKDAY(45296,1,45299)-45300.0-None]
- ✅ tarih `[=WORKDAY(45299,-1)-45296.0-None]
- ✅ tarih `[=WORKDAY(#N/A,1)-beklenen107-None]
- ✅ tarih `[=WORKDAY("45296","1")-45299.0-None]
- ✅ arama `[=VLOOKUP(2,A1:B3,2,FALSE)-b-veri0]
- ✅ arama `[=VLOOKUP(2.5,A1:B3,2)-b-veri1]
- ✅ arama `[=VLOOKUP(9,A1:B3,2,FALSE)-beklenen2-veri2]
- ✅ arama `[=VLOOKUP(2,A1:B3,3,FALSE)-beklenen3-veri3]
- ✅ arama `[=VLOOKUP(2,A1:B3,0,FALSE)-beklenen4-veri4]
- ✅ arama `[=VLOOKUP(#N/A,A1:B3,2,FALSE)-beklenen5-veri5]
- ✅ arama `[=VLOOKUP("B",B1:B3,1,FALSE)-b-veri6]
- ✅ arama `[=VLOOKUP("2",A1:B3,2,FALSE)-beklenen7-veri7]
- ✅ arama `[=VLOOKUP(0.5,A1:B3,2)-beklenen8-veri8]
- ✅ arama `[=VLOOKUP(E1,A1:B3,2,FALSE)-beklenen9-veri9]
- ✅ arama `[=VLOOKUP("a*",B1:B3,1,FALSE)-a-veri10]
- ✅ arama `[=VLOOKUP(2,A1:B3,2,0)-b-veri11]
- ✅ arama `[=HLOOKUP(2,A1:C2,2,FALSE)-b-veri12]
- ✅ arama `[=HLOOKUP(2.5,A1:C2,2)-b-veri13]
- ✅ arama `[=HLOOKUP(9,A1:C2,2,FALSE)-beklenen14-veri14]
- ✅ arama `[=HLOOKUP(2,A1:C2,3,FALSE)-beklenen15-veri15]
- ✅ arama `[=HLOOKUP(#N/A,A1:C2,2,FALSE)-beklenen16-veri16]
- ✅ arama `[=HLOOKUP(E1,A1:C2,2,FALSE)-beklenen17-veri17]
- ✅ arama `[=MATCH(2,A1:A3,0)-2.0-veri18]
- ✅ arama `[=MATCH(2.5,A1:A3,1)-2.0-veri19]
- ✅ arama `[=MATCH(2.5,A1:A3,0)-beklenen20-veri20]
- ✅ arama `[=MATCH("b",B1:B3,0)-2.0-veri21]
- ✅ arama `[=MATCH(#N/A,A1:A3,0)-beklenen22-veri22]
- ✅ arama `[=MATCH(5,E1:E3,0)-beklenen23-veri23]
- ✅ arama `[=MATCH("B*",B1:B3,0)-2.0-veri24]
- ✅ arama `[=MATCH(2,A1:B3,0)-beklenen25-veri25]
- ✅ arama `[=MATCH(2,C1:C3,-1)-beklenen26-veri26]
- ✅ arama `[=MATCH(2,A3:A1,-1)-beklenen27-veri27]
- ✅ arama `[=XMATCH(2,A1:A3)-2.0-veri28]
- ✅ arama `[=XMATCH(2.5,A1:A3,-1)-2.0-veri29]
- ✅ arama `[=XMATCH(2.5,A1:A3,1)-3.0-veri30]
- ✅ arama `[=XMATCH("b*",B1:B3,2)-2.0-veri31]
- ✅ arama `[=XMATCH(9,A1:A3)-beklenen32-veri32]
- ✅ arama `[=XMATCH(#N/A,A1:A3)-beklenen33-veri33]
- ✅ arama `[=XMATCH(1,A1:A3,0,-1)-1.0-veri34]
- ✅ arama `[=XMATCH(1,E1:E3)-beklenen35-veri35]
- ✅ arama `[=XLOOKUP(2,A1:A3,B1:B3)-b-veri36]
- ✅ arama `[=XLOOKUP(9,A1:A3,B1:B3,"yok")-yok-veri37]
- ✅ arama `[=XLOOKUP(9,A1:A3,B1:B3)-beklenen38-veri38]
- ✅ arama `[=XLOOKUP(2.5,A1:A3,B1:B3,,-1)-b-veri39]
- ✅ arama `[=XLOOKUP(2,A1:A3,B1:B2)-beklenen40-veri40]
- ✅ arama `[=XLOOKUP(#N/A,A1:A3,B1:B3)-beklenen41-veri41]
- ✅ arama `[=XLOOKUP("B",B1:B3,A1:A3)-2.0-veri42]
- ✅ arama `[=XLOOKUP(2,A1:C1,A2:C2)-b-veri43]
- ✅ arama `[=INDEX(A1:A3,2)-2.0-veri44]
- ✅ arama `[=INDEX(A1:B3,3,2)-c-veri45]
- ✅ arama `[=SUM(INDEX(A1:B3,0,1))-6.0-veri46]
- ✅ arama `[=INDEX(A1:A3,5)-beklenen47-veri47]
- ✅ arama `[=INDEX(A1:C1,2)-2.0-veri48]
- ✅ arama `[=INDEX(A1:A3,#N/A)-beklenen49-veri49]
- ✅ arama `[=INDEX(A1:A3,"2")-2.0-veri50]
- ✅ arama `[=INDEX(A1:A3,-1)-beklenen51-veri51]
- ✅ arama `[=INDEX(E1:E3,2)-0.0-veri52]
- ✅ arama `[=CHOOSE(2,"a","b","c")-b-None]
- ✅ arama `[=CHOOSE(4,"a","b","c")-beklenen54-None]
- ✅ arama `[=CHOOSE(B1,"a","b")-beklenen55-None]
- ✅ arama `[=CHOOSE(#N/A,1)-beklenen56-None]
- ✅ arama `[=CHOOSE("2",10,20)-20.0-None]
- ✅ arama `[=SUM(CHOOSE(1,A1:A3))-6.0-veri58]
- ✅ arama `[=ROW()-20.0-None]
- ✅ arama `[=ROW(A5)-5.0-None]
- ✅ arama `[=ROW(A2:A3)-2.0-None]
- ✅ arama `[=ROW(B9)-9.0-None]
- ✅ arama `[=ROW("a")-beklenen63-None]
- ✅ arama `[=ROW(#N/A)-beklenen64-None]
- ✅ arama `[=SUM(ROW(A1:A3))-6.0-None]
- ✅ arama `[=COLUMN()-20.0-None]
- ✅ arama `[=COLUMN(C1)-3.0-None]
- ✅ arama `[=COLUMN(B1:D1)-2.0-None]
- ✅ arama `[=COLUMN(E9)-5.0-None]
- ✅ arama `[=COLUMN("a")-beklenen70-None]
- ✅ arama `[=COLUMN(#N/A)-beklenen71-None]
- ✅ arama `[=SUM(COLUMN(A1:C1))-6.0-None]
- ✅ arama `[=ROWS(A1:A3)-3.0-None]
- ✅ arama `[=ROWS(A1:C1)-1.0-None]
- ✅ arama `[=ROWS(B1:B9)-9.0-None]
- ✅ arama `[=ROWS(5)-1.0-None]
- ✅ arama `[=ROWS({1;2;3})-3.0-None]
- ✅ arama `[=ROWS(#N/A)-beklenen78-None]
- ✅ arama `[=COLUMNS(A1:C1)-3.0-None]
- ✅ arama `[=COLUMNS(A1:A3)-1.0-None]
- ✅ arama `[=COLUMNS(B1:D9)-3.0-None]
- ✅ arama `[=COLUMNS(5)-1.0-None]
- ✅ arama `[=COLUMNS({1,2,3})-3.0-None]
- ✅ arama `[=COLUMNS(#N/A)-beklenen84-None]
- ✅ arama `[=INDIRECT("A2")-2.0-veri85]
- ✅ arama `[=INDIRECT("A"&3)-3.0-veri86]
- ✅ arama `[=SUM(INDIRECT("A1:A3"))-6.0-veri87]
- ✅ arama `[=INDIRECT("zzz")-beklenen88-veri88]
- ✅ arama `[=INDIRECT(B9)-beklenen89-veri89]
- ✅ arama `[=INDIRECT(#N/A)-beklenen90-veri90]
- ✅ arama `[=INDIRECT("A1",FALSE)-beklenen91-veri91]
- ✅ arama `[=INDIRECT("$A$2")-2.0-veri92]
- ✅ arama `[=INDIRECT("Yok!A1")-beklenen93-veri93]
- ✅ arama `[=OFFSET(A1,1,0)-2.0-veri94]
- ✅ arama `[=SUM(OFFSET(A1,0,0,3,1))-6.0-veri95]
- ✅ arama `[=OFFSET(A1,-1,0)-beklenen96-veri96]
- ✅ arama `[=OFFSET(A1,0,1)-a-veri97]
- ✅ arama `[=OFFSET(A1,#N/A,0)-beklenen98-veri98]
- ✅ arama `[=OFFSET("a",1,1)-beklenen99-veri99]
- ✅ arama `[=OFFSET(E9,0,0)-0.0-veri100]
- ✅ arama `[=SUM(OFFSET(A1:A2,1,0))-5.0-veri101]
- ✅ finans `[=PMT(0.08/12,10,10000)--1037.0320893591636-None]
- ✅ finans `[=PMT(0,10,1000)--100.0-None]
- ✅ finans `[=PMT(0.1,0,100)-beklenen2-None]
- ✅ finans `[=PMT(B1,12,1200)--100.0-None]
- ✅ finans `[=PMT(#N/A,12,1000)-beklenen4-None]
- ✅ finans `[=PMT("0,01","12","1000")--88.84878867834166-None]
- ✅ finans `[=FV(0.06/12,10,-200,-500,1)-2581.4033740601362-None]
- ✅ finans `[=FV(0,10,-100)-1000.0-None]
- ✅ finans `[=FV(B1,10,-100)-1000.0-None]
- ✅ finans `[=FV(#N/A,10,-100)-beklenen9-None]
- ✅ finans `[=FV("0,01","12","-100")-1268.2503013196979-None]
- ✅ finans `[=PV(0.08/12,240,500,0,0)--59777.14585118777-None]
- ✅ finans `[=PV(0,10,100)--1000.0-None]
- ✅ finans `[=PV(B1,10,100)--1000.0-None]
- ✅ finans `[=PV(#N/A,10,100)-beklenen14-None]
- ✅ finans `[=PV("0","10","100")--1000.0-None]
- ✅ finans `[=RATE(48,-200,8000)-0.00770147248820207-None]
- ✅ finans `[=RATE(10,0,-100,200)-0.07177346253629313-None]
- ✅ finans `[=RATE(#N/A,-200,8000)-beklenen18-None]
- ✅ finans `[=RATE("48","-200","8000")-0.00770147248820207-None]
- ✅ finans `[=RATE(10,100,100)-beklenen20-None]
- ✅ finans `[=NPV(0.1,-10000,3000,4200,6800)-1188.4434123352216-None]
- ✅ finans `[=NPV(0.1,A1:A4)-1188.4434123352216-veri22]
- ✅ finans `[=NPV(0.1,B1:B3)-0.0-None]
- ✅ finans `[=NPV(0.1,A1:A3)-beklenen24-veri24]
- ✅ finans `[=NPV(0.1,"100",A1:A2)-114.19984973703983-veri25]
- ✅ finans `[=NPV(-1,100)-beklenen26-None]
- ✅ finans `[=IRR(A1:A6)-0.0866309480365316-veri27]
- ✅ finans `[=IRR(A1:A5)--0.021244848273410947-veri28]
- ✅ finans `[=IRR(A1:A3)-beklenen29-veri29]
- ✅ finans `[=IRR(B1:B3)-beklenen30-None]
- ✅ finans `[=IRR(A1:A3)-beklenen31-veri31]
- ✅ finans `[=IRR(A1:A3,0.5)-1.0-veri32]
- ✅ kayitli her fonksiyonun turkce adi var
- ✅ dolayli baska sayfa

### `testler/test_fonk_sayisal.py` — 306/306 ✅
*115 fonksiyonun sayısal/mantık/istatistik/arama/finans grupları (kural 11: 4+ vaka)*

- ✅ matematik `[=SUM(A1:A3)-60.0-veri0]
- ✅ matematik `[=SUM(B1:B3)-0.0-veri1]
- ✅ matematik `[=SUM(A1:A3)-beklenen2-veri2]
- ✅ matematik `[=SUM(A1:A4,"5",TRUE)-66.0-veri3]
- ✅ matematik `[=ROUND(2.675,2)-2.68-None]
- ✅ matematik `[=ROUND(-2.5,0)--3.0-None]
- ✅ matematik `[=ROUND(1234.567,-2)-1200.0-None]
- ✅ matematik `[=ROUND(B1,0)-0.0-None]
- ✅ matematik `[=ROUND(#N/A,1)-beklenen8-None]
- ✅ matematik `[=ROUND("2,567",1)-2.6-None]
- ✅ matematik `[=ROUND(TRUE,0)-1.0-None]
- ✅ matematik `[=ROUNDUP(3.2,0)-4.0-None]
- ✅ matematik `[=ROUNDUP(-3.2,0)--4.0-None]
- ✅ matematik `[=ROUNDUP(31415.92654,-2)-31500.0-None]
- ✅ matematik `[=ROUNDUP(B1,0)-0.0-None]
- ✅ matematik `[=ROUNDUP(#N/A,0)-beklenen15-None]
- ✅ matematik `[=ROUNDUP("3,14159",3)-3.142-None]
- ✅ matematik `[=ROUNDDOWN(3.14159,3)-3.141-None]
- ✅ matematik `[=ROUNDDOWN(-3.14159,1)--3.1-None]
- ✅ matematik `[=ROUNDDOWN(31415.92654,-2)-31400.0-None]
- ✅ matematik `[=ROUNDDOWN(B1,0)-0.0-None]
- ✅ matematik `[=ROUNDDOWN(#N/A,0)-beklenen21-None]
- ✅ matematik `[=ROUNDDOWN("9,99",1)-9.9-None]
- ✅ matematik `[=TRUNC(8.9)-8.0-None]
- ✅ matematik `[=TRUNC(-8.9)--8.0-None]
- ✅ matematik `[=TRUNC(PI(),3)-3.141-None]
- ✅ matematik `[=TRUNC(B1)-0.0-None]
- ✅ matematik `[=TRUNC(#N/A)-beklenen27-None]
- ✅ matematik `[=TRUNC("4,56",1)-4.5-None]
- ✅ matematik `[=INT(8.9)-8.0-None]
- ✅ matematik `[=INT(-8.9)--9.0-None]
- ✅ matematik `[=INT(B1)-0.0-None]
- ✅ matematik `[=INT(#N/A)-beklenen32-None]
- ✅ matematik `[=INT("3,7")-3.0-None]
- ✅ matematik `[=MOD(3,2)-1.0-None]
- ✅ matematik `[=MOD(-3,2)-1.0-None]
- ✅ matematik `[=MOD(3,-2)--1.0-None]
- ✅ matematik `[=MOD(3,0)-beklenen37-None]
- ✅ matematik `[=MOD(B1,3)-0.0-None]
- ✅ matematik `[=MOD(#N/A,2)-beklenen39-None]
- ✅ matematik `[=MOD("10",3)-1.0-None]
- ✅ matematik `[=ABS(-4)-4.0-None]
- ✅ matematik `[=ABS(B1)-0.0-None]
- ✅ matematik `[=ABS(#N/A)-beklenen43-None]
- ✅ matematik `[=ABS("-2,5")-2.5-None]
- ✅ matematik `[=ABS(TRUE)-1.0-None]
- ✅ matematik `[=SQRT(16)-4.0-None]
- ✅ matematik `[=SQRT(-1)-beklenen47-None]
- ✅ matematik `[=SQRT(B1)-0.0-None]
- ✅ matematik `[=SQRT(#N/A)-beklenen49-None]
- ✅ matematik `[=SQRT("9")-3.0-None]
- ✅ matematik `[=POWER(5,2)-25.0-None]
- ✅ matematik `[=POWER(0,0)-beklenen52-None]
- ✅ matematik `[=POWER(B1,2)-0.0-None]
- ✅ matematik `[=POWER(#N/A,2)-beklenen54-None]
- ✅ matematik `[=POWER("2","3")-8.0-None]
- ✅ matematik `[=PI()-3.141592653589793-None]
- ✅ matematik `[=PI()+B1-3.141592653589793-None]
- ✅ matematik `[=PI()+#N/A-beklenen58-None]
- ✅ matematik `[=PI()+"1"-4.141592653589793-None]
- ✅ matematik `[=RAND()<1-True-None]
- ✅ matematik `[=RAND()>=0-True-None]
- ✅ matematik `[=RAND()+#N/A-beklenen62-None]
- ✅ matematik `[=RAND()*0+"2"-2.0-None]
- ✅ matematik `[=RANDBETWEEN(5,5)-5.0-None]
- ✅ matematik `[=RANDBETWEEN(1,10)>=1-True-None]
- ✅ matematik `[=RANDBETWEEN(B1,B1)-0.0-None]
- ✅ matematik `[=RANDBETWEEN(#N/A,1)-beklenen67-None]
- ✅ matematik `[=RANDBETWEEN("3",3)-3.0-None]
- ✅ matematik `[=RANDBETWEEN(5,1)-beklenen69-None]
- ✅ matematik `[=CEILING(2.5,1)-3.0-None]
- ✅ matematik `[=CEILING(-2.5,-2)--4.0-None]
- ✅ matematik `[=CEILING(-2.5,2)--2.0-None]
- ✅ matematik `[=CEILING(2.5,-1)-beklenen73-None]
- ✅ matematik `[=CEILING(1.5,0)-0.0-None]
- ✅ matematik `[=CEILING(0.234,0.01)-0.24-None]
- ✅ matematik `[=CEILING(B1,1)-0.0-None]
- ✅ matematik `[=CEILING(#N/A,1)-beklenen77-None]
- ✅ matematik `[=CEILING("1,5","1")-2.0-None]
- ✅ matematik `[=FLOOR(3.7,2)-2.0-None]
- ✅ matematik `[=FLOOR(-2.5,2)--4.0-None]
- ✅ matematik `[=FLOOR(-2.5,-2)--2.0-None]
- ✅ matematik `[=FLOOR(2.5,-1)-beklenen82-None]
- ✅ matematik `[=FLOOR(1,0)-beklenen83-None]
- ✅ matematik `[=FLOOR(0,0)-0.0-None]
- ✅ matematik `[=FLOOR(B1,1)-0.0-None]
- ✅ matematik `[=FLOOR(#N/A,1)-beklenen86-None]
- ✅ matematik `[=FLOOR("3,7","2")-2.0-None]
- ✅ matematik `[=SIGN(10)-1.0-None]
- ✅ matematik `[=SIGN(-0.1)--1.0-None]
- ✅ matematik `[=SIGN(B1)-0.0-None]
- ✅ matematik `[=SIGN(#N/A)-beklenen91-None]
- ✅ matematik `[=SIGN("-3")--1.0-None]
- ✅ matematik `[=EXP(1)-2.718281828459045-None]
- ✅ matematik `[=EXP(0)-1.0-None]
- ✅ matematik `[=EXP(B1)-1.0-None]
- ✅ matematik `[=EXP(#N/A)-beklenen96-None]
- ✅ matematik `[=EXP("1")-2.718281828459045-None]
- ✅ matematik `[=EXP(1000)-beklenen98-None]
- ✅ matematik `[=LN(86)-4.454347296253507-None]
- ✅ matematik `[=LN(1)-0.0-None]
- ✅ matematik `[=LN(0)-beklenen101-None]
- ✅ matematik `[=LN(B1)-beklenen102-None]
- ✅ matematik `[=LN(#N/A)-beklenen103-None]
- ✅ matematik `[=LN("2,718281828459045")-1.0-None]
- ✅ matematik `[=LOG(10)-1.0-None]
- ✅ matematik `[=LOG(8,2)-3.0-None]
- ✅ matematik `[=LOG(0)-beklenen107-None]
- ✅ matematik `[=LOG(10,1)-beklenen108-None]
- ✅ matematik `[=LOG(B1)-beklenen109-None]
- ✅ matematik `[=LOG(#N/A)-beklenen110-None]
- ✅ matematik `[=LOG("100","10")-2.0-None]
- ✅ matematik `[=LOG10(100)-2.0-None]
- ✅ matematik `[=LOG10(0)-beklenen113-None]
- ✅ matematik `[=LOG10(#N/A)-beklenen114-None]
- ✅ matematik `[=LOG10("1000")-3.0-None]
- ✅ matematik `[=LOG10(B1)-beklenen116-None]
- ✅ matematik `[=PRODUCT(A1:A3)-6000.0-veri117]
- ✅ matematik `[=PRODUCT(A1:A4)-6000.0-veri118]
- ✅ matematik `[=PRODUCT(B1:B3)-0.0-veri119]
- ✅ matematik `[=PRODUCT(A1:A3)-beklenen120-veri120]
- ✅ matematik `[=PRODUCT(A1:A2,"2",TRUE)-400.0-veri121]
- ✅ matematik `[=SUMIF(A1:A4,">15")-50.0-veri122]
- ✅ matematik `[=SUMIF(A1:A3,">15",C1:C3)-0.0-veri123]
- ✅ matematik `[=SUMIF(B1:B3,">1")-0.0-veri124]
- ✅ matematik `[=SUMIF(A1:A3,">5",B1:B3)-beklenen125-veri125]
- ✅ matematik `[=SUMIF(A1:A3,"a",C1:C3)-4.0-veri126]
- ✅ matematik `[=SUMIF(A1:A3,"A*",C1:C3)-4.0-veri127]
- ✅ matematik `[=SUMIF(A1:A3,20)-20.0-veri128]
- ✅ matematik `[=SUMIF(A1:A4,"<>x")-60.0-veri129]
- ✅ matematik `[=SUMIFS(C1:C3,A1:A3,"a",C1:C3,">1")-3.0-veri130]
- ✅ matematik `[=SUMIFS(E1:E3,F1:F3,">1")-0.0-None]
- ✅ matematik `[=SUMIFS(B1:B3,A1:A3,">5")-beklenen132-veri132]
- ✅ matematik `[=SUMIFS(C1:C3,A1:A2,"a")-beklenen133-veri133]
- ✅ matematik `[=SUMPRODUCT(A1:A3,C1:C3)-140.0-veri134]
- ✅ matematik `[=SUMPRODUCT(A1:A3)-60.0-veri135]
- ✅ matematik `[=SUMPRODUCT(A1:A3,C1:C3)-14.0-veri136]
- ✅ matematik `[=SUMPRODUCT(E1:E3,F1:F3)-0.0-None]
- ✅ matematik `[=SUMPRODUCT(A1:A3,C1:C3)-beklenen138-veri138]
- ✅ matematik `[=SUMPRODUCT(A1:A3,C1:C2)-beklenen139-veri139]
- ✅ matematik `[=SUMPRODUCT(--(A1:A3>1))-2.0-veri140]
- ✅ istatistik `[=AVERAGE(A1:A3)-20.0-veri0]
- ✅ istatistik `[=AVERAGE(B1:B3)-beklenen1-veri1]
- ✅ istatistik `[=AVERAGE(A1:A3)-beklenen2-veri2]
- ✅ istatistik `[=AVERAGE(A1:A4,"5",TRUE)-13.2-veri3]
- ✅ istatistik `[=COUNT(A1:A4)-3.0-veri4]
- ✅ istatistik `[=COUNT(B1:B3)-0.0-veri5]
- ✅ istatistik `[=COUNT(A1:A3)-2.0-veri6]
- ✅ istatistik `[=COUNT(A1:A6,"5","x",TRUE,1)-6.0-veri7]
- ✅ istatistik `[=COUNTA(A1:A5)-4.0-veri8]
- ✅ istatistik `[=COUNTA(B1:B3)-0.0-veri9]
- ✅ istatistik `[=COUNTA(A1:A3)-3.0-veri10]
- ✅ istatistik `[=COUNTA(A1:A6,"")-6.0-veri11]
- ✅ istatistik `[=COUNTBLANK(A1:A6)-1.0-veri12]
- ✅ istatistik `[=COUNTBLANK(B1:B3)-3.0-veri13]
- ✅ istatistik `[=COUNTBLANK(A1:A3)-0.0-veri14]
- ✅ istatistik `[=COUNTBLANK(A1:A5)-1.0-veri15]
- ✅ istatistik `[=COUNTIF(A1:A4,">15")-2.0-veri16]
- ✅ istatistik `[=COUNTIF(B1:B3,">0")-0.0-veri17]
- ✅ istatistik `[=COUNTIF(B1:B3,"")-3.0-veri18]
- ✅ istatistik `[=COUNTIF(A1:A3,">5")-2.0-veri19]
- ✅ istatistik `[=COUNTIF(A1:A3,"#N/A")-1.0-veri20]
- ✅ istatistik `[=COUNTIF(A1:A6,"x")-1.0-veri21]
- ✅ istatistik `[=COUNTIF(A1:A6,TRUE)-1.0-veri22]
- ✅ istatistik `[=COUNTIF(A1:A4,"<>x")-3.0-veri23]
- ✅ istatistik `[=COUNTIF(A1:A4,"?")-1.0-veri24]
- ✅ istatistik `[=COUNTIF(A1:A4,10)-1.0-veri25]
- ✅ istatistik `[=COUNTIFS(A1:A3,">5",C1:C3,"<3")-2.0-veri26]
- ✅ istatistik `[=COUNTIFS(E1:E3,">5")-0.0-None]
- ✅ istatistik `[=COUNTIFS(A1:A3,">5")-2.0-veri28]
- ✅ istatistik `[=COUNTIFS(A1:A3,">5",C1:C2,"<3")-beklenen29-veri29]
- ✅ istatistik `[=MAX(A1:A4)-30.0-veri30]
- ✅ istatistik `[=MAX(B1:B3)-0.0-veri31]
- ✅ istatistik `[=MAX(A1:A3)-beklenen32-veri32]
- ✅ istatistik `[=MAX(A1:A4,"50")-50.0-veri33]
- ✅ istatistik `[=MAX(A1:A4,TRUE)-30.0-veri34]
- ✅ istatistik `[=MIN(A1:A4)-10.0-veri35]
- ✅ istatistik `[=MIN(B1:B3)-0.0-veri36]
- ✅ istatistik `[=MIN(A1:A3)-beklenen37-veri37]
- ✅ istatistik `[=MIN(A1:A4,"5")-5.0-veri38]
- ✅ istatistik `[=MIN(A1:A4,TRUE)-1.0-veri39]
- ✅ istatistik `[=MAXIFS(C1:C3,A1:A3,">10")-3.0-veri40]
- ✅ istatistik `[=MAXIFS(E1:E3,F1:F3,">1")-0.0-None]
- ✅ istatistik `[=MAXIFS(B1:B3,A1:A3,">5")-beklenen42-veri42]
- ✅ istatistik `[=MAXIFS(C1:C3,A1:A2,">5")-beklenen43-veri43]
- ✅ istatistik `[=MINIFS(C1:C3,A1:A3,">10")-2.0-veri44]
- ✅ istatistik `[=MINIFS(E1:E3,F1:F3,">1")-0.0-None]
- ✅ istatistik `[=MINIFS(B1:B3,A1:A3,">5")-beklenen46-veri46]
- ✅ istatistik `[=MINIFS(C1:C3,A1:A3,"x")-0.0-veri47]
- ✅ istatistik `[=MEDIAN(A1:A3)-20.0-veri48]
- ✅ istatistik `[=MEDIAN(1,2,3,4)-2.5-None]
- ✅ istatistik `[=MEDIAN(B1:B3)-beklenen50-veri50]
- ✅ istatistik `[=MEDIAN(A1:A3)-beklenen51-veri51]
- ✅ istatistik `[=MEDIAN(A1:A4,"100")-25.0-veri52]
- ✅ istatistik `[=MODE(1,2,2,3)-2.0-None]
- ✅ istatistik `[=MODE(1,2,3)-beklenen54-None]
- ✅ istatistik `[=MODE(B1:B3)-beklenen55-veri55]
- ✅ istatistik `[=MODE(A1:A3)-beklenen56-veri56]
- ✅ istatistik `[=MODE(A1:A4,"20")-20.0-veri57]
- ✅ istatistik `[=STDEV(2,4,4,4,5,5,7,9)-2.138089935299395-None]
- ✅ istatistik `[=STDEV(5)-beklenen59-None]
- ✅ istatistik `[=STDEV(B1:B3)-beklenen60-veri60]
- ✅ istatistik `[=STDEV(A1:A3)-beklenen61-veri61]
- ✅ istatistik `[=STDEV(A1:A4)-10.0-veri62]
- ✅ istatistik `[=VAR(2,4,4,4,5,5,7,9)-4.571428571428571-None]
- ✅ istatistik `[=VAR(1)-beklenen64-None]
- ✅ istatistik `[=VAR(B1:B3)-beklenen65-veri65]
- ✅ istatistik `[=VAR(A1:A3)-beklenen66-veri66]
- ✅ istatistik `[=VAR(A1:A4)-100.0-veri67]
- ✅ istatistik `[=LARGE(A1:A3,1)-30.0-veri68]
- ✅ istatistik `[=LARGE(A1:A3,2)-20.0-veri69]
- ✅ istatistik `[=LARGE(A1:A3,4)-beklenen70-veri70]
- ✅ istatistik `[=LARGE(B1:B3,1)-beklenen71-veri71]
- ✅ istatistik `[=LARGE(A1:A3,1)-beklenen72-veri72]
- ✅ istatistik `[=LARGE(A1:A4,2)-20.0-veri73]
- ✅ istatistik `[=SMALL(A1:A3,1)-10.0-veri74]
- ✅ istatistik `[=SMALL(A1:A3,3)-30.0-veri75]
- ✅ istatistik `[=SMALL(A1:A3,0)-beklenen76-veri76]
- ✅ istatistik `[=SMALL(B1:B3,1)-beklenen77-veri77]
- ✅ istatistik `[=SMALL(A1:A3,1)-beklenen78-veri78]
- ✅ istatistik `[=SMALL(A1:A4,2)-20.0-veri79]
- ✅ istatistik `[=RANK(20,A1:A3)-2.0-veri80]
- ✅ istatistik `[=RANK(20,A1:A3,1)-2.0-veri81]
- ✅ istatistik `[=RANK(10,A1:A3,1)-1.0-veri82]
- ✅ istatistik `[=RANK(99,A1:A3)-beklenen83-veri83]
- ✅ istatistik `[=RANK(20,B1:B3)-beklenen84-veri84]
- ✅ istatistik `[=RANK(20,A1:A3)-beklenen85-veri85]
- ✅ istatistik `[=RANK("20",A1:A4)-2.0-veri86]
- ✅ mantik bilgi `[=IFS(FALSE,1,TRUE,2)-2.0-None]
- ✅ mantik bilgi `[=IFS(FALSE,1)-beklenen1-None]
- ✅ mantik bilgi `[=IFS(B1,1,TRUE,2)-2.0-None]
- ✅ mantik bilgi `[=IFS(#N/A,1)-beklenen3-None]
- ✅ mantik bilgi `[=IFS("TRUE",1)-1.0-None]
- ✅ mantik bilgi `[=AND(TRUE,TRUE)-True-None]
- ✅ mantik bilgi `[=AND(TRUE,FALSE)-False-None]
- ✅ mantik bilgi `[=AND(B1:B3)-beklenen7-None]
- ✅ mantik bilgi `[=AND(TRUE,#N/A)-beklenen8-None]
- ✅ mantik bilgi `[=AND(A1:A4)-True-veri9]
- ✅ mantik bilgi `[=AND(1,"x")-beklenen10-None]
- ✅ mantik bilgi `[=OR(FALSE,TRUE)-True-None]
- ✅ mantik bilgi `[=OR(FALSE,0)-False-None]
- ✅ mantik bilgi `[=OR(B1:B3)-beklenen13-None]
- ✅ mantik bilgi `[=OR(FALSE,#N/A)-beklenen14-None]
- ✅ mantik bilgi `[=OR(A1:A4)-True-veri15]
- ✅ mantik bilgi `[=OR(0,"x")-beklenen16-None]
- ✅ mantik bilgi `[=XOR(TRUE,FALSE)-True-None]
- ✅ mantik bilgi `[=XOR(TRUE,TRUE)-False-None]
- ✅ mantik bilgi `[=XOR(B1:B3)-beklenen19-None]
- ✅ mantik bilgi `[=XOR(TRUE,#N/A)-beklenen20-None]
- ✅ mantik bilgi `[=XOR(A1:A4)-True-veri21]
- ✅ mantik bilgi `[=NOT(TRUE)-False-None]
- ✅ mantik bilgi `[=NOT(0)-True-None]
- ✅ mantik bilgi `[=NOT(B1)-True-None]
- ✅ mantik bilgi `[=NOT(#N/A)-beklenen25-None]
- ✅ mantik bilgi `[=NOT("x")-beklenen26-None]
- ✅ mantik bilgi `[=NOT("TRUE")-False-None]
- ✅ mantik bilgi `[=TRUE()-True-None]
- ✅ mantik bilgi `[=FALSE()-False-None]
- ✅ mantik bilgi `[=TRUE()+1-2.0-None]
- ✅ mantik bilgi `[=FALSE()+#N/A-beklenen31-None]
- ✅ mantik bilgi `[=TRUE()&""-DO\u011eRU-None]
- ✅ mantik bilgi `[=IFERROR(1/0,"h")-h-None]
- ✅ mantik bilgi `[=IFERROR(5,"h")-5.0-None]
- ✅ mantik bilgi `[=IFERROR(B1,"h")-0.0-None]
- ✅ mantik bilgi `[=IFERROR(#N/A,B2)-0.0-None]
- ✅ mantik bilgi `[=IFERROR("a"+1,"bad")-bad-None]
- ✅ mantik bilgi `[=IFNA(#N/A,1)-1.0-None]
- ✅ mantik bilgi `[=IFNA(1/0,1)-beklenen39-None]
- ✅ mantik bilgi `[=IFNA(B1,5)-0.0-None]
- ✅ mantik bilgi `[=IFNA(2,3)-2.0-None]
- ✅ mantik bilgi `[=SWITCH(2,1,"a",2,"b","z")-b-None]
- ✅ mantik bilgi `[=SWITCH(9,1,"a","z")-z-None]
- ✅ mantik bilgi `[=SWITCH(9,1,"a")-beklenen44-None]
- ✅ mantik bilgi `[=SWITCH(B1,0,"zero","x")-zero-None]
- ✅ mantik bilgi `[=SWITCH(#N/A,1,2)-beklenen46-None]
- ✅ mantik bilgi `[=SWITCH("A","a",1)-1.0-None]
- ✅ mantik bilgi `[=ISNUMBER(1)-True-None]
- ✅ mantik bilgi `[=ISNUMBER("1")-False-None]
- ✅ mantik bilgi `[=ISNUMBER(B1)-False-None]
- ✅ mantik bilgi `[=ISNUMBER(#N/A)-False-None]
- ✅ mantik bilgi `[=ISNUMBER(TRUE)-False-None]
- ✅ mantik bilgi `[=ISTEXT("a")-True-None]
- ✅ mantik bilgi `[=ISTEXT(1)-False-None]
- ✅ mantik bilgi `[=ISTEXT(B1)-False-None]
- ✅ mantik bilgi `[=ISTEXT(#N/A)-False-None]
- ✅ mantik bilgi `[=ISBLANK(B1)-True-None]
- ✅ mantik bilgi `[=ISBLANK(A1)-False-veri58]
- ✅ mantik bilgi `[=ISBLANK("")-False-None]
- ✅ mantik bilgi `[=ISBLANK(#N/A)-False-None]
- ✅ mantik bilgi `[=ISERROR(1/0)-True-None]
- ✅ mantik bilgi `[=ISERROR(1)-False-None]
- ✅ mantik bilgi `[=ISERROR(B1)-False-None]
- ✅ mantik bilgi `[=ISERROR("a"+1)-True-None]
- ✅ mantik bilgi `[=ISERROR(#N/A)-True-None]
- ✅ mantik bilgi `[=ISNA(#N/A)-True-None]
- ✅ mantik bilgi `[=ISNA(1/0)-False-None]
- ✅ mantik bilgi `[=ISNA(1)-False-None]
- ✅ mantik bilgi `[=ISNA(B1)-False-None]
- ✅ mantik bilgi `[=ISLOGICAL(TRUE)-True-None]
- ✅ mantik bilgi `[=ISLOGICAL(1)-False-None]
- ✅ mantik bilgi `[=ISLOGICAL(B1)-False-None]
- ✅ mantik bilgi `[=ISLOGICAL(#N/A)-False-None]
- ✅ mantik bilgi `[=ISLOGICAL("TRUE")-False-None]
- ✅ mantik bilgi `[=SUMPRODUCT(--ISNUMBER(A1:A4))-3.0-veri75]
- ✅ olcut sozdizimi
- ✅ vektor yayma

### `testler/test_formul_arayuz.py` — 7/7 ✅
*Formül motorunun arayüze bağlanması: hesap, Türkçe görünüm, hatalı formülde düzenleme açık kalır*

- ✅ formul yazinca hesaplanir
- ✅ bagimli hucre guncellenir ve geri al
- ✅ f2 turkce gosterir
- ✅ hatali formul duzenleme acik kalir
- ✅ formul cubugundan hatali
- ✅ baska sayfa formulu
- ✅ hata sonucu turkce cizilir

### `testler/test_formul_ayristir.py` — 37/37 ✅
*Formül sözcükleyici ve ayrıştırıcı: öncelik, kesişim, dizi sabiti, hatalar*

- ✅ gidis donus birebir `[SUM(A1:A3, 2.5)]
- ✅ gidis donus birebir `[  A1 +  $B$2 ]
- ✅ gidis donus birebir `[IF(A1>0,"a ""b""",FALSE)]
- ✅ gidis donus birebir `['Gelir Gider'!A1:B2*2]
- ✅ gidis donus birebir `[{1,2;3,4}]
- ✅ gidis donus birebir `[-2^2%]
- ✅ gidis donus birebir `[A:A]
- ✅ gidis donus birebir `[1:1]
- ✅ gidis donus birebir `[Sayfa2!$A$1]
- ✅ gidis donus birebir `[#DIV/0!+1]
- ✅ tr gidis donus
- ✅ sayilar yerele gore
- ✅ metin kacisli tirnak
- ✅ kapanmamis tirnak
- ✅ basvuru turleri
- ✅ fonksiyon adi hucre gibi
- ✅ sayfa onekleri
- ✅ sayfa oneki yaz
- ✅ hata sabitleri
- ✅ dizi ayiricilari tr
- ✅ konumlar
- ✅ oncelik
- ✅ parantez ve cagri
- ✅ bos argumanlar
- ✅ mantiksal ve ad
- ✅ kesisim ve aralik islec
- ✅ dizi sabiti
- ✅ sozdizimi hatalari `[]
- ✅ sozdizimi hatalari `[1+]
- ✅ sozdizimi hatalari `[(1]
- ✅ sozdizimi hatalari `[1)]
- ✅ sozdizimi hatalari `[SUM(1]
- ✅ sozdizimi hatalari `[SUM(1 2]
- ✅ sozdizimi hatalari `[*1]
- ✅ sozdizimi hatalari `[{1,]
- ✅ hata sabiti dugumu
- ✅ formul esittir ile

### `testler/test_gecmis_sayfa_gecisi.py` — 4/4 ✅
*Geri al/yinele sayfa geçişi (6f): yalnız asıl değişikliğin sayfasına*

- ✅ satir ekle geri al asil sayfaya gider
- ✅ yan etki baska sayfaya gecirmez — Sayfa1'deyken satır eklemeyi geri al: Sayfa2'deki formül düzeltmesi pencereyi Sayfa2'ye götürmez.
- ✅ kes yapistir geri al kaynak yinele hedef
- ✅ ana sayfa komut turleri

### `testler/test_girdi.py` — 42/42 ✅
*Girdi çözümleyici: yazılan metin → sayı/mantıksal/formül/metin (Türkçe yerel ayar)*

- ✅ sayilar `[12-12.0]
- ✅ sayilar `[-3--3.0]
- ✅ sayilar `[+4-4.0]
- ✅ sayilar `[1,5-1.5]
- ✅ sayilar `[,5-0.5]
- ✅ sayilar `[5,-5.0]
- ✅ sayilar `[1.500-1500.0]
- ✅ sayilar `[1.234.567,89-1234567.89]
- ✅ sayilar `[1E3-1000.0]
- ✅ sayilar `[1,5E-2-0.015]
- ✅ sayilar `[  7  -7.0]
- ✅ sayi degil `[]
- ✅ sayi degil `[,]
- ✅ sayi degil `[-]
- ✅ sayi degil `[1.5]
- ✅ sayi degil `[1.50]
- ✅ sayi degil `[12.34.56]
- ✅ sayi degil `[abc]
- ✅ sayi degil `[1,2,3]
- ✅ sayi degil `[E3]
- ✅ sayi degil `[1e]
- ✅ sayi degil `[0x10]
- ✅ sayi degil `[inf]
- ✅ sayi degil `[nan]
- ✅ sayi degil `[1 000]
- ✅ girdi turleri
- ✅ duzenleme gidis donus `[None]
- ✅ duzenleme gidis donus `[hucre1]
- ✅ duzenleme gidis donus `[hucre2]
- ✅ duzenleme gidis donus `[hucre3]
- ✅ duzenleme gidis donus `[hucre4]
- ✅ duzenleme gidis donus `[hucre5]
- ✅ duzenleme gidis donus `[hucre6]
- ✅ duzenleme gidis donus `[hucre7]
- ✅ duzenleme gidis donus `[hucre8]
- ✅ duzenleme gidis donus `[hucre9]
- ✅ duzenleme gidis donus `[hucre10]
- ✅ duzenleme gidis donus `[hucre11]
- ✅ duzenleme gidis donus `[hucre12]
- ✅ duzenleme gidis donus `[hucre13]
- ✅ duzenleme gidis donus `[hucre14]
- ✅ duzenleme metni bicimi

### `testler/test_gosterim.py` — 8/8 ✅
*Genel sayı biçimi ve sığdırma (####, bilimsel)*

- ✅ goster genel
- ✅ sigiyorsa degismez
- ✅ ondalik yuvarlanir
- ✅ tam kisim yuvarlanamazsa bilimsel
- ✅ hic sigmazsa none
- ✅ sifira yuvarlanan sifir gosterilmez
- ✅ hata turkce gosterilir
- ✅ hata dahil tum degerler goster icin str doner

### `testler/test_isaretleme.py` — 27/27 ✅
*İşaretleme mantığı (Qt'siz): ekleme konumu, renkler, F4, öneriler, ipucu*

- ✅ eklenebilir konumlar `[=]
- ✅ eklenebilir konumlar `[=(]
- ✅ eklenebilir konumlar `[=TOPLA(]
- ✅ eklenebilir konumlar `[=A1+]
- ✅ eklenebilir konumlar `[=A1+ ]
- ✅ eklenebilir konumlar `[=E\u011eER(A1>1;]
- ✅ eklenebilir konumlar `[=-]
- ✅ eklenebilir konumlar `[=A1*(]
- ✅ eklenebilir konumlar `[=A1<=]
- ✅ eklenemez konumlar `[=A1]
- ✅ eklenemez konumlar `[=TOPLA(A1)]
- ✅ eklenemez konumlar `[=5]
- ✅ eklenemez konumlar `[="a]
- ✅ eklenemez konumlar `[=A1%]
- ✅ eklenemez konumlar `[=TOPLA]
- ✅ eklenemez konumlar `[metin]
- ✅ eklenemez konumlar `[]
- ✅ eklenebilir imlec ortada
- ✅ basvuru konumlari ve renkler
- ✅ renk paleti doner
- ✅ hatali formulde bos
- ✅ basvuru metni
- ✅ f4 dongusu
- ✅ f4 aralik ve sayfa oneki ve imlec
- ✅ ad oneki
- ✅ oneriler turkce ad ve sirali
- ✅ ipucu

### `testler/test_isaretleme_arayuz.py` — 28/28 ✅
*İşaretleme modu arayüzde (6d): tıklama/ok, F4, odak kaybı, formül çubuğu, sekmeler arası, Alt+=, öneri listesi, renkli metin*

- ✅ tiklama basvuru ekler onaylamaz
- ✅ surukleme aralik ekler
- ✅ yazinca isaret donar sonraki tiklama yeni parca
- ✅ formul olmayan metinde tiklama onaylar
- ✅ basvuru konumu degilse tiklama onaylar
- ✅ ok tuslari isaret hucresini gezdirir gir modunda
- ✅ duzenle modunda oklar imlec gezdirir
- ✅ f2 gir duzenle gecisi
- ✅ f4 dongusu duzenleyicide
- ✅ pencere disi odak kaybi onaylamaz
- ✅ renkli vurgu basvuru listesi
- ✅ formul cubugu ayni modu paylasir
- ✅ formul cubugu f4
- ✅ otomatik toplam ustteki blogu toplar
- ✅ otomatik toplam bitisik blokta durur
- ✅ otomatik toplam ustte yoksa soldakini toplar
- ✅ otomatik toplam veri yoksa bos imlec icinde
- ✅ oneri listesi acilir tab kabul eder
- ✅ oneri asagi ok secimi degistirir esc listeyi kapatir
- ✅ oneri tam ad yazilinca kapanir basvuruda acilmaz
- ✅ sekme tiklayarak baska sayfadan basvuru
- ✅ baska sayfadan esc vazgecer ve donunce onekler kalkar
- ✅ baska sayfadan asil sayfaya donup tiklarsa onek yok
- ✅ otomatik toplam cok satirli secim altina yazar
- ✅ otomatik toplam tek satirli secim sagina yazar
- ✅ renkli metin cizimi hata vermez ve boyar
- ✅ devredilen duzenleme isaret disi tiklamada onaylanir
- ✅ devredilen hatali formul tiklamada acik kalir

### `testler/test_iskelet.py` — 3/3 ✅
*Proje iskeleti: ad/sürüm sabiti, kaynak klasörü, model/formül paketlerinin Qt'siz olması*

- ✅ ad ve surum
- ✅ resource dir var
- ✅ model ve formul qt icermez

### `testler/test_izgara.py` — 108/108 ✅
*Izgara arayüzü: çizim, gezinme, seçim, düzenleme, boyutlandırma, gizleme, pano, taşan metin, çoklu aralık, artımlı kaydırma*

- ✅ goster
- ✅ baslangic
- ✅ ok tuslari sinirda kalir
- ✅ shift ok secimi genisletir
- ✅ ctrl ok veri blogu
- ✅ ctrl home end
- ✅ ctrl a ve bosluk
- ✅ enter tab
- ✅ asagi inince kayar
- ✅ sola donunce kayar
- ✅ fare tiklama ve surukleme
- ✅ baslik tiklama
- ✅ sinyaller
- ✅ cizim hatasiz ve goruntu
- ✅ yazarak duzenle enter
- ✅ tab ve ok onaylar
- ✅ esc iptal
- ✅ f2 mevcut icerik ve ok imlec
- ✅ formul saklanir
- ✅ delete ve geri al
- ✅ tum secim delete hizli
- ✅ duzenleme geri al tek adim
- ✅ degismeyen giris yigina girmez
- ✅ duzenlerken tiklama dogru hucreye yazar
- ✅ cift tik duzenler
- ✅ backspace bos baslatir
- ✅ duzenleyici yazdikca genisler
- ✅ sutun kenarindan boyutlandir ve geri al
- ✅ satir kenarindan boyutlandir
- ✅ boyut sinirlari
- ✅ secili sutunlar birlikte boyutlanir
- ✅ baslik disinda boyutlandirma olmaz
- ✅ cift tik otomatik sigdir
- ✅ otomatik sigdir bos sutun varsayilana doner
- ✅ genislik yukseklik ayarla
- ✅ satir ekle sil
- ✅ secili kadar satir eklenir
- ✅ sutun ekle sil
- ✅ sayfa sonunda ekleme reddedilir
- ✅ gizle goster
- ✅ gizli hucreler gezinmede atlanir
- ✅ klavye kisayollari gizle sil
- ✅ baslik menusu
- ✅ baslik menusu ekle calisir
- ✅ secili baslik menusu secimi bozmaz
- ✅ imlec kenarda degisir
- ✅ kopyala uc bicimde panoya yazar
- ✅ kopyala yapistir deger ve formul
- ✅ kes yapistir kaynagi bosaltir ve tek adimda geri alinir
- ✅ kes ikinci yapistirma kaynagi tekrar bosaltmaz
- ✅ kes ust uste biner alan
- ✅ kes sayfalar arasi
- ✅ baska kaynaktan metin yapistir
- ✅ html tablo yapistir
- ✅ tek hucre secime yayilir
- ✅ bos pano yapistirma bir sey yapmaz
- ✅ yapistirma sinir asimi uyari
- ✅ tam sutun kopyalama sinirli
- ✅ esc isareti kaldirir
- ✅ karinca cercevesi cizilir
- ✅ hucre menusu
- ✅ hucre menusu temizle
- ✅ duzenleyicide ctrl c metin kopyalar ve isareti kaldirir
- ✅ uzun metin bos komsuya tasar
- ✅ dolu komsu tasmayi keser
- ✅ kisa metin tasmaz
- ✅ sayi tasmaz sigmazsa kisaltilir ya da diyez
- ✅ cok dar sutunda diyez
- ✅ satir sonu tek satir gorunur
- ✅ mantiksal ortalanir
- ✅ gizli sutun tasmada atlanir
- ✅ alt enter hucre icinde yeni satir
- ✅ taşma ile cizim hatasiz
- ✅ ctrl tik aralik ekler
- ✅ ctrl surukleme aralik ekler
- ✅ duz tik ve klavye coklu secimi kaldirir
- ✅ shift tik son araligi genisletir oncekiler kalir
- ✅ ctrl baslik tik sutun ekler
- ✅ delete tum secili araliklari temizler
- ✅ coklu secimde kopyalama reddedilir
- ✅ coklu secim sinyali ve cizim
- ✅ ozet tum araliklari kapsar
- ✅ kucuk kaydirma pikselleri kaydirir
- ✅ kaydirma gizli satirlari piksel hesabina katmaz
- ✅ kaydirma yakinlastirmada piksel carpanli
- ✅ buyuk sicrama piksel kaydirmaz tam boyar
- ✅ ayni deger kaydirma yapmaz
- ✅ scroll contents by tum viewport yenilemez
- ✅ seçim boyama baslik ekran disi satir olsa da guncellenir — Seçili aralığın satırları ekran dışına kaydığında sütun başlığı vurgusu yine temizlenmeli.
- ✅ boyutlu viewport secim boyama hatasiz ve tam cizimle ayni
- ✅ page down up sayfa kadar gider
- ✅ shift page down secimi genisletir
- ✅ home satir basina gider
- ✅ ctrl shift rakam gizli satir sutun gosterir
- ✅ ctrl artı tam satir secimde satir ekler
- ✅ ctrl eksi hucre seciliyken hicbir sey silmez
- ✅ alternatif pano kisayollari
- ✅ shift delete hucreyi silmez ctrl delete gibi davranmaz
- ✅ satir otomatik sigdir varsayilana dondurur
- ✅ fare surukleme alt kenarin otesinde secimi uzatir
- ✅ yakinlastirma sinyali
- ✅ k1 bire dogru yazilabilir
- ✅ k3 kes sonra satir ekle isareti iptal eder
- ✅ k3 kes sonra kaynak duzenlenirse iptal
- ✅ k3 kes sonra boyutlandirma kes modunu bozmaz
- ✅ k3 kopya isareti birden cok yapistirmada kalir
- ✅ k3 geri al pano isaretini iptal eder
- ✅ koru odak kaybinda sifirlanir

### `testler/test_izgara_stil.py` — 23/23 ✅
**

- ✅ dolgu rengi cizilir
- ✅ bos hucrede dolgu ve stilli liste
- ✅ satir stili dolgusu tum satira uygulanir
- ✅ kenarlik cizilir kalin komsuyu ezer
- ✅ kalin italik boyut
- ✅ yazi rengi ve font ailesi
- ✅ hizalama metin sag orta girinti
- ✅ sayi sola hizali ve metin sagda taşmaz
- ✅ dikey hizalama konumu
- ✅ sayi bicimi metne yansir
- ✅ tarih bicimi ve renk
- ✅ bicim siginca diyez ve gecersiz kod genel
- ✅ metin bicimli sayi degeri degisince onbellek tazelenir
- ✅ stilsiz sayfada stilli liste bos
- ✅ yatay artimli kaydirma tam ciziminle ayni `[1]
- ✅ yatay artimli kaydirma tam ciziminle ayni `[2]
- ✅ yatay artimli kaydirma tam ciziminle ayni `[3]
- ✅ yatay artimli kaydirma tam ciziminle ayni `[-1]
- ✅ yatay kaydirma scroll cagirir ve son degeri izler
- ✅ buyuk secimde ozet ertelenir kucukte aninda
- ✅ shift ok yalniz fark bolgesini boyar
- ✅ ok tusu tum izgarayi yeniden boyamaz
- ✅ kalin ust kenarlik ustteki satirin piksellerine tasar

### `testler/test_kaydir.py` — 33/33 ✅
*Başvuru kaydırma: kopyala, ekle-sil, taşı ($'lılar, #BAŞV!)*

- ✅ kopyala `[=A1+B2-1-0-=A2+B3]
- ✅ kopyala `[=$A$1+A$1+$A1-2-3-=$A$1+D$1+$A3]
- ✅ kopyala `[=SUM(A1:B2)-0-1-=SUM(B1:C2)]
- ✅ kopyala `[=SUM(A:A)-5-1-=SUM(B:B)]
- ✅ kopyala `[=SUM(2:3)-1-9-=SUM(3:4)]
- ✅ kopyala `[=A1--1-0-=#REF!]
- ✅ kopyala `[=[2]!A1 + "A1"-1-0-=[2]!A2 + "A1"]
- ✅ kopyala `[=SUM($A$1:A1)-4-0-=SUM($A$1:A5)]
- ✅ kopyala `[=SUM(A$5:A1)-9-0-=SUM(A$5:A10)]
- ✅ kopyala sinir
- ✅ yapi `[=A5-satir-3-2-=A7]
- ✅ yapi `[=A2-satir-3-2-None]
- ✅ yapi `[=$A$5-satir-5-1-=$A$6]
- ✅ yapi `[=SUM(A2:A6)-satir-4-1-=SUM(A2:A7)]
- ✅ yapi `[=SUM(A2:A6)-satir-2-1-=SUM(A3:A7)]
- ✅ yapi `[=SUM(A:A)-satir-1-3-None]
- ✅ yapi `[=A5-satir-5--1-=#REF!]
- ✅ yapi `[=A5-satir-2--2-=A3]
- ✅ yapi `[=SUM(A2:A6)-satir-3--2-=SUM(A2:A4)]
- ✅ yapi `[=SUM(A2:A6)-satir-1--3-=SUM(A1:A3)]
- ✅ yapi `[=SUM(A2:A6)-satir-2--5-=SUM(#REF!)]
- ✅ yapi `[=SUM(A2:A6)-satir-5--10-=SUM(A2:A4)]
- ✅ yapi `[=C1-sutun-2-1-=D1]
- ✅ yapi `[=SUM(1:1)-sutun-1-5-None]
- ✅ yapi `[=SUM(B:D)-sutun-3--1-=SUM(B:C)]
- ✅ yapi baska sayfa
- ✅ tasi kurallari
- ✅ satir ekle formulleri duzeltir geri alinir
- ✅ satir sil ref ve geri al
- ✅ silinen satirdaki formul geri gelir
- ✅ sutun sil
- ✅ hucre tasi
- ✅ hucre tasi baska sayfaya

### `testler/test_kaydir_metin.py` — 21/21 ✅
**

- ✅ kaydirilmis metin satiri uzatir
- ✅ sutun genisleyince satir kisalir
- ✅ elle yukseklik kazanir ve otomatik sigdir geri acar
- ✅ kaydirma kapatilinca satir eski haline doner
- ✅ metin degisince yukseklik izler
- ✅ alt enter kaydirmayi acar ve satir uzar
- ✅ sayilar kaydirilmaz
- ✅ formul sonucu metin kaydirilir
- ✅ satir stili ile kaydirma
- ✅ gizli satir ve birlesik hucre katilmaz
- ✅ buyuk yazi boyutu satiri buyutur
- ✅ yakinlastirmada yukseklik olcekli
- ✅ satir ust alti konumlari ve kaydirma sonraki satirlari iter
- ✅ metin satirlara bolunur ve hucre icinde kalir
- ✅ kaydirma kapaliyken tek satir
- ✅ uzun kelime hucre genisliginde boyunca boler
- ✅ acik satir sonu satir sayisini belirler
- ✅ dikey hiza ust ve alt
- ✅ yatay ortalama sarilmis metinde
- ✅ birlesik hucrede kaydirilmis metin cok satirli
- ✅ stilli kaydirilmis hucre yazi rengi ve dolgu

### `testler/test_kosullu.py` — 41/41 ✅
*Koşullu biçim (5h): 12 kural türü, öncelik+dur, ölçek/çubuk, ekle-sil, komut*

- ✅ TestHucreDegeri::test buyuk normal bos hata karisim
- ✅ TestHucreDegeri::test bos hucre sifir gibi
- ✅ TestHucreDegeri::test islecler `[arasinda-2.0-4.0-gecen0-gecmeyen0]
- ✅ TestHucreDegeri::test islecler `[arasinda_degil-2.0-4.0-gecen1-gecmeyen1]
- ✅ TestHucreDegeri::test islecler `[esit-3.0-None-gecen2-gecmeyen2]
- ✅ TestHucreDegeri::test islecler `[esit_degil-3.0-None-gecen3-gecmeyen3]
- ✅ TestHucreDegeri::test islecler `[buyuk_esit-3.0-None-gecen4-gecmeyen4]
- ✅ TestHucreDegeri::test islecler `[kucuk_esit-3.0-None-gecen5-gecmeyen5]
- ✅ TestHucreDegeri::test metin karsilastirma turkce ve buyuk kucuk duyarsiz
- ✅ TestHucreDegeri::test hucre basvurulu goreli formul
- ✅ TestMetinBosHata::test icerir icermez baslar biter
- ✅ TestMetinBosHata::test sayi gorunen metinde aranir
- ✅ TestMetinBosHata::test bos ve bos degil
- ✅ TestMetinBosHata::test hata ve hata degil
- ✅ TestYinelenen::test yinelenen ve benzersiz
- ✅ TestYinelenen::test sayi ile metin ayri hata degerleri
- ✅ TestYinelenen::test degisince gecersiz ile yenilenir
- ✅ TestIlkOrtalama::test ilk son eslerle
- ✅ TestIlkOrtalama::test yuzde ve bos aralik
- ✅ TestIlkOrtalama::test ortalama ustu alti esit std
- ✅ TestFormul::test goreli formul satirin baska hucresine bakar
- ✅ TestFormul::test mantiksal sifir olmayan ve hata
- ✅ TestFormul::test tum satir boyama formulu
- ✅ TestOncelikVeDur::test yamalar birlesir ust oncelik kazanir
- ✅ TestOncelikVeDur::test dur sonrakileri atlar
- ✅ TestOncelikVeDur::test aralik disi ve kural yok
- ✅ TestOncelikVeDur::test bozuk formul kural uygulanmaz digerleri calisir
- ✅ TestRenkOlcegi::test uc renkli ara renk
- ✅ TestRenkOlcegi::test ara renk dogrusal
- ✅ TestRenkOlcegi::test sayi yuzde yuzdebirlik noktalari
- ✅ TestRenkOlcegi::test yuzdebirlik islevi
- ✅ TestRenkOlcegi::test gecersiz nokta sayisi
- ✅ TestVeriCubugu::test oran ve alt ust sinir
- ✅ TestVeriCubugu::test sabit uclar ve esit degerler
- ✅ TestVeriCubugu::test cubuk ve renk kurallari birlikte
- ✅ TestKuralModeli::test gecersiz alanlar
- ✅ TestKuralModeli::test bicimsiz mu ve kural ekle oncelik
- ✅ TestKuralModeli::test aralik temizle
- ✅ TestKomutVeEkleSil::test yap geri al yinele islev ve olay
- ✅ TestKomutVeEkleSil::test satir ekle aralik formul ve nokta kayar geri al
- ✅ TestKomutVeEkleSil::test aralik silinince kural duser

### `testler/test_kosullu_arayuz.py` — 26/26 ✅
*Koşullu biçim arayüzü (5h): çizim pikselleri, menü, pencereler, yönetici, yazdırma, .xlsx*

- ✅ kural hucreyi boyar geri al ve olay ile gecersiz
- ✅ renk olcegi ve veri cubugu cizilir
- ✅ yalniz cubuk metni gizler
- ✅ birlesik hucre boyanir
- ✅ baska sayfadaki degisiklik gecersiz kilar
- ✅ menu ogeleri
- ✅ yeni kural en yuksek oncelik ve capa kaymasi
- ✅ temizle secim ve sayfa ve tumunu temizle
- ✅ yonet sonucu uygular ve siralama
- ✅ deger donusumleri
- ✅ kural penceresi turleri ve geri yukleme
- ✅ kural penceresi kural olusturur `[metin-<lambda>-beklenen0]
- ✅ kural penceresi kural olusturur `[bos-<lambda>-beklenen1]
- ✅ kural penceresi kural olusturur `[hata_degil-<lambda>-beklenen2]
- ✅ kural penceresi kural olusturur `[benzersiz-<lambda>-beklenen3]
- ✅ kural penceresi kural olusturur `[son-<lambda>-beklenen4]
- ✅ kural penceresi kural olusturur `[ortalama_alti-<lambda>-beklenen5]
- ✅ kural penceresi kural olusturur `[formul-<lambda>-beklenen6]
- ✅ kural penceresi renk olcegi cubuk ve hatalar
- ✅ ozel bicim yamasi
- ✅ yonetici liste islemleri
- ✅ kural aciklamalari
- ✅ xlsx gidis donus ve oncelik
- ✅ xlsx dxf fill bgcolor ve oncelik dosyada
- ✅ xlsx desteklenmeyen tur uyari ve oncelik sirasi
- ✅ yazdirma koşullu biçimi çizer

### `testler/test_kurtarma.py` — 15/15 ✅
**

- ✅ surec canli mi
- ✅ kopya yaz ve bekleyenler
- ✅ en yeni once ve bozuklar atlanir
- ✅ klasor yoksa bos
- ✅ zamanlayici iki dakika
- ✅ otokayit yalniz degisince ve yalniz yeni degisiklikte
- ✅ otokayit ozgun dosyaya dokunmaz
- ✅ kaydedince kurtarma kopyasi silinir
- ✅ bilerek kapatinca kopya silinir
- ✅ kapatma iptal edilirse kopya kalir
- ✅ cokme sonrasi kurtarilir ve kaydedince silinir
- ✅ kurtarma sil ve sonra
- ✅ bozuk kurtarma kopyasi silinmez
- ✅ kurtarma penceresi listesi
- ✅ gercek surec cokmesi — Ayrı bir süreç değişiklik yapıp kopya yazar ve ölürse (os._exit) kopya bu süreçte önerilir.

### `testler/test_motor.py` — 20/20 ✅
*Hesaplayıcı: bağımlılık, yeniden hesaplama, döngü, sayfa işlemleri*

- ✅ ilk kurulumda hesaplar
- ✅ degisiklik bagimlilara yayilir
- ✅ yalniz etkilenenler hesaplanir
- ✅ sira bagimsiz yazim — Formül, öncülünden ÖNCE yazılsa da doğru sonuç (topolojik sıra).
- ✅ aralik bagimliligi ve tam sutun
- ✅ formul silinince bagimlilar guncellenir
- ✅ dongu
- ✅ kendine basvuru
- ✅ baska sayfa ve sayfa silme
- ✅ geri al yeniden hesaplar
- ✅ satir ekleyince tumu yeniden
- ✅ degisken fonksiyon her seferinde
- ✅ toplu yazim tek sonuc olayi
- ✅ bozuk formul ad hatasi
- ✅ uzun zincir — Özyineleme sınırına takılmadan uzun zincir (topolojik sıra).
- ✅ kapat dinlemeyi birakir
- ✅ bakiye zinciri dogrusal surede yeniden hesaplanir — Satır TOPLA + yürüyen bakiye: A1 değişince 4000 satır (eskiden ~20 sn, karesel). Sınır geniş
- ✅ hareketli ortalama zinciri
- ✅ tam sutun toplami kullanilan alanla sinirli — =TOPLA(A:A) 1.048.576 satırı gezmez (eskiden her turda ~0,4 sn); sonuç doğru kalır.
- ✅ bos sayfada tam sutun toplami sifir

### `testler/test_notlar.py` — 26/26 ✅
*Notlar (5e): model, komut, ekle-sil, sırala, kes-yapıştır, pano, .xlsx*

- ✅ TestModel::test not degismez ve kutu metni
- ✅ TestModel::test yaz ve eskiler
- ✅ TestModel::test none ve bos not siler
- ✅ TestModel::test tek ek olayi
- ✅ TestModel::test degisiklik yoksa olay yok
- ✅ TestKomut::test yap geri al yinele
- ✅ TestKomut::test bos mu
- ✅ TestKomut::test ana sayfa
- ✅ TestKomut::test hucre degeri notu silmez
- ✅ TestEkleSil::test satir ekle notu kaydirir geri al
- ✅ TestEkleSil::test satir sil notu siler geri al getirir
- ✅ TestEkleSil::test sutun ekle sil
- ✅ TestSirala::test not satirla birlikte tasinir
- ✅ TestTasi::test kes yapistir notu tasir geri al
- ✅ TestTasi::test baska sayfaya
- ✅ TestTasi::test notsuz tasima notlara dokunmaz
- ✅ TestPano::test veri notu tasir json
- ✅ TestPano::test yapistir notu getirir
- ✅ TestPano::test notsuz kaynak hedefteki notu siler
- ✅ TestPano::test desen seciliye yinelenir
- ✅ TestPano::test dis veri ve notsuz durum bos
- ✅ TestXlsx::test gidis donus
- ✅ TestXlsx::test excel onekli metin yazar ayrilir
- ✅ TestXlsx::test onek yoksa metin oldugu gibi
- ✅ TestXlsx::test dizili aciklama uyari
- ✅ TestXlsx::test notsuz dosya notsuz

### `testler/test_notlar_arayuz.py` — 12/12 ✅
*Not arayüzü (5e): üçgen, fare üstü kutu, Shift+F2, menü, temizle*

- ✅ uclu notlu hucrede cizilir
- ✅ shift f2 ekler odak kaybinda kaydeder geri al
- ✅ esc vazgecer
- ✅ duzenle mevcut notu yazari korur
- ✅ bos metin notu siler degisiklik yoksa komut yok
- ✅ fare ustu kutu
- ✅ kutu html kacisli
- ✅ tus kutuyu kapatir
- ✅ notu sil ve temizle secime uygulanir
- ✅ delete notu silmez tumunu temizle siler
- ✅ sag tik menusu
- ✅ kopyala yapistir notu getirir kes yapistir tasir

### `testler/test_olay.py` — 18/18 ✅
*Olay katmanı (K5): hücre/sonuç/yapı/boyut/sayfa olayları, toplu işlem tek olay*

- ✅ hucre olayi eski ve yeni tasir
- ✅ degismeyen yazim olay yaymaz
- ✅ sonuc olayi
- ✅ yapi olayi ekle ve sil
- ✅ reddedilen ekleme olay yaymaz
- ✅ boyut olayi komut ve geri al
- ✅ geri al da olay yayar
- ✅ dinlemeyi birakma
- ✅ birden cok dinleyici sirayla cagrilir
- ✅ kitapsiz sayfa olay yaymadan calisir
- ✅ sayfa olaylari
- ✅ degismeyen sayfa islemleri olay yaymaz
- ✅ kimlikler benzersiz ve kalici
- ✅ silinen sayfa geri konunca ayni kimlik ve veri
- ✅ silinmis sayfa olay yaymaz
- ✅ geri koyma hatalari
- ✅ sayfa silme son sayfa ve olay
- ✅ kitap kimlikleri 1den baslar

### `testler/test_olcu.py` — 3/3 ✅
*Excel ölçü birimleri: karakter/punto ⇄ piksel*

- ✅ excel varsayilanlari
- ✅ gidis donus
- ✅ sinirlar

### `testler/test_opus_faz2.py` — 11/11 ✅
**

- ✅ if dizi kosulu ogeye ogeye
- ✅ if dizi bos hucre ve hata ve metin
- ✅ if dizi kosul sabit dalli ve yayma
- ✅ if skaler davranis degismedi
- ✅ ifs dizi
- ✅ etarihli turkce ad ve microsoft ornekleri — Microsoft tr-tr ETARİHLİ sayfasının örnekleri: 1.1.2001–1.1.2003 "Y" = 2; 1.6.2001–15.8.2002
- ✅ eski yanlis ad tanimsiz
- ✅ eğersay olcut araligi benzersiz sayma deyimi
- ✅ etopla ve cokolcutlu olcut dizisi
- ✅ olcutte turkce hata adi
- ✅ na fonksiyonu yoksay — NA() → #YOK; Türkçe adı YOKSAY (Microsoft tr-tr NA sayfası sözdizimi satırı: YOKSAY()).

### `testler/test_opus_faz3.py` — 54/54 ✅
**

- ✅ metin duzenleme gidis donus `[12.10.2026]
- ✅ metin duzenleme gidis donus `[15%]
- ✅ metin duzenleme gidis donus `[1.5]
- ✅ metin duzenleme gidis donus `[\u20ba100]
- ✅ metin duzenleme gidis donus `[14:30]
- ✅ metin duzenleme gidis donus `[1 1/2]
- ✅ metin duzenleme gidis donus `[12 Ekim 2026]
- ✅ yuzde duzenleme gidis donus `[1e-07]
- ✅ yuzde duzenleme gidis donus `[0.123456789012345]
- ✅ yuzde duzenleme gidis donus `[0.15]
- ✅ yuzde duzenleme gidis donus `[0.0001]
- ✅ yuzde duzenleme gidis donus `[12.5]
- ✅ yuzde duzenleme gidis donus `[-0.07]
- ✅ yuzde duzenleme gidis donus `[1e-10]
- ✅ doldur uzun sayi serisi
- ✅ cok buyuk sayi bicimlenir `[0-1e+26]
- ✅ cok buyuk sayi bicimlenir `[0-1e+28]
- ✅ cok buyuk sayi bicimlenir `[0-1e+100]
- ✅ cok buyuk sayi bicimlenir `[0-1e+300]
- ✅ cok buyuk sayi bicimlenir `[0--1.5e+308]
- ✅ cok buyuk sayi bicimlenir `[0.00-1e+26]
- ✅ cok buyuk sayi bicimlenir `[0.00-1e+28]
- ✅ cok buyuk sayi bicimlenir `[0.00-1e+100]
- ✅ cok buyuk sayi bicimlenir `[0.00-1e+300]
- ✅ cok buyuk sayi bicimlenir `[0.00--1.5e+308]
- ✅ cok buyuk sayi bicimlenir `[#,##0.00-1e+26]
- ✅ cok buyuk sayi bicimlenir `[#,##0.00-1e+28]
- ✅ cok buyuk sayi bicimlenir `[#,##0.00-1e+100]
- ✅ cok buyuk sayi bicimlenir `[#,##0.00-1e+300]
- ✅ cok buyuk sayi bicimlenir `[#,##0.00--1.5e+308]
- ✅ cok buyuk sayi bicimlenir `[General-1e+26]
- ✅ cok buyuk sayi bicimlenir `[General-1e+28]
- ✅ cok buyuk sayi bicimlenir `[General-1e+100]
- ✅ cok buyuk sayi bicimlenir `[General-1e+300]
- ✅ cok buyuk sayi bicimlenir `[General--1.5e+308]
- ✅ cok buyuk sayi bicimlenir `["\u20ba"#,##0.00-1e+26]
- ✅ cok buyuk sayi bicimlenir `["\u20ba"#,##0.00-1e+28]
- ✅ cok buyuk sayi bicimlenir `["\u20ba"#,##0.00-1e+100]
- ✅ cok buyuk sayi bicimlenir `["\u20ba"#,##0.00-1e+300]
- ✅ cok buyuk sayi bicimlenir `["\u20ba"#,##0.00--1.5e+308]
- ✅ cok buyuk sayi bicimlenir `[0.00E+00-1e+26]
- ✅ cok buyuk sayi bicimlenir `[0.00E+00-1e+28]
- ✅ cok buyuk sayi bicimlenir `[0.00E+00-1e+100]
- ✅ cok buyuk sayi bicimlenir `[0.00E+00-1e+300]
- ✅ cok buyuk sayi bicimlenir `[0.00E+00--1.5e+308]
- ✅ sonsuz sayi metin kalir
- ✅ cift isaret para
- ✅ tam satir sutun kesisimi
- ✅ tum sayfa cok bicimli satir
- ✅ kaydirilmis metin onbellegi sinirli
- ✅ genel ile tarih harfi gecersiz `[Genel m]
- ✅ genel ile tarih harfi gecersiz `[General m]
- ✅ genel ile tarih harfi gecersiz `[Genel a]
- ✅ genel ile tarih harfi gecersiz `[General dd]

### `testler/test_opus_faz4.py` — 36/36 ✅
**

- ✅ 1904 tarih sistemi takvim tarihini korur
- ✅ gecersiz denetim karakteri silinir ve bildirilir
- ✅ uzun metin ve sonsuz sayi
- ✅ beklenmeyen kayit hatasi pencereyi kapatmaz
- ✅ closeevent istisnada kabul etmez
- ✅ arka plan sirasinda kapatma ertelenir
- ✅ seyrek dosya hizli acilir
- ✅ xlfn bilinmeyen islev oneki korunur `[=_xlfn.STDEV.S(A1:A3)]
- ✅ xlfn bilinmeyen islev oneki korunur `[=_xlfn._xlws.SORT(A1:A3)]
- ✅ xlfn bilinmeyen islev oneki korunur `[=_xlfn.CONCAT(A1,B1)]
- ✅ tablo koprul gruplama ustbilgi koruma uyarilir
- ✅ dizi formulu uyarilir
- ✅ gizli sayfa kayip sayilir
- ✅ duz dosyada yanlis uyari yok
- ✅ genis sutun araligi korunur
- ✅ ayrac ondalik virgul `[12,5;13,7\n14,2;15,9\n-;]
- ✅ ayrac ondalik virgul `[1,5\n2,5\n3,25\n-;]
- ✅ ayrac ondalik virgul `[a;b\n1,5;2,5\n-;]
- ✅ ayrac ondalik virgul `[a,b,c\n1,2,3\n-,]
- ✅ ayrac ondalik virgul `[1,2,3\n4,5,6\n-,]
- ✅ ayrac ondalik virgul `[ad,not\n"Ali, Veli",5\n-,]
- ✅ ayrac ondalik virgul `[a\tb\n1,5\t2\n-\t]
- ✅ utf16 unicode metin okunur
- ✅ csv genel sayi 15 basamak
- ✅ kurtarilan belgede veri kaybi uyarisi korunur
- ✅ kurtarilan belge varken ozgun dosya acilabilir
- ✅ pid yeniden kullanimi kopyayi gizlemez
- ✅ dondurma kilavuz sekme rengi degisti sayilir
- ✅ gorunum degisikligi dosyaya yazilir ve otokayit tetikler
- ✅ disk degisti onayi
- ✅ otomatik satir yuksekligi elle sayilmaz
- ✅ hizli formul yolu bastaki sifir ayirt eder
- ✅ hizli yol rastgele formullerde yavasla ayni
- ✅ cakisan birlesim atlanir
- ✅ tema renkleri dosyanin kendi temasindan
- ✅ pdf hatasinda ayni yoldaki eski dosya bozulmaz

### `testler/test_pano.py` — 25/25 ✅
*Pano: TSV/HTML okuma-yazma, kopyalanan veri, yapıştırma planı*

- ✅ tsv yaz basit ve tirnak
- ✅ tsv gidis donus `[satirlar0]
- ✅ tsv gidis donus `[satirlar1]
- ✅ tsv gidis donus `[satirlar2]
- ✅ tsv gidis donus `[satirlar3]
- ✅ tsv gidis donus `[satirlar4]
- ✅ tsv coz bicimleri
- ✅ html yaz ve coz gidis donus
- ✅ html excel benzeri tablo
- ✅ html colspan baslik ic ice tablo ve bosluklar
- ✅ html tablo yok ya da bozuk
- ✅ html script icerigi yoksayilir
- ✅ pano verisi al goreli konum
- ✅ pano araligi kullanilanla sinirlanir
- ✅ json gidis donus turleri korur
- ✅ metin satirlari gosterim
- ✅ metinden pano verisi girdi gibi cozer
- ✅ duzensiz satirlar dikdortgen olur
- ✅ plan ust sol koseye
- ✅ plan tek hucre secime yayilir
- ✅ plan desen tam kat ise yinelenir
- ✅ plan kat degilse ust sol koseye
- ✅ plan sinir asimi
- ✅ plan tam sutun secimine tek hucre asiri yayilmaz
- ✅ k4 pano formul sonucunu metin olarak verir girdiyi json ile

### `testler/test_pano_bicim.py` — 16/16 ✅
*Pano biçim taşıma (3b): PanoVerisi.stiller, JSON, HTML CSS, yapıştır/kes-taşı, Temizle menüsü, Delete biçimi korur*

- ✅ pano verisi stil ve bos bicimli hucre
- ✅ pano json stil gidis donus kenar dahil
- ✅ html dis aktarim satir ici css
- ✅ yapistirma stilleri desen yinelenir
- ✅ kopyala yapistir icerik ve bicim
- ✅ bicimsiz kaynak hedefin bicimini siler tumu
- ✅ disaridan metin yapistirma bicime dokunmaz
- ✅ bicim baska oturumdan stil nesnesiyle tasinir — Pano JSON'u Stil alanlarını taşır (kimlik değil): başka havuz/oturum güvenli.
- ✅ kes yapistir bicimi tasir kaynak varsayilana doner
- ✅ hucre tasi sayfalar arasi ve satir stili altinda
- ✅ hucre tasi ust uste biner alan ayni sayfa
- ✅ delete bicimi korur
- ✅ bicimleri temizle icerik kalir tek adim
- ✅ tumunu temizle icerik ve bicim tek adim
- ✅ bicimleri temizle tam satir satir stilini kaldirir
- ✅ bicim temizle satir bicimliyken hucreyi varsayilana alir

### `testler/test_pano_formul.py` — 6/6 ✅
*Pano ve formül (6c): kopyada başvuru kayması, kes-yapıştır taşıma, dış formül çevirisi*

- ✅ formul kopyalayinca basvuru kayar ve hesaplanir
- ✅ mutlak basvuru kaymaz
- ✅ kes yapistir formulu tasir basvuranlar kayar
- ✅ kes yapistir tasinan formulun kendi basvurusu kaymaz
- ✅ disaridan turkce formul kanonik saklanir
- ✅ baska oturumdan gelen formul ingilizceden cevrilir

### `testler/test_pencere.py` — 21/21 ✅
*Ana pencere: ad kutusu, formül çubuğu, durum çubuğu, sayfa sekmeleri, yakınlaştırma*

- ✅ baslik ad sabitinden
- ✅ ad kutusu aktif hucre
- ✅ ad kutusundan git
- ✅ formul cubugu icerigi gosterir
- ✅ formul cubugundan giris
- ✅ formul cubugu vazgec
- ✅ hucre ici duzenleme formul cubugunda aynalanir
- ✅ f2 modu
- ✅ durum ozeti
- ✅ secim boyutu surukleme sirasinda
- ✅ sayfa ekle ve gecis
- ✅ yeniden adlandir
- ✅ sayfa sil
- ✅ sayfa sil onay reddedilirse
- ✅ sekme surukleme modeli gunceller
- ✅ ortak geri al
- ✅ yakinlastirma
- ✅ ctrl tekerlek yakinlastirir
- ✅ sekme rengi
- ✅ sekme rengi tasinan sekmeyle gider
- ✅ sekme menusu rengi kaldir yalniz renkliyse

### `testler/test_pencere_sayfa.py` — 16/16 ✅
*Sayfa sekmeleri ve sayfa komutları arayüzde (ekle/sil/yeniden adlandır/taşı, geri al)*

- ✅ sayfa ekle geri al yinele
- ✅ sayfa sil geri al gecmis silinmez izgara korunur
- ✅ ortadaki sayfa silinince komsu secilir
- ✅ son sayfa silinince onceki secilir
- ✅ son sayfa silinemez
- ✅ yeniden adlandirma geri alinir
- ✅ ayni adla yeniden adlandirma gecmise girmez
- ✅ sekme tasima geri alinir
- ✅ model dogrudan degisirse arayuz olaylarla eslesir
- ✅ baska sayfadaki degisikligi geri alinca o sayfaya gecilir
- ✅ ayni sayfadaki geri al sekme degistirmez
- ✅ sayfa silme kopya isaretini temizler
- ✅ gecersiz ad geri al yigina girmez
- ✅ sekme rengi esitlemede korunur
- ✅ silinen sayfa olaylari arayuzu bozmaz
- ✅ birden cok sayfa islemi art arda tutarli

### `testler/test_sayfa.py` — 33/33 ✅
*Veri modeli: seyrek sayfa, satır/sütun ekle-sil, geri al yığını, sayfa adı kuralları, gizleme, kullanılan aralık önbelleği*

- ✅ ata oku sil
- ✅ aralik disi
- ✅ kullanilan aralik ve formul
- ✅ satir ekle sil
- ✅ sutun sil olcu
- ✅ kitap sayfalari
- ✅ geri al yinele hucre
- ✅ yeni komut yinele yiginini temizler
- ✅ satir sil geri al
- ✅ sutun ekle geri al ve grup
- ✅ yigin siniri
- ✅ sayfa adi dogrulama
- ✅ sayfa tasi
- ✅ gizli satir sutun genislik sifir
- ✅ gizli ekle sil ile kayar
- ✅ olcu degis geri al yinele
- ✅ olcu degis onceden uygulanmis durum
- ✅ satir sil geri al gizli doner
- ✅ aralikta iki strateji ayni sonucu verir
- ✅ dolu hucreler sirali ve sirasiz
- ✅ kullanilan aralik onbellegi dogru kalir
- ✅ kullanilan aralik onbellegi gecmis rastgele islemlerle eslesir
- ✅ k1 mantiksal ile sayi esit degil
- ✅ k2 ekleme dolu hucreyi sayfa disina itmez
- ✅ k2 sinira tam sigan ekleme calisir tasan calismaz
- ✅ k2 komut reddedilince yigin bozulmaz
- ✅ k4 hucre ya sabit ya formul
- ✅ k4 gorunen deger sonuctur girdi degil
- ✅ k4 sonuc yalniz formul hucresine yazilir
- ✅ k4 girdi degisince eski sonuc atilir
- ✅ k4 geri al yalniz girdiyi geri yukler sonuc atilir
- ✅ k4 sonuclar satir ekle sil ile kayar
- ✅ k4 hata degeri

### `testler/test_sayfa_komutlari.py` — 7/7 ✅
*Geri alınabilir sayfa komutları (K6)*

- ✅ sayfa ekle geri al yinele ayni nesne
- ✅ sayfa sil geri al veri ve sira korunur
- ✅ sayfa yeniden adlandir ve tasi geri al
- ✅ gecersiz yeniden adlandirma yigina girmez
- ✅ karisik gecmis sayfa silme dahil tutarli geri alinir — Sayfadaki yazım → sayfa silme → ikisi de sırayla geri alınır (geçmiş silinmez).
- ✅ sayfa komutlari sayfa olaylari yayar
- ✅ silme geri al sayfa sirasi birden cok silmede

### `testler/test_sayfalama.py` — 19/19 ✅
**

- ✅ varsayilan excel gibi
- ✅ gecersiz ayar `[kw0]
- ✅ gecersiz ayar `[kw1]
- ✅ gecersiz ayar `[kw2]
- ✅ gecersiz ayar `[kw3]
- ✅ gecersiz ayar `[kw4]
- ✅ gecersiz ayar `[kw5]
- ✅ bos sayfa yazdirilmaz
- ✅ kucuk icerik tek sayfa
- ✅ gizli satir sutun yazdirilmaz
- ✅ sayfa numarasi once asagi sonra saga
- ✅ dilimler tum satirlari tam bir kez kapsar
- ✅ baslik satirlari her sayfada
- ✅ baslik sayfadan buyukse yinelenmez
- ✅ sigdir genislik ve olcek
- ✅ yazdirma alani ayarli ve birlesim
- ✅ dev hucre tek basina sayfa
- ✅ komut geri al ve xlsx gidis donus
- ✅ xlsx sigdir genislik gidis donus

### `testler/test_sayi_bicimi.py` — 179/179 ✅
*Excel sayı biçimi kodu çözümleyici/biçimleyici (Faz 3 çekirdeği): Genel, 0#?, yüzde, bilimsel, kesir, bölümler, renk, tarih/saat, kanonik⇄yerel*

- ✅ bos hucre bos metin `[genel]
- ✅ bos hucre bos metin `[sayi]
- ✅ bos hucre bos metin `[yuzde]
- ✅ bos hucre bos metin `[bilimsel]
- ✅ bos hucre bos metin `[kesir]
- ✅ bos hucre bos metin `[tarih]
- ✅ bos hucre bos metin `[saat]
- ✅ bos hucre bos metin `[para]
- ✅ bos hucre bos metin `[renkli]
- ✅ bos hucre bos metin `[kosullu]
- ✅ bos hucre bos metin `[metin_bolumlu]
- ✅ hata degeri bicimlenmez ortalanir `[genel]
- ✅ hata degeri bicimlenmez ortalanir `[sayi]
- ✅ hata degeri bicimlenmez ortalanir `[yuzde]
- ✅ hata degeri bicimlenmez ortalanir `[bilimsel]
- ✅ hata degeri bicimlenmez ortalanir `[kesir]
- ✅ hata degeri bicimlenmez ortalanir `[tarih]
- ✅ hata degeri bicimlenmez ortalanir `[saat]
- ✅ hata degeri bicimlenmez ortalanir `[para]
- ✅ hata degeri bicimlenmez ortalanir `[renkli]
- ✅ hata degeri bicimlenmez ortalanir `[kosullu]
- ✅ hata degeri bicimlenmez ortalanir `[metin_bolumlu]
- ✅ mantiksal bicimlenmez `[genel]
- ✅ mantiksal bicimlenmez `[sayi]
- ✅ mantiksal bicimlenmez `[yuzde]
- ✅ mantiksal bicimlenmez `[bilimsel]
- ✅ mantiksal bicimlenmez `[kesir]
- ✅ mantiksal bicimlenmez `[tarih]
- ✅ mantiksal bicimlenmez `[saat]
- ✅ mantiksal bicimlenmez `[para]
- ✅ mantiksal bicimlenmez `[renkli]
- ✅ mantiksal bicimlenmez `[kosullu]
- ✅ mantiksal bicimlenmez `[metin_bolumlu]
- ✅ sayi gibi metin oldugu gibi sola `[General]
- ✅ sayi gibi metin oldugu gibi sola `[#,##0.00]
- ✅ sayi gibi metin oldugu gibi sola `[0.0%]
- ✅ sayi gibi metin oldugu gibi sola `[0.00E+00]
- ✅ sayi gibi metin oldugu gibi sola `[# ?/?]
- ✅ sayi gibi metin oldugu gibi sola `[dd.mm.yyyy]
- ✅ sayi gibi metin oldugu gibi sola `[hh:mm:ss]
- ✅ sayi gibi metin oldugu gibi sola `["\u20ba"#,##0.00]
- ✅ sayi gibi metin oldugu gibi sola `[[Red]0;[Blue]-0]
- ✅ sayi gibi metin oldugu gibi sola `[[>100]0;0.0]
- ✅ normal durum sayi saga `[General-1234.5-1234,5]
- ✅ normal durum sayi saga `[#,##0.00-1234.567-1.234,57]
- ✅ normal durum sayi saga `[0.0%-0.1234-12,3%]
- ✅ normal durum sayi saga `[0.00E+00-12200000.0-1,22E+07]
- ✅ normal durum sayi saga `[# ?/?-1.25-1 1/4]
- ✅ normal durum sayi saga `[dd.mm.yyyy-46307.0-12.10.2026]
- ✅ normal durum sayi saga `[hh:mm:ss-0.5-12:00:00]
- ✅ normal durum sayi saga `["\u20ba"#,##0.00-1234.5-\u20ba1.234,50]
- ✅ normal durum sayi saga `[[Red]0;[Blue]-0-5.0-5]
- ✅ normal durum sayi saga `[[>100]0;0.0-150.0-150]
- ✅ normal durum sayi saga `[0.00;-0.00;0;"Ad: "@-2.0-2,00]
- ✅ genel gosterim ile ayni
- ✅ genel yerel adi ve sabitle
- ✅ genel sigdir gosterim ile tutarli
- ✅ sayi ms ornekleri `[####.#-1234.59-1234,6]
- ✅ sayi ms ornekleri `[#.000-8.9-8,900]
- ✅ sayi ms ornekleri `[0.#-0.631-0,6]
- ✅ sayi ms ornekleri `[#.0#-12.0-12,0]
- ✅ sayi ms ornekleri `[#.0#-1234.568-1234,57]
- ✅ sayi ms ornekleri `[#,###-12000.0-12.000]
- ✅ sayi ms ornekleri `[#,-12000.0-12]
- ✅ sayi ms ornekleri `[0.0,,-12200000.0-12,2]
- ✅ sayi ms ornekleri `[#,##0-1234567.0-1.234.567]
- ✅ sayi ms ornekleri `[0-2.5-3]
- ✅ sayi ms ornekleri `[0--2.5--3]
- ✅ sayi ms ornekleri `[0-0.0-0]
- ✅ sayi ms ornekleri `[00000-123.0-00123]
- ✅ sayi ms ornekleri `[000-00-0000-123456789.0-123-45-6789]
- ✅ soru isareti hizalama `[44.398- 44,398]
- ✅ soru isareti hizalama `[102.65-102,65 ]
- ✅ soru isareti hizalama `[2.8-  2,8  ]
- ✅ sayi hata ve karisik
- ✅ yuzde
- ✅ bilimsel
- ✅ kesir `[# ?/?-1.25-1 1/4]
- ✅ kesir `[# ???/???-5.25-5 1/4]
- ✅ kesir `[# ???/???-5.3-5 3/10]
- ✅ kesir `[# ?/8-1.3-1 2/8]
- ✅ kesir `[?/?-5.25-21/4]
- ✅ kesir `[# ??/100-0.37-37/100]
- ✅ kesir dort vaka
- ✅ dort bolum ms ornegi
- ✅ iki bolum negatif isaretsiz
- ✅ bos bolum gizler
- ✅ metin bolumu tek basina
- ✅ renk ms ornegi ve kosul
- ✅ kosullu bolumler
- ✅ renk adlari tr en `[Siyah-Black-#000000]
- ✅ renk adlari tr en `[Ye\u015fil-Green-#00FF00]
- ✅ renk adlari tr en `[Beyaz-White-#FFFFFF]
- ✅ renk adlari tr en `[Mavi-Blue-#0000FF]
- ✅ renk adlari tr en `[Eflatun-Magenta-#FF00FF]
- ✅ renk adlari tr en `[Sar\u0131-Yellow-#FFFF00]
- ✅ renk adlari tr en `[Camg\xf6be\u011fi-Cyan-#00FFFF]
- ✅ renk adlari tr en `[K\u0131rm\u0131z\u0131-Red-#FF0000]
- ✅ renk numarasi palet openpyxl ile ayni
- ✅ sabitler
- ✅ dolgu yildiz
- ✅ tarih ms kodlari
- ✅ ay adlari `[1]
- ✅ ay adlari `[2]
- ✅ ay adlari `[3]
- ✅ ay adlari `[4]
- ✅ ay adlari `[5]
- ✅ ay adlari `[6]
- ✅ ay adlari `[7]
- ✅ ay adlari `[8]
- ✅ ay adlari `[9]
- ✅ ay adlari `[10]
- ✅ ay adlari `[11]
- ✅ ay adlari `[12]
- ✅ tarih dort vaka ve 1900
- ✅ negatif ya da cok buyuk tarih diyez
- ✅ saat ve dakika ay ayrimi
- ✅ gecen sure
- ✅ kanonik yerel gidis donus `[#,##0.00-#.##0,00]
- ✅ kanonik yerel gidis donus `[dd.mm.yyyy-gg.aa.yyyy]
- ✅ kanonik yerel gidis donus `[d mmmm yyyy dddd-g aaaa yyyy gggg]
- ✅ kanonik yerel gidis donus `[[Red]0.0%;[Blue]-0.0%-[K\u0131rm\u0131z\u0131]0,0%;[Mavi]-0,0%]
- ✅ kanonik yerel gidis donus `[General-Genel]
- ✅ kanonik yerel gidis donus `[0.00E+00-0,00E+00]
- ✅ kanonik yerel gidis donus `[[>1.5]0.0;0-[>1,5]0,0;0]
- ✅ kanonik yerel gidis donus `[hh:mm:ss.00-hh:mm:ss,00]
- ✅ kanonik yerel gidis donus `[[h]:mm-[h]:mm]
- ✅ kanonik yerel gidis donus `[#,##0.00 "\u20ba"-#.##0,00 "\u20ba"]
- ✅ kanonik yerel gidis donus `[# ?/?-# ?/?]
- ✅ kanonik yerel gidis donus `[@-@]
- ✅ hazir ve ornek kodlar gidis donus `[General]
- ✅ hazir ve ornek kodlar gidis donus `[0.00]
- ✅ hazir ve ornek kodlar gidis donus `[#,##0.00]
- ✅ hazir ve ornek kodlar gidis donus `["\u20ba"#,##0.00]
- ✅ hazir ve ornek kodlar gidis donus `["$"#,##0.00]
- ✅ hazir ve ornek kodlar gidis donus `[#,##0.00 "\u20ac"]
- ✅ hazir ve ornek kodlar gidis donus `[_-"\u20ba"* #,##0.00_-;-"\u20ba"* #,##0.00_-;_-"\u20ba"* "-"??_-;_-@_-]
- ✅ hazir ve ornek kodlar gidis donus `[d.mm.yyyy]
- ✅ hazir ve ornek kodlar gidis donus `[d mmmm yyyy dddd]
- ✅ hazir ve ornek kodlar gidis donus `[hh:mm:ss]
- ✅ hazir ve ornek kodlar gidis donus `[0.00%]
- ✅ hazir ve ornek kodlar gidis donus `[# ?/?]
- ✅ hazir ve ornek kodlar gidis donus `[0.00E+00]
- ✅ hazir ve ornek kodlar gidis donus `[@]
- ✅ hazir ve ornek kodlar gidis donus `[[Blue]#,##0.00_);[Red](#,##0.00);0.00;"sales "@]
- ✅ hazir ve ornek kodlar gidis donus `[000-00-0000]
- ✅ hazir ve ornek kodlar gidis donus `[0\\-0]
- ✅ hazir ve ornek kodlar gidis donus `[*-0]
- ✅ yerel tarih harfleri
- ✅ gecersiz kod `["abc]
- ✅ gecersiz kod `[[Foo]0]
- ✅ gecersiz kod `[0;0;0;0;0]
- ✅ gecersiz kod `[0x]
- ✅ gecersiz kod `[[Color0]0]
- ✅ gecersiz kod `[0_]
- ✅ gecersiz kod `[[>a]0]
- ✅ gecersiz kod `[0;@;0]
- ✅ gecersiz kod `[# ?/]
- ✅ sigdir sayi bicimi kisaltilmaz
- ✅ hazir bicimler
- ✅ ondalik artir azalt `[0-1-0.0]
- ✅ ondalik artir azalt `[#,##0.00-1-#,##0.000]
- ✅ ondalik artir azalt `[0.00--1-0.0]
- ✅ ondalik artir azalt `[0.0--1-0]
- ✅ ondalik artir azalt `[0%-1-0.0%]
- ✅ ondalik artir azalt `["\u20ba"#,##0.00--2-"\u20ba"#,##0]
- ✅ ondalik artir azalt `[0.00;(0.00)-1-0.000;(0.000)]
- ✅ ondalik genel degerden baslar
- ✅ hizli yol genel yolla ayni `[0]
- ✅ hizli yol genel yolla ayni `[#,##0.00]
- ✅ hizli yol genel yolla ayni `[0.0%]
- ✅ hizli yol genel yolla ayni `["\u20ba"#,##0.00]
- ✅ hizli yol genel yolla ayni `[#,##0,]
- ✅ hizli yol genel yolla ayni `[0.000]
- ✅ hizli yol genel yolla ayni `[#]
- ✅ hizli yol genel yolla ayni `[.00]
- ✅ hizli yol genel yolla ayni `[00000]
- ✅ hizli yol genel yolla ayni `[_-* #,##0.00_-]
- ✅ basarim kaba

### `testler/test_senaryo_bicimli.py` — 8/8 ✅
**

- ✅ baslik birlesim ve biçim
- ✅ para ve yuzde gorunumu
- ✅ tarih girisi ve ay doldurma
- ✅ boyaci ile biçim tasima ve geri al
- ✅ kopyala yapistir biçim ve formul tasir
- ✅ dondur ve gorunum sayfaya ozel
- ✅ hucreleri degistirince para biçimi degeri bozmaz
- ✅ metni kaydir otomatik satir yuksekligi

### `testler/test_senaryo_butce.py` — 8/8 ✅
*Faz 2 gerçek iş senaryosu: aylık bütçe çizelgesi (iki sayfa, kopyalama, ekle-sil, geri al, döngü, taşıma)*

- ✅ satir toplamlari asagi kopyalanir
- ✅ sutun toplamlari
- ✅ ozet sayfasi sayfalar arasi basvuru
- ✅ veri degisince ozet yeniden hesaplanir
- ✅ satir ekleyince formuller ve araliklar genisler ve geri alinir
- ✅ sifira bolme ve hata yayilimi
- ✅ dongu senaryosu uyari ve cozum
- ✅ kes yapistir sutunu tasiyinca basvurular izler

### `testler/test_senaryo_stok.py` — 7/7 ✅
*Faz 5 gerçek iş senaryosu: stok listesi (ad+DÜŞEYARA, doğrulama, koşullu biçim, sırala, filtre, ALTTOPLAM, not) + stok.xlsx örnek dosya gidiş-dönüşü*

- ✅ formuller adlar ve fiyat tablosu
- ✅ dogrulamali kategori ve adet
- ✅ kritik stok koşullu biçim ve tutar cubugu
- ✅ sirala filtrele alttoplam ve notlar
- ✅ kaydet yeniden ac geri al ve pdf
- ✅ ornek dosya stok xlsx gidis donus
- ✅ ornek dosya degismez

### `testler/test_sirala.py` — 28/28 ✅
*Sırala (5c): Türkçe harmanlama, karışık tür, çok düzey, renk, gizli satır, formül kayması, geri al*

- ✅ TestPlan::test artan azalan sayi
- ✅ TestPlan::test turkce harf sirasi
- ✅ TestPlan::test karisik tur ve bos en sonda
- ✅ TestPlan::test kararli ve cok duzey
- ✅ TestPlan::test baslik atlanir
- ✅ TestPlan::test buyuk kucuk duyarli
- ✅ TestPlan::test formul sonucuna gore
- ✅ TestPlan::test gizli satirlar yerinde kalir
- ✅ TestPlan::test birlesim reddedilir
- ✅ TestPlan::test olcut aralik disinda ve olcutsuz
- ✅ TestPlan::test renge gore
- ✅ TestPlan::test sutun sirala soldan saga
- ✅ TestBaslikTahmin::test metin ustu sayi
- ✅ TestBaslikTahmin::test hepsi sayi degil
- ✅ TestBaslikTahmin::test hepsi metin baslik sayilmaz
- ✅ TestBaslikTahmin::test kalin baslik
- ✅ TestBaslikTahmin::test tek satir
- ✅ TestKomut::test hucreler stil not tasinir geri al
- ✅ TestKomut::test formuller kopyala gibi kayar
- ✅ TestKomut::test mutlak basvuru sabit
- ✅ TestKomut::test disaridan baglanti degismez
- ✅ TestKomut::test gizli ve digerleri yerinde tek olay
- ✅ TestKomut::test birlesim yerinde
- ✅ TestKomut::test sutun sirala komutu
- ✅ TestKomut::test ana sayfa
- ✅ TestKomut::test yuz bin satir hizli
- ✅ TestKarsilastirmaTurkce::test karsilastir
- ✅ TestKarsilastirmaTurkce::test formul ve olcut

### `testler/test_sirala_arayuz.py` — 12/12 ✅
*Sırala arayüzü (5c): A→Z/Z→A, Sıralama Uyarısı, Özel Sıralama penceresi*

- ✅ menu eylemleri acik
- ✅ tek hucre artan baslik tahmini ve geri al
- ✅ azalan sayi sutunu
- ✅ sutun secimi yaninda veri uyarisi
- ✅ uyari genislet ve iptal
- ✅ birlesim varsa reddedilir
- ✅ coklu secim reddedilir
- ✅ ozel siralama penceresi duzeyler
- ✅ ozel siralama en cok 64 duzey
- ✅ ozel siralama uygula cok duzey
- ✅ ozel siralama renk secenekleri
- ✅ sag tik menusunde sirala

### `testler/test_stil.py` — 26/26 ✅
*Stil modeli (3a): Stil/StilYama/havuz, etkin stil önceliği, bicim olayı, BicimDegis, bicim_komutu, ekle-sil + geri al*

- ✅ stil varsayilanlari excel gibi
- ✅ stil dogrulama ve renk normallestirme
- ✅ stil yama kismi ve kenar birlestirme
- ✅ stil yama hash ve esitlik
- ✅ havuz interning ve yama onbellegi
- ✅ etkin stil hucre satir sutun sirasi
- ✅ acik varsayilan hucre satir stilini ezer
- ✅ bicim yaz aralik disi hata
- ✅ toplu bicim tek olay ve degismeyen olay yok
- ✅ bicim olayi formul motorunu ve hucre olayini tetiklemez
- ✅ bicim degis komutu geri al yinele
- ✅ bicim komutu aralik ve coklu secim
- ✅ bicim komutu kismi yama mevcut stili korur
- ✅ bicim komutu tam satir ve sutun stile yazilir
- ✅ bicim komutu tam satir acik kayitli hucreye de uygular
- ✅ bicim komutu asiri buyuk aralik reddedilir
- ✅ 100000 hucreye yama hizli
- ✅ satir ekle ustteki biclimi devralir ve alttakiler kayar
- ✅ ilk satira ekleme devralmaz
- ✅ satir stili ekle sil ile kayar ve devralinir
- ✅ satir sil stilleri kaydirir ve geri alinca aynen doner
- ✅ sutun ekle sil stil
- ✅ ekleme sayfa sonuna iterse stil kaybolur degil kayit atilir
- ✅ kullanilan aralik bicim dahil
- ✅ sayfa baska kitaba baglaninca kimlikler cevrilir
- ✅ sayfa silinip geri gelince stilleri korur

### `testler/test_toplu_ve_sonuc.py` — 12/12 ✅
*Toplu yazım ve girdi/sonuç ayrımı (K4)*

- ✅ toplu yaz tek olay ve eskiler
- ✅ toplu yaz hic degisiklik yoksa olay yok
- ✅ toplu yaz sinir disi hata verir
- ✅ toplu yaz kullanilan aralik ve sonuclari gunceller
- ✅ formul hucresi sonuc gelene kadar bos gorunur
- ✅ hata sonucu turkce ve ortali
- ✅ metin sonucu soldan tasar
- ✅ otomatik sigdir sonucu olcer
- ✅ ozet formul sonuclarini toplar
- ✅ ozet ust uste binen araliklar bir kez sayilir
- ✅ toplu yaz kullanilan aralik onbellegi rastgele islemlerle eslesir
- ✅ toplu yaz ata ile ayni sonucu verir

### `testler/test_xlsx_io.py` — 17/17 ✅
**

- ✅ degerler ve formuller
- ✅ sayi bicimi ve tarih
- ✅ stil gidis donus
- ✅ varsayilan font none kalir
- ✅ olculer gizli birlesim dondurma
- ✅ satir sutun stili
- ✅ cok sayfa ve sayfalar arasi formul
- ✅ xlfn oneki
- ✅ baska programda olusturulmus dosya
- ✅ veri kaybi taramasi
- ✅ kosullu bicim ve dogrulama uyarisi
- ✅ bozuk dosya anlasilir hata
- ✅ kayit gecici dosya kalmaz
- ✅ kayit hatasinda eski dosya bozulmaz
- ✅ gizli sayfa uyarisi
- ✅ hizli formul yolu yavasla ayni sonuc
- ✅ buyuk dosya gidis donus ayni

### `testler/test_xlsx_ornekler.py` — 9/9 ✅
**

- ✅ butce okunur beklenen icerik
- ✅ butce hesap dogru
- ✅ butce gidis donus kayipsiz
- ✅ butce openpyxl ile de ayni — Bizim yazdığımız dosyayı başka bir okuyucu (openpyxl) de aynı görür.
- ✅ grafikli uyarilar ve veri korunur
- ✅ ozgun dosya degismez
- ✅ turkce csv
- ✅ utf8 virgullu csv tirnakli alan
- ✅ is akisi ac duzenle kaydet pdf csv

### `testler/test_yazdir.py` — 16/16 ✅
**

- ✅ dolgu ve kenarlik cizilir
- ✅ kilavuz yalniz istenince
- ✅ metin cizilir ve tasar
- ✅ birlesim tek dikdortgen ve yatay ortala
- ✅ olcek cizimi kucultur
- ✅ pdf yaz sayfa sayisi ve yon
- ✅ pdf bos sayfa dosya yazmaz
- ✅ pdf tum sayfalar farkli yon
- ✅ pdf yazma hatasi
- ✅ menuden pdf
- ✅ menuden bos sayfa pdf uyarir
- ✅ sayfa yapisi penceresi ve geri al
- ✅ sayfa yapisi gecersiz giris pencereyi kapatmaz
- ✅ baslik satirlari yazim
- ✅ otomatik satir yuksekligi yazdirmaya yansir
- ✅ sigmayan sayi diyez basar

### `testler/test_yerellestirme.py` — 37/37 ✅
*TR ⇄ kanonik çeviri: ayırıcılar, fonksiyon/hata adları, sayfa başvuruları*

- ✅ tr den sakliya `[=TOPLA(A1:A3;2,5)-=SUM(A1:A3,2.5)]
- ✅ tr den sakliya `[=topla(a1:a3; 2,5)-=SUM(A1:A3, 2.5)]
- ✅ tr den sakliya `[=E\u011eER(A1>0;"a;b,c";YANLI\u015e)-=IF(A1>0,"a;b,c",FALSE)]
- ✅ tr den sakliya `[=e\u011fer(do\u011fru;1;2)-=IF(TRUE,1,2)]
- ✅ tr den sakliya `[=TOPLA(E\u011eER(A1;1;2);3)-=SUM(IF(A1,1,2),3)]
- ✅ tr den sakliya `[={1\\2;3\\4}-={1,2;3,4}]
- ✅ tr den sakliya `[=#B\xd6L/0!-=#DIV/0!]
- ✅ tr den sakliya `[=#yok-=#N/A]
- ✅ tr den sakliya `[=$b$2*c3-=$B$2*C3]
- ✅ tr den sakliya `[=B2:A1-=A1:B2]
- ✅ tr den sakliya `[=1,5E3-=1.5E3]
- ✅ tr den sakliya `[=SUM(1;2)-=SUM(1,2)]
- ✅ tr den sakliya `[=if(1;2;3)-=IF(1,2,3)]
- ✅ gidis donus `[=TOPLA(A1:A3;2,5)]
- ✅ gidis donus `[=E\u011eER(A1>0;"a;b,c";YANLI\u015e)]
- ✅ gidis donus `[={1\\2;3\\4}]
- ✅ gidis donus `[=#B\xd6L/0!+#YOK]
- ✅ gidis donus `[=TOPLA( A1 ; B2 )]
- ✅ gidis donus `[='Gelir Gider'!A1:B2*2]
- ✅ gidis donus `[=\u015eubat!$C$5]
- ✅ gidis donus `[=-2^2%]
- ✅ gidis donus `[=A:A]
- ✅ gidis donus `[=2:3]
- ✅ sayfa kimlikle saklanir
- ✅ yeniden adlandirma formulu degistirmez
- ✅ silinen sayfa basv
- ✅ olmayan sayfa reddedilir
- ✅ hatali girdi `[=TOPLA(]
- ✅ hatali girdi `[=1+]
- ✅ hatali girdi `[=E\u011eER(1)]
- ✅ hatali girdi `[="abc]
- ✅ hatali girdi `[=1;2]
- ✅ hatali girdi `[=TOPLA()]
- ✅ bilinmeyen fonksiyon kalir
- ✅ ingilizce disa ve iceri
- ✅ turkcesi olmayan fonksiyon ingilizce gorunur
- ✅ tum adlar gidis donus

<!-- OTOMATIK:BITIR -->

---

## 4. Performans ölçümü — 100.000 dolu hücre (5.000 × 20)

*Araç: `araclar/performans_olcum.py`. Hedef (plan.md Faz 1): akıcı kaydırma, **kare başına < 16 ms**. Pencere 1280×800, gerçek yazı tipi, Windows. Boş sayfada aynı ölçüm düzeneğinin kendi yükü ≈ 13 ms/kare (referans).*

**Faz 2'ye geçiş şartının yanıtı:** *Akıcı kaydırma hedefi (tek adım/üç adım dikey, ok tuşu) karşılandı ✅; ilk ölçümde 49 ms olan kare süresi 9–14 ms'ye indi.* Kalan 6 ölçüm hedefin üstünde (❌) — aşağıda gerekçeleriyle; **kabul edilip edilmeyeceği kullanıcı kararıdır** (§6).

| Ölçüm | İlk ölçüm | Optimizasyon sonrası | Hedef | Sonuç |
|---|---|---|---|---|
| Dikey kaydırma 1 satır/kare (başta) | 49 ms | **8,7 ms** | 16 | ✅ |
| Dikey kaydırma 1 satır/kare (ortada) | 49 ms | **9,8 ms** | 16 | ✅ |
| Dikey kaydırma 3 satır/kare | — | **13,7 ms** | 16 | ✅ |
| Ok tuşu ile hücre değiştirme + boyama | (tam çizim 58 ms) | **15,4 ms** | 16 | ✅ (sınırda) |
| Dikey sıçrama (kaydırma çubuğu sürükleme, 500 satır/kare) | 34 ms | 28,8 ms | 16 | ❌ tam çizim gerekir (≈35 ms) |
| Yatay kaydırma | 29 ms | 18,6 ms | 16 | ❌ tam çizim (taşan metin nedeniyle artımlı yapılmadı) |
| Shift+Ok ile seçim genişletme + boyama | — | 25,1 ms | 16 | ❌ durum çubuğu özeti + bölge boyama |
| İlk çizim (soğuk önbellek) | 123 ms | 40,5 ms | 16 | ❌ tek seferlik, kare değil |
| Ctrl+A + durum çubuğu özeti (100.000 hücre seçili) | 583 ms | 105 ms | 100 | ❌ marjinal; tek seferlik |
| Durum çubuğu özeti, 100.000 hücre seçili | 543 ms | **82 ms** (olay katmanı + sonuç ayrımı sonrası yeniden ölçüldü) | 100 | ✅ |
| Tam çizim (bilgi) | 123 ms | 34,6 ms/kare | — | bilgi |
| Veri yükleme (100.000 `ata`) | 334–1030 ms | 797 ms | — | bilgi |
| Ctrl+Aşağı / Ctrl+Yukarı / Ctrl+End | 28 / 31 / 26 ms | 45 / 8 / 2 ms | 100 | ✅ |
| `kullanilan_aralik()` (önbellekli) | 21 ms | 0,0 ms | 50 | ✅ |
| Tek hücre düzenleme / geri al / yinele | 0,3 / 0,2 / 0,2 ms | 1,0 / 0,5 / 0,4 ms | 50 | ✅ |
| Seçimi sil (100.000 hücre) / geri al | 647 / 638 ms | 211 / 237 ms | 2000 | ✅ |
| Kopyala (100.000; TSV+HTML+JSON) | 973 ms | 826 ms | 3000 | ✅ |
| Yapıştır (100.000) / geri al | 3044 / 587 ms | **1058 / 151 ms** | 3000 | ✅ |
| Satır ekle (en üste) / geri al | 646 / 606 ms | 120 / 74 ms | 1000 | ✅ |
| Sütun otomatik sığdır (5.000 hücre) | 726 ms | 130 ms | 500 | ✅ |
| Sütun sil / geri al | 591 / 708 ms | 83 / 96 ms | 1000 | ✅ |

**Yapılan optimizasyonlar** (ölçüm → profil → düzeltme): metin genişliği/sayı metni/`QStaticText` önbelleği; sığan metne `setClipRect` yok; dikey kaydırmada `viewport().scroll()` + yalnızca açığa çıkan satırları çizme (`scrollContentsBy` boşaltıldı: Qt varsayılanı tüm viewport'u geçersiz kılıyordu); seçim değişince yalnızca eski+yeni bölge boyanır; `kullanilan_aralik` önbelleği; büyük aralık işlemleri için sırasız `aralikta`/`dolu_hucreler(sirali=False)`.

**Ölçüm düzeneğinin sınırı:** `processEvents` Windows pencere birleştirmesini de içerir; gerçek kare süresi bu rakamlardan biraz düşük olabilir. Ölçüm 100.000 hücrelik *tüm sayfa dolu* senaryosu (en kötü durum).

---

## 5. Gerçek pencere piksel doğrulaması (`araclar/cizim_dogrula.py`)

Gerçek ekran görüntüsü ile sıfırdan çizilen görüntü karşılaştırılır (900×560, 370.396 piksel/adım). **Bu doğrulama iki gerçek hata yakaladı (düzeltildi):** (1) seçili alan ekran dışına kayınca sütun başlığı vurgusu eski kalıyordu; (2) çok uzun seçimlerin çerçevesi görünür alan kenarına çizilip kaydırmada artefakt bırakıyordu (sonra 28 piksellik "boşluk" da bulundu ve kapatıldı).

| Adım | Sonuç |
|---|---|
| başlangıç | ✅ 0 fark |
| 7 satır aşağı kaydırma (artımlı) | ✅ 0 |
| 7 satır yukarı kaydırma (artımlı) | ✅ 0 |
| taşan metin satırına kaydırma | ✅ 0 |
| çok hücreli seçim (kısmi boyama) | ✅ 0 |
| seçili alanla kaydırma | ❌ **1 piksel** fark (bilinen, bkz. §6) |
| seçimi taşıma (eski/yeni bölge) | ✅ 0 |
| Ctrl+tık çoklu seçim | ✅ 0 |
| kopyalama çerçevesi | ✅ 0 |
| sütun seçimi | ✅ 0 |
| sütun seçili, 6 adım kaydırma | ✅ 0 (her adımda) |
| **Toplam** | **1 piksel / ~6 milyon** (araç tolerans 1 ile geçer) |

---

## 6. Olumsuz / açık sonuçlar ve bilinen kusurlar

| # | Konu | Etki | Durum |
|---|---|---|---|
| 1 | Kaydırma çubuğunu sürükleyince (sıçrama) kare süresi ≈ 29 ms | Hafif takılma; Qt olayları birleştirdiği için pratikte az fark edilir | ❌ kabul önerilir; iyileştirme: sütun başına çizim önbelleği (Faz 3 biçimlendirmeyle birlikte) |
| 2 | Yatay kaydırma ≈ 18,6 ms/kare | Hedefin %16 üstü | ❌ kabul önerilir; artımlı yatay çizim taşan metin yüzünden riskli |
| 3 | Shift+Ok ile seçim genişletme ≈ 25 ms | Basılı tutunca takılma | ❌ iyileştirilebilir: özeti gecikmeli (zamanlayıcıyla) hesaplamak |
| 4 | Ctrl+A (tümünü seç) + özet ≈ 105–160 ms (özetin kendisi 82 ms ✅; geri kalanı Qt seçim/boyama) | Tek seferlik | ❌ marjinal |
| 5 | İlk çizim ≈ 40 ms | Tek seferlik | ❌ kare süresi değil |
| 6 | Seçili alan ekranın bir kenarından dışarı taşarken 1 piksellik köşe artefaktı | Görünmez; sonraki tam çizimde düzelir | ❌ bilinen, düşük öncelik |
| 7 | Fare sürüklerken kenarda sürekli otomatik kaydırma yok (her fare olayında 1 adım) | Excel'de fare kenarda durunca kaydırma sürer | ➖ eksik özellik |
| 8 | Ekran dışına kaymış hücrenin sağa taşan metni görünür alana uzanmıyor | Nadir | ➖ eksik özellik |
| 9 | Çoklu seçimde satır/sütun ekle-sil-gizle yalnız son aralığa uygulanır | Excel hepsine uygular | ➖ Faz 3'te |

**Karar bekleyen:** yukarıdaki 1–5. maddeler (performans) Faz 2'ye geçişi engelliyor mu? Önerim: **hayır** — plan.md'nin kendi ölçütü olan "akıcı kaydırma" karşılandı; kalanlar Faz 3'te (biçimlendirmeyle çizim yeniden yapılırken) ele alınabilir. ✅ **Kullanıcı kabul etti (2026-10-09)** — Faz 3'e.

---

## 7. Elle test bekleyenler (kullanıcı)

| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | Gerçek kullanım denemesi | `Tabcel.bat` ile aç; yaz, kaydır, seç, kopyala/yapıştır, sekme ekle, yakınlaştır | ⏳ |
| 2 | Windows 11 başlık çubuğu yeşil mi? | Pencerenin üst çubuğuna bak | ⏳ |
| 3 | Excel/Google E-Tablolar'dan yapıştırma | Excel'de bir aralığı kopyala → Tabcel'de yapıştır; tersini de dene | ⏳ |
| 4 | Excel web doğrulama listesi (11 madde) | `surec.md` §8b | ⏳ |

---

## 8. Faz 1 gözden geçirmesi (Opus 5.5) — 2026-10-08

*Yapan: Opus 5.5 (salt okunur alt ajan; Claude Code'da `/model` yalnızca kullanıcıda olduğu için ajan olarak çalıştırıldı). Rapor model çıktısıdır; bulgular tek tek **yeniden üretilip** doğrulandı (önce başarısız test, sonra düzeltme).*

**Durum (2026-10-08, aynı gün sonrası):** K1–K3 düzeltildi; kullanıcı onayıyla K4–K6 mimari düzenleme yapıldı (adım adım, her adımda testler geçti: 259 → 322); K7 Faz 2 başında. Performans yeniden ölçüldü, gerileme yok (olay katmanı toplu işlemlerde TEK olay; `toplu_yaz`).

**Genel değerlendirme (Opus):** Faz 1 kodu temiz, katmanlar doğru ayrılmış, testler gerçek davranışı sınıyor; boşa geçen test yok; kural 1/2/5 ihlali yok. Asıl risk modelin *"tek sayfa, doğrudan yazım, girdi ile sonuç aynı nesnede"* varsayımı. **Faz 2'ye geçiş tavsiyesi: koşullu evet** — önce K1–K3 hata düzeltmeleri, K4–K6 mimari kararlar ve K7 tasarım notu.

| # | Bulgu | Önem | Doğrulama | Durum |
|---|---|---|---|---|
| K1 | `Hucre(True) == Hucre(1.0)`: 1 olan hücreye DOĞRU yazmak "değişmedi" sayılıyordu | Kritik | ✅ yeniden üretildi (test kırmızıydı) | ✅ **düzeltildi**: eşitlik/hash artık değer türünü de karşılaştırır; 2 test |
| K2 | Satır/sütun ekleme sayfa sonundaki dolu hücreyi sessizce siliyor, geri al getirmiyor (model düzeyinde; arayüz zaten önceden kontrol ediyordu) | Önemli | ✅ yeniden üretildi | ✅ **düzeltildi**: `Sayfa._kaydir` Excel gibi reddeder (`AdresHatasi`), komut yığına girmez; 3 test |
| K3 | Kes → satır ekle/sil → yapıştır yanlış hücreleri boşaltıyor (kes işareti bayat) + sayfa silinince işaret kalıyor + kaynak düzenlenince kes modu iptal edilmiyor | Önemli | ✅ yeniden üretildi | ✅ **düzeltildi**: içerik/yapı değişikliği ve geri al/yinele ve sayfa silme işareti iptal eder; boyutlandırma/gizleme ve art arda yapıştırma işareti korur; 6 test |
| K4 | Hesaplanan sonuç ile kullanıcı girdisi aynı `Hucre`'de (`deger`+`formul`): her yeniden hesaplama yeni nesne yazar, geri al "girdi + eski sonuç" geri yükler | Mimari | kod okuma + betik | ✅ **yapıldı** (kullanıcı onayladı): `Hucre` yalnız girdi (ya sabit ya formül, ikisi birden hata); sonuç `Sayfa._sonuc` + `sonuc_ata`/`sonuc`/`deger`; girdi değişince sonuç atılır, satır/sütun ekle-sil sonuçları da kaydırır; `Hata` değer türü (`model/deger.py`, Türkçe gösterim doğrulanacak); pano/ızgara/özet sonucu kullanır; 17 test |
| K5 | Tek değişiklik giriş noktası / Qt'siz olay katmanı yok (komutlar `Sayfa.ata`/`_kaydir` çağırır; motor her yazımı görmeli; başka sayfa başvuruları düzeltilmeli) | Mimari | kod okuma | ✅ **yapıldı**: `model/olay.py` + `CalismaKitabi.dinle`; `Sayfa` her yazımda olay yayar (`hucre` [toplu işlemde TEK olay], `sonuc`, `yapi`, `boyut`), kitap `sayfa` olayları (ekle/sil/ad/taşı); sayfa **kimliği** (kalıcı, silme+geri almada aynı); `Sayfa.toplu_yaz`; geri al da aynı yoldan olay yayar; 30 test. *Not:* komutlar hâlâ doğrudan `Sayfa`'ya yazar — tek giriş noktası `Sayfa` mutatörleridir (her yazım olay yayar), bu Faz 2 motoru için yeterli |
| K6 | Sayfa ekle/sil/yeniden adlandır/taşı geri alınamıyor; sayfa silmek tüm geri al geçmişini siler; plan.md "sayfa_tasi + geri al komutu" diyor ama komut yok | Önemli | ✅ kod: window.py `yigin.temizle()` | ✅ **yapıldı** (karar: **kimlik, metinde ad**): `SayfaEkle/Sil/YenidenAdlandir/Tasi` komutları; geçmiş artık silinmez; pencere model olaylarıyla eşitlenir (komutsuz değişiklik, geri al, yinele aynı yoldan); silinen sayfanın ızgarası saklanır (geri alınca seçim/kaydırma korunur); başka sayfadaki değişikliği geri alınca o sayfaya geçilir; 22 test |
| K7 | Formül yazarken başka hücreye tıklamak Excel'de başvuru ekler; bizde onaylıyor (`mousePressEvent`, `focusOutEvent`); pencere odağı kaybolunca (Alt+Tab) düzenleme onaylanıp kapanıyor | Önemli (Faz 2) | kod okuma | ⏳ Faz 2 başında "işaretleme modu" tasarımı |
| — | `_koru` yalnız fare bırakılınca sıfırlanıyor (odak kaybında takılabilir) | Düşük | senaryo üretilemedi | ✅ önlem: odak kaybında sıfırlanır; 1 test |
| — | Geri al yığını bellek: 100.000 hücrelik silme komutu ≈ 16 MB (100 adımda ≈ 1,6 GB; RAM 7,9 GB) | Sonra | ✅ tracemalloc | ⏳ öneri: yığını adım yerine toplam hücre girdisiyle sınırla (2–5 milyon); boş hedef için `None` girdileri saklama |
| — | Ölçek (Faz 4: 100.000×20=2 milyon hücre ≈ 423 MB; `_kaydir` 1,8 sn; `dolu_hucreler(sirali=True)` 4,8 sn) | Sonra | ✅ ölçüldü | ⏳ `@dataclass(slots=True)`, satır dizinli yapı — Faz 4 öncesi |
| — | Faz 3 hazırlığı: `Hucre.stil` tam sayı kimliği + kitapta stil tablosu; `_kaydir` kaydırılan yapı kayıt listesi; dondurma artımlı dikey kaydırmayı bozar (`vp.scroll` dikdörtgeni donmuş satırların altıyla sınırlanmalı) | Sonra | kod okuma | ⏳ Faz 3 |
| — | Kaydırma çubuğu aralığı sabit 1.048.576 (sürüklemede çok hassas; Excel kullanılan alan+pay ile ölçekler) | Sonra | kod okuma | ⏳ |
| — | `CLAUDE.md` eski ifadeler ("hedef — Faz 1'de oluşur"); `girdi.py` formülü Türkçe saklıyor (kural 3'e Faz 2'de bağlanmalı) | Düşük | ✅ | ⏳ CLAUDE.md değişikliği kullanıcı onayıyla |
| — | `main.py` geçici örnek veri Faz 4'te kalkmalı; `suruklenuyor` yazımı | Düşük | — | ⏳ |

**Opus'un doğrulayamadıkları (belirsiz):** `QWidget::scroll`'un bekleyen güncelleme bölgelerini doğru kaydırması ve kopya çerçevesi zamanlayıcısıyla çakışması (animasyon yok, sorun beklenmez; piksel doğrulaması §5'te 0 fark verdi); düzenleme açıkken Ctrl+PageDown ile sayfa değişimi (kod okumaya göre doğru, çalıştırılmadı); `slots=True` bellek kazancı (ölçülmedi).

**Test kalitesi (Opus):** boşa geçen test yok; bulunan hatalar tam kapsam boşluklarındaydı (mantıksal≠sayı, sayfa sonu taşması, kes+yapı değişikliği, kes+silinen sayfa, focusOut onayı, sayfa silindikten sonra geri al). Bunlardan ilk üçü artık testli; **kes + silinen sayfa** pencere testinde, **focusOut onayı** ve **sayfa silindikten sonra geri al** henüz testsiz (K6/K7 ile birlikte ele alınacak).

**Performans kabulü (Opus):** `test.md` §6'daki kabul önerisine **katılıyor**; tek şart: çizim Faz 3'te stil ve dondurmayla yeniden ele alınırken satır bazlı önbellek planlanmalı.

---

## 9. Faz 2 — formül motoru (2026-10-09)

**Sonuç: 1236 test, hepsi geçiyor** (Faz 1 sonunda 259; Faz 2 ile +977). Dosya dökümü §3'te.

### 9.1 Kapsam
| Alan | Katman | Durum | Not |
|---|---|---|---|
| Sözcükleyici + ayrıştırıcı (öncelik, `-2^2`, kesişim, dizi sabiti, atlanmış argüman, sayfa önekleri) | A | ✅ | `test_formul_ayristir` |
| Değerlendirici (365 dizi semantiği, tür dönüşümleri, hata yayılımı, 15 basamak, 1900 tarih seri) | A | ✅ | `test_degerlendir` |
| TR ⇄ kanonik çeviri (ayırıcı, fonksiyon/hata adları, kimlikli sayfa başvurusu) | A | ✅ | `test_yerellestirme` — adlar tr-tr belgelerinden tek tek doğrulandı |
| Fonksiyon kütüphanesi: 115 fonksiyon, 8 grup, her biri 4+ vaka (kural 11) | A | ✅ | altın değerler Microsoft örneklerinden; `TEXT` (METNEÇEVİR) Faz 3'e bağlı |
| Bağımlılık grafiği, yeniden hesaplama, döngü, sayfa işlemleri | A | ✅ | `test_motor` |
| Başvuru kaydırma: kopyala / ekle-sil / taşı | A | ✅ | `test_kaydir` |
| Pano ve formül: kopyada kayma, kes = taşıma, dış formül çevirisi | B | ✅ | `test_pano_formul` |
| İşaretleme modu, F4, renkli başvuru, odak kaybı, formül çubuğu paylaşımı, sekmeler arası başvuru | B | ✅ | `test_isaretleme*` |
| Alt+=, otomatik tamamlama, ipucu | B | ✅ | ipucunda argüman adı yok (§8b-22) |
| Döngü uyarısı, geri al sayfa geçişi | B | ✅ | `test_dongu_arayuz`, `test_gecmis_sayfa_gecisi` |
| **Gerçek iş senaryosu: aylık bütçe çizelgesi** | B/E | ✅ | `test_senaryo_butce` (8 test): Türkçe formül girişi, aşağı kopyalama, iki sayfa arası ETOPLA/EĞER/YUVARLA, satır ekleyince aralıkların genişlemesi + geri al, sıfıra bölme/EĞERHATA, döngü, sütun taşıma |
| Görsel (renkli çerçeve + yazı, öneri listesi) | E | ✅ | ekran görüntüleriyle incelendi |
| Gerçek Excel'de aynı çizelge | F | ⏳ | kullanıcı: aynı bütçeyi Excel web'de kurup değerleri karşılaştırsın |

### 9.2 Performans (`araclar/formul_olcum.py`; ayrıntı `surec.md` §8)
50.000 formüllük zincir yazım+hesap 5,1 sn (çoğu ayrıştırma; Faz 4'te paylaşılan formül önbelleği); zincirde baştaki değişiklik 1,0 sn; sona bağlı tek değişiklik 0,2 ms; 5.000 satır çizelge + birikimli `TOPLA($D$1:D5000)` yazım 1,2 sn, tek hücre değişince 0,14 sn. Hedef karşılanmadı sayılan yok; 50.000 zincir 5 sn **kabul** (Faz 4'te iyileştirilecek).

### 9.3 Açık / bilinen kusurlar
| # | Konu | Durum |
|---|---|---|
| 1 | Taşma (spill) yok: çok hücreli sonuç tek değere iner | ➖ Faz 8 (bilerek) |
| 2 | `TEXT`/METNEÇEVİR ve metin tarihleri (`"1.1.2026"`) yok | ➖ Faz 3 (sayı biçimi çözümleyicisi) |
| 3 | `RANK.EŞİT`, `MODE.SNGL` ve benzeri yeni adlar yok | ➖ doğrulanınca (§8b-20) |
| 4 | Fonksiyon ipucunda gerçek argüman adı yok | ➖ §8b-22 |
| 5 | Sekme geçişinde hücre içi düzenleme formül çubuğuna taşınır | ➖ bilinçli sapma |
| 6 | Kriter/COUNTIF tam sütunda yalnız kullanılan alanı sayar (COUNTBLANK hariç) | ➖ §8b-21 |
| 7 | Enter çok hücreli seçimde gezmez | ➖ §8b-9 |
| 8 | Gerçek fare/klavye ile sekme tıklama, odak kaybı (Alt+Tab) akışları ekransız testle sınandı, **elle denenmedi** | ⏳ kullanıcı |

### 9.4 Elle test bekleyenler (kullanıcı)
| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | Formül yazarken hücreye tıklayıp başvuru ekleme | `=` yaz, hücrelere tıkla/sürükle, ok tuşları, F4; renkli çerçeveler | ⏳ |
| 2 | Formül yazarken başka sayfa sekmesine tıklama | Sayfa2'ye geç, hücre tıkla, Enter → ilk sayfaya dönmeli | ⏳ |
| 3 | Alt+Tab ile başka uygulamaya geçip dönme | Formül yarımken; düzenleme açık kalmalı | ⏳ |
| 4 | Alt+= ve otomatik tamamlama | Sayı sütununun altında Alt+=; `=TOP` yaz → liste, Tab | ⏳ |
| 5 | Excel'den formüllü aralık yapıştırma | Excel'de formüllü aralığı kopyala → burada yapıştır (şu an değer/metin gelir) | ⏳ |
| 6 | Bütçe çizelgesini Excel web'de kur | `test_senaryo_butce.py`'deki veri ve formüllerle; sonuçları karşılaştır | ⏳ |

---

## 10. Faz 2 gözden geçirmesi (Opus 5.5) — 2026-10-09

Salt okunur Opus 5.5 alt ajanı (70 araç çağrısı, çalıştırarak doğrulama; rastgele işlem dizileriyle 600 özellik testi dahil). **Tavsiye: koşullu evet** (1, 2, 3 önce; 6, 7 küçük; 4, 5 Faz 3 başında). Her bulgu bizde yeniden üretildi, düzeltildi ve gerileme testi yazıldı.

| # | Önem | Bulgu | Sonuç |
|---|---|---|---|
| 1 | KRİTİK | Yeniden hesap karesel: 4000 satırlı satır-TOPLA + yürüyen bakiye, A1 değişince 19,9 sn | ✅ düzeltildi → 0,1 sn (`test_motor`: bakiye zinciri, hareketli ortalama) |
| 2 | KRİTİK | `=TOPLA(A:A)` her turda 1.048.576 satır geziyor (0,4 sn, ~200 MB) | ✅ kullanılan alana kırpıldı → 0,5 ms |
| 3 | KRİTİK | EĞER/ÇOKEĞER dizi koşulunda öğe öğe çalışmıyor; `=TOPLA(EĞER(A1:A3>1;A1:A3;0))` 0 (Excel 365: 5), sessiz yanlış | ✅ `dizi_sec` (5 test) |
| 4 | ORTA | Ölçüt aralık/dizi olunca EĞERSAY/ETOPLA 0 (benzersiz sayma deyimi bozuk) | ✅ `olcut_yayar` (8 fonksiyon; 2 test) |
| 5 | ORTA | Ölçütte Türkçe hata adı (`"#BÖL/0!"`) tanınmıyor | ✅ |
| 6 | ORTA | **Kural 4 ihlali:** DATEDIF Türkçe adı `TARİHFARKI` yanlış; doğrusu `ETARİHLİ` | ✅ düzeltildi; **116 adın tamamı sözdizimi satırına karşı yeniden tarandı, başka hata yok**; `"G"`, `"YG"` birimleri eklendi |
| 7 | ORTA | Başka sayfadan formül yazarken işaret dışı tıklama düzenlemeyi ne onaylıyor ne iptal ediyor; sonraki giriş yanlış hücreye gidiyor | ✅ tıklama formülü ilk hücreye onaylar (2 test) |
| 8 | DÜŞÜK | Ölçütte eşitlik 15 basamakla karşılaştırılmıyor | ➖ Excel davranışı doğrulanacak (§8b-25) |
| 9 | DÜŞÜK | ETARİHLİ `"Y"` / `"YD"` çelişkisi (29.2.2020→28.2.2021) | ➖ doğrulanacak (§8b-23) |
| 10 | DÜŞÜK | `"="` ölçütü `""` ile aynı işleniyor | ➖ doğrulanacak (§8b-24) |
| 11 | DÜŞÜK | Kopyada sayfa önekli başvuru taşarsa önek düşüyor (`=#BAŞV!`) | ➖ yalnız görünüm (§8b-29) |
| + | (bizim) | `NA()` fonksiyonu yoktu (testle çıktı) | ✅ eklendi: `YOKSAY` (tr-tr sayfasıyla doğrulandı) |

**Temiz çıkanlar:** motor + geri al/yinele rastgele dizilerle (hücre yaz, satır/sütun ekle-sil, taşıma, sayfa ekle/sil) bağımsız tam hesapla birebir; DOLAYLI/KAYDIR, sayfa yeniden adlandırma, sayfa sil-geri al, döngü; tarih uç değerleri (1900, 0/60, EDATE/EOMONTH, WEEKNUM, NETWORKDAYS); `-2^2`, `%`, `&`, hata sırası, #YOK doldurma, kesişim; kural 2 (model/formul Qt içe aktarmıyor).

**İncelenmeyenler (Faz 3 başında hafifçe gözden geçirilebilir):** `arama/metin/finans/bilgi/istatistik` fonksiyonlarının tek tek doğruluğu (ölçütlüler dışında), `sozcuk.py`/`agac.py` ayrıştırıcı uç durumları, pano/otomatik tamamlama/odak kaybının gerçek pencerede davranışı (elle test), kural 11 sayımı ve test kalitesi taraması.

**Ders:** Microsoft tr-tr işlev sayfalarının **başlığı** (makine çevirisi) güvenilmez; ad yalnızca **sözdizimi/örnek satırından** doğrulanmalı (`araclar`'a taşınabilir: toplu doğrulama betiği `araclar/adlar_dogrula.py`).


---

## 11. Faz 3 — biçimlendirme, sayı biçimleri, doldurma, dondurma (2026-10-09)

**Sonuç: 1809 test, hepsi geçiyor** (Faz 2 sonunda 1236 → Faz 3 ile +573; ara kilometre taşı 1787 3j, 1801 3k, +8 senaryo).

### 11.1 Kapsam
| Alan | Katman | Durum | Test dosyası |
|---|---|---|---|
| Stil modeli, havuz (interning), etkin stil önceliği, `BicimDegis`, ekle-sil kaydırması | A | ✅ | `test_stil` |
| Sayı biçimi çözümleyici (Genel, bölümler, koşul, renk, tarih/saat, kesir, bilimsel, yerel⇄kanonik) | A | ✅ | `test_sayi_bicimi`, `test_bicim_kodlari` |
| Izgara çizimi (dolgu, kenarlık, yazı, hizalama, önbellek, artımlı = tam çizim) | B/E | ✅ | `test_izgara_stil` |
| Pano: biçim + birleşim taşıma, kes-yapıştır | B | ✅ | `test_pano_bicim`, `test_birlesim_pano` |
| Biçim çubuğu, Hücreleri Biçimlendir, kısayollar | B | ✅ | `test_bicim_cubugu`, `test_bicim_islem`, `test_bicim_penceresi` |
| Birleştirilmiş hücreler (model, gezinme, çizim, ekle-sil, pano) | A/B | ✅ | `test_birlesim`, `test_birlesim_arayuz` |
| Akıllı giriş (yüzde, para, kesir, saat, tarih), Metin biçimi | A/B | ✅ | `test_akilli_giris` |
| Doldurma (seri türleri, tutamaç, Ctrl+D/R/Enter) | A/B | ✅ | `test_doldur`, `test_doldur_arayuz` |
| Dondurma, kılavuz çizgisi | B/E | ✅ | `test_dondurma` |
| Metni kaydır, otomatik satır yüksekliği, Alt+Enter | B/E | ✅ | `test_kaydir_metin` |
| Biçim boyacısı | A/B | ✅ | `test_bicim_boyaci` |
| **Gerçek iş senaryosu: biçimli aylık bütçe** | B/E | ✅ | `test_senaryo_bicimli` (8): birleşik başlık, başlık dolgusu/yazı, para ve yüzde görünümü, tarih girişi, ay adı doldurma (+geri al), boyacıyla biçim taşıma (+geri al), kopyala-yapıştırda biçim + formül kayması (+geri al), dondurma sayfaya özel, para biçimli hücreye değer girişi, kaydırılmış metin satır yüksekliği |
| Görsel (biçimli çizelge ekran görüntüsü) | E | ✅ | birleşik başlık, yeşil başlık şeridi, boyanmış satır, fırça düğmesi görüldü. **Not:** ekransız ortamda yazı tipi yok (kutucuk glifleri); metin görünümü gerçek pencerede elle doğrulanmalı |
| Gerçek Excel'de aynı çizelge | F | ⏳ | kullanıcı |

### 11.2 Performans (`araclar/performans_olcum.py`, 100.000 hücre; ayrıntı `surec.md` §8)
Düz sayfa: dikey 1 satır/kare ✅, yatay 7,2 ms ✅, Ok tuşu 8,4 ms ✅, özet 79 ms ✅. Stilli (10 stil + 4 biçim): ilk çizim 25,8 ms ✅, 1 satır 10,8 ✅, yatay 6,7 ✅, Ok 12,5 ✅.
**Hâlâ hedefi aşan 6 ölçüm (kabul bekliyor):** ilk çizim `grab` 46 ms; dikey sıçrama 27 / stilli 37 ms; Shift+Ok 19,7 / stilli 23,4 ms; stilli 3 satır/kare 17 ms (sınırda). Neden: tam çizimde ~800 hücrede Python döngüsü; çözüm satır/karo piksel önbelleği (Faz 4+ ya da kullanıcı kararı).

### 11.3 Açık / bilinen kusurlar
| # | Konu | Durum |
|---|---|---|
| 1 | Hizalama `doldur`/`iki_yana`/`secim_ortasi` yaklaşık; girinti 9 px/düzey doğrulanmadı | ➖ |
| 2 | İç düzenleyici kaydırılmış metni çok satırlı göstermez; Otomatik Sığdır sütun genişliği kaydırmayı hesaba katmaz | ➖ |
| 3 | Dışarıdan yapıştırılan tarih metni Excel gibi çözülmez (yalnız elle yazım akıllı) | ➖ bilinçli (surec §4 3g) |
| 4 | Dondurma bölmesi sayfa başından (Excel kaydırılmış pencereden); sürükle-böl yok; dondurma/kılavuz .xlsx'e Faz 4'te | ➖ |
| 5 | Doldurma: Ctrl+sürükle, Seri… penceresi, seçenekler düğmesi, otomatik kaydırma yok | ➖ |
| 6 | Boyacı birleşim/boyut taşımaz; tam sütun hedef reddedilir | ➖ |
| 7 | Türkçe Excel kısayol doğrulaması ve §8b-30…33 (biçim kodu harfleri, ÖÖ/ÖS, kısaltmalar) | ⏳ kullanıcı |

### 11.4 Elle test bekleyenler (kullanıcı)
| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | Gerçek pencerede yazı tipleri/hizalama/kenarlık görünümü | Biçimli bütçeyi aç, ekran görüntüsü karşılaştır | ⏳ |
| 2 | Doldurma tutamacı, çift tık, sürükleme hissi | Ay adı / sayı serisi sürükle | ⏳ |
| 3 | Biçim boyacısı: tek tık, çift tık, Esc | Fırça düğmesi | ⏳ |
| 4 | Dondurma + kaydırma, kılavuz kapama | Görünüm menüsü | ⏳ |
| 5 | Metni kaydır + otomatik satır yüksekliği | Uzun metin, sütun daralt | ⏳ |
| 6 | Bütçeyi Excel web'de kur, görünen biçimleri karşılaştır | `test_senaryo_bicimli.py` verisiyle | ⏳ |

---

## 12. Faz 3 gözden geçirmesi (Opus 5.5) — 2026-10-09

Salt okunur Opus 5.5 alt ajanı (57 araç çağrısı; model düzeyinde 1500 tohum × 45 rastgele işlemle geri al/yinele, 55 bilinen Excel sayı biçimi örneği, 60.000 rastgele biçim kodu, 600.000 sayılık yuvarlama karşılaştırması). **Tavsiye: koşullu evet** (1–6 düzeltilmeden Faz 3 kapanmasın; 7–8 aynı tur). Bulgular bizde yeniden üretilip düzeltildi; gerileme testleri `testler/test_opus_faz3.py` (54 test). Testler 1809 → **1863**, hiçbir mevcut test değişmedi.

| # | Önem | Bulgu | Sonuç |
|---|---|---|---|
| 1 | KRİTİK | `'12.10.2026`, `'15%`, `'₺100`, `'14:30`… F2+Enter'da tarihe/sayıya dönüşüyordu (`duzenleme_metni` `'` kararını `girdi_coz` ile veriyordu, `hucre_gir` `akilli_coz`) | ✅ önek kararı `akilli_coz` ile |
| 2 | KRİTİK | Yüzde biçimli sayı F2+Enter'da bozuluyordu (`1E-05%`, 12 basamağa kırpma) | ✅ ondalık (Decimal) aritmetikle yazım/çözüm, gidiş-dönüş birebir |
| 3 | KRİTİK | Doldurma 13+ basamakta yanlış (EAN-13, 1e15+1): `_temiz` `%.12g` | ✅ `.15g` + tam sayılar olduğu gibi |
| 4 | KRİTİK | \|x\| ≥ 1e26'da `decimal.InvalidOperation`, `paintEvent` her seferinde yarıda kalıyordu | ✅ `bicimle`/`sigdir` 400 basamaklı bağlamda; ızgara `ArithmeticError/ValueError`'ı Genel'e düşürür. **Kalan:** `0%` + 1,7e308 (Excel sınırı 9,99E+307 üstü) model düzeyinde hâlâ `InvalidOperation` atar, ızgarada yakalanır |
| 5 | ORTA | `1E400` → `inf` saklanıyordu | ✅ metin kalır (Excel'in davranışı doğrulanmadı) |
| 6 | KRİTİK | Kaydırılmış metin yerleşim önbelleği sınırsız (400.000 `QTextLayout` ≈ +1,8 GB; sütun sürüklerken her fare hareketinde tüm sayfa yeniden yerleşiyordu) | ✅ otomatik yükseklik yalnız tamsayı yüksekliği saklar; çizim önbelleği 4000 girdiyle sınırlı; sütun sürüklerken yeniden hesap yok, bırakınca bir kez |
| 7 | ORTA | Tam satır biçimi sütun biçimiyle kesişimi eziyordu (B kırmızı + 3. satır kalın → B3 dolgusu kayboldu) | ✅ kesişimlere açık kayıt (tam sütun dalının simetriği) |
| 8 | ORTA | Ctrl+A ile biçim, 13+ biçimli satır varken kesişimleri sessizce atlıyordu | ✅ tüm sayfada satır stilleri de güncellenir; kısmi seçimde sınır aşılırsa sessiz geçme yerine uyarı (`AdresHatasi`) |
| 12 | DÜŞÜK | `kanonige("Genel m")` `KeyError`, `"Genel a"` → `"General m"` | ✅ `BicimHatasi` |
| 13 | DÜŞÜK | `-₺-5` → +5 | ✅ çift işarette metin kalır |
| 14 | DÜŞÜK | Belge sayısı eski; `test_senaryo_bicimli.py` takipsiz | ✅ belge güncellendi, dosya commit'e girer |
| 9 | DÜŞÜK | ≥1e12 değerlerde hızlı yol/genel yol 2. ondalıkta farklı yuvarlıyor (600.000 örnekte 324 fark) | ➖ **Excel'in hangisini gösterdiği belirsiz** (§8b-46) |
| 10 | DÜŞÜK | Son satır/sütundaki biçim, ekleme ile sayfa dışına itilince siliniyor, geri al getirmiyor | ➖ açık (bilinen sınır) |
| 11 | DÜŞÜK | Muhasebe biçiminde Ondalık Artır sıfır bölümünü `"-"??.0` yapıyor | ➖ Excel davranışı belirsiz (§8b-48) |

**Temiz çıkanlar:** geri al/yinele model düzeyinde 1500 tohum × 45 işlem, **0 sapma** (stil depoları, birleşimler, ölçüler); pano gidiş-dönüşü (formül kayması, stil, birleşim, kes-yapıştır); sayı biçimi 55 bilinen Excel örneğinin hepsi; akıllı giriş sınırları; doldurma ay sonu kırpma; kural 2; testlerde yutulan hata/skip yok; 100.000 hücrede kalın uygulama 301 ms, geri al 127 ms, boyacı 200.000 hücre 389 ms.

**İncelenmeyenler:** biçim çubuğu/Hücreleri Biçimlendir arayüz ayrıntıları; dondurma, kenarlık önceliği, birleşim çiziminin piksel doğruluğu; METNEÇEVİR; gerçek yazı tipiyle zamanlama; `paintEvent` istisnasının gerçek olay döngüsünde uygulamayı kapatıp kapatmadığı (düzeltme bunu gereksiz kıldı).


---

## 13. Faz 4 — dosyalar (2026-10-09)

**Sonuç: 1993 test, hepsi geçiyor** (Faz 3 sonunda 1863 → Faz 4 ile +130).

### 13.1 Kapsam
| Alan | Katman | Durum | Test dosyası |
|---|---|---|---|
| .xlsx aç/kaydet: değer, formül (`_xlfn.`, sayfa kimliği⇄ad), hata, tarih, stil, ölçü, gizli, birleşim, dondurma, kılavuz, sekme rengi, sayfa yapısı | A | ✅ | `test_xlsx_io` (17) |
| Korunamayan öğe taraması (grafik/resim/pivot/makro/yorum/koşullu biçim/doğrulama/filtre/tanımlı ad) + uyarı + onay | A/B | ✅ | `test_xlsx_io`, `test_dosya_menusu` |
| Atomik kayıt (geçici dosya + `os.replace`), hatada eski dosya bozulmaz | A | ✅ | `test_xlsx_io`, `test_csv_io`, `test_yazdir` |
| Dosya menüsü: Yeni/Aç/Kaydet/Farklı Kaydet/Son Kullanılanlar, değişti işareti, kapatırken sorma, komut satırı | B | ✅ | `test_dosya_menusu` (17) |
| .csv: kodlama/ayraç tanıma, önizleme, metin olarak al, görünen metinle yazma | A/B | ✅ | `test_csv_io` (21), `test_csv_menu` (9) |
| Sayfa yapısı, sayfalama (Qt'siz), PDF/yazdır çizimi, Sayfa Yapısı penceresi | A/B/E | ✅ | `test_sayfalama` (19), `test_yazdir` (17) |
| Otomatik kurtarma kopyası + çökme sonrası kurtarma (gerçek süreç çökmesi dahil) | A/B | ✅ | `test_kurtarma` (15) |
| Büyük dosya: arka plan çalıştırıcı, hızlı formül yolu = yavaş yol | A/B | ✅ | `test_arka_plan` (7), `test_xlsx_io` |
| **Örnek dosyalar gidiş-dönüşü** (`testler/ornekler/`: butce.xlsx, grafikli.xlsx, satis_tr.csv, satis_utf8.csv) | B | ✅ | `test_xlsx_ornekler` (9): kayıpsız karşılaştırıcı (`kitap_farklari`), openpyxl ile çapraz okuma, grafikli dosyada uyarı + veri korunur + korunamayan öğenin çıktığı doğrulanır, özgün dosya değişmez |
| **Gerçek iş akışı** | B/E | ✅ | aç → düzenle (formül yeniden hesap) → kurtarma kopyası → kaydet → yeniden aç → PDF (yatay+dikey sayfa) → CSV |
| Görsel (yazdırma sayfası) | E | ✅ | ekran görüntüsüyle incelendi (4d) |
| Gerçek Excel'de açma / Excel'in yazdığı dosyayı açma | F | ⏳ | kullanıcı |

### 13.2 Performans (`araclar/dosya_olcum.py`, 100.000 hücre; ayrıntı `surec.md` §8)
Açılış (model + motor hesabı) 8 → **5,5 sn** (hedef < 10 ✅); .xlsx kayıt 7,4 → **3,2 sn**; CSV yaz 0,5 sn, akıllı içe aktarma 1,7 sn.

### 13.3 Açık / bilinen kusurlar
| # | Konu | Durum |
|---|---|---|
| 1 | Grafik, resim, pivot, makro, yorum/not, koşullu biçim, veri doğrulama, filtre, tanımlı ad **korunmaz** (uyarılır; ilgili özellikler Faz 5–6'da modele girince eşlenecek) | ➖ bilinçli (openpyxl sınırı) |
| 2 | Formül önbellek değeri yazılmaz (Excel yeniden hesaplar; değeri okuyan bazı araçlar boş görür) | ➖ |
| 3 | Tema renkleri varsayılan Office teması varsayımıyla RGB'ye çevrilir; yeni Excel 365 teması farklı olabilir | ⏳ gerçek dosyada doğrulanacak |
| 4 | Sütun genişliği/satır yüksekliği dönüşümü yaklaşık (±7 px) | ➖ |
| 5 | Kurtarma kopyası ana iş parçacığında (100.000 hücrede ≈ 3 sn kısa donma) | ➖ anlık görüntü gerekir |
| 6 | Yazdırma: üst/alt bilgi, sayfa numarası, el ile sayfa sonu, sütun yineleme yok | ➖ |
| 7 | CSV: yazarken ayraç/kodlama seçimi yok (`;` + BOM); sütun bazlı tür seçimi yok | ➖ |
| 8 | `.xls`, `.ods`, parolalı .xlsx açılmaz | ➖ Faz 8 |

### 13.4 Elle test bekleyenler (kullanıcı)
| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | Tabcel'in kaydettiği .xlsx'i gerçek Excel'de aç | `testler/ornekler/butce.xlsx`'i aç → kaydet → Excel'de aç: biçim, birleşim, dondurma, formüller, sayfa yapısı | ⏳ |
| 2 | Excel'in kaydettiği gerçek bir dosyayı Tabcel'de aç | Kendi bütçe dosyan; tema renkleri, sütun genişlikleri, fontlar | ⏳ |
| 3 | PDF çıktısı | Dosya ▸ PDF ▸ başka okuyucuda aç; gerçek yazıcıdan çıktı | ⏳ |
| 4 | Çökme sonrası kurtarma | Değişiklik yap, 2 dk bekle, Görev Yöneticisi'nden sonlandır, yeniden aç | ⏳ |
| 5 | Büyük dosyada açılış | 100.000 satırlık gerçek dosya; "bekleyin" penceresi | ⏳ |
| 6 | CSV'yi Türkçe Excel'de aç | Tabcel'in yazdığı `;` + BOM CSV'yi çift tıkla | ⏳ |


---

## 14. Faz 4 gözden geçirmesi (Opus 5.5) — 2026-10-09

Salt okunur Opus 5.5 alt ajanı (58 araç çağrısı, ~25 dk; openpyxl ile üretilmiş dosyalar, 30.000 rastgele formül, 12.800 rastgele hızlı-yol karşılaştırması). **Tavsiye: koşullu evet** (1–3 ve 4, 6, 8, 10 önce). Bulgular bizde yeniden üretilip düzeltildi; gerileme testleri `testler/test_opus_faz4.py` (36 test). Testler 1993 → **2028**, mevcut hiçbir test değişmedi.

| # | Önem | Bulgu | Sonuç |
|---|---|---|---|
| 1 | KRİTİK | 1904 tarih sistemli dosyada tüm tarihler 4 yıl 1 gün kayıyordu (`to_excel(v, wb.epoch)`) | ✅ takvim tarihi korunur (`to_excel(v)`); 1904 dosyada uyarı (biçimsiz sayılar 1.462 gün kayabilir) |
| 2 | KRİTİK | Kayıt `XlsxHatasi` dışı istisnayla (örn. hücrede `\x0b`: `IllegalCharacterError`) düşünce **pencere yine de kapanıyor**, veri kaybolur, kurtarma kopyası da yazılamıyor | ✅ geçersiz denetim karakterleri silinir + uyarı; 32.767 karakterden uzun metin kırpılır + uyarı; NaN/sonsuz `#SAYI!`; `_kaydet_yola` ve `otokayit_yap` her istisnayı yakalar; `closeEvent` varsayılan **ignore**, yalnız başarıda kabul; kayıt sürerken (arka plan) kapatma ertelenir |
| 3 | KRİTİK | Seyrek dosyada açılış takılıyor (`iter_rows` tüm kutu): 3 hücreli 4,9 KB dosya 24,8 sn; A1+XFD1048576 → 1,6 GB | ✅ `ws._cells` ile yalnız var olan hücreler; aynı dosya < 5 sn (test) |
| 4 | ORTA | `_xlfn.` öneki yalnız 11 işlev için geri ekleniyordu; `STDEV.S`, `_xlfn._xlws.SORT` bozuluyordu | ✅ ~150 işlevlik liste (Microsoft belgesinden; tam doğrulanmadı §8b-51), `_xlws.` desteği, `ceviri._fonksiyon_adi` `_xlws.` öneki de düşer; gidiş-dönüşte metin birebir |
| 5 | ORTA | Dizi formülleri (CSE/çok hücreli) normal formüle dönüşüyor; çok hücreli dizinin diğer hücreleri boş | ➖ **açılışta uyarı** ve kaydederken onay (`veri_kaybi`); dizi anlamıyla yazma yok (Faz 8, taşma ile) |
| 6 | ORTA | Excel Tablosu, köprü, gruplama (outline), üst/alt bilgi, sayfa koruması **uyarısız** kayboluyor | ✅ hepsi taranır, uyarılır, kaydederken onay istenir; (dosyayı biz yazınca uyarı çıkmaz — test) |
| 7 | ORTA | 1000'den geniş `<col min max>` aralığında yalnız ilk sütun alınıyor ("K:XFD gizli" → K) | ✅ tüm aralık okunur; yazarken ardışık aynı özellikli sütunlar tek `<col>` olur |
| 8 | ORTA | Ayraç tanıma: ondalık virgüllü Türkçe CSV'de `,` seçiliyordu | ✅ `;` ve `,` ikisi tutarlıysa `;`; yalnız `rakam,rakam` virgülü ayraç sayılmaz; ≥%80 tutarlılık |
| 9 | ORTA | UTF-16 ("Unicode Metin") CSV bozuk okunuyor | ✅ BOM tanınır, kodlama listesinde |
| 10 | ORTA | Kurtarılan belgede veri kaybı uyarısı kayboluyor; Farklı Kaydet özgün dosyayı öneriyor | ✅ uyarı/`veri_kaybi` kurtarma üst verisinde saklanır ve geri yüklenir; öneri "… (Kurtarılan).xlsx"; özgün (kayıplı) dosyanın üzerine yazılırsa onay sorulur |
| 11 | ORTA | Dondurma/kılavuz/sekme rengi "değişti" saymıyor, sorulmadan kapanınca kayboluyor | ✅ görünüm sürümü sayacı: `degisti_mi`, kapatma sorusu, otomatik kopya |
| 12 | ORTA | Aynı dosya iki süreçte açılabiliyor; son kaydeden diğerini siliyor | ✅ **kısmen:** kayıtta dosyanın (mtime, boyut) damgası denetlenir, başka yerde değişmişse onay sorulur; tek örnek/IPC ve `~$` kilit dosyası yok (açık) |
| 13 | ORTA | Tema indeksi 10–11 siliniyor, dosyanın kendi teması okunmuyor | ✅ `xl/theme/theme1.xml` ayrıştırılır (yoksa varsayılan Office); indeks 10–11 dahil. Excel 365'in yeni teması dosyada gelen temayla zaten doğru okunur |
| 14 | ORTA | CSV'ye Genel sayı 10 basamağa kırpılıyor (12–15 basamaklı kimlik/hesap numarası bozulur) | ✅ Genel sayı CSV'ye 15 anlamlı basamakla yazılır (Excel'in davranışı belirsiz §8b-52) |
| 15 | DÜŞÜK | Otomatik satır yükseklikleri elle sayılıyor; genişliksiz `<col>` 96 px elle genişlik oluyor | ✅ `customHeight` ham XML'den okunur; varsayılan 13 karakter elenir |
| 16 | DÜŞÜK | Hızlı formül yolu baştaki sıfırda ayrışıyor (`$A$01`) | ✅ baştaki sıfırlı başvuru/sayı hızlı yola girmez; 3.000 rastgele formülde yavaşla birebir |
| 17 | DÜŞÜK | Seri 60 (29.02.1900) okununca 59 | ➖ açık (openpyxl tarihe çevirdiği için bilgi kayıp; ham okuma gerekir) |
| 18 | DÜŞÜK | Çakışan birleşimli bozuk dosya aynen kabul; gizli sayfa onaysız görünür yapılıyor | ✅ çakışanlar atlanır + uyarı; gizli sayfa `veri_kaybi` sayılır (kaydederken onay) |
| 19 | DÜŞÜK | 32.767+ karakter, NaN/sonsuz, zengin metin | ✅ ilk ikisi (bkz. 2); zengin metin biçimi düzleşir (uyarı yok, açık) |
| 20 | DÜŞÜK | Bilinmeyen kağıt boyutu A4; "1 sayfaya sığdır" "genişliğe sığdır"a dönüşüyor; birden çok yazdırma alanından ilki | ➖ açık |
| 21 | DÜŞÜK | PID yeniden kullanımı kurtarma kopyasını gizleyebilir | ✅ süreç başlangıç zamanı (`GetProcessTimes`) saklanır/karşılaştırılır |
| 22 | DÜŞÜK | Kurtarılan belge açıkken özgün dosya açılamıyor | ✅ |
| 23 | DÜŞÜK | Arka plan işlemi sırasında WM_CLOSE | ✅ `_mesgul` bayrağı; kapatma ertelenir (gerçek WM_CLOSE doğrulanmadı, `closeEvent` doğrudan sınandı) |
| 24 | DÜŞÜK | CSV'deki `=` alanları formül oluyor | ➖ **bilerek, Excel gibi** (surec.md §4'e yazıldı); "formülleri metin al" kutusu zaten var ("Tüm alanları metin olarak al") |
| 25 | DÜŞÜK | Anlamsız test (`test_pdf_eski_dosya_bozulmaz`) | ✅ aynı yolda gerçek yazma hatası (`QPainter.begin` False) ile yeniden yazıldı; eski anlamsız test kaldırıldı |

**Temiz çıkanlar:** kural 2 ve 8 (xlsx/csv/pdf/json hepsi geçici dosya→yerine koy); hata değeri gidiş-dönüşü; `=` ile başlayan düz metin; sayfa adları; bozuk dosyalar `XlsxHatasi`; 30.000 rastgele formülde istisna yok; `_xlfn` listesi kütüphanedeki 117 işlev için eksiksiz; CSV CR/boş/tırnak/çok satırlı; yazdırma gizli sütun; arka plan model güvenliği; performans (100.000 hücre: açılış 4,2+2,4 sn, kayıt 5,1 sn).

**İncelenmeyenler:** gerçek Excel'de açma (4, 5, 13, 14 numaralıların Excel web'de doğrulanması); gerçek yazıcı/PDF okuyucuları; iki ayrı süreçle gerçek eşzamanlılık; tepe bellek; 1 milyon yoğun hücre; zip bombası (`tara` her sayfa XML'ini belleğe okur).


---

## 15. Faz 5 — veri araçları (2026-10-10)

**Sonuç: 2518 test, hepsi geçiyor** (Faz 4 sonunda 2028 → Faz 5 ile +490). Opus gözden geçirmesi (§16) henüz yapılmadı.

### 15.1 Kapsam
| Alan | Katman | Durum | Test dosyası |
|---|---|---|---|
| Ortak altyapı: `ek`/`ad` olayları, aralık yardımcıları, ek veri depoları + ekle-sil + anlık durumla geri al, Türkçe harmanlama, ağaç kaydırma | A | ✅ | `test_faz5_altyapi` (65) |
| Bul / Değiştir / Git (joker, Formüller/Değerler/Notlar, kitap kapsamı, Tümünü Değiştir tek geri al) | A/B | ✅ | `test_bul` (29), `test_bul_arayuz` (12) |
| Sırala (Türkçe harmanlama, çok düzey, renk, gizli satır, formül kayması, birleşim reddi) + formülde metin karşılaştırmasının Türkçe harmanlamaya geçişi | A/B | ✅ | `test_sirala` (28), `test_sirala_arayuz` (12) |
| Adlandırılmış aralıklar (kapsam, göreli ad, yeniden adlandırma, ekle-sil/taşı, motor bağımlılığı, .xlsx, Ad Yöneticisi/Ad Kutusu) | A/B/E | ✅ | `test_adlar` (74), `test_adlar_arayuz` (17) |
| Notlar (üçgen, fare üstü kutu, Shift+F2, ekle-sil/sırala/kes/pano taşır, Delete korur, .xlsx) | A/B/E | ✅ | `test_notlar` (26), `test_notlar_arayuz` (12) |
| Filtre (6 koşul türü, değer listesi, görünen-hücre işlemleri, .xlsx) + ALTTOPLAM 1–11/101–111 (motor `boyut` olayında yeniden hesaplar) | A/B/E | ✅ | `test_filtre` (60), `test_filtre_arayuz` (15) |
| Veri doğrulama (7 tür × 8 işleç, liste kaynakları, özel formül, 3 hata stili, açılır liste, giriş iletisi, .xlsx) | A/B/E | ✅ | `test_dogrulama` (37), `test_dogrulama_arayuz` (25) |
| Koşullu biçim (12 kural türü, öncelik + durdur, renk ölçeği, veri çubuğu, çizim + yazdırma, Kuralları Yönet, .xlsx) | A/B/E | ✅ | `test_kosullu` (41), `test_kosullu_arayuz` (26) |
| **Örnek dosya** `testler/ornekler/stok.xlsx` (openpyxl; Faz 5'in tüm öğeleri): uyarısız açılır, kaydedilip yeniden açılınca aynı, özgün dosya değişmez | B | ✅ | `test_senaryo_stok` (2) |
| **Gerçek iş senaryosu: stok listesi** — adlı fiyat tablosu + DÜŞEYARA, doğrulamalı kategori/adet, kritik stok koşullu biçim + tutar çubuğu, sırala, kategoriye süz (ALTTOPLAM görünen toplam, TOPLA hepsi), not, kaydet → yeniden aç → geri al → PDF | B/E | ✅ | `test_senaryo_stok` (5) |
| Görsel (not üçgeni/kutu, filtre düğmeleri, açılır liste oku + giriş iletisi, koşullu biçim) | E | ✅ | ekran görüntüleriyle incelendi (yazı tipi olmayan ekransız ortamda metin kutucuk görünür; yerleşim doğru) |
| Gerçek Excel'de açma (`.xlsx` ile 5 öğe) / Excel'in yazdığı dosyayı açma | F | ⏳ | kullanıcı |

### 15.2 Performans (`araclar/performans_olcum.py`, `araclar/kosullu_olcum.py`; ayrıntı `surec.md` §8)
| Ölçüm | Sonuç | Ölçüt | Durum |
|---|---|---|---|
| Filtre uygula (100.000 satır × 5) | 0,7 sn | — | ✅ |
| Açılır liste kurma (500 benzersiz değer) | ≈ 1,6 sn | — | ✅ |
| Tümünü Bul (500.000 hücre) | 4,4 sn (100.000 hücrede ≈ 0,9) | ≤ 1 sn / 100.000 hücre | ✅ |
| Sırala (100.000 satır × 5, tek anahtar) | plan 0,9 + komut 3,1 ≈ **4 sn** | ≤ 2 sn | ❌ kabul önerildi |
| Ad ekleme (50.000 formüllü kitap) | ≤ 6 sn (test eşiği) | ≤ 3 sn | ⚠ ölçülmedi/yüklü makine |
| Koşullu biçim: ilk çizim / değişince yeniden çizim (100.000 hücre, 3 kural) | ≈ 430–690 / 340–800 ms | ≤ 60 / ≤ 50 ms | ❌ kabul önerildi (istatistik gerektiren kurallar; basit kurallar etkilenmez) |
| Koşullu biçim: sıcak çizim | 23–31 ms (kural yokken 40) | ≤ 16 ms (artımlı) | ✅ |
| Izgara: kaydırma/sıçrama/Shift+Ok (Faz 3'ten ertelenen **piksel önbelleği kararı**) | sıçrama 31–36 ms, ilk çizim 24–54 ms, Shift+Ok stilli 21 ms | 16–40 ms | ❌ **önbellek yazılmadı:** 2 kare süren tek seferlik sıçramalar; filtre/koşullu biçim çizime girdi, önbelleği yazmak bunları da geçersiz kılma karmaşasına katardı. Faz 7 (.exe öncesi) tekrar ölçülür |

### 15.3 Açık / bilinen kusurlar
| # | Konu | Durum |
|---|---|---|
| 1 | Kopyalama filtreli aralıkta gizli satırları da alır (Excel yalnız görünenleri); Ctrl+D/Ctrl+Enter/biçim uygulama filtreyle gizli satırları atlamaz (yalnız Delete/Tümünü Temizle/özet atlar) | ➖ |
| 2 | Renge göre filtre dosyaya yazılamaz (uyarı; gizlilik korunur); tarih/dinamik süzgeçler okunmaz | ➖ |
| 3 | Veri doğrulama yalnız elle girişte denetlenir; formül girişi/yapıştırma/doldurma denetlenmez (Excel formül girişinde sonucu denetler) | ➖ bilerek fark |
| 4 | Koşullu biçim/doğrulama pano, doldurma, biçim boyacısı ve kes-yapıştırla taşınmaz | ➖ sonraki faz |
| 5 | Veri çubuğu Excel 2007 biçimi (negatif eksen/kenarlık yok); gradyan/düz ayrımı .xlsx'e yazılmaz | ➖ |
| 6 | Not kutusu taşıma/boyutlandırma, "Tüm Notları Göster", dizili açıklama yanıtları yok | ➖ |
| 7 | Sıralamada özel liste (ay/gün adları) ve aynı boyutlu birleşim yok | ➖ |
| 8 | Koşullu biçim menüsü başlık şeridinde (tasarım: biçim çubuğu; çubuk 1100 px'i aşıyordu) | ✅ 5j: Giriş ▸ Stiller grubuna taşındı |
| 9 | Simge kümeleri, tarih oluşumu kuralları, Excel Tablosu nesnesi yok (açılışta uyarı) | ➖ Faz 8 |

### 15.4 Elle test bekleyenler (kullanıcı)
| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | `stok.xlsx`'i Excel'de aç | `testler/ornekler/stok.xlsx`'in kopyasını Excel'de aç: filtre düğmesi + gizli satırlar, kategori doğrulama listesi, <10 adet kırmızı, tutar çubuğu, fiyat ölçeği, not üçgeni, adlı aralıklar | ⏳ |
| 2 | Tabcel'de kaydedip Excel'de aç | Tabcel'de stok listesi kur → Kaydet → Excel'de aç: kurallar öncelik sırasında, doğrulama çalışıyor, filtre koşulu görünüyor | ⏳ |
| 3 | Excel'in kaydettiği dosyayı Tabcel'de aç | Kendi dosyan: dxf renkleri (`bgColor`), doğrulama listeleri, filtre koşulları, notlar | ⏳ |
| 4 | Pencereler ve menüler | Özel Sıralama, Ad Yöneticisi, Veri Doğrulama, Kural/Kuralları Yönet pencerelerinin metin görünümü ve yerleşimi (ekransız testte yazı tipi yok) | ⏳ |
| 5 | Açılır liste oku + giriş iletisi + not kutusu | konum ve odak (Popup liste), giriş iletisinin Excel'deki konumu (sağ alt) | ⏳ |
| 6 | Filtre paneli | Popup panel odağı, alt menüler, Alt+Aşağı, büyük listede arama | ⏳ |
| 7 | Excel iletileri/adları | §8b-58, 62, 64–74: Türkçe iletiler, harmanlama ve başlık tahmini davranışları Excel web'de doğrulanacak | ⏳ |

## 16. Faz 5 / 5j — sekmeli şerit (2026-10-10)

Tasarım: `faz5j_tasarim.md`. Uygulama: `ui/serit.py` (bileşenler, saf `daralma_plani`), `ui/serit_sekmeleri.py` (Sayfa Düzeni, Formüller, Veri, Gözden Geçir, Görünüm), `ui/bicim_cubugu.py` (Giriş), `Pencere._eylemleri_kur` (eylem kataloğu), `ui/icons.py` (32 px ızgara), `theme.serit_stil`.

### 16.1 Otomatik testler
| Alan | Dosya | Vaka |
|---|---|---|
| Daralma planı (aşamalı: önce durum 1, sonra 2; öncelik; eşitse sağdaki; hiç sığmaz; boş) | `test_serit.py` | 19 (widget'lar dahil: grup durumları, açılır çerçeve içeriği taşır/geri getirir, sayfa daralınca düşük öncelikli küçülür, Dosya sekmesi menü açar seçimi değiştirmez, daraltma, `eylemler()`) |
| İkonlar (20/32 px ızgara, 1x/1,5x/2x boş değil, tasarımdaki her ad var) | `test_ikonlar.py` | 40 |
| Eylem kataloğu (tek `QAction`, eski sözlükler aynı nesneler, kısayol yok, eylemler etkin sayfada çalışır) | `test_eylem_katalogu.py` | 10 |
| Şerit pencerede (sekmeler, grup sırası, başlıkta yalnız hızlı erişim, 800/700 px taşma yok, düğmeler odak almaz, not/filtre durumu, Ctrl+F1 ve çift tık daraltma, açılır sayfa stili, tema) | `test_serit_pencere.py` | 15 |
| Diğer sekmeler (eski menü eylemleri şeritte, 800/640 px × 5 sekme taşma yok, yönlendirme/kağıt/kenar + geri al, yazdırma alanı, ölçek/sığdır, kılavuz yazdır, sayfaya özel ayar, geçersiz değer, filtre/sırala/not/dondur/%100) | `test_serit_sekmeleri.py` | 24 |

### 16.2 Ölçütler (`faz5j_tasarim.md` §9)
| Ölçüt | Sonuç | Durum |
|---|---|---|
| Eski menülerdeki her eylem şeritten erişilir | `test_eski_menulerdeki_her_eylem_seritten_erisilir` | ✅ |
| Kısayollar çalışır (QShortcut'lar korundu; Ctrl+F1 eklendi) | mevcut testler + `test_ctrl_f1_*` | ✅ |
| Mevcut testler değişmeden geçer | iki onaylı/bildirilmiş değişiklik: `test_faz5_altyapi` menü düğmesi metni → şerit denetimi (kullanıcı onayı), `test_kaydir_metin` pencere yüksekliği 600 → 800 (şerit ızgara alanını daralttı; assertion'lar aynı) | ✅ |
| 1100 px: Giriş'te hiçbir grup durum 2'ye inmez | `araclar/serit_olcum.py` (gerçek yazı tipi): Düzenleme durum 1, diğerleri tam | ✅ (pytest'te değil: ekransız Qt yazıyı kutu ölçer) |
| 800 px: sayfa dışına taşma yok (5 sekme) | pytest + `serit_olcum.py` | ✅ |
| Düğmeye tıklamak odağı ızgaradan almaz | `test_dugmeler_odagi_izgaradan_almaz` | ✅ |
| Pencere açılış süresi ≤ +100 ms | ölçülmedi | ⏳ `performans_olcum.py`'ye satır eklenecek |

### 16.3 Açık / bilinen kusurlar
| # | Konu | Durum |
|---|---|---|
| 1 | Boyut ve Kenar Boşlukları menülerinde seçili olanın ✓ işareti yok | ➖ |
| 2 | Üst/alt bilgi boşluğu, Yapıştır menüsü (Özel Yapıştır), Hızlı Erişim'e ekleme, Alt tuş ipuçları, Dosya arka sahne sayfası, şerit özelleştirme, daraltma durumunun kalıcılığı yok | ➖ Faz 7 |
| 3 | Biçim Boyacısı ve harfli ikonlar ekransız ortamda kutu görünür; ikon şekilleri ilk taslak | ⏳ elle |
| 4 | `sizeHint` gerçek ekranda 1100 px'te 1106 (kenar boşlukları + ayırıcılar) — yerleşim sığıyor, taşma yok | ➖ |

### 16.4 Elle test bekleyenler (kullanıcı)
| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | Excel ile görsel karşılaştırma | sekme/grup adları, düğme sırası, ikonların okunurluğu | ⏳ |
| 2 | Windows ölçeği %125 / %150 | ikon ve yazı keskinliği, taşma | ⏳ |
| 3 | Daraltma | Ctrl+F1, sekmeye çift tık; daraltılmışken sekme tıkında açılan sayfa; dar pencerede açılır grup düğmesi | ⏳ |
| 4 | Dosya sekmesi | menü konumu, yeşil görünüm | ⏳ |
| 5 | Sayfa Düzeni | kenar/yön/boyut/alan/ölçek değişimi PDF/önizlemede görünüyor mu; Ctrl+Z | ⏳ |

## 17. Faz 6 — grafikler ve resimler (2026-10-11)

Tasarım: `faz6_tasarim.md`. Uygulama: `model/grafik.py`, `grafik_verisi.py`, `grafik_cizim.py` (Qt'siz çizim listesi), `grafik_islem.py`, `resim_yukle.py`; `io/xlsx_grafik.py`; `ui/grid_nesneler.py`, `grid_nesne_etkilesim.py`, `grafik_boyayici.py`, `grafik_eylemleri.py`, `grafik_pencereleri.py`; yazdırma: `model/sayfalama.py` + `ui/yazdir.py`.

### 17.1 Otomatik testler (Faz 6'ya özgü yeni dosyalar)
| Alan | Dosya | Vaka |
|---|---|---|
| Çizim listesi (geometri sayısal), veri çözümleme, seri tahmini, komutlar/ekle-sil kayması | `test_grafik_*` (model, cizim, verisi, islem) | 6a–6c |
| Izgara katmanı (konum, kaydırma, yakınlaştırma, dondurma, önbellek, 30 ms erteleme) | `test_grafik_katman.py` | 19 |
| Etkileşim (seçme, taşıma, boyutlandırma, klavye, pano, menü) | `test_grafik_etkilesim.py` | 33 |
| Ekle/Grafik sekmesi, pencereler, galeri | `test_grafik_arayuz.py` + `test_grafik_islem.py` | ≈ 66 |
| Resim | `test_resim.py` | 19 |
| .xlsx gidiş-dönüş (13 galeri öğesi, model eşitliği, Excel-benzeri dosya, uyarılar, **`ornekler/grafikler.xlsx`**) | `test_xlsx_grafik.py` | 34 |
| **Yazdırma/PDF (6i)** | `test_yazdir_nesne.py` | 10 |
| **Gerçek iş senaryosu (6j)** | `test_faz6_senaryo.py` | 1 (6 adım) |

### 17.2 Tam paket (`araclar/test_parcali.py`, 2026-10-11)
| Grup | Sonuç |
|---|---|
| model (38 dosya) | 1855 geçti, 1 başarısız → `test_sirala::test_yuz_bin_satir_hizli` (zamanlama) |
| arayüz (32 dosya) | 781 geçti, 1 başarısız → `test_grafik_etkilesim::test_boyutlandirmada_onizleme_gerilir_sonra_gercek_boyut` (60 ms zamanlayıcı) |
| arayüz2 (20 dosya) | 339 geçti |
İki başarısız test **tek başına geçti** (13 sn): paket koşarken aynı anda başka ağır testler çalıştığı (7,9 GB RAM) için zamanlama aşımı; mantık hatası yok. Pakete sonradan eklenen `test_faz6_senaryo` ve `grafikler.xlsx` testi ayrı koşuda geçti. **Toplam ≈ 2977 test.** Süre ≈ 17 dk (paralel yük altında; tek başına ≈ 5,5 dk).

### 17.3 Gerçek iş senaryosu (aylık gelir-gider, `test_faz6_senaryo.py`)
12 aylık Gelir/Gider/Net (Net formül) → sütun grafiği (2 seri) + çizgi grafiği + resim → ✅ başlangıç verisi doğru · ✅ hücre değişince grafik verisi güncellenir ve önbellek yenilenir · ✅ 5. satıra satır eklenince seri aralıkları ve çapa kayar, değerler aynı · ✅ geri al her şeyi eski haline döndürür · ✅ kaydet → aç: 2 grafik + resim, uyarı yok, değerler eşit · ✅ PDF üretilir, grafik alanı yazdırma kapsamında.

### 17.4 Performans (`araclar/performans_olcum.py`, 100.000 hücre, 2026-10-11)
Nesnesiz sayfada çizim maliyeti **artmadı** (dikey sıçrama 23,9 ms [önceki 28,8], yatay 6,5, ok tuşu 10,8; stilli ilk çizim 21,6 ms). Hedefi aşan 7 kalem öncekilerle **aynı ve kabul edilmiş** (sıçrama, Shift+Ok, stilli 3 satır/sıçrama/Shift+Ok, ilk çizim). **Tek fark: durum çubuğu özeti 131 ms** (önce 82 ms; hedef 100) — ölçüm sırasında makine yüklüydü; ızgaranın kitap olayı dinlemesi eklendiği için **bir sonraki boş makinede yeniden ölçülecek** (⏳).

### 17.5 Gerçek Excel (COM, `araclar/excel_dogrula.ps1`)
6h'de: 13 tür/alt tür doğru okundu, Excel'in kendi kaydı Tabcel'e farksız döndü. **2026-10-11 kullanıcı elle doğruladı: 13 grafikli dosya Excel'de "dosya onarıldı" iletisi çıkmadan açıldı** ✅.

### 17.6 Açık / bilinen
| # | Konu | Durum |
|---|---|---|
| 1 | Karışık z sırası (resim/grafik) dosyada korunmuyor; ikincil eksen/birleşik grafik yalnız ilk grafik; başlık/eksen yazı biçimi yazılmaz | ➖ |
| 2 | Yazdırma: nesne iki sayfaya bölününce Excel çıktısıyla karşılaştırılmadı | ⏳ (COM `ExportAsFixedFormat` ile denenebilir) |
| 3 | Sayfa sınırı çizgileri / el ile sayfa sonu yok | ⏳ **T9** |
| 4 | Offscreen testte yazı tipi yok (kutu): grafik/hücre yazısı görsel doğrulaması gerçek ekranda | ⏳ elle |
| 5 | Durum çubuğu özeti 131 ms (bkz. 17.4) | ⏳ yeniden ölç |
| 6 | Opus gözden geçirmesi (Faz 6 tasarım + uygulama) | ⏳ kullanıcı onayıyla |

### 17.7 Elle test bekleyenler (kullanıcı)
| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | Grafik görünümü | `testler/ornekler/grafikler.xlsx`'in kopyasını Tabcel ve Excel'de yan yana aç: renk, başlık, gösterge, eksen | ⏳ |
| 2 | Etkileşim hissi | taşıma/boyutlandırma akıcılığı, tutamaçlar, sağ tık menüsü, Delete/Ctrl+C-V | ⏳ |
| 3 | Yazdırma | grafikli sayfayı PDF'e al, sayfa sınırında bölünen grafiği Excel çıktısıyla karşılaştır | ⏳ |
| 4 | Resim | PNG/JPEG/GIF/BMP ekle, 25 MB üstü, bozuk dosya | ⏳ |

## 18. T9 — sayfa sonları ve sayfa taşması ayarları (2026-10-11)

Tasarım: `t9_tasarim.md`. Uygulama: `model/sayfa_yapisi.py`, `model/sayfalama.py` (`_plan`, `sayfala`, `sayfa_sinirlari`), `model/sayfa.py` (`_yapiyi_kaydir`, `yazdirma_yaz`, `sayfa_sonlari`), `io/xlsx_io.py`, `ui/grid.py` (`_sayfa_sonlarini_ciz`), `ui/window.py` + `serit_sekmeleri.py` + `dosya_islemleri.py` (eylemler), `ui/sayfa_yapisi_penceresi.py`.

### 18.1 Otomatik testler
| Alan | Dosya | Vaka |
|---|---|---|
| Model: doğrulama, kesmeli bölme (satır/sütun), otomatik bölmenin kesmeden sonra sürmesi, başlık yineleme, sığdır açıkken kesmeler yok sayılır, yüksekliğe sığdır ölçeği, sayfa sırası, `sayfa_sinirlari` ≡ `sayfala`, ekle-sil kayması (kesme + yazdırma alanı + başlık satırları) ve geri al, `SayfaYapisiDegis`, .xlsx gidiş-dönüş (6 yapı), Excel kimliği (`id` = önceki satır), başka programın fit dosyası | `test_sayfa_sonlari.py` | 29 |
| Arayüz: etkin hücre kuralları (A1 kapalı, A sütunu/1. satır tek yön), Kaldır, Sıfırla, geri al/yinele, "gösterme belgeyi değiştirmez / ekleme değiştirir", piksel (el ile koyu, otomatik kesikli, dikey, kapalıyken yok), olayla kayma, kapalıyken hesap yok + açıkken önbellek, şerit eylemleri, Sayfa Yapısı penceresi, PDF dilim sayısı | `test_sayfa_sonlari_arayuz.py` | 12 |

### 18.2 Tam paket (`araclar/test_parcali.py`, tek başına koşu)
model 1886 ✅ · arayüz 782 ✅ + 1 başarısız (`test_izgara_stil::test_buyuk_secimde_ozet_ertelenir_kucukte_aninda`, **zamanlama**: tek başına 3/3 geçti) · arayüz2 351 ✅. **Toplam ≈ 3019 geçti**, 1 zamanlama testi yük altında düşüyor (önceki koşuda başka iki zamanlama testi düşmüştü: bu sınıf testler paketin ağır parçasında kararsız → ileride aralıkları genişletmek ya da `@pytest.mark.zamanlama` ile ayırmak düşünülebilir ⏳).

### 18.3 Ekran görüntüsü (gerçek yazı tipi)
1100 px: Sayfa Düzeni'nde Sayfa Yapısı (6 düğme) + Sığdır (iki kutu) + Sayfa Seçenekleri sığıyor ✅; 800 px: Sayfa Seçenekleri tek açılır düğmeye iniyor, taşma yok ✅. Izgarada çizgiler (el ile düz koyu / otomatik kesikli) doğru yerde ✅.

### 18.4 Açık / bilinen
| # | Konu | Durum |
|---|---|---|
| 1 | Sayfa Sonu Önizleme (mavi sınır sürükleme) yok | ➖ sonra |
| 2 | Kesmeler / Sayfa Sırası düğmeleri `print_titles32` ikonunu paylaşıyor | ➖ ayrı ikon |
| 3 | Sayfa sınırı çizgileri açıkken büyük sayfada (100.000 satır) yeniden hesap süresi ölçülmedi | ⏳ |
| 4 | Excel'de aynı sayfa için `ExportAsFixedFormat` ile sayfa sayısı karşılaştırması; Excel'in manuel sonu ekranda hemen gösterip göstermediği | ⏳ |
| 5 | T9 tasarım notu Sonnet'ten; Opus gözden geçirmesi | ⏳ |

### 18.5 Elle test bekleyenler (kullanıcı)
| # | Ne | Nasıl | Durum |
|---|---|---|---|
| 1 | Çizgiler | uzun tablo aç → Görünüm → Sayfa Sonlarını Göster; boyut/kenar/ölçek değişince çizgiler kayıyor mu | ⏳ |
| 2 | Sayfa sonu ekle/kaldır | hücre seç → Kesmeler → Ekle; PDF'te o satırda yeni sayfa; Ctrl+Z | ⏳ |
| 3 | Excel uyumu | sayfa sonlu dosyayı Excel'de aç/kaydet ve Tabcel'e geri aç; Sığdır (yükseklik) ve Sayfa Sırası aynı mı | ⏳ |

## 19. Excel karşılaştırma ve "elle" test turu (Claude, 2026-10-15)
Kullanıcı arayüz/menü/formül elle testlerinin Claude'da olduğunu bildirdi. Yöntem: gerçek pencerede QTest klavye/fare + ekran görüntüsü; formül/biçim/ad doğrulaması bu bilgisayardaki **Türkçe Excel 16'ya COM ile** (`araclar/excel_vaka.py`). Ayrıntı ve düzeltme listesi: `surec.md` §8b bloğu + günlük "Excel karşılaştırma turu".

| Kalem | Sonuç |
|---|---|
| §9.4-1…4 formül yazarken tıkla/sürükle başvuru, sayfa sekmesine geçip dönme, Alt+Tab, Alt+= ve tamamlama | ✅ (tamamlama listesi kesilmesi düzeltildi) |
| §11.4-2…5 doldurma tutamacı, Biçim Boyacısı, dondurma | ✅ (metni kaydır/otomatik yükseklik testlerle kapsanıyor) |
| §16.4-3…5, §15.4-4 şerit sekmeleri ve pencereler görünümü | ✅ ekran görüntüsüyle; küçük kozmetik: açılır ok yakın, Sayfa Yapısı yer tutucu kırpık |
| Qt hazır düğme metinleri | ❌→✅ "OK/Cancel" görünüyordu → `qtbase_tr` yüklendi |
| Formül sonucu biçim mirası (Excel'de var, Tabcel'de yoktu) | ❌→✅ `formul/bicim_miras.py` |
| §8b Excel doğrulamaları | ✅ 5, 6, 12, 17–19, 24–27, 30–32, 34, 36–37, 40, 46; diğerleri §8b bloğunda |
| İşlev kapsamı | ⚠️ 188 sık kullanılan Excel işlevi yok (`eksik_fonksiyonlar.md`) |
| Gerçek yazıcı, Excel/Word pano, çökme kurtarma, %125/%150 ölçek, Excel arayüz hissi | ⏳ hâlâ elle (kullanıcıyla) |
| Tam paket (5 parça) | ✅ ≈3.940 geçti (+ ≈200 yeni); tek zamanlama testi yük altında kararsız |

## 20. Faz 10f — kural motoru + kayıt formu (Claude, 2026-10-15)
- Otomatik: `test_sablon_kayitlar.py` (19: bağlam, zorunlu/benzersiz/aralık/kimlik/liste kuralları, stok satır kuralı, `ne_zaman`, tablo taraması, yapıştırılan hatalı kayıt, yazım haritası, Sağlık Kontrolü) ve `test_sablon_formu.py` (23: açılış, kurallı kaydetme, Enter gezintisi, Ctrl+Enter, tek geri al adımı, hesaplanan alan, durdur/uyar, gezinme, kirli kayıt sorusu, arama, silme, yeniden eşleme, örnek veri temizleme, canlı eşzaman).
- Elle (ekranlı pencere + ekran görüntüsü): stok hareketi formu — tarih/ürün/hareket türü/miktar alanları, takvim düğmesi, kırmızı "Bu çıkış stoğu eksiye düşürür." iletisi. **Elle kalan:** gerçek klavyede uzun kullanım hissi, çok pencere/çok kullanıcı yok.

## 21. Elle test devri — kalan maddelerin Claude tarafından yapılması (2026-10-15)
Kullanıcı "elle testleri de sen yap, kontrol sende" dedi. Yöntem: gerçek süreçler, gerçek Excel 16 / Word (COM), QtPdf ile PDF geri okuma, ekranlı pencere görüntüleri. Betikler oturum geçici klasöründeydi (araçlaştırılmadı).

| # | Madde | Sonuç |
|---|---|---|
| 1 | Çökme sonrası kurtarma (13.4-4) | ✅ gerçek süreç `taskkill /F` ile öldürüldü, 2 dk'lık otomatik kayıt kopyası vardı; yeniden `main.main()` → "Belge Kurtarma" penceresi, "Seçilenleri Aç" → 4 hücre eksiksiz geldi, bilgi çubuğu uyarısı çıktı. **Bulgu:** gerçek kurtarma klasöründe 142 yetim `.json/.tmp` artığı birikmişti → `kurtarma.artiklari_temizle` eklendi (açılışta `bekleyenler()` çağırır) |
| 2 | Excel ↔ Tabcel pano (7-3, 9.4-5) | ⚠→✅ **2 gerçek bulgu düzeltildi:** (a) Tabcel'den kopyalanan tarih Excel'e seri sayı (46310) olarak gidiyor, formül/biçim kayboluyordu → görünen metin + `x:num`/`x:fmla`/`mso-number-format` ile Excel sayı+biçim+formül+kalın/dolgu olarak alıyor; Word tablo olarak görünen metinle (15.10.2026, 1.234,50) alıyor; (b) Excel'den gelen tarih/yüzde/para metin kalıyor, kalın/dolgu/biçim kayboluyordu → akıllı çözümleme + Excel HTML CSS (`xl6x` sınıfları, `mso-number-format`) okunuyor. **Kalan fark:** Excel panoya formül koymaz (HTML'de yok) → Excel'den yapıştırılan formüller değer olur (yardım "Kopyala ve Yapıştır"da yazıldı) |
| 3 | PDF çıktısı / yazıcı (13.4-3) | ⚠→✅ PDF QtPdf ile geri okunup ölçüldü: **bulgu 1:** kenar boşluğu iki kez sayılıyordu (içerik ayarlanan boşluğun 2 katı içeriden basılıyordu; `pageRect(DevicePixel)` kaydırılmış geliyor); **bulgu 2:** grafik yazı tipleri yazıcıda ×12 büyüyordu (punto tabanlı yazı + 1200 dpi). İkisi düzeltildi, `test_yazdir_kenar.py` (6) PDF'i ölçer. **Yapılamayan:** "Microsoft Print to PDF" sürücü yolu (Windows kaydet iletişim kutusu otomasyona açılmadı) ve fiziksel yazıcı (Canon G3070: kâğıt harcamamak için denenmedi) → **kullanıcıyla**, ayrıca yerel sürücüde kenar boşluğu doğruluğu (düzeltme `printer.width()/height()` kullanıyor; Qt belgesine göre sürücüde de aynı) |
| 4 | Windows ölçeği %125 / %150 (16.4-2) | ✅ `QT_SCALE_FACTOR=1.25/1.5` ile ekranlı pencere + 3 iletişim kutusu görüntüleri: ikonlar/yazı keskin, taşma yok. **Kozmetik düzeltildi:** Sayfa Yapısı "Yazdırma alanı" yer tutucusu kırpılıyordu → "boş = hepsi" |
| 5 | Excel'de Tabcel dosyaları (13.4-1, 15.4-1/2) | ✅ 8 şablon dosyası (6 akış, 2 cevap kombinasyonu) Excel'de açıldı: onarım iletisi yok, `_tabcel` **çok gizli (2)**, 0 hatalı formül hücresi, **tüm formül sonuçları Excel'inkiyle aynı** (1.014 hücre, fark 0), doğrulama ve adlar tamam |
| 6 | Excel'de düzenlenen şablon dosyası Tabcel'de | ✅ düz Excel kaydı (7 dosya): form açık, 0 kural ihlali · sayfa yeniden adlandırma: form açık (çapa) · sütun ekleme: açık + bilgi · başlık yeniden adlandırma / sütun silme: form kapalı + Türkçe uyarı, yeniden eşleme önerisi çalışıyor (başlık → aday) · `_tabcel` bozma: sağlama uyarısı, form kapalı · `_tabcel` silme: sıradan kitap |
| 7 | CSV'yi Türkçe Excel'de aç (13.4-6) | ✅ UTF-8 BOM + `;` + tırnak + satır sonu + `Ç/İ/ı/Ş/ğ` doğru; Excel kendisi baştaki sıfırı (`007`→7) ve telefonu bilimsel sayıya çevirir (Excel davranışı); Excel'in UTF-8 CSV'si Tabcel'de okunur |
| 8 | Büyük dosyada açılış (13.4-5) | ✅ (hızlı okuyucu sonrası: 686.000 hücre ≈ 10 sn; önceki ölçüm ⚠ 47 sn) çalışıyor, "bekleyin" penceresi (Tabcel) 400 ms sonra çıkıyor, uygulama donmuyor; **800.000 hücre (100.000×8) ≈ 47 sn**, 100.000 hücre ≈ 7 sn (Excel ≈ 2 sn). Zaman %75 openpyxl ayrıştırıcısında (profil). Karar bekliyor: hızlı sayfa okuyucu (özel `iterparse`) ayrı performans işi |
| 9 | Şerit (16.4-1/3/4) | ✅ Ctrl+F1 daraltma, 900/700 px'te grup küçülmesi, Dosya menüsü; sekme adları Excel Türkçesiyle aynı (Dosya, Giriş, Ekle, Sayfa Düzeni, Formüller, Veri, Gözden Geçir, Görünüm, Yardım) |

