import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
import re  # Módulo para validaciones de expresiones regulares (máscaras estrictas)
import sys
import os

# Asegurar que Python localice la carpeta raíz del proyecto para las importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.conexion import conectar
from logic.consultas import consultar_estado_cliente

# Variable global de control operativo para la sucursal
SEDE_ACTUAL = "A" 

# =========================================================================
# VALIDADORES NATIVOS Y FUNCIONES LÓGICAS DE SOPORTE
# =========================================================================

def validar_mascara_cedula(cedula_texto):
    """
    Filtro Estricto de Cédulas (RegEx):
    - Debe iniciar con la letra 'V' o 'E' (mayúscula o minúscula).
    - Debe continuar con un mínimo de 7 números y un máximo de 8 números.
    - No permite espacios ni caracteres especiales.
    """
    patron = r"^[VEve]\d{7,8}$"
    return bool(re.match(patron, cedula_texto.strip()))

def validar_solo_letras(texto):
    """Garantiza que en campos de nombres/apellidos no se escriban números."""
    return texto == "" or texto.replace(" ", "").isalpha()

def validar_monto_tasa(texto_entrante):
    """
    Filtro de Teclado en Caliente para la Tasa BCV:
    - Retorna True si lo digitado es válido, de lo contrario bloquea la tecla.
    - Permite dejar el campo vacío (cuando el usuario borra).
    - No permite espacios, letras ni múltiples puntos decimales.
    """
    if texto_entrante == "": 
        return True
    try:
        if " " in texto_entrante: 
            return False
        float(texto_entrante)  # Si Python logra convertirlo a flotante, la entrada es numérica
        return True
    except ValueError:
        return False

def formatear_moneda_ve(monto):
    """
    Conversor de Moneda al Formato de Venezuela:
    - Convierte un número flotante (Ej: 15400.5) en un string legible.
    - Coloca puntos (.) para separar los miles y una coma (,) para los decimales.
    - Resultado final: "15.400,50 Bs."
    """
    texto = f"{monto:,.2f}"
    texto = texto.replace(",", "X")  # Guardado temporal de la coma americana
    texto = texto.replace(".", ",")  # Cambiamos punto decimal por coma venezolana
    texto = texto.replace("X", ".")  # Colocamos el punto en los separadores de miles
    return f"{texto} Bs"

def calcular_edad_exacta(fecha_str):
    """Calcula los años exactos comparando la fecha de nacimiento con la del sistema."""
    try:
        if len(fecha_str) != 10: return None
        fn = datetime.strptime(fecha_str, "%d/%m/%Y")
        h = datetime.now()
        return h.year - fn.year - ((h.month, h.day) < (fn.month, fn.day))
    except:
        return None

def vincular_salto_enter(widget_actual, widget_siguiente):
    """Permite al operador avanzar de casilla de manera fluida usando la tecla Enter."""
    widget_actual.bind("<Return>", lambda e: widget_siguiente.focus())

