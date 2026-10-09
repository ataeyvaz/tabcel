# Faz 2 — Formül motoru tasarım notu (Opus 5.5, 2026-10-09)

Kapsam `plan.md` → Faz 2. Bu not çekirdeğin **nasıl** kurulduğunu ve Sonnet'e devredilecek işlerin sözleşmesini anlatır.

## 1. Katmanlar (`tabcel/formul/`, Qt yok)
| Dosya | Görev |
|---|---|
| `yerel.py` | `Yerel`: ayırıcılar (argüman, ondalık, dizi sütun/satır), hata adları, mantıksal adlar. `EN` (kanonik/.xlsx) ve `TR` |
| `sozcuk.py` | Sözcükleyici: metin → `Sozcuk` listesi. Boşluklar da sözcüktür → metin **birebir** geri kurulur (çeviri ve başvuru kaydırma kullanıcının yazımını bozmaz) |
| `agac.py` | Ayrıştırıcı: sözcükler → sözdizim ağacı (öncelik tırmanma) |
| `donustur.py` | Excel tür dönüşümleri (sayıya, metne, mantığa, karşılaştırma) |
| `degerlendir.py` | Ağacı değerlendirir (`Baglam`: kitap, sayfa, hücre, motor kancası) |
| `fonksiyonlar/` | Fonksiyon kaydı (`@fonksiyon`) + gruplar (matematik, istatistik, mantık, metin, tarih, arama, bilgi, finans) |
| `adlar.py` | İngilizce ⇄ Türkçe fonksiyon adları (yalnız Microsoft tr-tr belgesiyle **doğrulanmış** olanlar) |
| `ceviri.py` | Kullanıcı metni (TR) ⇄ saklanan biçim; .xlsx (EN, sayfa adlı) ⇄ saklanan biçim |
| `kaydir.py` | Başvuru kaydırma: kopyala, satır/sütun ekle-sil, taşı (kes-yapıştır) |
| `motor.py` | `Hesaplayici`: bağımlılık grafiği, kirli işaretleme, sıralı yeniden hesaplama, döngü tespiti |

## 2. Saklanan biçim (`Hucre.formul`)
- Kanonik İngilizce (`=SUM(A1:A3,2.5)`), .xlsx'teki gibi; **tek fark: başka sayfa başvurusu adla değil kimlikle**: `=[3]!A1+1` (K6 kararı). `[` sayfa adlarında yasak olduğundan gerçek bir adla çakışmaz.
  - Yeniden adlandırma formüllere dokunmaz (ekranda yeni ad görünür); silinen sayfaya giden başvuru `#REF!` hesaplanır ve `#BAŞV!` görünür; silme geri alınınca aynı kimlik geri gelir → formüller kendiliğinden düzelir.
  - Pano/.xlsx'e çıkarken kimlik → ad (`ceviri.disa`); kendi panomuz aynı kitapta olduğumuz için kimlikle taşır.
- Var olmayan sayfaya başvuru yazılırsa `FormulHatasi` ("Başvurulan sayfa bulunamadı") — Excel dosya iletişim kutusu açar; biz girişi reddedip düzenlemeyi açık bırakırız.
- Fonksiyon adı ve başvurular büyük harfe çevrilir (`=topla(a1)` → `=SUM(A1)`); boşluklar ve sayı yazımı korunur (`1,50` → `1.50`).

