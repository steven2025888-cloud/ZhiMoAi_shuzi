Option Explicit

Dim oFSO, oShell, sBase, sPyw, sPy, sScript, sLogFile, oLog

Set oFSO   = CreateObject("Scripting.FileSystemObject")
Set oShell = CreateObject("WScript.Shell")

sBase   = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sPyw    = sBase & "IndexTTS2-SonicVale\installer_files\env\pythonw.exe"
sPy     = sBase & "IndexTTS2-SonicVale\installer_files\env\python.exe"
sScript = sBase & "app_backend.py"
sLogFile = sBase & "vbs_startup.log"

Sub WriteLog(msg)
    On Error Resume Next
    Set oLog = oFSO.OpenTextFile(sLogFile, 8, True)
    oLog.WriteLine Now & " | " & msg
    oLog.Close
    Set oLog = Nothing
End Sub

WriteLog "========== Startup Begin =========="
WriteLog "Base Path: " & sBase

If Not oFSO.FileExists(sScript) Then
    WriteLog "[ERROR] app_backend.py not found: " & sScript
    MsgBox "Cannot find main program file:" & vbCrLf & vbCrLf & sScript & vbCrLf & vbCrLf & _
           "Please ensure program files are complete.", vbCritical, "Startup Failed"
    WScript.Quit
End If

WriteLog "[OK] Main program file exists"

Dim sPython
sPython = ""

If oFSO.FileExists(sPyw) Then
    sPython = sPyw
    WriteLog "[OK] Using pythonw.exe (no console)"
ElseIf oFSO.FileExists(sPy) Then
    sPython = sPy
    WriteLog "[OK] Using python.exe (console mode)"
Else
    WriteLog "[ERROR] Python interpreter not found"
    WriteLog "  Path 1: " & sPyw
    WriteLog "  Path 2: " & sPy
    MsgBox "Cannot find Python interpreter:" & vbCrLf & vbCrLf & _
           "pythonw.exe: " & sPyw & vbCrLf & _
           "python.exe: " & sPy & vbCrLf & vbCrLf & _
           "Please ensure environment is installed correctly.", vbCritical, "Startup Failed"
    WScript.Quit
End If

On Error Resume Next
Dim sCmd, iResult
sCmd = """" & sPython & """ """ & sScript & """"
WriteLog "Execute command: " & sCmd

iResult = oShell.Run(sCmd, 0, False)

If Err.Number <> 0 Then
    WriteLog "[ERROR] Startup failed - " & Err.Description & " (Code: " & Err.Number & ")"
    MsgBox "Startup failed:" & vbCrLf & vbCrLf & _
           "Error: " & Err.Description & vbCrLf & _
           "Code: " & Err.Number & vbCrLf & vbCrLf & _
           "Check log: vbs_startup.log", vbCritical, "Startup Failed"
Else
    WriteLog "[OK] Startup command executed"
    WriteLog "========== Startup Complete =========="
End If

Set oFSO   = Nothing
Set oShell = Nothing
