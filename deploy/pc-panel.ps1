# PC Panel: PowerShell'de uzun süren komut bitince karta bildirim (✓ / ✗, süre). Windows PowerShell 5.1 ve 7+.
# fish eklentisinin (deploy/pc-panel.fish) Windows karşılığı.
# Kurulum: deploy\kur.ps1 -PowerShell  → profil dosyasına bu dosyayı yükleyen bir satır ekler.
# Süre eşiği ve hariç tutulan programlar ayar dosyasının [komut] bölümünde (servis karar verir); burada yalnızca
# 5 sn'den uzun komutlar servise bildirilir. Olay doğrudan servisin yerel portuna yazılır (yeni süreç açılmaz).
if ($global:__PcPanelPrompt) { return }
$global:__PcPanelPrompt = $function:prompt
$global:__PcPanelLastId = (Get-History -Count 1).Id

function global:prompt {
    $ok = $?
    $code = $global:LASTEXITCODE
    try {
        $h = Get-History -Count 1
        if ($h -and $h.Id -ne $global:__PcPanelLastId) {
            $global:__PcPanelLastId = $h.Id
            $ms = [int]($h.EndExecutionTime - $h.StartExecutionTime).TotalMilliseconds
            if ($ms -ge 5000) {
                $kod = if ($ok) { 0 } elseif ($code) { $code } else { 1 }
                $text = $h.CommandLine
                if ($text.Length -gt 300) { $text = $text.Substring(0, 300) }
                $json = @{ k = 'cmd'; ms = $ms; code = $kod; cmd = $text } | ConvertTo-Json -Compress
                $client = New-Object System.Net.Sockets.TcpClient
                try {
                    if ($client.ConnectAsync('127.0.0.1', 47613).Wait(200)) {
                        $bytes = [Text.Encoding]::UTF8.GetBytes($json + "`n")
                        $client.GetStream().Write($bytes, 0, $bytes.Length)
                    }
                } finally { $client.Close() }
            }
        }
    } catch {}
    $global:LASTEXITCODE = $code
    & $global:__PcPanelPrompt
}
