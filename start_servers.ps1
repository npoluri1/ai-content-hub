$frontendDir = "D:\WorkSpace\LinkedIn_AI_TechStack_Content\frontend"
$backendDir = "D:\WorkSpace\LinkedIn_AI_TechStack_Content"
$npm = "C:\Program Files\nodejs\npm.cmd"
$python = "C:\Users\Legion\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

$logDir = "D:\WorkSpace\LinkedIn_AI_TechStack_Content"
$frontendLog = "$logDir\frontend.log"
$backendLog = "$logDir\backend.log"

# Start backend
Start-Process -NoNewWindow -FilePath $python -ArgumentList "-m uvicorn pipeline.api.main:app --reload --port 8000" -WorkingDirectory $backendDir -RedirectStandardOutput $backendLog -RedirectStandardError $backendLog

Start-Sleep -Seconds 3

# Start frontend
Start-Process -NoNewWindow -FilePath $npm -ArgumentList "run dev" -WorkingDirectory $frontendDir -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendLog

Write-Output "Started backend (PID: $(Get-Process -Name python | Select-Object -First 1 -ExpandProperty Id))"
Write-Output "Started frontend (PID: $(Get-Process -Name node | Select-Object -First 1 -ExpandProperty Id))"
