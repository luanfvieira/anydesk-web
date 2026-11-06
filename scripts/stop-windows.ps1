$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName 'AnyDeskWebBridge' -ErrorAction SilentlyContinue
if ($task) { Stop-ScheduledTask -TaskName 'AnyDeskWebBridge'; Unregister-ScheduledTask -TaskName 'AnyDeskWebBridge' -Confirm:$false }
Write-Output 'Tarefa da ponte encerrada. O serviço AnyDesk e sua configuração foram preservados.'
