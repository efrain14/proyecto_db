"""
PRUEBA DE MOROSIDAD - Simula titulares cuyo último pago fue hace N días.
Hace respaldo automático y BORRA los datos de prueba al terminar.
NO modifica ningún cliente real.
"""
import sqlite3
from datetime import datetime, timedelta
from database.conexion import conectar, obtener_ruta_db
from logic.consultas import consultar_estado_cliente

RUTA = obtener_ruta_db()
print("Base de datos:", RUTA)

# ---------- Respaldo ----------
respaldo = RUTA.replace(".db", "") + f"_RESPALDO_PRUEBA_{datetime.now():%Y%m%d_%H%M%S}.db"
orig = sqlite3.connect(RUTA)
bck = sqlite3.connect(respaldo)
orig.backup(bck)
bck.close()
orig.close()
print("Respaldo creado:", respaldo)

ESCENARIOS = [25, 30, 31, 35, 40, 65]
PRUEBAS = []

conn = conectar()
cur = conn.cursor()

try:
    # ---------- Crear titulares de prueba ----------
    for i, dias in enumerate(ESCENARIOS, start=1):
        ced = f"V999999{i:02d}"
        PRUEBAS.append(ced)
        hace = datetime.now() - timedelta(days=dias)
        cur.execute("""
            INSERT INTO titulares
                (cedula, contrato_viejo, contrato_nuevo, nombres, apellidos,
                 fecha_nacimiento, telefono, correo, direccion, tipo_contrato,
                 fecha_inicio, recibos_previos, notas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (ced, "", f"TEST-{i:03d}", "prueba", "morosidad",
              "01/01/1980", "", "", "", "PPA velación 24 meses",
              hace.strftime("%d/%m/%Y"), 0,
              "REGISTRO DE PRUEBA - SE BORRA AUTOMATICAMENTE"))
        cur.execute("""
            INSERT INTO pagos
                (num_recibo, titular_cedula, fecha_pago, monto_usd, monto_bs,
                 tasa_bcv, forma_pago, banco_origen, banco_destino,
                 num_operacion, cuota_numero)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (999990 + i, ced, hace.strftime("%Y-%m-%d"),
              10.0, 1000.0, 100.0, "Efectivo USD", "", "", "", 1))
    conn.commit()

    # ---------- Consultar el estado ----------
    print("\n" + "=" * 90)
    print(f"{'Días desde último pago':<24}{'moroso':<10}{'deuda_usd':<12}Lo que verías en pantalla")
    print("=" * 90)

    for i, dias in enumerate(ESCENARIOS, start=1):
        ced = f"V999999{i:02d}"
        try:
            est = consultar_estado_cliente(ced)
        except Exception as e:
            print(f"{dias:<24}ERROR: {e}")
            continue

        if not isinstance(est, dict) or "error" in est:
            print(f"{dias:<24}{est}")
            continue

        if est.get("moroso"):
            pantalla = f'ESTADO: MOROSO (Debe ${est["deuda_usd"]:.2f})  [ROJO]'
        elif est.get("deuda_usd", 0) > 0:
            pantalla = 'ESTADO: AL DÍA / SOLVENTE (Pendiente próxima cuota)  [NARANJA]'
        else:
            pantalla = 'ESTADO: AL DÍA / SOLVENTE (Sin cuotas pendientes)  [VERDE]'

        print(f"{dias:<24}{str(est.get('moroso')):<10}{est.get('deuda_usd', 0):<12.2f}{pantalla}")

        if dias == 35:
            print("\n  >>> Diccionario COMPLETO con 35 días:")
            print("  ", est, "\n")

    print("=" * 90)

finally:
    # ---------- Limpieza SIEMPRE, incluso si hubo error ----------
    for ced in PRUEBAS:
        cur.execute("DELETE FROM pagos WHERE titular_cedula=?", (ced,))
        cur.execute("DELETE FROM familiares WHERE titular_cedula=?", (ced,))
        cur.execute("DELETE FROM titulares WHERE cedula=?", (ced,))
    conn.commit()
    conn.close()
    print("\n✅ Registros de prueba eliminados. Ningún cliente real fue modificado.")

input("\nPresiona Enter para cerrar...")