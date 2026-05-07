param([string]$ScriptDir)

$desktop     = [Environment]::GetFolderPath('Desktop')
$shortcut    = Join-Path $desktop 'oXben - SpeechXText.lnk'
$voiceTyper  = Join-Path $ScriptDir 'voice_typer.py'
$iconPath    = Join-Path $ScriptDir 'icon.ico'

# Find pythonw.exe next to python.exe
$pythonExe   = (Get-Command python.exe -ErrorAction Stop).Source
$pythonwExe  = $pythonExe -replace 'python\.exe$','pythonw.exe'
if (-not (Test-Path $pythonwExe)) { $pythonwExe = $pythonExe }

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcut)
$sc.TargetPath      = $pythonwExe
$sc.Arguments       = "`"$voiceTyper`""
$sc.WorkingDirectory = $ScriptDir
$sc.IconLocation    = $iconPath
$sc.Description     = 'oXben - SpeechXText — Real-Time Turkish Dictation'
$sc.Save()

Write-Host "[OK] Kisayol olusturuldu: $shortcut"
