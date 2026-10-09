# Faz 3 — Biçimlendirme tasarım notu (Opus 5.5, 2026-10-09)

Kapsam `plan.md` → Faz 3. Bu not biçim verisinin **nasıl** tutulduğunu, geri al/olay/pano ile ilişkisini ve Sonnet'e devredilecek işlerin sözleşmesini anlatır. Çekirdekten yazılan: `model/sayi_bicimi.py` (+ `model/tarihseri.py`). Gerisi §8'deki sırayla.

## 1. Hücre stili veri modeli (`model/stil.py`, Qt yok)

**`Stil`** — değişmez, hashlenebilir `@dataclass(frozen=True)`; her alanın varsayılanı Excel'inki:

| Alan | Tür / değerler | Varsayılan |
|---|---|---|
| `yazi_tipi` | str \| None | None (= kitap varsayılanı Calibri 11; yoksa Aptos/Segoe UI) |
| `boyut` | float (punto) \| None | None (= 11) |
| `kalin`, `italik`, `ustu_cizili` | bool | False |
| `alti_cizili` | `"yok" \| "tek" \| "cift"` | `"yok"` |
| `yazi_rengi`, `dolgu` | `"#RRGGBB"` \| None | None (otomatik / dolgu yok) |
| `kenar` | `Kenarlik(ust, alt, sol, sag)`; her biri `(cizgi, "#RRGGBB")` \| None; `cizgi` ∈ `ince, orta, kalin, kesikli, noktali, cift, sac` | hepsi None |
| `yatay` | `genel, sol, orta, sag, doldur, iki_yana, secim_ortasi` | `genel` (sayı sağa, metin sola, mantıksal/hata ortaya — `BicimSonucu.hizalama`) |
| `dikey` | `ust, orta, alt` | `alt` (Excel) |
| `girinti` | int (0–15) | 0 |
| `kaydir` | bool (metni kaydır) | False |
| `sayi_bicimi` | **kanonik** kod (str) | `"General"` |

- `Stil.degistir(**alan)` = `dataclasses.replace`. Kısmi uygulama için **`StilYama`** (yalnız verilen alanlar): `yama.uygula(stil) -> Stil`.
- **Havuz (paylaşımlı saklama):** `StilHavuzu` kitap başına; `kimlik(stil) -> int` (aynı stil → aynı int; *interning*), `stil(kimlik) -> Stil`. Kimlik 0 = varsayılan stil. Havuz yalnız büyür (geri al eski kimlikleri kullanabilir); Faz 4 kaydederken yalnız kullanılanlar `cellXfs`'e yazılır. Önbellek `(eski_kimlik, yama) -> yeni_kimlik` → 100.000 hücreye kalın uygulamak sözlük aramasıdır.
  *Gerekçe:* gerçek dosyalarda farklı stil sayısı küçük (onlar–yüzler); hücre başına bir int hem bellek hem eşitlik hızı verir ve .xlsx'in `s="n"` modeline birebir oturur.
- **Seyrek depolar (`Sayfa`):** `_stil: Dict[(r,c), int]` (0 saklanmaz), `satir_stil: Dict[r, int]`, `sutun_stil: Dict[c, int]`.
  **Etkin stil:** hücre → satır → sütun → 0. Tam satır/sütun biçimlendirmesi (1.048.576 hücre) satır/sütun stiline yazılır **ve** o satır/sütunda zaten `_stil` kaydı olan hücrelere yama uygulanır (Excel de kesişimlere hücre stili yazar). Sütun biçimliyken satır biçimlenirse kesişimde satır stili kazanır (son uygulanan; Excel gibi).
