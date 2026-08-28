@echo off
rem Gera dist\ZilsXMLInspector.exe (executavel unico, sem console).
rem
rem --collect-data xmlschema e obrigatorio: a biblioteca carrega os XSDs do
rem proprio XML Schema em tempo de execucao e sem eles o .exe falha ao abrir o
rem primeiro arquivo.
setlocal
cd /d "%~dp0"

python -m pip install --disable-pip-version-check -r requirements-dev.txt || goto :erro

python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name ZilsXMLInspector ^
  --paths src ^
  --collect-data xmlschema ^
  --hidden-import elementpath ^
  src\main.py || goto :erro

echo.
echo Pronto: dist\ZilsXMLInspector.exe
goto :fim

:erro
echo.
echo Falhou a geracao do executavel.
exit /b 1

:fim
endlocal
