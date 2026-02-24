; ============================================================
; 织梦AI大模型 v2.0 — Inno Setup 打包脚本
; ============================================================
; 说明：
;   本脚本只打包根目录下的轻量文件（代码 + UI + 配置 + 启动脚本 + 资源目录）。
;   _internal_tts 和 _internal_sync（引擎环境）不包含在内，
;   需另行打包后让用户解压到安装目录对应位置。
;
; 更新内容：
;   - avatars/、voices/、unified_outputs/ 目录只创建空文件夹，不打包内容
;   - Python代码和env文件加密打包
;   - 不打包调试用的bat文件
;   - 启动应用.bat和启动应用.vbs合并为exe程序
;   - 自动清理超大日志文件
;   - 新增运行日志功能
;
; 使用方法：
;   1. 安装 Inno Setup Compiler（https://jrsoftware.org/isinfo.php）
;   2. 用 Inno Setup Compiler 打开本文件
;   3. 点击 Compile 即可生成安装包 exe
; ============================================================

#define MyAppName      "织梦AI大模型"
#define MyAppVersion   "2.0"
#define MyAppPublisher "织梦AI"
#define MyAppURL       "https://zhimengai.xyz"
; 源文件根目录 — 编译时请确保此路径正确
#define SourceRoot     "D:\ZhiMoAi_shuzi"

[Setup]
AppId={{B7E5F3A2-9C41-4D8E-A6B1-2F0E7D3C5A89}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\ZhiMoAI
DefaultGroupName={#MyAppName}
; 输出安装包到 SourceRoot\dist 目录
OutputDir={#SourceRoot}\dist
OutputBaseFilename=ZhiMoAI_v{#MyAppVersion}_Setup
SetupIconFile={#SourceRoot}\logo.ico
UninstallDisplayIcon={app}\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
; 需要管理员权限安装（某些目录需要写权限）
PrivilegesRequired=admin
; 向导界面设置
WizardStyle=modern
WizardSizePercent=120,120
DisableProgramGroupPage=yes
; 支持静默安装
; 自动关闭正在运行的应用程序
CloseApplications=yes
RestartApplications=yes
; 许可协议（可选：取消注释下面一行并提供文件）
; LicenseFile={#SourceRoot}\LICENSE.txt

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"
Name: "startmenuicon"; Description: "创建开始菜单快捷方式"; GroupDescription: "附加选项:"

; ============================================================
;  文件列表
; ============================================================
[Files]
; ── Python 字节码（加密版本 - 只打包.pyc，不打包.py）──
Source: "{#SourceRoot}\app_backend.pyc";          DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\unified_app.pyc";          DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_avatar.pyc";           DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_voice.pyc";            DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_subtitle.pyc";         DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_license.pyc";          DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_douyin_publish.pyc";   DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_bilibili_publish.pyc"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_shipinhao_publish.pyc"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_xiaohongshu_publish.pyc"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\lib_meta_store.pyc";       DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\ws_worker.pyc";            DestDir: "{app}"; Flags: ignoreversion

; 注意：不打包任何.py源文件，只打包.pyc加密文件

; ── 前端资源 ──
Source: "{#SourceRoot}\ui_init.js";     DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\ui_style.css";   DestDir: "{app}"; Flags: ignoreversion

; ── 配置文件 ──
Source: "{#SourceRoot}\.env";           DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\.license";       DestDir: "{app}"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SourceRoot}\pip.ini";        DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; ── Logo / 图标 ──
Source: "{#SourceRoot}\logo.ico";       DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\logo.jpg";       DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; ── 启动程序（exe）──
Source: "{#SourceRoot}\ZhiMoAI_Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\启动应用.bat";        DestDir: "{app}"; Flags: ignoreversion

; ── 工具脚本 ──
Source: "{#SourceRoot}\安装依赖.bat";       DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\安装抖音发布依赖.bat"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\打包检查清单.bat";    DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; ── 文档 ──
Source: "{#SourceRoot}\README.txt";                 DestDir: "{app}"; Flags: ignoreversion isreadme skipifsourcedoesntexist
Source: "{#SourceRoot}\客户使用手册.txt";             DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\Whisper使用说明.txt";          DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\抖音发布功能说明.txt";          DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\douyin_publish_agreement.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\功能演示-工作台记录.md";        DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; ── 字体目录 ──
Source: "{#SourceRoot}\fonts\*";        DestDir: "{app}\fonts"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ── ChromeDriver ──
Source: "{#SourceRoot}\chromedriver\*"; DestDir: "{app}\chromedriver"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ── 伪装内部目录（保持目录结构完整） ──
Source: "{#SourceRoot}\_internal_cache\*";  DestDir: "{app}\_internal_cache";  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "{#SourceRoot}\_internal_config\*"; DestDir: "{app}\_internal_config"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "{#SourceRoot}\_internal_data\*";   DestDir: "{app}\_internal_data";   Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "{#SourceRoot}\_internal_logs\*";   DestDir: "{app}\_internal_logs";   Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "{#SourceRoot}\_internal_temp\*";   DestDir: "{app}\_internal_temp";   Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ── 注意：avatars/、voices/、unified_outputs/ 目录只创建空文件夹，不打包内容 ──

; ============================================================
;  注意：以下目录 **不** 包含在安装包中：
;    _internal_tts   （语音合成引擎 — 需用户单独解压）
;    _internal_sync   （口型同步引擎 — 需用户单独解压）
;    启动浏览器版本.bat （调试用，不打包）
;    启动应用_调试模式.bat （调试用，不打包）
; ============================================================

[Dirs]
Name: "{app}\avatars"
Name: "{app}\voices"
Name: "{app}\unified_outputs"
Name: "{app}\logs"; Flags: uninsneveruninstall
Name: "{app}\_internal_tts";  Flags: uninsneveruninstall
Name: "{app}\_internal_sync"; Flags: uninsneveruninstall

; ============================================================
;  快捷方式
; ============================================================
[Icons]
Name: "{group}\{#MyAppName}";            Filename: "{app}\ZhiMoAI_Launcher.exe"; IconFilename: "{app}\logo.ico"; WorkingDir: "{app}"
Name: "{group}\卸载 {#MyAppName}";        Filename: "{uninstallexe}"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\{#MyAppName}";       Filename: "{app}\ZhiMoAI_Launcher.exe"; IconFilename: "{app}\logo.ico"; WorkingDir: "{app}"; Tasks: desktopicon

; ============================================================
;  安装后运行
; ============================================================
[Run]
; 普通安装完成后询问是否启动
Filename: "{app}\ZhiMoAI_Launcher.exe"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
; 静默安装完成后自动启动（用于自动更新）
Filename: "{app}\ZhiMoAI_Launcher.exe"; Flags: nowait skipifdoesntexist runhidden; Check: WizardSilent

; ============================================================
;  卸载时删除生成的文件（可选）
; ============================================================
[UninstallDelete]
Type: filesandordirs; Name: "{app}\unified_outputs"
Type: filesandordirs; Name: "{app}\_internal_cache"
Type: filesandordirs; Name: "{app}\_internal_logs"
Type: filesandordirs; Name: "{app}\_internal_temp"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files;          Name: "{app}\*.log"
; 注意：不删除 .license 文件，保留用户的卡密信息

[Code]
// 安装完成后的处理（已禁用提示）
procedure CurStepChanged(CurStep: TSetupStep);
begin
  // 不显示任何提示，直接完成安装
end;
