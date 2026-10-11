# Şablon Sihirbazı ve Veri Giriş Formları — tasarım taslağı (Faz 10)

Durum: **taslak, kod yok** (2026-10-11). Kapsam ve faz sırası `plan.md` Faz 10–11; kararlar §9. Uygulamadan önce Opus gözden geçirmesi önerilir (şema yanlışı sonradan pahalıdır).

## 1. İlkeler
1. **Her şey tanım dosyası:** sorular, modüller, sütunlar, türler, formüller, bağlantılar, kurallar, ayarlar, örnek veri, "Nasıl kullanılır" metni. Yeni şablon = yeni JSON; kod değişmez. Yeni *sütun türü* ya da *kural işlevi* kod ister (kapalı küme, §3.3).
2. **Tek kural kaynağı:** doğrulama kuralları yalnız veri modelindeki tanımda yaşar. Tablo hücre doğrulamasına (`Dogrulama`) derlenir; form aynı kuralı aynı formül motoruyla değerlendirir. Formda ya da tabloda ayrı kural yazılmaz (CLAUDE.md kural önerisi 21).
3. **Formül kanonik İngilizce** (CLAUDE.md kural 3): tanım dosyasındaki `formul` alanı kanonik biçimdedir (`=SUMIFS(...)`); kullanıcıya Türkçe gösterilir. Tabcel'e özel işlevler `TR_` önekiyle (kural 16).
4. **Üretilen kitap sıradan bir kitaptır:** formüller, doğrulamalar, açılır listeler, tanımlı adlar standart .xlsx öğeleridir; form bilgisi kaybolsa bile tablo Excel'de çalışır.
5. **Kimlikle bağ, konumla değil:** modül/sütun/ayar kimliği kalıcıdır; hücre adresi türetilir (§5).
6. **Sürümlü:** her tanım dosyasında ve gizli sayfadaki veride `surum` (şema sürümü) bulunur; eski sürüm `gocler` ile yükleme sırasında dönüştürülür; yeni sürüm eski uygulamada reddedilir (form devre dışı, tablo çalışır).
7. **Hata dayanıklılığı:** hatalı tanım uygulamayı çökertmez; atlanır, Türkçe gerekçeyle listelenir.

## 2. Dosya düzeni
```
tabcel/sablonlar/                 uygulama içi (salt okunur; PyInstaller verisi)
    akislar/stok_takibi.json      akış: sorular + hangi modüller + ayarlar + Nasıl Kullanılır
    moduller/urunler.json         modül: sütunlar, kurallar, örnek veri
    ortak/para_birimleri.json, anahtar_kelimeler.json
%APPDATA%\<APP_NAME>\sablonlar\   kullanıcı klasörü (aynı yapı; geçerli olanlar listeye eklenir)
```
- Kimlik = dosya adı değil, içindeki `kimlik` alanı. Aynı `kimlik` hem yerleşikte hem kullanıcıda varsa **ikisi de listelenir** (karar): kullanıcınınki "Stok takibi (benim sürümüm)" adıyla ayrı satır; yerleşik sessizce değişmez. İç kimlik `yerlesik:stok_takibi` / `kullanici:stok_takibi`.
- Kullanıcı modülü yerleşik modülü **adıyla** genişletemez (v1); akış kendi modülünü getirir ya da yerleşik modüle `kimlik@surum` ile başvurur.
- **Yükleme raporu:** her dosya şemaya göre doğrulanır; hatalı dosya atlanır, `YuklemeRaporu` → "Şablonlar" penceresinde `dosya.json — moduller[2].sutunlar[1].tur: bilinmeyen tür "para2"` gibi Türkçe satırlar. Uygulama açılışında sessiz; kullanıcı klasörü açılınca/yenilenince gösterilir.

## 3. Şema taslağı (surum 1)

### 3.1 Ortak alanlar
Her dosya: `{"surum": 1, "tur": "modul" | "akis", "kimlik": "...", "ad": "...", "aciklama": "...", ...}`. JSON yorum desteklemediği için açıklama her düğümde `aciklama` alanındadır (arayüze de ipucu olarak gider). Bilinmeyen alanlar **hata değil uyarı** (ileri uyum), zorunlu alan eksikse hata.

