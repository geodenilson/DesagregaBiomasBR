# DesagregaBiomasBR

## 📋 Descrição

Plugin para QGIS que oferece um **assistente guiado** para seleção e desagregação de dados ambientais brasileiros por região ou recorte espacial. O plugin facilita o acesso e processamento de dados oficiais dos principais programas de monitoramento ambiental do Brasil.

## 🎯 Funcionalidades Principais

### 📊 **Temas Suportados**

| Tema               | Descrição                                              | Fonte              |
|--------------------|--------------------------------------------------------|--------------------|
| **PRODES**         | Mapeamento do desmatamento anual                       | INPE/TerraBrasilis |
| **DETER**          | Alertas de desmatamento em tempo real                  | INPE/TerraBrasilis |
| **TERRACLASS**     | Qualificação do uso da terra em áreas desflorestadas   | INPE/EMBRAPA       |
| **ÁREA QUEIMADA**  | Dados mensais de queimadas (produto AQ1Km)             | INPE/LASA-UFRJ     |

### 🌿 **Biomas Disponíveis**

- **PRODES**: Amazônia, Amazônia Legal, Cerrado, Caatinga, Pantanal, Pampa, Mata Atlântica
- **DETER**: Cerrado, Amazônia Legal  
- **TERRACLASS**: Amazônia, Cerrado
- **ÁREA QUEIMADA**: Amazônia, Amazônia Legal, Cerrado, Caatinga, Pantanal, Pampa, Mata Atlântica

### ✂️ **Opções de Corte Espacial**

1. **Sem limite**: Baixa o bioma completo
2. **Layer do QGIS**: Usa layer já carregada no projeto (com filtros opcionais por campo/elemento)
3. **Desenho na tela**: Desenha retângulo diretamente no canvas do QGIS
4. **Limites IBGE**: Usa shapefile oficial para corte por estados/municípios

### 📁 **Formatos de Saída**

- **Shapefile** (.shp) - Formato padrão
- **GeoPackage** (.gpkg) - Formato moderno

### 🗺️ **Sistema de Coordenadas**

- **SIRGAS 2000 (EPSG:4674)** - Sistema oficial brasileiro

## 🔧 Instalação

### Requisitos
- QGIS 3.x
- Conexão com internet (para download dos dados)

