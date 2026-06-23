# =========================================================================
# ARCHIVO DE ARRANQUE PRINCIPAL (main.py)
# =========================================================================

from database.conexion import inicializar_base_de_datos
from gui.login import mostrar_ventana_login  # Profesor: Importamos tu módulo de Login
from gui.dashboard import mostrar_dashboard

import customtkinter as ctk

def iniciar_sistema():
    """
    Profesor: Explicación del flujo lógico del Sistema:
    1. Prepara las tablas y asegura el usuario administrador en la DB.
    2. Invoca el Login y le inyecta la función del Menú Principal como orden secreta.
    3. Si las claves coinciden, el Login muere y se despliega el Dashboard.
    """
    
    # 1. Asegurar la persistencia de datos
    inicializar_base_de_datos()
    
    # 2. Configuración estética global
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    # 3. Lanzar Portero (Login) pasándole la Pantalla Principal como destino exitoso
    # Profesor: Pasamos 'mostrar_dashboard' sin los paréntesis () para que no se ejecute
    # de inmediato, sino que el Login decida CUÁNDO llamarla.
    mostrar_ventana_login(mostrar_dashboard)

if __name__ == "__main__":
    iniciar_sistema()