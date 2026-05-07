@echo off
chcp 65001 >nul
echo ============================================
echo   Sesli Yazi - Kurulum
echo ============================================
echo.

:: Python kontrol
python --version >nul 2>&1
if errorlevel 1 (
    echo Python bulunamadi. Otomatik yukleniyor...
    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [HATA] winget de bulunamadi.
        echo Lutfen Microsoft Store'dan "App Installer" uygulamasini yukleyin
        echo veya https://www.python.org/downloads/ adresinden Python 3.11+ indirin.
        echo Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
        pause
        exit /b 1
    )
    echo winget ile Python 3.11 yukleniyor, lutfen bekleyin...
    winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [HATA] Python otomatik yuklenemedi.
        echo Lutfen https://www.python.org/downloads/ adresinden Python 3.11+ indirin.
        echo Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
        pause
        exit /b 1
    )
    :: PATH'i yenile
    call refreshenv >nul 2>&1
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Python yuklendi. Lutfen bu pencereyi kapatin ve setup.bat'i tekrar calistirin.
        pause
        exit /b 0
    )
    echo Python basariyla yuklendi!
)

echo [1/3] Bagimliliklar yukleniyor...
python -m pip install --upgrade pip -q
python -m pip install -r requirements_app.txt -q
if errorlevel 1 (
    echo [HATA] Paketler yuklenemedi. Internet baglantinizi kontrol edin.
    pause
    exit /b 1
)

echo [2/3] Masa ustu kisayolu olusturuluyor...
set SCRIPT_DIR=%~dp0
set SHORTCUT=%USERPROFILE%\Desktop\Sesli Yazi.lnk
set TARGET=pythonw.exe
set ARGS=%SCRIPT_DIR%voice_typer.py
set ICON=%SCRIPT_DIR%icon.ico

python -c "
import os, sys
script_dir = r'%SCRIPT_DIR%'
shortcut_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'Sesli Yazi.lnk')
icon_path = os.path.join(script_dir, 'icon.ico')
target = sys.executable.replace('python.exe', 'pythonw.exe')
if not os.path.exists(target):
    target = sys.executable
try:
    import win32com.client
    shell = win32com.client.Dispatch('WScript.Shell')
    sc = shell.CreateShortcut(shortcut_path)
    sc.TargetPath = target
    sc.Arguments = '\"' + os.path.join(script_dir, 'voice_typer.py') + '\"'
    sc.WorkingDirectory = script_dir
    if os.path.exists(icon_path):
        sc.IconLocation = icon_path
    sc.Description = 'Sesli Yazi - Gercek Zamanli Turkce Ses Yazici'
    sc.Save()
    print('Kisayol olusturuldu:', shortcut_path)
except Exception:
    # win32com yoksa powershell ile yap
    ps = '''
\$ws = New-Object -ComObject WScript.Shell
\$sc = \$ws.CreateShortcut('%USERPROFILE%\Desktop\Sesli Yazi.lnk')
\$sc.TargetPath = '''' + target + ''''
\$sc.Arguments = '''\"''' + os.path.join(script_dir, 'voice_typer.py') + '''\"'''
\$sc.WorkingDirectory = '''' + script_dir + ''''
\$sc.IconLocation = '''' + icon_path + ''''
\$sc.Save()
'''
    import subprocess
    subprocess.run(['powershell', '-Command', ps], check=False)
    print('Kisayol olusturuldu (PowerShell):', shortcut_path)
"

echo [3/3] Hazir!
echo.
echo ============================================
echo  Kurulum tamamlandi!
echo  Masa ustundeki "Sesli Yazi" ikonuna tiklayin.
echo  Ilk acilista model (~809 MB) indirilecek.
echo ============================================
echo.
pause
