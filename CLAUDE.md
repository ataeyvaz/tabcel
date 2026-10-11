# Tabcel — Claude Code proje kılavuzu

Bu dosya klasörün kökünde durur; Claude Code otomatik okur. Güncel durum: `surec.md`. Fazlar ve ayrıntılı kapsam: `plan.md`.

## Proje nedir
Microsoft Excel'e sade, Türkçe, yerel çalışan bir alternatif (masaüstü hesap tablosu). Sözcük'ün (Word alternatifi, `C:\Users\Ata\Desktop\sozcuk`) kardeş uygulaması; aynı görünüm dili ve ilkeler. Python 3.11 + PySide6. Çalıştırma: `Tabcel.bat` ya da `.venv\Scripts\python main.py`.

## Kesin kurallar (değiştirme, önce kullanıcıya sor)
1. **Ad geçicidir.** Kullanıcıya görünen ad yalnızca `tabcel/__init__.py` içindeki `APP_NAME` sabitinden okunur; pencere başlığı, menüler, mesajlar, yardım metni, `%APPDATA%` klasörü dahil. Arayüz metnine "Tabcel" sözcüğünü elle yazma. (Python paket adı `tabcel` (ad değişirse paket adının değişmesi gerekmez).) Kullanıcı verisi klasörü `QApplication.setOrganizationName` ile **değiştirilmez** — Sözcük'te bu, ayarları öksüz bırakmıştı.
2. **`tabcel/model/` ve `tabcel/formul/` Qt içe aktarmaz.** Saf Python; Qt'siz test edilir.
3. **Formüller içeride İngilizce kanonik biçimde saklanır** (`=SUM(A1:A3,2.5)`, .xlsx'teki gibi); kullanıcıya Türkçe Excel gibi gösterilir/yazdırılır (`=TOPLA(A1:A3;2,5)`). Dönüşüm yalnızca `formul/` içindeki yerelleştirme katmanında yapılır.
4. **Türkçe fonksiyon adları ve hata değerleri ezbere yazılmaz**; Microsoft'un resmî Türkçe listesiyle doğrulanır, doğrulanamayan "belirsiz" diye `surec.md`'ye yazılır.
5. **Lisans:** GPL/AGPL bileşen eklenmez (.exe dağıtımı; PySide6 LGPLv3 → yalnızca PyInstaller onedir, bkz. `surec.md` Lisans uyum notu). Yeni bağımlılıktan önce lisansı kontrol et, `README`/Hakkında listesine yaz. QtCharts kullanılmaz (GPL) — grafikler QPainter ile.
6. **Veri buluta gönderilmez.** Bulut yapay zekâ, telemetri, hesap bağlantısı yok.
7. **Excel davranışı esastır:** kısayollar, varsayılanlar, tarih seri sayısı, tür dönüşümleri Excel'deki gibi. Bilerek farklı yapılan her şey `surec.md` → Kararlar'a gerekçesiyle yazılır.
8. Dosya kaydı her zaman geçici dosyaya yaz → yerine koy düzeniyle (yarıda kalan kayıt dosyayı bozmaz).
9. Arayüz metinleri Türkçe; kod tanımlayıcıları İngilizce olabilir, yorumlar Türkçe ya da İngilizce (dosya içinde tutarlı).
10. Commit yalnızca kullanıcı isteyince. Silme/taşıma kullanıcı onayıyla.
11. **Fonksiyon test şablonu (Faz 2 ve sonrası):** her formül fonksiyonu için en az dört test vakası — normal durum, boş hücre/argüman, hata değeri girdisi, metin/sayı karışımı. Referans değer Microsoft belgesinden ya da kullanıcının Excel web'de doğruladığından alınır; emin olunmayan `surec.md` → "Excel web'de doğrulanacaklar" listesine yazılır (tahmin yürütme).
12. **Regresyon kuralı:** bir değişiklik mevcut bir özelliği/testi bozarsa devam etmeden önce kullanıcıya bildir (neyi bozdu, neden). Testi silerek/gevşeterek geçirme.
13. **Yardım güncel kalır:** yeni/değişen özellik, kısayol ya da Excel'den bilinçli fark `tabcel/yardim.md`'ye (ilgili konu, "Yenilikler", "Klavye Kısayolları", "Excel'den Farklar") aynı iş parçasında yazılır; testler yardımdaki kısayolların tanımlı olduğunu denetler.
14. **Türkçe büyük/küçük harf:** kullanıcı metninde (hücre değeri, sayfa/ad/not metni, arama) `str.upper/lower/casefold/title/capitalize` kullanılmaz; yalnız `tabcel.metin_tr` (`kucuk`, `buyuk`, `esit_mi`). ASCII teknik dizgiler (İngilizce işlev/hata adı, renk kodu, dosya uzantısı) serbest. Bilinçli istisna: sayfa adı karşılaştırması `casefold` (Excel davranışı doğrulanana dek, `surec.md` §8b).
15. **İçe aktarmada kimlik koruması:** CSV/dışarıdan gelen veride baştaki sıfırlı, 11 haneli (TC), 15 haneden uzun sayılar, IBAN ve `1-2`/`3/4` biçimli alanlar varsayılan olarak metin kalır (`csv_io.korunmali_mi`); kullanıcı sütun türüyle değiştirebilir.
16. **Tabcel'e özel işlevler** (Excel'de olmayan): kanonik adı İngilizce/ASCII `TR_` önekli (`TR_NUMBERTOWORDS`), Türkçe görünümü `adlar.TABCEL_OZEL`'de; `.xlsx`e kaydederken uyarı verilir.

