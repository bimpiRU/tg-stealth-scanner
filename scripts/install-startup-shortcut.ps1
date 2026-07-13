$startup = [Environment]::GetFolderPath('Startup')
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut("$startup\tg-stealth-scanner.lnk")
$shortcut.TargetPath = "D:\Repo\tg-stealth-scanner\scripts\startup.vbs"
$shortcut.WorkingDirectory = "D:\Repo\tg-stealth-scanner"
$shortcut.Save()
Write-Host "Shortcut created: $startup\tg-stealth-scanner.lnk"
