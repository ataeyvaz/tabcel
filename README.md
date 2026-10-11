# Tabcel

Excel'in kalabalığı yerine, günlük işte gerçekten kullanılan özellikleri sade bir yüzle sunan **Türkçe masaüstü hesap tablosu**. Windows için; Python 3.11 ve PySide6 ile yazıldı. [Sözcük](../sozcuk)'ün kardeş uygulamasıdır.

**Developed By Usta ve Ata**

Her şey **bilgisayarda** çalışır: çalışma kitaplarınız hiçbir sunucuya gönderilmez; bulut yapay zekâ, telemetri ve hesap bağlantısı yoktur.

## Neler var

- **Izgara ve formüller:** kendi çizdiğimiz ızgara, 100'den fazla işlev (Türkçe adlarıyla: `TOPLA`, `EĞER`, `DÜŞEYARA`…; ayırıcı `;`, ondalık `,`), Excel 365 dizi semantiği, döngü uyarısı, hata değerleri için Türkçe açıklama
- **Biçimlendirme:** yazı tipi, kenarlık, dolgu, sayı biçimleri (Türkçe bölgesel), birleştirme, metni kaydır, dondurma, biçim boyacısı, doldurma/seriler
- **Veri araçları:** sırala (Türkçe harf kurallarıyla), filtre, bul/değiştir, veri doğrulama, koşullu biçim, adlandırılmış aralıklar, notlar
- **Grafikler ve resimler:** sütun, çubuk, çizgi, pasta, halka, alan, dağılım; .xlsx'e yazma ve okuma
- **Dosyalar:** .xlsx (asıl biçim; **parolalı** açma/kaydetme), .xls (yalnız okuma), .csv (kodlama/ayraç tanıma, kimlik koruması), PDF dışa aktarma, yazdırma, sayfa sonları, otomatik kayıt + çökme kurtarma
- **Google Drive / OneDrive:** eşitleme klasöründeki dosyalarda canlı kayıt, dışarıdan değişikliği fark etme (API yok, hesaba dokunulmaz)
- **Yazım denetimi (F7):** Windows'un Türkçe yazım denetimi, çevrimdışı
- **Türkiye'ye özel işlevler:** `YAZIYLA`, `TCKİMLİKDOĞRULA` (Excel'de karşılığı yok; `.xlsx`e kaydederken uyarılır)
- **Excel kısayolları ve davranışı** esastır; farklar uygulama içi yardımdaki "Excel'den Farklar"da (F1)

## Çalıştırma (kaynaktan)

```bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Tabcel.bat
```

ya da `.venv\Scripts\python main.py [dosya.xlsx]`. Testler: `.venv\Scripts\python -m pytest testler -q`
(RAM sınırlıysa `.venv\Scripts\python araclar\test_parcali.py` tam paketi 3 süreçte koşar).

## Paketleme

```bat
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe araclar\ikon_uret.py
.venv\Scripts\python.exe -m PyInstaller tabcel.spec --noconfirm
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" kurulum\tabcel.iss
```

Sonuç: `dist\Tabcel\` (taşınabilir klasör, ≈75 MB) ve `dist\Tabcel-0.1-kurulum.exe` (kurulum paketi, ≈25 MB). PySide6 LGPLv3 gereği paket **yalnız klasör (onedir)** biçiminde dağıtılır. Kurulum "Birlikte aç" listesine ekler, istenirse .xlsx/.csv ilişkilendirir; kaldırma kullanıcı verisine (`%APPDATA%\Tabcel`) dokunmaz.

## Klasörler

| Yol | İçerik |
|---|---|
| `tabcel/model/`, `tabcel/formul/` | Qt'siz çekirdek: veri modeli, formül motoru |
| `tabcel/io/` | .xlsx, .csv, kurtarma, bulut klasörleri, Windows yazım denetimi |
| `tabcel/ui/` | arayüz (ızgara, şerit, pencereler) |
| `tabcel/yardim.md` | uygulama içi yardım (F1) |
| `testler/`, `araclar/` | testler; ölçüm/doğrulama/ikon betikleri |
| `kurulum/`, `tabcel.spec` | Inno Setup betiği, PyInstaller tarifi |
| `CLAUDE.md`, `plan.md`, `surec.md` | kurallar, plan, süreç günlüğü |

## Kullanılan açık kaynak bileşenler

PySide6 (Qt, LGPL v3) · openpyxl + et_xmlfile (MIT) · xlrd (BSD) · msoffcrypto-tool + cryptography (MIT / Apache 2.0 / BSD) · Pillow (HPND) · comtypes (MIT, yalnız Windows).
Derleme aracı: PyInstaller (GPL + paketleme istisnası; pakete girmez) · Inno Setup.

Tabcel'in kendi lisansı henüz belirlenmedi.
