param([Parameter(Mandatory)][string]$Girdi,[Parameter(Mandatory)][string]$Cikti)
$vakalar = [System.IO.File]::ReadAllText($Girdi,[System.Text.Encoding]::UTF8) | ConvertFrom-Json
$xl = New-Object -ComObject Excel.Application; $xl.Visible=$false; $xl.DisplayAlerts=$false
$sonuc = New-Object System.Collections.Generic.List[string]
try {
  $wb=$xl.Workbooks.Add(); $ws=$wb.Worksheets.Item(1); $ws.Columns.ColumnWidth=60
  foreach ($v in $vakalar) {
    $ws.Cells.Clear() | Out-Null
    try {
      if ($v.hucreler) { foreach ($p in $v.hucreler.PSObject.Properties) {
        $h=$ws.Range($p.Name); $val=$p.Value; if ($val -eq $null) { continue }
        if ($val -is [string] -and $val.StartsWith("=")) { $h.Formula=$val } elseif ($val -is [string]) { $h.NumberFormat="@"; $h.Value2=$val } elseif ($val -is [bool]) { if ($val) { $h.Formula='=TRUE' } else { $h.Formula='=FALSE' } } else { $h.Value2=[double]$val } } }
      $t=$ws.Range("Z1")
      if ($v.bicim) { $t.NumberFormatLocal=$v.bicim }
      if ($v.formul -ne $null) { $t.Formula=$v.formul } elseif ($v.deger -ne $null) { $t.Value2=[double]$v.deger }
      $xl.Calculate()
      $d=$t.Value2; $tx=$t.Text
      if ($d -eq $null) { $tur="bos"; $s="" }
      elseif ($d -is [string]) { $tur="metin"; $s=$d }
      elseif ($d -is [bool]) { $tur="bool"; $s="$d" }
      elseif ($d -is [int] -and $tx.StartsWith("#")) { $tur="hata"; $s=$tx }
      else { $tur="sayi"; $s=([double]$d).ToString("R",[System.Globalization.CultureInfo]::InvariantCulture) }
      $sonuc.Add(($v.id)+"`t$tur`t"+($s -replace "`r|`n|`t"," ")+"`t"+($tx -replace "`r|`n|`t"," "))
    } catch { $sonuc.Add(($v.id)+"`tISTISNA`t"+($_.Exception.Message -replace "`r|`n|`t"," ")+"`t") }
  }
  [System.IO.File]::WriteAllLines($Cikti,$sonuc,(New-Object System.Text.UTF8Encoding($false)))
  $wb.Close($false)
} catch { "HATA: $($_.Exception.Message)" } finally { $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl) }
