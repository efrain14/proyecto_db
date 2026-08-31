# =========================================================================
# CONEXIÓN A LA BASE DE DATOS
# =========================================================================
# Centraliza la ubicación de funeraria.db:
#   - En desarrollo (python main.py): usa la raíz del proyecto.
#   - Compilado (.exe con PyInstaller): usa la carpeta donde está el .exe.
# =========================================================================
import os
import sys
import sqlite3


def obtener_ruta_base():
    """
    Devuelve la carpeta donde debe vivir funeraria.db.
    - Si el programa corre como .exe: la misma carpeta del ejecutable.
    - Si corre desde VS Code: la raíz del proyecto.
    """
    if getattr(sys, "frozen", False):
        # Ejecutable compilado con PyInstaller
        return os.path.dirname(sys.executable)

    # Desarrollo normal
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def obtener_ruta_db():
    """Ruta completa del archivo de base de datos."""
    return os.path.join(obtener_ruta_base(), "funeraria.db")


def conectar():
    """Abre la conexión a funeraria.db en la ubicación correcta."""
    return sqlite3.connect(obtener_ruta_db())

def inicializar_base_de_datos():
    conn = conectar()
    cursor = conn.cursor()

    # 1. TABLA DE TITULARES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS titulares (
            cedula TEXT PRIMARY KEY,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            fecha_nacimiento TEXT NOT NULL,
            telefono TEXT,
            correo TEXT,
            direccion TEXT,
            tipo_contrato TEXT,
            fecha_inicio TEXT
        )
    """)

    # 2. TABLA DE FAMILIARES / AFILIADOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS familiares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            parentesco TEXT NOT NULL,
            titular_cedula TEXT,
            FOREIGN KEY (titular_cedula) REFERENCES titulares (cedula) ON DELETE CASCADE
        )
    """)

    # 3. TABLA DE PAGOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_recibo INTEGER NOT NULL,
            titular_cedula TEXT NOT NULL,
            fecha_pago TEXT NOT NULL,
            monto_usd REAL,
            monto_bs REAL,
            tasa_bcv REAL,
            forma_pago TEXT,
            banco_origen TEXT,
            banco_destino TEXT,
            num_operacion TEXT,
            FOREIGN KEY (titular_cedula) REFERENCES titulares (cedula)
        )
    """)

    # 4. TABLA DE USUARIOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL
        )
    """)

    # Inserción de usuario por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (usuario, contrasena) VALUES (?, ?)", ("admin", "admin123"))
        print("Usuario por defecto creado: admin / admin123")

    # Migración de columna rol para control de acceso
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'operador';")
    except sqlite3.OperationalError: pass
    
    cursor.execute("UPDATE usuarios SET rol = 'admin' WHERE usuario = 'admin';")
    conn.commit()

    # =========================================================================
    # MIGRACIONES Y ACTUALIZACIONES DE COLUMNAS
    # =========================================================================
    # Profesor: Añadimos la columna fecha_nacimiento a la tabla de familiares
    try:
        cursor.execute("ALTER TABLE familiares ADD COLUMN fecha_nacimiento TEXT;")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE titulares ADD COLUMN contrato_viejo TEXT;")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE titulares ADD COLUMN contrato_nuevo TEXT;")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE titulares ADD COLUMN recibos_previos INTEGER DEFAULT 0;")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE pagos ADD COLUMN contrato_viejo TEXT;")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE pagos ADD COLUMN contrato_nuevo TEXT;")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE pagos ADD COLUMN numero_recibo INTEGER;")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE pagos ADD COLUMN forma_pago TEXT;")
    except sqlite3.OperationalError: pass


# =========================================================================
# database/db.py (Añadir al final del archivo)
# =========================================================================

def obtener_estado_cuenta_titular(criterio_busqueda):
    """
    Calcula las métricas financieras acumuladas para un contrato específico.
    """
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Obtener datos básicos del contrato
    cursor.execute("""
        SELECT t.cedula, t.nombres, t.apellidos, t.contrato_nuevo, t.contrato_viejo, 
        t.fecha_ingreso, t.tipo_plan, t.precio_total_usd, t.cuotas_totales
        FROM titulares t
        WHERE t.cedula = ? OR t.contrato_nuevo = ? OR t.contrato_viejo = ?
    """, (criterio_busqueda, criterio_busqueda, criterio_busqueda))
    
    titular = cursor.fetchone()
    if not titular:
        conn.close()
        return None

    cedula, nombres, apellidos, c_nuevo, c_viejo, f_ingreso, plan, precio_total, cuotas_totales = titular

    # 2. Consultar historial de pagos realizados
    cursor.execute("""
        SELECT num_recibo, fecha_pago, monto_bs, monto_usd, forma_pago, num_operacion
        FROM pagos
        WHERE titular_cedula = ?
        ORDER BY fecha_pago ASC
    """, (cedula,))
    
    pagos = cursor.fetchall()
    conn.close()

    # 3. Cálculos de Estado de Cuenta
    recibos_pagados = len(pagos)
    total_pagado_bs = sum(p[2] for p in pagos)
    total_pagado_usd = sum(p[3] for p in pagos)
    
    recibos_pendientes = max(0, cuotas_totales - recibos_pagados)
    saldo_pendiente_usd = max(0.0, precio_total - total_pagado_usd)
    
    return {
        "cedula": cedula,
        "cliente": f"{nombres} {apellidos}",
        "contrato_nuevo": c_nuevo,
        "contrato_viejo": c_viejo,
        "fecha_inicio": f_ingreso,
        "plan": plan,
        "recibos_pagados": recibos_pagados,
        "recibos_pendientes": recibos_pendientes,
        "total_pagado_bs": total_pagado_bs,
        "total_pagado_usd": total_pagado_usd,
        "saldo_pendiente_usd": saldo_pendiente_usd,
        "historial_pagos": pagos
    }


    conn.commit()
    conn.close()
    print("Base de datos inicializada y actualizada con éxito.")