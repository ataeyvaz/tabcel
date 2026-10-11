# Tabcel — Proje Planı

> **Ad geçici:** "Tabcel" çalışma adıdır, değişebilir. Kod bu yüzden görünen adı tek bir sabitten okur (bkz. `CLAUDE.md` → Kesin kurallar 1).

## Amaç
Microsoft Excel'in kalabalık arayüzü yerine, gerçekten kullanılan %10'luk kısmı sade ve hızlı biçimde sunan bir masaüstü hesap tablosu uygulaması. Sözcük'ün (Word alternatifi, `Desktop\sozcuk`) kardeşi: aynı görünüm dili, aynı ilkeler (yerel çalışır, buluta veri göndermez, Türkçe; **arayüz Excel gibi sekmeli şerit olacak** — bkz. "Arayüz: sekmeli şerit").

Hedef kullanıcı: ev/ofis kullanıcısı — bütçe, liste, fatura/stok takibi, basit hesaplar, Excel'den gelen dosyayı açıp düzenleyip geri göndermek.

**Başarı ölçütü (2026-10-08, kullanıcı kararı):** özellik sayısı değil, *"kullanıcının günlük işinin ne kadarını karşılıyoruz"*. Hedef: makro (VBA) hariç günlük işlerin %50–70'i. Her fazın sonunda **gerçek iş senaryosu testi** yapılır: örnek bir bütçe, stok listesi ya da not çizelgesi dosyası baştan sona Tabcel'de hazırlanıp kaydedilir/yeniden açılır; takıldığımız yerler bir sonraki fazın girdisi olur (bkz. surec.md).

