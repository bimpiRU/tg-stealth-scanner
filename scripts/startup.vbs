' Runs tg-stealth-scanner autostart PowerShell script hidden on Windows logon.
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptPath = WScript.ScriptFullName
ScriptsDir = FSO.GetParentFolderName(ScriptPath)
ProjectPath = FSO.GetParentFolderName(ScriptsDir)
Cmd = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ScriptsDir & "\autostart.ps1"""
WshShell.Run Cmd, 0, False
Set WshShell = Nothing
Set FSO = Nothing
