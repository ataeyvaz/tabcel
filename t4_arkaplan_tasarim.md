# T4b — Otomatik kaydı arka planda yazma: tasarım notu (Opus 5.5, 2026-10-11)

## 1. Sorun
`dosya_islemleri.otokayit_yap` → `kurtarma.kopya_yaz` → `xlsx_io.kaydet` ana iş parçacığında:
100.000 hücre 3,3 sn, 500.000 hücre 16,6 sn donma (T4 ölçümü). T4'teki hafifletme yalnız aralığı
uzatıyor; donma sürüyor.

## 2. Seçenekler
| | Yöntem | ➕ | ➖ |
|---|---|---|---|
| A | **Kilit**: arka plan yazarken kitap kilitli, düzenleme bekler | basit | kullanıcı yazınca yine donar → sorunu taşır, çözmez |
| B | **Anlık görüntü + iş parçacığı**: ana iş parçacığında kitabın kap (dict/list/set) kopyası, yazma `QThread`'de | düzenleme sürer; model zaten değişmez değerlerle kurulu | GIL: yazma saf Python → ana iş parçacığıyla zaman paylaşır (arayüz akıcı ama kayıt biraz uzar); geçici bellek |
| C | Anlık görüntü + **ayrı süreç** | gerçek paralellik | görüntüyü pickle etmek ana iş parçacığında yine ≈ yazma süresinin önemli kısmı; süreç başlatma (PySide6'sız alt süreç) + RAM 7,9 GB |

**Öneri: B.** C'ye ancak B ölçümde yetmezse geçilir.

## 3. Anlık görüntü neden ucuz ve güvenli
Model değerleri **değişmez**: `Hucre` (frozen), `Stil`/`Kenarlik` (frozen), `SayfaYapisi` (frozen),
Faz 5 nesneleri (not/doğrulama/koşullu/filtre: "değişmez nesneler" kararı), `Hata`. Değişen yalnız
**kaplar** (`_hucreler`, `_stil`, `_sonuc`, `satir_stil`, `gizli_satir`, `birlesimler`, `nesneler`…).
`StilHavuzu` yalnız büyür (kimlikler kalıcı) → kopyalanmaz, paylaşılır.

```python
# model/anlik.py (Qt yok)
def kitap_anligi(kitap) -> CalismaKitabi   # olay dinleyicisi olmayan, salt okunur kopya
```
- Her `Sayfa` için `copy.copy` + yazıcının okuduğu her kap için sığ kopya (`dict(...)`, `set(...)`,
  `list(...)`); kitap düzeyinde `sayfalar`, `adlar`. `Grafik`/`Resim` frozen (denetlendi) →
  `nesneler` listesinin sığ kopyası yeter; resim baytları paylaşılır (`bytes` değişmez).
- **Bekçi testi:** yazıcının (`xlsx_io.kaydet`, `xlsx_grafik.nesneleri_yaz`) eriştiği tüm `Sayfa`
  öznitelikleri görüntüde kopya mı — `Sayfa.__dict__` üzerinde: liste/dict/set olan her alan kopya
  olmalı (yeni alan eklenince test uyarır). Değişmezlik: model türlerinin `frozen` olduğunu sınayan test.
- Maliyet tahmini: 500.000 girdili dict kopyası ≈ 15–30 ms (ölçülecek; ölçüt < 100 ms ana iş parçacığı).

## 4. Akış (`ui/dosya_islemleri.py`)
1. Zamanlayıcı → `otokayit_yap`: değişmemişse/son damga aynıysa çık (bugünkü gibi). **Önceki yazma
   sürüyorsa çık** (aynı anda tek yazıcı).
2. Ana iş parçacığında `damga` + `kitap_anligi` + rapor kopyası.
3. `_OtokayitIsi(QThread)`: `kurtarma.kopya_yaz(anlik, …)` (xlsx önce, json sonra — değişmez; yarıda
   kalan yazma eski kopyayı bozmaz: geçici dosya → yerine koy, kural 8).
4. Bitince (sinyal, ana iş parçacığı): başarılıysa `_son_otokayit = damga`; hata sessiz.
5. Aralık kuralı kalır ama yalnız GIL payı için: `max(2 dk, süre × 10)`.

## 5. Yarış durumları (asıl risk)
| Durum | Çözüm |
|---|---|
| Kullanıcı Kaydet/Kapat → `kurtarma.sil(kimlik)` yazma sürerken | `sil` öncesi `otokayit_bekle()` (iş biter ya da iptal bayrağı); bitince sil. Yoksa iş sonradan dosya oluşturur → sonraki açılışta sahte kurtarma önerisi |
| Pencere/uygulama kapanıyor | `closeEvent` işi bekler (en çok yazma süresi; 500.000'de bilgi çubuğu "kurtarma kopyası yazılıyor…") ya da iptal edip yarım `.tmp`'yi siler |
| Yazma sırasında kitap değişti | görüntü değişmez; damga eski → sonraki turda yeniden yazılır |
| `xlsx_io.kaydet` modül düzeyi önbellek/genel durum | denetlenecek: paylaşılan formül önbelleği (`_FormulOnbellek`) çağrı başına yerel ✔; `ad_agaci` `lru_cache` iş parçacığı güvenli (CPython) ✔; openpyxl iş parçacığı başına `Workbook` ✔ |
| Kullanıcının kendi Kaydet'i (`arka_planda`, pencere devre dışı) ile çakışma | farklı dosyalar; ama ikisi aynı anda RAM'i ikiye katlamasın → elle kayıtta önce otokayıt işi beklenir |
| Kurtarma kopyası ile `veri_kaybi` raporu | rapor görüntü anında kopyalanır |

## 6. Ölçüt ve test
- Ölçüm (`araclar/dosya_olcum.py`'ye ek): 100.000 / 500.000 hücrede ana iş parçacığı tıkanması
  (görüntü süresi + yazma sırasında 16 ms'lik zamanlayıcı gecikmesinin en büyüğü). Ölçüt: tıkanma
  < 100 ms, en büyük olay döngüsü gecikmesi < 200 ms.
- Testler (`test_kurtarma.py`'ye): görüntü sonrası kitap değişikliği kopyaya yansımaz; kopya =
  görüntü anındaki kitap (yeniden aç + karşılaştır); iş sürerken ikinci tetik yazmaz; `sil` işi
  bekler (iş yavaşlatılmış sahte `kopya_yaz` ile → yarıştan sonra dosya kalmaz); kapanışta bekleme;
  hata sinyali sessiz; bekçi (kaplar kopya, türler frozen). Süre ölçütleri test değil, ölçüm betiği.
- Mevcut 16 kurtarma testi değişmeden geçmeli; `otokayit_yap`'ın eşzamanlı davranışına dayanan testler
  için `otokayit_yap(bekle=True)` (test/kapanış yolu) eklenir — mevcut test değişirse bildiririm.

## 6b. Uygulama sonrası ölçüm (2026-10-11)
- Anlık görüntü (ana iş parçacığı): 100.000 hücre **5,5 ms**, 500.000 hücre **39 ms** (önce donma 3,3 / 16,6 sn) ✅
- 100.000 hücrede arka plan yazımı sırasında ana iş parçacığı: en büyük gecikme **181 ms**, ortalama 9,5 ms ✅
  (yazım süresi ≈ 5 sn, GIL paylaşımı; zamanlayıcı aralığı `max(2 dk, süre × 10)`)
- `otokayit_yap()` genel yöntemi **eşzamanlı** kaldı (aynı anlık görüntüden yazar) → mevcut testler değişmedi;
  zamanlayıcı `otokayit_yap(arka_plan=True)` çağırır. `otokayit_bekle()`: kurtarma kopyası silinmeden,
  elle .xlsx kaydından ve pencere kapanmadan önce

## 7. Kapsam dışı
Elle Kaydet'in arka plana alınması (bugün `arka_planda` + pencere devre dışı; doğru ve güvenli),
alt süreç (C), artımlı/fark kaydı.
