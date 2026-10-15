<!--
{APP_NAME} uygulama içi yardım içeriği (F1 → "Yardım ve Nasıl Kullanılır").

Yazım kuralları:
- Her konu "<!- - konu: kimlik | Başlık - ->" satırıyla başlar (tireler bitişik yazılır).
- Konu gövdesi Markdown'dır. Kısayollar `Ctrl+B` biçiminde yazılır; konular arası bağlantı [Başlık](konu:kimlik).
- Uygulama adı elle yazılmaz: {APP_NAME} yer tutucusu kullanılır (ad değişebilir).
- Yeni bir özellik eklendiğinde: ilgili konuyu güncelleyin, "Yenilikler"e tarihli madde ekleyin, yeni kısayol
  varsa "Klavye Kısayolları" tablosuna ekleyin. Excel'den bilerek farklı davranış "Excel'den Farklar"a yazılır.
-->

<!-- konu: baslarken | Başlarken -->
# {APP_NAME}'e Hoş Geldiniz

{APP_NAME}, Excel'e alışkın olanların rahatça kullanacağı, sade ve tamamen **bilgisayarınızda çalışan** bir hesap tablosu uygulamasıdır. Verileriniz hiçbir sunucuya gönderilmez; hesap, bulut ya da izleme yoktur.

## Ekranın bölümleri

- **Başlık şeridi (yeşil):** Kaydet, Geri Al ve Yinele düğmeleri ile belgenin adı.
- **Şerit:** Dosya, Giriş, Ekle, Sayfa Düzeni, Formüller, Veri, Gözden Geçir, Görünüm ve Yardım sekmeleri. Bir grafik seçiliyken en sağda turuncu bir **Grafik** sekmesi de belirir. `Ctrl+F1` ya da sekmeye çift tıklama şeridi daraltır/açar.
- **Ad Kutusu ve formül çubuğu:** Ad Kutusu seçili hücrenin adresini gösterir; oraya `B7` ya da `A1:C5` yazıp Enter'a basarak gidebilirsiniz. Formül çubuğunda hücrenin içeriği görünür ve düzenlenir.
- **Izgara:** hücrelerin bulunduğu alan. Satır ve sütun başlıklarına sağ tıklayınca ekle/sil/gizle menüsü açılır.
- **Sayfa sekmeleri (alt):** çalışma sayfaları; `+` ile yeni sayfa eklenir, sağ tıklayıp ad ve renk verilir.
- **Durum çubuğu (en alt):** seçili sayısal hücrelerin **Ortalama · Sayım · Toplam** özeti, yakınlaştırma çubuğu.

## İlk adımlar

1. Bir hücreye tıklayıp yazın, `Enter` ile onaylayın. Formüller `=` ile başlar: `=TOPLA(A1:A5)`.
2. Kaydetmek için `Ctrl+S`. Dosyalar Excel biçiminde (.xlsx) kaydedilir ve Excel'de açılır.
3. Takıldığınızda `F1` ile bu pencereyi açın; üstteki kutuya aradığınızı yazın.

<!-- konu: yenilikler | Yenilikler -->
# Yenilikler

En yenisi en üstte.

