# =========================================================================
# SISTEMA FUNERARIO - DASHBOARD PRINCIPAL
# =========================================================================
# Este archivo contiene la interfaz gráfica principal del sistema.
# Estructura del archivo:
#   1. Importaciones y configuración global
#   2. Funciones utilitarias (validadores, formateadores)
#   3. Funciones de lógica de negocio (base de datos, cálculos)
#   4. Función mostrar_dashboard() con las 5 pestañas
#   5. Componente modal de registro de afiliados
# =========================================================================

# -------------------------------------------------------------------------
# 1. IMPORTACIONES Y CONFIGURACIÓN GLOBAL
# -------------------------------------------------------------------------
import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
from datetime import datetime
import re
import sys
import os
import shutil

# Asegurar que Python localice la carpeta raíz del proyecto para las importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.conexion import conectar, obtener_ruta_db
from logic.consultas import consultar_estado_cliente
from gui.preview_recibo import abrir_previsualizacion_recibo
#from gui.reportes_gui import renderizar_grafico_cobranza

# Variable global de control operativo para la sucursal
SEDE_ACTUAL = "A"


# =========================================================================
# 2. FUNCIONES UTILITARIAS (Validadores y formateadores)
# =========================================================================
# Estas funciones se usan para validar la entrada del usuario en los campos
# de texto y para formatear valores monetarios.
# =========================================================================

def validar_solo_numeros(char):
    """Permite únicamente el ingreso de dígitos numéricos en los Entry."""
    return char.isdigit() or char == ""


def validar_monto_decimal(texto_entrante):
    """
    Permite solo números y un solo punto o coma decimal para montos en Bs.
    Se usa en los campos de Tasa BCV y Monto Cobrado.
    """
    if texto_entrante == "":
        return True

    if " " in texto_entrante:
        return False

    p_norm = texto_entrante.replace(",", ".")

    try:
        float(p_norm)
        return True
    except ValueError:
        return False


def validar_mascara_cedula(cedula_texto):
    """
    Filtro estricto de cédulas venezolanas usando RegEx.
    Formato válido: V o E seguido de 7 a 8 dígitos.
    Ejemplos válidos: V12345678, E87654321, v1234567
    """
    patron = r"^[VEve]\d{7,8}$"
    return bool(re.match(patron, cedula_texto.strip()))


def validar_solo_letras(texto):
    """
    Garantiza que en campos de nombres/apellidos no se escriban números.
    Permite espacios entre palabras.
    """
    return texto == "" or texto.replace(" ", "").isalpha()


def validar_monto_tasa(texto_entrante):
    """Filtro de teclado en caliente para la Tasa BCV."""
    if texto_entrante == "":
        return True

    try:
        if " " in texto_entrante:
            return False

        float(texto_entrante)
        return True
    except ValueError:
        return False


def validar_fecha_teclado(texto_entrante):
    """
    Permite escribir solamente una fecha con formato DD/MM/YYYY.
    Bloquea letras, espacios y caracteres inválidos mientras el usuario escribe.
    """
    if texto_entrante == "":
        return True

    if len(texto_entrante) > 10:
        return False

    patron = r"^\d{0,2}(/\d{0,2}(/\d{0,4})?)?$"
    return bool(re.match(patron, texto_entrante))


def validar_fecha_ddmmyyyy(fecha_texto):
    """
    Valida que la fecha sea realmente válida y tenga formato DD/MM/YYYY.
    Retorna True si la fecha está vacía (campo opcional) o si es válida.
    """
    if not fecha_texto:
        return True

    if len(fecha_texto) != 10:
        return False

    try:
        datetime.strptime(fecha_texto, "%d/%m/%Y")
        return True
    except ValueError:
        return False


def formatear_moneda_ve(monto):
    """
    Conversor de moneda al formato de Venezuela.
    Ejemplo: 1250.50 → "1.250,50 Bs"
    """
    texto = f"{monto:,.2f}"
    texto = texto.replace(",", "X")
    texto = texto.replace(".", ",")
    texto = texto.replace("X", ".")
    return f"{texto} Bs"


def convertir_numero(texto):
    """
    Convierte texto numérico a float.
    Soporta formatos: 1234.56 | 1234,56 | 1.234,56
    """
    texto = (texto or "").strip()

    if not texto:
        return 0.0

    # Formato tipo 1.234,56 (punto como separador de miles, coma como decimal)
    if "," in texto and "." in texto and texto.rfind(",") > texto.rfind("."):
        texto = texto.replace(".", "").replace(",", ".")

    # Formato tipo 1234,56 (coma como decimal)
    elif "," in texto:
        texto = texto.replace(",", ".")

    return float(texto)


def obtener_monto_usd_plan(tipo_contrato):
    """
    Devuelve el monto en USD de la cuota según el plan del titular.
    Regla de negocio:
      - Si el plan incluye 'entierro', la cuota es $20.
      - En cualquier otro caso, la cuota es $10.
    No existe cuota de $12.
    """
    plan = (tipo_contrato or "").lower()

    if "entierro" in plan:
        return 20.0

    return 10.0


def calcular_edad_exacta(fecha_str):
    """
    Calcula los años exactos de una persona a partir de su fecha de nacimiento.
    La fecha debe tener formato DD/MM/YYYY.
    Retorna None si la fecha no es válida.
    """
    try:
        if len(fecha_str) != 10:
            return None

        fn = datetime.strptime(fecha_str, "%d/%m/%Y")
        h = datetime.now()

        return h.year - fn.year - ((h.month, h.day) < (fn.month, fn.day))
    except:
        return None


def vincular_salto_enter(widget_actual, widget_siguiente):
    """
    Permite al operador avanzar de casilla usando la tecla Enter.
    Esto es fundamental para la transcripción rápida de datos.
    """
    widget_actual.bind("<Return>", lambda e: widget_siguiente.focus())


# =========================================================================
# 3. FUNCIONES DE LÓGICA DE NEGOCIO (Base de datos y cálculos)
# =========================================================================

