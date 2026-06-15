import customtkinter as ctk
from tkinter import messagebox
import sys
import os

# Permitir que encuentre la carpeta database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.conexion import conectar

# Configuración visual general de CustomTkinter
ctk.set_appearance_mode("System")  # Detecta si Windows está en modo oscuro o claro
ctk.set_default_color_theme("blue") # Tema de color de los botones

def validar_login(txt_usuario, txt_contrasena, ventana_login, al_conectar_exito):
    """Verifica si las credenciales coinciden con la base de datos."""
    usuario = txt_usuario.get().strip()
    contrasena = txt_contrasena.get().strip()
    
    if not usuario or not contrasena:
        messagebox.showwarning("Campos Vacíos", "Por favor, llene todos los campos.")
        return

    conn = conectar()
    cursor = conn.cursor()
    
    # Buscamos en la tabla usuarios si coinciden ambos campos
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND contrasena = ?", (usuario, contrasena))
    usuario_encontrado = cursor.fetchone()
    conn.close()
    
    if usuario_encontrado:
        # ¡Éxito! Cerramos la ventana de login y llamamos a la función que abrirá el menú principal
        ventana_login.destroy()
        al_conectar_exito()
    else:
        messagebox.showerror("Error de Acceso", "Usuario o contraseña incorrectos.")

def mostrar_ventana_login(funcion_menu_principal):
    """Crea y muestra la ventana física de inicio de sesión."""
    # Crear la ventana principal de CustomTkinter
    root = ctk.CTk()
    root.title("Sistema Funerario - Login")
    
    # Centrar la ventana en la pantalla (Dimensiones: 400x350)
    ancho = 400
    alto = 350
    pantalla_ancho = root.winfo_screenwidth()
    pantalla_alto = root.winfo_screenheight()
    x = (pantalla_ancho // 2) - (ancho // 2)
    y = (pantalla_alto // 2) - (alto // 2)
    root.geometry(f"{ancho}x{alto}+{x}+{y}")
    root.resizable(False, False) # Evita que cambien el tamaño de la ventana

    # --- DISEÑO DE LA INTERFAZ ---
    
    # Título Principal
    lbl_titulo = ctk.CTkLabel(root, text="Control de Afiliados", font=("Arial", 24, "bold"))
    lbl_titulo.pack(pady=(30, 20))
    
    # Campo: Usuario
    txt_usuario = ctk.CTkEntry(root, placeholder_text="Nombre de usuario", width=250, height=40)
    txt_usuario.pack(pady=10)
    
    # Campo: Contraseña (usamos show="*" para ocultar el texto)
    txt_contrasena = ctk.CTkEntry(root, placeholder_text="Contraseña", show="*", width=250, height=40)
    txt_contrasena.pack(pady=10)
    
    # Botón de Ingresar
    # El comando 'lambda' nos permite pasarle variables a nuestra función de validación
    btn_ingresar = ctk.CTkButton(
        root, 
        text="Iniciar Sesión", 
        width=250, 
        height=40,
        font=("Arial", 14, "bold"),
        command=lambda: validar_login(txt_usuario, txt_contrasena, root, funcion_menu_principal)
    )
    btn_ingresar.pack(pady=(20, 10))
    
    # Iniciar el bucle de la ventana (para que se quede abierta esperando clics)
    root.mainloop()