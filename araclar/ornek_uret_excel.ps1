<#
 T10 (t10_xlsx_kayip_tasarim.md): GERÇEK Excel'de (COM) `testler\ornekler\grafikler.xlsx`ten özellikli/aç-kaydet örnekleri üretir:
 `testler\ornekler\excel\*.xlsx` (gecis = aç-kaydet; trend/hata/eksen2/birlesik/gradyan/desen/nokta/etiket/log/bos/yumusak/isaret/
 baslikyazi/bosluk/stil = tek özellik eklenmiş; excel_yeni = Excel'de sıfırdan, Tabcel imi YOK). Testler (`test_xlsx_kayip.py`)
 bu dosyaları okur; Excel gerekmez. Yeni Excel örneği açar (kullanıcının açık kitaplarına dokunmaz), DisplayAlerts kapalı, sonunda Quit.
 Kullanım:  powershell -File araclar\ornek_uret_excel.ps1
#>
param([string]$Kok = (Join-Path (Split-Path -Parent $PSScriptRoot) "testler\ornekler\excel"),
      [string]$Kaynak = (Join-Path (Split-Path -Parent $PSScriptRoot) "testler\ornekler\grafikler.xlsx"))
New-Item -ItemType Directory -Force $Kok | Out-Null
$once = @(Get-Process EXCEL -ErrorAction SilentlyContinue | ForEach-Object Id)
$xl = New-Object -ComObject Excel.Application
$sonra = @(Get-Process EXCEL -ErrorAction SilentlyContinue | ForEach-Object Id)
$yeni = $sonra | Where-Object { $once -notcontains $_ }
"onceki PID: $once  yeni PID: $yeni"
if (-not $yeni) { "Yeni Excel örneği oluşmadı; durdu."; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl); exit 1 }
$xl.Visible = $false; $xl.DisplayAlerts = $false
$kaynak = $Kaynak
function Uygula($ad, [scriptblock]$is) {
  try {
    $wb = $xl.Workbooks.Open($kaynak)
    $ws = $wb.Worksheets.Item(1)
    & $is $ws
    $wb.SaveAs((Join-Path $Kok "$ad.xlsx"), 51)
    $wb.Close($false)
    "ok $ad"
  } catch { "HATA $ad : $($_.Exception.Message)"; try { $wb.Close($false) } catch {} }
}
try {
  Uygula "gecis" { param($ws) }
  Uygula "trend" { param($ws) [void]$ws.ChartObjects(1).Chart.SeriesCollection(1).Trendlines().Add() }
  Uygula "eksen2" { param($ws) $ws.ChartObjects(1).Chart.SeriesCollection(2).AxisGroup = 2 }
  Uygula "birlesik" { param($ws) $ws.ChartObjects(1).Chart.SeriesCollection(2).ChartType = 4 }
  Uygula "gradyan" { param($ws) $ws.ChartObjects(1).Chart.SeriesCollection(1).Format.Fill.TwoColorGradient(1, 1) }
  Uygula "desen" { param($ws) $ws.ChartObjects(1).Chart.SeriesCollection(1).Format.Fill.Patterned(5) }
  Uygula "hata" { param($ws) [void]$ws.ChartObjects(1).Chart.SeriesCollection(1).ErrorBar(1, 1, 1, 1) }
  Uygula "nokta" { param($ws) $ws.ChartObjects(1).Chart.SeriesCollection(1).Points(2).Format.Fill.ForeColor.RGB = 255 }
  Uygula "etiket" { param($ws) $s = $ws.ChartObjects(1).Chart.SeriesCollection(1); $s.HasDataLabels = $true; $s.DataLabels().ShowCategoryName = $true }
  Uygula "log" { param($ws) $ws.ChartObjects(1).Chart.Axes(2).ScaleType = -4133 }
  Uygula "bosluk" { param($ws) $ws.ChartObjects(1).Chart.ChartGroups(1).GapWidth = 50 }
  Uygula "bos" { param($ws) $ws.ChartObjects(1).Chart.DisplayBlanksAs = 2 }
  Uygula "stil" { param($ws) $ws.ChartObjects(1).Chart.ChartStyle = 205 }
  Uygula "yumusak" { param($ws) $ws.ChartObjects(7).Chart.SeriesCollection(1).Smooth = $true }
  Uygula "isaret" { param($ws) $ws.ChartObjects(7).Chart.SeriesCollection(1).MarkerStyle = 3 }
  Uygula "baslikyazi" { param($ws) $ws.ChartObjects(1).Chart.ChartTitle.Format.TextFrame2.TextRange.Font.Size = 20 }
  # Excel'de sıfırdan grafik (im yok)
  try {
    $wb = $xl.Workbooks.Add(); $ws = $wb.Worksheets.Item(1)
    $ws.Range("A1").Value2 = "Ay"; $ws.Range("B1").Value2 = "Satis"; $ws.Range("C1").Value2 = "Gider"
    for ($i = 2; $i -le 5; $i++) { $ws.Cells.Item($i, 1).Value2 = "A$i"; $ws.Cells.Item($i, 2).Value2 = $i * 10; $ws.Cells.Item($i, 3).Value2 = $i * 7 }
    $ws.Shapes.AddChart2(201, 51, 200, 20, 360, 220).Chart.SetSourceData($ws.Range("A1:C5"))
    $ws.Shapes.AddChart2(227, 4, 200, 260, 360, 220).Chart.SetSourceData($ws.Range("A1:C5"))
    $ws.Shapes.AddChart2(251, 5, 200, 500, 360, 220).Chart.SetSourceData($ws.Range("A1:C5"))
    $wb.SaveAs((Join-Path $Kok "excel_yeni.xlsx"), 51); $wb.Close($false); "ok excel_yeni"
  } catch { "HATA excel_yeni : $($_.Exception.Message)" }
} finally { $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl); [GC]::Collect() }
"kalan PID: $(@(Get-Process EXCEL -ErrorAction SilentlyContinue | ForEach-Object Id))"
