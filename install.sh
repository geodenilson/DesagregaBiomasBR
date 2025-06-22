#!/bin/bash
# -*- coding: utf-8 -*-
# Instalador DesagregaBiomasBR para Linux/macOS

set -e  # Para em caso de erro

echo "==============================================="
echo "  Instalador DesagregaBiomasBR para Linux/macOS"
echo "==============================================="
echo

# Verifica se Python está disponível
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python não encontrado!"
        echo "   Instale Python e tente novamente."
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "🐍 Usando Python: $PYTHON_CMD"

# Compila recursos
echo "🔨 Compilando recursos..."
if ! $PYTHON_CMD compile_resources.py; then
    echo "❌ Erro ao compilar recursos!"
    exit 1
fi

# Define diretório de plugins do QGIS baseado no OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    QGIS_PLUGINS_DIR="$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins"
else
    # Linux
    QGIS_PLUGINS_DIR="$HOME/.local/share/QGIS/QGIS3/profiles/default/python/plugins"
fi

# Verifica se o diretório existe, cria se necessário
if [ ! -d "$QGIS_PLUGINS_DIR" ]; then
    echo "📁 Criando diretório de plugins..."
    mkdir -p "$QGIS_PLUGINS_DIR"
fi

# Define diretório do plugin
PLUGIN_DIR="$QGIS_PLUGINS_DIR/DesagregaBiomasBR"

# Remove instalação anterior se existir
if [ -d "$PLUGIN_DIR" ]; then
    echo "🗑️  Removendo instalação anterior..."
    rm -rf "$PLUGIN_DIR"
fi

# Cria diretório do plugin
echo "📁 Criando diretório do plugin..."
mkdir -p "$PLUGIN_DIR"

# Lista de arquivos para copiar
FILES=(
    "__init__.py"
    "metadata.txt" 
    "plugin_main.py"
    "dialog.py"
    "resources.py"
    "resources.qrc"
    "compile_resources.py"
    "validate_plugin.py"
    "README.md"
)

# Copia arquivos
echo "📋 Copiando arquivos..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$PLUGIN_DIR/"
        echo "   ✅ $file"
    else
        echo "   ⚠️  $file não encontrado"
    fi
done

# Copia diretório de ícones
if [ -d "icones" ]; then
    echo "📋 Copiando ícones..."
    cp -r "icones" "$PLUGIN_DIR/"
    echo "   ✅ icones/"
else
    echo "   ⚠️  Diretório icones não encontrado"
fi

# Define permissões
echo "🔐 Definindo permissões..."
chmod -R 755 "$PLUGIN_DIR"

# Valida instalação
echo "🔍 Validando instalação..."
cd "$PLUGIN_DIR"
VALIDATION_RESULT=0
if ! $PYTHON_CMD validate_plugin.py; then
    VALIDATION_RESULT=1
fi

echo
echo "==============================================="
if [ $VALIDATION_RESULT -eq 0 ]; then
    echo "✅ Plugin instalado com sucesso!"
    echo
    echo "📍 Localização: $PLUGIN_DIR"
    echo
    echo "🎯 Próximos passos:"
    echo "   1. Abra o QGIS"
    echo "   2. Vá em Plugins > Gerenciar e Instalar Plugins"
    echo "   3. Na aba 'Instalados', procure por 'DesagregaBiomasBR'"
    echo "   4. Marque a caixa para ativar o plugin"
else
    echo "❌ Plugin instalado com avisos/erros!"
    echo "   Verifique a saída da validação acima."
fi
echo "==============================================="

echo
echo "📚 Para mais informações, consulte o README.md"
echo "🌐 GitHub: https://github.com/seu-usuario/DesagregaBiomasBR"
echo 