## 3. Değerlendirme kuralları
- Öncelik (yüksekten alçağa, Excel): `:` aralık → boşluk (kesişim) → tekli `-`/`+` → `%` → `^` (soldan) → `* /` → `+ -` → `&` → karşılaştırmalar. `=-2^2` = 4.
- **Dizi semantiği Excel 365 gibi** (referansımız Excel web): işleçler aralık/dizi üzerinde öğe öğe çalışır (`=TOPLA(A1:A3*B1:B3)` çalışır). **Taşma (spill) yok (Faz 8):** hücrenin sonucu çok hücreli olursa → aralıksa örtük kesişim (formül hücresinin satırı/sütunu), diziyse sol üst öğe. *Excel 365 bunu taşırır — bilerek fark, Kararlar'a yazıldı.*
- Tür dönüşümü: boş → 0 / "" ; DOĞRU → 1 ; sayı gibi metin → sayı (Türkçe yazım, `%` dahil; tarih metni Faz 3) ; dönüşmeyen metin → `#DEĞER!`. Karşılaştırma: sayı < metin < mantıksal; metin büyük/küçük harf duyarsız (Türkçe kurala göre).
- Sayının metne dönüşümü (`&`): en çok 15 anlamlı basamak, ondalık virgül. Bilimsel gösterime geçiş eşiği belirsiz (§8b).
- Kayan nokta: toplama/çıkarmada sonuç işlenenlere göre ~1e-15 göreli küçüklükteyse 0 (Excel'in "yakın sıfır" düzeltmesi); kesin eşik belirsiz (§8b-7).
- Hata yayılımı soldan sağa ilk hata.

## 4. Bağımlılık grafiği ve yeniden hesaplama (`motor.py`)
- Her formül hücresi için ayrıştırılmış ağaç (metin → ağaç önbelleği) ve **durağan öncüller**: tek hücreler (sözlük: hücre → bağımlılar) ve aralıklar (sayfa başına liste).
- Kitap olaylarını dinler: `hucre` → değişen hücreleri yeniden kaydet + kirli işaretle + hesapla; `yapi` ve `sayfa` (ekle/sil) → grafiği baştan kur + tümünü hesapla (basit ve doğru; ölçümde yavaşsa daraltılır); `sayfa`/`ad` → yalnız değişkenler.
- Kirli küme: değişen hücrelerden BFS (hücre + aralık bağımlıları) + değişken fonksiyonlu hücreler (BUGÜN, ŞİMDİ, S_SAYI_ÜRET, DOLAYLI, KAYDIR).
- Sıra: kirli alt grafikte Kahn topolojik sırası; kalan düğümler **döngü** → sonuç 0, `motor.donguler` doldurulur, arayüz uyarır (Excel gibi).
- Dinamik başvuru (DOLAYLI/KAYDIR): değerlendirme sırasında henüz hesaplanmamış kirli hücreye rastlanırsa o hücre önce hesaplanır (özyineleme koruması: aynı anda hesaplanan hücre → döngü).
- Sonuçlar sayfa başına toplu yazılır (`Sayfa.sonuclari_yaz` → tek `sonuc` olayı).
- Bilinen optimizasyon noktası: aralık bağımlılıkları doğrusal taranıyor; 50.000 formül ölçümünde gerekirse sütun kovalı dizine geçilir.

## 5. Başvuru kaydırma (`kaydir.py`, sözcük düzeyinde — boşluk korunur)
- **Kopyala/doldur:** göreli kısımlar (dr, dc) kadar kayar, `$`'lılar sabit; sayfa dışına çıkan başvuru `#REF!`.
- **Satır/sütun ekle** (n'den itibaren +d): ilgili sayfadaki her uç ≥ n ise +d (mutlak/göreli fark etmez); aralığın içine ekleme aralığı büyütür. Tam sütun başvurusu satır eklemeden etkilenmez (tersi de).
- **Satır/sütun sil** [n, n+d−1]: tek hücre silinen bölgedeyse `#REF!`; aralık uçları daralır, tamamı silindiyse `#REF!`.
- Komutlar (`SatirEkleSil`/`SutunEkleSil`) kaydırmadan **sonra** tüm kitaptaki formül metinlerini yeniden yazar ve eskilerini saklar; geri alırken önce metinler geri yüklenir, sonra kaydırma geri alınır → tek geri al adımı.
- **Taşı (kes-yapıştır, `HucreTasi`):** taşınan bölgenin TAMAMEN içinde kalan başvurular yeni yere kayar (kısmen içerdeki aralık değişmez); taşınan formülün kendi göreli başvuruları kaymaz; sayfalar arası taşımada nitelendirme eklenir/kaldırılır.

## 6. K7 — İşaretleme modu (formül yazarken fareyle/klavyeyle başvuru seçme)
Durum makinesi (ızgara + düzenleyici + formül çubuğu ortak kullanır):
- **Hazır** → yazmaya/F2'ye basınca **Gir**/**Düzenle**.
- Gir/Düzenle iken metin `=` ile başlıyorsa ve imleç **başvuru eklenebilir bir konumdaysa** (imleçten önceki anlamlı karakter `=`, `(`, `;`, bir işleç ya da `:`; ya da az önce eklenmiş başvurunun hemen sonu) → **İşaret** alt modu etkin.
- İşaret modunda:
  - Hücreye tıklama/sürükleme **onaylamaz**: düzenleyicideki "işaret başvurusu" (son eklenen parça) seçilen hücre/aralıkla değiştirilir; düzenleyici odağı korur.
  - Gir modundaysa oklar işaret hücresini gezdirir (Shift+ok aralık genişletir); Düzenle modunda oklar imleçtir (Excel gibi, F2 ikisi arasında geçiş).
  - Başka sayfa sekmesine tıklamak düzenlemeyi kapatmaz; eklenen başvuru `Sayfa2!A1` olur; Enter formülü **ilk** hücreye yazar ve o sayfaya döner.
  - Herhangi bir karakter yazılınca işaret parçası "donar" (sonraki tıklama yeni parça ekler).
- İşaret modu dışında (metin formül değil ya da imleç başvuru konumunda değil): tıklama Faz 1'deki gibi **onaylar**.
- **Odak kaybı:** pencere dışına geçiş (Alt+Tab, başka uygulama) düzenlemeyi **onaylamaz, açık bırakır** (Excel gibi); yalnız uygulama içinde başka bir denetime (ad kutusu, menü) geçiş onaylar. `focusOutEvent` → `olay.reason()` `ActiveWindowFocusReason`/`PopupFocusReason` ise onaylamaz.
- Renkli başvuru vurgusu: düzenlenen formüldeki her başvuru sırayla bir renk alır (Excel paleti), ızgarada o renkte çerçeve; düzenleyicide aynı renkte metin. Kaynak: `sozcuk.sozcukle` (başvuru sözcüklerinin metin konumları).
- F4: imleçteki başvuruda `A1 → $A$1 → A$1 → $A1 → A1` döngüsü.
- Uygulama Sonnet'e: `ui/grid.py` (`_Duzenleyici` + `mousePressEvent`), `ui/window.py` (formül çubuğu aynı modu paylaşır). Ölçüt: yukarıdaki her madde için ekransız test.

## 7. Sonnet'e devredilecekler (sözleşme)
1. `fonksiyonlar/` içinde ~80 fonksiyon: `@fonksiyon("SUM", en_az=1, en_cok=255)` kalıbı, `donustur` yardımcıları; her biri 4 vakalık test (kural 11).
2. `adlar.py`: Microsoft tr-tr işlev sayfalarından doğrulanmış Türkçe adlar; doğrulanamayan → `surec.md` §8b.
3. K7 işaretleme modu, renkli başvuru vurgusu, F4, otomatik tamamlama + ipucu, Otomatik Toplam (Alt+=).
4. Pano: formül kopyalanınca `kaydir.kopyala`; kes-yapıştır → `HucreTasi` komutu (`kaydir.tasi`).
5. Ölçüm: 50.000 formüllük zincirde yeniden hesaplama süresi (`araclar/performans_olcum.py`).
