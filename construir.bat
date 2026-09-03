@echo off
setlocal enabledelayedexpansion
title RenombradorPDF - construir distribuible
cd /d "%~dp0"

set "VPY=%~dp0venv\Scripts\python.exe"
set "TESSDIR=C:\Program Files\Tesseract-OCR"
set "SALIDA=%~dp0dist\RenombradorPDF-Experimental"
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

echo ==========================================================
echo   1/4  Compilando con PyInstaller
echo ==========================================================
if not exist "%VPY%" (
  echo [X] No se encontro venv\Scripts\python.exe
  pause & exit /b 1
)
"%VPY%" -m PyInstaller --noconfirm RenombradorPDF-Experimental.spec
if errorlevel 1 (echo [X] Fallo la compilacion. & pause & exit /b 1)

echo.
echo ==========================================================
echo   2/4  Copiando la configuracion junto al ejecutable
echo ==========================================================
if not exist "%SALIDA%\src" mkdir "%SALIDA%\src"
copy /y "src\config.json" "%SALIDA%\src\config.json" >nul
echo     config.json copiado.

echo.
echo ==========================================================
echo   3/4  Empaquetando Tesseract OCR
echo ==========================================================
if not exist "%TESSDIR%\tesseract.exe" (
  echo [!] No se encontro Tesseract en "%TESSDIR%".
  echo     Instalalo desde https://github.com/UB-Mannheim/tesseract/wiki
  echo     o edita la variable TESSDIR al inicio de este archivo.
  echo     El programa funcionara igual, pero sin OCR para PDFs escaneados.
  goto instalador
)

if not exist "%SALIDA%\tesseract" mkdir "%SALIDA%\tesseract"
rem  Ejecutable y librerias, sin arrastrar todos los idiomas
xcopy "%TESSDIR%\*.exe" "%SALIDA%\tesseract\" /y /q >nul
xcopy "%TESSDIR%\*.dll" "%SALIDA%\tesseract\" /y /q >nul
if exist "%TESSDIR%\doc" xcopy "%TESSDIR%\doc" "%SALIDA%\tesseract\doc\" /e /i /y /q >nul

if not exist "%SALIDA%\tesseract\tessdata" mkdir "%SALIDA%\tesseract\tessdata"
for %%L in (spa eng osd) do (
  if exist "%TESSDIR%\tessdata\%%L.traineddata" (
    copy /y "%TESSDIR%\tessdata\%%L.traineddata" "%SALIDA%\tesseract\tessdata\" >nul
    echo     idioma %%L copiado.
  ) else (
    echo     [!] falta %%L.traineddata
  )
)
if exist "%TESSDIR%\tessdata\configs" xcopy "%TESSDIR%\tessdata\configs" "%SALIDA%\tesseract\tessdata\configs\" /e /i /y /q >nul
if exist "%TESSDIR%\tessdata\tessconfigs" xcopy "%TESSDIR%\tessdata\tessconfigs" "%SALIDA%\tesseract\tessdata\tessconfigs\" /e /i /y /q >nul
echo     Tesseract empaquetado en dist\...\tesseract\

:instalador
echo.
echo ==========================================================
echo   4/4  Generando el instalador con Inno Setup
echo ==========================================================
if not exist "%ISCC%" (
  echo [!] No se encontro Inno Setup en "%ISCC%".
  echo     Descargalo gratis en https://jrsoftware.org/isdl.php
  echo     Luego vuelve a ejecutar este archivo, o abre
  echo     instalador\RenombradorPDF.iss y pulsa Compilar.
  echo.
  echo     La carpeta lista para usar quedo en:
  echo     %SALIDA%
  pause & exit /b 0
)
"%ISCC%" "instalador\RenombradorPDF.iss"
if errorlevel 1 (echo [X] Fallo la generacion del instalador. & pause & exit /b 1)

echo.
echo ==========================================================
echo   Listo. El instalador quedo en instalador\salida\
echo ==========================================================
pause
endlocal
