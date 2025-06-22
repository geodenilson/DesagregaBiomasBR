@echo off
setlocal enabledelayedexpansion

echo ===============================================
echo   Instalador DesagregaBiomasBR para Windows
echo ===============================================
echo.

:: Verifica se Python está disponível
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado!
    echo    Instale Python e tente novamente.
    pause
    exit /b 1
)

:: Compila recursos
echo 🔨 Compilando recursos...
python compile_resources.py
if %errorlevel% neq 0 (
    echo ❌ Erro ao compilar recursos!
    pause
    exit /b 1
)

:: Define diretório de plugins do QGIS
set QGIS_PLUGINS_DIR=%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins

:: Verifica se o diretório existe
if not exist "%QGIS_PLUGINS_DIR%" (
    echo 📁 Criando diretório de plugins...
    mkdir "%QGIS_PLUGINS_DIR%"
)

:: Define diretório do plugin
set PLUGIN_DIR=%QGIS_PLUGINS_DIR%\DesagregaBiomasBR

:: Remove instalação anterior se existir
if exist "%PLUGIN_DIR%" (
    echo 🗑️  Removendo instalação anterior...
    rmdir /s /q "%PLUGIN_DIR%"
)

:: Cria diretório do plugin
echo 📁 Criando diretório do plugin...
mkdir "%PLUGIN_DIR%"

:: Lista de arquivos para copiar
set FILES=__init__.py metadata.txt plugin_main.py dialog.py resources.py resources.qrc compile_resources.py validate_plugin.py README.md

:: Copia arquivos
echo 📋 Copiando arquivos...
for %%f in (%FILES%) do (
    if exist "%%f" (
        copy "%%f" "%PLUGIN_DIR%\" >nul
        echo    ✅ %%f
    ) else (
        echo    ⚠️  %%f não encontrado
    )
)

:: Copia diretório de ícones
if exist "icones" (
    echo 📋 Copiando ícones...
    xcopy /s /i "icones" "%PLUGIN_DIR%\icones" >nul
    echo    ✅ icones/
) else (
    echo    ⚠️  Diretório icones não encontrado
)

:: Valida instalação
echo 🔍 Validando instalação...
cd "%PLUGIN_DIR%"
python validate_plugin.py
set VALIDATION_RESULT=%errorlevel%

echo.
echo ===============================================
if %VALIDATION_RESULT% equ 0 (
    echo ✅ Plugin instalado com sucesso!
    echo.
    echo 📍 Localização: %PLUGIN_DIR%
    echo.
    echo 🎯 Próximos passos:
    echo    1. Abra o QGIS
    echo    2. Vá em Plugins ^> Gerenciar e Instalar Plugins
    echo    3. Na aba 'Instalados', procure por 'DesagregaBiomasBR'
    echo    4. Marque a caixa para ativar o plugin
) else (
    echo ❌ Plugin instalado com avisos/erros!
    echo    Verifique a saída da validação acima.
)
echo ===============================================

pause 