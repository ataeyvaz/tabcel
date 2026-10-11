# T10 — Excel'de değiştirilmiş grafiklerde sessiz kayıp: tasarım notu (Opus 5.5, 2026-10-11)

Kaynak: `surec.md` → "Faz 6 + T9 Opus gözden geçirmesi", önemli bulgu (2). Uygulayan: Sonnet 5.5. Bu not tek başına yeterli olacak biçimde yazıldı; kanıtlar 2026-10-11'de gerçek Excel'le (Office 16, COM, ayrı ve görünmez örnek, kullanıcının açık kitabına dokunulmadan) üretildi.

## 1. Sorun (doğrulandı)
`grafikler.xlsx`'e (Tabcel imli) Excel'de eğilim çizgisi, ikincil eksen, gradyan ve hata çubuğu eklenip dosya kaydedildi. Bugünkü `xlsx_io.ac` her birinde `uyarilar == []`, `veri_kaybi == False` döndürüyor; Tabcel kaydedince bu öğeler sessizce siliniyor.

## 2. Karar: im + grafik XML taraması birlikte (karma); özet (hash) kullanılmıyor
- **Özet (hash) tek başına işe yaramıyor (denendi):** Excel aç-kaydet sırasında her grafiğin XML'ini baştan yazıyor. `c:strCache/numCache`, `c:extLst/c16:uniqueId`, `c14:invertSolidFillFmt`, `c:roundedCorners`, `c:style`, `c:lang`, `c:printSettings`, `c:varyColors=1`, boş `c:dLbls` ekliyor; dağılım grafiğinde `xVal/numRef` yerine `strRef` yazıyor, dağılım serisine `c:smooth val=1` koyuyor. Bu yüzden Excel'den geçen her dosyada özet tutmaz ve zararsız bir aç-kaydet bile uyarı verir. Ayrıca özet yalnızca "değişti" der, *neyin* değiştiğini söyleyemez; veri aralığını değiştirmek gibi zararsız düzenlemelerde de uyarır.
- **Seçilen yol:** her grafik parçası (`xl/charts/chartN.xml`) imden bağımsız olarak doğrudan taranır. Tabcel'in modelleyemediği öğeler kapalı bir kural listesiyle bulunur (§3). Kurallar iki sınıftır:
  - **A (yapısal kayıp):** her dosyada uyarılır.
  - **B (biçim):** yalnızca im *varken* uyarılır. İm yoksa B'yi zaten bugünkü genel "uyarlandı" iletisi kapsıyor.
- **Neden XML, neden openpyxl nesnesi değil:** openpyxl `extLst` içindekileri (`c15` filtrelenmiş seri, hücreden gelen etiket aralığı) ve birleşik grafikte ilk grafik dışındaki grupları atıyor. Tespit, bağımlılığın gizli API'lerine (`ws._charts`) bağlı kalmasın.
- **İmin yeni rolü:** "bu dosyayı en son Tabcel yazdı, biçim Tabcel'in varsayılanı" sinyali. Kalır; artık tek güvence değildir, yalnızca B sınıfının ve genel iletinin anahtarıdır.

## 3. Kapalı kural listesi
Önekler: `c:` = `…/drawingml/2006/chart`, `a:` = `…/drawingml/2006/main`, `c15:` = `…/office/drawing/2012/chart`. Openpyxl önek koymuyor, Excel `c:` koyuyor; ad alanı URI'siyle eşleştirin (ET `{uri}ad`).

Ön koşullar:
- `plotArea` içindeki grup öğeleri (`barChart|lineChart|pieChart|doughnutChart|areaChart|scatterChart`) okunur.
- Gruplardan biri desteklenmeyen türse (`*3DChart`, `radarChart`, `bubbleChart`, `stockChart`, `surface*`, `ofPieChart`) ya da XML ayrıştırılamıyorsa kural atlanır. Bunlar zaten "N grafik desteklenmiyor" diye uyarılıyor, çift uyarı olmasın.
- "Eksen sayısı" = `plotArea` altındaki `valAx|catAx|dateAx|serAx` sayısı.

