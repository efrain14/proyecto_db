from datetime import datetime
import sys
import os

# Esto permite que este archivo pueda encontrar la carpeta 'database' que está al mismo nivel
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.conexion import conectar

def obtener_meses_transcurridos(fecha_inicio_str):
    """Calcula cuántos meses han pasado desde la fecha de inicio hasta hoy."""
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%d/%m/%Y")
    except Exception:
        return 1
        
    fecha_hoy = datetime.now()
    meses = (fecha_hoy.year - fecha_inicio.year) * 12 + (fecha_hoy.month - fecha_inicio.month)
    
    if meses <= 0:
        return 1
    
    # Solo incrementamos el mes exigible si ya pasó el día del mes de cobro
    if fecha_hoy.day > fecha_inicio.day:
        return meses + 1
    
    return meses

def consultar_estado_cliente(cedula_titular):
    """
    Calcula la deuda actual en dólares del cliente contemplando recibos previos e historial.
    Determina morosidad considerando el vencimiento mensual de 30 días.
    """
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT tipo_contrato, fecha_inicio, recibos_previos 
        FROM titulares 
        WHERE cedula = ?
    """, (cedula_titular,))
    titular = cursor.fetchone()
    
    if not titular:
        conn.close()
        return {"error": "Cliente no encontrado"}
    
    tipo_contrato, fecha_inicio_str, r_previos = titular
    recibos_previos = r_previos or 0
    
    tipo_lower = (tipo_contrato or "").lower()
    if "entierro" in tipo_lower:
        costo_mensual = 20.0
    elif "renovación" in tipo_lower or "renovacion" in tipo_lower:
        costo_mensual = 12.0
    else:
        costo_mensual = 10.0
    
    # Calcular meses exigibles por tiempo transcurrido
    meses_totales = obtener_meses_transcurridos(fecha_inicio_str or datetime.now().strftime("%d/%m/%Y"))
    
    # Limitar cuotas exigibles del plan si es PPA 24 meses
    if "24 meses" in tipo_lower:
        cuotas_exigibles = min(24, meses_totales)
    else:
        cuotas_exigibles = meses_totales
        
    # Obtener historial de pagos en sistema
    cursor.execute("""
        SELECT COUNT(*), SUM(monto_usd) 
        FROM pagos 
        WHERE titular_cedula = ?
    """, (cedula_titular,))
    res_pagos = cursor.fetchone()
    pagos_cnt = res_pagos[0] or 0
    pagos_sum = res_pagos[1] or 0.0
    
    total_cuotas_pagadas = recibos_previos + pagos_cnt
    total_pagado_usd = (recibos_previos * costo_mensual) + pagos_sum
    
    cuotas_debitables = max(0, cuotas_exigibles - total_cuotas_pagadas)
    deuda_usd = cuotas_debitables * costo_mensual
    
    conn.close()
    
    # Es moroso solo si debe MÁS de 1 cuota vencida (pasaron más de 30 días sin pagar la cuota anterior)
    es_moroso = cuotas_debitables > 1
    
    return {
        "meses_transcurridos": cuotas_exigibles,
        "cuotas_pagadas": total_cuotas_pagadas,
        "total_debido_usd": cuotas_exigibles * costo_mensual,
        "total_pagado_usd": total_pagado_usd,
        "deuda_usd": deuda_usd,
        "moroso": es_moroso
    }