$ProjectPath = Split-Path -Parent $PSScriptRoot
$startup = [Environment]::GetFolderPath('Startup')
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut("$startup\tg-stealth-scanner.lnk")
$shortcut.TargetPath = "$ProjectPath\scripts\startup.vbs"
$shortcut.WorkingDirectory = $ProjectPath
$shortcut.Save()
Write-Host "Shortcut created: $startup\tg-stealth-scanner.lnk"
