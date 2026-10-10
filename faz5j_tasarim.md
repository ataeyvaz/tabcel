# 5j — Sekmeli şerit: tasarım notu (Opus 5.5, 2026-10-10)

Kapsam ve ölçüt `plan.md` → "Arayüz: sekmeli şerit". Bu not uygulayıcı (Sonnet 5.5) için sözleşmedir: neyin nereye taşınacağı, hangi adların korunacağı, iş sırası ve ölçütler.

**Temel ilke: şerit yalnız yerleşimdir.** Hiçbir komutun davranışı değişmez; yeni işlev yalnız §4'te "yeni (küçük)" diye işaretlenenlerdir ve her biri var olan bir model/komut yolunu çağırır.

---

## 1. Bugünkü durum (değişecek olan)
- Yeşil başlık şeridi (`#header`): Dosya / Görünüm / Düzen / Veri / Koşullu Biçim menü düğmeleri + Geri Al / Yinele + belge adı.
- Altında `BicimCubugu` (tek satır, ≤ 1100 px; `test_bicim_cubugu::test_ekran_goruntusu_boyutlari`).
- Kısayollar `QShortcut` ile pencereye bağlı; menü eylemlerinde kısayol yalnız metinde gösterilir (çift tanım belirsizlik yaratıyordu, `window.py` yorumu). **Bu düzen korunur.**

