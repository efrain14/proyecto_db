import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
import sys
import os

# Asegurar que encuentre los otros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.conexion import conectar
from logic.consultas import consultar_estado_cliente

def mostrar_dashboard():
    ventana = ctk.CTk()
    ventana.title("Sistema Funerario - Panel de Control")
    ventana.geometry("900x650")
    
    # Creamos las pestañas principales
    pestanas = ctk.CTkTabview(ventana, width=860, height=600)
    pestanas.pack(pady=10, padx=10, fill="both", expand=True)
    
    tab_clientes = pestanas.add("Registro de Clientes")
    tab_pagos = pestanas.add("Control de Pagos y Estado")
    
    # =========================================================================
    # DISEÑO DE LA PESTAÑA 1: REGISTRO DE CLIENTES (TITULARES)
    # =========================================================================
    
    lbl_tit_reg = ctk.CTkLabel(tab_clientes, text="Datos del Titular del Contrato", font=("Arial", 16, "bold"))
    lbl_tit_reg.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="w")
    
    txt_cedula = ctk.CTkEntry(tab_clientes, placeholder_text="Cédula de Identidad", width=200)
    txt_cedula.grid(row=1, column=0, pady=5, padx=10, sticky="w")
    
    txt_nombres = ctk.CTkEntry(tab_clientes, placeholder_text="Nombres", width=250)
    txt_nombres.grid(row=1, column=1, pady=5, padx=10, sticky="w")
    
    txt_apellidos = ctk.CTkEntry(tab_clientes, placeholder_text="Apellidos", width=250)
    txt_apellidos.grid(row=2, column=0, pady=5, padx=10, sticky="w")
    
    txt_fecha_nac = ctk.CTkEntry(tab_clientes, placeholder_text="Fecha Nacimiento (DD-MM-YYYY)", width=200)
    txt_fecha_nac.grid(row=2, column=1, pady=5, padx=10, sticky="w")
    
    txt_telefono = ctk.CTkEntry(tab_clientes, placeholder_text="Teléfono", width=200)
    txt_telefono.grid(row=3, column=0, pady=5, padx=10, sticky="w")
    
    txt_direccion = ctk.CTkEntry(tab_clientes, placeholder_text="Dirección de Habitación", width=470)
    txt_direccion.grid(row=3, column=1, pady=5, padx=10, sticky="w")
    
    # Selección del tipo de contrato
    lbl_contrato = ctk.CTkLabel(tab_clientes, text="Tipo de Contrato:")
    lbl_contrato.grid(row=4, column=0, pady=5, padx=10, sticky="w")
    
    combo_contrato = ctk.CTkComboBox(tab_clientes, values=["Velación ($10)", "Velación + Entierro/Incineración ($20)"], width=250)
    combo_contrato.grid(row=4, column=1, pady=5, padx=10, sticky="w")
    
    def guardar_titular():
        ced = txt_cedula.get().strip()
        nom = txt_nombres.get().strip()
        ape = txt_apellidos.get().strip()
        f_nac = txt_fecha_nac.get().strip()
        tel = txt_telefono.get().strip()
        dir_hab = txt_direccion.get().strip()
        tipo_c = "velacion" if "Velación ($10)" in combo_contrato.get() else "completo"
        f_inicio = datetime.now().strftime("%d-%m-%Y") # Fecha de hoy en formato latino
        
        if not ced or not nom or not ape or not f_nac:
            messagebox.showwarning("Campos Requeridos", "Cédula, Nombres, Apellidos y Fecha de Nacimiento son obligatorios.")
            return
            
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO titulares (cedula, nombres, apellidos, fecha_nacimiento, telefono, direccion, tipo_contrato, fecha_inicio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ced, nom, ape, f_nac, tel, dir_hab, tipo_c, f_inicio))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", f"Titular {nom} registrado exitosamente.\nContrato inicia hoy: {f_inicio}")
            btn_add_fam.configure(state="normal") # Habilitar botón de familiares
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar (Posible cédula duplicada).\nDetalle: {e}")

    btn_guardar_tit = ctk.CTkButton(tab_clientes, text="Guardar Titular", fg_color="green", command=guardar_titular)
    btn_guardar_tit.grid(row=5, column=0, pady=15, padx=10, sticky="w")
    
    # Botón para añadir familiares (Inicia desactivado hasta guardar un titular)
    def abrir_ventana_familiares():
        ced_t = txt_cedula.get().strip()
        if not ced_t:
            messagebox.showwarning("Atención", "Escriba la cédula del titular guardado para asociar familiares.")
            return
        abrir_modulo_familiares(ventana, ced_t)

    btn_add_fam = ctk.CTkButton(tab_clientes, text="+ Agregar Familiares Amparados (Hasta 8)", fg_color="#1f538d", state="disabled", command=abrir_ventana_familiares)
    btn_add_fam.grid(row=5, column=1, pady=15, padx=10, sticky="w")

    # =========================================================================
    # DISEÑO DE LA PESTAÑA 2: CONTROL DE PAGOS Y ESTADO DE CUENTA
    # =========================================================================
    
    lbl_busq = ctk.CTkLabel(tab_pagos, text="Buscar Titular por Cédula:", font=("Arial", 14, "bold"))
    lbl_busq.grid(row=0, column=0, pady=10, padx=10, sticky="w")
    
    txt_busqueda_ced = ctk.CTkEntry(tab_pagos, placeholder_text="Ej: V-12345678", width=200)
    txt_busqueda_ced.grid(row=0, column=1, pady=10, padx=10, sticky="w")
    
    # Etiquetas que cambiarán dinámicamente de texto y color
    lbl_nombre_clie = ctk.CTkLabel(tab_pagos, text="Cliente: Seleccione un titular", font=("Arial", 14))
    lbl_nombre_clie.grid(row=1, column=0, columnspan=2, pady=5, padx=10, sticky="w")
    
    lbl_aviso_morosidad = ctk.CTkLabel(tab_pagos, text="ESTADO: --", font=("Arial", 16, "bold"), text_color="grey")
    lbl_aviso_morosidad.grid(row=2, column=0, columnspan=2, pady=5, padx=10, sticky="w")

    def buscar_y_calcular():
        ced = txt_busqueda_ced.get().strip()
        if not ced:
            return
            
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT nombres, apellidos FROM titulares WHERE cedula = ?", (ced,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            lbl_nombre_clie.configure(text=f"Cliente: {res[0]} {res[1]}")
            # Llamamos a nuestra lógica matemática de la Fase 2
            estado = consultar_estado_cliente(ced)
            
            if estado["moroso"]:
                lbl_aviso_morosidad.configure(text=f"ESTADO: MOROSO (Debe ${estado['deuda_usd']:.2f})", text_color="red")
            else:
                lbl_aviso_morosidad.configure(text="ESTADO: AL DÍA / SOLVENTE", text_color="green")
            
            # Habilitar campos de pago
            txt_tasa.configure(state="normal")
            btn_pagar.configure(state="normal")
        else:
            messagebox.showerror("No Encontrado", "Cédula no registrada en el sistema.")
            
    btn_buscar = ctk.CTkButton(tab_pagos, text="Buscar y Verificar", width=120, command=buscar_y_calcular)
    btn_buscar.grid(row=0, column=2, pady=10, padx=10, sticky="w")
    
    # Formulario para registrar el Pago Mensual
    lbl_secc_pago = ctk.CTkLabel(tab_pagos, text="Registrar Pago Mensual", font=("Arial", 14, "bold"))
    lbl_secc_pago.grid(row=3, column=0, pady=15, padx=10, sticky="w")
    
    txt_tasa = ctk.CTkEntry(tab_pagos, placeholder_text="Tasa BCV del día (Bs.)", width=200, state="disabled")
    txt_tasa.grid(row=4, column=0, pady=5, padx=10, sticky="w")
    
    lbl_calculo_bs = ctk.CTkLabel(tab_pagos, text="Monto a pagar: 0.00 Bs.", font=("Arial", 13, "italic"))
    lbl_calculo_bs.grid(row=4, column=1, pady=5, padx=10, sticky="w")
    
    def actualizar_calculo_bolivares(*args):
        """Calcula en tiempo real los Bs basándose en la tasa y el tipo de contrato"""
        ced = txt_busqueda_ced.get().strip()
        try:
            tasa = float(txt_tasa.get().strip())
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT tipo_contrato FROM titulares WHERE cedula = ?", (ced,))
            tipo = cursor.fetchone()[0]
            conn.close()
            
            usd = 10.0 if tipo == "velacion" else 20.0
            total_bs = usd * tasa
            lbl_calculo_bs.configure(text=f"Monto a pagar ({usd} USD): {total_bs:.2f} Bs.")
        except:
            lbl_calculo_bs.configure(text="Monto a pagar: -- Bs.")

    # Vincular que cuando escribas en la tasa, se actualice la etiqueta automáticamente
    txt_tasa.bind("<KeyRelease>", actualizar_calculo_bolivares)

    def ejecutar_pago():
        ced = txt_busqueda_ced.get().strip()
        try:
            tasa = float(txt_tasa.get().strip())
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT tipo_contrato FROM titulares WHERE cedula = ?", (ced,))
            tipo = cursor.fetchone()[0]
            
            usd = 10.0 if tipo == "velacion" else 20.0
            bs = usd * tasa
            fecha_p = datetime.now().strftime("%d-%m-%Y")
            
            cursor.execute("""
                INSERT INTO pagos (titular_cedula, monto_usd, tasa_bcv, monto_bs, fecha_pago)
                VALUES (?, ?, ?, ?, ?)
            """, (ced, usd, tasa, bs, fecha_p))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Pago Registrado", f"Pago de ${usd} ({bs:.2f} Bs.) guardado con éxito.")
            buscar_y_calcular() # Refresca la pantalla para quitar el aviso de moroso si ya pagó
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar el pago. Verifique la tasa.\n{e}")

    btn_pagar = ctk.CTkButton(tab_pagos, text="Procesar Pago", fg_color="green", state="disabled", command=ejecutar_pago)
    btn_pagar.grid(row=5, column=0, pady=10, padx=10, sticky="w")

    ventana.mainloop()