## 15 Ekim 2026
- **İşlev kitaplığı genişledi** (2026-10-15, adlar ve sonuçlar gerçek Excel'de doğrulandı): trigonometri (`SİN`, `COS`, `TAN`, `ASİN`, `ATAN2`…), sayı kuramı (`ÇARPINIM`, `KOMBİNASYON`, `OBEB`, `OKEK`, `ROMEN`, `TABAN`…), bit ve sayı tabanı çevirme (`BİTVE`, `DEC2BIN`, `HEX2DEC`…), istatistik (`STDSAPMA.S/P`, `VAR.S/P`, `YÜZDEBİRLİK`, `DÖRTTEBİRLİK`, `KORELASYON`, `EĞİM`, `TAHMİN`, `NORM.DAĞ`, `NORM.TERS`, `RANK.EŞİT`…), metin (`DAMGA`, `KOD`, `SAYIDÜZENLE`, `LİRA`, `SAYIDEĞERİ`, `ÖNCEKİMETİN`, `SONRAKİMETİN`…), tarih (`TARİHSAYISI`, `ZAMANSAYISI`, `GÜN360`, `YILORAN`, `ISOHAFTASAY`, `TAMİŞGÜNÜ.ULUSL`, `İŞGÜNÜ.ULUSL`), finans (`FAİZTUTARI`, `ANA_PARA_ÖDEMESİ`, `TAKSİT_SAYISI`, `DA`, `YAT`, `AZALANBAKİYE`, `ÇİFTAZALANBAKİYE`, `AİÇVERİMORANI`, `ANBD`…) bilgi (`ÇİFTMİ`, `TEKMİ`, `HATA.TİPİ`, `TÜR`, `ADRES`, `SAYFA`…), matris/dizi (`DÇARP`, `DETERMİNANT`, `DİZEY_TERS`, `BİRİMMATRİS`, `SIKLIK`, `EĞİLİM`, `BÜYÜME`, `DOT`, `SATIRSAR`, `SÜTUNSAR`, `METİNBÖL`) ve veritabanı (`VSEÇTOPLA`, `VSEÇORT`, `VSEÇSAY`, `VSEÇMAK`, `VSEÇMİN`, `VAL`) işlevleri, ayrıca `TOPLAMA` (AGGREGATE)..
- **Şablonlar için Kayıt Formu** (Veri → Kayıt Formu, `Ctrl+Alt+F`): tablodaki kayıtları form olarak girin; kurallar (zorunlu, benzersiz, stok eksiye düşmesin…) tabloyla aynıdır. **Tablo Sağlığı** artık *Şablon kural ihlali* de bulur. Ayrıntı: "Şablondan Yeni".
- **Şablon Düzenleyici:** kendi şablonunuzu (sorular, tablolar, sütunlar, kurallar) liste tabanlı düzenleyicide hazırlayın ya da açık kitaptan şablon üretin: **Dosya → Kitaptan Şablon Oluştur…**, **Şablonlar… → Yeni şablon / Kopyasını düzenle**. Ayrıntı: "Şablondan Yeni".
- **Excel ile karşılaştırma düzeltmeleri** (gerçek Excel'de ölçüldü): sıfıra bölme hatası `#SAYI/0!` olarak gösterilir (eski `#BÖL/0!` yazımı girişte hâlâ okunur); **İLKEŞLEŞEN** (SWITCH) adı düzeltildi; yeni işlev **ARA** (LOOKUP); Genel biçim en çok 11 karakter gösterir (`1,23457E+11`); `DÜŞEYARA`/`KAÇINCI` yaklaşık eşleşmesi Excel gibi ikili arama yapar; `EĞERSAY(…;"=")` yalnız gerçekten boş hücreleri sayar; Türkçe özel biçim kodlarında saat `s`, dakika `d`, saniye `n` olur (`ss:dd:nn`).
- **Formül yazınca biçim kendiliğinden ayarlanır** (Genel biçimli hücrede, Excel gibi): `=BUGÜN()`/`=TARİH(…)` tarih, `=ŞİMDİ()` tarih ve saat, `=DEVRESEL_ÖDEME(…)` ve benzeri finans işlevleri para, `=İÇ_VERİM_ORANI(…)` yüzde; `=A1+1` gibi formüller başvurulan hücrenin biçimini taşır. Ayrıntı: "Formüller".
- **Dosya → Şablondan Yeni…:** ne yapmak istediğinizi yazın, {APP_NAME} uygun hazır tabloyu soru-cevapla kurar. Hazır şablonlar: *Stok takibi*, *Cari hesap takibi*, *Apartman / site aidat takibi*, *Teklif hazırlama*, *Çek ve senet takibi*, *Not çizelgesi*. Ayrıntı: "Dosyalar, Yazdırma ve Kurtarma".

## 12 Ekim 2026
- Yeni işlevler: **TELEFONGEÇERLİ**, **EPOSTAGEÇERLİ**, **TRTAMİŞGÜNÜ**, **TRİŞGÜNÜ** (Türkiye resmî tatilleriyle iş günü). Ayrıntı: "Türkiye'ye özel işlevler".
- Excel'de "çok gizli" sayfalar artık dosyada çok gizli olarak korunur. Şablonla üretilen dosyalarda şablon bilgisi çok gizli `_tabcel` sayfasında saklanır; Paylaşım Temizleyici bunu da tarar ve temiz kopyada maskeler.

## 11 Ekim 2026

- **Paylaşım Temizleyici:** dosyayı başkasıyla paylaşmadan önce T.C. no, vergi no, IBAN, telefon, e-posta, kart no ve (sütun başlığına göre) ad-soyad bulur; seçtiğinizi maskeler ya da siler ve **yeni bir dosyaya** yazar. Yardımcı araçtır; yasal uygunluğu garanti etmez. Bkz. [Formüller](konu:formuller).
- **Tablo Sağlığı:** sekiz kontrolle eksik aralık, tutarsız formül, metin sayı, hata, geçersiz T.C./vergi no/IBAN vb. bulur; onayınız olmadan hücre değiştirmez. Bkz. [Formüller](konu:formuller).
- **Hesap İzleme paneli:** bir hücrenin değerinin nereden geldiğini ve nerelerde kullanıldığını ağaç olarak gösterir; tıklayınca hücreye gider. Bkz. [Formüller](konu:formuller).
- **Ne yapmak istiyorsun? (asistan):** isteğinizi Türkçe yazın, formül ya da Özet Tablo önerisi önizlemeyle gelir; onaylarsanız yazılır. Yerel ve kural tabanlıdır. Bkz. [Formüller](konu:formuller).
- **Doldurma seçenekleri:** Ctrl ile sürüklemede seri ⇄ kopya geçişi ve doldurma sonrası *Otomatik Doldurma Seçenekleri* düğmesi (kopyala / seri / yalnız biçim / biçimlendirmeden). Bkz. [Doldurma ve Seriler](konu:doldurma).
- **Dinamik diziler:** formül sonuçları komşu hücrelere taşar; `SIRALA`, `FİLTRE`, `BENZERSİZ`, `SIRALI`, `AL`, `BIRAK`, `DÜŞEYYIĞ`, `YATAYYIĞ`, `SÜTUNA`, `SATIRA`, `SÜTUNSEÇ`, `SATIRSEÇ`, `GENİŞLET`, `RASGDİZİ`, `DEVRİK_DÖNÜŞÜM` ve `LET` işlevleri eklendi. Bkz. [Formüller](konu:formuller).
- **Özet Tablo:** Ekle sekmesinden satır/sütun/değer alanlarıyla özet tablo oluşturulur (anlık görüntü). Bkz. [Sırala, Filtre, Bul ve Değiştir](konu:siralafiltre).
- **.ods (OpenDocument Hesap Tablosu):** açılır ve kaydedilir; Excel ve LibreOffice ile uyumludur. Bkz. [Dosyalar, Yazdırma ve Kurtarma](konu:dosyalar).
- **Parolalı çalışma kitabı:** Dosya → *Parola Belirle…*; parolalı .xlsx açılırken parola sorulur. Bkz. [Dosyalar, Yazdırma ve Kurtarma](konu:dosyalar).
- **.xls açma:** eski Excel dosyaları artık açılır (yalnız okuma; formüller değer olarak gelir). Bkz. [Dosyalar, Yazdırma ve Kurtarma](konu:dosyalar).
- **Hızlı Erişim çubuğu:** şeritteki herhangi bir düğmeye sağ tıklayıp *Hızlı Erişim Araç Çubuğuna Ekle* deyin; komut pencerenin üst şeridinde Kaydet/Geri Al/Yinele'nin yanında durur (en çok 12). Kaldırmak için o düğmeye sağ tıklayın. Ayar kapatıp açınca kalır.
- **Yazım denetimi (F7):** Gözden Geçir sekmesinde; Windows'un Türkçe yazım denetimiyle metin hücrelerini denetler. Bkz. [Veri Doğrulama, Koşullu Biçim ve Notlar](konu:veriaraclari).
- **Hakkında ve uygulama ikonu:** Yardım sekmesi → Hakkında; sürüm, künye ve kullanılan açık kaynak bileşenler. Uygulamanın kendi ikonu (yeşil sayfa, ızgara, T) eklendi.
- **Google Drive / OneDrive:** Dosya menüsünden buluttaki klasörden aç/oraya kaydet; dosya başka yerde değişirse haber verilir. Bkz. [Dosyalar, Yazdırma ve Kurtarma](konu:dosyalar).
- **Hata açıklamaları:** hata değeri olan hücrede (ipucu ve durum çubuğu) hatanın nedeni ve hangi hücreden geldiği Türkçe yazılır. Bkz. [Formüller](konu:formuller).
- **Seçim içinde gezinme (Excel gibi):** birden çok hücre seçiliyken `Enter`/`Tab` etkin hücreyi seçimin içinde dolaştırır; `Ctrl+Boşluk`/`Shift+Boşluk` etkin hücreyi yerinde bırakır; `Ctrl+A` önce veri bölgesini, ikinci basışta tüm sayfayı seçer.
- **Türkiye'ye özel işlevler:** `YAZIYLA(sayı)` sayıyı yazıya çevirir (125 → *yüz yirmi beş*), `TCKİMLİKDOĞRULA(no)` T.C. kimlik numarasının sağlama kuralına uyup uymadığını söyler. Bkz. [Formüller](konu:formuller).

- **Sayfa sınırı çizgileri ve el ile sayfa sonu:** Görünüm → Sayfa Sonlarını Göster; Sayfa Düzeni → Kesmeler. Ayrıca *yüksekliği tek sayfaya sığdır* ve *sayfa sırası* seçenekleri. Bkz. [Dosyalar, Yazdırma ve Kurtarma](konu:dosyalar).

- **Grafik ve resim yazdırma:** grafikler ve resimler artık yazdırılır ve PDF'e aktarılır. Bkz. [Dosyalar, Yazdırma ve Kurtarma](konu:dosyalar).

## 10 Ekim 2026

- **Resim ekleme:** **Ekle → Resim…** ile PNG, JPEG, GIF ya da BMP dosyası ekleyin; taşıyıp boyutlandırabilirsiniz. Bkz. [Grafikler ve Resimler](konu:grafikler).
- **Dosyada grafik ve resim:** grafikler ve resimler artık .xlsx'e kaydedilir, Excel'den gelen grafikli dosyalar açılır.
- **Grafikler:** **Ekle** sekmesinden sütun, çubuk, çizgi, pasta, halka, alan ve dağılım grafiği ekleyin. Grafik sayfanın üzerinde yüzer; taşıyıp boyutlandırabilir, verisi değişince canlı güncellendiğini görebilirsiniz. Bkz. [Grafikler](konu:grafikler).
- **Sekmeli şerit:** menüler yerini Excel'deki gibi sekmeli şeride bıraktı.
- **Yardım:** bu pencere (`F1`).

<!-- konu: hucreler | Hücreler ve Giriş -->
# Hücreler ve Giriş

## Yazma ve düzenleme

- Hücreye yazıp `Enter` (aşağı) ya da `Tab` (sağa) ile onaylayın; `Esc` girişi iptal eder. Birden çok hücre seçiliyse `Enter`/`Tab` (geri için `Shift` ile) seçimin **içinde** ilerler: önce sütun boyunca (Enter) ya da satır boyunca (Tab), sonda başa döner; seçim bozulmaz, böylece bir alanı art arda doldurabilirsiniz.
- `F2` ya da çift tıklama hücreyi düzenleme kipine alır. Hücre içinde satır sonu için `Alt+Enter`; böyle girilen metin kendiliğinden "Metni Kaydır" olur.
- `Ctrl+Enter` yazdığınızı seçili tüm hücrelere uygular.
- `Delete` içeriği siler (biçim kalır). **Giriş → Temizle** menüsü biçimi, notu ya da hepsini temizler.
- `Ctrl+Z` geri alır, `Ctrl+Y` yineler. Hemen her işlem tek adımda geri alınır.

## Akıllı giriş: yazdığınız ne olarak anlaşılır?

{APP_NAME} Türkçe yazımı tanır:

| Yazdığınız | Anlaşılan |
|---|---|
| `1.234,56` | sayı (binlik nokta, ondalık virgül) |
| `₺100`, `1.234,56 ₺` | para birimli sayı |
| `%15` | yüzde (0,15) |
| `10.10.2026`, `10/10/2026`, `12 Ekim 2026`, `2026-01-02` | tarih |
| `(5)` | eksi sayı (−5) |
| `14:30` | saat |
| `00123` | sayı **123** olur (Excel gibi); sıfırı korumak için hücreyi Metin biçimine alın |

Anlaşılamayan her şey metin olarak kalır. Tarih ve sayı biçimi hücreye otomatik verilir; sonradan **Giriş → Sayı** ya da `Ctrl+1` ile değiştirilir.

## Seçim

- Sürükleyin ya da `Shift` + ok / tıklama ile aralık seçin; `Ctrl` + tıklama ile birden çok aralık seçin.
- Başlığa tıklayarak tüm satır/sütunu seçin; `Ctrl+Boşluk` sütunu, `Shift+Boşluk` satırı seçer (etkin hücre yerinde kalır). `Ctrl+A` etkin hücre bir veri bloğundaysa önce o bloğu, ikinci basışta tüm sayfayı seçer.
- `Ctrl` + ok veri bloğunun kenarına atlar; `Ctrl+Home` / `Ctrl+End` sayfanın başına / son hücresine gider.
- `Ctrl+G` ya da `F5` **Git** penceresini açar (adresler ve tanımlı adlar).

<!-- konu: formuller | Formüller -->
# Formüller

Formül `=` ile başlar. Fonksiyon adları **Türkçe**, bağımsız değişken ayırıcı **noktalı virgüldür**: `=EĞER(A1>10;"büyük";"küçük")`, `=TOPLA(A1:A3;2,5)`. Ondalık ayırıcı virgüldür. Dosyayı Excel'e kaydettiğinizde formüller Excel'in kendi biçimine çevrilir ve orada da çalışır.

## Yazarken yardım

- Fonksiyon adını yazmaya başlayınca öneri listesi açılır; tanımlı adlarınız da listede görünür.
- Formül yazarken bir hücreye tıklamak ya da ok tuşlarıyla gezmek **başvuruyu yazar**; başvurular renkli gösterilir.
- `F4` başvuruyu `A1 → $A$1 → A$1 → $A1 → A1` sırasıyla mutlak/göreli yapar.
- **Otomatik Toplam** (`Alt+=`) seçili sayıların toplamını altına ya da yanına yazar.

## Formül yazınca hücre biçimi (biçim mirası)

Hücrenin biçimi **Genel** iken formül yazarsanız {APP_NAME} de Excel gibi sonuca uygun biçimi kendiliğinden verir; biçimi sonradan Hücreleri Biçimlendir ile değiştirebilirsiniz. Başka bir biçim verilmiş hücreye dokunulmaz; kopyala-yapıştırda kaynağın biçimi gelir.

- `=BUGÜN()`, `=TARİH(…)`: kısa tarih · `=ŞİMDİ()`: tarih ve saat · `=ZAMAN(…)`: saat.
- `=DEVRESEL_ÖDEME`, `=GD`, `=BD`, `=NBD` finans işlevleri: para; `=İÇ_VERİM_ORANI`, `=FAİZ_ORANI`: yüzde.
- `=A1`, `=A1+1`, `=B1+A1`, `=-A1`, `=TOPLA(…)`, `=ORTALAMA(…)`, `=MAK`, `=MİN`, `=ORTANCA`, `=YUVARLA`, `=TAMSAYI`, `=MOD`: başvurulan ilk biçimli hücrenin biçimi. İki tarihin farkı gün sayısıdır (Genel). `*`, `/`, `^`, `&`, `%` ve karşılaştırma işleçleri ya da diğer işlevler (MUTLAK, EĞER, EĞERSAY…) biçim taşımaz.

## Hata değerleri

| Değer | Anlamı |
|---|---|
| `#SAYI/0!` | sıfıra bölme |
| `#DEĞER!` | işlenemeyen değer türü (ör. sayı beklenen yerde metin) |
| `#BAŞV!` | geçersiz başvuru (silinen hücre/sayfa) |
| `#AD?` | tanınmayan fonksiyon ya da ad |
| `#SAYI!` | geçersiz sayısal değer |
| `#YOK` | aranan değer bulunamadı |
| `#BOŞ!` | kesişmeyen aralıklar |
| `####` | sütun sayıyı göstermeye yetmeyecek kadar dar; genişletin |

Döngüsel başvuru (bir hücre kendi sonucuna bağlıysa) durum çubuğunda "Döngüsel Başvurular" olarak bildirilir.

**Hatanın nedeni:** hata değeri olan bir hücreye fareyle gelip biraz bekleyin ya da hücreyi seçin; ipucunda ve durum çubuğunda Türkçe açıklama görünür, ör. *#DEĞER!: B3 hücresinde sayı yerine metin var ("abc").* Hata başka bir hücreden geliyorsa yol da gösterilir: *#DEĞER!: B3 hücresinden geliyor (D5 → C4 → B3). B3: …* Böylece hatayı asıl üreten hücreye gidip düzeltebilirsiniz. Çok uzun zincirlerde (2.000 hücreden fazla) arama durur ve son izlenen hücre söylenir.

## Türkiye'ye özel işlevler

- **YAZIYLA(sayı):** sayıyı Türkçe yazıya çevirir. `=YAZIYLA(125)` → *yüz yirmi beş*, `=YAZIYLA(-3)` → *eksi üç*, `=YAZIYLA(2,05)` → *iki virgül sıfır beş*. Mutlak değeri katrilyonun (10^15) altında olmalı, yoksa `#SAYI!` verir.
- **TCKİMLİKDOĞRULA(no):** 11 haneli T.C. kimlik numarası sağlama kurallarına uyuyorsa DOĞRU, uymuyorsa YANLIŞ verir. Sayı ya da metin kabul eder (baştaki sıfır kaybolmasın diye metin yazabilirsiniz). Kişinin gerçekten var olup olmadığını denetlemez.
- **VERGİNOGEÇERLİ(no):** 10 haneli vergi kimlik numarası sağlama kuralına uyuyorsa DOĞRU verir. Sıfırla başlayan numaraları **metin** olarak yazın (`"0123456789"`), yoksa sayıda baştaki sıfır kaybolur.
- **IBANGEÇERLİ(iban):** Türkiye IBAN'ı (26 karakter, mod-97) doğruysa DOĞRU verir; boşluklu ya da tireli yazım kabul edilir. Hesabın var olup olmadığını denetlemez.
- **TELEFONGEÇERLİ(numara):** Türkiye telefonu (`+90 532 123 45 67`, `0532…`, parantezli/tireli yazım; cep, sabit ve 850 hatları) doğruysa DOĞRU verir. Hattın var olup olmadığını denetlemez.
- **EPOSTAGEÇERLİ(adres):** e-posta adresi biçimi doğruysa DOĞRU verir; adresin var olup olmadığını denetlemez.
- **TRTAMİŞGÜNÜ(başlangıç; bitiş; [tatiller]):** `TAMİŞGÜNÜ` gibi, ama Türkiye resmî tatillerini (yılbaşı, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz, 30 Ağustos, 29 Ekim, dini bayramlar) kendiliğinden eler; isteğe bağlı `tatiller` listesi bunlara eklenir. Arife günleri tam iş günü sayılır. Tatil verisi **2024–2028** yıllarını kapsar; dışındaki tarihlerde `#SAYI!` verir. Dini bayram tarihleri henüz doğrulanmadı; idari izin/köprü günleri yoktur.
- **TRİŞGÜNÜ(başlangıç; gün; [tatiller]):** `İŞGÜNÜ` gibi, resmî tatilleri atlayarak. `TAMİŞGÜNÜ`/`İŞGÜNÜ` Excel'deki gibi çalışmaya devam eder.
- Bu işlevler **Excel'de yoktur**; dosyayı .xlsx olarak kaydedince Excel ve diğer programlarda `#AD?` verirler. Kaydederken bu konuda uyarılırsınız. Başka kişiye gidecek dosyada sonucu değere çevirmeniz (kopyala → Özel Yapıştır → Değerler) önerilir.

## Hesap İzleme: “Bu sayı nereden geliyor?”

**Formüller → Formül Denetleme → Hesap İzleme** (ya da `Ctrl+Alt+I`) yan paneli açar; bir hücre seçtiğinizde o değerin **nasıl hesaplandığını** adım adım gösterir. Panel sürüklenerek istediğiniz kenara yerleştirilebilir, kapatılabilir; hücreleri **değiştirmez**.

- **Nereden geliyor?** sekmesi: seçili hücrenin formülü (Türkçe) ve altında hesap zinciri: her satırda hücre adresi, formül ve değer (hücrenin sayı biçimiyle, ör. `145.000 ₺`). Ağaç tembel açılır; ilk iki seviye hazır gelir, `▸` ile derinleşirsiniz. Formülü olmayan hücreler (sabit değerler) zincirin yapraklarıdır. Başka sayfadaki hücreler sayfa adıyla yazılır (`Veri!A1`).
- **Aralıklar tek satırdır:** `TOPLA(A1:A1000)` için `A1:A1000 — 1.000 hücre, 1.000 dolu, toplam 84.250`; açınca dolu hücreler 100'erli sayfalarla listelenir (`… daha göster`). Binlerce satır birden çizilmez.
- **Nerelerde kullanılıyor?** sekmesi: seçili hücreyi okuyan formüller (doğrudan, ya da bir aralık içinden); her biri kendi bağımlılarıyla açılır.
- Bir satıra **tıklayınca** ızgarada o hücreye gidilir (başka sayfaya da) ve hücre kısa süre turuncu çerçeveyle vurgulanır. Panel gezinirken kök değişmez; ızgarada kendiniz başka hücre seçince panel o hücreye geçer.
- **Hata değerleri:** zincirde hata varsa panelin üstünde *Hatanın kaynağı: …* yazar ve hatanın asıl doğduğu hücre `⚠` ile işaretlenir.
- **Döngüsel başvuru** `↻` ile işaretlenir ve açılmaz (sonsuz döngü olmaz).
- Değerler yeniden hesaplanınca panel kendiliğinden güncellenir; formül düzenlenince ağaç yeniden kurulur. Panel kapalıyken hiçbir işlem yapılmaz.

## Tablo Sağlığı: sorunlu yerleri bulma

**Gözden Geçir → Denetim → Tablo Sağlığı** yan paneli açar ve çalışma kitabının tüm sayfalarını tarar. Tarama arka planda küçük dilimlerle çalışır: arayüz donmaz, ilerleme çubuğu görünür, **İptal** ile durdurabilirsiniz. Denetçi **hiçbir hücreyi kendiliğinden değiştirmez**; yalnız siz *Düzelt*'e basarsanız değiştirir ve `Ctrl+Z` geri alır.

Sekiz kontrol vardır; sonuçlar *Kritik / Uyarı / Bilgi* altında adetleriyle listelenir:

- **Eksik aralık** (kritik): `TOPLA`, `ORTALAMA`, `SAY`… aralığının hemen bitişiğindeki veri toplamaya katılmıyor.
- **Hata değerleri** (kritik): hata veren hücreler; aynı kaynaktan doğanlar tek bulguda toplanır ve hatanın asıl doğduğu hücreye gidilir.
- **Geçersiz kimlik verisi** (kritik): T.C. kimlik no, vergi no, IBAN sütunlarında sağlama kuralına uymayan değerler. Sütun, başlığından ya da içeriğinin çoğunun geçerli olmasından anlaşılır.
- **Tutarsız formül** (uyarı): komşularıyla aynı desende olması gereken ama farklı olan formül (bilerek dönüşümlü desenler sayılmaz).
- **Metin olarak saklanan sayı** (uyarı; tüm sütun metinse bilgi): hesaplara katılmayan sayılar. IBAN, T.C. no, telefon, baştaki sıfırlı kodlar ve *Metin* biçimli hücreler sorun sayılmaz.
- **Formül içinde sabit sayı** (bilgi): `=B5*1,18` gibi. Sık kullanılan sayılar (0, 1, 2, 12, 100, 365…) yoksayılır; liste **Ayarlar…**'dan değişir.
- **Boş hücreye başvuru** (bilgi) ve **Yinelenen satırlar** (bilgi).

Bir bulguya **tıklayınca** ızgarada ilgili hücreye gidilir; altında sade bir açıklama ve “neden sorun olabilir” yazar. **Düzelt** yalnız güvenli durumlarda vardır (metni sayıya çevir, eksik aralığı genişlet, formülü komşularla eşitle) ve önerinin ne yapacağını önceden yazar. **Yoksay** bulguyu kalıcı olarak gizler; yoksayılanlar dosyayla birlikte saklanır (**Yoksayılanları geri al** ile döner). Her kontrol **Ayarlar…**'dan kapatılabilir. Kitap değişince sonuçların eskidiğini söyleyen bir uyarı görünür; yeniden taramak için *Tara*'ya basın.

## Paylaşım Temizleyici: kişisel verileri maskeleme

**Gözden Geçir → Denetim → Paylaşım Temizleyici**, dosyayı başkasına göndermeden önce içindeki kişisel verileri bulmanıza ve gizlemenize yardım eder. *Yardımcı araçtır:* bulduklarını siz onaylarsınız, KVKK ya da başka bir mevzuata uygunluğu garanti etmez. **Verileriniz bilgisayarınızdan çıkmaz.**

- **Neleri bulur:** T.C. kimlik no, vergi no, IBAN, telefon, e-posta, kredi kartı no (sağlama kurallarıyla doğrulanır; rastgele bir sayıya yanlış alarm vermemesi için) ve **ad-soyad** (yalnız başlığı *Ad Soyad*, *Müşteri Adı* gibi olan sütunların altı; öneridir). 10 haneli çıplak sayı telefon ya da vergi no olabilir; *belirsiz* diye işaretlenir.
- **Nerelere bakar:** tüm sayfalar, **gizli satır/sütun/sayfa**, hücre notları ve not yazarları, formüllerin içindeki metinler, tanımlı adlar, sayfa adları, grafik başlıkları ve seri adları, veri doğrulama listeleri ve iletileri. Gizli yerdekiler kırmızı *gizli …* notuyla belirtilir. **Resimlerin içeriği taranamaz**; resim varsa uyarılır, elle bakmanız gerekir.
- **Ne yapar:** her veri türü için *Maskele* (örn. `12*******34`), *Sil* ya da *Bırak* seçersiniz; **Maske…** ile açık kalacak karakter sayısını değiştirirsiniz. Listede tek tek kutuyu kaldırarak bir bulguyu dışarıda bırakabilir, tıklayarak hücreye gidebilirsiniz.
- **Özgün dosya değişmez.** **Temiz kopya oluştur…** yeni bir dosyaya yazar; özgün dosyanın üzerine yazmaya izin vermez. Temiz kopyada özgün dosyanın yazar/son kaydeden gibi meta verisi, üst-alt bilgisi, geri al geçmişi ve kurtarma kopyası bulunmaz. Yazdıktan sonra dosyanın tüm parçalarında özgün değerin kalmadığı **otomatik doğrulanır**; bulunursa dosya silinir ve uyarılır.
- **Formüller:** maskelenen hücreye bağlı formüller korunur ve maskeli değerle yeniden hesaplanır. Sonucu değişen ya da hataya dönen formüller kaydetmeden önce listelenir; isterseniz özgün sonuçlarıyla *değere çevirebilirsiniz*; ancak sonuç kişisel veriden türetilmişse (kimlik no + 1 gibi) yine bilgi taşır, yalnız toplam/uzunluk gibi sonuçlar için işaretleyin.

## Ne yapmak istiyorsun? (Asistan)

Bir tablonun içinde bir hücre seçip **Formüller → Ne yapmak istiyorsun?** (ya da `Alt+Q`) deyin ve isteğinizi Türkçe yazın: *“Bölgeye göre toplam satış”*. {APP_NAME} tablonun başlıklarına ve değerlerine bakıp yapacağını **önizleme** olarak gösterir (formül ve yazılacak yer); **Uygula** deyince yazar, `Ctrl+Z` ile geri alınır. Hiçbir şey sormadan yazmaz.

- **Tek değer:** *Satış toplamı*, *tutar ortalaması*, *en yüksek tutar*, *kaç kayıt var*; koşullu: *Kuzey bölgesinin toplam satışı*, *Kuzey ve çay için adet toplamı*, *1000'den büyük satış sayısı*.
- **Gruplama (Özet Tablo):** *Bölgeye göre toplam satış*, *bölge ve ürüne göre ortalama tutar*, *her ürün için kaç adet var*.
- **Listeleme:** *Tutarı 500'den büyük olanları listele*, *Güney bölgesindekileri göster*, *ortalamanın üstünde olanlar*; **en yüksek/en düşük N**: *en yüksek 5 satış*; **sıralama**: *tutara göre büyükten küçüğe sırala*; **benzersiz / tekrar eden**: *ürünlerin benzersiz listesi*, *tekrar eden müşteriler*.
- **Yeni sütun:** *toplamdaki payı (%)*, *değişim (%)*, *kümülatif toplam*.

Sütun adları büyük/küçük harf, Türkçe harf ve ek farkına bakmaz (`bölgeye` = *Bölge*, `satışların` = *Satış*); hücrelerdeki metin değerleri de (ör. *Kuzey*) tanınır. Cümleyi anlayamazsa **tahmin yürütmez**: nedenini, tablonun sütunlarını ve örnekleri söyler. Asistan tamamen bu bilgisayarda, kurallarla çalışır; yapay zekâ modeli ya da internet kullanmaz, bu yüzden yalnız yukarıdaki kalıpları anlar.

## Dinamik diziler (taşma)

Çok hücreli bir sonuç üreten formül, sonucunu **komşu hücrelere taşırır**: `=SIRALA(A1:B10;2;-1)` yalnız D1'e yazılır, sonuç D1:E10'u doldurur. Taşan hücreler formülün parçasıdır; onları ayrıca düzenlemezsiniz. Kaynak değişince taşma büyür/küçülür; `TOPLA(D1:D20)` gibi formüller taşan hücreleri okur.

- **Yeni işlevler:** `SIRALA` (SORT), `SIRALAÖLÇÜT` (SORTBY), `FİLTRE` (FILTER), `BENZERSİZ` (UNIQUE), `SIRALI` (SEQUENCE), `RASGDİZİ` (RANDARRAY), `AL` (TAKE), `BIRAK` (DROP), `DÜŞEYYIĞ` (VSTACK), `YATAYYIĞ` (HSTACK), `SÜTUNA` (TOCOL), `SATIRA` (TOROW), `SÜTUNSEÇ` (CHOOSECOLS), `SATIRSEÇ` (CHOOSEROWS), `GENİŞLET` (EXPAND), `DEVRİK_DÖNÜŞÜM` (TRANSPOSE) ve `LET` (adlı ara değerler: `=LET(x;TOPLA(B1:B9);x*2)`).
- **#TAŞMA!:** taşacak alanda dolu ya da birleşik bir hücre varsa (ya da alan sayfa sınırını aşarsa) formül `#TAŞMA!` verir; hücrenin üstüne gelince hangi hücrenin engellediği yazılır. Engeli kaldırınca formül kendiliğinden taşar. Taşan bir hücrenin üstüne yazarsanız da formül `#TAŞMA!` olur (geri alınca düzelir).
- **#HESAPLA!:** sonuç boş bir dizi (ör. `FİLTRE` koşula uyan satır bulamadı; üçüncü bağımsız değişkenle yerine bir değer verebilirsiniz).
- **Excel'e kaydederken** taşan formül eski tür dizi formülü (`{=…}`) olarak yazılır: Excel'de açılır ve değerler doğrudur, ancak alanı sabittir. `.ods`/`.csv`'ye değer olarak yazılır.

## Adlandırılmış aralıklar

**Formüller → Ad Tanımla** ya da Ad Kutusu'na ad yazarak seçimi adlandırın; `Ctrl+F3` **Ad Yöneticisi**'ni açar. Formüllerde `=TOPLA(Satışlar)` gibi kullanılır.

<!-- konu: bicimlendirme | Biçimlendirme -->
# Biçimlendirme

**Giriş** sekmesi: yazı tipi ve boyutu, `Ctrl+B` kalın, `Ctrl+I` italik, `Ctrl+U` altı çizili, `Ctrl+5` üstü çizili, dolgu ve yazı rengi, kenarlıklar, hizalama, girinti, **Metni Kaydır**, **Birleştir ve Ortala**.

- **Hücreleri Biçimlendir** (`Ctrl+1`): Sayı, Hizalama, Yazı Tipi, Kenarlık ve Dolgu sekmeleri. Yalnız değiştirdiğiniz alanlar seçili tüm hücrelere uygulanır.
- **Sayı biçimleri:** Genel, Sayı, Para Birimi, Yüzde, Tarih, Saat, Kesir, Bilimsel, Metin ve Özel. Kısayollar: `Ctrl+Shift+4` para, `Ctrl+Shift+5` yüzde, `Ctrl+Shift+1` binlik ayraçlı sayı. Özel biçim kodları Türkçe yazılır: ondalık ayraç `,`, binlik `.`; gün `g`, ay `a`, yıl `yyyy`, **saat `s`, dakika `d`, saniye `n`** (ör. `gg.aa.yyyy ss:dd:nn`), geçen süre `[s]:dd`. Tarih biçiminde `/` ayırıcı olarak `.` görünür (Türkçe Excel gibi).
- **Biçim Boyacısı:** kaynak hücreyi seçip fırçaya bir kez tıklayın (tek kullanım) ya da çift tıklayın (kalıcı); hedefi seçin. `Esc` bitirir.
- **Birleştirme:** birden çok hücre seçili iken Birleştir'e basılırsa yalnız sol üstteki değer kalır (uyarı verilir). Aynı düğme birleşimi geri çözer.
- **Metni Kaydır** açıkken satır yüksekliği içeriğe göre kendiliğinden artar; satır başlığına çift tıklayarak elle verilen yüksekliği otomatiğe döndürebilirsiniz.

<!-- konu: doldurma | Doldurma ve Seriler -->
# Doldurma ve Seriler

- Seçimin sağ alt köşesindeki **doldurma tutamacını** sürükleyin; seri devam eder: `1, 2, 3 …`, `Ocak, Şubat …`, `Pazartesi …`, `Ürün 1, Ürün 2 …`, `1. Çeyrek …`. Aşağı/sağa ve yukarı/sola çalışır.
- İki sayı seçip sürüklerseniz aradaki **adım** kullanılır; üç ve fazlasında doğrusal eğilim sürer.
- Tutamaca **çift tıklama** komşu sütundaki verinin sonuna kadar doldurur.
- **Ctrl basılıyken** sürüklemek varsayılanı tersine çevirir (Excel gibi): tek sayı `5` → `5, 6, 7 …` seri olur; `1, 2` ya da `Ocak` gibi seriler seri olmadan **kopyalanır**.
- Doldurmanın hemen sonrasında köşede beliren **Otomatik Doldurma Seçenekleri** düğmesi (▾) sonucu değiştirir: *Hücreleri Kopyala*, *Seriyi Doldur*, *Yalnızca Biçimleri Doldur* (içerik değişmez), *Biçimlendirmeden Doldur* (hedefin biçimi korunur). Başka bir işlem yapınca düğme kalkar. Seçim, doldurmayı geri alıp yeniden yapar (tek geri al adımı).
- Formüller doldurulurken başvurular göreli kayar.
- `Ctrl+D` üstteki hücreyi aşağıya, `Ctrl+R` soldaki hücreyi sağa **kopyalar**.
- Birleşik hücreler dolduruma katılamaz.

<!-- konu: satirsutun | Satır, Sütun ve Görünüm -->
# Satır, Sütun ve Görünüm

- **Boyut:** başlığın kenarını sürükleyin; seçili birden çok satır/sütun birlikte boyutlanır. Kenara çift tıklamak içeriğe göre sığdırır.
- **Ekle / Sil:** başlığa sağ tık ya da **Giriş → Hücreler**. Formüller, grafikler, adlar ve birleşimler otomatik kayar.
- **Gizle / Göster:** `Ctrl+9` satırı, `Ctrl+0` sütunu gizler; `Ctrl+Shift+9` / `Ctrl+Shift+0` gösterir.
- **Bölmeleri Dondur** (**Görünüm** sekmesi): etkin hücrenin üstündeki satırlar ve solundaki sütunlar kaydırmada sabit kalır. Üst Satırı / İlk Sütunu Dondur kısa yollardır.
- **Kılavuz çizgileri** Görünüm sekmesinden gösterilir/gizlenir.
- **Yakınlaştırma:** sağ alttaki çubuk ya da `Ctrl` + fare tekerleği.
- **Sayfalar:** `Ctrl+PgDown` / `Ctrl+PgUp` sayfalar arasında gezer; sekmeye sağ tıklayarak yeniden adlandırın, renk verin, silin.

<!-- konu: siralafiltre | Sırala, Filtre, Bul ve Değiştir -->
# Sırala, Filtre, Bul ve Değiştir

## Sırala

**Veri → Sırala** ya da A→Z / Z→A düğmeleri. Sıralama **Türkçe alfabeye** göre yapılır (ç, ğ, ı, ö, ş, ü doğru yerlerinde). **Özel Sırala** ile birden çok düzey tanımlanır. Sıralarken formüller kopyalamadaki gibi kayar; yalnız görünen satırlar sıralanır.

## Filtre

`Ctrl+Shift+L` seçime (tek hücreyse bitişik veri bloğuna) filtre ekler/kaldırır. Başlıktaki oku tıklayıp değer, metin, sayı ya da renk koşuluyla süzün. `Ctrl+Alt+L` koşulları değişen veriye göre yeniden uygular. Süzülen satırlar silinmez, yalnız gizlenir; durum çubuğundaki özet gizli satırları saymaz.

## Bul ve Değiştir

`Ctrl+F` bulur, `Ctrl+H` değiştirir. `Shift+F4` sonrakini, `Ctrl+Shift+F4` öncekini bulur (pencere kapalıyken de). Arama Türkçe büyük/küçük harf kurallarını bilir (`I`/`ı`, `İ`/`i`).

## Özet Tablo

**Ekle → Tablolar → Özet Tablo** büyük bir listeyi satır/sütun başına özetler (ör. bölgeye göre toplam satış).

1. Başlıklı veri aralığını seçin (tek hücre seçerseniz çevresindeki veri bloğu alınır) ve Özet Tablo'ya tıklayın.
2. **Satırlar** ve isteğe bağlı **Sütunlar** alanını, en çok üç **Değer** alanını ve işlevini seçin: *Toplam*, *Sayı*, *Ortalama*, *Maks*, *Min*.
3. Hedef: yeni sayfa ya da bu sayfada bir hücre. *Genel Toplam* satırı/sütunu isteğe bağlıdır.

Gruplama Türkçe harf kurallarıyla büyük/küçük harfe duyarsızdır (`Çay` = `ÇAY`); boş değerler `(boş)` olarak gruplanır. Toplam/Ortalama/Maks/Min yalnız sayıları katar, Sayı boş olmayanları sayar; kaynakta hata değeri varsa o hücrenin sonucu o hatadır. İşlem tek geri al adımıdır.

**Önemli:** Özet tablo bir **anlık görüntüdür** — kaynak veri değişince kendiliğinden güncellenmez (yeniden oluşturun) ve .xlsx'e düz değerler olarak kaydedilir.

<!-- konu: veriaraclari | Veri Doğrulama, Koşullu Biçim, Notlar -->
# Veri Doğrulama, Koşullu Biçim ve Notlar

- **Veri Doğrulama** (**Veri** sekmesi): hücreye girilebilecekleri sınırlayın (liste, sayı, tarih, metin uzunluğu…); hatalı girişte uyarı iletisi görünür, liste doğrulamasında hücrede açılır ok çıkar.
- **Koşullu Biçimlendirme** (**Giriş → Stiller**): değere göre renklendirme (büyüktür, arasında, yinelenen, en yüksek/en düşük, ortalamanın üstü, renk ölçekleri, veri çubukları, formüle dayalı kurallar). **Kuralları Yönet** ile sıra ve kapsam düzenlenir.
- **Notlar:** `Shift+F2` hücreye not ekler/düzenler; notlu hücrelerin köşesinde işaret görünür. **Gözden Geçir** sekmesinden silinir.
- **Yazım denetimi** (`F7`, **Gözden Geçir** sekmesi): Windows'un Türkçe yazım denetimini kullanır; metniniz bu bilgisayardan çıkmaz. Birkaç hücre seçiliyse yalnız onlar, tek hücre seçiliyse tüm sayfa sayfanın başından itibaren denetlenir. Yalnız **sabit metin** hücreleri denetlenir (formüller, sayılar ve tarihler denetlenmez). Yanlış sözcük için öneri listesinden seçip **Değiştir** / **Tümünü Değiştir**, ya da **Yoksay** / **Tümünü Yoksay**; her düzeltme ayrı bir geri al adımıdır. Windows'ta Türkçe yazma bileşeni yüklü değilse denetim açılmaz ve nasıl ekleneceği söylenir.

<!-- konu: grafikler | Grafikler ve Resimler -->
# Grafikler ve Resimler

## Grafik ekleme

1. Başlıklarıyla birlikte veriyi seçin (tek hücre seçerseniz çevresindeki veri bloğu alınır).
2. **Ekle** sekmesinde grafik türünü seçin: Sütun, Çubuk, Çizgi, Pasta (ve Halka), Alan, Dağılım. Oklu düğmelerde yığılmış ve %100 yığılmış seçenekler vardır.

Grafik görünen alanın ortasına yerleşir. {APP_NAME} seçimden **serileri kendisi tahmin eder**: ilk sütun/satır metin ya da tarihse kategori, ilk satır metinse seri adı olur; küçük olan eksen seri sayılır. Tahmin yanlışsa **Satır/Sütun Değiştir** ya da **Veriyi Seç** kullanın. Seçimde çizilebilir sayı yoksa uyarı verilir.

## Düzenleme

- **Seçmek** için tıklayın; **taşımak** için sürükleyin (`Shift` yatay/dikey kilitler); **boyutlandırmak** için kenar ve köşe tutamaçlarını sürükleyin.
- Klavye: ok tuşları 1 piksel, `Ctrl` + ok 10 piksel taşır; `Delete` siler; `Esc` seçimi bırakır; `Ctrl+C` / `Ctrl+X` / `Ctrl+V` kopyalar, keser, yapıştırır (etkin hücreye).
- Sağ tık menüsü: Kes, Kopyala, Sil, Öne Getir, Arkaya Gönder, Veriyi Seç, Grafik Türünü Değiştir, Grafik Ayarları.
- Grafiğin verisi değiştiğinde grafik **canlı güncellenir**; satır ya da sütun eklerken/silerken grafik başvuruları da kayar.

## Resim ekleme

**Ekle → Resim…** ile bir resim dosyası (PNG, JPEG, GIF, BMP; en çok 25 MB) seçin. Resim görünen alanın ortasına, doğal boyutunda (en çok 600 piksel genişlik) eklenir. Grafiklerdeki gibi taşınır, boyutlandırılır (köşeden sürüklerken oran korunur, `Shift` oranı serbest bırakır), `Delete` ile silinir, kopyalanıp yapıştırılır ve sağ tık menüsüyle öne/arkaya getirilir. Resim kırpma, döndürme ve parlaklık ayarı yoktur.

**Excel'de değiştirilmiş grafikler:** Excel'de bir grafiğe eğilim çizgisi, ikincil eksen, birleşik grafik, gradyan/desen dolgusu, hata çubukları, logaritmik eksen, veri etiketi ayrıntıları, düzgünleştirilmiş çizgi gibi {APP_NAME}'in desteklemediği öğeler eklenmişse, dosyayı açarken **hangi grafikte (ve hangi sayfada) hangi öğelerin olduğu** uyarı çubuğunda yazılır ve kaydederken ayrıca sorulur; kaydederseniz bu öğeler dosyadan çıkar. Dosyayı daha önce {APP_NAME} kaydetmişse yazı boyutu, tema rengi, çubuk aralığı gibi **biçim** değişiklikleri de aynı şekilde bildirilir. Excel'de hiçbir şey değiştirmeden aç-kaydet yapılmış dosyada uyarı çıkmaz.

**Başka çalışma kitabına kopyalama:** grafik ve resim aynı kitabın başka sayfasına kopyalanıp kesilip yapıştırılabilir. **Başka bir kitaba** yalnız **resim** yapıştırılır (kopya olarak; "kes" bile kaynağı silmez). Grafik başka kitaba yapıştırılamaz, çünkü verisi kendi kitabındaki sayfalara bağlıdır; önce verisini o kitaba taşıyıp grafiği orada oluşturun.

## Grafik sekmesi

Bir grafik seçiliyken beliren **Grafik** sekmesinde: tür ve veri değiştirme, başlık / gösterge / eksen başlıkları / veri etiketleri açma-kapama, renk şemaları ve öne/arkaya getirme bulunur. Çift tıklama ya da **Grafik Ayarları** ayrıntılı pencereyi açar (başlıklar, eksen en küçük/en büyük değerleri, her serinin adı, değer aralığı, kategorisi ve rengi). Aralıklar `Sayfa1!$B$2:$B$5` biçiminde yazılır.

<!-- konu: dosyalar | Dosyalar, Yazdırma ve Kurtarma -->
# Dosyalar, Yazdırma ve Kurtarma

## Açma ve kaydetme

- `Ctrl+N` yeni, `Ctrl+O` aç, `Ctrl+S` kaydet, `Ctrl+Shift+S` ya da `F12` farklı kaydet. Dosyayı komut satırından ya da Dosya Gezgini'nden de açabilirsiniz.
- Biçimler: **.xlsx** (asıl biçim), **.ods** (OpenDocument; aç/kaydet), **.xls** (eski Excel; yalnız okunur) ve **.csv**. `.ods` dosyasında sayfalar, değerler, formüller, birleşim, sütun genişliği/satır yüksekliği/gizleme, hücre biçimi ve temel sayı biçimleri (sayı, binlik, yüzde, para, tarih/saat, metin) taşınır; **grafik, resim, koşullu biçim, veri doğrulama, notlar, filtre, tanımlı adlar ve sayfa yapısı** `.ods`ye yazılmaz/okunmaz (dosyada varsa pencerenin üstündeki uyarı çubuğu söyler, kaydederken sorulur). `.xls` açılınca biçim, birleşim, sütun genişliği, not ve dondurma gelir; **formüller okunamaz** (hücreler son hesaplanan değerleriyle açılır), grafik/resim/makro/koşullu biçim/veri doğrulama/tanımlı adlar okunmaz — pencerenin üstündeki uyarı çubuğu bunu söyler. Kaydederken yeni bir **.xlsx** dosyası oluşturulur (özgün .xls'e dokunulmaz). CSV açarken kodlama (UTF-8 / Windows-1254) ve ayırıcı otomatik tanınır, bir **önizleme** penceresi görürsünüz; "metin olarak aç" seçeneği vardır. Bilgi kaybettirecek alanlar **otomatik metin kalır**: baştaki sıfırlı sayılar (`00123`), 11 haneli (TC kimlik no) ve 15 haneden uzun sayılar, IBAN, `1-2` / `3/4` gibi tarihe benzeyen kodlar. Tam tarihler (`01/02/2024`) ve normal sayılar çevrilmeye devam eder. Önizleme penceresinde ayrıca **sütun türü** (Genel / Metin / Sayı-tarih çevir), **ondalık ayırıcı** (Türkçe virgül ya da İngilizce nokta) seçebilir ve otomatik korumayı kapatabilirsiniz.
- Kayıt güvenlidir: önce geçici dosyaya yazılır, sonra yerine konur; kayıt yarıda kesilirse özgün dosya bozulmaz.
- **Grafikler ve resimler** .xlsx dosyasına kaydedilir ve Excel'de açıldığında grafik/resim olarak görünür. Excel'de hazırlanmış dosyalarda sütun, çubuk, çizgi, pasta, halka, alan ve dağılım grafikleri okunur; **3B, radar, borsa, kabarcık** gibi türler, ikincil eksenler ve birleşik grafikler desteklenmez.
- Açılan dosyada {APP_NAME}'in korumadığı bir öğe varsa (ör. pivot tablo, şekil, makro, desteklenmeyen grafik türü) pencerenin üstünde **uyarı çubuğu** çıkar ve kaydederken ayrıca sorulur; böylece sessizce veri kaybetmezsiniz. Excel'de hazırlanmış grafikli dosyalarda "grafikler uyarlandı" bilgisi görürsünüz: grafik açılır, ancak Excel'e özgü süslemeler (gradyan, eğilim çizgisi vb.) kaydedince kaybolabilir.

## Google Drive ve OneDrive

- Bilgisayarınızda **Google Drive** ya da **OneDrive** masaüstü uygulaması kuruluysa Dosya menüsünde *Google Drive'dan Aç…*, *Google Drive'a Kaydet…* (ve OneDrive karşılıkları) görünür. {APP_NAME} hesabınıza, şifrenize ya da buluta **hiç bağlanmaz**; dosyayı eşitleme klasörüne yazar, gerisini sizin Drive/OneDrive uygulamanız yapar.
- Açık dosya başka yerde (web, başka bilgisayar) değişirse fark edilir: sizin kaydedilmemiş değişikliğiniz yoksa yeni sürüm kendiliğinden yüklenir; varsa **Onların Sürümünü Yükle**, **Benimkini Koru** ya da **Benimkini Ayrı Kaydet** seçeneklerini görürsünüz.
- `.gsheet` gibi Google biçimli dosyaların içeriği bilgisayarda bulunmaz, açılamaz; tarayıcıda Dosya → İndir → Microsoft Excel (.xlsx) ile indirip burada açın.

## Parola ile koruma

- **Dosya → Parola Belirle…** çalışma kitabını parolayla şifreler (Excel'in *Parolayla Şifrele*si ile aynı biçim; Excel'de de açılır). Parola iki kez sorulur; boş bırakırsanız parola kaldırılır. Parola **bir sonraki kayıtta** uygulanır.
- Parolalı .xlsx açılırken parola sorulur; yanlışsa yeniden sorulur. Kaydedince dosya aynı parolayla yeniden şifrelenir.
- **Parolayı unutursanız dosya açılamaz** ({APP_NAME}'in de kurtarma yolu yoktur). Parola dosyaya, ayarlara ya da son dosyalar listesine yazılmaz; yalnız pencere açıkken bellekte durur.
- Güvenlik gereği parolalı belgeler için **otomatik kurtarma kopyası yazılmaz** (düz kopya diskte kalmasın); sık kaydedin.
- Parolalı **.xls** dosyaları açılamaz.

## Otomatik kayıt ve kurtarma

Çalışırken her 2 dakikada bir **kurtarma kopyası** yazılır; özgün dosyanıza dokunulmaz. Uygulama beklenmedik kapanırsa bir sonraki açılışta kurtarma önerilir.

## Yazdırma ve PDF

**Sayfa Düzeni** sekmesi: kenar boşlukları, yönlendirme, kâğıt boyutu, yazdırma alanı, başlıkları yazdır, ölçek, genişliği ve/veya yüksekliği tek sayfaya sığdır, sayfa sırası. `Ctrl+P` yazdırır, **Dosya → Yazdırma Önizleme** sonucu gösterir; etkin sayfa ya da tüm sayfalar **PDF** olarak dışa aktarılabilir.

**Grafik ve resimler** de yazdırılır ve PDF'e girer. Grafikler vektör olarak çizilir (büyütünce bulanıklaşmaz). Yazdırma alanı ayarlamadıysanız alan, hücreler ile grafik/resimlerin kapladığı yeri birlikte kapsar; sayfada yalnız grafik olsa bile basılır. Bir grafik sayfa sınırına denk gelirse (Excel'deki gibi) iki sayfaya bölünerek basılır; yazdırma alanı ayarladıysanız alanın dışında kalan kısmı basılmaz.

### Sayfa sınırları ve sayfa sonları
- **Görünüm → Sayfa Sonlarını Göster** ekranda sayfaların nerede bölüneceğini gösterir: **kesikli gri çizgi** otomatik sayfa sınırı, **düz koyu çizgi** sizin eklediğiniz sayfa sonudur. Çizgiler yazdırma alanı boyunca uzanır; sayfa boyutunu, kenar boşluklarını, ölçeği ya da satır/sütun boyutunu değiştirince kendiliğinden yenilenir.
- **Sayfa Düzeni → Kesmeler → Sayfa Sonu Ekle:** etkin hücrenin **üstüne ve soluna** sayfa sonu koyar (A sütunundaysanız yalnız yatay, 1. satırdaysanız yalnız dikey; A1'de eklenemez). **Sayfa Sonunu Kaldır** etkin hücrenin üstündeki/solundaki sonu kaldırır, **Tüm Sayfa Sonlarını Sıfırla** hepsini siler. Hepsi `Ctrl+Z` ile geri alınır.
- Satır/sütun ekleyip sildiğinizde sayfa sonları, yazdırma alanı ve yinelenen başlık satırları birlikte kayar.
- Bir sayfa sonu gizli bir satır/sütuna (ör. filtre yüzünden) denk gelirse, sonraki **görünür** satır/sütunda başlar.
- **Sığdır** seçeneklerinden biri açıkken el ile sayfa sonları yok sayılır (Excel gibi); çizgiler de gösterilmez.
- **Sayfa Düzeni → Sığdır:** *Genişliği tek sayfaya sığdır* ve *Yüksekliği tek sayfaya sığdır* ayrı ayrı ya da birlikte işaretlenebilir (ölçek gerektiği kadar küçülür). **Sayfa Sırası** çok sayfalı çıktıda önce aşağı mı önce sağa mı gidileceğini belirler; Sayfa Yapısı penceresinde de vardır.
- Sayfa sonları ve sığdır ayarları `.xlsx` dosyasına yazılır; Excel'de hazırlanmış dosyadaki el ile sayfa sonları okunur.

## Şablondan Yeni: hazır tablo düzenleri

**Dosya → Şablondan Yeni…** ne yapmak istediğinizi yazmanızla başlar (ör. *stok takibi yapmak istiyorum*). {APP_NAME} yazdıklarınızı yerelde, anahtar kelimelerle bir şablona eşler (yapay zekâ ve internet kullanılmaz); yazmak istemezseniz kategori düğmelerinden ya da listeden seçebilirsiniz. Sonra birkaç evet/hayır soru sorulur (ör. *birden fazla deponuz var mı?*); emin değilseniz **Emin değilim, siz seçin** işaretlenir ve önerilen cevap kullanılır. Son adımda oluşacak sayfalar ve ilk satırları önizlenir; **Oluştur** yeni bir pencerede sıradan bir kitap açar: başlıklar, biçimler, açılır listeler, veri doğrulama ve hesaplanan sütunlar hazırdır, her şeyi istediğiniz gibi değiştirebilirsiniz. Örnek veriler isteğe bağlıdır.

- Şablonla üretilen dosyada, şablon bilgisi **çok gizli `_tabcel` sayfasında** saklanır (Excel'in Göster listesinde bile çıkmaz). Dosyayı Excel'de düzenleseniz de tablo çalışır; sütunlar silinir ya da başlıkları değişirse {APP_NAME} bunu açılışta fark eder ve bilgi çubuğunda uyarır.
- **Şablonlar…** düğmesi yüklenen şablonları ve varsa hatalı dosyaları (neden yazılı) gösterir. Kendi şablonlarınızı kullanıcı klasörüne (**Klasörü Aç**) JSON olarak koyabilirsiniz; aynı adlı bir yerleşik şablon varsa ikisi de listelenir.
- Oluşturulan sayfalarda hesaplanan sütunların formülleri ilk 200–1.000 satıra (şablona göre), açılır liste ve doğrulama ilk 20.000 satıra uygulanır; hesaplanan sütunların altındaki satırlara formül yazılmaz.
- **Hazır şablonlar:** *Stok takibi* (ürünler, giriş/çıkış, stok durumu, varyant [stok adetli, matris girişli]/depo/cari isteğe bağlı) · *Cari hesap takibi* (cari kartlar, borç/alacak hareketleri, bakiye) · *Apartman / site aidat takibi* (daireler, ödemeler, kalan borç; ek ödeme ve basit gecikme zammı isteğe bağlı) · *Teklif hazırlama* (müşteriler, teklifler, kalemler; KDV, iskonto ve toplamı yazıyla gösterme isteğe bağlı) · *Çek ve senet takibi* (vade, kalan gün, vade uyarısı; isteğe bağlı iş günü vadesi) · *Not çizelgesi* (öğrenciler, notlar, ağırlıklı ortalama, geçti/kaldı, devamsızlık).
- *Toplamı yazıyla gösterme* (Teklif) ve *iş günü vadesi* (Çek-senet) {APP_NAME}'e özgü işlevleri kullanır: dosyayı .xlsx olarak kaydedince Excel'de çalışmazlar (kaydederken uyarılırsınız). Resmî tatil verisi 2024–2028'i kapsar; dini bayram tarihleri henüz doğrulanmadı.
- Apartman aidatındaki gecikme zammı basit bir hesaptır (kalan borç × aylık oran), yasal faiz hesabı değildir; oranı kendiniz belirlersiniz.
- *Paylaşım Temizleyici* şablon bilgisindeki kişisel verileri de tarar.

### Kendi şablonunuzu hazırlama (Şablon Düzenleyici)
**Dosya → Şablondan Yeni… → Şablonlar…** penceresinde:
- **Yeni şablon…** iki sütunlu bir başlangıç şablonu açar; **Kopyasını düzenle…** seçili şablonun (yerleşik de olur) kendi adınıza kopyasını alır — yerleşik şablonlar değişmez; **Düzenle…** ve **Sil…** yalnız sizin şablonlarınız içindir.
- **Dosya → Kitaptan Şablon Oluştur…** açık çalışma kitabındaki sayfalardan şablon üretir: ilk satır başlık olur, sütun türleri verilerden tahmin edilir (tarih, sayı, para, yüzde, evet/hayır, kısa liste, T.C./vergi no/IBAN/telefon/e-posta), yalnız aynı satırdaki hücrelere bakan formüller hesaplanan sütun olur (dönüştürülemeyenler için uyarı çıkar). İsterseniz ilk 20 satır örnek veri olarak eklenir. Sonuç düzenleyicide açılır; gözden geçirip kaydedersiniz.
- **Düzenleyici:** *Genel* (ad, kategori, açıklama, sihirbazın şablonu bulması için anahtar kelimeler), *Sorular* (en çok 7 evet/hayır; bir cevaba bağlı sütun/modül için *Koşul (bayrak)* kutusuna soru kimliğini yazın), *Modüller* (her biri bir sayfa; sütunlar: tür, zorunlu, benzersiz, en az/en çok/uzunluk, seçenekler, bağlantı `modül.alan`, hesaplanan formül `=[@miktar]*[@fiyat]`; kurallar: `DOĞRU` = geçerli, *Ne zaman*, ileti, şiddet; modül kimliği değişince bağlantılar ve formüller güncellenir; varyant matrisi için matris alanları), *Ayarlar*, *Nasıl kullanılır*, *İleri (JSON)* (ham tanım).
- Tanım **her değişiklikte doğrulanır**; hatalar altta Türkçe, konumuyla listelenir ve düzeltilene kadar **Kaydet** kapalıdır. **Denetle (Tablo Sağlığı)** şablonu tüm cevap kombinasyonlarında üretip Tablo Sağlık Kontrolü'nden geçirir; sorun varsa kaydedilmez.
- Şablonlar `%APPDATA%\{APP_NAME}\sablonlar` klasörüne JSON olarak yazılır (geçici dosyaya yazıp yerine koyarak); aynı kimlik varsa üzerine yazmak için sorulur. Şablonu başkasına vermek için `akislar\` ve `moduller\` altındaki dosyaları kopyalamak yeter.

### Kayıt Formu (Veri → Kayıt Formu, `Ctrl+Alt+F`)
Şablonla üretilen tablolardaki her kayıt için otomatik bir form açılır; tabloyu elle doldurmak yerine alan alan girebilirsiniz.
- **Alanlar** sütun türüne göre gelir: metin kutusu, takvimli tarih (`gg.aa.yyyy`), açılır liste, yazdıkça süzülen bağlantı listesi (ör. ürün kodu), evet/hayır kutusu; hesaplanan alanlar yalnızca gösterilir. `*` zorunlu alandır.
- **Klavye:** `Enter` sonraki alana geçer (son alanda kaydeder), `Ctrl+Enter` kaydeder ve yeni kayda geçer, `Ctrl+PgDn` / `Ctrl+PgUp` sonraki / önceki kayıt, `Ctrl+F` kayıt arar (Türkçe harf duyarsız), `Esc` kapatır.
- **Kurallar tabloyla aynıdır:** zorunlu, benzersiz, sayı aralığı, T.C./vergi no/IBAN/telefon/e-posta ve açılır liste kuralları tablodaki veri doğrulamasıdır; ayrıca şablonun satır kuralları da denetlenir (ör. *stok eksiye düşemez*). Hata iletisi alanın altında kırmızı çıkar ve kayıt yapılmaz; *uyarı* düzeyindeki kurallarda onay sorulur.
- Form ayrı veri tutmaz: tablodaki satırı doğrudan okur ve yazar. Bir kaydın kaydedilmesi tek **Geri Al** adımıdır; tablodaki değişiklikler formda, formdaki kayıtlar tabloda anında görünür.
- **Örnek verileri temizle** şablonla gelen örnek kayıtları siler (kendi değiştirdiğiniz satırlara dokunmaz; geri alınabilir).
- Sütun başlıkları değiştirilmiş ya da silinmişse form kapanır; **Kayıt Formu**'nu açınca *Sütunları yeniden eşlemek* isteyip istemediğiniz sorulur ve eksik başlıklar tablodaki başlıklarla eşlenir.
- **Tablo Sağlığı** artık *Şablon kural ihlali* de bulur: tabloya yapıştırılan ya da elle yazılan, forma girilseydi kaydedilmeyecek kayıtlar. (Stok gibi başka tabloların toplamlarına bakan kurallar yalnızca form girişinde denetlenir.)
- **Barkod okuyucu:** USB barkod okuyucu klavye gibi çalışır (yazar, sonunda `Enter` gönderir); özel sürücü gerekmez. `Ctrl+B` odağı barkod okutulacak alana taşır. *Stok hareketi* formunda **Ürün kodu** alanına barkod okutunca ürün kendiliğinden seçilir ve sonraki alana geçilir (baştaki sıfırlar önemlidir; ürün kodu okutmak da olur). *Ürünler* formunda kayıtlı bir barkod okutursanız o ürünün kaydına gidilir.
- Okutulan barkod hiçbir ürüne ait değilse alanın altında **Yeni ürün olarak ekle** düğmesi çıkar: Ürünler formu barkod dolu açılır, kaydedince hareket formuna dönülür (diğer alanlarınız korunur) ve yeni ürün seçili gelir.
- **Varyant matrisi (Matris giriş…):** *Varyantlar* gibi çeşit tablolarında (Stok takibi → çeşitleri var) formdaki **Matris giriş…** düğmesi beden × renk gibi iki boyutu tek ızgarada girmenizi sağlar. Ürünü seçin, satır (ör. `S, M, L`) ve sütun etiketlerini (ör. `Kırmızı, Mavi`) yazın, **Tabloyu kur**'a basıp adetleri doldurun (Excel'den kopyaladığınız bloğu `Ctrl+V` ile yapıştırabilirsiniz). **Kaydet**'te her dolu hücre ayrı bir kayıt olur; boş hücre yazılmaz. Ürünün kayıtlı çeşitleri ızgaraya otomatik gelir; değerini değiştirirseniz yeni satır açılmaz, mevcut kaydın adedi güncellenir (barkod gibi diğer alanlara dokunulmaz). Tüm kayıtlar form kurallarından geçer; tek ihlal bile varsa hiçbir şey yazılmaz. Matrisin tamamı tek **Geri Al** adımıdır.
- Yeni kayıt, hazır formüllerin bittiği satırın ötesine eklenirse hesaplanan sütunların formülleri forma kaydederken o satıra da yazılır.

<!-- konu: pano | Kopyala ve Yapıştır -->
# Kopyala ve Yapıştır

- `Ctrl+C`, `Ctrl+X`, `Ctrl+V` hücre içeriğini, biçimi ve formülü birlikte taşır. Kopyalanan formülün başvuruları göreli kayar; kesip yapıştırınca başvurular yeni yere uyar.
- Kopyalanan alan kesikli çerçeveyle gösterilir; `Esc` kaldırır.
- {APP_NAME} içinden Excel ya da Word'e yapıştırdığınızda tablo, sayı ve temel biçimler korunur; Excel, Word ve web sayfalarından gelen tablolar da hücrelere yerleşir. Dışarıdan yapıştırılan `=` ile başlayan metin formül olarak anlaşılır.
- **Excel ve Word ile biçim korunur** (gerçek Excel 16'da denendi): {APP_NAME}'ten kopyalanan tarih, para ve yüzde Excel'de **sayı + aynı biçimle** gelir, formüller formül olarak, kalın/renk/dolgu biçimiyle; Word'e tablo olarak, ekranda göründüğü metinle yapışır. Excel'den kopyalanan tablodaki tarih/yüzde/para değerleri sayı olarak ve biçimiyle (`gg.aa.yyyy`, `0,0%`, `#.##0,00`), kalın ve dolgu rengiyle yapışır. Excel'den yapıştırılan **formüller değer olarak** gelir (Excel panoya yalnız sonucu koyar); formüllü bloğu taşımak için dosyayı kaydedip açın.
- Kopyalanan veya kesilen hücreyi bir birleşimin içine kısmen yapıştırmak uyarıyla reddedilir.

<!-- konu: kisayollar | Klavye Kısayolları -->
# Klavye Kısayolları

| Kısayol | İşlev |
|---|---|
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` | Yeni / Aç / Kaydet |
| `Ctrl+Shift+S`, `F12` | Farklı Kaydet |
| `Ctrl+P` | Yazdır |
| `Ctrl+Z` / `Ctrl+Y` | Geri Al / Yinele |
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Kopyala / Kes / Yapıştır |
| `Ctrl+D` / `Ctrl+R` | Aşağı / Sağa doldur (kopyala) |
| `Ctrl+Enter` | Girişi tüm seçime uygula |
| `F2` | Hücreyi düzenle |
| `Alt+Enter` | Hücre içinde satır sonu |
| `F4` | Başvuruyu mutlak/göreli yap (formülde) |
| `Alt+=` | Otomatik Toplam |
| `Ctrl+B` / `Ctrl+I` / `Ctrl+U` | Kalın / İtalik / Altı çizili |
| `Ctrl+5` | Üstü çizili |
| `Ctrl+1` | Hücreleri Biçimlendir |
| `Ctrl+Shift+4` / `Ctrl+Shift+5` / `Ctrl+Shift+1` | Para / Yüzde / Binlik ayraçlı sayı |
| `Ctrl+F` / `Ctrl+H` | Bul / Değiştir |
| `Shift+F4` / `Ctrl+Shift+F4` | Sonrakini / Öncekini bul |
| `Ctrl+G`, `F5` | Git |
| `Ctrl+F3` | Ad Yöneticisi |
| `Ctrl+Shift+L` | Filtreyi aç/kapat |
| `Ctrl+Alt+L` | Filtreyi yeniden uygula |
| `Shift+F2` | Not ekle / düzenle |
| `F7` | Yazım denetimi |
| `Alt+Q` | Ne yapmak istiyorsun? (asistan) |
| `Ctrl+Alt+I` | Hesap İzleme panelini aç/kapat |
| `Ctrl+Alt+F` | Kayıt Formu (şablon tabloları) |
| `Ctrl+9` / `Ctrl+0` | Satırları / Sütunları gizle |
| `Ctrl+Shift+9` / `Ctrl+Shift+0` | Satırları / Sütunları göster |
| `Ctrl+Boşluk` / `Shift+Boşluk` | Sütunu / Satırı seç |
| `Ctrl+Home` / `Ctrl+End` | Sayfanın başına / sonuna git |
| `Ctrl+PgDown` / `Ctrl+PgUp` | Sonraki / Önceki sayfa |
| `Ctrl+F1` | Şeridi daralt / aç |
| `F1` | Yardım |
| `Delete` | İçeriği sil (grafik seçiliyken grafiği siler) |
| `Esc` | Girişi / kopyalama çerçevesini / grafik seçimini iptal et |

<!-- konu: farklar | Excel'den Farklar -->
# Excel'den Farklar

{APP_NAME} Excel davranışını esas alır; aşağıdakiler **bilerek** farklıdır ya da henüz yoktur.

- **`EĞİLİM`, `BÜYÜME`, `DOT`** yalnız tek bağımsız değişkenle çalışır. `LAMBDA` ailesi (`MAP`, `REDUCE`, `SCAN`, `MAKEARRAY`), `DAB` (VDB), `HÜCRE` ve `BİLGİ` yoktur.
- **`AİÇVERİMORANI` (XIRR)** köke Excel'den biraz daha sıkı yaklaşır (Excel yinelemeyi 10⁻⁸ doğrulukta keser); sonuçlar ilk 7–8 ondalıkta aynıdır. **`ANBD` (XNPV)** Excel gibi oran 0 ve altında `#SAYI!` verir.
- **Çok uzun sayı girişi:** Excel 15 anlamlı basamaktan sonrasını atar (`1234567890123456` → `1234567890123450`); {APP_NAME} sayıyı tam duyarlıkla tutar. Kimlik koruması (TC, IBAN) için bkz. "Akıllı giriş".
- **Kesir biçimi** (`# ?/?`, `# ??/??`): Excel gibi ardışık yaklaşım (sürekli kesir) kullanılır; az sayıda değerde Excel farklı bir kesir seçebilir (ör. `0,9` için `8/9`).
- **METNEÇEVİR** biçim argümanında Türkçe kod beklenir (`"gg.aa.yyyy"`); {APP_NAME} Excel'in aksine İngilizce kodu (`"dd.mm.yyyy"`) Türkçe kodlar çözümlenemezse yine kabul eder.
- **DATEDIF "YD"** ve 1900 yılı Şubat'ındaki sahte 29 Şubat çevresinde Excel'in kendi hatalı davranışı bazı uç tarihlerde birebir taklit edilmez.
- **Hata açıklamaları:** Excel hatalı hücrede yeşil üçgen ve "Hatayı İzle" okları gösterir; {APP_NAME} açıklamayı ipucunda ve durum çubuğunda yazar (ok çizimi yok). Açıklama cümleleri {APP_NAME}'e özgüdür, Excel'in iletilerinin çevirisi değildir.
- **Taşma yalnız hesaplanmış dizilerde:** `=SIRALA(…)`, `=A1:A3*2` gibi hesaplanmış dizi sonuçları taşar; düz aralık başvurusu (`=A1:A3`) taşmaz, tek değer (örtük kesişim) verir (Excel 365 bu durumda da taşırır). Taşan formül Excel'e eski tür dizi formülü olarak kaydedilir (alan sabit). `LAMBDA`, `MAP`, `REDUCE`, `BYROW`, `METİNBÖL`, `SATIRSAR` gibi diğer dinamik dizi işlevleri henüz yoktur; `@` işleci ve `A1#` taşma başvurusu da yoktur.
- **Pivot tablo, Tablo nesnesi, makro (VBA), Solver, .xls ve .ods** henüz desteklenmez.
- **Excel'de eklenen eğilim çizgisi, ikincil eksen vb. korunmaz** (açılışta hangi grafikte olduğu bildirilir, kaydederken sorulur).
- **Grafik başka çalışma kitabına yapıştırılamaz** (Excel yapıştırıp özgün kitaba bağlı kalır); resim yapıştırılır.
- **Grafikler:** yalnız 7 temel tür vardır; ikincil eksen, eğilim çizgisi, hata çubukları ve 3B yoktur. Grafikler ve resimler dosyada ayrı katmanlarda saklandığından, karışık üst üste sıralama (bir resmin grafiğin üstünde olması gibi) kaydedip açınca grafikler altta, resimler üstte olacak biçimde yeniden dizilebilir.
- **Bölmeleri Dondur** sayfanın başından dondurur (Excel kaydırılmış pencerenin üstünden dondurur).
- Var olmayan sayfaya başvuran formül reddedilir ve düzenleme açık kalır.
- Biçim Boyacısı sayfa değişince biter (Excel sayfalar arasında da boyar) ve birleşimi/sütun genişliğini taşımaz.
- Dışarıdan yapıştırılan metindeki tarihler tarih olarak anlaşılmaz (elle yazarken anlaşılır).
- Birleşik hücrelerin bulunduğu alana doldurma yapılamaz.
- **Özet Tablo** canlı değildir: bir **anlık görüntü** olarak düz hücrelere yazılır (kaynak değişince yenilenmez, Excel'e Özet Tablo nesnesi olarak kaydedilmez); filtre/dilimleyici, hesaplanmış alan, gruplama (tarih/aralık) ve tek değer alanından fazla işlev yoktur.
- **.xls** yalnız okunur ve formüller değere döner (xlrd formül metnini vermez); .xls olarak kaydedilemez, `.xlsx` önerilir. Pivot tablo sonraki sürümdedir. **.ods** dosyasında sayı biçimlerinin yalnız temel kodları taşınır (renkli/koşullu bölümlü kodlar Genel olur; kaydederken uyarılır); parola .ods'de desteklenmez.
- **Yazım denetimi** sayfanın başından başlar (Excel etkin hücreden başlar, sonda baştan devam edilsin mi diye sorar); yalnız sabit metin hücreleri denetlenir, özel sözlüğe ekleme ve otomatik düzeltme yoktur.
- Excel'de hazırlanmış dosyada "2 sayfa genişliğine × 3 sayfa yüksekliğine sığdır" gibi çok sayfalı sığdırma tek sayfaya sığdırma olarak uygulanır (açılışta bilgi verilir).
- **Sayfa Sonu Önizleme** görünümü (mavi sınırı sürükleyerek sayfa sonu koyma) yoktur; sayfa sonları yalnız Kesmeler menüsünden eklenir. Sayfa sonu çizgilerini göstermek dosyaya yazılmaz (Excel'de de ayrı bir görünüm ayarıdır), ama el ile sayfa sonları yazılır. Üst/alt bilgi ve sayfa numarası henüz yoktur.
- Elle yazılan bazı nadir girdiler Excel'den farklı anlaşılır: `$5` (Excel Türkçe ayarında metin bırakır, burada para birimli sayı olur), tek haneli yıllı `1/2/3`, `1/13`, `1-2-3`, `12:3`, `25:00` ve `- 5` (Excel sayıya/tarihe çevirir, burada metin kalır).
- `YAZIYLA` ve `TCKİMLİKDOĞRULA` işlevleri yalnız bu uygulamaya özgüdür (Excel'de karşılığı yok); dosyada `TR_NUMBERTOWORDS` ve `TR_VALIDATE_TCKN` adıyla saklanır, Excel'de `#AD?` görünür.
- **Gizli sayfa:** Excel'de gizli olan sayfa {APP_NAME}'te sekme olarak görünür (gizleme/gösterme komutu yoktur); kaydedince dosyada yine gizli kalır. *Çok gizli* sayfalar (Excel'in Göster listesinde bile çıkmayanlar) dosyada çok gizli kalır. *Paylaşım Temizleyici* gizli sayfadaki ve `_tabcel` şablon bilgisindeki kişisel verileri ayrıca bildirir.
- **Paylaşım Temizleyici** Excel'de yoktur. Üst/alt bilgi {APP_NAME}'te saklanmadığı için temiz kopyada hiç bulunmaz; resimlerin içi taranamaz.
- **Şablondan Yeni** Excel'de yoktur. Üretilen dosya sıradan bir .xlsx'tir; şablon bilgisi çok gizli `_tabcel` sayfasındadır (Excel'de düzenlerseniz uyuşmazlığı {APP_NAME} açılışta uyarır). Açılır listeler boş satırları da içerebilir; doğrulama yapıştırılan veriyi denetlemez (Excel'de de böyledir).
- Veri bulutta tutulmaz; bulut yapay zekâ, hesap girişi ve telemetri yoktur.

<!-- konu: sorunlar | Sık Sorulanlar ve Sorun Giderme -->
# Sık Sorulanlar ve Sorun Giderme

**Hücrede `####` görüyorum.** Sütun, sayıyı ya da tarihi göstermeye yetmeyecek kadar dar. Sütun başlığının kenarına çift tıklayın.

**Formülüm `#AD?` veriyor.** Fonksiyon adı yanlış yazılmış olabilir. Adı yazmaya başlayınca çıkan öneri listesinden seçin; ayırıcının `,` değil `;` olduğundan emin olun.

**Yazdığım sayı metin gibi sola yaslanıyor.** Hücre Metin biçimindedir ya da girdi sayı olarak anlaşılamamıştır (ör. `1,234.5` yerine `1.234,5` yazın). Biçimi Genel yapıp yeniden girin.

**Baştaki sıfırlar (`00123`) kayboluyor.** Hücreyi önce **Metin** biçimine alın, sonra yazın. CSV dosyalarında baştaki sıfırlı alanlar zaten metin kalır; başka bir sütunu metin açmak için "metin olarak aç" seçeneğini kullanın.

**Grafik oluşmadı.** Seçimde en az bir sayısal sütun/satır olmalı. Başlıklarla birlikte seçmeyi deneyin.

**Dosya kaydedilirken uyarı çıktı.** Açtığınız dosyada {APP_NAME}'in desteklemediği bir öğe var; kaydederseniz o öğe kaybolur. Özgün dosyayı yedek olarak saklayın ve "Farklı Kaydet" ile yeni bir ad verin.

**Uygulama beklenmedik kapandı.** Yeniden açtığınızda kurtarma önerisi çıkar; son 2 dakikaya kadar olan çalışmanız geri getirilebilir.

**Çok büyük dosyada yavaşlık.** Yüz binlerce hücreli dosyalarda sıralama birkaç saniye sürebilir; bu beklenen davranıştır. Başka ağır uygulamaları kapatmak yardımcı olur.
