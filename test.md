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
| Formül motoru, yerelleştirme, tarih seri no, 15 basamak | — | ➖ | Faz 2 (test şablonu CLAUDE.md kural 11) |
| Biçimlendirme, sayı biçimleri, birleştirme, dondurma | — | ➖ | Faz 3 |
| Windows başlık çubuğu rengi (DWM) | F | ⏳ | yalnız Win11'de görünür; kullanıcı gözle doğrular |
| Gerçek kullanım (`Tabcel.bat`) | F | ⏳ | kullanıcı elle deneyecek |
| Excel uyumu (§8b listesi: 11 madde) | F | ⏳ | kullanıcı Excel web'de doğrulayacak (`surec.md`) |

---

## 3. Otomatik testler (pytest) — her testin sonucu

<!-- OTOMATIK:BASLA -->

**Son çalıştırma: 2026-10-08 — ✅ 322/322 test geçti, 0 olumsuz** (süre ≈ 3.1 sn). Bu bölüm `araclar/test_raporu.py` ile üretilir; elle düzenlemeyin.

| Dosya | Kapsam | Test | ✅ Olumlu | ❌ Olumsuz |
|---|---|---|---|---|
| `test_adres.py` | Adresleme: A1 ⇄ satır/sütun, $ mutlak, aralıklar, sınırlar (XFD, 1.048.576) | 26 | 26 | 0 |
| `test_girdi.py` | Girdi çözümleyici: yazılan metin → sayı/mantıksal/formül/metin (Türkçe yerel ayar) | 42 | 42 | 0 |
| `test_gosterim.py` | Genel sayı biçimi ve sığdırma (####, bilimsel) | 8 | 8 | 0 |
| `test_iskelet.py` | Proje iskeleti: ad/sürüm sabiti, kaynak klasörü, model/formül paketlerinin Qt'siz olması | 3 | 3 | 0 |
| `test_izgara.py` | Izgara arayüzü: çizim, gezinme, seçim, düzenleme, boyutlandırma, gizleme, pano, taşan metin, çoklu aralık, artımlı kaydırma | 108 | 108 | 0 |
| `test_olay.py` |  | 18 | 18 | 0 |
| `test_olcu.py` | Excel ölçü birimleri: karakter/punto ⇄ piksel | 3 | 3 | 0 |
| `test_pano.py` | Pano: TSV/HTML okuma-yazma, kopyalanan veri, yapıştırma planı | 25 | 25 | 0 |
| `test_pencere.py` | Ana pencere: ad kutusu, formül çubuğu, durum çubuğu, sayfa sekmeleri, yakınlaştırma | 21 | 21 | 0 |
| `test_pencere_sayfa.py` |  | 16 | 16 | 0 |
| `test_sayfa.py` | Veri modeli: seyrek sayfa, satır/sütun ekle-sil, geri al yığını, sayfa adı kuralları, gizleme, kullanılan aralık önbelleği | 33 | 33 | 0 |
| `test_sayfa_komutlari.py` |  | 7 | 7 | 0 |
| `test_toplu_ve_sonuc.py` |  | 12 | 12 | 0 |
| **Toplam** | | **322** | **322** | **0** |

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

### `testler/test_olay.py` — 18/18 ✅
**

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
**

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
**

- ✅ sayfa ekle geri al yinele ayni nesne
- ✅ sayfa sil geri al veri ve sira korunur
- ✅ sayfa yeniden adlandir ve tasi geri al
- ✅ gecersiz yeniden adlandirma yigina girmez
- ✅ karisik gecmis sayfa silme dahil tutarli geri alinir — Sayfadaki yazım → sayfa silme → ikisi de sırayla geri alınır (geçmiş silinmez).
- ✅ sayfa komutlari sayfa olaylari yayar
- ✅ silme geri al sayfa sirasi birden cok silmede

### `testler/test_toplu_ve_sonuc.py` — 12/12 ✅
**

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
