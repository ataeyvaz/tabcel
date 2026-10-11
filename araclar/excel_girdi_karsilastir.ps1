# Belirsiz girdilerin gerçek Excel'deki karşılığı (T5b). Kullanım: .\araclar\excel_girdi_karsilastir.ps1 <girdiler.txt> <çıktı.tsv>
# girdiler.txt: her satır bir girdi (UTF-8). Çıktı: girdi <TAB> tür (sayi|metin|bool|hata|bos) <TAB> değer <TAB> sayı biçimi
# Görünmez yeni Excel örneği açar; kullanıcının açık çalışma kitaplarına dokunmaz; sonunda Quit.
param([string]$Girdi, [string]$Cikti)
$ErrorActionPreference = "Stop"
$satirlar = [System.IO.File]::ReadAllLines((Resolve-Path $Girdi), [System.Text.Encoding]::UTF8)
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Add()
    $ws = $wb.Worksheets.Item(1)
    $sonuc = New-Object System.Collections.Generic.List[string]
    $i = 1
    foreach ($g in $satirlar) {
        $h = $ws.Cells.Item($i, 1)
        $h.NumberFormat = "General"
        $h.FormulaLocal = $g           # elle yazılmış gibi, Excel arayüzünün bölgesel ayarlarıyla ayrıştırılır (Value2 ABD biçimiyle ayrıştırır: kullanma)
        $v = $h.Value2
        $f = $h.NumberFormat
        if ($v -eq $null) { $t = "bos"; $d = "" }
        elseif ($v -is [string]) { $t = "metin"; $d = $v }
        elseif ($v -is [bool]) { $t = "bool"; $d = $v }
        elseif ($v -is [int] -and $v -lt 0 -and $h.Text.StartsWith("#")) { $t = "hata"; $d = $h.Text }
        else { $t = "sayi"; $d = ([double]$v).ToString([System.Globalization.CultureInfo]::InvariantCulture) }
        $sonuc.Add("$g`t$t`t$d`t$f")
        $i++
    }
    [System.IO.File]::WriteAllLines($Cikti, $sonuc, (New-Object System.Text.UTF8Encoding($false)))
    $wb.Close($false)
} finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
