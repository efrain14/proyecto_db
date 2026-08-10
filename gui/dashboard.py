import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
from datetime import datetime
import re
import sys
import os
import shutil

# Asegurar que Python localice la carpeta raíz del proyecto para las importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.conexion import conectar
from logic.consultas import consultar_estado_cliente
from gui.preview_recibo import abrir_previsualizacion_recibo
from gui.reportes_gui import renderizar_grafico_cobranza

# Variable global de control operativo para la sucursal
SEDE_ACTUAL = "A"


# =========================================================================
# VALIDADORES NATIVOS Y FUNCIONES LÓGICAS DE SOPORTE
# =========================================================================

def validar_solo_numeros(char):
    """Permite únicamente el ingreso de dígitos numéricos en los Entry."""
    return char.isdigit() or char == ""


def validar_monto_decimal(texto_entrante):
    """Permite solo números y un solo punto o coma decimal para montos en Bs."""
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
    """Filtro Estricto de Cédulas (RegEx)"""
    patron = r"^[VEve]\d{7,8}$"
    return bool(re.match(patron, cedula_texto.strip()))


def validar_solo_letras(texto):
    """Garantiza que en campos de nombres/apellidos no se escriban números."""
    return texto == "" or texto.replace(" ", "").isalpha()


def validar_monto_tasa(texto_entrante):
    """Filtro de Teclado en Caliente para la Tasa BCV"""
    if texto_entrante == "":
        return True

    try:
        if " " in texto_entrante:
            return False

        float(texto_entrante)
        return True
    except ValueError:
        return False


def formatear_moneda_ve(monto):
    """Conversor de Moneda al Formato de Venezuela (1.250,00 Bs)"""
    texto = f"{monto:,.2f}"
    texto = texto.replace(",", "X")
    texto = texto.replace(".", ",")
    texto = texto.replace("X", ".")
    return f"{texto} Bs"


def convertir_numero(texto):
    """
    Convierte texto numérico a float.
    Soporta:
      - 1234.56
      - 1234,56
      - 1.234,56
    """
    texto = (texto or "").strip()

    if not texto:
        return 0.0

    # Formato tipo 1.234,56
    if "," in texto and "." in texto and texto.rfind(",") > texto.rfind("."):
        texto = texto.replace(".", "").replace(",", ".")

    # Formato tipo 1234,56
    elif "," in texto:
        texto = texto.replace(",", ".")

    return float(texto)


def obtener_monto_usd_plan(tipo_contrato):
    """
    Devuelve el monto en USD de la cuota según el plan.
    Solo existen cuotas de $10 y $20.
    La renovación anual conserva el monto del plan original.
    """
    plan = (tipo_contrato or "").lower()

    if "entierro" in plan:
        return 20.0

    return 10.0