## Dosya yapısı
```
main.py              giriş noktası (komut satırından dosya açma)
Tabcel.bat           .venv ile konsolsuz başlatma
requirements.txt     bağımlılıklar
tabcel/__init__.py   APP_NAME, __version__, künye, resource_dir()
tabcel/metin_tr.py   Türkçe büyük/küçük harf, tek kaynak (kural 14) — Qt yok
tabcel/model/        sayfa (Hucre/Sayfa/CalismaKitabi), anlik (salt okunur kitap kopyası), adres, girdi, deger (Hata), gosterim, olay,
                     komutlar (geri al), pano, olcu, stil, sayi_bicimi, doldur, sayfa_yapisi, sayfalama;
                     Faz 5: harmanla, bul, sirala, filtre, dogrulama, kosullu; Faz 6: grafik, grafik_verisi,
                     grafik_cizim (çizim listesi), grafik_islem, resim_yukle; ayrıca ad, notlar, bicim_islem,
                     bicim_kodlari, tarihseri, sirala — Qt yok
tabcel/formul/       yerel, sozcuk (tokenizer), agac (parser), degerler, donustur, degerlendir,
                     fonksiyonlar/ (kayıt + gruplar), adlar (tr⇄en), ceviri, motor (bağımlılık +
                     yeniden hesap), kaydir (başvuru kaydırma), ad_yardim, isaretleme, hata_neden (T8 hata açıklaması); Faz 5: kosul (koşullu
                     biçim + doğrulama değerlendirmesi); fonksiyonlar/turkiye (Tabcel'e özel, kural 16) — Qt yok
tabcel/io/           xlsx_io, xlsx_grafik (grafik/resim), xlsx_kayip (Excel'de değişmiş grafik tespiti),
                     csv_io, kurtarma, son_dosyalar; Faz 7: bulut (Drive/OneDrive klasörleri, Qt yok),
                     yazim_motoru (Windows yazım denetimi, comtypes)
tabcel/ui/           window, grid (+ grid_nesneler/grid_nesne_etkilesim: yüzen nesneler), theme, icons, widgets, serit +
                     serit_sekmeleri (sekmeli şerit), grafik_eylemleri/grafik_pencereleri/grafik_boyayici, yardim,
                     arka_plan (iş parçacığı), dosya_islemleri, bicim_cubugu, renkli,
                     pencereler (*_penceresi: bicim, csv, sayfa yapısı, yazdır…);
                     Faz 7: bulut_islemleri, hizli_erisim, hakkinda_penceresi, yazim_penceresi
testler/             pytest
araclar/             ölçüm/doğrulama betikleri (performans_olcum, formul_olcum, dosya_olcum, cizim_dogrula,
                     test_raporu, test_parcali [tam paket 3 süreçte], ornek_uret(.py/_excel.ps1),
                     excel_dogrula.ps1, excel_girdi_karsilastir.ps1 [gerçek Excel, COM])
kurulum/             Inno Setup betiği (tabcel.iss); kökte tabcel.spec (PyInstaller onedir), tabcel.ico (araclar/ikon_uret.py)
tabcel/yardim.md     uygulama içi yardım içeriği (F1); ad `{APP_NAME}` yer tutucusuyla yazılır
plan.md / surec.md / test.md                     plan, süreç günlüğü, test sonuçları
faz2/3/5/5j/6_tasarim.md   formül motoru / biçimlendirme / veri araçları / şerit / grafik tasarımı
t8/t9/t10_*/t4_arkaplan/secim_tasarim.md   T-işleri tasarım notları (hata açıklamaları, sayfa sonları,
                     xlsx kayıp tespiti, arka plan otokayıt, seçim modeli)
```