### Instalação Manual
1. Baixe ou clone este repositório
2. Copie a pasta `DesagregaBiomasBR` para o diretório de plugins do QGIS:
   - **Windows**: `C:\Users\[usuário]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Abra o QGIS e ative o plugin em `Plugins > Gerenciar e Instalar Plugins`

### Scripts de Instalação
- **Windows**: Execute `install.bat` como Administrador
- **Linux/macOS**: Execute `./install.sh`

## 🚀 Como Usar

### Interface de Assistente Guiado (3 Etapas)

#### **Etapa 1: Seleção do Tema**
1. Escolha o tema desejado (PRODES, DETER, TERRACLASS ou ÁREA QUEIMADA)
2. Selecione o bioma/região
3. Configure o limite de corte (opcional)

#### **Etapa 2: Configurações Específicas**

**PRODES:**
- Tipo: Incremental (período específico) ou Acumulado (desde início até ano final)
- Período: Selecione anos inicial e final

**DETER:**
- Período: Anos inicial e final
- Classes: Selecione classes de alertas (DESMATAMENTO_CR, DEGRADAÇÃO, etc.)

**TERRACLASS:**
- Ano: Selecione ano de referência
- Estado: Obrigatório
- Município: Opcional (para download municipal)

**ÁREA QUEIMADA:**
- Tipo: Anual (dados unidos) ou Mensal (arquivos originais)
- Período: Ano completo ou mês específico

#### **Etapa 3: Processamento Final**
1. Configure pasta de destino
2. Escolha formato de saída
3. Opções: Adicionar ao mapa e gerar metadados
4. Inicie o processamento

### 🔍 **Recursos Avançados**

#### **Sistema de Metadados Completos**
- Informações de origem dos dados
- Metodologia de cada tema
- Configurações de processamento
- URLs dos serviços utilizados
- Estatísticas do arquivo final

#### **Corte Automático por Bioma (ÁREA QUEIMADA)**
- Dados de queimada cobrem todo o Brasil
- Plugin aplica corte automático pelo bioma selecionado
- Possibilidade de corte adicional configurado pelo usuário

#### **Sistema de Abort**
- Possibilita interromper downloads longos
- Limpeza automática de arquivos temporários

#### **Interface Responsiva**
- Ajuste automático de tamanho baseado nas opções selecionadas
- Notas dinâmicas com resumo das configurações
- Sistema de validação em tempo real

## 📈 **Configurações Específicas por Tema**

### **PRODES - Dados de Desmatamento**

**Tipos de Dados:**
- **Incremental**: Desmatamento em período específico (ex: 2020-2023)
- **Acumulado**: Desmatamento desde o ano base até ano final (ex: 2000-2023)

**Anos Base por Bioma:**
- Cerrado, Pantanal, Pampa, Mata Atlântica, Caatinga: 2000
- Amazônia, Amazônia Legal: 2007

**Metodologia:**
- Imagens Landsat ou similares
- Áreas mapeadas ≥ 6,25 hectares
- Considera supressão de vegetação nativa independente do uso futuro

### **DETER - Alertas de Desmatamento**

**Período de Dados:**
- **Cerrado**: Maio/2018 até presente
- **Amazônia Legal**: Agosto/2016 até presente

**Classes de Alertas:**
- **Cerrado**: DESMATAMENTO_CR
- **Amazônia Legal**: CICATRIZ_DE_QUEIMADA, CORTE_SELETIVO, CS_DESORDENADO, CS_GEOMETRICO, DEGRADACAO, DESMATAMENTO_CR, DESMATAMENTO_VEG, MINERACAO

### **TERRACLASS - Uso da Terra**

**Objetivo:**
- Qualificar desflorestamento da Amazônia Legal e Cerrado
- Mapear uso e cobertura das terras desflorestadas

**Anos Disponíveis:**
- **Amazônia**: 2008, 2010, 2012, 2014, 2018, 2020, 2022
- **Cerrado**: 2018, 2020, 2022

**Classes Identificadas:**
- Vegetação natural (primária e secundária)
- Cultura agrícola (perene, semiperene, temporária)
- Pastagem, silvicultura, mineração
- Área urbanizada, outros usos, corpos d'água

### **ÁREA QUEIMADA - Produto AQ1Km**

**Características:**
- **Resolução**: 1 km (baixa resolução espacial)
- **Cobertura**: Diária com abordagem sinótica
- **Metodologia**: Algoritmos com bandas térmicas (4 µm) MODIS
- **Período**: Setembro/2002 até mês anterior ao atual

**Tipos de Processamento:**
- **Anual**: Une todos os meses do ano em arquivo único
- **Mensal**: Mantém arquivos mensais originais

**Limitações:**
- Não recomendado para análises locais (resolução 1 km)
- Ideal para análises regionais/nacionais

## 📂 **Estrutura de Arquivos**

```
DesagregaBiomasBR/
├── __init__.py              # Inicialização do plugin
├── plugin_main.py           # Configuração principal
├── dialog.py                # Interface e lógica principal
├── metadata.txt             # Metadados do plugin QGIS
├── README.md                # Este arquivo
├── resources.py             # Recursos compilados
├── resources.qrc           # Definição de recursos
├── estilo_terraclass.qml   # Simbologia TERRACLASS
├── install.bat             # Script instalação Windows
├── install.sh              # Script instalação Linux/macOS
├── icones/                 # Ícones da interface
│   ├── deter.png
│   ├── layers.png
│   ├── mapa.png
│   ├── prodes.png
│   └── queimadas.png
└── shapefile/              # Dados IBGE para cortes
    ├── BC250, 2023.cpg
    ├── BC250, 2023.dbf
    ├── BC250, 2023.prj
    ├── BC250, 2023.shp
    ├── BC250, 2023.shx
    └── BC250, 2023.shp.xml
```

## 🔗 **URLs dos Serviços**

### **PRODES - WFS TerraBrasilis**
- Amazônia: `https://terrabrasilis.dpi.inpe.br/geoserver/prodes-amazon-nb/*/ows`
- Cerrado: `https://terrabrasilis.dpi.inpe.br/geoserver/prodes-cerrado-nb/*/ows`
- Outros biomas: URLs específicas por bioma

