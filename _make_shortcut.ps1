param([string]$ScriptDir)

$ErrorActionPreference = 'Stop'

$desktop     = [Environment]::GetFolderPath('Desktop')
$shortcut    = Join-Path $desktop 'oXben - SpeechXText.lnk'
$voiceTyper  = Join-Path $ScriptDir 'voice_typer.py'
$srcIcon     = Join-Path $ScriptDir 'icon.ico'

# voice_typer.py kontrolu
if (-not (Test-Path $voiceTyper)) {
    Write-Error "voice_typer.py bulunamadi: $voiceTyper"
    exit 1
}

# Copy icon to a path with NO special/unicode characters so Windows loads it reliably
$iconDir  = Join-Path $env:APPDATA 'oXben'
$iconPath = Join-Path $iconDir 'icon.ico'
if (-not (Test-Path $iconDir)) { New-Item -ItemType Directory -Path $iconDir | Out-Null }

if (Test-Path $srcIcon) {
    Copy-Item -Path $srcIcon -Destination $iconPath -Force
    Write-Host "[OK] Ikon kopyalandi: $iconPath"
} else {
    Write-Host "[UYARI] icon.ico bulunamadi, ikonsuz kisayol olusturuluyor."
    $iconPath = $null
}

# Find pythonw.exe next to python.exe
try {
    $pythonExe = (Get-Command python.exe -ErrorAction Stop).Source
} catch {
    Write-Error "python.exe PATH'te bulunamadi. Python'un PATH'e ekli oldugunu dogrulayin."
    exit 1
}
$pythonwExe  = $pythonExe -replace 'python\.exe$','pythonw.exe'
if (-not (Test-Path $pythonwExe)) { $pythonwExe = $pythonExe }

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcut)
$sc.TargetPath      = $pythonwExe
$sc.Arguments       = "`"$voiceTyper`""
$sc.WorkingDirectory = $ScriptDir
if ($iconPath) { $sc.IconLocation = "$iconPath,0" }
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
