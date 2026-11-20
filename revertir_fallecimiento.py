"""
Revierte el fallecimiento de un afiliado (vuelve a estado VIVO).
Hace respaldo automático antes de modificar. NO borra al afiliado.
"""
import os
import sqlite3
from datetime import datetime

RUTA_DB = input("Ruta de la BD [Enter = funeraria.db de esta carpeta]: ").strip().strip('"')
if not RUTA_DB:
    RUTA_DB = "funeraria.db"

if not os.path.exists(RUTA_DB):
    print("❌ No existe:", RUTA_DB)
    input("Enter para salir...")
    raise SystemExit

CEDULA = input("Cédula del TITULAR (ej: V3923013): ").strip().upper()

con = sqlite3.connect(RUTA_DB)
c = con.cursor()

c.execute("SELECT nombres, apellidos FROM titulares WHERE cedula=?", (CEDULA,))
t = c.fetchone()
if not t:
    print("❌ No se encontró el titular:", CEDULA)
    con.close()
    input("Enter para salir...")
    raise SystemExit

print(f"\nTitular: {(t[0] or '').title()} {(t[1] or '').title()}  ({CEDULA})")

c.execute("""
    SELECT id, cedula, nombres, apellidos, parentesco, fallecido, fecha_servicio
    FROM familiares WHERE titular_cedula=? ORDER BY id
""", (CEDULA,))
afiliados = c.fetchall()

if not afiliados:
    print("Este titular no tiene afiliados registrados.")
    con.close()
    input("Enter para salir...")
    raise SystemExit

print("\n" + "=" * 80)
print(f"{'ID':<5}{'Cédula':<12}{'Nombre completo':<30}{'Parentesco':<13}{'Fallecido':<11}{'F.Servicio':<12}")
print("=" * 80)
for a in afiliados:
    nombre = f"{(a[2] or '').title()} {(a[3] or '').title()}"
    print(f"{a[0]:<5}{str(a[1] or ''):<12}{nombre:<30}{(a[4] or '').title():<13}"
          f"{'SÍ' if a[5] else 'NO':<11}{a[6] or '-':<12}")
print("=" * 80)

fallecidos = [a for a in afiliados if a[5]]
if not fallecidos:
    print("\n✅ Ningún afiliado de este titular está marcado como fallecido.")
    con.close()
    input("Enter para salir...")
    raise SystemExit

print("\nIDs marcados como fallecidos:", ", ".join(str(a[0]) for a in fallecidos))
id_txt = input("Escribe el ID del afiliado que quieres volver a VIVO: ").strip()

if not id_txt.isdigit():
    print("❌ Debes escribir un número de ID.")
    con.close()
    input("Enter para salir...")
    raise SystemExit

ID = int(id_txt)
sel = next((a for a in afiliados if a[0] == ID), None)

if not sel:
    print("❌ Ese ID no pertenece a los afiliados de este titular.")
    con.close()
    input("Enter para salir...")
    raise SystemExit

if not sel[5]:
    print("ℹ️ Ese afiliado ya está en estado VIVO. Nada que revertir.")
    con.close()
    input("Enter para salir...")
    raise SystemExit

nombre_sel = f"{(sel[2] or '').title()} {(sel[3] or '').title()}"
print(f"\nSe va a revertir: {nombre_sel} (ID {ID})")
print("  fallecido      : SÍ  ->  NO")
print(f"  fecha_servicio : {sel[6]}  ->  (vacío)")

if input("\n¿Confirmas? (s/n): ").strip().lower() != "s":
    con.close()
    print("Cancelado. No se modificó nada.")
    input("Enter para salir...")
    raise SystemExit

# Respaldo íntegro de la BD antes de escribir
respaldo = RUTA_DB.replace(".db", "") + f"_RESPALDO_{datetime.now():%Y%m%d_%H%M%S}.db"
bck = sqlite3.connect(respaldo)
con.backup(bck)
bck.close()
print("✅ Respaldo creado:", respaldo)

c.execute("UPDATE familiares SET fallecido=0, fecha_servicio=NULL WHERE id=?", (ID,))
con.commit()

c.execute("SELECT id, nombres, apellidos, fallecido, fecha_servicio FROM familiares WHERE id=?", (ID,))
r = c.fetchone()
print("\n--- RESULTADO ---")
print(f"ID {r[0]} | {(r[1] or '').title()} {(r[2] or '').title()} | "
      f"Fallecido: {'SÍ' if r[3] else 'NO'} | F. Servicio: {r[4] or '(vacío)'}")

con.close()
input("\nPresiona Enter para cerrar...")