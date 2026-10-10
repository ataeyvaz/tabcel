# Faz 5 — Veri araçları tasarım notu (Opus 5.5, 2026-10-10)

Kapsam `plan.md` → Faz 5: sırala, filtre, bul-değiştir, adlandırılmış aralıklar, notlar, veri doğrulama, koşullu biçim. Bu not her özelliğin **verisinin nerede tutulduğunu**, olay/geri al/ekle-sil/pano/.xlsx ile ilişkisini ve Sonnet'e devredilecek işlerin sözleşmesini anlatır. Excel'den bilinçli farklar §11'de; doğrulanması gerekenler `surec.md` §8b-55…72'de.

Genel ilke (Faz 1–4 ile aynı): **veri `model/`de (Qt yok), formül değerlendiren her şey `formul/`de (Qt yok), çizim ve pencereler `ui/`de.** Her değişiklik geri alınabilir komuttur (aksi §11'de yazılı); toplu işlem TEK olay, TEK geri al adımı.

## 1. Ortak altyapı (5a)

### 1.1 Yeni olay türleri (`model/olay.py` belgesine eklenir)
- **`ek`** — sayfaya bağlı ek veriler değişti. `ayrinti`: `alan` ∈ `not | dogrulama | kosullu | filtre`, isteğe bağlı `anahtarlar` (değişen hücreler; `not` için). Motor `ek`'i yok sayar (koşullu biçim/doğrulama formülleri hücre değeri değildir); ızgara: `not` → ilgili hücreler, diğerleri → tam yeniden çizim (seyrek olaylar).
- **`ad`** — kitap düzeyi tanımlı ad değişti. `sayfa` alanı **None** (ad kitaba aittir), `ayrinti`: `eski`, `yeni` (`TanimliAd | None`). Motor: grafiği baştan kurar + tümünü hesaplar (ad değişikliği seyrek; §4.4). Mevcut dinleyiciler `tur`'a göre dallandığından None sayfa onlara ulaşmaz — Sonnet bunu `window._kitap_olayi`, `Hesaplayici._olay`, `dosya_islemleri._gorunum_olayi` için testle doğrular.
- "Değişti" işareti ayrı iş istemez: hepsi komutla geldiği için `GeriAlYigini.damga` zaten kirlenir. **İstisna:** filtre açılır listesinden yapılan işlem de komuttur (§6.3), görünüm değildir.

### 1.2 Aralık yardımcıları (`model/adres.py`)
- `aralik_kaydir(ar, eksen, nerede, fark, sinir) -> Optional[Aralik]` — `Sayfa._birlesimleri_kaydir`'daki kuralın genel hali (içine ekleme büyütür, silme küçültür, tamamen silinen None). Birleşimler de buna geçer (tek hücreye inen birleşimi kaldırma kuralı birleşimde kalır). **Ölçüt:** mevcut birleşim ekle-sil testleri değişmeden geçer.
- `aralik_cikar(a, b) -> List[Aralik]` — `a − b`, en çok 4 dikdörtgen (doğrulama/koşullu biçim aralıklarından hücre çıkarmak için).
- `bitisik_bolge(sayfa, r, c) -> Aralik` — Excel "geçerli bölge" (Ctrl+Shift+*): dolu hücrelerin 8-komşulukla bitişik dikdörtgeni, kutu büyümez hale gelene dek genişletilir. Sıralama, filtre ve Otomatik Toplam bunu kullanır. Tek dolu hücre yoksa o hücre.

### 1.3 Ekle-sil kaydırması ve anlık durum (`Sayfa`)
- `Sayfa._kaydir` yeni depoları da kaydırır: `notlar` (anahtar kaydırma, silinen bant `silinen_notlar` olarak döner), `dogrulamalar` / `kosullu` (her aralık `aralik_kaydir`; aralıksız kalan kural düşer), `filtre.aralik` (`aralik_kaydir`; başlık satırı silinirse filtre kalkar — Excel).
- **Formül içeren ek veriler** (doğrulama formülleri, koşullu biçim formülleri, tanımlı adlar) model katmanında kaydırılamaz (formül sözcükleyicisi `formul/`de). `komutlar._SatirSutun._formulleri_duzelt` genişler: `kaydir.yapi_duzeltmeleri` yanında `kaydir.ek_duzeltmeleri(kitap, sayfa, eksen, nerede, fark)` doğrulama/koşullu biçim formüllerini ve **kitaptaki tüm adların** formüllerini düzeltir.
- Geri al için tek kalıp: `Sayfa.ek_durumu()` → `(notlar kopyası, dogrulamalar, kosullu, filtre)` (hepsi değişmez nesnelerin listesi/sözlüğü → sığ kopya yeter); `ek_durumu_yukle(durum)` → TEK `ek` olayı (`alan="hepsi"`). `_SatirSutun` bunu `birlesim_durumu` gibi önce alır, geri alırken yükler; adlar `kitap.ad_durumu()`/`ad_durumu_yukle()`.
  *Gerekçe:* bu yapılar küçüktür (onlarca kural, yüzlerce not); fark çıkarmak yerine anlık görüntü hem basit hem hatasız.

### 1.4 Türkçe harmanlama (`model/harmanla.py`, Qt yok)
- `metin_anahtari(s, buyuk_kucuk=False) -> tuple` — Türkçe alfabe sırası: `a b c ç d e f g ğ h ı i j k l m n o ö p q r s ş t u ü v w x y z`. Büyük/küçük harf `tr_kucuk` ile (İ→i, I→ı). Aksanlı yabancı harfler (â î û é…) temel harfle aynı birincil ağırlık, ikincil ağırlıkta sonra. Rakamlar harflerden önce, noktalama/simgeler rakamlardan önce. Kısa çizgi ve kesme işareti **birincil düzeyde yok sayılır** (Windows "word sort"; §8b-56), eşitlikte ikincil düzeyde karşılaştırılır.
- `buyuk_kucuk=True` (sıralama seçeneği): eşit birincil anahtarda küçük harf önce (Excel; §8b-57).
- `deger_anahtari(v, artan) -> tuple` — Excel sıralama düzeni: **artan** sayı < metin < YANLIŞ < DOĞRU < hata < boş; **azalan** hata, mantıksal, metin, sayı, **boş yine en sonda**. Hatalar kendi aralarında eşit (kararlı sıralama sırayı korur). Sayı karşılaştırması `onbes_basamak` mantığıyla (model içinde kopyalanır; `formul/` içe aktarılmaz).
- **Regresyon notu (kural 12):** `formul/donustur.karsilastir` ve `ortak.kriter` metni şu an kod noktası sırasıyla karşılaştırıyor (`"ç" > "z"`). Türkçe Excel'de `="ç"<"d"` DOĞRU olmalı (§8b-55). 5c'de `karsilastir` da `metin_anahtari`'nı kullanır; **bir mevcut test değişirse Sonnet devam etmeden kullanıcıya bildirir.** `EĞERSAY(A:A;"<m")` gibi ölçütler de aynı yoldan düzelir.

### 1.5 Ağaç kaydırma (`formul/agac.py`)
Koşullu biçim, doğrulama ve göreli tanımlı ad formülleri **bir çapa hücreye göre** yazılır ve başka hücrede **göreli kısımları kaydırılarak** değerlendirilir. Her hücre için metin kaydırıp yeniden ayrıştırmak (`kaydir.kopyala` + `formul_ayristir`) pahalı olduğundan:
- `agac_kaydir(agac, dr, dc) -> Dugum` — `Ref` düğümlerinde `$`'sız uçları kaydırır (sayfa dışına çıkan → `Sabit(#BAŞV!)`), diğer düğümleri paylaşır. Sonuç `(id(agac), dr, dc)` anahtarlı LRU önbellekte (4096).
- **Ölçüt:** 1.000 farklı (dr, dc) için `agac_kaydir` + değerlendirme ≤ 10 ms (basit `=A1>5` kuralı); `kaydir.kopyala` + ayrıştırmayla sonuç eşitliği 200 rastgele formülde.

### 1.6 Menüler
Başlık şeridine (Dosya, Görünüm yanına) **Düzen** (Bul… Ctrl+F, Değiştir… Ctrl+H, Git… F5/Ctrl+G) ve **Veri** (Artan Sırala, Azalan Sırala, Özel Sıralama…, Filtre Ctrl+Shift+L, Filtreyi Temizle, Yeniden Uygula Ctrl+Alt+L, Veri Doğrulama…, Ad Tanımla…, Ad Yöneticisi Ctrl+F3) menüleri; biçim çubuğuna **Koşullu Biçimlendirme** menü düğmesi (§9.5). Hücre sağ tık menüsüne Sırala ▸, Filtre ▸, Not Ekle/Düzenle/Sil, Ad Tanımla.

## 2. Bul ve Değiştir (5b)

### 2.1 Model (`model/bul.py`, Qt yok — çevirici/biçimleyici dışarıdan verilir)
- `BulSecenek(metin, buyuk_kucuk=False, tam_hucre=False, bakilan="formul"|"deger"|"not", kapsam="sayfa"|"kitap", yon="satir"|"sutun")`.
- `eslesmeler(kitap, sayfa, secim, secenek, metin_al) -> Iterator[(Sayfa, r, c)]` — `metin_al(sayfa, r, c, bakilan) -> str|None` arayüzden verilir:
  - `formul`: hücrenin **düzenleme metni** (formül Türkçe: `=TOPLA(A1;2,5)`; sabit `duzenleme_metni` ile — tarih `gg.aa.yyyy`). Excel "Formüller"de arar.
  - `deger`: **görünen metin** (sayı biçimi uygulanmış, `####` değil tam metin).
  - `not`: not metni.
- Eşleşme: Türkçe büyük/küçük harf duyarsız (`tr_kucuk`), `*` `?` joker, `~` kaçış (`ortak.metin_deseni`'nin alt dize hali — yeni `joker_alt_dize(desen)` `formul/fonksiyonlar/ortak.py` yanına değil **`model/bul.py`'ye** yazılır; ortak.py'deki ile aynı kurallar, testle eşitlenir). `tam_hucre` → tüm metin eşleşmeli.
- Sıra: etkin hücreden **sonraki** hücreden başlar, satır (ya da sütun) sırasıyla sarar; seçim tek hücreden büyükse yalnız seçimde arar (Excel), çoklu seçimde tüm parçalar. Birleşimin kapsanan hücreleri atlanır. Yalnız dolu hücreler gezilir (`dolu_hucreler(sirali=True)` + not anahtarları) → 100.000 hücrede "Tümünü Bul" ≤ 1 sn ölçütü.
- **Değiştir:** yalnız `bakilan="formul"`da (Excel). Yeni metin düzenleme metninde değiştirilir ve **elle yazılmış gibi** çözülür (`ceviri.hucre_girdisi` / `girdi.akilli_coz`; Genel hücreye önerilen sayı biçimi — 3g kuralı). Formül bozulursa o hücre atlanır, sonuçta "N hücre değiştirildi, M hücrede formül geçersiz olacağı için değiştirilmedi" denir (Excel ilk hatada durur — bilerek fark §11). "Tümünü Değiştir" = tek `Grup(HucrelerDegis, BicimDegis)` (sayfa başına), tek geri al adımı.
- Sayfa koruması yok (Faz 8) → her hücre yazılabilir.

### 2.2 Arayüz (`ui/bul_penceresi.py`)
Kipsiz (modeless) pencere, sekmeler **Bul / Değiştir**; "Seçenekler >>" ile: İçinde (Sayfa/Çalışma Kitabı), Ara (Satırlarda/Sütunlarda), Bakılacak yer (Formüller/Değerler/Notlar), Büyük/küçük harf eşleştir, Hücre içeriğinin tamamını eşleştir. Düğmeler: Tümünü Bul, Sonrakini Bul (Shift: önceki), Değiştir, Tümünü Değiştir, Kapat. "Tümünü Bul" listesi: Kitap, Sayfa, Hücre, Değer, Formül; satıra tıklamak hücreye gider (sayfa değiştirir). Bulunamazsa "Aradığınız bulunamadı." (Excel'in tam Türkçe iletisi §8b-58). Shift+F4 = sonrakini bul (pencere kapalıyken de).
**Git (F5):** adres, aralık ya da tanımlı ad (5d'den sonra) yazılır; liste tanımlı adları gösterir. Ad kutusunun mevcut `_ad_kutusundan_git` yolu paylaşılır.

## 3. Sırala (5c)

### 3.1 Model (`model/sirala.py`, Qt yok)
- `SiralamaAnahtari(sutun, artan=True, olcut="deger"|"dolgu"|"yazi_rengi", renk=None)` — `sutun` mutlak sütun (satır sıralamasında satır).
- `siralama_plani(sayfa, aralik, anahtarlar, baslik=False, buyuk_kucuk=False, yon="satir") -> List[int]` — veri satırlarının yeni sırası (permütasyon). **Kararlı** (Python `sorted`; çok düzey = tek bileşik anahtar). Değer `sayfa.deger` (formül sonucu). Renk ölçütü: seçilen renk önce, diğerleri özgün sırada (Excel "Hücre Rengine Göre — Üstte").
- **Gizli satırlar:** sıralama yalnız **görünen** satırları yer değiştirir, gizli satırlar yerinde kalır (Excel filtreli listede böyle; elle gizlenen için §8b-59). Uygulama: görünen satır indeksleri listesi → permütasyon bu listeye uygulanır.
- **Birleşim:** aralık içinde birleşim varsa reddedilir: "Bunu yapmak için tüm birleştirilmiş hücrelerin aynı boyutta olması gerekir." (Excel iletisi; aynı boyutlu birleşimlerin sıralanması yok — §11).
- **Başlık tahmini** `baslik_tahmin(sayfa, aralik) -> bool`: ilk satır tümüyle metin/boş değil-metin karışımı değilken ve en az bir sütunda ilk satır metin, altı metin değilse; ya da ilk satırın stili (kalın/dolgu) altındakilerden farklıysa → başlık var (Excel sezgisi yaklaşık; §8b-60).

### 3.2 Komut `Sirala(sayfa, aralik, permutasyon, yon)` (`model/komutlar.py`)
- Hücreler: satır `i` → `j`; **formül `kaydir.kopyala(f, j−i, 0)` ile kayar** (Excel sıralamayı kopyala gibi uygular: `=B2*C2` 5. satıra gidince `=B5*C5`; dışarıdan bu hücrelere işaret eden başvurular **değişmez**, Excel'de de değişmez — §8b-61).
- Taşınanlar: girdi, hücre stili (ham `_stil`), not. Taşınmayanlar (Excel gibi): satır yüksekliği, satır stili, doğrulama ve koşullu biçim aralıkları (konuma bağlıdır), birleşimler (yukarıda reddedildi).
- Uygulama: `Grup(HucrelerDegis, BicimDegis, NotlarDegis)` planı tek seferde kurulur (sayfa başına tek olay); geri al tek adım. `ana_sayfa` tanır.
- **Ölçüt:** 100.000 satır × 5 sütun, tek anahtar sıralama ≤ 2 sn (anahtar hesabı + plan + yazım); Türkçe harf sırası, karışık tür, boş en sonda, azalan, kararlılık, çok düzey, renk, gizli satır, birleşim reddi, formül kayması, geri al — her biri test.

### 3.3 Arayüz
- **Artan/Azalan (A→Z, Z→A)** düğmeleri: seçim tek hücreyse `bitisik_bolge`, başlık `baslik_tahmin`; anahtar etkin hücrenin sütunu. Seçim çok hücreli ve bitişik veri seçimin dışına taşıyorsa Excel'in **"Sıralama Uyarısı"** sorulur: "Seçimi genişlet" (varsayılan) / "Geçerli seçimle devam et".
- **Özel Sıralama…** (`ui/sirala_penceresi.py`): düzey tablosu (Sıralama ölçütü sütun adı — başlık varsa başlık metni, yoksa "Sütun A"; Sıralama koşulu Hücre Değerleri / Hücre Rengi / Yazı Tipi Rengi; Düzen A'dan Z'ye / Z'den A'ya — sayı sütununda "Küçükten Büyüğe"), Düzey Ekle/Sil/Kopyala, yukarı/aşağı, "Verilerim üst bilgi içeriyor", Seçenekler: büyük/küçük harf duyarlı, yukarıdan aşağı / soldan sağa. En çok 64 düzey (Excel).
- Özel listeye göre sıralama (Ocak, Şubat… / Pzt, Sal…) — **5c kapsamında değil**, §11.

## 4. Adlandırılmış aralıklar (5d)

### 4.1 Model
- `TanimliAd(ad, formul, kapsam: Optional[int] = None, aciklama="", gizli=False)` — değişmez. `formul` **saklanan biçimde** (`=[1]!$A$1:$B$10`, kanonik İngilizce, başka sayfa kimlikle), sabit (`=0.18`) ya da herhangi bir formül (`=OFFSET(...)`) olabilir. Göreli başvurular **A1'e göre** saklanır (.xlsx `definedName` gibi); kullanıldığı hücreye göre `agac_kaydir(r−1, c−1)` ile değerlendirilir.
- `CalismaKitabi.adlar: Dict[Tuple[Optional[int], str], TanimliAd]` anahtar `(kapsam, tr_kucuk(ad))`. `ad_bul(ad, sayfa_kimligi)` → önce sayfa kapsamı, sonra kitap. Kapsamı silinmiş sayfa olan ad görünmez/kullanılmaz ama **silinmez** (sayfa silme geri alınınca kendiliğinden döner — K6 kimlik düzeninin aynısı).
- `ad_dogrula(ad)` (Excel kuralları): ilk karakter harf, `_` ya da `\`; sonrakiler harf, rakam, `.`, `_`; boşluk yok; hücre başvurusuna benzemez (`A1`, `XFD1048576`, `R1C1`, `R`, `C`, `r`, `c`); en çok 255 karakter; `DOĞRU`/`YANLIŞ`/`TRUE`/`FALSE` olamaz; kapsamında büyük/küçük harf duyarsız benzersiz. Türkçe harfler serbest. İletiler Excel'deki anlamla Türkçe ("Girdiğiniz ad geçerli değil." — §8b-62).
- Komut `AdDegis(kitap, eski, yeni)` → `ad` olayı. **Yeniden adlandırma** kitaptaki tüm formüllerdeki (hücre + doğrulama + koşullu biçim + diğer adlar) `AD` sözcüklerini yeni adla yazar — `kaydir._donustur` benzeri sözcük düzeyi `adi_degistir(formul, eski, yeni)`; tek geri al adımı (`Grup`). **Silme**: formüller metni korur, `#AD?` hesaplanır (Excel).

### 4.2 Formül tarafı
- Sözcükleyici `AD` sözcüğü ve ağaç `Ad` düğümü hazır. `degerlendir`: `Ad` → `Baglam.ad_coz(ad)` → adın ağacı (motorun ağaç önbelleğinden) `agac_kaydir` ile hücreye göre kaydırılıp değerlendirilir; bulunamazsa `#AD?`. Özyineleme koruması: değerlendirme yığınında aynı ad varsa `#AD?` (Excel döngüsel adı da hata verir; derinlik 64).
- `ceviri`: ad metni dilden bağımsızdır, olduğu gibi geçer; .xlsx ⇄ saklanan biçimde adın formülü de sayfa adı ⇄ kimlik çevrilir.
- Otomatik tamamlama (6d) listesine adlar eklenir (fonksiyonlardan sonra, farklı simge). Renkli başvuru vurgusu adları vurgulamaz (Excel de).

### 4.3 Ekle-sil, taşı, kopyala
- Satır/sütun ekle-sil: adların formülleri `kaydir.yapi` ile düzelir (§1.3), tek geri al adımı.
- Kes-yapıştır (`HucreTasi`): taşınan bölgeye tamamen işaret eden ad başvuruları kayar (Excel) — `kaydir.tasi` adlara da uygulanır.
- Kopyala-yapıştır adları etkilemez.

### 4.4 Motor
- `_oncul_topla` `Ad` düğümünde adın ağacını (kaydırılmış) özyinelemeli tarar → hücre/aralık öncülleri normal kaydedilir. Bulunamayan ad öncül vermez.
- `ad` olayı → `tumunu_hesapla()` (ad tanımı seyrek; basit ve doğru). Ölçüt: 50.000 formüllük kitapta ad ekleme ≤ 3 sn (Faz 4 açılış hesabı ölçeğinde); aşarsa yalnız o adı (adla `AD` sözcüğü taşıyan formülleri) kirletmeye daraltılır.

### 4.5 Arayüz
- **Ad kutusu:** adres değil geçerli bir ad yazılırsa: ad varsa aralığına gider (seçer, sayfa değiştirir); yoksa **seçimi bu adla tanımlar** (kitap kapsamı, Excel). Açılır liste adları gösterir. Seçim tam olarak bir adın aralığıysa ad kutusu adı gösterir (Excel).
- **Ad Tanımla…** (`ui/ad_penceresi.py`): Ad, Kapsam (Çalışma Kitabı / sayfalar), Açıklama, Başvurur (Türkçe formül metni; K7 işaretleme modu bu alanda **yok** — §11).
- **Ad Yöneticisi** (Ctrl+F3): liste (Ad, Değer, Başvurur, Kapsam, Açıklama), Yeni/Düzenle/Sil, süzgeç yok. Gizli adlar gösterilmez.

## 5. Notlar (5e)

- **Model:** `Not(metin, yazar="")` değişmez; `Sayfa.notlar: Dict[Anahtar, Not]`. `notlari_yaz({anahtar: Not|None}) -> eskiler` → TEK `ek` olayı (`alan="not"`, `anahtarlar`). Komut `NotlarDegis(sayfa, yeni)`.
- Excel'de "Not" (eski "Açıklama") — biz yalnız **not** destekleriz; dizili açıklamalar (threaded comments) açılışta uyarı olarak kalır (openpyxl onların düz kopyasını not olarak okur: `[Threaded comment]` ön ekli metni not olarak alıp uyarıyı korur).
- **Hareket eder:** satır/sütun ekle-sil (§1.3), sıralama, kes-yapıştır (`HucreTasi` notu taşır), kopyala-yapıştır "Tümü" (`PanoVerisi.notlar {(dr,dc): Not}`; kendi biçimimizde; dışarıya gitmez), Temizle ▸ Tümü ve yeni **Temizle ▸ Notlar**. **Delete notu silmez** (Excel: yalnız içerik). Doldurma notu taşımaz (§8b-63).
- **Izgara:** notlu hücrenin sağ üst köşesinde kırmızı üçgen (Excel ~6 px, `#C00000`); fare üzerinde ~400 ms bekleyince açık sarı kutu (`#FFFFE1`, ince siyah çerçeve, yazar adı kalın ilk satır) hücrenin sağ üstünden ok çizgisiyle. Shift+F2 notu düzenle/ekle (kutu düzenlenebilir hale gelir, dışına tıklayınca kaydeder). Yazar varsayılanı Windows kullanıcı adı (`os.getlogin`), ayar yok.
- "Tüm Notları Göster" ve kutuyu taşıma/boyutlandırma **yok** (§11).
- **.xlsx:** openpyxl `Comment(text, author)` okuma/yazma; kutu boyutu varsayılan.

## 6. Filtre (5f)

### 6.1 Model (`model/filtre.py`, Qt yok)
- `Filtre(aralik, kosullar: Dict[int, Kosul])` — `aralik` başlık satırı dahil; anahtar mutlak sütun. Sayfa başına **bir** otomatik filtre (Excel).
- Koşul türleri (değişmez):
  - `DegerKosulu(metinler: frozenset, bos: bool)` — **görünen metne** göre (Excel değer listesi biçimlenmiş metni kullanır; büyük/küçük harf duyarsız `tr_kucuk`). Tarihlerin yıl/ay/gün ağacı **yok**, düz liste (§11).
  - `OzelKosul(k1, k2=None, ve=True)`; her `k` = `(islec, deger)`; işleçler `esit, esit_degil, buyuk, buyuk_esit, kucuk, kucuk_esit, baslar, biter, icerir, icermez`. Metin işleçleri joker destekler. Sayı karşılaştırması sayı hücrelerinde, metin karşılaştırması `metin_anahtari` ile.
  - `IlkKosul(n, alt=False, yuzde=False)` — İlk 10 / Son 10 / İlk %10.
  - `OrtalamaKosulu(ustu=True)`.
  - `RenkKosulu(tur="dolgu"|"yazi", renk)`.
- `gizlenecekler(sayfa, filtre, metin_al) -> Set[int]` — veri satırlarından (başlık hariç) **en az bir** koşulu sağlamayanlar. İlk/ortalama koşulları sütunun **tüm** veri satırlarına göre (diğer filtrelerden bağımsız — §8b-64).
- **Gizleme tek bittir** (Excel'deki gibi): filtre `gizli_satir`'a yazar. "Filtreyle gizli" = etkin filtrenin veri aralığında olup gizli olan satır (Excel de ayrım tutmaz; filtre yeniden uygulanınca aralıktaki tüm satırların gizliliği baştan hesaplanır, elle gizlenmiş satır da açılabilir). Böylece ızgara, gezinme, yazdırma, pano değişmeden çalışır.
  *Gerekçe:* ayrı bir "filtre gizli" kümesi her `gizli_satir` kullanımını (ızgara 9 yer, xlsx, sayfalama) iki kümeye bakar hale getirirdi; Excel'in dosya modeli (`row hidden=1`) de tek bittir.
- **Aralık genişlemesi:** filtre açılırken `bitisik_bolge`; açılır liste açılırken ve "Yeniden Uygula"da aralık başlığın altındaki bitişik dolu satırlara kadar **genişler** (Excel filtre aralığını kendiliğinden uzatır). Veri değişince filtre **kendiliğinden yeniden uygulanmaz** (Excel; Ctrl+Alt+L).

### 6.2 Komut `FiltreDegis(sayfa, yeni_filtre | None)`
Eski filtreyi ve aralıktaki satırların gizlilik durumunu saklar; yeni gizli kümeyi uygular (filtre kaldırılınca aralıktaki tüm satırlar görünür). Olay: `boyut` + `ek(alan="filtre")`. **Geri alınabilir** (Excel'de filtre uygulamak geri alınabilir — §8b-65). `ana_sayfa` tanır.

### 6.3 Filtreli aralıkta işlemler (Excel)
- Kopyala yalnız **görünen** satırları alır (filtre etkinken; elle gizlenen satırlar Excel'de de kopyalanır — biz "filtre aralığında gizli = filtreli" kuralıyla filtre aralığında atlarız).
- Delete / Temizle / biçim uygulama / Ctrl+D / Ctrl+Enter yalnız görünen hücrelere.
- Yapıştırma ve doldurma tutamacı gizli satırları **atlamaz** (Excel'in de bilinen davranışı) — değişiklik yok.
- Sıralama yalnız görünen satırları yer değiştirir (§3.1).

### 6.4 ALTTOPLAM (SUBTOTAL)
- `formul/fonksiyonlar/istatistik.py`'ye `SUBTOTAL(islev_no, başv1, …)`: 1–11 (ORTALAMA, BAĞ_DEĞ_SAY, BAĞ_DEĞ_DOLU_SAY, MAK, MİN, ÇARPIM, STDSAPMA, STDSAPMAS, TOPLA, VAR, VARS) ve 101–111. **Filtreyle gizli satırlar her iki grupta da dışlanır**; 101–111 ayrıca elle gizlenen satırları dışlar (bizde: filtre aralığı dışındaki gizli satırlar); aralıktaki başka ALTTOPLAM hücreleri sayılmaz. Türkçe ad `ALTTOPLAM` **tr-tr belgesinden doğrulanacak** (kural 4). TOPLAMA (AGGREGATE) Faz 8.
- Motor: ALTTOPLAM gizliliğe bağlı. Fonksiyon kaydına `gizlilik=True` niteliği; motor bu hücreleri ayrı kümede tutar ve **`boyut` olayında** yeniden hesaplar (değişken sayılmaz; her düzenlemede değil yalnız gizleme/gösterme/filtrede).
- Durum çubuğu özeti filtre etkinken gizli satırları saymaz (Excel; §8b-66). Excel'in durum çubuğu iletisi "N kayıttan M kayıt bulundu" filtre uygulanınca kısa süre gösterilir.

### 6.5 Arayüz
- Ctrl+Shift+L / Veri ▸ Filtre aç-kapa. Başlık hücrelerinin sağında açılır düğme (16×16 px, yakınlaştırmayla ölçeklenir; koşullu sütunda huni simgesi). Filtreli satır numaraları **mavi** (`#0563C1`, Excel). Düğme alanına tıklama hücre seçimini değiştirmez; Alt+Aşağı başlık hücresindeyken listeyi açar.
- Açılır panel (`ui/filtre_paneli.py`, `QFrame` açılır pencere): A'dan Z'ye Sırala, Z'den A'ya Sırala, Renge Göre Sırala ▸ · "<Sütun>" Filtresini Temizle · Renge Göre Filtrele ▸ · Metin/Sayı Filtreleri ▸ (sütun türüne göre; Eşittir…, Eşit Değildir…, İle Başlar…, İle Biter…, İçerir…, İçermez…, Büyüktür…, Küçüktür…, Arasında…, İlk 10…, Ortalamanın Üstünde/Altında, Özel Filtre…) · Ara kutusu · liste: "(Tümünü Seç)", değerler `metin_anahtari` sırasıyla, "(Boş)" en sonda — **diğer sütunların filtrelerine göre görünen satırların** değerleri (Excel). Liste üst sınırı 10.000 benzersiz değer (Excel). Tamam/İptal.
- Özel Filtre penceresi: iki satır (işleç + değer açılır kutusu), Ve/Veya; `?` ve `*` ipucu metni.

## 7. Veri doğrulama (5g)

### 7.1 Model (`model/dogrulama.py`, Qt yok)
- `Dogrulama(araliklar: Tuple[Aralik,...], tur, islec="arasinda", formul1=None, formul2=None, bos_yoksay=True, acilir_liste=True, giris=(goster, baslik, ileti), hata=(goster, stil, baslik, ileti))` — değişmez.
  - `tur` ∈ `her_deger, tam_sayi, ondalik, liste, tarih, saat, metin_uzunlugu, ozel`; `islec` ∈ `arasinda, arasinda_degil, esit, esit_degil, buyuk, kucuk, buyuk_esit, kucuk_esit`; `stil` ∈ `durdur, uyari, bilgi`.
  - `formul1/2` saklanan biçimde: formül (`=$A$1:$A$5`, `=[2]!$A:$A`, `=A1>0`), sayı/tarih sabiti (`=10`), **liste sabiti** `"Evet,Hayır"` (.xlsx gibi virgüllü, tırnaklı). Göreli başvurular aralığın **ilk aralığının sol üst** hücresine göre (Excel/.xlsx).
- `Sayfa.dogrulamalar: List[Dogrulama]`; her hücrede **en çok bir** doğrulama: `dogrulama_yaz(araliklar, dv | None)` önce bu hücreleri diğer kuralların aralıklarından `aralik_cikar` ile düşürür (Excel yeni doğrulamayla eskisinin yerini alır). `dogrulama(r, c)` → kural (aralık sayısı küçük; doğrusal tarama, gerekirse satır indeksi).
- Komut `DogrulamaDegis(sayfa, yeni_liste)` (önce/sonra tüm liste — küçük).

### 7.2 Denetim (`formul/kosul.py`, Qt yok)
- `dogrula(sayfa, r, c, deger, kitap) -> bool` — formüller `agac_kaydir` ile hücreye göre; liste: sabit liste ya da aralığın değerleri (görünen metinle değil **değerle** karşılaştırılır, metin büyük/küçük harf duyarsız; §8b-67); `ozel`: formül sonucu DOĞRU ya da sıfır olmayan sayı → geçerli; hata → geçersiz. `bos_yoksay` ve boş girdi → geçerli. Tarih/saat seri sayıyla.
- **Yalnız elle girişte denetlenir** (`Izgara.hucre_gir`, Ctrl+Enter, açılır listeden seçim). Yapıştırma, doldurma, formül sonucu, Değiştir **denetlenmez** (Excel). §11.

### 7.3 Arayüz
- Veri ▸ Veri Doğrulama… (`ui/dogrulama_penceresi.py`), sekmeler **Ayarlar** (İzin Verilen, Veri, En Az/En Çok/Değer/Kaynak, Boşluğu yoksay, Hücre içi açılır liste), **Giriş İletisi**, **Hata Uyarısı**; Tümünü Temizle. Seçimde birden fazla farklı kural varsa Excel'in "Seçim, veri doğrulama ayarları olmayan hücreler içeriyor…" sorusu (§8b-68). Kaynak alanı Türkçe yazım: liste ayırıcı **`;`** (Türkçe Excel; `Evet;Hayır` → saklanan `"Evet,Hayır"`, §8b-69), formül `=$A$1:$A$5` / `=Sayfa2!$A:$A` (K7 işaretleme yok, §11).
- Geçersiz girişte: `durdur` → "Bu değer, bu hücre için tanımlanan veri doğrulama kısıtlamalarıyla eşleşmiyor." Yeniden Dene / İptal (Yeniden Dene düzenlemeyi açık bırakır, İptal girişi bırakır); `uyari` → "Devam etmek istiyor musunuz?" Evet / Hayır / İptal; `bilgi` → Tamam / İptal. Kullanıcı başlık/ileti verdiyse o metin. (Excel iletilerinin Türkçe yazımı §8b-70.)
- **Açılır liste:** etkin hücre liste doğrulamalıysa hücrenin **sağ kenarının dışında** ok düğmesi (Excel); tık ya da Alt+Aşağı → liste (en çok 8 satır görünür, kaydırılabilir); seçim `hucre_gir` yolundan yazılır. Liste aralığı boş hücre içeriyorsa boş satır gösterilir (Excel).
- **Giriş iletisi:** hücre seçilince hücrenin sağ altında sarı ipucu kutusu (başlık kalın), hücreden ayrılınca kaybolur.
- "Geçersiz Verileri Daire İçine Al" **yok** (§11).

## 8. Koşullu biçim çizimi ve değerlendirme (5h)

### 8.1 Model (`model/kosullu.py`, Qt yok)
- `KosulluKural(araliklar, tur, bicim: StilYama | None, dur=False, ...)` — değişmez; liste sırası = öncelik (0 en yüksek). Türler ve parametreleri:
  - `hucre_degeri(islec, formul1, formul2)` — işleçler doğrulamadakiyle aynı.
  - `metin(islec ∈ icerir|icermez|baslar|biter, metin)`.
  - `bos`, `bos_degil`, `hata`, `hata_degil`.
  - `yinelenen(benzersiz=False)` — sayı/metin değerine göre, metin büyük/küçük harf **duyarsız** (§8b-71).
  - `ilk_son(n, alt=False, yuzde=False)`, `ortalama(ustu=True, esit=False, std=0)`.
  - `formul(formul)` — DOĞRU/sıfır olmayan sayı → uygulanır.
  - `renk_olcegi(noktalar)` — 2 ya da 3 nokta; nokta = `(tur ∈ min|max|sayi|yuzde|yuzdebirlik|formul, deger, renk)`.
  - `veri_cubugu(renk, min_nokta, max_nokta, yalniz_cubuk=False, gradyan=True)`.
  - Yapılmayanlar: simge kümeleri, tarih oluşumu ("Dün/Bu hafta…"), Excel 2010 veri çubuğu uzantıları (negatif eksen, kenarlık) → §11; açılışta uyarı.
- `bicim` yalnız bu alanları taşır (Excel `dxf`): yazı rengi, kalın, italik, altı çizili, üstü çizili, dolgu, kenarlık, sayı biçimi. **Yazı tipi/boyutu değiştirmez** (Excel de izin vermez).
- `Sayfa.kosullu: List[KosulluKural]`; komut `KosulluDegis(sayfa, yeni_liste)`.

### 8.2 Değerlendirme (`formul/kosul.py`)
- `KosulluHesap(sayfa, kitap)`: `hucre(r, c) -> (yama: StilYama | None, cubuk: (oran 0–1, renk, yalniz_cubuk) | None)`.
  - Önce kuralların **sınır kutuları**; hücre hiçbirine düşmüyorsa hemen `(None, None)`.
  - Aralık istatistikleri (ilk/son eşiği, ortalama, std, yinelenen sayaçları, ölçek min/max/yüzdebirlik) kural başına **tembel** ve önbellekli.
  - Öncelik sırasıyla uygulanır; aynı özelliği daha yüksek öncelikli kural belirler (yamalar alttan üste birleştirilir); `dur=True` uygulanırsa sonrakiler atlanır (Excel `stopIfTrue`). Renk ölçeği `StilYama(dolgu=ara renk)` üretir (doğrusal RGB ara değer).
  - Hücre sonucu `(r, c)` anahtarlı önbellekte.
- **Geçersiz kılma:** kitapta herhangi bir `hucre`, `sonuc`, `yapi`, `ek(kosullu)` ya da `sayfa` olayında **tüm** önbellek boşaltılır (basit/doğru; kural formülleri başka sayfaya bakabilir). Ölçüm kötü çıkarsa (aşağıda) daraltılır.

### 8.3 Izgara
- `_yerlesim` stil kimliğini hesapladıktan sonra: `sayfa.kosullu` boş değilse `yama` → `havuz.yama_uygula(k, yama)` (havuzun `(kimlik, yama)` önbelleği var) ile yeni kimlik; sayı biçimi ve renk de buradan gelir. **Kural yoksa ek maliyet tek boolean denetimi** (3c/3f ile aynı ilke).
- Veri çubukları `_cubuklar` listesine eklenir; çizim sırası: dolgu → **veri çubuğu** (hücre içinde 2 px iç boşlukla, gradyan soldan sağa açılır) → kılavuz → kenarlık → metin. `yalniz_cubuk` metni çizmez.
- Yazdırma/PDF (`ui/yazdir.py`) aynı yolu kullanır (koşullu biçim çıktıda görünür — Excel).
- **Ölçütler:** 100.000 hücre, 3 kural (hücre değeri, yinelenen, renk ölçeği) tüm sütunlarda: dikey kaydırma 1 satır ≤ 16 ms, ilk çizim ≤ 60 ms; bir hücre değişince yeniden çizim ≤ 50 ms (istatistik yeniden hesabı dahil — yinelenen/renk ölçeği 100.000 hücrede bir geçiş).

### 8.4 Arayüz (biçim çubuğunda **Koşullu Biçimlendirme** menü düğmesi)
- **Hücre Kurallarını Vurgula ▸** Büyüktür…, Küçüktür…, Arasında…, Eşittir…, Metin İçerir…, Yinelenen Değerler… · **İlk/Son Kuralları ▸** İlk 10 Öğe…, İlk %10…, Son 10 Öğe…, Son %10…, Ortalamanın Üstünde…, Ortalamanın Altında… · **Veri Çubukları ▸** 6 düz/gradyan renk (Excel paleti: mavi `#638EC6`, yeşil `#63BE7B`, kırmızı `#F8696B`, turuncu `#FFB628`, açık mavi `#008AEF`, mor `#D6007B`) · **Renk Ölçekleri ▸** 4 hazır (yeşil-sarı-kırmızı `#63BE7B/#FFEB84/#F8696B`, kırmızı-sarı-yeşil, yeşil-beyaz, beyaz-kırmızı) · Yeni Kural… (formül ve hücre değeri) · Kuralları Temizle ▸ Seçili Hücrelerden / Tüm Sayfadan · Kuralları Yönet…
- Hızlı pencereler: değer alanı (hücreden seçilebilir: başvuru yazılır) + hazır biçim listesi (Excel): "Koyu Kırmızı Metinli Açık Kırmızı Dolgu" (`#FFC7CE`/`#9C0006`), "Koyu Sarı Metinli Sarı Dolgu" (`#FFEB9C`/`#9C5700`), "Koyu Yeşil Metinli Yeşil Dolgu" (`#C6EFCE`/`#006100`), "Açık Kırmızı Dolgu", "Kırmızı Metin", "Kırmızı Kenarlık", "Özel Biçim…" (Hücreleri Biçimlendir penceresinin Yazı Tipi/Kenarlık/Dolgu/Sayı sekmeleri, yazı tipi adı/boyutu kapalı). Hazır adların Türkçe yazımı §8b-72.
- Kuralları Yönet: liste (Kural, Biçim önizlemesi, Uygulandığı yer, Doğruysa Durdur), Yeni/Düzenle/Sil, yukarı/aşağı (öncelik), "Biçimlendirme kurallarını göster: Geçerli Seçim / Bu Sayfa".
- Koşullu biçim **kopyalanmaz/boyanmaz** (pano, doldurma, biçim boyacısı) — §11.

## 9. .xlsx gidiş-dönüşü (her alt işte kendi parçası)
| Öğe | openpyxl | Dikkat |
|---|---|---|
| Tanımlı ad | `wb.defined_names` (+ `ws.defined_names` sayfa kapsamı, openpyxl ≥3.1) | `_xlnm.*` (Print_Area/Print_Titles 4d'de; `_FilterDatabase` filtreden yeniden üretilir) ad listesine girmez; formül `ceviri` ile sayfa adı ⇄ kimlik; `hidden` korunur |
| Not | `cell.comment = Comment(metin, yazar)` | dizili açıklama uyarısı kalır |
| Filtre | `ws.auto_filter.ref`, `filterColumn` (`filters`, `customFilters`, `top10`, `dynamicFilter type="aboveAverage"`, `colorFilter` → dxf) | açılışta gizli satırlar zaten `row hidden`; filtre koşulları yalnız yeniden uygulamada kullanılır (açılışta yeniden hesaplanmaz — Excel de açılışta uygulamaz) |
| Doğrulama | `ws.data_validations` (`DataValidation`) | **tuzak:** .xlsx `showDropDown="1"` açılır listeyi **gizler** (ters anlam); liste sabiti `"a,b"` tırnaklı; `sqref` çok aralıklı |
| Koşullu biçim | `ws.conditional_formatting` (`Rule`, `DifferentialStyle`, `ColorScale`, `DataBar`) | **tuzak:** dxf düz dolguda renk `bgColor`'dadır (hücre stilindeki `fgColor` değil); `priority` → liste sırası; desteklenmeyen tür (simge kümesi, `timePeriod`, x14 uzantıları) → kural atlanır + uyarı |

- `xlsx_io` korunamayan öğe taraması daralır: koşullu biçim/doğrulama/filtre/not/tanımlı ad **yalnız desteklenmeyen alt türleri** için uyarır (her alt iş kendi taramasını günceller; uyarının **artık çıkmadığı** da test edilir).
- `testler/ornekler/` her öğe için birer örnek (openpyxl ile üretilmiş) + gidiş-dönüş eşitliği; gerçek Excel'de açma `test.md`'de "elle test bekliyor".

## 10. Sonnet'e devir — sıralı alt işler (her biri testli; kural 11/12)

| # | İş | Bitiş ölçütü |
|---|---|---|
| 5a | Ortak altyapı (§1): `ek`/`ad` olayları, `aralik_kaydir` (birleşimler buna geçer), `aralik_cikar`, `bitisik_bolge`, `Sayfa` ek depoları + `_kaydir` + `ek_durumu`, `kaydir.ek_duzeltmeleri` iskeleti, `model/harmanla.py`, `agac_kaydir`, Düzen/Veri menü iskeleti | Qt'siz testler; mevcut birleşim/ekle-sil testleri değişmeden geçer; `agac_kaydir` ⇔ `kopyala` eşitliği; harmanlama: Türkçe alfabe, İ/ı, rakam/noktalama, karışık tür, boş en sonda |
| 5b | Bul / Değiştir / Git (§2) | Her seçenek için test; Tümünü Değiştir tek geri al; 100.000 hücrede Tümünü Bul ≤ 1 sn |
| 5c | Sırala (§3) + `karsilastir`'ın Türkçe harmanlamaya geçişi (§1.4 regresyon notu) | §3.2 ölçütleri; değişen mevcut test varsa önce kullanıcıya bildirildi |
| 5d | Adlandırılmış aralıklar (§4) + .xlsx | Kapsam önceliği, göreli ad, yeniden adlandırma formülleri düzeltir, silinen ad `#AD?`, ekle-sil, sayfa silme/geri al, motor bağımlılığı, döngüsel ad; ad kutusu tanımlar/gider |
| 5e | Notlar (§5) + .xlsx | Ekle-sil, sırala, kes/kopyala, Temizle, Delete korur; ekran görüntüsü (üçgen, kutu) |
| 5f | Filtre + ALTTOPLAM (§6) + .xlsx | Her koşul türü × 4 vaka; görünen-hücre işlemleri; ALTTOPLAM 1–11/101–111 × 4 vaka (kural 11), `boyut` olayında yeniden hesap; panel ekransız testi |
| 5g | Veri doğrulama (§7) + .xlsx | Her tür × işleç; üç hata stili; açılır liste; yapıştırma denetlenmez; `showDropDown` ters anlam testi |
| 5h | Koşullu biçim (§8) + .xlsx | Her kural türü × 4 vaka; öncelik + `dur`; dxf `bgColor`; §8.3 performans ölçütleri; `cizim_dogrula` + ekran görüntüsü |
| 5i | Faz 5 sonu: `test.md` bölümü, örnek dosyalar, gerçek iş senaryosu (stok listesi: sırala, filtrele, ALTTOPLAM, doğrulamalı açılır liste, koşullu biçimli kritik stok, adlandırılmış fiyat tablosu, notlar), performans ölçümü — **ertelenen satır/karo piksel önbelleği kararı burada** (`surec.md` 2026-10-10 kararı: hâlâ ❌ ise yapılır), Opus gözden geçirmesi | plan.md faz bitiş ölçütü |

**Arayüz sözleşmesi (5a sonunda hazır olur):** `adres.aralik_kaydir/aralik_cikar/bitisik_bolge`; `harmanla.metin_anahtari/deger_anahtari`; `agac.agac_kaydir`; `Sayfa.notlar/dogrulamalar/kosullu/filtre`, `Sayfa.ek_durumu/ek_durumu_yukle`; `CalismaKitabi.adlar/ad_bul/ad_durumu`; olaylar `ek`, `ad`.

## 11. Kararlar (Excel'den bilinçli farklar ve varsayımlar)
- Filtre gizliliği tek bit (`gizli_satir`); filtre aralığında gizli satır = filtreli sayılır (ALTTOPLAM, kopyala, Delete). Excel'in dosya modeliyle aynı; elle gizlenmiş satır filtre yeniden uygulanınca açılabilir (Excel de).
- Filtre değer listesi düz metin listesi; tarihler yıl/ay/gün ağacında gruplanmaz.
- Sıralama: özel listeye göre (ay/gün adları) ve aynı boyutlu birleşimli aralık sıralaması yok; birleşimli aralık reddedilir.
- Değiştir geçersiz formül üreten hücreyi atlar ve sonunda bildirir (Excel ilk hatada durur).
- Tanımlı ad, doğrulama kaynağı ve koşullu biçim formülü alanlarında K7 işaretleme modu yok (metin yazılır); ileride eklenebilir.
- Notlar: "Tüm notları göster", not kutusunu taşıma/boyutlandırma, dizili açıklamalar yok.
- Veri doğrulama yalnız elle girişte (Excel de yapıştırmada denetlemez); "Geçersiz verileri daire içine al" yok.
- Koşullu biçim ve doğrulama pano/doldurma/biçim boyacısıyla **taşınmaz** (Excel taşır — sonraki faz; şimdilik konuma bağlı kalır, ekle-sil ve kes-yapıştırda değil yalnız ekle-silde aralık kayar). Simge kümeleri ve tarih oluşumu kuralları yok (açılışta uyarı).
- Koşullu biçim önbelleği her içerik/sonuç olayında tümden boşalır (doğruluk önce; ölçüm kötüyse daraltılır).
- "Tablo olarak biçimlendir" (Excel tablo nesnesi, yapılandırılmış başvurular) Faz 5'te **yok** → Faz 8; açılışta uyarı sürer.
