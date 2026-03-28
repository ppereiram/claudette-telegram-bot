# sync_vault.ps1
# Sincroniza todos los vaults de Obsidian al repo de Claudette
# y dispara kb_ingest en Render via Telegram
# 
# Uso manual:   .\sync_vault.ps1
# Task Scheduler: cada noche a las 2am

$ErrorActionPreference = "Stop"
$RepoPath = "C:\Users\Pablo\Documents\GitHub\claudette-telegram-bot"
$VaultBase = "C:\Users\Pablo\Documents\Obsidian Vault"
$LogFile = "$RepoPath\sync_vault.log"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content $LogFile $line
}

Log "=== SYNC VAULT INICIADO ==="

# --- 1. Copiar vaults al repo ---
$vaults = @{
    "Trader Bot"          = "TraderBot"
    "Arepartir"           = "Arepartir"
    "Ensayos"             = "Ensayos"
    "Novela"              = "Novela"
    "Claudette Agent\Claudette Agent" = "ClaudetteAgent"
    "Graficador matematico" = "GraficadorMatematico"
    "Soluciones GR"       = "SolucionesGR"
    "Biblioteca Viva"     = "BibliotecaViva"
    "CEREBRO2"            = "CEREBRO2"
    "Desarrollador Inmobiliario" = "DesarrolladorInmobiliario"
    "Libros"              = "Libros"
}

$changed = $false

foreach ($src in $vaults.Keys) {
    $dst = $vaults[$src]
    $srcPath = "$VaultBase\$src"
    $dstPath = "$RepoPath\vault\$dst"

    if (-Not (Test-Path $srcPath)) {
        Log "SKIP: $src no existe"
        continue
    }

    # Copiar SOLO archivos .md, excluyendo carpetas de sistema
    robocopy "$srcPath" "$dstPath" *.md /E /XD .obsidian .trash .claude .git __pycache__ node_modules /XF *.py *.db *.pyc *.env *.html *.txt *.lnk *.js *.ts *.json *.css *.log /NFL /NDL /NJH /NJS /nc /ns /np 2>$null | Out-Null

    Log "OK: $src -> vault/$dst"
    $changed = $true
}

# --- 2. Git add + commit + push ---
Set-Location $RepoPath

# Verificar si hay cambios reales
git add vault/ 2>$null
$status = git status --porcelain

if ($status) {
    $date = Get-Date -Format "yyyy-MM-dd HH:mm"
    git commit -m "sync: vault update $date"
    git push origin main
    Log "GIT: push exitoso"
    $changed = $true
} else {
    Log "GIT: sin cambios, nada que pushear"
    $changed = $false
}

# --- 3. Notificar a Claudette via Telegram para que corra kb_ingest ---
if ($changed) {
    $token = $env:TELEGRAM_BOT_TOKEN
    $chatId = $env:TELEGRAM_CHAT_ID

    if ($token -and $chatId) {
        $msg = "kb_ingest"
        $url = "https://api.telegram.org/bot$token/sendMessage"
        $body = @{ chat_id = $chatId; text = $msg } | ConvertTo-Json
        Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json" | Out-Null
        Log "TELEGRAM: kb_ingest enviado"
    } else {
        Log "TELEGRAM: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados, saltando"
    }
}

Log "=== SYNC VAULT COMPLETADO ==="
