# T8 — Türkçe hata açıklamaları: tasarım notu (Opus 5.5, 2026-10-11)

**Hedef:** hata değeri olan hücrede (fareyle üzerine gelince ipucu, etkin hücre olunca durum çubuğu)
anlaşılır açıklama: `#DEĞER!: B3 hücresinde sayı yerine metin var.` Hata başka hücreden geliyorsa
zincir: `#DEĞER!: C5'ten geliyor → C5: B3 hücresinde sayı yerine metin var.`

## 1. Bugünkü durum (kodda bulunanlar)
- `model/deger.Hata` donmuş dataclass, tek alan `kod`; 7 **tekil** nesne (`D.BOL0`, `D.DEGER_HATASI`…).
  Eşitlik `kod`la; kodda `is D.X` kimlik denetimi **yok** (grep), xlsx/pano/gösterim yalnız `kod` okur.
- Hata üretilen yer ≈ **140**: `degerlendir.py` (işleçler, aralık/kesişim, bilinmeyen işlev, argüman
  sayısı, tanımsız ad, silinmiş sayfa), `donustur.py` (`sayiya`/`mantiga` → #DEĞER!, `sayi_sonucu` →
  #SAYI!), `motor._degerle` (çözümlenemeyen formül → #AD?, özyineleme → #SAYI!, istisna → #DEĞER!) ve
  işlev grupları (arama 26, istatistik 18, tarih/matematik 16, metin 15, finans 13…).
- Hata, üretildiği yerden **dönüş değeri olarak yukarı yayılır** (her işleç/işlev "argüman hataysa
  onu döndür" der). Değer okunurken adres kaybolur: `AralikDeger.hucre_degeri` yalnız değeri verir,
  `sayiya("abc")` hangi hücreden geldiğini bilmez.
- Motor her formül hücresinin öncüllerini tutar: `_kayit[a].hucreler` (tek hücreler) ve
  `.araliklar` (kutular). Hesap sonucu `Sayfa._sonuc`'ta.

## 2. Seçenekler

### A — Neden bilgisini `Hata` nesnesinde taşımak (hesap anında)
`Hata(kod, neden=..., kaynak=(sayfa, r, c))`, `compare=False` alanlarla (eşitlik değişmez).
- ➕ Açıklama hazır durur, ipucu anında okunur.
- ➖ ≈140 üretim yerinin hepsine bağlam (hangi argüman, hangi hücre) eklemek gerekir; adres bilgisi
  `sayiya`'ya kadar inmiyor → `AralikDeger`/`_okuyucu`/`_yay` imzaları değişir. Formül çekirdeğine
  geniş, riskli dokunuş (kural 12: 3000+ test).
- ➖ **Performans:** tekil nesne yerine her hata için yeni nesne + metin. 100.000 hücrelik bir sütunda
  `=A1/B1` ve B boşsa 100.000 nesne + biçimlenmiş metin; dizi işlemlerinde öğe başına. Hesap yolu
  ölçülebilir yavaşlar, kimse ipucuna bakmasa bile.
- ➖ `_sonuc` artık nedenli nesneler tutar → kurtarma kopyası/xlsx önbelleği/pano bunu yok saymalı,
  geri al sonrası yeniden hesapta neden yeniden üretilmeli (tutarlılık yükü).

### B — Bağımlılık grafiğinde zincirleme geri izleme (yalnız grafik)
Hatalı hücrenin öncüllerinden aynı kodlu hata taşıyanı bul, oradan devam et; öncülü temiz olan ilk
hücre = **kaynak**.
- ➕ Hesap yoluna sıfır maliyet, çekirdeğe dokunmaz, yalnız istenince çalışır.
- ➖ Yalnız "nerede" der, "neden" demez (`B3`'teki formül neden #DEĞER! verdi?). Hedef metnin yarısı.

### C — İsteğe bağlı tanı değerlendirmesi (önerilen: B + tanı)
Kullanıcı hatalı hücreye bakınca:
1. **Geri izleme (B):** öncül grafiğinde aynı kodlu hatayı taşıyan hücre zinciri → kaynak hücre.
2. **Tanı:** kaynak hücrenin formül ağacı **ayrı bir yürüyücüyle** baştan değerlendirilir; her düğüm
   için normal `degerlendir` çağrılır ve "sonucu hata, çocuklarının hiçbiri o hatayı taşımıyor" olan
   **ilk (en derin) düğüm** hatanın doğduğu yerdir. Açıklama o düğümün türünden ve işlenenlerinden
   kurulur (işlenen bir `Ref` ise adresi bilinir → "B3 hücresinde…").
- ➕ Hesap yolu **hiç değişmez** (≈140 yere dokunulmaz, `Hata` aynı kalır) → performans, geri al,
  xlsx, kurtarma etkisi **yok**.
- ➕ Excel'in kendi yaklaşımıyla aynı: Excel de nedeni saklamaz, "Hatayı İzle"/"Hata denetimi"
  istenince hesaplar.
- ➖ Tanı formülü bir kez daha değerlendirir (düğüm başına alt ağaç: derinlik² — formüller küçük,
  ölçülecek). Değişken işlevlerde (S_SAYI_ÜRET, ŞİMDİ) yeniden değerlendirme farklı sonuç verebilir →
  tanıdaki değer kayıtlı sonuçla aynı koddan değilse "neden belirlenemedi" denir.
- ➖ Tembel işlevlerde (EĞER) hangi dalın seçildiğini dışarıdan bilmek gerek → kural: sonucu hata olan
  çağrıda, **değeri aynı kodlu hata olan ilk argümana** inilir; yoksa işlevin kendisi kaynaktır.

**Öneri: C.** A'nın tek üstünlüğü (anında okuma) ipucu için gereksiz; C'nin maliyeti yalnız bakılan
hücrede, sınırlı ve ölçülebilir.

## 3. Önerilen yapı

### 3.1 `formul/hata_neden.py` (Qt yok, kural 2)
```python
@dataclass(frozen=True)
class Adim:            # zincirin bir halkası
    sayfa: object; satir: int; sutun: int
    kod: str           # kanonik
    neden: str | None  # yalnız kaynak hücrede dolu (Türkçe cümle)

def acikla(kitap, sayfa, r, c, sinir=10_000) -> list[Adim] | None
def metin(adimlar, etkin_sayfa) -> str     # "#DEĞER!: C5'ten geliyor → C5: B3 hücresinde …"
```
- **Geri izleme:** öncüller `formul_ayristir` + `motor._oncul_topla` (kendi sayfasına göre) ile
  bulunur — motora bağımlı değil (kitapsız/motorsuz testte de çalışır). Aralık öncülünde yalnız
  aralıktaki **dolu** hücreler gezilir (`Sayfa.aralikta`); aynı kodlu ilk hücre (satır sırası) seçilir.
  Ziyaret kümesi + `sinir` adım (aşılırsa "kaynak bulunamadı: zincir çok uzun"). Döngü yok sayılır.
- **Hata formülsüz hücredeyse** (elle yazılmış `#YOK`, xlsx'ten gelen değer): "Hücreye hata değeri
  yazılmış." Çözümlenemeyen formül (`kayit.agac is None`): "Formül çözümlenemedi."
- **Tanı yürüyücüsü** düğüm türüne göre:
  | Düğüm / durum | Açıklama örneği |
  |---|---|
  | `+ - * / ^ %`, tekli `-`; işlenen metin, `sayiya` → #DEĞER! | "B3 hücresinde sayı yerine metin var (\"abc\")." / işlenen sabitse "Formülde sayı yerine metin var (\"abc\")." |
  | `/` sıfır ya da boş bölen | "Bölen (B3) sıfır ya da boş." |
  | `^` 0^0, negatif tabanın kesirli üssü, taşma | "0'ın 0. kuvveti tanımsız." / "Sonuç hesaplanamayacak kadar büyük ya da geçersiz." |
  | `sayi_sonucu` sonsuz/NaN | "Sonuç çok büyük ya da tanımsız." |
  | Kesişim boş (`A1:A3 C1:C3`) | "İki aralığın ortak hücresi yok." |
  | Bilinmeyen işlev | "'TOPLAM' adlı bir işlev yok." (Türkçe görünen adıyla) |
  | Argüman sayısı | "TOPLA en az 1 bağımsız değişken ister, 0 verildi." |
  | Tanımsız ad | "'Gelir' adı tanımlı değil." / döngüsel ad |
  | Silinmiş sayfa başvurusu | "Başvurulan sayfa silinmiş." |
  | İşlev içi hata (argümanlarda o hata yok) | (işlev, kod) tablosu: `VLOOKUP/#N/A` → "DÜŞEYARA aranan değeri (\"x\") bulamadı."; `SQRT/#NUM!` → "KAREKÖK negatif sayı aldı."; tablo dışı → kod başına genel cümle ("İşlev geçersiz bir sayısal sonuç üretti.") |
- İşlev tablosu ilk adımda **en sık 15–20 işlev** (DÜŞEYARA, YATAYARA, KAÇINCI, İNDİS, X-ARA, KAREKÖK,
  LOG, BÖLÜM, ORTALAMA (#BÖL/0!), TARİH, METNEÇEVİR, PARÇAAL, BUL, DOLAYLI, KAYDIR…); gerisi genel cümle.
  Türkçe işlev adları `adlar` modülünden okunur (ezbere yazılmaz, kural 4).
- Açıklama cümleleri **bizim metnimiz**, Excel'in Türkçe "hata denetimi" iletilerinin çevirisi değil
  (Microsoft'un Türkçe metni doğrulanmadığı için birebir taklit edilmez; `yardim.md` Excel'den Farklar'a yazılır).

### 3.2 Arayüz (`ui/grid.py`, `ui/window.py`)
- **İpucu:** not ipucunun yanında aynı zamanlayıcı düzeni: fare hatalı hücrede ~400 ms bekleyince
  `QToolTip` (notlu hücrede not kutusu öncelikli; ikisi birden varsa notun altına bir satır).
- **Durum çubuğu:** etkin hücre hatalıysa ve tek hücre seçiliyse sol tarafta açıklama (özet etiketiyle
  çakışmaz; çok hücreli seçimde gösterilmez). Hesap 300 ms'de bir değil, **seçim değişince bir kez**.
- Sonuç önbelleği: `(sayfa kimliği, r, c)` → metin; kitapta herhangi bir `hucre/sonuc/yapi/sayfa/ad`
  olayında tümü düşer (basit, doğru; tanı ucuz).
- Kural 1: metinlerde uygulama adı geçmez. Kural 13: `yardim.md` (Formüller → "Hata açıklamaları",
  Yenilikler, Excel'den Farklar).

## 4. Performans
- Hesap yolu: **değişmez** (ölçüt: `araclar/formul_olcum.py` öncesi/sonrası aynı ±%3).
- Tanı ölçütleri (100.000 dolu hücreli kitapta): tek hücrelik tanı < **5 ms**; `=TOPLA(A1:A100000)`
  ve hata A99999'da < **50 ms** (dolu hücre gezisi); 10.000 halkalı `=A1+1` zinciri < **100 ms**;
  `sinir` aşımı uyarıyla biter, donma yok.
- **Uygulama sonrası ölçüm (2026-10-11):** tek hücre 0,1 ms ✅; TOPLA(A1:A100000) **62 ms** (hata hücresi
  dizini sayfada bir geçiş; hedef 50 ms — kabul, ipucu önbellekte); halka başına ≈ 45 µs → sınır
  **2.000 halkaya** indirildi (≈ 52 ms ✅); sınırı aşan zincirde "son izlenen hücre" söylenir, kaynak iddia
  edilmez. Motor verilirse ağaçlar `Hesaplayici.agac` ile yeniden ayrıştırılmaz. Testler süre değil adım sayısı/sonuç sınar (kırılgan
  zamanlama testinden kaçınma kararı); süre `araclar/` ölçümünde.

## 5. Geri al / xlsx / kurtarma
Hiçbir kalıcı durum eklenmez: `Hata`, `_sonuc`, xlsx, pano, kurtarma **aynı**. Geri al sonrası yeni
sonuç olayı önbelleği düşürür. Mevcut test değişmesi beklenmez.

## 6. Test planı (`testler/test_hata_neden.py`, Qt'siz + birkaç arayüz testi)
1. Doğrudan nedenler: metin işlenen (hücre/sabit), bölen sıfır/boş, 0^0, bilinmeyen işlev, argüman
   sayısı, tanımsız ad, silinmiş sayfa, boş kesişim, elle yazılmış hata, çözümlenemeyen formül.
2. Zincir: C5 = B3+1, B3 = A1*2, A1 = "abc" → 3 halka, kaynak A1… (doğru sıra ve metin); başka sayfa
   halkası (metinde `Sayfa2!B3`); aralık öncülü (`=TOPLA(A1:A1000)`, hata A700'de).
3. Tembel işlev: `=EĞER(A1>0;1/0;2)` doğru dalda; yanlış daldaki hata kaynak gösterilmez.
4. İşlev tablosu: DÜŞEYARA #YOK, KAREKÖK #SAYI!, ORTALAMA boş aralık #BÖL/0! (her biri 4 vaka değil —
   bunlar işlev değil açıklama testi; kural 11 yeni işlev eklemediği için geçerli değil).
5. Sınırlar: döngü (sonsuz döngüye girmez), `sinir` aşımı, değişken işlev, hata olmayan hücre → None.
6. Arayüz: ipucu metni (QTest fare bekletme, koşul beklemeli), durum çubuğu tek/çok hücre, olayla
   önbelleğin düşmesi, notlu hücre önceliği.
7. Bekçi: `tabcel/formul/hata_neden.py` Qt içe aktarmaz (mevcut kural 2 testine eklenir).

## 7. Uygulama sırası (onaydan sonra)
1. `hata_neden.py` geri izleme + doğrudan nedenler + testler (1, 2, 5)
2. Tanı yürüyücüsü tembel/dizi kuralları + işlev tablosu (3, 4)
3. Arayüz ipucu + durum çubuğu (6), `yardim.md`, ölçüm (§4), `surec.md`

## 8. Açık sorular (kullanıcı)
- İpucu mu, durum çubuğu mu, ikisi mi? (öneri: ikisi)
- Excel'deki yeşil üçgen/“!” akıllı etiketi (Hata denetimi menüsü: "Hatayı İzle", "Bu hata hakkında
  yardım") istenir mi? Öneri: şimdilik **hayır** (T8 kapsamı açıklama; ok çizimi ayrı iş, Faz 7+).
