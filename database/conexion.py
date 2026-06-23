import sqlite3
import os

def conectar():
    ruta_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'funeraria.db'))
    conn = sqlite3.connect(ruta_db)
    return conn

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
            titular_cedula TEXT,
            monto_usd REAL,
            tasa_bcv REAL,
            monto_bs REAL,
            fecha_pago TEXT,
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

    conn.commit()
    conn.close()
    print("Base de datos inicializada y actualizada con éxito.")