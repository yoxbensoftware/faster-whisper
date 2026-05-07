@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Sesli Yazi - Kurulum
echo.
echo  ============================================
echo    Sesli Yazi - Kurulum Basliyor
echo  ============================================
echo.

:: ── 1. Python kontrol ────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python bulunamadi. winget ile otomatik yukleniyor...
    echo.
    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [HATA] winget bulunamadi.
        echo Lutfen https://www.python.org/downloads/ adresinden
        echo Python 3.11+ indirin ve "Add Python to PATH" secin.
        echo.
        pause
        exit /b 1
    )
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo [HATA] Python yuklenemedi.
        echo Lutfen https://www.python.org/downloads/ adresinden manuel indirin.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Python yuklendi. Bu pencereyi kapatip setup.bat'i tekrar calistirin.
    pause
    exit /b 0
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v bulundu.
echo.

:: ── 2. Pip guncelle ──────────────────────────────────────────────────────────
echo [1/3] pip guncelleniyor...
python -m pip install --upgrade pip
echo.

:: ── 3. Bagimliliklar ─────────────────────────────────────────────────────────
echo [2/3] Bagimliliklar yukleniyor (bu 2-5 dakika surebilir)...
echo       faster-whisper, sounddevice, numpy, pynput...
echo.
python -m pip install -r requirements_app.txt
if errorlevel 1 (
    echo.
    echo [HATA] Paket yuklemesi basarisiz. Internet baglantinizi kontrol edin.
    pause
    exit /b 1
)
echo.
echo [OK] Bagimliliklar yuklendi.
echo.

:: ── 4. Masaustu kisayolu ─────────────────────────────────────────────────────
echo [3/3] Masaustu kisayolu olusturuluyor...
set SCRIPT_DIR=%~dp0

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_make_shortcut.ps1" "%~dp0"

echo.
echo  ============================================
echo   Kurulum TAMAMLANDI!
echo.
echo   Masaustundeki "Sesli Yazi" ikonuna tiklayin.
echo   Ilk acilista model (~809 MB) indirilir.
echo   (internet hizina gore 2-5 dakika surebilir)
echo  ============================================
echo.
pause
