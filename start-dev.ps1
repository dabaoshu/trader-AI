Param()

$ErrorActionPreference = "Stop"

# 项目根目录（即本脚本所在目录）
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CChanTrader-AI 一键开发启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 激活虚拟环境 traderCC
$venvActivate = Join-Path $root "traderCC\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Error "未找到虚拟环境激活脚本：$venvActivate"
    exit 1
}

Write-Host "[→] 正在激活虚拟环境 traderCC ..." -ForegroundColor Yellow
. $venvActivate
Write-Host "[✓] 虚拟环境已激活" -ForegroundColor Green
Write-Host ""

# 启动 Flask 后端（前台运行，日志直接输出到当前终端）
Write-Host "[→] 启动 Flask 后端 (http://localhost:8080) ..." -ForegroundColor Yellow
try {
    python backend/app.py
}
catch {
    Write-Error "Flask 启动失败：$($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "[OK] Flask exited, script finished." -ForegroundColor Green
