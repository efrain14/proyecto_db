from logic.consultas import consultar_estado_cliente
from database.conexion import conectar
import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
import sys
import os

# Asegurar que encuentre los otros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# =========================================================================
# FUNCIONES DE VALIDACIÓN Y MÁSCARAS (Para evitar errores de escritura)
# =========================================================================


def validar_cedula_titular(texto_actualizado):
    """Solo permite una V o E al inicio, seguida de hasta 8 números enteros."""
    if texto_actualizado == "":
        return True

    # El primer carácter obligatorio debe ser V, v, E o e
    primer_caracter = texto_actualizado[0].upper()
    if primer_caracter not in ['V', 'E']:
        return False

    # El resto deben ser solo números enteros y máximo 8 dígitos (Total 9 caracteres)
    if len(texto_actualizado) > 1:
        resto_texto = texto_actualizado[1:]
        if not resto_texto.isdigit() or len(resto_texto) > 8:
            return False

    return True


def validar_cedula_familiar(texto_actualizado):
    """Igual al del titular pero permite escribir la palabra 'MENOR' o dejar vacío."""
    if texto_actualizado == "":
        return True

    # Permitir que escriba 'MENOR' para niños sin cédula
    if "MENOR".startswith(texto_actualizado.upper()):
        return True

    primer_caracter = texto_actualizado[0].upper()
    if primer_caracter not in ['V', 'E']:
        return False

    if len(texto_actualizado) > 1:
        resto_texto = texto_actualizado[1:]
        if not resto_texto.isdigit() or len(resto_texto) > 8:
            return False

    return True


def validar_solo_letras(texto_actualizado):
    """Impide que el usuario escriba números o símbolos en nombres y apellidos."""
    if texto_actualizado == "":
        return True
    # Reemplazamos los espacios para permitir nombres compuestos (ej: Juan Carlos)
    return texto_actualizado.replace(" ", "").isalpha()


