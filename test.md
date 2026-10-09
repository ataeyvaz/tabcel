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

**Son çalıştırma: 2026-10-09 — ✅ 1253/1253 test geçti, 0 olumsuz** (süre ≈ 8.8 sn). Bu bölüm `araclar/test_raporu.py` ile üretilir; elle düzenlemeyin.

| Dosya | Kapsam | Test | ✅ Olumlu | ❌ Olumsuz |
|---|---|---|---|---|
| `test_adres.py` | Adresleme: A1 ⇄ satır/sütun, $ mutlak, aralıklar, sınırlar (XFD, 1.048.576) | 26 | 26 | 0 |
| `test_degerlendir.py` | Formül değerlendirici: tür dönüşümleri, dizi yayma, hata yayılımı, 15 basamak | 46 | 46 | 0 |
| `test_dongu_arayuz.py` | Döngüsel başvuru uyarısı (6e): durum çubuğu etiketi, tek uyarı | 5 | 5 | 0 |
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
| `test_kaydir.py` | Başvuru kaydırma: kopyala, ekle-sil, taşı ($'lılar, #BAŞV!) | 33 | 33 | 0 |
| `test_motor.py` | Hesaplayıcı: bağımlılık, yeniden hesaplama, döngü, sayfa işlemleri | 20 | 20 | 0 |
| `test_olay.py` | Olay katmanı (K5): hücre/sonuç/yapı/boyut/sayfa olayları, toplu işlem tek olay | 18 | 18 | 0 |
| `test_olcu.py` | Excel ölçü birimleri: karakter/punto ⇄ piksel | 3 | 3 | 0 |
| `test_opus_faz2.py` |  | 11 | 11 | 0 |
| `test_pano.py` | Pano: TSV/HTML okuma-yazma, kopyalanan veri, yapıştırma planı | 25 | 25 | 0 |
| `test_pano_formul.py` | Pano ve formül (6c): kopyada başvuru kayması, kes-yapıştır taşıma, dış formül çevirisi | 6 | 6 | 0 |
| `test_pencere.py` | Ana pencere: ad kutusu, formül çubuğu, durum çubuğu, sayfa sekmeleri, yakınlaştırma | 21 | 21 | 0 |
| `test_pencere_sayfa.py` | Sayfa sekmeleri ve sayfa komutları arayüzde (ekle/sil/yeniden adlandır/taşı, geri al) | 16 | 16 | 0 |
| `test_sayfa.py` | Veri modeli: seyrek sayfa, satır/sütun ekle-sil, geri al yığını, sayfa adı kuralları, gizleme, kullanılan aralık önbelleği | 33 | 33 | 0 |
| `test_sayfa_komutlari.py` | Geri alınabilir sayfa komutları (K6) | 7 | 7 | 0 |
| `test_senaryo_butce.py` | Faz 2 gerçek iş senaryosu: aylık bütçe çizelgesi (iki sayfa, kopyalama, ekle-sil, geri al, döngü, taşıma) | 8 | 8 | 0 |
| `test_toplu_ve_sonuc.py` | Toplu yazım ve girdi/sonuç ayrımı (K4) | 12 | 12 | 0 |
| `test_yerellestirme.py` | TR ⇄ kanonik çeviri: ayırıcılar, fonksiyon/hata adları, sayfa başvuruları | 37 | 37 | 0 |
| **Toplam** | | **1253** | **1253** | **0** |

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

### `testler/test_dongu_arayuz.py` — 5/5 ✅
*Döngüsel başvuru uyarısı (6e): durum çubuğu etiketi, tek uyarı*

- ✅ dongu yoksa etiket gizli
- ✅ dongu olusunca etiket ve tek uyari
- ✅ dongu cozulunce etiket kalkar
- ✅ kendine basvuru ve geri al uyarmaz
- ✅ baska sayfadaki dongu adressiz etiket

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

