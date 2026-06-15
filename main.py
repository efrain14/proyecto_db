import sys
import os
import customtkinter as ctk

# Importamos los módulos correspondientes
from database.conexion import crear_tablas
from gui.login import mostrar_ventana_login
from gui.dashboard import mostrar_dashboard # <-- NUEVA IMPORTACIÓN

def abrir_dashboard():
    """Llama a la interfaz principal del programa al pasar el login exitosamente."""
    mostrar_dashboard()

def inicio():
    # 1. Asegurar base de datos limpia al arrancar
    crear_tablas()
    
    # 2. Arrancar con el Login
    mostrar_ventana_login(abrir_dashboard)

if __name__ == "__main__":
    inicio()