def calcular_edad_exacta(fecha_str):
    """Calcula los años basándose en la fecha DD-MM-YYYY."""
    try:
        fecha_nac = datetime.strptime(fecha_str, "%d-%m-%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nac.year - \
            ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        return edad if edad >= 0 else None
    except ValueError:
        return None

# =========================================================================
# INTERFAZ GRÁFICA PRINCIPAL
# =========================================================================


def mostrar_dashboard():
    ventana = ctk.CTk()
    ventana.title("Sistema Funerario - Panel de Control")
    ventana.geometry("1000x700")

    # Registrar funciones de validación en el sistema de Tkinter
    v_ced_tit = ventana.register(validar_cedula_titular)
    v_ced_fam = ventana.register(validar_cedula_familiar)
    v_letras = ventana.register(validar_solo_letras)

    # Estilo para la tabla tipo Excel (Treeview)
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#2a2a2a",
                    foreground="white", fieldbackground="#2a2a2a", rowheight=25)
    style.map("Treeview", background=[('selected', '#1f538d')])
    style.configure("Treeview.Heading", background="#1f538d",
                    foreground="white", font=("Arial", 10, "bold"))

    pestanas = ctk.CTkTabview(ventana, width=960, height=650)
    pestanas.pack(pady=10, padx=10, fill="both", expand=True)

    tab_clientes = pestanas.add("Registro de Clientes")
    tab_edicion = pestanas.add("Edición de Titulares")
    tab_pagos = pestanas.add("Control de Pagos y Estado")

    # =========================================================================
    # PESTAÑA 1: REGISTRO DE CLIENTES
    # =========================================================================

    lbl_tit_reg = ctk.CTkLabel(
        tab_clientes, text="Datos del Titular del Contrato", font=("Arial", 16, "bold"))
    lbl_tit_reg.grid(row=0, column=0, columnspan=3,
                     pady=10, padx=10, sticky="w")

    # Aplicando validaciones a los campos con validate="key"
    txt_cedula = ctk.CTkEntry(tab_clientes, placeholder_text="Cédula (Ej: V12345678)",
                              width=180, validate="key", validatecommand=(v_ced_tit, '%P'))
    txt_cedula.grid(row=1, column=0, pady=5, padx=10, sticky="w")

    txt_nombres = ctk.CTkEntry(tab_clientes, placeholder_text="Nombres",
                               width=220, validate="key", validatecommand=(v_letras, '%P'))
    txt_nombres.grid(row=1, column=1, pady=5, padx=10, sticky="w")

    txt_apellidos = ctk.CTkEntry(tab_clientes, placeholder_text="Apellidos",
                                 width=220, validate="key", validatecommand=(v_letras, '%P'))
    txt_apellidos.grid(row=1, column=2, pady=5, padx=10, sticky="w")

    txt_fecha_nac = ctk.CTkEntry(
        tab_clientes, placeholder_text="Nacimiento (DD-MM-YYYY)", width=180)
    txt_fecha_nac.grid(row=2, column=0, pady=5, padx=10, sticky="w")

    lbl_edad_titular = ctk.CTkLabel(
        tab_clientes, text="Edad: -- años", font=("Arial", 12, "bold"), text_color="#1f538d")
    lbl_edad_titular.grid(row=2, column=1, pady=5, padx=10, sticky="w")

    def disparar_calculo_edad(*args):
        texto = txt_fecha_nac.get().strip()
        if len(texto) == 10:
            edad = calcular_edad_exacta(texto)
            if edad is not None:
                lbl_edad_titular.configure(text=f"Edad: {edad} años")
            else:
                lbl_edad_titular.configure(text="Edad: Inválida")
    txt_fecha_nac.bind("<KeyRelease>", disparar_calculo_edad)

    txt_telefono = ctk.CTkEntry(
        tab_clientes, placeholder_text="Teléfono", width=180)
    txt_telefono.grid(row=3, column=0, pady=5, padx=10, sticky="w")

    txt_correo = ctk.CTkEntry(
        tab_clientes, placeholder_text="Correo Electrónico", width=220)
    txt_correo.grid(row=3, column=1, pady=5, padx=10, sticky="w")

    txt_direccion = ctk.CTkEntry(
        tab_clientes, placeholder_text="Dirección Completa de Habitación", width=450)
    txt_direccion.grid(row=4, column=0, columnspan=2,
                       pady=5, padx=10, sticky="w")

    combo_contrato = ctk.CTkComboBox(
        tab_clientes, values=["Velación ($10)", "Velación + Entierro ($20)"], width=220)
    combo_contrato.grid(row=4, column=2, pady=5, padx=10, sticky="w")

    # --- TABLA EXCEL (TREEVIEW) PARA FAMILIARES ---
    lbl_fam_tab = ctk.CTkLabel(
        tab_clientes, text="Familiares Amparados Asociados:", font=("Arial", 13, "bold"))
    lbl_fam_tab.grid(row=5, column=0, columnspan=3,
                     pady=(15, 2), padx=10, sticky="w")

    tabla_frame = ctk.CTkFrame(tab_clientes)
    tabla_frame.grid(row=6, column=0, columnspan=3,
                     pady=5, padx=10, sticky="nsew")

    tabla = ttk.Treeview(tabla_frame, columns=(
        "cedula", "nombres", "apellidos", "parentesco"), show="headings", height=5)
    tabla.heading("cedula", text="Cédula / Identificador")
    tabla.heading("nombres", text="Nombres")
    tabla.heading("apellidos", text="Apellidos")
    tabla.heading("parentesco", text="Parentesco")
    tabla.column("cedula", width=150, anchor="center")
    tabla.column("nombres", width=220)
    tabla.column("apellidos", width=220)
    tabla.column("parentesco", width=150, anchor="center")
    tabla.pack(fill="both", expand=True)

    def refrescar_tabla_familiares(ced_t):
        # Limpiar tabla
        for item in tabla.get_children():
            tabla.delete(item)
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT cedula, nombres, apellidos, parentesco FROM familiares WHERE titular_cedula = ?", (ced_t,))
        for fila in cursor.fetchall():
            # Mostramos en la tabla convirtiendo la primera letra en mayúscula visualmente para estética
            tabla.insert("", "end", values=(
                fila[0].upper(), fila[1].title(), fila[2].title(), fila[3].title()))
        conn.close()

    def guardar_titular():
        ced = txt_cedula.get().strip().upper()
        # NORMALIZACIÓN: Guardamos todo estrictamente en minúsculas a la Base de Datos
        nom = txt_nombres.get().strip().lower()
        ape = txt_apellidos.get().strip().lower()
        f_nac = txt_fecha_nac.get().strip()
        tel = txt_telefono.get().strip()
        corr = txt_correo.get().strip().lower()
        dir_hab = txt_direccion.get().strip().lower()
        tipo_c = "velacion" if "Velación ($10)" in combo_contrato.get(
        ) else "completo"
        f_inicio = datetime.now().strftime("%d-%m-%Y")

        if not ced or not nom or not ape or not f_nac:
            messagebox.showwarning(
                "Campos Requeridos", "Cédula, Nombres, Apellidos y Fecha de Nacimiento son obligatorios.")
            return

        try:
            conn = conectar()
            cursor = conn.cursor()
            # Añadir columna correo a la consulta de guardado
            # Nota: Al final del script te enseño cómo actualizar tu base de datos existente para que acepte el correo
            cursor.execute("""
                INSERT INTO titulares (cedula, nombres, apellidos, fecha_nacimiento, telefono, direccion, tipo_contrato, fecha_inicio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ced, nom, ape, f_nac, tel, dir_hab, tipo_c, f_inicio))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", f"Titular registrado exitosamente.")
            btn_add_fam.configure(state="normal")
            refrescar_tabla_familiares(ced)
        except Exception as e:
            messagebox.showerror(
                "Error", f"No se pudo guardar. Verifique si la cédula ya existe.")

    btn_guardar_tit = ctk.CTkButton(
        tab_clientes, text="Guardar Titular", fg_color="green", command=guardar_titular)
    btn_guardar_tit.grid(row=7, column=0, pady=10, padx=10, sticky="w")

    def abrir_ventana_familiares():
        ced_t = txt_cedula.get().strip().upper()
        if not ced_t:
            messagebox.showwarning(
                "Atención", "Ingrese una cédula de titular.")
            return
        abrir_modulo_familiares(
            ventana, ced_t, v_ced_fam, v_letras, lambda: refrescar_tabla_familiares(ced_t))

    btn_add_fam = ctk.CTkButton(tab_clientes, text="+ Agregar Familiar Amparado",
                                fg_color="#1f538d", state="disabled", command=abrir_ventana_familiares)
    btn_add_fam.grid(row=7, column=1, pady=10, padx=10, sticky="w")

    # =========================================================================
    # PESTAÑA 2: EDICIÓN Y EDICIÓN DE TITULARES (CRUD COMPLETO)
    # =========================================================================
    lbl_busq_ed = ctk.CTkLabel(
        tab_edicion, text="Buscar Titular para Modificar (Cédula, Nombre o Apellido):")
    lbl_busq_ed.grid(row=0, column=0, columnspan=2,
                     pady=10, padx=10, sticky="w")

    txt_busq_ed = ctk.CTkEntry(
        tab_edicion, placeholder_text="Escriba el criterio de búsqueda...", width=300)
    txt_busq_ed.grid(row=1, column=0, pady=5, padx=10, sticky="w")

    # Campos destinados a la edición
    txt_ed_tel = ctk.CTkEntry(
        tab_edicion, placeholder_text="Modificar Teléfono", width=200)
    txt_ed_tel.grid(row=2, column=0, pady=10, padx=10, sticky="w")

    txt_ed_dir = ctk.CTkEntry(
        tab_edicion, placeholder_text="Modificar Dirección", width=400)
    txt_ed_dir.grid(row=2, column=1, pady=10, padx=10, sticky="w")

    def buscar_titular_editar():
        criterio = txt_busq_ed.get().strip().lower()
        if not criterio:
            return

        conn = conectar()
        cursor = conn.cursor()
        # Buscamos coincidencias aproximadas por Cédula, Nombre o Apellido usando LIKE de SQL
        cursor.execute("""
            SELECT cedula, telefono, direccion FROM titulares 
            WHERE cedula LIKE ? OR nombres LIKE ? OR apellidos LIKE ?
        """, (f"%{criterio}%", f"%{criterio}%", f"%{criterio}%"))
        res = cursor.fetchone()
        conn.close()

        if res:
            # Rellenamos los campos con la información actual para proceder a editar
            txt_busq_ed.delete(0, "end")
            # Congelamos la cédula encontrada ahí
            txt_busq_ed.insert(0, res[0])
            txt_ed_tel.delete(0, "end")
            txt_ed_tel.insert(0, res[1] if res[1] else "")
            txt_ed_dir.delete(0, "end")
            txt_ed_dir.insert(0, res[2] if res[2] else "")
            btn_actualizar.configure(state="normal")
            messagebox.showinfo(
                "Encontrado", f"Titular Cédula {res[0]} cargado listo para editar.")
        else:
            messagebox.showerror("Error", "No se encontraron resultados.")

    btn_bus_ed = ctk.CTkButton(
        tab_edicion, text="Buscar", width=100, command=buscar_titular_editar)
    btn_bus_ed.grid(row=1, column=1, pady=5, padx=10, sticky="w")

    def actualizar_datos_titular():
        ced = txt_busq_ed.get().strip()
        tel = txt_ed_tel.get().strip()
        dir_h = txt_ed_dir.get().strip().lower()

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE titulares SET telefono = ?, direccion = ? WHERE cedula = ?", (tel, dir_h, ced))
        conn.commit()
        conn.close()
        messagebox.showinfo("Éxito", "Datos del contrato actualizados.")
        btn_actualizar.configure(state="disabled")

    btn_actualizar = ctk.CTkButton(tab_edicion, text="Guardar Cambios",
                                   fg_color="green", state="disabled", command=actualizar_datos_titular)
    btn_actualizar.grid(row=3, column=0, pady=10, padx=10)

    # =========================================================================
    # PESTAÑA 3: CONTROL DE PAGOS E HISTORIAL (CON ÚLTIMO PAGO EN VIVO)
    # =========================================================================
    lbl_busq = ctk.CTkLabel(
        tab_pagos, text="Buscar Titular por Cédula:", font=("Arial", 14, "bold"))
    lbl_busq.grid(row=0, column=0, pady=10, padx=10, sticky="w")

    txt_busqueda_ced = ctk.CTkEntry(
        tab_pagos, placeholder_text="Ej: V12345678", width=200)
    txt_busqueda_ced.grid(row=0, column=1, pady=10, padx=10, sticky="w")

    lbl_nombre_clie = ctk.CTkLabel(
        tab_pagos, text="Cliente: Seleccione un titular", font=("Arial", 14, "bold"))
    lbl_nombre_clie.grid(row=1, column=0, columnspan=2,
                         pady=5, padx=10, sticky="w")

    lbl_aviso_morosidad = ctk.CTkLabel(
        tab_pagos, text="ESTADO: --", font=("Arial", 16, "bold"), text_color="grey")
    lbl_aviso_morosidad.grid(
        row=2, column=0, columnspan=2, pady=5, padx=10, sticky="w")

    # --- CUADRO RECUADRO VISUAL: ÚLTIMO PAGO REALIZADO ---
    frame_ultimo_pago = ctk.CTkFrame(
        tab_pagos, border_width=2, border_color="#1f538d")
    frame_ultimo_pago.grid(row=3, column=0, columnspan=3,
                           pady=10, padx=10, sticky="ew")

    lbl_up_tit = ctk.CTkLabel(frame_ultimo_pago, text="INFORMACIÓN DEL ÚLTIMO PAGO REGISTRADO", font=(
        "Arial", 11, "bold", "underline"))
    lbl_up_tit.pack(pady=2, padx=10, anchor="w")

    lbl_up_detalles = ctk.CTkLabel(
        frame_ultimo_pago, text="Fecha: --  |  Monto: -- USD  |  Total Cancelado en Bs: -- Bs.", font=("Arial", 12, "italic"))
    lbl_up_detalles.pack(pady=5, padx=10, anchor="w")

    def buscar_y_calcular():
        ced = txt_busqueda_ced.get().strip().upper()
        if not ced:
            return

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nombres, apellidos FROM titulares WHERE cedula = ?", (ced,))
        res = cursor.fetchone()

        if res:
            lbl_nombre_clie.configure(
                text=f"Cliente: {res[0].upper()} {res[1].upper()}")
            estado = consultar_estado_cliente(ced)

            if estado["moroso"]:
                lbl_aviso_morosidad.configure(
                    text=f"ESTADO: MOROSO (Debe ${estado['deuda_usd']:.2f})", text_color="red")
            else:
                lbl_aviso_morosidad.configure(
                    text="ESTADO: AL DÍA / SOLVENTE", text_color="green")

            # CONSULTAR EL ÚLTIMO PAGO EN LA BASE DE DATOS
            cursor.execute("""
                SELECT fecha_pago, monto_usd, monto_bs FROM pagos 
                WHERE titular_cedula = ? ORDER BY id DESC LIMIT 1
            """, (ced,))
            u_pago = cursor.fetchone()

            if u_pago:
                lbl_up_detalles.configure(
                    text=f"Fecha: {u_pago[0]}  |  Monto: ${u_pago[1]:.2f} USD  |  Equivalente Cobrado: {u_pago[2]:.2f} Bs.")
            else:
                lbl_up_detalles.configure(
                    text="Fecha: NINGUNA  |  Monto: No registra pagos anteriores.")

            txt_tasa.configure(state="normal")
            btn_pagar.configure(state="normal")
        else:
            messagebox.showerror("No Encontrado", "Cédula no registrada.")
        conn.close()

    btn_buscar = ctk.CTkButton(
        tab_pagos, text="Buscar y Verificar", width=120, command=buscar_y_calcular)
    btn_buscar.grid(row=0, column=2, pady=10, padx=10, sticky="w")

    # Formulario para registrar el Pago
    txt_tasa = ctk.CTkEntry(
        tab_pagos, placeholder_text="Tasa BCV del día (Bs.)", width=200, state="disabled")
    txt_tasa.grid(row=4, column=0, pady=15, padx=10, sticky="w")

    lbl_calculo_bs = ctk.CTkLabel(
        tab_pagos, text="Monto a pagar: 0.00 Bs.", font=("Arial", 13, "italic"))
    lbl_calculo_bs.grid(row=4, column=1, pady=15, padx=10, sticky="w")

    def actualizar_calculo_bolivares(*args):
        ced = txt_busqueda_ced.get().strip().upper()
        try:
            tasa = float(txt_tasa.get().strip())
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tipo_contrato FROM titulares WHERE cedula = ?", (ced,))
            tipo = cursor.fetchone()[0]
            conn.close()
            usd = 10.0 if tipo == "velacion" else 20.0
            lbl_calculo_bs.configure(
                text=f"Monto a pagar ({usd} USD): {usd * tasa:.2f} Bs.")
        except:
            lbl_calculo_bs.configure(text="Monto a pagar: -- Bs.")

    txt_tasa.bind("<KeyRelease>", actualizar_calculo_bolivares)

    def ejecutar_pago():
        ced = txt_busqueda_ced.get().strip().upper()
        try:
            tasa = float(txt_tasa.get().strip())
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tipo_contrato FROM titulares WHERE cedula = ?", (ced,))
            tipo = cursor.fetchone()[0]
            usd = 10.0 if tipo == "velacion" else 20.0
            bs = usd * tasa
            fecha_p = datetime.now().strftime("%d-%m-%Y")

            cursor.execute("INSERT INTO pagos (titular_cedula, monto_usd, tasa_bcv, monto_bs, fecha_pago) VALUES (?, ?, ?, ?, ?)",
                           (ced, usd, tasa, bs, fecha_p))
            conn.commit()
            conn.close()
            messagebox.showinfo("Pago Registrado",
                                "El cobro se completó correctamente.")
            buscar_y_calcular()
        except:
            messagebox.showerror(
                "Error", "Revise el valor de la tasa cambiaria introducida.")

    btn_pagar = ctk.CTkButton(tab_pagos, text="Procesar Pago",
                              fg_color="green", state="disabled", command=ejecutar_pago)
    btn_pagar.grid(row=5, column=0, pady=10, padx=10, sticky="w")

    ventana.mainloop()

# =========================================================================
# VENTANA EMERGENTE POP-UP: AGREGAR FAMILIARES (VALIDADO)
# =========================================================================


def abrir_modulo_familiares(ventana_padre, cedula_titular, v_ced, v_let, funcion_exito_refrescar):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM familiares WHERE titular_cedula = ?", (cedula_titular,))
    cantidad = cursor.fetchone()[0]
    conn.close()

    if cantidad >= 8:
        messagebox.showwarning("Límite", "Máximo de 8 familiares alcanzado.")
        return

    pop = ctk.CTkToplevel(ventana_padre)
    pop.title("Agregar Familiar")
    pop.geometry("400x380")
    pop.grab_set()

    txt_fcedula = ctk.CTkEntry(pop, placeholder_text="Cédula (O escriba MENOR)",
                               width=250, validate="key", validatecommand=(v_ced, '%P'))
    txt_fcedula.pack(pady=10)

    txt_fnombre = ctk.CTkEntry(pop, placeholder_text="Nombres",
                               width=250, validate="key", validatecommand=(v_let, '%P'))
    txt_fnombre.pack(pady=10)

    txt_fapellido = ctk.CTkEntry(pop, placeholder_text="Apellidos",
                                 width=250, validate="key", validatecommand=(v_let, '%P'))
    txt_fapellido.pack(pady=10)

    txt_fparentesco = ctk.CTkEntry(pop, placeholder_text="Parentesco (Ej: Hijo, Esposa)",
                                   width=250, validate="key", validatecommand=(v_let, '%P'))
    txt_fparentesco.pack(pady=10)

    def guardar_familiar():
        fced = txt_fcedula.get().strip().upper()
        fnom = txt_fnombre.get().strip().lower()
        fape = txt_fapellido.get().strip().lower()
        fpar = txt_fparentesco.get().strip().lower()

        # Si no tiene cédula, le asignamos por defecto la palabra MENOR
        if not fced:
            fced = "MENOR"

        if not fnom or not fape or not fpar:
            messagebox.showwarning(
                "Campos Vacíos", "Nombres, Apellidos y Parentesco son obligatorios.")
            return

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO familiares (cedula, nombres, apellidos, parentesco, titular_cedula) VALUES (?, ?, ?, ?, ?)",
                       (fced, fnom, fape, fpar, cedula_titular))
        conn.commit()
        conn.close()

        messagebox.showinfo(
            "Éxito", "Familiar agregado al amparo de la póliza.")
        # Llama a recargar la tabla tipo Excel de la ventana principal
        funcion_exito_refrescar()
        pop.destroy()

    btn_fguardar = ctk.CTkButton(
        pop, text="Registrar Familiar", fg_color="green", command=guardar_familiar)
    btn_fguardar.pack(pady=15)
