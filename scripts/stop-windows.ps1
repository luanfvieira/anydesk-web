param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$task = Get-ScheduledTask -TaskName 'AnyDeskWebBridge' -ErrorAction SilentlyContinue
if (!$task) { Write-Output 'A tarefa da ponte não existe.'; exit 0 }
if ($task.State -eq 'Running') {
    & (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'shutdown.py') $Port
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível liberar entradas. A tarefa não será encerrada à força.' }
    $deadline = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 200
        $task = Get-ScheduledTask -TaskName 'AnyDeskWebBridge'
    } while ($task.State -eq 'Running' -and (Get-Date) -lt $deadline)
    if ($task.State -eq 'Running') { throw 'O processo não confirmou saída. A tarefa foi preservada para diagnóstico.' }
}
Unregister-ScheduledTask -TaskName 'AnyDeskWebBridge' -Confirm:$false
Write-Output 'Ponte encerrada e entradas liberadas. Sessões nativas do AnyDesk preservadas.'
