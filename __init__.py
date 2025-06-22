# -*- coding: utf-8 -*-
"""
DesagregaBiomasBR Plugin
Plugin para seleção e desagregação de dados PRODES, DETER ou TERRACLASS
"""

def classFactory(iface):
    """Load DesagregaBiomasBR class from file plugin_main.
    
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .plugin_main import DesagregaBiomasBR
    return DesagregaBiomasBR(iface) 