### **DETER - WFS TerraBrasilis**  
- Cerrado: `https://terrabrasilis.dpi.inpe.br/geoserver/deter-cerrado-nb/deter_cerrado/ows`
- Amazônia Legal: `https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/deter_amz/ows`

### **TERRACLASS - Download Direto**
- Base: `https://www.terraclass.gov.br/helpers/terraclass_data4download_2024/`
- Estrutura: `V/{tipo}/{bioma}.{ano}.{localidade}.{geocodigo}.V.zip`

### **ÁREA QUEIMADA - Download ZIP**
- Base: `https://dataserver-coids.inpe.br/queimadas/queimadas/area_queimada/AQ1km/shp/`
- Formato: `{YYYY_MM_01}_aq1km_{v6|V6}.zip`

## ⚙️ **Configurações Técnicas**

### **Processamento de Dados**
- Download automático via WFS/HTTP
- Corte espacial usando algoritmos nativos do QGIS
- Correção automática de geometrias inválidas
- Reprojeção automática para SIRGAS 2000
- Merge de múltiplas camadas quando necessário

### **Otimizações**
- Download paginado para grandes volumes de dados
- Sistema de cache para múltiplas tentativas
- Verificação de abort durante processamentos longos
- Limpeza automática de arquivos temporários

### **Logs e Debug**
- Sistema de logs persistentes usando QgsMessageLog
- Mensagens de debug detalhadas para resolução de problemas
- Validação de geometrias e CRS
- Relatórios de estatísticas de processamento

## 🐛 **Solução de Problemas**

### **Problemas Comuns**

**Erro de conectividade:**
- Verifique conexão com internet
- URLs dos serviços podem estar temporariamente indisponíveis

**Geometrias inválidas:**
- Plugin aplica correção automática usando `native:fixgeometries`
- Se persistir, verifique dados de entrada

**CRS incompatíveis:**
- Plugin reprojeta automaticamente para EPSG:4674
- Dados de saída sempre em SIRGAS 2000

**Download interrompido:**
- Use botão "Abortar Download" para parar seguramente
- Arquivos temporários são limpos automaticamente

### **Logs de Debug**
Os logs detalhados ficam disponíveis em:
- QGIS > Exibir > Painéis > Log de Mensagens > DesagregaBiomasBR

## 📚 **Referências**

### **Fontes de Dados**
- **PRODES/DETER**: Instituto Nacional de Pesquisas Espaciais (INPE) - TerraBrasilis
- **TERRACLASS**: INPE/EMBRAPA
- **ÁREA QUEIMADA**: INPE/LASA-UFRJ
- **Limites IBGE**: Instituto Brasileiro de Geografia e Estatística

### **Metodologias**
- **AQ1Km**: LIBONATI, R. et al. Remote Sensing, v. 7, p. 15782–15803, 2015
- **PRODES**: Metodologia INPE para detecção de desmatamento
- **TERRACLASS**: Análise de séries temporais de imagens 20-10m

## 📄 **Licença**

Este plugin é desenvolvido para facilitar o acesso aos dados públicos de monitoramento ambiental brasileiro.

## 🤝 **Contribuições**

Contribuições são bem-vindas! Para melhorias ou correções:

1. Faça fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📧 **Suporte**

Para dúvidas ou problemas:
- Abra uma issue neste repositório
- Consulte os logs de debug do QGIS
- Verifique a documentação das fontes de dados originais

## 🙏 **Agradecimentos**

Agradecimentos especiais às instituições que disponibilizam dados públicos e financiaram essa pesquisa:
- **INPE** - Instituto Nacional de Pesquisas Espaciais
- **EMBRAPA** - Empresa Brasileira de Pesquisa Agropecuária  
- **IBGE** - Instituto Brasileiro de Geografia e Estatística
- **LASA-UFRJ** - Laboratório de Aplicações de Satélites Ambientais
- **FAO** - Organização das Nações Unidas para Alimentação e Agricultura

E à comunidade QGIS pelo excelente framework de desenvolvimento de plugins! 🗺️

---

**Desenvolvido para facilitar o acesso aos dados de monitoramento ambiental do Brasil** 🇧🇷 