## 2. Yeni pencere düzeni (yukarıdan aşağı)
1. **Başlık şeridi** (yeşil, `#header`, kalır): solda hızlı erişim: **Kaydet** (yeni ikon, beyaz), `geri_dugmesi`, `yinele_dugmesi`; ortada `belge_etiketi`. Menü düğmeleri buradan **kalkar**.
2. **Şerit** (`ui/serit.py` → `Serit`): sekme satırı + etkin sekmenin sayfası.
3. Bilgi çubuğu (`bilgi_cubugu`; Excel'de ileti çubuğu şeridin altındadır).
4. Ad kutusu + formül çubuğu, ızgara, sayfa sekmeleri, durum çubuğu (değişmez).

Görünüm: sekme satırı ve sayfa beyaz (`SURFACE`); seçili sekme `ACCENT` yazı + altında 3 px `ACCENT` çizgi; **Dosya** sekmesi `ACCENT` zeminli beyaz yazı (Excel 2016 gibi), tıklayınca bugünkü Dosya menüsü açılır (arka sahne sayfası sonra). Grup adı alt ortada, 11 px, `TEXT_MUTED`; gruplar arası 1 px `BORDER` dikey çizgi. Sayfa yüksekliği ≈ 92 px (büyük düğme: 32 px ikon + en çok 2 satır metin; küçük düğme sütunları: 3 × 22 px; grup adı 16 px).

## 3. Bileşenler (`ui/serit.py`, yeni)
| Sınıf | Görev |
|---|---|
| `Serit(QWidget)` | `QTabBar` (sekmeler) + `QStackedWidget` (sayfalar). `sekme_ekle(ad, sayfa)`, `dosya_menusu_ayarla(menu)`, `daralt(bool)`, `daraltilmis()`, `guncelle()` (her sayfanın `guncelle`'sini çağırır), `eylemler()` (tüm düğme + menülerdeki `QAction`'ları özyinelemeli toplar — test için) |
| `SeritSayfasi(QWidget)` | Gruplar yatay; `grup_ekle(grup, konum=None)`; `resizeEvent` → daralma planı (§3.1); `guncelle()` alt sınıfa açık |
| `SeritGrubu(QWidget)` | Başlık + içerik; `buyuk(eylem_ya_da_menu, ikon32, metin)`, `kucukler([...])` (3 satırlık sütun), `satir([...])` (yazı tipi kutusu gibi serbest widget'lı satırlar); isteğe bağlı sağ alt köşe **↘ pencere başlatıcı** düğmesi (`dialog_launcher`); `oncelik: int` |
| `daralma_plani(genislikler, oncelikler, kullanilabilir) -> List[int]` | **Saf işlev** (Qt'siz test edilir): her grubun durumu 0 = tam, 1 = küçük düğmeler yazısız, 2 = tek açılır düğme |

Düğmeler: `QToolButton.setDefaultAction(eylem)` (metin/ikon/ipucu/etkinlik/işaret durumu eylemden gelir, tek kaynak); açılır menülü düğmeler `InstantPopup` (yalnız menü) ya da `MenuButtonPopup` (ana işlem + ok; ör. Yapıştır, Birleştir). **Tüm şerit düğmeleri `Qt.NoFocus`** (bugünkü `BicimCubugu` kuralı): düzenleme/formül çubuğu odağı çalınmaz. Açılan kutular (yazı tipi, boyut, sayı biçimi, ölçek) işlemden sonra odağı ızgaraya verir (bugünkü `_uygula` düzeni).

Metinlerde `&` kullanılmaz (Qt bunu Alt+harf kısayoluna çevirir; Alt+=, Alt+Enter, Alt+Aşağı bozulmasın). Gereken yerde `&&`.

### 3.1 Daralma (dar pencere)
- Her grubun her durumdaki genişliği `sizeHint`'ten ölçülür ve önbelleğe alınır (yazı tipi/yakınlaştırma değişince boşalır).
- Plan: hepsi 0'dan başlar; toplam > kullanılabilir oldukça **en düşük öncelikli** grup bir durum küçülür (önce durum 1, gruplar bitince durum 2); eşit öncelikte **sağdaki önce** (Excel sağdan sola daraltır). Durum 1 yalnız yazılı küçük düğmesi olan grupta anlamlıdır, yoksa doğrudan 2.
- Durum 2: grup, grubun ikonlu tek büyük düğmesine iner; tıklayınca grubun içeriği `Qt.Popup` çerçevede açılır (içerik widget'ı çerçeveye **taşınır**, durum 0/1'e dönünce geri taşınır — iki kopya yok, sinyal bağlantıları bozulmaz).
- Hepsi durum 2'de de sığmıyorsa sayfa kırpılır; pencerenin en küçük genişliği 640 px (`setMinimumWidth`).
- **Ölçüt:** 1100 px'te Giriş sekmesinde hiçbir grup durum 2'ye inmez; 800 px'te hiçbir sekmede düğme sayfa dışına taşmaz (geometri testi).

### 3.2 Şeridi daraltma
- **Ctrl+F1** ve sekmeye **çift tık**: sayfalar gizlenir, yalnız sekme satırı kalır. Daraltılmışken sekmeye tek tık sayfayı ızgaranın **üstünde** `Qt.Popup` olarak açar (Excel gibi); komut çalışınca/dışarı tıklanınca kapanır. Durum bu sürümde kalıcı değil (ayar dosyası Faz 7).

## 4. Sekmeler ve içerik
Kısaltmalar: **B** büyük düğme, **k** küçük düğme, **▾** açılır menü, **↘** pencere başlatıcı. Parantezde çağrılan var olan yöntem. Öncelik: yüksek sayı = geç daralır.

**Dosya** — açılır menü (`_dosya_menusu_doldur`, değişmez).

**Giriş** — `BicimCubugu` bu sekmenin sayfası olur (§5).
| Grup (öncelik) | İçerik |
|---|---|
| Pano (5) | B Yapıştır (`yapistir`; MenuButtonPopup, menü şimdilik yalnız "Yapıştır"), k Kes, k Kopyala, k Biçim Boyacısı (`boyaci`) |
| Yazı Tipi (9) | satır 1: yazı tipi, boyut, büyüt, küçült · satır 2: K İ A, kenarlık ▾, dolgu, yazı rengi · ↘ Ctrl+1 (Yazı Tipi sekmesi) |
| Hizalama (8) | satır 1: üst/orta/alt, metni kaydır · satır 2: sol/orta/sağ, birleştir ▾ · satır 3: girinti azalt/artır · ↘ Ctrl+1 (Hizalama sekmesi) |
| Sayı (7) | satır 1: sayı biçimi kutusu · satır 2: ₺ % 000, ondalık artır/azalt · ↘ Ctrl+1 (Sayı sekmesi) |
| Stiller (3) | B Koşullu Biçimlendirme ▾ (bugünkü `_kosullu_menusu`, aynen) |
| Hücreler (4) | B Ekle ▾ (Sayfa Satırları Ekle `satirlari_ekle`, Sayfa Sütunları Ekle `sutunlari_ekle`, Sayfa Ekle `sayfa_ekle`) · B Sil ▾ (satır/sütun/sayfa sil) · B Biçim ▾ (Satır Yüksekliği…, Satır Yüksekliğini Otomatik Sığdır, Sütun Genişliği…, Sütun Genişliğini Otomatik Sığdır, Gizle ve Göster ▸ [satır/sütun gizle/göster], Sayfayı Yeniden Adlandır, Sekme Rengi…, Hücreleri Biçimlendir…) |
| Düzenleme (6) | k Otomatik Toplam (`otomatik_toplam`, ipucu Alt+=) · k Doldur ▾ (Aşağı Ctrl+D, Sağa Ctrl+R) · k Temizle ▾ (Tümünü, Biçimleri, İçeriği, Notları) · B Sırala ve Filtre Uygula ▾ (A→Z, Z→A, Özel Sıralama…, Filtre, Temizle, Yeniden Uygula) · B Bul ve Seç ▾ (Bul…, Değiştir…, Git…) |

Not: `satirlari_ekle`/`sil` bugün **seçimin satırlarına** göre çalışır (hücre seçiminde de) — Excel'in "Sayfa Satırları Ekle"siyle aynı; uygulayıcı bir testle doğrular.

**Sayfa Düzeni**
| Grup | İçerik |
|---|---|
| Sayfa Yapısı (5) | B Kenar Boşlukları ▾ (Normal / Geniş / Dar hazır değerleri + Özel Kenar Boşlukları… = pencere) · B Yönlendirme ▾ (Dikey / Yatay) · B Boyut ▾ (`KAGITLAR`) · B Yazdırma Alanı ▾ (Yazdırma Alanını Belirle = seçim, Yazdırma Alanını Temizle) · B Başlıkları Yazdır (pencere) · ↘ Sayfa Yapısı penceresi |
| Sığdır (4) | ölçek kutusu (% 10–400), ☐ Genişliği tek sayfaya sığdır |
| Sayfa Seçenekleri (3) | Kılavuz çizgileri: ☐ Görüntüle (= `kilavuz_eylemi`, aynı eylem) · ☐ Yazdır (`SayfaYapisi.kilavuz`) |

**Yeni (küçük):** `Pencere.sayfa_yapisi_degistir(**alanlar) -> bool` — `SayfaYapisiDegis(sayfa, sayfa.sayfa_yapisi.degistir(**alanlar))`, `bos_mu` değilse `yigin.calistir` + `_baslik_guncelle` (`sayfa_yapisi_ac`'daki yolun aynısı; geri alınır). Bu grubun tüm düğmeleri bunu çağırır. Hazır kenar boşlukları (cm, üst/alt/sol/sağ): Normal 1,91/1,91/1,78/1,78 (bizim varsayılan), Geniş 2,54 hepsi, Dar 1,91/1,91/0,64/0,64 — **Excel değerleri §8b'ye "doğrulanacak" yazılır**. Başlık/altbilgi boşluğu modelimizde yok (atlanır).

**Formüller**
| Grup | İçerik |
|---|---|
| İşlev Kitaplığı (5) | B Otomatik Toplam (`otomatik_toplam`). Ortalama/Say/En Büyük/En Küçük alt menüsü **sonra** (yeni işlev olur) |
| Tanımlı Adlar (4) | B Ad Yöneticisi (Ctrl+F3) · k Ad Tanımla… |

**Veri**
| Grup | İçerik |
|---|---|
| Sırala ve Filtre Uygula (5) | k A→Z, k Z→A · B Sırala (Özel Sıralama…) · B Filtre (işaretli = sayfada filtre var; Ctrl+Shift+L) · k Temizle · k Yeniden Uygula (Ctrl+Alt+L) |
| Veri Araçları (4) | B Veri Doğrulama… |

**Gözden Geçir**
| Grup | İçerik |
|---|---|
| Notlar (5) | B Yeni Not (etkin hücrede not varsa metin "Notu Düzenle"; Shift+F2; `not_duzenle`) · k Notu Sil (`notu_sil`; not yoksa kapalı) |

(Yazım denetimi Faz 7'de buraya gelir.)

**Görünüm**
| Grup | İçerik |
|---|---|
| Göster (3) | ☐ Kılavuz Çizgileri (`kilavuz_eylemi`) |
| Yakınlaştır (4) | B %100 (`izgara().yakinlastir(1.0)`) |
| Pencere (5) | B Bölmeleri Dondur ▾ (`gorunum_eylemleri`, aboutToShow `_gorunum_menusu_hazirla` aynen) |

**Ekle** sekmesi 5j'de **gösterilmez** (içerecek işlev yok; boş sekme kötü). Faz 6 grafiklerle Giriş'ten sonra ekler — sekme sırası tek listede (`_SEKMELER`).

Kapsam dışı (sonra): Alt tuş ipuçları, Dosya arka sahne sayfası, şerit özelleştirme, Hızlı Erişim'e ekleme, sekme/daralma durumunun kalıcılığı, Yapıştır Özel.

## 5. Uyumluluk sözleşmesi (testlerin dayandığı adlar)
**Korunur (aynı nesne, aynı anahtarlar):**
- `pencere.bicim_cubugu` — `BicimCubugu` sınıfı kalır, **Giriş sayfası olur** (`SeritSayfasi` alt sınıfı). Mevcut öznitelikler aynı adla: `boyaci, yazi_tipi, boyut, buyut, kucult, kalin, italik, altcizili, yazi_rengi, dolgu, kenarlik, kenar_eylemleri, dikey, yatay, birlestir, birlestir_eylemleri, kaydir, girinti_azalt, girinti_artir, sayi_bicimi, para, yuzde, binlik, ondalik_artir, ondalik_azalt, pencere_dugmesi` ve yöntemler `guncelle, penceresi_ac, kenarlik_uygula, birlestir_uygula`. `pencere_dugmesi` = Yazı Tipi grubunun ↘ düğmesi (Ctrl+1, sekme 0). Kısayollar aynı yerde kalır.
- Pano / Stiller / Hücreler / Düzenleme grupları `Pencere` tarafından `bicim_cubugu.grup_ekle(...)` ile eklenir (BicimCubugu pencereyi tanımaz; bugünkü gibi yalnız `izgara_al` alır).
- `duzen_eylemleri`, `veri_eylemleri`, `gorunum_eylemleri`, `kilavuz_eylemi`, `kosullu_eylemleri` — **aynı `QAction` nesneleri**, şerit düğmeleri bunları kullanır. Tüm eylemler tek yerde kurulur: `Pencere._eylemleri_kur()` → `self.eylemler: Dict[str, QAction]`; eski sözlükler bunun görünümleridir. Kısayollar yine `QShortcut`; eylemde yalnız ipucunda gösterilir ("Filtre (Ctrl+Shift+L)").
- `geri_dugmesi`, `yinele_dugmesi`, `belge_etiketi`, `bilgi_cubugu`, `dosya_dugmesi` (= Dosya sekmesi düğmesi, menüsü aynı).

**Değişen (kural 12 — kullanıcıya bildirildi):** `test_faz5_altyapi.py:582` `p.duzen_dugmesi.text() == "Düzen" and p.veri_dugmesi.text() == "Veri"` — menü düğmeleri kalkıyor. Öneri: bu satır `"Veri" in p.serit.sekme_adlari()` ve Bul/Değiştir/Git'in şeritte olduğu denetimiyle değiştirilir (testin amacı — iskeletin var olması — korunur). Kullanıcı istemezse alternatif: `duzen_dugmesi`/`veri_dugmesi` gizli uyumluluk düğmesi olarak bırakılır (önerilmez: ölü arayüz). `test_ekran_goruntusu_boyutlari` (≤ 1100) **değişmeden** kalır ve artık "Giriş sayfası 1100 px'te sığar" anlamına gelir (sayfanın `sizeHint`'i o anki daralma durumundaki genişliktir).

## 6. İkonlar (`ui/icons.py`)
- Spesifikasyona isteğe bağlı `"grid": 32` anahtarı: büyük düğme ikonları **32 px ızgarada 1 px çizgiyle** çizilir (20'lik ikonu 32'ye büyütmek 1,6 px bulanık çizgi verir — Sözcük dersi). `draw` ölçeği `spec.get("grid", GRID)`'den alır. Aynı ikonun küçük hali gerekiyorsa ayrı 20'lik ad (`paste` / `paste32`).
- Yeni (yaklaşık): 32: `paste32, cond_format32, insert32, delete32, format32, sort_filter32, find32, sort32, filter32, validation32, name_manager32, margins32, orientation32, paper32, print_area32, print_titles32, note32, freeze32, zoom100_32, autosum32` · 20: `cut, copy, autosum (Σ), fill, clear, sort_az, sort_za, filter_clear, reapply, define_name, note_delete, save` (başlıkta beyaz: `icon("save", "#ffffff")`).
- **Ölçüt:** `araclar/ikon_sayfasi.py` tüm ikonları 20/32 px (+ %150 ölçek) tek PNG'ye çizer; ekran görüntüsü incelenir (bulanık/kayık çizgi yok).

## 7. Durum eşitleme
`Pencere._arayuzu_guncelle` sonunda `self.serit.guncelle()` (bugünkü `bicim_cubugu.guncelle()` bunun içinde). Eşitlenenler: biçim düğmeleri (bugünkü gibi), Filtre işareti (`sayfa.filtre is not None`), Kılavuz işaretleri (görüntüle/yazdır), Notu Sil etkinliği + Yeni Not/Notu Düzenle metni, Sığdır kutusu/ölçek (sayfa değişince). Ucuz kalmalı: `guncelle` yalnız **görünen** sayfayı eşitler; sekme değişince o sayfa eşitlenir (her seçim değişiminde 7 sayfayı gezmek gereksiz).

## 8. Uygulama sırası (Sonnet 5.5; her adımda testler geçer, kural 12)
1. **5j-1** `ui/serit.py`: `Serit`, `SeritSayfasi`, `SeritGrubu`, `daralma_plani` + `testler/test_serit.py` (plan işlevi: sığar/hiç sığmaz/eşit öncelik sağdan/durum 1 atlanır; widget: grup ekleme, durum 2 açılır çerçeve içeriği taşır ve geri getirir).
2. **5j-2** ikonlar: `grid` anahtarı + yeni ikonlar + `araclar/ikon_sayfasi.py`; ekran görüntüsü incele.
3. **5j-3** `_eylemleri_kur` (eylem kataloğu; eski sözlükler görünüm) — henüz yerleşim değişmeden; tüm testler aynen geçer.
4. **5j-4** Başlıktan menüler kalkar, `Serit` eklenir, `BicimCubugu` Giriş sayfasına dönüşür + Pano/Stiller/Hücreler/Düzenleme; `test_faz5_altyapi:582` §5'teki gibi (kullanıcı onayıyla).
5. **5j-5** Sayfa Düzeni (+ `sayfa_yapisi_degistir`), Formüller, Veri, Gözden Geçir, Görünüm.
6. **5j-6** Ctrl+F1 / çift tık daraltma, tema, ekran görüntüleri (1100 ve 800 px, her sekme), `test.md` bölümü, `surec.md`.

## 9. Ölçütler (5j bitti sayılması için)
- Eski menülerdeki **her eylem** şeritten erişilir: test, eski sözlüklerdeki (`duzen/veri/gorunum/kosullu_eylemleri`, `kilavuz_eylemi`) ve Dosya menüsündeki her eylemin `serit.eylemler()` içinde olduğunu denetler.
- Tüm kısayollar (Ctrl+B/I/U/5/1, Ctrl+Shift+1/4/5, Ctrl+F/H/G, F5, Ctrl+Shift+L, Ctrl+Alt+L, Ctrl+F3, Shift+F2, Shift+F4, Alt+=, Ctrl+D/R, Ctrl+PgUp/PgDn, Ctrl+N/O/S/P) çalışmaya devam eder; Ctrl+F1 eklenir.
- Mevcut testler (§5'teki bir satır dışında) değişmeden geçer.
- 1100 px: Giriş'te durum 2 grup yok; 800 px: hiçbir sekmede taşma yok.
- Şerit düğmesine tıklamak odağı ızgaradan almaz; hücre düzenlenirken Kalın'a basmak düzenlemeyi bozmaz (bugünkü davranış).
- Başlangıç süresi: pencere açılışı 5j öncesine göre ≤ +100 ms (`araclar/performans_olcum.py`'ye satır eklenir).
- **Elle test bekliyor (kullanıcı):** Excel ile görsel karşılaştırma (sekme/grup adları, ikonların okunurluğu), %125/%150 Windows ölçeğinde keskinlik, daraltma ve açılır grup davranışı.

## 10. Kararlar (gerekçeli)
- **Kendi şeridimiz, `QTabWidget` değil:** `QTabWidget` sayfa yüksekliğini en yüksek sayfaya kilitler ve daraltma/açılır sayfa (Popup) için sekme satırını sayfadan ayırmak gerekir → `QTabBar` + `QStackedWidget`.
- **Eylem tek kaynak (`QAction` + `setDefaultAction`):** aynı komut şeritte, sağ tık menüsünde ve (Faz 7) Hızlı Erişim'de tek nesne; etkin/işaretli durum bir yerde.
- **Kısayollar eyleme konmaz:** aynı tuş iki yerde tanımlanınca Qt "belirsiz kısayol" verir ve hiçbiri çalışmaz (bugün de bu yüzden `QShortcut`).
- **Ekle sekmesi Faz 6'ya:** boş sekme Excel'den farklı ama yanıltıcı değil; Faz 6'da grafiklerle gelir.
- **Bul/Sırala hem Giriş ▸ Düzenleme hem kendi sekmesinde:** Excel'deki gibi (aynı `QAction`).
