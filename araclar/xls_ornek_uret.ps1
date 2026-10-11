# testler\ornekler\ornek.xls dosyasını gerçek Excel'de (COM) üretir: değer/tarih/mantıksal/hata/birleşim/biçim/not/dondurma.
# Kullanım: powershell -File araclar\xls_ornek_uret.ps1 <çıktı.xls>
param([string]$Cikti)
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Add()
    $ws = $wb.Worksheets.Item(1); $ws.Name = "Satış"
    $ws.Range("A1").Value2 = "Ürün"; $ws.Range("B1").Value2 = "Adet"; $ws.Range("C1").Value2 = "Fiyat"; $ws.Range("D1").Value2 = "Tarih"
    $ws.Range("A1:D1").Font.Bold = $true; $ws.Range("A1:D1").Interior.Color = 0x50AF4F   # BGR yeşil
    $ws.Range("A2").Value2 = "Çay"; $ws.Range("B2").Value2 = 3; $ws.Range("C2").Value2 = 12.5
    $ws.Range("A3").Value2 = "$([char]0x015E)eker"; $ws.Range("B3").Value2 = 10; $ws.Range("C3").Value2 = 8.25
    $ws.Range("C2:C3").NumberFormatLocal = "0,00"
    $ws.Range("D2").Formula = "=DATE(2026,10,12)"; $ws.Range("D2").Value2 = $ws.Range("D2").Value2; $ws.Range("D2").NumberFormatLocal = "gg.aa.yyyy"
    $ws.Range("A4").Value2 = $true
    $ws.Range("B4").Formula = "=1/0"
    $ws.Range("C4").Formula = "=B2*C2"
    $ws.Range("A6:C6").Merge(); $ws.Range("A6").Value2 = "Birleşik başlık"; $ws.Range("A6").HorizontalAlignment = -4108
    $ws.Columns.Item(1).ColumnWidth = 20
    $ws.Range("A2").AddComment("Not metni") | Out-Null
    $ws.Range("A1:D1").Borders.LineStyle = 1
    $ws.Activate(); $xl.ActiveWindow.SplitRow = 1; $xl.ActiveWindow.SplitColumn = 0; $xl.ActiveWindow.FreezePanes = $true
    $ws2 = $wb.Worksheets.Add([Type]::Missing, $wb.Worksheets.Item(1)); $ws2.Name = "İkinci"
    $ws2.Range("A1").Value2 = "metin"; $ws2.Range("A1").Font.Italic = $true; $ws2.Range("A1").Font.Color = 0x0000FF
    $ws2.Range("A2").Value2 = 0.15; $ws2.Range("A2").Style = "Percent"
    $ws.Range("C5").Formula = "=SUM(B2:B3)+'İkinci'!A2*0"
    $ws.Range("D5").Formula = '=IF(B2>1,"çok","az")'
    $bicim = 56; if ($Cikti.ToLower().EndsWith('.ods')) { $bicim = 60 }   # 56 xlExcel8 (.xls), 60 OpenDocument (.ods)
    $wb.SaveAs($Cikti, $bicim)
    $wb.Close($false)
} finally { $xl.Quit() }