## Teknik altyapı
- **Dil / arayüz:** Python 3.11 + PySide6 (Qt) — Sözcük ile aynı
- **Izgara:** kendi çizdiğimiz ızgara bileşeni (`QAbstractScrollArea` + `QPainter`). *Neden QTableView değil:* birleştirilmiş hücreler, taşan metin (boş komşu hücreye yazının taşması), bölmeleri dondurma, doldurma tutamacı, Excel tarzı seçim çerçevesi QTableView'da ancak yamalarla olur; kendi çizimimizde hem tam denetim hem hız var (yalnızca ekrandaki hücreler çizilir)
- **Veri modeli:** Qt'den bağımsız saf Python; seyrek depolama (yalnızca dolu hücreler sözlükte). Sınırlar Excel ile aynı: 1.048.576 satır × 16.384 sütun (XFD)
- **Formül motoru:** kendimiz yazıyoruz (tokenizer → ayrıştırıcı → sözdizim ağacı → değerlendirici + bağımlılık grafiği). Hazır kütüphane (`formulas`, `pycel`) ağır, yavaş ya da Türkçe/yerel ayar desteği yok
- **Dosyalar:** `openpyxl` (MIT) .xlsx; `csv` (standart kütüphane); `xlrd` (BSD) .xls okuma; `odfpy` (Apache/GPL çift — lisans faz 8'de doğrulanacak) .ods; PDF/yazdırma Qt ile; şifreli .xlsx için `msoffcrypto-tool` (Sözcük'te kullanılıyor)
- **Grafikler:** QPainter ile kendi çizimimiz (QtCharts GPL/ticari lisanslı olabilir — kullanılmayacak, bkz. Kararlar)
- **Paketleme:** PyInstaller **tek klasör (onedir) — zorunlu, tek dosya (onefile) kullanılmaz** (PySide6 LGPLv3 uyumu: Qt DLL'leri ayrı dosya kalır, kullanıcı değiştirebilir; ayrıntı surec.md → Lisans uyum notu) + Inno Setup 6.5+ — Sözcük'teki `sozcuk.spec` / `kurulum/sozcuk.iss` örnek alınır
- **Lisans ilkesi (Sözcük'ten devralındı):** GPL/AGPL bileşen yok (.exe dağıtımı için). PySide6 LGPLv3'tür: dinamik bağlanır, onedir paketlenir, lisans metni + kaynak bilgisi Hakkında'da verilir (surec.md → Lisans uyum notu). Yığın Python/PySide6 olduğu için JS tabanlı kütüphaneler (Univer, HyperFormula [GPLv3/ticari], SheetJS, ECharts) kullanılmaz — karar 2026-10-08, gerekçe surec.md → Kararlar

## Excel ile uyum ilkeleri (baştan sabit)
1. **Formül saklama biçimi İngilizce ve kanoniktir** (`=SUM(A1:A3,2.5)`), tıpkı .xlsx dosyasının içindeki gibi. Kullanıcıya **Türkçe Excel gibi** gösterilir ve öyle yazılır: `=TOPLA(A1:A3;2,5)` — fonksiyon adları Türkçe, ayraç `;`, ondalık `,`. Ayarlardan İngilizce gösterim seçilebilir. Kullanıcı İngilizce adla yazarsa da (`=SUM(...)`) kabul edilir
2. **Tarihler Excel seri sayısıdır** (1900 tarih sistemi, Excel'in 29 Şubat 1900 hatası dahil — uyum için bilerek)
3. **Hata değerleri Excel'in Türkçe karşılıklarıyla gösterilir:** `#BÖL/0!`, `#AD?`, `#BAŞV!`, `#DEĞER!`, `#YOK`, `#SAYI!`, `#BOŞ!` (dosyada İngilizce: `#DIV/0!` …)
4. **Varsayılanlar Excel'inkidir:** Calibri 11 (yoksa Aptos/Segoe UI), sütun genişliği 8,43 karakter (64 px), satır yüksekliği 15 nk (20 px), sayfa adı "Sayfa1"
5. **Klavye Excel'dekiyle aynıdır:** Enter aşağı, Tab sağa, F2 düzenle, Ctrl+ok veri kenarına atla, Ctrl+Shift+ok seçerek atla, Ctrl+Home/End, F4 başvuruyu $'la, Ctrl+; bugünün tarihi, Ctrl+Shift+: saat, Ctrl+D/Ctrl+R aşağı/sağa doldur, Alt+= Otomatik Toplam, Ctrl+1 Hücreleri Biçimlendir, Ctrl+PageUp/Down sayfa değiştir, Delete içeriği sil

## Mimari (katmanlar)
```
tabcel/
  __init__.py        APP_NAME, sürüm, künye, resource_dir() — görünen ad YALNIZCA buradan
  model/             Qt'siz: Workbook, Sheet, Cell, stiller, adresleme (A1 ⇄ satır/sütun), geri al komutları
  formul/            Qt'siz: tokenizer, parser, ast, evaluator, fonksiyonlar (tr/en ad tablosu), bağımlılık grafiği, başvuru kaydırma
  io/                xlsx_io, csv_io, (xls_io, ods_io), pdf/yazdırma
  ui/                window, grid (ızgara), formula_bar, sheet_tabs, headers, dialogs, theme, icons, widgets
testler/             pytest — model/formül testleri Qt'siz; arayüz testleri QT_QPA_PLATFORM=offscreen
araclar/             ikon üretimi vb.
kurulum/             Inno Setup betiği
```
Kural: `model/` ve `formul/` Qt içe aktarmaz → hızlı test edilir, ileride başka arayüzle de kullanılabilir.

---

## Fazlar

### Faz özeti: zorluk ve risk
| Faz | Zorluk | Başlıca risk |
|---|---|---|
| 1 Çekirdek / ızgara | Orta | Pano (HTML/TSV) uyumu; 100.000 hücrede akıcılık |
| 2 Formül motoru | **Yüksek** | Excel uyumu uç durumlarda (tür dönüşümü, tarih serisi, 15 basamak); başvuru kaydırma; Türkçe ad/ayraç çevirisi |
| 3 Biçimlendirme | Orta–yüksek | Özel sayı biçim kodları; birleştirilmiş hücreler ve ızgara çizimi |
| 4 Dosyalar | **Yüksek** | .xlsx gidiş-dönüşte veri kaybı (openpyxl: grafik/resim korunmaz); büyük dosya hızı |
| 5 Veri araçları | Orta | Koşullu biçim/doğrulama .xlsx gidiş-dönüşü; Türkçe sıralama |
| 6 Grafikler | Orta–yüksek | QPainter ile kendi grafik motoru; .xlsx'e yazma |
| 7 Paket/dağıtım | Orta | PyInstaller boyutu; LGPL uyumu; kurulum testi |
| 8 Sonra | Değişken | Pivot, dinamik diziler |

**Her faz bitiş ölçütü:** testler geçer → gerçek iş senaryosu testi → surec.md güncel → (kullanıcı isterse) commit.

### Faz 0 — Planlama ve iskelet
**Durum:** Planlama tamamlandı (2026-10-08). Kod yok.
- `plan.md`, `CLAUDE.md`, `surec.md`, `.gitignore`, git deposu
- Sıradaki: `.venv`, `requirements.txt`, `main.py`, `Tabcel.bat`, boş paket yapısı, ilk test

### Faz 1 — Çekirdek: veri modeli + ızgara + temel düzenleme
- Veri modeli: seyrek hücreler, değer türleri (sayı, metin, mantıksal, tarih=sayı+biçim, hata, boş), sayfalar
- Izgara: sütun başlıkları (A…XFD), satır numaraları, kılavuz çizgiler, kaydırma, yalnızca görünen hücreleri çizme, sayı sağa / metin sola hizalı, metnin boş komşuya taşması, `####` (sayı sığmazsa)
- Seçim: tek hücre, fareyle aralık, Shift+tık, Ctrl ile çoklu aralık, tüm satır/sütun (başlığa tık), tümünü seç (köşe / Ctrl+A); etkin hücre çerçevesi Excel yeşili
- Düzenleme: yazınca başla (üzerine yaz), F2 / çift tık (içinde düzenle), Esc iptal, Enter/Tab/Shift+Enter/Shift+Tab yönleri, Alt+Enter hücre içinde yeni satır, Delete
- **Formül çubuğu** + **ad kutusu** (A1 yaz → git; aralık seçilince "3S x 2Sü" gösterimi)
- Satır/sütun: kenarından sürükleyerek boyutlandırma, çift tıkla otomatik sığdır, ekle/sil, gizle/göster (sağ tık menüsü)
- Sayfa sekmeleri: ekle (+), yeniden adlandır (çift tık), sil, taşı (sürükle), renk; Ctrl+PageUp/Down
- Geri al / yinele (komut deseni, çok adımlı, aralık işlemleri tek adım)
- Pano: kopyala/kes/yapıştır — kendi içinde tam (değer+biçim+formül), dışarıya/dışarıdan TSV + HTML (Excel, Google E-Tablolar, Sözcük, web tabloları); kes-yapıştırın kesik çizgili "karınca" çerçevesi
- Durum çubuğu: Hazır/Gir/Düzenle modu; seçimde **Ortalama · Sayım · Toplam** (Excel gibi); yakınlaştırma kaydırıcısı (%10–%400, Ctrl+tekerlek)
- Görünüm: Sözcük'ün tema dili — başlık şeridi **Excel yeşili (#217346)**, Windows 11 başlık çubuğu aynı renk (DWM), tek satır komut çubuğu, Dosya menüsü
- Test: model birim testleri; ızgara için ekransız testler (seçim, düzenleme, gezinme, geri al) + ekran görüntüsü incelemesi
- **Faz 2 başlamadan önce zorunlu:** 100.000 dolu hücrede (ör. 5.000 × 20) kaydırma, ilk çizim, düzenleme ve geri al süresi ölçülür; sonuç surec.md'ye yazılır. Hedef: kaydırmada kare başına < 16 ms; yavaşsa Faz 2'ye geçmeden önce çizim önbelleği/optimizasyon yapılır
- **Sayfa sıralama:** `CalismaKitabi.sayfa_tasi(sayfa, yeni_indeks)` (model) + geri al komutu; sekme sürüklemesi UI'da buna bağlanır

### Faz 2 — Formül motoru
- Tokenizer + ayrıştırıcı: sayılar (yerel ayarlı), metin, mantıksal, hata sabitleri, işleçler (`+ - * / ^ & = <> < > <= >= %`, tekli eksi, öncelik Excel'deki gibi), başvurular (`A1`, `$A$1`, `A:A`, `1:1`, `A1:B5`, `Sayfa2!A1`, `'Gelir Gider'!A1:B2`), fonksiyon çağrıları, dizi sabitleri `{1;2;3}`
- Değerlendirici: Excel'in tür dönüşüm kuralları (metin "3" + 1 = 4, boş = 0, TRUE = 1…), hata yayılımı, aralıkta örtük kesişim (basit)
- **Bağımlılık grafiği:** hücre değişince yalnızca etkilenenler yeniden hesaplanır (topolojik sıra); **döngüsel başvuru** tespiti ve uyarısı; değişken fonksiyonlar (BUGÜN, ŞİMDİ, S_SAYI_ÜRET) her hesaplamada
- **Başvuru kaydırma:** formül kopyalanınca göreli başvurular kayar, `$`'lılar sabit kalır; satır/sütun ekle-sil sonrası formüller düzelir, silinen hedef `#BAŞV!` olur; sayfa yeniden adlandırılınca formüller güncellenir
- Formül yazarken: başvuruyu fareyle seçme (renkli çerçeveli başvuru vurgusu, Excel gibi), fonksiyon adı otomatik tamamlama + kısa açıklama ipucu, F4 ile `$` döngüsü, **Otomatik Toplam** (Σ düğmesi / Alt+=)
- **Fonksiyonlar — ilk küme (~80), Türkçe + İngilizce adlarıyla:**
  - Matematik: SUM, SUMIF, SUMIFS, SUMPRODUCT, PRODUCT, ROUND, ROUNDUP, ROUNDDOWN, INT, MOD, ABS, SQRT, POWER, PI, RAND, RANDBETWEEN, CEILING, FLOOR, TRUNC, SIGN, EXP, LN, LOG, LOG10
  - İstatistik: AVERAGE, AVERAGEIF, AVERAGEIFS, COUNT, COUNTA, COUNTBLANK, COUNTIF, COUNTIFS, MAX, MIN, MAXIFS, MINIFS, MEDIAN, MODE, STDEV, VAR, LARGE, SMALL, RANK
  - Mantık: IF, IFS, AND, OR, NOT, XOR, IFERROR, IFNA, SWITCH, TRUE, FALSE
  - Arama: VLOOKUP, HLOOKUP, XLOOKUP, INDEX, MATCH, XMATCH, CHOOSE, ROW, COLUMN, ROWS, COLUMNS, INDIRECT, OFFSET
  - Metin: CONCATENATE, CONCAT, TEXTJOIN, LEFT, RIGHT, MID, LEN, UPPER, LOWER, PROPER, TRIM, FIND, SEARCH, SUBSTITUTE, REPLACE, TEXT, VALUE, REPT, EXACT
  - Tarih: TODAY, NOW, DATE, TIME, YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, WEEKDAY, WEEKNUM, EDATE, EOMONTH, DATEDIF, DAYS, NETWORKDAYS, WORKDAY
  - Bilgi: ISNUMBER, ISTEXT, ISBLANK, ISERROR, ISNA, ISLOGICAL
  - Finans (temel): PMT, FV, PV, RATE, NPV, IRR
- **Türkçe fonksiyon adları Microsoft'un resmî Türkçe çeviri listesinden doğrulanarak** tek bir tabloya (`formul/adlar.py`) yazılır — ezbere yazılmaz. Büyük/küçük harf ve Türkçe İ/ı doğru işlenir (`=topla(...)` → `=TOPLA(...)`)
- UPPER/LOWER/PROPER Türkçe harf kuralına uyar (i→İ, ı→I) — Excel'in Türkçe sürümü gibi
- **Test şablonu (zorunlu, CLAUDE.md kural 11):** her fonksiyon için en az dört vaka — (1) normal durum, (2) boş hücre/boş argüman, (3) hata değeri girdisi (hata yayılımı), (4) metin/sayı karışımı; ayrıca Microsoft belgelerindeki örneklerle "altın" testler
- **Türkçe yerel ayar çeviri katmanı ve ayrı testleri** (`testler/test_yerellestirme.py`): kanonik İngilizce ⇄ Türkçe çeviri yalnızca fonksiyon adlarını değil **ayırıcıları** da kapsar — argüman ayırıcı `;` ⇄ `,`, ondalık `,` ⇄ `.`, dizi sabitindeki satır/sütun ayırıcıları (Türkçe Excel'de İngilizce'dekinden farklı olabilir — Excel web'de doğrulanacak), metin sabiti içindeki `;`/`,` çevrilmez, iç içe fonksiyon, sayfa adı içeren başvuru (`'Gelir Gider'!A1`), gidiş-dönüş (tr→en→tr aynı metni verir). Fonksiyon adları Microsoft'un **resmî Türkçe fonksiyon adı listesine** göre belirlenir; listede doğrulanamayan "belirsiz" diye surec.md'ye yazılır
- **Tarih seri numarası testleri:** 1 = 1.1.1900, 60 = 29.2.1900 (Excel'in bilinen artık yıl hatası — var olmayan bir gün; uyum için bilerek korunur), 61 = 1.3.1900; sınır değerleri, saat kesri (0,5 = 12:00), TARİH/YIL/AY/GÜN/HAFTANINGÜNÜ/EDATE/EOMONTH/NETWORKDAYS'ın 1900 Şubat çevresindeki davranışı, seri ⇄ tarih gidiş-dönüşü
- **15 anlamlı basamak testleri:** Excel sayıları çift duyarlıklı saklar ama **15 anlamlı basamak** gösterir ve girişte 15. basamaktan sonrasını sıfırlar (16+ basamaklı sayı yazılınca); `0,1+0,2` gibi kayan nokta örnekleri ve karşılaştırma/çıkarmada Excel'in yakın-sıfıra yuvarlama davranışı. Kesin kurallar Excel web'de doğrulanır (aşağıda); doğrulanana dek "belirsiz" listesinde durur
- Ayrıştırıcı için uç durumlar; 50.000 formüllük zincirde yeniden hesaplama süresi
- **Referans değerler:** bu bilgisayarda Excel yok. Referans olarak Microsoft belgeleri + **Excel'in web sürümü** (ücretsiz, Microsoft hesabıyla) kullanılır. Doğrulanamayan/emin olunmayan her vaka surec.md → "Excel web'de doğrulanacaklar" listesine yazılır; **doğrulamayı kullanıcı yapar** (Claude Excel web'e erişemez), sonuç listeye işlenir ve teste dönüştürülür
- Sonraya: dinamik diziler / taşma (SORT, FILTER, UNIQUE, SEQUENCE), LET, LAMBDA

### Faz 3 — Biçimlendirme ve verimlilik
- Yazı tipi, boyut, kalın/italik/altı çizili/üstü çizili, yazı rengi, dolgu rengi (Sözcük'ün renk seçicisi), kenarlıklar (Excel'in kenarlık menüsü), yatay/dikey hizalama, girinti, metni kaydır, döndürme yok (sonra)
- **Hücreleri birleştir** (Birleştir ve Ortala / Birleştir / Çöz)
- **Sayı biçimleri:** Genel, Sayı, Para Birimi (₺, $, €), Muhasebe, Tarih (kısa/uzun), Saat, Yüzde, Kesir, Bilimsel, Metin, **Özel** (Excel biçim kodları: `#.##0,00 ₺`, `gg.aa.yyyy`, `[Kırmızı]`… — .xlsx'ten gelen kodları okuyup doğru göstermek için gerekli). Türkçe yerel ayar: ondalık `,`, binlik `.`, ay/gün adları Türkçe; ondalık artır/azalt düğmeleri
- **Akıllı giriş:** `12.10.2026` → tarih, `%15` → yüzde, `1.234,5` → sayı, `₺100` → para; başında `'` olan metin olarak kalır
- **Doldurma tutamacı:** sağ alt köşeden sürükleyerek seri (1,2,3 / Ocak, Şubat / Pzt, Sal / tarih / "Ürün 1, Ürün 2"), formül kopyalama, çift tıkla aşağı doldur; Ctrl+D / Ctrl+R
- **Biçim boyacısı**, **Bölmeleri dondur** (üst satır / ilk sütun / seçili hücreden), kılavuz çizgileri göster/gizle
- Hücre stilleri (Sözcük'teki gibi az sayıda hazır: Başlık, Toplam, İyi/Kötü/Nötr) — isteğe bağlı
- **Tablo olarak biçimlendir** (şeritli satırlar + başlık satırı; Excel "Tablo" nesnesinin hafif hali) — isteğe bağlı, Faz 5'e kayabilir

### Faz 4 — Dosyalar
- **.xlsx aç/kaydet** (openpyxl): değerler, formüller, sayı biçimleri, yazı tipi/renk/dolgu/kenarlık/hizalama, birleştirmeler, sütun genişliği/satır yüksekliği, gizli satır/sütun, dondurulmuş bölmeler, sayfa adları/renkleri/sırası, adlandırılmış aralıklar, yorum/notlar
- Açılışta desteklenmeyen öğeler (makro/VBA, pivot tablo, grafik*, görsel, koşullu biçim*, veri doğrulama*, dış bağlantılar) bilgi çubuğunda bildirilir: "Kaydederseniz bu öğeler dosyadan çıkarılır" (*: ilgili faz gelince desteklenir)
- **openpyxl sınırı — veri kaybı uyarısı (zorunlu):** openpyxl açıp kaydetmede **grafik ve resimleri korumaz**. Böyle bir dosya açılırken (grafik/resim/şekil/pivot/makro tespit edilince) bilgi çubuğunda **açık uyarı** gösterilir: "Bu dosyada grafik/resim var; kaydederseniz kaybolur" ve kaydetme sırasında bir kez daha onay istenir (*Farklı kaydet* önerilir, özgün dosyaya dokunulmaz). Tespit .xlsx zip'inde `xl/charts/`, `xl/drawings/`, `xl/media/` yollarına bakılarak yapılır (openpyxl'e güvenmeden)
- **Gidiş-dönüş testleri (Faz 4 çıkış şartı):** `testler/ornekler/` altında örnek .xlsx dosyaları — değer/formül/biçim/birleştirme/gizli satır/dondurma/çok sayfa/yorum içeren; ayrıca **grafikli ve resimli örnek dosya** (bu dosyada uyarının çıktığı ve geri kalan verinin kaybolmadığı doğrulanır). Döngü: aç → kaydet → tekrar aç → hücre değerleri, formüller, biçimler, boyutlar eşit; kayıp olan her öğe listelenir. Gerçek Excel'de açılabilirlik kullanıcıya "elle test bekliyor" diye bırakılır
- Bilinen openpyxl sınırı: kaydedilen formüllerin önbellek değeri yazılmaz → Excel açınca yeniden hesaplar (sorun değil), ama değeri okuyan bazı araçlar boş görebilir. Faz 4'te araştırılıp gerekirse önbellek değerleri sonradan XML'e eklenir
- Büyük dosyalar: arka plan iş parçacığında açma/kaydetme, ilerleme çubuğu; hedef: 100.000 satır × 20 sütun < 10 sn açılış
- **.csv** aç/kaydet: kodlama (UTF-8 BOM / Windows-1254) ve ayraç (`;` `,` sekme) otomatik tanıma, önizlemeli içe aktarma penceresi; Türkçe Excel'in `;`'lü CSV'siyle uyumlu
- **PDF olarak dışa aktar** ve **Yazdır:** sayfa yapısı (dikey/yatay, kenar boşlukları, sayfaya sığdır), yazdırma alanı, başlık satırlarını her sayfada yinele, önizleme
- Kaydetme güvenliği (Sözcük'teki düzen): geçici dosyaya yaz → yerine koy; dosya Excel'de açıksa anlaşılır mesaj
- **Otomatik kaydetme** + 2 dakikada bir kurtarma kopyası (`%APPDATA%\<APP_NAME>\recovery`), çökme sonrası geri yükleme önerisi
- Son kullanılan dosyalar, komut satırından dosya açma (`Tabcel.bat dosya.xlsx`)

### Faz 5 — Veri araçları
- **Sırala** (A→Z, Z→A, çok düzeyli özel sıralama; Türkçe alfabe sırası: Ç, Ğ, İ, Ö, Ş, Ü doğru yerde)
- **Filtre** (başlık oklarıyla: değer listesi onay kutuları, metin/sayı/tarih koşulları, renkle); filtre .xlsx'e yazılır
- **Bul ve Değiştir** (Ctrl+F / Ctrl+H; değerlerde/formüllerde, tüm sayfalarda, tam hücre eşleşmesi)
- **Koşullu biçimlendirme** (temel: büyüktür/küçüktür/arasında/eşittir/metin içerir/yinelenenler, ilk 10, renk ölçeği, veri çubukları) — .xlsx gidiş-dönüş
- **Veri doğrulama** (açılır liste, sayı/tarih aralığı, hata mesajı) — .xlsx gidiş-dönüş
- **Adlandırılmış aralıklar** (ad kutusundan tanımlama, Ad Yöneticisi), **Notlar/Açıklamalar** (kırmızı köşe üçgeni, üzerine gelince göster)
- Yinelenenleri kaldır, Metni Sütunlara Dönüştür, Hızlı Doldur yok (sonra)

### Faz 6 — Grafikler
- Seçili veriden grafik ekle: sütun, çubuk, çizgi, pasta, halka, alan, dağılım (XY)
- Grafik sayfanın üzerinde yüzen nesne: taşı, boyutlandır, sil; başlık, gösterge, eksen başlıkları, renkler; veri değişince canlı güncellenir
- .xlsx'e yazma **ve okuma** (openpyxl ikisini de yapar — 2026-10-10'da `grafikli.xlsx` ile doğrulandı; plan'daki "okuma yok" yanlıştı); openpyxl'in anlamadığı biçimler/türler düşer ve uyarı verilir. Ayrıntı `faz6_tasarim.md`
- Görsel ekleme (resim) — Sözcük'ün `images.py` deneyimiyle

### Faz 7 — Ortak özellikler, paket ve dağıtım (Sözcük'ten)
- **Google Drive / OneDrive canlı kayıt** (Sözcük'teki `cloud.py` düzeni: eşitleme klasörü üzerinden, API yok)
- **Yazım denetimi** (Windows Yazım Denetimi API'si, Sözcük'teki `spellengine.py`) — metin hücreleri için F7
- Yardım ve Nasıl Kullanılır (`yardim.md`), **Hakkında** (sürüm, "Developed By Usta ve Ata", bileşen lisansları), Yenilikler
- İkon (`araclar/ikon_uret.py`: Excel yeşili, ızgara + harf), özelleştirilebilir komut çubuğu
- **PyInstaller** (`tabcel.spec`, gereksiz Qt modülleri dışlanır; hedef < 150 MB) + **Inno Setup** (Türkçe sihirbaz, .xlsx/.csv ilişkilendirme, "Birlikte aç", kaldırma) + kurulum testi
- GitHub deposu (kullanıcı onayıyla; noreply e-posta), README

### Faz 8 — Sonra / değerlendirilecek
- .xls okuma (xlrd), .ods aç/kaydet, parola korumalı .xlsx (msoffcrypto-tool), sayfa/çalışma kitabı koruması
- Basit **Özet Tablo** (pivot: satır/sütun/değer alanları, Toplam/Sayım/Ortalama)
- Dinamik dizi fonksiyonları (FILTER, SORT, UNIQUE, SEQUENCE), LET
- openpyxl'in düşürdüğü Excel grafik biçimlerini kurtarma (kendi XML okuyucumuz; temel okuma Faz 6'da openpyxl ile)
- Sözcük ⇄ Tabcel: Sözcük'e bağlı tablo yapıştırma, ortak tema/bileşenlerin paylaşılan pakete çıkarılması
- Karanlık tema

### Faz 9 — Güven ve denetim araçları (imza özellikler; karar 2026-10-11, kullanıcı)
Tabcel'i Excel'den ayıran üç özellik; kalite ve güvenilirlik (özellikle **düşük yanlış alarm**) hızdan önce gelir. Sıra: 9a → 9b → 9c → 9d.
- **9a — Ortak altyapı:** `model/kimlik.py` (Qt'siz, TEK kaynak): TC kimlik no (mevcut algoritma buraya taşınır), vergi no (10 hane), IBAN (TR, mod-97; boşluklu/boşluksuz), kredi kartı (Luhn + kart ön eki), telefon (TR biçimleri), e-posta; güven düzeyi KESİN (algoritma) / BİÇİM / BELİRSİZ (ör. 10 haneli sayı: vergi no mu telefon mu); metin içinde bulma (`tara_metin`) ve maskeleme (ayarlanabilir `MaskeAyari`). Tabcel'e özel işlevler `VERGİNOGEÇERLİ` (`TR_VALIDATE_VKN`) ve `IBANGEÇERLİ` (`TR_VALIDATE_IBAN`) (kural 16). Motora salt okunur **`onculler` / `bagimlilar` API'si**. Formül ağacından metne yazım (eksik aralık düzeltmesi için) doğrulanır.
- **9b — Özellik 1: Hesap İzleme Paneli** ("Bu sayı nereden geliyor?"): yerleştirilebilir (dock) yan panel; seçili hücrenin Türkçe formülü + tembel açılan hesap zinciri ağacı (adres, formül, değer — hücrenin sayı biçimiyle); aralıklar tek düğüm ("A1:A1000 — 1.000 hücre, toplam 84.250"), açılınca sayfalı; sayfalar arası başvuru sayfa adıyla; tıklayınca ızgarada hücreye git + vurgula; **ters yön** sekmesi (bu hücre nerelerde kullanılıyor); hatanın asıl kaynağı ayrıca işaretlenir (`hata_neden`); döngü açıkça belirtilir (sonsuz döngü yok); sabit değerler yaprak; değer değişince panel güncellenir. Ölçüt: 100.000 hücrelik tabloda arayüz donmaz, ölçüm `surec.md`'ye yazılır.
- **9c — Özellik 3: Tablo Sağlık Kontrolü:** tüm kitabı arka planda (anlık görüntü + iş parçacığı, ilerleme, iptal) tarar. Kontroller (önem sırası): (1) eksik aralık (TOPLA/ORTALAMA/SAY… bitişikteki aynı türden veriyi kapsamıyor — ara toplam/başlık/formül hücresi ayıklama kurallarıyla), (2) tutarsız formül (komşu çoğunluğuna göre göreli yapı farkı), (3) metin olarak saklanan sayı (IBAN/TC/telefon istisna: `csv_io.korunmali_mi`), (4) formül içinde sabit sayı (yoksayılacak sayılar ayarlı; 0, 1 vb. alarm vermez), (5) hata değerleri + kaynak, (6) boş hücreye başvuru, (7) yinelenen satırlar, (8) geçersiz TC/vergi no/IBAN (`kimlik.py`). Rapor paneli Kritik / Uyarı / Bilgi, adetli; bulguya tıklayınca hücreye git + sade Türkçe açıklama; güvenli durumlarda **onayla** tek tıkla düzeltme (geri al yığınına girer); **denetçi onaysız hücre değiştirmez**; "Yoksay" kalıcı (dosyada özel özellik, **yalnız adres+kural, değer yok**); her kontrol ayarlardan açılıp kapanır (kullanıcı ayarı `%APPDATA%`). Her kontrol için hem "sorun var" hem "benziyor ama sorun değil" testi.
- **9d — Özellik 5: KVKK Paylaşım Temizleyici** ("yardımcı araç"; hukuki uygunluk iddiası yok; "Verileriniz bilgisayarınızdan çıkmaz"): algılanan veri: TC, vergi no, IBAN, telefon, e-posta, kart (Luhn), ad-soyad (yalnız sütun başlığına göre öneri). Taranan yerler: tüm sayfalar, gizli satır/sütun, **gizli sayfa** (model gizli sayfayı korur — aşağıdaki karar), notlar, grafik başlıkları/seri adları, tanımlı adlar, sayfa adları, doğrulama listeleri, üst/alt bilgi, özgün dosyanın meta verisi (yazar vb.; resimler taranamaz → uyarı). Tür başına Maskele / Sil / Bırak; maske biçimleri ayarlı; gizli yerdeki veri için özel uyarı. **Özgün dosya asla değişmez** (yeni dosya, kullanıcı ad/yer seçer; özgün yola yazma engellenir); temiz kopya bellekte derin kopyadan üretilir, geçmiş/geri al/meta verisi yoktur, kurtarma kopyası yazılmaz; testle dosya düzeyinde "özgün değer hiçbir parçada yok" doğrulanır. Maskelenen hücreye bağlı formüller: **formül kalır, maskeli değerle yeniden hesaplanır; kaydetmeden önce sonucu değişen/hataya dönen formüller listelenir; isteğe bağlı "değere çevir" yalnız sonuç maskelenen bir değeri içermiyorsa** (özgün değerlerle dondurmak sızdırabilir).
- **Kararlar (kullanıcı onayı 2026-10-11):** formül stratejisi yukarıdaki; `VERGİNOGEÇERLİ`/`IBANGEÇERLİ` adları; gizli sayfa korunur (`Sayfa.gizli`; mevcut "görünür yap + uyar" davranışı ve `test_gizli_sayfa_kayip_sayilir` buna göre güncellenir — kural 12 bildirimi); yoksayma kaydı yalnız adres+kural.
- **Test verisi yalnız sentetik** (algoritmaya göre geçerli ama rastgele üretilmiş TC/vergi no/IBAN/kart); gerçek kişi verisi kullanılmaz.

## Yapılmayacaklar
- VBA/makro çalıştırma (güvenlik + kapsam), Power Query, Power Pivot, **Solver**, ortak canlı düzenleme (Excel Online'a özgü), bulut yapay zekâ (Sözcük kararı: veri buluta gitmez)

## Arayüz: sekmeli şerit (karar 2026-10-10, kullanıcı)
Excel'e benzer **sekmeli şerit** (Dosya · Giriş · Ekle · Sayfa Düzeni · Formüller · Veri · Gözden Geçir · Görünüm; her sekmede gruplar, büyük/küçük düğmeler). Önceki "şerit yok" ilkesi kaldırıldı.
- **Teknoloji: Python + PySide6 yeterli; C++/C# ayrı arayüz yok.** Şerit, Qt Widgets ile kendimiz yazılır (`QTabBar` + grup başlıklı düğme panelleri); hazır Qt şerit bileşeni yok ama yapı basit. Gerekçe ve karşılaştırma `surec.md` → Kararlar (2026-10-10).
- **Zamanlama:** Faz 5 bitince (5i'den sonra) ayrı iş **5j**, grafikler (Faz 6) başlamadan: şerit bir kez tasarlansın. Komutlar zaten `Pencere`/`Izgara` yöntemleri ve menü eylemleridir; şerit yalnız yerleşimdir (mevcut `BicimCubugu` ve Düzen/Veri/Görünüm menüleri şeride taşınır, işlev değişmez).
- **Kapsam:** daralan pencerede grup küçülmesi/taşma menüsü, şeridi daraltma (Ctrl+F1), Alt tuş ipuçları (isteğe bağlı), simge seti (`ui/icons.py` genişler, 20 px / 1 px çizgi kuralı), Dosya sekmesi (şimdilik açılır menü; arka sahne sayfası sonra).
- **Ölçüt:** tüm mevcut kısayol ve komutlar şeritten de erişilir; mevcut testler değişmeden geçer; 1100 px genişlikte kırpılma yok.

## Model kullanımı (Claude Code)
- **Planlama, mimari kararlar, faz sonu gözden geçirme:** Opus 5.5 (`/model opus`)
- **Kod yazımı ve testler:** Sonnet 5.5 (`/model sonnet`) — her faz `plan.md`'de ayrıntılı tarif edildiği için Sonnet'in uygulaması yeterli
- **İstisna — Opus'la yazılacak zor çekirdekler:** formül ayrıştırıcı + bağımlılık grafiği + başvuru kaydırma (Faz 2 çekirdeği), .xlsx biçim/sayı biçimi kodu çözümleyicisi (Faz 3–4). Bunlarda hata, sonradan her yere yayılır
- Her fazın sonunda kısa bir Opus gözden geçirmesi: "plan.md'deki Faz X'i surec.md'deki kayda göre gözden geçir"
