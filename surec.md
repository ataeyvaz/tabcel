# Tabcel — süreç ve durum (2026-10-08)

Kalıcı kurallar için `CLAUDE.md`, fazların kapsamı için `plan.md`. Bu dosya: nerede kaldık, nasıl çalışıyoruz, sırada ne var. Ayrıntılı tarihli günlük en altta (Sözcük'teki gibi).

## 1. Neredeyiz
| Faz | Hedef | Yapılan | Durum |
|---|---|---|---|
| 0 | Planlama, belgeler, iskelet | plan.md, CLAUDE.md, surec.md, .gitignore, git deposu, kod iskeleti | ✅ |
| 1 | Veri modeli + ızgara + temel düzenleme | — | ⏳ sıradaki |
| 2 | Formül motoru | — | ⏳ |
| 3 | Biçimlendirme, sayı biçimleri, doldurma, dondurma | — | ⏳ |
| 4 | .xlsx / .csv / PDF / yazdır / otomatik kayıt | — | ⏳ |
| 5 | Sırala, filtre, bul-değiştir, koşullu biçim, veri doğrulama | — | ⏳ |
| 6 | Grafikler | — | ⏳ |
| 7 | Drive/OneDrive, yazım denetimi, yardım, .exe + kurulum | — | ⏳ |
| 8 | .xls/.ods, pivot, dinamik diziler… | — | ⏳ (sonra) |

Son commit: yok · Testler: henüz yok

## 2. Sıradaki işler (öncelik sırasıyla)
1. ✅ Faz 1 iskeleti bitti (2026-10-08): `.venv`, `requirements.txt`, `main.py` (boş pencere), `Tabcel.bat`, `tabcel/__init__.py`, boş alt paketler, `testler/test_iskelet.py` (3 test geçti)
3. ✅ Adresleme bitti: `tabcel/model/adres.py` (A1 ⇄ satır/sütun, `$` mutlak, tam sütun/satır aralıkları, `XFD`/1.048.576 sınırı), 26 test
3b. ✅ `model/sayfa.py` (Hucre, Sayfa, CalismaKitabi) ve `model/komutlar.py` (GeriAlYigini, HucrelerDegis, SatirEkleSil, SutunEkleSil, Grup) bitti, 11 test
4a. ✅ `ui/grid.py` çizim + kaydırma + seçim + klavye/fare gezinme bitti (14 test, ekran görüntüsü incelendi)
4b. ✅ Hücre düzenleme bitti: `model/girdi.py` (girdi çözümleyici) + `Izgara` satır içi düzenleyici, Delete, Ctrl+Z/Y (55 test)
4c. ✅ Ana pencere bitti (`ui/window.py`): yeşil başlık şeridi (+ Win11 başlık çubuğu rengi), ad kutusu, formül çubuğu, sayfa sekmeleri, durum çubuğu, yakınlaştırma (20 test)
4d. ✅ Satır/sütun işlemleri bitti: kenardan sürükleyerek boyutlandırma (seçili tam satır/sütunlar birlikte), çift tık otomatik sığdır, ekle/sil/gizle/göster, başlık sağ tık menüsü, Ctrl+9/0 gizle, Ctrl+Shift+9/0 göster, Ctrl+−/+ sil/ekle, gizli satır/sütunlar gezinmede atlanır; hepsi geri alınır (27 test)
4e. Faz 1 kalan — birden çok aralık (Ctrl), `####`, taşan metin, Alt+Enter, sayfa rengi, Dosya menüsü (Yeni/Çıkış dışında boş), hücre sağ tık menüsü (pano ile)
5. Faz 1 — pano (TSV/HTML); (✅ yakınlaştırma, ✅ sayfa sıralama modeli+sekme sürükleme); Faz 1 sonu Opus gözden geçirmesi
5b. **Faz 2'ye geçmeden ZORUNLU:** 100.000 hücre performans ölçümü (5.000 × 20: ilk çizim, kaydırma kare süresi < 16 ms, düzenleme, geri al, `kullanilan_aralik`, Ctrl+ok); sonuç §8'e yazılır (kullanıcı kararı 2026-10-08)
5c. Her faz sonunda **gerçek iş senaryosu testi** (örnek bütçe/stok/not çizelgesi) ve gidiş-dönüş/regresyon denetimi
6. Faz 2 — formül motoru çekirdeği (**Opus ile**), sonra fonksiyonlar (Sonnet)

## 3. Çalışma sistemi (her adımda)
1. `surec.md`'yi oku, sıradaki işi al; kapsam `plan.md`'de
2. Küçük parçalar halinde yaz; `model/` ve `formul/` için önce/birlikte test
3. Testleri çalıştır: `.venv\Scripts\python -m pytest testler -q`; arayüz değiştiyse ekran görüntüsü al ve incele
4. Bu dosyayı güncelle: durum tablosu (§1), sıradaki işler (§2), kararlar (§4), en alta tarihli günlük girişi
5. Commit — yalnızca kullanıcı isterse (sonuna Co-Authored-By satırı)
6. Bağlam dolunca: "surec.md güncel, commit istersen atayım; ardından /clear önerilir"

## 4. Kararlar (tarihli)
- 2026-10-08: Uygulama adı **"Tabcel"** (önce "Tablo" çalışma adıydı; kullanıcı Tabcel dedi), yine de değişebilir → ad tek sabitte (`APP_NAME`). Aday adlar §5'te
- 2026-10-08: Proje klasörü `Desktop	ablo` → `Desktop	abcel`; Python paketi `tabcel`. Commit: her faz bitiminde (kullanıcı kararı)
- 2026-10-08: Altyapı Sözcük ile aynı: Python 3.11 + PySide6, proje `.venv`'i, PyInstaller + Inno Setup — iki uygulama aynı görünür, Sözcük'teki çözümler yeniden kullanılır
- 2026-10-08: Izgara **kendi çizimimiz** (QTableView değil) — birleştirme, taşan metin, dondurma, doldurma tutamacı için tam denetim ve hız
- 2026-10-08: **Formül motoru kendimiz** — hazır kütüphaneler ağır/yavaş, Türkçe yerel ayar yok
- 2026-10-08: Formül içeride İngilizce kanonik, ekranda Türkçe Excel gibi (`TOPLA`, `;`, `,`) — .xlsx ile birebir uyum
- 2026-10-08: Grafikler QPainter ile; QtCharts GPL olduğu için kullanılmaz
- 2026-10-08: Tema rengi Excel yeşili `#217346` (Sözcük'te Word mavisi `#185ABD`)
- 2026-10-08: **Yığın değişmez; JS kütüphaneleri (Univer, HyperFormula, SheetJS/ExcelJS, ECharts) kapsam dışı.** Gerekçe: hepsi JavaScript, bizimki Python/PySide6; geçiş = modeli/ızgarayı/testleri atmak; HyperFormula GPLv3/ticari (kural 5'e aykırı). Opus 5.5 ajanı da onayladı
- 2026-10-08: **Başarı ölçütü** "günlük işin %50–70'i (VBA hariç)"; her faz sonunda gerçek iş senaryosu testi (plan.md → Amaç)
- 2026-10-08: CLAUDE.md'ye **kural 11 (fonksiyon test şablonu: 4 vaka)** ve **kural 12 (regresyon kuralı)** eklendi; Solver "yapılmayacaklar"a eklendi
- 2026-10-08: **PyInstaller onedir zorunlu** (PySide6 LGPLv3 uyumu) — bkz. §9 Lisans uyum notu
- 2026-10-08: **openpyxl grafik/resim korumaz →** Faz 4'te açılışta + kaydederken veri kaybı uyarısı; gidiş-dönüş testlerine grafikli/resimli örnek dosya
- 2026-10-08: Referans değerler Microsoft belgeleri + **Excel web** (kullanıcı doğrular); emin olunmayanlar §8b listesinde
- 2026-10-08: Türkçe yerelleştirme katmanı ayırıcıları (`;` `,` ondalık `,`) da çevirir, **ayrı testlerle** (`testler/test_yerellestirme.py`); Faz 2 testlerine tarih seri numaraları (1900 artık yıl hatası) ve 15 anlamlı basamak eklendi
- 2026-10-08: **Model kullanımı:** planlama/mimari/gözden geçirme + formül çekirdeği + sayı biçimi çözümleyici Opus 5.5; geri kalan kod ve testler Sonnet 5.5 (kullanıcı kararı Claude'a bıraktı)

## 5. Açık sorular / bekleyenler
- **Kalıcı ad:** "Excel" İngilizcede "üstün olmak, sivrilmek" demek; birebir Türkçesi ("Üstün") bir hesap tablosu için anlamsız kaçıyor. Sözcük = "Word"ün birebir karşılığıydı; işlevden giden adaylar vardı; kullanıcı **Tabcel** dedi (karar verildi, ad yine tek sabitte)
- `git init` yapıldı; ilk commit kullanıcı isteyince
- GitHub deposu: Faz 7'de, kullanıcı onayıyla

## 6. Araçlar ve komutlar
| Ne | Komut / yer |
|---|---|
| Sanal ortam | `py -3.11 -m venv .venv` |
| Bağımlılık kur | `.venv\Scripts\python -m pip install -r requirements.txt` |
| Çalıştır | `Tabcel.bat` / `.venv\Scripts\python main.py` |
| Test | `.venv\Scripts\python -m pytest testler -q` |
| Örnek alınacak kardeş proje | `C:\Users\Ata\Desktop\sozcuk` (salt okunur: theme.py, icons.py, widgets.py, cloud.py, spellengine.py, sozcuk.spec, kurulum/sozcuk.iss) |

## 7. Bilinen sorunlar ve tuzaklar
- Bu bilgisayarda Excel yok → gerçek Excel'de açma testleri kullanıcıya kalır
- RAM 7,9 GB: büyük dosya / paketleme testlerinden önce diğer uygulamaları kontrol et
- npm/pip önbelleği temizlendi: ilk `pip install` paketleri internetten indirir (yavaş olabilir, hata değil)
- Sözcük'ten ders: `setOrganizationName` kullanıcı verisi klasörünü değiştirir — kullanma
- Sözcük'ten ders: ikonlar 20 px ızgarada 1 px çizgiyle çizilmeli, yoksa bulanık görünür

## 8. Performans ölçümleri
- **100.000 hücre ölçümü: HENÜZ YAPILMADI** — Faz 2'den önce zorunlu (§2, madde 5b). Sonuç buraya tarihli yazılacak.

## 8b. Excel web'de doğrulanacaklar (kullanıcı doğrular; sonra teste dönüşür)
Excel'in web sürümü (ücretsiz, Microsoft hesabıyla) Türkçe arayüze/yerel ayara ayarlıyken denenecek. Her satır "belirsiz" — doğrulanana dek kodda varsayım olarak işaretli.
| # | Soru | Şu anki varsayım (kodda) | Sonuç |
|---|---|---|---|
| 1 | Türkçe Excel'de hücreye `TRUE` / `FALSE` yazınca mantıksal olur mu, yoksa yalnızca `DOĞRU` / `YANLIŞ` mi? | İkisi de kabul (`model/girdi.py`) | ⏳ |
| 2 | `1.5` yazınca ne olur? (tarih "1 Mayıs" mı, metin mi, sayı mı) | Metin kalır (tarih çözümü Faz 3) | ⏳ |
| 3 | `1.500` → 1500 sayı mı? `5,` → 5 ve `,5` → 0,5 mi? `1.5E3`? | Evet / Evet / bilinmiyor | ⏳ |
| 4 | Dizi sabitinde ayırıcılar Türkçe'de nedir? (`{1;2;3}` satır/sütun ayrımı, `{1,2;3,4}` karşılığı) | Bilinmiyor — Faz 2'de çeviri katmanı yazılmadan önce doğrulanmalı | ⏳ |
| 5 | Hata değerlerinin Türkçe yazımı: `#BÖL/0!`, `#AD?`, `#BAŞV!`, `#DEĞER!`, `#YOK`, `#SAYI!`, `#BOŞ!`, `#TAŞMA!`… | plan.md'deki liste (resmî listeyle doğrulanmadı) | ⏳ |
| 6 | Faz 2 fonksiyonlarının resmî Türkçe adları (özellikle XLOOKUP=ÇAPRAZARA?, XMATCH, TEXTJOIN, IFS, SWITCH, MAXIFS…) | Yazılmadı; Microsoft'un resmî çeviri listesinden alınacak | ⏳ |
| 7 | 15 anlamlı basamak: 16+ basamaklı sayı girişi, `=0,1+0,2-0,3`, `=1*(0,5-0,4-0,1)`, karşılaştırma `=(0,1+0,2)=0,3` sonuçları | Bilinmiyor | ⏳ |
| 8 | 1900 artık yıl hatası: `=TARİH(1900;2;29)`, `=HAFTANINGÜNÜ(1)`, `=HAFTANINGÜNÜ(59)`, `=GÜN(60)` ve `AY(60)` sonuçları | 60 = 29.2.1900 kabul | ⏳ |
| 9 | Çok hücreli seçimde Enter, seçim içinde mi gezer? | Gezmez, aktif hücre bir aşağı (basitleştirme) | ⏳ |

## 9. Lisans uyum notu (PySide6 / LGPLv3)
*(Hukuki tavsiye değildir; bilinen LGPL gereklerine göre iç not. Faz 7'de yeniden gözden geçirilecek.)*
- PySide6 (Qt for Python) **LGPLv3** altındadır; uygulamamız kapalı/ticari olabilir ama LGPL şartları sağlanmalıdır: kullanıcı kütüphaneyi kendi sürümüyle değiştirebilmeli.
- **PyInstaller tek klasör (onedir) kullan, tek dosya (onefile) KULLANMA:** Qt/PySide6 DLL'leri ayrı dosya olarak kalır → değiştirilebilir. Onefile her açılışta geçici klasöre açıp değiştirmeyi zorlaştırır.
- Statik bağlama yok; PySide6'ya kendi koduna karıştırarak değişiklik yapma (yaparsak kaynağı yayımlamak gerekir).
- **Hakkında/README'ye:** PySide6/Qt'nin LGPLv3 olduğu, lisans metni ve kaynak koduna nereden erişileceği (qt.io / PySide6 PyPI), openpyxl (MIT) vb. bileşen lisansları.
- Qt'nin **GPL-only modülleri kullanılmaz** (QtCharts vb.; kural 5). Paketlerken kullanılmayan Qt modülleri dışlanır (hem boyut hem lisans yüzeyi).
- Faz 7'de: PyInstaller çıktısında `PySide6`/`Qt` DLL'lerinin ayrı durduğu ve yalnızca LGPL/izinli modüllerin girdiği doğrulanır; kurulum klasörüne lisans metinleri konur.

---

## Günlük

## [2026-10-08] — Faz 0: Planlama
- Kullanıcı Sözcük'ün kardeşi olarak bir Excel alternatifi istedi; ad şimdilik "Tabcel", değişebilir
- Planlama Opus 5.5 ile yapıldı: `plan.md` (8 faz, mimari, Excel uyum ilkeleri, fonksiyon listesi), `CLAUDE.md` (kesin kurallar), `surec.md`, `.gitignore`; `git init`
- Sonraki adım: Sonnet 5.5 ile Faz 1 iskeleti (§2)

## [2026-10-08] — Yeniden adlandırma
- Ad Tabcel oldu; belgeler güncellendi, klasör `tabcel` yapıldı. Henüz kod yok.

## [2026-10-08] — Faz 0: Kod iskeleti (Sonnet 5.5)
- `.venv` (Python 3.11) + PySide6/openpyxl/pytest kuruldu; `main.py` boş pencere açıyor (offscreen doğrulandı); `Tabcel.bat` pythonw ile konsolsuz başlatır
- Testler: 3 geçti. Sonraki: `tabcel/model/` adresleme (§2, madde 3)

## [2026-10-08] — Faz 1: Adresleme (Sonnet 5.5)
- `model/adres.py`: `sutun_harfe`, `harften_sutun`, `hucre_coz`, `hucre_yaz`, `aralik_coz` (normalize; `A:C`, `2:5` desteği), `aralik_yaz`, `aralik_icinde`. Satır/sütun 1 tabanlı
- Testler: toplam 29 geçti. Sonraki: Cell/Sheet/Workbook

## [2026-10-08] — Faz 1: Veri modeli ve geri al (Sonnet 5.5)
- `Hucre` değişmez (deger + kanonik formul); `Sayfa` seyrek sözlük, satır/sütun ekle-sil hücreleri ve boyutları kaydırır; `CalismaKitabi` sayfa adı büyük/küçük harf duyarsız benzersiz, son sayfa silinemez
- Geri al: komut deseni, sınır 100 adım, yeni komut yinele yığınını temizler; silme geri alınca hücreler ve boyutlar döner
- Bilerek eksik: ekle-sil sonrası formül başvurusu düzeltme (`#BAŞV!`) Faz 2'de; stiller Faz 3'te
- Testler: toplam 40 geçti. Sonraki: `ui/grid.py` (çizim + kaydırma + seçim)

## [2026-10-08] — Faz 1: Izgara çizimi ve seçim (Sonnet 5.5)
- `ui/grid.py` `Izgara(QAbstractScrollArea)`: kaydırma çubukları hücre sırasıyla (1.048.576 satır / 16.384 sütun, Excel gibi); başlıklar, çizgiler, sayı sağa/metin sola/mantıksal ortaya, seçim dolgusu + çerçeve, aktif hücre çerçevesi; `aktifDegisti`/`secimDegisti` sinyalleri
- Gezinme: oklar, Shift+ok, Ctrl+ok (veri bloğu atlama), Home, Ctrl+Home/End, PageUp/Down, Ctrl+A, Ctrl+Boşluk, Shift+Boşluk, Tab/Enter; fare: tıklama, sürükleme, Shift+tıklama, satır/sütun başlığı, sol üst köşe
- Başlıktan/Ctrl+A ile seçim kaydırmaz (`kaydir=False`); uzak hedefe (Ctrl+↓ → son satır) tek seferde atlar
- `ui/theme.py` yalnızca renkler (stil sayfası pencere işiyle gelecek). `goster()` geçici "Genel" biçim; sayı biçimleri Faz 3
- Tuzak: offscreen Qt platformunda yazı tipi yok (metin kutu görünür); metinli ekran görüntüsü için platformsuz (`QT_QPA_PLATFORM` ayarsız) `grab()` kullan. `test_iskelet`'teki Qt'siz denetim ayrı süreçte çalışır
- Testler: toplam 54 geçti. Sonraki: düzenleme + formül çubuğu + pencere

## [2026-10-08] — Faz 1: Hücre düzenleme (Sonnet 5.5)
- `model/girdi.py` (Qt'siz): `girdi_coz` (boş→sil, `'` önek→metin, `=`→formül, DOĞRU/YANLIŞ→mantıksal, sayı), `duzenleme_metni` (gidis-dönüş testli; sayı gibi metne `'` ekler)
- Sayı kuralı: ondalık virgül, binlik nokta yalnızca 3'lü gruplarla (`1.500`=1500); `1.5` şimdilik metin (Excel'de tarih olabilir → Faz 3)
- Formül şimdilik **yazıldığı gibi** `Hucre.formul`'a gider (Türkçe); kanonik İngilizceye çeviri Faz 2
- Izgara: yazarak başlama (oklar onaylar), F2/çift tık (Düzenle modu, oklar imleç), Backspace boş başlatır, Enter/Shift+Enter/Tab/Shift+Tab onaylar+gider, Esc iptal, fareyle başka yere tıklama onaylar (düzenlenen hücreye yazar), Delete seçimi temizler (yalnızca dolu hücreler gezilir), Ctrl+Z/Y; değişmeyen giriş geri al yığınına girmez; düzenleyici yazdıkça genişler; `degisti` sinyali
- Tuzaklar: Qt Tab'ı `keyPressEvent`'ten önce odak gezintisi sayar → `event()` içinde yakalanır (düzenleyici + ızgara). Testte ilk karakter ızgaraya, gerisi `focusWidget()`'e gönderilir
- **Doğrulanmadı:** Türkçe Excel'de `TRUE`/`FALSE` yazınca mantıksal olup olmadığı belirsiz; şimdilik DOĞRU/YANLIŞ ile birlikte kabul ediliyor (elle test bekliyor)
- Testler: toplam 109 geçti. Sonraki: formül çubuğu, ad kutusu, sayfa sekmeleri, durum çubuğu, ana pencere

## [2026-10-08] — Plan güncellemesi (Opus 5.5 ajan değerlendirmesi)
- Kullanıcı bir Opus 5.5 ajanının önerisini getirdi (Excel benzeri uygulama için JS kütüphaneli yol haritası); değerlendirildi: yığın değişmez, olumlu yanlar plana alındı (Kararlar)
- `plan.md`: başarı ölçütü, faz zorluk/risk tablosu + faz bitiş ölçütü, 100.000 hücre ölçümü şartı, sayfa sıralama, Faz 2 test şablonu + yerelleştirme/ayırıcı testleri + tarih seri (1900) + 15 basamak testleri + Excel web referansı, Faz 4 openpyxl uyarısı + gidiş-dönüş testleri (grafikli/resimli örnek), paketleme onedir, Solver yapılmayacaklar
- `CLAUDE.md`: kural 11, 12; kural 5 LGPL notu; "Bilinen sınırlar" güncellendi
- `surec.md`: §8 performans, §8b Excel web doğrulama listesi (kullanıcı yapacak), §9 lisans uyum notu
- Kod değişmedi; testler 109 geçiyor

## [2026-10-08] — Faz 1: Ana pencere (Sonnet 5.5)
- `ui/window.py` `Pencere`: başlık şeridi (Dosya ▸ Çıkış, Geri Al, Yinele, belge adı), ad kutusu (adres/aralık yaz → git; sürüklerken "3S x 2Sü"), formül çubuğu (Enter onaylar+aşağı, Esc vazgeçer, hücre içi düzenlemeyi aynalar), her sayfa için ayrı `Izgara` (seçim/kaydırma sayfada kalır), durum çubuğu (Hazır/Gir/Düzenle, Ortalama · Sayım · Toplam, yakınlaştırma kaydırıcısı), Ctrl+PgUp/PgDn, Ctrl+tekerlek yakınlaştırma (%10–%400, sayfa başına)
- Sayfa sekmeleri: + ekle, çift tık/sağ tık menüsüyle yeniden adlandır, sil (dolu sayfada onay; son sayfa silinmez), sürükleyerek sırala. `model/sayfa.py`: `sayfa_adi_dogrula` (Excel kuralları: ≤31 karakter, `\ / ? * [ ] :` yok, başta/sonda `'` yok, boş olamaz), `CalismaKitabi.sayfa_tasi`
- **Kararlar/sapmalar:** geri al yığını çalışma kitabı genelinde **ortak** (Excel gibi); sayfa ekle/sil/yeniden adlandır/taşı geri alınamaz, sayfa silinince yığın temizlenir (komutlar silinen sayfaya bağlı olabilir). Yeni sayfa en sona eklenir (Excel etkin sayfanın sağına ekler). Formül çubuğunda yazarken başka yere tıklanırsa değişiklik **atılır** (Excel formülde başvuru seçimi yapar — Faz 2). Sayfa yeniden adlandırınca formül güncelleme Faz 2
- `ui/theme.py`: `stylesheet()` + `baslik_cubugu_rengi()` (DWM; Win11 dışında sessiz geçer)
- Testler: toplam 129 geçti; ekran görüntüsü incelendi. Sonraki: boyutlandırma + satır/sütun menüsü, ardından pano

## [2026-10-08] — Faz 1: Satır/sütun işlemleri (Sonnet 5.5)
- Model: `Sayfa.gizli_satir/gizli_sutun` (gizliyken `genislik()/yukseklik()` 0 döner, özgün ölçü saklı kalır; ekle-sil ile kayar), `boyut_durumu()/boyut_durumu_yukle()`; komutlar: `OlcuDegis` (uygula işlevi **ya da** önceden uygulanmış eski/yeni durum — fare sürüklemesi için), `SatirEkleSil/SutunEkleSil` artık gizli durumu da geri alır. `model/olcu.py`: karakter⇄px (8,43 kar = 64 px, 7 px/kar + 5 dolgu) ve punto⇄px (15 pt = 20 px), sınırlar (genişlik 3–1790 px, yükseklik 3–545 px) — yaklaşık dönüşüm; kesin sınama Faz 4 (.xlsx)
- Izgara: başlık kenarında ±3 px'te imleç değişir, sürükleyerek boyutlandırılır (tek geri al adımı); seçili tam satır/sütunlar birlikte boyutlanır; çift tık sütunu içeriğe sığdırır (satırda metin kaydırma yokken varsayılana döner); ekle = seçili sayıda satır/sütun seçimin üstüne/soluna; sayfa sonuna dolu hücre itilecekse **reddedilir + uyarı** (Excel gibi veri kaybı yok); tek işlemde en çok 20.000 satır/sütun (gizle/boyutlandır/ekle); başlık sağ tık menüsü (Ekle, Sil, Gizle, Göster, genişlik/yükseklik diyaloğu karakter/punto cinsinden, Otomatik sığdır); `uyari` sinyali pencerede durum çubuğu + uyarı kutusu
- Sapma: boyutlandırmada alt sınır 3 px (0'a çekince gizlemek yerine); gizleme menüden/Ctrl+9,0
- Henüz yok: hücre aralığı seçiliyken Ctrl+−/+ ("hücreleri kaydır" diyaloğu), satır yüksekliğini metin kaydırmaya göre otomatik sığdırma (Faz 3)
- Testler: toplam 156 geçti. Sonraki: pano (TSV/HTML) + hücre sağ tık menüsü

*(Yeni girişler en alta eklenir.)*
