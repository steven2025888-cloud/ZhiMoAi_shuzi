' VocalSync AI Studio Launcher
Option Explicit

Dim oFSO, oShell, sBase, sPyw, sPy, sScript

Set oFSO   = CreateObject("Scripting.FileSystemObject")
Set oShell = CreateObject("WScript.Shell")

sBase   = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sPyw    = sBase & "IndexTTS2-SonicVale\installer_files\env\pythonw.exe"
sPy     = sBase & "IndexTTS2-SonicVale\installer_files\env\python.exe"
sScript = sBase & "app_backend.py"

If Not oFSO.FileExists(sScript) Then
    MsgBox "Not found: " & sScript, vbCritical, "VocalSync - Error"
    WScript.Quit
End If

If oFSO.FileExists(sPyw) Then
    oShell.Run """" & sPyw & """ """ & sScript & """", 0, False
ElseIf oFSO.FileExists(sPy) Then
    oShell.Run """" & sPy & """ """ & sScript & """", 0, False
Else
    MsgBox "Python not found: " & sPyw, vbCritical, "VocalSync - Error"
End If

Set oFSO   = Nothing
Set oShell = Nothing