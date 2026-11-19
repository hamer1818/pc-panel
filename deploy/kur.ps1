# PC Panel servisini Windows'ta kurar / kaldırır (yönetici GEREKMEZ — Görev Zamanlayıcı'da kullanıcı görevi).
# Linux karşılığı: deploy/kur.sh (systemd kullanıcı servisi).
#
#   powershell -ExecutionPolicy Bypass -File deploy\kur.ps1               → kur ve başlat
#   powershell -ExecutionPolicy Bypass -File deploy\kur.ps1 -PowerShell   → + PowerShell uzun komut bildirimi
#   powershell -ExecutionPolicy Bypass -File deploy\kur.ps1 kaldir        → durdur ve kaldır
#
# Servis oturum açılınca penceresiz başlar (pythonw), günlük: %LOCALAPPDATA%\pc-panel\pc-panel.log
param(
    [ValidateSet('kur', 'kaldir')][string]$Islem = 'kur',
    [switch]$PowerShell
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$Kok = Split-Path -Parent $PSScriptRoot           # proje klasörü
$Host_ = Join-Path $Kok 'host'
$Pythonw = Join-Path $Host_ '.venv\Scripts\pythonw.exe'
$Python = Join-Path $Host_ '.venv\Scripts\python.exe'
$TaskName = 'PC Panel'
$LogDir = Join-Path $env:LOCALAPPDATA 'pc-panel'
$Log = Join-Path $LogDir 'pc-panel.log'
$Startup = [Environment]::GetFolderPath('Startup')
$StartupLnk = Join-Path $Startup 'PC Panel.lnk'
$ProfileMark = '# pc-panel (deploy\kur.ps1 -PowerShell)'

function Stop-PcPanel {
    Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe' OR Name='pc-panel.exe'" |
        Where-Object { $_.CommandLine -match 'pc_panel|pc-panel' -and $_.CommandLine -notmatch '--konsol|--once|--json' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Get-ProfilePaths {
    $docs = [Environment]::GetFolderPath('MyDocuments')
    @((Join-Path $docs 'WindowsPowerShell\profile.ps1'), (Join-Path $docs 'PowerShell\profile.ps1'))
}

if ($Islem -eq 'kaldir') {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    Remove-Item $StartupLnk -ErrorAction SilentlyContinue
    Stop-PcPanel
    foreach ($p in Get-ProfilePaths) {
        if (Test-Path $p) {
            $lines = Get-Content $p -Encoding UTF8 | Where-Object { $_ -notlike "*$ProfileMark*" }
            Set-Content -Path $p -Value $lines -Encoding UTF8
        }
    }
    Write-Host 'pc-panel servisi kaldırıldı. (Claude Code hook''ları için: host\.venv\Scripts\python.exe deploy\claude_hooks.py kaldir)'
    exit 0
}

# 1) Python ortamı (uv)
if (-not (Test-Path $Pythonw)) {
    Write-Host 'host\.venv yok, kuruluyor (uv sync)…'
    Push-Location $Host_
    try {
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            uv sync
        } else {
            Write-Host 'uv yok, kuruluyor (python -m pip install --user uv)…'
            python -m pip install --user --disable-pip-version-check -q uv
            python -m uv sync
        }
        if ($LASTEXITCODE) { throw 'uv sync başarısız' }
    } finally { Pop-Location }
}

# 2) Elle çalışan bir kopya portu tutar: kapat (kurulumdan sonra görev yeniden başlatır)
Stop-PcPanel

# 3) Ayar dosyası: yoksa Windows örneğini kopyala, varsa dokunma
$ConfDir = Join-Path $env:APPDATA 'pc-panel'
$Conf = Join-Path $ConfDir 'ayarlar.toml'
if (-not (Test-Path $Conf)) {
    New-Item -ItemType Directory -Force $ConfDir | Out-Null
    Copy-Item (Join-Path $Kok 'deploy\ayarlar.ornek.windows.toml') $Conf
    Write-Host "Ayar dosyası oluşturuldu: $Conf"
}

# 4) Claude Code hook'ları (Geliştirici sayfası)
if (Test-Path (Join-Path $env:USERPROFILE '.claude')) {
    & $Python (Join-Path $Kok 'deploy\claude_hooks.py') kur
}

# 5) İsteğe bağlı: PowerShell'de uzun komut bitince bildirim
if ($PowerShell) {
    $snippet = Join-Path $Kok 'deploy\pc-panel.ps1'
    $line = "if (Test-Path '$snippet') { . '$snippet' }  $ProfileMark"
    foreach ($p in Get-ProfilePaths) {
        New-Item -ItemType Directory -Force (Split-Path $p) | Out-Null
        $old = if (Test-Path $p) { @(Get-Content $p -Encoding UTF8 | Where-Object { $_ -notlike "*$ProfileMark*" }) } else { @() }
        Set-Content -Path $p -Value ($old + $line) -Encoding UTF8
        Write-Host "PowerShell profiline eklendi: $p"
    }
    $policy = Get-ExecutionPolicy -Scope CurrentUser
    if ($policy -in 'Undefined', 'Restricted', 'AllSigned') {
        if ((Get-ExecutionPolicy -Scope LocalMachine) -in 'Undefined', 'Restricted', 'AllSigned') {
            Write-Host 'UYARI: betik çalıştırma kapalı, profil yüklenmez. Açmak için (bir kez):' -ForegroundColor Yellow
            Write-Host '  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned' -ForegroundColor Yellow
        }
    }
}

# 6) Oturum açılınca başlayan görev
New-Item -ItemType Directory -Force $LogDir | Out-Null
$user = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute $Pythonw -Argument "-m pc_panel --gunluk `"$Log`"" -WorkingDirectory $Host_
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew -Priority 5
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Principal $principal -Description 'PC Panel - ESP32-S3 ekran kartı servisi (deploy\kur.ps1)' -Force | Out-Null
    Remove-Item $StartupLnk -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Görev Zamanlayıcı'ya eklendi: '$TaskName' (oturum açılınca başlar)"
} catch {
    # Bazı sistemlerde (ilke) kullanıcı görev ekleyemez: Başlangıç klasörüne kısayol
    Write-Host "Görev eklenemedi ($($_.Exception.Message)); Başlangıç klasörüne kısayol konuyor."
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($StartupLnk)
    $lnk.TargetPath = $Pythonw
    $lnk.Arguments = "-m pc_panel --gunluk `"$Log`""
    $lnk.WorkingDirectory = $Host_
    $lnk.Description = 'PC Panel servisi'
    $lnk.Save()
    Start-Process -FilePath $Pythonw -ArgumentList '-m', 'pc_panel', '--gunluk', "`"$Log`"" -WorkingDirectory $Host_
}

Start-Sleep -Seconds 4
Write-Host ''
if (Test-Path $Log) { Get-Content $Log -Encoding UTF8 -Tail 6 }
Write-Host ''
Write-Host "Kuruldu. Günlük: $Log"
Write-Host "  izlemek için:  Get-Content `"$Log`" -Wait -Tail 20"