| # | Kural (koşul) | Etiket (uyarıda) | Tabcel'de karşılığı | Sahte uyarıya karşı not |
|---|---|---|---|---|
| A1 | `.//c:ser/c:trendline` | eğilim çizgisi | yok | Excel/Tabcel varsayılanında yok |
| A2 | `.//c:ser/c:errBars` | hata çubukları | yok | — |
| A3 | eksen sayısı > 2 | ikincil eksen | yok | Excel `AxisGroup=2` → 2. `barChart` + `catAx(delete=1)` + `valAx(axPos=r, crosses=max)` |
| A4 | > 1 grup (farklı tür ya da A3 olmadan aynı tür) | birleşik grafik | yalnızca ilk grup okunur | A3 ile birlikte de çıkabilir |
| A5 | `chartSpace` altında herhangi bir `a:gradFill`, `a:pattFill` ya da `a:blipFill` | gradyan/desen/resim dolgusu | yalnızca düz renk | aç-kaydette yok; Excel'de grafik stili (ChartStyle) de gradyan ekler, o da kayıp |
| A6 | eksende `c:scaling/c:logBase` ya da `c:orientation val=maxMin` ya da `c:majorUnit/minorUnit/dispUnits` | eksen ölçeği (logaritmik, ters, birim) | yalnızca en küçük/en büyük | — |
| A7 | eksen sayısı ≤ 2 ve bir eksende `c:delete val=1` (pasta/halka dışında) | gizlenmiş eksen | Tabcel her zaman `delete=0` yazar | yalnızca ≤ 2 eksende (A3'teki gizli 2. eksen sayılmaz) |
| A8 | pasta/halka dışında `c:ser/c:dPt`; pasta/halkada dPt dolgusu ne `srgbClr == palet_rengi(idx)` ne de alt öğesiz `schemeClr val=accent{idx%6+1}` ise, ya da `c:explosion > 0` | tek tek biçimlendirilmiş veri noktası / ayrık dilim | yok (Tabcel dilim renklerini paletten yazar) | Excel'in sıfırdan pastası `schemeClr accentN` yazar: o B4'tür, A8 değil (denendi) |
| A9 | grup ya da seri `c:dLbls` içinde `showCatName`, `showSerName` ya da `showLegendKey` `=1`; tek etiket `c:dLbl`; `c15:datalabelsRange`; pastada `showVal=1`; ya da grup düzeyinde etiket yokken etiketin yalnızca bazı serilerde olması | veri etiketi ayrıntıları | yalnızca değer (pastada %) | **`showBubbleSize` kullanmayın:** Excel aç-kaydette `showBubbleSize val=1` yazıyor (denendi, sahte uyarı verir). Excel grup `dLbls`'ini her seriye de kopyalıyor; bu tutarlı, uyarı değil |
| A10 | `lineChart` serisinde `c:smooth val=1` | düzgünleştirilmiş çizgi | yok | **yalnızca çizgi grafiği:** Excel dağılım serisine `smooth=1` ekliyor (denendi) |
| A11 | `lineChart` serisinde `c:marker/c:symbol val≠none`, ya da seride `marker` yokken grupta `c:marker val=1` | çizgi işaretçileri | Tabcel `symbol=none` yazar | — |
| A12 | `scatterChart` serisinde `spPr/a:ln/a:noFill` yok | dağılım grafiğinde çizgi | yalnızca işaretçi | Tabcel `ln/noFill` yazar, Excel korur |
| A13 | `c:chart/c:dispBlanksAs val≠gap` | boş hücre gösterimi | yalnızca boşluk | Tabcel ve Excel varsayılanı `gap` |
| A14 | `c:chart/c:plotVisOnly val=0` | gizli hücre verisi | gizli satırlar çizilmez | — |
| A15 | grupta `c:upDownBars`, `dropLines`, `hiLowLines` ya da `serLines` | yardımcı çizgiler | yok | — |
| A16 | `plotArea/c:dTable` | veri tablosu | yok | — |
| A17 | XML'de `filtered…Series` (c15 `extLst`) | filtrelenmiş (gizli) seri | yok; openpyxl atıyor | **COM ile denenmedi (belirsiz)** |
| B1 | `.//c:txPr` ya da `a:defRPr`/`a:rPr` üzerinde `sz` veya `b="1"` | yazı biçimi | yok | aç-kaydet `a:rPr lang` ekliyor ama `sz` eklemiyor (denendi) |
| B2 | `chartSpace`, `plotArea`, `title` ya da `legend` doğrudan altında `c:spPr` | alan/çerçeve biçimi | yok | aç-kaydette yok |
| B3 | `mc:AlternateContent` (c14:style) | grafik stili | yok | — |
| B4 | seri dolgusunda (`spPr`, `spPr/a:ln` ya da `marker/spPr` altında `a:solidFill`) `srgbClr` yok ya da renk alt öğeli (`lumMod`…) | tema rengi | renk paletten alınır | Excel'de tema paletinden renk seçmek `schemeClr` yazar |
| B5 | `barChart`'ta `gapWidth≠150` ya da `overlap∉{0,100}` | çubuk aralığı | sabit | Tabcel 150 ve yığılıda 100 yazar |

Kapsam dışı (uyarılmaz, Kararlar'a "bilinçli" diye yazılacak): eksen sayı biçimi (`numFmt sourceLinked=0`), onay çizgisi ve etiket konumu, ikincil kılavuz çizgileri, `firstSliceAng`, `holeSize`, `dLblPos`, gösterge öğesi silme, `dateAx` (tarih ekseni zaten §11'de bilinçli fark).

## 4. Davranış ve uyarı metni
- **Tespit birimi** grafiktir ve grafiğe ad verilir:
  - Grafik başlığı varsa (`c:title//a:t`) `'Aylık satış' grafiği`.
  - Yoksa `{n}. grafik` (n: o sayfanın çizim XML'indeki `c:chart r:id` sırası).
  - Sayfa adı ilişki zincirinden bulunur: `workbook.xml` → `_rels` → `sheetN.xml.rels` → `drawingN.xml(.rels)`.
- **Satır (A, ve im varsa B):** `"'Aylık satış' grafiğinde (Sayfa1) {APP_NAME}'in desteklemediği öğeler var: eğilim çizgisi, ikincil eksen; Excel biçimi: yazı biçimi. Kaydederseniz bunlar kaybolur."`
  - Yalnızca B varsa: `"'…' grafiğinin (Sayfa1) Excel'de değiştirilen biçimi (yazı biçimi, tema rengi) kaydedince {APP_NAME} varsayılanına döner."`
  - Her satır `rapor.ekle(…, True)` ile eklenir; A ve B ikisi de `veri_kaybi=True` yapar, kayıtta üç seçenekli onay çıkar.
- **Bilgi çubuğu taşmasın:** en çok 3 grafik satırı yazılır. Fazlası için: `"…ve {k} grafikte daha desteklenmeyen öğe var; kaydederseniz kaybolur."`
- **İm yoksa:** bugünkü genel "uyarlandı" iletisi aynen kalır (metin değişmez). Altına yalnızca A satırları eklenir; B gösterilmez (genel ileti onu kapsıyor).
- **İm varsa:** A ve B satırları gösterilir. Hiçbiri yoksa uyarı yok (bugünkü gibi).
- Tabcel kaydedince öğeler dosyadan çıkar; yeniden açınca uyarı gelmez (test edilir).
- Kurtarma (`kurtarma.py`) `veri_kaybi`'ni taşıdığı için değişiklik gerekmez.

## 5. Uygulama adımları (Sonnet; tahmini ~150 satır kod + ~150 satır test)
1. **`tabcel/io/xlsx_grafik.py`** (Qt yok, saf ve test edilebilir):
   - `grafik_ozellikleri(xml: bytes) -> Tuple[List[str], List[str]]` (A ve B etiketleri; sıra §3 tablosu, yinelenmesiz). Kurallar tek bir tablo/işlev listesinde dursun; `ET.ParseError` → `([], [])`.
   - `grafik_basligi(xml) -> Optional[str]`.
   - `grafik_parcalari(z: ZipFile) -> List[Tuple[sayfa_adi, sira, parca_yolu]]`: ilişki zinciri, hedef yollar `posixpath.normpath` ile; grafik sayfası (`xl/chartsheets`) ve erişilemeyen parçalar atlanır.
   - Ad alanı sabitleri modül başında.
2. **`tabcel/io/xlsx_io.py`:**
   - `_nesne_sayilari` aynı zip açılışında bir de `ozellikler: List[(sayfa, ad, A, B)]` döndürsün (dördüncü öğe; çağıran yalnızca `_nesne_uyarilari`).
   - `_nesne_uyarilari` §4'teki satırları kursun. İmsiz dosyada B'yi atlasın.
   - Genel iletideki örnek listesi ("3B, eğilim çizgisi…") aynı kalsın.
3. **Performans:** yalnızca `xl/charts/chart\d+.xml` okunur, grafik yoksa maliyet sıfır.
   - Ölçüt: 100.000 noktalı, Excel'in önbellekle kaydettiği bir grafikte tarama ≤ 200 ms.
   - Aşılırsa `ET.iterparse` ile `c:numCache/strCache` atlanarak taranır. `araclar/`'da ölçün, `surec.md`'ye yazın.
4. **Örnek dosyalar:** yeni `araclar/ornek_uret_excel.ps1` (COM; `excel_dogrula.ps1` düzeni: yeni örnek, `DisplayAlerts=false`, `finally Quit`, öncesi/sonrası PID denetimi) iki dosya üretip `testler/ornekler/`'e koyar (her biri ~32 KB):
   - `excel_gecis.xlsx`: `grafikler.xlsx`'in değer etiketli, eksen başlıklı, sınırlı, göstergesiz ve başlıksız varyantının Excel aç-kaydeti.
   - `excel_ozellikli.xlsx`: her grafikte bir özellik. Kullanılan COM çağrıları:
     - `SeriesCollection(1).Trendlines().Add()`
     - `SeriesCollection(2).AxisGroup=2`
     - `SeriesCollection(2).ChartType=4` (birleşik)
     - `Format.Fill.TwoColorGradient(1,1)` ve `Patterned(5)`
     - `ErrorBar(1,1,1,1)`
     - `Points(2).Format.Fill.ForeColor.RGB=255`
     - `DataLabels().ShowCategoryName=$true`
     - `Axes(2).ScaleType=-4133`
     - `DisplayBlanksAs=2`
     - `Smooth=$true` ve `MarkerStyle=3` (çizgi grafiği)
     - `ChartTitle…Font.Size=20`
     - `ChartGroups(1).GapWidth=50`
     - `FullSeriesCollection(2).IsFiltered=$true` (A17 doğrulaması)
5. `tabcel/yardim.md` (Kural 13: Grafikler ve Resimler, Excel'den Farklar, Yenilikler) ve `surec.md` (Kararlar: §2 kararı, §3 kapsam dışı listesi, B'nin imsiz dosyada gizlenmesi).

## 6. Test ölçütleri (`testler/test_xlsx_grafik_kayip.py` + örnekler)
- **(a)** Tabcel yazdı (`grafikler.xlsx` ve tüm alanlar dolu bir varyant) → uyarı yok, `veri_kaybi` yok.
- **(b)** Excel aç-kaydet → uyarı yok. **Denendi:**
  - `grafikler.xlsx` (13 grafik ve resim), değer etiketli, eksen başlıklı ve sınırlı varyantı ile iki kez aç-kaydet: prototip temiz çıktı.
  - Tabcel modeli aç-kaydetten önce ve sonra eşit (14 nesne).
  - Bu testte `showBubbleSize` ve dağılımdaki `smooth` sahte uyarıları yakalanıp kurallardan çıkarıldı.
- **(c)** Excel ile özellik eklenmiş dosya (tümü denendi, prototip doğru buldu): bu dosyalar bugün uyarısız açılıyor.

  | Excel işlemi | Beklenen etiket |
  |---|---|
  | eğilim çizgisi | A1 |
  | `AxisGroup=2` | A3 (A7 çıkmamalı) |
  | birleşik | A4 |
  | gradyan, desen | A5 |
  | hata çubuğu | A2 |
  | tek nokta rengi | A8 |
  | kategori adı etiketi | A9 |
  | logaritmik eksen | A6 |
  | boş hücreler sıfır | A13 |
  | yumuşak çizgi | A10 |
  | üçgen işaretçi | A11 |
  | başlık 20 pt | B1 |
  | boşluk 50 | B5 |
  | ChartStyle 205 | A5 + A7 + B1–B5 |

  Her biri için `veri_kaybi=True` ve metinde grafik adı ile sayfa adı bulunmalı.
- **(d)** openpyxl `Series.trendline=Trendline()` → imsiz dosyada genel ileti + "eğilim çizgisi" satırı (denendi: A1 bulundu). Eğilim çizgisi olmayan openpyxl dosyası → yalnızca genel ileti (denendi).
- **(e)** Excel'de sıfırdan çizilmiş sütun, çizgi ve pasta (imsiz) → yalnızca genel ileti. Denendi: pastadaki `schemeClr accentN` kuralı uygulanınca A çıkmıyor. Aynı grafikler imli bir dosyada olsaydı B satırları çıkardı (beklenen).
- **Birim testleri:** her kural için küçük XML parçası (hem önekli hem öneksiz).
  - `<c/>` ve bozuk XML → boş sonuç.
  - Desteklenmeyen tür → boş sonuç.
  - 3'ten fazla grafikte "ve k grafikte daha" satırı.
  - Kaydet → aç sonrası uyarı yok.
- **Mevcut testler (Kural 12):** prototipe göre **hiçbirinin değişmemesi beklenir**:
  - `test_excel_dosyasi_yuklenir_im_yok_uyarisi` (`len(uyarilar)==1`): openpyxl sütun grafiği temiz.
  - `test_grafikli_uyarilar…`: `grafikli.xlsx` temiz.
  - `test_ornek_grafikler_xlsx_uyarisiz…`: temiz.
  - `test_desteklenmeyen_turler…`, `test_im_var_ama_okunamayan…` (`<c/>`): atlanır.

  Yine de `test_xlsx_grafik`, `test_xlsx_ornekler`, `test_xlsx_io`, `test_opus_faz4`, `test_dosya_menusu` ve `test_kurtarma` koşulmalı. Biri değişirse önce kullanıcıya bildirilmeli.

## 7. Açık, belirsiz ve kapsam dışı
- **Belirsiz:**
  - A17 (`filtered…Series` öğe adları) COM ile denenmedi.
  - `chartEx` grafikleri (şelale, huni, ağaç haritası; `xl/charts/chartEx*.xml`) `_nesne_sayilari`'nda sayılmıyor. Çizimdeki `mc:Fallback` şekli yüzünden `tara`'nın "şekil" uyarısı muhtemelen yakalıyor, ama denenmedi. Öneri: `chartEx` parçalarını "desteklenmiyor" diye saymak (küçük ek adım; kullanıcı onayıyla).
- **Kullanıcı kararı:**
  - B sınıfı (biçim) im varken uyarı ve kayıt onayı veriyor. İstenirse B yalnızca bilgi olarak gösterilir (`veri_kaybi=False`). Varsayılan öneri: onay versin ("sessiz olmaz" ilkesi).
  - Excel'de imli dosyaya eklenen yeni grafik B4/B1 verir. Bu doğru ama ilk kez görülünce gürültülü gelebilir.
- **Kapsam dışı:**
  - B öğelerini *korumak*: tema rengini (`schemeClr accentN` → palet) okumak sonraki bir iyileştirme; yapılırsa B4'ün büyük kısmı kalkar.
  - §3'teki "uyarılmaz" listesi.
  - Grafik sayfası.
  - Grafik dışı çizimler (`tara` zaten uyarıyor).
