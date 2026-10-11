# T9 — Sayfa sonları ve sayfa taşması ayarları (tasarım notu, 2026-10-11)

Yazan: Sonnet 5.5 (surec.md'de Opus önerilmişti; kapsam küçük ve mevcut `sayfala`/`SayfaYapisi` üzerine kurulu olduğu için doğrudan yazıldı — **Opus gözden geçirmesi önerilir**). İstek: kullanıcı, 2026-10-11 ("sayfa sınır çizgilerini göremiyorum… satır ve sütunların ayarı ile sayfa taşkınlıklarını da ayarlayabilmeliyiz").

## 1. Kapsam
1. **Ekranda sayfa sınırı çizgileri:** otomatik sınır = kesikli gri, el ile sonu = düz koyu çizgi (Excel gibi). Görünüm → "Sayfa Sonlarını Göster" (sayfaya özel, varsayılan kapalı; el ile sayfa sonu eklenince açılır). Çizgi yazdırma alanı boyunca uzanır.
2. **El ile sayfa sonu:** Sayfa Düzeni → Kesmeler: *Sayfa Sonu Ekle* (etkin hücrenin üstüne ve soluna; A sütunundaysa yalnız yatay, 1. satırdaysa yalnız dikey, A1'de kapalı), *Sayfa Sonunu Kaldır* (etkin hücrenin üstündeki/solundaki kesme), *Tüm Sayfa Sonlarını Sıfırla*. Geri alınır.
3. **Taşma ayarları:** *Yüksekliği tek sayfaya sığdır* (genişlikle birlikte ya da ayrı), *Sayfa sırası* (önce aşağı / önce sağa). Sayfa Yapısı penceresinde de.
4. `.xlsx`: `rowBreaks/colBreaks` (yalnız el ile, `man=1`), `fitToWidth/fitToHeight`, `pageOrder`.

Kapsam dışı (sonra): *Sayfa Sonu Önizleme* görünümü (mavi sınırı sürükleme), üst/alt bilgi, sayfa numarası.

## 2. Model (Qt'siz)
- `SayfaYapisi` yeni alanlar (hepsi varsayılanlı; mevcut kayıtlar/testler değişmez): `satir_kesmeleri: Tuple[int,...]`, `sutun_kesmeleri: Tuple[int,...]` (sıralı, tekrarsız, ≥ 2; **değer = yeni sayfanın BAŞLADIĞI satır/sütun**, Excel'deki "üstüne kesme" anlamı), `sigdir_yukseklik: bool`, `sayfa_sirasi: "asagi_sonra_sag" | "sag_sonra_asagi"`. Doğrulama `__post_init__`'te.
- **Kararlar:** kesmeler `SayfaYapisi`nde durur → `SayfaYapisiDegis` geri al/yinele bedavadır, sayfaya özeldir.
- **Satır/sütun ekle-sil kesmeleri kaydırır** (Excel gibi): `Sayfa._kaydir` içinde `_yapiyi_kaydir` — kesmeler `_kaydir_indeks` ile; silinen bant içindeki kesme düşer. Aynı yerde **yazdırma alanı** (`aralik_kaydir`) ve **başlık satırları** da kaydırılır (şimdiye dek kaymıyordu — küçük hata, aynı iş parçasında düzeltilir, bildirilir). `_SatirSutun.yap/geri_al` `sayfa_yapisi`ni saklar/geri yükler.
- **`sayfala`:** kesmeler **yalnız ölçek ve "sığdır" kapalıyken** uygulanır (Excel: "sığdır" seçilince el ile sayfa sonları yok sayılır). `_bol(..., kesmeler)`: kesme satırı/sütunu yeni dilim başlatır; ondan sonra otomatik bölme sürer; yinelenen başlık yer ayırması kesmeden sonraki dilimlerde de uygulanır. `sigdir_yukseklik`: `olcek = min(1, sayfa_g/toplam_g [sigdir_genislik ise], sayfa_y/toplam_y)` (alt sınır 0,1). `sayfa_sirasi` yalnız numaralamayı (döngü sırası) değiştirir.
- Yeni `sayfa_sinirlari(sayfa, yapi, gen, yuk) -> SayfaSinirlari(satirlar: ((satir, el_ile),…), sutunlar: ((sutun, el_ile),…), alan)`: `sayfala` ile **aynı bölme kodu** (ortak `_plan`), ekranda ve yazdırmada tutarsızlık olmasın. Çizgi, ilgili satırın/sütunun **önünde**dir.

## 3. .xlsx
- Yazma: `ws.row_breaks.append(Break(id=r-1, man=True))` (Excel `id` = kesmeden ÖNCEKİ satır), `col_breaks` aynı; `pageSetup.pageOrder = "overThenDown"` (yalnız sağ-sonra-aşağı iken); `fitToWidth = 1 / 0`, `fitToHeight = 1 / 0`, `fitToPage` ikisinden biri açıksa.
- Okuma: yalnız `man` kesmeler (Excel otomatik olanları yazmaz); `id+1`; aralık dışı/bozuk atlanır. **Fit okuma düzeltmesi:** `fitToWidth/Height` yoksa 1 sayılır, 0 = serbest (şimdiki "fitToPage → yalnız genişlik" varsayımı kalkar; Tabcel'in kendi yazdığı dosya aynı kalır).

## 4. Arayüz
- **Izgara çizimi** (`_boya`, nesnelerden önce, dondurma çizgisinden önce): `sayfa_sinirlari` **önbelleklenir** (anahtar: `sayfa_yapisi` kimliği + boyut/yapı/içerik olay sayacı; tembel; yalnız seçenek açıkken hesaplanır — 100.000 satırda her karede hesap yok). Çizgi: otomatik `#7f7f7f` kesikli 1 px, el ile `#444` düz 1 px; hücre kılavuzunun üstünde, seçimin altında. Yakınlaştırma ve dondurmayla uyumlu (hücre dikdörtgeni yardımcılarından).
- **Şerit:** Sayfa Düzeni → Sayfa Yapısı grubuna "Kesmeler ▾" (Ekle / Kaldır / Sıfırla); Sığdır grubuna "Yüksekliği tek sayfaya sığdır" ve "Sayfa sırası ▾"; Görünüm → Göster: "Sayfa Sonlarını Göster". Kısayol yok.
- **Sayfa Yapısı penceresi:** yükseklik sığdır + sayfa sırası alanları (kesmeler pencerede değil, ızgarada).
- Etkinlik: Ekle/Kaldır etkin hücreye göre açık/kapalı; "sığdır" açıkken kesme eklenebilir ama durum çubuğunda/ipucunda "Sığdır açıkken sayfa sonları yok sayılır" bilgisi.

## 5. Excel'den bilinçli farklar / belirsizler
- Sayfa sonları ekranda varsayılan **kapalı** (Excel de yazdırma/önizlemeden önce göstermez); açma durumu `.xlsx`e yazılmaz (kapanışta unutulur). **Belirsiz:** Excel'in manuel sayfa sonunu hemen gösterip göstermediği — biz gösteririz.
- Kesme silinen satıra denk gelirse düşer (Excel'in tam davranışı doğrulanmadı → `surec.md` §8b "Excel web'de doğrulanacaklar").
- Sayfa Sonu Önizleme (sürüklenebilir mavi sınır) yok.

## 6. Test ölçütleri (kural 11/12/13)
`test_sayfa_sonlari.py`: model (doğrulama, `sayfala` kesmeli bölme/başlık yineleme/sığdır yok sayar/sığdır yükseklik ölçeği/sayfa sırası, `sayfa_sinirlari` = `sayfala` ile uyum, ekle-sil kayması + alan/başlık kayması + geri al, `.xlsx` gidiş-dönüş + Excel-benzeri dosya + fit okuma), arayüz (Ekle/Kaldır/Sıfırla etkin-hücre kuralları, geri al, şerit taşma 800/1100 px, çizgi piksel testi açık/kapalı/el ile/otomatik, dondurma/yakınlaştırma, PDF dilim sayısı). Gerçek Excel'de `ExportAsFixedFormat` ile sayfa sayısı karşılaştırması (COM). `yardim.md`: Yazdırma, Görünüm, Kısayol yok, Yenilikler, "Excel'den Farklar".
