# -*- coding: utf-8 -*-
"""
DesagregaBiomasBR Dialog
Interface do usuário com assistente guiado
"""

import os
import tempfile
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, pyqtSignal, QUrl, QTimer
from qgis.PyQt.QtGui import QIcon, QPixmap, QFont, QColor
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
                                 QLabel, QPushButton, QComboBox, QTextEdit, 
                                 QGroupBox, QRadioButton, QButtonGroup, 
                                 QScrollArea, QWidget, QSizePolicy, QFrame,
                                 QProgressBar, QMessageBox, QCheckBox, QSpacerItem)
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from qgis.core import (QgsProject, QgsVectorLayer, QgsWkbTypes, QgsGeometry, 
                       QgsRectangle, QgsCoordinateReferenceSystem, QgsFeature,
                       QgsPointXY, QgsApplication, QgsFeatureRequest)
from qgis.gui import QgsMapTool, QgsRubberBand, QgsMapToolEmitPoint

class DrawRectangleTool(QgsMapTool):
    """Ferramenta para desenhar retângulo no canvas"""
    rectangleDrawn = pyqtSignal(QgsRectangle)
    
    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.rubber_band = None
        self.start_point = None
        self.end_point = None
        
    def canvasPressEvent(self, event):
        self.start_point = self.toMapCoordinates(event.pos())
        if self.rubber_band:
            self.rubber_band.reset()
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        
    def canvasMoveEvent(self, event):
        if self.start_point and self.rubber_band:
            self.end_point = self.toMapCoordinates(event.pos())
            rect = QgsRectangle(self.start_point, self.end_point)
            self.rubber_band.setToGeometry(QgsGeometry.fromRect(rect), None)
            
    def canvasReleaseEvent(self, event):
        if self.start_point:
            self.end_point = self.toMapCoordinates(event.pos())
            rect = QgsRectangle(self.start_point, self.end_point)
            self.rectangleDrawn.emit(rect)
            if self.rubber_band:
                self.rubber_band.reset()
                self.rubber_band = None

class DesagregaBiomasBRDialog(QDialog):
    """Dialog principal do DesagregaBiomasBR"""

    def __init__(self):
        """Constructor."""
        super(DesagregaBiomasBRDialog, self).__init__()
        
        print("🔄 DEBUG: Inicializando nova instância DesagregaBiomasBRDialog")
        
        # Configurações da janela
        self.setWindowTitle("DesagregaBiomasBR")
        
        # Caminho base para os ícones
        self.plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(self.plugin_dir, 'icones', 'mapa.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # CORREÇÃO 1: Janela não modal para não bloquear o QGIS
        self.setModal(False)
        
        # CORREÇÃO 2: Tamanho inicial menor e responsivo
        self.setMinimumSize(500, 400)
        self.resize(600, 450)  # Tamanho inicial menor
        
        # Permitir redimensionamento
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # SEMPRE reset completo de todas as variáveis
        self.reset_all_variables()
        
        # Shapefile IBGE local para limites
        self.ibge_shapefile_name = self.get_ibge_shapefile_name()
        self.ibge_shapefile_path = os.path.join(os.path.dirname(__file__), 'shapefile', f'{self.ibge_shapefile_name}.shp')
        
        # Configurações dos temas
        self.biome_options = {
            'DETER': ['Cerrado', 'Amazônia Legal'],
            'PRODES': ['Amazônia', 'Amazônia Legal', 'Cerrado', 'Caatinga', 'Pantanal', 'Pampa', 'Mata Atlântica'],
            'TERRACLASS': ['Amazônia', 'Cerrado'],
            'ÁREA QUEIMADA': ['Amazônia', 'Amazônia Legal', 'Cerrado', 'Caatinga', 'Pantanal', 'Pampa', 'Mata Atlântica']
        }
        
        # Anos disponíveis por bioma para TERRACLASS
        self.terraclass_years = {
            'Amazônia': [2008, 2010, 2012, 2014, 2018, 2020, 2022],
            'Cerrado': [2018, 2020, 2022]
        }
        
        # Configurações ÁREA QUEIMADA
        # Base URL para downloads
        self.queimadas_base_url = "https://dataserver-coids.inpe.br/queimadas/queimadas/area_queimada/AQ1km/shp/"
        
        # Data de início das área queimada (setembro 2002)
        self.queimadas_start_date = "2002-09-01"
        
        # Gera anos disponíveis dinamicamente (2002 até ano atual)
        import datetime
        current_year = datetime.datetime.now().year
        self.queimadas_years = list(range(2002, current_year + 1))
        
        # Gera meses disponíveis dinamicamente (09/2002 até mês atual -1)
        self.queimadas_months = self.generate_queimadas_months()
        
        # Anos disponíveis por bioma para PRODES (incrementais)
        self.prodes_years = {
            'Cerrado': [2002,2004,2006,2007,2008,2010,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
            'Pantanal': [2004,2006,2007,2008,2010,2011,2013,2014,2016,2017,2018,2019,2020,2021,2022,2023],
            'Pampa': [2004,2006,2007,2008,2010,2011,2013,2014,2016,2017,2018,2019,2020,2021,2022,2023],
            'Mata Atlântica': [2004,2006,2008,2010,2011,2013,2014,2016,2017,2018,2019,2020,2021,2022,2023],
            'Caatinga': [2004,2006,2008,2010,2011,2013,2014,2016,2017,2018,2019,2020,2021,2022,2023],
            'Amazônia': [2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023],
            'Amazônia Legal': [2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023]
        }
        
        # Anos disponíveis para dados acumulados (incluem os anos dos prodes_base_years)
        self.prodes_years_acumulado = {
            'Cerrado': [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
            'Pantanal': [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
            'Pampa': [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
            'Mata Atlântica': [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
            'Caatinga': [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
            'Amazônia': [2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
            'Amazônia Legal': [2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024]
        }
        
        # Anos iniciais para dados acumulados por bioma
        self.prodes_base_years = {
            'Cerrado': 2000,
            'Pantanal': 2000,
            'Pampa': 2000,
            'Mata Atlântica': 2000,
            'Caatinga': 2000,
            'Amazônia': 2007,
            'Amazônia Legal': 2007
        }
        
        # Ferramenta de desenho
        self.draw_tool = None
        
        # URLs e configurações DETER
        self.deter_urls = {
            'Cerrado': 'https://terrabrasilis.dpi.inpe.br/geoserver/deter-cerrado-nb/deter_cerrado/ows',
            'Amazônia Legal': 'https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/deter_amz/ows'
        }
        
        # Classes DETER por bioma
        self.deter_classes = {
            'Cerrado': ['DESMATAMENTO_CR'],
            'Amazônia Legal': [
                'CICATRIZ_DE_QUEIMADA', 
                'CORTE_SELETIVO', 
                'CS_DESORDENADO', 
                'CS_GEOMETRICO', 
                'DEGRADACAO', 
                'DESMATAMENTO_CR', 
                'DESMATAMENTO_VEG', 
                'MINERACAO'
            ]
        }
        
        # Datas de início DETER por bioma
        self.deter_start_dates = {
            'Cerrado': '2018-05-01',      # 01/05/2018
            'Amazônia Legal': '2016-08-02'  # 02/08/2016
        }
        
        # TypeNames DETER
        self.deter_typenames = {
            'Cerrado': 'deter-cerrado-nb:deter_cerrado',
            'Amazônia Legal': 'deter-amz:deter_amz'
        }

        # Network manager
        self.network_manager = QNetworkAccessManager()
        
        # Setup da UI
        self.setupUi()
        self.update_interface()

    def setupUi(self):
        """Configuração da interface do usuário"""
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # CORREÇÃO 6: Cabeçalho reorganizado
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)
        
        # CORREÇÃO 2: Área de conteúdo sem scroll, responsiva
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Adiciona diretamente sem scroll area
        main_layout.addWidget(self.content_widget)
        
        # Quadro de notas
        self.notes_frame = self.create_notes_frame()
        main_layout.addWidget(self.notes_frame)
        
        # Botões de navegação
        buttons_layout = self.create_navigation_buttons()
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)

    def reset_all_variables(self):
        """Reset COMPLETO de todas as variáveis para garantir estado limpo"""
        print("🧹 DEBUG: Executando reset_all_variables - zerando todas as variáveis")
        
        # Estado do assistente
        self.current_step = 1
        self.max_steps = 3
        
        # Sistema de notas inteligente
        self.config_note = ""
        self.status_note = ""
        self.final_note = ""
        
        # Dados do assistente principal
        self.selected_theme = None
        self.selected_biome = None
        self.cut_option = None
        self.selected_layer = None
        self.selected_field = None
        self.selected_element = None
        self.drawn_rectangle = None
        
        # Dados IBGE
        self.ibge_layer = None
        self.ibge_field = None
        self.ibge_element = None
        self.ibge_biome_region = None
        self.ibge_state = None
        self.ibge_municipality = None
        
        # Dados temporais (PRODES)
        self.data_type = None
        self.start_year = None
        self.end_year = None
        
        # Dados temporais (DETER)
        self.deter_start_year = None
        self.deter_end_year = None
        self.deter_selected_classes = []
        
        # Dados temporais (TERRACLASS)
        self.terraclass_year = None
        self.terraclass_state = None
        self.terraclass_municipality = None
        
        # Dados WFS (para opção 3)
        self.wfs_type = None
        self.wfs_field = None
        self.wfs_element = None
        self.wfs_layer = None
        
        # Ferramentas de desenho
        self.draw_tool = None
        
        # Listas de processamento
        self.processing_layers = []
        self.urls_and_filters = {}
        
        # Sistema de rastreamento de processamentos para metadados
        self.processing_log = []
        
        # Sistema de abortar download
        self.abort_download = False  # Flag para abortar download
        self.download_in_progress = False  # Flag para controlar estado do download
        
        # Estado completamente limpo

    def add_processing_log(self, operation, details):
        """Registra um processamento realizado para incluir nos metadados"""
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            
            log_entry = {
                'timestamp': timestamp,
                'operation': operation,
                'details': details
            }
            
            self.processing_log.append(log_entry)
            
        except Exception as e:
            pass  # Falha silenciosa no log não deve interromper processamento
    
    def get_processing_summary(self):
        """Retorna resumo dos processamentos para metadados"""
        if not self.processing_log:
            return ["Nenhum processamento especial realizado (dados utilizados como baixados)"]
        
        summary = []
        for entry in self.processing_log:
            summary.append(f"{entry['timestamp']} - {entry['operation']}: {entry['details']}")
        
        return summary

    def create_header(self):
        """Cria o cabeçalho dinâmico baseado na etapa atual"""
        header_layout = QHBoxLayout()
        
        # Determina ícones e título baseado na etapa
        if self.current_step == 1:
            # Etapa 1: Seleção e Corte do Tema
            left_icon = 'layers.png'
            title_text = "SELEÇÃO DO TEMA"
            title_color = "#2e7c3f"
        elif self.current_step == 2:
            # Etapa 2: Filtros específicos por tema
            if self.selected_theme == "PRODES":
                left_icon = 'prodes.png'
                title_text = f"FILTROS PRODES - {self.selected_biome.upper()}" if self.selected_biome else "FILTROS PRODES"
                title_color = "#2e7c3f"  # MUDADO PARA VERDE
            elif self.selected_theme == "DETER":
                left_icon = 'deter.png'  # Se existir
                title_text = f"FILTROS DETER - {self.selected_biome.upper()}" if self.selected_biome else "FILTROS DETER"
                title_color = "#2e7c3f"  # VERDE IGUAL AO PRODES
            elif self.selected_theme == "TERRACLASS":
                left_icon = 'terraclass.png'  # Se existir
                title_text = f"Filtros TERRACLASS - {self.selected_biome}" if self.selected_biome else "Filtros TERRACLASS"
                title_color = "#388e3c"
            elif self.selected_theme == "ÁREA QUEIMADA":
                left_icon = 'queimadas.png'
                title_text = f"FILTROS ÁREA QUEIMADA - {self.selected_biome.upper()}" if self.selected_biome else "FILTROS ÁREA QUEIMADA"
                title_color = "#2e7c3f"
            else:
                left_icon = 'layers.png'
                title_text = "CONFIGURAÇÕES DE PROCESSAMENTO"
                title_color = "#2e7c3f"
        else:
            # Etapa 3: Processamento Final
            left_icon = 'layers.png'
            title_text = "PROCESSAMENTO FINAL"
            title_color = "#2e7c3f"
        
        # Ícone esquerda
        self.icon_label_left = QLabel()
        left_icon_path = self.plugin_dir + f'/icones/{left_icon}'
        if os.path.exists(left_icon_path):
            pixmap_left = QPixmap(left_icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            # Fallback para layers.png se o ícone específico não existir
            pixmap_left = QPixmap(self.plugin_dir + '/icones/layers.png').scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label_left.setPixmap(pixmap_left)
        
        # Título central - GUARDAR REFERÊNCIA
        self.title_label = QLabel(title_text)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"color: {title_color};")
        
        # Ícone mapa (direita) - sempre o mesmo
        self.icon_label_right = QLabel()
        pixmap_right = QPixmap(self.plugin_dir + '/icones/mapa.png').scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label_right.setPixmap(pixmap_right)
        
        header_layout.addWidget(self.icon_label_left)
        header_layout.addStretch()
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.icon_label_right)
        
        return header_layout

    def create_notes_frame(self):
        """Cria o quadro de notas"""
        notes_frame = QGroupBox("Notas")
        notes_layout = QVBoxLayout()
        
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setReadOnly(True)
        self.notes_text.setPlainText("💡 DesagregaBiomasBR é um plugin que facilita o acesso e processamento de dados dos principais sistemas de monitoramento ambiental brasileiro: 🌲 PRODES (desmatamento), 🚨 DETER (alertas), 🔥 QUEIMADAS (áreas queimadas) e 🏞️ TERRACLASS (uso da terra).")
        
        notes_layout.addWidget(self.notes_text)
        notes_frame.setLayout(notes_layout)
        
        return notes_frame

    def create_navigation_buttons(self):
        """Cria os botões de navegação"""
        buttons_layout = QHBoxLayout()
        
        self.btn_back = QPushButton("← Voltar")
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_next = QPushButton("Avançar →")
        self.btn_finish = QPushButton("Finalizar")
        self.btn_process = QPushButton("🚀 Iniciar Processamento")
        self.btn_abort = QPushButton("🛑 Abortar Download")
        
        self.btn_back.clicked.connect(self.go_back)
        self.btn_cancel.clicked.connect(self.cancel_wizard)
        self.btn_next.clicked.connect(self.go_next)
        self.btn_finish.clicked.connect(self.finish_wizard)
        self.btn_process.clicked.connect(self.start_processing)
        self.btn_abort.clicked.connect(self.abort_processing)
        
        # Estilo dos botões
        self.btn_cancel.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        self.btn_process.setStyleSheet("background-color: #2e7c3f; color: white; font-weight: bold; padding: 8px;")
        
        # Inicialmente oculto (será mostrado apenas na etapa 3)
        self.btn_process.setVisible(False)
        self.btn_abort.setVisible(False)  # Inicialmente oculto
        
        # Estilo do botão abortar
        self.btn_abort.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")
        
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_back)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_next)
        buttons_layout.addWidget(self.btn_finish)
        buttons_layout.addWidget(self.btn_process)
        buttons_layout.addWidget(self.btn_abort)
        
        return buttons_layout

    def update_interface(self):
        """Atualiza a interface baseada no passo atual"""
        # Limpa o layout de conteúdo
        self.clear_layout(self.content_layout)
        
        # Atualiza cabeçalho existente em vez de recriar
        self.update_header()
        
        # Atualiza o conteúdo baseado no passo
        if self.current_step == 1:
            self.create_step1_content()
        elif self.current_step == 2:
            self.create_step2_content()
        elif self.current_step == 3:
            self.create_step3_content()
        
        # Atualiza botões de navegação
        self.update_navigation_buttons()
        
        # CORREÇÃO 2: Ajusta o tamanho da janela dinamicamente
        self.adjustSize()
        # Força atualização do layout
        self.content_widget.updateGeometry()

    def update_header(self):
        """Atualiza apenas o conteúdo do cabeçalho existente"""
        if not hasattr(self, 'icon_label_left') or not hasattr(self, 'icon_label_right'):
            return
            
        # Determina ícones e título baseado na etapa
        if self.current_step == 1:
            # Etapa 1: Seleção e Corte do Tema
            left_icon = 'layers.png'
            title_text = "SELEÇÃO DO TEMA"
            title_color = "#2e7c3f"
        elif self.current_step == 2:
            # Etapa 2: Filtros específicos por tema
            if self.selected_theme == "PRODES":
                left_icon = 'prodes.png'
                title_text = f"FILTROS PRODES - {self.selected_biome.upper()}" if self.selected_biome else "FILTROS PRODES"
                title_color = "#2e7c3f"  # MUDADO PARA VERDE
            elif self.selected_theme == "DETER":
                left_icon = 'deter.png'  # Se existir
                title_text = f"FILTROS DETER - {self.selected_biome.upper()}" if self.selected_biome else "FILTROS DETER"
                title_color = "#2e7c3f"  # VERDE IGUAL AO PRODES
            elif self.selected_theme == "TERRACLASS":
                left_icon = 'terraclass.png'  # Se existir
                title_text = f"Filtros TERRACLASS - {self.selected_biome}" if self.selected_biome else "Filtros TERRACLASS"
                title_color = "#388e3c"
            elif self.selected_theme == "ÁREA QUEIMADA":
                left_icon = 'queimadas.png'
                title_text = f"FILTROS ÁREA QUEIMADA - {self.selected_biome.upper()}" if self.selected_biome else "FILTROS ÁREA QUEIMADA"
                title_color = "#2e7c3f"
            else:
                left_icon = 'layers.png'
                title_text = "CONFIGURAÇÕES DE PROCESSAMENTO"
                title_color = "#2e7c3f"
        else:
            # Etapa 3: Processamento Final
            left_icon = 'layers.png'
            title_text = "PROCESSAMENTO FINAL"
            title_color = "#2e7c3f"
        
        # Atualiza ícone esquerda
        left_icon_path = self.plugin_dir + f'/icones/{left_icon}'
        if os.path.exists(left_icon_path):
            pixmap_left = QPixmap(left_icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            # Fallback para layers.png se o ícone específico não existir
            pixmap_left = QPixmap(self.plugin_dir + '/icones/layers.png').scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label_left.setPixmap(pixmap_left)
        
        # Atualiza título se existe
        if hasattr(self, 'title_label'):
            self.title_label.setText(title_text)
            self.title_label.setStyleSheet(f"color: {title_color}; font-weight: bold; font-size: 14px;")
        
        # Ícone da direita sempre o mesmo (mapa)
        pixmap_right = QPixmap(self.plugin_dir + '/icones/mapa.png').scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label_right.setPixmap(pixmap_right)

    def clear_layout(self, layout):
        """Limpa todos os widgets de um layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def create_step1_content(self):
        """Cria o conteúdo da primeira etapa - Interface Responsiva"""
        
        # SEMPRE VISÍVEL: Seleção do Tema
        theme_group = QGroupBox("Seleção do Tema")
        theme_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["", "PRODES", "DETER", "TERRACLASS", "ÁREA QUEIMADA"])
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed_responsive)
        
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        self.content_layout.addWidget(theme_group)
        
        # APARECE APÓS TEMA: Seleção do bioma/região
        self.biome_group = QGroupBox("Bioma/Região")
        biome_layout = QVBoxLayout()
        
        self.biome_combo = QComboBox()
        self.biome_combo.currentTextChanged.connect(self.on_biome_changed_responsive)
        
        biome_layout.addWidget(self.biome_combo)
        self.biome_group.setLayout(biome_layout)
        self.content_layout.addWidget(self.biome_group)
        
        # APARECE APÓS BIOMA: Limite de corte (opcional)
        self.cut_group = QGroupBox("Limite de corte (opcional)")
        cut_layout = QVBoxLayout()
        
        # Opções de corte
        self.cut_button_group = QButtonGroup()
        
        self.radio_no_cut = QRadioButton("Sem limite de corte (todo o bioma/região)")
        self.radio_loaded_layer = QRadioButton("Usar layer já carregado no QGIS")
        self.radio_draw = QRadioButton("Desenhar na tela")
        self.radio_ibge = QRadioButton(f"Limites IBGE ({self.ibge_shapefile_name})")
        
        self.cut_button_group.addButton(self.radio_no_cut, 0)
        self.cut_button_group.addButton(self.radio_loaded_layer, 1)
        self.cut_button_group.addButton(self.radio_draw, 2)
        self.cut_button_group.addButton(self.radio_ibge, 3)
        
        self.radio_no_cut.setChecked(True)
        
        cut_layout.addWidget(self.radio_no_cut)
        cut_layout.addWidget(self.radio_loaded_layer)
        cut_layout.addWidget(self.radio_draw)
        cut_layout.addWidget(self.radio_ibge)
        
        # Conecta sinais
        self.cut_button_group.buttonClicked.connect(self.on_cut_option_changed_responsive)
        
        self.cut_group.setLayout(cut_layout)
        self.content_layout.addWidget(self.cut_group)
        
        # Área para configurações específicas de cada opção
        self.specific_config_widget = QWidget()
        self.specific_config_layout = QVBoxLayout(self.specific_config_widget)
        self.content_layout.addWidget(self.specific_config_widget)
        
        # ESTADO INICIAL: Apenas tema visível
        self.biome_group.setVisible(False)
        self.cut_group.setVisible(False)
        self.specific_config_widget.setVisible(False)
        
        # Restaura seleções anteriores se existirem (com lógica responsiva)
        if self.selected_theme:
            self.theme_combo.setCurrentText(self.selected_theme)
            # Trigger responsivo será chamado automaticamente
        
        # Interface começa compacta
        self.force_resize_minimal()

    def create_step2_content(self):
        """Cria o conteúdo da segunda etapa baseado no tema selecionado"""
        if self.selected_theme == "PRODES":
            self.create_prodes_step2_content()
        elif self.selected_theme == "DETER":
            self.create_deter_step2_content()
        elif self.selected_theme == "TERRACLASS":
            self.create_terraclass_step2_content()
        elif self.selected_theme == "ÁREA QUEIMADA":
            self.create_queimadas_step2_content()
        else:
            # Fallback genérico
            step_title = QLabel("ETAPA 2 - CONFIGURAÇÕES DE PROCESSAMENTO")
            step_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #2e7c3f;")
            self.content_layout.addWidget(step_title)
            
            info_label = QLabel("Selecione um tema na etapa anterior para continuar.")
            self.content_layout.addWidget(info_label)

    def create_step3_content(self):
        """Cria o conteúdo da terceira etapa - Processamento Final"""
        
        # URLs dos serviços PRODES por bioma
        self.prodes_urls = {
            'Pantanal': {
                'accumulated': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-pantanal-nb/accumulated_deforestation_2000/ows',
                'yearly': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-pantanal-nb/yearly_deforestation/ows'
            },
            'Amazônia': {
                'accumulated': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-amazon-nb/accumulated_deforestation_2007_biome/ows',
                'yearly': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-amazon-nb/yearly_deforestation_biome/ows'
            },
            'Cerrado': {
                'accumulated': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-cerrado-nb/accumulated_deforestation_2000/ows',
                'yearly': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-cerrado-nb/yearly_deforestation/ows'
            },
            'Pampa': {
                'accumulated': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-pampa-nb/accumulated_deforestation_2000/ows',
                'yearly': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-pampa-nb/yearly_deforestation/ows'
            },
            'Caatinga': {
                'accumulated': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-caatinga-nb/accumulated_deforestation_2000/ows',
                'yearly': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-caatinga-nb/yearly_deforestation/ows'
            },
            'Mata Atlântica': {
                'accumulated': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-mata-atlantica-nb/accumulated_deforestation_2000/ows',
                'yearly': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-mata-atlantica-nb/yearly_deforestation/ows'
            },
            'Amazônia Legal': {
                'accumulated': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-legal-amz/accumulated_deforestation_2007/ows',
                'yearly': 'https://terrabrasilis.dpi.inpe.br/geoserver/prodes-legal-amz/yearly_deforestation/ows'
            }
        }
        
        # Configurações de Salvamento
        save_group = QGroupBox("📁 Configurações de Salvamento")
        save_layout = QVBoxLayout()
        
        # Pasta de destino
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Pasta de destino:")
        self.dest_path_edit = QTextEdit()
        self.dest_path_edit.setMaximumHeight(25)
        self.dest_path_edit.setText("")  # Deixa em branco para usuário configurar
        self.browse_button = QPushButton("📂 Procurar...")
        self.browse_button.clicked.connect(self.browse_destination_folder)
        
        dest_layout.addWidget(dest_label)
        dest_layout.addWidget(self.dest_path_edit)
        dest_layout.addWidget(self.browse_button)
        
        # Formato de saída
        format_layout = QHBoxLayout()
        format_label = QLabel("Formato de saída:")
        
        self.format_button_group = QButtonGroup()
        self.radio_shapefile = QRadioButton("Shapefile (.shp)")
        self.radio_geopackage = QRadioButton("GeoPackage (.gpkg)")
        self.radio_shapefile.setChecked(True)  # Padrão Shapefile
        
        self.format_button_group.addButton(self.radio_shapefile, 0)
        self.format_button_group.addButton(self.radio_geopackage, 1)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.radio_shapefile)
        format_layout.addWidget(self.radio_geopackage)
        format_layout.addStretch()
        
        # Opções
        options_label = QLabel("Opções:")
        self.checkbox_add_to_map = QCheckBox("Adicionar automaticamente ao mapa")
        self.checkbox_add_to_map.setChecked(True)
        self.checkbox_generate_metadata = QCheckBox("Gerar arquivo de metadados (.txt)")
        self.checkbox_generate_metadata.setChecked(True)
        
        save_layout.addLayout(dest_layout)
        save_layout.addLayout(format_layout)
        save_layout.addWidget(options_label)
        save_layout.addWidget(self.checkbox_add_to_map)
        save_layout.addWidget(self.checkbox_generate_metadata)
        
        save_group.setLayout(save_layout)
        self.content_layout.addWidget(save_group)
        
        # Status do Processamento
        status_group = QGroupBox("⚡ Status do Processamento")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("💡 Configure a pasta de destino e clique em 'Iniciar Processamento'")
        self.status_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        
        # Barra de progresso sem porcentagem
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        self.progress_bar.setVisible(False)  # Inicialmente oculta
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        self.content_layout.addWidget(status_group)
        
        # Resumo das seleções nas notas
        self.update_processing_notes()
        
        # Ajustar tamanho da janela
        self.adjustSize()
        QTimer.singleShot(10, self.force_resize)

    def browse_destination_folder(self):
        """Abre diálogo para escolher pasta de destino"""
        from qgis.PyQt.QtWidgets import QFileDialog
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta de destino",
            self.dest_path_edit.toPlainText(),
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.dest_path_edit.setText(folder)
            print(f"🔧 DEBUG: Pasta de destino selecionada: {folder}")

    def update_processing_notes(self):
        """Atualiza as notas com resumo LIMPO das seleções para conferência final"""
        notes_parts = []
        
        # Informações básicas
        notes_parts.append(f"📊 Tema: {self.selected_theme}")
        notes_parts.append(f"🌿 Bioma: {self.selected_biome}")
        
        # Informações específicas por tema
        if self.selected_theme == "PRODES":
            # Informações temporais PRODES
            if hasattr(self, 'data_type') and self.data_type:
                type_text = "Incremental" if self.data_type == "incremental" else "Acumulado"
                notes_parts.append(f"📈 Tipo: {type_text}")
            
            # Período temporal
            if hasattr(self, 'data_type') and self.data_type:
                if self.data_type == "incremental" and hasattr(self, 'start_year') and hasattr(self, 'end_year') and self.start_year and self.end_year:
                    notes_parts.append(f"🗓️ Período: {self.start_year} - {self.end_year}")
                elif self.data_type == "acumulado" and hasattr(self, 'end_year') and self.end_year:
                    base_year = self.prodes_base_years.get(self.selected_biome, 2000)
                    notes_parts.append(f"🗓️ Período: {base_year} - {self.end_year} (acumulado)")
                    # Para acumulado, mostra que usará 2 camadas (informação útil)
                    notes_parts.append(f"📋 Camadas: accumulated_deforestation + yearly_deforestation (até {self.end_year})")
                    
        elif self.selected_theme == "DETER":
            # Período DETER
            if hasattr(self, 'deter_start_year') and hasattr(self, 'deter_end_year') and self.deter_start_year and self.deter_end_year:
                notes_parts.append(f"🗓️ Período: {self.deter_start_year} - {self.deter_end_year}")
            
            # Classes DETER (informação resumida)
            if hasattr(self, 'deter_selected_classes') and isinstance(self.deter_selected_classes, list):
                if self.selected_biome in self.deter_classes:
                    total_available = len(self.deter_classes[self.selected_biome])
                    total_selected = len(self.deter_selected_classes)
                    
                    if total_selected == total_available:
                        notes_parts.append(f"🏷️ Classes: Todas ({total_selected}) - SEM filtro")
                    else:
                        notes_parts.append(f"🏷️ Classes: {total_selected} de {total_available} selecionadas")
                    
        elif self.selected_theme == "TERRACLASS":
            # Informações específicas TERRACLASS
            if hasattr(self, 'terraclass_year') and self.terraclass_year:
                notes_parts.append(f"🗓️ Ano: {self.terraclass_year}")
            
            if hasattr(self, 'terraclass_state') and self.terraclass_state:
                notes_parts.append(f"🏛️ Estado: {self.terraclass_state}")
            
            if hasattr(self, 'terraclass_municipality') and self.terraclass_municipality:
                notes_parts.append(f"🏘️ Município: {self.terraclass_municipality}")
                
        elif self.selected_theme == "ÁREA QUEIMADA":
            # Informações específicas ÁREA QUEIMADA
            if hasattr(self, 'queimadas_data_type') and self.queimadas_data_type:
                type_text = "Anual (dissolvido)" if self.queimadas_data_type == "anual" else "Mensal (original)"
                notes_parts.append(f"📈 Tipo: {type_text}")
            
            # Período temporal
            if hasattr(self, 'queimadas_data_type') and self.queimadas_data_type:
                if self.queimadas_data_type == "anual" and hasattr(self, 'queimadas_year') and self.queimadas_year:
                    notes_parts.append(f"🗓️ Ano: {self.queimadas_year}")
                elif self.queimadas_data_type == "mensal" and hasattr(self, 'queimadas_month') and self.queimadas_month:
                    year, month, _ = self.queimadas_month.split('_')
                    notes_parts.append(f"🗓️ Período: {month}/{year}")
        
        # Informações de limite espacial (SIMPLIFICADAS)
        if self.selected_theme in ["PRODES", "DETER", "ÁREA QUEIMADA"] and hasattr(self, 'cut_option') and self.cut_option is not None:
            if self.cut_option == 0:
                notes_parts.append("📋 Limite: Todo o bioma")
            elif self.cut_option == 1 and hasattr(self, 'selected_layer') and self.selected_layer:
                # Nome simplificado do layer
                layer_name = self.selected_layer.name()
                notes_parts.append(f"📋 Limite: {layer_name}")
            elif self.cut_option == 2:
                notes_parts.append("📋 Limite: Retângulo desenhado")
            elif self.cut_option == 3:
                # Para IBGE, mostra informação mais específica
                if hasattr(self, 'ibge_state') and self.ibge_state:
                    if hasattr(self, 'ibge_municipality') and self.ibge_municipality:
                        notes_parts.append(f"📋 Limite: IBGE - {self.ibge_state}, {self.ibge_municipality}")
                    else:
                        notes_parts.append(f"📋 Limite: IBGE - {self.ibge_state}")
                else:
                    notes_parts.append("📋 Limite: IBGE")
        
        if notes_parts:
            # USA O NOVO SISTEMA - linha de configuração contínua
            config_text = " | ".join(notes_parts)
            self.update_notes(config_text, "config")
        else:
            theme_name = self.selected_theme if self.selected_theme else "dados"
            self.update_notes(f"💡 Processamento {theme_name} pronto para iniciar!", "config")

    def start_processing(self):
        """Inicia o processamento dos dados (PRODES ou DETER)"""
        print(f"🚀 DEBUG: Iniciando processamento {self.selected_theme}")
        print(f"🔧 DEBUG: Tema={self.selected_theme}, Bioma={self.selected_biome}")
        
        # Validações básicas
        if not self.selected_theme or not self.selected_biome:
            self.update_notes("❌ ERRO: Tema e bioma devem estar selecionados!")
            return
        
        # Validações específicas por tema
        if self.selected_theme == "PRODES":
            print(f"🔧 DEBUG: Tipo={getattr(self, 'data_type', None)}, Baseado na coluna 'year'")
            print(f"🔧 DEBUG: Anos={getattr(self, 'start_year', None)}-{getattr(self, 'end_year', None)}")
            
            if not hasattr(self, 'data_type') or not self.data_type:
                self.update_notes("❌ ERRO: Tipo de dados PRODES não foi configurado!")
                return
            
            if not hasattr(self, 'end_year') or not self.end_year:
                self.update_notes("❌ ERRO: Período temporal PRODES não foi configurado!")
                return
            
            # Verifica se bioma tem URLs disponíveis para PRODES
            if self.selected_biome not in self.prodes_urls:
                self.update_notes(f"❌ ERRO: URLs PRODES não disponíveis para {self.selected_biome}!")
                return
                
        elif self.selected_theme == "DETER":
            print(f"🔧 DEBUG: Anos DETER={getattr(self, 'deter_start_year', None)}-{getattr(self, 'deter_end_year', None)}")
            print(f"🔧 DEBUG: Classes selecionadas={getattr(self, 'deter_selected_classes', [])}")
            
            if not hasattr(self, 'deter_start_year') or not self.deter_start_year:
                self.update_notes("❌ ERRO: Período DETER não foi configurado!")
                return
            
            if not hasattr(self, 'deter_selected_classes') or not self.deter_selected_classes:
                self.update_notes("❌ ERRO: Classes DETER não foram selecionadas!")
                return
            
            # Verifica se bioma tem URLs disponíveis para DETER
            deter_urls = {
                'Cerrado': 'https://terrabrasilis.dpi.inpe.br/geoserver/deter-cerrado-nb/deter_cerrado/ows',
                'Amazônia Legal': 'https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/deter_amz/ows'
            }
            
            if self.selected_biome not in deter_urls:
                self.update_notes(f"❌ ERRO: URLs DETER não disponíveis para {self.selected_biome}!")
                return
        
        elif self.selected_theme == "TERRACLASS":
            print(f"🔧 DEBUG: Ano TERRACLASS={getattr(self, 'terraclass_year', None)}")
            print(f"🔧 DEBUG: Estado={getattr(self, 'terraclass_state', None)}")
            print(f"🔧 DEBUG: Município={getattr(self, 'terraclass_municipality', None)}")
            
            if not hasattr(self, 'terraclass_year') or not self.terraclass_year:
                self.update_notes("❌ ERRO: Ano TERRACLASS não foi configurado!")
                return
            
            if not hasattr(self, 'terraclass_state') or not self.terraclass_state:
                self.update_notes("❌ ERRO: Estado TERRACLASS não foi configurado!")
                return
            
            # Verifica se bioma é suportado pelo TERRACLASS
            terraclass_biomes = ['Amazônia', 'Cerrado']
            if self.selected_biome not in terraclass_biomes:
                self.update_notes(f"❌ ERRO: TERRACLASS não disponível para {self.selected_biome}!")
                return
        
        elif self.selected_theme == "ÁREA QUEIMADA":
            print(f"🔧 DEBUG: Tipo ÁREA QUEIMADA={getattr(self, 'queimadas_data_type', None)}")
            print(f"🔧 DEBUG: Período={getattr(self, 'queimadas_year', None)} ou {getattr(self, 'queimadas_month', None)}")
            
            if not hasattr(self, 'queimadas_data_type') or not self.queimadas_data_type:
                self.update_notes("❌ ERRO: Tipo de dados ÁREA QUEIMADA não foi configurado!")
                return
            
            if self.queimadas_data_type == "anual":
                if not hasattr(self, 'queimadas_year') or not self.queimadas_year:
                    self.update_notes("❌ ERRO: Ano ÁREA QUEIMADA não foi configurado!")
                    return
            else:  # mensal
                if not hasattr(self, 'queimadas_month') or not self.queimadas_month:
                    self.update_notes("❌ ERRO: Mês ÁREA QUEIMADA não foi configurado!")
                    return
        
        else:
            self.update_notes(f"❌ ERRO: Tema {self.selected_theme} não suportado!")
            return
        
        # Valida pasta de destino
        dest_path = self.dest_path_edit.toPlainText().strip()
        if not dest_path:
            self.update_notes("❌ ERRO: Selecione uma pasta de destino!")
            return
        
        # Mostra barra de progresso e ativa modo download
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"🔄 Processando dados {self.selected_theme}...")
        self.start_download_mode()  # Ativa modo download com botão abortar
        
        # Inicia processamento baseado no tema
        if self.selected_theme == "PRODES":
            QTimer.singleShot(100, self.process_prodes_data)
        elif self.selected_theme == "DETER":
            QTimer.singleShot(100, self.process_deter_data)
        elif self.selected_theme == "TERRACLASS":
            QTimer.singleShot(100, self.process_terraclass_data)
        elif self.selected_theme == "ÁREA QUEIMADA":
            QTimer.singleShot(100, self.process_queimadas_data)
        else:
            self.update_notes(f"❌ ERRO: Processamento para {self.selected_theme} não implementado!")
            self.end_download_mode(success=False)

    def process_prodes_data(self):
        """Processa os dados PRODES conforme configurações - VERSÃO REAL"""
        try:
            print(f"🚀 DEBUG: === INICIANDO PROCESSAMENTO REAL PRODES ===")
            
            # NOVO: Reseta log de processamentos para nova operação
            self.processing_log = []
            
            # Gera nome do arquivo baseado nas seleções
            self.output_filename = self.generate_output_filename()
            print(f"📁 DEBUG: Nome do arquivo: {self.output_filename}")
            
            # Constrói URLs e filtros CQL
            self.urls_and_filters = self.build_urls_and_filters()
            print(f"🌐 DEBUG: URLs e filtros: {self.urls_and_filters}")
            
            # Inicia processamento REAL
            self.current_step_index = 0
            self.processing_layers = []  # Para armazenar layers baixadas
            
            # Etapa 1: Conectar aos serviços PRODES
            self.real_step_connect_services()
            
        except Exception as e:
            print(f"❌ ERROR process_prodes_data: {str(e)}")
            self.status_label.setText(f"❌ Erro no processamento: {str(e)}")
            self.end_download_mode(success=False)

    def process_deter_data(self):
        """Processa os dados DETER conforme configurações"""
        try:
            print(f"🚀 DEBUG: === INICIANDO PROCESSAMENTO REAL DETER ===")
            
            # NOVO: Reseta log de processamentos para nova operação
            self.processing_log = []
            
            # Gera nome do arquivo baseado nas seleções DETER
            self.output_filename = self.generate_deter_output_filename()
            print(f"📁 DEBUG: Nome do arquivo DETER: {self.output_filename}")
            
            # Constrói URLs e filtros CQL para DETER
            self.urls_and_filters = self.build_deter_urls_and_filters()
            print(f"🌐 DEBUG: URLs e filtros DETER: {self.urls_and_filters}")
            
            # Inicia processamento REAL
            self.current_step_index = 0
            self.processing_layers = []  # Para armazenar layers baixadas
            
            # Etapa 1: Conectar aos serviços
            self.real_step_connect_services()
            
        except Exception as e:
            print(f"❌ ERROR process_deter_data: {str(e)}")
            self.status_label.setText(f"❌ Erro no processamento DETER: {str(e)}")
            self.end_download_mode(success=False)

    def real_step_connect_services(self):
        """Etapa 1: Conecta aos serviços WFS (PRODES ou DETER)"""
        try:
            self.status_label.setText(f"🔄 Conectando aos serviços {self.selected_theme}...")
            self.update_notes(f"📊 Conectando ao servidor TerraBrasilis | Bioma: {self.selected_biome} | Tema: {self.selected_theme}", "status")
            
            # Testa conectividade com os serviços
            urls = self.urls_and_filters['urls']
            all_connected = True
            
            for i, url in enumerate(urls):
                print(f"🌐 DEBUG: Testando conectividade com {url[:60]}...")
                if not self.test_wfs_connectivity(url):
                    print(f"❌ DEBUG: Falha na conectividade com URL {i+1}")
                    all_connected = False
                    break
                else:
                    print(f"✅ DEBUG: Conectividade OK com URL {i+1}")
            
            if all_connected:
                print(f"✅ DEBUG: Todas as conexões WFS estão funcionais")
                # Agenda próxima etapa
                QTimer.singleShot(1000, self.real_step_download_data)
            else:
                raise Exception(f"Falha na conectividade com serviços {self.selected_theme}")
                
        except Exception as e:
            print(f"❌ ERROR real_step_connect_services: {str(e)}")
            self.status_label.setText(f"❌ Erro na conexão: {str(e)}")
            self.progress_bar.setVisible(False)
            self.btn_process.setEnabled(True)

    def real_step_download_data(self):
        """Etapa 2: Baixa dados do servidor"""
        try:
            self.status_label.setText("📥 Baixando dados do servidor...")
            
            urls = self.urls_and_filters['urls']
            filters = self.urls_and_filters['filters']
            layer_names = self.urls_and_filters['layer_names']
            
            self.update_notes(f"📥 Baixando {len(urls)} camada(s) | {' + '.join(layer_names)}", "status")
            
            self.processing_layers = []
            
            for i, (url, filter_str, layer_name) in enumerate(zip(urls, filters, layer_names)):
                print(f"🔄 DEBUG: Baixando camada {i+1}/{len(urls)}: {layer_name}")
                
                # NOVA IMPLEMENTAÇÃO: Constrói URL simples com filtro
                if filter_str:
                    # Adiciona apenas o filtro CQL à URL base
                    download_url = f"{url}?CQL_FILTER={filter_str}"
                else:
                    # URL base sem filtro para accumulated_deforestation
                    download_url = url
                
                print(f"🌐 DEBUG: URL de download: {download_url[:100]}...")
                
                # Baixa a camada usando a nova implementação
                layer = self.download_wfs_layer(download_url, f"{layer_name}_{self.selected_biome}")
                
                if layer and layer.isValid() and layer.featureCount() > 0:
                    # CORREÇÃO DETER: Aplica memory_filter se for DETER
                    if self.selected_theme == 'DETER' and 'memory_filter' in self.urls_and_filters and self.urls_and_filters['memory_filter']:
                        memory_filter = self.urls_and_filters['memory_filter']
                        print(f"⏰ DEBUG: Aplicando filtro DETER na memória: {memory_filter}")
                        print(f"📊 DEBUG: Layer original DETER: {layer.featureCount()} feições")
                        
                        # Lista campos disponíveis para debug
                        field_names = [field.name() for field in layer.fields()]
                        print(f"🔍 DEBUG: Campos disponíveis na layer: {field_names}")
                        
                        # Aplica filtro temporal/classes do DETER
                        filtered_layer = self.apply_temporal_filter(layer, memory_filter, f"{layer_name}_filtered")
                        if filtered_layer and filtered_layer.isValid():
                            original_count = layer.featureCount()
                            layer = filtered_layer
                            filtered_count = layer.featureCount()
                            print(f"✅ DEBUG: Filtro DETER aplicado: {filtered_count} feições (de {original_count} originais)")
                            
                            # Debug adicional: verifica se restaram feições após filtro
                            if filtered_count == 0:
                                print(f"⚠️ WARNING: Filtro DETER resultou em 0 feições - pode haver problema no filtro")
                                print(f"⚠️ DEBUG: Filtro aplicado: {memory_filter}")
                        else:
                            print(f"⚠️ DEBUG: Falha no filtro DETER, usando dados completos")
                    
                    self.processing_layers.append(layer)
                    print(f"✅ DEBUG: Camada {layer_name} processada: {layer.featureCount()} feições")
                else:
                    raise Exception(f"Falha ao baixar camada {layer_name}")
            
            print(f"✅ DEBUG: Todas as camadas baixadas com sucesso")
            
            # Agenda próxima etapa
            QTimer.singleShot(1000, self.real_step_apply_spatial_cut)
            
        except Exception as e:
            print(f"❌ ERROR real_step_download_data: {str(e)}")
            self.status_label.setText(f"❌ Erro no download: {str(e)}")
            self.end_download_mode(success=False)

    def download_wfs_layer(self, url, layer_name):
        """Baixa uma camada WFS com paginação automática - NOVA ESTRATÉGIA SEPARADA"""
        try:
            print(f"🔄 DEBUG: Baixando dados WFS com paginação: {layer_name}")
            print(f"🔄 DEBUG: NOVA ESTRATÉGIA - Filtros espaciais e temporais separados")
            
            # Extrai typename da URL base
            typename = self.extract_typename_from_url(url, layer_name)
            if not typename:
                print(f"❌ DEBUG: Não foi possível extrair typename")
                return None
            
            # Separa URL base dos parâmetros
            base_url = url.split('?')[0]
            
            # NOVA ESTRATÉGIA: Extrai filtro CQL mas NÃO usa junto com BBOX
            original_cql_filter = None
            if 'CQL_FILTER=' in url:
                original_cql_filter = url.split('CQL_FILTER=')[1].split('&')[0]
                original_cql_filter = original_cql_filter.replace('%20', ' ').replace('%27', "'")
                print(f"🔍 DEBUG: Filtro temporal extraído (aplicado depois): {original_cql_filter}")
            # CORREÇÃO: Verifica cut_option ANTES de tentar extrair BBOX
            bbox_filter = None
            has_spatial_cut = False
            
            if hasattr(self, 'cut_option') and self.cut_option is not None and self.cut_option != 0:
                print(f"🗺️ DEBUG: Usuário selecionou corte espacial (cut_option={self.cut_option})")
                bbox_filter = self.get_cut_geometry_bbox()
                has_spatial_cut = bbox_filter is not None
                
                if has_spatial_cut:
                    print(f"✅ DEBUG: BBOX extraído: {bbox_filter}")
                else:
                    print(f"⚠️ DEBUG: BBOX não pôde ser extraído - corte espacial solicitado mas falhou")
            else:
                print(f"🌍 DEBUG: Usuário selecionou BIOMA TODO (cut_option={getattr(self, 'cut_option', 'None')})")
                print(f"🌍 DEBUG: Nenhum BBOX necessário - baixando bioma completo")
            
            
            # Configuração de paginação
            page_size = 50000  # Tamanho de cada página
            start_index = 0
            all_temp_files = []
            total_features = 0
            
            if has_spatial_cut:
                print(f"🗺️ DEBUG: ESTRATÉGIA ESPACIAL: Download com BBOX apenas")
                print(f"🗺️ DEBUG: BBOX: {bbox_filter}")
                print(f"📊 DEBUG: Iniciando download paginado COM BBOX (páginas de {page_size} feições)")
            else:
                print(f"🌍 DEBUG: ESTRATÉGIA GLOBAL: Download sem filtros")
                print(f"📊 DEBUG: Iniciando download paginado SEM FILTROS (páginas de {page_size} feições)")
            
            import requests
            import tempfile
            temp_dir = tempfile.gettempdir()
            
            # Loop de paginação
            page_number = 1
            while True:
                # VERIFICAÇÃO DE ABORT: Para interromper download se solicitado
                if self.check_abort_signal():
                    print(f"🛑 DEBUG: Download abortado pelo usuário na página {page_number}")
                    return None
                
                print(f"📄 DEBUG: Baixando página {page_number} (índice {start_index})...")
                
                # NOVA ESTRATÉGIA: Parâmetros diferentes baseados na presença de corte espacial
                if has_spatial_cut:
                    # Parâmetros APENAS com BBOX (sem CQL_FILTER)
                    params = {
                "service": "WFS",
                        "version": "2.0.0",
                "request": "GetFeature",
                "typeName": typename,
                        "outputFormat": "GML2",
                        "srsName": "EPSG:4674",
                        "count": page_size,
                        "startIndex": start_index,
                        "BBOX": bbox_filter  # APENAS filtro espacial
                    }
                else:
                    # Parâmetros SEM filtros (bioma completo)
                    params = {
                        "service": "WFS",
                        "version": "2.0.0",
                        "request": "GetFeature",
                        "typeName": typename,
                        "outputFormat": "GML2",
                        "srsName": "EPSG:4674",
                        "count": page_size,
                        "startIndex": start_index
                        # SEM BBOX e SEM CQL_FILTER
                    }
                
                # Atualiza notas com progresso
                if hasattr(self, 'update_notes'):
                    self.update_notes(f"📄 Baixando página {page_number} ({total_features} feições baixadas)", "status")
                
                # Processa eventos da interface para detectar clique no botão abortar
                QgsApplication.processEvents()
                
                # Verificação de abort adicional antes da requisição HTTP
                if self.check_abort_signal():
                    print(f"🛑 DEBUG: Download abortado antes da requisição da página {page_number}")
                    return None
                
                # Faz requisição
                response = requests.get(base_url, params=params, timeout=120)
                
                if response.status_code != 200:
                    print(f"❌ DEBUG: Erro HTTP {response.status_code} na página {page_number}")
                    if page_number == 1:
                        # Se a primeira página falha, tenta com WFS 1.0
                        print(f"🔄 DEBUG: Tentando com WFS 1.0 sem paginação...")
                        return self.download_wfs_layer_fallback(url, layer_name)
                    else:
                        break  # Para o loop se páginas subsequentes falham
                
                # Salva arquivo temporário desta página
                temp_file = os.path.join(temp_dir, f"{layer_name}_page_{page_number}_{id(self)}.gml")
                
                with open(temp_file, 'wb') as f:
                    f.write(response.content)
                
                # Verifica se a página tem dados válidos
                if len(response.content) < 1000:
                    print(f"⚠️ DEBUG: Página {page_number} muito pequena, verificando...")
                    with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(500)
                        if 'ows:ExceptionReport' in content or 'ServiceException' in content:
                            print(f"❌ DEBUG: Erro no servidor na página {page_number}")
                            break
                        elif 'numberOfFeatures="0"' in content or ('<wfs:FeatureCollection' in content and '</wfs:FeatureCollection>' in content and 'gml:featureMember' not in content):
                            print(f"✅ DEBUG: Página {page_number} vazia - fim dos dados")
                            break
                
                # Testa se a página tem feições
                test_layer = QgsVectorLayer(temp_file, f"test_page_{page_number}", "ogr")
                if test_layer.isValid():
                    page_features = test_layer.featureCount()
                    if page_features == 0:
                        print(f"✅ DEBUG: Página {page_number} sem feições - fim dos dados")
                        break
                    else:
                        print(f"✅ DEBUG: Página {page_number}: {page_features} feições")
                        all_temp_files.append(temp_file)
                        total_features += page_features
                        
                        # Se esta página tem menos feições que o tamanho da página, é a última
                        if page_features < page_size:
                            print(f"✅ DEBUG: Última página detectada ({page_features} < {page_size})")
                            break
                else:
                    print(f"❌ DEBUG: Página {page_number} inválida")
                    break
                
                # Prepara próxima página
                start_index += page_size
                page_number += 1
                
                # Atualiza interface
                QgsApplication.processEvents()
                
                # Verificação final de abort entre páginas
                if self.check_abort_signal():
                    print(f"🛑 DEBUG: Download abortado entre páginas {page_number-1} e {page_number}")
                    return None
                
                # Proteção contra loop infinito
                if page_number > 100:  # Máximo 100 páginas = 5 milhões de feições
                    print(f"⚠️ DEBUG: Limite de páginas atingido (100)")
                    break
            
            print(f"📊 DEBUG: Download concluído - {total_features} feições em {len(all_temp_files)} páginas")
            
            if not all_temp_files:
                print(f"❌ DEBUG: Nenhuma página válida baixada")
                return None
            
            # Atualiza notas finais
            if hasattr(self, 'update_notes'):
                self.update_notes(f"🔗 Combinando {len(all_temp_files)} páginas ({total_features} feições)...", "status")
            
            # Se apenas uma página, usa ela diretamente
            if len(all_temp_files) == 1:
                final_layer = QgsVectorLayer(all_temp_files[0], layer_name, "ogr")
            else:
                # Combina múltiplas páginas em uma layer única
                print(f"🔗 DEBUG: Combinando {len(all_temp_files)} páginas...")
                final_layer = self.merge_wfs_pages(all_temp_files, layer_name)
            
            if final_layer and final_layer.isValid():
                QgsApplication.processEvents()
                final_count = final_layer.featureCount()
                print(f"✅ DEBUG: Layer final carregada com {final_count} feições")
                
                # CORREÇÃO 2: Força projeção SIRGAS 2000 (EPSG:4674)
                target_crs = QgsCoordinateReferenceSystem("EPSG:4674")
                if final_layer.crs() != target_crs:
                    print(f"🗺️ DEBUG: Corrigindo projeção para SIRGAS 2000 (EPSG:4674)")
                    final_layer.setCrs(target_crs)
                
                # CORREÇÃO 3: Aplica fix geometry nos dados PRODES baixados
                print(f"🔧 DEBUG: Aplicando fix geometry nos dados PRODES baixados...")
                fixed_final_layer = self.auto_fix_geometries(final_layer, "prodes_downloaded")
                if fixed_final_layer and fixed_final_layer.isValid():
                    print(f"✅ DEBUG: Fix geometry aplicado nos dados PRODES: {fixed_final_layer.featureCount()} feições")
                    final_layer = fixed_final_layer
                    # Força projeção novamente na layer corrigida
                    if final_layer.crs() != target_crs:
                        final_layer.setCrs(target_crs)
                else:
                    print(f"⚠️ DEBUG: Fix geometry falhou nos dados PRODES, usando layer original")
                
                # NOVA ESTRATÉGIA: Aplica filtro temporal APÓS o download (se necessário)
                if original_cql_filter:
                    print(f"⏰ DEBUG: Aplicando filtro temporal nos dados baixados...")
                    if hasattr(self, 'update_notes'):
                        self.update_notes(f"⏰ Aplicando filtro temporal: {original_cql_filter}", "status")
                    
                    filtered_layer = self.apply_temporal_filter(final_layer, original_cql_filter, layer_name)
                    if filtered_layer and filtered_layer.isValid():
                        # CORREÇÃO 2: Força projeção também na layer filtrada
                        if filtered_layer.crs() != target_crs:
                            print(f"🗺️ DEBUG: Corrigindo projeção da layer filtrada para SIRGAS 2000 (EPSG:4674)")
                            filtered_layer.setCrs(target_crs)
                        
                        filtered_count = filtered_layer.featureCount()
                        print(f"✅ DEBUG: Filtro temporal aplicado: {filtered_count} feições")
                        
                        # Atualiza notas de sucesso
                        if hasattr(self, 'update_notes'):
                            self.update_notes(f"✅ WFS baixado e filtrado: {filtered_count} feições")
                        
                        return filtered_layer
                    else:
                        print(f"⚠️ DEBUG: Falha no filtro temporal, retornando dados completos")
                        # Atualiza notas de sucesso
                        if hasattr(self, 'update_notes'):
                            self.update_notes(f"✅ WFS baixado: {final_count} feições (sem filtro temporal)")
                        return final_layer
                else:
                    print(f"✅ DEBUG: Sem filtro temporal necessário")
                    # Atualiza notas de sucesso
                    if hasattr(self, 'update_notes'):
                        self.update_notes(f"✅ WFS baixado: {final_count} feições ({len(all_temp_files)} páginas)", "status")
                    return final_layer
            else:
                print(f"❌ DEBUG: Falha ao criar layer final")
                return None
                
        except Exception as e:
            print(f"❌ ERROR download_wfs_layer: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def download_wfs_layer_fallback(self, url, layer_name):
        """Fallback para WFS 1.0 sem paginação - NOVA ESTRATÉGIA SEPARADA"""
        try:
            print(f"🔄 DEBUG: Fallback - Baixando dados WFS sem paginação: {layer_name}")
            print(f"🔄 DEBUG: ESTRATÉGIA SEPARADA também no fallback")
            
            # Extrai typename da URL base
            typename = self.extract_typename_from_url(url, layer_name)
            # CORREÇÃO: Verifica cut_option ANTES de tentar extrair BBOX (fallback)
            bbox_filter = None
            has_spatial_cut = False
            
            if hasattr(self, 'cut_option') and self.cut_option is not None and self.cut_option != 0:
                print(f"🗺️ DEBUG: FALLBACK - Usuário selecionou corte espacial (cut_option={self.cut_option})")
                bbox_filter = self.get_cut_geometry_bbox()
                has_spatial_cut = bbox_filter is not None
                
                if has_spatial_cut:
                    print(f"✅ DEBUG: FALLBACK - BBOX extraído: {bbox_filter}")
                else:
                    print(f"⚠️ DEBUG: FALLBACK - BBOX não pôde ser extraído")
            else:
                print(f"🌍 DEBUG: FALLBACK - Usuário selecionou BIOMA TODO (cut_option={getattr(self, 'cut_option', 'None')})")
                print(f"🌍 DEBUG: FALLBACK - Nenhum BBOX necessário")
            base_url = url.split('?')[0]
            
            # NOVA ESTRATÉGIA: Extrai filtro CQL mas NÃO usa junto com BBOX
            original_cql_filter = None
            if 'CQL_FILTER=' in url:
                original_cql_filter = url.split('CQL_FILTER=')[1].split('&')[0]
                original_cql_filter = original_cql_filter.replace('%20', ' ').replace('%27', "'")
                print(f"🔍 DEBUG: Filtro temporal extraído (aplicado depois): {original_cql_filter}")
            
            # Verifica se há filtro espacial (BBOX)
            bbox_filter = self.get_cut_geometry_bbox()
            has_spatial_cut = bbox_filter is not None
            
            # NOVA ESTRATÉGIA: Parâmetros diferentes baseados na presença de corte espacial
            if has_spatial_cut:
                print(f"🗺️ DEBUG: FALLBACK com BBOX apenas")
                # Parâmetros APENAS com BBOX (sem CQL_FILTER)
                params = {
                    "service": "WFS",
                    "version": "1.0.0", 
                    "request": "GetFeature",
                    "typeName": typename,
                    "outputFormat": "GML2",
                    "srsName": "EPSG:4674",
                    "BBOX": bbox_filter  # APENAS filtro espacial
                }
            else:
                print(f"🌍 DEBUG: FALLBACK sem filtros")
                # Parâmetros SEM filtros
                params = {
                    "service": "WFS",
                    "version": "1.0.0", 
                    "request": "GetFeature",
                    "typeName": typename,
                    "outputFormat": "GML2",
                    "srsName": "EPSG:4674"
                    # SEM BBOX e SEM CQL_FILTER
                }
            
            print(f"🌐 DEBUG: URL base: {base_url}")
            print(f"📋 DEBUG: Parâmetros: {params}")
            
            # Faz download usando requests
            import requests
            response = requests.get(base_url, params=params, timeout=120)
            
            if response.status_code != 200:
                print(f"❌ DEBUG: Erro HTTP {response.status_code}: {response.text[:200]}")
                return None
            
            # Salva arquivo temporário
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"{layer_name}_{id(self)}.gml")
            
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            print(f"📁 DEBUG: Arquivo temporário salvo: {temp_file}")
            print(f"📊 DEBUG: Tamanho do arquivo: {len(response.content)} bytes")
            
            # Carrega como layer do QGIS
            layer = QgsVectorLayer(temp_file, layer_name, "ogr")
            
            if not layer.isValid():
                print(f"❌ DEBUG: Layer inválida: {layer.error().message()}")
                layer = QgsVectorLayer(f"{temp_file}|encoding=UTF-8", layer_name, "ogr")
                
                if not layer.isValid():
                    print(f"❌ DEBUG: Layer ainda inválida mesmo com UTF-8")
                    return None
            
            QgsApplication.processEvents()
            feature_count = layer.featureCount()
            print(f"✅ DEBUG: Layer fallback carregada com {feature_count} feições")
            
            # CORREÇÃO 2: Força projeção SIRGAS 2000 (EPSG:4674) no fallback
            target_crs = QgsCoordinateReferenceSystem("EPSG:4674")
            if layer.crs() != target_crs:
                print(f"🗺️ DEBUG: Corrigindo projeção fallback para SIRGAS 2000 (EPSG:4674)")
                layer.setCrs(target_crs)
            
            # CORREÇÃO 3: Aplica fix geometry nos dados PRODES baixados (fallback)
            print(f"🔧 DEBUG: Aplicando fix geometry nos dados PRODES baixados (fallback)...")
            fixed_layer = self.auto_fix_geometries(layer, "prodes_downloaded_fallback")
            if fixed_layer and fixed_layer.isValid():
                print(f"✅ DEBUG: Fix geometry aplicado nos dados PRODES (fallback): {fixed_layer.featureCount()} feições")
                layer = fixed_layer
                # Força projeção novamente na layer corrigida
                if layer.crs() != target_crs:
                    layer.setCrs(target_crs)
            else:
                print(f"⚠️ DEBUG: Fix geometry falhou nos dados PRODES (fallback), usando layer original")
            
            # NOVA ESTRATÉGIA: Aplica filtro temporal APÓS o download (se necessário)
            if original_cql_filter:
                print(f"⏰ DEBUG: Aplicando filtro temporal no fallback...")
                filtered_layer = self.apply_temporal_filter(layer, original_cql_filter, layer_name)
                if filtered_layer and filtered_layer.isValid():
                    # CORREÇÃO 2: Força projeção na layer filtrada do fallback
                    if filtered_layer.crs() != target_crs:
                        print(f"🗺️ DEBUG: Corrigindo projeção da layer filtrada fallback para SIRGAS 2000 (EPSG:4674)")
                        filtered_layer.setCrs(target_crs)
                    
                    filtered_count = filtered_layer.featureCount()
                    print(f"✅ DEBUG: Filtro temporal aplicado no fallback: {filtered_count} feições")
                    return filtered_layer
                else:
                    print(f"⚠️ DEBUG: Falha no filtro temporal fallback, retornando dados completos")
                    return layer
            else:
                print(f"✅ DEBUG: Fallback sem filtro temporal necessário")
                return layer
            
        except Exception as e:
            print(f"❌ ERROR download_wfs_layer_fallback: {str(e)}")
            return None

    def merge_wfs_pages(self, temp_files, layer_name):
        """Combina múltiplas páginas WFS em uma layer única"""
        try:
            print(f"🔗 DEBUG: Mesclando {len(temp_files)} páginas WFS...")
            
            # Carrega primeira página como base
            first_layer = QgsVectorLayer(temp_files[0], "first_page", "ogr")
            if not first_layer.isValid():
                print(f"❌ DEBUG: Primeira página inválida")
                return None
            
            # Cria layer em memória para combinar todas
            memory_layer = QgsVectorLayer(f"Polygon?crs={first_layer.crs().authid()}", layer_name, "memory")
            memory_provider = memory_layer.dataProvider()
            
            # Adiciona campos da primeira layer
            memory_provider.addAttributes(first_layer.fields())
            memory_layer.updateFields()
            
            total_added = 0
            
            # Adiciona feições de todas as páginas
            for i, temp_file in enumerate(temp_files):
                print(f"🔗 DEBUG: Processando página {i+1}/{len(temp_files)}...")
                
                # Atualiza interface periodicamente
                if i % 5 == 0:
                    QgsApplication.processEvents()
                    if hasattr(self, 'update_notes'):
                        self.update_notes(f"🔗 Combinando página {i+1}/{len(temp_files)} ({total_added} feições)", "status")
                
                page_layer = QgsVectorLayer(temp_file, f"page_{i+1}", "ogr")
                if page_layer.isValid():
                    features = list(page_layer.getFeatures())
                    if features:
                        memory_provider.addFeatures(features)
                        total_added += len(features)
                        print(f"✅ DEBUG: Adicionadas {len(features)} feições da página {i+1}")
                else:
                    print(f"⚠️ DEBUG: Página {i+1} inválida, pulando...")
            
            memory_layer.updateExtents()
            print(f"✅ DEBUG: Mesclagem concluída - {total_added} feições totais")
            
            return memory_layer
            
        except Exception as e:
            print(f"❌ ERROR merge_wfs_pages: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def extract_typename_from_url(self, url, layer_name):
        """Extrai o typename correto baseado na URL e nome da layer"""
        try:
            # Mapeamento de typenames corretos por bioma
            typename_mapping = {
                'Pantanal': {
                    'accumulated_deforestation': 'prodes-pantanal-nb:accumulated_deforestation_2000',
                    'yearly_deforestation': 'prodes-pantanal-nb:yearly_deforestation',
                    'deter_alerts': 'deter-cerrado-nb:deter_cerrado'  # DETER Pantanal usa mesmo endpoint do Cerrado
                },
                'Amazônia': {
                    'accumulated_deforestation': 'prodes-amazon-nb:accumulated_deforestation_2007_biome',
                    'yearly_deforestation': 'prodes-amazon-nb:yearly_deforestation_biome',
                    'deter_alerts': 'deter-amz:deter_amz'
                },
                'Cerrado': {
                    'accumulated_deforestation': 'prodes-cerrado-nb:accumulated_deforestation_2000',
                    'yearly_deforestation': 'prodes-cerrado-nb:yearly_deforestation',
                    'deter_alerts': 'deter-cerrado-nb:deter_cerrado'
                },
                'Pampa': {
                    'accumulated_deforestation': 'prodes-pampa-nb:accumulated_deforestation_2000',
                    'yearly_deforestation': 'prodes-pampa-nb:yearly_deforestation',
                    'deter_alerts': 'deter-cerrado-nb:deter_cerrado'  # DETER Pampa usa mesmo endpoint do Cerrado
                },
                'Caatinga': {
                    'accumulated_deforestation': 'prodes-caatinga-nb:accumulated_deforestation_2000',
                    'yearly_deforestation': 'prodes-caatinga-nb:yearly_deforestation',
                    'deter_alerts': 'deter-cerrado-nb:deter_cerrado'  # DETER Caatinga usa mesmo endpoint do Cerrado
                },
                'Mata Atlântica': {
                    'accumulated_deforestation': 'prodes-mata-atlantica-nb:accumulated_deforestation_2000',
                    'yearly_deforestation': 'prodes-mata-atlantica-nb:yearly_deforestation',
                    'deter_alerts': 'deter-cerrado-nb:deter_cerrado'  # DETER Mata Atlântica usa mesmo endpoint do Cerrado
                },
                'Amazônia Legal': {
                    'accumulated_deforestation': 'prodes-legal-amz:accumulated_deforestation_2007',
                    'yearly_deforestation': 'prodes-legal-amz:yearly_deforestation',
                    'deter_alerts': 'deter-amz:deter_amz'
                }
            }
            
            # Determina tipo de layer
            if 'accumulated' in layer_name.lower():
                layer_type = 'accumulated_deforestation'
            elif 'deter' in layer_name.lower() or layer_name == 'deter_alerts':
                layer_type = 'deter_alerts'
            else:
                layer_type = 'yearly_deforestation'
            
            # Busca typename correto
            biome_mapping = typename_mapping.get(self.selected_biome, {})
            typename = biome_mapping.get(layer_type)
            
            if typename:
                print(f"✅ DEBUG: Typename encontrado: {typename}")
                return typename
            else:
                print(f"❌ DEBUG: Typename não encontrado para {self.selected_biome} - {layer_type}")
                # Fallback: extrai da URL
                if '/geoserver/' in url:
                    parts = url.split('/geoserver/')[1].split('/')[0:2]
                    if len(parts) >= 2:
                        namespace = parts[0]
                        layer_part = parts[1]
                        fallback_typename = f"{namespace}:{layer_part}"
                        print(f"🔄 DEBUG: Usando fallback typename: {fallback_typename}")
                        return fallback_typename
                        
                return None
                
        except Exception as e:
            print(f"❌ ERROR extract_typename_from_url: {str(e)}")
            return None

    def get_cut_geometry_bbox(self):
        """
        Extrai bounding box da geometria de corte para otimização WFS
        NOVA VERSÃO: Usa a mesma lógica dos testes de BBOX que funcionaram
        """
        try:
            print(f"🗺️ DEBUG: === EXTRAÇÃO DE BBOX PARA WFS ===")
            print(f"🔍 DEBUG: Verificando variáveis disponíveis...")
            
            # DEBUG COMPLETO: Verifica todas as variáveis
            print(f"🔍 DEBUG: hasattr selected_layer: {hasattr(self, 'selected_layer')}")
            print(f"🔍 DEBUG: selected_layer value: {getattr(self, 'selected_layer', 'N/A')}")
            print(f"🔍 DEBUG: hasattr selected_field: {hasattr(self, 'selected_field')}")
            print(f"🔍 DEBUG: selected_field value: {getattr(self, 'selected_field', 'N/A')}")
            print(f"🔍 DEBUG: hasattr selected_element: {hasattr(self, 'selected_element')}")
            print(f"🔍 DEBUG: selected_element value: {getattr(self, 'selected_element', 'N/A')}")
            
            # ESTRATÉGIA 1: Se tem layer + campo + elemento selecionados (já testado e funcionando)
            if (hasattr(self, 'selected_layer') and self.selected_layer and 
                hasattr(self, 'selected_field') and self.selected_field and 
                hasattr(self, 'selected_element') and self.selected_element):
                
                print(f"                ✅ DEBUG: TODAS as variáveis estão disponíveis!")
                print(f"🎯 DEBUG: Usando layer específico: {self.selected_layer.name()}")
                print(f"🎯 DEBUG: Campo: {self.selected_field}, Elemento: {self.selected_element}")
                
                # CORREÇÃO: Fix geometries antes de aplicar filtro
                print(f"🔧 DEBUG: Aplicando fix geometry no layer de corte...")
                fixed_layer = self.auto_fix_geometries(self.selected_layer, "corte")
                if fixed_layer and fixed_layer.isValid():
                    print(f"✅ DEBUG: Layer com geometrias corrigidas: {fixed_layer.featureCount()} feições")
                    layer_to_filter = fixed_layer
                else:
                    print(f"⚠️ DEBUG: Fix geometry falhou, usando layer original")
                    layer_to_filter = self.selected_layer
                
                # Aplica filtro (igual ao teste que funcionou)
                from qgis.core import QgsFeatureRequest
                
                # CORREÇÃO: Testa diferentes formatos de expressão
                element_clean = str(self.selected_element).strip()
                field_clean = str(self.selected_field).strip()
                
                print(f"🔍 DEBUG: Campo limpo: '{field_clean}'")
                print(f"🔍 DEBUG: Elemento limpo: '{element_clean}'")
                
                # Testa expressões com diferentes formatos
                expressions_to_try = [
                    f'"{field_clean}" = \'{element_clean}\'',  # Formato original
                    f"{field_clean} = '{element_clean}'",      # Sem aspas duplas no campo
                    f'"{field_clean}" = "{element_clean}"',    # Aspas duplas no valor
                    f'{field_clean} = "{element_clean}"',      # Sem aspas no campo, duplas no valor
                ]
                
                filtered_layer = None
                working_expression = None
                
                for i, expression in enumerate(expressions_to_try):
                     print(f"🔍 DEBUG: Tentativa {i+1}: {expression}")
                     try:
                         request = QgsFeatureRequest().setFilterExpression(expression)
                         test_layer = layer_to_filter.materialize(request)
                         
                         if test_layer and test_layer.isValid() and test_layer.featureCount() > 0:
                             print(f"✅ DEBUG: SUCESSO na tentativa {i+1}! {test_layer.featureCount()} feições encontradas")
                             filtered_layer = test_layer
                             working_expression = expression
                             break
                         else:
                             print(f"❌ DEBUG: Tentativa {i+1} falhou - {test_layer.featureCount() if test_layer else 0} feições")
                     except Exception as e:
                         print(f"❌ DEBUG: Erro na tentativa {i+1}: {e}")
                
                print(f"🔍 DEBUG: Expressão final que funcionou: {working_expression}")
                print(f"🔍 DEBUG: Layer filtrado final: {filtered_layer.featureCount() if filtered_layer else 0} feições")
                
                # Se nenhuma expressão funcionou, lista valores reais do campo
                if not filtered_layer:
                    print(f"🔍 DEBUG: NENHUMA expressão funcionou! Listando valores reais do campo '{field_clean}':")
                    try:
                        unique_values = []
                        for feature in self.selected_layer.getFeatures():
                            value = feature[field_clean]
                            if value and value not in unique_values:
                                unique_values.append(str(value))
                                if len(unique_values) <= 10:  # Mostra só os primeiros 10
                                    print(f"   📋 Valor real: '{value}' (tipo: {type(value).__name__})")
                        
                        print(f"🔍 DEBUG: Total de valores únicos encontrados: {len(unique_values)}")
                        print(f"🔍 DEBUG: Elemento procurado: '{element_clean}' (tipo: {type(element_clean).__name__})")
                        
                        # Verifica se há match exato (case insensitive)
                        element_lower = element_clean.lower()
                        matches = [v for v in unique_values if v.lower() == element_lower]
                        if matches:
                            print(f"✅ DEBUG: Match encontrado (case insensitive): '{matches[0]}'")
                            # Tenta novamente com o valor exato encontrado
                            exact_expression = f'"{field_clean}" = \'{matches[0]}\''
                            print(f"🔍 DEBUG: Tentando com valor exato: {exact_expression}")
                            request = QgsFeatureRequest().setFilterExpression(exact_expression)
                            filtered_layer = self.selected_layer.materialize(request)
                            working_expression = exact_expression
                            
                    except Exception as e:
                        print(f"❌ DEBUG: Erro ao listar valores: {e}")
                
                print(f"🔍 DEBUG: Layer original: {self.selected_layer.featureCount()} feições")
                print(f"🔍 DEBUG: Filtered layer válido: {filtered_layer.isValid() if filtered_layer else 'None'}")
                print(f"🔍 DEBUG: Filtered layer count: {filtered_layer.featureCount() if filtered_layer else 'N/A'}")
                
                if filtered_layer and filtered_layer.isValid() and filtered_layer.featureCount() > 0:
                    extent = filtered_layer.extent()
                    print(f"✅ DEBUG: SUCESSO - {filtered_layer.featureCount()} feições filtradas")
                    print(f"📍 DEBUG: BBOX do elemento '{self.selected_element}' extraído")
                    print(f"📍 DEBUG: Extent filtrado: {extent.xMinimum():.6f},{extent.yMinimum():.6f},{extent.xMaximum():.6f},{extent.yMaximum():.6f}")
                else:
                    # FALLBACK: Se filtro falhou, usa layer completo
                    extent = self.selected_layer.extent()
                    print(f"❌ DEBUG: FILTRO FALHOU - usando layer completo")
                    print(f"❌ DEBUG: Razão: filtered_layer={filtered_layer}, valid={filtered_layer.isValid() if filtered_layer else 'N/A'}, count={filtered_layer.featureCount() if filtered_layer else 'N/A'}")
                    print(f"📍 DEBUG: Extent completo: {extent.xMinimum():.6f},{extent.yMinimum():.6f},{extent.xMaximum():.6f},{extent.yMaximum():.6f}")
                    
                    # ADICIONA mensagem específica nas Notas sobre o erro
                    current_text = self.notes_text.toPlainText()
                    self.notes_text.setPlainText(current_text + f"\n❌ FALHA NO FILTRO: Usando BBOX do layer completo")
                    self.notes_text.setPlainText(self.notes_text.toPlainText() + f"\n🔍 Expressão testada: {expression}")
                    
            # ESTRATÉGIA 2: Se tem cut_layer (fallback para outras opções)
            elif hasattr(self, 'cut_option') and self.cut_option is not None and self.cut_option != 0:
                cut_layer = self.get_cut_layer()
                if cut_layer and cut_layer.isValid():
                    extent = cut_layer.extent()
                    print(f"📊 DEBUG: Usando cut_layer com {cut_layer.featureCount()} feições")
                else:
                    print(f"❌ DEBUG: cut_layer inválido")
                    return None
                    
            # ESTRATÉGIA 3: Se tem retângulo desenhado
            elif hasattr(self, 'drawn_rectangle') and self.drawn_rectangle:
                extent = self.drawn_rectangle
                print(f"📊 DEBUG: Usando retângulo desenhado")
                
            else:
                print(f"❌ DEBUG: NENHUMA geometria de corte encontrada!")
                print(f"❌ DEBUG: Verificar se usuário fez as seleções corretas:")
                print(f"   📋 Layer carregado: {hasattr(self, 'selected_layer') and self.selected_layer}")
                print(f"   📋 Campo selecionado: {hasattr(self, 'selected_field') and self.selected_field}")
                print(f"   📋 Elemento selecionado: {hasattr(self, 'selected_element') and self.selected_element}")
                print(f"   📋 Cut option definida: {hasattr(self, 'cut_option') and self.cut_option is not None}")
                print(f"   📋 Retângulo desenhado: {hasattr(self, 'drawn_rectangle') and self.drawn_rectangle}")
                
                # Adiciona informações nas Notas sobre o que falta
                current_text = self.notes_text.toPlainText()
                self.notes_text.setPlainText(current_text + f"\n❌ SEM BBOX: Nenhuma geometria de corte encontrada")
                
                if not (hasattr(self, 'selected_layer') and self.selected_layer):
                    self.notes_text.setPlainText(self.notes_text.toPlainText() + f"\n   ❌ Falta: Selecionar layer")
                if not (hasattr(self, 'selected_field') and self.selected_field):
                    self.notes_text.setPlainText(self.notes_text.toPlainText() + f"\n   ❌ Falta: Selecionar campo")
                if not (hasattr(self, 'selected_element') and self.selected_element):
                    self.notes_text.setPlainText(self.notes_text.toPlainText() + f"\n   ❌ Falta: Selecionar elemento")
                
                return None
            
            if extent.isEmpty():
                print(f"⚠️ DEBUG: Extent vazio")
                return None
            
            # Converte para EPSG:4674 se necessário (simplificado)
            if (hasattr(self, 'selected_layer') and self.selected_layer and 
                self.selected_layer.crs() != QgsCoordinateReferenceSystem("EPSG:4674")):
                
                from qgis.core import QgsCoordinateTransform, QgsProject
                layer_crs = self.selected_layer.crs()
                target_crs = QgsCoordinateReferenceSystem("EPSG:4674")
                transform = QgsCoordinateTransform(layer_crs, target_crs, QgsProject.instance())
                extent = transform.transformBoundingBox(extent)
                print(f"🔄 DEBUG: Convertido de {layer_crs.authid()} para EPSG:4674")
            
            # Formata BBOX para WFS
            bbox_str = f"{extent.xMinimum():.6f},{extent.yMinimum():.6f},{extent.xMaximum():.6f},{extent.yMaximum():.6f},EPSG:4674"
            
            print(f"✅ DEBUG: BBOX extraído para WFS: {bbox_str}")
            
            # Adiciona à caixa de Notas também
            current_text = self.notes_text.toPlainText()
            self.notes_text.setPlainText(current_text + f"\n🌐 BBOX WFS: {bbox_str}")
            
            return bbox_str
            
        except Exception as e:
            print(f"❌ DEBUG: Erro ao extrair BBOX: {str(e)}")
            current_text = self.notes_text.toPlainText()
            self.notes_text.setPlainText(current_text + f"\n❌ ERRO BBOX WFS: {e}")
            return None

    def apply_temporal_filter(self, layer, qgis_expression, layer_name):
        """Aplica filtro usando expressões nativas do QGIS - ESTRATÉGIA SIMPLIFICADA"""
        try:
            print(f"⏰ DEBUG: Aplicando filtro QGIS: {qgis_expression}")
            print(f"📊 DEBUG: Layer original: {layer.featureCount()} feições")
            
            # Lista campos disponíveis para debug
            field_names = [field.name() for field in layer.fields()]
            print(f"🔍 DEBUG: Campos disponíveis na layer: {field_names}")
            
            # Cria layer em memória para o resultado filtrado
            memory_layer = QgsVectorLayer(f"Polygon?crs=EPSG:4674", f"{layer_name}_filtered", "memory")
            memory_provider = memory_layer.dataProvider()
            
            # Adiciona campos da layer original
            memory_provider.addAttributes(layer.fields())
            memory_layer.updateFields()
            
            # NOVA ESTRATÉGIA: Usa QgsFeatureRequest com expressão nativa do QGIS
            request = QgsFeatureRequest()
            request.setFilterExpression(qgis_expression)
            
            # Aplica filtro e copia feições filtradas
            filtered_features = []
            for feature in layer.getFeatures(request):
                filtered_features.append(feature)
            
            if filtered_features:
                memory_provider.addFeatures(filtered_features)
                memory_layer.updateExtents()
                
                filtered_count = len(filtered_features)
                total_count = layer.featureCount()
                print(f"✅ DEBUG: Filtro QGIS aplicado: {filtered_count}/{total_count} feições")
                
                return memory_layer
            else:
                print(f"⚠️ DEBUG: Nenhuma feição passou no filtro QGIS")
                return None
                
        except Exception as e:
            print(f"❌ ERROR apply_temporal_filter: {str(e)}")
            print(f"❌ Expressão problemática: {qgis_expression}")
            return layer  # Retorna layer original em caso de erro



    def real_step_apply_spatial_cut(self):
        """Etapa 3: Aplica corte espacial"""
        try:
            self.status_label.setText("✂️ Realizando corte espacial...")
            
            # CORREÇÃO 1: Verifica se realmente precisa fazer corte espacial
            # DEBUG: Mostra valor atual de cut_option
            cut_option_value = getattr(self, 'cut_option', None)
            print(f"🔧 DEBUG: cut_option atual = {cut_option_value}")
            print(f"🔧 DEBUG: type(cut_option) = {type(cut_option_value)}")
            
            # CORREÇÃO MELHORADA: Verifica se realmente precisa fazer corte espacial
            # Considera None, 0 ou atributo não existente como "sem corte"
            needs_cut = (
                hasattr(self, 'cut_option') and 
                self.cut_option is not None and 
                self.cut_option != 0
            )
            
            if not needs_cut:
                # Sem corte espacial - pula esta etapa
                self.update_notes(f"🌍 Sem recorte espacial | Usando bioma completo: {self.selected_biome}", "status")
                print(f"🌍 DEBUG: Sem corte espacial - pulando etapa")
                
                # Agenda próxima etapa diretamente
                QTimer.singleShot(1000, self.real_step_merge_layers)
                return
            
            # Se chegou aqui, precisa fazer corte espacial
            self.update_notes(f"✂️ Aplicando recorte espacial | Opção: {self.get_cut_option_name()}", "status")
            
            # Obtém layer de corte
            cut_layer = self.get_cut_layer()
            
            if not cut_layer:
                raise Exception("Falha ao obter layer de corte espacial")
            
            print(f"🔄 DEBUG: Aplicando corte espacial com {cut_layer.name()}")
            
            # CORREÇÃO 2: Aplica fixgeometries automaticamente em ambas as layers
            print(f"🔧 DEBUG: Aplicando fixgeometries nas layers...")
            
            # Fix geometries na layer de corte
            fixed_cut_layer = self.auto_fix_geometries(cut_layer, "corte")
            if not fixed_cut_layer:
                print(f"⚠️ DEBUG: Falha no fix da layer de corte, usando original")
                fixed_cut_layer = cut_layer
            
            # Aplica corte em cada layer processada
            clipped_layers = []
            
            for i, layer in enumerate(self.processing_layers):
                print(f"✂️ DEBUG: Cortando layer {i+1}/{len(self.processing_layers)}: {layer.name()}...")
                
                # Fix geometries na layer de dados
                fixed_data_layer = self.auto_fix_geometries(layer, f"dados_{i}")
                if not fixed_data_layer:
                    print(f"⚠️ DEBUG: Falha no fix da layer de dados {i}, usando original")
                    fixed_data_layer = layer
                
                # Aplica corte com layers corrigidas
                clipped_layer = self.clip_layer(fixed_data_layer, fixed_cut_layer)
                
                if clipped_layer:
                    clipped_layers.append(clipped_layer)
                    print(f"✅ DEBUG: Layer cortada: {clipped_layer.featureCount()} feições")
                else:
                    print(f"❌ DEBUG: Falha ao cortar layer {layer.name()}")
            
            if not clipped_layers:
                raise Exception("Nenhuma layer foi cortada com sucesso")
            
            self.processing_layers = clipped_layers
            
            # Agenda próxima etapa
            QTimer.singleShot(1000, self.real_step_merge_layers)
            
        except Exception as e:
            print(f"❌ ERROR real_step_apply_spatial_cut: {str(e)}")
            self.status_label.setText(f"❌ Erro no corte espacial: {str(e)}")
            self.progress_bar.setVisible(False)
            self.btn_process.setEnabled(True)

    def auto_fix_geometries(self, layer, layer_type):
        """Aplica fixgeometries automaticamente sem avisar o usuário"""
        try:
            import processing
            
            print(f"🔧 DEBUG: Aplicando fixgeometries na layer {layer_type}...")
            
            # Executa fixgeometries
            fixed_result = processing.run("native:fixgeometries", {
                'INPUT': layer,
                'OUTPUT': 'memory:'
            })
            
            fixed_layer = fixed_result['OUTPUT']
            
            if fixed_layer and fixed_layer.isValid():
                original_count = layer.featureCount()
                fixed_count = fixed_layer.featureCount()
                
                # NOVO: Registra processamento com detalhes sobre perda
                if fixed_count < original_count:
                    loss_count = original_count - fixed_count
                    loss_percent = (loss_count / original_count) * 100
                    self.add_processing_log(
                        "CORREÇÃO DE GEOMETRIAS",
                        f"{original_count} feições antes e {fixed_count} feições depois (PERDA: {loss_count} polígonos inválidos removidos - {loss_percent:.1f}%)"
                    )
                elif fixed_count > original_count:
                    gain_count = fixed_count - original_count
                    self.add_processing_log(
                        "CORREÇÃO DE GEOMETRIAS",
                        f"{original_count} feições antes e {fixed_count} feições depois (GANHO: {gain_count} polígonos corrigidos/divididos)"
                    )
                else:
                    self.add_processing_log(
                        "CORREÇÃO DE GEOMETRIAS",
                        f"{original_count} feições antes e {fixed_count} feições depois (SEM PERDA: todas as geometrias já eram válidas)"
                    )
                
                print(f"✅ DEBUG: Fixgeometries aplicado na layer {layer_type}")
                print(f"   Feições: {original_count} → {fixed_count}")
                
                # Define nome para a layer corrigida
                fixed_layer.setName(f"{layer.name()}_fixed")
                
                return fixed_layer
            else:
                print(f"⚠️ DEBUG: Fixgeometries falhou para layer {layer_type}")
                return None
                
        except Exception as e:
            print(f"⚠️ DEBUG: Erro no fixgeometries da layer {layer_type}: {str(e)}")
            return None

    def clip_layer(self, input_layer, clip_layer, log_processing=True):
        """Aplica corte espacial usando processing"""
        try:
            import processing
            
            # Verifica se as layers são válidas
            if not input_layer.isValid() or not clip_layer.isValid():
                return None
            
            # Verifica se há geometrias
            if input_layer.featureCount() == 0 or clip_layer.featureCount() == 0:
                return None
            
            # Executa algoritmo de clip
            result = processing.run("native:clip", {
                'INPUT': input_layer,
                'OVERLAY': clip_layer,
                'OUTPUT': 'memory:'
            })
            
            if not result or 'OUTPUT' not in result:
                return None
            
            clipped_layer = result['OUTPUT']
            
            if not clipped_layer or not clipped_layer.isValid():
                return None
            
            feature_count = clipped_layer.featureCount()
            original_count = input_layer.featureCount()
            
            # NOVO: Registra processamento apenas se solicitado
            if log_processing:
                if feature_count == 0:
                    self.add_processing_log(
                        "CORTE ESPACIAL",
                        f"{original_count} feições → 0 feições (área fora do polígono de corte)"
                    )
                else:
                    reduction_percent = ((original_count - feature_count) / original_count) * 100 if original_count > 0 else 0
                    self.add_processing_log(
                        "CORTE ESPACIAL",
                        f"{original_count} feições → {feature_count} feições (redução de {reduction_percent:.1f}%)"
                    )
            
            if feature_count == 0:
                # Retorna layer vazia mas válida
                clipped_layer.setName(f"{input_layer.name()}_clipped_empty")
                return clipped_layer
            
            clipped_layer.setName(f"{input_layer.name()}_clipped")
            return clipped_layer
                
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            error_msg = f"❌ ERRO clip_layer: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "DesagregaBiomasBR", Qgis.Critical)
            return None


    
    def reproject_layer(self, layer, target_crs):
        """
        Reprojeta uma layer para o CRS de destino
        """
        try:
            import processing
            
            # Parâmetros para reprojeção
            params = {
                'INPUT': layer,
                'TARGET_CRS': target_crs,
                'OUTPUT': 'memory:'
            }
            
            # Executa o algoritmo de reprojeção
            result = processing.run("native:reprojectlayer", params)
            
            if result and 'OUTPUT' in result:
                reprojected_layer = result['OUTPUT']
                
                if reprojected_layer and reprojected_layer.isValid():
                    # NOVO: Registra processamento
                    original_crs = layer.crs().authid()
                    target_crs_id = target_crs if isinstance(target_crs, str) else target_crs.authid()
                    self.add_processing_log(
                        "REPROJEÇÃO DE COORDENADAS",
                        f"{original_crs} → {target_crs_id}"
                    )
                    return reprojected_layer
                else:
                    return None
            else:
                return None
                
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            error_msg = f"❌ ERRO reproject_layer: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "DesagregaBiomasBR", Qgis.Critical)
            return None

    def real_step_merge_layers(self):
        """Etapa 4: Mescla layers se necessário (para tipo acumulado)"""
        try:
            self.status_label.setText("🔄 Mesclando dados...")
            
            if self.data_type == "acumulado" and len(self.processing_layers) > 1:
                # Para acumulado, precisa mesclar accumulated + yearly
                self.update_notes(f"🔄 Mesclando camadas | accumulated_deforestation + yearly_deforestation", "status")
                
                print(f"🔄 DEBUG: Mesclando {len(self.processing_layers)} layers para tipo acumulado")
                
                merged_layer = self.merge_layers(self.processing_layers)
                
                if merged_layer:
                    self.processing_layers = [merged_layer]
                    print(f"✅ DEBUG: Layers mescladas: {merged_layer.featureCount()} feições")
                else:
                    raise Exception("Falha ao mesclar layers")
                    
            else:
                # Para incremental, usa apenas uma layer
                self.update_notes(f"📊 Processando dados incrementais | {self.processing_layers[0].featureCount()} feições", "status")
                print(f"📊 DEBUG: Tipo incremental - usando layer única")
            
            # Agenda próxima etapa
            QTimer.singleShot(1000, self.real_step_save_file)
            
        except Exception as e:
            print(f"❌ ERROR real_step_merge_layers: {str(e)}")
            self.status_label.setText(f"❌ Erro na mesclagem: {str(e)}")
            self.end_download_mode(success=False)

    def merge_layers(self, layers):
        """Mescla múltiplas layers em uma só"""
        try:
            import processing
            
            print(f"🔄 DEBUG: Mesclando {len(layers)} layers")
            
            if len(layers) == 1:
                return layers[0]
            
            # Executa merge
            result = processing.run("native:mergevectorlayers", {
                'LAYERS': layers,
                'CRS': layers[0].crs(),
                'OUTPUT': 'memory:'
            })
            
            merged_layer = result['OUTPUT']
            
            if merged_layer and merged_layer.isValid():
                merged_layer.setName(f"PRODES_{self.selected_biome}_merged")
                
                # NOVO: Registra processamento
                total_features = sum(layer.featureCount() for layer in layers)
                merged_count = merged_layer.featureCount()
                self.add_processing_log(
                    "UNIÃO DE CAMADAS",
                    f"{len(layers)} camadas unidas → {merged_count} feições totais"
                )
                
                print(f"✅ DEBUG: Merge executado com sucesso")
                return merged_layer
            else:
                print(f"❌ DEBUG: Resultado do merge inválido")
                return None
                
        except Exception as e:
            print(f"❌ ERROR merge_layers: {str(e)}")
            return None

    def real_step_save_file(self):
        """Etapa 5: Salva arquivo no formato escolhido"""
        try:
            self.status_label.setText("💾 Salvando arquivo...")
            
            if not self.processing_layers:
                raise Exception("Nenhuma layer para salvar")
            
            final_layer = self.processing_layers[0]
            
            # Determina formato e extensão
            if self.radio_shapefile.isChecked():
                format_name = "ESRI Shapefile"
                extension = ".shp"
            else:
                format_name = "GPKG"
                extension = ".gpkg"
            
            # Monta caminho completo
            dest_path = self.dest_path_edit.toPlainText().strip()
            full_path = os.path.join(dest_path, f"{self.output_filename}{extension}")
            
            self.update_notes(f"💾 Salvando arquivo | Formato: {format_name} | Destino: {full_path}", "status")
            
            print(f"💾 DEBUG: Salvando em {full_path}")
            
            # Salva o arquivo
            success = self.save_layer_to_file(final_layer, full_path, format_name)
            
            if success:
                self.final_file_path = full_path
                print(f"✅ DEBUG: Arquivo salvo com sucesso")
                
                # Agenda próxima etapa
                QTimer.singleShot(1000, self.real_step_generate_metadata)
            else:
                raise Exception("Falha ao salvar arquivo")
                
        except Exception as e:
            print(f"❌ ERROR real_step_save_file: {str(e)}")
            self.status_label.setText(f"❌ Erro ao salvar: {str(e)}")
            self.end_download_mode(success=False)

    def save_layer_to_file(self, layer, file_path, format_name):
        """Salva layer em arquivo"""
        try:
            from qgis.core import QgsVectorFileWriter
            
            print(f"💾 DEBUG: Salvando layer {layer.name()} em {file_path}")
            
            # Cria pasta se não existir
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Configura opções de salvamento
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = format_name
            options.fileEncoding = "UTF-8"
            
            # Salva o arquivo
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                file_path,
                layer.transformContext(),
                options
            )
            
            if error[0] == QgsVectorFileWriter.NoError:
                print(f"✅ DEBUG: Arquivo salvo com sucesso")
                return True
            else:
                print(f"❌ DEBUG: Erro ao salvar: {error[1]}")
                return False
                
        except Exception as e:
            print(f"❌ ERROR save_layer_to_file: {str(e)}")
            return False

    def real_step_generate_metadata(self):
        """Etapa 6: Gera arquivo de metadados"""
        try:
            self.status_label.setText("📄 Gerando metadados...")
            
            if self.checkbox_generate_metadata.isChecked():
                self.update_notes(f"📄 Gerando metadados | Arquivo: {self.output_filename}.txt", "status")
                
                metadata_path = os.path.join(
                    self.dest_path_edit.toPlainText().strip(),
                    f"{self.output_filename}.txt"
                )
                
                print(f"📄 DEBUG: Gerando metadados em {metadata_path}")
                
                success = self.generate_metadata_file(metadata_path)
                
                if success:
                    self.metadata_file_path = metadata_path
                    print(f"✅ DEBUG: Metadados gerados com sucesso")
                else:
                    print(f"⚠️ DEBUG: Falha ao gerar metadados (continuando...)")
            else:
                self.update_notes(f"📄 Metadados desabilitados pelo usuário", "status")
                print(f"📄 DEBUG: Geração de metadados desabilitada")
            
            # Agenda próxima etapa
            QTimer.singleShot(1000, self.real_step_add_to_qgis)
            
        except Exception as e:
            print(f"❌ ERROR real_step_generate_metadata: {str(e)}")
            # Não falha o processo por causa dos metadados
            QTimer.singleShot(1000, self.real_step_add_to_qgis)

    def generate_metadata_file(self, metadata_path):
        """Gera arquivo de metadados em formato texto"""
        try:
            from datetime import datetime
            
            metadata_content = []
            metadata_content.append("=" * 60)
            metadata_content.append(f"METADADOS DO PROCESSAMENTO {self.selected_theme}")
            metadata_content.append("Plugin DesagregaBiomasBR")
            metadata_content.append("=" * 60)
            metadata_content.append("")
            
            # Texto introdutório específico por tema
            if self.selected_theme == "PRODES":
                period_text = ""
                if hasattr(self, 'data_type') and self.data_type and hasattr(self, 'start_year') and hasattr(self, 'end_year'):
                    if self.data_type == "incremental" and self.start_year and self.end_year:
                        if self.start_year == self.end_year:
                            period_text = f"no ano de {self.start_year}"
                        else:
                            period_text = f"no período de {self.start_year} a {self.end_year}"
                    elif self.data_type == "acumulado" and self.end_year:
                        base_year = self.prodes_base_years.get(self.selected_biome, 2000)
                        period_text = f"acumuladas de {base_year} até {self.end_year}"
                
                intro_text = f"Áreas desmatadas {period_text}. O mapeamento utiliza imagens do satélite "
                intro_text += "Landsat ou similares, para registrar e quantificar as áreas desmatadas maiores que "
                intro_text += "6,25 hectares. O PRODES considera como desmatamento a supressão da vegetação nativa, "
                intro_text += "independentemente da futura utilização destas áreas."
                
            elif self.selected_theme == "ÁREA QUEIMADA":
                intro_text = "O shapefile refere-se ao produto AQ1Km, que apresenta uma estimativa das áreas queimadas nos biomas brasileiros, "
                intro_text += "gerado a partir de dados MODIS (coleção 6) dos satélites AQUA e TERRA. Trata-se de um produto de baixa resolução "
                intro_text += "espacial (1 km), com cobertura diária e abordagem sinótica, voltado à identificação e ao monitoramento contínuo "
                intro_text += "de áreas afetadas por queimadas."
                
            else:
                intro_text = f"Processamento de dados {self.selected_theme} para análise ambiental."
            
            metadata_content.append("DESCRIÇÃO:")
            metadata_content.append(intro_text)
            metadata_content.append("")
            
            # Informações gerais
            metadata_content.append("INFORMAÇÕES GERAIS:")
            metadata_content.append(f"Data/Hora do processamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            metadata_content.append(f"Tema: {self.selected_theme}")
            metadata_content.append(f"Bioma: {self.selected_biome}")
            metadata_content.append("")
            
            # Configurações temporais específicas por tema
            metadata_content.append("CONFIGURAÇÕES TEMPORAIS:")
            
            if self.selected_theme == "PRODES":
                metadata_content.append(f"Unidade temporal: Baseado na coluna 'year' dos dados")
                metadata_content.append(f"Tipo de dados: {getattr(self, 'data_type', 'N/A')}")
                
                if hasattr(self, 'start_year') and hasattr(self, 'end_year'):
                    if self.data_type == "incremental":
                        metadata_content.append(f"Período: {self.start_year} - {self.end_year}")
                    elif self.data_type == "acumulado":
                        base_year = self.prodes_base_years.get(self.selected_biome, 2000)
                        metadata_content.append(f"Período: {base_year} - {self.end_year} (acumulado)")
                        
            elif self.selected_theme == "ÁREA QUEIMADA":
                metadata_content.append(f"Unidade temporal: Dados mensais")
                metadata_content.append(f"Tipo de dados: {getattr(self, 'queimadas_data_type', 'N/A')}")
                
                if hasattr(self, 'queimadas_data_type') and self.queimadas_data_type:
                    if self.queimadas_data_type == "anual" and hasattr(self, 'queimadas_year') and self.queimadas_year:
                        metadata_content.append(f"Período: Janeiro de {self.queimadas_year} a Dezembro de {self.queimadas_year}")
                        # Calcula quantos meses foram processados
                        months_count = len([m for m in self.queimadas_months if m.startswith(f"{self.queimadas_year:04d}_")])
                        metadata_content.append(f"Arquivos processados: {months_count} meses unidos")
                    elif self.queimadas_data_type == "mensal" and hasattr(self, 'queimadas_month') and self.queimadas_month:
                        year, month, _ = self.queimadas_month.split('_')
                        metadata_content.append(f"Período: {month}/{year}")
                        metadata_content.append(f"Arquivos processados: 1 arquivo mensal")
                        
            elif self.selected_theme == "DETER":
                metadata_content.append(f"Unidade temporal: Baseado na coluna 'view_date' dos dados")
                if hasattr(self, 'deter_start_year') and hasattr(self, 'deter_end_year'):
                    metadata_content.append(f"Período: {self.deter_start_year} - {self.deter_end_year}")
                if hasattr(self, 'deter_selected_classes') and self.deter_selected_classes:
                    metadata_content.append(f"Classes selecionadas: {', '.join(self.deter_selected_classes)}")
                    
            elif self.selected_theme == "TERRACLASS":
                metadata_content.append(f"Unidade temporal: Anual")
                if hasattr(self, 'terraclass_year') and self.terraclass_year:
                    metadata_content.append(f"Ano: {self.terraclass_year}")
                    
            metadata_content.append("")
            
            # Filtros aplicados - específico por tema
            metadata_content.append("FILTROS APLICADOS:")
            if self.selected_theme == "ÁREA QUEIMADA":
                # Para ÁREA QUEIMADA, os filtros são automáticos (bioma + período)
                metadata_content.append(f"Filtro espacial automático: Bioma {self.selected_biome}")
                metadata_content.append("Observação: Dados originais cobrem todo o Brasil, corte por bioma aplicado automaticamente")
                if hasattr(self, 'queimadas_download_info_metadata') and self.queimadas_download_info_metadata:
                    if self.queimadas_download_info_metadata['data_type'] == 'anual':
                        metadata_content.append(f"Filtro temporal: Ano {self.queimadas_download_info_metadata['year']}")
                    else:
                        metadata_content.append(f"Filtro temporal: Mês específico")
            else:
                # Para PRODES, DETER, TERRACLASS usa o formato original
                if hasattr(self, 'urls_and_filters') and self.urls_and_filters:
                    for i, filter_str in enumerate(self.urls_and_filters['filters']):
                        if filter_str:
                            clean_filter = filter_str.replace('%20', ' ').replace('%27', "'")
                            metadata_content.append(f"Camada {i+1}: {clean_filter}")
                        else:
                            metadata_content.append(f"Camada {i+1}: Sem filtro")
                else:
                    metadata_content.append("Nenhum filtro específico aplicado")
            metadata_content.append("")
            
            # NOVO: Corte espacial detalhado
            metadata_content.append("CORTE ESPACIAL:")
            
            if self.selected_theme == "ÁREA QUEIMADA":
                # Para ÁREA QUEIMADA sempre há corte por bioma
                metadata_content.append("1. Corte automático por bioma (sempre aplicado):")
                metadata_content.append(f"   - Bioma selecionado: {self.selected_biome}")
                metadata_content.append(f"   - Shapefile de referência: {self.ibge_shapefile_name}")
                if self.selected_biome == 'Amazônia Legal':
                    metadata_content.append(f"   - Coluna utilizada: regiao = 'Amazônia Legal'")
                else:
                    metadata_content.append(f"   - Coluna utilizada: bioma = '{self.selected_biome}'")
                
                # Verifica se há corte adicional
                if hasattr(self, 'cut_option') and self.cut_option is not None and self.cut_option != 0:
                    metadata_content.append("")
                    metadata_content.append("2. Corte adicional (configurado pelo usuário):")
                    if self.cut_option == 1:
                        metadata_content.append("   - Tipo: Layer do QGIS")
                        if hasattr(self, 'selected_layer') and self.selected_layer:
                            metadata_content.append(f"   - Nome da layer: {self.selected_layer.name()}")
                            metadata_content.append(f"   - Número de feições: {self.selected_layer.featureCount()}")
                            metadata_content.append(f"   - Sistema de coordenadas da layer: {self.selected_layer.crs().authid()} - {self.selected_layer.crs().description()}")
                            
                            if hasattr(self, 'selected_field') and self.selected_field:
                                metadata_content.append(f"   - Campo utilizado: {self.selected_field}")
                                if hasattr(self, 'selected_element') and self.selected_element:
                                    metadata_content.append(f"   - Elemento selecionado: {self.selected_element}")
                    elif self.cut_option == 2:
                        metadata_content.append("   - Tipo: Retângulo desenhado")
                        if hasattr(self, 'drawn_rectangle') and self.drawn_rectangle:
                            metadata_content.append(f"   - Coordenadas: ({self.drawn_rectangle.xMinimum():.6f}, {self.drawn_rectangle.yMinimum():.6f}) - ({self.drawn_rectangle.xMaximum():.6f}, {self.drawn_rectangle.yMaximum():.6f})")
                    elif self.cut_option == 3:
                        metadata_content.append("   - Tipo: IBGE")
                        metadata_content.append(f"   - Shapefile: {self.ibge_shapefile_name}")
                        if self.ibge_state:
                            metadata_content.append(f"   - Estado: {self.ibge_state}")
                            if self.ibge_municipality:
                                metadata_content.append(f"   - Município: {self.ibge_municipality}")
                else:
                    metadata_content.append("")
                    metadata_content.append("2. Corte adicional: Nenhum (apenas corte por bioma aplicado)")
                    
            else:
                # Para outros temas (PRODES, DETER, TERRACLASS) mantém lógica original
                if hasattr(self, 'cut_option'):
                    if self.cut_option == 0:
                        metadata_content.append("Tipo: Sem corte (bioma completo)")
                    elif self.cut_option == 1:
                        metadata_content.append("Tipo: Layer do QGIS")
                        if hasattr(self, 'selected_layer') and self.selected_layer:
                            metadata_content.append(f"Nome da layer: {self.selected_layer.name()}")
                            metadata_content.append(f"Número de feições: {self.selected_layer.featureCount()}")
                            metadata_content.append(f"Sistema de coordenadas da layer: {self.selected_layer.crs().authid()} - {self.selected_layer.crs().description()}")
                            
                            if hasattr(self, 'selected_field') and self.selected_field:
                                metadata_content.append(f"Campo utilizado: {self.selected_field}")
                                if hasattr(self, 'selected_element') and self.selected_element:
                                    metadata_content.append(f"Elemento selecionado: {self.selected_element}")
                    elif self.cut_option == 2:
                        metadata_content.append("Tipo: Retângulo desenhado")
                        if hasattr(self, 'drawn_rectangle') and self.drawn_rectangle:
                            metadata_content.append(f"Coordenadas: ({self.drawn_rectangle.xMinimum():.6f}, {self.drawn_rectangle.yMinimum():.6f}) - ({self.drawn_rectangle.xMaximum():.6f}, {self.drawn_rectangle.yMaximum():.6f})")
                    elif self.cut_option == 3:
                        metadata_content.append("Tipo: IBGE")
                        metadata_content.append(f"Shapefile: {self.ibge_shapefile_name}")
                        metadata_content.append(f"Bioma/Região: {self.selected_biome} (já filtrado)")
                        if self.ibge_state:
                            metadata_content.append(f"Estado: {self.ibge_state}")
                            if self.ibge_municipality:
                                metadata_content.append(f"Município: {self.ibge_municipality}")
                                
            metadata_content.append("")
            
            # URLs utilizadas - específico por tema
            metadata_content.append("URLS DOS SERVIÇOS:")
            
            if self.selected_theme == "ÁREA QUEIMADA":
                # Para ÁREA QUEIMADA, lista as URLs dos ZIPs baixados
                if hasattr(self, 'queimadas_download_info_metadata') and self.queimadas_download_info_metadata:
                    metadata_content.append(f"Servidor base: {self.queimadas_download_info_metadata['base_url']}")
                    metadata_content.append(f"Arquivos baixados: {len(self.queimadas_download_info_metadata['urls'])} ZIPs")
                    # Lista alguns exemplos das URLs
                    for i, url in enumerate(self.queimadas_download_info_metadata['urls'][:3]):  # Primeiros 3
                        month = self.queimadas_download_info_metadata['months'][i]
                        metadata_content.append(f"  Exemplo {i+1}: {url}")
                    if len(self.queimadas_download_info_metadata['urls']) > 3:
                        metadata_content.append(f"  ... e mais {len(self.queimadas_download_info_metadata['urls']) - 3} arquivos")
            else:
                # Para PRODES, DETER, TERRACLASS usa o formato original
                if hasattr(self, 'urls_and_filters') and self.urls_and_filters:
                    for i, (url, layer_name) in enumerate(zip(self.urls_and_filters['urls'], self.urls_and_filters['layer_names'])):
                        metadata_content.append(f"{layer_name}: {url}")
                        
            metadata_content.append("")
            
            # NOVO: Informações do arquivo final com sistema de coordenadas
            metadata_content.append("ARQUIVO RESULTANTE:")
            metadata_content.append(f"Nome: {self.output_filename}")
            metadata_content.append(f"Caminho: {getattr(self, 'final_file_path', 'N/A')}")
            metadata_content.append(f"Formato: {'Shapefile' if self.radio_shapefile.isChecked() else 'GeoPackage'}")
            
            if hasattr(self, 'processing_layers') and self.processing_layers:
                final_layer = self.processing_layers[0]
                metadata_content.append(f"Número de feições: {final_layer.featureCount()}")
                metadata_content.append(f"Sistema de coordenadas: EPSG:4674 - SIRGAS 2000")
                metadata_content.append(f"Tipo de geometria: {QgsWkbTypes.displayString(final_layer.wkbType())}")
                
                # Extensão geográfica
                extent = final_layer.extent()
                if not extent.isEmpty():
                    metadata_content.append(f"Extensão geográfica:")
                    metadata_content.append(f"  Longitude mínima: {extent.xMinimum():.6f}")
                    metadata_content.append(f"  Longitude máxima: {extent.xMaximum():.6f}")
                    metadata_content.append(f"  Latitude mínima: {extent.yMinimum():.6f}")
                    metadata_content.append(f"  Latitude máxima: {extent.yMaximum():.6f}")
                    
                # Campos da tabela
                fields = final_layer.fields()
                if len(fields) > 0:
                    metadata_content.append(f"Campos da tabela:")
                    for field in fields:
                        metadata_content.append(f"  {field.name()}: {field.typeName()}")
            
            # Informações específicas por tema
            if self.selected_theme == "ÁREA QUEIMADA":
                metadata_content.append("")  # NOVO: Linha em branco antes da seção específica
                metadata_content.append("INFORMAÇÕES ESPECÍFICAS DO PRODUTO AQ1KM:")
                metadata_content.append("")
                
                metadata_content.append("Título:")
                metadata_content.append("Produto AQ1Km – Áreas Queimadas com Resolução Espacial de 1 km")
                metadata_content.append("")
                
                # Adiciona período específico baseado no processamento
                periodo_temporal = "Dados mensais"
                if hasattr(self, 'queimadas_download_info_metadata') and self.queimadas_download_info_metadata:
                    if self.queimadas_download_info_metadata['data_type'] == 'anual':
                        ano = self.queimadas_download_info_metadata['year']
                        periodo_temporal = f"Janeiro de {ano} a Dezembro de {ano}"
                    elif self.queimadas_download_info_metadata['data_type'] == 'mensal':
                        mes_data = self.queimadas_download_info_metadata.get('month', '')
                        if mes_data:
                            year, month, _ = mes_data.split('_')
                            periodo_temporal = f"{month}/{year}"
                
                metadata_content.append("Cobertura Temporal:")
                metadata_content.append(periodo_temporal)
                metadata_content.append("")
                
                metadata_content.append("Fonte e Parceria:")
                metadata_content.append("O desenvolvimento do produto AQ1Km é fruto da parceria entre o Instituto Nacional de Pesquisas Espaciais (INPE) e o Laboratório de Aplicações de Satélites Ambientais (LASA/UFRJ), no âmbito de pesquisas voltadas ao monitoramento ambiental por sensoriamento remoto.")
                metadata_content.append("")
                
                metadata_content.append("Metodologia:")
                metadata_content.append("A detecção das áreas queimadas é realizada com base em algoritmos que utilizam bandas térmicas (4 µm) dos sensores MODIS, com foco na identificação de alterações na resposta espectral associadas a queimadas recentes. A metodologia está descrita em detalhes no artigo científico:")
                metadata_content.append("")
                metadata_content.append("LIBONATI, R.; DACAMARA, C.; SETZER, A.; MORELLI, F.; MELCHIORI, A. An Algorithm for Burned Area Detection in the Brazilian Cerrado Using 4 µm MODIS Imagery. Remote Sensing, v. 7, p. 15782–15803, 2015. https://doi.org/10.3390/rs71215803")
                metadata_content.append("")
                
                metadata_content.append("Características Técnicas:")
                metadata_content.append("- Resolução Espacial: 1 km")
                metadata_content.append("- Sistema de Referência: SIRGAS 2000 – EPSG:4674")
                metadata_content.append("- Formato: Shapefile (vetorial)")
                metadata_content.append("- Cobertura: Diária com abordagem sinótica")
                metadata_content.append("")
                
                metadata_content.append("Uso Recomendado:")
                metadata_content.append("O produto é indicado para análises de caráter regional ou nacional, avaliação de tendências temporais de queimadas, estudos ambientais e suporte à formulação de políticas públicas relacionadas à conservação dos biomas brasileiros.")
                metadata_content.append("")
                
                metadata_content.append("Limitações de Uso:")
                metadata_content.append("Devido à sua resolução espacial de 1 km, não é recomendado para análises locais ou de pequena escala.")
                metadata_content.append("")
            
            # NOVO: Seção de processamentos realizados
            metadata_content.append("=" * 60)
            metadata_content.append("PROCESSAMENTOS REALIZADOS:")
            metadata_content.append("=" * 60)
            processing_summary = self.get_processing_summary()
            
            if len(processing_summary) == 1 and "Nenhum processamento" in processing_summary[0]:
                metadata_content.append("Dados utilizados conforme baixados da fonte original, sem processamentos adicionais.")
            else:
                metadata_content.append("Os seguintes processamentos foram aplicados aos dados originais:")
                metadata_content.append("")
                
                for i, process in enumerate(processing_summary, 1):
                    metadata_content.append(f"{i:2d}. {process}")
                
                metadata_content.append("")
                metadata_content.append("NOTA: Todos os processamentos utilizaram algoritmos nativos do QGIS.")
                metadata_content.append("Os dados de saída preservam a qualidade e integridade dos dados originais.")
            
            metadata_content.append("")
            metadata_content.append("=" * 60)
            metadata_content.append("Gerado pelo plugin DesagregaBiomasBR")
            metadata_content.append(f"Desenvolvido para processamento de dados {self.selected_theme}")
            metadata_content.append("=" * 60)
            
            # Salva arquivo
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(metadata_content))
            
            print(f"✅ DEBUG: Metadados salvos com {len(metadata_content)} linhas")
            return True
            
        except Exception as e:
            print(f"❌ ERROR generate_metadata_file: {str(e)}")
            return False

    def real_step_add_to_qgis(self):
        """Etapa 7: Adiciona arquivo ao QGIS"""
        try:
            self.status_label.setText("🗺️ Adicionando ao QGIS...")
            
            if self.checkbox_add_to_map.isChecked() and hasattr(self, 'final_file_path'):
                self.update_notes(f"🗺️ Carregando no QGIS | Arquivo: {os.path.basename(self.final_file_path)}", "status")
                
                print(f"🗺️ DEBUG: Adicionando {self.final_file_path} ao QGIS")
                
                # CORREÇÃO 1: Nome real do shapefile (baseado no filename)
                real_filename = os.path.splitext(os.path.basename(self.final_file_path))[0]
                layer_name = real_filename  # Usa o nome real do arquivo
                
                print(f"📋 DEBUG: Nome da layer: {layer_name}")
                
                # Carrega layer no QGIS
                layer = QgsVectorLayer(self.final_file_path, layer_name, "ogr")
                
                if layer.isValid():
                    # CORREÇÃO 2: Define CRS como 4674 (SIRGAS 2000)
                    from qgis.core import QgsCoordinateReferenceSystem
                    
                    
                    # CORREÇÃO: Não força CRS, preserva projeção original dos dados
                    # DEBUG: setCrs removido - preserva CRS original
                    print(f"✅ DEBUG: Preservando CRS original: {layer.crs().authid()}")
                    
                    print(f"✅ DEBUG: Preservando CRS original: {layer.crs().authid()}")
                    print(f"📍 DEBUG: Extensão da layer: {layer.extent()}")
                    # Adiciona ao projeto
                    QgsProject.instance().addMapLayer(layer)
                    print(f"✅ DEBUG: Layer '{layer_name}' adicionada ao projeto")
                    
                    # Zoom para a extensão da layer
                    try:
                        from qgis.utils import iface
                        iface.mapCanvas().setExtent(layer.extent())
                        iface.mapCanvas().refresh()
                        print(f"🎯 DEBUG: Zoom ajustado para a extensão da layer")
                    except:
                        print(f"✅ DEBUG: Layer adicionada (zoom não ajustado)")
                        
                else:
                    print(f"⚠️ DEBUG: Falha ao carregar layer no QGIS (arquivo foi salvo)")
            else:
                self.update_notes(f"🗺️ Adição ao QGIS desabilitada pelo usuário", "status")
                print(f"🗺️ DEBUG: Adição ao QGIS desabilitada")
            
            # Agenda finalização
            QTimer.singleShot(1000, self.real_step_finish)
            
        except Exception as e:
            print(f"❌ ERROR real_step_add_to_qgis: {str(e)}")
            # Não falha o processo por causa do QGIS
            QTimer.singleShot(1000, self.real_step_finish)

    def real_step_finish(self):
        """Etapa 8: Finaliza processamento"""
        try:
            self.status_label.setText("✅ Processamento concluído com sucesso!")
            self.status_label.setStyleSheet("color: #2e7c3f; font-weight: bold;")
            
            # Finaliza modo download com sucesso
            self.end_download_mode(success=True)
            
            # Atualiza notas finais
            final_notes = []
            
            if hasattr(self, 'final_file_path'):
                final_notes.append(f"✅ Arquivo salvo: {self.final_file_path}")
            
            final_notes.append(f"📊 Dados: {self.selected_theme} - {self.selected_biome}")
            
            if hasattr(self, 'data_type'):
                final_notes.append(f"📈 Tipo: {self.data_type}")
            
            if hasattr(self, 'start_year') and hasattr(self, 'end_year'):
                final_notes.append(f"🗓️ Período: {self.start_year}-{self.end_year}")
            
            if hasattr(self, 'processing_layers') and self.processing_layers:
                final_notes.append(f"📊 Feições: {self.processing_layers[0].featureCount()}")
            
            if hasattr(self, 'metadata_file_path'):
                final_notes.append(f"📄 Metadados: {os.path.basename(self.metadata_file_path)}")
            
            if self.checkbox_add_to_map.isChecked():
                final_notes.append(f"🗺️ Adicionado ao QGIS")
            
            # Adiciona resultado final à linha de configuração (contínua)
            final_part = f"✅ Arquivo salvo: {os.path.basename(self.final_file_path)}"
            
            # Obtém a configuração atual e adiciona o resultado
            if hasattr(self, 'config_note') and self.config_note:
                complete_line = f"{self.config_note} | {final_part}"
            else:
                complete_line = final_part
            
            self.update_notes(complete_line, "config")
            # Limpa status para mostrar só a linha completa
            self.status_note = ""
            self._update_notes_display()
            
            print(f"🎉 DEBUG: === PROCESSAMENTO REAL CONCLUÍDO COM SUCESSO! ===")
            
        except Exception as e:
            print(f"❌ ERROR real_step_finish: {str(e)}")
            self.status_label.setText(f"❌ Erro na finalização: {str(e)}")
            self.btn_process.setEnabled(True)

    def generate_output_filename(self):
        """Gera nome do arquivo baseado nas seleções"""
        try:
            # Base do nome
            parts = [
                self.selected_theme.lower(),
                self.selected_biome.lower().replace(' ', '_').replace('ã', 'a').replace('ô', 'o'),
                self.data_type
            ]
            
            # Adiciona informações temporais
            if self.data_type == "incremental" and hasattr(self, 'start_year') and hasattr(self, 'end_year'):
                parts.append(f"{self.start_year}_{self.end_year}")
            elif self.data_type == "acumulado" and hasattr(self, 'end_year'):
                base_year = self.prodes_base_years.get(self.selected_biome, 2000)
                parts.append(f"{base_year}_{self.end_year}")
            
            # NOVO: Adiciona informações de corte espacial com nome do arquivo
            if hasattr(self, 'cut_option') and self.cut_option != 0:
                if self.cut_option == 1 and hasattr(self, 'selected_layer') and self.selected_layer:
                    # Layer carregado - usa nome da layer
                    layer_name = self.selected_layer.name()
                    # Remove caracteres especiais e limita tamanho
                    clean_name = layer_name.replace(' ', '_').replace('-', '_').replace('.', '_')
                    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '_')[:20]
                    parts.append(f"corte_{clean_name}")
                    
                    # Se tem campo e elemento específico, adiciona também
                    if hasattr(self, 'selected_field') and self.selected_field and hasattr(self, 'selected_element') and self.selected_element:
                        clean_element = str(self.selected_element).replace(' ', '_').replace('-', '_')
                        clean_element = ''.join(c for c in clean_element if c.isalnum() or c == '_')[:15]
                        parts.append(clean_element)
                        
                elif self.cut_option == 2:
                    # Retângulo desenhado
                    parts.append("corte_retangulo")
                    
                elif self.cut_option == 3:
                    # IBGE - inclui informações da seleção
                    parts.append("corte_ibge")
                    if self.ibge_state:
                        clean_state = self.ibge_state.replace(' ', '_')
                        clean_state = ''.join(c for c in clean_state if c.isalnum() or c == '_')[:10]
                        parts.append(clean_state.lower())
                        
                        if self.ibge_municipality:
                            clean_municipality = self.ibge_municipality.replace(' ', '_')
                            clean_municipality = ''.join(c for c in clean_municipality if c.isalnum() or c == '_')[:15]
                            parts.append(clean_municipality.lower())
            
            filename = "_".join(parts)
            
            # Limita tamanho total do nome (alguns sistemas têm limite)
            if len(filename) > 100:
                filename = filename[:100]
                
            print(f"📁 DEBUG: Nome do arquivo gerado: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ ERROR generate_output_filename: {str(e)}")
            return "prodes_result"

    def build_urls_and_filters(self):
        """Constrói URLs e filtros CQL para o processamento"""
        try:
            result = {
                'urls': [],
                'filters': [],
                'layer_names': []
            }
            
            urls = self.prodes_urls[self.selected_biome]
            
            if self.data_type == "incremental":
                # Só yearly_deforestation com filtro
                result['urls'].append(urls['yearly'])
                result['layer_names'].append('yearly_deforestation')
                
                # Constrói filtro CQL baseado na coluna 'year'
                cql_filter = f"year BETWEEN {self.start_year} AND {self.end_year}"
                
                result['filters'].append(cql_filter)
                
            elif self.data_type == "acumulado":
                # accumulated_deforestation (sem filtro) + yearly_deforestation (com filtro até ano final)
                result['urls'].append(urls['accumulated'])
                result['urls'].append(urls['yearly'])
                result['layer_names'].append('accumulated_deforestation')
                result['layer_names'].append('yearly_deforestation')
                
                # Filtro só para yearly (accumulated não precisa de filtro)
                result['filters'].append("")  # Sem filtro para accumulated
                
                # Para yearly até o ano final, baseado na coluna 'year'
                base_year = self.prodes_base_years.get(self.selected_biome, 2000)
                cql_filter = f"year%20BETWEEN%20{base_year}%20AND%20{self.end_year}"
                
                result['filters'].append(cql_filter)
            
            return result
            
        except Exception as e:
            print(f"❌ ERROR build_urls_and_filters: {str(e)}")
            return {'urls': [], 'filters': [], 'layer_names': []}

    def build_deter_urls_and_filters(self):
        """Constrói URLs e filtros para processamento DETER - ESTRATÉGIA ROBUSTA"""
        try:
            result = {
                'urls': [],
                'filters': [],
                'layer_names': []
            }
            
            # URLs dos serviços DETER
            deter_urls = {
                'Cerrado': 'https://terrabrasilis.dpi.inpe.br/geoserver/deter-cerrado-nb/deter_cerrado/ows',
                'Amazônia Legal': 'https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/deter_amz/ows'
            }
            
            # URL única para DETER
            url = deter_urls[self.selected_biome]
            result['urls'].append(url)
            result['layer_names'].append('deter_alerts')
            
            # ESTRATÉGIA ROBUSTA: Baixar primeiro só com filtro espacial
            # Depois aplicar filtros temporais/classes na memória
            
            # Para "todo o bioma": SEM filtro na URL
            # Para corte espacial: filtro BBOX na URL
            # Filtros temporais/classes: aplicados na memória
            
            # CORREÇÃO: DETER usa a mesma estratégia que PRODES
            # Não precisa construir BBOX aqui, a função download_wfs_layer() já faz isso
            print(f"✅ INFO: DETER usará função download_wfs_layer() com suporte automático ao BBOX")
            result['filters'].append('')  # Sem filtro na URL - filtros aplicados na memória
            
            # NOVA ESTRATÉGIA: Constrói expressão QGIS nativa
            # Formato de data ISO para QGIS: YYYY-MM-DD
            start_date = f"{self.deter_start_year}-01-01"
            end_date = f"{self.deter_end_year}-12-31"
            
            # Expressão de data usando sintaxe QGIS
            date_filter = f"\"view_date\" >= '{start_date}' AND \"view_date\" <= '{end_date}'"
            
            # Classes selecionadas
            available_classes = self.deter_classes[self.selected_biome]
            total_available = len(available_classes)
            total_selected = len(self.deter_selected_classes)
            
            if total_selected == total_available:
                # Todas as classes = só filtro temporal
                qgis_expression = date_filter
                print(f"✅ INFO: Todas as {total_selected} classes selecionadas - aplicando APENAS filtro temporal")
            else:
                # Algumas classes = filtro temporal + classes
                if len(self.deter_selected_classes) == 1:
                    class_filter = f"\"classname\" = '{self.deter_selected_classes[0]}'"
                else:
                    classes_str = "','".join(self.deter_selected_classes)
                    class_filter = f"\"classname\" IN ('{classes_str}')"
                
                qgis_expression = f"{date_filter} AND {class_filter}"
                print(f"✅ INFO: {total_selected}/{total_available} classes selecionadas - aplicando filtros temporal + classes")
            
            # ARMAZENA expressão QGIS para usar na função apply_temporal_filter
            result['memory_filter'] = qgis_expression
            
            print(f"🔍 DEBUG: URL DETER: {url}")
            print(f"🔍 DEBUG: Expressão QGIS: {qgis_expression}")
            
            return result
            
        except Exception as e:
            print(f"❌ ERROR build_deter_urls_and_filters: {str(e)}")
            return {'urls': [], 'filters': [], 'layer_names': [], 'memory_filter': ''}

    def process_terraclass_data(self):
        """Processa os dados TERRACLASS conforme configurações - VERSÃO REAL"""
        try:
            print(f"🚀 DEBUG: === INICIANDO PROCESSAMENTO REAL TERRACLASS ===")
            
            # NOVO: Reseta log de processamentos para nova operação
            self.processing_log = []
            
            # Gera nome do arquivo baseado nas seleções TERRACLASS
            self.output_filename = self.generate_terraclass_output_filename()
            print(f"📁 DEBUG: Nome do arquivo TERRACLASS: {self.output_filename}")
            
            # Constrói URLs e informações para TERRACLASS
            self.terraclass_download_info = self.build_terraclass_download_info()
            print(f"🌐 DEBUG: Info de download TERRACLASS: {self.terraclass_download_info}")
            
            # Inicia processamento REAL
            self.current_step_index = 0
            self.processing_layers = []  # Para armazenar layers baixadas
            
            # Etapa 1: Baixar arquivo ZIP
            self.terraclass_step_download_zip()
            
        except Exception as e:
            print(f"❌ ERROR process_terraclass_data: {str(e)}")
            self.status_label.setText(f"❌ Erro no processamento TERRACLASS: {str(e)}")
            self.end_download_mode(success=False)

    def generate_terraclass_output_filename(self):
        """Gera nome do arquivo de saída para TERRACLASS"""
        try:
            # Componentes do nome
            theme = self.selected_theme.lower()
            biome = self.selected_biome.lower().replace(' ', '_').replace('ã', 'a').replace('ô', 'o')
            year = str(self.terraclass_year)
            
            # Estado normalizado
            state_normalized = self.normalize_terraclass_text(self.terraclass_state)
            
            # Tipo de download
            if self.terraclass_municipality:
                # Download municipal
                municipality_normalized = self.normalize_terraclass_text(self.terraclass_municipality)
                download_type = "municipal"
                location_part = f"{state_normalized}_{municipality_normalized}"
            else:
                # Download estadual
                download_type = "estadual"
                location_part = state_normalized
            
            # Nome final
            filename = f"{theme}_{biome}_{year}_{download_type}_{location_part}"
            
            # Limita tamanho do nome
            if len(filename) > 100:
                filename = f"{theme}_{biome}_{year}_{location_part}"
            
            print(f"📁 DEBUG: Nome TERRACLASS gerado: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ ERROR generate_terraclass_output_filename: {str(e)}")
            return f"terraclass_{self.selected_biome.lower()}_{self.terraclass_year}_{self.terraclass_state.lower()}"

    def build_terraclass_download_info(self):
        """Constrói informações de download para TERRACLASS"""
        try:
            # Obtém dados do shapefile IBGE
            shapefile_data = self.get_terraclass_shapefile_data()
            if not shapefile_data:
                raise Exception("Falha ao obter dados do shapefile IBGE")
            
            # Constrói URL baseada no tipo de download
            if self.terraclass_municipality:
                # Download municipal
                url_template = "https://www.terraclass.gov.br/helpers/terraclass_data4download_2024/V/municipal/{uf_lower}/{biome}.{ano}.{municipio_normalizado}.{UF}.{geocodigo_munic}.V.zip"
                
                url = url_template.format(
                    uf_lower=shapefile_data['uf'].lower(),
                    biome='AMZ' if self.selected_biome == 'Amazônia' else 'CER',
                    ano=self.terraclass_year,
                    municipio_normalizado=self.normalize_terraclass_text(self.terraclass_municipality),
                    UF=shapefile_data['uf'],
                    geocodigo_munic=shapefile_data['geocodigo']
                )
                download_type = "Municipal"
                location = f"{self.terraclass_state} - {self.terraclass_municipality}"
            else:
                # Download estadual
                url_template = "https://www.terraclass.gov.br/helpers/terraclass_data4download_2024/V/estadual/{biome}.{ano}.{estado_normalizado}.{geocodigo_uf}.V.zip"
                
                url = url_template.format(
                    biome='AMZ' if self.selected_biome == 'Amazônia' else 'CER',
                    ano=self.terraclass_year,
                    estado_normalizado=self.normalize_terraclass_text(self.terraclass_state),
                    geocodigo_uf=shapefile_data['cod_uf']
                )
                download_type = "Estadual"
                location = self.terraclass_state
            
            return {
                'url': url,
                'download_type': download_type,
                'location': location,
                'biome': self.selected_biome,
                'year': self.terraclass_year,
                'shapefile_data': shapefile_data
            }
            
        except Exception as e:
            print(f"❌ ERROR build_terraclass_download_info: {str(e)}")
            return None

    def get_terraclass_shapefile_data(self):
        """Obtém dados necessários do shapefile IBGE para TERRACLASS"""
        try:
            if not self.ibge_layer:
                return None
            
            # Constrói filtro para encontrar os dados necessários
            if self.terraclass_municipality:
                # Para município específico
                expression = f'"bioma" = \'{self.selected_biome}\' AND "estado" = \'{self.terraclass_state}\' AND "nome" = \'{self.terraclass_municipality}\''
            else:
                # Para estado (pega qualquer município do estado para obter cod_uf)
                expression = f'"bioma" = \'{self.selected_biome}\' AND "estado" = \'{self.terraclass_state}\''
            
            # Busca primeira feição que atende o critério
            request = QgsFeatureRequest().setFilterExpression(expression)
            features = list(self.ibge_layer.getFeatures(request))
            
            if not features:
                print(f"❌ DEBUG: Nenhuma feição encontrada no shapefile para {self.terraclass_state}")
                return None
            
            feature = features[0]  # Usa primeira feição encontrada
            
            data = {
                'nome': feature['nome'],
                'geocodigo': feature['geocodigo'], 
                'uf': feature['uf'],
                'estado': feature['estado'],
                'bioma': feature['bioma'],
                'cod_uf': feature['cod_uf']
            }
            
            print(f"✅ DEBUG: Dados do shapefile obtidos: {data}")
            return data
            
        except Exception as e:
            print(f"❌ ERROR get_terraclass_shapefile_data: {str(e)}")
            return None

    def terraclass_step_download_zip(self):
        """Etapa 1: Baixa arquivo ZIP do TERRACLASS"""
        try:
            self.status_label.setText("📥 Baixando arquivo TERRACLASS...")
            self.update_notes(f"📥 Baixando {self.terraclass_download_info['download_type']} | {self.terraclass_download_info['location']}", "status")
            
            url = self.terraclass_download_info['url']
            print(f"🌐 DEBUG: URL TERRACLASS: {url}")
            
            # Baixa arquivo ZIP
            zip_file_path = self.download_terraclass_zip(url)
            
            if zip_file_path:
                print(f"✅ DEBUG: ZIP baixado com sucesso: {zip_file_path}")
                self.terraclass_zip_path = zip_file_path
                
                # Agenda próxima etapa
                QTimer.singleShot(1000, self.terraclass_step_extract_zip)
            else:
                raise Exception("Falha ao baixar arquivo ZIP")
                
        except Exception as e:
            print(f"❌ ERROR terraclass_step_download_zip: {str(e)}")
            self.status_label.setText(f"❌ Erro no download: {str(e)}")
            self.end_download_mode(success=False)

    def download_terraclass_zip(self, url):
        """Baixa arquivo ZIP do TERRACLASS"""
        try:
            from qgis.PyQt.QtCore import QUrl, QEventLoop
            from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
            import tempfile
            import os
            
            print(f"🌐 DEBUG: Iniciando download ZIP: {url}")
            
            # Verifica abort antes de iniciar download
            if self.check_abort_signal():
                print("🛑 DEBUG: Download TERRACLASS abortado antes do início")
                return None
            
            # Cria request
            request = QNetworkRequest(QUrl(url))
            request.setRawHeader(b"User-Agent", b"QGIS-DesagregaBiomasBR")
            reply = self.network_manager.get(request)
            
            # Aguarda resposta com verificações periódicas de abort
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            
            # Timer para verificar abort periodicamente durante download
            abort_timer = QTimer()
            abort_timer.timeout.connect(lambda: (
                self.check_abort_signal() and (
                    reply.abort(),
                    loop.quit(),
                    print("🛑 DEBUG: Download TERRACLASS abortado durante transferência")
                )[-1]
            ))
            abort_timer.start(500)  # Verifica a cada 500ms
            
            loop.exec_()
            abort_timer.stop()
            
            if reply.error() == QNetworkReply.NoError:
                # Lê dados
                data = reply.readAll()
                
                if len(data) > 1000:  # Verifica se é um arquivo válido
                    # Salva arquivo temporário
                    temp_dir = tempfile.gettempdir()
                    zip_filename = f"terraclass_{self.terraclass_year}_{id(self)}.zip"
                    zip_path = os.path.join(temp_dir, zip_filename)
                    
                    with open(zip_path, 'wb') as f:
                        f.write(data.data())
                    
                    print(f"✅ DEBUG: ZIP salvo em: {zip_path}")
                    print(f"📊 DEBUG: Tamanho do arquivo: {len(data)} bytes")
                    
                    reply.deleteLater()
                    return zip_path
                else:
                    print(f"❌ DEBUG: Arquivo muito pequeno ({len(data)} bytes) - provavelmente erro")
            else:
                error_msg = reply.errorString()
                print(f"❌ DEBUG: Erro no download: {error_msg}")
            
            reply.deleteLater()
            return None
            
        except Exception as e:
            print(f"❌ ERROR download_terraclass_zip: {str(e)}")
            return None

    def terraclass_step_extract_zip(self):
        """Etapa 2: Extrai arquivo ZIP e processa shapefile"""
        try:
            self.status_label.setText("📦 Extraindo arquivo TERRACLASS...")
            self.update_notes(f"📦 Extraindo ZIP | Processando shapefile", "status")
            
            # Extrai ZIP
            extracted_files = self.extract_terraclass_zip(self.terraclass_zip_path)
            
            if extracted_files:
                # Procura shapefile principal
                shapefile_path = self.find_terraclass_shapefile(extracted_files)
                
                if shapefile_path:
                    print(f"✅ DEBUG: Shapefile encontrado: {shapefile_path}")
                    self.terraclass_shapefile_path = shapefile_path
                    
                    # Carrega shapefile
                    layer = QgsVectorLayer(shapefile_path, f"TERRACLASS_{self.terraclass_year}", "ogr")
                    
                    if layer.isValid():
                        self.processing_layers = [layer]
                        
                        # NOVO: Registra processamento específico TERRACLASS
                        self.add_processing_log(
                            "EXTRAÇÃO DE ARQUIVO",
                            f"Arquivo ZIP extraído → Shapefile TERRACLASS carregado ({layer.featureCount()} feições)"
                        )
                        
                        print(f"✅ DEBUG: Shapefile carregado: {layer.featureCount()} feições")
                        
                        # Agenda próxima etapa
                        QTimer.singleShot(1000, self.terraclass_step_apply_style)
                    else:
                        raise Exception("Shapefile extraído é inválido")
                else:
                    raise Exception("Nenhum shapefile encontrado no ZIP")
            else:
                raise Exception("Falha ao extrair arquivo ZIP")
                
        except Exception as e:
            print(f"❌ ERROR terraclass_step_extract_zip: {str(e)}")
            self.status_label.setText(f"❌ Erro na extração: {str(e)}")
            self.end_download_mode(success=False)

    def extract_terraclass_zip(self, zip_path):
        """Extrai arquivo ZIP do TERRACLASS"""
        try:
            import zipfile
            import tempfile
            import os
            
            # Cria diretório temporário para extração
            extract_dir = os.path.join(tempfile.gettempdir(), f"terraclass_extract_{id(self)}")
            os.makedirs(extract_dir, exist_ok=True)
            
            print(f"📦 DEBUG: Extraindo para: {extract_dir}")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
                # Lista arquivos extraídos
                extracted_files = []
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        extracted_files.append(file_path)
                        print(f"   📄 {file}")
                
                print(f"✅ DEBUG: {len(extracted_files)} arquivos extraídos")
                return extracted_files
                
        except Exception as e:
            print(f"❌ ERROR extract_terraclass_zip: {str(e)}")
            return None

    def find_terraclass_shapefile(self, extracted_files):
        """Encontra o shapefile principal nos arquivos extraídos"""
        try:
            # Procura por arquivos .shp
            shapefiles = [f for f in extracted_files if f.endswith('.shp')]
            
            if not shapefiles:
                print(f"❌ DEBUG: Nenhum arquivo .shp encontrado")
                return None
            
            # Se há apenas um, usa ele
            if len(shapefiles) == 1:
                print(f"✅ DEBUG: Shapefile único encontrado: {shapefiles[0]}")
                return shapefiles[0]
            
            # Se há múltiplos, procura pelo principal (maior ou com padrão específico)
            main_shapefile = None
            
            for shp in shapefiles:
                filename = os.path.basename(shp).lower()
                # Padrões que indicam arquivo principal
                if any(pattern in filename for pattern in ['terraclass', 'principal', 'main']):
                    main_shapefile = shp
                    break
            
            # Se não encontrou por padrão, usa o primeiro
            if not main_shapefile:
                main_shapefile = shapefiles[0]
            
            print(f"✅ DEBUG: Shapefile principal selecionado: {main_shapefile}")
            return main_shapefile
            
        except Exception as e:
            print(f"❌ ERROR find_terraclass_shapefile: {str(e)}")
            return None

    def terraclass_step_apply_style(self):
        """Etapa 3: Aplica estilo e finaliza processamento"""
        try:
            self.status_label.setText("🎨 Aplicando estilo TERRACLASS...")
            self.update_notes(f"🎨 Aplicando simbologia | Finalizando processamento", "status")
            
            if self.processing_layers:
                layer = self.processing_layers[0]
                
                # Aplica estilo TERRACLASS se arquivo existe
                style_applied = self.apply_terraclass_style(layer)
                
                if style_applied:
                    print(f"✅ DEBUG: Estilo TERRACLASS aplicado")
                else:
                    print(f"⚠️ DEBUG: Estilo padrão aplicado (arquivo QML não encontrado)")
                
                # Agenda finalização
                QTimer.singleShot(1000, self.terraclass_step_finish)
            else:
                raise Exception("Nenhuma layer para aplicar estilo")
                
        except Exception as e:
            print(f"❌ ERROR terraclass_step_apply_style: {str(e)}")
            self.status_label.setText(f"❌ Erro ao aplicar estilo: {str(e)}")
            self.progress_bar.setVisible(False)
            self.btn_process.setEnabled(True)

    def apply_terraclass_style(self, layer):
        """Aplica estilo TERRACLASS conforme arquivo QML"""
        try:
            # Procura arquivo de estilo
            style_path = os.path.join(self.plugin_dir, 'estilo_terraclass.qml')
            
            if os.path.exists(style_path):
                print(f"🎨 DEBUG: Aplicando estilo: {style_path}")
                
                # Carrega estilo do arquivo QML
                result = layer.loadNamedStyle(style_path)
                
                if result[1]:  # result[1] indica sucesso
                    print(f"✅ DEBUG: Estilo QML aplicado com sucesso")
                    layer.triggerRepaint()
                    return True
                else:
                    print(f"⚠️ DEBUG: Falha ao carregar estilo QML: {result[0]}")
            else:
                print(f"⚠️ DEBUG: Arquivo de estilo não encontrado: {style_path}")
            
            # Aplica estilo padrão se QML falhar
            self.apply_default_terraclass_style(layer)
            return False
            
        except Exception as e:
            print(f"❌ ERROR apply_terraclass_style: {str(e)}")
            self.apply_default_terraclass_style(layer)
            return False

    def apply_default_terraclass_style(self, layer):
        """Aplica estilo padrão para TERRACLASS"""
        try:
            from qgis.core import QgsSymbol, QgsSingleSymbolRenderer
            from qgis.PyQt.QtGui import QColor
            
            # Cria símbolo padrão
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(QColor(34, 139, 34, 180))  # Verde semi-transparente
            symbol.symbolLayer(0).setStrokeColor(QColor(0, 100, 0, 255))  # Borda verde escura
            symbol.symbolLayer(0).setStrokeWidth(0.5)
            
            # Aplica renderizador
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            
            print(f"✅ DEBUG: Estilo padrão TERRACLASS aplicado")
            
        except Exception as e:
            print(f"❌ ERROR apply_default_terraclass_style: {str(e)}")

    def terraclass_step_finish(self):
        """Etapa 4: Salva arquivo e finaliza processamento TERRACLASS"""
        try:
            # Salva arquivo na pasta escolhida pelo usuário
            if not self.processing_layers:
                raise Exception("Nenhuma layer para salvar")
            
            final_layer = self.processing_layers[0]
            
            # Determina formato e extensão
            if self.radio_shapefile.isChecked():
                format_name = "ESRI Shapefile"
                extension = ".shp"
            else:
                format_name = "GPKG"
                extension = ".gpkg"
            
            # Monta caminho completo na pasta escolhida pelo usuário
            dest_path = self.dest_path_edit.toPlainText().strip()
            full_path = os.path.join(dest_path, f"{self.output_filename}{extension}")
            
            self.status_label.setText("💾 Salvando arquivo TERRACLASS...")
            
            # Salva o arquivo
            success = self.save_layer_to_file(final_layer, full_path, format_name)
            
            if not success:
                raise Exception("Falha ao salvar arquivo TERRACLASS")
            
            self.final_file_path = full_path
            
            # Gera metadados se solicitado
            if self.checkbox_generate_metadata.isChecked():
                self.status_label.setText("📄 Gerando metadados TERRACLASS...")
                
                metadata_path = os.path.join(dest_path, f"{self.output_filename}.txt")
                self.generate_terraclass_metadata_file(metadata_path)
                self.metadata_file_path = metadata_path
            
            # Adiciona layer ao QGIS se solicitado
            if self.checkbox_add_to_map.isChecked():
                self.status_label.setText("🗺️ Adicionando TERRACLASS ao QGIS...")
                
                # Carrega layer salva no QGIS
                layer_name = self.output_filename
                layer = QgsVectorLayer(full_path, layer_name, "ogr")
                
                if layer.isValid():
                    # Adiciona ao projeto
                    QgsProject.instance().addMapLayer(layer)
                    
                    # 🎨 APLICA SIMBOLOGIA TERRACLASS
                    self.status_label.setText("🎨 Aplicando simbologia TERRACLASS...")
                    self.apply_terraclass_style(layer)
                    
                    # Zoom para a extensão da layer
                    try:
                        from qgis.utils import iface
                        iface.mapCanvas().setExtent(layer.extent())
                        iface.mapCanvas().refresh()
                    except:
                        pass
            
            # Atualiza status final
            self.status_label.setText("✅ Processamento TERRACLASS concluído com sucesso!")
            self.status_label.setStyleSheet("color: #2e7c3f; font-weight: bold;")
            
            # Finaliza modo download com sucesso
            self.end_download_mode(success=True)
            
            # Atualiza notas finais
            final_part = f"✅ Arquivo salvo: {os.path.basename(full_path)}"
            
            # Obtém a configuração atual e adiciona o resultado
            if hasattr(self, 'config_note') and self.config_note:
                complete_line = f"{self.config_note} | {final_part}"
            else:
                complete_line = final_part
            
            self.update_notes(complete_line, "config")
            # Limpa status para mostrar só a linha completa
            self.status_note = ""
            self._update_notes_display()
            
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            error_msg = f"❌ ERRO terraclass_step_finish: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "DesagregaBiomasBR", Qgis.Critical)
            self.status_label.setText(f"❌ Erro na finalização: {str(e)}")
            self.end_download_mode(success=False)

    def generate_terraclass_metadata_file(self, metadata_path):
        """Gera arquivo de metadados específico para TERRACLASS"""
        try:
            from datetime import datetime
            
            metadata_content = []
            metadata_content.append("=" * 60)
            metadata_content.append(f"METADADOS DO PROCESSAMENTO TERRACLASS")
            metadata_content.append("Plugin DesagregaBiomasBR")
            metadata_content.append("=" * 60)
            metadata_content.append("")
            
            # Texto introdutório específico do TERRACLASS
            intro_text = "O Projeto TerraClass tem como objetivo qualificar o desflorestamento da Amazônia Legal e Cerrado. "
            intro_text += "A partir das áreas mapeadas pelo PRODES, o TerraClass produz mapas sistêmicos de uso e cobertura "
            intro_text += "das terras desflorestadas nas regiões indicadas."
            
            metadata_content.append("DESCRIÇÃO:")
            metadata_content.append(intro_text)
            metadata_content.append("")
            
            # Informações gerais
            metadata_content.append("INFORMAÇÕES GERAIS:")
            metadata_content.append(f"Data/Hora do processamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            metadata_content.append(f"Tema: TERRACLASS")
            metadata_content.append(f"Bioma: {self.selected_biome}")
            metadata_content.append(f"Ano: {self.terraclass_year}")
            if hasattr(self, 'terraclass_state') and self.terraclass_state:
                metadata_content.append(f"Estado: {self.terraclass_state}")
            if hasattr(self, 'terraclass_municipality') and self.terraclass_municipality:
                metadata_content.append(f"Município: {self.terraclass_municipality}")
            metadata_content.append("")
            
            # Metodologia
            metadata_content.append("METODOLOGIA:")
            methodol_text = "A metodologia TerraClass, desenvolvida conjuntamente entre o INPE e a EMBRAPA, "
            methodol_text += "baseia-se atualmente na análise da série temporal de imagens de satélite de média resolução (20 a 10m), "
            methodol_text += "e técnicas de processamento de imagens, para identificar as diferentes classes de uso e cobertura: "
            methodol_text += "vegetação natural – primária e secundária; cultura agrícola – perene, semiperene, temporária de um ciclo, "
            methodol_text += "e de mais de um ciclo; pastagem; silvicultura; mineração; urbanizada; outras áreas edificadas; "
            methodol_text += "outros usos; natural não-florestal e corpos d´água."
            metadata_content.append(methodol_text)
            metadata_content.append("")
            
            # Configurações temporais
            metadata_content.append("CONFIGURAÇÕES TEMPORAIS:")
            metadata_content.append(f"Unidade temporal: Anual")
            metadata_content.append(f"Ano de referência: {self.terraclass_year}")
            metadata_content.append("")
            
            # Configurações espaciais
            metadata_content.append("CONFIGURAÇÕES ESPACIAIS:")
            metadata_content.append(f"Bioma: {self.selected_biome}")
            if hasattr(self, 'terraclass_state') and self.terraclass_state:
                metadata_content.append(f"Estado: {self.terraclass_state}")
                if hasattr(self, 'terraclass_municipality') and self.terraclass_municipality:
                    metadata_content.append(f"Município: {self.terraclass_municipality}")
                    metadata_content.append("Tipo de recorte: Municipal")
                else:
                    metadata_content.append("Tipo de recorte: Estadual")
            else:
                metadata_content.append("Tipo de recorte: Bioma completo")
            metadata_content.append("")
            
            # URL do arquivo
            metadata_content.append("ORIGEM DOS DADOS:")
            if hasattr(self, 'terraclass_download_info') and self.terraclass_download_info:
                metadata_content.append(f"Tipo de download: {self.terraclass_download_info['download_type']}")
                metadata_content.append(f"Local: {self.terraclass_download_info['location']}")
                metadata_content.append(f"URL: {self.terraclass_download_info['url']}")
            metadata_content.append("")
            
            # Informações do arquivo final
            metadata_content.append("ARQUIVO RESULTANTE:")
            metadata_content.append(f"Nome: {self.output_filename}")
            metadata_content.append(f"Caminho: {getattr(self, 'final_file_path', 'N/A')}")
            metadata_content.append(f"Formato: {'Shapefile' if self.radio_shapefile.isChecked() else 'GeoPackage'}")
            
            if hasattr(self, 'processing_layers') and self.processing_layers:
                final_layer = self.processing_layers[0]
                metadata_content.append(f"Número de feições: {final_layer.featureCount()}")
                metadata_content.append(f"Sistema de coordenadas: {final_layer.crs().authid()} - {final_layer.crs().description()}")
                metadata_content.append(f"Tipo de geometria: {QgsWkbTypes.displayString(final_layer.wkbType())}")
                
                # Extensão geográfica
                extent = final_layer.extent()
                if not extent.isEmpty():
                    metadata_content.append(f"Extensão geográfica:")
                    metadata_content.append(f"  Longitude mínima: {extent.xMinimum():.6f}")
                    metadata_content.append(f"  Longitude máxima: {extent.xMaximum():.6f}")
                    metadata_content.append(f"  Latitude mínima: {extent.yMinimum():.6f}")
                    metadata_content.append(f"  Latitude máxima: {extent.yMaximum():.6f}")
                
                metadata_content.append("")  # NOVO: Linha em branco antes dos campos da tabela
                    
                # Campos da tabela (classes de uso)
                fields = final_layer.fields()
                if len(fields) > 0:
                    metadata_content.append(f"Campos da tabela:")
                    for field in fields:
                        metadata_content.append(f"  {field.name()}: {field.typeName()}")
                        
                    metadata_content.append("")  # NOVO: Linha em branco após campos da tabela
                    
                    # Análise das classes de uso presentes
                    metadata_content.append("CLASSES DE USO E COBERTURA IDENTIFICADAS:")
                    
                    # Busca por campos que podem conter classes de uso
                    class_fields = []
                    for field in fields:
                        field_name = field.name().lower()
                        if any(keyword in field_name for keyword in ['class', 'uso', 'cover', 'terra']):
                            class_fields.append(field.name())
                    
                    if class_fields:
                        for class_field in class_fields[:2]:  # Primeiros 2 campos de classe
                            unique_values = []
                            for feature in final_layer.getFeatures():
                                value = feature[class_field]
                                if value and value not in unique_values:
                                    unique_values.append(value)
                            
                            if unique_values:
                                metadata_content.append(f"  Campo '{class_field}':")
                                for value in sorted(unique_values)[:15]:  # Primeiras 15 classes
                                    metadata_content.append(f"    - {value}")
                                if len(unique_values) > 15:
                                    metadata_content.append(f"    ... e mais {len(unique_values) - 15} classes")
            
            metadata_content.append("")
            metadata_content.append("INFORMAÇÕES ADICIONAIS:")
            metadata_content.append("O TerraClass é uma iniciativa conjunta do INPE (Instituto Nacional de Pesquisas Espaciais)")
            metadata_content.append("e EMBRAPA (Empresa Brasileira de Pesquisa Agropecuária) para qualificação do uso da terra")
            metadata_content.append("em áreas desflorestadas dos biomas brasileiros.")
            metadata_content.append("")
            metadata_content.append("Palavras-chave: uso da terra, cobertura da terra, desflorestamento, PRODES, sensoriamento remoto")
            metadata_content.append("")
            
            # NOVO: Seção específica de processamentos TERRACLASS
            metadata_content.append("=" * 60)
            metadata_content.append("PROCESSAMENTOS REALIZADOS:")
            metadata_content.append("=" * 60)
            processing_summary = self.get_processing_summary()
            
            if len(processing_summary) == 1 and "Nenhum processamento" in processing_summary[0]:
                metadata_content.append("Dados utilizados conforme baixados da fonte original (arquivo ZIP).")
                metadata_content.append("Processamento realizado: Extração de arquivo ZIP + Aplicação de simbologia padrão.")
            else:
                metadata_content.append("Os seguintes processamentos foram aplicados aos dados originais:")
                metadata_content.append("")
                
                for i, process in enumerate(processing_summary, 1):
                    metadata_content.append(f"{i:2d}. {process}")
                
                metadata_content.append("")
                metadata_content.append("NOTA: Todos os processamentos utilizaram algoritmos nativos do QGIS.")
                metadata_content.append("Os dados TERRACLASS preservam a classificação original INPE/EMBRAPA.")
                
            metadata_content.append("")
            metadata_content.append("=" * 60)
            metadata_content.append("Gerado pelo plugin DesagregaBiomasBR")
            metadata_content.append(f"Desenvolvido para processamento de dados TERRACLASS")
            metadata_content.append("=" * 60)
            
            # Salva arquivo
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(metadata_content))
            
            return True
            
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            error_msg = f"❌ ERRO generate_terraclass_metadata_file: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "DesagregaBiomasBR", Qgis.Critical)
            return False

    def generate_deter_output_filename(self):
        """Gera nome do arquivo de saída para DETER"""
        try:
            # Componentes do nome
            theme = self.selected_theme.lower()
            biome = self.selected_biome.lower().replace(' ', '_').replace('â', 'a').replace('ô', 'o')
            period = f"{self.deter_start_year}_{self.deter_end_year}"
            
            # Classes selecionadas com lógica inteligente
            if self.selected_biome and self.selected_biome in self.deter_classes:
                available_classes = self.deter_classes[self.selected_biome]
                total_available = len(available_classes)
                total_selected = len(self.deter_selected_classes)
                
                if total_selected == total_available:
                    # Todas as classes = sem filtro
                    classes_part = "todas_classes"
                elif total_selected == 1:
                    # Uma classe específica
                    classes_part = self.deter_selected_classes[0].lower().replace('_', '')
                else:
                    # Algumas classes
                    classes_part = f"select_{total_selected}_de_{total_available}"
            else:
                # Fallback
                classes_part = "classes_selecionadas"
            
            # Tipo de corte
            cut_name = self.get_cut_option_name()
            
            # Nome final
            filename = f"{theme}_{biome}_{period}_{classes_part}_{cut_name}"
            
            # Limita tamanho do nome
            if len(filename) > 100:
                filename = f"{theme}_{biome}_{period}_{cut_name}"
            
            print(f"📁 DEBUG: Nome DETER gerado: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ ERROR generate_deter_output_filename: {str(e)}")
            return f"deter_{self.selected_biome.lower()}_{self.deter_start_year}_{self.deter_end_year}"



    def create_prodes_step2_content(self):
        """Cria o conteúdo específico para configuração temporal do PRODES"""
        
        # Campo 1: Tipo de Dados (renumerado de 2 para 1)
        data_type_group = QGroupBox("1. Tipo de Dados PRODES")
        data_type_layout = QVBoxLayout()
        
        self.data_type_button_group = QButtonGroup()
        
        self.radio_incremental = QRadioButton("Incremental (apenas os anos do intervalo)")
        self.radio_incremental.setToolTip("Intervalo de desmatamento entre um período de anos específico")
        self.radio_incremental.setChecked(True)  # Padrão incremental
        
        self.radio_acumulado = QRadioButton("Acumulado (do primeiro ano até o ano final)")
        self.radio_acumulado.setToolTip("Parte do zero de cada bioma até o ano final escolhido")
        
        self.data_type_button_group.addButton(self.radio_incremental, 0)
        self.data_type_button_group.addButton(self.radio_acumulado, 1)
        self.data_type_button_group.buttonClicked.connect(self.on_data_type_changed)
        
        data_type_layout.addWidget(self.radio_incremental)
        data_type_layout.addWidget(self.radio_acumulado)
        data_type_group.setLayout(data_type_layout)
        self.content_layout.addWidget(data_type_group)
        
        # Campo 2: Seleção de Anos (renumerado de 3 para 2)
        self.years_group = QGroupBox("2. Seleção de Anos")
        years_layout = QGridLayout()
        
        # Labels e combos para anos
        self.start_year_label = QLabel("Ano inicial:")
        self.start_year_combo = QComboBox()
        self.start_year_combo.currentTextChanged.connect(self.on_start_year_changed)
        
        self.end_year_label = QLabel("Ano final:")
        self.end_year_combo = QComboBox()
        self.end_year_combo.currentTextChanged.connect(self.on_end_year_changed)
        
        years_layout.addWidget(self.start_year_label, 0, 0)
        years_layout.addWidget(self.start_year_combo, 0, 1)
        years_layout.addWidget(self.end_year_label, 1, 0)
        years_layout.addWidget(self.end_year_combo, 1, 1)
        
        self.years_group.setLayout(years_layout)
        self.content_layout.addWidget(self.years_group)
        
        # Inicializa valores padrão (SEM temporal_unit, apenas data_type)
        self.data_type = "incremental"
        
        # Popula anos baseado no bioma selecionado
        self.populate_years()
        
        # Atualiza interface inicial
        self.update_years_interface()
        self.update_prodes_notes()

    def create_deter_step2_content(self):
        """Cria o conteúdo específico para configuração temporal do DETER"""
        
        # Campo 1: Período de Análise (direto, sem escolha civil/PRODES)
        periodo_group = QGroupBox("1. Período de Análise")
        periodo_layout = QGridLayout()
        
        # Labels e combos para anos
        self.deter_start_year_label = QLabel("Ano inicial:")
        self.deter_start_year_combo = QComboBox()
        self.deter_start_year_combo.currentTextChanged.connect(self.on_deter_start_year_changed)
        
        self.deter_end_year_label = QLabel("Ano final:")
        self.deter_end_year_combo = QComboBox()
        self.deter_end_year_combo.currentTextChanged.connect(self.on_deter_end_year_changed)
        
        periodo_layout.addWidget(self.deter_start_year_label, 0, 0)
        periodo_layout.addWidget(self.deter_start_year_combo, 0, 1)
        periodo_layout.addWidget(self.deter_end_year_label, 1, 0)
        periodo_layout.addWidget(self.deter_end_year_combo, 1, 1)
        
        periodo_group.setLayout(periodo_layout)
        self.content_layout.addWidget(periodo_group)
        
        # Campo 2: Classes de Alertas DETER
        classes_group = QGroupBox("2. Classes de Alertas DETER")
        classes_layout = QVBoxLayout()
        
        # Container para checkboxes das classes
        self.deter_classes_widget = QWidget()
        self.deter_classes_layout = QVBoxLayout(self.deter_classes_widget)
        self.deter_classes_checkboxes = {}
        
        classes_layout.addWidget(self.deter_classes_widget)
        
        classes_group.setLayout(classes_layout)
        self.content_layout.addWidget(classes_group)
        
        # Inicializa valores padrão
        self.deter_selected_classes = []
        
        # Popula anos e classes baseado no bioma selecionado
        self.populate_deter_years()
        self.populate_deter_classes()
        
        # Atualiza interface e notas
        self.update_deter_notes()

    def create_terraclass_step2_content(self):
        """Cria o conteúdo específico para configuração temporal do TERRACLASS"""
        
        # Campo 1: Seleção de Ano
        year_group = QGroupBox("1. Seleção de Ano")
        year_layout = QVBoxLayout()
        
        self.terraclass_year_combo = QComboBox()
        self.terraclass_year_combo.currentTextChanged.connect(self.on_terraclass_year_changed)
        
        year_layout.addWidget(self.terraclass_year_combo)
        year_group.setLayout(year_layout)
        self.content_layout.addWidget(year_group)
        
        # Campo 2: Seleção de Estado
        state_group = QGroupBox("2. Seleção de Estado")
        state_layout = QVBoxLayout()
        
        self.terraclass_state_combo = QComboBox()
        self.terraclass_state_combo.currentTextChanged.connect(self.on_terraclass_state_changed)
        
        state_layout.addWidget(self.terraclass_state_combo)
        state_group.setLayout(state_layout)
        self.content_layout.addWidget(state_group)
        
        # Campo 3: Seleção de Município (opcional)
        municipality_group = QGroupBox("3. Seleção de Município (opcional)")
        municipality_layout = QVBoxLayout()
        
        self.terraclass_municipality_combo = QComboBox()
        self.terraclass_municipality_combo.currentTextChanged.connect(self.on_terraclass_municipality_changed)
        
        municipality_layout.addWidget(self.terraclass_municipality_combo)
        municipality_group.setLayout(municipality_layout)
        self.content_layout.addWidget(municipality_group)
        
        # Inicializa valores padrão
        self.terraclass_year = None
        self.terraclass_state = None
        self.terraclass_municipality = None
        
        # Popula anos baseado no bioma selecionado
        self.populate_terraclass_years()
        self.populate_terraclass_states()
        
        # Atualiza interface e notas
        self.update_terraclass_notes()

    def on_theme_changed_responsive(self, theme):
        """Callback RESPONSIVO para mudança de tema"""
        print(f"🔧 DEBUG on_theme_changed_responsive: theme='{theme}'")
        self.selected_theme = theme
        print(f"🔧 DEBUG on_theme_changed_responsive: self.selected_theme='{self.selected_theme}'")
        
        if theme and theme in self.biome_options:
            # Popula e mostra o combo de bioma
            self.biome_combo.clear()
            self.biome_combo.addItem("")
            self.biome_combo.addItems(self.biome_options[theme])
            self.biome_group.setVisible(True)
            
            # TRATAMENTO ESPECIAL PARA TERRACLASS
            if theme == "TERRACLASS":
                # Para TERRACLASS, esconde completamente as opções de corte
                self.cut_group.setVisible(False)
                self.specific_config_widget.setVisible(False)
                
                # Define automaticamente opção IBGE (mas escondida)
                self.cut_option = 3
            else:
                # Para PRODES e DETER, comportamento normal
                # ESCONDE as opções de corte até bioma ser selecionado
                self.cut_group.setVisible(False)
                self.specific_config_widget.setVisible(False)
                
                # Mostra todas as opções novamente
                self.radio_no_cut.setVisible(True)
                self.radio_loaded_layer.setVisible(True)
                self.radio_draw.setVisible(True)
            
            # Limpa seleção anterior de bioma (interface responsiva)
            self.selected_biome = None
            
            # Atualiza notas
            self.update_comprehensive_notes_responsive()
            
            # Ajusta tamanho para acomodar bioma
            QTimer.singleShot(10, self.adjustSize)
            
        else:
            # Esconde tudo exceto tema quando não há tema selecionado
            self.biome_group.setVisible(False)
            self.cut_group.setVisible(False)
            self.specific_config_widget.setVisible(False)
            self.biome_combo.clear()
            
            # Limpa seleções
            self.selected_biome = None
            self.cut_option = None
            
            # Mostra todas as opções de corte novamente
            self.radio_no_cut.setVisible(True)
            self.radio_loaded_layer.setVisible(True)
            self.radio_draw.setVisible(True)
            
            if not theme:
                self.update_notes("💡 DesagregaBiomasBR é um plugin que facilita o acesso e processamento de dados dos principais sistemas de monitoramento ambiental brasileiro: 🌲 PRODES (desmatamento), 🚨 DETER (alertas), 🔥 QUEIMADAS (áreas queimadas) e 🏞️ TERRACLASS (uso da terra).")
            else:
                self.update_comprehensive_notes_responsive()
            
            # Força tamanho mínimo
            QTimer.singleShot(10, self.force_resize_minimal)
        
        # Atualiza botões de navegação
        self.update_navigation_buttons()
        print(f"🔧 DEBUG on_theme_changed_responsive: can_advance = {self.can_advance()}")

    # Mantém função original para compatibilidade
    def on_theme_changed(self, theme):
        """Callback original (compatibilidade) - redireciona para responsivo"""
        self.on_theme_changed_responsive(theme)

    def on_biome_changed_responsive(self, biome):
        """Callback RESPONSIVO para mudança de bioma"""
        print(f"🔧 DEBUG on_biome_changed_responsive: biome='{biome}'")
        print(f"🔧 DEBUG on_biome_changed_responsive: self.selected_biome anterior='{self.selected_biome}'")
        
        # Atualiza selected_biome
        if biome and biome.strip():
            self.selected_biome = biome
            print(f"🔧 DEBUG on_biome_changed_responsive: self.selected_biome atualizado para='{self.selected_biome}'")
            
            # TRATAMENTO ESPECIAL PARA TERRACLASS
            if self.selected_theme == "TERRACLASS":
                # Para TERRACLASS, automaticamente configura IBGE e mostra configurações específicas
                self.cut_option = 3  # Força IBGE
                
                # Esconde opções de corte (não necessárias para TERRACLASS)
                self.cut_group.setVisible(False)
                
                # Limpa e cria configurações TERRACLASS na etapa 1
                self.clear_layout(self.specific_config_layout)
                self.create_terraclass_direct_config()
                self.specific_config_widget.setVisible(True)
                
                print(f"🔧 DEBUG: TERRACLASS - configurações diretas criadas para {biome}")
            else:
                # Para PRODES e DETER, comportamento normal
                # MOSTRA as opções de corte quando bioma é selecionado
                self.cut_group.setVisible(True)
                # Radio "Sem limite" já está marcado por padrão
                self.cut_option = 0  # Sem limite
                
                # Limpa configurações específicas anteriores
                self.clear_layout(self.specific_config_layout)
                self.specific_config_widget.setVisible(False)
            
            # Atualiza notas
            self.update_comprehensive_notes_responsive()
            
            # Ajusta tamanho para acomodar opções de corte
            QTimer.singleShot(10, self.adjustSize)
            
        elif not biome:
            # ESCONDE opções de corte quando bioma é desmarcado
            self.cut_group.setVisible(False)
            self.specific_config_widget.setVisible(False)
            self.selected_biome = None
            self.cut_option = None
            print(f"🔧 DEBUG on_biome_changed_responsive: self.selected_biome limpo")
            
            # Atualiza notas
            self.update_comprehensive_notes_responsive()
            
            # Volta ao tamanho menor
            QTimer.singleShot(10, self.adjustSize)
        
        # Atualiza botões de navegação
        self.update_navigation_buttons()
        print(f"🔧 DEBUG on_biome_changed_responsive: can_advance = {self.can_advance()}")

    # Mantém função original para compatibilidade
    def on_biome_changed(self, biome):
        """Callback original (compatibilidade) - redireciona para responsivo"""
        self.on_biome_changed_responsive(biome)

    def on_cut_option_changed_responsive(self, button):
        """Callback RESPONSIVO para mudança de opção de corte"""
        option_id = self.cut_button_group.id(button)
        self.cut_option = option_id
        print(f"🔧 DEBUG on_cut_option_changed_responsive: option_id='{option_id}'")
        
        # Limpa configurações específicas anteriores
        self.clear_layout(self.specific_config_layout)
        
        if option_id == 0:  # Sem limite de corte
            # ESCONDE configurações específicas para opção "sem limite"
            self.specific_config_widget.setVisible(False)
            print(f"🔧 DEBUG: Sem limite de corte - escondendo configurações específicas")
            
        elif option_id == 1:  # Layer carregado no QGIS
            self.create_loaded_layer_config()
            self.specific_config_widget.setVisible(True)
            print(f"🔧 DEBUG: Layer carregado - mostrando configurações específicas")
            
        elif option_id == 2:  # Desenhar na tela
            self.create_draw_config()
            self.specific_config_widget.setVisible(True)
            print(f"🔧 DEBUG: Desenhar na tela - mostrando configurações específicas")
            
        elif option_id == 3:  # IBGE
            self.create_ibge_config()
            self.specific_config_widget.setVisible(True)
            print(f"🔧 DEBUG: IBGE - mostrando configurações específicas")
        
        # Atualiza notas
        self.update_comprehensive_notes_responsive()
        
        # RESPONSIVIDADE: Ajusta tamanho baseado na opção
        if option_id == 0:
            # Para "Sem limite", compacta interface
            QTimer.singleShot(10, self.adjustSize)
        else:
            # Para outras opções, permite crescimento
            QTimer.singleShot(10, self.adjustSize)
            # Timer adicional para garantir ajuste após carregar configurações
            QTimer.singleShot(50, self.force_resize)

    # Mantém função original para compatibilidade
    def on_cut_option_changed(self, button):
        """Callback original (compatibilidade) - redireciona para responsivo"""
        self.on_cut_option_changed_responsive(button)

    def update_comprehensive_notes_responsive(self):
        """Atualiza as notas de forma RESPONSIVA conforme seleções"""
        notes_parts = []
        
        # Sempre mostra tema se selecionado
        if self.selected_theme:
            notes_parts.append(f"📊 Tema: {self.selected_theme}")
        
        # Mostra bioma apenas se tema estiver selecionado
        if self.selected_biome and self.selected_theme:
            notes_parts.append(f"🌿 Bioma: {self.selected_biome}")
        
        # TRATAMENTO ESPECIAL PARA TERRACLASS
        if self.selected_theme == "TERRACLASS" and self.selected_biome:
            # Para TERRACLASS, sempre mostra "Limites IBGE" e as configurações específicas
            notes_parts.append("🇧🇷 Limite: IBGE")
            
            # Informações de ano
            if hasattr(self, 'terraclass_year') and self.terraclass_year:
                notes_parts.append(f"🗓️ Ano: {self.terraclass_year}")
            
            # Informações de estado
            if hasattr(self, 'terraclass_state') and self.terraclass_state:
                notes_parts.append(f"🏛️ Estado: {self.terraclass_state}")
            
            # Informações de município
            if hasattr(self, 'terraclass_municipality') and self.terraclass_municipality:
                notes_parts.append(f"🏘️ Município: {self.terraclass_municipality}")
        
        # Mostra informações de corte apenas se bioma estiver selecionado E NÃO FOR TERRACLASS
        elif self.cut_option is not None and self.selected_biome:
            if self.cut_option == 0:
                notes_parts.append("🌍 Limite: Todo o bioma (sem corte)")
            elif self.cut_option == 1:
                if self.selected_layer:
                    layer_info = f"📋 Layer: {self.selected_layer.name()}"
                    if self.selected_field:
                        layer_info += f" → Campo: {self.selected_field}"
                        if self.selected_element:
                            layer_info += f" → Elemento: {self.selected_element}"
                    notes_parts.append(layer_info)
                else:
                    notes_parts.append("📋 Limite: Layer do QGIS (selecione um layer)")
            elif self.cut_option == 2:
                if hasattr(self, 'drawn_rectangle') and self.drawn_rectangle:
                    notes_parts.append(f"🎯 Limite: Retângulo desenhado ({self.drawn_rectangle.xMinimum():.3f}, {self.drawn_rectangle.yMinimum():.3f}) - ({self.drawn_rectangle.xMaximum():.3f}, {self.drawn_rectangle.yMaximum():.3f})")
                else:
                    notes_parts.append("🎯 Limite: Desenho na tela (ative a ferramenta)")
            elif self.cut_option == 3:
                # IBGE - informações da seleção hierárquica
                ibge_info = f"🇧🇷 IBGE: {self.ibge_shapefile_name}"
                if hasattr(self, 'ibge_state') and self.ibge_state:
                    ibge_info += f" → {self.ibge_state}"
                    if hasattr(self, 'ibge_municipality') and self.ibge_municipality:
                        ibge_info += f" → {self.ibge_municipality}"
                notes_parts.append(ibge_info)
        
        # Preserva mensagens de debug existentes
        current_text = self.notes_text.toPlainText()
        debug_lines = []
        if current_text:
            lines = current_text.split('\n')
            for line in lines:
                if '📍' in line:  # Preserva linhas de debug BBOX
                    debug_lines.append(line)
        
        # Usa o novo sistema de notas
        if notes_parts:
            config_text = " | ".join(notes_parts)
            self.update_notes(config_text, "config")
        else:
            if not self.selected_theme:
                config_text = "💡 DesagregaBiomasBR é um plugin que facilita o acesso e processamento de dados dos principais sistemas de monitoramento ambiental brasileiro: 🌲 PRODES (desmatamento), 🚨 DETER (alertas), 🔥 QUEIMADAS (áreas queimadas) e 🏞️ TERRACLASS (uso da terra)."
            elif not self.selected_biome:
                config_text = f"📊 Tema: {self.selected_theme} | 🎯 Selecione um bioma/região para continuar"
            else:
                config_text = f"📊 Tema: {self.selected_theme} | 🌿 Bioma: {self.selected_biome} | 🎯 Configure o limite de corte"
            
            self.update_notes(config_text, "config")

    # Mantém função original para compatibilidade
    def update_comprehensive_notes(self):
        """Função original (compatibilidade) - redireciona para responsiva"""
        self.update_comprehensive_notes_responsive()

    def create_loaded_layer_config(self):
        """Cria configurações para layer já carregado"""
        print(f"🎯 DEBUG: create_loaded_layer_config INICIADA")
        config_group = QGroupBox("Configurações de Layer")
        config_layout = QVBoxLayout()
        
        # Lista de layers carregados
        layer_label = QLabel("Layer:")
        self.layer_combo = QComboBox()
        
        # Popula com layers vectoriais carregados
        layers = QgsProject.instance().mapLayers().values()
        vector_layers = [layer for layer in layers if isinstance(layer, QgsVectorLayer)]
        
        self.layer_combo.addItem("")
        for layer in vector_layers:
            self.layer_combo.addItem(layer.name(), layer)
        
        self.layer_combo.currentIndexChanged.connect(self.on_layer_selected)
        print(f"🔗 DEBUG: Sinal layer_combo conectado a on_layer_selected")
        
        config_layout.addWidget(layer_label)
        config_layout.addWidget(self.layer_combo)
        
        # Campo para seleção de atributo
        self.field_label = QLabel("Campo (opcional):")
        self.field_combo = QComboBox()
        self.field_combo.currentTextChanged.connect(self.on_field_selected)
        print(f"🔗 DEBUG: Sinal field_combo conectado a on_field_selected")
        
        config_layout.addWidget(self.field_label)
        config_layout.addWidget(self.field_combo)
        
        # Campo para seleção de elemento
        self.element_label = QLabel("Elemento (opcional):")
        self.element_combo = QComboBox()
        self.element_combo.currentTextChanged.connect(self.on_element_selected)
        print(f"🔗 DEBUG: Sinal element_combo conectado a on_element_selected")
        
        config_layout.addWidget(self.element_label)
        config_layout.addWidget(self.element_combo)
        
        config_group.setLayout(config_layout)
        self.specific_config_layout.addWidget(config_group)
        
        # Inicialmente ocultos
        self.field_label.setVisible(False)
        self.field_combo.setVisible(False)
        self.element_label.setVisible(False)
        self.element_combo.setVisible(False)
        
        # CORREÇÃO: Ajusta tamanho imediatamente após criar as configurações
        self.adjustSize()
        
        # CORREÇÃO MELHORADA: Usa timer para garantir ajuste após processamento completo
        QTimer.singleShot(10, self.force_resize)

    def force_resize(self):
        """Força o redimensionamento da janela"""
        self.content_widget.updateGeometry()
        self.updateGeometry()
        self.adjustSize()
        # Força repaint
        self.repaint()

    def force_resize_minimal(self):
        """Força redimensionamento ao tamanho mínimo (para opção sem limite)"""
        # Remove qualquer tamanho fixo
        self.setMaximumSize(16777215, 16777215)  # Remove limite máximo
        
        # Define tamanho mínimo e redimensiona
        self.resize(600, 450)
        self.content_widget.adjustSize()
        self.adjustSize()
        
        # Força repaint
        self.repaint()
        
        # Define tamanho mínimo apropriado
        self.setMinimumSize(500, 400)

    def create_draw_config(self):
        """Cria configurações para desenho na tela"""
        config_group = QGroupBox("Desenhar Retângulo")
        config_layout = QVBoxLayout()
        
        info_label = QLabel("Clique no botão abaixo para ativar a ferramenta de desenho:")
        draw_button = QPushButton("Ativar Desenho")
        draw_button.clicked.connect(self.activate_drawing_tool)
        
        config_layout.addWidget(info_label)
        config_layout.addWidget(draw_button)
        
        config_group.setLayout(config_layout)
        self.specific_config_layout.addWidget(config_group)
        
        # CORREÇÃO: Ajuste de tamanho consistente
        self.adjustSize()
        QTimer.singleShot(10, self.force_resize)

    def create_ibge_config(self):
        """Cria configurações para shapefile IBGE"""
        if not self.selected_biome:
            info_label = QLabel("Selecione primeiro um bioma/região para ver as opções IBGE disponíveis.")
            self.specific_config_layout.addWidget(info_label)
            self.adjustSize()
            QTimer.singleShot(10, self.force_resize)
            return
            
        # Carrega o shapefile IBGE se ainda não foi carregado
        if not self.ibge_layer:
            self.load_ibge_shapefile()
            
        if not self.ibge_layer:
            error_label = QLabel("❌ Erro ao carregar o shapefile IBGE. Verifique se o arquivo existe na pasta 'shapefile'.")
            self.specific_config_layout.addWidget(error_label)
            self.adjustSize()
            QTimer.singleShot(10, self.force_resize)
            return
            
        config_group = QGroupBox(f"Configurações IBGE - {self.ibge_shapefile_name}")
        config_layout = QVBoxLayout()
        
        # Define automaticamente o bioma/região com base na seleção já feita
        self.ibge_biome_region = self.selected_biome
        
        # Primeira seleção: Estado (filtrado pelo bioma já selecionado)
        self.ibge_state_label = QLabel("Estado:")
        self.ibge_state_combo = QComboBox()
        self.populate_states_combo(self.selected_biome)  # Usa o bioma já selecionado
        self.ibge_state_combo.currentTextChanged.connect(self.on_ibge_state_changed)
        
        config_layout.addWidget(self.ibge_state_label)
        config_layout.addWidget(self.ibge_state_combo)
        
        # Segunda seleção: Município (será populado após seleção do estado)
        self.ibge_municipality_label = QLabel("Município (opcional):")
        self.ibge_municipality_combo = QComboBox()
        self.ibge_municipality_combo.currentTextChanged.connect(self.on_ibge_municipality_changed)
        
        config_layout.addWidget(self.ibge_municipality_label)
        config_layout.addWidget(self.ibge_municipality_combo)
        
        # Inicialmente oculto até seleção do estado
        self.ibge_municipality_label.setVisible(False)
        self.ibge_municipality_combo.setVisible(False)
        
        config_group.setLayout(config_layout)
        self.specific_config_layout.addWidget(config_group)
        
        self.adjustSize()
        QTimer.singleShot(10, self.force_resize)

    def create_terraclass_direct_config(self):
        """Cria configurações TERRACLASS diretamente na etapa 1 (ano, estado, município)"""
        print(f"🔧 DEBUG: create_terraclass_direct_config para bioma {self.selected_biome}")
        
        # Campo: Seleção de Ano
        year_group = QGroupBox("Seleção de Ano")
        year_layout = QVBoxLayout()
        
        self.terraclass_year_combo = QComboBox()
        self.terraclass_year_combo.currentTextChanged.connect(self.on_terraclass_year_changed)
        
        year_layout.addWidget(self.terraclass_year_combo)
        year_group.setLayout(year_layout)
        self.specific_config_layout.addWidget(year_group)
        
        # Campo: Seleção de Estado
        state_group = QGroupBox("Seleção de Estado")
        state_layout = QVBoxLayout()
        
        self.terraclass_state_combo = QComboBox()
        self.terraclass_state_combo.currentTextChanged.connect(self.on_terraclass_state_changed)
        
        state_layout.addWidget(self.terraclass_state_combo)
        state_group.setLayout(state_layout)
        self.specific_config_layout.addWidget(state_group)
        
        # Campo: Seleção de Município (opcional)
        municipality_group = QGroupBox("Seleção de Município (opcional)")
        municipality_layout = QVBoxLayout()
        
        self.terraclass_municipality_combo = QComboBox()
        self.terraclass_municipality_combo.currentTextChanged.connect(self.on_terraclass_municipality_changed)
        
        municipality_layout.addWidget(self.terraclass_municipality_combo)
        municipality_group.setLayout(municipality_layout)
        self.specific_config_layout.addWidget(municipality_group)
        
        # Inicializa valores padrão
        self.terraclass_year = None
        self.terraclass_state = None
        self.terraclass_municipality = None
        
        # Popula anos e estados baseado no bioma selecionado
        self.populate_terraclass_years()
        self.populate_terraclass_states()
        
        # Atualiza interface e notas
        self.update_terraclass_notes()
        
        # Ajusta tamanho da janela
        self.adjustSize()
        QTimer.singleShot(10, self.force_resize)

    def on_layer_selected(self, index):
        """Callback para seleção de layer"""
        print(f"🚨 DEBUG: on_layer_selected CHAMADA com index: {index}")
        if index > 0:
            layer = self.layer_combo.itemData(index)
            self.selected_layer = layer
            
            print(f"🔍 DEBUG: LAYER SELECIONADO: '{layer.name() if layer else 'None'}'")
            print(f"🔍 DEBUG: Layer tem {layer.featureCount() if layer else 0} feições")
            
            # Testa BBOX imediatamente quando layer é selecionado (sem filtro)
            if layer:
                print(f"🔍 DEBUG: TESTANDO BBOX do layer completo...")
                try:
                    # Método direto: pega extent do layer sem usar get_cut_geometry_bbox 
                    extent = layer.extent()
                    if extent and not extent.isEmpty():
                        # Formata como WFS BBOX
                        bbox_wfs = f"{extent.xMinimum():.6f},{extent.yMinimum():.6f},{extent.xMaximum():.6f},{extent.yMaximum():.6f},EPSG:4674"
                        print(f"🔍 DEBUG: BBOX LAYER COMPLETO: {bbox_wfs}")
                        # Adiciona diretamente nas notas
                        current_text = self.notes_text.toPlainText()
                        self.notes_text.setPlainText(current_text + f"\n📍 BBOX Layer Completo: {bbox_wfs}")
                    else:
                        print(f"🔍 DEBUG: BBOX LAYER COMPLETO: Extent vazio")
                        current_text = self.notes_text.toPlainText()
                        self.notes_text.setPlainText(current_text + f"\n📍 BBOX Layer Completo: Extent vazio")
                except Exception as e:
                    print(f"🔍 DEBUG: ERRO ao extrair BBOX: {e}")
                    current_text = self.notes_text.toPlainText()
                    self.notes_text.setPlainText(current_text + f"\n📍 ERRO ao extrair BBOX: {e}")
            
            # Popula campos
            self.field_combo.clear()
            self.field_combo.addItem("")
            
            if layer:
                for field in layer.fields():
                    self.field_combo.addItem(field.name())
                
                self.field_label.setVisible(True)
                self.field_combo.setVisible(True)
                
                # CORREÇÃO 4: Usar notas completas
                self.update_comprehensive_notes()
                
                # CORREÇÃO 2: Ajustar tamanho
                self.adjustSize()
        else:
            self.field_label.setVisible(False)
            self.field_combo.setVisible(False)
            self.element_label.setVisible(False)
            self.element_combo.setVisible(False)
            self.selected_layer = None
            self.selected_field = None
            self.selected_element = None
            self.update_comprehensive_notes()

    def on_field_selected(self, field_name):
        """Callback para seleção de campo"""
        print(f"🚨 DEBUG: on_field_selected CHAMADA com field_name: '{field_name}'")
        self.selected_field = field_name
        
        print(f"🔍 DEBUG: CAMPO SELECIONADO: '{field_name}'")
        
        if field_name and self.selected_layer:
            # Popula elementos únicos do campo
            self.element_combo.clear()
            self.element_combo.addItem("")
            
            unique_values = self.selected_layer.uniqueValues(self.selected_layer.fields().indexFromName(field_name))
            print(f"🔍 DEBUG: Campo '{field_name}' tem {len(unique_values)} valores únicos")
            
            for value in sorted(unique_values):
                if value is not None:
                    self.element_combo.addItem(str(value))
            
            self.element_label.setVisible(True)
            self.element_combo.setVisible(True)
            
            # CORREÇÃO 4: Usar notas completas
            self.update_comprehensive_notes()
            
            # CORREÇÃO 2: Ajustar tamanho
            self.adjustSize()
        else:
            self.element_label.setVisible(False)
            self.element_combo.setVisible(False)
            self.selected_field = None
            self.selected_element = None
            self.update_comprehensive_notes()

    def on_element_selected(self, element):
        """Callback para seleção de elemento"""
        print(f"🚨 DEBUG: on_element_selected CHAMADA com element: '{element}'")
        self.selected_element = element
        print(f"🔍 DEBUG: ELEMENTO SELECIONADO: '{element}'")
        print(f"🔍 DEBUG: Campo atual: '{getattr(self, 'selected_field', 'None')}'")
        print(f"🔍 DEBUG: Layer atual: '{getattr(self, 'selected_layer', 'None')}'")
        
        # Testa BBOX imediatamente para ver se muda
        if hasattr(self, 'selected_layer') and self.selected_layer and hasattr(self, 'selected_field') and self.selected_field and element:
            print(f"🔍 DEBUG: TESTANDO BBOX após seleção do elemento...")
            
            # Testa filtro direto sem usar get_cut_layer
            try:
                # Cria expressão de filtro
                expression = f'"{self.selected_field}" = \'{element}\''
                print(f"🔍 DEBUG: Expressão de filtro: {expression}")
                
                # Aplica filtro
                from qgis.core import QgsFeatureRequest
                request = QgsFeatureRequest().setFilterExpression(expression)
                filtered_layer = self.selected_layer.materialize(request)
                
                if filtered_layer and filtered_layer.featureCount() > 0:
                    print(f"🔍 DEBUG: Layer filtrado criado com {filtered_layer.featureCount()} feições")
                    current_text = self.notes_text.toPlainText()
                    self.notes_text.setPlainText(current_text + f"\n📍 Layer filtrado: {filtered_layer.featureCount()} feições para '{element}'")
                    
                    # Calcula BBOX do elemento específico
                    extent = filtered_layer.extent()
                    if extent and not extent.isEmpty():
                        bbox_wfs = f"{extent.xMinimum():.6f},{extent.yMinimum():.6f},{extent.xMaximum():.6f},{extent.yMaximum():.6f},EPSG:4674"
                        print(f"🔍 DEBUG: BBOX ELEMENTO ESPECÍFICO: {bbox_wfs}")
                        current_text = self.notes_text.toPlainText()
                        self.notes_text.setPlainText(current_text + f"\n📍 BBOX Elemento '{element}': {bbox_wfs}")
                    else:
                        print(f"🔍 DEBUG: BBOX ELEMENTO ESPECÍFICO: Extent vazio")
                        current_text = self.notes_text.toPlainText()
                        self.notes_text.setPlainText(current_text + f"\n📍 BBOX Elemento '{element}': Extent vazio")
                else:
                    print(f"🔍 DEBUG: Nenhuma feição encontrada para '{element}'")
                    current_text = self.notes_text.toPlainText()
                    self.notes_text.setPlainText(current_text + f"\n📍 ERRO: Nenhuma feição encontrada para '{element}'")
                    
            except Exception as e:
                print(f"🔍 DEBUG: ERRO ao filtrar elemento: {e}")
                current_text = self.notes_text.toPlainText()
                self.notes_text.setPlainText(current_text + f"\n📍 ERRO ao filtrar elemento: {e}")
        elif element:
            print(f"🔍 DEBUG: Elemento selecionado mas faltam layer/campo")
            current_text = self.notes_text.toPlainText()
            self.notes_text.setPlainText(current_text + f"\n📍 Elemento '{element}' selecionado (aguardando layer/campo)")
        
        # CORREÇÃO 4: Usar notas completas
        self.update_comprehensive_notes()

    def on_wfs_type_changed(self, wfs_type):
        """Callback para mudança do tipo WFS - conecta automaticamente"""
        print(f"🔧 DEBUG: on_wfs_type_changed chamada com: '{wfs_type}'")
        print(f"🔧 DEBUG: selected_biome atual: '{self.selected_biome}'")
        
        if wfs_type:
            print(f"🔧 DEBUG: wfs_type válido, chamando connect_wfs...")
            # Conecta automaticamente quando tipo for selecionado
            self.connect_wfs()
        else:
            print(f"🔧 DEBUG: wfs_type vazio, limpando campos...")
            # Limpa campos se tipo for deselecionado
            if hasattr(self, 'wfs_field_combo'):
                self.wfs_field_combo.clear()
                self.wfs_field_label.setVisible(False)
                self.wfs_field_combo.setVisible(False)
                self.wfs_element_label.setVisible(False)
                self.wfs_element_combo.setVisible(False)
        
        # Atualizar notas
        self.update_comprehensive_notes()

    # WFS Real direto - sem fallbacks simulados
    def connect_wfs(self):
        """Conecta diretamente ao serviço WFS real"""
        print(f"🔧 DEBUG: connect_wfs iniciada")
        
        wfs_type = self.wfs_type_combo.currentText()
        print(f"🔧 DEBUG: wfs_type obtido: '{wfs_type}'")
        
        # Mapeia os tipos para as chaves do dicionário  
        type_mapping = {
            "Unidades de Conservação": "conservation_units",
            "Terras Indígenas": "indigenous_area", 
            "Municípios": "municipalities",
            "Estados": "states"
        }
        
        type_key = type_mapping.get(wfs_type)
        print(f"🔧 DEBUG: type_key mapeado: '{type_key}'")
        if not type_key:
            print(f"🔧 DEBUG: type_key não encontrado, retornando")
            return
            
        print(f"🔧 DEBUG: Verificando se bioma '{self.selected_biome}' existe em wfs_urls[{type_key}]")
        if self.selected_biome not in self.wfs_urls[type_key]:
            print(f"🔧 DEBUG: Bioma não encontrado em wfs_urls")
            print(f"🔧 DEBUG: Biomas disponíveis: {list(self.wfs_urls[type_key].keys())}")
            self.update_notes(f"❌ WFS não disponível para {wfs_type} no bioma {self.selected_biome}")
            return
            
        base_url = self.wfs_urls[type_key][self.selected_biome]
        print(f"🔧 DEBUG: URL WFS encontrada: {base_url}")
        
        self.update_notes(f"🔄 Conectando ao WFS: {wfs_type} - {self.selected_biome}...")
        print(f"🔧 DEBUG: Chamando create_wfs_layer...")
        
        # ESTRATÉGIA 1: Tenta função robusta primeiro
        wfs_layer = self.create_wfs_layer(base_url, type_key)
        
        # ESTRATÉGIA 2: Se falhou, tenta função simples
        if not wfs_layer or not wfs_layer.isValid() or wfs_layer.featureCount() == 0:
            print(f"🔧 DEBUG: Função robusta falhou, tentando função simplificada...")
            wfs_layer = self.create_simple_wfs_layer(base_url, type_key)
        
        if wfs_layer and wfs_layer.isValid() and wfs_layer.featureCount() > 0:
            print(f"🔧 DEBUG: WFS conectado com sucesso!")
            # WFS conectado com sucesso
            self.wfs_layer = wfs_layer
            
            # Obtém campos reais da camada
            fields = [field.name() for field in wfs_layer.fields()]
            print(f"🔧 DEBUG: Campos obtidos: {fields}")
            
            # Popula combo de campos com dados reais
            self.wfs_field_combo.clear()
            self.wfs_field_combo.addItem("")
            self.wfs_field_combo.addItems(fields)
            
            # Conecta sinal para povoar elementos reais
            self.wfs_field_combo.currentTextChanged.connect(self.on_wfs_field_selected_real)
            
            # Mostra campos de configuração
            self.wfs_field_label.setVisible(True)
            self.wfs_field_combo.setVisible(True)
            
            self.update_notes(f"✅ WFS conectado: {wfs_layer.featureCount()} feições de {wfs_type}")
            self.update_comprehensive_notes()
            
            # Ajustar tamanho após mostrar campos WFS
            self.adjustSize()
            QTimer.singleShot(10, self.force_resize)
            
        else:
            print(f"🔧 DEBUG: Falha na conexão WFS")
            # Falha na conexão WFS
            self.update_notes(f"❌ Falha na conexão WFS: {wfs_type} - {self.selected_biome}")
            
            # Limpa campos
            if hasattr(self, 'wfs_field_combo'):
                self.wfs_field_combo.clear()
                self.wfs_field_label.setVisible(False)
                self.wfs_field_combo.setVisible(False)
                self.wfs_element_label.setVisible(False)
                self.wfs_element_combo.setVisible(False)

    def create_wfs_layer(self, base_url, type_key):
        """Cria layer WFS com múltiplas estratégias para máxima compatibilidade"""
        
        print(f"🔧 DEBUG: Iniciando create_wfs_layer com URL: {base_url}")
        
        try:
            # Extrai namespace e layer name da URL
            url_parts = base_url.split('/geoserver/')[1].split('/ows')[0].split('/')
            if len(url_parts) >= 2:
                namespace = url_parts[0]
                layer_name = url_parts[1]
                full_type_name = f"{namespace}:{layer_name}"
                print(f"🔍 TypeName extraído: {full_type_name}")
                print(f"🔗 URL base: {base_url}")
            else:
                print(f"❌ URL inválida: {base_url}")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao extrair typeName: {str(e)}")
            return None
        
        # ESTRATÉGIA 1: Tenta múltiplas versões WFS
        wfs_versions = ["1.0.0", "1.1.0", "2.0.0"]
        
        # ESTRATÉGIA 2: Múltiplos formatos (ordem de preferência)
        formats_strategy = [
            ("text/xml; subtype=gml/2.1.2", "GML2"),
            ("text/xml; subtype=gml/3.1.1", "GML3"),
            ("application/gml+xml", "GML"),
            ("text/xml", "XML"),
            ("application/json", "GeoJSON")
        ]
        
        # ESTRATÉGIA 3: Múltiplas formas de especificar o layer
        layer_strategies = [
            full_type_name,  # namespace:layer (padrão)
            layer_name,      # apenas layer name
            namespace + ":" + layer_name.replace("_", ":")  # tentativa alternativa
        ]
        
        attempt_count = 0
        
        for version in wfs_versions:
            for layer_strategy in layer_strategies:
                for output_format, format_name in formats_strategy:
                    attempt_count += 1
                    
                    try:
                        # Monta URL WFS com estratégia atual
                        wfs_url = f"{base_url}?service=WFS&version={version}&request=GetFeature&typeName={layer_strategy}&outputFormat={output_format}&srsName=EPSG:4674"
                        
                        print(f"🌐 Tentativa {attempt_count}: {format_name} (v{version}) - {layer_strategy}")
                        print(f"🔗 URL: {wfs_url}")
                        
                        # ESTRATÉGIA 4: Configurações diferentes de layer
                        layer_configs = [
                            # Configuração 1: WFS direto
                            {
                                'url': wfs_url,
                                'name': f"WFS_{type_key}_{attempt_count}",
                                'provider': "WFS"
                            },
                            # Configuração 2: WFS com opções
                            {
                                'url': f"url='{wfs_url}' typename='{layer_strategy}' version='{version}'",
                                'name': f"WFS_OPT_{type_key}_{attempt_count}",
                                'provider': "WFS"
                            }
                        ]
                        
                        for config in layer_configs:
                            try:
                                print(f"   🔄 Testando configuração: {config['provider']}")
                                
                                # Cria layer WFS
                                temp_layer = QgsVectorLayer(config['url'], config['name'], config['provider'])
                                
                                # Verifica se layer é válida
                                if temp_layer.isValid():
                                    feature_count = temp_layer.featureCount()
                                    print(f"   📊 Layer válida com {feature_count} feições")
                                    
                                    if feature_count > 0:
                                        fields = [f.name() for f in temp_layer.fields()]
                                        print(f"   ✅ SUCESSO! {feature_count} feições carregadas")
                                        print(f"   📋 Campos disponíveis: {fields}")
                                        return temp_layer
                                    else:
                                        print(f"   ⚠️ Layer válida mas vazia")
                                else:
                                    error = temp_layer.error().message() if temp_layer.error() else "Erro desconhecido"
                                    print(f"   ❌ Layer inválida: {error}")
                                    
                            except Exception as e:
                                print(f"   ❌ Erro na configuração: {str(e)}")
                                continue
                                
                    except Exception as e:
                        print(f"❌ Erro na tentativa {attempt_count}: {str(e)}")
                        continue
        
        print(f"❌ Todas as {attempt_count} tentativas falharam para {full_type_name}")
        
        # ESTRATÉGIA 5: Teste de conectividade básica
        print(f"🔍 Testando conectividade básica com {base_url}")
        try:
            test_url = f"{base_url}?service=WFS&version=1.0.0&request=GetCapabilities"
            print(f"🌐 Teste GetCapabilities: {test_url}")
            
            # Tenta criar uma layer apenas para testar conectividade
            test_layer = QgsVectorLayer(test_url, "test_connectivity", "WFS")
            if test_layer.isValid():
                print(f"✅ Conectividade OK - servidor WFS responde")
            else:
                print(f"❌ Problema de conectividade ou servidor indisponível")
                
        except Exception as e:
            print(f"❌ Erro no teste de conectividade: {str(e)}")
        
        return None

    def on_wfs_field_selected_real(self, field_name):
        """Callback para seleção de campo WFS real"""
        print(f"🔧 DEBUG: Campo selecionado: '{field_name}'")
        print(f"🔧 DEBUG: WFS Layer válida? {hasattr(self, 'wfs_layer') and self.wfs_layer and self.wfs_layer.isValid()}")
        print(f"🔧 DEBUG: WFS Layer featureCount: {self.wfs_layer.featureCount() if hasattr(self, 'wfs_layer') and self.wfs_layer else 'N/A'}")
        
        if not field_name:
            print(f"🔧 DEBUG: Campo vazio, ocultando elementos")
            self.wfs_element_label.setVisible(False)
            self.wfs_element_combo.setVisible(False)
            self.adjustSize()
            QTimer.singleShot(10, self.force_resize)
            self.update_comprehensive_notes()
            return
            
        # SEMPRE mostra o campo elemento primeiro
        self.wfs_element_label.setVisible(True)
        self.wfs_element_combo.setVisible(True)
        self.wfs_element_combo.clear()
        self.wfs_element_combo.addItem("🔄 Carregando...")
        
        # Força atualização visual imediata
        self.wfs_element_label.repaint()
        self.wfs_element_combo.repaint()
        self.adjustSize()
        
        print(f"✅ DEBUG: Campo 'Elemento' MOSTRADO imediatamente")
        
        # Tenta obter valores reais com múltiplas estratégias
        real_values = self.get_real_field_values(field_name)
        
        # Limpa o combo e popula com dados reais ou padrão
        self.wfs_element_combo.clear()
        self.wfs_element_combo.addItem("")  # Opção vazia
        
        if real_values:
            print(f"✅ DEBUG: Obtidos {len(real_values)} valores reais: {real_values[:3]}...")
            self.wfs_element_combo.addItems(real_values)
            self.update_notes(f"✅ WFS: {len(real_values)} elementos carregados para {field_name}")
        else:
            print(f"⚠️ DEBUG: Nenhum valor real obtido para {field_name}")
            # Em vez de valores padrão, mostra mensagem de erro
            error_messages = ["❌ Falha ao carregar dados", "Tente outro campo", "Verifique conexão WFS"]
            self.wfs_element_combo.addItems(error_messages)
            self.update_notes(f"❌ Falha ao carregar elementos de {field_name} - erro de conexão WFS")
        
        # Conecta sinal
        try:
            self.wfs_element_combo.currentTextChanged.disconnect()
        except:
            pass
        self.wfs_element_combo.currentTextChanged.connect(self.on_wfs_element_selected_real)
        
        print(f"🎯 DEBUG: Campo populado com {self.wfs_element_combo.count()-1} opções")
        
        # Atualizar notas
        self.update_comprehensive_notes()

    def get_real_field_values(self, field_name):
        """Tenta obter valores REAIS do campo usando múltiplas estratégias"""
        print(f"🔍 DEBUG: === FORÇANDO LEITURA DE VALORES REAIS PARA '{field_name}' ===")
        
        # NOVA ESTRATÉGIA 0: Tenta criar layer mínima nova
        print(f"🔄 DEBUG: ESTRATÉGIA 0 - Criando layer WFS mínima nova...")
        values = self.create_minimal_wfs_layer(field_name)
        if values:
            print(f"✅ DEBUG: ESTRATÉGIA 0 SUCESSO! {len(values)} valores REAIS obtidos")
            return values
        
        # ESTRATÉGIA 1: Força leitura da layer atual ignorando erros
        print(f"🔄 DEBUG: ESTRATÉGIA 1 - Forçando leitura da layer WFS atual...")
        values = self.force_read_current_layer(field_name)
        if values:
            print(f"✅ DEBUG: ESTRATÉGIA 1 SUCESSO! {len(values)} valores REAIS obtidos")
            return values
        
        # ESTRATÉGIA 2: Recarrega layer com parâmetros diferentes
        print(f"🔄 DEBUG: ESTRATÉGIA 2 - Recarregando WFS com novos parâmetros...")
        values = self.reload_wfs_with_different_params(field_name)
        if values:
            print(f"✅ DEBUG: ESTRATÉGIA 2 SUCESSO! {len(values)} valores REAIS obtidos")
            return values
            
        # ESTRATÉGIA 3: Força download direto via HTTP
        print(f"🔄 DEBUG: ESTRATÉGIA 3 - Download direto via HTTP...")
        values = self.force_http_download(field_name)
        if values:
            print(f"✅ DEBUG: ESTRATÉGIA 3 SUCESSO! {len(values)} valores REAIS obtidos")
            return values
        
        print(f"❌ DEBUG: === FALHA AO OBTER VALORES REAIS ===")
        return []

    def create_minimal_wfs_layer(self, field_name):
        """Cria uma layer WFS mínima nova apenas para extrair valores do campo"""
        try:
            print(f"🔧 DEBUG: Criando layer WFS mínima para campo '{field_name}'...")
            
            wfs_type = self.wfs_type_combo.currentText()
            type_mapping = {
                "Unidades de Conservação": "conservation_units",
                "Terras Indígenas": "indigenous_area", 
                "Municípios": "municipalities",
                "Estados": "states"
            }
            
            type_key = type_mapping.get(wfs_type)
            if not type_key or self.selected_biome not in self.wfs_urls[type_key]:
                print(f"❌ DEBUG: URL não disponível para {wfs_type} - {self.selected_biome}")
                return []
                
            base_url = self.wfs_urls[type_key][self.selected_biome]
            
            # Extrai namespace e layer name
            try:
                url_parts = base_url.split('/geoserver/')[1].split('/ows')[0].split('/')
                namespace = url_parts[0]
                layer_name = url_parts[1]
                print(f"🔧 DEBUG: Namespace: {namespace}, Layer: {layer_name}")
            except:
                print(f"❌ DEBUG: Erro ao extrair namespace/layer da URL")
                return []
            
            # Estratégia super mínima - apenas 1 feição, apenas o campo desejado
            minimal_urls = [
                # Tenta com propertyName para pegar apenas o campo desejado
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&propertyName={field_name}&srsName=EPSG:4674",
                # Tenta formato JSON que pode ser mais tolerante
                f"{base_url}?service=WFS&version=1.1.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=application/json&propertyName={field_name}&srsName=EPSG:4674",
                # Tenta com srsName especificado
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&srsName=EPSG:4674"
            ]
            
            unique_values = set()
            
            for i, test_url in enumerate(minimal_urls, 1):
                try:
                    print(f"🌐 DEBUG: Tentativa mínima {i}/3...")
                    
                    # Cria layer temporária
                    temp_layer = QgsVectorLayer(test_url, f"minimal_{i}", "WFS")
                    
                    # Tenta capturar dados imediatamente, mesmo antes de validação completa
                    if temp_layer:
                        # Busca o campo mesmo que a layer não seja "válida"
                        fields = temp_layer.fields()
                        field_names = [f.name() for f in fields]
                        print(f"🔧 DEBUG: Campos encontrados: {field_names}")
                        
                        # Tenta encontrar o campo
                        field_idx = -1
                        for idx, f in enumerate(fields):
                            if f.name() == field_name or field_name.lower() in f.name().lower():
                                field_idx = idx
                                actual_field_name = f.name()
                                print(f"✅ DEBUG: Campo encontrado: {actual_field_name} (índice {field_idx})")
                                break
                        
                        if field_idx >= 0:
                            # Tenta obter features mesmo com erros
                            try:
                                feature_count = 0
                                features = temp_layer.getFeatures()
                                
                                for feat in features:
                                    try:
                                        # Múltiplas tentativas de acesso
                                        val = None
                                        try:
                                            val = feat.attribute(actual_field_name)
                                        except:
                                            try:
                                                val = feat[field_idx]
                                            except:
                                                try:
                                                    attrs = feat.attributes()
                                                    if len(attrs) > field_idx:
                                                        val = attrs[field_idx]
                                                except:
                                                    pass
                                        
                                        if val is not None and str(val).strip():
                                            unique_values.add(str(val).strip())
                                            feature_count += 1
                                            
                                    except Exception as e:
                                        continue
                                
                                if unique_values:
                                    print(f"✅ DEBUG: {len(unique_values)} valores extraídos na tentativa {i}")
                                    
                            except Exception as e:
                                print(f"⚠️ DEBUG: Erro ao iterar features: {str(e)}")
                    
                    # Deleta a layer temporária
                    del temp_layer
                    
                except Exception as e:
                    print(f"❌ DEBUG: Erro na tentativa mínima {i}: {str(e)}")
                    continue
            
            if unique_values:
                result = sorted(list(unique_values))
                print(f"✅ DEBUG: Total de {len(result)} valores únicos extraídos")
                return result
            else:
                print(f"❌ DEBUG: Nenhum valor extraído na estratégia mínima")
                return []
                
        except Exception as e:
            print(f"❌ DEBUG: Erro geral na estratégia mínima: {str(e)}")
            return []

    def force_read_current_layer(self, field_name):
        """Força leitura da layer atual ignorando warnings e erros"""
        try:
            if not hasattr(self, 'wfs_layer') or not self.wfs_layer:
                print(f"⚠️ DEBUG: Layer WFS não existe")
                return []
            
            # Ignora validação e força leitura
            print(f"🔧 DEBUG: Forçando leitura mesmo com erros...")
            
            field_index = -1
            # Busca o campo de forma mais robusta
            for i, field in enumerate(self.wfs_layer.fields()):
                if field.name() == field_name:
                    field_index = i
                    break
                    
            if field_index < 0:
                print(f"⚠️ DEBUG: Campo não encontrado, tentando por nome similar...")
                # Tenta buscar por nome similar
                for i, field in enumerate(self.wfs_layer.fields()):
                    if field_name.lower() in field.name().lower():
                        field_index = i
                        field_name = field.name()
                        print(f"✅ DEBUG: Campo similar encontrado: {field_name}")
                        break
                        
            if field_index < 0:
                return []
            
            unique_values = set()
            error_count = 0
            success_count = 0
            
            # Força iteração com timeout e tratamento de erros
            print(f"🔧 DEBUG: Tentando ler feições (ignorando erros)...")
            
            # Tenta diferentes formas de acessar as feições
            try:
                # Método 1: getFeatures direto
                features = self.wfs_layer.getFeatures()
                for i, feature in enumerate(features):
                    try:
                        # Tenta várias formas de acessar o valor
                        value = None
                        try:
                            value = feature.attribute(field_name)
                        except:
                            try:
                                value = feature[field_index]
                            except:
                                try:
                                    value = feature.attributes()[field_index]
                                except:
                                    pass
                                    
                        if value is not None and str(value).strip():
                            unique_values.add(str(value).strip())
                            success_count += 1
                            if success_count % 10 == 0:
                                print(f"   ✅ {success_count} valores lidos...")
                    except Exception as e:
                        error_count += 1
                        if error_count <= 3:
                            print(f"   ⚠️ Erro na feição {i}: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"⚠️ DEBUG: Erro no método 1: {str(e)}")
                
                # Método 2: Tenta com QgsFeatureRequest
                try:
                    print(f"🔧 DEBUG: Tentando método alternativo...")
                    request = QgsFeatureRequest()
                    request.setFlags(QgsFeatureRequest.NoGeometry)
                    request.setSubsetOfAttributes([field_index])
                    
                    features = self.wfs_layer.getFeatures(request)
                    for feature in features:
                        try:
                            value = feature[field_index]
                            if value is not None and str(value).strip():
                                unique_values.add(str(value).strip())
                        except:
                            continue
                            
                except Exception as e2:
                    print(f"⚠️ DEBUG: Erro no método 2: {str(e2)}")
            
            if unique_values:
                result = sorted(list(unique_values))
                print(f"✅ DEBUG: {len(result)} valores únicos extraídos com {error_count} erros ignorados")
                return result
            else:
                print(f"❌ DEBUG: Nenhum valor extraído após {error_count} erros")
                return []
                
        except Exception as e:
            print(f"❌ DEBUG: Erro geral forçando leitura: {str(e)}")
            return []

    def reload_wfs_with_different_params(self, field_name):
        """Recarrega WFS com parâmetros diferentes para contornar erro XML"""
        try:
            print(f"🔧 DEBUG: Tentando recarregar WFS com parâmetros alternativos...")
            
            wfs_type = self.wfs_type_combo.currentText()
            type_mapping = {
                "Unidades de Conservação": "conservation_units",
                "Terras Indígenas": "indigenous_area", 
                "Municípios": "municipalities",
                "Estados": "states"
            }
            
            type_key = type_mapping.get(wfs_type)
            if not type_key or self.selected_biome not in self.wfs_urls[type_key]:
                return []
                
            base_url = self.wfs_urls[type_key][self.selected_biome]
            
            # Extrai namespace e layer name
            url_parts = base_url.split('/geoserver/')[1].split('/ows')[0].split('/')
            namespace = url_parts[0]
            layer_name = url_parts[1]
            
            # Tenta diferentes configurações de URL
            test_urls = [
                # JSON com diferentes versões
                f"{base_url}?service=WFS&version=2.0.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=application/json&propertyName={field_name}",
                f"{base_url}?service=WFS&version=1.1.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=json&propertyName={field_name}",
                # CSV format (mais simples de parsear)
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=csv",
                # GML com limite pequeno
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}"
            ]
            
            unique_values = set()
            
            for i, test_url in enumerate(test_urls, 1):
                print(f"🌐 DEBUG: Tentativa {i}/{len(test_urls)}: {test_url[:100]}...")
                
                try:
                    # Cria layer temporária
                    temp_layer = QgsVectorLayer(test_url, f"temp_reload_{i}", "WFS")
                    
                    # Aguarda um momento para carregamento
                    QgsApplication.processEvents()
                    
                    if temp_layer.featureCount() > 0:
                        print(f"✅ DEBUG: Layer carregada com {temp_layer.featureCount()} feições")
                        
                        # Busca o campo
                        field_index = -1
                        for idx, field in enumerate(temp_layer.fields()):
                            if field.name() == field_name or field_name.lower() in field.name().lower():
                                field_index = idx
                                break
                                
                        if field_index >= 0:
                            unique_values = set()
                            for feature in temp_layer.getFeatures():
                                try:
                                    value = feature[field_index]
                                    if value is not None and str(value).strip():
                                        unique_values.add(str(value).strip())
                                except:
                                    continue
                                    
                            if unique_values:
                                result = sorted(list(unique_values))
                                print(f"✅ DEBUG: {len(result)} valores extraídos via reload")
                                return result
                                
                except Exception as e:
                    print(f"⚠️ DEBUG: Tentativa {i} falhou: {str(e)}")
                    continue
                    
            return []
            
        except Exception as e:
            print(f"❌ DEBUG: Erro no reload: {str(e)}")
            return []

    def force_http_download(self, field_name):
        """Força download direto via HTTP e processa resposta manualmente"""
        try:
            print(f"🔧 DEBUG: Tentando download HTTP direto...")
            
            from qgis.PyQt.QtCore import QUrl, QEventLoop
            from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
            
            wfs_type = self.wfs_type_combo.currentText()
            type_mapping = {
                "Unidades de Conservação": "conservation_units",
                "Terras Indígenas": "indigenous_area", 
                "Municípios": "municipalities",
                "Estados": "states"
            }
            
            type_key = type_mapping.get(wfs_type)
            if not type_key or self.selected_biome not in self.wfs_urls[type_key]:
                return []
                
            base_url = self.wfs_urls[type_key][self.selected_biome]
            
            # Extrai namespace e layer
            try:
                url_parts = base_url.split('/geoserver/')[1].split('/ows')[0].split('/')
                namespace = url_parts[0]
                layer_name = url_parts[1]
            except:
                print(f"❌ DEBUG: Erro ao extrair namespace/layer")
                return []
            
            # Múltiplas URLs para testar
            test_urls = [
                # GetCapabilities primeiro para verificar formatos disponíveis
                f"{base_url}?service=WFS&request=GetCapabilities",
                # Tenta pegar apenas 1 feature em diferentes formatos
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&srsName=EPSG:4674",
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=GML2&srsName=EPSG:4674",
                f"{base_url}?service=WFS&version=1.1.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=text/xml&srsName=EPSG:4674",
                # Tenta JSON explicitamente
                f"{base_url}?service=WFS&version=2.0.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=application/json&srsName=EPSG:4674",
                # Tenta GeoJSON
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=json&srsName=EPSG:4674"
            ]
            
            unique_values = set()
            
            for i, test_url in enumerate(test_urls):
                try:
                    print(f"🌐 DEBUG: Tentativa HTTP {i+1}/{len(test_urls)}: {test_url[:80]}...")
                    
                    # Cria request
                    request = QNetworkRequest(QUrl(test_url))
                    request.setRawHeader(b"User-Agent", b"QGIS")
                    reply = self.network_manager.get(request)
                    
                    # Aguarda resposta
                    loop = QEventLoop()
                    reply.finished.connect(loop.quit)
                    loop.exec_()
                    
                    if reply.error() == QNetworkReply.NoError:
                        # Lê resposta
                        data = reply.readAll()
                        
                        # Tenta decodificar com diferentes encodings
                        text = ""
                        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']:
                            try:
                                text = data.data().decode(encoding, errors='ignore')
                                break
                            except:
                                continue
                        
                        print(f"✅ DEBUG: {len(text)} bytes baixados")
                        
                        # Mostra primeiros caracteres para debug
                        print(f"🔍 DEBUG: Primeiros 200 caracteres: {text[:200]}")
                        
                        # Se for GetCapabilities, apenas mostra formatos disponíveis
                        if "GetCapabilities" in test_url:
                            import re
                            formats = re.findall(r'<Format>([^<]+)</Format>', text)
                            if formats:
                                print(f"📋 DEBUG: Formatos WFS disponíveis: {formats}")
                            continue
                        
                        # Procura valores do campo no texto
                        if field_name and len(text) > 0:
                            import re
                            
                            # Lista expandida de padrões para buscar
                            patterns = [
                                # XML/GML patterns
                                f'<[^:>]*:{field_name}>([^<]+)<',  # namespace:field
                                f'<{field_name}>([^<]+)</{field_name}>',  # field direto
                                f'<[^>]*{field_name}[^>]*>([^<]+)<',  # field em qualquer tag
                                f'{field_name}="([^"]+)"',  # atributo
                                # JSON patterns
                                f'"{field_name}"\\s*:\\s*"([^"]+)"',  # JSON string
                                f'"{field_name}"\\s*:\\s*([^,\\]\\}}]+)',  # JSON any value
                                f"'{field_name}'\\s*:\\s*'([^']+)'",  # JSON single quotes
                                # CSV/texto patterns
                                f'{field_name}[=:]\\s*([^,;\\n]+)',  # key=value ou key:value
                                # Busca mais genérica
                                f'\\b{field_name}\\b[^>]*>([^<]+)',  # palavra seguida de valor
                            ]
                            
                            # Tenta também variações do nome do campo
                            field_variations = [
                                field_name,
                                field_name.lower(),
                                field_name.upper(),
                                field_name.replace('_', ''),
                                field_name.replace('_', '-')
                            ]
                            
                            for field_var in field_variations:
                                for pattern in patterns:
                                    try:
                                        actual_pattern = pattern.replace(field_name, field_var)
                                        matches = re.findall(actual_pattern, text, re.IGNORECASE | re.MULTILINE)
                                        
                                        for match in matches:
                                            if match and str(match).strip() and len(str(match).strip()) > 0:
                                                value = str(match).strip()
                                                # Limpa valores comuns de XML
                                                value = value.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                                                if value and value not in ['null', 'NULL', 'None', '']:
                                                    unique_values.add(value)
                                                    if len(unique_values) <= 5:  # Mostra primeiros valores
                                                        print(f"   ✅ Valor encontrado: '{value}'")
                                    except Exception as re_error:
                                        continue
                            
                            print(f"🔧 DEBUG: {len(unique_values)} valores únicos encontrados até agora")
                    else:
                        error_string = reply.errorString()
                        print(f"❌ DEBUG: Erro HTTP: {error_string}")
                        
                        # Mesmo com erro, tenta ler conteúdo
                        data = reply.readAll()
                        if data.size() > 0:
                            error_text = data.data().decode('utf-8', errors='ignore')
                            print(f"🔍 DEBUG: Resposta de erro: {error_text[:200]}")
                    
                    reply.deleteLater()
                    
                except Exception as e:
                    print(f"❌ DEBUG: Erro na tentativa HTTP {i+1}: {str(e)}")
                    continue
            
            if unique_values:
                result = sorted(list(unique_values))
                print(f"✅ DEBUG: Total de {len(result)} valores únicos extraídos via HTTP")
                print(f"📋 DEBUG: Primeiros valores: {result[:5]}")
                return result
            else:
                print(f"❌ DEBUG: Nenhum valor extraído via HTTP")
                
                # Última tentativa desesperada - tenta acessar diretamente o GeoServer REST API
                print(f"🔧 DEBUG: Tentando GeoServer REST API como última opção...")
                rest_url = base_url.replace('/ows', f'/wfs?service=WFS&version=1.0.0&request=DescribeFeatureType&typeName={namespace}:{layer_name}')
                print(f"🌐 DEBUG: REST URL: {rest_url[:80]}...")
                
                try:
                    request = QNetworkRequest(QUrl(rest_url))
                    reply = self.network_manager.get(request)
                    loop = QEventLoop()
                    reply.finished.connect(loop.quit)
                    loop.exec_()
                    
                    if reply.error() == QNetworkReply.NoError:
                        data = reply.readAll().data().decode('utf-8', errors='ignore')
                        print(f"📋 DEBUG: DescribeFeatureType response: {data[:300]}")
                    
                    reply.deleteLater()
                except:
                    pass
                
            return []
            
        except Exception as e:
            print(f"❌ DEBUG: Erro geral no download HTTP: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def get_known_values_for_wfs_type(self, field_name):
        """REMOVIDO - Não usar valores fictícios"""
        return []

    def get_default_options_for_field(self, field_name):
        """Retorna mensagem informativa em vez de valores fictícios"""
        return ["Erro ao carregar dados do WFS", "Verifique a conexão", "Tente recarregar"]

    def on_wfs_element_selected_real(self, element):
        """Callback para seleção de elemento WFS real"""
        print(f"🔧 DEBUG: on_wfs_element_selected_real chamada com elemento: '{element}'")
        
        self.wfs_element = element
        
        if element:
            print(f"✅ DEBUG: Elemento selecionado: '{element}'")
        else:
            print(f"🔧 DEBUG: Elemento vazio/desmarcado")
            
        self.update_comprehensive_notes()

    def get_cut_layer(self):
        """Retorna a layer de corte baseada na opção selecionada"""
        print(f"🔧 DEBUG get_cut_layer: Iniciando...")
        print(f"🔧 DEBUG get_cut_layer: cut_option = {getattr(self, 'cut_option', 'UNDEFINED')}")
        
        if not hasattr(self, 'cut_option'):
            print(f"❌ DEBUG get_cut_layer: cut_option não existe!")
            return None
            
        if self.cut_option == 0:
            # Sem limite de corte
            print(f"🔧 DEBUG get_cut_layer: cut_option=0 (sem corte)")
            return None
            
        elif self.cut_option == 1:
            # Layer carregado no QGIS
            print(f"🔧 DEBUG get_cut_layer: cut_option=1 (layer carregado)")
            print(f"🔧 DEBUG get_cut_layer: selected_layer = {getattr(self, 'selected_layer', 'UNDEFINED')}")
            print(f"🔧 DEBUG get_cut_layer: selected_field = {getattr(self, 'selected_field', 'UNDEFINED')}")
            print(f"🔧 DEBUG get_cut_layer: selected_element = {getattr(self, 'selected_element', 'UNDEFINED')}")
            
            if self.selected_layer:
                if self.selected_field and self.selected_element:
                    # Cria layer filtrada
                    try:
                        print(f"🔧 DEBUG get_cut_layer: Tentando criar layer filtrada...")
                        expression = f'"{self.selected_field}" = \'{self.selected_element}\''
                        print(f"🔧 DEBUG get_cut_layer: Expression = {expression}")
                        
                        request = QgsFeatureRequest().setFilterExpression(expression)
                        filtered_layer = self.selected_layer.materialize(request)
                        
                        if filtered_layer and filtered_layer.isValid():
                            feature_count = filtered_layer.featureCount()
                            print(f"✅ DEBUG get_cut_layer: Layer filtrada criada com {feature_count} feições")
                            
                            if feature_count > 0:
                                filtered_layer.setName(f"{self.selected_layer.name()}_{self.selected_field}_{self.selected_element}")
                                return filtered_layer
                            else:
                                print(f"⚠️ DEBUG get_cut_layer: Layer filtrada vazia - usando layer original")
                                return self.selected_layer
                        else:
                            print(f"❌ DEBUG get_cut_layer: Falha ao criar layer filtrada - usando layer original")
                            return self.selected_layer
                            
                    except Exception as e:
                        print(f"❌ DEBUG get_cut_layer: Erro ao filtrar: {e}")
                        print(f"🔧 DEBUG get_cut_layer: Retornando layer original")
                        return self.selected_layer
                else:
                    print(f"🔧 DEBUG get_cut_layer: Sem filtro - retornando layer original")
                    return self.selected_layer
            else:
                print(f"❌ DEBUG get_cut_layer: selected_layer é None!")
                return None
            
        elif self.cut_option == 2:
            # Desenho na tela
            print(f"🔧 DEBUG get_cut_layer: cut_option=2 (desenho)")
            print(f"🔧 DEBUG get_cut_layer: drawn_rectangle = {getattr(self, 'drawn_rectangle', 'UNDEFINED')}")
            
            if hasattr(self, 'drawn_rectangle') and self.drawn_rectangle:
                try:
                    print(f"🔧 DEBUG get_cut_layer: Criando layer de retângulo...")
                    # Cria layer de memória com o retângulo
                    rect_layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "RetanguloDesenhado", "memory")
                    provider = rect_layer.dataProvider()
                    
                    # Cria feição com geometria do retângulo
                    rect_feature = QgsFeature()
                    rect_geometry = QgsGeometry.fromRect(self.drawn_rectangle)
                    rect_feature.setGeometry(rect_geometry)
                    
                    # Adiciona feição
                    provider.addFeature(rect_feature)
                    rect_layer.updateExtents()
                    
                    print(f"✅ DEBUG get_cut_layer: Layer de retângulo criada")
                    return rect_layer
                except Exception as e:
                    print(f"❌ DEBUG get_cut_layer: Erro ao criar retângulo: {e}")
                    return None
            else:
                print(f"❌ DEBUG get_cut_layer: drawn_rectangle não existe ou é None!")
                return None
            
        elif self.cut_option == 3:
            # IBGE
            print(f"🔧 DEBUG get_cut_layer: cut_option=3 (IBGE)")
            try:
                ibge_layer = self.get_ibge_cut_layer()
                if ibge_layer:
                    print(f"✅ DEBUG get_cut_layer: Layer IBGE obtida: {ibge_layer.featureCount()} feições")
                else:
                    print(f"❌ DEBUG get_cut_layer: get_ibge_cut_layer retornou None")
                return ibge_layer
            except Exception as e:
                print(f"❌ DEBUG get_cut_layer: Erro ao obter layer IBGE: {e}")
                return None
        
        print(f"❌ DEBUG get_cut_layer: cut_option inválido: {self.cut_option}")
        return None

    def get_wfs_cut_layer(self):
        """Retorna a layer de corte WFS configurada"""
        if not hasattr(self, 'wfs_layer') or not self.wfs_layer or not self.wfs_layer.isValid():
            return None
            
        # Se não há filtro por campo/elemento, retorna a layer completa
        if not hasattr(self, 'wfs_field_combo') or not self.wfs_field_combo.currentText():
            # Cria uma cópia da layer para não afetar a original
            temp_layer = self.wfs_layer.clone()
            temp_layer.setName(f"WFS_{self.wfs_type_combo.currentText()}")
            return temp_layer
            
        # Se há filtro, cria layer filtrada
        field_name = self.wfs_field_combo.currentText()
        element_value = self.wfs_element_combo.currentText() if hasattr(self, 'wfs_element_combo') else None
        
        if element_value:
            try:
                # Cria expressão de filtro
                expression = f'"{field_name}" = \'{element_value}\''
                
                # Cria layer filtrada em memória
                request = QgsFeatureRequest().setFilterExpression(expression)
                filtered_layer = self.wfs_layer.materialize(request)
                filtered_layer.setName(f"WFS_Filtrado_{field_name}_{element_value}")
                
                return filtered_layer
                
            except Exception as e:
                # Em caso de erro, retorna layer original
                temp_layer = self.wfs_layer.clone()
                temp_layer.setName(f"WFS_{self.wfs_type_combo.currentText()}_ErroFiltro")
                return temp_layer
        
        temp_layer = self.wfs_layer.clone()
        temp_layer.setName(f"WFS_{self.wfs_type_combo.currentText()}")
        return temp_layer

    def activate_drawing_tool(self):
        """Ativa a ferramenta de desenho"""
        try:
            from qgis.utils import iface
            canvas = iface.mapCanvas()
            
            self.draw_tool = DrawRectangleTool(canvas)
            self.draw_tool.rectangleDrawn.connect(self.on_rectangle_drawn)
            
            canvas.setMapTool(self.draw_tool)
            self.hide()  # Esconde a janela temporariamente
            
            self.update_notes("🎯 Clique e arraste no mapa para desenhar um retângulo")
            
        except Exception as e:
            self.update_notes(f"❌ Erro ao ativar ferramenta de desenho: {str(e)}")

    def on_rectangle_drawn(self, rectangle):
        """Callback para retângulo desenhado"""
        self.drawn_rectangle = rectangle
        
        # CORREÇÃO 4: Usar notas completas
        self.update_comprehensive_notes()
        
        # Restaura a ferramenta anterior e mostra a janela
        try:
            from qgis.utils import iface
            canvas = iface.mapCanvas()
            canvas.unsetMapTool(self.draw_tool)
        except:
            pass
            
        self.show()

    def update_notes(self, message, note_type="status"):
        """
        Atualiza o quadro de notas com sistema inteligente
        
        Args:
            message: Mensagem a ser exibida
            note_type: 'config' (linha fixa), 'status' (dinâmico), 'final' (resultado)
        """
        if note_type == "config":
            # Linha de configuração fixa - substitui ou define a primeira linha
            self.config_note = message
            self._update_notes_display()
        elif note_type == "status":
            # Status dinâmico - sobrescreve linha de status
            self.status_note = message
            self._update_notes_display()
        elif note_type == "final":
            # Resultado final - adiciona ao final
            self.final_note = message
            self._update_notes_display()
        else:
            # Compatibilidade - comportamento antigo para casos não especificados
            current_text = self.notes_text.toPlainText()
            if current_text:
                self.notes_text.setPlainText(current_text + "\n" + message)
            else:
                self.notes_text.setPlainText(message)
    
    def _update_notes_display(self):
        """Atualiza a exibição das notas com sistema de partes"""
        parts = []
        
        # Linha de configuração (sempre no topo)
        if hasattr(self, 'config_note') and self.config_note:
            parts.append(self.config_note)
        
        # Linha de status (dinâmica)
        if hasattr(self, 'status_note') and self.status_note:
            parts.append(self.status_note)
        
        # Resultado final (se existir)
        if hasattr(self, 'final_note') and self.final_note:
            parts.append(self.final_note)
        
        # Atualiza display
        if parts:
            self.notes_text.setPlainText("\n".join(parts))
        else:
            self.notes_text.clear()
    
    def clear_notes(self):
        """Limpa todas as notas"""
        self.config_note = ""
        self.status_note = ""
        self.final_note = ""
        self.notes_text.clear()

    def update_navigation_buttons(self):
        """Atualiza o estado dos botões de navegação"""
        can_advance = self.can_advance()
        
        print(f"🔧 DEBUG update_navigation_buttons: current_step={self.current_step}")
        print(f"🔧 DEBUG update_navigation_buttons: can_advance={can_advance}")
        print(f"🔧 DEBUG update_navigation_buttons: max_steps={self.max_steps}")
        
        # CORREÇÃO CRÍTICA: Garantir que can_advance seja sempre um boolean
        if can_advance is None:
            print("⚠️ WARNING: can_advance retornou None! Definindo como False")
            can_advance = False
        elif isinstance(can_advance, list):
            print(f"⚠️ WARNING: can_advance retornou uma lista ({can_advance})! Convertendo para boolean")
            can_advance = bool(can_advance and len(can_advance) > 0)
        elif not isinstance(can_advance, bool):
            print(f"⚠️ WARNING: can_advance retornou tipo inválido ({type(can_advance)}: {can_advance})! Convertendo para boolean")
            can_advance = bool(can_advance)
        
        self.btn_back.setEnabled(self.current_step > 1)
        self.btn_next.setEnabled(self.current_step < self.max_steps and can_advance)
        
        # NOVO: Lógica para etapa 3 (processamento)
        if self.current_step == self.max_steps:
            # Etapa 3: Esconde "Finalizar" e "Avançar", mostra processamento
            self.btn_finish.setVisible(False)
            self.btn_next.setVisible(False)
            
            # Lógica de botões de processamento baseada no estado do download
            if hasattr(self, 'btn_process') and hasattr(self, 'btn_abort'):
                if self.download_in_progress:
                    # Durante download: esconde processar, mostra abortar
                    self.btn_process.setVisible(False)
                    self.btn_abort.setVisible(True)
                    self.btn_abort.setEnabled(True)
                else:
                    # Fora do download: mostra processar, esconde abortar
                    self.btn_process.setVisible(True)
                    self.btn_process.setEnabled(can_advance)
                    self.btn_abort.setVisible(False)
        else:
            # Etapas 1 e 2: Mostra navegação normal
            self.btn_finish.setVisible(False)  # Sempre oculto, não usamos mais
            self.btn_next.setVisible(True)
            
            # Esconde botões de processamento se existirem
            if hasattr(self, 'btn_process'):
                self.btn_process.setVisible(False)
            if hasattr(self, 'btn_abort'):
                self.btn_abort.setVisible(False)
        
        # Botão cancelar sempre habilitado
        self.btn_cancel.setEnabled(True)
        
        print(f"🔧 DEBUG update_navigation_buttons: btn_next.isEnabled()={self.btn_next.isEnabled()}")
        print(f"🔧 DEBUG update_navigation_buttons: btn_back.isEnabled()={self.btn_back.isEnabled()}")

    def can_advance(self):
        """Verifica se pode avançar para o próximo passo"""
        try:
            if self.current_step == 1:
                # Para avançar da etapa 1, precisa ter tema e bioma selecionados
                has_theme_biome = bool(self.selected_theme and self.selected_biome)
                print(f"🔧 DEBUG can_advance: step=1, theme={self.selected_theme}, biome={self.selected_biome}, has_theme_biome={has_theme_biome}")
                
                # LÓGICA ESPECIAL PARA TERRACLASS: valida configurações já na etapa 1
                if self.selected_theme == "TERRACLASS" and has_theme_biome:
                    terraclass_valid = self.validate_terraclass_settings()
                    print(f"🔧 DEBUG can_advance: TERRACLASS step=1, terraclass_valid={terraclass_valid}")
                    return terraclass_valid
                else:
                    return has_theme_biome
            elif self.current_step == 2:
                # Para avançar da etapa 2, verifica se as configurações temporais estão completas
                result = self.validate_temporal_settings()
                print(f"🔧 DEBUG can_advance: step=2, temporal_valid={result}")
                return result if result is not None else False
            else:
                return True
        except Exception as e:
            print(f"❌ ERROR can_advance: {str(e)}")
            return False  # Retorna False em caso de erro, nunca None

    def cancel_wizard(self):
        """Cancela o assistente e destrói a instância para garantir estado limpo"""
        print("🔧 DEBUG: cancel_wizard called - executando limpeza completa")
        
        # Limpa ferramentas de desenho se ativas
        if hasattr(self, 'draw_tool') and self.draw_tool:
            try:
                from qgis.utils import iface
                canvas = iface.mapCanvas()
                canvas.unsetMapTool(self.draw_tool)
                print("🔧 DEBUG: Ferramenta de desenho removida")
            except:
                pass
        
        # NOVA ESTRATÉGIA: Em vez de reset, destrói diretamente a instância
        # Isso garante que a próxima abertura seja com estado 100% limpo
        print("✅ DEBUG: Cancelamento executado - destruindo instância")
        
        # CORREÇÃO: Fecha e DESTRÓI a janela para garantir estado limpo na próxima abertura
        print("🗑️ DEBUG: Destruindo instância do dialog para garantir estado limpo")
        self.close()
        self.deleteLater()  # Marca para o PyQt destruir o objeto

    def validate_temporal_settings(self):
        """Valida se as configurações temporais estão completas"""
        try:
            if self.current_step != 2:
                return True
                
            if not self.selected_theme:
                return False
                
            # Verificações específicas por tema
            if self.selected_theme == "PRODES":
                result = self.validate_prodes_settings()
                return result if result is not None else False
            elif self.selected_theme == "DETER":
                result = self.validate_deter_settings()
                return result if result is not None else False
            elif self.selected_theme == "TERRACLASS":
                result = self.validate_terraclass_settings()
                return result if result is not None else False
            elif self.selected_theme == "ÁREA QUEIMADA":
                result = self.validate_queimadas_settings()
                return result if result is not None else False
                
            return False
        except Exception as e:
            print(f"❌ ERROR validate_temporal_settings: {str(e)}")
            return False  # Sempre retorna False em caso de erro

    def validate_prodes_settings(self):
        """Valida configurações específicas do PRODES"""
        try:
            print(f"🔧 DEBUG validate_prodes_settings: checking PRODES settings")
            
            # Verifica se tipo de dado foi escolhido (SEM verificar temporal_unit)
            has_data_type = hasattr(self, 'data_type') and self.data_type
            print(f"🔧 DEBUG validate_prodes_settings: data_type={getattr(self, 'data_type', None)}, has_data_type={has_data_type}")
            
            if not has_data_type:
                return False
                
            # Verifica anos baseado no tipo de dado
            if self.data_type == "incremental":
                has_start = hasattr(self, 'start_year') and self.start_year
                has_end = hasattr(self, 'end_year') and self.end_year
                valid_range = has_start and has_end and self.start_year <= self.end_year
                print(f"🔧 DEBUG validate_prodes_settings: incremental - start_year={getattr(self, 'start_year', None)}, end_year={getattr(self, 'end_year', None)}, valid_range={valid_range}")
                return valid_range
            elif self.data_type == "acumulado":
                has_end = hasattr(self, 'end_year') and self.end_year
                print(f"🔧 DEBUG validate_prodes_settings: acumulado - end_year={getattr(self, 'end_year', None)}, has_end={has_end}")
                return has_end
                
            return False
        except Exception as e:
            print(f"❌ ERROR validate_prodes_settings: {str(e)}")
            return False  # Sempre retorna False em caso de erro

    def validate_deter_settings(self):
        """Valida configurações específicas do DETER"""
        try:
            print(f"🔧 DEBUG validate_deter_settings: checking DETER settings")
            
            # Verifica anos selecionados
            has_start = hasattr(self, 'deter_start_year') and self.deter_start_year
            has_end = hasattr(self, 'deter_end_year') and self.deter_end_year
            valid_range = has_start and has_end and self.deter_start_year <= self.deter_end_year
            print(f"🔧 DEBUG validate_deter_settings: start_year={getattr(self, 'deter_start_year', None)}, end_year={getattr(self, 'deter_end_year', None)}, valid_range={valid_range}")
            
            if not valid_range:
                return False
                
            # LÓGICA INTELIGENTE DE CLASSES DETER
            deter_classes = getattr(self, 'deter_selected_classes', None)
            print(f"🔧 DEBUG validate_deter_settings: deter_selected_classes={deter_classes}, type={type(deter_classes)}")
            
            # Garantia que seja sempre uma lista
            if not isinstance(deter_classes, list):
                print(f"⚠️ WARNING: deter_selected_classes não é lista! Tipo: {type(deter_classes)}")
                return False
            
            # Obtem classes disponíveis para o bioma
            if not self.selected_biome or self.selected_biome not in self.deter_classes:
                print(f"⚠️ WARNING: Bioma não encontrado: {self.selected_biome}")
                return False
                
            available_classes = self.deter_classes[self.selected_biome]
            total_available = len(available_classes)
            total_selected = len(deter_classes)
            
            print(f"🔧 DEBUG validate_deter_settings: bioma={self.selected_biome}")
            print(f"🔧 DEBUG validate_deter_settings: available_classes={available_classes} (total: {total_available})")
            print(f"🔧 DEBUG validate_deter_settings: selected_classes={deter_classes} (total: {total_selected})")
            
            # REGRA: Pelo menos uma classe deve estar selecionada
            if total_selected == 0:
                print("❌ ERRO: Nenhuma classe DETER foi selecionada!")
                return False
            
            # REGRA: Se todas as classes estão selecionadas = SEM FILTRO (válido)
            if total_selected == total_available:
                print("✅ INFO: Todas as classes selecionadas - será baixado SEM filtro de classes")
                return True
                
            # REGRA: Se algumas classes estão selecionadas = COM FILTRO (válido)
            print(f"✅ INFO: {total_selected}/{total_available} classes selecionadas - será aplicado filtro")
            return True
            
        except Exception as e:
            print(f"❌ ERROR validate_deter_settings: {str(e)}")
            return False

    def validate_terraclass_settings(self):
        """Valida configurações específicas do TERRACLASS"""
        try:
            print(f"🔧 DEBUG validate_terraclass_settings: checking TERRACLASS settings")
            
            # Verifica se ano foi selecionado
            has_year = hasattr(self, 'terraclass_year') and self.terraclass_year
            print(f"🔧 DEBUG validate_terraclass_settings: year={getattr(self, 'terraclass_year', None)}, has_year={has_year}")
            
            if not has_year:
                return False
                
            # Verifica se estado foi selecionado
            has_state = hasattr(self, 'terraclass_state') and self.terraclass_state
            print(f"🔧 DEBUG validate_terraclass_settings: state={getattr(self, 'terraclass_state', None)}, has_state={has_state}")
            
            if not has_state:
                return False
                
            # Município é opcional - se ano e estado estiverem selecionados, já é válido
            print(f"🔧 DEBUG validate_terraclass_settings: municipality={getattr(self, 'terraclass_municipality', None)} (opcional)")
            
            return True
        except Exception as e:
            print(f"❌ ERROR validate_terraclass_settings: {str(e)}")
            return False  # Sempre retorna False em caso de erro

    def go_back(self):
        """Volta para o passo anterior"""
        print(f"🔧 DEBUG go_back: current_step={self.current_step}")
        
        if self.current_step > 1:
            # LÓGICA ESPECIAL PARA TERRACLASS: Volta da etapa 3 para etapa 1 (sem passar pela etapa 2)
            if (self.selected_theme == "TERRACLASS" and self.current_step == 3):
                print(f"🔧 DEBUG go_back: TERRACLASS detectado - voltando da etapa 3 para etapa 1")
                self.current_step = 1  # Volta direto para etapa 1
            else:
                self.current_step -= 1
            
            print(f"🔧 DEBUG go_back: voltando para step {self.current_step}")
            
            # CORREÇÃO: Preserva seleções ao voltar
            if self.current_step == 1:
                # Ao voltar para etapa 1, preserva tema e bioma selecionados
                print(f"🔧 DEBUG go_back: preservando tema={self.selected_theme}, bioma={self.selected_biome}")
            
            self.update_interface()
            
            # CORREÇÃO: Restaura seleções após atualizar interface
            if self.current_step == 1:
                self.restore_step1_selections()
            
            # Força responsividade
            self.adjustSize()
            QTimer.singleShot(10, self.force_resize)

    def restore_step1_selections(self):
        """Restaura as seleções da etapa 1 após voltar"""
        try:
            print(f"🔧 DEBUG restore_step1_selections: restaurando tema={self.selected_theme}, bioma={self.selected_biome}")
            
            # Restaura tema
            if self.selected_theme and hasattr(self, 'theme_combo'):
                self.theme_combo.setCurrentText(self.selected_theme)
                print(f"✅ DEBUG: Tema restaurado: {self.theme_combo.currentText()}")
                
                # CORREÇÃO: Força chamada do on_theme_changed para mostrar bioma
                print(f"🔧 DEBUG: Forçando atualização do bioma após restaurar tema")
                self.on_theme_changed(self.selected_theme)
            
            # NOVA ESTRATÉGIA: Restaura bioma com múltiplas tentativas e timers escalonados
            if self.selected_biome and hasattr(self, 'biome_combo'):
                print(f"🔧 DEBUG: Iniciando restauração escalonada do bioma")
                # Primeira tentativa: 200ms
                QTimer.singleShot(200, lambda: self.restore_biome_direct())
                # Segunda tentativa: 400ms (se primeira falhar)
                QTimer.singleShot(400, lambda: self.restore_biome_fallback())
                # Terceira tentativa: 600ms (força total)
                QTimer.singleShot(600, lambda: self.restore_biome_force())
                
            # Restaura opção de corte
            if hasattr(self, 'cut_option') and self.cut_option is not None:
                if hasattr(self, 'cut_button_group'):
                    button = self.cut_button_group.button(self.cut_option)
                    if button:
                        button.setChecked(True)
                        # Recria configurações específicas
                        self.on_cut_option_changed(button)
                        
        except Exception as e:
            print(f"⚠️ WARNING restore_step1_selections: {str(e)}")

    def restore_biome_direct(self):
        """Primeira tentativa de restauração direta do bioma"""
        try:
            if not self.selected_biome or not hasattr(self, 'biome_combo'):
                return
                
            print(f"🔧 DEBUG restore_biome_direct: Tentativa 1 - bioma={self.selected_biome}")
            print(f"🔧 DEBUG restore_biome_direct: combo tem {self.biome_combo.count()} itens")
            
            # Bloqueia sinais temporariamente para evitar conflitos
            self.biome_combo.blockSignals(True)
            
            # Procura e seleciona o bioma
            biome_found = False
            for i in range(self.biome_combo.count()):
                item_text = self.biome_combo.itemText(i)
                if item_text == self.selected_biome:
                    print(f"✅ DEBUG: Bioma encontrado no índice {i} - selecionando")
                    self.biome_combo.setCurrentIndex(i)
                    biome_found = True
                    break
            
            # Reativa sinais
            self.biome_combo.blockSignals(False)
            
            if biome_found:
                # Força atualização das notas sem chamar callback problemático
                print(f"✅ DEBUG: Bioma restaurado com sucesso - atualizando notas")
                self.update_comprehensive_notes()
                self.update_navigation_buttons()
            else:
                print(f"⚠️ DEBUG: Bioma não encontrado na tentativa 1")
                
        except Exception as e:
            print(f"❌ DEBUG restore_biome_direct: {str(e)}")

    def restore_biome_fallback(self):
        """Segunda tentativa - verifica se ainda precisa restaurar"""
        try:
            if not self.selected_biome or not hasattr(self, 'biome_combo'):
                return
                
            # Verifica se já foi restaurado
            current_text = self.biome_combo.currentText()
            if current_text == self.selected_biome:
                print(f"✅ DEBUG: Bioma já restaurado corretamente: {current_text}")
                return
                
            print(f"🔧 DEBUG restore_biome_fallback: Tentativa 2 - current='{current_text}', target='{self.selected_biome}'")
            
            # Tenta novamente com bloqueio de sinais
            self.biome_combo.blockSignals(True)
            
            # Força refresh da lista primeiro
            if self.selected_theme and self.selected_theme in self.biome_options:
                self.biome_combo.clear()
                self.biome_combo.addItem("")
                self.biome_combo.addItems(self.biome_options[self.selected_theme])
                print(f"🔧 DEBUG: Lista de biomas recarregada: {self.biome_combo.count()} itens")
            
            # Procura e seleciona novamente
            for i in range(self.biome_combo.count()):
                if self.biome_combo.itemText(i) == self.selected_biome:
                    self.biome_combo.setCurrentIndex(i)
                    print(f"✅ DEBUG: Bioma selecionado na tentativa 2")
                    break
            
            self.biome_combo.blockSignals(False)
            self.update_comprehensive_notes()
            
        except Exception as e:
            print(f"❌ DEBUG restore_biome_fallback: {str(e)}")

    def restore_biome_force(self):
        """Terceira tentativa - força total com callback"""
        try:
            if not self.selected_biome or not hasattr(self, 'biome_combo'):
                return
                
            current_text = self.biome_combo.currentText()
            if current_text == self.selected_biome:
                print(f"✅ DEBUG: Bioma já restaurado na força: {current_text}")
                return
                
            print(f"🔧 DEBUG restore_biome_force: Tentativa 3 (FORÇA) - forçando restauração")
            
            # Última tentativa: permite sinais e força callback
            for i in range(self.biome_combo.count()):
                if self.biome_combo.itemText(i) == self.selected_biome:
                    print(f"🔧 DEBUG: Aplicando força bruta - setCurrentIndex({i})")
                    self.biome_combo.setCurrentIndex(i)
                    
                    # Força callback manual se necessário
                    if self.biome_combo.currentText() == self.selected_biome:
                        print(f"✅ DEBUG: Força total bem-sucedida!")
                        # Não chama on_biome_changed para evitar conflitos, só atualiza notas
                        self.update_comprehensive_notes()
                        self.update_navigation_buttons()
                    else:
                        print(f"❌ DEBUG: Força total falhou")
                    break
                    
        except Exception as e:
            print(f"❌ DEBUG restore_biome_force: {str(e)}")

    def go_next(self):
        """Avança para o próximo passo"""
        print(f"🔧 DEBUG go_next: current_step={self.current_step}, max_steps={self.max_steps}")
        print(f"🔧 DEBUG go_next: can_advance={self.can_advance()}")
        
        if self.current_step < self.max_steps and self.can_advance():
            # LÓGICA ESPECIAL PARA TERRACLASS: Pula da etapa 1 para etapa 3 (sem filtros)
            if (self.selected_theme == "TERRACLASS" and self.current_step == 1):
                print(f"🔧 DEBUG go_next: TERRACLASS detectado - pulando etapa 2 (sem filtros)")
                self.current_step = 3  # Pula direto para processamento final
            else:
                self.current_step += 1
            
            print(f"🔧 DEBUG go_next: advancing to step {self.current_step}")
            self.update_interface()
        else:
            print(f"🔧 DEBUG go_next: cannot advance - step={self.current_step}, max={self.max_steps}, can_advance={self.can_advance()}")

    def finish_wizard(self):
        """Finaliza o assistente"""
        self.accept()

    def closeEvent(self, event):
        """Evento de fechamento da janela"""
        print("🗑️ DEBUG: closeEvent chamado - limpando recursos e destruindo instância")
        
        # Limpa ferramentas de desenho se ativas
        if self.draw_tool:
            try:
                from qgis.utils import iface
                canvas = iface.mapCanvas()
                canvas.unsetMapTool(self.draw_tool)
                print("🔧 DEBUG: Ferramenta de desenho removida")
            except:
                pass
        
        # Força destruição da instância para garantir estado limpo na próxima abertura
        self.deleteLater()
        print("✅ DEBUG: Instância marcada para destruição - próxima abertura será com estado limpo")
        
        event.accept()

    def get_selection_summary(self):
        """Retorna um resumo das seleções para usar nas próximas etapas"""
        summary = {
            'theme': self.selected_theme,
            'biome': self.selected_biome,
            'cut_option': self.cut_option,
            'cut_layer': self.get_cut_layer()
        }
        
        # Adiciona detalhes específicos de cada opção
        if self.cut_option == 1 and self.selected_layer:
            summary['layer_name'] = self.selected_layer.name()
            summary['field_name'] = self.selected_field
            summary['element_value'] = self.selected_element
            
        elif self.cut_option == 2 and self.drawn_rectangle:
            summary['rectangle'] = self.drawn_rectangle
            
        elif self.cut_option == 3:
            summary['wfs_type'] = getattr(self, 'wfs_type_combo', None) and self.wfs_type_combo.currentText()
            summary['wfs_field'] = getattr(self, 'wfs_field_combo', None) and self.wfs_field_combo.currentText()
            summary['wfs_element'] = getattr(self, 'wfs_element', None)
            
        return summary

    def create_simple_wfs_layer(self, base_url, type_key):
        """Função simplificada para WFS - usado como fallback"""
        return self.create_wfs_layer_simple(base_url, type_key)



    def create_direct_download_layer(self, base_url, type_key):
        """Tenta criar layer WFS com download direto e múltiplas estratégias"""
        try:
            print(f"🌐 DEBUG: === CRIANDO LAYER COM DOWNLOAD DIRETO ===")
            
            # Extrai informações da URL
            try:
                url_parts = base_url.split('/geoserver/')[1].split('/ows')[0].split('/')
                namespace = url_parts[0]
                layer_name = url_parts[1]
                print(f"🔧 DEBUG: Namespace: {namespace}, Layer: {layer_name}")
            except:
                print(f"❌ DEBUG: Erro ao extrair namespace/layer")
                return None
            
            # Estratégias de URL mais simples para download
            simple_strategies = [
                # Estratégia 1: WFS 1.0.0 simples
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}",
                # Estratégia 2: Apenas layer name
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={layer_name}",
                # Estratégia 3: Com CRS explícito
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&srsName=EPSG:4674",
                # Estratégia 4: GML2 que é mais compatível
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=text/xml;subtype=gml/2.1.2",
                # Estratégia 5: Com timeout maior
                f"url='{base_url}' typename='{namespace}:{layer_name}' version='1.0.0'",
            ]
            
            for i, url_strategy in enumerate(simple_strategies, 1):
                try:
                    print(f"🌐 DEBUG: Estratégia direta {i}/{len(simple_strategies)}")
                    print(f"🔗 DEBUG: URL: {url_strategy[:100]}...")
                    
                    # Cria layer
                    layer = QgsVectorLayer(url_strategy, f"DirectWFS_{i}", "WFS")
                    
                    # Aguarda carregamento
                    QgsApplication.processEvents()
                    
                    print(f"🔧 DEBUG: Layer válida: {layer.isValid()}")
                    
                    if layer.isValid():
                        feature_count = layer.featureCount()
                        print(f"🔧 DEBUG: Feições: {feature_count}")
                        
                        if feature_count > 0:
                            print(f"✅ DEBUG: Estratégia {i} bem-sucedida! {feature_count} feições")
                            
                            # Testa algumas feições para garantir que têm geometria
                            features = list(layer.getFeatures())[:3]
                            valid_geom_count = 0
                            for feat in features:
                                if feat.hasGeometry() and not feat.geometry().isEmpty():
                                    valid_geom_count += 1
                            
                            print(f"✅ DEBUG: {valid_geom_count}/3 feições testadas têm geometria válida")
                            return layer
                        else:
                            print(f"⚠️ DEBUG: Layer válida mas vazia")
                    else:
                        error = layer.error().message() if layer.error() else "Erro desconhecido"
                        print(f"❌ DEBUG: Layer inválida: {error}")
                        
                except Exception as e:
                    print(f"❌ DEBUG: Erro na estratégia {i}: {str(e)}")
                    continue
            
            print(f"❌ DEBUG: Todas as estratégias diretas falharam")
            return None
            
        except Exception as e:
            print(f"❌ DEBUG: Erro geral no download direto: {str(e)}")
            return None

    def create_fresh_wfs_layer(self):
        """Cria uma nova layer WFS do zero"""
        try:
            print(f"🔧 DEBUG: Criando nova layer WFS...")
            
            wfs_type = self.wfs_type_combo.currentText()
            type_mapping = {
                "Unidades de Conservação": "conservation_units",
                "Terras Indígenas": "indigenous_area", 
                "Municípios": "municipalities",
                "Estados": "states"
            }
            
            type_key = type_mapping.get(wfs_type)
            if not type_key or self.selected_biome not in self.wfs_urls[type_key]:
                print(f"❌ DEBUG: URL WFS não disponível")
                return None
                
            base_url = self.wfs_urls[type_key][self.selected_biome]
            
            # Cria layer WFS com estratégia mais robusta
            layer = self.create_wfs_layer(base_url, type_key)
            
            if layer and layer.isValid():
                print(f"✅ DEBUG: Nova layer WFS criada com sucesso")
                return layer
            else:
                print(f"❌ DEBUG: Falha ao criar nova layer WFS")
                return None
                
        except Exception as e:
            print(f"❌ DEBUG: Erro ao criar nova layer WFS: {str(e)}")
            return None

    def create_wfs_debug_layer(self):
        """Cria layer de debug específica para WFS"""
        try:
            if not self.wfs_layer or not self.wfs_layer.isValid():
                print(f"❌ DEBUG: Layer WFS base inválida")
                return None
                
            print(f"🔧 DEBUG: === CRIANDO LAYER DE DEBUG WFS ===")
            print(f"🔧 DEBUG: Layer base tem {self.wfs_layer.featureCount()} feições")
            
            # TESTE CRÍTICO: Verifica se a layer base realmente tem feições
            print(f"🔍 DEBUG: === VERIFICAÇÃO CRÍTICA DA LAYER BASE ===")
            base_feature_test = self.test_layer_features(self.wfs_layer, "Base WFS")
            
            if not base_feature_test:
                print(f"❌ DEBUG: Layer base não tem feições reais!")
                return None
            
            # PRIMEIRO: Verifica se há filtro
            has_filter = (hasattr(self, 'wfs_field_combo') and self.wfs_field_combo.currentText() and 
                         hasattr(self, 'wfs_element_combo') and self.wfs_element_combo.currentText())
            
            field_name = self.wfs_field_combo.currentText() if has_filter else None
            element_value = self.wfs_element_combo.currentText() if has_filter else None
            
            print(f"🔧 DEBUG: Filtro ativo: {has_filter}")
            if has_filter:
                print(f"🔧 DEBUG: Campo: '{field_name}', Elemento: '{element_value}'")
            
            # SEGUNDO: Testa layer SEM filtro primeiro (para verificar geometrias)
            print(f"🔧 DEBUG: === TESTANDO LAYER SEM FILTRO ===")
            base_layer = self.wfs_layer.clone()
            
            if base_layer and base_layer.isValid():
                base_count = base_layer.featureCount()
                print(f"✅ DEBUG: Layer sem filtro: {base_count} feições")
                
                # TESTE CRÍTICO: Verifica se o clone tem feições reais
                print(f"🔍 DEBUG: === VERIFICAÇÃO DO CLONE ===")
                clone_feature_test = self.test_layer_features(base_layer, "Clone Base")
                
                if not clone_feature_test:
                    print(f"❌ DEBUG: Clone perdeu as feições!")
                    print(f"🔧 DEBUG: Tentando criar nova layer sem clone...")
                    base_layer = self.wfs_layer  # Usa original
                    
                    # Testa original novamente
                    original_test = self.test_layer_features(base_layer, "Original WFS")
                    if not original_test:
                        print(f"❌ DEBUG: Nem a layer original tem feições reais!")
                        return None
                
                if base_count > 0:
                    # Testa algumas geometrias
                    geometry_stats = self.check_geometry_validity(base_layer)
                    print(f"🔍 DEBUG: Geometrias - Válidas: {geometry_stats['valid']}, Inválidas: {geometry_stats['invalid']}, Vazias: {geometry_stats['empty']}")
                    
                    # Se há geometrias inválidas, aplica fix
                    if geometry_stats['invalid'] > 0:
                        print(f"🔧 DEBUG: === APLICANDO FIX GEOMETRY ===")
                        fixed_layer = self.fix_layer_geometries(base_layer)
                        if fixed_layer:
                            base_layer = fixed_layer
                            print(f"✅ DEBUG: Fix geometry aplicado")
                
                # Se não há filtro, retorna a layer base
                if not has_filter:
                    print(f"✅ DEBUG: Retornando layer completa (sem filtro): {base_layer.featureCount()} feições")
                    
                    # TESTE FINAL: Verifica se a layer final tem feições reais
                    final_test = self.test_layer_features(base_layer, "Final Sem Filtro")
                    if not final_test:
                        print(f"❌ DEBUG: Layer final perdeu as feições!")
                        return None
                        
                    return base_layer
            else:
                print(f"❌ DEBUG: Erro ao clonar layer base")
                return None
            
            # TERCEIRO: Se há filtro, verifica se os valores existem ANTES de aplicar
            if has_filter:
                print(f"🔧 DEBUG: === VERIFICANDO FILTRO ===")
                
                # Lista valores reais do campo
                real_values = self.list_real_field_values(base_layer, field_name)
                print(f"🔍 DEBUG: Valores reais no campo '{field_name}': {real_values[:10]}...")  # Primeiros 10
                
                # Verifica se o elemento procurado existe
                if element_value not in real_values:
                    print(f"❌ DEBUG: ELEMENTO '{element_value}' NÃO ENCONTRADO!")
                    print(f"🔍 DEBUG: Valores disponíveis: {real_values}")
                    print(f"⚠️ DEBUG: Retornando layer SEM filtro para análise")
                    
                    # Retorna layer sem filtro para o usuário ver o que há disponível
                    base_layer.setName(f"DEBUG_SemFiltro_VerifiqueElementos")
                    return base_layer
                else:
                    print(f"✅ DEBUG: Elemento '{element_value}' encontrado na lista")
                
                # QUARTO: Aplica filtro COM VERIFICAÇÃO DETALHADA
                print(f"🔧 DEBUG: === APLICANDO FILTRO COM VERIFICAÇÃO ===")
                try:
                    expression = f'"{field_name}" = \'{element_value}\''
                    print(f"🔧 DEBUG: Expressão: {expression}")
                    
                    # Testa a expressão primeiro
                    print(f"🔍 DEBUG: Testando expressão antes de aplicar...")
                    test_count = 0
                    for feature in base_layer.getFeatures():
                        try:
                            value = feature.attribute(field_name)
                            if str(value).strip() == element_value.strip():
                                test_count += 1
                        except:
                            continue
                    
                    print(f"🔧 DEBUG: Teste manual encontrou {test_count} feições que atendem o filtro")
                    
                    # Aplica filtro oficial
                    request = QgsFeatureRequest().setFilterExpression(expression)
                    
                    print(f"🔧 DEBUG: Criando layer filtrada...")
                    filtered_layer = base_layer.materialize(request)
                    
                    filtered_count = filtered_layer.featureCount()
                    print(f"✅ DEBUG: Layer filtrada criada: {filtered_count} feições")
                    
                    # TESTE CRÍTICO: Verifica se a materialização preservou as feições
                    print(f"🔍 DEBUG: === VERIFICAÇÃO DA MATERIALIZAÇÃO ===")
                    if filtered_count > 0:
                        material_test = self.test_layer_features(filtered_layer, "Materializada")
                        if not material_test:
                            print(f"❌ DEBUG: Materialização perdeu as feições!")
                            print(f"🔧 DEBUG: Tentando método alternativo...")
                            
                            # Método alternativo: cria layer em memória manualmente
                            alt_layer = self.create_filtered_layer_manually(base_layer, field_name, element_value)
                            if alt_layer:
                                print(f"✅ DEBUG: Layer alternativa criada: {alt_layer.featureCount()} feições")
                                alt_test = self.test_layer_features(alt_layer, "Alternativa")
                                if alt_test:
                                    return alt_layer
                        else:
                            return filtered_layer
                    
                    if filtered_count > 0:
                        return filtered_layer
                    else:
                        print(f"⚠️ DEBUG: Filtro resultou em 0 feições")
                        print(f"🔧 DEBUG: Tentando filtro case-insensitive...")
                        
                        # Tenta filtro case-insensitive
                        expression_ci = f'upper("{field_name}") = upper(\'{element_value}\')'
                        request_ci = QgsFeatureRequest().setFilterExpression(expression_ci)
                        filtered_layer_ci = base_layer.materialize(request_ci)
                        
                        filtered_count_ci = filtered_layer_ci.featureCount()
                        print(f"🔧 DEBUG: Filtro case-insensitive: {filtered_count_ci} feições")
                        
                        if filtered_count_ci > 0:
                            # Verifica a materialização case-insensitive
                            ci_test = self.test_layer_features(filtered_layer_ci, "Case-Insensitive")
                            if ci_test:
                                return filtered_layer_ci
                        
                        print(f"⚠️ DEBUG: Mesmo case-insensitive não funcionou")
                        print(f"🔧 DEBUG: Retornando layer sem filtro para investigação")
                        base_layer.setName(f"DEBUG_FiltroFalhou_VerifiqueValores")
                        return base_layer
                        
                except Exception as e:
                    print(f"❌ DEBUG: Erro ao aplicar filtro: {str(e)}")
                    print(f"🔧 DEBUG: Retornando layer sem filtro")
                    return base_layer
            
            print(f"❌ DEBUG: Chegou ao final sem retornar layer")
            return None
                
        except Exception as e:
            print(f"❌ DEBUG: Erro ao criar layer de debug: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def test_layer_features(self, layer, layer_name):
        """Testa se a layer realmente tem feições acessíveis"""
        try:
            print(f"🔍 DEBUG: Testando feições da layer '{layer_name}'...")
            
            if not layer or not layer.isValid():
                print(f"❌ DEBUG: Layer inválida")
                return False
            
            # Teste 1: featureCount()
            count = layer.featureCount()
            print(f"🔧 DEBUG: featureCount(): {count}")
            
            if count == 0:
                print(f"❌ DEBUG: featureCount() retorna 0")
                return False
            
            # Teste 2: Tenta iterar as feições
            print(f"🔧 DEBUG: Tentando iterar feições...")
            real_count = 0
            features_with_attrs = 0
            features_with_geom = 0
            
            try:
                for i, feature in enumerate(layer.getFeatures()):
                    real_count += 1
                    
                    # Testa atributos
                    attrs = feature.attributes()
                    if attrs and any(attr is not None for attr in attrs):
                        features_with_attrs += 1
                    
                    # Testa geometria
                    if feature.hasGeometry() and not feature.geometry().isEmpty():
                        features_with_geom += 1
                    
                    # Só testa as primeiras 5 para performance
                    if i >= 4:
                        break
                        
                print(f"✅ DEBUG: Iteração bem-sucedida:")
                print(f"   Real count: {real_count}")
                print(f"   Com atributos: {features_with_attrs}")
                print(f"   Com geometria: {features_with_geom}")
                
                if real_count == 0:
                    print(f"❌ DEBUG: Iteração não retornou feições!")
                    return False
                
                if features_with_attrs == 0:
                    print(f"⚠️ DEBUG: Nenhuma feição tem atributos!")
                    
                return True
                
            except Exception as iter_error:
                print(f"❌ DEBUG: Erro na iteração: {str(iter_error)}")
                return False
            
        except Exception as e:
            print(f"❌ DEBUG: Erro no teste de feições: {str(e)}")
            return False

    def create_filtered_layer_manually(self, base_layer, field_name, element_value):
        """Cria layer filtrada manualmente copiando feições uma por uma"""
        try:
            print(f"🔧 DEBUG: Criando layer filtrada manualmente...")
            
            from qgis.core import QgsVectorLayer, QgsFeature, QgsField
            from qgis.PyQt.QtCore import QVariant
            
            # Cria layer de memória
            geom_type = QgsWkbTypes.displayString(base_layer.wkbType())
            crs = base_layer.crs().authid()
            
            memory_layer = QgsVectorLayer(f"{geom_type}?crs={crs}", "FilteredManual", "memory")
            
            if not memory_layer.isValid():
                print(f"❌ DEBUG: Falha ao criar layer de memória")
                return None
            
            # Copia campos
            memory_layer.dataProvider().addAttributes(base_layer.fields())
            memory_layer.updateFields()
            
            # Filtra e copia feições manualmente
            copied_count = 0
            
            for feature in base_layer.getFeatures():
                try:
                    value = feature.attribute(field_name)
                    if str(value).strip() == element_value.strip():
                        # Copia a feição
                        new_feature = QgsFeature(memory_layer.fields())
                        new_feature.setAttributes(feature.attributes())
                        if feature.hasGeometry():
                            new_feature.setGeometry(feature.geometry())
                        
                        success = memory_layer.dataProvider().addFeature(new_feature)
                        if success:
                            copied_count += 1
                        
                except Exception as feat_error:
                    print(f"⚠️ DEBUG: Erro ao copiar feição: {str(feat_error)}")
                    continue
            
            memory_layer.updateExtents()
            
            print(f"✅ DEBUG: Layer manual criada com {copied_count} feições")
            
            if copied_count > 0:
                return memory_layer
            else:
                return None
                
        except Exception as e:
            print(f"❌ DEBUG: Erro na criação manual: {str(e)}")
            return None

    def check_geometry_validity(self, layer):
        """Verifica a validade das geometrias da layer"""
        try:
            stats = {'valid': 0, 'invalid': 0, 'empty': 0, 'total': 0}
            
            # Testa até 10 feições para estatística
            features = list(layer.getFeatures())[:10]
            
            for feature in features:
                stats['total'] += 1
                
                if not feature.hasGeometry():
                    stats['empty'] += 1
                elif feature.geometry().isEmpty():
                    stats['empty'] += 1
                elif feature.geometry().isGeosValid():
                    stats['valid'] += 1
                else:
                    stats['invalid'] += 1
                    
            return stats
            
        except Exception as e:
            print(f"❌ DEBUG: Erro ao verificar geometrias: {str(e)}")
            return {'valid': 0, 'invalid': 0, 'empty': 0, 'total': 0}

    def fix_layer_geometries(self, layer):
        """Aplica fix geometry na layer"""
        try:
            print(f"🔧 DEBUG: Aplicando fix geometry...")
            
            from qgis.core import QgsVectorFileWriter
            from processing import run as processing_run
            import tempfile
            import os
            
            # Cria arquivo temporário
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"temp_wfs_{id(layer)}.gpkg")
            
            # Salva layer temporariamente
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer, temp_file, layer.transformContext(), options
            )
            
            if error[0] == QgsVectorFileWriter.NoError:
                print(f"✅ DEBUG: Layer salva temporariamente")
                
                # Aplica fix geometry usando processing
                try:
                    result = processing_run("native:fixgeometries", {
                        'INPUT': temp_file,
                        'OUTPUT': 'memory:'
                    })
                    
                    fixed_layer = result['OUTPUT']
                    
                    if fixed_layer and fixed_layer.isValid():
                        print(f"✅ DEBUG: Fix geometry aplicado com sucesso")
                        print(f"✅ DEBUG: Layer corrigida: {fixed_layer.featureCount()} feições")
                        return fixed_layer
                    else:
                        print(f"❌ DEBUG: Fix geometry falhou")
                        
                except Exception as proc_error:
                    print(f"❌ DEBUG: Erro no processing fix geometry: {str(proc_error)}")
                
                # Limpa arquivo temporário
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
            else:
                print(f"❌ DEBUG: Erro ao salvar layer temporária: {error}")
                
            return None
            
        except Exception as e:
            print(f"❌ DEBUG: Erro geral no fix geometry: {str(e)}")
            return None

    def list_real_field_values(self, layer, field_name):
        """Lista valores reais de um campo da layer"""
        try:
            if not layer or not layer.isValid():
                return []
                
            print(f"🔍 DEBUG: Listando valores do campo '{field_name}'...")
            
            # Encontra índice do campo
            field_index = layer.fields().indexOf(field_name)
            if field_index < 0:
                print(f"❌ DEBUG: Campo '{field_name}' não encontrado")
                # Lista campos disponíveis
                available_fields = [f.name() for f in layer.fields()]
                print(f"🔍 DEBUG: Campos disponíveis: {available_fields}")
                return []
            
            # Coleta valores únicos
            unique_values = set()
            feature_count = 0
            
            for feature in layer.getFeatures():
                try:
                    value = feature.attribute(field_name)
                    if value is not None:
                        unique_values.add(str(value).strip())
                    feature_count += 1
                    
                    # Limite para performance
                    if feature_count >= 1000:
                        break
                        
                except Exception as e:
                    continue
            
            result = sorted(list(unique_values))
            print(f"✅ DEBUG: {len(result)} valores únicos encontrados em {feature_count} feições")
            
            return result
            
        except Exception as e:
            print(f"❌ DEBUG: Erro ao listar valores: {str(e)}")
            return []

    def get_cut_option_name(self):
        """Retorna o nome da opção de corte selecionada"""
        if self.cut_option == 0:
            return "SemCorte"
        elif self.cut_option == 1:
            return f"Layer_{self.selected_layer.name() if self.selected_layer else 'Indefinido'}"
        elif self.cut_option == 2:
            return "RetanguloDesenhado"
        elif self.cut_option == 3:
            # IBGE
            parts = ["IBGE"]
            if self.ibge_state:
                parts.append(self.ibge_state.replace(" ", "_"))
            if self.ibge_municipality:
                parts.append(self.ibge_municipality.replace(" ", "_"))
            return "_".join(parts)
        else:
            return "Desconhecido"

    def get_cut_option_details(self):
        """Retorna detalhes da opção de corte para exibição"""
        if self.cut_option == 0:
            return "Todo o bioma (sem corte)"
        elif self.cut_option == 1:
            details = f"Layer: {self.selected_layer.name()}" if self.selected_layer else "Layer não definido"
            if self.selected_field:
                details += f", Campo: {self.selected_field}"
                if self.selected_element:
                    details += f", Elemento: {self.selected_element}"
            return details
        elif self.cut_option == 2:
            if self.drawn_rectangle:
                return f"Retângulo: ({self.drawn_rectangle.xMinimum():.3f}, {self.drawn_rectangle.yMinimum():.3f}) - ({self.drawn_rectangle.xMaximum():.3f}, {self.drawn_rectangle.yMaximum():.3f})"
            else:
                return "Retângulo não desenhado"
        elif self.cut_option == 3:
            # IBGE
            details = f"IBGE: {self.ibge_shapefile_name}"
            if self.ibge_state:
                details += f", {self.ibge_state}"
            if self.ibge_municipality:
                details += f", {self.ibge_municipality}"
            return details
        else:
            return "Opção não reconhecida"









    def test_wfs_connectivity(self, url):
        """Testa conectividade WFS para dados PRODES/DETER"""
        try:
            print(f"🌐 DEBUG: Testando conectividade WFS: {url[:80]}...")
            
            # Extrai URL base sem parâmetros
            base_url = url.split('?')[0]
            
            # Testa GetCapabilities simples
            import requests
            caps_url = f"{base_url}?service=WFS&request=GetCapabilities&version=2.0.0"
            
            response = requests.get(caps_url, timeout=10)
            
            if response.status_code == 200:
                # Verifica se tem conteúdo WFS válido
                content = response.text.lower()
                if 'wfs_capabilities' in content or 'featurecollection' in content or 'wfs:wfs_capabilities' in content:
                    print(f"✅ DEBUG: Conectividade WFS OK")
                    return True
                else:
                    print(f"❌ DEBUG: Resposta inválida - não contém capabilities WFS")
                    return False
            else:
                print(f"❌ DEBUG: Erro HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ DEBUG: Erro na conectividade WFS: {str(e)}")
            return False

    def normalize_terraclass_text(self, text):
        """Normaliza texto para URLs TERRACLASS - remove acentos e caracteres especiais"""
        import unicodedata
        import re
        
        # Remove acentos
        text_normalized = unicodedata.normalize('NFD', text)
        text_ascii = ''.join(c for c in text_normalized if unicodedata.category(c) != 'Mn')
        
        # Converte para maiúsculo e substitui espaços por _
        text_clean = text_ascii.upper().replace(' ', '_')
        
        # Remove outros caracteres especiais
        text_clean = re.sub(r'[^A-Z0-9_]', '', text_clean)
        
        return text_clean

    def create_wfs_layer_simple(self, base_url, type_key):
        """Cria uma layer WFS com múltiplas estratégias"""
        try:
            # Extrai namespace e layer
            try:
                url_parts = base_url.split('/geoserver/')[1].split('/ows')[0].split('/')
                namespace = url_parts[0]
                layer_name = url_parts[1]
            except:
                return None
            
            # URLs de teste - estratégias QGIS-nativas
            qgis_native_urls = [
                f"url='{base_url}' typename='{namespace}:{layer_name}' version='1.0.0'",
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}",
                f"url='{base_url}' typename='{namespace}:{layer_name}' version='1.1.0'",
                f"{base_url}?service=WFS&version=1.1.0&request=GetFeature&typename={namespace}:{layer_name}",
                f"url='{base_url}' typename='{layer_name}' version='1.0.0'",
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&srsName=EPSG:4674",
                base_url,
                f"{base_url}?service=WFS&version=1.0.0&request=GetFeature&typeName={namespace}:{layer_name}&outputFormat=GML2"
            ]
            
            for i, url in enumerate(qgis_native_urls, 1):
                try:
                    layer = QgsVectorLayer(url, f"WFS_{i}", "WFS")
                    
                    # Força carregamento
                    QgsApplication.processEvents()
                    
                    # Aguarda carregamento completo
                    import time
                    time.sleep(1)
                    QgsApplication.processEvents()
                    
                    layer.reload()
                    layer.dataProvider().reloadData()
                    QgsApplication.processEvents()
                    
                    if layer.isValid():
                        feature_count = layer.featureCount()
                        
                        if feature_count > 0:
                            # Testa se tem dados reais
                            try:
                                features = []
                                feature_iter = layer.getFeatures()
                                
                                for idx, feature in enumerate(feature_iter):
                                    if idx >= 3:
                                        break
                                    features.append(feature)
                                
                                actual_count = len(features)
                                
                                if actual_count > 0:
                                    first_feature = features[0]
                                    attrs = first_feature.attributes()
                                    has_geom = first_feature.hasGeometry()
                                    
                                    # Sucesso se tem atributos OU geometria
                                    if (attrs and any(attr is not None for attr in attrs)) or has_geom:
                                        return layer
                                
                            except Exception as iter_error:
                                # Verifica se é erro conhecido do servidor
                                if any(err in str(iter_error).lower() for err in ['not well-formed', 'invalid token', 'primary key', 'natural order']):
                                    continue
                                else:
                                    # Erro diferente, layer pode funcionar mesmo assim
                                    if feature_count > 0:
                                        return layer
                        
                except Exception as e:
                    # Verifica se é erro conhecido do servidor
                    known_errors = ['not well-formed', 'invalid token', 'primary key', 'natural order', 'boundedBy']
                    if any(err in str(e).lower() for err in known_errors):
                        continue
            
            # Se todas as estratégias falharam, retorna None
            return None
            
        except Exception as e:
            return None



    def on_data_type_changed(self, button):
        """Callback para mudança do tipo de dados"""
        option_id = self.data_type_button_group.id(button)
        if option_id == 0:
            self.data_type = "incremental"
        elif option_id == 1:
            self.data_type = "acumulado"
        
        self.update_years_interface()
        self.update_prodes_notes()
        self.update_navigation_buttons()

    def populate_years(self):
        """Popula os combos de anos baseado no bioma selecionado e tipo de dados"""
        if not self.selected_biome:
            return
        
        # Escolhe a lista de anos baseada no tipo de dados
        if self.data_type == "acumulado":
            # Para acumulado, usa a lista estendida que inclui anos iniciais
            if self.selected_biome not in self.prodes_years_acumulado:
                return
            available_years = self.prodes_years_acumulado[self.selected_biome]
        else:
            # Para incremental, usa a lista padrão
            if self.selected_biome not in self.prodes_years:
                return
            available_years = self.prodes_years[self.selected_biome]
        
        # Limpa combos
        self.start_year_combo.clear()
        self.end_year_combo.clear()
        
        # Adiciona opção vazia
        self.start_year_combo.addItem("")
        self.end_year_combo.addItem("")
        
        # Adiciona anos disponíveis
        for year in available_years:
            self.start_year_combo.addItem(str(year))
            self.end_year_combo.addItem(str(year))
        
        # Define valores padrão
        if available_years:
            # Para incremental: primeiro e último ano
            if self.data_type == "incremental":
                self.start_year_combo.setCurrentText(str(available_years[0]))
                self.end_year_combo.setCurrentText(str(available_years[-1]))
            # Para acumulado: só último ano
            else:
                self.end_year_combo.setCurrentText(str(available_years[-1]))

    def update_years_interface(self):
        """Atualiza interface dos anos baseado no tipo de dados"""
        if not hasattr(self, 'years_group'):
            return
            
        if self.data_type == "incremental":
            # Mostra ambos os campos
            self.start_year_label.setVisible(True)
            self.start_year_combo.setVisible(True)
            self.end_year_label.setVisible(True)
            self.end_year_combo.setVisible(True)
        elif self.data_type == "acumulado":
            # Esconde ano inicial
            self.start_year_label.setVisible(False)
            self.start_year_combo.setVisible(False)
            self.end_year_label.setVisible(True)
            self.end_year_combo.setVisible(True)
        
        # Repopula anos
        self.populate_years()
        
        # Ajusta tamanho da janela
        self.adjustSize()
        QTimer.singleShot(10, self.force_resize)

    def on_start_year_changed(self, year_text):
        """Callback para mudança do ano inicial"""
        try:
            print(f"🔧 DEBUG on_start_year_changed: year_text='{year_text}'")
            
            if year_text and year_text.strip():
                self.start_year = int(year_text)
                print(f"🔧 DEBUG on_start_year_changed: start_year definido como {self.start_year}")
                # CORREÇÃO: Valida imediatamente para feedback rápido
                if not self.validate_year_range():
                    # Se ano inválido, a função validate_year_range já resetou
                    return
            else:
                self.start_year = None
                print(f"🔧 DEBUG on_start_year_changed: start_year definido como None")
            
            self.update_prodes_notes()
            
            # CORREÇÃO: Proteção adicional
            try:
                self.update_navigation_buttons()
            except Exception as nav_error:
                print(f"⚠️ WARNING on_start_year_changed navigation error: {str(nav_error)}")
                
        except Exception as e:
            print(f"❌ ERROR on_start_year_changed: {str(e)}")
            self.start_year = None

    def on_end_year_changed(self, year_text):
        """Callback para mudança do ano final"""
        try:
            print(f"🔧 DEBUG on_end_year_changed: year_text='{year_text}'")
            
            if year_text and year_text.strip():
                self.end_year = int(year_text)
                print(f"🔧 DEBUG on_end_year_changed: end_year definido como {self.end_year}")
                # CORREÇÃO: Valida imediatamente para feedback rápido
                if not self.validate_year_range():
                    # Se ano inválido, a função validate_year_range já resetou
                    return
            else:
                self.end_year = None
                print(f"🔧 DEBUG on_end_year_changed: end_year definido como None")
            
            self.update_prodes_notes()
            
            # CORREÇÃO: Proteção adicional
            try:
                self.update_navigation_buttons()
            except Exception as nav_error:
                print(f"⚠️ WARNING on_end_year_changed navigation error: {str(nav_error)}")
                
        except Exception as e:
            print(f"❌ ERROR on_end_year_changed: {str(e)}")
            self.end_year = None

    def validate_year_range(self):
        """Valida o intervalo de anos selecionado"""
        try:
            if (hasattr(self, 'data_type') and self.data_type == "incremental" and 
                hasattr(self, 'start_year') and self.start_year and 
                hasattr(self, 'end_year') and self.end_year and 
                self.start_year > self.end_year):
                
                # CORREÇÃO: Preenchimento automático ao invés de reset
                print(f"⚠️ WARNING: Ano inválido detectado - start: {self.start_year}, end: {self.end_year}")
                
                # CORREÇÃO: Estratégia inteligente - detecta qual foi alterado
                import inspect
                caller_frame = inspect.currentframe().f_back
                caller_name = caller_frame.f_code.co_name if caller_frame else ""
                
                if "start_year" in caller_name:
                    # Foi alterado o ano inicial, ajusta o ano final para ser igual
                    print(f"🔧 DEBUG: Ano inicial alterado, ajustando ano final para {self.start_year}")
                    if hasattr(self, 'end_year_combo'):
                        self.end_year_combo.setCurrentText(str(self.start_year))
                        self.end_year = self.start_year
                    self.update_notes(f"✅ Ano final ajustado automaticamente para {self.start_year}")
                else:
                    # Foi alterado o ano final, mantém o final e ajusta o inicial se necessário
                    print(f"🔧 DEBUG: Ano final alterado para valor menor, ajustando para {self.start_year}")
                    if hasattr(self, 'end_year_combo'):
                        self.end_year_combo.setCurrentText(str(self.start_year))
                        self.end_year = self.start_year
                    self.update_notes(f"✅ Ano final ajustado automaticamente para {self.start_year}")
                
                return True  # CORREÇÃO: Retorna True porque corrigiu automaticamente
            
            return True
        except Exception as e:
            print(f"❌ ERROR validate_year_range: {str(e)}")
            return True  # Em caso de erro, não bloqueia

    def update_prodes_notes(self):
        """Atualiza as notas com informações do PRODES - SISTEMA SIMPLIFICADO"""
        if self.current_step != 2 or self.selected_theme != "PRODES":
            return
        
        # Apenas informações específicas da etapa 2 - não repete config da etapa 1
        status_parts = []
        
        # Informações temporais (apenas tipo de dados)
        if hasattr(self, 'data_type') and self.data_type:
            type_text = "Incremental" if self.data_type == "incremental" else "Acumulado"
            status_parts.append(f"📈 Tipo: {type_text}")
        
        # Informações de anos
        if hasattr(self, 'data_type') and self.data_type:
            if self.data_type == "incremental":
                if (hasattr(self, 'start_year') and self.start_year and 
                    hasattr(self, 'end_year') and self.end_year):
                    status_parts.append(f"🗓️ Período: {self.start_year} - {self.end_year}")
            elif self.data_type == "acumulado":
                if hasattr(self, 'end_year') and self.end_year:
                    base_year = self.prodes_base_years.get(self.selected_biome, 2000)
                    status_parts.append(f"🗓️ Período: {base_year} - {self.end_year} (acumulado)")
        
        # Atualiza apenas a linha de status (não toda a configuração)
        if status_parts:
            self.update_notes(" | ".join(status_parts), "status")
        else:
            self.update_notes("💡 Configure o tipo e período PRODES", "status")

    def get_ibge_shapefile_name(self):
        """Busca dinamicamente o nome do shapefile IBGE na pasta shapefile (sem extensão)"""
        shapefile_dir = os.path.join(os.path.dirname(__file__), 'shapefile')
        
        if not os.path.exists(shapefile_dir):
            print(f"❌ Diretório shapefile não encontrado: {shapefile_dir}")
            return "shapefile_not_found"
        
        # Busca por arquivos .shp na pasta
        shp_files = [f for f in os.listdir(shapefile_dir) if f.endswith('.shp')]
        
        if not shp_files:
            print(f"❌ Nenhum arquivo .shp encontrado em: {shapefile_dir}")
            return "no_shapefile_found"
        
        # Usa o primeiro arquivo .shp encontrado (sem extensão)
        shapefile_name = shp_files[0][:-4]  # Remove .shp
        print(f"✅ Shapefile IBGE encontrado: {shapefile_name}.shp")
        return shapefile_name

    def load_ibge_shapefile(self):
        """Carrega o shapefile IBGE dos limites"""
        try:
            if os.path.exists(self.ibge_shapefile_path):
                self.ibge_layer = QgsVectorLayer(self.ibge_shapefile_path, "IBGE_Limites", "ogr")
                if self.ibge_layer.isValid():
                    print(f"✅ Shapefile IBGE carregado: {self.ibge_layer.featureCount()} feições")
                    return True
                else:
                    print(f"❌ Shapefile IBGE inválido: {self.ibge_shapefile_path}")
                    return False
            else:
                print(f"❌ Shapefile IBGE não encontrado: {self.ibge_shapefile_path}")
                return False
        except Exception as e:
            print(f"❌ Erro ao carregar shapefile IBGE: {str(e)}")
            return False



    def populate_states_combo(self, biome_region):
        """Popula o combo de estados baseado na seleção de bioma/região"""
        self.ibge_state_combo.clear()
        self.ibge_state_combo.addItem("")
        
        if not self.ibge_layer:
            return
        
        # Determina filtro baseado na seleção
        if biome_region == 'Amazônia Legal':
            expression = f'"regiao" = \'Amazônia Legal\''
        else:
            expression = f'"bioma" = \'{biome_region}\''
        
        # Aplica filtro e obtém estados únicos
        request = QgsFeatureRequest().setFilterExpression(expression)
        states = set()
        
        for feature in self.ibge_layer.getFeatures(request):
            state = feature['estado']
            if state:
                states.add(state)
        
        # Adiciona estados ordenados ao combo
        for state in sorted(states):
            self.ibge_state_combo.addItem(state)

    def on_ibge_state_changed(self, selection):
        """Callback para mudança de estado - popula lista de municípios"""
        self.ibge_state = selection
        
        if selection:
            # Popula municípios baseado na seleção (usa self.selected_biome já definido)
            self.populate_municipalities_combo(self.selected_biome, selection)
            self.ibge_municipality_label.setVisible(True)
            self.ibge_municipality_combo.setVisible(True)
            
            # Limpa seleção de município
            self.ibge_municipality = None
        else:
            # Oculta campo de município
            self.ibge_municipality_label.setVisible(False)
            self.ibge_municipality_combo.setVisible(False)
            self.ibge_state = None
            self.ibge_municipality = None
        
        self.update_comprehensive_notes()
        self.adjustSize()

    def populate_municipalities_combo(self, biome_region, state):
        """Popula o combo de municípios baseado na seleção de bioma/região e estado"""
        self.ibge_municipality_combo.clear()
        self.ibge_municipality_combo.addItem("")
        
        if not self.ibge_layer:
            return
        
        # Constrói filtro combinado
        if biome_region == 'Amazônia Legal':
            expression = f'"regiao" = \'Amazônia Legal\' AND "estado" = \'{state}\''
        else:
            expression = f'"bioma" = \'{biome_region}\' AND "estado" = \'{state}\''
        
        # Aplica filtro e obtém municípios únicos
        request = QgsFeatureRequest().setFilterExpression(expression)
        municipalities = set()
        
        for feature in self.ibge_layer.getFeatures(request):
            municipality = feature['nome']
            if municipality:
                municipalities.add(municipality)
        
        # Adiciona municípios ordenados ao combo
        for municipality in sorted(municipalities):
            self.ibge_municipality_combo.addItem(municipality)

    def on_ibge_municipality_changed(self, selection):
        """Callback para mudança de município"""
        self.ibge_municipality = selection
        self.update_comprehensive_notes()

    def get_ibge_cut_layer(self):
        """Obtém a camada de corte baseada na seleção IBGE"""
        if not self.ibge_layer:
            return None
        
        # Constrói filtro baseado na seleção hierárquica
        filters = []
        
        # Filtro por bioma/região
        if self.ibge_biome_region:
            if self.ibge_biome_region == 'Amazônia Legal':
                filters.append(f'"regiao" = \'Amazônia Legal\'')
            else:
                filters.append(f'"bioma" = \'{self.ibge_biome_region}\'')
        
        # Filtro por estado
        if self.ibge_state:
            filters.append(f'"estado" = \'{self.ibge_state}\'')
        
        # Filtro por município (se selecionado)
        if self.ibge_municipality:
            filters.append(f'"nome" = \'{self.ibge_municipality}\'')
        
        if not filters:
            return None
        
        # Aplica filtros
        expression = ' AND '.join(filters)
        request = QgsFeatureRequest().setFilterExpression(expression)
        
        # Cria nova camada com as feições filtradas
        filtered_layer = QgsVectorLayer(f"Polygon?crs={self.ibge_layer.crs().authid()}", "IBGE_Filtered", "memory")
        provider = filtered_layer.dataProvider()
        provider.addAttributes(self.ibge_layer.fields())
        filtered_layer.updateFields()
        
        # Adiciona feições filtradas
        features = []
        for feature in self.ibge_layer.getFeatures(request):
            features.append(feature)
        
        provider.addFeatures(features)
        
        if not self.ibge_municipality and self.ibge_state:
            # Se não selecionou município, dissolve por estado
            dissolved_layer = self.dissolve_layer(filtered_layer, 'estado')
            return dissolved_layer if dissolved_layer else filtered_layer
        
        return filtered_layer

    def dissolve_layer(self, layer, field):
        """Dissolve uma camada por um campo específico"""
        try:
            from qgis.analysis import QgsNativeAlgorithms
            import processing
            
            # Configura parâmetros para dissolução
            params = {
                'INPUT': layer,
                'FIELD': [field],
                'OUTPUT': 'memory:'
            }
            
            # Executa algoritmo de dissolução
            result = processing.run("native:dissolve", params)
            dissolved_layer = result['OUTPUT']
            
            if dissolved_layer and dissolved_layer.isValid():
                original_count = layer.featureCount()
                dissolved_count = dissolved_layer.featureCount()
                
                # NOVO: Registra processamento de dissolve
                if dissolved_count < original_count:
                    reduction_count = original_count - dissolved_count
                    reduction_percent = (reduction_count / original_count) * 100
                    self.add_processing_log(
                        f"DISSOLUÇÃO POR CAMPO '{field}'",
                        f"{original_count} feições → {dissolved_count} feições dissolvidas (união de {reduction_count} polígonos - {reduction_percent:.1f}% redução)"
                    )
                else:
                    self.add_processing_log(
                        f"DISSOLUÇÃO POR CAMPO '{field}'",
                        f"{original_count} feições analisadas → {dissolved_count} feições (nenhum polígono foi unido)"
                    )
            
            return dissolved_layer
        except Exception as e:
            print(f"❌ Erro ao dissolver camada: {str(e)}")
            return None
    def dissolve_queimadas_layer(self, layer):
        """Dissolve áreas queimadas com tratamento de sobreposições"""
        try:
            import processing
            
            print(f"🔥 DEBUG: Aplicando dissolve em áreas queimadas...")
            original_count = layer.featureCount()
            
            # ETAPA 1: Buffer 0 para limpar sobreposições
            print(f"🔥 DEBUG: Limpando sobreposições com buffer 0...")
            clean_params = {
                'INPUT': layer,
                'DISTANCE': 0,
                'OUTPUT': 'memory:'
            }
            
            clean_result = processing.run("native:buffer", clean_params)
            clean_layer = clean_result['OUTPUT']
            
            if not clean_layer or not clean_layer.isValid():
                print(f"❌ DEBUG: Buffer 0 falhou")
                return None
            
            # ETAPA 2: Dissolve completo (une TODAS as geometrias adjacentes)
            print(f"🔥 DEBUG: Aplicando dissolve completo...")
            dissolve_params = {
                'INPUT': clean_layer,
                'FIELD': [],  # Sem campo = dissolve tudo
                'OUTPUT': 'memory:'
            }
            
            result = processing.run("native:dissolve", dissolve_params)
            dissolved_layer = result['OUTPUT']
            
            if dissolved_layer and dissolved_layer.isValid():
                dissolved_count = dissolved_layer.featureCount()
                
                print(f"✅ DEBUG: Dissolve concluído: {original_count} → {dissolved_count} feições")
                
                # LOGS REMOVIDOS: Evita duplicação com o novo log otimizado
                # O log detalhado agora é feito na função queimadas_step_dissolve_after_cut
                
                dissolved_layer.setName(f"{layer.name()}_dissolved")
                return dissolved_layer
            else:
                print(f"❌ DEBUG: Dissolve retornou layer inválida")
                return None
            
        except Exception as e:
            print(f"❌ ERROR dissolve_queimadas_layer: {str(e)}")
            # LOGS REMOVIDOS: Evita duplicação com o novo log otimizado
            # O log detalhado de erro agora é feito na função queimadas_step_dissolve_after_cut
            return None
    # =====================================
    # FUNÇÕES DETER
    # =====================================

    def populate_deter_years(self):
        """Popula os combos de anos baseado no bioma DETER selecionado"""
        if not self.selected_biome or self.selected_biome not in self.deter_start_dates:
            print(f"🔧 DEBUG: Bioma não encontrado nas datas DETER: {self.selected_biome}")
            return
        
        from datetime import datetime
        
        # Data de início baseada no bioma
        start_date_str = self.deter_start_dates[self.selected_biome]
        start_year = int(start_date_str.split('-')[0])
        
        # Ano atual
        current_year = datetime.now().year
        
        # Gera lista de anos - do ano de início até o ano atual (incluindo o atual)
        available_years = list(range(start_year, current_year + 1))
        print(f"🔧 DEBUG DETER: Anos disponíveis para {self.selected_biome}: {start_year} - {current_year}")
        
        # Limpa combos
        self.deter_start_year_combo.clear()
        self.deter_end_year_combo.clear()
        
        # Adiciona anos disponíveis (SEM opção vazia)
        for year in available_years:
            self.deter_start_year_combo.addItem(str(year))
            self.deter_end_year_combo.addItem(str(year))
        
        # Define valores padrão: primeiro ano e ano atual
        if len(available_years) >= 1:
            # Primeiro ano disponível e último ano
            first_year = available_years[0]
            last_year = available_years[-1]
            
            self.deter_start_year_combo.setCurrentText(str(first_year))
            self.deter_end_year_combo.setCurrentText(str(last_year))
            
            # Define variáveis
            self.deter_start_year = first_year
            self.deter_end_year = last_year
            
            print(f"🔧 DEBUG DETER: Valores padrão definidos: {first_year} - {last_year}")

    def populate_deter_classes(self):
        """Popula as classes DETER baseado no bioma selecionado"""
        if not self.selected_biome or self.selected_biome not in self.deter_classes:
            print(f"🔧 DEBUG: Bioma não encontrado nas classes DETER: {self.selected_biome}")
            return
        
        print(f"🔧 DEBUG DETER: Populando classes para {self.selected_biome}")
        
        # Limpa checkboxes anteriores se existirem
        if hasattr(self, 'deter_classes_checkboxes'):
            for checkbox in self.deter_classes_checkboxes.values():
                try:
                    checkbox.setParent(None)
                    checkbox.deleteLater()
                except:
                    pass
        
        # Inicializa dicionário
        self.deter_classes_checkboxes = {}
        
        # Classes disponíveis para o bioma
        available_classes = self.deter_classes[self.selected_biome]
        print(f"🔧 DEBUG DETER: Classes disponíveis: {available_classes}")
        
        # Cria checkboxes para cada classe - BLOQUEANDO SINAIS durante criação
        for class_name in available_classes:
            checkbox = QCheckBox(class_name)
            checkbox.blockSignals(True)  # BLOQUEIA sinais durante inicialização
            checkbox.setChecked(True)  # Marca todas por padrão
            
            self.deter_classes_checkboxes[class_name] = checkbox
            self.deter_classes_layout.addWidget(checkbox)
            print(f"🔧 DEBUG DETER: Checkbox criado para {class_name}")
        
        # Atualiza lista de classes selecionadas - SEMPRE UMA LISTA
        self.deter_selected_classes = list(available_classes) if available_classes else []
        print(f"🔧 DEBUG DETER: deter_selected_classes inicializada como: {self.deter_selected_classes}")
        
        # AGORA conecta os sinais e reativa após TODA a inicialização
        for class_name, checkbox in self.deter_classes_checkboxes.items():
            checkbox.blockSignals(False)  # REATIVA sinais
            checkbox.stateChanged.connect(self.on_deter_class_changed)
            print(f"🔧 DEBUG DETER: Signal conectado para {class_name}")
        
        # Mostra informação específica do bioma
        if self.selected_biome == 'Cerrado':
            info_label = QLabel("ℹ️ Cerrado possui apenas a classe DESMATAMENTO_CR")
            info_label.setStyleSheet("color: #666666; font-style: italic;")
            self.deter_classes_layout.addWidget(info_label)

    def on_deter_start_year_changed(self, year_text):
        """Callback para mudança do ano inicial DETER"""
        try:
            print(f"🔧 DEBUG on_deter_start_year_changed: year_text='{year_text}'")
            
            if year_text and year_text.strip():
                self.deter_start_year = int(year_text)
                print(f"🔧 DEBUG on_deter_start_year_changed: start_year definido como {self.deter_start_year}")
                # Valida imediatamente para feedback rápido
                if not self.validate_deter_year_range():
                    return
            else:
                self.deter_start_year = None
                print(f"🔧 DEBUG on_deter_start_year_changed: start_year definido como None")
            
            self.update_deter_notes()
            
            # Proteção adicional
            try:
                self.update_navigation_buttons()
            except Exception as nav_error:
                print(f"⚠️ WARNING on_deter_start_year_changed navigation error: {str(nav_error)}")
                
        except Exception as e:
            print(f"❌ ERROR on_deter_start_year_changed: {str(e)}")
            self.deter_start_year = None

    def on_deter_end_year_changed(self, year_text):
        """Callback para mudança do ano final DETER"""
        try:
            print(f"🔧 DEBUG on_deter_end_year_changed: year_text='{year_text}'")
            
            if year_text and year_text.strip():
                self.deter_end_year = int(year_text)
                print(f"🔧 DEBUG on_deter_end_year_changed: end_year definido como {self.deter_end_year}")
                # Valida imediatamente para feedback rápido
                if not self.validate_deter_year_range():
                    return
            else:
                self.deter_end_year = None
                print(f"🔧 DEBUG on_deter_end_year_changed: end_year definido como None")
            
            self.update_deter_notes()
            
            # Proteção adicional
            try:
                self.update_navigation_buttons()
            except Exception as nav_error:
                print(f"⚠️ WARNING on_deter_end_year_changed navigation error: {str(nav_error)}")
                
        except Exception as e:
            print(f"❌ ERROR on_deter_end_year_changed: {str(e)}")
            self.deter_end_year = None

    def validate_deter_year_range(self):
        """Valida o intervalo de anos DETER selecionado"""
        try:
            if (hasattr(self, 'deter_start_year') and self.deter_start_year and 
                hasattr(self, 'deter_end_year') and self.deter_end_year and 
                self.deter_start_year > self.deter_end_year):
                
                # Preenchimento automático ao invés de reset
                print(f"⚠️ WARNING: Ano inválido detectado - start: {self.deter_start_year}, end: {self.deter_end_year}")
                
                # Estratégia inteligente - detecta qual foi alterado
                import inspect
                caller_frame = inspect.currentframe().f_back
                caller_name = caller_frame.f_code.co_name if caller_frame else ""
                
                if "deter_start_year" in caller_name:
                    # Foi alterado o ano inicial, ajusta o ano final para ser igual
                    print(f"🔧 DEBUG: Ano inicial alterado, ajustando ano final para {self.deter_start_year}")
                    if hasattr(self, 'deter_end_year_combo'):
                        self.deter_end_year_combo.setCurrentText(str(self.deter_start_year))
                        self.deter_end_year = self.deter_start_year
                    self.update_notes(f"✅ Ano final ajustado automaticamente para {self.deter_start_year}")
                else:
                    # Foi alterado o ano final, mantém o final e ajusta o inicial se necessário
                    print(f"🔧 DEBUG: Ano final alterado para valor menor, ajustando para {self.deter_start_year}")
                    if hasattr(self, 'deter_end_year_combo'):
                        self.deter_end_year_combo.setCurrentText(str(self.deter_start_year))
                        self.deter_end_year = self.deter_start_year
                    self.update_notes(f"✅ Ano final ajustado automaticamente para {self.deter_start_year}")
                
                return False  # Retorna False para indicar que houve correção
            
            return True
        except Exception as e:
            print(f"❌ ERROR validate_deter_year_range: {str(e)}")
            return True  # Em caso de erro, não bloqueia

    def on_deter_class_changed(self):
        """Callback para mudança das classes DETER selecionadas"""
        try:
            # Inicializa como lista vazia
            self.deter_selected_classes = []
            
            if hasattr(self, 'deter_classes_checkboxes'):
                for class_name, checkbox in self.deter_classes_checkboxes.items():
                    if checkbox.isChecked():
                        self.deter_selected_classes.append(class_name)
            
            print(f"🔧 DEBUG DETER: Classes selecionadas: {self.deter_selected_classes}")
            
            # Verificação inteligente baseada no bioma
            if self.selected_biome and self.selected_biome in self.deter_classes:
                available_classes = self.deter_classes[self.selected_biome]
                total_available = len(available_classes)
                total_selected = len(self.deter_selected_classes)
                
                if total_selected == 0:
                    print("❌ ERRO: Classes DETER não foram selecionadas!")
                elif total_selected == total_available:
                    print(f"✅ INFO: Todas as {total_selected} classes selecionadas - download SEM filtro de classes")
                else:
                    print(f"✅ INFO: {total_selected}/{total_available} classes selecionadas - download COM filtro de classes")
            
            self.update_deter_notes()
            self.update_navigation_buttons()
        except Exception as e:
            print(f"❌ ERROR on_deter_class_changed: {str(e)}")
            # Garante que deter_selected_classes seja sempre uma lista em caso de erro
            self.deter_selected_classes = []

    # =====================================
    # FUNÇÕES ÁREA QUEIMADA
    # =====================================
    
    def generate_queimadas_months(self):
        """Gera lista de meses disponíveis dinamicamente (09/2002 até mês atual -1)"""
        try:
            import datetime
            
            # Data atual
            now = datetime.datetime.now()
            
            # Mês anterior (atual -1)
            if now.month == 1:
                end_year = now.year - 1
                end_month = 12
            else:
                end_year = now.year
                end_month = now.month - 1
            
            # Lista de meses no formato YYYY_MM_01
            months = []
            
            # Começar em setembro de 2002
            year = 2002
            month = 9
            
            while year < end_year or (year == end_year and month <= end_month):
                month_str = f"{year:04d}_{month:02d}_01"
                months.append(month_str)
                
                # Próximo mês
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            
            print(f"🔥 DEBUG: {len(months)} meses de área queimada disponíveis (2002-09 até {end_year:04d}-{end_month:02d})")
            return months
            
        except Exception as e:
            print(f"❌ ERROR generate_queimadas_months: {str(e)}")
            return []
    
    def create_queimadas_step2_content(self):
        """Cria o conteúdo específico para configuração ÁREA QUEIMADA"""
        
        # Campo 1: Tipo de Dados
        data_type_group = QGroupBox("1. Tipo de Dados")
        data_type_layout = QVBoxLayout()
        
        self.queimadas_data_type_button_group = QButtonGroup()
        
        self.radio_queimadas_anual = QRadioButton("Anual (dados do ano unidos e dissolvidos)")
        self.radio_queimadas_anual.setToolTip("Baixa todos os meses do ano selecionado e os une em um único arquivo")
        self.radio_queimadas_anual.setChecked(True)  # Padrão anual
        
        self.radio_queimadas_mensal = QRadioButton("Mensal (dados originais)")
        self.radio_queimadas_mensal.setToolTip("Baixa arquivos mensais individuais para o período selecionado")
        
        self.queimadas_data_type_button_group.addButton(self.radio_queimadas_anual, 0)
        self.queimadas_data_type_button_group.addButton(self.radio_queimadas_mensal, 1)
        self.queimadas_data_type_button_group.buttonClicked.connect(self.on_queimadas_data_type_changed)
        
        data_type_layout.addWidget(self.radio_queimadas_anual)
        data_type_layout.addWidget(self.radio_queimadas_mensal)
        data_type_group.setLayout(data_type_layout)
        self.content_layout.addWidget(data_type_group)
        
        # Campo 2: Seleção de Período
        self.queimadas_period_group = QGroupBox("2. Mês/Ano")
        period_layout = QVBoxLayout()
        
        # Container para seleção de ano (modo anual)
        self.queimadas_year_widget = QWidget()
        year_layout = QHBoxLayout(self.queimadas_year_widget)
        year_layout.setContentsMargins(0, 0, 0, 0)
        
        year_label = QLabel("Ano:")
        self.queimadas_year_combo = QComboBox()
        self.queimadas_year_combo.currentTextChanged.connect(self.on_queimadas_year_changed)
        
        year_layout.addWidget(year_label)
        year_layout.addWidget(self.queimadas_year_combo)
        year_layout.addStretch()
        
        # Container para seleção de período mensal (SIMPLIFICADO - apenas 1 mês)
        self.queimadas_month_widget = QWidget()
        month_layout = QHBoxLayout(self.queimadas_month_widget)
        month_layout.setContentsMargins(0, 0, 0, 0)
        
        month_label = QLabel("Mês/Ano:")
        self.queimadas_month_combo = QComboBox()
        self.queimadas_month_combo.currentTextChanged.connect(self.on_queimadas_month_changed)
        
        month_layout.addWidget(month_label)
        month_layout.addWidget(self.queimadas_month_combo)
        month_layout.addStretch()
        
        period_layout.addWidget(self.queimadas_year_widget)
        period_layout.addWidget(self.queimadas_month_widget)
        
        self.queimadas_period_group.setLayout(period_layout)
        self.content_layout.addWidget(self.queimadas_period_group)
        
        # Inicializa valores padrão
        self.queimadas_data_type = "anual"
        self.queimadas_year = None
        self.queimadas_month = None  # SIMPLIFICADO - apenas 1 mês
        
        # Popula combos
        self.populate_queimadas_years()
        self.populate_queimadas_months()
        
        # Atualiza interface inicial
        self.update_queimadas_interface()
        self.update_queimadas_notes()
    
    def populate_queimadas_years(self):
        """Popula combo de anos para modo anual"""
        self.queimadas_year_combo.clear()
        self.queimadas_year_combo.addItem("")
        
        for year in self.queimadas_years:
            self.queimadas_year_combo.addItem(str(year))
        
        # Define valor padrão (ano mais recente)
        if self.queimadas_years:
            self.queimadas_year_combo.setCurrentText(str(self.queimadas_years[-1]))
    
    def populate_queimadas_months(self):
        """Popula combo de meses para modo mensal (SIMPLIFICADO - apenas 1 mês)"""
        self.queimadas_month_combo.clear()
        self.queimadas_month_combo.addItem("")
        
        # Formata meses para exibição mais amigável
        for month_str in self.queimadas_months:
            # Converte YYYY_MM_01 para MM/YYYY
            year, month, _ = month_str.split('_')
            display_text = f"{month}/{year}"
            
            self.queimadas_month_combo.addItem(display_text, month_str)
        
        # Define valor padrão (último mês disponível)
        if self.queimadas_months:
            last_month = self.queimadas_months[-1]
            year, month, _ = last_month.split('_')
            last_display = f"{month}/{year}"
            self.queimadas_month_combo.setCurrentText(last_display)
    
    def on_queimadas_data_type_changed(self, button):
        """Callback para mudança do tipo de dados ÁREA QUEIMADA"""
        option_id = self.queimadas_data_type_button_group.id(button)
        if option_id == 0:
            self.queimadas_data_type = "anual"
        elif option_id == 1:
            self.queimadas_data_type = "mensal"
        
        self.update_queimadas_interface()
        self.update_queimadas_notes()
        self.update_navigation_buttons()
    
    def update_queimadas_interface(self):
        """Atualiza interface baseada no tipo de dados selecionado"""
        if self.queimadas_data_type == "anual":
            self.queimadas_year_widget.setVisible(True)
            self.queimadas_month_widget.setVisible(False)
        else:  # mensal
            self.queimadas_year_widget.setVisible(False)
            self.queimadas_month_widget.setVisible(True)
    
    def on_queimadas_year_changed(self, year_text):
        """Callback para mudança do ano (modo anual)"""
        if year_text and year_text.strip():
            try:
                self.queimadas_year = int(year_text)
                print(f"🔥 DEBUG: Ano selecionado: {self.queimadas_year}")
            except ValueError:
                self.queimadas_year = None
        else:
            self.queimadas_year = None
            
        self.update_queimadas_notes()
        self.update_navigation_buttons()
    
    def on_queimadas_month_changed(self, month_text):
        """Callback para mudança do mês (modo mensal simplificado)"""
        if month_text and month_text.strip():
            # Encontra o valor interno correspondente
            index = self.queimadas_month_combo.currentIndex()
            if index > 0:  # Ignora item vazio
                self.queimadas_month = self.queimadas_month_combo.itemData(index)
                print(f"🔥 DEBUG: Mês selecionado: {self.queimadas_month} ({month_text})")
            else:
                self.queimadas_month = None
        else:
            self.queimadas_month = None
            
        self.update_queimadas_notes()
        self.update_navigation_buttons()
    
    def update_queimadas_notes(self):
        """Atualiza as notas específicas para ÁREA QUEIMADA"""
        try:
            notes_parts = [f"📊 Tema: ÁREA QUEIMADA", f"🌿 Bioma: {self.selected_biome}"]
            
            if hasattr(self, 'queimadas_data_type') and self.queimadas_data_type:
                type_text = "Anual (dissolvido)" if self.queimadas_data_type == "anual" else "Mensal (original)"
                notes_parts.append(f"📈 Tipo: {type_text}")
            
            # Informações de período
            if self.queimadas_data_type == "anual" and hasattr(self, 'queimadas_year') and self.queimadas_year:
                notes_parts.append(f"🗓️ Ano: {self.queimadas_year}")
                # Calcula quantos meses serão baixados
                months_count = len([m for m in self.queimadas_months if m.startswith(f"{self.queimadas_year:04d}_")])
                if months_count > 0:
                    notes_parts.append(f"📋 Arquivos: {months_count} meses serão unidos")
            elif self.queimadas_data_type == "mensal":
                if hasattr(self, 'queimadas_month') and self.queimadas_month:
                    # Formata para exibição
                    year, month, _ = self.queimadas_month.split('_')
                    notes_parts.append(f"🗓️ Mês: {month}/{year}")
                    notes_parts.append(f"📋 Arquivos: 1 arquivo mensal")
            
            # Informações de limite espacial (ÁREA QUEIMADA sempre corta por bioma)
            notes_parts.append(f"✂️ Corte automático: Bioma {self.selected_biome}")
            
            # Se há corte adicional configurado, menciona também
            if hasattr(self, 'cut_option') and self.cut_option is not None and self.cut_option != 0:
                if self.cut_option == 1 and hasattr(self, 'selected_layer') and self.selected_layer:
                    notes_parts.append(f"➕ Corte adicional: {self.selected_layer.name()}")
                elif self.cut_option == 2:
                    notes_parts.append("➕ Corte adicional: Retângulo desenhado")
                elif self.cut_option == 3:
                    notes_parts.append("➕ Corte adicional: IBGE")
            
            if notes_parts:
                config_text = " | ".join(notes_parts)
                self.update_notes(config_text, "config")
            else:
                self.update_notes("💡 Configure o tipo e período para ÁREA QUEIMADA", "config")
                
        except Exception as e:
            print(f"❌ ERROR update_queimadas_notes: {str(e)}")
            self.update_notes("⚠️ Erro ao atualizar notas ÁREA QUEIMADA", "error")
    
    def validate_queimadas_settings(self):
        """Valida se as configurações ÁREA QUEIMADA estão completas"""
        try:
            if not hasattr(self, 'queimadas_data_type') or not self.queimadas_data_type:
                return False
                
            if self.queimadas_data_type == "anual":
                return hasattr(self, 'queimadas_year') and self.queimadas_year is not None
            else:  # mensal
                return hasattr(self, 'queimadas_month') and self.queimadas_month
                        
        except Exception as e:
            print(f"❌ ERROR validate_queimadas_settings: {str(e)}")
            return False
    
    def process_queimadas_data(self):
        """Processa os dados ÁREA QUEIMADA conforme configurações"""
        try:
            print(f"🔥 DEBUG: === INICIANDO PROCESSAMENTO ÁREA QUEIMADA ===")
            
            # NOVO: Reseta log de processamentos para nova operação
            self.processing_log = []
            
            # CORREÇÃO: Carrega shapefile IBGE para corte por bioma
            print(f"🔥 DEBUG: Carregando shapefile IBGE para corte por bioma...")
            if not hasattr(self, 'ibge_layer') or not self.ibge_layer:
                success = self.load_ibge_shapefile()
                if not success:
                    print(f"⚠️ WARNING: Falha ao carregar shapefile IBGE - corte por bioma pode não funcionar")
                else:
                    print(f"✅ DEBUG: Shapefile IBGE carregado com sucesso: {self.ibge_layer.featureCount()} feições")
            else:
                print(f"✅ DEBUG: Shapefile IBGE já carregado: {self.ibge_layer.featureCount()} feições")
            
            # Gera nome do arquivo baseado nas seleções
            self.output_filename = self.generate_queimadas_output_filename()
            print(f"📁 DEBUG: Nome do arquivo ÁREA QUEIMADA: {self.output_filename}")
            
            # Constrói lista de URLs para download
            self.queimadas_download_info = self.build_queimadas_download_info()
            print(f"🌐 DEBUG: Info de download ÁREA QUEIMADA: {len(self.queimadas_download_info['urls'])} arquivos")
            
            # Inicia processamento REAL
            self.current_step_index = 0
            self.processing_layers = []  # Para armazenar layers baixadas
            
            # Etapa 1: Baixar arquivos ZIP
            self.queimadas_step_download_files()
            
        except Exception as e:
            print(f"❌ ERROR process_queimadas_data: {str(e)}")
            self.status_label.setText(f"❌ Erro no processamento ÁREA QUEIMADA: {str(e)}")
            self.end_download_mode(success=False)
    
    def generate_queimadas_output_filename(self):
        """Gera nome do arquivo de saída para ÁREA QUEIMADA"""
        try:
            # Componentes do nome
            theme = "area_queimada"
            biome = self.selected_biome.lower().replace(' ', '_').replace('ã', 'a').replace('ô', 'o')
            
            # Período baseado no tipo
            if self.queimadas_data_type == "anual":
                period = f"{self.queimadas_year}"
                data_type = "anual_dissolvido"
            else:  # mensal
                year, month, _ = self.queimadas_month.split('_')
                period = f"{year}{month}"
                data_type = "mensal_original"
            
            # Tipo de corte
            cut_name = self.get_cut_option_name()
            
            # Nome final
            filename = f"{theme}_{biome}_{period}_{data_type}_{cut_name}"
            
            # Limita tamanho do nome
            if len(filename) > 100:
                filename = f"{theme}_{biome}_{period}_{cut_name}"
            
            print(f"📁 DEBUG: Nome ÁREA QUEIMADA gerado: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ ERROR generate_queimadas_output_filename: {str(e)}")
            return f"area_queimada_{self.selected_biome.lower()}_{self.queimadas_data_type}"
    
    def build_queimadas_download_info(self):
        """Constrói informações de download para ÁREA QUEIMADA"""
        try:
            result = {
                'urls': [],
                'months': [],
                'data_type': self.queimadas_data_type
            }
            
            if self.queimadas_data_type == "anual":
                # Busca todos os meses do ano selecionado
                year_months = [m for m in self.queimadas_months if m.startswith(f"{self.queimadas_year:04d}_")]
                for month_str in year_months:
                    url = self.build_queimadas_url(month_str)
                    result['urls'].append(url)
                    result['months'].append(month_str)
                    
                print(f"🔥 DEBUG: Ano {self.queimadas_year} - {len(year_months)} meses encontrados")
                    
            else:  # mensal (SIMPLIFICADO - apenas 1 mês)
                month_str = self.queimadas_month
                url = self.build_queimadas_url(month_str)
                result['urls'].append(url)
                result['months'].append(month_str)
                    
                print(f"🔥 DEBUG: Mês selecionado: {month_str}")
            
            if not result['urls']:
                raise Exception("Nenhum arquivo encontrado para o período selecionado")
                
            return result
            
        except Exception as e:
            print(f"❌ ERROR build_queimadas_download_info: {str(e)}")
            return {'urls': [], 'months': [], 'data_type': self.queimadas_data_type}
    
    def build_queimadas_url(self, month_str):
        """Constrói URL específica baseada no mês (resolve problema v/V)"""
        try:
            # Extrai ano e mês do formato YYYY_MM_01
            year, month, day = month_str.split('_')
            year_int = int(year)
            month_int = int(month)
            
            # CORREÇÃO: Define padrão v/V baseado na data
            # Até agosto de 2020 (2020_08_01): usa 'v' minúsculo
            # A partir de setembro de 2020 (2020_09_01): usa 'V' maiúsculo
            if year_int < 2020 or (year_int == 2020 and month_int <= 8):
                version = "v6"  # minúsculo
            else:
                version = "V6"  # maiúsculo
            
            url = f"{self.queimadas_base_url}{month_str}_aq1km_{version}.zip"
            print(f"🔥 DEBUG: URL construída: {url} (padrão: {version})")
            
            return url
            
        except Exception as e:
            print(f"❌ ERROR build_queimadas_url: {str(e)}")
            # Fallback para padrão antigo
            return f"{self.queimadas_base_url}{month_str}_aq1km_v6.zip"
    
    def queimadas_step_download_files(self):
        """Etapa 1: Baixa arquivos ZIP de área queimada"""
        try:
            self.status_label.setText("📥 Baixando arquivos de área queimada...")
            
            total_files = len(self.queimadas_download_info['urls'])
            print(f"🔥 DEBUG: Iniciando download de {total_files} arquivos")
            print(f"🔥 DEBUG: Salvando queimadas_download_info para metadados")
            
            # CORREÇÃO: Cria variável para metadados com informações detalhadas
            # Esta variável será usada na função generate_metadata_file
            self.queimadas_download_info_metadata = {
                'urls': self.queimadas_download_info['urls'].copy(),
                'months': self.queimadas_download_info['months'].copy(),
                'base_url': self.queimadas_base_url,
                'data_type': self.queimadas_data_type,
                'year': getattr(self, 'queimadas_year', None),
                'month': getattr(self, 'queimadas_month', None)
            }
            
            self.queimadas_downloaded_files = []
            self.queimadas_current_file = 0
            
            # Inicia download do primeiro arquivo
            self.download_next_queimadas_file()
            
        except Exception as e:
            print(f"❌ ERROR queimadas_step_download_files: {str(e)}")
            self.status_label.setText(f"❌ Erro no download: {str(e)}")
            self.end_download_mode(success=False)
    
    def download_next_queimadas_file(self):
        """Baixa o próximo arquivo da lista"""
        try:
            if self.queimadas_current_file >= len(self.queimadas_download_info['urls']):
                # Todos os arquivos baixados - próxima etapa
                print(f"✅ DEBUG: Todos os {len(self.queimadas_downloaded_files)} arquivos baixados")
                QTimer.singleShot(1000, self.queimadas_step_extract_files)
                return
            
            url = self.queimadas_download_info['urls'][self.queimadas_current_file]
            month_str = self.queimadas_download_info['months'][self.queimadas_current_file]
            
            file_num = self.queimadas_current_file + 1
            total_files = len(self.queimadas_download_info['urls'])
            
            print(f"🔥 DEBUG: Baixando arquivo {file_num}/{total_files}: {month_str}")
            self.status_label.setText(f"📥 Baixando área queimada {file_num}/{total_files}: {month_str}")
            
            # Aplica verificação de abort
            if self.check_abort_signal():
                return
            
            # Inicia download assíncrono
            self.download_queimadas_zip(url, month_str)
            
        except Exception as e:
            print(f"❌ ERROR download_next_queimadas_file: {str(e)}")
            self.status_label.setText(f"❌ Erro no download: {str(e)}")
            self.end_download_mode(success=False)
    
    def download_queimadas_zip(self, url, month_str):
        """Baixa um arquivo ZIP específico de área queimada"""
        try:
            import os
            import tempfile
            from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
            from qgis.PyQt.QtCore import QUrl
            
            # Arquivo temporário para download
            temp_dir = tempfile.gettempdir()
            zip_filename = f"{month_str}_aq1km_v6.zip"
            temp_zip_path = os.path.join(temp_dir, zip_filename)
            
            print(f"🔥 DEBUG: Baixando de {url}")
            print(f"🔥 DEBUG: Salvando em {temp_zip_path}")
            
            # Inicia download
            request = QNetworkRequest(QUrl(url))
            request.setRawHeader(b'User-Agent', b'QGIS DesagregaBiomasBR')
            
            reply = self.network_manager.get(request)
            
            # Conecta sinais para este download específico
            reply.finished.connect(lambda: self.on_queimadas_zip_downloaded(reply, temp_zip_path, month_str))
            reply.errorOccurred.connect(lambda error: self.on_queimadas_download_error(error, month_str))
            
            # Armazena reply para possível cancelamento
            self.current_queimadas_reply = reply
            
        except Exception as e:
            print(f"❌ ERROR download_queimadas_zip: {str(e)}")
            self.status_label.setText(f"❌ Erro no download {month_str}: {str(e)}")
            self.end_download_mode(success=False)
    
    def on_queimadas_zip_downloaded(self, reply, temp_zip_path, month_str):
        """Callback quando download do ZIP é concluído"""
        try:
            if reply.error() == QNetworkReply.NoError:
                # Salva arquivo
                with open(temp_zip_path, 'wb') as f:
                    f.write(reply.readAll().data())
                
                file_size = os.path.getsize(temp_zip_path)
                print(f"✅ DEBUG: Arquivo {month_str} baixado: {file_size} bytes")
                
                # Adiciona à lista de arquivos baixados
                self.queimadas_downloaded_files.append({
                    'path': temp_zip_path,
                    'month': month_str
                })
                
                # Próximo arquivo
                self.queimadas_current_file += 1
                QTimer.singleShot(500, self.download_next_queimadas_file)
                
            else:
                error_msg = reply.errorString()
                print(f"❌ DEBUG: Erro no download {month_str}: {error_msg}")
                self.status_label.setText(f"❌ Erro no download {month_str}: {error_msg}")
                self.end_download_mode(success=False)
            
            reply.deleteLater()
            
        except Exception as e:
            print(f"❌ ERROR on_queimadas_zip_downloaded: {str(e)}")
            self.status_label.setText(f"❌ Erro ao salvar {month_str}: {str(e)}")
            self.end_download_mode(success=False)
    
    def on_queimadas_download_error(self, error, month_str):
        """Callback para erro no download"""
        print(f"❌ DEBUG: Erro de rede {month_str}: {error}")
        self.status_label.setText(f"❌ Erro de rede {month_str}: {error}")
        self.end_download_mode(success=False)
    
    def queimadas_step_extract_files(self):
        """Etapa 2: Extrai arquivos ZIP e carrega shapefiles"""
        try:
            self.status_label.setText("📂 Extraindo arquivos de área queimada...")
            
            total_files = len(self.queimadas_downloaded_files)
            print(f"🔥 DEBUG: Extraindo {total_files} arquivos ZIP")
            
            self.queimadas_extracted_layers = []
            self.queimadas_current_extract = 0
            
            # Inicia extração do primeiro arquivo
            self.extract_next_queimadas_file()
            
        except Exception as e:
            print(f"❌ ERROR queimadas_step_extract_files: {str(e)}")
            self.status_label.setText(f"❌ Erro na extração: {str(e)}")
            self.end_download_mode(success=False)
    
    def extract_next_queimadas_file(self):
        """Extrai o próximo arquivo ZIP e carrega o shapefile"""
        try:
            if self.queimadas_current_extract >= len(self.queimadas_downloaded_files):
                # Todos os arquivos extraídos - próxima etapa
                print(f"✅ DEBUG: Todas as {len(self.queimadas_extracted_layers)} layers carregadas")
                QTimer.singleShot(1000, self.queimadas_step_process_layers)
                return
            
            file_info = self.queimadas_downloaded_files[self.queimadas_current_extract]
            zip_path = file_info['path']
            month_str = file_info['month']
            
            file_num = self.queimadas_current_extract + 1
            total_files = len(self.queimadas_downloaded_files)
            
            print(f"🔥 DEBUG: Extraindo arquivo {file_num}/{total_files}: {month_str}")
            self.status_label.setText(f"📂 Extraindo área queimada {file_num}/{total_files}: {month_str}")
            
            # Aplica verificação de abort
            if self.check_abort_signal():
                return
            
            # Extrai ZIP e carrega shapefile
            layer = self.extract_and_load_queimadas_shapefile(zip_path, month_str)
            
            if layer and layer.isValid():
                self.queimadas_extracted_layers.append({
                    'layer': layer,
                    'month': month_str
                })
                print(f"✅ DEBUG: Layer {month_str} carregada: {layer.featureCount()} feições")
            else:
                print(f"⚠️ DEBUG: Falha ao carregar layer {month_str}")
            
            # Próximo arquivo
            self.queimadas_current_extract += 1
            QTimer.singleShot(500, self.extract_next_queimadas_file)
            
        except Exception as e:
            print(f"❌ ERROR extract_next_queimadas_file: {str(e)}")
            self.status_label.setText(f"❌ Erro na extração: {str(e)}")
            self.end_download_mode(success=False)
    
    def extract_and_load_queimadas_shapefile(self, zip_path, month_str):
        """Extrai ZIP e carrega o shapefile de área queimada"""
        try:
            import zipfile
            import tempfile
            import os
            from qgis.core import QgsVectorLayer
            
            # Cria diretório temporário para extração
            extract_dir = os.path.join(tempfile.gettempdir(), f"queimadas_{month_str}")
            os.makedirs(extract_dir, exist_ok=True)
            
            # Extrai ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                extracted_files = zip_ref.namelist()
                print(f"🔥 DEBUG: Extraídos {len(extracted_files)} arquivos para {extract_dir}")
            
            # Procura arquivo .shp
            shp_file = None
            for file in extracted_files:
                if file.endswith('.shp'):
                    shp_file = os.path.join(extract_dir, file)
                    break
            
            if not shp_file or not os.path.exists(shp_file):
                print(f"❌ DEBUG: Arquivo .shp não encontrado em {zip_path}")
                return None
            
            # Carrega shapefile
            layer = QgsVectorLayer(shp_file, f"area_queimada_{month_str}", "ogr")
            
            if layer.isValid():
                print(f"✅ DEBUG: Shapefile {month_str} carregado: {layer.featureCount()} feições")
                return layer
            else:
                print(f"❌ DEBUG: Shapefile {month_str} inválido")
                return None
                
        except Exception as e:
            print(f"❌ ERROR extract_and_load_queimadas_shapefile: {str(e)}")
            return None
    
    def queimadas_step_process_layers(self):
        """Etapa 3: Processa layers (merge para anual ou mantém mensal) - OTIMIZADO"""
        try:
            if self.queimadas_data_type == "anual":
                self.status_label.setText("🔄 Unindo dados anuais de área queimada...")
                print(f"🔥 DEBUG: Modo anual - unindo {len(self.queimadas_extracted_layers)} layers")
                
                # Une todas as layers do ano (SEM dissolve ainda - será feito após corte)
                layers = [item['layer'] for item in self.queimadas_extracted_layers]
                merged_layer = self.merge_layers(layers)
                
                if merged_layer and merged_layer.isValid():
                    print(f"✅ DEBUG: Layers anuais unidas: {merged_layer.featureCount()} feições")
                    self.processing_layers = [merged_layer]
                else:
                    raise Exception("Falha ao unir layers anuais")
                    
            else:  # mensal
                self.status_label.setText("📋 Processando dados mensais de área queimada...")
                print(f"🔥 DEBUG: Modo mensal - mantendo {len(self.queimadas_extracted_layers)} layers separadas")
                
                # Mantém layers separadas
                self.processing_layers = [item['layer'] for item in self.queimadas_extracted_layers]
            
            # CORTE AUTOMÁTICO POR BIOMA para ÁREA QUEIMADA
            # Como os dados são sempre do Brasil todo, aplicamos corte automático pelo bioma
            # OTIMIZAÇÃO: Dissolve será aplicado APÓS o corte para maior eficiência
            QTimer.singleShot(1000, self.queimadas_step_apply_biome_cut)
            
        except Exception as e:
            print(f"❌ ERROR queimadas_step_process_layers: {str(e)}")
            self.status_label.setText(f"❌ Erro no processamento: {str(e)}")
            self.end_download_mode(success=False)
    
    def queimadas_step_apply_biome_cut(self):
        """Etapa específica para ÁREA QUEIMADA: Aplica corte automático por bioma"""
        try:
            self.status_label.setText("✂️ Aplicando corte por bioma...")
            
            # Lista feições originais antes do corte
            total_original = sum([layer.featureCount() for layer in self.processing_layers])
            
            # Cria layer de corte baseada no bioma selecionado
            cut_layer = self.get_queimadas_biome_cut_layer()
            
            if not cut_layer or not cut_layer.isValid():
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"❌ FALHA: Corte por bioma não funcionou para {self.selected_biome}", "DesagregaBiomasBR", Qgis.Warning)
                # Se não conseguir cortar, continua com dados originais mas ainda prossegue
                QTimer.singleShot(1000, self.queimadas_check_additional_cut)
                return
            
            # Aplica corte em todas as layers de processamento
            cut_layers = []
            total_cut = 0
            
            for i, layer in enumerate(self.processing_layers):
                self.status_label.setText(f"✂️ Preparando layer {i+1}/{len(self.processing_layers)} para corte...")
                
                # ETAPA 1: Corrigir geometrias inválidas
                fixed_layer = self.auto_fix_geometries(layer, f"queimadas_{i}")
                
                if not fixed_layer or not fixed_layer.isValid():
                    fixed_layer = layer
                
                # ETAPA 2: Reprojetar para o mesmo CRS do shapefile IBGE
                target_crs = cut_layer.crs()
                
                if fixed_layer.crs().authid() != target_crs.authid():
                    reprojected_layer = self.reproject_layer(fixed_layer, target_crs)
                    
                    if not reprojected_layer or not reprojected_layer.isValid():
                        prepared_layer = fixed_layer
                    else:
                        prepared_layer = reprojected_layer
                else:
                    prepared_layer = fixed_layer
                
                # ETAPA 3: Aplicar corte espacial (sem registro individual - será registrado em lote)
                self.status_label.setText(f"✂️ Cortando layer {i+1}/{len(self.processing_layers)} por bioma...")
                
                # Temporariamente desativa registro para evitar duplicação
                original_count = prepared_layer.featureCount()
                
                cut_result = self.clip_layer(prepared_layer, cut_layer, log_processing=False)
                
                if cut_result and cut_result.isValid():
                    cut_count = cut_result.featureCount()
                    cut_layers.append(cut_result)
                    total_cut += cut_count
                else:
                    cut_layers.append(layer)  # Usa original se corte falhar
                    total_cut += layer.featureCount()
            
            # Atualiza layers de processamento com versões cortadas por bioma
            if total_cut < total_original:
                reduction = total_original - total_cut
                percentage = (reduction / total_original) * 100
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"✅ SUCESSO: Corte por bioma aplicado! {total_original} → {total_cut} feições ({percentage:.1f}% redução)", "DesagregaBiomasBR", Qgis.Success)
                
                # NOVO: Registra processamento de corte por bioma
                self.add_processing_log(
                    "CORTE POR BIOMA",
                    f"{total_original} feições → {total_cut} feições (redução de {percentage:.1f}%) - Bioma: {self.selected_biome}"
                )
            else:
                # NOVO: Registra quando não houve redução
                self.add_processing_log(
                    "CORTE POR BIOMA",
                    f"{total_original} feições mantidas - Bioma: {self.selected_biome} (dados já estavam dentro do bioma)"
                )
            
            self.processing_layers = cut_layers
            
            # OTIMIZAÇÃO: Aplica dissolve APÓS o corte (só para modo anual)
            # Agora dissolve apenas os dados do bioma, não do Brasil todo!
            if self.queimadas_data_type == "anual" and len(self.processing_layers) == 1:
                QTimer.singleShot(1000, self.queimadas_step_dissolve_after_cut)
            else:
                # Modo mensal ou sem necessidade de dissolve - continua
                QTimer.singleShot(1000, self.queimadas_check_additional_cut)
            
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            error_msg = f"❌ ERRO queimadas_step_apply_biome_cut: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "DesagregaBiomasBR", Qgis.Critical)
            self.status_label.setText(f"❌ Erro no corte por bioma: {str(e)}")
            # Continua mesmo com erro de corte
            QTimer.singleShot(1000, self.queimadas_check_additional_cut)
    
    def queimadas_check_additional_cut(self):
        """Verifica se ÁREA QUEIMADA precisa de corte espacial adicional além do bioma"""
        try:
            # Para ÁREA QUEIMADA:
            # - SEMPRE aplicamos corte por bioma (já foi feito)
            # - SE o usuário selecionou corte adicional (cut_option != 0 e != None), aplicamos também
            # - SE não selecionou corte adicional, vamos direto para merge
            
            needs_additional_cut = (
                hasattr(self, 'cut_option') and 
                self.cut_option is not None and 
                self.cut_option != 0
            )
            
            if needs_additional_cut:
                # Tem corte adicional configurado - aplicar
                self.status_label.setText("✂️ Aplicando corte espacial adicional...")
                QTimer.singleShot(1000, self.real_step_apply_spatial_cut)
            else:
                # Não tem corte adicional - só o corte por bioma é suficiente
                self.status_label.setText("✅ Corte por bioma concluído")
                QTimer.singleShot(1000, self.real_step_merge_layers)
            
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"❌ ERRO queimadas_check_additional_cut: {str(e)}", "DesagregaBiomasBR", Qgis.Critical)
            # Em caso de erro, continua para merge
            QTimer.singleShot(1000, self.real_step_merge_layers)

    def get_queimadas_biome_cut_layer(self):
        """Cria layer de corte baseada no bioma selecionado para ÁREA QUEIMADA"""
        try:
            if not self.ibge_layer:
                return None
            
            # Constrói expressão de filtro baseada no bioma
            if self.selected_biome == 'Amazônia Legal':
                # Para Amazônia Legal, usa coluna 'regiao'
                expression = f'"regiao" = \'Amazônia Legal\''
            else:
                # Para outros biomas, usa coluna 'bioma' (com b minúsculo)
                expression = f'"bioma" = \'{self.selected_biome}\''
            
            # Aplica filtro
            request = QgsFeatureRequest().setFilterExpression(expression)
            
            # Conta quantas feições correspondem ao filtro
            filtered_features = list(self.ibge_layer.getFeatures(request))
            
            if not filtered_features:
                return None
            
            # Cria layer filtrada em memória
            filtered_layer = QgsVectorLayer(f"Polygon?crs={self.ibge_layer.crs().authid()}", f"corte_{self.selected_biome}", "memory")
            provider = filtered_layer.dataProvider()
            provider.addAttributes(self.ibge_layer.fields())
            filtered_layer.updateFields()
            
            # Adiciona feições filtradas
            provider.addFeatures(filtered_features)
            filtered_layer.updateExtents()
            
            return filtered_layer
                
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            error_msg = f"❌ ERRO get_queimadas_biome_cut_layer: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "DesagregaBiomasBR", Qgis.Critical)
            return None

    def queimadas_step_dissolve_after_cut(self):
        """NOVA ETAPA OTIMIZADA: Aplica dissolve APÓS o corte por bioma para maior eficiência"""
        try:
            self.status_label.setText("🔄 Dissolvendo áreas queimadas adjacentes (pós-corte)...")
            print(f"🔥 DEBUG: Aplicando dissolve otimizado após corte por bioma...")
            
            # Pega a layer já cortada por bioma
            cut_layer = self.processing_layers[0]
            features_before = cut_layer.featureCount()
            
            print(f"🔥 DEBUG: Dissolve pós-corte - processando {features_before} feições do bioma {self.selected_biome}")
            
            # Aplica dissolve nas áreas queimadas já cortadas
            dissolved_layer = self.dissolve_queimadas_layer(cut_layer)
            
            if dissolved_layer and dissolved_layer.isValid():
                features_after = dissolved_layer.featureCount()
                reduction = features_before - features_after
                
                self.processing_layers = [dissolved_layer]
                print(f"✅ DEBUG: Dissolve pós-corte concluído: {features_before} → {features_after} feições")
                
                if reduction > 0:
                    percentage = (reduction / features_before) * 100
                    self.add_processing_log(
                        "DISSOLUÇÃO DE ÁREAS QUEIMADAS",
                        f"{features_before} feições → {features_after} feições (redução de {percentage:.1f}%) - Bioma: {self.selected_biome}"
                    )
                else:
                    self.add_processing_log(
                        "DISSOLUÇÃO DE ÁREAS QUEIMADAS",
                        f"{features_before} feições mantidas (sem áreas adjacentes para unir) - Bioma: {self.selected_biome}"
                    )
                    
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"✅ SUCESSO: Dissolve pós-corte - {features_before} → {features_after} feições", "DesagregaBiomasBR", Qgis.Success)
                
            else:
                # Se dissolve falhar, usa layer cortada mesmo
                print(f"⚠️ DEBUG: Dissolve pós-corte falhou, usando layer cortada")
                self.add_processing_log(
                    "DISSOLUÇÃO DE ÁREAS QUEIMADAS",
                    f"Falha no dissolve - mantendo {features_before} feições cortadas do bioma {self.selected_biome}"
                )
            
            # Continua para verificação de corte adicional
            QTimer.singleShot(1000, self.queimadas_check_additional_cut)
            
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            error_msg = f"❌ ERRO queimadas_step_dissolve_after_cut: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "DesagregaBiomasBR", Qgis.Critical)
            self.status_label.setText(f"❌ Erro no dissolve: {str(e)}")
            
            # Continua mesmo com erro no dissolve
            QTimer.singleShot(1000, self.queimadas_check_additional_cut)

    # =====================================
    # FUNÇÕES TERRACLASS
    # =====================================
    
    def populate_terraclass_years(self):
        """Popula os anos baseado no bioma TERRACLASS selecionado"""
        if not self.selected_biome or self.selected_biome not in self.terraclass_years:
            return
        
        # Anos disponíveis para o bioma
        available_years = self.terraclass_years[self.selected_biome]
        
        # Limpa combo
        self.terraclass_year_combo.clear()
        
        # Adiciona opção vazia
        self.terraclass_year_combo.addItem("")
        
        # Adiciona anos disponíveis
        for year in available_years:
            self.terraclass_year_combo.addItem(str(year))
        
        # NÃO define valor padrão - deixa em branco
        self.terraclass_year = None

    def populate_terraclass_states(self):
        """Popula o combo de estados baseado no bioma TERRACLASS selecionado"""
        if not self.selected_biome:
            return
        
        # Carrega o shapefile IBGE se ainda não foi carregado
        if not self.ibge_layer:
            self.load_ibge_shapefile()
        
        if not self.ibge_layer:
            return
        
        # Limpa combo
        self.terraclass_state_combo.clear()
        self.terraclass_state_combo.addItem("")
        
        # Determina filtro baseado no bioma
        expression = f'"bioma" = \'{self.selected_biome}\''
        
        # Aplica filtro e obtém estados únicos
        request = QgsFeatureRequest().setFilterExpression(expression)
        states = set()
        
        for feature in self.ibge_layer.getFeatures(request):
            state = feature['estado']
            if state:
                states.add(state)
        
        # Adiciona estados ordenados ao combo
        sorted_states = sorted(states)
        for state in sorted_states:
            self.terraclass_state_combo.addItem(state)
        
        # NÃO define estado padrão - deixa em branco
        self.terraclass_state = None

    def populate_terraclass_municipalities(self, biome, state):
        """Popula o combo de municípios baseado na seleção de bioma e estado"""
        if not self.ibge_layer:
            return
        
        # Limpa combo
        self.terraclass_municipality_combo.clear()
        self.terraclass_municipality_combo.addItem("")
        
        # Constrói filtro combinado
        expression = f'"bioma" = \'{biome}\' AND "estado" = \'{state}\''
        
        # Aplica filtro e obtém municípios únicos
        request = QgsFeatureRequest().setFilterExpression(expression)
        municipalities = set()
        
        for feature in self.ibge_layer.getFeatures(request):
            municipality = feature['nome']
            if municipality:
                municipalities.add(municipality)
        
        # Adiciona municípios ordenados ao combo
        for municipality in sorted(municipalities):
            self.terraclass_municipality_combo.addItem(municipality)

    def on_terraclass_year_changed(self, year_text):
        """Callback para mudança do ano TERRACLASS"""
        try:
            if year_text and year_text.strip():
                self.terraclass_year = int(year_text)
            else:
                self.terraclass_year = None
            
            self.update_terraclass_notes()
            self.update_navigation_buttons()
                
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"❌ ERRO on_terraclass_year_changed: {str(e)}", "DesagregaBiomasBR", Qgis.Critical)
            self.terraclass_year = None

    def on_terraclass_state_changed(self, state_text):
        """Callback para mudança do estado TERRACLASS"""
        try:
            self.terraclass_state = state_text if state_text and state_text.strip() else None
            
            if self.terraclass_state and self.selected_biome:
                # Popula municípios quando estado é selecionado
                self.populate_terraclass_municipalities(self.selected_biome, self.terraclass_state)
            else:
                # Limpa municípios se estado for desmarcado
                if hasattr(self, 'terraclass_municipality_combo'):
                    self.terraclass_municipality_combo.clear()
                    self.terraclass_municipality_combo.addItem("")
                self.terraclass_municipality = None
            
            self.update_terraclass_notes()
            self.update_navigation_buttons()
                
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"❌ ERRO on_terraclass_state_changed: {str(e)}", "DesagregaBiomasBR", Qgis.Critical)
            self.terraclass_state = None

    def on_terraclass_municipality_changed(self, municipality_text):
        """Callback para mudança do município TERRACLASS"""
        try:
            self.terraclass_municipality = municipality_text if municipality_text and municipality_text.strip() else None
            
            self.update_terraclass_notes()
            self.update_navigation_buttons()
                
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"❌ ERRO on_terraclass_municipality_changed: {str(e)}", "DesagregaBiomasBR", Qgis.Critical)
            self.terraclass_municipality = None

    def update_terraclass_notes(self):
        """Atualiza as notas com informações do TERRACLASS - INTEGRAÇÃO COM INTERFACE RESPONSIVA"""
        if self.selected_theme != "TERRACLASS":
            return
        
        # Para TERRACLASS, integra com o sistema de notas responsivo
        # Atualiza as notas completas que incluem TERRACLASS automaticamente
        self.update_comprehensive_notes_responsive()

    def update_deter_notes(self):
        """Atualiza as notas com informações do DETER - SISTEMA SIMPLIFICADO"""
        if self.current_step != 2 or self.selected_theme != "DETER":
            return
        
        # Apenas informações específicas da etapa 2 - não repete config da etapa 1
        status_parts = []
        
        # Informações de classes com lógica inteligente
        if hasattr(self, 'deter_selected_classes') and isinstance(self.deter_selected_classes, list):
            if self.selected_biome and self.selected_biome in self.deter_classes:
                available_classes = self.deter_classes[self.selected_biome]
                total_available = len(available_classes)
                total_selected = len(self.deter_selected_classes)
                
                if total_selected == 0:
                    status_parts.append("⚠️ Classes: Nenhuma selecionada")
                elif total_selected == total_available:
                    status_parts.append(f"✅ Classes: Todas ({total_selected}) - SEM filtro")
                else:
                    status_parts.append(f"🏷️ Classes: {total_selected} selecionada(s)")
        
        # Informações de anos
        if hasattr(self, 'deter_start_year') and hasattr(self, 'deter_end_year'):
            if self.deter_start_year and self.deter_end_year:
                status_parts.append(f"🗓️ Período: {self.deter_start_year} - {self.deter_end_year}")
        
        # Atualiza apenas a linha de status (não toda a configuração)
        if status_parts:
            self.update_notes(" | ".join(status_parts), "status")
        else:
            self.update_notes("💡 Configure o período e classes DETER", "status")

    # =====================================
    # SISTEMA DE ABORTAR DOWNLOAD
    # =====================================

    def abort_processing(self):
        """Aborta o processamento em andamento de forma segura"""
        if not self.download_in_progress:
            return
        
        # Define flag de abort
        self.abort_download = True
        
        # Atualiza interface imediatamente
        self.update_notes("🛑 Abortando download... Aguarde alguns segundos", "status")
        self.btn_abort.setText("⏳ Abortando...")
        self.btn_abort.setEnabled(False)  # Desabilita botao temporariamente
        self.status_label.setText("🛑 Abortando processamento...")
        
        # Forca atualizacao da interface
        QgsApplication.processEvents()

    def reset_download_state(self):
        """Reseta o estado do download para permitir novo processamento"""
        self.abort_download = False
        self.download_in_progress = False
        
        # Restaura interface
        self.progress_bar.setVisible(False)
        self.btn_process.setEnabled(True)
        self.btn_abort.setVisible(False)
        self.btn_abort.setEnabled(True)
        
        # CORREÇÃO: Reseta texto do botão abortar para próximo uso
        self.btn_abort.setText("🛑 Abortar Download")
        
        # Atualiza notas
        self.update_processing_notes()

    def check_abort_signal(self):
        """Verifica se foi solicitado abortar o download"""
        if self.abort_download:
            # Limpa arquivos temporários se necessário
            self.cleanup_temp_files()
            
            # Reseta estado
            self.reset_download_state()
            
            # Atualiza interface
            self.update_notes("🛑 Download abortado pelo usuário", "status")
            self.status_label.setText("🛑 Processamento abortado")
            
            return True
        return False

    def cleanup_temp_files(self):
        """Limpa arquivos temporários criados durante o download"""
        try:
            import tempfile
            import glob
            temp_dir = tempfile.gettempdir()
            
            # Remove arquivos temporários relacionados ao plugin
            patterns = [
                f"*{id(self)}*.gml",
                f"*{id(self)}*.shp",
                f"*{id(self)}*.zip"
            ]
            
            for pattern in patterns:
                files = glob.glob(os.path.join(temp_dir, pattern))
                for file in files:
                    try:
                        os.remove(file)
                    except:
                        pass
                        
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"❌ ERRO ao limpar arquivos temporários: {str(e)}", "DesagregaBiomasBR", Qgis.Warning)

    def start_download_mode(self):
        """Ativa o modo de download com botão de abortar visível"""
        self.download_in_progress = True
        self.abort_download = False
        
        # Mostra botão de abortar e esconde botão de processar
        self.btn_process.setVisible(False)
        self.btn_abort.setVisible(True)
        self.btn_abort.setEnabled(True)
        
        # CORREÇÃO: Garante que o texto do botão esteja correto
        self.btn_abort.setText("🛑 Abortar Download")
        
        # Desabilita outros botões durante download
        self.btn_back.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_finish.setEnabled(False)

    def end_download_mode(self, success=True):
        """Desativa o modo de download e restaura interface normal"""
        self.download_in_progress = False
        self.abort_download = False
        
        # Esconde barra de progresso
        self.progress_bar.setVisible(False)
        
        # Restaura botões principais
        self.btn_process.setVisible(True)
        self.btn_abort.setVisible(False)
        
        if success:
            self.btn_process.setEnabled(True)
            self.btn_process.setText("🔄 Processar Novamente")
        else:
            self.btn_process.setEnabled(True)
            self.btn_process.setText("🚀 Iniciar Processamento")
        
        # Reabilita outros botões
        self.btn_back.setEnabled(True)
        self.btn_next.setEnabled(True)
        self.btn_finish.setEnabled(True)