# =========================================================================
# COMPONENTE VENTANA EMERGENTE: AGREGAR FAMILIARES
# =========================================================================
def abrir_modulo_familiares(ventana_padre, cedula_titular):
    """Ventana emergente tipo Pop-up para registrar los familiares de un titular."""
    
    # Verificar cuántos familiares tiene actualmente para no pasar de 8
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM familiares WHERE titular_cedula = ?", (cedula_titular,))
    cantidad_actual = cursor.fetchone()[0]
    conn.close()
    
    if cantidad_actual >= 8:
        messagebox.showwarning("Límite Alcanzado", "Este titular ya tiene el máximo de 8 familiares amparados.")
        return

    pop = ctk.CTkToplevel(ventana_padre)
    pop.title("Agregar Familiar Amparado")
    pop.geometry("450x350")
    pop.grab_set() # Bloquea la ventana de atrás para que complete el formulario
    
    lbl_cant = ctk.CTkLabel(pop, text=f"Familiares registrados de este titular: {cantidad_actual}/8", font=("Arial", 12, "italic"))
    lbl_cant.pack(pady=5)
    
    txt_fcedula = ctk.CTkEntry(pop, placeholder_text="Cédula del Familiar", width=250)
    txt_fcedula.pack(pady=5)
    
    txt_fnombre = ctk.CTkEntry(pop, placeholder_text="Nombres", width=250)
    txt_fnombre.pack(pady=5)
    
    txt_fapellido = ctk.CTkEntry(pop, placeholder_text="Apellidos", width=250)
    txt_fapellido.pack(pady=5)
    
    txt_fparentesco = ctk.CTkEntry(pop, placeholder_text="Parentesco (Ej: Hijo, Esposa, Madre)", width=250)
    txt_fparentesco.pack(pady=5)
    
    def guardar_familiar():
        fced = txt_fcedula.get().strip()
        fnom = txt_fnombre.get().strip()
        fape = txt_fapellido.get().strip()
        fpar = txt_fparentesco.get().strip()
        
        if not fced or not fnom or not fape or not fpar:
            messagebox.showwarning("Campos Vacíos", "Todos los campos son requeridos.")
            return
            
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO familiares (cedula, nombres, apellidos, parentesco, titular_cedula)
            VALUES (?, ?, ?, ?, ?)
        """, (fced, fnom, fape, fpar, cedula_titular))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Agregado", f"{fnom} fue agregado como familiar amparado.")
        pop.destroy() # Cierra la ventanita emergente

    btn_fguardar = ctk.CTkButton(pop, text="Registrar Familiar", fg_color="green", command=guardar_familiar)
    btn_fguardar.pack(pady=15)