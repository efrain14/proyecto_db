import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
import sys
import os

# Asegurar que encuentre los otros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.conexion import conectar
from logic.consultas import consultar_estado_cliente

# =========================================================================
# FUNCIONES DE VALIDACIÓN Y UTILERÍAS
# =========================================================================

def validar_cedula_titular(texto_actualizado):
    if texto_actualizado == "": return True
    primer_caracter = texto_actualizado[0].upper()
    if primer_caracter not in ['V', 'E']: return False
    if len(texto_actualizado) > 1:
        resto_texto = texto_actualizado[1:]
        if not resto_texto.isdigit() or len(resto_texto) > 8: return False
    return True

def validar_cedula_familiar(texto_actualizado):
    if texto_actualizado == "": return True
    if "MENOR".startswith(texto_actualizado.upper()): return True
    primer_caracter = texto_actualizado[0].upper()
    if primer_caracter not in ['V', 'E']: return False
    if len(texto_actualizado) > 1:
        resto_texto = texto_actualizado[1:]
        if not resto_texto.isdigit() or len(resto_texto) > 8: return False
    return True

def validar_solo_letras(texto_actualizado):
    if texto_actualizado == "": return True
    return texto_actualizado.replace(" ", "").isalpha()

def calcular_edad_exacta(fecha_str):
    """Profesor: Adaptada para procesar barras diagonales (DD/MM/YYYY) de forma segura."""
    try:
        if len(fecha_str) != 10:
            return None
        fecha_nac = datetime.strptime(fecha_str, "%d/%m/%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        return edad if edad >= 0 else None
    except:
        return None

def vincular_salto_enter(widget_actual, widget_siguiente):
    widget_actual.bind("<Return>", lambda event: widget_siguiente.focus())

# =========================================================================
# INTERFAZ GRÁFICA PRINCIPAL
# =========================================================================

def mostrar_dashboard():
    ventana = ctk.CTk()
    ventana.title("Sistema Funerario - Panel de Control")
    ventana.geometry("1050x750")
    
    v_ced_tit = ventana.register(validar_cedula_titular)
    v_ced_fam = ventana.register(validar_cedula_familiar)
    v_letras = ventana.register(validar_solo_letras)
    
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#2a2a2a", foreground="white", fieldbackground="#2a2a2a", rowheight=25)
    style.map("Treeview", background=[('selected', '#1f538d')])
    style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=("Arial", 10, "bold"))

    pestanas = ctk.CTkTabview(ventana, width=1010, height=700)
    pestanas.pack(pady=10, padx=10, fill="both", expand=True)
    
    tab_clientes = pestanas.add("Registro de Clientes")
    tab_edicion = pestanas.add("Edición de Titulares y Afiliados")
    tab_pagos = pestanas.add("Control de Pagos y Estado")
    
    cedula_titular_edicion = [""]

    # =========================================================================
    # PESTAÑA 1: REGISTRO DE CLIENTES
    # =========================================================================
    frame_form_reg = ctk.CTkFrame(tab_clientes, fg_color="transparent")
    frame_form_reg.grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky="w")
    
    ctk.CTkLabel(frame_form_reg, text="Cédula de Identidad:", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_cedula = ctk.CTkEntry(frame_form_reg, width=180, validate="key", validatecommand=(v_ced_tit, '%P'))
    txt_cedula.grid(row=1, column=0, padx=10, pady=(2,10), sticky="w")
    
    ctk.CTkLabel(frame_form_reg, text="Nombres:", font=("Arial", 12, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    txt_nombres = ctk.CTkEntry(frame_form_reg, width=220, validate="key", validatecommand=(v_letras, '%P'))
    txt_nombres.grid(row=1, column=1, padx=10, pady=(2,10), sticky="w")
    
    ctk.CTkLabel(frame_form_reg, text="Apellidos:", font=("Arial", 12, "bold")).grid(row=0, column=2, padx=10, sticky="w")
    txt_apellidos = ctk.CTkEntry(frame_form_reg, width=220, validate="key", validatecommand=(v_letras, '%P'))
    txt_apellidos.grid(row=1, column=2, padx=10, pady=(2,10), sticky="w")
    
    # Profesor: Modificado el placeholder para indicar el uso de barras "/"
    ctk.CTkLabel(frame_form_reg, text="Fecha de Nacimiento:", font=("Arial", 12, "bold")).grid(row=2, column=0, padx=10, sticky="w")
    txt_fecha_nac = ctk.CTkEntry(frame_form_reg, placeholder_text="DD/MM/YYYY", width=180)
    txt_fecha_nac.grid(row=3, column=0, padx=10, pady=(2,10), sticky="w")
    
    # Profesor: Añadido color de fondo amarillo con letras negras para un contraste perfecto de la edad
    lbl_edad_titular = ctk.CTkLabel(
        frame_form_reg, 
        text=" Edad: -- años ", 
        font=("Arial", 12, "bold"), 
        fg_color="#f39c12", 
        text_color="black",
        corner_radius=6
    )
    lbl_edad_titular.grid(row=3, column=1, padx=10, pady=(2,10), sticky="w")
    
    def disparar_calculo_edad(*args):
        texto = txt_fecha_nac.get().strip()
        edad = calcular_edad_exacta(texto)
        if edad is not None: 
            lbl_edad_titular.configure(text=f" Edad: {edad} años ")
        else: 
            lbl_edad_titular.configure(text=" Edad: -- años ")
            
    txt_fecha_nac.bind("<KeyRelease>", disparar_calculo_edad)
    
    ctk.CTkLabel(frame_form_reg, text="Teléfono de Contacto:", font=("Arial", 12, "bold")).grid(row=2, column=2, padx=10, sticky="w")
    txt_telefono = ctk.CTkEntry(frame_form_reg, width=220)
    txt_telefono.grid(row=3, column=2, padx=10, pady=(2,10), sticky="w")
    
    ctk.CTkLabel(frame_form_reg, text="Correo Electrónico:", font=("Arial", 12, "bold")).grid(row=4, column=0, padx=10, sticky="w")
    txt_correo = ctk.CTkEntry(frame_form_reg, width=180)
    txt_correo.grid(row=5, column=0, padx=10, pady=(2,10), sticky="w")
    
    ctk.CTkLabel(frame_form_reg, text="Dirección Completa de Habitación:", font=("Arial", 12, "bold")).grid(row=4, column=1, padx=10, sticky="w")
    txt_direccion = ctk.CTkEntry(frame_form_reg, width=220)
    txt_direccion.grid(row=5, column=1, padx=10, pady=(2,10), sticky="w")
    
    ctk.CTkLabel(frame_form_reg, text="Tipo de Contrato Comercial:", font=("Arial", 12, "bold")).grid(row=4, column=2, padx=10, sticky="w")
    combo_contrato = ctk.CTkComboBox(frame_form_reg, values=["Velación ($10)", "Velación + Entierro ($20)"], width=220)
    combo_contrato.grid(row=5, column=2, padx=10, pady=(2,10), sticky="w")

    vincular_salto_enter(txt_cedula, txt_nombres)
    vincular_salto_enter(txt_nombres, txt_apellidos)
    vincular_salto_enter(txt_apellidos, txt_fecha_nac)
    vincular_salto_enter(txt_fecha_nac, txt_telefono)
    vincular_salto_enter(txt_telefono, txt_correo)
    vincular_salto_enter(txt_correo, txt_direccion)

    tabla_frame = ctk.CTkFrame(tab_clientes)
    tabla_frame.grid(row=1, column=0, columnspan=3, pady=10, padx=10, sticky="nsew")
    
    tabla = ttk.Treeview(tabla_frame, columns=("cedula", "nombres", "apellidos", "parentesco"), show="headings", height=6)
    tabla.heading("cedula", text="Cédula / Identificador")
    tabla.heading("nombres", text="Nombres")
    tabla.heading("apellidos", text="Apellidos")
    tabla.heading("parentesco", text="Parentesco")
    tabla.column("cedula", width=150, anchor="center")
    tabla.column("parentesco", width=150, anchor="center")
    tabla.pack(fill="both", expand=True)
    
    def refrescar_tabla_familiares(ced_t):
        for item in tabla.get_children(): tabla.delete(item)
        if not ced_t: return
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT cedula, nombres, apellidos, parentesco FROM familiares WHERE titular_cedula = ?", (ced_t,))
        for fila in cursor.fetchall():
            tabla.insert("", "end", values=(fila[0], fila[1].title(), fila[2].title(), fila[3].title()))
        conn.close()

    def guardar_titular():
        ced = txt_cedula.get().strip().upper()
        nom = txt_nombres.get().strip().lower()
        ape = txt_apellidos.get().strip().lower()
        f_nac = txt_fecha_nac.get().strip()
        tel = txt_telefono.get().strip()
        corr = txt_correo.get().strip().lower()
        dir_hab = txt_direccion.get().strip().lower()
        tipo_c = "velacion" if "Velación ($10)" in combo_contrato.get() else "completo"
        f_inicio = datetime.now().strftime("%d/%m/%Y")
        
        if not ced or not nom or not ape or not f_nac:
            messagebox.showwarning("Campos Requeridos", "Por favor complete los datos obligatorios.")
            return
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO titulares (cedula, nombres, apellidos, fecha_nacimiento, telefono, correo, direccion, tipo_contrato, fecha_inicio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ced, nom, ape, f_nac, tel, corr, dir_hab, tipo_c, f_inicio))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", "Titular guardado satisfactoriamente.")
            btn_add_fam.configure(state="normal")
            refrescar_tabla_familiares(ced)
        except Exception as e:
            messagebox.showerror("Error", "La cédula ya se encuentra registrada.")

    btn_guardar_tit = ctk.CTkButton(tab_clientes, text="Guardar Titular", fg_color="green", command=guardar_titular)
    btn_guardar_tit.grid(row=2, column=0, pady=10, padx=10, sticky="w")
    
    def abrir_ventana_familiares():
        ced_t = txt_cedula.get().strip().upper()
        # Profesor: Le pasamos también la función para refrescar la Pestaña 1
        abrir_modulo_familiares(ventana, ced_t, v_ced_fam, v_letras, lambda: refrescar_tabla_familiares(ced_t))

    btn_add_fam = ctk.CTkButton(tab_clientes, text="+ Agregar Familiar", fg_color="#1f538d", state="disabled", command=abrir_ventana_familiares)
    btn_add_fam.grid(row=2, column=1, pady=10, padx=10, sticky="w")
    
    btn_salir_t1 = ctk.CTkButton(tab_clientes, text="Salir del Sistema", fg_color="#d35400", command=ventana.destroy)
    btn_salir_t1.grid(row=2, column=2, pady=10, padx=10, sticky="e")

    # =========================================================================
    # PESTAÑA 2: EDICIÓN COMPLETA (CON RETIRO TOTALMENTE SINCRONIZADO)
    # =========================================================================
    frame_busq_ed = ctk.CTkFrame(tab_edicion, fg_color="transparent")
    frame_busq_ed.pack(pady=10, padx=10, fill="x")
    
    ctk.CTkLabel(frame_busq_ed, text="Buscar por Cédula, Nombre o Apellido del Titular:", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_busq_ed = ctk.CTkEntry(frame_busq_ed, width=350)
    txt_busq_ed.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    frame_campos_ed = ctk.CTkFrame(tab_edicion)
    frame_campos_ed.pack(pady=5, padx=10, fill="x")
    
    ctk.CTkLabel(frame_campos_ed, text="Modificar Teléfono:", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_ed_tel = ctk.CTkEntry(frame_campos_ed, width=180)
    txt_ed_tel.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    ctk.CTkLabel(frame_campos_ed, text="Modificar Correo:", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")
    txt_ed_corr = ctk.CTkEntry(frame_campos_ed, width=220)
    txt_ed_corr.grid(row=1, column=1, padx=10, pady=5, sticky="w")
    
    ctk.CTkLabel(frame_campos_ed, text="Modificar Dirección de Habitación:", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=10, sticky="w")
    txt_ed_dir = ctk.CTkEntry(frame_campos_ed, width=350)
    txt_ed_dir.grid(row=1, column=2, padx=10, pady=5, sticky="w")
    
    vincular_salto_enter(txt_busq_ed, txt_ed_tel)
    vincular_salto_enter(txt_ed_tel, txt_ed_corr)
    vincular_salto_enter(txt_ed_corr, txt_ed_dir)

    ctk.CTkLabel(tab_edicion, text="Afiliados de esta póliza (Seleccione uno para eliminar/retirar):", font=("Arial", 12, "bold")).pack(pady=(10,2), padx=10, anchor="w")
    
    tabla_ed_frame = ctk.CTkFrame(tab_edicion)
    tabla_ed_frame.pack(pady=5, padx=10, fill="both", expand=True)
    
    tabla_ed = ttk.Treeview(tabla_ed_frame, columns=("id", "cedula", "nombres", "apellidos", "parentesco"), show="headings", height=4)
    tabla_ed.heading("id", text="ID")
    tabla_ed.heading("cedula", text="Cédula")
    tabla_ed.heading("nombres", text="Nombres")
    tabla_ed.heading("apellidos", text="Apellidos")
    tabla_ed.heading("parentesco", text="Parentesco")
    tabla_ed.column("id", width=50, anchor="center")
    tabla_ed.column("cedula", width=120, anchor="center")
    tabla_ed.pack(fill="both", expand=True)

    def cargar_datos_edicion():
        criterio = txt_busq_ed.get().strip().lower()
        if not criterio: return
        
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cedula, telefono, correo, direccion FROM titulares 
            WHERE cedula LIKE ? OR nombres LIKE ? OR apellidos LIKE ?
        """, (f"%{criterio}%", f"%{criterio}%", f"%{criterio}%"))
        res = cursor.fetchone()
        
        if res:
            cedula_titular_edicion[0] = res[0]
            txt_ed_tel.delete(0, "end"); txt_ed_tel.insert(0, res[1] if res[1] else "")
            txt_ed_corr.delete(0, "end"); txt_ed_corr.insert(0, res[2] if res[2] else "")
            txt_ed_dir.delete(0, "end"); txt_ed_dir.insert(0, res[3] if res[3] else "")
            
            for item in tabla_ed.get_children(): tabla_ed.delete(item)
            cursor.execute("SELECT id, cedula, nombres, apellidos, parentesco FROM familiares WHERE titular_cedula = ?", (res[0],))
            for f in cursor.fetchall():
                tabla_ed.insert("", "end", values=(f[0], f[1], f[2].title(), f[3].title(), f[4].title()))
                
            btn_actualizar.configure(state="normal")
            btn_retirar_fam.configure(state="normal")
            btn_add_fam_ed.configure(state="normal")
        else:
            messagebox.showerror("Error", "No se encontró ningún registro coincidente.")
        conn.close()

    btn_bus_ed = ctk.CTkButton(frame_busq_ed, text="Buscar Contrato", width=120, command=cargar_datos_edicion)
    btn_bus_ed.grid(row=1, column=1, padx=10, pady=5)

    def actualizar_titular_y_afiliados():
        ced = cedula_titular_edicion[0]
        tel = txt_ed_tel.get().strip()
        corr = txt_ed_corr.get().strip().lower()
        dir_h = txt_ed_dir.get().strip().lower()
        
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("UPDATE titulares SET telefono = ?, correo = ?, direccion = ? WHERE cedula = ?", (tel, corr, dir_h, ced))
        conn.commit()
        conn.close()
        messagebox.showinfo("Éxito", "Información del contrato actualizada.")
        cargar_datos_edicion()

    def eliminar_familiar_seleccionado():
        """Profesor: Sincronizada para limpiar simultáneamente la tabla de la Pestaña 1."""
        seleccionado = tabla_ed.selection()
        if not seleccionado:
            messagebox.showwarning("Selección", "Por favor seleccione un afiliado de la lista.")
            return
        id_fam = tabla_ed.item(seleccionado)['values'][0]
        
        if messagebox.askyesno("Confirmar", "¿Está seguro de retirar este familiar de la póliza?"):
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM familiares WHERE id = ?", (id_fam,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", "Familiar retirado.")
            
            # 1. Refrescar la tabla actual (Pestaña 2)
            cargar_datos_edicion()
            # 2. Profesor: Obligamos a la Pestaña 1 a redibujar los datos vigentes
            refrescar_tabla_familiares(cedula_titular_edicion[0])

    def agregar_familiar_desde_edicion():
        # Al agregar desde aquí, refresca ambas vistas al guardarse
        abrir_modulo_familiares(ventana, cedula_titular_edicion[0], v_ced_fam, v_letras, lambda: [cargar_datos_edicion(), refrescar_tabla_familiares(cedula_titular_edicion[0])])

    frame_botones_ed = ctk.CTkFrame(tab_edicion, fg_color="transparent")
    frame_botones_ed.pack(pady=10, padx=10, fill="x")
    
    btn_actualizar = ctk.CTkButton(frame_botones_ed, text="Guardar Cambios Titular", fg_color="green", state="disabled", command=actualizar_titular_y_afiliados)
    btn_actualizar.grid(row=0, column=0, padx=5)
    
    btn_retirar_fam = ctk.CTkButton(frame_botones_ed, text="- Retirar Afiliado Seleccionado", fg_color="red", state="disabled", command=eliminar_familiar_seleccionado)
    btn_retirar_fam.grid(row=0, column=1, padx=5)
    
    btn_add_fam_ed = ctk.CTkButton(frame_botones_ed, text="+ Reemplazar / Agregar Afiliado", fg_color="#1f538d", state="disabled", command=agregar_familiar_desde_edicion)
    btn_add_fam_ed.grid(row=0, column=2, padx=5)
    
    btn_salir_t2 = ctk.CTkButton(frame_botones_ed, text="Salir", fg_color="#d35400", command=ventana.destroy)
    btn_salir_t2.grid(row=0, column=3, padx=20)

    # =========================================================================
    # PESTAÑA 3: CONTROL DE PAGOS E HISTORIAL
    # =========================================================================
    frame_busq_pagos = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_busq_pagos.pack(pady=10, padx=10, fill="x")
    
    ctk.CTkLabel(frame_busq_pagos, text="Buscar Titular por Cédula de Identidad:", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_busqueda_ced = ctk.CTkEntry(frame_busq_pagos, width=250)
    txt_busqueda_ced.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    lbl_nombre_clie = ctk.CTkLabel(tab_pagos, text="Cliente: Seleccione un titular", font=("Arial", 14, "bold"))
    lbl_nombre_clie.pack(pady=5, padx=20, anchor="w")
    
    lbl_aviso_morosidad = ctk.CTkLabel(tab_pagos, text="ESTADO: --", font=("Arial", 16, "bold"), text_color="grey")
    lbl_aviso_morosidad.pack(pady=5, padx=20, anchor="w")
    
    frame_ultimo_pago = ctk.CTkFrame(tab_pagos, border_width=2, border_color="#1f538d")
    frame_ultimo_pago.pack(pady=10, padx=20, fill="x")
    
    ctk.CTkLabel(frame_ultimo_pago, text="INFORMACIÓN DEL ÚLTIMO PAGO REGISTRADO", font=("Arial", 11, "bold", "underline")).pack(pady=2, padx=10, anchor="w")
    lbl_up_detalles = ctk.CTkLabel(frame_ultimo_pago, text="Fecha: --  |  Monto: -- USD  |  Total Cancelado en Bs: -- Bs.", font=("Arial", 12, "italic"))
    lbl_up_detalles.pack(pady=5, padx=10, anchor="w")

    frame_cobro = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_cobro.pack(pady=10, padx=20, fill="x")
    
    ctk.CTkLabel(frame_cobro, text="Tasa de Cambio Oficial BCV (Bs.):", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, sticky="w")
    txt_tasa = ctk.CTkEntry(frame_cobro, width=200, state="disabled")
    txt_tasa.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    lbl_calculo_bs = ctk.CTkLabel(frame_cobro, text="Monto a pagar: 0.00 Bs.", font=("Arial", 13, "bold", "italic"))
    lbl_calculo_bs.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    def buscar_y_calcular():
        ced = txt_busqueda_ced.get().strip().upper()
        if not ced: return
            
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT nombres, apellidos FROM titulares WHERE cedula = ?", (ced,))
        res = cursor.fetchone()
        
        if res:
            lbl_nombre_clie.configure(text=f"Cliente: {res[0].upper()} {res[1].upper()}")
            estado = consultar_estado_cliente(ced)
            
            if estado["moroso"]:
                lbl_aviso_morosidad.configure(text=f"ESTADO: MOROSO (Debe ${estado['deuda_usd']:.2f})", text_color="red")
            else:
                lbl_aviso_morosidad.configure(text="ESTADO: AL DÍA / SOLVENTE", text_color="green")
            
            cursor.execute("SELECT fecha_pago, monto_usd, monto_bs FROM pagos WHERE titular_cedula = ? ORDER BY id DESC LIMIT 1", (ced,))
            u_pago = cursor.fetchone()
            if u_pago:
                lbl_up_detalles.configure(text=f"Fecha: {u_pago[0]}  |  Monto: ${u_pago[1]:.2f} USD  |  Equivalente: {u_pago[2]:.2f} Bs.")
            else:
                lbl_up_detalles.configure(text="Fecha: NINGUNA  |  Monto: No registra pagos anteriores.")
            
            txt_tasa.configure(state="normal")
            btn_pagar.configure(state="normal")
        else:
            messagebox.showerror("No Encontrado", "Cédula no registrada.")
        conn.close()
            
    btn_buscar = ctk.CTkButton(frame_busq_pagos, text="Verificar Estado", width=120, command=buscar_y_calcular)
    btn_buscar.grid(row=1, column=1, padx=10, pady=5)
    vincular_salto_enter(txt_busqueda_ced, txt_tasa)

    def actualizar_calculo_bolivares(*args):
        ced = txt_busqueda_ced.get().strip().upper()
        try:
            tasa = float(txt_tasa.get().strip())
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT tipo_contrato FROM titulares WHERE cedula = ?", (ced,))
            tipo = cursor.fetchone()[0]
            conn.close()
            usd = 10.0 if tipo == "velacion" else 20.0
            lbl_calculo_bs.configure(text=f"Monto a pagar ({usd} USD): {usd * tasa:.2f} Bs.")
        except:
            lbl_calculo_bs.configure(text="Monto a pagar: -- Bs.")

    txt_tasa.bind("<KeyRelease>", actualizar_calculo_bolivares)

    def ejecutar_pago():
        ced = txt_busqueda_ced.get().strip().upper()
        try:
            tasa = float(txt_tasa.get().strip())
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT tipo_contrato FROM titulares WHERE cedula = ?", (ced,))
            tipo = cursor.fetchone()[0]
            usd = 10.0 if tipo == "velacion" else 20.0
            bs = usd * tasa
            fecha_p = datetime.now().strftime("%d/%m/%Y")
            
            cursor.execute("INSERT INTO pagos (titular_cedula, monto_usd, tasa_bcv, monto_bs, fecha_pago) VALUES (?, ?, ?, ?, ?)", 
                           (ced, usd, tasa, bs, fecha_p))
            conn.commit()
            conn.close()
            messagebox.showinfo("Pago Registrado", "El cobro se completó correctamente.")
            buscar_y_calcular()
        except:
            messagebox.showerror("Error", "Verifique la tasa cambiaria.")

    frame_acciones_p = ctk.CTkFrame(tab_pagos, fg_color="transparent")
    frame_acciones_p.pack(pady=15, padx=20, fill="x")
    
    btn_pagar = ctk.CTkButton(frame_acciones_p, text="Procesar Pago", fg_color="green", state="disabled", command=ejecutar_pago)
    btn_pagar.grid(row=0, column=0, padx=5)
    
    btn_salir_t3 = ctk.CTkButton(frame_acciones_p, text="Salir", fg_color="#d35400", command=ventana.destroy)
    btn_salir_t3.grid(row=0, column=1, padx=20)

    ventana.mainloop()

# =========================================================================
# COMPONENTE MODAL: AGREGAR FAMILIARES (TECLADO AUTOMÁTICO COMPLETO)
# =========================================================================
def abrir_modulo_familiares(ventana_padre, cedula_titular, v_ced, v_let, funcion_exito_refrescar):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM familiares WHERE titular_cedula = ?", (cedula_titular,))
    cantidad = cursor.fetchone()[0]
    conn.close()
    
    if cantidad >= 8:
        messagebox.showwarning("Límite", "Máximo de 8 familiares alcanzado.")
        return

    pop = ctk.CTkToplevel(ventana_padre)
    pop.title("Agregar Familiar")
    pop.geometry("420x420")
    pop.grab_set()
    
    ctk.CTkLabel(pop, text="Cédula del Familiar (O deje vacío si es menor):", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fcedula = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_ced, '%P'))
    txt_fcedula.pack(pady=2, padx=20)
    
    ctk.CTkLabel(pop, text="Nombres:", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fnombre = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fnombre.pack(pady=2, padx=20)
    
    ctk.CTkLabel(pop, text="Apellidos:", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fapellido = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fapellido.pack(pady=2, padx=20)
    
    ctk.CTkLabel(pop, text="Parentesco con el Titular:", font=("Arial", 11, "bold")).pack(pady=(10,2), padx=20, anchor="w")
    txt_fparentesco = ctk.CTkEntry(pop, width=280, validate="key", validatecommand=(v_let, '%P'))
    txt_fparentesco.pack(pady=2, padx=20)
    
    # Profesor: Forzamos a que el cursor parpadee de inmediato en la cédula al abrirse
    txt_fcedula.focus_set()

    vincular_salto_enter(txt_fcedula, txt_fnombre)
    vincular_salto_enter(txt_fnombre, txt_fapellido)
    vincular_salto_enter(txt_fapellido, txt_fparentesco)

    def guardar_familiar():
        fced = txt_fcedula.get().strip().upper()
        fnom = txt_fnombre.get().strip().lower()
        fape = txt_fapellido.get().strip().lower()
        fpar = txt_fparentesco.get().strip().lower()
        
        if not fced: fced = "MENOR"
        if not fnom or not fape or not fpar:
            messagebox.showwarning("Campos Vacíos", "Nombres, Apellidos y Parentesco son obligatorios.")
            return
            
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO familiares (cedula, nombres, apellidos, parentesco, titular_cedula) VALUES (?, ?, ?, ?, ?)",
                       (fced, fnom, fape, fpar, cedula_titular))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Éxito", "Familiar agregado correctamente.")
        funcion_exito_refrescar()
        pop.destroy()

    # Profesor: Vinculamos la tecla Enter de la última casilla (Parentesco) para guardar de una vez
    txt_fparentesco.bind("<Return>", lambda event: guardar_familiar())

    btn_fguardar = ctk.CTkButton(pop, text="Registrar Familiar", fg_color="green", command=guardar_familiar)
    btn_fguardar.pack(pady=20)