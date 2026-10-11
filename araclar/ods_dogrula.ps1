# Tabcel'in yazdığı .ods dosyasını gerçek Excel'de (COM, görünmez) açıp özetler: sayfalar, biçim, formül, birleşim, genişlik, gizleme.
# Kullanım: powershell -File araclar\ods_dogrula.ps1 <dosya.ods>   (örnek üretmek için: testler	est_ods.py::_kitap ile kaydet)
param([string]$F)
$xl = New-Object -ComObject Excel.Application; $xl.Visible=$false; $xl.DisplayAlerts=$false
try {
  $wb = $xl.Workbooks.Open($F); $ws = $wb.Worksheets.Item(1)
  "sayfalar: " + (($wb.Worksheets | ForEach-Object { $_.Name }) -join " | ")
  $b = $ws.Range("B1"); "B1 text=[{0}] fmt=[{1}] bold={2} italic={3} strike={4} color={5} fill={6} wrap={7} halign={8} font={9} size={10}" -f $b.Text,$b.NumberFormat,$b.Font.Bold,$b.Font.Italic,$b.Font.Strikethrough,$b.Font.Color,$b.Interior.Color,$b.WrapText,$b.HorizontalAlignment,$b.Font.Name,$b.Font.Size
  "B2 formula=[{0}] text=[{1}]" -f $ws.Range("B2").Formula,$ws.Range("B2").Text
  "C2 formula=[{0}] text=[{1}]" -f $ws.Range("C2").Formula,$ws.Range("C2").Text
  "D2 formula=[{0}] text=[{1}]" -f $ws.Range("D2").Formula,$ws.Range("D2").Text
  "merge A4: " + $ws.Range("A4").MergeArea.Address()
  "col B width=" + $ws.Columns.Item(2).ColumnWidth + " C hidden=" + $ws.Columns.Item(3).Hidden + " row3 h=" + $ws.Rows.Item(3).RowHeight + " row6 hidden=" + $ws.Rows.Item(6).Hidden
  "E20=" + $ws.Range("E20").Text + " D1=" + $ws.Range("D1").Text + " C1=" + $ws.Range("C1").Text
  $wb.Close($false)
} finally { $xl.Quit() }