def generar_siguiente_contrato():
    """Genera de forma correlativa y automática el próximo código de contrato del sistema."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT contrato_nuevo FROM titulares WHERE contrato_nuevo LIKE ? ORDER BY contrato_nuevo DESC LIMIT 1", (f"{SEDE_ACTUAL}-%",))
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

def mostrar_dashboard():
    ventana = ctk.CTk()
    ventana.title(f"Sistema Funerario - Panel de Control (Sede {SEDE_ACTUAL})")
    ventana.geometry("1150x850")
    
    # Registrar los validadores de entrada dentro de la instancia de Tkinter
    v_letras = ventana.register(validar_solo_letras)
    v_tasa_num = ventana.register(validar_monto_tasa)
    
    # Configuración estética para las tablas de visualización de datos (Treeview)
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#2a2a2a", foreground="white", fieldbackground="#2a2a2a", rowheight=25)
    style.map("Treeview", background=[('selected', '#1f538d')])
    style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=("Arial", 10, "bold"))

    # Contenedor principal de pestañas del sistema
    pestanas = ctk.CTkTabview(ventana, width=1110, height=800)
    pestanas.pack(pady=10, padx=10, fill="both", expand=True)
    
    tab_clientes = pestanas.add("Registro de Clientes")
    tab_edicion = pestanas.add("Edición de Titulares y Afiliados")
    tab_pagos = pestanas.add("Control de Pagos y Estado")
    
    # Memorias dinámicas de intercambio de datos entre funciones
    cedula_titular_edicion = [""]
    proximo_recibo_global = [1]
    tipo_contrato_global = [""]

    # =========================================================================
    # PESTAÑA 1: REGISTRO DE CLIENTES NUEVOS
    # =========================================================================
    frame_form_reg = ctk.CTkFrame(tab_clientes, fg_color="transparent")
    frame_form_reg.grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky="w")
    
    ctk.CTkLabel(frame_form_reg, text="Cédula Titular (Ej: V12345678):", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_cedula = ctk.CTkEntry(frame_form_reg, width=150, placeholder_text="V12345678")
    txt_cedula.grid(row=1, column=0, padx=10, pady=(2,10))
    
    ctk.CTkLabel(frame_form_reg, text="N° Contrato Anterior (Manual):", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    txt_cont_viejo = ctk.CTkEntry(frame_form_reg, width=180, placeholder_text="Opcional")
    txt_cont_viejo.grid(row=1, column=1, padx=10, pady=(2,10))
    
    ctk.CTkLabel(frame_form_reg, text="N° Contrato Sistema (Auto):", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, sticky="w")
    txt_cont_nuevo = ctk.CTkEntry(frame_form_reg, width=150, fg_color="#1e272e", text_color="#2ecc71", font=("Arial", 12, "bold"))
    txt_cont_nuevo.insert(0, generar_siguiente_contrato())
    txt_cont_nuevo.configure(state="disabled")
    txt_cont_nuevo.grid(row=1, column=2, padx=10, pady=(2,10))

    ctk.CTkLabel(frame_form_reg, text="Nombres:", font=("Arial", 11, "bold")).grid(row=2, column=0, padx=10, sticky="w")
    txt_nombres = ctk.CTkEntry(frame_form_reg, width=200, validate="key", validatecommand=(v_letras, '%P'))
    txt_nombres.grid(row=3, column=0, padx=10, pady=(2,10))
    
    ctk.CTkLabel(frame_form_reg, text="Apellidos:", font=("Arial", 11, "bold")).grid(row=2, column=1, padx=10, sticky="w")
    txt_apellidos = ctk.CTkEntry(frame_form_reg, width=200, validate="key", validatecommand=(v_letras, '%P'))
    txt_apellidos.grid(row=3, column=1, padx=10, pady=(2,10))
    
    ctk.CTkLabel(frame_form_reg, text="Fecha Nacimiento:", font=("Arial", 11, "bold")).grid(row=2, column=2, padx=10, sticky="w")
    txt_fecha_nac = ctk.CTkEntry(frame_form_reg, placeholder_text="DD/MM/YYYY", width=150)
    txt_fecha_nac.grid(row=3, column=2, padx=10, pady=(2,10))

    lbl_edad_titular = ctk.CTkLabel(frame_form_reg, text=" Edad: -- años ", font=("Arial", 11, "bold"), fg_color="#f39c12", text_color="black", corner_radius=6)
    lbl_edad_titular.grid(row=5, column=0, padx=10, pady=(2,10))
    txt_fecha_nac.bind("<KeyRelease>", lambda e: lbl_edad_titular.configure(text=f" Edad: {calcular_edad_exacta(txt_fecha_nac.get().strip()) or '--'} años "))
    
    ctk.CTkLabel(frame_form_reg, text="Teléfono Contacto:", font=("Arial", 11, "bold")).grid(row=4, column=1, padx=10, sticky="w")
    txt_telefono = ctk.CTkEntry(frame_form_reg, width=200)
    txt_telefono.grid(row=5, column=1, padx=10, pady=(2,10))
    
    # Campo de Recibos Corregido: Se eliminó el "0" precargado para evitar corrupciones de tipeo
    ctk.CTkLabel(frame_form_reg, text="Recibos ya Cancelados (Histórico):", font=("Arial", 11, "bold", "underline"), text_color="#e74c3c").grid(row=4, column=2, padx=10, sticky="w")
    txt_recibos_previos = ctk.CTkEntry(frame_form_reg, width=150, placeholder_text="Ej: 14 (Vacío = 0)")
    txt_recibos_previos.grid(row=5, column=2, padx=10, pady=(2,10))

    ctk.CTkLabel(frame_form_reg, text="Correo Electrónico:", font=("Arial", 11, "bold")).grid(row=6, column=0, padx=10, sticky="w")
    txt_correo = ctk.CTkEntry(frame_form_reg, width=180)
    txt_correo.grid(row=7, column=0, padx=10, pady=(2,10))
    
    ctk.CTkLabel(frame_form_reg, text="Dirección de Habitación:", font=("Arial", 11, "bold")).grid(row=6, column=1, padx=10, sticky="w")
    txt_direccion = ctk.CTkEntry(frame_form_reg, width=200)
    txt_direccion.grid(row=7, column=1, padx=10, pady=(2,10))
    
    ctk.CTkLabel(frame_form_reg, text="Tipo de Contrato:", font=("Arial", 11, "bold")).grid(row=6, column=2, padx=10, sticky="w")
    combo_contrato = ctk.CTkComboBox(frame_form_reg, values=["PPA velación 24 meses", "PPA velación + entierro 24 meses", "renovación anual 12 meses"], width=230)
    combo_contrato.grid(row=7, column=2, padx=10, pady=(2,10))

    # Vinculación correlativa del Enter para agilizar el llenado manual
    vincular_salto_enter(txt_cedula, txt_cont_viejo)
    vincular_salto_enter(txt_cont_viejo, txt_nombres)
    vincular_salto_enter(txt_nombres, txt_apellidos)
    vincular_salto_enter(txt_apellidos, txt_fecha_nac)
    vincular_salto_enter(txt_fecha_nac, txt_telefono)
    vincular_salto_enter(txt_telefono, txt_recibos_previos)
    vincular_salto_enter(txt_recibos_previos, txt_correo)
    vincular_salto_enter(txt_correo, txt_direccion)

    # Tabla visual inferior para listar familiares asociados en caliente
    tabla_frame = ctk.CTkFrame(tab_clientes)
    tabla_frame.grid(row=1, column=0, columnspan=3, pady=10, padx=10, sticky="nsew")
    tabla = ttk.Treeview(tabla_frame, columns=("cedula", "nombres", "apellidos", "parentesco", "f_nac", "edad"), show="headings", height=5)
    for c, t, w in [("cedula", "Cédula", 120), ("nombres", "Nombres", 150), ("apellidos", "Apellidos", 150), ("parentesco", "Parentesco", 120), ("f_nac", "F. Nacimiento", 130), ("edad", "Edad Calculada", 110)]:
        tabla.heading(c, text=t); tabla.column(c, width=w, anchor="center")
    tabla.pack(fill="both", expand=True)

    # =========================================================================
    # PESTAÑA 2: EDICIÓN DE TITULARES Y FAMILIARES
    # =========================================================================
    frame_busq_ed = ctk.CTkFrame(tab_edicion, fg_color="transparent")
    frame_busq_ed.pack(pady=10, padx=10, fill="x")
    
    ctk.CTkLabel(frame_busq_ed, text="Buscar Póliza (Cédula o N° Contratos):", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_busq_ed = ctk.CTkEntry(frame_busq_ed, width=380, placeholder_text="Ingrese cédula V/E o código de contrato...")
    txt_busq_ed.grid(row=1, column=0, padx=10, pady=5)
    
    lbl_fecha_contrato_ed = ctk.CTkLabel(frame_busq_ed, text="fecha de contrato: --/--/----", font=("Arial", 12, "italic", "bold"), text_color="#3498db")
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
    tabla_ed = ttk.Treeview(tabla_ed_frame, columns=("id", "cedula", "nombres", "apellidos", "parentesco", "f_nac", "edad"), show="headings", height=4)
    for c, t, w in [("id", "ID", 60), ("cedula", "Cédula", 110), ("nombres", "Nombres", 150), ("apellidos", "Apellidos", 150), ("parentesco", "Parentesco", 120), ("f_nac", "F. Nacimiento", 120), ("edad", "Edad", 90)]:
        tabla_ed.heading(c, text=t); tabla_ed.column(c, width=w, anchor="center")
    tabla_ed.pack(fill="both", expand=True)

    # =========================================================================
    # PESTAÑA 3: CONTROL DE COBROS Y PAGOS (REPOTENCIADA)
    # =========================================================================
    frame_busq_pagos = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_busq_pagos.pack(pady=10, padx=10, fill="x")
    
    ctk.CTkLabel(frame_busq_pagos, text="Buscar Titular (Cédula o Contrato Viejo/Nuevo):", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_busqueda_ced = ctk.CTkEntry(frame_busq_pagos, width=280, placeholder_text="Cédula, Contrato Viejo o Contrato Nuevo...")
    txt_busqueda_ced.grid(row=1, column=0, padx=10, pady=5)
    
    # Panel Informativo Superior de la Póliza consultada
    frame_info_contratos = ctk.CTkFrame(tab_pagos, fg_color="#1e272e")
    frame_info_contratos.pack(pady=5, padx=20, fill="x")
    
    lbl_cv_display = ctk.CTkLabel(frame_info_contratos, text="Contrato Viejo: --", font=("Arial", 11, "bold"), text_color="#f1c40f")
    lbl_cv_display.grid(row=0, column=0, padx=15, pady=5)
    lbl_cn_display = ctk.CTkLabel(frame_info_contratos, text="Contrato Sistema: --", font=("Arial", 11, "bold"), text_color="#2ecc71")
    lbl_cn_display.grid(row=0, column=1, padx=15, pady=5)
    lbl_recibo_next = ctk.CTkLabel(frame_info_contratos, text="N° Recibo Asignado a Procesar: --", font=("Arial", 11, "bold"), text_color="#e67e22")
    lbl_recibo_next.grid(row=0, column=2, padx=15, pady=5)
    
    # Etiquetas maestras de estatus dinámico
    lbl_nombre_clie = ctk.CTkLabel(tab_pagos, text="Cliente: Seleccione un titular", font=("Arial", 13, "bold"), justify="left")
    lbl_nombre_clie.pack(pady=5, padx=20, anchor="w")
    
    lbl_aviso_morosidad = ctk.CTkLabel(tab_pagos, text="ESTADO: --", font=("Arial", 14, "bold"), text_color="grey")
    lbl_aviso_morosidad.pack(pady=2, padx=20, anchor="w")
    
    frame_ultimo_pago = ctk.CTkFrame(tab_pagos, border_width=2, border_color="#1f538d")
    frame_ultimo_pago.pack(pady=5, padx=20, fill="x")
    lbl_up_detalles = ctk.CTkLabel(frame_ultimo_pago, text="Historial de Cobros: Sin registrar búsquedas.", font=("Arial", 12, "italic"))
    lbl_up_detalles.pack(pady=5, padx=10, anchor="w")

    # Panel de entrada para la facturación en Bolívares
    frame_cobro = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_cobro.pack(pady=10, padx=20, fill="x")
    
    ctk.CTkLabel(frame_cobro, text="Tasa Oficial BCV (Bs.):", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    
    # Campo Tasa: Ahora incluye validación restrictiva de teclado por caracteres (v_tasa_num)
    txt_tasa = ctk.CTkEntry(frame_cobro, width=150, placeholder_text="0.00", state="disabled", validate="key", validatecommand=(v_tasa_num, '%P'))
    txt_tasa.grid(row=1, column=0, padx=10, pady=5)
    
    ctk.CTkLabel(frame_cobro, text="Forma de Pago:", font=("Arial", 12, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    combo_forma_pago = ctk.CTkComboBox(frame_cobro, values=["Efectivo", "Transferencia", "Tarjeta de debito", "Pago Móvil"], width=180)
    combo_forma_pago.grid(row=1, column=1, padx=10, pady=5)
    
    lbl_calculo_bs = ctk.CTkLabel(frame_cobro, text="Monto a pagar: 0,00 Bs", font=("Arial", 14, "bold", "italic"))
    lbl_calculo_bs.grid(row=1, column=2, padx=20, pady=5)

    # =========================================================================
    # FUNCIONES GENERALES DE ACCIÓN AUTOMÁTICA
    # =========================================================================

    def refrescar_tabla_familiares(ced_t):
        """Busca y refresca la lista de familiares de la pestaña 1."""
        for item in tabla.get_children(): tabla.delete(item)
        if not ced_t: return
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT cedula, nombres, apellidos, parentesco, fecha_nacimiento FROM familiares WHERE titular_cedula = ?", (ced_t.upper(),))
        for f in cursor.fetchall():
            edad_calc = f"{calcular_edad_exacta(f[4])} años" if f[4] else "N/A"
            tabla.insert("", "end", values=(f[0], f[1].title(), f[2].title(), f[3].title(), f[4] or "N/A", edad_calc))
        conn.close()

    def guardar_titular():
        """Lógica estricta de validación y almacenamiento de nuevos titulares."""
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
        
        # Validación interna inteligente de los recibos previos vacíos
        recibos_raw = txt_recibos_previos.get().strip()
        try: r_previos = int(recibos_raw) if recibos_raw else 0
        except: r_previos = 0
        
        # APLICACIÓN DE LA MÁSCARA OBLIGATORIA
        if not validar_mascara_cedula(ced):
            messagebox.showwarning("Formato Requerido", "Cédula del titular inválida.\nDebe comenzar con V o E seguido de 7 a 8 números.\nEjemplo: V12345678")
            txt_cedula.focus()
            return
            
        if not nom or not ape or not f_nac:
            messagebox.showwarning("Campos Requeridos", "Nombres, Apellidos y Fecha de Nacimiento son campos obligatorios.")
            return
            
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO titulares (cedula, contrato_viejo, contrato_nuevo, nombres, apellidos, fecha_nacimiento, telefono, correo, direccion, tipo_contrato, fecha_inicio, recibos_previos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ced, c_viejo, c_nuevo, nom, ape, f_nac, tel, corr, dir_hab, tipo_c, datetime.now().strftime("%d/%m/%Y"), r_previos))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", f"Titular registrado con el Contrato Sistema: {c_nuevo}")
            btn_add_fam.configure(state="normal")
            refrescar_tabla_familiares(ced)
            
            txt_cont_nuevo.configure(state="normal")
            txt_cont_nuevo.delete(0, "end"); txt_cont_nuevo.insert(0, generar_siguiente_contrato())
            txt_cont_nuevo.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Error de Duplicidad", f"La cédula o el número de contrato ya se encuentran registrados en el sistema.\n{e}")

    def cargar_datos_edicion():
        """Búsqueda e indexación omnicanal de datos para la pestaña 2."""
        crit = txt_busq_ed.get().strip().upper()  # Forzado a mayúsculas estrictas para SQLite
        if not crit: return
        
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
            for txt, val in [(txt_ed_nom, res[4]), (txt_ed_ape, res[5]), (txt_ed_tel, res[1]), (txt_ed_corr, res[2]), (txt_ed_dir, res[3])]:
                txt.delete(0, "end"); txt.insert(0, val.title() if isinstance(val, str) and txt in [txt_ed_nom, txt_ed_ape] else (val or ""))
            
            lbl_fecha_contrato_ed.configure(text=f"fecha de contrato  {res[6] or '--/--/----'}")
            for item in tabla_ed.get_children(): tabla_ed.delete(item)
            
            cursor.execute("SELECT id, cedula, nombres, apellidos, parentesco, fecha_nacimiento FROM familiares WHERE titular_cedula = ?", (res[0],))
            for f in cursor.fetchall():
                edad_calc = f"{calcular_edad_exacta(f[5])} años" if f[5] else "N/A"
                tabla_ed.insert("", "end", values=(f[0], f[1], f[2].title(), f[3].title(), f[4].title(), f[5] or "N/A", edad_calc))
            
            for b in [btn_actualizar, btn_retirar_fam, btn_add_fam_ed]: b.configure(state="normal")
            txt_ed_nom.focus()
        else:
            messagebox.showerror("No Localizado", "No se encontró ningún contrato asociado al dato ingresado.")
        conn.close()

    # =========================================================================
    # LÓGICA DE CONTROL DE COBROS, TASAS Y CUOTAS (SOLUCIONADO)
    # =========================================================================

    def buscar_y_calcular_pagos():
        """
        Búsqueda Omnicanal de Pagos:
        - Busca por Cédula Titular, Cédula Familiar, Contrato Viejo o Contrato Nuevo.
        - Calcula de forma exacta las cuotas pagadas/restantes según el contrato.
        - Activa el campo de tasa y le otorga el foco automático al operador.
        """
        ced = txt_busqueda_ced.get().strip().upper()
        if not ced: return
            
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
            tipo_contrato_global[0] = res[5]
            recibos_previos = res[4]
            
            # SOLUCIONADO: Desbloqueamos, limpiamos y enfocamos el campo de la tasa
            txt_tasa.configure(state="normal")
            txt_tasa.delete(0, "end")
            
            # Consultar cuántos pagos se han procesado en el software
            cursor.execute("SELECT COUNT(*) FROM pagos WHERE titular_cedula = ?", (cedula_real,))
            pagos_sistema = cursor.fetchone()[0]
            
            # Sumatoria del histórico más lo actual
            total_pagados = recibos_previos + pagos_sistema
            
            # MATEMÁTICA INTEGRADA DE CUOTAS
            if "24 meses" in res[5].lower():
                cuotas_totales_plan = 24
                cuotas_restantes = max(0, cuotas_totales_plan - total_pagados)
                status_cuotas_texto = f"Cuotas Canceladas: {total_pagados} / 24 | Restantes: {cuotas_restantes}"
                proximo_recibo_global[0] = total_pagados + 1
            else:
                # Si es un contrato de renovación anual (ciclos de 12 meses)
                cuotas_en_renovacion = total_pagados - 24 if total_pagados >= 24 else total_pagados
                cuotas_restantes = max(0, 12 - (cuotas_en_renovacion % 12))
                status_cuotas_texto = f"Ciclo Renovación -> Pagadas: {cuotas_en_renovacion % 12} / 12 | Restantes: {cuotas_restantes}"
                proximo_recibo_global[0] = ((total_pagados - 24) % 12) + 1 if total_pagados >= 24 else (total_pagados % 12) + 1
            
            # Renderizar datos en pantalla
            lbl_nombre_clie.configure(
                text=f"Cliente: {res[0].upper()} {res[1].upper()} | Plan: {res[5].upper()}\n[{status_cuotas_texto}]"
            )
            lbl_cv_display.configure(text=f"Contrato Viejo: {res[2] or 'NINGUNO'}")
            lbl_cn_display.configure(text=f"Contrato Sistema: {res[3]}")
            lbl_recibo_next.configure(text=f"N° Recibo Asignado a Procesar: #{proximo_recibo_global[0]}")
            
            # Consultar y pintar estado de morosidad
            estado = consultar_estado_cliente(cedula_real)
            if estado["moroso"]:
                lbl_aviso_morosidad.configure(text=f"ESTADO: MOROSO (Debe ${estado['deuda_usd']:.2f})", text_color="red")
            else:
                lbl_aviso_morosidad.configure(text="ESTADO: AL DÍA / SOLVENTE", text_color="green")
            
            # Cargar la bitácora del último cobro registrado
            cursor.execute("SELECT fecha_pago, monto_usd, numero_recibo, forma_pago FROM pagos WHERE titular_cedula = ? ORDER BY id DESC LIMIT 1", (cedula_real,))
            u = cursor.fetchone()
            lbl_up_detalles.configure(text=f"Último Pago -> Fecha: {u[0]} | Monto: ${u[1]:.2f} USD | Recibo: #{u[2]} | Método: {u[3]}" if u else "Historial: Sin cobros procesados en el sistema.")
            
            # Habilitar el botón de procesar cobro y fijar cursor en tasa
            btn_pagar.configure(state="normal")
            txt_tasa.focus()
        else:
            messagebox.showerror("No Encontrado", "No se localizó ningún contrato asociado al dato ingresado.")
            txt_tasa.configure(state="disabled")
            btn_pagar.configure(state="disabled")
        conn.close()

    def actualizar_calculo_bolivares(*args):
        """Recalcula y formatea en caliente los Bolívares usando separadores venezolanos."""
        try:
            tasa_texto = txt_tasa.get().strip()
            if not tasa_texto:
                lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")
                return
                
            tasa = float(tasa_texto)
            # Tarifa según plan: Renovación = $12, Velación 24 = $10, Velación+Entierro = $20
            usd = 12.0 if "renovación" in tipo_contrato_global[0].lower() else (10.0 if "velación 24" in tipo_contrato_global[0].lower() else 20.0)
            
            monto_bs = usd * tasa
            # SOLUCIONADO: Mostrar con formato de miles (.) y decimales (,)
            lbl_calculo_bs.configure(text=f"Monto a pagar ({usd} USD): {formatear_moneda_ve(monto_bs)}")
        except:
            lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")

    # Enlazar recálculo dinámico al escribir en la casilla de la tasa
    txt_tasa.bind("<KeyRelease>", actualizar_calculo_bolivares)

    def ejecutar_pago():
        """
        Procesamiento y Facturación del Cobro:
        - Inserta de forma definitiva el pago en la base de datos sqlite.
        - Migra automáticamente los contratos de 24 meses que ya cumplieron sus cuotas.
        """
        ced_busq = txt_busqueda_ced.get().strip().upper()
        tasa_raw = txt_tasa.get().strip()
        
        if not tasa_raw or float(tasa_raw) <= 0:
            messagebox.showwarning("Falta Información", "Por favor introduzca una tasa oficial de cambio válida.")
            return
            
        try:
            tasa = float(tasa_raw)
            f_pago = combo_forma_pago.get()
            
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cedula, contrato_viejo, contrato_nuevo, recibos_previos, tipo_contrato FROM titulares 
                WHERE cedula=? OR UPPER(contrato_viejo)=? OR UPPER(contrato_nuevo)=?
                   OR cedula IN (SELECT titular_cedula FROM familiares WHERE UPPER(cedula) = ?)
            """, (ced_busq, ced_busq, ced_busq, ced_busq))
            t_data = cursor.fetchone()
            
            ced_real, c_viejo, c_nuevo, r_previos, t_contrato = t_data[0], t_data[1], t_data[2], t_data[3], t_data[4]
            
            usd = 12.0 if "renovación" in t_contrato.lower() else (10.0 if "velación 24" in t_contrato.lower() else 20.0)
            bs = usd * tasa
            fecha_p = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            # Registrar el cobro en la tabla de pagos
            cursor.execute("""
                INSERT INTO pagos (titular_cedula, monto_usd, tasa_bcv, monto_bs, fecha_pago, contrato_viejo, contrato_nuevo, numero_recibo, forma_pago) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ced_real, usd, tasa, bs, fecha_p, c_viejo, c_nuevo, proximo_recibo_global[0], f_pago))
            
            # Validar si el cliente califica para migración automática de plan
            cursor.execute("SELECT COUNT(*) FROM pagos WHERE titular_cedula = ?", (ced_real,))
            pagos_sistema = cursor.fetchone()[0]
            total_acumulado = r_previos + pagos_sistema
            
            if "24 meses" in t_contrato.lower() and total_acumulado >= 24:
                cursor.execute("UPDATE titulares SET tipo_contrato = 'renovación anual 12 meses' WHERE cedula = ?", (ced_real,))
                messagebox.showinfo("Migración de Contrato", "¡MIGRACIÓN DE CONTRATO AUTOMÁTICA!\nEl titular completó las 24 cuotas bases. Ha sido cambiado al plan de 'renovación anual 12 meses'.")
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Pago Exitoso", f"Recibo #{proximo_recibo_global[0]} guardado e impreso de forma exitosa.")
            
            # Limpieza operativa para obligar a una nueva consulta limpia
            txt_tasa.delete(0, "end")
            txt_tasa.configure(state="disabled")
            buscar_y_calcular_pagos()
        except Exception as e:
            messagebox.showerror("Error", f"Fallo crítico al facturar el pago en la base de datos.\nDetalle: {e}")

    # =========================================================================
    # CONEXIONES DIRECTAS DE BOTONES Y EVENTOS DE RETORNO (ENTER)
    # =========================================================================
    
    # SOLUCIONADO: El botón de verificar estado ahora está perfectamente vinculado a la función lógica
    btn_buscar = ctk.CTkButton(frame_busq_pagos, text="Verificar Estado", width=120, command=buscar_y_calcular_pagos)
    btn_buscar.grid(row=1, column=1, padx=10, pady=5)
    txt_busqueda_ced.bind("<Return>", lambda e: buscar_y_calcular_pagos())

    # Vincular búsquedas de la pestaña 2
    ctk.CTkButton(frame_busq_ed, text="Buscar Contrato", width=120, command=cargar_datos_edicion).grid(row=1, column=1, padx=10, pady=5)
    txt_busq_ed.bind("<Return>", lambda e: cargar_datos_edicion())

    # Declaración de botones físicos del panel
    btn_guardar_tit = ctk.CTkButton(tab_clientes, text="Guardar Titular", fg_color="green", command=guardar_titular)
    btn_guardar_tit.grid(row=2, column=0, pady=10, padx=10, sticky="w")
    
    btn_add_fam = ctk.CTkButton(tab_clientes, text="+ Agregar Familiar", fg_color="#1f538d", state="disabled", command=lambda: abrir_modulo_familiares(ventana, txt_cedula.get().strip().upper(), v_letras, lambda: refrescar_tabla_familiares(txt_cedula.get().strip().upper())))
    btn_add_fam.grid(row=2, column=1, pady=10, padx=10, sticky="w")
    
    ctk.CTkButton(tab_clientes, text="Salir del Sistema", fg_color="#d35400", command=ventana.destroy).grid(row=2, column=2, pady=10, padx=10, sticky="e")

    frame_botones_ed = ctk.CTkFrame(tab_edicion, fg_color="transparent")
    frame_botones_ed.pack(pady=10, padx=10, fill="x")
    
    btn_actualizar = ctk.CTkButton(frame_botones_ed, text="Guardar Cambios Titular", fg_color="green", state="disabled", command=lambda: [conectar().cursor().execute("UPDATE titulares SET nombres=?, apellidos=?, telefono=?, correo=?, direccion=? WHERE cedula=?", (txt_ed_nom.get().strip().lower(), txt_ed_ape.get().strip().lower(), txt_ed_tel.get().strip(), txt_ed_corr.get().strip().lower(), txt_ed_dir.get().strip().lower(), cedula_titular_edicion[0])), conectar().commit(), messagebox.showinfo("Éxito", "Historial modificado."), cargar_datos_edicion()])
    btn_actualizar.grid(row=0, column=0, padx=5)
    
    btn_retirar_fam = ctk.CTkButton(frame_botones_ed, text="- Retirar Afiliado Seleccionado", fg_color="red", state="disabled", command=lambda: [conectar().cursor().execute("DELETE FROM familiares WHERE id=?", (tabla_ed.item(tabla_ed.selection())['values'][0],)), conectar().commit(), cargar_datos_edicion(), refrescar_tabla_familiares(cedula_titular_edicion[0])])
    btn_retirar_fam.grid(row=0, column=1, padx=5)
    
    btn_add_fam_ed = ctk.CTkButton(frame_botones_ed, text="+ Reemplazar / Agregar Afiliado", fg_color="#1f538d", state="disabled", command=lambda: abrir_modulo_familiares(ventana, cedula_titular_edicion[0], v_letras, lambda: [cargar_datos_edicion(), refrescar_tabla_familiares(cedula_titular_edicion[0])]))
    btn_add_fam_ed.grid(row=0, column=2, padx=5)
    
    ctk.CTkButton(frame_botones_ed, text="Salir", fg_color="#d35400", command=ventana.destroy).grid(row=0, column=3, padx=20)

    frame_acciones_p = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_acciones_p.pack(pady=15, padx=20, fill="x")
    
    # SOLUCIONADO: Botón de cobro enlazado directamente a ejecutar_pago
    btn_pagar = ctk.CTkButton(frame_acciones_p, text="Procesar Pago", fg_color="green", state="disabled", command=ejecutar_pago)
    btn_pagar.grid(row=0, column=0, padx=5)
    
    ctk.CTkButton(frame_acciones_p, text="Salir", fg_color="#d35400", command=ventana.destroy).grid(row=0, column=1, padx=20)

    # =========================================================================
    # MOTOR DE LIMPIEZA INTER-PESTAÑAS (SEGURIDAD CONTRA ERRORES CRUZADOS)
    # =========================================================================
    def gestionar_limpieza_pestanas():
        """Limpia automáticamente los historiales consultados de las otras pestañas al cambiar de ventana."""
        # Reseteo estricto de Pestaña 2 (Edición)
        txt_busq_ed.delete(0, "end")
        lbl_fecha_contrato_ed.configure(text="fecha de contrato: --/--/----")
        for t in [txt_ed_nom, txt_ed_ape, txt_ed_tel, txt_ed_corr, txt_ed_dir]: t.delete(0, "end")
        for item in tabla_ed.get_children(): tabla_ed.delete(item)
        for b in [btn_actualizar, btn_retirar_fam, btn_add_fam_ed]: b.configure(state="disabled")
        
        # Reseteo estricto de Pestaña 3 (Control de Pagos)
        txt_busqueda_ced.delete(0, "end")
        txt_tasa.delete(0, "end"); txt_tasa.configure(state="disabled")
        lbl_nombre_clie.configure(text="Cliente: Seleccione un titular")
        lbl_cv_display.configure(text="Contrato Viejo: --")
        lbl_cn_display.configure(text="Contrato Sistema: --")
        lbl_recibo_next.configure(text="N° Recibo Asignado a Procesar: --")
        lbl_aviso_morosidad.configure(text="ESTADO: --", text_color="grey")
        lbl_up_detalles.configure(text="Historial de Cobros: Sin registrar búsquedas.")
        lbl_calculo_bs.configure(text="Monto a pagar: 0,00 Bs")
        btn_pagar.configure(state="disabled")

    # Escuchar de forma nativa los clics en el Tabview
    pestanas.configure(command=gestionar_limpieza_pestanas)

    ventana.mainloop()

# =========================================================================
# COMPONENTE MODAL: REGISTRO DE AFILIADOS (CON MÁSCARA ESTRICTA)
# =========================================================================
def abrir_modulo_familiares(ventana_padre, cedula_titular, v_let, funcion_exito_refrescar):
    """Abre un pop-up flotante controlado para indexar familiares al contrato."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM familiares WHERE titular_cedula = ?", (cedula_titular,))
    cantidad = cursor.fetchone()[0]
    conn.close()
    
    if cantidad >= 8:
        messagebox.showwarning("Límite Alcanzado", "Este contrato ya cuenta con los 8 familiares permitidos por póliza.")
        return

    pop = ctk.CTkToplevel(ventana_padre)
    pop.title("Agregar Familiar")
    pop.geometry("450x480")
    pop.grab_set()  # Bloquea la interacción con la ventana de atrás hasta cerrar el modal
    
    ctk.CTkLabel(pop, text="Cédula Familiar (V/E + Números, o vacío si es menor):", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fcedula = ctk.CTkEntry(pop, width=280, placeholder_text="Ej: V25111222")
    txt_fcedula.pack(pady=2, padx=20)
    
    ctk.CTkLabel(pop, text="Nombres:", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fnombre = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fnombre.pack(pady=2, padx=20)
    
    ctk.CTkLabel(pop, text="Apellidos:", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fapellido = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fapellido.pack(pady=2, padx=20)
    
    ctk.CTkLabel(pop, text="Fecha Nacimiento Afiliado:", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_ffecha = ctk.CTkEntry(pop, placeholder_text="DD/MM/YYYY", width=280)
    txt_ffecha.pack(pady=2, padx=20)
    
    ctk.CTkLabel(pop, text="Parentesco con el Titular:", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fparentesco = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fparentesco.pack(pady=2, padx=20)
    
    txt_fcedula.focus_set()

    # Saltos de enter internos del pop-up