### 3.2 Modül
```jsonc
{
  "surum": 1, "tur": "modul", "kimlik": "urunler", "ad": "Ürünler", "tekil_ad": "Ürün",
  "aciklama": "Satılan ya da stokta tutulan her ürün için bir satır.",
  "sayfa_adi": "Ürünler",                  // Excel sayfa kuralları (≤31, yasak karakter yok) yükleyicide denetlenir
  "gorunen": ["urun_kodu", "ad"],          // başka modülde seçim listesinde gösterilen metin
  "sutunlar": [ /* §3.3 */ ],
  "kurallar": [ /* §3.4: satır düzeyi */ ],
  "form": { "gruplar": [ {"ad": "Genel", "alanlar": ["urun_kodu","ad","barkod"]} ] },   // isteğe bağlı; yoksa sütun sırası
  "matris": null,                           // Aşama 4 (varyant matrisi): {"satir":"beden","sutun":"renk","deger":"miktar"}
  "ornek_veri": [ {"urun_kodu":"U001","ad":"Örnek tişört","alis_fiyati":120} ]
}
```

### 3.3 Sütun
```jsonc
{ "kimlik": "alis_fiyati", "ad": "Alış fiyatı",
  "tur": "para",                 // metin | tam_sayi | ondalik | para | yuzde | tarih | evet_hayir | baglanti | hesaplanan
                                 // | tc_kimlik | vergi_no | iban | telefon | eposta
  "para_birimi": "TRY",          // yalnız para; ayarlardan da gelebilir ("ayar:para_birimi")
  "zorunlu": false, "benzersiz": false, "varsayilan": null,
  "kisit": {"min": 0, "max": null, "uzunluk": null},
  "baglanti": {"modul": "urunler", "alan": "urun_kodu"},    // yalnız baglanti: yazdıkça süzülen liste + doğrulama
  "formul": "=[urunler.alis_fiyati]*(1+AYAR.kdv)",           // yalnız hesaplanan (§3.5 yer tutucuları)
  "eger": "fiyat_takibi",        // bayrak ifadesi; yanlışsa sütun hiç üretilmez
  "barkod": false,               // Aşama 4: bu alan barkod girişi
  "aciklama": "KDV hariç birim alış fiyatı." }
```
Tür → davranış tablosu (tek yerde, kodda kapalı küme): hücre sayı biçimi, hücre doğrulaması (`Dogrulama`), form bileşeni, boş değer kuralı.
`tc_kimlik/vergi_no/iban/telefon/eposta` doğrulaması **yalnız `model/kimlik.py`** (kural 18); hücre doğrulamasında özel formül `TCKİMLİKDOĞRULA`/`VERGİNOGEÇERLİ`/`IBANGEÇERLİ` (telefon/e-posta için `TR_VALIDATE_*` eklenmesi 10a ön işi). Bu sütunlar baştaki sıfırı korumak için **metin biçimlidir** (kural 15).

### 3.4 Kural (satır düzeyi)
```jsonc
{ "kimlik": "stok_negatif_olmasin", "ad": "Stok eksiye düşemez",
  "formul": "=[stok_durumu.mevcut]-[@miktar]>=0",     // aynı formül dili; DOĞRU = geçerli
  "ne_zaman": "hareket_turu=Çıkış",                    // isteğe bağlı koşul
  "ileti": "Bu çıkış stoğu eksiye düşürür (mevcut: {mevcut}).", "siddet": "durdur" }   // durdur | uyar
```
Zorunlu/benzersiz/tür/aralık kısıtları sütunda; çok alanlı ve modüller arası kurallar burada. Derleme: tek hücreye indirgenebilenler `Dogrulama(tur="ozel")`; başka satırlara bakanlar (benzersizlik, stok) formül tabanlı özel doğrulama. Form aynı `formul`u motorla değerlendirir.
*Sınır:* hücre doğrulaması yapıştırmada Excel'de de atlanır; form her zaman denetler, tabloya yapıştırma Tabcel'de de doğrulamayı atlar → "Sağlık Kontrolü: kural ihlali" bulgusu (10f) yapıştırılan hatalı kayıtları yakalar.

