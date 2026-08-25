import sqlite3
import os
import shutil
from datetime import datetime

DB = "funeraria.db"


def hacer_backup_previo():
    if os.path.exists(DB):
        nombre_backup = f"funeraria_pre_migracion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(DB, nombre_backup)
        print(f"✔ Backup de seguridad creado: {nombre_backup}")
    else:
        print("⚠ No existe funeraria.db todavía. Se creará una base nueva si hace falta.")


def tabla_existe(cursor, nombre_tabla):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name = ?
    """, (nombre_tabla,))

    return cursor.fetchone() is not None


def columna_existe(cursor, nombre_tabla, nombre_columna):
    cursor.execute(f"PRAGMA table_info({nombre_tabla})")
    columnas = cursor.fetchall()

    for col in columnas:
        if col[1] == nombre_columna:
            return True

    return False


def agregar_columna(cursor, nombre_tabla, nombre_columna, tipo_columna):
    if not tabla_existe(cursor, nombre_tabla):
        print(f"⚠ La tabla {nombre_tabla} no existe. No se agregó {nombre_columna}.")
        return

    if columna_existe(cursor, nombre_tabla, nombre_columna):
        print(f"✔ La columna {nombre_columna} ya existe en {nombre_tabla}.")
        return

    cursor.execute(f"""
        ALTER TABLE {nombre_tabla}
        ADD COLUMN {nombre_columna} {tipo_columna}
    """)

    print(f"✔ Columna agregada: {nombre_tabla}.{nombre_columna}")


def crear_tablas_basicas_si_no_existen(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            contrasena TEXT,
            rol TEXT DEFAULT 'operador'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS titulares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT,
            contrato_viejo TEXT,
            contrato_nuevo TEXT,
            nombres TEXT,
            apellidos TEXT,
            fecha_nacimiento TEXT,
            telefono TEXT,
            correo TEXT,
            direccion TEXT,
            tipo_contrato TEXT,
            fecha_inicio TEXT,
            recibos_previos INTEGER DEFAULT 0,
            fecha_contrato_anterior TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS familiares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT,
            nombres TEXT,
            apellidos TEXT,
            parentesco TEXT,
            fecha_nacimiento TEXT,
            titular_cedula TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_recibo TEXT,
            titular_cedula TEXT,
            fecha_pago TEXT,
            monto_usd REAL,
            monto_bs REAL,
            tasa_bcv REAL,
            forma_pago TEXT,
            banco_origen TEXT,
            banco_destino TEXT,
            num_operacion TEXT,
            cuota_numero INTEGER
        )
    """)

    print("✔ Verificación/creación de tablas básicas completada.")


def crear_usuario_admin_si_no_existe(cursor):
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]

    if total_usuarios == 0:
        cursor.execute("""
            INSERT INTO usuarios (usuario, contrasena, rol)
            VALUES (?, ?, ?)
        """, ("admin", "admin", "admin"))

        print("✔ Usuario admin creado con contraseña admin.")
    else:
        print("✔ Ya existen usuarios en la base de datos.")


def revisar_recibos_duplicados(cursor):
    cursor.execute("""
        SELECT num_recibo, COUNT(*)
        FROM pagos
        GROUP BY num_recibo
        HAVING COUNT(*) > 1
        LIMIT 1
    """)

    duplicado = cursor.fetchone()

    if duplicado:
        print("⚠ Se encontraron recibos duplicados en pagos.")
        print("⚠ No se creó índice único de recibos.")
        print("⚠ Si quieres empezar con pagos limpios, puedes borrar la tabla pagos manualmente.")
    else:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_pagos_num_recibo
            ON pagos(num_recibo)
        """)

        print("✔ Índice único de recibos creado o ya existente.")


def main():
    hacer_backup_previo()

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    crear_tablas_basicas_si_no_existen(cursor)

    # Columnas importantes para titulares
    columnas_titulares = [
        ("cedula", "TEXT"),
        ("contrato_viejo", "TEXT"),
        ("contrato_nuevo", "TEXT"),
        ("nombres", "TEXT"),
        ("apellidos", "TEXT"),
        ("fecha_nacimiento", "TEXT"),
        ("telefono", "TEXT"),
        ("correo", "TEXT"),
        ("direccion", "TEXT"),
        ("tipo_contrato", "TEXT"),
        ("fecha_inicio", "TEXT"),
        ("recibos_previos", "INTEGER DEFAULT 0"),
        ("fecha_contrato_anterior", "TEXT"),
    ]

    for columna, tipo in columnas_titulares:
        agregar_columna(cursor, "titulares", columna, tipo)

    # Columnas importantes para pagos
    columnas_pagos = [
        ("num_recibo", "TEXT"),
        ("titular_cedula", "TEXT"),
        ("fecha_pago", "TEXT"),
        ("monto_usd", "REAL"),
        ("monto_bs", "REAL"),
        ("tasa_bcv", "REAL"),
        ("forma_pago", "TEXT"),
        ("banco_origen", "TEXT"),
        ("banco_destino", "TEXT"),
        ("num_operacion", "TEXT"),
        ("cuota_numero", "INTEGER"),
    ]

    for columna, tipo in columnas_pagos:
        agregar_columna(cursor, "pagos", columna, tipo)

    crear_usuario_admin_si_no_existe(cursor)
    revisar_recibos_duplicados(cursor)

    conn.commit()
    conn.close()

    print("")
    print("✅ Proceso terminado.")
    print("Ya puedes abrir el sistema y probar.")


if __name__ == "__main__":
    main()