- **K4 ile ilişki:** stil `Hucre`'de **değil**, ayrı depoda. `Hucre` girdi (sabit/formül) olarak kalır → biçim değişikliği formül motorunu tetiklemez, `Hucre` eşitliği/`hucre` olayı değişmez, Delete (içeriği sil) biçimi korur (Excel gibi). **Boş ama biçimli hücre** doğal: yalnız `_stil`'de kaydı vardır.
- **`kullanilan_aralik`:** içerik tabanlı kalır (formül `A:A` kırpması, pano, özet bunu kullanır; değişirse hepsi yavaşlar). Yeni `kullanilan_aralik(bicim_dahil=True)`: Ctrl+End, yazdırma alanı, .xlsx `dimension` için. **Karar (Excel'den fark):** Excel'in UsedRange'i biçimli boş hücreleri hep içerir; biz yalnız gereken yerde içeriyoruz.

## 2. Olaylar ve geri al

- Yeni olay türü **`bicim`** (`model/olay.py` belgesine eklenecek): `degisiklikler` {(r,c): (eski_kimlik, yeni_kimlik)}, isteğe bağlı `satir` {r: (eski, yeni)}, `sutun` {c: (eski, yeni)}, `birlesim` (eklenen/kaldırılan aralıklar), `gorunum` (dondurma, kılavuz). Toplu işlem **tek olay** (K5 kuralı). Motor `bicim`'i yok sayar; ızgara yalnız ilgili satırları geçersiz kılar; otomatik kayıt "kirli" işaretler.
- `Sayfa` API: `stil(r,c) -> Stil` (etkin), `stil_kimligi(r,c) -> int`, `stilleri_yaz({anahtar: kimlik}) -> eskiler` (tek olay), `satir_stili_yaz`, `sutun_stili_yaz`.
- Komut **`BicimDegis(sayfa, hucreler={…}, satirlar={…}, sutunlar={…})`**: eski kimlikleri saklar, geri alınca yükler. Kurucu yardımcı `bicim_komutu(sayfa, araliklar, yama) -> BicimDegis` (çoklu seçim dahil; tam satır/sütun seçiminde satır/sütun stili yolunu seçer).
- "Temizle ▸ Tümü" = `Grup(HucrelerDegis, BicimDegis)`; "Biçimleri temizle" = yalnız `BicimDegis`. `komutlar.ana_sayfa` `BicimDegis`'i tanır.
- **Satır/sütun ekle-sil:** `Sayfa._kaydir` `_stil`, `satir_stil/sutun_stil` ve birleşimleri de kaydırır; silinen stiller `silinen` gibi döner ve `_SatirSutun` geri alırken geri yazar. **Eklenen satır/sütun üstündeki satırın (solundaki sütunun) biçimini alır** — Excel'in varsayılan "Ekleme Seçenekleri" davranışı.
- **Pano:** `PanoVerisi.stiller {(dr,dc): Stil}` (kimlik değil `Stil` nesnesi → başka kitap/oturuma güvenli; JSON'da alan sözlüğü). Yapıştır = içerik + biçim (Excel "Tümü"); "Özel Yapıştır" (Değerler / Biçimler / Formüller) aynı planın alt kümeleri. Dışarıya HTML'de temel satır içi CSS (kalın, italik, renk, dolgu, hizalama); dışarıdan HTML'de aynı alt küme okunur (isteğe bağlı).
- **`HucreTasi`:** biçim de taşınır (kaynak kimlik 0'a döner, hedef taşınan kimlikleri alır), içindeki birleşimler de; tek geri al adımı (mevcut `_plan`'a stil planı eklenir).

## 3. Birleştirilmiş hücreler

- `Sayfa.birlesimler: List[Aralik]` + dizin `_birlesim_hucre: Dict[(r,c), Aralik]` (yalnız kapsanan hücreler; birleşimler küçük/az → bellek sorun değil). `birlesim(r,c) -> Optional[Aralik]`.
- Kurallar: çakışan birleşim **reddedilir**; birleştirirken sol üst dışındaki dolu hücreler silinir (UI önce Excel'deki gibi uyarır: "Yalnızca sol üstteki değer kalır"). Komut: `Grup(HucrelerDegis(silinecek), BirlesimDegis(eklenen, kaldırılan))`. "Birleştir ve Ortala" ek olarak sol üst stilde `yatay="orta"`. Çöz: içerik sol üstte kalır.
- Ekle-sil: birleşimin içine ekleme onu büyütür, silme küçültür, tamamen silinen kalkar (Excel gibi). Kopyala/yapıştır göreli birleşimleri taşır. Kapsanan hücreye başvuru boş değer okur (Excel de).
- Izgara: aktif hücre/oklar birleşimi tek hücre gibi gezer; seçim birleşimi kesiyorsa genişletilir (Excel).

## 4. Dondurulmuş bölmeler ve görünüm

- `Sayfa.dondur: Optional[Tuple[int, int]]` = kaydırılabilir bölgenin sol üst hücresi (Excel `pane topLeftCell`; `(2,1)` = üst satır, `(1,2)` = ilk sütun, `(r,c)` = seçili hücreden). `Sayfa.kilavuz: bool = True`.
- **Karar:** dondurma/kılavuz **geri al yığınına girmez** (Excel'de de geri alınamaz); `bicim` olayı `gorunum` anahtarıyla yayılır (kaydet kirli olur).

## 5. Doldurma (`model/doldur.py`, Qt yok)

- `seri_plani(sayfa, kaynak: Aralik, hedef: Aralik) -> (hucreler {anahtar: Hucre|None}, stiller {anahtar: kimlik})`; yön hedefin kaynağa göre konumundan; kaynak blok satır/sütun başına ayrı seri olarak tanınır, tanınmayan blok **desen olarak yinelenir**.
- Seri tanıma (sıra önemli):
  1. Formül → `kaydir.kopyala` (hedef ofsetine göre).
  2. Sayı: tek değer → **kopya** (Excel: Ctrl'siz sürükleme kopyalar); iki değer → sabit adım; 3+ → doğrusal eğilim (en küçük kareler; Excel'in "en iyi uyum" dolgusu — doğrulanacak).
  3. Tarih (sayı + `kod_coz(stil.sayi_bicimi).tarih_mi`): tek → +1 gün; iki → gün adımı; aynı gün farklı ay/yıl → ay/yıl adımı (doğrulanacak).
  4. Ay/gün adları (`sayi_bicimi.AYLAR/GUNLER` + kısaltmalar): döngüsel, büyük/küçük harf korunur.
  5. Metin + sayı (`Ürün 1`, `1. Çeyrek`): son sayı artar (tek değerde bile), basamak sayısı korunur (`A01` → `A02`).
  6. Diğer metin/mantıksal → kopya.
- Biçim: kaynak stiller desen olarak hedefe kopyalanır.
- **Ctrl+D / Ctrl+R:** seçimin ilk satırı/sütunu **kopyalanır** (seri değil; formül kayar, biçim gelir); tek hücre seçiliyken üstteki/soldaki hücreden. Ctrl+Enter: girdi tüm seçime (formül göreli kayar). Hepsi tek `Grup(HucrelerDegis, BicimDegis)`.

## 6. Akıllı giriş (`model/girdi.py`)

- Yeni **`akilli_coz(metin) -> (Hucre | None, onerilen_kod | None)`**; `girdi_coz` geriye uyumlu kalır (`akilli_coz(...)[0]`). Sıra: `'` → metin; `=` → formül; mantıksal; sayı (mevcut); yüzde (`%15`, `15%` → 0,15, `0%`/`0.00%`); para (`₺100`, `100 ₺`, `$100`, `100 €` → para kodu); kesir (`1 1/2` → 1,5, `# ?/?`); bilimsel (`1,5E3` → `0.00E+00`); saat (`14:30`, `14:30:15`, `2:30 ÖS`); tarih (`12.10.2026`, `12.10.26`, `12/10/2026`, `12-10-2026`, `12.10` = bu yıl, `12 Ekim 2026`, `12 Eki`; isteğe bağlı saatle). İki basamaklı yıl: 00–29 → 20xx, 30–99 → 19xx (Windows varsayılanı). Tarih → seri `tarihseri.ymd_seri`.
- Arayüz kuralı: önerilen kod yalnız hücrenin biçimi **Genel** ise aynı `Grup` içinde uygulanır; hücre **Metin (`@`)** biçimliyse her girdi metin kalır (Excel). Düzenleme metni (`duzenleme_metni`) tarih biçimli hücrede tarihi `gg.aa.yyyy` gösterir.
- `formul/donustur.sayi_metninden` aynı çözümleyiciyi kullanır (`="1.1.2026"+1` → tarih; §8b-14).
- **`METNEÇEVİR` (TEXT):** `formul/fonksiyonlar/metin.py` → `sayi_bicimi.bicimle(x, kod, yerel=True)`. Türkçe Excel'de TEXT'in biçim argümanı yerel dildedir (`"gg.aa.yyyy"`); kanonik kod da kabul edilir mi doğrulanacak.

## 7. Izgara çizimi — gereksinimler (Faz 1 ❌'leri burada kapanır)

- **Satır bazlı çizim önbelleği:** `_satir_onb[r] = [HucreCizim(c, metin, hizalama, renk, yazi_anahtari, dolgu, kenar, kaydir, tasma_bitis)]`. Kaynak: girdi/sonuç + etkin stil + `sayi_bicimi.bicimle`. Geçersiz kılma olaydan: `hucre`/`sonuc`/`bicim` → değişen satırlar; `yapi`/`boyut`/yakınlaştırma/yazı tipi → tümü. Genişliğe bağlı kısım (`sigdir`, `####`, taşma) `(r, c, genişlik)` anahtarlı ayrı önbellek.
- Çizim sırası: dolgu → kılavuz çizgileri (dolgulu hücrenin altında **çizilmez**, Excel) → kenarlıklar (komşu kenarda kalın olan kazanır) → metin (yazı tipi `QFont` önbelleği stil+yakınlaştırma anahtarlı; hizalama, girinti, dikey hiza, kaydırma `QTextLayout`) → seçim → başlıklar. Birleşim tek dikdörtgen; kapsanan hücreler atlanır.
- **Yatay artımlı kaydırma** (❌ 18,6 ms): `viewport().scroll(dx)` + açığa çıkan sütunlar; satır önbelleğindeki `tasma_bitis` ile açığa çıkan bölgeye taşan metinlerin kaynak sütunları da yeniden çizilir.
- **Sıçrama** (❌ 28,8 ms): satır önbelleği + `QStaticText` tekrar kullanımı; ilk ölçümde hedef ≤ 16 ms.
- **Shift+Ok / Ctrl+A özeti** (❌ 25 / 105 ms): durum çubuğu özeti 50 ms tek atımlık zamanlayıcıyla ertelenir (çizim beklemez).
- **Dondurma:** 4 bölge, her biri kendi kaydırma ofsetiyle; artımlı kaydırma yalnız kaydırılabilir bölgede (`scroll(dx, dy, rect)`).
- `sayi_bicimi` ölçümü (bu oturum, 100.000 çağrı): Genel 2,8 µs; `0` / `#,##0.00` / `0.0%` / `"₺"#,##0.00` 6,5–8,6 µs (hızlı yol); tarih 10,6 µs; saat 9,1 µs; bilimsel 30 µs; kesir ~55 µs. Görünen ~1.000 hücrenin soğuk biçimlemesi ≈ 7–10 ms → **önbellek zorunlu** (yalnız ilk görünüşte biçimlenir).
- Ölçütler: `araclar/performans_olcum.py` tüm satırlar ≤ 16 ms (özet ≤ 100 ms); yeni senaryo: 100.000 hücre, 10 farklı stil + 4 sayı biçimi, kaydırma ≤ 16 ms; `araclar/cizim_dogrula.py` 0 piksel fark (dolgu/kenarlık/birleşim/dondurma adımlarıyla genişletilir).

## 8. Sonnet'e devir — sıralı alt işler (her biri testli; kural 11/12)

| # | İş | Bitiş ölçütü |
|---|---|---|
| 3a | `model/stil.py` (`Stil`, `Kenarlik`, `StilYama`, `StilHavuzu`) + `Sayfa` stil depoları + `bicim` olayı + `BicimDegis` + ekle-sil kaydırması (üstteki biçimi devralma) | Qt'siz testler: interning, etkin stil önceliği, tek olay, geri al/yinele, ekle-sil + geri al, 100.000 hücreye yama < 300 ms |
| 3b | Pano biçim taşıma (`PanoVerisi.stiller`, JSON), `HucreTasi` stil+birleşim, Temizle menüsü (Tümü/Biçimler/İçerik), Delete biçimi korur | Gidiş-dönüş testleri; mevcut pano testleri bozulmaz |
| 3c | **Izgara çizimi yeniden** (§7): satır önbelleği, dolgu, kenarlık, yazı tipi/renk/hizalama, `sayi_bicimi.sigdir`/`doldur`, yatay artımlı kaydırma, ertelenmiş özet | §7 ölçütleri; `cizim_dogrula` 0 fark; ekran görüntüsü incelemesi |
| 3d | Biçim araç çubuğu (yazı tipi, boyut, K/İ/A, yazı/dolgu rengi — Sözcük renk seçicisi, kenarlık menüsü, hizalama, birleştir, sayı biçimi listesi `HAZIR`, ondalık artır/azalt `ondalik_degistir`, %, ₺, binlik) + kısayollar | Her düğme için ekransız test; kısayolların Türkçe Excel karşılığı doğrulanana dek Sözcük'teki kararla aynı |
| 3e | "Hücreleri Biçimlendir" (Ctrl+1): Sayı (kategoriler + **Özel**: kod yerel yazımla girilir/gösterilir `yerele/kanonige`, `BicimHatasi` → Excel'deki gibi uyarı, canlı önizleme), Hizalama, Yazı Tipi, Kenarlık, Dolgu | Kanonik saklanır, yerel görünür (test) |
| 3f | Birleştirme (§3): model + komut + gezinme/seçim/çizim | Çakışma reddi, ekle-sil, pano, geri al testleri |
| 3g | Akıllı giriş (§6) + `donustur` tarih metni + Metin biçimli hücre + **METNEÇEVİR** | Her desen için 4 vaka; §8b satırları güncellenir |
| 3h | Doldurma (§5): `model/doldur.py`, Ctrl+D/R/Enter, doldurma tutamacı (sürükle, çift tık aşağı doldur) | Seri türleri × 4 vaka; tek geri al adımı |
| 3i | Dondurulmuş bölmeler + kılavuz çizgisi göster/gizle (§4, §7) | Kaydırma/seçim/çizim testleri; piksel doğrulama |
| 3j | Metni kaydır + satır yüksekliğini içeriğe göre otomatik ayarlama (Alt+Enter kaydırmayı açar, Excel) | §8b-11 güncellenir |
| 3k | Biçim boyacısı (tek tık bir kez, çift tık kalıcı, Esc) | Ekransız test |
| 3l | Faz 3 sonu: `test.md` bölümü, gerçek iş senaryosu (biçimli bütçe), performans ölçümü, Opus gözden geçirmesi | plan.md faz bitiş ölçütü |

**Arayüz sözleşmesi (çekirdek, hazır):** `model/sayi_bicimi.py`
- `bicimle(deger, kod="General", yerel=False) -> BicimSonucu(metin, renk, hizalama, dolgu, diyez)` — `renk` `#RRGGBB`/None; `hizalama` ∈ `sol/sag/orta` (stil `yatay="genel"` iken kullanılır); `dolgu` `*x` için `(konum, x)`; `diyez` → hücre `####`.
- `sigdir(deger, kod, sigar) -> str | None` (Genel: `gosterim.sayiyi_sigdir` ile birebir; diğerleri kısaltılmaz, sığmazsa None → `####`), `doldur(sonuc, sigar)`.
- `kod_coz(kod, yerel=False) -> BicimKodu` (önbellekli; `.tarih_mi`, `.genel_mi`, `.yaz(yerel)`), `BicimHatasi`.
- `yerele(kod)`, `kanonige(kod)`; `HAZIR` + `ad_kodu(ad)`; `ondalik_degistir(kod, ±1, deger)`; `AYLAR`, `GUNLER`, `AY_KISA`, `GUN_KISA`.
- `model/tarihseri.py`: `seri_ymd`, `ymd_seri`, `ay_gun_sayisi`, `ayin_ilki`, `haftanin_gunu0`, `MAKS_SERI` (formül fonksiyonları buradan alır; `model/` → `formul/` içe aktarması yok).

## 9. Kararlar (Excel'den bilinçli farklar ve varsayımlar)
- `kullanilan_aralik` içerik tabanlı; biçimli boş hücreler yalnız `bicim_dahil=True` ile (§1).
- Yerel biçim kodunda saat/dakika/saniye harfleri kanonik (`h`, `m`, `s`); yalnız gün `g` ve ay `a` Türkçeleşir. Gerekçe: Microsoft tr-tr kılavuzu saat/dakika/saniye harflerinde kendi içinde çelişkili; doğrulanınca değişir (§8b). Yerelde `a` her zaman ay, `m` Excel'in bağlam kuralıyla (saatten sonra / saniyeden önce dakika) çözülür; `d` de gün kabul edilir.
- Yerel → kanonik çeviride "saatten hemen sonra açıkça ay" (`hh:aa`) yazımı kanonikte dakika okunur (kanonik yazımda ifade edilemez; kenar durum).
- Renkli sayı biçimi metin hücresine (metin bölümü yoksa) renk uygulamaz; hiçbir koşula uymayan sayı `####`; negatif değerin sıfıra yuvarlanması `-0` gösterir (Excel davranışı doğrulanacak).
- `[Renk N]` Türkçe yazımı doğrulanmadığından yalnız `[ColorN]` tanınır; yerel yazımda da `[ColorN]` görünür.
- Dondurma/kılavuz geri al yığınına girmez (Excel gibi).