def asegurar_esquema_pagos():
    """
    Prepara la tabla 'pagos' para trabajar con:
      - Columna cuota_numero (número de cuota pagada)
      - Índice único en num_recibo (evita recibos duplicados)
    
    No borra datos. Solo adapta la estructura si hace falta.
    Se ejecuta una vez al iniciar el dashboard.
    """
    try:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(pagos)")
        columnas = {row[1] for row in cursor.fetchall()}

        if "cuota_numero" not in columnas:
            cursor.execute("ALTER TABLE pagos ADD COLUMN cuota_numero INTEGER")
            conn.commit()

        # Verificar si hay recibos duplicados antes de crear índice único
        cursor.execute("""
            SELECT num_recibo, COUNT(*)
            FROM pagos
            GROUP BY num_recibo
            HAVING COUNT(*) > 1
            LIMIT 1
        """)

        duplicado = cursor.fetchone()

        if not duplicado:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_pagos_num_recibo
                ON pagos(num_recibo)
            """)
            conn.commit()
        else:
            print("Aviso: existen recibos duplicados en pagos. No se creó índice único.")

        conn.close()

    except Exception as e:
        print(f"Aviso al preparar esquema de pagos: {e}")


def obtener_siguiente_recibo(cursor):
    """
    Devuelve el próximo número de recibo único.
    Usa MAX(num_recibo) + 1 para garantizar secuencia.
    """
    cursor.execute("""
        SELECT COALESCE(MAX(CAST(num_recibo AS INTEGER)), 0) + 1
        FROM pagos
    """)

    row = cursor.fetchone()

    try:
        return int(row[0]) if row and row[0] is not None else 1
    except:
        return 1


def calcular_cuota_numero(tipo_contrato, total_cuotas):
    """
    Calcula el número de cuota que se está pagando según el tipo de plan.
    - Planes PPA de 24 meses: cuota 1 a 24.
    - Planes de renovación de 12 meses: cuota 1 a 12 por ciclo.
    """
    plan = (tipo_contrato or "").lower()

    if total_cuotas <= 0:
        return 1

    if "24 meses" in plan:
        return min(24, total_cuotas)

    if total_cuotas > 24:
        return ((total_cuotas - 24) % 12) or 12

    return (total_cuotas % 12) or 12


def generar_siguiente_contrato():
    """
    Genera el próximo código de contrato del sistema.
    Formato: SEDE-XXXXX (ejemplo: A-00001, A-00002)
    Busca el último contrato registrado y le suma 1.
    """
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT contrato_nuevo FROM titulares WHERE contrato_nuevo LIKE ? ORDER BY contrato_nuevo DESC LIMIT 1",
        (f"{SEDE_ACTUAL}-%",)
    )

    ultimo = cursor.fetchone()
    conn.close()

    if ultimo and ultimo[0]:
        try:
            numero_actual = int(ultimo[0].split("-")[1])
            nuevo_numero = numero_actual + 1
        except:
            nuevo_numero = 1
    else:
        nuevo_numero = 1

    return f"{SEDE_ACTUAL}-{nuevo_numero:05d}"


# =========================================================================
# 4. INTERFAZ GRÁFICA PRINCIPAL (DASHBOARD)
# =========================================================================

def mostrar_dashboard(usuario_actual="admin"):
    """
    Función principal que construye toda la interfaz del dashboard.
    Recibe el nombre del usuario autenticado para mostrar en el título
    y determinar si tiene permisos de administrador.
    """

    # Preparar tabla de pagos para recibos únicos y cuota_numero
    asegurar_esquema_pagos()

    # Consultar el rol del usuario autenticado en la base de datos
    conn_u = conectar()
    cursor_u = conn_u.cursor()
    cursor_u.execute("SELECT rol FROM usuarios WHERE usuario = ?", (usuario_actual,))
    res_u = cursor_u.fetchone()
    conn_u.close()

    rol_usuario = (res_u[0] if res_u and res_u[0] else "operador").lower()
    es_admin = (rol_usuario == "admin" or usuario_actual == "admin")

    # -----------------------------------------------------------------
    # Crear la ventana principal
    # -----------------------------------------------------------------
    ventana = ctk.CTk()
    ventana.title(f"Sistema Funerario - Panel de Control (Sede {SEDE_ACTUAL} | Usuario: {usuario_actual} [{rol_usuario.upper()}])")
    ventana.geometry("1150x850")

    # Ocultar temporalmente la ventana principal mientras se muestra el splash
    ventana.withdraw()

    # -----------------------------------------------------------------
    # SPLASH DE CARGA (ventana de espera)
    # -----------------------------------------------------------------
    splash = ctk.CTkToplevel(ventana)
    splash.title("Cargando sistema")
    splash.geometry("420x200")
    splash.resizable(False, False)
    splash.configure(fg_color="#101010")
    splash.attributes("-topmost", True)
    splash.transient(ventana)
    splash.grab_set()

    # Centrar el splash en la pantalla
    splash.update_idletasks()
    x = (splash.winfo_screenwidth() // 2) - (420 // 2)
    y = (splash.winfo_screenheight() // 2) - (200 // 2)
    splash.geometry(f"420x200+{x}+{y}")

    ctk.CTkLabel(
        splash,
        text="Sistema Funerario",
        font=("Arial", 18, "bold")
    ).pack(pady=(25, 5))

    ctk.CTkLabel(
        splash,
        text="Cargando panel de control...",
        font=("Arial", 12)
    ).pack(pady=(0, 10))

    barra_splash = ctk.CTkProgressBar(splash, width=260)
    barra_splash.set(0.25)
    barra_splash.pack(pady=5)

    splash.update_idletasks()
    splash.update()

    # -----------------------------------------------------------------
    # Registrar validadores de entrada en la ventana
    # -----------------------------------------------------------------
    v_numeros_puro = ventana.register(validar_solo_numeros)
    v_letras = ventana.register(validar_solo_letras)
    v_monto_decimal = ventana.register(validar_monto_decimal)
    v_fecha = ventana.register(validar_fecha_teclado)

    # -----------------------------------------------------------------
    # Configurar estilo de las tablas (Treeview)
    # -----------------------------------------------------------------
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Treeview",
        background="#2a2a2a",
        foreground="white",
        fieldbackground="#2a2a2a",
        rowheight=25
    )
    style.map("Treeview", background=[('selected', '#1f538d')])
    style.configure(
        "Treeview.Heading",
        background="#1f538d",
        foreground="white",
        font=("Arial", 10, "bold")
    )

    # -----------------------------------------------------------------
    # Crear el contenedor de pestañas principal
    # -----------------------------------------------------------------
    pestanas = ctk.CTkTabview(ventana, width=1110, height=800)
    pestanas.pack(pady=10, padx=10, fill="both", expand=True)

    tab_clientes = pestanas.add("Registro de Clientes")
    tab_edicion = pestanas.add("Edición de Titulares y Afiliados")
    tab_pagos = pestanas.add("Control de Pagos y Estado")
    tab_reportes = pestanas.add("Reportes y Estados de Cuenta")

    # La pestaña de Configuración solo aparece si el usuario es administrador
    if es_admin:
        tab_config = pestanas.add("Configuración")

    # -----------------------------------------------------------------
    # Variables globales internas del dashboard
    # Se usan listas para permitir modificación dentro de funciones anidadas
    # -----------------------------------------------------------------
    cedula_titular_edicion = [""]       # Cédula del titular que se está editando
    cedula_titular_pago = [""]          # Cédula del titular en la pestaña de pagos
    proximo_recibo_global = [1]         # Próximo número de recibo a asignar
    tipo_contrato_global = [""]         # Tipo de contrato del titular actual
    nota_titular_global = [""]          # Nota del titular actual (para el popup)
    procesando_pago = [False]           # Bandera para evitar doble clic en procesar pago

    # =========================================================================
    # PESTAÑA 1: REGISTRO DE CLIENTES NUEVOS
    # =========================================================================
    # Esta pestaña permite registrar un nuevo titular con sus datos
    # personales, contrato y afiliados.
    # =========================================================================

    # --- Frame del formulario de registro ---
    frame_form_reg = ctk.CTkFrame(tab_clientes, fg_color="transparent")
    frame_form_reg.grid(row=0, column=0, columnspan=4, pady=10, padx=10, sticky="w")

    # Fila 0-1: Cédula, Contrato Anterior, Fecha Contrato Anterior, Contrato Sistema
    ctk.CTkLabel(frame_form_reg, text="Cédula Titular (Ej: V12345678):", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_cedula = ctk.CTkEntry(frame_form_reg, width=150, placeholder_text="V12345678")
    txt_cedula.grid(row=1, column=0, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="N° Contrato Anterior (Manual):", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    txt_cont_viejo = ctk.CTkEntry(frame_form_reg, width=180, placeholder_text="Opcional")
    txt_cont_viejo.grid(row=1, column=1, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Fecha Contrato Anterior:", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, sticky="w")
    txt_fecha_contrato_ant = ctk.CTkEntry(
        frame_form_reg,
        width=150,
        placeholder_text="DD/MM/YYYY"
    )
    txt_fecha_contrato_ant.grid(row=1, column=2, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="N° Contrato Sistema (Auto):", font=("Arial", 11, "bold")).grid(row=0, column=3, padx=10, sticky="w")
    txt_cont_nuevo = ctk.CTkEntry(
        frame_form_reg,
        width=150,
        fg_color="#1e272e",
        text_color="#2ecc71",
        font=("Arial", 12, "bold")
    )
    txt_cont_nuevo.insert(0, generar_siguiente_contrato())
    txt_cont_nuevo.configure(state="disabled")
    txt_cont_nuevo.grid(row=1, column=3, padx=10, pady=(2, 10))

    # Fila 2-3: Nombres, Apellidos, Fecha de Nacimiento
    ctk.CTkLabel(frame_form_reg, text="Nombres:", font=("Arial", 11, "bold")).grid(row=2, column=0, padx=10, sticky="w")
    txt_nombres = ctk.CTkEntry(frame_form_reg, width=200, validate="key", validatecommand=(v_letras, '%P'))
    txt_nombres.grid(row=3, column=0, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Apellidos:", font=("Arial", 11, "bold")).grid(row=2, column=1, padx=10, sticky="w")
    txt_apellidos = ctk.CTkEntry(frame_form_reg, width=200, validate="key", validatecommand=(v_letras, '%P'))
    txt_apellidos.grid(row=3, column=1, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Fecha Nacimiento:", font=("Arial", 11, "bold")).grid(row=2, column=2, padx=10, sticky="w")
    txt_fecha_nac = ctk.CTkEntry(frame_form_reg, placeholder_text="DD/MM/YYYY", width=150)
    txt_fecha_nac.grid(row=3, column=2, padx=10, pady=(2, 10))

    # Etiqueta de edad calculada (se actualiza al escribir la fecha de nacimiento)
    lbl_edad_titular = ctk.CTkLabel(
        frame_form_reg,
        text=" Edad: -- años ",
        font=("Arial", 11, "bold"),
        fg_color="#f39c12",
        text_color="black",
        corner_radius=6
    )
    lbl_edad_titular.grid(row=5, column=0, padx=10, pady=(2, 10))

    # Evento: calcular edad automáticamente al escribir la fecha de nacimiento
    txt_fecha_nac.bind(
        "<KeyRelease>",
        lambda e: lbl_edad_titular.configure(text=f" Edad: {calcular_edad_exacta(txt_fecha_nac.get().strip()) or '--'} años ")
    )

    # Fila 4-5: Teléfono, Recibos Previos
    ctk.CTkLabel(frame_form_reg, text="Teléfono Contacto:", font=("Arial", 11, "bold")).grid(row=4, column=1, padx=10, sticky="w")
    txt_telefono = ctk.CTkEntry(frame_form_reg, width=200)
    txt_telefono.grid(row=5, column=1, padx=10, pady=(2, 10))

    ctk.CTkLabel(
        frame_form_reg,
        text="Recibos ya Cancelados (Histórico):",
        font=("Arial", 11, "bold", "underline"),
        text_color="#e74c3c"
    ).grid(row=4, column=2, padx=10, sticky="w")

    txt_recibos_previos = ctk.CTkEntry(frame_form_reg, width=150, placeholder_text="Ej: 14 (Vacío = 0)")
    txt_recibos_previos.grid(row=5, column=2, padx=10, pady=(2, 10))

    # Fila 6-7: Correo, Dirección, Tipo de Contrato
    ctk.CTkLabel(frame_form_reg, text="Correo Electrónico:", font=("Arial", 11, "bold")).grid(row=6, column=0, padx=10, sticky="w")
    txt_correo = ctk.CTkEntry(frame_form_reg, width=180)
    txt_correo.grid(row=7, column=0, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Dirección de Habitación:", font=("Arial", 11, "bold")).grid(row=6, column=1, padx=10, sticky="w")
    txt_direccion = ctk.CTkEntry(frame_form_reg, width=200)
    txt_direccion.grid(row=7, column=1, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Tipo de Contrato:", font=("Arial", 11, "bold")).grid(row=6, column=2, padx=10, sticky="w")
    combo_contrato = ctk.CTkComboBox(
        frame_form_reg,
        values=[
            "PPA velación 24 meses",
            "PPA velación + entierro 24 meses",
            "renovación anual 12 meses",
            "renovación anual + entierro 12 meses"
        ],
        width=280
    )
    combo_contrato.grid(row=7, column=2, padx=10, pady=(2, 10))

    # Navegación con Enter en PESTAÑA 1 (orden de transcripción)
    vincular_salto_enter(txt_cedula, txt_cont_viejo)
    vincular_salto_enter(txt_cont_viejo, txt_fecha_contrato_ant)
    vincular_salto_enter(txt_fecha_contrato_ant, txt_nombres)
    vincular_salto_enter(txt_nombres, txt_apellidos)
    vincular_salto_enter(txt_apellidos, txt_fecha_nac)
    vincular_salto_enter(txt_fecha_nac, txt_telefono)
    vincular_salto_enter(txt_telefono, txt_recibos_previos)
    vincular_salto_enter(txt_recibos_previos, txt_correo)
    vincular_salto_enter(txt_correo, txt_direccion)

    # --- Frame de la tabla de afiliados ---
    tabla_frame = ctk.CTkFrame(tab_clientes)
    tabla_frame.grid(row=1, column=0, columnspan=4, pady=10, padx=10, sticky="nsew")

    # --- Campo de Notas / Observaciones del Contrato ---
    ctk.CTkLabel(
        tab_clientes,
        text="Notas / Observaciones del Contrato:",
        font=("Arial", 11, "bold", "underline"),
        text_color="#e67e22"
    ).grid(row=2, column=0, columnspan=3, padx=10, sticky="w")

    txt_notas_registro = ctk.CTkTextbox(
        tab_clientes,
        width=800,
        height=70,
        font=("Arial", 10),
        wrap="word"
    )
    txt_notas_registro.grid(row=3, column=0, columnspan=3, padx=10, pady=(2, 5), sticky="ew")

    # Tabla de afiliados vinculados al titular
    tabla = ttk.Treeview(
        tabla_frame,
        columns=("cedula", "nombres", "apellidos", "parentesco", "f_nac", "edad"),
        show="headings",
        height=5
    )

    for c, t, w in [
        ("cedula", "Cédula", 120),
        ("nombres", "Nombres", 150),
        ("apellidos", "Apellidos", 150),
        ("parentesco", "Parentesco", 120),
        ("f_nac", "F. Nacimiento", 130),
        ("edad", "Edad Calculada", 110)
    ]:
        tabla.heading(c, text=t)
        tabla.column(c, width=w, anchor="center")

    tabla.pack(fill="both", expand=True)

    # =========================================================================
    # PESTAÑA 2: EDICIÓN DE TITULARES Y AFILIADOS
    # =========================================================================
    # Esta pestaña permite buscar un titular existente y modificar sus datos,
    # incluyendo contrato viejo, fecha de contrato viejo y notas.
    # =========================================================================

    # --- Área de búsqueda superior ---
    frame_busq_ed = ctk.CTkFrame(tab_edicion, fg_color="transparent")
    frame_busq_ed.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(
        frame_busq_ed,
        text="Buscar Póliza (Cédula o N° Contratos):",
        font=("Arial", 11, "bold")
    ).grid(row=0, column=0, padx=10, sticky="w")

    txt_busq_ed = ctk.CTkEntry(frame_busq_ed, width=380, placeholder_text="Ingrese cédula V/E o código de contrato...")
    txt_busq_ed.grid(row=1, column=0, padx=10, pady=5)

    # Botón de búsqueda (alternativa a presionar Enter)
    btn_buscar_ed = ctk.CTkButton(frame_busq_ed, text="Buscar", width=100, command=lambda: None)
    btn_buscar_ed.grid(row=1, column=1, padx=10, pady=5)

    # Etiquetas informativas del titular buscado (lado derecho)
    # lbl_fecha_contrato_ed: muestra la fecha de inicio del contrato (azul)
    lbl_fecha_contrato_ed = ctk.CTkLabel(
        frame_busq_ed,
        text="fecha de contrato: --/--/----",
        font=("Arial", 12, "italic", "bold"),
        text_color="#3498db"
    )
    lbl_fecha_contrato_ed.grid(row=1, column=2, padx=20)

    # lbl_contrato_nuevo_ed: muestra el número de contrato asignado por el sistema (verde)
    lbl_contrato_nuevo_ed = ctk.CTkLabel(
        frame_busq_ed,
        text="Contrato Sistema: --",
        font=("Arial", 12, "italic", "bold"),
        text_color="#2ecc71"
    )
    lbl_contrato_nuevo_ed.grid(row=2, column=2, padx=20, sticky="w")

    # lbl_tipo_contrato_ed: muestra el tipo de contrato del titular (azul oscuro)
    lbl_tipo_contrato_ed = ctk.CTkLabel(
        frame_busq_ed,
        text="Tipo de Contrato: --",
        font=("Arial", 12, "italic", "bold"),
        text_color="#2980b9"
    )
    lbl_tipo_contrato_ed.grid(row=3, column=2, padx=20, sticky="w")

    # --- Frame de campos editables ---
    # Distribución:
    #   Fila 0-1: Nombres | Apellidos | Teléfono
    #   Fila 2-3: Correo  | Contrato Viejo | Fecha Contrato Viejo
    #   Fila 4-5: Dirección
    # --- Frame de campos editables ---
    frame_campos_ed = ctk.CTkFrame(tab_edicion)
    frame_campos_ed.pack(pady=5, padx=10, fill="x")

    # ---------------------------------------------------------------
    # FILA 0-1: Nombres | Apellidos | Teléfono
    # Todas las etiquetas y casillas usan sticky="w" para quedar
    # alineadas a la izquierda de su columna.
    # ---------------------------------------------------------------
    ctk.CTkLabel(frame_campos_ed, text="Modificar Nombres:", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_ed_nom = ctk.CTkEntry(frame_campos_ed, width=180, validate="key", validatecommand=(v_letras, '%P'))
    txt_ed_nom.grid(row=1, column=0, padx=10, pady=5, sticky="w")

    ctk.CTkLabel(frame_campos_ed, text="Modificar Apellidos:", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    txt_ed_ape = ctk.CTkEntry(frame_campos_ed, width=180, validate="key", validatecommand=(v_letras, '%P'))
    txt_ed_ape.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    ctk.CTkLabel(frame_campos_ed, text="Modificar Teléfono:", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, sticky="w")
    txt_ed_tel = ctk.CTkEntry(frame_campos_ed, width=180)
    txt_ed_tel.grid(row=1, column=2, padx=10, pady=5, sticky="w")

    # ---------------------------------------------------------------
    # FILA 2-3: Correo | Contrato Viejo | Fecha Contrato Viejo
    # ---------------------------------------------------------------
    ctk.CTkLabel(frame_campos_ed, text="Modificar Correo:", font=("Arial", 11, "bold")).grid(row=2, column=0, padx=10, sticky="w")
    txt_ed_corr = ctk.CTkEntry(frame_campos_ed, width=180)
    txt_ed_corr.grid(row=3, column=0, padx=10, pady=5, sticky="w")

    ctk.CTkLabel(frame_campos_ed, text="Contrato Viejo:", font=("Arial", 11, "bold")).grid(row=2, column=1, padx=10, sticky="w")
    txt_ed_contrato_viejo = ctk.CTkEntry(frame_campos_ed, width=180, placeholder_text="Opcional")
    txt_ed_contrato_viejo.grid(row=3, column=1, padx=10, pady=5, sticky="w")

    ctk.CTkLabel(frame_campos_ed, text="Fecha Contrato Viejo:", font=("Arial", 11, "bold")).grid(row=2, column=2, padx=10, sticky="w")
    txt_ed_fecha_contrato_viejo = ctk.CTkEntry(frame_campos_ed, width=180, placeholder_text="DD/MM/YYYY")
    txt_ed_fecha_contrato_viejo.grid(row=3, column=2, padx=10, pady=5, sticky="w")

    # ---------------------------------------------------------------
    # FILA 4-5: Dirección de Habitación
    # IMPORTANTE: la etiqueta y la casilla ocupan las 3 columnas
    # (columnspan=3) para que NO ensanchen la columna 0 y
    # desalineen las casillas de arriba.
    # ---------------------------------------------------------------
    ctk.CTkLabel(frame_campos_ed, text="Modificar Dirección de Habitación:", font=("Arial", 11, "bold")).grid(row=4, column=0, columnspan=3, padx=10, sticky="w")
    txt_ed_dir = ctk.CTkEntry(frame_campos_ed, width=580)
    txt_ed_dir.grid(row=5, column=0, columnspan=3, padx=10, pady=5, sticky="w")

    # Navegación con Enter en PESTAÑA 2 (orden de edición)
    vincular_salto_enter(txt_ed_nom, txt_ed_ape)
    vincular_salto_enter(txt_ed_ape, txt_ed_tel)
    vincular_salto_enter(txt_ed_tel, txt_ed_corr)
    vincular_salto_enter(txt_ed_corr, txt_ed_contrato_viejo)
    vincular_salto_enter(txt_ed_contrato_viejo, txt_ed_fecha_contrato_viejo)
    vincular_salto_enter(txt_ed_fecha_contrato_viejo, txt_ed_dir)

    # --- Frame de Notas / Observaciones en Edición ---
    frame_notas_ed = ctk.CTkFrame(tab_edicion)
    frame_notas_ed.pack(pady=5, padx=10, fill="x")

    ctk.CTkLabel(
        frame_notas_ed,
        text="Notas / Observaciones del Contrato:",
        font=("Arial", 11, "bold", "underline"),
        text_color="#e67e22"
    ).pack(anchor="w", padx=10)

    txt_ed_notas = ctk.CTkTextbox(
        frame_notas_ed,
        width=700,
        height=60,
        font=("Arial", 10),
        wrap="word"
    )
    txt_ed_notas.pack(padx=10, pady=(2, 5), fill="x")

    # --- Tabla de afiliados del titular en edición ---
    tabla_ed_frame = ctk.CTkFrame(tab_edicion)
    tabla_ed_frame.pack(pady=5, padx=10, fill="both", expand=True)

    tabla_ed = ttk.Treeview(
        tabla_ed_frame,
        columns=("id", "cedula", "nombres", "apellidos", "parentesco", "f_nac", "edad"),
        show="headings",
        height=4
    )

    for c, t, w in [
        ("id", "ID", 60),
        ("cedula", "Cédula", 110),
        ("nombres", "Nombres", 150),
        ("apellidos", "Apellidos", 150),
        ("parentesco", "Parentesco", 120),
        ("f_nac", "F. Nacimiento", 120),
        ("edad", "Edad", 90)
    ]:
        tabla_ed.heading(c, text=t)
        tabla_ed.column(c, width=w, anchor="center")

    tabla_ed.pack(fill="both", expand=True)
    
    # =========================================================================
    # PESTAÑA 3: CONTROL DE COBROS Y PAGOS
    # =========================================================================
    # Esta pestaña permite buscar un titular, verificar su estado de pago
    # y procesar nuevos cobros con generación de recibo PDF.
    # =========================================================================

    # --- Área de búsqueda de titulares ---
    frame_busq_pagos = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_busq_pagos.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(
        frame_busq_pagos,
        text="Buscar Titular (Cédula o Contrato Viejo/Nuevo):",
        font=("Arial", 11, "bold")
    ).grid(row=0, column=0, padx=10, sticky="w")

    txt_busqueda_ced = ctk.CTkEntry(frame_busq_pagos, width=280, placeholder_text="Cédula, Contrato Viejo o Contrato Nuevo...")
    txt_busqueda_ced.grid(row=1, column=0, padx=10, pady=5)

    # Botón de búsqueda de estado del titular
    btn_buscar = ctk.CTkButton(frame_busq_pagos, text="Verificar Estado", width=120, command=lambda: None)
    btn_buscar.grid(row=1, column=1, padx=10, pady=5)

    # --- Panel informativo del contrato (Contrato Viejo, Sistema, Recibo) ---
    frame_info_contratos = ctk.CTkFrame(tab_pagos, fg_color="#1e272e")
    frame_info_contratos.pack(pady=5, padx=20, fill="x")

    # lbl_cv_display: muestra el contrato viejo del titular (amarillo)
    lbl_cv_display = ctk.CTkLabel(frame_info_contratos, text="Contrato Viejo: --", font=("Arial", 11, "bold"), text_color="#f1c40f")
    lbl_cv_display.grid(row=0, column=0, padx=15, pady=5)

    # lbl_cn_display: muestra el contrato nuevo asignado por el sistema (verde)
    lbl_cn_display = ctk.CTkLabel(frame_info_contratos, text="Contrato Sistema: --", font=("Arial", 11, "bold"), text_color="#2ecc71")
    lbl_cn_display.grid(row=0, column=1, padx=15, pady=5)

    # lbl_recibo_next: muestra el próximo número de recibo a asignar (naranja)
    lbl_recibo_next = ctk.CTkLabel(
        frame_info_contratos,
        text="N° Recibo Asignado a Procesar: --",
        font=("Arial", 11, "bold"),
        text_color="#e67e22"
    )
    lbl_recibo_next.grid(row=0, column=2, padx=15, pady=5)

    # --- Nombre del cliente y estado de morosidad ---
    lbl_nombre_clie = ctk.CTkLabel(tab_pagos, text="Cliente: Seleccione un titular", font=("Arial", 13, "bold"), justify="left")
    lbl_nombre_clie.pack(pady=5, padx=20, anchor="w")

    lbl_aviso_morosidad = ctk.CTkLabel(tab_pagos, text="ESTADO: --", font=("Arial", 14, "bold"), text_color="grey")
    lbl_aviso_morosidad.pack(pady=2, padx=20, anchor="w")

    # --- Historial del último pago ---
    frame_ultimo_pago = ctk.CTkFrame(tab_pagos, border_width=2, border_color="#1f538d")
    frame_ultimo_pago.pack(pady=5, padx=20, fill="x")

    lbl_up_detalles = ctk.CTkLabel(frame_ultimo_pago, text="Historial de Cobros: Sin registrar búsquedas.", font=("Arial", 12, "italic"))
    lbl_up_detalles.pack(pady=5, padx=10, anchor="w")

    # --- Botón para ver las notas del titular (abre ventana emergente) ---
    frame_notas_pagos = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_notas_pagos.pack(pady=2, padx=20, anchor="w")

    btn_ver_notas = ctk.CTkButton(
        frame_notas_pagos,
        text="📝 Ver Notas del Titular",
        fg_color="#8e44ad",
        command=lambda: None,  # Se configura después de definir la función
        width=180,
        state="disabled"
    )
    btn_ver_notas.pack(side="left")

    # --- Frame de cobro: Tasa, Forma de Pago, Monto y Datos Bancarios ---
    frame_cobro = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_cobro.pack(pady=10, padx=20, fill="x")

    # FILA 0: Etiquetas de Tasa, Forma de Pago y Monto
    ctk.CTkLabel(frame_cobro, text="Tasa Oficial BCV (Bs.):", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")

    txt_tasa = ctk.CTkEntry(
        frame_cobro,
        width=130,
        placeholder_text="0.00",
        state="normal",
        validate="key",
        validatecommand=(v_monto_decimal, '%P')
    )
    txt_tasa.grid(row=1, column=0, padx=10, pady=5, sticky="w")

    ctk.CTkLabel(frame_cobro, text="Forma de Pago:", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")

    combo_forma_pago = ctk.CTkComboBox(
        frame_cobro,
        values=["Efectivo USD", "Efectivo Bs", "Transferencia", "Pago Móvil", "Tarjeta de debito"],
        width=160,
        command=lambda: None  # Se configura después de definir la función
    )
    combo_forma_pago.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    ctk.CTkLabel(frame_cobro, text="Monto Cobrado (Bs.):", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, sticky="w")

    txt_monto_bs = ctk.CTkEntry(
        frame_cobro,
        width=140,
        placeholder_text="0.00",
        validate="key",
        validatecommand=(v_monto_decimal, '%P')
    )
    txt_monto_bs.grid(row=1, column=2, padx=10, pady=5, sticky="w")

    # Etiqueta que muestra el cálculo del monto a pagar en Bs
    lbl_calculo_bs = ctk.CTkLabel(frame_cobro, text="Monto a pagar: 0,00 Bs", font=("Arial", 13, "bold", "italic"), fg_color="transparent")
    lbl_calculo_bs.grid(row=1, column=3, padx=15, pady=5, sticky="w")

    # FILA 1: Campos bancarios (solo visibles para Transferencia/Pago Móvil)
    lbl_b_origen = ctk.CTkLabel(frame_cobro, text="Banco Pagador:", font=("Arial", 11, "bold"))
    lbl_b_origen.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")

    txt_banco_origen = ctk.CTkEntry(frame_cobro, width=140, placeholder_text="Ej: Banesco", state="disabled")
    txt_banco_origen.grid(row=3, column=0, padx=10, pady=5, sticky="w")

    lbl_b_destino = ctk.CTkLabel(frame_cobro, text="Banco Receptor:", font=("Arial", 11, "bold"))
    lbl_b_destino.grid(row=2, column=1, padx=10, pady=(10, 0), sticky="w")

    txt_banco_destino = ctk.CTkEntry(frame_cobro, width=160, placeholder_text="Ej: Mercantil", state="disabled")
    txt_banco_destino.grid(row=3, column=1, padx=10, pady=5, sticky="w")

    lbl_ref = ctk.CTkLabel(frame_cobro, text="N° Operación (Solo Números):", font=("Arial", 11, "bold"))
    lbl_ref.grid(row=2, column=2, padx=10, pady=(10, 0), sticky="w")

    txt_num_referencia = ctk.CTkEntry(
        frame_cobro,
        width=150,
        placeholder_text="Ref. Numérica",
        state="disabled",
        validate="key",
        validatecommand=(v_numeros_puro, '%P')
    )
    txt_num_referencia.grid(row=3, column=2, padx=10, pady=5, sticky="w")

    # =========================================================================
    # PESTAÑA 4: REPORTES Y ESTADOS DE CUENTA
    # =========================================================================
    # Esta pestaña se construye completa con construir_pestana_reportes(),
    # que se llama en la sección de botones y enlaces (después de definir
    # las funciones de reportes). Aquí solo se crea el frame del gráfico,
    # SIN empacarlo todavía, para poder ubicarlo al final de la pestaña.
    #frame_grafico = ctk.CTkFrame(tab_reportes, fg_color="#2b2b2b", height=200)

    # =========================================================================
    # PESTAÑA 5: CONFIGURACIÓN (Solo Administradores)
    # =========================================================================
    # Esta pestaña solo aparece si el usuario tiene rol de administrador.
    # Permite respaldar la base de datos y gestionar usuarios.
    # =========================================================================

    if es_admin:
        # Título de la sección de configuración
        lbl_titulo_conf = ctk.CTkLabel(
            tab_config,
            text="⚙️ Panel de Configuración y Seguridad (Administrador)",
            font=("Arial", 16, "bold")
        )
        lbl_titulo_conf.pack(pady=(10, 5), padx=20, anchor="w")

        frame_grid_conf = ctk.CTkFrame(tab_config, fg_color="transparent")
        frame_grid_conf.pack(pady=10, padx=10, fill="both", expand=True)

        # -----------------------------------------------------------------
        # SECCIÓN 1: RESPALDO DE BASE DE DATOS A USB / CARPETA
        # -----------------------------------------------------------------
        frame_respaldo = ctk.CTkFrame(frame_grid_conf, border_width=2, border_color="#1f538d")
        frame_respaldo.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(
            frame_respaldo,
            text="📦 Respaldo de Seguridad de Base de Datos",
            font=("Arial", 14, "bold"),
            text_color="#3498db"
        ).pack(pady=(10, 2), padx=15, anchor="w")

        ctk.CTkLabel(
            frame_respaldo,
            text="Haga clic en el botón para copiar y exportar la base de datos (.db) a un Pendrive USB o carpeta externa.",
            font=("Arial", 11)
        ).pack(pady=(0, 10), padx=15, anchor="w")

        # Botón de respaldo (se configura después de definir la función)
        btn_respaldo = ctk.CTkButton(
            frame_respaldo,
            text="💾 Exportar Copia de Respaldo a USB / Disco",
            fg_color="#27ae60",
            font=("Arial", 12, "bold"),
            height=35,
            command=lambda: None
        )
        btn_respaldo.pack(pady=(0, 15), padx=15, anchor="w")

        # -----------------------------------------------------------------
        # SECCIÓN 2: GESTIÓN DE USUARIOS Y CLAVES
        # -----------------------------------------------------------------
        frame_usuarios = ctk.CTkFrame(frame_grid_conf)
        frame_usuarios.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            frame_usuarios,
            text="👥 Gestión de Usuarios y Claves de Acceso",
            font=("Arial", 14, "bold"),
            text_color="#f1c40f"
        ).pack(pady=(10, 5), padx=15, anchor="w")

        # Formulario para crear nuevos usuarios
        frame_form_u = ctk.CTkFrame(frame_usuarios, fg_color="transparent")
        frame_form_u.pack(pady=5, padx=15, fill="x")

        ctk.CTkLabel(frame_form_u, text="Nuevo Usuario:", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=5, sticky="w")
        txt_u_user = ctk.CTkEntry(frame_form_u, width=130, placeholder_text="Ej: operador1")
        txt_u_user.grid(row=1, column=0, padx=5, pady=5)

        ctk.CTkLabel(frame_form_u, text="Contraseña:", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=5, sticky="w")
        txt_u_pass = ctk.CTkEntry(frame_form_u, width=130, placeholder_text="Clave de acceso", show="*")
        txt_u_pass.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_form_u, text="Confirmar Clave:", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=5, sticky="w")
        txt_u_pass2 = ctk.CTkEntry(frame_form_u, width=130, placeholder_text="Repetir clave", show="*")
        txt_u_pass2.grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkLabel(frame_form_u, text="Rol de Acceso:", font=("Arial", 11, "bold")).grid(row=0, column=3, padx=5, sticky="w")
        combo_u_rol = ctk.CTkComboBox(frame_form_u, values=["operador", "admin"], width=120)
        combo_u_rol.grid(row=1, column=3, padx=5, pady=5)

        # Botón para agregar usuario (se configura después de definir la función)
        btn_add_u = ctk.CTkButton(frame_form_u, text="➕ Agregar Usuario", fg_color="#1f538d", command=lambda: None)
        btn_add_u.grid(row=1, column=4, padx=15, pady=5)

        # Tabla de usuarios registrados
        tabla_u_frame = ctk.CTkFrame(frame_usuarios)
        tabla_u_frame.pack(pady=10, padx=15, fill="both", expand=True)

        tabla_u = ttk.Treeview(tabla_u_frame, columns=("id", "usuario", "rol"), show="headings", height=5)

        for c, t, w in [
            ("id", "ID", 60),
            ("usuario", "Nombre de Usuario", 250),
            ("rol", "Rol de Acceso", 150)
        ]:
            tabla_u.heading(c, text=t)
            tabla_u.column(c, width=w, anchor="center")

        tabla_u.pack(fill="both", expand=True)

        # Frame de acciones de usuarios (cambiar clave, eliminar, salir)
        frame_u_acciones = ctk.CTkFrame(frame_usuarios, fg_color="transparent")
        frame_u_acciones.pack(pady=(5, 10), padx=15, fill="x")

    # =========================================================================
    # FUNCIONES CALLBACK - PESTAÑA 1: REGISTRO DE CLIENTES
    # =========================================================================
    # Estas funciones manejan la lógica de guardado, limpieza y actualización
    # de la pestaña de registro de nuevos titulares.
    # =========================================================================

    def refrescar_tabla_familiares(ced_t):
        """
        Actualiza la tabla de afiliados mostrando los familiares
        vinculados a la cédula del titular indicado.
        """
        for item in tabla.get_children():
            tabla.delete(item)

        if not ced_t:
            return

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT cedula, nombres, apellidos, parentesco, fecha_nacimiento FROM familiares WHERE titular_cedula = ?",
            (ced_t.upper(),)
        )

        for f in cursor.fetchall():
            edad_calc = f"{calcular_edad_exacta(f[4])} años" if f[4] else "N/A"
            tabla.insert("", "end", values=(f[0], f[1].title(), f[2].title(), f[3].title(), f[4] or "N/A", edad_calc))

        conn.close()

    def guardar_titular():
        """
        Guarda un nuevo titular en la base de datos con todos sus datos:
        cédula, contratos, nombres, apellidos, contacto, tipo de contrato,
        recibos previos, notas y fecha del contrato anterior.
        """
        # Capturar todos los datos del formulario
        ced = txt_cedula.get().strip().upper()
        c_viejo = txt_cont_viejo.get().strip()
        fecha_c_viejo = txt_fecha_contrato_ant.get().strip()
        c_nuevo = txt_cont_nuevo.get().strip()
        nom = txt_nombres.get().strip().lower()
        ape = txt_apellidos.get().strip().lower()
        f_nac = txt_fecha_nac.get().strip()
        tel = txt_telefono.get().strip()
        corr = txt_correo.get().strip().lower()
        dir_hab = txt_direccion.get().strip().lower()
        tipo_c = combo_contrato.get()
        notas = txt_notas_registro.get("1.0", "end").strip()
        recibos_raw = txt_recibos_previos.get().strip()

        # Convertir recibos previos a entero (0 si está vacío)
        try:
            r_previos = int(recibos_raw) if recibos_raw else 0
        except:
            r_previos = 0

        # Validar fecha del contrato anterior (si se proporcionó)
        if fecha_c_viejo and not validar_fecha_ddmmyyyy(fecha_c_viejo):
            messagebox.showwarning(
                "Fecha Contrato Anterior Inválida",
                "La fecha del contrato anterior debe tener formato DD/MM/YYYY.\nEjemplo: 15/03/2024"
            )
            txt_fecha_contrato_ant.focus()
            return

        # Validar formato de cédula
        if not validar_mascara_cedula(ced):
            messagebox.showwarning(
                "Formato Requerido",
                "Cédula del titular inválida.\nDebe comenzar con V o E seguido de 7 a 8 números.\nEjemplo: V12345678"
            )
            txt_cedula.focus()
            return

        # Validar campos obligatorios
        if not nom or not ape or not f_nac:
            messagebox.showwarning(
                "Campos Requeridos",
                "Nombres, Apellidos y Fecha de Nacimiento son campos obligatorios."
            )
            return

        # Insertar el titular en la base de datos
        try:
            conn = conectar()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO titulares (
                    cedula, contrato_viejo, contrato_nuevo, nombres, apellidos,
                    fecha_nacimiento, telefono, correo, direccion, tipo_contrato,
                    fecha_inicio, recibos_previos, notas, fecha_contrato_anterior
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ced, c_viejo, c_nuevo, nom, ape, f_nac, tel, corr, dir_hab,
                tipo_c, datetime.now().strftime("%d/%m/%Y"), r_previos, notas,
                fecha_c_viejo or None
            ))

            conn.commit()
            conn.close()

            messagebox.showinfo("Éxito", f"Titular registrado con el Contrato Sistema: {c_nuevo}")

            btn_add_fam.configure(state="normal")
            refrescar_tabla_familiares(ced)

            # Generar el siguiente número de contrato para el próximo registro
            txt_cont_nuevo.configure(state="normal")
            txt_cont_nuevo.delete(0, "end")
            txt_cont_nuevo.insert(0, generar_siguiente_contrato())
            txt_cont_nuevo.configure(state="disabled")

        except Exception as e:
            messagebox.showerror(
                "Error de Duplicidad",
                f"La cédula o el número de contrato ya se encuentran registrados en el sistema.\n{e}"
            )

    def limpiar_formulario_registro():
        """
        Resetea todos los campos del formulario de la Pestaña 1
        para ingresar un nuevo contrato desde cero.
        """
        txt_cedula.delete(0, "end")
        txt_cont_viejo.delete(0, "end")
        txt_fecha_contrato_ant.delete(0, "end")
        txt_nombres.delete(0, "end")
        txt_apellidos.delete(0, "end")
        txt_fecha_nac.delete(0, "end")
        txt_telefono.delete(0, "end")
        txt_recibos_previos.delete(0, "end")
        txt_correo.delete(0, "end")
        txt_direccion.delete(0, "end")
        txt_notas_registro.delete("1.0", "end")
        combo_contrato.set("PPA velación 24 meses")

        lbl_edad_titular.configure(text=" Edad: -- años ")

        # Generar nuevo número de contrato
        txt_cont_nuevo.configure(state="normal")
        txt_cont_nuevo.delete(0, "end")
        txt_cont_nuevo.insert(0, generar_siguiente_contrato())
        txt_cont_nuevo.configure(state="disabled")

        # Limpiar tabla de afiliados
        for item in tabla.get_children():
            tabla.delete(item)

        btn_add_fam.configure(state="disabled")
        txt_cedula.focus()

    # =========================================================================
    # FUNCIONES CALLBACK - PESTAÑA 2: EDICIÓN DE TITULARES
    # =========================================================================
    # Estas funciones manejan la búsqueda, carga y guardado de cambios
    # de los datos del titular en la pestaña de edición.
    # =========================================================================

    def cargar_datos_edicion():
        """
        Busca un titular en la base de datos por cédula o número de contrato
        y carga sus datos en los campos de edición.
        También carga la lista de afiliados vinculados a ese titular.
        
        Índices del SELECT:
          0=cedula, 1=telefono, 2=correo, 3=direccion, 4=nombres, 5=apellidos,
          6=fecha_inicio, 7=notas, 8=contrato_viejo, 9=contrato_nuevo,
          10=fecha_contrato_anterior, 11=tipo_contrato
        """
        crit = txt_busq_ed.get().strip().upper()

        if not crit:
            return

        conn = conectar()
        cursor = conn.cursor()

        # Consulta que incluye todos los campos necesarios para la edición
        cursor.execute("""
            SELECT cedula, telefono, correo, direccion, nombres, apellidos, fecha_inicio,
                   notas, contrato_viejo, contrato_nuevo, fecha_contrato_anterior, tipo_contrato
            FROM titulares 
            WHERE cedula = ? OR UPPER(contrato_viejo) = ? OR UPPER(contrato_nuevo) = ?
            OR cedula IN (SELECT titular_cedula FROM familiares WHERE UPPER(cedula) = ?)
        """, (crit, crit, crit, crit))

        res = cursor.fetchone()

        if res:
            cedula_titular_edicion[0] = res[0]

            # Cargar campos de texto editables
            for txt, val in [
                (txt_ed_nom, res[4]),       # nombres
                (txt_ed_ape, res[5]),       # apellidos
                (txt_ed_tel, res[1]),       # teléfono
                (txt_ed_corr, res[2]),      # correo
                (txt_ed_dir, res[3])        # dirección
            ]:
                txt.delete(0, "end")
                txt.insert(0, val.title() if isinstance(val, str) and txt in [txt_ed_nom, txt_ed_ape] else (val or ""))

            # Cargar contrato viejo (índice 8)
            txt_ed_contrato_viejo.delete(0, "end")
            txt_ed_contrato_viejo.insert(0, res[8] or "")

            # Cargar fecha del contrato viejo (índice 10)
            txt_ed_fecha_contrato_viejo.delete(0, "end")
            txt_ed_fecha_contrato_viejo.insert(0, res[10] or "")

            # Cargar notas (índice 7)
            txt_ed_notas.delete("1.0", "end")
            txt_ed_notas.insert("1.0", res[7] or "")

            # Actualizar etiquetas informativas
            # lbl_fecha_contrato_ed: fecha de inicio del contrato (azul)
            lbl_fecha_contrato_ed.configure(text=f"fecha de contrato  {res[6] or '--/--/----'}")

            # lbl_contrato_nuevo_ed: número de contrato del sistema (verde, índice 9)
            lbl_contrato_nuevo_ed.configure(text=f"Contrato Sistema: {res[9] or '--'}")

            # lbl_tipo_contrato_ed: tipo de contrato del titular (azul oscuro, índice 11)
            lbl_tipo_contrato_ed.configure(text=f"Tipo de Contrato: {res[11] or '--'}")

            # Limpiar y recargar tabla de afiliados
            for item in tabla_ed.get_children():
                tabla_ed.delete(item)

            cursor.execute(
                "SELECT id, cedula, nombres, apellidos, parentesco, fecha_nacimiento FROM familiares WHERE titular_cedula = ?",
                (res[0],)
            )

            for f in cursor.fetchall():
                edad_calc = f"{calcular_edad_exacta(f[5])} años" if f[5] else "N/A"
                tabla_ed.insert("", "end", values=(f[0], f[1], f[2].title(), f[3].title(), f[4].title(), f[5] or "N/A", edad_calc))

            # Habilitar botones de acción
            for b in [btn_actualizar, btn_retirar_fam, btn_add_fam_ed]:
                b.configure(state="normal")

            txt_ed_nom.focus()

        else:
            messagebox.showerror("No Localizado", "No se encontró ningún contrato asociado al dato ingresado.")

        conn.close()

    def ejecutar_guardar_cambios_titular():
        """
        Guarda los cambios realizados en los campos de edición del titular.
        Incluye: nombres, apellidos, teléfono, correo, dirección, notas,
        contrato viejo y fecha del contrato viejo.
        """
        nom = txt_ed_nom.get().strip().lower()
        ape = txt_ed_ape.get().strip().lower()
        tel = txt_ed_tel.get().strip()
        corr = txt_ed_corr.get().strip().lower()
        dir_h = txt_ed_dir.get().strip().lower()
        notas_ed = txt_ed_notas.get("1.0", "end").strip()
        c_viejo_ed = txt_ed_contrato_viejo.get().strip()
        fecha_c_viejo_ed = txt_ed_fecha_contrato_viejo.get().strip()
        ced = cedula_titular_edicion[0]

        # Validar campos obligatorios
        if not nom or not ape:
            messagebox.showwarning("Error", "Campos de texto obligatorios vacíos.")
            return

        # Validar fecha del contrato viejo (si se proporcionó)
        if fecha_c_viejo_ed and not validar_fecha_ddmmyyyy(fecha_c_viejo_ed):
            messagebox.showwarning(
                "Fecha Contrato Viejo Inválida",
                "La fecha del contrato viejo debe tener formato DD/MM/YYYY.\nEjemplo: 15/03/2024"
            )
            txt_ed_fecha_contrato_viejo.focus()
            return

        # Actualizar los datos del titular en la base de datos
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE titulares
            SET nombres=?, apellidos=?, telefono=?, correo=?, direccion=?,
                notas=?, contrato_viejo=?, fecha_contrato_anterior=?
            WHERE cedula=?
        """, (
            nom,
            ape,
            tel,
            corr,
            dir_h,
            notas_ed,
            c_viejo_ed,
            fecha_c_viejo_ed or None,
            ced
        ))

        conn.commit()
        conn.close()

        messagebox.showinfo("Éxito", "Historial modificado con éxito.")
        cargar_datos_edicion()

    def ejecutar_retirar_familiar():
        """
        Elimina un afiliado seleccionado de la tabla de familiares.
        Pide confirmación antes de eliminar.
        """
        seleccionado = tabla_ed.selection()

        if not seleccionado:
            messagebox.showwarning("Selección", "Por favor seleccione un afiliado de la lista.")
            return

        id_fam = tabla_ed.item(seleccionado)['values'][0]

        if messagebox.askyesno("Confirmar", "¿Desea retirar de forma definitiva este familiar de la póliza?"):
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM familiares WHERE id=?", (id_fam,))
            conn.commit()
            conn.close()

            messagebox.showinfo("Éxito", "Familiar retirado.")
            cargar_datos_edicion()
            refrescar_tabla_familiares(cedula_titular_edicion[0])

    # =========================================================================
    # FUNCIONES CALLBACK - PESTAÑA 3: CONTROL DE PAGOS
    # =========================================================================
    # Estas funciones manejan la búsqueda de titulares, cálculo de montos,
    # procesamiento de pagos y renovación automática de contratos.
    # =========================================================================

    def alternar_campos_bancarios_cobro(metodo):
        """
        Habilita o deshabilita los campos bancarios (Banco Pagador,
        Banco Receptor, N° Operación) según la forma de pago seleccionada.
        Solo se habilitan para Transferencia y Pago Móvil.
        """
        es_bancario = metodo in ["Transferencia", "Pago Móvil"]
        estado = "normal" if es_bancario else "disabled"

        txt_banco_origen.configure(state=estado)
        txt_banco_destino.configure(state=estado)
        txt_num_referencia.configure(state=estado)

        # Limpiar campos si se cambia a un método que no los necesita
        if not es_bancario:
            txt_banco_origen.delete(0, "end")
            txt_banco_destino.delete(0, "end")
            txt_num_referencia.delete(0, "end")

    def ver_notas_titular():
        """
        Abre una ventana emergente (popup) mostrando las notas del titular
        actual en modo solo lectura.
        """
        nota = nota_titular_global[0]

        top_notas = ctk.CTkToplevel(ventana)
        top_notas.title("Notas del Titular")
        top_notas.geometry("500x350")
        top_notas.grab_set()

        ctk.CTkLabel(
            top_notas,
            text="📝 Notas / Observaciones del Contrato",
            font=("Arial", 14, "bold"),
            text_color="#8e44ad"
        ).pack(pady=(15, 5), padx=20, anchor="w")

        txt_ver_notas = ctk.CTkTextbox(
            top_notas,
            width=450,
            height=220,
            font=("Arial", 10),
            wrap="word",
            state="disabled"
        )
        txt_ver_notas.pack(padx=20, pady=5, fill="both", expand=True)

        # Insertar la nota o mensaje de sin notas
        txt_ver_notas.configure(state="normal")
        if nota:
            txt_ver_notas.insert("1.0", nota)
        else:
            txt_ver_notas.insert("1.0", "No hay notas registradas para este titular.")
        txt_ver_notas.configure(state="disabled")

        ctk.CTkButton(
            top_notas,
            text="Cerrar",
            fg_color="#7f8c8d",
            command=top_notas.destroy
        ).pack(pady=10)

    def buscar_y_calcular_pagos():
        """
        Busca un titular por cédula o contrato, calcula el estado de sus pagos
        (cuotas pagadas, restantes, morosidad) y actualiza la interfaz.
        También prepara el próximo número de recibo a asignar.
        """
        ced = txt_busqueda_ced.get().strip().upper()

        if not ced:
            return

        conn = conectar()
        cursor = conn.cursor()

        # Consulta que incluye notas para el botón "Ver Notas"
        cursor.execute("""
            SELECT nombres, apellidos, contrato_viejo, contrato_nuevo, recibos_previos, tipo_contrato, cedula, notas FROM titulares 
            WHERE cedula=? OR UPPER(contrato_viejo)=? OR UPPER(contrato_nuevo)=?
            OR cedula IN (SELECT titular_cedula FROM familiares WHERE UPPER(cedula) = ?)
        """, (ced, ced, ced, ced))

        res = cursor.fetchone()

        if res:
            cedula_real = res[6]
            cedula_titular_pago[0] = cedula_real
            tipo_contrato_global[0] = res[5]
            nota_titular_global[0] = res[7] or ""
            recibos_previos = res[4]

            txt_tasa.configure(state="normal")
            txt_tasa.delete(0, "end")

            cursor.execute("SELECT COUNT(*) FROM pagos WHERE titular_cedula = ?", (cedula_real,))
            pagos_sistema = cursor.fetchone()[0]

            total_pagados = recibos_previos + pagos_sistema

            # Calcular cuotas según el tipo de plan
            if "24 meses" in res[5].lower():
                cuotas_totales_plan = 24
                cuotas_restantes = max(0, cuotas_totales_plan - total_pagados)
                status_cuotas_texto = f"Cuotas Canceladas: {total_pagados} / 24 | Restantes: {cuotas_restantes}"
            else:
                cuotas_totales_plan = 12
                cuotas_en_renovacion = total_pagados - 24 if total_pagados >= 24 else total_pagados
                pagadas_ciclo = cuotas_en_renovacion % 12
                cuotas_restantes = max(0, 12 - pagadas_ciclo)
                status_cuotas_texto = f"Ciclo Renovación -> Pagadas: {pagadas_ciclo} / 12 | Restantes: {cuotas_restantes}"

            # Próximo recibo único global
            proximo_recibo_global[0] = obtener_siguiente_recibo(cursor)

            lbl_nombre_clie.configure(
                text=f"Cliente: {res[0].upper()} {res[1].upper()} | Plan: {res[5].upper()}\n[{status_cuotas_texto}]"
            )

            lbl_cv_display.configure(text=f"Contrato Viejo: {res[2] or 'NINGUNO'}")
            lbl_cn_display.configure(text=f"Contrato Sistema: {res[3]}")
            lbl_recibo_next.configure(text=f"N° Recibo Asignado a Procesar: #{proximo_recibo_global[0]}")

            # Consultar estado de morosidad del cliente
            estado = consultar_estado_cliente(cedula_real)

            if isinstance(estado, dict) and "error" in estado:
                lbl_aviso_morosidad.configure(text="ESTADO: ERROR AL CONSULTAR", text_color="red")
            else:
                if estado["moroso"]:
                    lbl_aviso_morosidad.configure(text=f"ESTADO: MOROSO (Debe ${estado['deuda_usd']:.2f})", text_color="red")
                elif estado["deuda_usd"] > 0:
                    lbl_aviso_morosidad.configure(
                        text=f"ESTADO: AL DÍA / SOLVENTE (Pendiente próxima cuota de {cuotas_totales_plan})",
                        text_color="#f39c12"
                    )
                else:
                    lbl_aviso_morosidad.configure(text="ESTADO: AL DÍA / SOLVENTE (Sin cuotas pendientes)", text_color="#2ecc71")

            # Mostrar el último pago registrado
            cursor.execute(
                "SELECT fecha_pago, monto_usd, num_recibo, forma_pago FROM pagos WHERE titular_cedula = ? ORDER BY id DESC LIMIT 1",
                (cedula_real,)
            )

            u = cursor.fetchone()

            lbl_up_detalles.configure(
                text=f"Último Pago -> Fecha: {u[0]} | Monto: ${u[1]:.2f} USD | Recibo: #{u[2]} | Método: {u[3]}"
                if u else "Historial: Sin cobros procesados en el sistema."
            )

            btn_procesar_pago.configure(state="normal")
            btn_ver_notas.configure(state="normal")

            # ---------------------------------------------------------
            # AVISO VISUAL DE NOTAS:
            # Si el titular tiene notas guardadas, el botón se pinta
            # ROJO para que el operario lo note sin tener que abrirlo.
            # Si no tiene notas, queda en su color morado normal.
            # ---------------------------------------------------------
            if nota_titular_global[0]:
                btn_ver_notas.configure(
                    fg_color="#c0392b",
                    text="📝 Ver Notas (este titular tiene notas)"
                )
            else:
                btn_ver_notas.configure(
                    fg_color="#8e44ad",
                    text="📝 Ver Notas del Titular"
                )

            txt_tasa.focus()

        else:
            messagebox.showerror("No Encontrado", "No se localizó ningún contrato asociado al dato ingresado.")

            cedula_titular_pago[0] = ""
            tipo_contrato_global[0] = ""

            txt_tasa.configure(state="disabled")
            btn_procesar_pago.configure(state="disabled")
            btn_ver_notas.configure(state="disabled")

        conn.close()

    def actualizar_calculo_bolivares(*args):
        """
        Se ejecuta cada vez que el usuario escribe en el campo de Tasa BCV.
        Calcula y muestra el monto a pagar en bolívares según la tasa
        y el plan del titular ($10 o $20 por cuota).
        """
        try:
            tasa_texto = txt_tasa.get().strip()

            if not tasa_texto:
                lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")
                return

            tasa = convertir_numero(tasa_texto)

            # Calcular monto según el plan ($10 o $20)
            usd = obtener_monto_usd_plan(tipo_contrato_global[0])
            monto_bs = usd * tasa

            lbl_calculo_bs.configure(text=f"Monto a pagar ({usd:.0f} USD): {formatear_moneda_ve(monto_bs)}")

        except:
            lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")

    # Vincular el cálculo automático al campo de tasa
    txt_tasa.bind("<KeyRelease>", actualizar_calculo_bolivares)

    def ejecutar_pago():
        """
        Procesa un pago: valida el monto, registra el pago en la base de datos,
        verifica si el contrato debe renovarse, genera el recibo PDF
        y actualiza la interfaz.
        
        IMPORTANTE: Usa la bandera procesando_pago para evitar doble clic.
        """
        if procesando_pago[0]:
            return

        procesando_pago[0] = True

        try:
            # Detectar la cédula real del titular desde la búsqueda de pagos
            cedula_actual = cedula_titular_pago[0] or txt_busqueda_ced.get().strip().upper()

            if not cedula_actual:
                messagebox.showwarning(
                    "Sin Titular",
                    "Debe buscar primero al titular antes de procesar un pago."
                )
                return

            # Capturar datos del formulario de pago
            metodo = combo_forma_pago.get()

            b_origen = txt_banco_origen.get().strip().upper() if metodo in ["Transferencia", "Pago Móvil"] else ""
            b_destino = txt_banco_destino.get().strip().upper() if metodo in ["Transferencia", "Pago Móvil"] else ""
            num_op = txt_num_referencia.get().strip() if metodo in ["Transferencia", "Pago Móvil"] else ""

            # -----------------------------------------------------------------
            # VALIDACIÓN DE MONTO INGRESADO
            # -----------------------------------------------------------------
            try:
                monto_ingresado = convertir_numero(txt_monto_bs.get())
            except ValueError:
                messagebox.showwarning("Monto Inválido", "Por favor, ingrese un monto cobrado válido.")
                txt_monto_bs.focus()
                return

            # -----------------------------------------------------------------
            # VALIDACIÓN DE TASA BCV
            # -----------------------------------------------------------------
            try:
                tasa_val_num = convertir_numero(txt_tasa.get())
            except ValueError:
                tasa_val_num = 0.0

            if tasa_val_num <= 0:
                messagebox.showwarning(
                    "Tasa Requerida",
                    "Ingrese la tasa oficial BCV válida antes de procesar el pago."
                )
                txt_tasa.focus()
                return

            # -----------------------------------------------------------------
            # VALIDACIÓN DE COINCIDENCIA DE MONTOS
            # Regla: Si el plan tiene "entierro" → $20, si no → $10
            # -----------------------------------------------------------------
            plan_monto_txt = (tipo_contrato_global[0] or "").lower()
            usd_plan = 20.0 if "entierro" in plan_monto_txt else 10.0

            monto_esperado = usd_plan * tasa_val_num

            if abs(monto_ingresado - monto_esperado) > 0.05:
                messagebox.showerror(
                    "Diferencia de Montos",
                    f"⚠️ El monto ingresado (Bs. {monto_ingresado:,.2f}) NO coincide con el monto a pagar calculado ({usd_plan:.2f} USD = Bs. {monto_esperado:,.2f}).\n\nPor favor verifique antes de procesar el pago."
                )
                txt_monto_bs.focus()
                return

            # Validar campos bancarios si es pago electrónico
            if metodo in ["Transferencia", "Pago Móvil"] and (not b_origen or not b_destino or not num_op):
                messagebox.showwarning(
                    "Faltan Datos",
                    "Para Transferencias y Pago Móvil debe ingresar Banco Pagador, Banco Receptor y N° Operación."
                )
                return

            conn = None

            try:
                conn = conectar()
                cursor = conn.cursor()

                # Obtener datos actuales del titular antes de insertar el pago
                cursor.execute("""
                    SELECT recibos_previos, tipo_contrato
                    FROM titulares
                    WHERE cedula = ?
                """, (cedula_actual,))

                res_titular = cursor.fetchone()

                if not res_titular:
                    messagebox.showerror(
                        "Titular no encontrado",
                        "No se encontró el titular en la base de datos."
                    )
                    return

                recibos_previos = res_titular[0] or 0
                plan_actual = res_titular[1] or ""

                # Calcular total de cuotas incluyendo el pago actual
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM pagos
                    WHERE titular_cedula = ?
                """, (cedula_actual,))

                pagos_sistema_previos = cursor.fetchone()[0]
                total_cuotas_nuevo = recibos_previos + pagos_sistema_previos + 1

                # Normalizar el nombre del plan (quitar acentos para comparar)
                plan_norm = plan_actual.lower()
                plan_norm = (plan_norm.replace("á", "a")
                                      .replace("é", "e")
                                      .replace("í", "i")
                                      .replace("ó", "o")
                                      .replace("ú", "u")
                                      .replace("ñ", "n"))

                es_renovacion = "renovacion anual" in plan_norm
                es_renovacion_despues_ppa = es_renovacion and "velacion" in plan_norm

                # Calcular el número de cuota que se está pagando
                if "24 meses" in plan_norm:
                    cuota_numero = min(24, total_cuotas_nuevo)

                elif es_renovacion and not es_renovacion_despues_ppa:
                    # Renovación independiente (no viene después de PPA)
                    cuota_numero = ((total_cuotas_nuevo - 1) % 12) + 1 if total_cuotas_nuevo > 0 else 1

                elif total_cuotas_nuevo > 24:
                    # Renovación que viene después de un PPA de 24 meses
                    cuota_numero = ((total_cuotas_nuevo - 24 - 1) % 12) + 1

                else:
                    cuota_numero = ((total_cuotas_nuevo - 1) % 12) + 1 if total_cuotas_nuevo > 0 else 1

                # Calcular próximo recibo único
                recibo_a_guardar = obtener_siguiente_recibo(cursor)

                # Protección adicional contra duplicados de recibo
                for _ in range(10):
                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM pagos
                        WHERE CAST(num_recibo AS INTEGER) = ?
                    """, (recibo_a_guardar,))

                    if cursor.fetchone()[0] == 0:
                        break

                    recibo_a_guardar += 1

                monto_bs_val = monto_ingresado
                tasa_val = tasa_val_num
                monto_usd_val = round(monto_bs_val / tasa_val, 2) if tasa_val > 0 else 0.0

                # Verificar si existe la columna cuota_numero y hacer el INSERT
                cursor.execute("PRAGMA table_info(pagos)")
                columnas_pagos = {row[1] for row in cursor.fetchall()}

                if "cuota_numero" in columnas_pagos:
                    cursor.execute("""
                        INSERT INTO pagos (
                            num_recibo, titular_cedula, fecha_pago, monto_usd, monto_bs,
                            tasa_bcv, forma_pago, banco_origen, banco_destino, num_operacion,
                            cuota_numero
                        ) VALUES (?, ?, DATE('now'), ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        recibo_a_guardar, cedula_actual, monto_usd_val, monto_bs_val,
                        tasa_val, metodo, b_origen, b_destino, num_op, cuota_numero
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO pagos (
                            num_recibo, titular_cedula, fecha_pago, monto_usd, monto_bs,
                            tasa_bcv, forma_pago, banco_origen, banco_destino, num_operacion
                        ) VALUES (?, ?, DATE('now'), ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        recibo_a_guardar, cedula_actual, monto_usd_val, monto_bs_val,
                        tasa_val, metodo, b_origen, b_destino, num_op
                    ))

                conn.commit()

                # -------------------------------------------------------------
                # LÓGICA DE RENOVACIÓN AUTOMÁTICA DE PLANES
                # -------------------------------------------------------------

                # CASO 1: Planes PPA de 24 meses que alcanzan la cuota 24
                if "24 meses" in plan_norm and total_cuotas_nuevo == 24:

                    if "entierro" in plan_norm:
                        nuevo_plan = "RENOVACION ANUAL 12 MESES - VELACION + ENTIERRO"
                        precio_nuevo = "$20.00"
                    else:
                        nuevo_plan = "RENOVACION ANUAL 12 MESES - VELACION"
                        precio_nuevo = "$10.00"

                    cursor.execute("""
                        UPDATE titulares 
                        SET tipo_contrato = ? 
                        WHERE cedula = ?
                    """, (nuevo_plan, cedula_actual))

                    conn.commit()
                    tipo_contrato_global[0] = nuevo_plan

                    messagebox.showinfo(
                        "¡Contrato Renovado!",
                        f"🎉 El titular ha completado la cuota N° 24.\n\n"
                        f"Su contrato se ha renovado automáticamente al plan:\n"
                        f"• {nuevo_plan}\n"
                        f"• Cuota mensual asignada: {precio_nuevo}"
                    )

                # CASO 2: Renovación independiente que completa un ciclo de 12
                elif es_renovacion and not es_renovacion_despues_ppa:
                    if total_cuotas_nuevo > 0 and total_cuotas_nuevo % 12 == 0:
                        if "entierro" in plan_norm:
                            messagebox.showinfo(
                                "¡Renovación Anual + Entierro Completada!",
                                "🎉 El titular ha completado las 12 cuotas del ciclo de Renovación Anual + Entierro.\n\n"
                                "El contrato continuará activo para el siguiente período de 12 meses."
                            )
                        else:
                            messagebox.showinfo(
                                "¡Renovación Anual Completada!",
                                "🎉 El titular ha completado las 12 cuotas del ciclo de Renovación Anual.\n\n"
                                "El contrato continuará activo para el siguiente período de 12 meses."
                            )

                # CASO 3: Renovación después de PPA que completa un ciclo de 12
                elif es_renovacion and es_renovacion_despues_ppa:
                    if total_cuotas_nuevo > 24 and ((total_cuotas_nuevo - 24) % 12 == 0):
                        if "entierro" in plan_norm:
                            messagebox.showinfo(
                                "¡Renovación Anual + Entierro Completada!",
                                "🎉 El titular ha completado las 12 cuotas del ciclo de Renovación Anual + Entierro.\n\n"
                                "El contrato continuará activo para el siguiente período de 12 meses."
                            )
                        else:
                            messagebox.showinfo(
                                "¡Renovación Anual Completada!",
                                "🎉 El titular ha completado las 12 cuotas del ciclo de Renovación Anual.\n\n"
                                "El contrato continuará activo para el siguiente período de 12 meses."
                            )

                # -------------------------------------------------------------
                # PREPARAR DATOS PARA EL RECIBO PDF
                # -------------------------------------------------------------
                cursor.execute("""
                    SELECT nombres, apellidos
                    FROM titulares
                    WHERE cedula = ?
                """, (cedula_actual,))

                tit_datos = cursor.fetchone()
                nombre_cliente_limpio = f"{tit_datos[0]} {tit_datos[1]}".upper() if tit_datos else cedula_actual

                # Generar texto descriptivo de la cuota pagada
                if "24 meses" in plan_norm or "ppa" in plan_norm:
                    cuotas_rest = max(0, 24 - cuota_numero)
                    cuota_str = f"Cuota #{cuota_numero} de 24 (Canceladas: {cuota_numero}/24 | Restantes: {cuotas_rest})"

                elif "renovacion anual" in plan_norm and "entierro" in plan_norm:
                    cuotas_rest = max(0, 12 - cuota_numero)
                    cuota_str = f"Ciclo Renovación + Entierro -> Cuota #{cuota_numero} de 12 (Canceladas: {cuota_numero}/12 | Restantes: {cuotas_rest})"

                else:
                    cuotas_rest = max(0, 12 - cuota_numero)
                    cuota_str = f"Ciclo Renovación -> Cuota #{cuota_numero} de 12 (Canceladas: {cuota_numero}/12 | Restantes: {cuotas_rest})"

                # Diccionario con todos los datos del recibo
                datos_recibo = {
                    "num_recibo": recibo_a_guardar,
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "cedula": cedula_actual,
                    "nombre_titular": nombre_cliente_limpio,
                    "cuota_info": cuota_str,
                    "num_contrato": lbl_cn_display.cget("text").replace("Contrato Sistema: ", ""),
                    "tipo_contrato": tipo_contrato_global[0] or plan_actual,
                    "sede": f"SEDE {SEDE_ACTUAL}",
                    "forma_pago": metodo,
                    "monto_bs": monto_bs_val,
                    "monto_usd": monto_usd_val,
                    "tasa_bcv": tasa_val,
                    "banco_origen": b_origen if metodo in ["Pago Móvil", "Transferencia"] else "N/A",
                    "banco_destino": b_destino if metodo in ["Pago Móvil", "Transferencia"] else "N/A",
                    "num_operacion": num_op if metodo in ["Pago Móvil", "Transferencia"] else "N/A"
                }

                # Limpiar entradas de cobro
                txt_monto_bs.delete(0, "end")
                txt_banco_origen.delete(0, "end")
                txt_banco_destino.delete(0, "end")
                txt_num_referencia.delete(0, "end")

                # Refrescar la pantalla antes de abrir el recibo
                try:
                    buscar_y_calcular_pagos()
                except Exception as e_refresh:
                    print(f"Aviso al refrescar la pantalla: {e_refresh}")

                # Intentar abrir el recibo PDF
                try:
                    abrir_previsualizacion_recibo(ventana, datos_recibo)
                except PermissionError:
                    messagebox.showwarning(
                        "Pago registrado, recibo bloqueado",
                        "⚠️ El pago quedó registrado correctamente.\n\n"
                        "No se pudo generar/abrir el recibo PDF porque el archivo PDF está bloqueado o sin permisos.\n\n"
                        "Cierre cualquier ventana/PDF de recibo abierto y vuelva a intentar si necesita reemitir el recibo."
                    )
                except Exception as e_recibo:
                    messagebox.showwarning(
                        "Pago registrado, recibo no generado",
                        f"⚠️ El pago quedó registrado correctamente.\n\n"
                        f"Error al generar/abrir el recibo PDF:\n{e_recibo}"
                    )

            except Exception as e:
                if conn:
                    conn.rollback()
                messagebox.showerror("Fallo al registrar el cobro", f"Detalle: {e}")

            finally:
                if conn:
                    conn.close()

        finally:
            procesando_pago[0] = False

    # =========================================================================
    # FUNCIONES CALLBACK - PESTAÑA 4: REPORTES
    # =========================================================================

    # =========================================================================
    # UTILIDAD: Restar meses a una fecha (para períodos de reportes)
    # =========================================================================
    def restar_meses(fecha, meses):
        """Devuelve la fecha resultante de restar N meses a la fecha dada."""
        dias_por_mes = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        anno = fecha.year
        mes = fecha.month - meses

        while mes <= 0:
            mes += 12
            anno -= 1

        dia = min(fecha.day, dias_por_mes[mes - 1])
        return datetime(anno, mes, dia)

    # =========================================================================
    # REPORTE 1: GENERAL (todos los titulares y sus afiliados)
    # =========================================================================
    def construir_datos_reporte_afiliados():
        """
        Consulta la base de datos y devuelve una lista de filas en texto plano.
        Cada fila: [cédula, nombre, contrato, afiliados, tipo, pagadas, faltantes]
        """
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                t.cedula,
                t.nombres,
                t.apellidos,
                t.contrato_nuevo,
                t.tipo_contrato,
                t.recibos_previos,
                (SELECT COUNT(*) FROM familiares f WHERE f.titular_cedula = t.cedula) AS total_afiliados,
                (SELECT COUNT(*) FROM pagos p WHERE p.titular_cedula = t.cedula) AS pagos_sistema
            FROM titulares t
            ORDER BY t.contrato_nuevo ASC
        """)

        titulares = cursor.fetchall()
        conn.close()

        filas = []

        for row in titulares:
            cedula = row[0] or ""
            nombres = (row[1] or "").title()
            apellidos = (row[2] or "").title()
            contrato_nuevo = row[3] or ""
            tipo_contrato = row[4] or ""
            recibos_previos = row[5] or 0
            total_afiliados = row[6] or 0
            pagos_sistema = row[7] or 0

            cuotas_pagadas = recibos_previos + pagos_sistema

            tipo_lower = tipo_contrato.lower()
            if "24 meses" in tipo_lower:
                cuotas_totales = 24
            elif "renovación" in tipo_lower or "renovacion" in tipo_lower:
                cuotas_totales = 12
            else:
                cuotas_totales = 24

            if "24 meses" in tipo_lower:
                cuotas_en_ciclo = cuotas_pagadas
                cuotas_faltantes = max(0, cuotas_totales - cuotas_en_ciclo)
            else:
                if cuotas_pagadas > 24:
                    cuotas_en_ciclo = (cuotas_pagadas - 24) % 12
                    if cuotas_en_ciclo == 0 and cuotas_pagadas > 24:
                        cuotas_en_ciclo = 12
                else:
                    cuotas_en_ciclo = cuotas_pagadas % 12
                    if cuotas_en_ciclo == 0 and cuotas_pagadas > 0:
                        cuotas_en_ciclo = 12
                cuotas_faltantes = max(0, 12 - cuotas_en_ciclo)

            filas.append([
                cedula,
                f"{nombres} {apellidos}",
                contrato_nuevo,
                str(total_afiliados),
                tipo_contrato,
                f"{cuotas_en_ciclo}/{cuotas_totales}",
                str(cuotas_faltantes)
            ])

        return filas

    # =========================================================================
    # REPORTE 2: TITULAR INDIVIDUAL (datos + pagos del período)
    # =========================================================================
    def construir_reporte_titular(crit, meses):
        """
        Busca un titular por cédula, contrato nuevo o contrato viejo y arma
        el reporte con sus pagos de los últimos N meses (o todo el historial).
        Devuelve None si no encuentra al titular.
        """
        crit = crit.strip().upper()

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cedula, nombres, apellidos, contrato_viejo, contrato_nuevo, tipo_contrato, fecha_inicio
            FROM titulares
            WHERE cedula = ? OR UPPER(contrato_nuevo) = ? OR UPPER(contrato_viejo) = ?
        """, (crit, crit, crit))

        t = cursor.fetchone()

        if not t:
            conn.close()
            return None

        cedula, nombres, apellidos, c_viejo, c_nuevo, tipo_c, f_inicio = t

        # Determinar el período a consultar
        hoy = datetime.now()

        if meses:
            limite = restar_meses(hoy, meses)
            texto_periodo = f"Últimos {meses} meses (desde el {limite.strftime('%d/%m/%Y')})"
            cursor.execute("""
                SELECT num_recibo, fecha_pago, cuota_numero, forma_pago, monto_usd, monto_bs, tasa_bcv
                FROM pagos
                WHERE titular_cedula = ? AND fecha_pago >= ?
                ORDER BY fecha_pago DESC
            """, (cedula, limite.strftime("%Y-%m-%d")))
        else:
            texto_periodo = "Todo el historial de pagos"
            cursor.execute("""
                SELECT num_recibo, fecha_pago, cuota_numero, forma_pago, monto_usd, monto_bs, tasa_bcv
                FROM pagos
                WHERE titular_cedula = ?
                ORDER BY fecha_pago DESC
            """, (cedula,))

        pagos = cursor.fetchall()
        conn.close()

        filas = []
        total_usd = 0.0
        total_bs = 0.0

        for p in pagos:
            try:
                fecha_bonita = datetime.strptime(p[1], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                fecha_bonita = p[1] or "S/F"

            filas.append([
                f"#{p[0]}",
                fecha_bonita,
                p[2] if p[2] is not None else "S/F",
                p[3] or "N/A",
                f"${(p[4] or 0):,.2f}",
                f"Bs. {(p[5] or 0):,.2f}",
                f"{(p[6] or 0):,.2f}",
            ])
            total_usd += p[4] or 0
            total_bs += p[5] or 0

        return {
            "titulo": "REPORTE DE TITULAR INDIVIDUAL",
            "lineas": [
                f"Titular: {nombres.title()} {apellidos.title()} | Cédula: {cedula}",
                f"Contrato Viejo: {c_viejo or 'NINGUNO'} | Contrato Sistema: {c_nuevo} | Tipo: {tipo_c}",
                f"Fecha de contrato: {f_inicio or 'S/F'} | Período: {texto_periodo}",
                f"Pagos en el período: {len(pagos)} | Total USD: ${total_usd:,.2f} | Total Bs: {total_bs:,.2f}",
            ],
            "encabezados": ["Recibo", "Fecha", "Cuota", "Método", "Monto USD", "Monto Bs", "Tasa"],
            "filas": filas,
            "anchos": [60, 80, 60, 110, 80, 100, 70],
            "centradas": (0, 1, 2, 3, 6),
            "resumen": f"Pagos: {len(pagos)} | Total: ${total_usd:,.2f}",
            "nombre": f"reporte_titular_{cedula}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        }

    # =========================================================================
    # REPORTE 3: PAGOS POR PERÍODO (todos los titulares que pagaron)
    # =========================================================================
    def construir_reporte_periodo(desde_str, hasta_str):
        """
        Arma el reporte de todos los pagos registrados entre dos fechas
        (inclusive), de todos los titulares.
        Devuelve None si las fechas no son válidas.
        """
        if not validar_fecha_ddmmyyyy(desde_str) or not validar_fecha_ddmmyyyy(hasta_str):
            return None

        desde = datetime.strptime(desde_str, "%d/%m/%Y")
        hasta = datetime.strptime(hasta_str, "%d/%m/%Y")

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.fecha_pago, t.cedula, t.nombres, t.apellidos, t.contrato_nuevo,
                   p.num_recibo, p.forma_pago, p.monto_usd, p.monto_bs
            FROM pagos p
            JOIN titulares t ON t.cedula = p.titular_cedula
            WHERE p.fecha_pago BETWEEN ? AND ?
            ORDER BY p.fecha_pago ASC, t.nombres ASC
        """, (desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d")))

        pagos = cursor.fetchall()
        conn.close()

        filas = []
        total_usd = 0.0
        total_bs = 0.0

        for p in pagos:
            try:
                fecha_bonita = datetime.strptime(p[0], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                fecha_bonita = p[0] or "S/F"

            filas.append([
                fecha_bonita,
                p[1],
                f"{(p[2] or '').title()} {(p[3] or '').title()}",
                p[4] or "",
                f"#{p[5]}",
                p[6] or "N/A",
                f"${(p[7] or 0):,.2f}",
                f"Bs. {(p[8] or 0):,.2f}",
            ])
            total_usd += p[7] or 0
            total_bs += p[8] or 0

        return {
            "titulo": "REPORTE DE PAGOS POR PERÍODO",
            "lineas": [
                f"Período: desde el {desde_str} hasta el {hasta_str}",
                f"Pagos registrados: {len(pagos)} | Total USD: ${total_usd:,.2f} | Total Bs: {total_bs:,.2f}",
            ],
            "encabezados": ["Fecha", "Cédula", "Titular", "Contrato", "Recibo", "Método", "Monto USD", "Monto Bs"],
            "filas": filas,
            "anchos": [70, 90, 160, 70, 60, 100, 80, 100],
            "centradas": (0, 1, 4, 5),
            "resumen": f"Pagos: {len(pagos)} | Total: ${total_usd:,.2f}",
            "nombre": f"reporte_periodo_{desde_str.replace('/', '')}_{hasta_str.replace('/', '')}.pdf",
        }

    # =========================================================================
    # GENERADOR GENÉRICO DE PDF (lo usan los 3 reportes)
    # =========================================================================
    def guardar_pdf_reporte(titulo, lineas_info, encabezados, filas, anchos, centradas, nombre_sugerido, ruta_destino=None):
        """
        Genera el PDF horizontal con la tabla del reporte.
        - Si ruta_destino es None: pregunta al usuario dónde guardar.
        - Si ruta_destino tiene una ruta: guarda ahí sin preguntar (para imprimir).
        Devuelve la ruta final o None si el usuario canceló.
        """
        from xml.sax.saxutils import escape
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        if ruta_destino is None:
            ruta_destino = filedialog.asksaveasfilename(
                title="Guardar Reporte",
                defaultextension=".pdf",
                initialfile=nombre_sugerido,
                filetypes=[("Archivo PDF", "*.pdf"), ("Todos los archivos", "*.*")]
            )

            if not ruta_destino:
                return None

        styles = getSampleStyleSheet()

        estilo_izq = ParagraphStyle('repIzq', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.black)
        estilo_cen = ParagraphStyle('repCen', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.black, alignment=1)
        estilo_head = ParagraphStyle('repHead', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1)

        story = [Paragraph(f"<b>{escape(titulo)}</b>", styles['Title'])]

        for linea in lineas_info:
            story.append(Paragraph(escape(linea), styles['Normal']))

        story.append(Spacer(1, 10))

        datos_tabla = [[Paragraph(escape(str(h)), estilo_head) for h in encabezados]]

        for fila in filas:
            datos_tabla.append([
                Paragraph(escape(str(celda)), estilo_cen if i in centradas else estilo_izq)
                for i, celda in enumerate(fila)
            ])

        tabla = Table(datos_tabla, colWidths=anchos)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f538d")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#7f8c8d")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))

        story.append(tabla)

        doc = SimpleDocTemplate(
            ruta_destino,
            pagesize=landscape(letter),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        doc.build(story)

        return ruta_destino

    # =========================================================================
    # CENTRO DE REPORTES: ventana con vista previa y guardado opcional
    # =========================================================================
    def construir_pestana_reportes():
        """
        Construye el Centro de Reportes DENTRO de la pestaña
        "Reportes y Estados de Cuenta", sin abrir ventanas nuevas.
        Orden visual (de arriba a abajo):
          1. Título
          2. Selector de tipo de reporte
          3. Parámetros dinámicos
          4. Botones de acción (siempre visibles)
          5. Tabla de vista previa (ocupa el espacio libre)
          6. Resumen
          7. Gráfico de cobranzas (altura fija)
        """
        # Datos de la vista previa actual (los usa Guardar/Imprimir)
        datos_preview = {"listo": False}

        # Widgets de parámetros dinámicos
        params = {}

        # -----------------------------------------------------------------
        # 1. Título
        # -----------------------------------------------------------------
        ctk.CTkLabel(tab_reportes, text="📊 Centro de Reportes", font=("Arial", 16, "bold")).pack(pady=(10, 5), padx=20, anchor="w")

        # -----------------------------------------------------------------
        # 2. Selector de tipo de reporte
        # -----------------------------------------------------------------
        frame_tipo = ctk.CTkFrame(tab_reportes, fg_color="transparent")
        frame_tipo.pack(pady=2, padx=20, fill="x")

        ctk.CTkLabel(frame_tipo, text="Tipo de Reporte:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))

        tipos_reporte = [
            "General (todos los titulares)",
            "Titular Individual",
            "Pagos por Período",
        ]

        # -----------------------------------------------------------------
        # 3. Parámetros dinámicos
        # -----------------------------------------------------------------
        frame_params = ctk.CTkFrame(tab_reportes, fg_color="transparent")
        frame_params.pack(pady=2, padx=20, fill="x")

        def redibujar_parametros():
            """Muestra solo los parámetros que necesita el tipo elegido."""
            for w in frame_params.winfo_children():
                w.destroy()

            tipo = combo_tipo.get()

            if tipo == "Titular Individual":
                ctk.CTkLabel(frame_params, text="Cédula o Contrato:", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=5, sticky="w")
                params["txt_busq"] = ctk.CTkEntry(frame_params, width=220, placeholder_text="V12345678 o A-00001")
                params["txt_busq"].grid(row=1, column=0, padx=5, pady=2)

                ctk.CTkLabel(frame_params, text="Período:", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=5, sticky="w")
                params["combo_meses"] = ctk.CTkComboBox(
                    frame_params,
                    values=["Últimos 1 mes", "Últimos 3 meses", "Últimos 6 meses", "Últimos 12 meses", "Todos los pagos"],
                    width=160
                )
                params["combo_meses"].set("Últimos 6 meses")
                params["combo_meses"].grid(row=1, column=1, padx=5, pady=2)

            elif tipo == "Pagos por Período":
                ctk.CTkLabel(frame_params, text="Desde (DD/MM/YYYY):", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=5, sticky="w")
                params["txt_desde"] = ctk.CTkEntry(
                    frame_params, width=130, placeholder_text="DD/MM/YYYY",
                    validate="key", validatecommand=(v_fecha, '%P')
                )
                params["txt_desde"].grid(row=1, column=0, padx=5, pady=2)

                ctk.CTkLabel(frame_params, text="Hasta (DD/MM/YYYY):", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=5, sticky="w")
                params["txt_hasta"] = ctk.CTkEntry(
                    frame_params, width=130, placeholder_text="DD/MM/YYYY",
                    validate="key", validatecommand=(v_fecha, '%P')
                )
                params["txt_hasta"].grid(row=1, column=1, padx=5, pady=2)

        combo_tipo = ctk.CTkComboBox(
            frame_tipo,
            values=tipos_reporte,
            width=280,
            command=lambda e: redibujar_parametros()
        )
        combo_tipo.set(tipos_reporte[0])
        combo_tipo.pack(side="left")

        redibujar_parametros()

        # -----------------------------------------------------------------
        # 4. Frame de botones de acción (se empaca ANTES que la vista previa
        #    para que los botones NUNCA queden tapados)
        # -----------------------------------------------------------------
        frame_botones_rep = ctk.CTkFrame(tab_reportes, fg_color="transparent")
        frame_botones_rep.pack(pady=5, padx=20, fill="x")

        # -----------------------------------------------------------------
        # 5. Área de vista previa (ocupa el espacio libre de la pestaña)
        # -----------------------------------------------------------------
        frame_preview = ctk.CTkFrame(tab_reportes)
        frame_preview.pack(pady=5, padx=20, fill="both", expand=True)

        # -----------------------------------------------------------------
        # 6. Etiqueta de resumen
        # -----------------------------------------------------------------
        lbl_resumen = ctk.CTkLabel(tab_reportes, text="", font=("Arial", 11, "bold"), text_color="#2ecc71")
        lbl_resumen.pack(pady=(0, 5), padx=20, anchor="w")

        # -----------------------------------------------------------------
        # 7. Gráfico de cobranzas (altura fija para no robar espacio)
        # -----------------------------------------------------------------
        #frame_grafico.pack(pady=(0, 10), padx=20, fill="x")

        # -----------------------------------------------------------------
        # FUNCIONES DE ACCIÓN (definidas antes de crear los botones)
        # -----------------------------------------------------------------

        def previsualizar():
            """Consulta los datos según el tipo y los muestra en la tabla."""
            tipo = combo_tipo.get()

            if tipo == tipos_reporte[0]:
                # ---------------- REPORTE GENERAL ----------------
                filas = construir_datos_reporte_afiliados()

                if not filas:
                    messagebox.showwarning("Sin Datos", "No hay titulares registrados.")
                    return

                datos_preview.clear()
                datos_preview.update({
                    "listo": True,
                    "titulo": "REPORTE DE AFILIADOS",
                    "lineas": [f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Sede: {SEDE_ACTUAL}"],
                    "encabezados": ["Cédula", "Nombre Completo", "Contrato N°", "Afiliados", "Tipo de Contrato", "Cuotas Pagadas", "Cuotas Faltantes"],
                    "filas": filas,
                    "anchos": [70, 150, 70, 55, 150, 75, 75],
                    "centradas": (0, 2, 3, 5, 6),
                    "resumen": f"Total de titulares: {len(filas)} | Total de afiliados: {sum(int(f[3]) for f in filas)}",
                    "nombre": f"reporte_afiliados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                })

            elif tipo == tipos_reporte[1]:
                # ---------------- TITULAR INDIVIDUAL ----------------
                crit = params.get("txt_busq").get().strip()

                if not crit:
                    messagebox.showwarning("Falta Dato", "Ingrese la cédula o el contrato del titular.")
                    return

                mapa_meses = {
                    "Últimos 1 mes": 1,
                    "Últimos 3 meses": 3,
                    "Últimos 6 meses": 6,
                    "Últimos 12 meses": 12,
                    "Todos los pagos": None,
                }

                resultado = construir_reporte_titular(crit, mapa_meses.get(params.get("combo_meses").get(), 6))

                if resultado is None:
                    messagebox.showerror("No Encontrado", "Ningún titular coincide con esa cédula o contrato.")
                    return

                datos_preview.clear()
                datos_preview.update(resultado)
                datos_preview["listo"] = True

            else:
                # ---------------- PAGOS POR PERÍODO ----------------
                resultado = construir_reporte_periodo(
                    params.get("txt_desde").get().strip(),
                    params.get("txt_hasta").get().strip()
                )

                if resultado is None:
                    messagebox.showwarning("Fecha Inválida", "Revise las fechas. Deben tener formato DD/MM/YYYY.")
                    return

                if not resultado["filas"]:
                    messagebox.showwarning("Sin Datos", "No hay pagos registrados en ese período.")
                    return

                datos_preview.clear()
                datos_preview.update(resultado)
                datos_preview["listo"] = True

            # ---------------- Redibujar la tabla de vista previa ----------------
            for w in frame_preview.winfo_children():
                w.destroy()

            cols = tuple(f"c{i}" for i in range(len(datos_preview["encabezados"])))
            arbol = ttk.Treeview(frame_preview, columns=cols, show="headings", height=10)

            for i, (col, head) in enumerate(zip(cols, datos_preview["encabezados"])):
                arbol.heading(col, text=head)
                arbol.column(col, width=datos_preview["anchos"][i], anchor="center")

            barra = ttk.Scrollbar(frame_preview, orient="vertical", command=arbol.yview)
            arbol.configure(yscrollcommand=barra.set)

            for fila in datos_preview["filas"]:
                arbol.insert("", "end", values=fila)

            arbol.pack(side="left", fill="both", expand=True)
            barra.pack(side="right", fill="y")

            lbl_resumen.configure(text=datos_preview["resumen"])

        def guardar_pdf():
            """Guarda como PDF lo que está en la vista previa."""
            if not datos_preview.get("listo"):
                messagebox.showwarning("Sin Vista Previa", "Primero presione 'Previsualizar'.")
                return

            try:
                ruta = guardar_pdf_reporte(
                    datos_preview["titulo"],
                    datos_preview["lineas"],
                    datos_preview["encabezados"],
                    datos_preview["filas"],
                    datos_preview["anchos"],
                    datos_preview["centradas"],
                    datos_preview["nombre"],
                    ruta_destino=None,
                )
            except PermissionError:
                messagebox.showerror("Error de Permisos", "No se pudo guardar el PDF. Intente otra ubicación.")
                return
            except Exception as e:
                messagebox.showerror("Error al Generar PDF", f"Ocurrió un error:\n\n{e}")
                return

            if ruta:
                messagebox.showinfo("Reporte Generado", f"✅ El reporte fue guardado en:\n\n{ruta}")
                os.startfile(ruta)

        def imprimir_reporte():
            """
            Envía el reporte de la vista previa directo a la impresora
            predeterminada, sin necesidad de guardarlo como PDF antes.
            """
            if not datos_preview.get("listo"):
                messagebox.showwarning("Sin Vista Previa", "Primero presione 'Previsualizar'.")
                return

            import tempfile

            # Generar un PDF temporal solo para imprimir
            ruta_temp = os.path.join(
                tempfile.gettempdir(),
                f"reporte_print_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
            )

            try:
                guardar_pdf_reporte(
                    datos_preview["titulo"],
                    datos_preview["lineas"],
                    datos_preview["encabezados"],
                    datos_preview["filas"],
                    datos_preview["anchos"],
                    datos_preview["centradas"],
                    datos_preview["nombre"],
                    ruta_destino=ruta_temp,
                )
            except Exception as e:
                messagebox.showerror("Error de Impresión", f"No se pudo generar el reporte para imprimir:\n\n{e}")
                return

            try:
                # Enviar directo a la impresora predeterminada de Windows
                os.startfile(ruta_temp, "print")
                messagebox.showinfo("Imprimiendo", "🖨 El reporte fue enviado a la impresora predeterminada.")
            except Exception:
                # Si no hay verbo de impresión, abrir el visor para imprimir desde ahí
                os.startfile(ruta_temp)
                messagebox.showwarning(
                    "Impresión",
                    "No se pudo enviar directo a la impresora.\n\n"
                    "El reporte se abrió en su visor PDF.\n"
                    "Imprímalo desde ahí con Ctrl + P."
                )

        # -----------------------------------------------------------------
        # BOTONES DE ACCIÓN (se crean al final, cuando las funciones existen)
        # -----------------------------------------------------------------
        ctk.CTkButton(
            frame_botones_rep,
            text="🔍 Previsualizar",
            fg_color="#27ae60",
            font=("Arial", 12, "bold"),
            command=previsualizar
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_botones_rep,
            text="💾 Guardar como PDF",
            fg_color="#1f538d",
            font=("Arial", 12, "bold"),
            command=guardar_pdf
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_botones_rep,
            text="🖨 Imprimir Reporte",
            fg_color="#8e44ad",
            font=("Arial", 12, "bold"),
            command=imprimir_reporte
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_botones_rep,
            text="Salir del Sistema",
            fg_color="#d35400",
            command=ventana.destroy
        ).pack(side="right", padx=5)

        # Cargar el gráfico de cobranzas al construir la pestaña
        #cargar_reporte_cobros()

    def cargar_reporte_cobros():
        """
        Carga el gráfico de cobros mensuales en la pestaña de reportes.
        Muestra los últimos 6 meses con el total cobrado en cada uno.
        """
        # for widget in frame_grafico.winfo_children():
        #     widget.destroy()

        # conn = conectar()
        # cursor = conn.cursor()

        # cursor.execute("SELECT strftime('%m/%Y', fecha_pago) as mes, SUM(monto_usd) FROM pagos GROUP BY mes ORDER BY fecha_pago ASC LIMIT 6")

        # filas = cursor.fetchall()
        # conn.close()

        # datos_meses = {}

        # if filas:
        #     for mes, monto in filas:
        #         datos_meses[mes or "S/F"] = monto or 0.0
        # else:
        #     datos_meses = {"Ene": 0, "Feb": 0, "Mar": 0}

        # try:
        #     renderizar_grafico_cobranza(frame_grafico, datos_meses)
        # except Exception as ex:
        #     ctk.CTkLabel(frame_grafico, text=f"No se pudo cargar el gráfico: {ex}", font=("Arial", 12)).pack(pady=20)
            
    # =========================================================================
    # FUNCIONES CALLBACK - PESTAÑA 5: CONFIGURACIÓN (Solo Administradores)
    # =========================================================================

    if es_admin:
        def ejecutar_respaldo():
            """
            Copia la base de datos funeraria.db a una ubicación elegida
            por el usuario (USB, carpeta externa, etc.)
            """
            fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_defecto = f"respaldo_funeraria_{fecha_str}.db"

            destino = filedialog.asksaveasfilename(
                title="Guardar Respaldo de Base de Datos",
                initialfile=nombre_defecto,
                defaultextension=".db",
                filetypes=[("Base de Datos SQLite", "*.db"), ("Todos los archivos", "*.*")]
            )

            if destino:
                try:
                    ruta_origen = obtener_ruta_db()
                    shutil.copy2(ruta_origen, destino)

                    messagebox.showinfo(
                        "Respaldo Éxitoso",
                        f"🎉 Copia de seguridad guardada exitosamente en:\n\n{destino}"
                    )

                except Exception as ex:
                    messagebox.showerror("Error de Respaldo", f"No se pudo copiar la base de datos:\n{ex}")

        def refrescar_tabla_usuarios():
            """Actualiza la tabla de usuarios registrados en el sistema."""
            for item in tabla_u.get_children():
                tabla_u.delete(item)

            conn = conectar()
            cursor = conn.cursor()

            cursor.execute("SELECT id, usuario, COALESCE(rol, 'operador') FROM usuarios ORDER BY id ASC")

            for u_row in cursor.fetchall():
                tabla_u.insert("", "end", values=(u_row[0], u_row[1], u_row[2].upper()))

            conn.close()

        def crear_usuario():
            """
            Crea un nuevo usuario en el sistema con usuario, contraseña y rol.
            Valida que las contraseñas coincidan antes de guardar.
            """
            u_name = txt_u_user.get().strip().lower()
            u_clave = txt_u_pass.get().strip()
            u_clave2 = txt_u_pass2.get().strip()
            u_role = combo_u_rol.get().lower()

            if not u_name or not u_clave or not u_clave2:
                messagebox.showwarning(
                    "Campos Requeridos",
                    "Debe completar todos los campos: usuario, contraseña y la confirmación."
                )
                return

            if u_clave != u_clave2:
                messagebox.showerror(
                    "Error de Coincidencia",
                    "⚠️ Las contraseñas ingresadas NO coinciden. Por favor verifique."
                )
                txt_u_pass2.focus()
                return

            try:
                conn = conectar()
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)",
                    (u_name, u_clave, u_role)
                )

                conn.commit()
                conn.close()

                messagebox.showinfo("Éxito", f"Usuario '{u_name}' registrado correctamente como {u_role.upper()}.")

                txt_u_user.delete(0, "end")
                txt_u_pass.delete(0, "end")
                txt_u_pass2.delete(0, "end")

                refrescar_tabla_usuarios()

            except Exception as ex:
                messagebox.showerror("Error al Crear Usuario", f"No se pudo crear el usuario. Posiblemente ya existe.\n{ex}")

        def cambiar_clave_usuario():
            """
            Abre una ventana emergente para cambiar la contraseña
            del usuario seleccionado en la tabla de usuarios.
            """
            sel = tabla_u.selection()

            if not sel:
                messagebox.showwarning(
                    "Selección Requerida",
                    "Seleccione un usuario de la tabla para cambiar su contraseña."
                )
                return

            u_id, u_name, _ = tabla_u.item(sel)['values']

            top_pass = ctk.CTkToplevel(ventana)
            top_pass.title(f"Cambiar Contraseña - {u_name}")
            top_pass.geometry("380x250")
            top_pass.grab_set()

            ctk.CTkLabel(
                top_pass,
                text=f"🔒 Nueva Clave para '{u_name}':",
                font=("Arial", 12, "bold")
            ).pack(pady=(15, 2), padx=20, anchor="w")

            txt_p1 = ctk.CTkEntry(top_pass, width=280, show="*")
            txt_p1.pack(pady=2, padx=20)

            ctk.CTkLabel(top_pass, text="Confirmar Nueva Clave:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")

            txt_p2 = ctk.CTkEntry(top_pass, width=280, show="*")
            txt_p2.pack(pady=2, padx=20)

            txt_p1.focus_set()

            def guardar_nueva_clave():
                p1 = txt_p1.get().strip()
                p2 = txt_p2.get().strip()

                if not p1 or not p2:
                    messagebox.showwarning("Campos Vacíos", "Debe llenar ambos campos de contraseña.", parent=top_pass)
                    return

                if p1 != p2:
                    messagebox.showerror(
                        "Error de Coincidencia",
                        "⚠️ Las contraseñas ingresadas NO coinciden.",
                        parent=top_pass
                    )
                    txt_p2.focus()
                    return

                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("UPDATE usuarios SET contrasena = ? WHERE id = ?", (p1, u_id))
                conn.commit()
                conn.close()

                messagebox.showinfo("Éxito", f"Contraseña del usuario '{u_name}' actualizada correctamente.")
                top_pass.destroy()

            ctk.CTkButton(top_pass, text="Guardar Nueva Clave", fg_color="green", command=guardar_nueva_clave).pack(pady=15)

        def eliminar_usuario():
            """
            Elimina un usuario del sistema previa confirmación.
            No permite eliminar el usuario con el que se inició sesión.
            """
            sel = tabla_u.selection()

            if not sel:
                messagebox.showwarning("Selección Requerida", "Seleccione un usuario de la tabla para eliminarlo.")
                return

            u_id, u_name, u_rol = tabla_u.item(sel)['values']

            if u_name.lower() == usuario_actual.lower():
                messagebox.showerror(
                    "Acción Bloqueada",
                    "No puede eliminar la cuenta activa con la que ha iniciado sesión actualmente."
                )
                return

            if messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Está seguro de eliminar de forma definitiva al usuario '{u_name}'?"
            ):
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM usuarios WHERE id = ?", (u_id,))
                conn.commit()
                conn.close()

                messagebox.showinfo("Éxito", f"Usuario '{u_name}' eliminado.")
                refrescar_tabla_usuarios()

        # Cargar la tabla de usuarios al iniciar
        refrescar_tabla_usuarios()

    # =========================================================================
    # CONFIGURACIÓN DE BOTONES (Se asignan las funciones a cada botón)
    # =========================================================================
    # Los botones se crearon con command=lambda: None como placeholder.
    # Aquí se les asigna la función correspondiente usando .configure()
    # =========================================================================

    # --- PESTAÑA 1: Botones de Registro de Clientes ---
    frame_botones_registro = ctk.CTkFrame(tab_clientes, fg_color="transparent")
    frame_botones_registro.grid(row=4, column=0, columnspan=4, pady=15, padx=10, sticky="ew")

    btn_guardar_tit = ctk.CTkButton(frame_botones_registro, text="Guardar Titular", fg_color="green", command=guardar_titular)
    btn_guardar_tit.pack(side="left", padx=5)

    btn_add_fam = ctk.CTkButton(
        frame_botones_registro,
        text="+ Agregar Familiar",
        fg_color="#1f538d",
        state="disabled",
        command=lambda: abrir_modulo_familiares(
            ventana,
            txt_cedula.get().strip().upper(),
            v_letras,
            lambda: refrescar_tabla_familiares(txt_cedula.get().strip().upper())
        )
    )
    btn_add_fam.pack(side="left", padx=5)

    btn_nuevo_contrato = ctk.CTkButton(frame_botones_registro, text="✨ Nuevo Contrato", fg_color="#8e44ad", command=limpiar_formulario_registro)
    btn_nuevo_contrato.pack(side="left", padx=5)

    btn_salir = ctk.CTkButton(frame_botones_registro, text="Salir del Sistema", fg_color="#d35400", command=ventana.destroy)
    btn_salir.pack(side="right", padx=5)

    # --- PESTAÑA 2: Botones de Edición ---
    frame_botones_ed = ctk.CTkFrame(tab_edicion, fg_color="transparent")
    frame_botones_ed.pack(pady=10, padx=10, fill="x")

    btn_actualizar = ctk.CTkButton(
        frame_botones_ed,
        text="Guardar Cambios Titular",
        fg_color="green",
        state="disabled",
        command=ejecutar_guardar_cambios_titular
    )
    btn_actualizar.grid(row=0, column=0, padx=5)

    btn_retirar_fam = ctk.CTkButton(
        frame_botones_ed,
        text="- Retirar Afiliado Seleccionado",
        fg_color="red",
        state="disabled",
        command=ejecutar_retirar_familiar
    )
    btn_retirar_fam.grid(row=0, column=1, padx=5)

    btn_add_fam_ed = ctk.CTkButton(
        frame_botones_ed,
        text="+ Reemplazar / Agregar Afiliado",
        fg_color="#1f538d",
        state="disabled",
        command=lambda: abrir_modulo_familiares(
            ventana,
            cedula_titular_edicion[0],
            v_letras,
            lambda: [cargar_datos_edicion(), refrescar_tabla_familiares(cedula_titular_edicion[0])]
        )
    )
    btn_add_fam_ed.grid(row=0, column=2, padx=5)

    # Botón Salir de la pestaña de edición
    ctk.CTkButton(frame_botones_ed, text="Salir", fg_color="#d35400", command=ventana.destroy).grid(row=0, column=3, padx=20)

    # Configurar el botón de búsqueda de la pestaña de edición
    btn_buscar_ed.configure(command=cargar_datos_edicion)

    # Enlace: al presionar Enter en el campo de búsqueda, se ejecuta la búsqueda
    txt_busq_ed.bind("<Return>", lambda e: cargar_datos_edicion())

    # --- PESTAÑA 3: Botones de Control de Pagos ---
    # Configurar botones que fueron creados como placeholder
    btn_buscar.configure(command=buscar_y_calcular_pagos)
    btn_ver_notas.configure(command=ver_notas_titular)
    combo_forma_pago.configure(command=alternar_campos_bancarios_cobro)

    # Botón de Procesar Pago
    btn_procesar_pago = ctk.CTkButton(
        frame_cobro,
        text="Procesar Pago",
        command=ejecutar_pago,
        fg_color="#1f538d",
        font=("Arial", 12, "bold")
    )
    btn_procesar_pago.grid(row=3, column=3, padx=10, pady=5)

    # Inicializar el estado de los campos bancarios según la forma de pago actual
    alternar_campos_bancarios_cobro(combo_forma_pago.get())

    # Enlace: al presionar Enter en el campo de búsqueda de pagos
    txt_busqueda_ced.bind("<Return>", lambda e: buscar_y_calcular_pagos())

    # Botón Salir de la pestaña de pagos
    frame_acciones_p = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_acciones_p.pack(pady=15, padx=20, fill="x")
    ctk.CTkButton(frame_acciones_p, text="Salir", fg_color="#d35400", command=ventana.destroy).grid(row=0, column=1, padx=20)

    # --- PESTAÑA 4: Construir el Centro de Reportes dentro de la pestaña ---
    construir_pestana_reportes()

    # --- PESTAÑA 5: Configurar botones de administración ---
    if es_admin:
        btn_respaldo.configure(command=ejecutar_respaldo)
        btn_add_u.configure(command=crear_usuario)

        # Botones de acciones de usuarios
        ctk.CTkButton(frame_u_acciones, text="🔑 Cambiar Contraseña", fg_color="#e67e22", command=cambiar_clave_usuario).pack(side="left", padx=5)
        ctk.CTkButton(frame_u_acciones, text="❌ Eliminar Usuario", fg_color="#c0392b", command=eliminar_usuario).pack(side="left", padx=5)
        ctk.CTkButton(frame_u_acciones, text="Salir del Sistema", fg_color="#d35400", command=ventana.destroy).pack(side="right", padx=5)

    # =========================================================================
    # NAVEGACIÓN CON TECLA ENTER - PESTAÑA 3: CONTROL DE PAGOS
    # =========================================================================
    # Permite al operador avanzar entre campos de pago usando Enter,
    # facilitando la transcripción rápida de datos.
    # =========================================================================

    vincular_salto_enter(txt_tasa, combo_forma_pago)
    vincular_salto_enter(combo_forma_pago, txt_monto_bs)

    def saltar_desde_monto(_):
        """
        Al presionar Enter en el campo de monto:
        - Si es Transferencia/Pago Móvil, salta al Banco Pagador.
        - Si es Efectivo, salta directamente al botón Procesar Pago.
        """
        if combo_forma_pago.get() in ["Transferencia", "Pago Móvil"]:
            txt_banco_origen.focus()
        else:
            btn_procesar_pago.focus()

        return "break"

    txt_monto_bs.bind("<Return>", saltar_desde_monto)

    vincular_salto_enter(txt_banco_origen, txt_banco_destino)
    vincular_salto_enter(txt_banco_destino, txt_num_referencia)
    vincular_salto_enter(txt_num_referencia, btn_procesar_pago)

    # =========================================================================
    # MOTOR DE LIMPIEZA INTER-PESTAÑAS
    # =========================================================================
    # Cada vez que el usuario cambia de pestaña, se limpian los campos
    # de la pestaña anterior para evitar confusiones con datos viejos.
    # =========================================================================

    def gestionar_limpieza_pestanas():
        """
        Limpia todos los campos de las pestañas cuando el usuario
        cambia entre ellas. Esto evita que datos de un titular
        anterior aparezcan al buscar uno nuevo.
        """
        # Limpiar PESTAÑA 2: Edición
        txt_busq_ed.delete(0, "end")
        lbl_fecha_contrato_ed.configure(text="fecha de contrato: --/--/----")
        lbl_contrato_nuevo_ed.configure(text="Contrato Sistema: --")
        lbl_tipo_contrato_ed.configure(text="Tipo de Contrato: --")

        for t in [txt_ed_nom, txt_ed_ape, txt_ed_tel, txt_ed_corr, txt_ed_dir,
                  txt_ed_contrato_viejo, txt_ed_fecha_contrato_viejo]:
            t.delete(0, "end")

        txt_ed_notas.delete("1.0", "end")

        for item in tabla_ed.get_children():
            tabla_ed.delete(item)

        for b in [btn_actualizar, btn_retirar_fam, btn_add_fam_ed]:
            b.configure(state="disabled")

        # Limpiar PESTAÑA 3: Pagos
        txt_busqueda_ced.delete(0, "end")

        cedula_titular_pago[0] = ""
        tipo_contrato_global[0] = ""
        proximo_recibo_global[0] = 1

        txt_tasa.delete(0, "end")
        txt_tasa.configure(state="disabled")

        lbl_nombre_clie.configure(text="Cliente: Seleccione un titular")
        lbl_cv_display.configure(text="Contrato Viejo: --")
        lbl_cn_display.configure(text="Contrato Sistema: --")
        lbl_recibo_next.configure(text="N° Recibo Asignado a Procesar: --")
        lbl_aviso_morosidad.configure(text="ESTADO: --", text_color="grey")
        lbl_up_detalles.configure(text="Historial de Cobros: Sin registrar búsquedas.")
        lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")

        btn_procesar_pago.configure(state="disabled")
        btn_ver_notas.configure(state="disabled")
        btn_ver_notas.configure(fg_color="#8e44ad", text="📝 Ver Notas del Titular")
        nota_titular_global[0] = ""

    # Vincular la limpieza al cambio de pestaña
    pestanas.configure(command=gestionar_limpieza_pestanas)

    # =========================================================================
    # MOSTRAR SPLASH Y LUEGO DASHBOARD
    # =========================================================================
    # El splash se muestra durante 1.6 segundos mientras se carga
    # la interfaz principal. Luego se destruye y aparece el dashboard.
    # =========================================================================

    def actualizar_barra_splash(valor):
        """Actualiza la barra de progreso del splash de carga."""
        try:
            barra_splash.set(valor)
        except Exception:
            pass

    def cerrar_splash():
        """
        Cierra la ventana del splash y muestra la ventana principal
        del dashboard. Se ejecuta después de la animación de carga.
        """
        try:
            splash.destroy()
        except Exception:
            pass

        ventana.deiconify()
        ventana.lift()
        ventana.focus_force()

    # Permitir cerrar el splash manualmente si el usuario lo cierra
    splash.protocol("WM_DELETE_WINDOW", cerrar_splash)

    # Pequeña animación de carga (la barra avanza en 3 pasos)
    ventana.after(400, lambda: actualizar_barra_splash(0.55))
    ventana.after(900, lambda: actualizar_barra_splash(0.80))
    ventana.after(1300, lambda: actualizar_barra_splash(1.0))

    # Mostrar el dashboard después del splash (1.6 segundos)
    ventana.after(1600, cerrar_splash)

    # Iniciar el bucle principal de la aplicación
    ventana.mainloop()


# =========================================================================
# 5. COMPONENTE MODAL: REGISTRO DE AFILIADOS
# =========================================================================
# Esta es una ventana emergente (modal) que permite agregar familiares
# al contrato de un titular. Se abre desde las pestañas 1 y 2.
# =========================================================================

def abrir_modulo_familiares(ventana_padre, cedula_titular, v_let, funcion_exito_refrescar):
    """
    Abre una ventana modal para registrar un nuevo afiliado (familiar)
    vinculado al titular indicado por cedula_titular.
    
    Parámetros:
      - ventana_padre: ventana principal del dashboard
      - cedula_titular: cédula del titular al que se le agrega el familiar
      - v_let: validador de solo letras registrado en la ventana
      - funcion_exito_refrescar: función a ejecutar después de guardar
    """
    # Verificar que el titular no tenga ya 8 afiliados (límite del contrato)
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM familiares WHERE titular_cedula = ?", (cedula_titular,))
    cantidad = cursor.fetchone()[0]

    conn.close()

    if cantidad >= 8:
        messagebox.showwarning("Límite Alcanzado", "Este contrato ya cuenta con los 8 familiares permitidos.")
        return

    # Crear la ventana modal
    pop = ctk.CTkToplevel(ventana_padre)
    pop.title("Agregar Familiar")
    pop.geometry("450x480")
    pop.grab_set()  # Forzar foco en esta ventana

    # Campo: Cédula del familiar (opcional si es menor de edad)
    ctk.CTkLabel(
        pop,
        text="Cédula Familiar (V/E + Números, o vacío si es menor):",
        font=("Arial", 11, "bold")
    ).pack(pady=(10, 2), padx=20, anchor="w")

    txt_fcedula = ctk.CTkEntry(pop, width=280, placeholder_text="Ej: V25111222")
    txt_fcedula.pack(pady=2, padx=20)

    # Campo: Nombres del familiar
    ctk.CTkLabel(pop, text="Nombres:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_fnombre = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fnombre.pack(pady=2, padx=20)

    # Campo: Apellidos del familiar
    ctk.CTkLabel(pop, text="Apellidos:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_fapellido = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fapellido.pack(pady=2, padx=20)

    # Campo: Fecha de nacimiento del familiar
    ctk.CTkLabel(pop, text="Fecha Nacimiento Afiliado:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_ffecha = ctk.CTkEntry(pop, placeholder_text="DD/MM/YYYY", width=280)
    txt_ffecha.pack(pady=2, padx=20)

    # Campo: Parentesco con el titular
    ctk.CTkLabel(pop, text="Parentesco con el Titular:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_fparentesco = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fparentesco.pack(pady=2, padx=20)

    # Establecer foco en el primer campo
    txt_fcedula.focus_set()

    # Navegación con Enter entre los campos del modal
    vincular_salto_enter(txt_fcedula, txt_fnombre)
    vincular_salto_enter(txt_fnombre, txt_fapellido)
    vincular_salto_enter(txt_fapellido, txt_ffecha)
    vincular_salto_enter(txt_ffecha, txt_fparentesco)

    def guardar_familiar():
        """
        Valida y guarda el nuevo familiar en la base de datos.
        Verifica que la cédula no esté duplicada en otro contrato.
        """
        fced_raw = txt_fcedula.get().strip().upper()
        fced = fced_raw if fced_raw else "MENOR"

        fnom = txt_fnombre.get().strip().lower()
        fape = txt_fapellido.get().strip().lower()
        fpar = txt_fparentesco.get().strip().lower()
        ffec = txt_ffecha.get().strip()

        # Validar cédula (si no es menor de edad)
        if fced != "MENOR" and not validar_mascara_cedula(fced):
            messagebox.showwarning("Formato Obligatorio", "Cédula del familiar inválida.")
            txt_fcedula.focus()
            return

        # Validar campos obligatorios
        if not fnom or not fape or not fpar or not ffec:
            messagebox.showwarning("Campos Vacíos", "Todos los campos son obligatorios.")
            return

        # Validar formato de fecha
        try:
            if len(ffec) != 10:
                raise ValueError
            datetime.strptime(ffec, "%d/%m/%Y")
        except ValueError:
            messagebox.showwarning(
                "Fecha Inválida",
                "La fecha de nacimiento debe tener un formato válido DD/MM/YYYY (Ej: 15/05/1990)."
            )
            return

        # Verificar que la cédula no esté registrada en otro contrato
        if fced != "MENOR":
            conn = conectar()
            cursor = conn.cursor()

            cursor.execute("SELECT titular_cedula FROM familiares WHERE UPPER(cedula) = ?", (fced,))
            duplicado = cursor.fetchone()

            conn.close()

            if duplicado:
                messagebox.showerror(
                    "Bloqueo de Cobertura",
                    f"Familiar ya registrado bajo la póliza del titular: {duplicado[0]}"
                )
                return

        # Insertar el familiar en la base de datos
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO familiares (cedula, nombres, apellidos, parentesco, fecha_nacimiento, titular_cedula) VALUES (?, ?, ?, ?, ?, ?)",
            (fced, fnom, fape, fpar, ffec, cedula_titular)
        )

        conn.commit()
        conn.close()

        messagebox.showinfo("Éxito", "Familiar indexado correctamente.")

        # Ejecutar la función de refresco y cerrar el modal
        funcion_exito_refrescar()
        pop.destroy()

    # Enlace: al presionar Enter en el último campo, guardar
    txt_fparentesco.bind("<Return>", lambda event: guardar_familiar())

    # Botón para guardar el familiar
    ctk.CTkButton(pop, text="Registrar Familiar", fg_color="green", command=guardar_familiar).pack(pady=20)            