### 3.5 Formül yer tutucuları (genişleme kuralları — kodda tek yer)
| Yer tutucu | Anlamı |
|---|---|
| `[@kimlik]` | aynı satırdaki sütun (`$C2`) |
| `[modul.kimlik]` | modülün sütununun veri aralığı (sınırlı adlandırılmış aralık `TR_M_modul_kimlik`) |
| `AYAR.kdv` | Ayarlar sayfasındaki adlandırılmış hücre (`TR_AYAR_kdv`) |
| `[modul]` | modülün tüm veri bölgesi |
Genişleme sonucu **kanonik İngilizce, sıradan A1/ad başvurusu** olur; kitapta yer tutucu kalmaz. Sütun/satır ekleme-silmede formüller zaten mevcut `kaydir` ile uyum sağlar. Aralık sınırı: veri bölgesi adı `TR_M_*` dinamik değildir → sabit kapasite (varsayılan 20.000 satır, ayarlanabilir; aşılırsa yeniden boyutlandırma "Şablonu genişlet" komutu). *Gerekçe:* Tablo nesnesi (yapısal başvuru) yoktur (Faz 8'e ertelendi).

### 3.6 Ayarlar
Akışta/modülde `ayarlar: [{"kimlik":"kdv","ad":"KDV oranı","tur":"yuzde","varsayilan":0.20,"aciklama":"…"}]` → tek "Ayarlar" sayfası, adlandırılmış hücreler; oranlar formüle gömülmez.

### 3.7 Akış (sihirbaz)
```jsonc
{
  "surum": 1, "tur": "akis", "kimlik": "stok_takibi", "ad": "Stok takibi", "kategori": "Ticaret",
  "aciklama": "Ürünlerin giriş-çıkışını ve anlık stok durumunu izleyin.",
  "anahtar_kelimeler": { "kokler": ["stok","stoğ"], "es_anlamlilar": ["envanter","depo takibi","mal takibi"], "agirlik": 1.0 },
  "sorular": [
    {"kimlik":"varyant","metin":"Ürünlerinizin beden, renk gibi çeşitleri var mı?","tur":"evet_hayir",
     "varsayilan": false, "emin_degilim": false, "aciklama":"Evet derseniz her çeşit ayrı satırda izlenir."},
    {"kimlik":"depo","metin":"Birden fazla deponuz veya şubeniz var mı?","tur":"evet_hayir","varsayilan":false,"emin_degilim":false},
    {"kimlik":"fiyat","metin":"Alış ve satış fiyatlarını takip etmek ister misiniz?","tur":"evet_hayir","varsayilan":true,"emin_degilim":true},
    {"kimlik":"cari","metin":"Müşteri ve tedarikçilerinizi de kaydetmek ister misiniz?","tur":"evet_hayir","varsayilan":false,"emin_degilim":false}
  ],                                                         // en çok 7 soru (yükleyici denetler)
  "moduller": [
    {"modul":"urunler"}, {"modul":"stok_hareketleri"}, {"modul":"stok_durumu"},
    {"modul":"varyantlar","eger":"varyant"}, {"modul":"depolar","eger":"depo"}, {"modul":"cariler","eger":"cari"}
  ],
  "bayraklar": { "fiyat_takibi": "fiyat", "coklu_depo": "depo" },     // bayrak = cevap kimliği (ya da ifade)
  "ayarlar": [ {"kimlik":"kdv","ad":"KDV oranı","tur":"yuzde","varsayilan":0.20} ],
  "nasil_kullanilir": [ {"baslik":"Ürün ekleme","metin":"…"} ],
  "ornek_veri": true
}
```
"Emin değilim, siz seçin" her soruda sihirbaz tarafından otomatik eklenir (tanımda `varsayilan` uygulanır); soru sırası, atlanabilir sorular (`"eger"`) desteklenir.

### 3.8 Anahtar kelime eşleştirme (YZ yok)
`metin_tr.kucuk` + ASCII katlama (`stoğu`→`stogu`) + sözcük bölme; her sözcük için `kök` **önek eşleştirmesi** (≥3 harf; ekler: stoklarımı, stoğu, stokta) — ünsüz yumuşaması (k→ğ) için tanımda kök listesine yumuşak biçim konur (`stok`, `stoğ`). Puan = eşleşen kök/eş anlamlı ağırlığı; eşik üstündeki en yüksek akış önerilir, yakın puanlar birlikte gösterilir; eşleşme yoksa kategori düğmeleri. Tüm veri `anahtar_kelimeler`'de (kod değişmez).

## 4. Üretim
`uret(akis, cevaplar, kullanici_sablonlari) → CalismaKitabi` (Qt'siz): bayrakları çöz → modül/sütun filtrele (`eger`) → sayfa + başlık satırı + tür biçimleri + `Dogrulama` + açılır liste (bağlantı: başka modülün sütunu) + formül genişletme + tanımlı adlar (`TR_M_…`, `TR_AYAR_…`) + Ayarlar + **Nasıl Kullanılır** + (isteğe bağlı) örnek veri + gizli sayfa (§5). "Örnek verileri temizle" komutu örnek satırları **işaretli** (gizli sayfada anahtar listesi) olduğu için yalnız onları siler. Canlı önizleme aynı `uret`'i bellekte çalıştırıp ilk N satırı gösterir.

## 5. Saklama: çok gizli sayfa `_tabcel` (karar)
- **Neden:** openpyxl `veryHidden` sayfayı gidiş-dönüşte korur (denendi); bilinmeyen `customXml` parçasını **siler**; özel belge özellikleri parçalı/sınırlı.
- **İçerik:** (A) başlık satırı: `surum`, `uretici` (APP_NAME + sürüm), `parca_sayisi`, `sağlama` (SHA-256 hex); (B) A2…An: JSON **parçaları** (her hücre ≤ 30.000 karakter; sınır 32.767). JSON = `{surum, akis_kimligi, akis_surumu, cevaplar, tanim (kullanılan modüllerin tam kopyası), baglar}`. Tanım kopyası gömülür → kullanıcı şablonu sonradan değişse/silinse de dosya kendi başına çalışır.
- **Model:** `Sayfa.gizli` bool → `gizli: "yok"|"gizli"|"cok_gizli"` (xlsx okuma/yazma; arayüzde sekme yine görünmez *çok gizli* için gösterilmez). `_tabcel` kitap modelinde sıradan sayfa **değil**, `kitap.sablon` nesnesidir (açılışta ayrıştırılır, kayıtta yazılır).
- **Bağlama (konumla değil):** her modül için (1) **tanımlı ad çapası** `TR_MOD_<modül>` = başlık satırı aralığı → Excel sayfa yeniden adlandırma ve sütun ekle/sil'de bunu kendisi günceller (ana mekanizma); (2) sütun = **başlık metni** (yedek) + gizli sayfada sütun kimliği ↔ başlık eşlemesi; (3) hesaplanan sütunlar için sağlama özeti (formül metni).
- **Açılışta uyuşma denetimi:** `sablon_denetle(kitap)` → bulgular: sağlama uyuşmuyor/JSON bozuk (devre dışı), çapa yok, sayfa yok, başlık yok/yeni sütun/yerinde değil (başlık adıyla yeniden eşleme **önerilir**, kullanıcı onaylar), sürüm daha yeni (devre dışı). Her durumda: **form devre dışı + durum çubuğunda/şeritte Türkçe uyarı; tablo ve formüller çalışmaya devam eder; çökme yok.** Kullanıcı seçenekleri: "Yeniden eşle", "Formu kapat (şablon bilgisini sil)", "Olduğu gibi bırak".
- **KVKK Paylaşım Temizleyici:** `kitap.sablon` JSON'u ve (modele düşmemiş) **tüm çok gizli sayfaları** tarar (gizli yer olarak etiketlenir, "çok gizli"); temiz kopyada şablon bilgisi korunur ama içindeki metinler (örnek veri, etiketler) maskelenir; `uretici`/kullanıcı adı alanı yazılmaz.
- **Excel'de düzenleme:** kullanıcı Excel'de `_tabcel`'i değiştirirse sağlama tutmaz → devre dışı + uyarı; gizli sayfayı yalnız VBA/özel araçla göstermek mümkündür (belgelenir).

## 6. Form ve tablo eşzamanı
- Form modülün **veri aralığını** doğrudan okur/yazar; ayrı kopya yok. Kayıt = mevcut komutlar (`HucrelerDegis`) → **geri al yığını**; tablo düzenlemesi de aynı yığın. Kitap olayları (`hucre`, `yapi`, `sonuc`) formu dinler; açık formda ilgili satır değişirse alanlar yenilenir (düzenlenmekte olan alan uyarıyla korunur: "bu kayıt başka yerde değişti").
- Hesaplanan alanlar salt okunur; anlık değer için formun taslak satırı **geçici bir satırda** (kitapta görünmeyen sanal satır) motorla değerlendirilir ya da formül ifadesi ayrı değerlendirilir (10f'te karar: ilkine eğilimli — tek hesap yolu).
- Satır silme/ekleme/sıralama/filtre sonrası kayıt kimliği: modül `anahtar` sütunu (benzersiz) → konum değil anahtar izlenir; anahtar yoksa gizli `_kayit_no` sütunu (kalıcı artan sayı) eklenir.

## 7. Form arayüzü (özet)
Alan türü → bileşen: metin → `QLineEdit`; tam/ondalık/para/yüzde → Türkçe biçimli sayı kutusu (`girdi.akilli_coz` kuralları); tarih → takvimli seçici + klavye (`gg.aa.yyyy`); evet/hayır → onay kutusu (Boşluk); bağlantı → yazdıkça süzülen `QComboBox` (editable + `QCompleter`, Türkçe harmanlama `metin_tr`); hesaplanan → salt okunur etiket. **Klavye:** Enter = sonraki alan (çok satırlı hariç), son alanda Kaydet, `Ctrl+Enter` = Kaydet ve yeni, `Esc`, `Ctrl+PgUp/PgDn` = önceki/sonraki kayıt, `Ctrl+F` = kayıt ara. Hata iletisi alanın altında; kural `siddet` = `durdur` ise kaydedilmez, `uyar` ise onayla kaydedilir.

## 8. Aşama 4 notları
- **Barkod:** USB okuyucu = hızlı tuş dizisi + Enter; barkod alanında Enter'da arama (`baglanti` alanı üzerinde tam eşleşme); bulunamazsa "Yeni ürün olarak ekle" (Ürünler formu barkod önceden dolu açılır, kaydedince hareket formuna döner). Algılama için özel sürücü yok.
- **Varyant matrisi:** `matris` tanımıyla tek ızgara (satır: beden, sütun: renk); girilen sayılar **ayrı ayrı satırlar** olarak yazılır (tek geri al adımı); boş hücre yazılmaz.

## 9. Kararlar (kullanıcı, 2026-10-11)
JSON (YAML değil; bağımlılık/lisans yok, `aciklama` alanları) · uygulama içi + kullanıcı klasörü; aynı kimlik → **ikisi de listelenir** · saklama: **çok gizli sayfa** + parçalama + sağlama + tanımlı ad çapası + başlık/kimlik eşleme · uyuşmazlıkta çökmez, formu devre dışı bırakır, yeniden eşleme önerir · Temizleyici çok gizli sayfayı tarar · `surum` her tanımda ve gizli veride, göç zinciri · Şablon Düzenleyici ayrı faz (Faz 11).

## 10. Açık teknik riskler (uygulamada karara bağlanacak)
- Hesaplanan alanın anlık değeri için sanal satır mı, ayrı ifade değerlendirmesi mi (§6).
- Sabit kapasiteli adlandırılmış aralıklar × `SUMIFS` performansı (20.000 satır × N ürün; `formul_olcum` ile ölçülecek, gerekirse `Stok Durumu` ürün başına tek geçişli `SUMIFS` yerine sıralı birikim).
- Hücre doğrulamasının yapıştırmada atlanması (Excel'de de) → Sağlık Kontrolü "kural ihlali" kontrolü.
- Tek geri al adımında çok satır (varyant matrisi) ve form–tablo eşzamanlı düzenleme çakışması.
