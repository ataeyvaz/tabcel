# Seçim modeli ayrımı (çapa ≠ etkin hücre): tasarım notu (Opus 5.5, 2026-10-11)

Kaynak: `surec.md` T2 günlüğü; `testler/test_kisayollar.py` içindeki 3 strict xfail (`FARK`).

## 1. Sorun
`Izgara._aktif` iki işi birden yapıyor: **etkin hücre** (düzenleme, formül çubuğu, beyaz çizilen
hücre, not/doğrulama, ad kutusu) ve **seçim çapası** (`secim = _aktif ↔ _uc`). Excel'de bunlar ayrı;
bu yüzden etkin hücre seçimi bozmadan seçim içinde hareket edemiyor.

## 2. Karar: yeni alan `_capa`; `_aktif` "etkin hücre" anlamında kalır
grid.py'deki 64 `_aktif` kullanımının ≈ 50'si zaten "etkin hücre" demek (düzenleme 2529–2853,
doğrulama 3005–3071, not 1422–1431, çizim 1218–1241, dosya_islemleri/window/nesne yapıştırma) →
**dokunulmaz**. Değişen yalnız çapa anlamındaki ≈ 14 yer:

| Yer (grid.py) | Bugün | Yeni |
|---|---|---|
| 275 `__init__` | `_aktif`, `_uc` | + `_capa = (1, 1)` |
| 696 `secim` | `_aktif ↔ _uc` | `_capa ↔ _uc` |
| 707–723 `sec(aktif, uc, kaydir)` | çapa = etkin | imza aynı + `etkin=None`: `_capa = aktif`, `_aktif = etkin or aktif` (seçim içine kıstırılır); `aktifDegisti` etkin değişince |
| 725–746 `_birlesime_uydur` | `_aktif` çapa | genişleme `_capa`/`_uc` üzerinden; etkin hücre birleşimdeyse sol üste |
| 1715, 1764–1768 Shift+tık, başlık Shift+tık | `sec(self._aktif, …)` | `sec(self._capa, …, etkin=self._aktif)` |
| 1810, 1816 başlık Shift+sürükle | `_aktif[1]` | `_capa[1]` / `_capa[0]` |
| 1853/1861/1869 Shift+ok/PgDn/Home | kaynak `_uc` | aynı (uç); genişletme `_git` → `sec(self._capa, hedef, etkin=self._aktif)` (3284) |
| 1874 Ctrl+A | tüm sayfa | §3.3 |
| 1876–1879 Ctrl/Shift+Boşluk | `_sutun_sec` etkin hücreyi taşır | `_sutun_sec(c, etkin=self._aktif)` |
| 1880–1888 Tab/Enter | seçimi daraltıp ilerler | §3.1 |
| 2817–2819 düzenleme Enter ile onay | `sec((r+dr, c+dc))` | aynı §3.1 yolu (çok hücreli seçimde içinde dolaşır) |

**Geriye uyum:** `sec(a, u)` çağıran her yer (≈ 40, testler dahil) aynı anlamı korur (çapa = etkin =
`a`). `aktif`/`secim`/`secimler` özellikleri ve sinyaller aynı. Ok tuşu (Shift'siz) etkin hücreden
çıkar ve seçimi tek hücreye indirir (Excel gibi; bugünkü davranış).

## 3. Davranış (Excel)
### 3.1 Enter / Shift+Enter / Tab / Shift+Tab, çok hücreli seçimde
- Seçim tek hücreyse: bugünkü gibi (seçim dışına bir hücre).
- Çok hücreliyse etkin hücre **seçimin içinde** ilerler, seçim değişmez:
  Enter aşağı → sütun sonunda sonraki sütunun başı → son hücreden ilk hücreye; Tab sağa → satır
  sonunda sonraki satırın başı; Shift ters yön. Gizli satır/sütun atlanır, birleşik hücre tek
  adım (sol üstü). **Çoklu aralıkta** son hücreden sonraki aralığın ilk hücresine geçilir (Excel).
- Tam sütun/satır seçimi (A:A) de aynı kural; çok büyük seçimde (tam sayfa) son hücreye sarmak için
  gezinme yok, aritmetik (O(1)).
- **Belirsiz (Excel'de denenecek, §8b):** Enter ile seçim içinde ilerledikten sonra Shift+ok
  genişletmenin çapası özgün çapa mı (bizim önerimiz) yoksa etkin hücre mi.

### 3.2 Ctrl+Boşluk / Shift+Boşluk
Sütun/satır seçilir, **etkin hücre yerinde kalır** (`etkin=self._aktif`); ardından Shift+Sağ bir
sütun genişletir (çapa sütunun başı).

### 3.3 Ctrl+A
Etkin hücre boş olmayan bir veri bölgesindeyse ve seçim o bölgeye eşit değilse →
`adres.bitisik_bolge(sayfa, *aktif)` seçilir; aksi halde tüm sayfa. Etkin hücre korunur. (Excel'in
"tablo içinde üç aşama" davranışı yok — Tablo nesnesi Faz 8.)

## 4. Riskler
- Çizim: `_secim_boya` eski/yeni etkin hücreyi ayrıca boyuyor (758) → seçim değişmeden etkin hücre
  değişince de doğru bölge boyanmalı; `_secim_farki_boya` "etkin değişti → hızlı yol yok" diyor (775),
  bu yeni durumda küçük bir hızlandırma: yalnız iki hücre boyanır.
- İşaretleme modu (`_isaret_capa`) ayrı alan; etkilenmez.
- Biçim boyacısı, doldurma tutamacı, pano: `secim` okur → çapa değişikliğinden bağımsız.

## 5. Test stratejisi
1. Önce: `test_kisayollar.py` + seçim/ızgara/pano/doldurma/birleşim testleri koşulur (taban).
2. 3 strict xfail düzelince **XPASS → başarısız** olur; bu beklenen sinyal: `xfail` işaretleri
   kaldırılır (test gevşetme değil, sabitleme). Kural 12 gereği listede bildiririm.
3. Yeni testler (`test_kisayollar.py`'ye): Enter sarma (sütun → sonraki sütun → başa), Shift+Enter
   ters, Tab satır düzeni, tek hücrede eski davranış, gizli satır atlama, birleşik hücre tek adım,
   çoklu aralık geçişi, düzenleme Enter ile onaylanınca seçim içinde ilerleme, Ctrl+Boşluk sonra
   Shift+Sağ, Ctrl+A iki basış + boş hücrede doğrudan tüm sayfa, `aktifDegisti` yayılır/`secimDegisti`
   yayılmaz.
4. `yardim.md`: "Excel'den Farklar"dan 3 madde çıkar, Klavye Kısayolları'na Enter/Tab-seçim içinde.
