# =========================================================================
# CONEXIÓN A LA BASE DE DATOS
# =========================================================================
# Este módulo centraliza la ubicación de funeraria.db:
#   - En desarrollo (python main.py): usa la raíz del proyecto.
#   - Compilado (.exe con PyInstaller): usa la carpeta donde está el .exe.
# =========================================================================
import os
import sys
import sqlite3


def obtener_ruta_base():
    """
    Devuelve la carpeta donde debe vivir funeraria.db.
    - Si el programa corre como .exe: la misma carpeta del ejecutable.
    - Si corre desde VS Code: la raíz del proyecto.
    """
    if getattr(sys, "frozen", False):
        # Ejecutable compilado con PyInstaller
        return os.path.dirname(sys.executable)

    # Desarrollo normal
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def obtener_ruta_db():
    """Ruta completa del archivo de base de datos."""
    return os.path.join(obtener_ruta_base(), "funeraria.db")


def conectar():
    """Abre la conexión a funeraria.db en la ubicación correcta."""
    return sqlite3.connect(obtener_ruta_db())

