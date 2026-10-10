# Faz 6 — Grafikler ve resimler: tasarım notu (2026-10-10)

> **Not (yazar):** proje kuralı bu notun Opus 5.5 ile yazılmasını ister; oturumda model değiştirilmediği için **Sonnet 5.5** yazdı. Uygulamaya başlamadan önce **Opus gözden geçirmesi önerilir** (özellikle §3 konum/ekle-sil, §6 .xlsx, §10 kararlar). Excel'den bilinçli farklar §11'de; doğrulanması gerekenler `surec.md` §8b'ye yazılır.

Kapsam `plan.md` → Faz 6: sütun, çubuk, çizgi, pasta, halka, alan, dağılım (XY) grafikleri; sayfa üstünde yüzen nesne (taşı, boyutlandır, sil); başlık, gösterge, eksen başlıkları, renkler; veri değişince canlı güncelleme; .xlsx yazma **ve okuma**; resim ekleme; **Ekle sekmesi** (5j'de bilerek ertelendi).

Genel ilke (Faz 1–5 ile aynı): **veri ve geometri `model/`de (Qt yok, Qt'siz test edilir), Qt yalnız `ui/`de.** Her değişiklik geri alınabilir komuttur; toplu işlem TEK olay, TEK geri al adımı. QtCharts kullanılmaz (GPL, kural 5): grafikler QPainter ile.

## 0. Önemli bulgu: openpyxl grafikleri OKUYABİLİYOR (plan.md düzeltmesi)
`plan.md` "okuma openpyxl'de yok" diyordu; **yanlış**. openpyxl ≥ 2.5 `ws._charts`ı yükler (`reader/drawings.find_images` → `chart/reader`), `testler/ornekler/grafikli.xlsx` ile doğrulandı: `BarChart`, çapa, başlık, seri başvuruları (`'Satış'!$B$2:$B$5`) okunuyor. Sınır: openpyxl'in anlamadığı biçimler (3B, eğilim çizgisi, ikincil eksen, gradyan, bazı türler) düşer; **resimleri okumak/yazmak Pillow ister** (şu an kurulu değil). Sonuç: Faz 6'da grafik gidiş-dönüşü openpyxl üzerinden yapılır, kendi XML okuyucusu **gerekmez** (Faz 8'deki "Excel grafiklerini okuma" maddesi yalnız openpyxl'in düşürdüklerini kurtarmaya iner). Faz 4'te yazılan "grafik uyarısı" mantığı yeniden düzenlenir (§6.3).

## 1. Model (`model/grafik.py`, Qt yok)

```
Referans(sayfa_kimlik: int, aralik: Aralik)            # değişmez; sayfa KİMLİKLE (K6): sayfa silinince #BAŞV!, geri alınca düzelir
Seri(ad: Optional[str], ad_ref: Optional[Referans],     # ad: sabit metin; ad_ref: başlık hücresi (varsa o kazanır)
     deger: Optional[Referans], kategori: Optional[Referans],   # dağılımda kategori = X değerleri
     renk: Optional[str])                              # '#rrggbb' ya da None (palet sırası)
Konum(satir, sutun, dx, dy)                            # sol üst çapa hücre + o hücreden piksel kayması (%100 yakınlaştırmada, 96 dpi)
Grafik(kimlik, tur, alt_tur, seriler: Tuple[Seri], baslik, gosterge,
       x_baslik, y_baslik, deger_etiketi: bool, y_min, y_max, x_min, x_max,
       konum: Konum, boyut: (genislik, yukseklik))     # piksel; varsayılan 480 × 288
Resim(kimlik, veri: bytes, ad, konum, boyut)           # PNG/JPEG/GIF/BMP baytları aynen saklanır (xlsx'e kayıpsız yazılsın)
```
- `tur` ∈ `sutun | cubuk | cizgi | pasta | halka | alan | dagilim`; `alt_tur` ∈ `kumelenmis | yigili | yuzde_yigili` (sütun/çubuk/alan; çizgide yalnız `kumelenmis` + `yigili`; pasta/halka/dağılımda yok sayılır). `gosterge` ∈ `sag | alt | ust | sol | None`. Hepsi değişmez (`dataclass(frozen=True)`, `degistir(**)`); eşitlik değer eşitliğidir.
- **Kimlik:** sayfa başına artan sayı (`Sayfa._sonraki_nesne`), `.xlsx` yüklemede de atanır; komutlar nesneyi kimlikle bulur (örnek nesne değil) → geri al/yinele sonrası seçim korunabilir.
- `Sayfa.nesneler: List[Union[Grafik, Resim]]` — **liste sırası = z sırası** (son en üstte). Yöntemler: `nesne(kimlik)`, `nesne_ekle(n, indeks=None)`, `nesne_sil(kimlik) -> (nesne, indeks)`, `nesne_degistir(yeni)` (kimliği aynı), `nesne_sirala(kimlik, indeks)`. Her biri TEK `nesne` olayı yayar.
- **Yeni olay `nesne`:** `ayrinti`: `islem` ∈ `ekle | sil | degis | sira`, `kimlik`. Formül motoru **yok sayar**; ızgara ilgili nesnenin önbelleğini düşürür + o dikdörtgeni yeniden çizer; pencere "değişti" işareti zaten komuttan gelir (`GeriAlYigini.damga`). *(`window._kitap_olayi`, `Hesaplayici._olay`, `dosya_islemleri._gorunum_olayi` yeni türü yok sayarken bozulmasın — Sonnet testle doğrular; `olay.py` belgesine eklenir.)*
- **`ek_durumu()` 4'lü demeti DEĞİŞMEZ** (mevcut testler `ek_durumu_yukle(({..}, [], [], None))` çağırır, kural 12). Nesneler ayrı: `Sayfa.nesne_durumu()` → `list(nesneler)` (değişmez nesneler → sığ kopya yeter), `nesne_durumu_yukle(liste)` → TEK `nesne` olayı (`islem="hepsi"`).

### 1.1 Komutlar (`model/komutlar.py`)
`NesneEkle(sayfa, nesne)`, `NesneSil(sayfa, kimlik)`, `NesneDegis(sayfa, yeni)` (taşıma, boyutlandırma, tür/başlık/seri değişimi — **sürükleme boyunca canlı önizleme komutsuz yapılır, bırakınca TEK komut**), `NesneSirala(sayfa, kimlik, yon)` (`one_getir`, `arkaya_gonder`, `bir_one`, `bir_arkaya`). Hepsi `ana_sayfa` tarafından tanınır (geri al o sayfaya geçirir).

## 2. Konum, ekle-sil, sıralama

### 2.1 Çapa ve boyut
Excel'in grafikte **"Hücrelerle birlikte taşı ve boyutlandır"** (twoCell) varsayılanı yerine **oneCell (taşı, boyutlandırma)** kullanılır: nesne sol üst çapasına bağlı kalır, boyutu piksel sabittir. Gerekçe: satır yüksekliği/otomatik yükseklik değişince grafiğin esnemesi sürpriz olur; model sade kalır (çapa + boyut). Okurken `twoCellAnchor` boyuta çevrilir (sütun genişlikleri/satır yükseklikleri toplanarak); yazarken `oneCellAnchor` + `ext` yazılır (Excel açar, **bilerek fark** §11).

Piksel konumu: `(x, y) = hücre_sol_ust(satir, sutun) + (dx, dy)` — ızgara bunu mevcut `_gen/_yuk` toplamlarıyla hesaplar (gizli satır/sütun 0 genişlik → nesne o hücrede "çöker", Excel'de de çapa gizliyse aynı). `dx, dy` hücreden büyükse çizimde taşar (normal). **Taşıma:** yeni piksel konumundan `Konum` geri hesaplanır (en yakın hücre + kalan kayma); `dx, dy ≥ 0` tutulur.

### 2.2 Satır/sütun ekle-sil
- Kaydırma kuralı `Sayfa._kaydir_indeks` ile: `satir ≥ nerede` ise `satir += fark`; çapa hücresi **silinen bantta** ise nesne silinmez, çapa bandın hemen ötesine (`nerede`) iner, `dx/dy` sıfırlanır (Excel nesneyi korur). Boyut değişmez.
- **Başvurular (seriler) da kayar** — ve bu **kitap düzeyindedir**: Sayfa2'deki grafik Sayfa1'in aralığına bakıyorsa Sayfa1'de satır eklemek o başvuruyu da düzeltmeli. `formul/kaydir.ek_duzeltmeleri` (5a'daki) genişler: tüm sayfaların nesnelerindeki `Referans`lar `aralik_kaydir` ile (içine ekleme büyütür, silme küçültür, tamamen silinen **aralık → None** = o seri/kategori başvurusu kaybolur; seri değeri kalmayan seri düşer, hiç seri kalmayan grafik **silinmez**, boş görünür: "Grafik için veri yok").
- **Geri al:** `_SatirSutun` zaten tüm sayfaların `ek_durumu`sunu önce saklıyor; yanına `nesne_durumu()` listesi eklenir (`_ek_once` demetinin yeni, 3. öğesi — mevcut anahtarlar değişmez), geri alırken `nesne_durumu_yukle`.
- **Sıralama, filtre, kes-yapıştır:** grafik başvuruları **aralık olarak sabit** kalır (Excel gibi sıralama grafiği değiştirmez ama veri değişir → canlı güncelleme). Kes-yapıştır (`HucreTasi`) başvuruyu taşımaz (Excel taşır; **bilerek fark**, §11).
- Sayfa silinir/geri gelir: kimlik düzeni sayesinde otomatik (silinen sayfaya başvuran seri `#BAŞV!` → çizimde boş).

## 3. Veri çözümleme (`model/grafik_verisi.py`, Qt yok)

`grafik_verisi(kitap, grafik) -> GrafikVerisi` — `seriler: List[SeriVerisi(ad, degerler: List[Optional[float]], kategoriler: List[str], x: Optional[List[float]], renk)]`, `bos: bool`.
- Değerler `Sayfa.deger` (formül sonucu): sayı → float; **boş hücre → None** (çizgi/dağılımda boşluk, sütunda 0 yükseklik); metin/mantıksal → 0 (Excel: metin 0 çizilir; **doğrulanacak** §8b); hata değeri → None (`#YOK` boşluk kuralı).
- **Gizli satır/sütun çizilmez** (Excel varsayılan "Gizli ve boş hücreleri göster" kapalı; filtreyle gizlenenler dahil): `Sayfa.gizli_satir/gizli_sutun`. Gizlilik değişince (`boyut` olayı) ilgili grafikler yeniden hesaplanır.
- Kategori etiketleri **görünen metin** (`gosterim`/`sayi_bicimi.bicimle`, hücrenin sayı biçimiyle); tarih kategorileri **metin eksenidir** (Excel'in otomatik tarih ekseni yok, §11). Değer ekseni/veri etiketleri ilk serinin ilk dolu hücresinin sayı biçimini kullanır ("kaynağa bağlı").
- Seri adı: `ad_ref` varsa onun görünen metni, yoksa `ad`, yoksa "Seri{n}".
- **Seri tahmini** `seriler_tahmin(sayfa, aralik, tur) -> Tuple[List[Seri], bool]` (grafik eklerken): Excel sezgisi — ilk satır **tamamen metin** ve altı sayı ise üst bilgi satırı; ilk sütun metin (ya da tarih) ise kategori sütunu; **boyutu küçük olan eksen seridir** (sütun sayısı ≤ satır sayısı → seriler sütunlarda). Sol üst hücre boşsa hem satır hem sütun başlığı var sayılır. Dağılım: ilk sütun X, kalanlar Y. Pasta/halka: yalnız ilk seri. `satirda_seri` bayrağı döner (arayüzde "Satır/Sütun Değiştir"). Tahmin edilemezse (hiç sayı yok) `ValueError("Seçili alanda çizilebilecek sayısal veri yok")`.

## 4. Çizim: Qt'siz "çizim listesi" + ince Qt boyayıcı

**Karar:** grafik geometrisi (eksen ölçeği, çubuk/çizgi/pasta yerleşimi, gösterge, başlık) **`model/grafik_cizim.py` içinde Qt'siz hesaplanır** ve ilkellerden oluşan bir **çizim listesi** döner; `ui/grafik_boyayici.py` bu listeyi QPainter'la oynatır (ızgara önbelleği, yazdırma/PDF ve belki ileride SVG aynı listeyi kullanır). Gerekçe: Faz 2'deki "değerlendirici Qt'siz" ilkesi — geometri **sayısal olarak** test edilir (piksel karşılaştırması gevşek/kırılgan olur).

```
cizim_listesi(veri: GrafikVerisi, grafik: Grafik, boyut: (w, h), olcer: Callable[[str, float], (w, h)], palet) -> List[Cizim]
Cizim = Dikdortgen(x,y,w,h, dolgu, kenar) | Cizgi(x1,y1,x2,y2, renk, kalinlik) | Dizi(noktalar, renk, kalinlik)   # kırık çizgi (None noktada kopar)
      | Cokgen(noktalar, dolgu)        | Dilim(merkez, r_ic, r_dis, a0, a1, dolgu) | Isaret(x, y, boyut, sekil, dolgu)
      | Metin(x, y, metin, hiza, boyut_pt, renk, kalin, aci)
```
`olcer(metin, pt) -> (genislik, yukseklik)` dışarıdan verilir (arayüz `QFontMetrics`, testler sabit genişlikli sahte ölçer) → etiket sığdırma/döndürme kararları da testlenir.

- **Düzen:** dış boşluk 8; başlık üstte (14 pt, kalın; yoksa alan yok); gösterge `sag|alt|ust|sol` (seri/pasta için kategori adları, işaretli kutucuk + metin; tek serili sütun/çizgi grafikte Excel gibi gösterge yok varsayılanı); eksen başlıkları (Y döndürülmüş −90°); sonra çizim alanı. Y ekseni etiket genişliği önce ölçülür, alan ona göre daralır.
- **Eksen ölçeği** `guzel_olcek(min, max, hedef_adet) -> (alt, ust, adim)` — "güzel sayılar" (1, 2, 2.5, 5 × 10ⁿ); sütun/alan/çubukta alt sınır sıfırı içerir (Excel); çizgi/dağılımda veri aralığına göre (sıfıra zorlanmaz, Excel gibi alt sınır verinin %… altı — **doğrulanacak** §8b); negatif değerlerde eksen sıfırdan geçer; `y_min/y_max` doluysa onlar. Yığılı: toplamlara göre; %100 yığılı: 0–1 (%).
- **Türler:**
  - *Sütun/çubuk:* kümelenmiş (kategori genişliği = seri sayısı × çubuk + boşluk; **Excel varsayılanı boşluk genişliği %219 (Excel 2013+) / %150 (eski), çakışma %0** — hangisinin Türkçe Excel web'de görüldüğü doğrulanacak §8b; ilk uygulama %150), yığılı, %100 yığılı. Çubuk = eksenler yer değiştirmiş sütun (kategoriler dikey eksende, **ilk kategori altta**, Excel çubuk grafiği gibi).
  - *Çizgi:* düz çizgi + işaretçi (daire, 5 px), yığılı seçeneği; boş değer çizgiyi koparır (`Dizi` parçalanır).
  - *Alan:* poligon (yarı saydam yok — Excel 2013 düz dolgu), yığılı.
  - *Pasta/halka:* tek seri; dilimler saat yönünde 12 yönünden; negatif/sıfır değer dilimi yok; dilim etiketi isteğe bağlı (yüzde); halka iç yarıçap %50; çok serili halka **yok** (ilk seri).
  - *Dağılım:* yalnız işaretçi (varsayılan; çizgili seçeneği sonra), X sayısal ölçek, kategori yoksa 1,2,3….
- **Palet:** Office 2013+ vurguları `#4472C4 #ED7D31 #A5A5A5 #FFC000 #5B9BD5 #70AD47`, sonrası aynı renklerin %60 koyu/%40 açık tonları (Excel'in sırasıyla); `Seri.renk` doluysa o. Uygulama vurgu yeşili (`#217346`) serilerde **kullanılmaz** (Excel ile aynı görünsün). Yazı rengi `#595959`, ızgara çizgisi `#D9D9D9`, eksen çizgisi `#BFBFBF`.
- **Çok noktalı seride (> ~2×genişlik) boşaltma:** çizgi/alan/dağılım için piksel sütunu başına en küçük/en büyük nokta (min/max boşaltma) → çizim listesi ≤ ~4 × genişlik öğe; sütun/çubukta > genişlik/2 kategori varsa etiketler seyreltilir (her n'inci). **Ölçüt:** 100.000 noktalı çizgi grafiği listeyi kurma ≤ 150 ms; 1.000 noktalı ≤ 10 ms.
- **Boş/hatalı durum:** hiç seri/veri yoksa ortada gri "Grafik için veri yok" metni.

## 5. Izgarada katman (`ui/grid.py` + yeni `ui/grafik_boyayici.py`)

**Karar: nesneler `Izgara._boya` içinde, hücrelerin üstünde çizilir; çocuk QWidget kullanılmaz.** Gerekçe: ızgara zaten artımlı kaydırma (`viewport().scroll`) ve kendi çizimiyle çalışıyor, çocuk widget'lar dondurulmuş bölme/yakınlaştırma/birleşik hücrelerle yeniden konumlama karmaşası getirir; süzgeç düğmeleri ve doldurma tutamacı da böyle çiziliyor.
- **Sıra:** hücre içerikleri → birleşimler → notlar → … → **nesneler (z sırasıyla)** → seçim/kopyalama çerçeveleri → (üstte) açılır liste/not kutusu widget'ları. Seçili nesnenin tutamaçları nesnelerin üstünde. Nesne **seçim çerçevesini örter** (Excel gibi).
- **Önbellek:** her nesne için `QPixmap` (`Izgara._nesne_onbellek[kimlik] = (anahtar, pixmap)`; anahtar `(nesne, boyut×yakınlaştırma×dpr, veri_surumu)`). Grafik: çizim listesi → pixmap bir kez; her `_boya` yalnız `drawPixmap` (≤ 1 ms). Resim: ölçeklenmiş pixmap. **Geçersiz kılma:** `nesne` olayı (ilgili kimlik), `hucre`/`sonuc`/`yapi`/`boyut` olayı (başvurusu o hücrelerle **kesişen** grafikler — `Referans.aralik` ∩ değişen anahtarlar; ad/biçim değişimi `bicim` olayında sayı biçimi etiketleri için), yakınlaştırma (hepsi).
- **Canlı güncelleme erteleme:** `hucre`/`sonuc` olayları bayrak koyar, **tek `QTimer` (30 ms)** yeniden kurar (50.000 hücrelik tek `sonuc` olayı bir kez işlenir; yazarken her tuşta çizim yok). Ölçüt: tek hücre değişince grafik ≤ 100 ms içinde güncel (1.000 noktalı).
- **Kaydırma:** satır/sütun adımlı kaydırmada piksel kaydırma nesnelerle uyumludur (nesne çapası bir hücreye bağlı, `viewport.scroll` hücre ve nesne pikselini birlikte kaydırır); yalnız açığa çıkan şeritlerde nesneler kırpılarak yeniden çizilir (mevcut `_boya(kirp)` düzeni). **Dondurulmuş bölme:** nesne çapasının bölgesine göre kırpılır (Excel gibi bölme çizgisini geçen kısım kesilir); dondurma açıkken zaten tam çizim yapılıyor.
- **Yakınlaştırma:** konum/boyut `_z()` ile ölçeklenir, grafik yazıları `taban × yakınlaştırma` punto (çizim listesi ölçekli boyutla yeniden kurulur, `olcer` ölçekli yazı tipiyle).
- **Hiçbir nesne yokken ek maliyet:** `if self.sayfa.nesneler:` tek denetim (Faz 5 kuralı).

### 5.1 Etkileşim
- **Seçme:** nesneye tık → nesne seçilir (`Izgara._secili_nesne: Optional[int]` kimlik), **hücre seçimi değişmez** (Excel gibi hücre seçimi kalkmaz ama biz aktif hücre çerçevesini nesne seçiliyken gizlemeyiz); nesne dışına tık / Esc / hücre klavye gezinmesi nesne seçimini bırakır. Üst üste nesnelerde en üstteki (listede sonuncu) seçilir; **Alt+tık** bir alttakini (isteğe bağlı, sonra).
- **Taşıma:** gövdeden sürükle (4 piksel eşik); sürüklerken canlı önizleme (önbellek pixmap'i kaydırılır), bırakınca `NesneDegis`. **Shift** eksene kilitler; sayfa kenarına yaklaşınca otomatik kaydırma **yok** (§11). Nesne başlıkların (satır/sütun başlığı) altına sürüklenemez (konum ≥ 1,1 hücresi).
- **Boyutlandırma:** 8 tutamaç (köşe 7 px kare, orta kenar); köşede **Shift** oranı korur (Resim için varsayılan oran korunur, Shift serbest bırakır — Excel'in tersi: resim köşeden oranlı, grafik serbest); en küçük boyut 40×30 px. Yeniden boyutlandırırken canlı: pixmap ölçeklenir, 60 ms'de bir gerçek yeniden kurulum, bırakınca `NesneDegis`.
- **Klavye:** `Delete` seçili nesneyi siler; **ok tuşları** nesneyi 1 px kaydırır (Ctrl: 10 px)… *yalnız nesne seçiliyken* (hücre gezinmesini bozmaz); `Esc` seçimi bırakır; `Ctrl+C/X/V` nesneyi **dahili panoya** (yalnız bu uygulama; aynı kitapta çoğaltma, sayfalar arası) — dış panoya resim/grafik yazılmaz (§11).
- **Sağ tık menüsü (nesne):** Kes, Kopyala, Sil · Öne Getir ▸ (Öne Getir / Bir Adım Öne), Arkaya Gönder ▸ · Grafik: **Veriyi Seç…**, **Grafik Türünü Değiştir…**, **Grafik Ayarları…** · Resim: **Boyutu Sıfırla**, **Resmi Değiştir…** (sonra).
- **Çift tık:** grafik → Grafik Ayarları penceresi; resim → yok.
- Hücre sağ tık menüsüne "Grafik Ekle" **eklenmez** (şerit Ekle sekmesi yeterli).
- İmleç: gövdede dört yönlü ok, tutamaçta yeniden boyutlandırma okları. Durum çubuğu: seçili nesne adı ("Grafik 1", "Resim 2"; Ad Kutusu nesne adını gösterir — Excel gibi, düzenlenebilir ad **yok**, §11).

## 6. Arayüz

### 6.1 Ekle sekmesi (Giriş'ten sonra, `ui/serit_sekmeleri.py` → `EkleSayfasi`)
| Grup (öncelik) | İçerik |
|---|---|
| Grafikler (5) | B **Sütun ▾** (Kümelenmiş, Yığılı, %100 Yığılı) · B **Çubuk ▾** (aynı üçü) · B **Çizgi ▾** (Çizgi, Yığılı Çizgi) · B **Pasta ▾** (Pasta, Halka) · B **Alan ▾** (Alan, Yığılı Alan) · B **Dağılım** (XY) · ↘ **Veriyi Seç / Grafik Ekle…** penceresi |
| Resimler (4) | B **Resim…** (dosya iletişim kutusu; PNG/JPG/GIF/BMP) |
Her galeri öğesi: seçili aralıktan `seriler_tahmin` + `NesneEkle` (tek geri al adımı); konum **görünen alanın ortası**, çapa en yakın hücre; yeni nesne seçili olur ve "Grafik" bağlamsal sekmesi görünür. Seçim tek hücre ise bitişik bölge (`bitisik_bolge`). Sayısal veri yoksa uyarı.
- **Sekme sırası** (Excel): Dosya, Giriş, **Ekle**, Sayfa Düzeni, Formüller, Veri, Gözden Geçir, Görünüm. *(Kural 12: `test_serit_pencere`, `test_serit_sekmeleri` sekme listesi `["Dosya", "Giriş", "Ekle", …]`'e güncellenir — beklenen, bilgi.)*

### 6.2 "Grafik" bağlamsal sekmesi
Yalnız grafik seçiliyken görünür (`Serit.sekme_goster(ad, bool)` = `QTabBar.setTabVisible`; **vurgu renkli sekme** — Excel'in "Grafik Araçları"); seçim değişince **otomatik geçilmez** (yalnız yeni eklenen grafikte geçilir). İçerik (hepsi var olan komutlara bağlı):
- **Tür** grubu: Grafik Türünü Değiştir ▾ (galeri), Satır/Sütun Değiştir, Veriyi Seç…
- **Grafik Öğeleri** grubu: ☑ Grafik Başlığı, ☑ Gösterge ▾ (Sağ/Alt/Üst/Sol/Yok), ☑ Eksen Başlıkları, ☑ Veri Etiketleri (hepsi işaretli eylem; model alanını değiştirir)
- **Renkler** grubu: Renkleri Değiştir ▾ (Office, Mavi tonları, Yeşil tonları, Turuncu tonları, Gri — seri renklerini topluca yazar)
- **Düzen** grubu: Öne Getir ▾, Arkaya Gönder ▾, Sil.
Sekme gizlenirken şerit geçerli sekmesi Giriş'e döner. Resim seçiliyken bağlamsal sekme yok (yalnız sağ tık menüsü; sonra).

### 6.3 Pencereler (`ui/grafik_pencereleri.py`)
- **Grafik Ayarları** (çift tık / sağ tık / bağlamsal sekme): Tür + alt tür (liste), Başlık, Gösterge konumu, Eksen başlıkları, Değer etiketleri, Eksen en küçük/en büyük (boş = otomatik), Seri listesi (ekle/sil/yukarı/aşağı: **Seri adı**, **Değerler** aralık kutusu, **Kategori/X değerleri**, Renk düğmesi). Aralık kutuları tür **Excel yazımıyla** (`Sayfa1!$B$2:$B$5`, Türkçe Excel'de de aynı); geçersiz aralıkta pencere kapanmaz, uyarı. Tamam → tek `NesneDegis`.
- Aralık kutusuna **seçimle doldurma** (küçük "aralık seç" düğmesi, formül çubuğundaki K7 işaretleme modu ayrı iş — Faz 6 kapsamında yok: kutuya elle yazılır; `Ad Tanımla` penceresindeki aynı kalıp).

## 7. Yazdırma ve PDF (`ui/yazdir.py`)
`SayfaCizici` hücrelerden sonra **dilimle kesişen nesneleri** çizer: nesnenin sayfa pikseli (çapa hücrelerinin kümülatif konumu, `sayfalama` aynı `genislik/yukseklik` işlevleriyle) dilim dikdörtgeniyle kesiştiği kadar, **dilim alanına kırpılarak** (nesne iki baskı sayfasına bölünebilir — Excel de böyle). Grafik **vektör** çizilir (çizim listesi yazıcı çözünürlüğünde yeniden kurulur, `olcer` yazıcı yazı tipiyle); resim yazıcı pikseline ölçeklenir. Yazdırma alanı dışında kalan nesne kısmı çizilmez. Nesneler `kullanilan_aralik`'a **dahil edilmez** ama yazdırma kapsamı (kullanılan alan) nesneyi içermiyorsa Excel nesne alanını da yazdırır: **kullanılan alan = hücre alanı ∪ nesne sınırları** (yalnız yazdırma ve önizlemede; `kullanilan_aralik()` değişmez).

## 8. .xlsx (`io/xlsx_io.py`)

### 8.1 Yazma
- Grafik → openpyxl nesnesi: `BarChart(type="col"|"bar", grouping=standard|stacked|percentStacked, overlap=100 yığılıda)`, `LineChart`, `PieChart`, `DoughnutChart`, `AreaChart`, `ScatterChart(style=marker)`. Seri başvurusu `Referans` → `'Sayfa Adı'!$B$2:$B$5` (kimlik→ad, **mevcut `_adlari_yaz`/`_formul_yaz` sayfa çevirisi yeniden kullanılır**); silinen sayfaya başvuru **yazılmaz** (seri düşer). Seri adı: `tx.strRef` (başlık hücresi) ya da `tx.v` (sabit). Renk: **her seri/pasta dilimi için açık `solidFill`** (palet dahil → Excel ve Tabcel aynı görünür). Başlık/eksen başlıkları/gösterge konumu/`dLbls.showVal`/eksen `min`/`max`. `oneCellAnchor` (piksel × 9525 = EMU).
- **Tabcel imi:** kaydedilen kitaba özel belge özelliği `TabcelSurum=<APP_NAME sürümü>` (`wb.custom_doc_props`); grafik güvenilirliğini belirler (§8.3). *(openpyxl 3.1 `custom_doc_props` var; doğrulanır, yoksa `docProps/custom.xml` elle.)*
- **Resim:** `openpyxl.drawing.image.Image(BytesIO(veri))` + `OneCellAnchor` — **Pillow gerekir** (§10-D2). Resim baytları kayıpsız yazılır.

### 8.2 Okuma
`ws._charts` / `ws._images` taranır; **anlaşılan** her grafik → `Grafik`'e çevrilir: tür (sınıf + `grouping` + `barDir`), seriler (`val.numRef.f`, `cat.numRef/strRef.f`, `xVal/yVal` dağılımda, `tx.strRef.f`/`tx.v`; başvuru metni sayfa **adı** → `Referans` kimliğe çevrilir; bilinmeyen sayfa/çözülemeyen başvuru → seri atlanır + uyarı), başlık (zengin metinden düz metin), eksen başlıkları, gösterge konumu, `dLbls.showVal`, seri/dilim `solidFill` rengi (yoksa None), çapa → `Konum` + boyut (twoCell ise sütun/satır boyutlarıyla toplanır; oneCell `ext`). **Anlaşılmayan** grafik türü (radar, borsa, yüzey, kabarcık, 3B…) **atlanır**, "N grafik desteklenmiyor ve kaydedilince dosyadan çıkar" uyarısı. Çok aralıklı/ad tabanlı/sabit dizi serileri atlanır (uyarı: "bazı seriler okunamadı").

### 8.3 Uyarı mantığı (`tara`/`Rapor`) — Faz 4 kuralı yeniden
Faz 4'te grafik/resim **her zaman** "kaybolur" uyarısı veriyordu. Yeni kural:
- **Tabcel imi var** (dosya Tabcel'in kaydı): okunan grafik/resim **sayısı = zip'teki sayı** ise uyarı **yok** (gidiş-dönüş kayıpsız, testle).
- **İm yok** (Excel/başka program): grafik/resim yine yüklenir **ama** sarı bilgi çubuğu: "Bu dosyadaki grafikler Tabcel'e uyarlandı; 3B, eğilim çizgisi, ikincil eksen, gradyan gibi Excel'e özgü biçimler kaydedince kaybolabilir." ve **kaydederken eski üç seçenekli onay** (Farklı Kaydet / Yine de Kaydet / İptal) korunur (`veri_kaybi=True`). Atlanan (desteklenmeyen) grafik sayısı ayrıca belirtilir.
- Şekil/SmartArt/dilimleyici/pivot/makro: eskisi gibi "kaybolur" (`tara`'daki `xl/drawings/` içindeki `<xdr:sp>`/`<xdr:grpSp>` varlığı; yalnız `pic`/`graphicFrame` içeren çizim parçaları artık uyarı vermez).
- **Kural 12 bildirimi:** `test_xlsx_ornekler.py::test_grafikli_uyarilar_ve_veri_korunur` ("grafik"/"resim" uyarıları) ve `test_xlsx_io.py`'deki grafik uyarı testleri değişir (grafik yüklenir, im yok → yeni uyarı metni). Beklenen değişiklik; Sonnet değişikliği ve gerekçesini kullanıcıya bildirir.

## 9. Resim (`Resim`, Pillow kararı)
- Dosya seçilir → baytlar okunur (`≤ 25 MB`), `QImage` ile çözülür (boyut/geçerlilik; bozuksa "Bu dosya resim olarak açılamadı"). Varsayılan boyut: doğal boyut (96 dpi), **en çok 600 px genişlik**, oran korunur. Çizim: ölçeklenmiş `QPixmap` önbelleği.
- Dosyaya yazma/okuma Pillow ister (openpyxl). **Alternatif (Pillow'suz):** çizim parçasını (`xl/drawings/drawingN.xml` + `media/`) kendimiz zip'e yazıp okumak (~150 satır) — gerek olursa. **Öneri: Pillow** (HPND lisansı, izinli; ≈ 3 MB; kural 5 → `README`/Hakkında listesine yazılır; kullanıcı onayı gerekir §10-D2).
- Resim ayarları (kırpma, döndürme, parlaklık) **yok** (§11).

## 10. Kararlar ve kullanıcıya sorular
| # | Karar | Gerekçe / durum |
|---|---|---|
| D1 | **Grafik gidiş-dönüşü openpyxl ile; kendi XML okuyucusu gerekmez** | §0 bulgu. Faz 8'deki "Excel grafiklerini okuma" yalnız düşenleri kurtarır |
| D2 | **Pillow bağımlılığı** (resim yazma/okuma için) | ✅ **Kullanıcı onayladı (2026-10-10): Pillow eklendi** (`requirements.txt`: `Pillow>=10.0`; 12.3.0 kuruldu; lisans MIT-CMU/HPND, izinli; `README`/Hakkında bileşen listesine Faz 7'de yazılır) |
| D3 | oneCell çapa (esnemez); twoCell dosyalar okunurken boyuta çevrilir | §2.1 |
| D4 | Nesneler `Izgara._boya` içinde + pixmap önbelleği, çocuk widget yok | §5 |
| D5 | Çizim listesi Qt'siz (`model/grafik_cizim.py`), boyayıcı ince | §4; testler sayısal |
| D6 | `ek_durumu` 4'lüsü değişmez; nesne durumu ayrı | mevcut test uyumu (kural 12) |
| D7 | Grafik başvuruları kitap düzeyinde kayar (`ek_duzeltmeleri`) | §2.2 |
| D8 | "Grafik" bağlamsal sekmesi, otomatik geçmez | §6.2 |
| D9 | Tabcel imi (`TabcelSurum`) ile uyarı ayrımı | §8.3 |

## 11. Excel'den bilinçli farklar (Faz 6 kapsamı dışı / farklı)
3B grafik, eğilim çizgisi, hata çubukları, ikincil eksen, birleşik (combo) grafik, kabarcık/radar/borsa/yüzey/hunili/şelale/harita, **Grafik sayfası** (ayrı sayfa olarak grafik), sparkline, grafik stilleri/efektleri, eksen biçimlendirme ayrıntısı (aralık/ölçek log, birim, tarih ekseni), veri tablosu, **tarih ekseni** (tarihler metin kategorisi), özel veri noktası biçimi, **nesne adı düzenleme/Seçim Bölmesi**, nesne gruplama/hizalama/kilitleme, nesne adı kutusunda görünür adlandırma, grafik alanı biçimlendirme, resim düzenleme (kırpma/döndürme/efekt), dış panoya grafik/resim kopyalama, nesneyi sayfa kenarında sürüklerken otomatik kaydırma, **twoCell** çapa (okunur, yazılmaz), kes-yapıştırda grafik başvurusunun taşınması, hücre başvurusuna tıklayarak aralık seçme penceresi. Hepsi `surec.md` Kararlar'a "bilerek fark" olarak yazılır.

## 12. Uygulama sırası (Sonnet 5.5; her biri ölçütlü, kural 11/12)
- **6a Model** — `model/grafik.py` (Referans/Seri/Konum/Grafik/Resim, `degistir`), `Sayfa.nesneler` + yöntemler + `nesne` olayı, `nesne_durumu`; komutlar `NesneEkle/Sil/Degis/Sirala`; satır/sütun ekle-sil (çapa + başvuru, kitap düzeyi `ek_duzeltmeleri`, geri al); sayfa silme/geri; `olay.py` belgesi. **Ölçüt:** her komut geri al/yinele eşitliği; ekle-sil × çapa/başvuru tablo testi; başka sayfadaki grafiğin başvurusu kayar; mevcut testler değişmez.
- **6b Veri** — `model/grafik_verisi.py`: `grafik_verisi`, `seriler_tahmin`, gizli satır, boş/metin/hata kuralları, sayı biçimi etiketleri. **Ölçüt:** kural 11 şablonu (normal/boş/hata/metin-sayı karışımı) her tür için; tahmin tablosu (başlıklı/başlıksız/satırda seri/tarih kategorisi).
- **6c Çizim listesi** — `model/grafik_cizim.py`: `guzel_olcek`, düzen, 7 tür, palet, boşaltma. **Ölçüt:** geometri sayısal testleri (çubuk x/y/genişlik, pasta açıları toplamı 360°, güzel ölçek tablosu, %100 yığılı toplam 1, boş değer çizgiyi koparır); 100.000 nokta ≤ 150 ms.
- **6d Izgara katmanı** — `ui/grafik_boyayici.py` (listeyi oynat), `Izgara` nesne çizimi + önbellek + 30 ms erteleme + yakınlaştırma/kaydırma/dondurma. **Ölçüt:** piksel temelli kısa denetim (grafik alanı boş değil, kaydırınca konum doğru, `araclar/cizim_dogrula.py` artımlı = tam çizim); tek hücre değişiminde ≤ 100 ms; nesne yokken çizim maliyeti artmaz (`performans_olcum.py`).
- **6e Etkileşim** — seçme, taşıma, boyutlandırma, Delete/ok/Esc, sıra, dahili pano, sağ tık menüsü, çift tık. **Ölçüt:** QTest fare testleri (tutamaç geometrisi, eşik, Shift kilidi, en küçük boyut, geri al tek adım).
- **6f Ekle sekmesi + Grafik sekmesi + pencereler + ikonlar** (`serit_sekmeleri.EkleSayfasi`, `GrafikSayfasi`, `Serit.sekme_goster`, `grafik_pencereleri.py`, 32 px ikonlar: sütun, çubuk, çizgi, pasta, halka, alan, dağılım, resim). **Ölçüt:** her galeri öğesi `NesneEkle` üretir; bağlamsal sekme seçimle görünür/gizlenir; 1100/800 px'te taşma yok.
- **6g Resim** — D2 kararına göre.
- **6h .xlsx** — yazma/okuma, `TabcelSurum`, `tara`/`Rapor` yeni mantık. **Ölçüt:** her tür × alt tür gidiş-dönüş (model eşitliği); örnek `grafikli.xlsx` yüklenir; Excel-üretimi grafikli dosya (el yapımı XML) açılır; desteklenmeyen tür atlanır + uyarı; kaydet → aç → kaydet kararlı (idempotent).
- **6i Yazdırma/PDF**. **Ölçüt:** nesneli sayfa PDF'i üretilir, sayfa bölünmesinde nesne kırpılır (test: iki dilimde de nesnenin kendi parçası).
- **6j Faz 6 sonu** — `test.md` bölümü, **gerçek iş senaryosu** (aylık gelir-gider: grafik ekle → veri değişince güncellenir → satır ekle başvuru kayar → kaydet/aç → PDF), performans ölçümü, örnek dosya (`testler/ornekler/grafikler.xlsx` her tür), Opus gözden geçirmesi.
