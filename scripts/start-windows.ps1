param([string]$InteractiveUser = 'TI-LOCAL\ti-it', [int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path $root '.runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
$python = Join-Path $root '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Crie .venv e instale requirements.txt antes de iniciar.' }
$existing = Get-ScheduledTask -TaskName 'AnyDeskWebBridge' -ErrorAction SilentlyContinue
if ($existing -and $existing.State -eq 'Running') { Write-Output 'A ponte já está em execução.'; exit 0 }
if (Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "A porta $Port está ocupada." }
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('-u -m bridge --port ' + $Port + ' --origin http://127.0.0.1:' + $Port) -WorkingDirectory $root
$principal = New-ScheduledTaskPrincipal -UserId $InteractiveUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'AnyDeskWebBridge' -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'AnyDeskWebBridge'
Write-Output "Inicialização solicitada em $InteractiveUser. URL pelo túnel: http://127.0.0.1:$Port"
