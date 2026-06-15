from datetime import datetime
import sys
import os

# Esto permite que este archivo pueda encontrar la carpeta 'database' que está al mismo nivel
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.conexion import conectar

def obtener_meses_transcurridos(fecha_inicio_str):
    """Calcula cuántos meses han pasado desde la fecha de inicio hasta hoy."""
    # CAMBIO AQUÍ: Ahora convertimos usando el formato Latinoamericano DD-MM-YYYY
    fecha_inicio = datetime.strptime(fecha_inicio_str, "%d-%m-%Y")
    fecha_hoy = datetime.now()
    
    # Fórmula matemática para calcular la diferencia en meses exactos
    meses = (fecha_hoy.year - fecha_inicio.year) * 12 + (fecha_hoy.month - fecha_inicio.month)
    
    # Si el contrato empezó hoy o este mes, contamos al menos 1 mes (el mes en curso)
    if meses <= 0:
        return 1
    
    # Si ya pasó el día del mes de cobro, sumamos el mes en curso
    if fecha_hoy.day >= fecha_inicio.day:
        return meses + 1
    
    return meses

def consultar_estado_cliente(cedula_titular):
    """
    Calcula la deuda actual en dólares del cliente y determina si está moroso.
    Devuelve un diccionario con los datos del estado.
    """
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Obtener los datos del contrato del titular
    cursor.execute("SELECT tipo_contrato, fecha_inicio FROM titulares WHERE cedula = ?", (cedula_titular,))
    titular = cursor.fetchone()
    
    if not titular:
        conn.close()
        return {"error": "Cliente no encontrado"}
    
    tipo_contrato, fecha_inicio_str = titular
    # Asignamos el precio según el tipo de contrato
    costo_mensual = 10.0 if tipo_contrato == "velacion" else 20.0
    
    # 2. Calcular cuántos meses debe llevar pagados hasta hoy
    meses_totales = obtener_meses_transcurridos(fecha_inicio_str)
    total_a_pagar_usd = meses_totales * costo_mensual
    
    # 3. Sumar todos los pagos que ya ha hecho el cliente en dólares
    cursor.execute("SELECT SUM(monto_usd) FROM pagos WHERE titular_cedula = ?", (cedula_titular,))
    resultado_pagos = cursor.fetchone()[0]
    total_pagado_usd = resultado_pagos if resultado_pagos is not None else 0.0
    
    # 4. Calcular la deuda
    deuda_usd = total_a_pagar_usd - total_pagado_usd
    
    conn.close()
    
    if deuda_usd < 0:
        deuda_usd = 0.0
        
    es_moroso = deuda_usd > 0
    
    return {
        "meses_transcurridos": meses_totales,
        "total_debido_usd": total_a_pagar_usd,
        "total_pagado_usd": total_pagado_usd,
        "deuda_usd": deuda_usd,
        "moroso": es_moroso
    }