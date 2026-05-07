@echo off
chcp 65001 > nul
echo.
echo  ==========================================
echo   Sesli Yazi - EXE Derleme Scripti
echo  ==========================================
echo.

:: Venv varsa aktif et
if exist ".venv\Scripts\activate.bat" (
    echo  [*] .venv aktif ediliyor...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo  [*] venv aktif ediliyor...
    call venv\Scripts\activate.bat
)

echo.
echo  [1/4] Gerekli kutuphaneler kontrol ediliyor...
pip install sounddevice pynput Pillow pyinstaller --quiet
if %errorlevel% neq 0 (
    echo  HATA: Kutuphaneler yuklenemedi!
    pause & exit /b 1
)
echo       Tamam.

echo.
echo  [2/4] Ikon olusturuluyor...
python create_icon.py
if %errorlevel% neq 0 (
    echo  HATA: Ikon olusturulamadi!
    pause & exit /b 1
)

echo.
echo  [3/4] EXE derleniyor (3-5 dakika surebilir)...
pyinstaller --noconfirm --clean ^
  --onedir ^
  --windowed ^
  --icon=icon.ico ^
  --name="Sesli Yazi" ^
  --add-data "icon.ico;." ^
  --hidden-import="faster_whisper" ^
  --hidden-import="ctranslate2" ^
  --hidden-import="tokenizers" ^
  --hidden-import="huggingface_hub" ^
  --hidden-import="onnxruntime" ^
  --hidden-import="av" ^
  --hidden-import="sounddevice" ^
  --hidden-import="numpy" ^
  --hidden-import="pynput.keyboard._win32" ^
  --hidden-import="pynput.mouse._win32" ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all onnxruntime ^
  --exclude-module matplotlib ^
  --exclude-module scipy ^
  --exclude-module pandas ^
  --exclude-module IPython ^
  voice_typer.py

if %errorlevel% neq 0 (
    echo.
    echo  HATA: Derleme basarisiz!
    pause & exit /b 1
)

echo.
echo  [4/4] Masaustu kisayolu olusturuluyor...
powershell -NoProfile -Command ^
  "$exe = [System.IO.Path]::GetFullPath('dist\Sesli Yazi\Sesli Yazi.exe'); ^
   $desk = [Environment]::GetFolderPath('Desktop'); ^
   $lnk = Join-Path $desk 'Sesli Yazi.lnk'; ^
   $sh = New-Object -ComObject WScript.Shell; ^
   $s = $sh.CreateShortcut($lnk); ^
   $s.TargetPath = $exe; ^
   $s.IconLocation = $exe; ^
   $s.WorkingDirectory = [System.IO.Path]::GetFullPath('dist\Sesli Yazi'); ^
   $s.Description = 'Sesli Yazi - Turkce gercek zamanli ses tanima'; ^
   $s.Save(); ^
   Write-Host ('Kisayol olusturuldu: ' + $lnk)"

echo.
echo  ==========================================
echo   TAMAMLANDI!
echo.
echo   EXE : dist\Sesli Yazi\Sesli Yazi.exe
echo   Masaustu kisayolu olusturuldu.
echo.
echo   NOT: Ilk calistirmada Whisper modeli
echo   (~150 MB) indirilecek, internet gerekli.
echo  ==========================================
echo.
pause
