#Requires -RunAsAdministrator
# Installs a scheduled task that starts the tg-stealth-scanner Docker container on user logon.

param(
    [string]$ProjectPath = "D:\Repo\tg-stealth-scanner"
)

$TaskName = "tg-stealth-scanner-autostart"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ProjectPath\scripts\autostart.ps1`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
Write-Host "Scheduled task '$TaskName' installed. The bot will start automatically after you log in."
