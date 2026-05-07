param([string]$ScriptDir)

$desktop     = [Environment]::GetFolderPath('Desktop')
$shortcut    = Join-Path $desktop 'oXben - SpeechXText.lnk'
$voiceTyper  = Join-Path $ScriptDir 'voice_typer.py'
$srcIcon     = Join-Path $ScriptDir 'icon.ico'

# Copy icon to a path with NO special/unicode characters so Windows loads it reliably
$iconDir  = Join-Path $env:APPDATA 'oXben'
$iconPath = Join-Path $iconDir 'icon.ico'
if (-not (Test-Path $iconDir)) { New-Item -ItemType Directory -Path $iconDir | Out-Null }
Copy-Item -Path $srcIcon -Destination $iconPath -Force
Write-Host "[OK] Ikon kopyalandi: $iconPath"

# Find pythonw.exe next to python.exe
$pythonExe   = (Get-Command python.exe -ErrorAction Stop).Source
$pythonwExe  = $pythonExe -replace 'python\.exe$','pythonw.exe'
if (-not (Test-Path $pythonwExe)) { $pythonwExe = $pythonExe }

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcut)
$sc.TargetPath      = $pythonwExe
$sc.Arguments       = "`"$voiceTyper`""
$sc.WorkingDirectory = $ScriptDir
$sc.IconLocation    = "$iconPath,0"
$sc.Description     = 'oXben - SpeechXText — Real-Time Turkish Dictation'
$sc.Save()

# Force Windows to rebuild icon cache so the shortcut shows correct icon
$cachePath = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Explorer'
Get-ChildItem $cachePath -Filter "iconcache*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem $cachePath -Filter "thumbcache*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
# Notify shell of association change to force icon refresh
Add-Type -TypeDefinition @"
using System.Runtime.InteropServices;
public class Shell32 {
    [DllImport("shell32.dll")] public static extern void SHChangeNotify(int e, int f, System.IntPtr a, System.IntPtr b);
}
"@ -ErrorAction SilentlyContinue
try { [Shell32]::SHChangeNotify(0x8000000, 0, [System.IntPtr]::Zero, [System.IntPtr]::Zero) } catch {}

Write-Host "[OK] Kisayol olusturuldu: $shortcut"
