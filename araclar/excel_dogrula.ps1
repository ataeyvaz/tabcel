# Gerçek Excel ile uyum denetimi (Faz 6 / 6h): bir .xlsx'i Excel'de (COM, görünmez) açar, grafik/resim sayısını ve
# türlerini yazar, her grafiği PNG olarak dışa aktarır ve Excel'in kendi kaydıyla bir kopya üretir.
# Kullanım: powershell -File araclar\excel_dogrula.ps1 <dosya.xlsx> <cikti_klasoru>
# Excel yolu: C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE (Office 16). Açıkken kullanıcı belgelerine dokunmaz.
param([Parameter(Mandatory)][string]$Dosya, [Parameter(Mandatory)][string]$Cikti)
New-Item -ItemType Directory -Force $Cikti | Out-Null
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
  "Excel sürümü: $($xl.Version)"
  $wb = $xl.Workbooks.Open((Resolve-Path $Dosya).Path)
  $ws = $wb.Worksheets.Item(1)
  $ws.Activate()
  "Grafik sayısı: $($ws.ChartObjects().Count)  Şekil/resim toplamı: $($ws.Shapes.Count)"
  $i = 0
  foreach ($co in $ws.ChartObjects()) {
    $i++
    $c = $co.Chart
    $t = if ($c.HasTitle) { $c.ChartTitle.Text } else { "(başlıksız)" }
    "{0,2}. tür={1,5} seri={2} başlık='{3}' konum={4}" -f $i, $c.ChartType, $c.SeriesCollection().Count, $t, $co.TopLeftCell.Address($false, $false)
    [void]$xl.Goto($co.TopLeftCell, $true)                       # ekran dışındaki grafik boş dışa aktarılmasın
    [void]$c.Export((Join-Path (Resolve-Path $Cikti).Path "g$i.png"))
  }
  $wb.SaveAs((Join-Path (Resolve-Path $Cikti).Path "excel_kaydetti.xlsx"))
  $wb.Close($false)
} catch { "HATA: $($_.Exception.Message)" } finally { $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl) }
