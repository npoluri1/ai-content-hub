param(
    [string]$Action = "all",
    [string]$PythonPath = "python"
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

# Config
$env:SOURCES_ENABLED = "demo"
$env:LLM_PROVIDER = "none"
$env:CHROMA_DB_PATH = ".\data\chroma_db"
$env:SQL_DB_PATH = ".\data\content_hub.db"

# Ensure data dirs
New-Item -ItemType Directory -Force -Path ".\data" | Out-Null
New-Item -ItemType Directory -Force -Path ".\data\chroma_db" | Out-Null

function Run-Pipeline {
    Write-Host "=== Running Pipeline ===" -ForegroundColor Cyan
    & $PythonPath -m pipeline run
    if ($LASTEXITCODE -ne 0) { throw "Pipeline failed" }
}

function Start-Api {
    Write-Host "=== Starting API on port 8000 ===" -ForegroundColor Cyan
    $env:API_PORT = 8000
    $job = Start-Job -ScriptBlock {
        param($p, $d)
        Set-Location $d
        & $p -m pipeline api
    } -ArgumentList $PythonPath, $RootDir
    Start-Sleep -Seconds 3
    Write-Host "API started!" -ForegroundColor Green
    return $job
}

function Start-Dashboard {
    Write-Host "=== Starting Dashboard on port 8501 ===" -ForegroundColor Cyan
    $job = Start-Job -ScriptBlock {
        param($p, $d)
        Set-Location $d
        & $p -m streamlit run pipeline/dashboard/app.py --server.port=8501 --server.headless=true
    } -ArgumentList $PythonPath, $RootDir
    Start-Sleep -Seconds 3
    Write-Host "Dashboard started!" -ForegroundColor Green
    return $job
}

function Start-Frontend {
    Write-Host "=== Starting React Frontend on port 3000 ===" -ForegroundColor Cyan
    $job = Start-Job -ScriptBlock {
        param($d)
        Set-Location "$d\frontend"
        npm run dev
    } -ArgumentList $RootDir
    Start-Sleep -Seconds 3
    Write-Host "Frontend started!" -ForegroundColor Green
    return $job
}

function Show-Status {
    Write-Host "`n========================================" -ForegroundColor Yellow
    Write-Host "  AI Content Hub - Local Deployment" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  API:        http://localhost:8000" -ForegroundColor Green
    Write-Host "  Dashboard:  http://localhost:8501" -ForegroundColor Green
    Write-Host "  Frontend:   http://localhost:3000" -ForegroundColor Green
    Write-Host "  Health:     http://localhost:8000/health" -ForegroundColor Green
    Write-Host "  Stats:      http://localhost:8000/stats" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Yellow
}

# Main
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  AI Content Hub - Local Deployment" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

switch ($Action) {
    "pipeline" { Run-Pipeline }
    "api" { $null = Start-Api; Show-Status }
    "dashboard" { $null = Start-Dashboard; Show-Status }
    "frontend" { $null = Start-Frontend; Show-Status }
    "all" {
        Run-Pipeline
        $null = Start-Api
        $null = Start-Dashboard
        $null = Start-Frontend
        Show-Status
        Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Red
        while ($true) { Start-Sleep -Seconds 10 }
    }
    default {
        Write-Host "Usage: .\start.ps1 [pipeline|api|dashboard|frontend|all]" -ForegroundColor Yellow
    }
}