## Teknoloji ve kısıtlar
- Python 3.11 (`py -3.11`), proje sanal ortamı `.venv` (genel Python'a paket kurma)
- PySide6 ≥ 6.6, openpyxl (MIT); sonraki fazlarda xlrd (BSD), msoffcrypto-tool (MIT)
- Izgara kendi çizimimiz (`QAbstractScrollArea` + `QPainter`), QTableView değil — gerekçe `plan.md`
- Tema: Excel yeşili `#217346` başlık şeridi; Sözcük'ün `theme.py`, `icons.py`, `widgets.py` dosyaları örnek alınır (kopyalanıp uyarlanır, Sözcük klasöründe **değişiklik yapılmaz**)
- Bilgisayar: RAM 7,9 GB — ağır testlerde başka uygulamaların kapalı olduğunu kontrol et
- **Bu bilgisayarda Excel kurulu** (`C:\Program Files\Microsoft Officeoot\Office16\EXCEL.EXE`, Office 16; 2026-10-11'de kullanıcı bildirdi). Excel uyumu **COM ile gerçek Excel'de** denenir: `araclar\excel_dogrula.ps1 <dosya.xlsx> <çıktı_klasörü>` (görünmez açar, grafik türlerini/sayılarını yazar, grafikleri PNG'ye döker, Excel'in kendi kaydını üretir). Excel'de görsel/davranış doğrulaması gereken işlerde önce bunu kullan; yalnız Excel'in arayüzünde elle denenmesi gerekenler (kısayol hissi, iletişim kutuları) `surec.md`'ye "elle test bekliyor" diye yazılır. Excel'i çalıştırırken kullanıcının açık çalışma kitaplarına dokunma (yeni örnek, `DisplayAlerts=false`, işin sonunda `Quit`)

## Test ve çalıştırma
- Çalıştır: `Tabcel.bat` ya da `.venv\Scripts\python main.py [dosya.xlsx]`
- Testler: `.venv\Scripts\python -m pytest testler -q`
- Arayüz testleri ekransız: `QT_QPA_PLATFORM=offscreen`; görsel denetim için ekran görüntüsü alıp incele
- Her iş parçası bitince: testler geçer → `surec.md` güncellenir

## Model kullanımı
- Planlama, mimari, faz sonu gözden geçirme ve formül motoru çekirdeği / sayı biçimi çözümleyicisi: **Opus 5.5**
- Diğer kod yazımı ve testler: **Sonnet 5.5**
- Ayrıntı: `plan.md` → "Model kullanımı"

## Bilinen sınırlar
- Faz 1–6 bitti (model, formül, biçim, .xlsx/.csv/PDF/kurtarma, veri araçları, şerit, grafik/resim); Faz 6 kapanış onayı bekliyor. T1–T7, T9, T10 bitti. Ayrıntı: `surec.md`
- Tabcel'e özel işlevler (YAZIYLA, TCKİMLİKDOĞRULA) Excel'de `#AD?` verir
- Otomatik kayıt arka planda (anlık görüntü `model/anlik.py`; yazım sırasında arayüz GIL payı yüzünden en çok ≈ 0,2 sn takılabilir)
- Hata açıklamaları (`formul/hata_neden.py`) en çok 2.000 halkalı zinciri izler
- Taşma (spill): yalnız hesaplanmış `Dizi` sonuçları taşar (`TasmaHucre`, motor yönetir); düz aralık başvurusu (`=A1:A3`) taşmaz, `A1#`/`@` ve LAMBDA ailesi yok; xlsx'e eski tür dizi formülü olarak yazılır
