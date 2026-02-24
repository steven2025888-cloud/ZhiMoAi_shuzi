' VBS 脚本 - 自动化文件上传对话框
' 使用方法: cscript upload_file.vbs "文件完整路径"

Set WshShell = CreateObject("WScript.Shell")
Set objArgs = WScript.Arguments

If objArgs.Count = 0 Then
    WScript.Echo "错误: 请提供文件路径"
    WScript.Quit 1
End If

filePath = objArgs(0)

' 等待文件对话框出现
WScript.Sleep 1500

' 尝试激活文件对话框窗口
WshShell.AppActivate "打开"
WScript.Sleep 300

' 如果上面失败，尝试其他常见标题
On Error Resume Next
WshShell.AppActivate "Open"
WScript.Sleep 300
WshShell.AppActivate "选择文件"
WScript.Sleep 300
WshShell.AppActivate "Choose File"
WScript.Sleep 300
On Error Goto 0

' 按 Ctrl+G 或直接定位到文件名输入框
' 在 Windows 文件对话框中，Ctrl+Shift+G 或 Alt+D 可以激活地址栏
WshShell.SendKeys "^+g"
WScript.Sleep 200

' 如果上面不行，尝试 Alt+D
WshShell.SendKeys "%d"
WScript.Sleep 200

' 输入文件路径
WshShell.SendKeys filePath
WScript.Sleep 500

' 按回车确认
WshShell.SendKeys "{ENTER}"
WScript.Sleep 300

WScript.Echo "文件路径已发送: " & filePath
