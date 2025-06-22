# -*- coding: utf-8 -*-
"""
DesagregaBiomasBR Plugin
Classe principal de integração com QGIS
"""

import os.path
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .dialog import DesagregaBiomasBRDialog


class DesagregaBiomasBR:
    """Plugin principal DesagregaBiomasBR."""

    def __init__(self, iface):
        """Constructor.

        :param iface: Interface instance do QGIS
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'DesagregaBiomasBR_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&DesagregaBiomasBR')
        
        # Barra de ferramentas personalizada
        self.toolbar = None

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        # Create the dialog instance
        self.dlg = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('DesagregaBiomasBR', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.
        :type whats_this: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :returns: The action that was created.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # Cria barra de ferramentas simples (sem estilo, só funcional)
        self.toolbar = self.iface.addToolBar(u'DesagregaBiomasBR')
        self.toolbar.setObjectName(u'DesagregaBiomasBRToolbar')
        self.toolbar.setToolTip(u'DesagregaBiomasBR - Dados de Biomas Brasileiros')
        
        # Estilo minimalista - sem bordas, sem fundo, só ícone
        self.toolbar.setStyleSheet("""
            QToolBar {
                background: transparent;
                border: none;
                spacing: 2px;
                padding: 2px;
            }
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 3px;
                padding: 3px;
                margin: 1px;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 3px;
            }
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)

        icon_path = os.path.join(self.plugin_dir, 'icones', 'mapa.png')
        
        # Botão simples - só ícone, sem texto
        main_action = QAction(QIcon(icon_path), '', self.iface.mainWindow())
        main_action.setToolTip('DesagregaBiomasBR\nDownload de dados dos biomas brasileiros')
        main_action.setStatusTip('Abrir DesagregaBiomasBR')
        main_action.triggered.connect(self.run)
        
        # Adiciona à barra
        self.toolbar.addAction(main_action)
        
        # Define tamanho do ícone (20% maior que padrão, que é normalmente 16px)
        button = self.toolbar.widgetForAction(main_action)
        if button:
            button.setIconSize(QSize(15, 15))  # 20% maior que 16px padrão
        
        # Adiciona também ao menu tradicional
        self.add_action(
            icon_path,
            text=self.tr(u'DesagregaBiomasBR'),
            callback=self.run,
            add_to_toolbar=False,  # Não adiciona à barra padrão (já temos a personalizada)
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&DesagregaBiomasBR'),
                action)
            self.iface.removeToolBarIcon(action)
        
        # Remove a barra de ferramentas personalizada
        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

    def run(self):
        """Run method that performs all the real work"""
        try:
            # SEMPRE cria uma nova instância para garantir estado limpo
            print("🔄 DEBUG: Criando nova instância do DesagregaBiomasBRDialog")
            
            # Destrói instância anterior se existir
            if hasattr(self, 'dlg') and self.dlg is not None:
                print("🗑️ DEBUG: Verificando instância anterior")
                try:
                    # Testa se o objeto ainda é válido
                    self.dlg.isVisible()  # Método simples para testar validade
                    print("🗑️ DEBUG: Destruindo instância anterior válida")
                    self.dlg.deleteLater()
                except RuntimeError:
                    print("✅ DEBUG: Instância anterior já foi destruída (conforme esperado)")
                finally:
                    self.dlg = None
            
            # Cria SEMPRE uma nova instância
            self.dlg = DesagregaBiomasBRDialog()
            print("✅ DEBUG: Nova instância criada com estado limpo")

            # Verifica se a criação foi bem-sucedida
            if self.dlg is None:
                print("❌ ERROR: Falha na criação do diálogo!")
                return

            # show the dialog
            self.dlg.show()
            # Traz a janela para frente
            self.dlg.raise_()
            self.dlg.activateWindow()
            
        except Exception as e:
            print(f"❌ ERROR: Falha na inicialização do plugin: {str(e)}")
            import traceback
            traceback.print_exc() 