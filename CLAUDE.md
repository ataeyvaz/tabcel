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

## Dosya yapısı
```
main.py              giriş noktası (komut satırından dosya açma)
Tabcel.bat           .venv ile konsolsuz başlatma
requirements.txt     bağımlılıklar
tabcel/__init__.py   APP_NAME, __version__, künye, resource_dir()
tabcel/model/        sayfa (Hucre/Sayfa/CalismaKitabi), adres, girdi, deger (Hata), gosterim, olay,
                     komutlar (geri al), pano, olcu, stil, sayi_bicimi, doldur, sayfa_yapisi, sayfalama;
                     Faz 5: harmanla, bul, sirala, filtre, dogrulama, kosullu — Qt yok
tabcel/formul/       yerel, sozcuk (tokenizer), agac (parser), degerler, donustur, degerlendir,
                     fonksiyonlar/ (kayıt + gruplar), adlar (tr⇄en), ceviri, motor (bağımlılık +
                     yeniden hesap), kaydir (başvuru kaydırma); Faz 5: kosul (koşullu biçim +
                     doğrulama değerlendirmesi) — Qt yok
tabcel/io/           xlsx_io, csv_io, kurtarma, son_dosyalar
tabcel/ui/           window, grid, theme, icons, widgets, pencereler (bicim, csv, sayfa yapısı, yazdır…)
testler/             pytest
araclar/             ölçüm/doğrulama betikleri (performans_olcum, formul_olcum, cizim_dogrula, test_raporu)
kurulum/             Inno Setup betiği (Faz 7)
plan.md / surec.md / test.md                     plan, süreç günlüğü, test sonuçları
faz2_tasarim.md / faz3_tasarim.md / faz5_tasarim.md   formül motoru / biçimlendirme / veri araçları tasarımı
```

## Teknoloji ve kısıtlar
- Python 3.11 (`py -3.11`), proje sanal ortamı `.venv` (genel Python'a paket kurma)
- PySide6 ≥ 6.6, openpyxl (MIT); sonraki fazlarda xlrd (BSD), msoffcrypto-tool (MIT)
- Izgara kendi çizimimiz (`QAbstractScrollArea` + `QPainter`), QTableView değil — gerekçe `plan.md`
- Tema: Excel yeşili `#217346` başlık şeridi; Sözcük'ün `theme.py`, `icons.py`, `widgets.py` dosyaları örnek alınır (kopyalanıp uyarlanır, Sözcük klasöründe **değişiklik yapılmaz**)
- Bilgisayar: RAM 7,9 GB — ağır testlerde başka uygulamaların kapalı olduğunu kontrol et
- Bu bilgisayarda Excel kurulu değil: Excel uyumu belgelerdeki örneklerle ve .xlsx dosyalarını openpyxl ile okuyup karşılaştırarak test edilir; gerçek Excel'de açma testi kullanıcıya bırakılır ve `surec.md`'ye "elle test bekliyor" diye yazılır

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
- Faz 1–4 bitti (model, formül motoru, biçimlendirme, .xlsx/.csv/PDF/kurtarma). Faz 5 (veri araçları) tasarlandı, uygulama sürüyor. Ayrıntı: `surec.md`
- Taşma (spill) yok (Faz 8): çok hücreli formül sonucu tek değere indirgenir