def asegurar_esquema_pagos():
    """
    Prepara la tabla pagos para trabajar con:
    - cuota_numero
    - num_recibo único

    No borra datos. Solo adapta estructura si hace falta.
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
            print("Limpie o corrija los recibos duplicados antes de usar en producción.")

        conn.close()

    except Exception as e:
        print(f"Aviso al preparar esquema de pagos: {e}")


def obtener_siguiente_recibo(cursor):
    """
    Devuelve el próximo número de recibo único.
    Usa MAX(num_recibo) + 1.
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
    Calcula el número de cuota que se está pagando.
    """
    plan = (tipo_contrato or "").lower()

    if total_cuotas <= 0:
        return 1

    if "24 meses" in plan:
        return min(24, total_cuotas)

    if total_cuotas > 24:
        return ((total_cuotas - 24) % 12) or 12

    return (total_cuotas % 12) or 12


def calcular_edad_exacta(fecha_str):
    """Calcula los años exactos comparando la fecha con barras diagonales."""
    try:
        if len(fecha_str) != 10:
            return None

        fn = datetime.strptime(fecha_str, "%d/%m/%Y")
        h = datetime.now()

        return h.year - fn.year - ((h.month, h.day) < (fn.month, fn.day))
    except:
        return None


def vincular_salto_enter(widget_actual, widget_siguiente):
    """Permite al operador avanzar de casilla usando la tecla Enter."""
    widget_actual.bind("<Return>", lambda e: widget_siguiente.focus())


def generar_siguiente_contrato():
    """Genera el próximo código de contrato del sistema."""
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
# INTERFAZ GRÁFICA PRINCIPAL (DASHBOARD)
# =========================================================================

def mostrar_dashboard(usuario_actual="admin"):
    # Preparar tabla de pagos para recibos únicos y cuota_numero
    asegurar_esquema_pagos()

    # Consultar el rol del usuario autenticado
    conn_u = conectar()
    cursor_u = conn_u.cursor()
    cursor_u.execute("SELECT rol FROM usuarios WHERE usuario = ?", (usuario_actual,))
    res_u = cursor_u.fetchone()
    conn_u.close()

    rol_usuario = (res_u[0] if res_u and res_u[0] else "operador").lower()
    es_admin = (rol_usuario == "admin" or usuario_actual == "admin")

    # 1. Crear la ventana principal
    ventana = ctk.CTk()
    ventana.title(f"Sistema Funerario - Panel de Control (Sede {SEDE_ACTUAL} | Usuario: {usuario_actual} [{rol_usuario.upper()}])")
    ventana.geometry("1150x850")

    # Registrar la regla de validación en la ventana activa
    v_numeros_puro = ventana.register(validar_solo_numeros)
    v_letras = ventana.register(validar_solo_letras)
    v_monto_decimal = ventana.register(validar_monto_decimal)

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

    pestanas = ctk.CTkTabview(ventana, width=1110, height=800)
    pestanas.pack(pady=10, padx=10, fill="both", expand=True)

    tab_clientes = pestanas.add("Registro de Clientes")
    tab_edicion = pestanas.add("Edición de Titulares y Afiliados")
    tab_pagos = pestanas.add("Control de Pagos y Estado")
    tab_reportes = pestanas.add("Reportes y Estados de Cuenta")

    if es_admin:
        tab_config = pestanas.add("Configuración")

    cedula_titular_edicion = [""]
    cedula_titular_pago = [""]
    proximo_recibo_global = [1]
    tipo_contrato_global = [""]
    procesando_pago = [False]

    # =========================================================================
    # PESTAÑA 1: REGISTRO DE CLIENTES NUEVOS
    # =========================================================================

    frame_form_reg = ctk.CTkFrame(tab_clientes, fg_color="transparent")
    frame_form_reg.grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky="w")

    ctk.CTkLabel(frame_form_reg, text="Cédula Titular (Ej: V12345678):", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_cedula = ctk.CTkEntry(frame_form_reg, width=150, placeholder_text="V12345678")
    txt_cedula.grid(row=1, column=0, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="N° Contrato Anterior (Manual):", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    txt_cont_viejo = ctk.CTkEntry(frame_form_reg, width=180, placeholder_text="Opcional")
    txt_cont_viejo.grid(row=1, column=1, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="N° Contrato Sistema (Auto):", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, sticky="w")
    txt_cont_nuevo = ctk.CTkEntry(
        frame_form_reg,
        width=150,
        fg_color="#1e272e",
        text_color="#2ecc71",
        font=("Arial", 12, "bold")
    )
    txt_cont_nuevo.insert(0, generar_siguiente_contrato())
    txt_cont_nuevo.configure(state="disabled")
    txt_cont_nuevo.grid(row=1, column=2, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Nombres:", font=("Arial", 11, "bold")).grid(row=2, column=0, padx=10, sticky="w")
    txt_nombres = ctk.CTkEntry(frame_form_reg, width=200, validate="key", validatecommand=(v_letras, '%P'))
    txt_nombres.grid(row=3, column=0, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Apellidos:", font=("Arial", 11, "bold")).grid(row=2, column=1, padx=10, sticky="w")
    txt_apellidos = ctk.CTkEntry(frame_form_reg, width=200, validate="key", validatecommand=(v_letras, '%P'))
    txt_apellidos.grid(row=3, column=1, padx=10, pady=(2, 10))

    ctk.CTkLabel(frame_form_reg, text="Fecha Nacimiento:", font=("Arial", 11, "bold")).grid(row=2, column=2, padx=10, sticky="w")
    txt_fecha_nac = ctk.CTkEntry(frame_form_reg, placeholder_text="DD/MM/YYYY", width=150)
    txt_fecha_nac.grid(row=3, column=2, padx=10, pady=(2, 10))

    lbl_edad_titular = ctk.CTkLabel(
        frame_form_reg,
        text=" Edad: -- años ",
        font=("Arial", 11, "bold"),
        fg_color="#f39c12",
        text_color="black",
        corner_radius=6
    )
    lbl_edad_titular.grid(row=5, column=0, padx=10, pady=(2, 10))

    txt_fecha_nac.bind(
        "<KeyRelease>",
        lambda e: lbl_edad_titular.configure(text=f" Edad: {calcular_edad_exacta(txt_fecha_nac.get().strip()) or '--'} años ")
    )

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
            "renovación anual 12 meses"
        ],
        width=230
    )
    combo_contrato.grid(row=7, column=2, padx=10, pady=(2, 10))

    vincular_salto_enter(txt_cedula, txt_cont_viejo)
    vincular_salto_enter(txt_cont_viejo, txt_nombres)
    vincular_salto_enter(txt_nombres, txt_apellidos)
    vincular_salto_enter(txt_apellidos, txt_fecha_nac)
    vincular_salto_enter(txt_fecha_nac, txt_telefono)
    vincular_salto_enter(txt_telefono, txt_recibos_previos)
    vincular_salto_enter(txt_recibos_previos, txt_correo)
    vincular_salto_enter(txt_correo, txt_direccion)

    tabla_frame = ctk.CTkFrame(tab_clientes)
    tabla_frame.grid(row=1, column=0, columnspan=3, pady=10, padx=10, sticky="nsew")

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
    # PESTAÑA 2: EDICIÓN DE TITULARES Y FAMILIARES
    # =========================================================================

    frame_busq_ed = ctk.CTkFrame(tab_edicion, fg_color="transparent")
    frame_busq_ed.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(
        frame_busq_ed,
        text="Buscar Póliza (Cédula o N° Contratos):",
        font=("Arial", 11, "bold")
    ).grid(row=0, column=0, padx=10, sticky="w")

    txt_busq_ed = ctk.CTkEntry(frame_busq_ed, width=380, placeholder_text="Ingrese cédula V/E o código de contrato...")
    txt_busq_ed.grid(row=1, column=0, padx=10, pady=5)

    lbl_fecha_contrato_ed = ctk.CTkLabel(
        frame_busq_ed,
        text="fecha de contrato: --/--/----",
        font=("Arial", 12, "italic", "bold"),
        text_color="#3498db"
    )
    lbl_fecha_contrato_ed.grid(row=1, column=2, padx=20)

    frame_campos_ed = ctk.CTkFrame(tab_edicion)
    frame_campos_ed.pack(pady=5, padx=10, fill="x")

    ctk.CTkLabel(frame_campos_ed, text="Modificar Nombres:", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_ed_nom = ctk.CTkEntry(frame_campos_ed, width=180, validate="key", validatecommand=(v_letras, '%P'))
    txt_ed_nom.grid(row=1, column=0, padx=10, pady=5)

    ctk.CTkLabel(frame_campos_ed, text="Modificar Apellidos:", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    txt_ed_ape = ctk.CTkEntry(frame_campos_ed, width=180, validate="key", validatecommand=(v_letras, '%P'))
    txt_ed_ape.grid(row=1, column=1, padx=10, pady=5)

    ctk.CTkLabel(frame_campos_ed, text="Modificar Teléfono:", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, sticky="w")
    txt_ed_tel = ctk.CTkEntry(frame_campos_ed, width=150)
    txt_ed_tel.grid(row=1, column=2, padx=10, pady=5)

    ctk.CTkLabel(frame_campos_ed, text="Modificar Correo:", font=("Arial", 11, "bold")).grid(row=2, column=0, padx=10, sticky="w")
    txt_ed_corr = ctk.CTkEntry(frame_campos_ed, width=220)
    txt_ed_corr.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    ctk.CTkLabel(frame_campos_ed, text="Modificar Dirección de Habitación:", font=("Arial", 11, "bold")).grid(row=2, column=2, padx=10, sticky="w")
    txt_ed_dir = ctk.CTkEntry(frame_campos_ed, width=350)
    txt_ed_dir.grid(row=3, column=2, padx=10, pady=5, sticky="w")

    vincular_salto_enter(txt_ed_nom, txt_ed_ape)
    vincular_salto_enter(txt_ed_ape, txt_ed_tel)
    vincular_salto_enter(txt_ed_tel, txt_ed_corr)
    vincular_salto_enter(txt_ed_corr, txt_ed_dir)

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

    frame_busq_pagos = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_busq_pagos.pack(pady=10, padx=10, fill="x")

    ctk.CTkLabel(
        frame_busq_pagos,
        text="Buscar Titular (Cédula o Contrato Viejo/Nuevo):",
        font=("Arial", 11, "bold")
    ).grid(row=0, column=0, padx=10, sticky="w")

    txt_busqueda_ced = ctk.CTkEntry(frame_busq_pagos, width=280, placeholder_text="Cédula, Contrato Viejo o Contrato Nuevo...")
    txt_busqueda_ced.grid(row=1, column=0, padx=10, pady=5)

    frame_info_contratos = ctk.CTkFrame(tab_pagos, fg_color="#1e272e")
    frame_info_contratos.pack(pady=5, padx=20, fill="x")

    lbl_cv_display = ctk.CTkLabel(frame_info_contratos, text="Contrato Viejo: --", font=("Arial", 11, "bold"), text_color="#f1c40f")
    lbl_cv_display.grid(row=0, column=0, padx=15, pady=5)

    lbl_cn_display = ctk.CTkLabel(frame_info_contratos, text="Contrato Sistema: --", font=("Arial", 11, "bold"), text_color="#2ecc71")
    lbl_cn_display.grid(row=0, column=1, padx=15, pady=5)

    lbl_recibo_next = ctk.CTkLabel(
        frame_info_contratos,
        text="N° Recibo Asignado a Procesar: --",
        font=("Arial", 11, "bold"),
        text_color="#e67e22"
    )
    lbl_recibo_next.grid(row=0, column=2, padx=15, pady=5)

    lbl_nombre_clie = ctk.CTkLabel(tab_pagos, text="Cliente: Seleccione un titular", font=("Arial", 13, "bold"), justify="left")
    lbl_nombre_clie.pack(pady=5, padx=20, anchor="w")

    lbl_aviso_morosidad = ctk.CTkLabel(tab_pagos, text="ESTADO: --", font=("Arial", 14, "bold"), text_color="grey")
    lbl_aviso_morosidad.pack(pady=2, padx=20, anchor="w")

    frame_ultimo_pago = ctk.CTkFrame(tab_pagos, border_width=2, border_color="#1f538d")
    frame_ultimo_pago.pack(pady=5, padx=20, fill="x")

    lbl_up_detalles = ctk.CTkLabel(frame_ultimo_pago, text="Historial de Cobros: Sin registrar búsquedas.", font=("Arial", 12, "italic"))
    lbl_up_detalles.pack(pady=5, padx=10, anchor="w")

    # -------------------------------------------------------------------------
    # FRAME DE COBRO ACTUALIZADO CON MONTO BS Y DATOS BANCARIOS
    # -------------------------------------------------------------------------

    frame_cobro = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_cobro.pack(pady=10, padx=20, fill="x")

    # --- FILA 0: Tasa, Forma de Pago, Monto en Bs y Etiqueta de Cálculo ---

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

    # Función para controlar la activación de campos bancarios
    def alternar_campos_bancarios_cobro(metodo):
        """Habilita los bancos y referencia solo si es Transferencia o Pago Móvil."""
        es_bancario = metodo in ["Transferencia", "Pago Móvil"]
        estado = "normal" if es_bancario else "disabled"

        txt_banco_origen.configure(state=estado)
        txt_banco_destino.configure(state=estado)
        txt_num_referencia.configure(state=estado)

        if not es_bancario:
            txt_banco_origen.delete(0, "end")
            txt_banco_destino.delete(0, "end")
            txt_num_referencia.delete(0, "end")

    ctk.CTkLabel(frame_cobro, text="Forma de Pago:", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")

    combo_forma_pago = ctk.CTkComboBox(
        frame_cobro,
        values=["Efectivo USD", "Efectivo Bs", "Transferencia", "Pago Móvil", "Tarjeta de debito"],
        width=160,
        command=alternar_campos_bancarios_cobro
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

    # Etiqueta plana sin borde para el cálculo
    lbl_calculo_bs = ctk.CTkLabel(frame_cobro, text="Monto a pagar: 0,00 Bs", font=("Arial", 13, "bold", "italic"), fg_color="transparent")
    lbl_calculo_bs.grid(row=1, column=3, padx=15, pady=5, sticky="w")

    # --- FILA 1: Banco Pagador, Banco Receptor y N° Operación ---

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

    def ejecutar_pago():
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

            # Capturar datos del formulario
            metodo = combo_forma_pago.get()

            b_origen = txt_banco_origen.get().strip().upper() if metodo in ["Transferencia", "Pago Móvil"] else ""
            b_destino = txt_banco_destino.get().strip().upper() if metodo in ["Transferencia", "Pago Móvil"] else ""
            num_op = txt_num_referencia.get().strip() if metodo in ["Transferencia", "Pago Móvil"] else ""

            # -------------------------------------------------------------------------
            # VALIDACIÓN DE MONTO
            # -------------------------------------------------------------------------

            try:
                monto_ingresado = convertir_numero(txt_monto_bs.get())
            except ValueError:
                messagebox.showwarning("Monto Inválido", "Por favor, ingrese un monto cobrado válido.")
                txt_monto_bs.focus()
                return

            # -------------------------------------------------------------------------
            # VALIDACIÓN DE TASA
            # -------------------------------------------------------------------------

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

            # -------------------------------------------------------------------------
            # VALIDACIÓN DE COINCIDENCIA DE MONTOS
            # -------------------------------------------------------------------------

            usd_plan = obtener_monto_usd_plan(tipo_contrato_global[0])
            monto_esperado = usd_plan * tasa_val_num

            if abs(monto_ingresado - monto_esperado) > 0.05:
                messagebox.showerror(
                    "Diferencia de Montos",
                    f"⚠️ El monto ingresado (Bs. {monto_ingresado:,.2f}) NO coincide con el monto a pagar calculado ({usd_plan:.2f} USD = Bs. {monto_esperado:,.2f}).\n\nPor favor verifique antes de procesar el pago."
                )
                txt_monto_bs.focus()
                return

            # Validar campos bancarios en caso de pago electrónico
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

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM pagos
                    WHERE titular_cedula = ?
                """, (cedula_actual,))

                pagos_sistema_previos = cursor.fetchone()[0]

                total_cuotas_nuevo = recibos_previos + pagos_sistema_previos + 1
                cuota_numero = calcular_cuota_numero(plan_actual, total_cuotas_nuevo)

                # Calcular próximo recibo único
                recibo_a_guardar = obtener_siguiente_recibo(cursor)

                # Protección adicional contra duplicados
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

                # Verificar si existe la columna cuota_numero
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
                        recibo_a_guardar,
                        cedula_actual,
                        monto_usd_val,
                        monto_bs_val,
                        tasa_val,
                        metodo,
                        b_origen,
                        b_destino,
                        num_op,
                        cuota_numero
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO pagos (
                            num_recibo, titular_cedula, fecha_pago, monto_usd, monto_bs,
                            tasa_bcv, forma_pago, banco_origen, banco_destino, num_operacion
                        ) VALUES (?, ?, DATE('now'), ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        recibo_a_guardar,
                        cedula_actual,
                        monto_usd_val,
                        monto_bs_val,
                        tasa_val,
                        metodo,
                        b_origen,
                        b_destino,
                        num_op
                    ))

                conn.commit()

                # -------------------------------------------------------------------------
                # LÓGICA DE RENOVACIÓN AUTOMÁTICA DE PLANES
                # -------------------------------------------------------------------------

                # CASO 1: Planes PPA de 24 meses que alcanzan la cuota 24
                if "24 meses" in plan_actual.lower() and total_cuotas_nuevo == 24:

                    plan_actual_lower = plan_actual.lower()

                    if "entierro" in plan_actual_lower:
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

                # CASO 2: Plan RENOVACION ANUAL 12 MESES completando un ciclo de 12 cuotas
                elif "renovacion anual" in plan_actual.lower() and total_cuotas_nuevo > 24 and ((total_cuotas_nuevo - 24) % 12 == 0):
                    messagebox.showinfo(
                        "¡Renovación Anual Completada!",
                        f"🎉 El titular ha completado las 12 cuotas del ciclo de Renovación Anual.\n\n"
                        f"El contrato continuará activo para el siguiente período de 12 meses."
                    )

                # Datos para el recibo
                cursor.execute("""
                    SELECT nombres, apellidos
                    FROM titulares
                    WHERE cedula = ?
                """, (cedula_actual,))

                tit_datos = cursor.fetchone()
                nombre_cliente_limpio = f"{tit_datos[0]} {tit_datos[1]}".upper() if tit_datos else cedula_actual

                if "24 meses" in plan_actual.lower() or "ppa" in plan_actual.lower():
                    cuotas_rest = max(0, 24 - cuota_numero)
                    cuota_str = f"Cuota #{cuota_numero} de 24 (Canceladas: {cuota_numero}/24 | Restantes: {cuotas_rest})"
                else:
                    cuotas_rest = max(0, 12 - cuota_numero)
                    cuota_str = f"Ciclo Renovación -> Cuota #{cuota_numero} de 12 (Canceladas: {cuota_numero}/12 | Restantes: {cuotas_rest})"

                datos_recibo = {
                    "num_recibo": recibo_a_guardar,
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "cedula": cedula_actual,
                    "nombre_titular": nombre_cliente_limpio,
                    "cuota_info": cuota_str,
                    "num_contrato": lbl_cn_display.cget("text").replace("Contrato Sistema: ", ""),
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

                # Refrescar la pantalla antes de intentar abrir el recibo.
                # Esto evita que la interfaz quede desactualizada si el PDF falla.
                try:
                    buscar_y_calcular_pagos()
                except Exception as e_refresh:
                    print(f"Aviso al refrescar la pantalla: {e_refresh}")

                # Intentar abrir el recibo.
                # Si falla el PDF, no se debe mostrar que el pago falló.
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

    # -------------------------------------------------------------------------
    # 2. CREACIÓN DEL BOTÓN
    # -------------------------------------------------------------------------

    btn_procesar_pago = ctk.CTkButton(
        frame_cobro,
        text="Procesar Pago",
        command=ejecutar_pago,
        fg_color="#1f538d",
        font=("Arial", 12, "bold")
    )
    btn_procesar_pago.grid(row=3, column=3, padx=10, pady=5)

    alternar_campos_bancarios_cobro(combo_forma_pago.get())

    # -------------------------------------------------------------------------
    # 3. NAVEGACIÓN CON TECLA ENTER
    # -------------------------------------------------------------------------

    vincular_salto_enter(txt_tasa, combo_forma_pago)
    vincular_salto_enter(combo_forma_pago, txt_monto_bs)

    def saltar_desde_monto(_):
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
    # FUNCIONES GENERALES DE ACCIÓN AUTOMÁTICA
    # =========================================================================

    def refrescar_tabla_familiares(ced_t):
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
        ced = txt_cedula.get().strip().upper()
        c_viejo = txt_cont_viejo.get().strip()
        c_nuevo = txt_cont_nuevo.get().strip()
        nom = txt_nombres.get().strip().lower()
        ape = txt_apellidos.get().strip().lower()
        f_nac = txt_fecha_nac.get().strip()
        tel = txt_telefono.get().strip()
        corr = txt_correo.get().strip().lower()
        dir_hab = txt_direccion.get().strip().lower()
        tipo_c = combo_contrato.get()
        recibos_raw = txt_recibos_previos.get().strip()

        try:
            r_previos = int(recibos_raw) if recibos_raw else 0
        except:
            r_previos = 0

        if not validar_mascara_cedula(ced):
            messagebox.showwarning(
                "Formato Requerido",
                "Cédula del titular inválida.\nDebe comenzar con V o E seguido de 7 a 8 números.\nEjemplo: V12345678"
            )
            txt_cedula.focus()
            return

        if not nom or not ape or not f_nac:
            messagebox.showwarning(
                "Campos Requeridos",
                "Nombres, Apellidos y Fecha de Nacimiento son campos obligatorios."
            )
            return

        try:
            conn = conectar()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO titulares (
                    cedula, contrato_viejo, contrato_nuevo, nombres, apellidos, fecha_nacimiento,
                    telefono, correo, direccion, tipo_contrato, fecha_inicio, recibos_previos
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ced,
                c_viejo,
                c_nuevo,
                nom,
                ape,
                f_nac,
                tel,
                corr,
                dir_hab,
                tipo_c,
                datetime.now().strftime("%d/%m/%Y"),
                r_previos
            ))

            conn.commit()
            conn.close()

            messagebox.showinfo("Éxito", f"Titular registrado con el Contrato Sistema: {c_nuevo}")

            btn_add_fam.configure(state="normal")
            refrescar_tabla_familiares(ced)

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
        """Resetea el formulario de la Pestaña 1 para ingresar un nuevo contrato."""
        txt_cedula.delete(0, "end")
        txt_cont_viejo.delete(0, "end")
        txt_nombres.delete(0, "end")
        txt_apellidos.delete(0, "end")
        txt_fecha_nac.delete(0, "end")
        txt_telefono.delete(0, "end")
        txt_recibos_previos.delete(0, "end")
        txt_correo.delete(0, "end")
        txt_direccion.delete(0, "end")

        combo_contrato.set("PPA velación 24 meses")

        lbl_edad_titular.configure(text=" Edad: -- años ")

        txt_cont_nuevo.configure(state="normal")
        txt_cont_nuevo.delete(0, "end")
        txt_cont_nuevo.insert(0, generar_siguiente_contrato())
        txt_cont_nuevo.configure(state="disabled")

        for item in tabla.get_children():
            tabla.delete(item)

        btn_add_fam.configure(state="disabled")
        txt_cedula.focus()

    def cargar_datos_edicion():
        crit = txt_busq_ed.get().strip().upper()

        if not crit:
            return

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cedula, telefono, correo, direccion, nombres, apellidos, fecha_inicio FROM titulares 
            WHERE cedula = ? OR UPPER(contrato_viejo) = ? OR UPPER(contrato_nuevo) = ?
            OR cedula IN (SELECT titular_cedula FROM familiares WHERE UPPER(cedula) = ?)
        """, (crit, crit, crit, crit))

        res = cursor.fetchone()

        if res:
            cedula_titular_edicion[0] = res[0]

            for txt, val in [
                (txt_ed_nom, res[4]),
                (txt_ed_ape, res[5]),
                (txt_ed_tel, res[1]),
                (txt_ed_corr, res[2]),
                (txt_ed_dir, res[3])
            ]:
                txt.delete(0, "end")
                txt.insert(0, val.title() if isinstance(val, str) and txt in [txt_ed_nom, txt_ed_ape] else (val or ""))

            lbl_fecha_contrato_ed.configure(text=f"fecha de contrato  {res[6] or '--/--/----'}")

            for item in tabla_ed.get_children():
                tabla_ed.delete(item)

            cursor.execute(
                "SELECT id, cedula, nombres, apellidos, parentesco, fecha_nacimiento FROM familiares WHERE titular_cedula = ?",
                (res[0],)
            )

            for f in cursor.fetchall():
                edad_calc = f"{calcular_edad_exacta(f[5])} años" if f[5] else "N/A"
                tabla_ed.insert("", "end", values=(f[0], f[1], f[2].title(), f[3].title(), f[4].title(), f[5] or "N/A", edad_calc))

            for b in [btn_actualizar, btn_retirar_fam, btn_add_fam_ed]:
                b.configure(state="normal")

            txt_ed_nom.focus()

        else:
            messagebox.showerror("No Localizado", "No se encontró ningún contrato asociado al dato ingresado.")

        conn.close()

    def buscar_y_calcular_pagos():
        ced = txt_busqueda_ced.get().strip().upper()

        if not ced:
            return

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT nombres, apellidos, contrato_viejo, contrato_nuevo, recibos_previos, tipo_contrato, cedula FROM titulares 
            WHERE cedula=? OR UPPER(contrato_viejo)=? OR UPPER(contrato_nuevo)=?
            OR cedula IN (SELECT titular_cedula FROM familiares WHERE UPPER(cedula) = ?)
        """, (ced, ced, ced, ced))

        res = cursor.fetchone()

        if res:
            cedula_real = res[6]
            cedula_titular_pago[0] = cedula_real
            tipo_contrato_global[0] = res[5]
            recibos_previos = res[4]

            txt_tasa.configure(state="normal")
            txt_tasa.delete(0, "end")

            cursor.execute("SELECT COUNT(*) FROM pagos WHERE titular_cedula = ?", (cedula_real,))
            pagos_sistema = cursor.fetchone()[0]

            total_pagados = recibos_previos + pagos_sistema

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
            txt_tasa.focus()

        else:
            messagebox.showerror("No Encontrado", "No se localizó ningún contrato asociado al dato ingresado.")

            cedula_titular_pago[0] = ""
            tipo_contrato_global[0] = ""

            txt_tasa.configure(state="disabled")
            btn_procesar_pago.configure(state="disabled")

        conn.close()

    def actualizar_calculo_bolivares(*args):
        try:
            tasa_texto = txt_tasa.get().strip()

            if not tasa_texto:
                lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")
                return

            tasa = convertir_numero(tasa_texto)

            usd = obtener_monto_usd_plan(tipo_contrato_global[0])
            monto_bs = usd * tasa

            lbl_calculo_bs.configure(text=f"Monto a pagar ({usd:.0f} USD): {formatear_moneda_ve(monto_bs)}")

        except:
            lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")

    txt_tasa.bind("<KeyRelease>", actualizar_calculo_bolivares)

    def ejecutar_guardar_cambios_titular():
        nom = txt_ed_nom.get().strip().lower()
        ape = txt_ed_ape.get().strip().lower()
        tel = txt_ed_tel.get().strip()
        corr = txt_ed_corr.get().strip().lower()
        dir_h = txt_ed_dir.get().strip().lower()
        ced = cedula_titular_edicion[0]

        if not nom or not ape:
            messagebox.showwarning("Error", "Campos de texto obligatorios vacíos.")
            return

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE titulares SET nombres=?, apellidos=?, telefono=?, correo=?, direccion=? WHERE cedula=?",
            (nom, ape, tel, corr, dir_h, ced)
        )

        conn.commit()
        conn.close()

        messagebox.showinfo("Éxito", "Historial modificado con éxito.")
        cargar_datos_edicion()

    def ejecutar_retirar_familiar():
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
    # ENLACES DIRECTOS Y BOTONES FÍSICOS
    # =========================================================================

    # 1. Enlaces de la Pestaña de Control de Pagos
    btn_buscar = ctk.CTkButton(frame_busq_pagos, text="Verificar Estado", width=120, command=buscar_y_calcular_pagos)
    btn_buscar.grid(row=1, column=1, padx=10, pady=5)

    txt_busqueda_ced.bind("<Return>", lambda e: buscar_y_calcular_pagos())

    # 2. Enlace para la casilla de búsqueda en la Pestaña de Edición
    txt_busq_ed.bind("<Return>", lambda e: cargar_datos_edicion())

    # 3. Botones de la Pestaña de Registro de Clientes
    frame_botones_registro = ctk.CTkFrame(tab_clientes, fg_color="transparent")
    frame_botones_registro.grid(row=2, column=0, columnspan=4, pady=15, padx=10, sticky="ew")

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

    # 4. Estructura de botones de la Pestaña de Edición
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

    btn_buscar_ed = ctk.CTkButton(frame_busq_ed, text="Buscar", width=100, command=cargar_datos_edicion)
    btn_buscar_ed.grid(row=1, column=1, padx=10, pady=5)

    ctk.CTkButton(frame_botones_ed, text="Salir", fg_color="#d35400", command=ventana.destroy).grid(row=0, column=3, padx=20)

    frame_acciones_p = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_acciones_p.pack(pady=15, padx=20, fill="x")

    ctk.CTkButton(frame_acciones_p, text="Salir", fg_color="#d35400", command=ventana.destroy).grid(row=0, column=1, padx=20)

    # =========================================================================
    # PESTAÑA 4: REPORTES Y ESTADOS DE CUENTA
    # =========================================================================

    lbl_titulo_rep = ctk.CTkLabel(tab_reportes, text="📊 Resumen Estadístico de Cobranzas", font=("Arial", 16, "bold"))
    lbl_titulo_rep.pack(pady=(10, 5), padx=20, anchor="w")

    frame_grafico = ctk.CTkFrame(tab_reportes, fg_color="#2b2b2b")
    frame_grafico.pack(pady=10, padx=20, fill="both", expand=True)

    def cargar_reporte_cobros():
        for widget in frame_grafico.winfo_children():
            widget.destroy()

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT strftime('%m/%Y', fecha_pago) as mes, SUM(monto_usd)
            FROM pagos
            GROUP BY mes
            ORDER BY fecha_pago ASC
            LIMIT 6
        """)

        filas = cursor.fetchall()
        conn.close()

        datos_meses = {}

        if filas:
            for mes, monto in filas:
                datos_meses[mes or "S/F"] = monto or 0.0
        else:
            datos_meses = {"Ene": 0, "Feb": 0, "Mar": 0}

        try:
            renderizar_grafico_cobranza(frame_grafico, datos_meses)
        except Exception as ex:
            ctk.CTkLabel(frame_grafico, text=f"No se pudo cargar el gráfico: {ex}", font=("Arial", 12)).pack(pady=20)

    # =========================================================================
    # PESTAÑA 5: CONFIGURACIÓN (Solo Administradores)
    # =========================================================================

    if es_admin:
        lbl_titulo_conf = ctk.CTkLabel(
            tab_config,
            text="⚙️ Panel de Configuración y Seguridad (Administrador)",
            font=("Arial", 16, "bold")
        )
        lbl_titulo_conf.pack(pady=(10, 5), padx=20, anchor="w")

        frame_grid_conf = ctk.CTkFrame(tab_config, fg_color="transparent")
        frame_grid_conf.pack(pady=10, padx=10, fill="both", expand=True)

        # ---------------------------------------------------------------------
        # SECCIÓN 1: RESPALDO DE BASE DE DATOS A USB / CARPETA
        # ---------------------------------------------------------------------

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

        def ejecutar_respaldo():
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
                    ruta_origen = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'funeraria.db'))
                    shutil.copy2(ruta_origen, destino)

                    messagebox.showinfo(
                        "Respaldo Éxitoso",
                        f"🎉 Copia de seguridad guardada exitosamente en:\n\n{destino}"
                    )

                except Exception as ex:
                    messagebox.showerror("Error de Respaldo", f"No se pudo copiar la base de datos:\n{ex}")

        btn_respaldo = ctk.CTkButton(
            frame_respaldo,
            text="💾 Exportar Copia de Respaldo a USB / Disco",
            fg_color="#27ae60",
            font=("Arial", 12, "bold"),
            height=35,
            command=ejecutar_respaldo
        )
        btn_respaldo.pack(pady=(0, 15), padx=15, anchor="w")

        # ---------------------------------------------------------------------
        # SECCIÓN 2: GESTIÓN DE USUARIOS Y CLAVES
        # ---------------------------------------------------------------------

        frame_usuarios = ctk.CTkFrame(frame_grid_conf)
        frame_usuarios.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            frame_usuarios,
            text="👥 Gestión de Usuarios y Claves de Acceso",
            font=("Arial", 14, "bold"),
            text_color="#f1c40f"
        ).pack(pady=(10, 5), padx=15, anchor="w")

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

        def refrescar_tabla_usuarios():
            for item in tabla_u.get_children():
                tabla_u.delete(item)

            conn = conectar()
            cursor = conn.cursor()

            cursor.execute("SELECT id, usuario, COALESCE(rol, 'operador') FROM usuarios ORDER BY id ASC")

            for u_row in cursor.fetchall():
                tabla_u.insert("", "end", values=(u_row[0], u_row[1], u_row[2].upper()))

            conn.close()

        def crear_usuario():
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

        btn_add_u = ctk.CTkButton(frame_form_u, text="➕ Agregar Usuario", fg_color="#1f538d", command=crear_usuario)
        btn_add_u.grid(row=1, column=4, padx=15, pady=5)

        # Tabla de Usuarios registrados
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

        frame_u_acciones = ctk.CTkFrame(frame_usuarios, fg_color="transparent")
        frame_u_acciones.pack(pady=(5, 10), padx=15, fill="x")

        def cambiar_clave_usuario():
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

        ctk.CTkButton(frame_u_acciones, text="🔑 Cambiar Contraseña", fg_color="#e67e22", command=cambiar_clave_usuario).pack(side="left", padx=5)
        ctk.CTkButton(frame_u_acciones, text="❌ Eliminar Usuario", fg_color="#c0392b", command=eliminar_usuario).pack(side="left", padx=5)
        ctk.CTkButton(frame_u_acciones, text="Salir del Sistema", fg_color="#d35400", command=ventana.destroy).pack(side="right", padx=5)

        refrescar_tabla_usuarios()

    # =========================================================================
    # MOTOR DE LIMPIEZA INTER-PESTAÑAS
    # =========================================================================

    def gestionar_limpieza_pestanas():
        txt_busq_ed.delete(0, "end")
        lbl_fecha_contrato_ed.configure(text="fecha de contrato: --/--/----")

        for t in [txt_ed_nom, txt_ed_ape, txt_ed_tel, txt_ed_corr, txt_ed_dir]:
            t.delete(0, "end")

        for item in tabla_ed.get_children():
            tabla_ed.delete(item)

        for b in [btn_actualizar, btn_retirar_fam, btn_add_fam_ed]:
            b.configure(state="disabled")

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

    pestanas.configure(command=gestionar_limpieza_pestanas)

    ventana.mainloop()


# =========================================================================
# COMPONENTE MODAL: REGISTRO DE AFILIADOS
# =========================================================================

def abrir_modulo_familiares(ventana_padre, cedula_titular, v_let, funcion_exito_refrescar):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM familiares WHERE titular_cedula = ?", (cedula_titular,))
    cantidad = cursor.fetchone()[0]

    conn.close()

    if cantidad >= 8:
        messagebox.showwarning("Límite Alcanzado", "Este contrato ya cuenta con los 8 familiares permitidos.")
        return

    pop = ctk.CTkToplevel(ventana_padre)
    pop.title("Agregar Familiar")
    pop.geometry("450x480")
    pop.grab_set()

    ctk.CTkLabel(
        pop,
        text="Cédula Familiar (V/E + Números, o vacío si es menor):",
        font=("Arial", 11, "bold")
    ).pack(pady=(10, 2), padx=20, anchor="w")

    txt_fcedula = ctk.CTkEntry(pop, width=280, placeholder_text="Ej: V25111222")
    txt_fcedula.pack(pady=2, padx=20)

    ctk.CTkLabel(pop, text="Nombres:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_fnombre = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fnombre.pack(pady=2, padx=20)

    ctk.CTkLabel(pop, text="Apellidos:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_fapellido = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fapellido.pack(pady=2, padx=20)

    ctk.CTkLabel(pop, text="Fecha Nacimiento Afiliado:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_ffecha = ctk.CTkEntry(pop, placeholder_text="DD/MM/YYYY", width=280)
    txt_ffecha.pack(pady=2, padx=20)

    ctk.CTkLabel(pop, text="Parentesco con el Titular:", font=("Arial", 11, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
    txt_fparentesco = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fparentesco.pack(pady=2, padx=20)

    txt_fcedula.focus_set()

    vincular_salto_enter(txt_fcedula, txt_fnombre)
    vincular_salto_enter(txt_fnombre, txt_fapellido)
    vincular_salto_enter(txt_fapellido, txt_ffecha)
    vincular_salto_enter(txt_ffecha, txt_fparentesco)

    def guardar_familiar():
        fced_raw = txt_fcedula.get().strip().upper()
        fced = fced_raw if fced_raw else "MENOR"

        fnom = txt_fnombre.get().strip().lower()
        fape = txt_fapellido.get().strip().lower()
        fpar = txt_fparentesco.get().strip().lower()
        ffec = txt_ffecha.get().strip()

        if fced != "MENOR" and not validar_mascara_cedula(fced):
            messagebox.showwarning("Formato Obligatorio", "Cédula del familiar inválida.")
            txt_fcedula.focus()
            return

        if not fnom or not fape or not fpar or not ffec:
            messagebox.showwarning("Campos Vacíos", "Todos los campos son obligatorios.")
            return

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

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO familiares (cedula, nombres, apellidos, parentesco, fecha_nacimiento, titular_cedula) VALUES (?, ?, ?, ?, ?, ?)",
            (fced, fnom, fape, fpar, ffec, cedula_titular)
        )

        conn.commit()
        conn.close()

        messagebox.showinfo("Éxito", "Familiar indexado correctamente.")

        funcion_exito_refrescar()
        pop.destroy()

    txt_fparentesco.bind("<Return>", lambda event: guardar_familiar())

    ctk.CTkButton(pop, text="Registrar Familiar", fg_color="green", command=guardar_familiar).pack(pady=20)