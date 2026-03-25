@echo off
cd /d "C:\Users\Pablo\Documents\Obsidian Vault\Trader Bot"

git pull --no-rebase

git add Bot_Quant_IA/market_logs/
git diff --staged --quiet && (
    echo [AutoPush] Sin cambios en market_logs, nada que pushear.
) || (
    git commit -m "auto: strategies_pnl %date%"
    git push
    echo [AutoPush] Push completado.
)
