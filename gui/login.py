import customtkinter as ctk
from tkinter import messagebox
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.conexion import conectar

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def validar_login(txt_usuario, txt_contrasena, ventana_login, al_conectar_exito):
    usuario = txt_usuario.get().strip()
    contrasena = txt_contrasena.get().strip()
    
    if not usuario or not contrasena:
        messagebox.showwarning("Campos Vacíos", "Por favor, llene todos los campos.")
        return

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND contrasena = ?", (usuario, contrasena))
    usuario_encontrado = cursor.fetchone()
    conn.close()
    
    if usuario_encontrado:
        ventana_login.destroy()
        al_conectar_exito()
    else:
        messagebox.showerror("Error de Acceso", "Usuario o contraseña incorrectos.")

def mostrar_ventana_login(funcion_menu_principal):
    root = ctk.CTk()
    root.title("Sistema Funerario - Login")
    
    ancho = 400
    alto = 350
    pantalla_ancho = root.winfo_screenwidth()
    pantalla_alto = root.winfo_screenheight()
    x = (pantalla_ancho // 2) - (ancho // 2)
    y = (pantalla_alto // 2) - (alto // 2)
    root.geometry(f"{ancho}x{alto}+{x}+{y}")
    root.resizable(False, False)

    lbl_titulo = ctk.CTkLabel(root, text="Control de Afiliados", font=("Arial", 24, "bold"))
    lbl_titulo.pack(pady=(30, 20))
    
    txt_usuario = ctk.CTkEntry(root, placeholder_text="Nombre de usuario", width=250, height=40)
    txt_usuario.pack(pady=10)
    
    txt_contrasena = ctk.CTkEntry(root, placeholder_text="Contraseña", show="*", width=250, height=40)
    txt_contrasena.pack(pady=10)
    
    # Profesor: Vinculamos las acciones del Enter (<Return>) en el Login
    # Al dar enter en usuario, pasa a la contraseña
    txt_usuario.bind("<Return>", lambda event: txt_contrasena.focus())
    # Al dar enter en contraseña, ejecuta la validación directamente
    txt_contrasena.bind("<Return>", lambda event: validar_login(txt_usuario, txt_contrasena, root, funcion_menu_principal))
    
    btn_ingresar = ctk.CTkButton(
        root, 
        text="Iniciar Sesión", 
        width=250, 
        height=40,
        font=("Arial", 14, "bold"),
        command=lambda: validar_login(txt_usuario, txt_contrasena, root, funcion_menu_principal)
    )
    btn_ingresar.pack(pady=(20, 10))
    
    root.mainloop()