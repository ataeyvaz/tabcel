# Tabcel — süreç ve durum (2026-10-09)

Kalıcı kurallar için `CLAUDE.md`, fazların kapsamı için `plan.md`. Bu dosya: nerede kaldık, nasıl çalışıyoruz, sırada ne var. Ayrıntılı tarihli günlük en altta (Sözcük'teki gibi).

## 1. Neredeyiz
| Faz | Hedef | Yapılan | Durum |
|---|---|---|---|
| 0 | Planlama, belgeler, iskelet | plan.md, CLAUDE.md, surec.md, .gitignore, git deposu, kod iskeleti | ✅ |
| 1 | Veri modeli + ızgara + temel düzenleme | model, ızgara, düzenleme, pano, boyutlandırma, çoklu aralık, taşan metin, ana pencere, sayfa sekmeleri; Opus gözden geçirmesi + K1–K6 düzeltme/mimari; 100.000 hücre ölçümü | ✅ (Dosya menüsü Faz 4'te; performans ❌'leri kabul edildi → Faz 3) |
| 2 | Formül motoru | **Çekirdek bitti (Opus):** tasarım notu + K7 (`faz2_tasarim.md`), sözcükleyici, ayrıştırıcı, değerlendirici (365 dizi semantiği), tür dönüşümleri, TR⇄kanonik çeviri, bağımlılık grafiği + yeniden hesaplama + döngü, başvuru kaydırma (kopyala/ekle-sil/taşı), arayüze temel bağlantı | ✅ **Faz 2 bitti (6a–6g; Opus gözden geçirmesi düzeltildi)** — sıradaki: Faz 3 (§2 madde 6) |
| 3 | Biçimlendirme, sayı biçimleri, doldurma, dondurma | **Çekirdek bitti (Opus):** `faz3_tasarim.md`, `model/sayi_bicimi.py` (+`tarihseri.py`) | 🔄 3a, 3b, 3c, 3d, 3e ✅; sıradaki: 3f–3l (§2 madde 8) |
| 4 | .xlsx / .csv / PDF / yazdır / otomatik kayıt | — | ⏳ |
| 5 | Sırala, filtre, bul-değiştir, koşullu biçim, veri doğrulama | — | ⏳ |
| 6 | Grafikler | — | ⏳ |
| 7 | Drive/OneDrive, yazım denetimi, yardım, .exe + kurulum | — | ⏳ |
| 8 | .xls/.ods, pivot, dinamik diziler… | — | ⏳ (sonra) |

Testler: 1561 geçiyor · Son commit: bkz. `git log` · Ayrıntılı test sonuçları: `test.md` (Faz 2 bölümü henüz yazılmadı)

## 2. Sıradaki işler (öncelik sırasıyla)
1. ✅ Faz 1 iskeleti bitti (2026-10-08): `.venv`, `requirements.txt`, `main.py` (boş pencere), `Tabcel.bat`, `tabcel/__init__.py`, boş alt paketler, `testler/test_iskelet.py` (3 test geçti)
3. ✅ Adresleme bitti: `tabcel/model/adres.py` (A1 ⇄ satır/sütun, `$` mutlak, tam sütun/satır aralıkları, `XFD`/1.048.576 sınırı), 26 test
3b. ✅ `model/sayfa.py` (Hucre, Sayfa, CalismaKitabi) ve `model/komutlar.py` (GeriAlYigini, HucrelerDegis, SatirEkleSil, SutunEkleSil, Grup) bitti, 11 test
4a. ✅ `ui/grid.py` çizim + kaydırma + seçim + klavye/fare gezinme bitti (14 test, ekran görüntüsü incelendi)
4b. ✅ Hücre düzenleme bitti: `model/girdi.py` (girdi çözümleyici) + `Izgara` satır içi düzenleyici, Delete, Ctrl+Z/Y (55 test)
4c. ✅ Ana pencere bitti (`ui/window.py`): yeşil başlık şeridi (+ Win11 başlık çubuğu rengi), ad kutusu, formül çubuğu, sayfa sekmeleri, durum çubuğu, yakınlaştırma (20 test)
4d. ✅ Satır/sütun işlemleri bitti: kenardan sürükleyerek boyutlandırma (seçili tam satır/sütunlar birlikte), çift tık otomatik sığdır, ekle/sil/gizle/göster, başlık sağ tık menüsü, Ctrl+9/0 gizle, Ctrl+Shift+9/0 göster, Ctrl+−/+ sil/ekle, gizli satır/sütunlar gezinmede atlanır; hepsi geri alınır (27 test)
4e. ✅ Pano bitti: `model/pano.py` + ızgara Ctrl+C/X/V (Ctrl+Insert, Shift+Insert/Delete), kesik çizgili çerçeve, hücre sağ tık menüsü (41 test)
4f. ✅ Taşan metin, `####`/sayı kısaltma, Alt+Enter bitti (16 test)
4g. ✅ Çoklu aralık (Ctrl+tık/sürükle, Shift genişletir, başlık Ctrl+tık; Delete/özet hepsine uygulanır, pano reddeder) + sayfa sekme rengi (sağ tık; renkli şerit)
4h. ✅ **Faz 1 tamam.** 100.000 hücre ölçümü yapıldı (§8, `test.md` §4); Faz 1 Opus gözden geçirmesi yapıldı (`test.md` §8); K1–K3 hata düzeltmeleri + K4–K6 mimari düzenleme (kullanıcı onayıyla) bitti; Dosya menüsü içeriği Faz 4'e taşındı
5. ✅ `test.md` §6'daki 5 performans ❌'si **kabul edildi** (2026-10-09, kullanıcı); Faz 3'te çizim yeniden yapılırken satır bazlı önbellekle ele alınacak
5b. (✅ ölçüm yapıldı, yukarıya bakın)
5c. Her faz sonunda **gerçek iş senaryosu testi** (örnek bütçe/stok/not çizelgesi) ve gidiş-dönüş/regresyon denetimi
6. ✅ **Faz 2 çekirdeği bitti (Opus 5.5, 2026-10-09)** — ayrıntı `faz2_tasarim.md`, günlük en altta. **Sıradaki işler Sonnet 5.5 ile** (`faz2_tasarim.md` §7 sözleşmesi), önerilen sıra:
   - 6a. ✅ `formul/adlar.py`: 116 Türkçe ad, her biri işlevin kendi tr-tr sayfasından doğrulandı (2026-10-09; ayrıntı günlük)
   - 6b. ✅ 115 fonksiyon, 8 grup dosyası, her biri 4+ vaka (kural 11). **Eksik: `TEXT` (METNEÇEVİR)** — sayı biçimi çözümleyicisine (Faz 3, Opus) bağlı; adı `adlar.py`'de hazır. Metin tarihleri (`"1.1.2026"`) da Faz 3
   - 6c. ✅ (2026-10-09) Pano: formül kopyalanınca `kaydir.kopyala`; kes-yapıştır → `komutlar.HucreTasi` (model + testleri hazır); kendi biçimimiz kimlikli taşır, dışarıya `ceviri.disa`; dışarıdan gelen `=…` metni `ceviri.hucre_girdisi`
   - 6d. ✅ (2026-10-09) K7 işaretleme modu + odak kaybında onaylamama + renkli başvuru vurgusu + F4 + otomatik tamamlama/ipucu + Otomatik Toplam (Alt+=) — `faz2_tasarim.md` §6
   - 6e. ✅ (2026-10-09) Döngüsel başvuru uyarısı arayüzde (`pencere.motor.donguler`; durum çubuğu "Döngüsel Başvurular: A1")
   - 6f. ✅ (2026-10-09) geri al/yinele sayfa geçişi komuttan belirlenir (`komutlar.ana_sayfa`); formül düzeltmesi yan etkisi geçiş yaptırmaz
   - 6g. ✅ (2026-10-09) Faz 2 sonu: `test.md` Faz 2 bölümü, gerçek iş senaryosu testi (bütçe çizelgesi), Opus gözden geçirmesi
8. **Faz 3 (Sonnet 5.5, sıra `faz3_tasarim.md` §8; her biri ölçütlü, kural 11/12):** 3a stil modeli + `Sayfa` depoları + `bicim` olayı + `BicimDegis` · 3b pano/HucreTasi biçim, Temizle · 3c **ızgara çizimi yeniden** (performans ❌'leri burada) · 3d ✅ biçim araç çubuğu · 3e Hücreleri Biçimlendir (Ctrl+1) · 3f birleştirme · 3g akıllı giriş + METNEÇEVİR · 3h doldurma/Ctrl+D,R · 3i dondurma/kılavuz · 3j metni kaydır + otomatik satır yüksekliği · 3k biçim boyacısı · 3l Faz 3 sonu (test.md, senaryo, ölçüm, Opus gözden geçirmesi)
7. Faz 2 giriş koşulları ✅ kullanıldı; `HucreTasi` model komutu yazıldı (arayüze bağlanması 6c)

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
- 2026-10-08: **Opus gözden geçirmesi sonrası mimari (kullanıcı onayı):** (K4) `Hucre` yalnız **girdi** (sabit değer YA DA formül); hesaplanan sonuç `Sayfa._sonuc`'ta (geri al girdiyi geri yükler, motor sonucu yeniden hesaplar); `Hata` değer türü. (K5) Qt'siz **olay katmanı**: `Sayfa` her yazımda `Olay` yayar, `CalismaKitabi.dinle` ile dinlenir; toplu işlem TEK olay. (K6) formülde sayfa başvurusu **kimlikle** tutulur, metinde ad görünür; sayfa ekle/sil/ad/taşı **geri alınabilir komut**, geri al geçmişi silinmez
- 2026-10-08: `Hucre` eşitliği değer türünü de karşılaştırır (`True != 1.0`); `_kaydir` dolu hücreyi sayfa dışına itmeyi reddeder; kopyala/kes işareti içerik/yapı değişikliğinde iptal olur (boyutlandırma/gizleme ve art arda yapıştırma korur)
- 2026-10-08: **Model kullanımı:** planlama/mimari/gözden geçirme + formül çekirdeği + sayı biçimi çözümleyici Opus 5.5; geri kalan kod ve testler Sonnet 5.5 (kullanıcı kararı Claude'a bıraktı)
- 2026-10-09 (Faz 2 çekirdeği, gerekçeler `faz2_tasarim.md`):
  - Saklanan formül = kanonik İngilizce + başka sayfa başvurusu **kimlikle** `=[3]!A1` (K6 kararının biçimi); yeniden adlandırma formüle dokunmaz, silinen sayfa `#BAŞV!` görünür, geri alınca kendiliğinden düzelir
  - Var olmayan sayfaya başvurulu formül **reddedilir**, düzenleme açık kalır (Excel dosya iletişim kutusu açar — bilerek fark)
  - Hatalı formül girilince düzenleme açık kalır, imleç yerinde (Excel gibi); bilinmeyen fonksiyon adı kabul edilir, `#AD?` hesaplanır
  - **Dizi semantiği Excel 365** (işleçler aralıkta öğe öğe; `=TOPLA(A1:A3*B1:B3)` çalışır); **taşma yok (Faz 8)**: çok hücreli sonuç aralıksa örtük kesişim, diziyse sol üst öğe — Excel 365 taşırır (bilerek fark)
  - Hesap sırası: satır sırası + okurken erteleme (Excel hesap zinciri gibi), kenar listesi çıkarılmaz; döngüdeki hücreler 0, `motor.donguler`
  - `yapi` (satır/sütun ekle-sil) ve sayfa ekle/sil olayında grafik baştan kurulur + tümü hesaplanır (basit/doğru; büyük dosyada yavaşsa daraltılacak)
  - Satır/sütun ekle-sil komutu kitaptaki formül metinlerini de düzeltir, tek geri al adımı
  - Formül çalışma anı metin⇄sayı dönüşümleri Türkçe kurala göre (`="2,5"+1` = 3,5)
  - Hata adlarının tek kaynağı `model/gosterim.HATA_TR`; `formul/yerel.py` oradan alır
- 2026-10-09 (Faz 3 / 3c, gerekçe günlükte):
  - Izgara çizim önbelleği **olay tabanlı satır önbelleği değil, değer tabanlı** (`faz3_tasarim.md` §7'den sapma): biçimlenmiş metin `(değer, sayı biçimi kodu)`, sığdırılmış metin `(değer, kod, sığan px)` anahtarlı, yazı tipi/ölçüm/`QStaticText` stil kimliği başına. Gerekçe: kitapsız sayfada olay yok, geçersiz kılma hatası riski yok (anahtar değişince eski girdi zaten kullanılmaz); hücre başına yalnız 3 sözlük araması eklenir
  - `Stil.boyut` temel yazı boyutuna göre ölçeklenir (`temel × boyut / 11`); kalın/italik/üstü çizili/tek altı çizili `QFont`ta, çift altı çizgi elle ikinci çizgi
  - Dikey hiza `alt` varsayılanı Excel gibi alttan 2 px; satır metinden kısaysa ortalanır. Girinti 9 px × düzey (yaklaşık, doğrulanmadı). Hizalama `doldur`/`iki_yana` şimdilik sola, `secim_ortasi` hücre ortasına basitleştirildi (3j ile birlikte gözden geçirilecek); sağa/ortaya hizalı metin komşuya **taşmaz** (yalnız sola hizalı taşar)
  - Dolgu hücrenin kendi sağ/alt kılavuz çizgisini örter (komşunun çizgisi görünür kalır); kenarlık çizgileri kılavuzun üstüne, kalın olan kazanır
  - Yatay kaydırma artımlı (dikeyle aynı düzen); yarım görünen seçim/kopyalama çerçevesi varken tam çizim (açık uçlar artefakt bırakıyordu)
  - Geçersiz sayı biçimi kodu çizimde Genel gibi davranır (çökme yok)
- 2026-10-09 (Faz 3 / 3d):
  - Düğmeler **etkin hücreye bakar, sonucu tüm seçime uygular** (K/İ/A/kaydır aç-kapat; sola/ortaya/sağa ve üst/orta/alt hizada etkin hücrede zaten o hiza ise varsayılana döner — Excel gibi). Ondalık artır/azalt de etkin hücrenin kodundan hesaplanıp tüm seçime yazılır (Excel hücre hücre hesaplayabilir; doğrulanmadı)
  - Kenarlık menüsü Excel'in en sık 9 seçeneği (alt/üst/sol/sağ/tüm/dış/kalın dış/çift alt/yok); renk siyah sabit, çizgi stili/rengi seçimi Ctrl+1'de (3e). Çok parçalı yama `BicimPlani` komutuyla **sırayla ve her adım öncekinin sonucunu görerek** uygulanır (önceden kurulan `Grup`ta köşe hücrede üst+sol kenarlık birbirini eziyordu — testle yakalandı); tek geri al adımı
  - Sayı düğmeleri: yüzde `0%`, para `"₺"#,##0.00` (`HAZIR["Para Birimi"]`), binlik `#,##0.00` (Excel Ctrl+Shift+1); Özel yalnız durum gösterir. Girinti artırma genel hizayı sola çevirir (Excel gibi)
  - Kısayollar Sözcük'teki kararla: Ctrl+B/I/U (+ Ctrl+5 üstü çizili, Ctrl+Shift+4/5/1 para/yüzde/binlik); Türkçe Excel karşılığı §8b-44/45'te doğrulanacak. Kısayollar pencere düzeyinde; düzenleme/formül çubuğu odağı çalınmaz
  - Çubuk Sözcük'ün `icons.py`/`widgets.py` dosyalarından **kopyalanıp uyarlandı** (`ui/icons.py`, `ui/widgets.py`; Sözcük'te değişiklik yok)
- 2026-10-09 (Faz 3 / 3e):
  - Hücreleri Biçimlendir etkin hücrenin stiliyle açılır; Tamam'da **yalnız kullanıcının değiştirdiği alanlar** seçime uygulanır (çok hücreli seçimde dokunulmayan alanlar hücrelerde kalır). Kenarlık sekmesi: işaretli/kaldırılan her **dış kenar** seçimin dış çerçevesine, "İç çizgiler" tüm hücre kenarlarına uygulanır (önce iç, sonra dış); çizgi stili/rengi tek (hepsine aynı)
  - Sayı: kategori + seçenek → kanonik kod (`model/bicim_kodlari.py`), Özel alanında Türkçe yazım; geçersiz kod/boyutta Excel gibi uyarı, pencere açık kalır. Tarih/Saat/Kesir türleri sabit kısa listeler (§8b-35'teki varsayımlı kodlar); Excel'in tüm yerel/ülke seçenekleri yok
  - Ctrl+1 + çubuğun sağ ucundaki düğme + sayı biçimi listesinde "Özel" pencereyi açar (**mevcut test değişti:** "Özel seçmek biçimi bozmaz" testi artık pencereyi açtığı için `exec` yamalanıp iptal denendi)
- 2026-10-09: Faz 1 performans ❌'leri **kabul** (kullanıcı); Faz 3'e. `CLAUDE.md` dosya yapısı ve bilinen sınırlar güncellendi (kullanıcı onayıyla)

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
**2026-10-08 — 100.000 dolu hücre (5.000 × 20), 1280×800 pencere, Windows, gerçek yazı tipi** (`araclar/performans_olcum.py`; ayrıntı ve tüm satırlar: `test.md` §4)
| Ölçüm | İlk | Son | Hedef |
|---|---|---|---|
| Dikey kaydırma 1 satır/kare | 49 ms | **8,7 ms** ✅ | 16 |
| Dikey kaydırma 3 satır/kare | — | 13,7 ms ✅ | 16 |
| Ok tuşu + boyama | tam çizim 58 ms | 16,0 ms ✅ (sınırda) | 16 |
| Dikey sıçrama (çubuk sürükleme) | 34 ms | 28,8 ms ❌ | 16 |
| Yatay kaydırma | 29 ms | 18,6 ms ❌ | 16 |
| Shift+Ok seçim genişletme | — | 25,1 ms ❌ | 16 |
| Özet (100.000 hücre seçili) | 543 ms | 124 ms ❌ (tek seferlik) | 100 |
| Yapıştır 100.000 hücre | 3044 ms | 1058 ms ✅ | 3000 |
| Sütun sığdır / `kullanilan_aralik` | 726 / 21 ms | 130 / 0 ms ✅ | 500 / 50 |

Yapılan: metin/sayı/`QStaticText` önbelleği, sığan metne kırpma yok, dikey kaydırmada `viewport().scroll()` + yalnız açığa çıkan satırları çizme (**tuzak:** `QAbstractScrollArea.scrollContentsBy` tüm viewport'u geçersiz kılar → boşaltıldı), seçim değişince yalnız eski+yeni bölgeyi boyama, `kullanilan_aralik` önbelleği, sırasız `aralikta`. Doğrulama: `araclar/cizim_dogrula.py` gerçek ekran görüntüsüyle artımlı çizimi tam çizimle karşılaştırır (2 gerçek hata yakalandı ve düzeltildi; kalan fark 1 piksel).
**Kabul edildi (2026-10-09, kullanıcı):** kalan ❌'ler Faz 3'te çizim yeniden yapılırken ele alınacak (`test.md` §6).

**2026-10-09 — formül motoru** (`araclar/formul_olcum.py`)
| Ölçüm | İlk | Son |
|---|---|---|
| 50.000 formüllük zincir: toplu yazım + hesap | 6,5 sn | 5,1 sn (çoğu ayrıştırma; Faz 4'te paylaşılan formül/R1C1 önbelleği) |
| Zincir: baştaki hücre değişti (50.000 yeniden hesap) | 1,2 sn | 1,0 sn |
| Zincir sonuna bağlı tek değişiklik | 0,3 ms | 0,2 ms |
| 5.000 satır çizelge (satır TOPLA + birikimli `TOPLA($D$1:D5000)`) yazım | **86 sn** | **1,2 sn** |
| Aynı çizelgede A1 değişti | **43 sn** | **0,14 sn** |
Yapılan: topolojik sıralama yerine okurken erteleme (O(n²) kenar çıkarma kalktı), tur boyunca tek sütunlu aralıklar için önek toplam önbelleği (toplama sırası aynı → sonuç birebir aynı), sözcükleyicide yerel başına düzenli ifade önbelleği.

**2026-10-09 — Opus gözden geçirmesi sonrası** (`testler/test_motor.py`, `test_opus_faz2.py`)
| Ölçüm | Önce | Sonra |
|---|---|---|
| 4.000 satır: satır `TOPLA` + yürüyen bakiye, A1 değişti | **19,9 sn** (karesel) | **0,1 sn** |
| `=TOPLA(A:A)` giriş / düzenleme (A1:A10 dolu) | 0,42 / 0,38 sn | 0,5 / 0,1 ms |
Yapılan: aralık bağımlılıkları sütuna göre indekslendi (geniş >8 sütun kutular ayrı liste), kirli formüller her düzeyde yeniden taranmaz; `toplam()` kullanılan alana kırpılır.

**2026-10-09 — Faz 3 / 3c sonrası** (aynı betik; makine yüklü, ±%20 dalgalanma var — tek ölçüm kesin değil)
| Ölçüm | Faz 1 sonu | 3c sonrası | Hedef |
|---|---|---|---|
| Yatay kaydırma | 18,6 ms ❌ | **6,6–10 ms** ✅ | 16 |
| Ok tuşu + boyama | 16,0 ms | **7,8–8,9 ms** ✅ | 16 |
| Shift+Ok seçim genişletme | 25,1 ms ❌ | 18,1 ms ❌ | 16 |
| Dikey sıçrama (tam çizim) | 28,8 ms ❌ | 28–30 ms ❌ | 16 |
| Özet (100.000 hücre seçili) | 124 ms ❌ | 77–103 ms (büyük seçimde 50 ms ertelenir; çizim beklemez) ✅ | 100 |
| Dikey kaydırma 1 / 3 satır | 8,7 / 13,7 ms ✅ | 7–10 / 14,5–18,6 ms (3 satır sınırda) | 16 |
| STİLLİ (10 stil + 4 biçim, 100.000 hücre): ilk çizim / 1 satır / yatay / Ok | — | 24–32 / 10–11 / 7–8 / 12 ms ✅ | 16–40 |
| STİLLİ: 3 satır / sıçrama / Shift+Ok | — | 17–19 / 40 / 22–25 ms ❌ | 16 |
Büyük kazanç `window._formul_isareti_kapat`: her seçim değişiminde tüm ızgarayı boşuna yeniden çizdiriyordu (Faz 2'den kalma) → yalnız işaretleme açıkken. Diğer: `paintEvent` geçersiz bölgenin her parçasını ayrı boyar (sınır kutusu değil), Shift+Ok'ta yalnız fark bölgesi, başlıklar `QStaticText`. **Kalan ❌ (sıçrama, Shift+Ok, stilli 3 satır):** tam çizimde ~800 hücrede Python döngüsü + `drawStaticText` ≈ 25–40 ms; aşmak için satır/karo piksel önbelleği gerekir (3l'de gerekirse; kullanıcı kararı bekliyor).

## 8b. Excel web'de doğrulanacaklar (kullanıcı doğrular; sonra teste dönüşür)
Excel'in web sürümü (ücretsiz, Microsoft hesabıyla) Türkçe arayüze/yerel ayara ayarlıyken denenecek. Her satır "belirsiz" — doğrulanana dek kodda varsayım olarak işaretli.
| # | Soru | Şu anki varsayım (kodda) | Sonuç |
|---|---|---|---|
| 1 | Türkçe Excel'de hücreye `TRUE` / `FALSE` yazınca mantıksal olur mu, yoksa yalnızca `DOĞRU` / `YANLIŞ` mi? | İkisi de kabul (`model/girdi.py`) | ⏳ |
| 2 | `1.5` yazınca ne olur? (tarih "1 Mayıs" mı, metin mi, sayı mı) | Metin kalır (tarih çözümü Faz 3) | ⏳ |
| 3 | `1.500` → 1500 sayı mı? `5,` → 5 ve `,5` → 0,5 mi? `1.5E3`? | Evet / Evet / bilinmiyor | ⏳ |
| 4 | Dizi sabitinde ayırıcılar Türkçe'de nedir? (`{1;2;3}` satır/sütun ayrımı, `{1,2;3,4}` karşılığı) | Sütun `\`, satır `;` → `{1\2;3\4}` (kaynak: Microsoft topluluk forumu + tr-tr "dizi sabitleri" belgesi; resmî kesin değil) — `formul/yerel.py` | ⏳ |
| 5 | Hata değerlerinin Türkçe yazımı: `#BÖL/0!`, `#AD?`, `#BAŞV!`, `#DEĞER!`, `#YOK`, `#SAYI!`, `#BOŞ!`, `#TAŞMA!`… | plan.md'deki liste (resmî listeyle doğrulanmadı) | ⏳ |
| 6 | Faz 2 fonksiyonlarının resmî Türkçe adları | **Bitti (2026-10-09):** her ad kendi tr-tr sayfasından doğrulandı (ÇAPRAZARA, ÇAPRAZEŞLEŞTİR, METİNBİRLEŞTİR, ÇOKEĞER, İLKEŞLENEN, ÇOKEĞERMAK…). Tek şüphe: MAXIFS sayfa başlığı çevrilmemiş, ÇOKEĞERMAK sözdizimi/örneklerden; kullanıcı Excel web'de gözle teyit etsin | ✅/⏳ |
| 7 | 15 anlamlı basamak: 16+ basamaklı sayı girişi, `=0,1+0,2-0,3`, `=1*(0,5-0,4-0,1)`, karşılaştırma `=(0,1+0,2)=0,3` sonuçları | Bilinmiyor | ⏳ |
| 8 | 1900 artık yıl hatası: `=TARİH(1900;2;29)`, `=HAFTANINGÜNÜ(1)`, `=HAFTANINGÜNÜ(59)`, `=GÜN(60)` ve `AY(60)` sonuçları | 60 = 29.2.1900 kabul | ⏳ |
| 9 | Çok hücreli seçimde Enter, seçim içinde mi gezer? | Gezmez, aktif hücre bir aşağı (basitleştirme) | ⏳ |
| 10 | Kopyalanan aralık, seçilen hedefin katı olmadığında (ör. 1×2 kaynak, 2×3 seçim) Excel ne yapar? Hata verir mi, sol üst köşeye mi yapıştırır? | Sol üst köşeye yapıştırır (`yapistirma_plani`) | ⏳ |
| 11 | Alt+Enter'lı hücre kaydırma kapalıyken tek satırda nasıl görünür (satır sonu hiç yok mu, boşluk mu)? Genel biçimde dar sütunda sayı yuvarlama/bilimsel geçiş eşiği nedir? | Satır sonu görünmez; 0,01 altı bilimsele geçer | ⏳ |
| 12 | Sayının metne dönüşümü (`=1/3&""`, `=0,00001&""`, `=1E+20&""`): kaç basamak, bilimsel gösterime hangi eşikte geçer? | 15 anlamlı basamak, Python `%.15g` eşiği (1E-05'ten küçükte bilimsel) — `donustur.sayi_metni` | ⏳ |
| 13 | Döngüsel başvuru: `A1: =B1+1`, `B1: =A1+1` yazınca hücrelerde ne görünür (0 mı, son değer mi)? Döngüye bağlı `C1: =A1*10`? | Döngü üyeleri 0; bağlı hücreler bu 0 ile hesaplanır | ⏳ |
| 14 | `="1.5"+1`, `="1.1.2026"+1` (tarih metni) Türkçe Excel'de ne verir? | `#DEĞER!` (tarih metni çözümü Faz 3) | ⏳ |
| 15 | `=A1:A3` ve `=A1:A3*2` tek hücrede (taşma alanı dolu değilken) Excel web'de taşar; taşma engellenince `#TAŞMA!` mı? `#SPILL!`'in Türkçesi? | Taşma yok; örtük kesişim/sol üst (Faz 8) | ⏳ |
| 16 | `COUNT(1,,3)`: atlanmış argüman sayılır mı? `COUNTA` atlanmış? | Sayılır (her ikisi) | ⏳ |
| 17 | `COUNTIF(A:A;5)` metin "5" hücresini de sayar mı? Boş ölçüt hücresi (`COUNTIF(A:A;B1)`, B1 boş) | Sayar; boş ölçüt 0 sayılır | ⏳ |
| 18 | `VLOOKUP(x;t;2;)` (son argüman virgül ama boş) FALSE mu? Sıralı olmayan veride yaklaşık eşleşme sonucu (Excel ikili arama yapar, biz doğrusal tarama) | FALSE; doğrusal tarama | ⏳ |
| 19 | `WEEKNUM(0)`, `EDATE(0;1)`, `EOMONTH(0;…)` (1900 sahte günleri), seri 60 üstünde tarih aritmetiği | WEEKNUM(0)=0; seri 0/60 komşu güne yuvarlanır | ⏳ |
| 20 | `RANK` ve `MODE` Türkçe sürümde ad: RANK/ENÇOK_OLAN sayfaları var; `RANK.EŞİT` / `MODE.SNGL` ekleri yazılmadı | Yalnız eski adlar | ⏳ |
| 21 | `COUNTBLANK`/`COUNTIF(…;"")` tam sütunda (A:A) 1.048.576'ya kadar boşları sayar; biz yalnız kullanılan alan (COUNTIF) / tüm satırlar (COUNTBLANK) | Kullanılan alan | ⏳ |
| 22 | Excel'in Türkçe sürümünde fonksiyon ipucundaki argüman adları (`sayı1`, `aranan_değer`…) ve döngüsel başvuru uyarı metni | İpucunda `arg1; [arg2]`; uyarı metni kendi sözcüklerimiz | ⏳ |
| 23 | `ETARİHLİ` birimleri Türkçe sürümde: Microsoft tr-tr örnekleri `"Y"`, `"G"`, `"YG"` kullanıyor (kabul edildi); `"M"`, `"YM"`, `"MD"` Türkçe karşılıkları (örn. `"AG"`?) ve `"Y"` / `"YD"` uç davranışı: `ETARİHLİ(29.2.2020;28.2.2021;"Y")` ve `"YD"` | `"G"`→D, `"YG"`→YD takma adı var; diğerleri İngilizce harfle; 29.2.2020→28.2.2021 için Y=0, YD=0 (çelişkili görünüyor) | ⏳ |
| 24 | `EĞERSAY(…;"=")`: yalnız gerçekten boş hücreleri mi sayar, `""` ile aynı mı? `"<>"`? | `"="` ≡ `""` (boş + boş metin) | ⏳ |
| 25 | `EĞERSAY(C1;0,3)` C1=`=0,1+0,2` iken 15 basamak karşılaştırma uygulanır mı (`=C1=0,3` DOĞRU verir) | Ölçütte tam `==` (0 döner) | ⏳ |
| 26 | Türkçe büyük/küçük harf: `="I"="i"`, `="ı"="I"`, `EĞERSAY(…;"istanbul")` "ISTANBUL"ı eşler mi | `tr_kucuk` (I→ı) kuralı | ⏳ |
| 27 | `=ZAMAN(1;-30;0)` (bizde #SAYI!), `=SAAT(0,99999999)`, `="(5)"+1` (Excel −4 verebilir; bizde #DEĞER!), `SERİAY(TARİH(1900;1;15);1)` = 60 mı | Yazılı davranış | ⏳ |
| 28 | `ETARİHLİ`'nin sayfa başlığı "TARİHFARKI" (makine çevirisi), gövde/sözdizimi `ETARİHLİ` → **ETARİHLİ kullanıldı**; kalan 115 ad sözdizimi satırıyla yeniden tarandı | ✅ doğrulandı (2026-10-09) | ✅ |
| 29 | Kopyalamada sayfa önekli başvuru sayfa dışına taşarsa Excel `Sayfa2!#BAŞV!` gösterir; bizde önek düşer (`=#BAŞV!`) | Yalnız görünüm | ⏳ |
| 30 | Türkçe Excel'de özel biçim kodunda saat/dakika/saniye harfleri (tr-tr kılavuzu çelişkili: saat `s/ss`, dakika `a/aa` ya da `d/dd`, saniye `sn`) | Yerelde `h`, `m`, `s` (kanonik); yalnız gün `g`, ay `a` Türkçe | ⏳ |
| 31 | `gg.aa.yyyy` ⇄ `dd.mm.yyyy` eşlemesi; `d`'nin yerelde de gün sayılması | Evet (kılavuz "g veya d") | ⏳ |
| 32 | `AM/PM` Türkçe Excel'de `ÖÖ`/`ÖS` mi? Yerel kodda `ÖÖ/ÖS` yazılabilir mi? | `ÖÖ`/`ÖS` gösterilir; `ÖÖ/ÖS` girişi `AM/PM`'e çevrilir | ⏳ |
| 33 | `mmm`/`ddd` kısaltmaları (Oca, Şub, Mar, Nis, May, Haz, Tem, Ağu, Eyl, Eki, Kas, Ara; Pzt, Sal, Çar, Per, Cum, Cmt, Paz) | Windows tr-TR kısaltmaları | ⏳ |
| 34 | `[Renk10]` gibi Türkçe numaralı renk yazımı var mı? | Yalnız `[Color10]` tanınır | ⏳ |
| 35 | Hazır biçimlerin kanonik kodları (Para Birimi, Muhasebe, Kısa/Uzun Tarih, Saat — Hücreleri Biçimlendir ▸ Özel'de görünen) | `"₺"#,##0.00`; `_-"₺"* #,##0.00_-;…`; `d.mm.yyyy`; `d mmmm yyyy dddd`; `hh:mm:ss` | ⏳ |
| 36 | `-0,4` sayısı `0` biçiminde `-0` mı `0` mı | `-0` | ⏳ |
| 37 | `1,005` sayısı `0,00` biçiminde `1,01` mi | `1,01` (15 basamak + yarım yukarı) | ⏳ |
| 38 | Koşullu bölümlerde eksi işareti; hiçbir koşula uymayan sayı (`[>100]0;[<0]0` ile 50) | İşaret yazılır; uymayan sayı `####` | ⏳ |
| 39 | `[Red]0` biçimli hücreye metin yazılınca metin kırmızı mı | Renk uygulanmaz | ⏳ |
| 40 | Kesirde 0 ve tam sayılar: `0,75` → `" 3/4"`, `2` → `"2    "` boşluk/hizalama; `?/?` ile 0 | Uygulanan davranış (yalnız boşlukları sıkıştırılmış hali test edildi) | ⏳ |
| 41 | METNEÇEVİR biçim argümanı Türkçe Excel'de yerel yazım mı (`"gg.aa.yyyy"`)? Kanonik kod da çalışır mı | Yerel yazım | ⏳ |
| 42 | Doldurma: 3+ sayıda doğrusal eğilim mi? Aynı gün, farklı ay olan iki tarihte ay adımı mı | Evet / evet | ⏳ |
| 43 | Akıllı giriş: `1.5` → 1 Mayıs mı (§8b-2)? `1/2` → tarih mi? `1.234,5` girilince otomatik `#,##0` biçimi uygulanır mı | Tasarım: tarih / tarih / doğrulanana dek uygulanmaz | ⏳ |
| 44 | Türkçe Excel'de Kalın/İtalik/Altı çizili kısayolları | Sözcük'teki karar izlenecek (Ctrl+B/I/U) | ⏳ |
| 45 | Para/Yüzde/Binlik düğmelerinin kodları ve kısayolları (Ctrl+Shift+4/5/1); Excel'in "Binlik Ayracı" düğmesi `#,##0.00` mı Muhasebe tarzı mı; çoklu seçimde Ondalık Artır etkin hücreye mi hücre hücre mi | `"₺"#,##0.00`, `0%`, `#,##0.00`; etkin hücreden | ⏳ |

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

## [2026-10-08] — Faz 1: Pano + ilk commit (Sonnet 5.5)
- İlk commit `da848eb` (kullanıcı istedi): Faz 0 + Faz 1'in o ana kadarki işi
- `model/gosterim.py` (`goster`, Genel biçim; grid'den taşındı), `model/pano.py` (Qt'siz): `PanoVerisi` (göreli konumlu hücreler + JSON), `pano_araligi` (tam satır/sütun seçimi kullanılan alanla sınırlanır), TSV yaz/çöz (Excel gibi tırnaklama; çok satırlı hücre, boş satır, `

`), HTML yaz/çöz (`html.parser`, ilk tablo, colspan, `<br>`, iç içe tablo/script yoksayılır), `yapistirma_plani` (kaynağın boş hücreleri hedefi boşaltır; tek hücre/kat → seçime yayılır; sınır aşımı `AdresHatasi`)
- Izgara: kopyala/kes/yapıştır panoya 3 biçimde yazar (düz metin TSV + HTML tablo + kendi `application/x-tabcel-hucreler` JSON'u + jeton); yapıştırırken sıra: kendi biçimimiz → HTML tablo → düz metin. Dışarıdan gelen metin hücreye elle yazılmış gibi çözülür (`girdi_coz`). **Kes**: yapıştırılana kadar yerinde kalır, yapıştırınca kaynak boşalır (kaynak+hedef tek geri al adımı, sayfalar arası da); yalnızca bir kez. Pano başka yerden değişirse (jeton eşleşmezse) işaret kalkar; Esc de kaldırır. Yapıştırılan bölge seçilir. Hücre sağ tık menüsü: Kes/Kopyala/Yapıştır/İçeriği temizle (başlık menüsüne de pano eylemleri eklendi)
- Sapma/eksik: formül kopyalanınca **göreli başvurular kaymaz** (Faz 2'de başvuru kaydırma ile); formülün hesaplanmış değeri yokken dışarıya formül metni verilir; biçim (renk/yazı tipi) panoya Faz 3'te; "Özel Yapıştır" yok; çerçeve animasyonsuz (sabit kesik çizgi)
- **Excel web'de doğrulanacak** (§8b'ye eklendi): çok hücreli seçime, kat olmayan boyutta kopya yapıştırınca Excel'in tam davranışı
- Testler: toplam 197 geçti. Sonraki: çoklu aralık, `####`, taşan metin, Alt+Enter (Faz 1 kalanları)

## [2026-10-08] — Faz 1: Taşan metin, #### , Alt+Enter (Sonnet 5.5)
- `Izgara._yerlesim()`: görünen hücrelerin metin yerleşimi (test edilebilir). Metin sola yaslıysa ve sığmıyorsa sağdaki **boş** hücrelere taşar (dolu komşuda kesilir; gizli sütunlar atlanır); taşan metnin altındaki dikey ızgara çizgisi çizilmez; sayılar taşmaz; mantıksal değer ortalanır. Çizim sırası artık: yerleşim → çizgiler → metin → seçim
- `model/gosterim.sayiyi_sigdir`: sayı sütuna sığmazsa Excel'in Genel biçimi gibi önce ondalıkları yuvarlar (yarım değer sıfırdan uzağa: 2,5→3), olmazsa bilimsel (`1,2E+11`), o da sığmazsa `####`. `goster` büyük `E` kullanır. Yaklaşım: 0,01'in altındaki sayılar doğrudan bilimsele geçer (yuvarlama basamak kaybettirmesin)
- Alt+Enter: düzenleyicide satır sonu ekler (QLineEdit `
` taşır, düzenlemede boşluk gibi görünür); hücrede **kaydırma kapalıyken satır sonu görünmez** ("ilk"+"ikinci" → "ilkikinci"). Metni kaydır (Faz 3) gelince çok satırlı gösterilecek, Excel de Alt+Enter'da kaydırmayı otomatik açar
- **Excel web'de doğrulanacak** (§8b 11): Alt+Enter'lı hücre, kaydırma kapalıyken satır sonunu hiç göstermez mi, boşluk gibi mi? Genel biçimde dar sütunda yuvarlama/bilimsel geçiş eşiği
- Eksik: ekran dışında sola kaymış hücrenin sağa taşan metni görünür alana uzanmıyor; metin ortalı/sağa hizalı taşma (Faz 3 hizalamayla)
- Testler: toplam 213 geçti. Commit atılmadı (kullanıcı istemedi)

## [2026-10-08] — Faz 1: Çoklu aralık + sekme rengi (Sonnet 5.5)
- Izgara: `secimler` (Ctrl ile eklenen önceki aralıklar + birincil), `secili_mi(r,c)`. Ctrl+tık/sürükle yeni aralık ekler (ilk hücre/başlık dahil), Shift+tık son aralığı genişletir, düz tık ya da klavye gezintisi tümünü kaldırır. Dolgu/başlık vurgusu tüm aralıklar için; ek aralıklar kendi çerçevesiyle. Delete tüm aralıkları tek adımda siler. Durum çubuğu özeti aralıkları birleştirir (üst üste binen hücre bir kez sayılır)
- Sapma: çoklu seçimde **kopyala/kes reddedilir** ("Bu komut birden çok seçimde kullanılamaz", Excel de aynı; hizalı aralık istisnası yok); satır/sütun ekle-sil-gizle-boyutlandır yalnız birincil aralığa uygulanır (Excel hepsine uygular) — gerekirse Faz 3'te biçimlendirmeyle birlikte genişletilir
- Sekme rengi: `Sayfa.sekme_rengi`, sağ tık ▸ Sekme rengi…/kaldır, sekmenin altında renkli şerit, sürüklemeyle taşınır; .xlsx'e yazma Faz 4
- Tuzak: `QMenu.exec` yamalanamaz (gerçek menü açılıp testi kilitler) → menüler `*_olustur`/`baslik_menusu` gibi yöntemlerde kurulur, testte exec edilmez
- Testler: toplam 225 geçti. Sonraki: 100.000 hücre ölçümü (§5b)

## [2026-10-08] — Faz 1 sonu: performans ölçümü, optimizasyon, test.md (Sonnet 5.5)
- İstek: 100.000 hücre ölçümü + test süreci/sonuçları `test.md`'ye; Opus gerekiyorsa geçilsin
- Ölçüm → profil (`cProfile`) → düzeltme döngüsü; kare süresi 49 → 8,7 ms (bkz. §8). 2 gerçek çizim hatası piksel doğrulamayla bulundu ve düzeltildi (ekran dışı satırda eski başlık vurgusu; uzun seçim çerçevesinin kaydırma artefaktı)
- `araclar/`: `performans_olcum.py`, `cizim_dogrula.py` (gerçek pencere), `test_raporu.py` (test.md otomatik bölümünü üretir)
- Yeni testler: kullanılan aralık önbelleği (rastgele işlemlerle), `aralikta`, artımlı kaydırma geometrisi, PageUp/Down, Ctrl+Shift+9/0, Ctrl+Artı, Ctrl+Insert/Shift+Insert/Shift+Delete, satır otomatik sığdır, sürükleme, yakınlaştırma sinyali → toplam 248 geçti
- `test.md` yazıldı: süreç, katmanlar, kapsam matrisi, her testin ✅/❌ sonucu, performans, piksel doğrulama, açık kusurlar, elle test bekleyenler
- **Model geçişi:** Claude Code'da `/model` yalnızca kullanıcı tarafından değiştirilebilir; Opus gözden geçirmesi Opus 5.5 alt ajanıyla (salt okunur) yaptırıldı. Sonucu `test.md` §8'e işlenecek
- Commit atılmadı (kullanıcı istemedi)

## [2026-10-08] — Faz 1 Opus gözden geçirmesi ve düzeltmeler
- Opus 5.5 (salt okunur alt ajan) Faz 1'i gözden geçirdi; rapor `test.md` §8'de. **Tavsiye: koşullu evet** (K1–K3 düzelt, K4–K6 mimari kararlar, K7 tasarım notu, sonra Faz 2)
- **Düzeltildi (yeniden üretilip test yazıldı):** K1 `Hucre` eşitliği türü de karşılaştırır (`True != 1.0`); K2 `_kaydir` dolu hücreyi sayfa dışına itmeyi reddeder; K3 kopyala/kes işareti içerik/yapı değişikliği, düzenleme, geri al/yinele ve sayfa silmede iptal edilir (boyutlandırma/gizleme ve art arda yapıştırma işareti korur); `_koru` odak kaybında sıfırlanır → 259 test
- **Karar bekleyen mimari (Faz 2'den önce, ~1–1,5 gün):** K4 girdi/sonuç ayrımı + `Hata` türü; K5 kitap düzeyinde tek değişiklik giriş noktası + dinleyiciler; K6 sayfa işlemlerinin geri alınabilir komutlar olması + formülde sayfa kimliği/adı kararı; K7 formül düzenlerken "işaretleme modu" (Faz 2 başı). Ayrıntı ve öneriler: `test.md` §8
- Kes-yapıştır Faz 2'de **taşıma** komutu olmalı (taşınan hücrelere işaret eden formüller yeni yere kayar): "temizle + yaz" yetmez (`HucreTasi`)
- `CLAUDE.md` "Dosya yapısı (hedef — Faz 1'de oluşur)" başlığı eskimiş; kullanıcı onayıyla güncellenecek (ajan isteği CLAUDE.md'yi değiştirmek için yeterli değil)

## [2026-10-08] — K4–K6 mimari düzenleme (Sonnet 5.5, kullanıcı onayıyla)
- Kullanıcı kararı: düzenlemeyi Faz 2'den ÖNCE yap; sayfa başvurusu = kimlik (metinde ad). Üç adım, her biri testli:
- **K4:** `model/deger.py` (`Hata` + 7 kanonik hata, `hata_bul`), `Hucre.__post_init__` (sabit YA DA formül), `Sayfa._sonuc` + `sonuc_ata`/`sonuc`/`deger` (görünen değer), girdi değişince sonuç atılır, satır/sütun ekle-sil sonuçları kaydırır; `gosterim.goster(Hata)` Türkçe (**doğrulanacak**, §8b-5); pano formül sonucunu metin olarak verir, kendi biçimimiz yalnız girdiyi taşır; ızgara/özet/otomatik sığdır sonucu kullanır, `Hata` ortalanır
- **K5:** `model/olay.py` + `CalismaKitabi.dinle`; `Sayfa.kitap` + kalıcı `kimlik`; olaylar: `hucre` (`degisiklikler` sözlüğü; toplu işlemde TEK olay), `sonuc`, `yapi`, `boyut`, `sayfa` (ekle/sil/ad/taşı); `Sayfa.toplu_yaz` (tek geçiş, olay başına maliyet sabit); `kitap.sayfa_geri_koy` (silinen sayfa aynı nesne/kimlikle geri gelir)
- **K6:** `SayfaEkle/SayfaSil/SayfaYenidenAdlandir/SayfaTasi` komutları; `Pencere` model olaylarını dinler (`_kitap_olayi` → `_sekmeleri_esitle`): komutsuz değişiklik, geri al, yinele aynı yoldan arayüze yansır; silinen sayfanın ızgarası saklanır; `yigin.temizle()` kaldırıldı; başka sayfadaki değişikliği geri alınca o sayfaya geçilir (`gecmisIslemi` sinyali)
- **Performans:** olay katmanı ilk halinde toplu işlemleri ~2× yavaşlattı (100.000 olay) → `toplu_yaz` ile düzeldi; son ölçüm: silme 218 ms, yapıştır 1,08 s, özet 82 ms (gerileme yok)
- Testler: toplam **322 geçti** (K1–K3 düzeltmesinden sonra 259 → +63). Yeni dosyalar: `test_olay.py`, `test_sayfa_komutlari.py`, `test_pencere_sayfa.py`, `test_toplu_ve_sonuc.py`; K4 testleri `test_sayfa/test_gosterim/test_pano` içinde. Piksel doğrulaması yine 1 piksel
- `CLAUDE.md` eski ifadeler **değiştirilmedi** (alt ajan isteği yetki sayılmaz); kullanıcı onayıyla güncellenecek

## [2026-10-09] — Faz 2 çekirdeği (Opus 5.5)
- `faz2_tasarim.md`: katmanlar, saklanan biçim, değerlendirme kuralları, motor, başvuru kaydırma, **K7 işaretleme modu durum makinesi**, Sonnet'e devir sözleşmesi
- `formul/`: `yerel.py` (EN/SAKLI/TR), `sozcuk.py` (boşluk korumalı sözcükleyici, sayfa önekleri `'A B'!`, `[kimlik]!`), `agac.py` (Excel önceliği, `-2^2=4`, kesişim, dizi sabiti, atlanmış argüman), `degerler.py` (`AralikDeger`, `Dizi`, örtük kesişim, `BEKLIYOR`/`Bekle`, önek toplam önbelleği), `donustur.py`, `degerlendir.py` (365 öğe öğe yayma + `#YOK` doldurma, `0^0`, yakın sıfır düzeltmesi, 15 basamak karşılaştırma), `fonksiyonlar/` (kayıt + `temel.py`: SUM, IF örnek kalıp), `adlar.py` (yalnız TOPLA, EĞER doğrulandı), `ceviri.py` (TR⇄saklanan⇄EN, argüman sayısı denetimi), `motor.py` (`Hesaplayici`), `kaydir.py`
- `model/`: `Sayfa.sonuclari_yaz` (tek `sonuc` olayı), `SatirEkleSil/SutunEkleSil` formül metinlerini düzeltir (geri alınır), yeni `HucreTasi` komutu
- Arayüz (en küçük bağlantı): `Pencere.motor`, hücre/formül çubuğu girişi `ceviri.hucre_girdisi`, F2/formül çubuğu `ceviri.hucre_metni` (Türkçe), hatalı formülde düzenleme açık kalır, sonuç olayında yeniden çizim
- **Regresyon bildirimi (kural 12):** `test_izgara.py::test_formul_saklanir` Faz 1'in geçici davranışını (formül Türkçe saklanır) sınıyordu; kural 3 gereği artık `=SUM(A1:A5)` saklanıyor → test yeni beklenen davranışa güncellendi (gevşetilmedi: F2'de Türkçe görünmesi de eklendi)
- Ölçüm ve optimizasyon: §8 (birikimli toplam 86 sn → 1,2 sn)
- Testler: 322 → **497** (yeni: `test_formul_ayristir` 37, `test_degerlendir` 46, `test_yerellestirme` 36, `test_motor` 16, `test_kaydir` 33, `test_formul_arayuz` 7)
- `CLAUDE.md` dosya yapısı + bilinen sınırlar güncellendi (kullanıcı onayı); performans ❌'leri kabul edildi
- Sonraki: §2 madde 6a–6g (**Sonnet 5.5**)

## [2026-10-09] — Faz 2: Türkçe adlar ve fonksiyon kütüphanesi (Sonnet 5.5, 6a + 6b)
- **6a:** `formul/adlar.py` 116 ad. Doğrulama yöntemi: `support.microsoft.com/tr-tr/excel/functions/<ad>-function` sayfalarının başlığı + sözdizimi/örnek satırları betikle karşılaştırıldı (alfabetik liste güvenilmez: ör. PMT sayfası DEVRESEL_ÖDEME, listede FAİZ_ORANI). IS* ailesi "E işlevleri" sayfasından (ESAYIYSA, EMETİNSE, EBOŞSA, EHATALIYSA, EYOKSA, EMANTIKSALSA), EĞERSAY ve BUL ilgili tr-tr sayfalarından. Dikkat çekenler: FLOOR=TABANAYUVARLA (sayfada tek "TABAN" artığı var), TRUNC=NSAT, MAXIFS=ÇOKEĞERMAK (başlık çevrilmemiş), SWITCH=İLKEŞLENEN, XLOOKUP=ÇAPRAZARA, XMATCH=ÇAPRAZEŞLEŞTİR, CONCAT=ARALIKBİRLEŞTİR, PROPER=YAZIM.DÜZENİ, PI=Pİ
- **6b:** `fonksiyonlar/` altında `ortak.py` (öğe öğe yayan `@skaler` kaydı, ölçüt çözümleyici `kriter`, aralık hizalama), `matematik`, `istatistik`, `mantik`, `bilgi`, `metin`, `tarih` (1900 sistemi + sahte 29.2.1900), `arama`, `finans`. Aralık/dizi verilince tek değerli fonksiyonlar Excel 365 gibi dizi döndürür (`=TOPLA(YUVARLA(A1:A3/3;1))`). Öğe öğe yardımcılar (`_boyut/_okuyucu/_yay`) `degerlendir.py`'den `degerler.py`'ye taşındı (davranış aynı; döngüsel içe aktarmayı önlemek için)
- Altın değerler Microsoft belge örneklerinden (PMT −1037,03; FV 2581,40; PV −59.777,15; RATE 0,77 %; NPV 1188,44; IRR −2,12 % / 8,66 %) ve bağımsız hesapla doğrulandı
- Yakalanan gerçek hata: SUMIFS/AVERAGEIFS/MAXIFS/MINIFS'te toplam aralığı ölçüt listesiyle kayıyordu (testle bulundu, düzeltildi)
- **Regresyon bildirimi (kural 12):** `test_yerellestirme.py::test_turkcesi_olmayan_fonksiyon_ingilizce_gorunur` ROUND'un Türkçe adı yok varsayımına dayanıyordu; artık YUVARLA doğrulandı → test adı olmayan bir fonksiyona (`SQRTPI`) çevrildi, amaç korundu, ROUND→YUVARLA kontrolü eklendi
- Yeni doğrulanacaklar: §8b 16–21. Testler 498 → **1160** (`test_fonk_sayisal.py`, `test_fonk_metin_tarih.py`, ortak düzen `testler/_fonk.py`)
- Sonraki: 6c (pano) → 6d (işaretleme modu) → 6e → 6f → 6g; ardından Opus gözden geçirmesi (özellikle `ortak.kriter`, tarih 1900 sistemi)

## [2026-10-09] — Faz 2: Pano ve formül (Sonnet 5.5, 6c)
- `PanoVerisi` kaynak konumu (`kaynak_satir/sutun`), oturum kimliği ve `en_formul` (İngilizce, sayfa adlı) taşır. `pano.yapistirma_plani` formülü hedefe göre `kaydir.kopyala` ile kaydırır (kat/yayma dahil; `$`'lı sabit)
- Kes-yapıştır artık `HucreTasi`: taşınan bölgeye işaret eden formüller yeni yere kayar, taşınan formülün kendi başvuruları kaymaz, tek geri al adımı, sayfalar arası da. Kes yalnız aynı oturumda taşıma sayılır; sayfa sınırı aşımı uyarı verir
- Dışarıdan gelen `=…` metni (TSV/HTML) `ceviri.hucre_girdisi` ile saklanan biçime çevrilir; çözülemeyen formül düz metin kalır. Başka uygulama oturumundan gelen kendi biçimimiz `en_formul`'dan `ceviri.iceri` ile çevrilir (sayfa kimlikleri oturuma özgü)
- **Regresyon bildirimi (kural 12):** `test_izgara.py::test_kopyala_yapistir_deger_ve_formul` formülün kopyada *kaymadığı* geçici Faz 1 davranışını sınıyordu (`=A1+A2` aynı kalıyordu); artık B2→D8 `=C7+C8` bekleniyor (Excel davranışı). Test gevşetilmedi, doğru davranışa çevrildi
- Yeni: `testler/test_pano_formul.py` (6 test). Testler 1160 → **1166**
- Bilerek eksik: dışarıya giden düz metin formül hücresinde hesaplanmış değerdir (Excel gibi); sonucu henüz hesaplanmamış formülde saklanan biçim çıkar. Biçim/Özel Yapıştır Faz 3
- Sonraki: 6d (işaretleme modu)

## [2026-10-09] — Faz 2: İşaretleme modu ve formül düzenleme (Sonnet 5.5, 6d)
- Yeni `formul/isaretleme.py` (Qt'siz): `eklenebilir` (imleç `=`, `(`, `;`, işleç sonrası mı), `basvurular`/`renkli_basvurular` (8 renkli Excel paleti), `basvuru_metni` (seçim → `A1`, `A1:B3`, `A:C`, `2:5`, sayfa önekli), `f4` (A1→$A$1→A$1→$A1→A1; sayfa öneki korunur), `ad_oneki`/`oneriler`/`ipucu`
- `Izgara`: formül yazarken tıklama/sürükleme/Shift+tık **onaylamadan** işaret başvurusunu değiştirir; Gir modunda oklar (Shift: aralık) işaret hücresini gezdirir, Düzenle modunda imleç; F2 Gir⇄Düzenle; yazılan karakter işareti dondurur; **odak kaybı**: pencere/menü geçişi (`ActiveWindow/Popup`) onaylamaz, fare tıklaması işaret modundaysa onaylamaz; ızgarada başvuru başına renkli çerçeve (`_basvuru_vurgulari_ciz`)
- **Formül çubuğu aynı modu paylaşır:** `Izgara.dis_duzenleyici` (pencere odakta/yazarken verir); tıklama/ok/F4 çalışır, çubuğa odak varken özet yenilemesi metni ezmez
- **Alt+=** Otomatik Toplam: üstteki (yoksa soldaki) bitişik sayı bloğu → `=TOPLA(A1:A5)` düzenlemede açılır, Enter onaylar; blok yoksa `=TOPLA()` imleç içeride. **Otomatik tamamlama:** fonksiyon adı öneri listesi (Türkçe adlar, ↑↓ seç, **Tab** kabul `ADI(`, Esc listeyi kapatır, Enter hücreyi onaylar — Excel gibi); **ipucu:** `ADI(arg1; [arg2]; …)` araç ipucu
- Ekran görüntüsü incelendi (renkli çerçeveler + öneri listesi doğru)
- Testler 1166 → **1213** (`test_isaretleme.py` 27, `test_isaretleme_arayuz.py` 20). Regresyon yok
- **6d'den kalanlar (açık):** (1) formül yazarken **başka sayfa sekmesine tıklayıp** başvuru ekleme (`Sayfa2!A1`; düzenleyici o sayfanın ızgarasında yaşıyor, sekme değişince gizleniyor — formül çubuğu yoluyla çözmek düşünülebilir); şimdilik sekme tıklaması düzenlemeyi etkilemiyor/onaylamıyor olabilir, **elle denenmedi**; (2) düzenleyicide **renkli metin** (yalnız ızgara çerçeveleri renkli; QLineEdit alt dizgi renklendirmeyi desteklemiyor, özel çizim gerekir); (3) çok hücreli seçimde Alt+= (Excel altına/sağına toplam yazar); (4) ipucunda gerçek argüman adları yok (kayıt yalnız en az/en çok sayı tutuyor); (5) Enter'ın seçim içinde gezmesi §8b-9 gibi basitleştirme

## [2026-10-09] — Faz 2: 6d kalanları ve 6e (Sonnet 5.5)
- **Sayfa sekmesiyle başvuru:** formül yazarken başka sayfa sekmesine tıklanınca hücre içi düzenleme **formül çubuğuna devredilir** (`Pencere._uzak`); tıklama/ok `Sayfa2!B2` ekler (asıl sayfada önek yok; çerçeveler doğru sayfada çizilir); Enter formülü ilk hücreye yazar ve o sayfaya döner, Esc vazgeçer. Sapma: düzenleme sekme geçişinde hücre içinden formül çubuğuna taşınır (Excel hücrede tutar)
- **Renkli metin:** `ui/renkli.py` — hücre düzenleyicisi ve formül çubuğunda başvurular kendi renginde (normal çizimden sonra üstüne çizilir; metin kutuyu aşıp kayarsa ya da seçim varken çizilmez). Ekran görüntüsüyle iki kutuda hizalama doğrulandı
- **Alt+= çok hücreli seçim:** çok satırda her sütunun toplamı seçimin altına, tek satırda sağına yazılır (doğrudan, tek geri al adımı)
- **İpucunda gerçek argüman adı bilerek yok:** Türkçe argüman adları (sayı1…) Microsoft belgesiyle doğrulanmadan yazılamaz (kural 4); doğrulanırsa `fonksiyonlar` kaydına eklenir → §8b'ye eklendi (#22)
- **6e döngüsel başvuru:** durum çubuğunda "Döngüsel Başvurular: A1" (seçili sayfadaki ilk döngü hücresi; yalnız başka sayfadaysa adressiz), yeni döngü oluşunca **bir kez** uyarı iletisi (geri al/yinele'de uyarmaz); `theme.UYARI`. Uyarı metni bize ait (Excel'in birebir metni doğrulanmadı). Düzeltme: `Izgara._gecmis` artık `degisti`yi bayrak açıkken yayar
- Testler 1213 → **1224** (`test_dongu_arayuz.py` 5; `test_isaretleme_arayuz.py` +6)
- Kalan Faz 2: 6f (geri al başka sayfaya geçme sorunu), 6g (test.md Faz 2, bütçe senaryosu, Opus gözden geçirmesi). Elle denenmedi: gerçek fareyle sekme tıklama akışı

## [2026-10-09] — Faz 2: 6f geri al sayfa geçişi (Sonnet 5.5)
- Sorun: geri al/yinele sırasında pencere, ilk gelen olayın sayfasına geçiyordu; başka sayfalardaki formül düzeltmeleri (satır ekle-sil, taşıma yan etkisi) yanlış sayfaya götürebilirdi
- Çözüm: `komutlar.ana_sayfa(komut, geri_al)` asıl değişikliğin sayfasını verir (taşımada geri alırken kaynak, yinelerken hedef; `Grup` ilk alt komut; sayfa işlemleri None), `GeriAlYigini.son_komut/son_geri_al`; `Pencere._gecmis_islemi_ayarla(False)` işlem bitince o sayfaya geçer. `_kitap_olayi`'ndaki olay tabanlı geçiş kaldırıldı
- Testler 1224 → **1228** (`test_gecmis_sayfa_gecisi.py`). Sonraki: 6g

## [2026-10-09] — Faz 2 Opus gözden geçirmesi: bulgular ve düzeltmeler (Sonnet 5.5)
- Opus 5.5 (salt okunur alt ajan) raporu: tavsiye **koşullu** (1, 2, 3 düzelt; 6, 7 küçük; 4, 5 Faz 3 başı). Her bulgu önce **yeniden üretildi**, sonra düzeltildi; ayrıntı `test.md` §10. Tamamı `testler/test_opus_faz2.py` + `test_motor.py` + `test_isaretleme_arayuz.py`
- **1 (KRİTİK) karesel yeniden hesap → düzeltildi:** aralık bağımlılıkları sütun indeksli (`motor._aralik_sutun/_aralik_genis`), `_bagimlilar` kirli formülleri atlar. 4000 satırlı yürüyen bakiyede 19,9 sn → 0,1 sn
- **2 (KRİTİK) `TOPLA(A:A)` 1.048.576 satır geziyordu → düzeltildi:** `AralikDeger.toplam` kullanılan alana kırpar (0,42 sn → 0,5 ms)
- **3 (KRİTİK) EĞER dizi üzerinde öğe öğe çalışmıyordu → düzeltildi:** `temel.dizi_sec` (yayma + #YOK doldurma + hata öğesi); EĞER ve ÇOKEĞER. `=TOPLA(EĞER(A1:A3>1;A1:A3;0))` artık 5 (önce 0)
- **4 ölçüt dizi/aralık → düzeltildi:** `ortak.olcut_yayar` dekoratörü (EĞERSAY/ÇOKEĞERSAY/ETOPLA/ÇOKETOPLA/EĞERORTALAMA/ÇOKEĞERORTALAMA/ÇOKEĞERMAK/MIN); benzersiz sayma deyimi çalışıyor
- **5 ölçütte Türkçe hata adı → düzeltildi** (`#BÖL/0!`, `#YOK`; kanonik adlar da çalışır)
- **6 (kural 4 ihlali) DATEDIF adı yanlıştı → düzeltildi:** `TARİHFARKI` değil **`ETARİHLİ`** (Microsoft sayfasının başlığı makine çevirisi, sözdizimi satırı ETARİHLİ). **Tüm 116 ad** sözdizimi/örnek satırına karşı betikle yeniden tarandı: 105 sayfadan, ROW/INDIRECT/OFFSET (403 sonrası yeniden), IS* ailesi "E işlevleri" sayfasından, EĞERSAY ve BUL ilgili tr-tr sayfalarından doğrulandı → başka hata yok. Microsoft örneklerindeki birimler `"G"`, `"YG"` takma ad olarak eklendi
- **7 başka sayfadan formül yazarken yarım kalan düzenleme → düzeltildi:** devredilen düzenleme sürerken işaret dışı tıklama formülü ilk hücreye **onaylar** (hatalıysa açık kalır); `Izgara.uzakOnay` sinyali. Karar: Excel'in tam davranışı doğrulanmadı; Enter ile aynı sonucu veriyor (asıl sayfaya dönüş)
- **Yan bulgu (testle çıktı): `NA()` fonksiyonu yoktu → eklendi** (`YOKSAY`, tr-tr NA sayfasının sözdizimi satırıyla doğrulandı). Fonksiyon sayısı 116
- **Bilerek değiştirilmedi (Excel davranışı doğrulanmadan tahmin yok, §8b 23–29):** 8 ölçütte 15 basamak eşitlik, 9 ETARİHLİ "Y"/"YD", 10 `"="` ölçütü, 11 sayfa önekli başvuru taşması görünümü
- Testler 1236 → **1253**. Ölçüm §8. `test.md` §10'a rapor işlendi
- **Faz 2 bitti.** Sıradaki: Faz 3 (biçimlendirme, sayı biçimleri, doldurma, dondurma; çizim yeniden yapımı + `TEXT`/METNEÇEVİR + metin tarihleri); plan.md → Faz 3. Girişte: Opus gözden geçirmesinin "incelenmedi" listesi (`arama/metin/finans/bilgi/istatistik` doğruluğu, ayrıştırıcı uç durumları) Faz 3 başında hafifçe gözden geçirilebilir

## [2026-10-09] — Faz 3 çekirdeği (Opus 5.5, alt ajan)
- Faz 2 düzeltmeleri commit `85d65a3`. Faz 3 çekirdeği Opus 5.5 alt ajanıyla (salt okunur olmayan, yalnız belirtilen dosyalar) yazıldı; **ben doğruladım:** 1432 test geçiyor (1253 + 179), `git status` yalnız beklenen 5 dosya, `model/` Qt ve `formul/` içe aktarmıyor
- Yeni: `faz3_tasarim.md` (stil modeli, olay/geri al, birleştirme, dondurma, doldurma, akıllı giriş, çizim gereksinimleri, 3a–3l devir listesi, kararlar), `model/sayi_bicimi.py` (Genel, 0#?, binlik/ölçek, yüzde, bilimsel, kesir, `@`, 4 bölüm + koşullu, 8 renk (Siyah, Yeşil, Beyaz, Mavi, **Eflatun** (Macenta değil), Sarı, Camgöbeği, Kırmızı — tr-tr kılavuzundan), sabit metin, `_x`, `*x` (`BicimSonucu.dolgu`), tarih/saat/`[h]`, kanonik⇄yerel `yerele/kanonige`, `HAZIR`/`ad_kodu`, `ondalik_degistir`, `sigdir`/`doldur`, `lru_cache`), `model/tarihseri.py` (seri⇄tarih yardımcıları `formul/`'dan taşındı → kural 2 korunur; `tarih.py` oradan alır)
- Hız (100.000 çağrı): Genel 2,8 µs; `0`/`#,##0.00`/`0.0%`/`"₺"#,##0.00` 6,5–8,6 µs; tarih 10,6; saat 9,1; bilimsel 30; kesir ~55 µs. Ekrandaki ~1.000 hücrenin soğuk biçimlemesi 7–10 ms → **3c'de satır önbelleği zorunlu**
- Doğrulanamayanlar §8b 30–44'e yazıldı (ay/gün kısaltmaları, ÖÖ/ÖS, saat/dakika/saniye harfleri, `[Renk N]`, hazır biçim kodları…). `Genel` kod adı kabul ediliyor ama doğrulanmadı
- Riskler: Türkçe saat harfleri yanlış çıkarsa yalnız `yerele/kanonige` tablosu değişir (saklama kanonik); Excel'in kesir yaklaşımı/`?` hizası birebir doğrulanmadı; Excel'in hazır biçim tablosu (numFmtId 0–49) Faz 4'te openpyxl'den alınmalı
- Sıradaki: **3a** (Sonnet)

## [2026-10-09] — Faz 3 / 3a bitti (Sonnet 5.5)
- `model/stil.py` (`Stil`, `Kenarlik`, `StilYama`, `StilHavuzu`); `Sayfa` stil depoları (`_stil`, `satir_stil`, `sutun_stil`, `stil_kimligi/stil/ham_stil_kimligi`, `bicim_yaz` → tek `bicim` olayı, `stilleri_yaz/satir_stili_yaz/sutun_stili_yaz`, `havuza_gec`, `bicim_silinecek/bicim_geri_koy`, `kullanilan_aralik(bicim_dahil)`); `CalismaKitabi.stil_havuzu`; `komutlar.BicimDegis` + `bicim_komutu`; `ana_sayfa` BicimDegis'i tanır; `_SatirSutun` silinen stilleri saklar/geri koyar; `olay.py` belgesine `bicim`
- Kararlar/ayrıntılar: hücre değeri 0 yalnız satır/sütun stili varken **açık** saklanır (Biçimleri temizle satır biçimliyken doğru çalışsın); tam sütun biçimlenince biçimli satırların kesişimine açık kayıt yazılır (son uygulanan kazanır; ≤200.000 kayıt); tek aralık ≤5.000.000 hücre (aşarsa `AdresHatasi`; UI tam satır/sütun önerir); satır/sütun ekleme üstteki/soldaki biçimi devralır, silme geri alınınca aynen döner (devralınan bant temizlenir); sayfa başka kitaba bağlanırken kimlikler çevrilir
- Testler 1432 → **1458** (`test_stil.py` 26: interning, öncelik, tek olay, formül motoru tetiklenmez, geri al/yinele, tam satır/sütun, 100.000 hücre < 1,5 sn (hedef 0,3), ekle-sil + geri al, kitap/sayfa silme). Regresyon yok
- Commit atılmadı (kullanıcı isteyince; Faz 3 çekirdeği + 3a birlikte)
- Sıradaki: **3b** (pano biçim taşıma `PanoVerisi.stiller`, `HucreTasi` stil, Temizle menüsü, Delete biçimi korur)

## [2026-10-09] — Faz 3 / 3b bitti (Sonnet 5.5)
- Commit `8eb1103` (Faz 3 çekirdeği + 3a). **3b:** `PanoVerisi.stiller` ({(dr,dc): Stil}, JSON `"st"`; eski stilsiz JSON okunur), `pano_araligi` biçimli boş hücreleri de kapsar (`kullanilan_aralik(bicim_dahil=True)`), `stil_sozluk/stil_sozlukten`, `pano._yerlestir` (tek yerleşim üreteci) + `yapistirma_stilleri`, `html_yaz(satirlar, stiller)` (kalın/italik/çizgi/renk/dolgu/hizalama satır içi CSS; dışarıdan HTML'den biçim okuma **yok**)
- **Yapıştır:** kendi biçimimiz = içerik + biçim, tek `Grup` (Excel "Tümü": biçimsiz kaynak hedefin biçimini de siler); dışarıdan gelen metin/HTML biçime dokunmaz (`kaynak_satir` yoksa). **Kes-yapıştır:** `HucreTasi` etkin stilleri taşır, kaynak varsayılana döner, hedefte satır/sütun stilini ezer, geri alınca aynen döner; sayfalar arası ve üst üste binen alan dahil
- **Temizle:** `bicim_komutu(..., sifirla=True)`; ızgarada `bicimleri_temizle()` (içerik kalır), `tumunu_temizle()` (tek `Grup`); hücre sağ tık menüsüne "Biçimleri temizle", "Tümünü temizle" eklendi; Delete biçimi korur (test)
- **Regresyon bildirimi (kural 12):** `test_izgara.py::test_hucre_menusu` menüdeki eylem listesini tam sınıyordu; menüye iki eylem eklendiği için beklenen liste `[…, "İçeriği temizle", "Biçimleri temizle", "Tümünü temizle"]` oldu (gevşetilmedi, genişletildi)
- Testler 1458 → **1474** (`test_pano_bicim.py` 16)
- Bilerek eksik: Özel Yapıştır (Değerler/Biçimler/Formüller) menüsü; birleşimlerin pano/taşıma ile taşınması (3f ile)
- Sıradaki: **3c** (ızgara çizimi yeniden — Faz 1 performans ❌'leri burada kapanır; ölçüt `faz3_tasarim.md` §7)

## [2026-10-09] — Faz 3 / 3c bitti (Sonnet 5.5)
- **Çizim stili uygular:** `Izgara._yerlesim` hücre stiline göre: sayı biçimi (`sayi_bicimi.bicimle/sigdir`, renk `[Red]`…, `####`, `*x` dolgu), yatay/dikey hiza, girinti, yazı tipi (aile, boyut, kalın, italik, üstü/altı çizili, yazı rengi); `_stilli` yan ürünü dolgu/kenarlıklı görünen hücreleri (boş dahil) verir. `_dolgu_ciz`, `_kenar_ciz` (ince/orta/kalın/kesikli/noktalı/çift/saç; komşu kenarda kalın kazanır; sol/üst kenar komşunun sağ/alt çizgisine oturur, başlığın altında kalır). Test sözleşmesi korundu (`_yerlesim` 2'li dönüş, ilk 4 alan aynı; 6. alan `(renk, yazı tipi girdisi, stil)` eklendi)
- **Önbellekler:** `_FontGirdisi` (stil kimliği başına QFont/QFontMetrics/genişlik/QStaticText/sığdırılmış sayı), `(değer, kod)` biçim önbelleği; yakınlaştırma/yazı tipi/havuz değişince sıfırlanır
- **Artımlı çizim:** yatay kaydırma `viewport().scroll` (+ sınır şeridi yeniden boyanır: kalın kenarlık komşuya 2 px taşar); bölgenin her parçası ayrı boyanır ve kendi dikdörtgenine kırpılır (tek kırpma bölgesiyle çift çizimde başlık metni koyulaşıyordu); hücre işlemede 3 px taşma payı; Shift+Ok yalnız fark bölgesini boyar (`_secim_farki_boya`); büyük seçimde (>5000 hücre) durum çubuğu özeti 50 ms ertelenir (küçükte anında — testler aynen geçer)
- **Hata düzeltmesi (Faz 2'den kalma):** `Pencere._formul_isareti_kapat` her seçim değişiminde tüm viewport'u yeniden çizdiriyordu → artık yalnız işaretleme etkinken
- **Doğrulama:** testler 1474 → **1497** (`test_izgara_stil.py` 23: dolgu/kenarlık piksel, yazı tipi, hizalama, girinti, sayı biçimi, `####`, geçersiz kod, yatay artımlı = tam çizim, özet erteleme, kısmi boyama alanı). `araclar/cizim_dogrula.py` dolgu/kenarlık/biçimli hücre + yatay kaydırma + Shift+Ok adımlarıyla genişletildi (gerçek pencere): **1 piksel fark** (bilinen köşe artefaktı, tolerans 1). `performans_olcum.py`'ye stilli senaryo eklendi (§8). Regresyon yok, hiçbir test değiştirilmedi
- **Bilerek eksik (sonraki işlere):** metni kaydır + otomatik satır yüksekliği (3j; `kaydir` şimdilik taşmayı kapatır, sarma yok), kılavuz gizle/dondurma (3i), birleşim (3f), `doldur`/`iki_yana`/`secim_ortasi` tam hizası, sağa hizalı metnin sola taşması. Ekran görüntüsü incelendi (başlık dolgusu, para/yüzde/kırmızı negatif biçimi, kalın/çift kenarlık, girinti, 18 punto satır — doğru). Bilinen sınır: A sütununun sol ve 1. satırın üst kenarlığı başlığın altında kalır (görünmez; Excel gösterir)
- Sıradaki: **3d** (biçim araç çubuğu)

## [2026-10-09] — Faz 3 / 3d bitti (Sonnet 5.5)
- **Yeni:** `model/bicim_islem.py` (Qt'siz: aç-kapat/hiza/girinti/ondalık/boyut adımı/kenarlık planı yamaları), `komutlar.BicimPlani` (sıralı çok yamalı tek adım; `ana_sayfa` tanır), `Izgara.bicim_uygula(yama | plan)`, `ui/bicim_cubugu.py` (yazı tipi, boyut + büyüt/küçült, K/İ/A, yazı rengi, dolgu rengi, kenarlık menüsü, dikey+yatay hiza, metni kaydır, girinti ±, sayı biçimi listesi `HAZIR`, ₺/%/binlik, ondalık ±), `ui/icons.py`, `ui/widgets.py` (`RenkDugmesi`: Office paleti + Diğer Renkler), tema `#formatBar`. Çubuk başlık şeridi ile formül çubuğu arasında; her seçim/geri al/yinele sonrası etkin hücreyi yansıtır
- **Hata (testle yakalandı, düzeltildi):** kenarlık plan adımları önceden `bicim_komutu` ile kurulunca örtüşen köşe hücrelerde sonraki adım öncekini eziyordu → `BicimPlani` komutları yap() anında üretir
- Testler 1497 → **1543** (`test_bicim_islem.py` 23 Qt'siz, `test_bicim_cubugu.py` 23 pencere: her düğme, etkin hücre mantığı, tek geri al, kısayollar, tam sütunda kenarlık, düzenlerken odak, ikinci sayfa). Regresyon yok, hiçbir test değiştirilmedi. Ekran görüntüsü incelendi (çubuk 1200 px'te tek satır, işaretli düğme/dolgu/kenarlık/yüzde doğru)
- **Bilerek eksik:** Birleştir düğmesi (3f ile eklenir), biçim boyacısı (3k), kenarlık rengi/stili seçimi (3e), "Özel" liste öğesi yalnız gösterge, Metni Kaydır düğmesi stili yazar ama sarma çizimi 3j'de; Türkçe Excel kısayol doğrulaması (§8b-44/45). `CLAUDE.md` dosya yapısına yeni `ui/` dosyaları (icons, widgets, bicim_cubugu) ve `model/bicim_islem.py` eklenmedi — kullanıcı onayı bekler
- Commit atılmadı (kullanıcı isteyince)
- Sıradaki: **3e** (Hücreleri Biçimlendir, Ctrl+1)

## [2026-10-09] — Faz 3 / 3e bitti (Sonnet 5.5)
- Commit `783a136` (3d). **3e:** `ui/bicim_penceresi.py` (Sayı: kategori listesi, ondalık/binlik/simge/tür, Özel kod yerel yazımla + canlı önizleme; Hizalama; Yazı Tipi; Kenarlık; Dolgu), `model/bicim_kodlari.py` (Qt'siz kategori ⇄ kanonik kod, 14 hazır kodun gidiş-dönüşü), `bicim_islem.kenar_ayar_plani`, Ctrl+1 ve çubukta düğme
- Testler 1543 → **1561** (`test_bicim_kodlari.py` 6, `test_bicim_penceresi.py` 12: başlangıç değerleri, yalnız değişenler, kategoriler, Özel kanonik/yerel, geçersiz kod/boyut uyarısı, kenarlık planı, Ctrl+1 uçtan uca + tek geri al, iptal, çok hücreli korunma). Ekran görüntüleri incelendi (Sayı, Kenarlık). Kural 12: yalnız yukarıdaki tek test değişti (gerekçe Kararlar'da)
- **Bilerek eksik:** Excel'deki kenarlık önizleme kutusu/çapraz çizgiler, yazı tipi önizlemesi, "Koruma" sekmesi, Özel kod listesi (hazır örnekler), kategoriye göre negatif sayı seçenekleri (kırmızı/parantez); Metin kaydır çizimi 3j'de
- Sıradaki: **3f** (birleştirme)

*(Yeni girişler en alta eklenir.)*

