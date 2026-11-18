"""
Diagnóstico de cuotas de un titular.
SOLO LECTURA: no modifica ni borra nada de la base de datos.
"""
import sqlite3

CEDULA = input("Cédula del titular a revisar (ej: V3923013): ").strip().upper()

con = sqlite3.connect("funeraria.db")
c = con.cursor()

c.execute("SELECT tipo_contrato, recibos_previos FROM titulares WHERE cedula=?", (CEDULA,))
t = c.fetchone()

if not t:
    print("\n❌ No se encontró ningún titular con la cédula:", CEDULA)
else:
    plan = t[0] or ""
    previos = t[1] or 0

    print("\n" + "=" * 62)
    print("PLAN ACTUAL     :", plan)
    print("RECIBOS PREVIOS :", previos)
    print("=" * 62)

    c.execute("""
        SELECT num_recibo, fecha_pago, cuota_numero, monto_usd
        FROM pagos WHERE titular_cedula=? ORDER BY id
    """, (CEDULA,))
    pagos = c.fetchall()

    print("PAGOS REGISTRADOS EN EL SISTEMA:", len(pagos))
    print("-" * 62)
    print(f"{'N°':<4}{'Recibo':<10}{'Fecha':<13}{'Cuota':<8}{'Total acum.':<13}{'USD':<8}")
    print("-" * 62)

    for i, p in enumerate(pagos, 1):
        print(f"{i:<4}{str(p[0]):<10}{str(p[1]):<13}{str(p[2]):<8}{previos + i:<13}{p[3]:.2f}")

    print("-" * 62)
    print("TOTAL ACUMULADO (previos + sistema):", previos + len(pagos))

    # Detectar el síntoma del bug: varias cuotas marcadas como 24
    cuotas24 = [p[0] for p in pagos if p[2] == 24]
    if len(cuotas24) > 1:
        print(f"\n⚠️  ATENCIÓN: hay {len(cuotas24)} pagos marcados con cuota 24.")
        print("   Recibos afectados:", cuotas24)
    else:
        print("\n✅ No hay cuotas 24 duplicadas en el histórico.")

con.close()
input("\nPresiona Enter para cerrar...")