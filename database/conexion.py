import sqlite3
import os

# Ruta donde se guardará la base de datos dentro de la carpeta database
DB_PATH = os.path.join(os.path.dirname(__file__), 'funeraria.db')

def conectar():
    """Establece la conexión con la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    # Esto ayuda a que SQLite devuelva los textos correctamente (UTF-8)
    conn.text_factory = str 
    return conn

def crear_tablas():
    """Crea las tablas necesarias si no existen."""
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. TABLA DE USUARIOS (Para el Login)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL
        )
    ''')
    
    # 2. TABLA DE TITULARES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS titulares (
            cedula TEXT PRIMARY KEY,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            fecha_nacimiento TEXT NOT NULL,
            telefono TEXT,
            correo TEXT,
            direccion TEXT,
            tipo_contrato TEXT NOT NULL, -- 'velacion' o 'completo'
            fecha_inicio TEXT NOT NULL   -- Formato: YYYY-MM-DD
        )
    ''')
    
    # 3. TABLA DE FAMILIARES (Hasta 8 por titular)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS familiares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            parentesco TEXT NOT NULL,
            titular_cedula TEXT NOT NULL,
            FOREIGN KEY (titular_cedula) REFERENCES titulares(cedula) ON DELETE CASCADE
        )
    ''')
    
    # 4. TABLA DE PAGOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular_cedula TEXT NOT NULL,
            monto_usd REAL NOT NULL,
            tasa_bcv REAL NOT NULL,
            monto_bs REAL NOT NULL,
            fecha_pago TEXT NOT NULL, -- Formato: YYYY-MM-DD
            FOREIGN KEY (titular_cedula) REFERENCES titulares(cedula)
        )
    ''')
    
    # Insertar un usuario administrador por defecto para poder hacer pruebas de Login
    try:
        cursor.execute("INSERT INTO usuarios (usuario, contrasena) VALUES (?, ?)", ('admin', 'admin123'))
    except sqlite3.IntegrityError:
        # Si el usuario ya existe, ignoramos el error para que no falle el programa
        pass

    conn.commit()
    conn.close()
    print("¡Base de datos y tablas preparadas con éxito!")

# Esto permite que si ejecutas este archivo directamente, se creen las tablas
if __name__ == "__main__":
    crear_tablas()