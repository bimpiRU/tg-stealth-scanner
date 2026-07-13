' Runs tg-stealth-scanner autostart PowerShell script hidden on Windows logon.
Set WshShell = CreateObject("WScript.Shell")
ProjectPath = "D:\Repo\tg-stealth-scanner"
Cmd = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ProjectPath & "\scripts\autostart.ps1"""
WshShell.Run Cmd, 0, False
Set WshShell = Nothing
