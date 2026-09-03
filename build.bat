@echo off
chcp 65001 >nul
setlocal

echo ================================================
echo    RemzonaDownloader - Сборка и подпись
echo ================================================
echo.

:: ---------- НАСТРОЙКИ ----------
set APP_NAME=RemzonaDownloader
set ICON=logo.ico
set CERT_FILE=mycert.pfx
set CERT_PASS=your_password_here
set TIMESTAMP_URL=http://timestamp.digicert.com
:: --------------------------------

:: Проверка наличия PyInstaller
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] PyInstaller не найден. Установи: pip install pyinstaller
    pause
    exit /b 1
)

:: Очистка старых сборок
echo [1/3] Очистка старых файлов...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %APP_NAME%.spec del /q %APP_NAME%.spec

:: Сборка
echo [2/3] Сборка exe...
pyinstaller --onefile --windowed --clean ^
  --name=%APP_NAME% ^
  --icon=%ICON% ^
  --add-data "logo.png;." ^
  --add-data "logo.ico;." ^
  --manifest filedownloader.manifest ^
  run.py

if errorlevel 1 (
    echo [ОШИБКА] Сборка не удалась.
    pause
    exit /b 1
)

echo.
echo Сборка завершена: dist\%APP_NAME%.exe
echo.

:: Подпись (если есть сертификат)
if not exist "%CERT_FILE%" (
    echo [3/3] Файл сертификата %CERT_FILE% не найден.
    echo Подпись пропущена.
    goto end
)

where signtool >nul 2>&1
if errorlevel 1 (
    echo [3/3] signtool не найден.
    echo Установи Windows SDK или добавь signtool в PATH.
    goto end
)

echo [3/3] Подписываем exe...
signtool sign /f "%CERT_FILE%" /p "%CERT_PASS%" /tr %TIMESTAMP_URL% /td sha256 /fd sha256 "dist\%APP_NAME%.exe"

if errorlevel 1 (
    echo [ОШИБКА] Подпись не удалась. Проверь сертификат и пароль.
) else (
    echo Подпись успешно применена.
)

:end
echo.
echo ================================================
echo Готово. Файл: dist\%APP_NAME%.exe
echo ================================================
pause