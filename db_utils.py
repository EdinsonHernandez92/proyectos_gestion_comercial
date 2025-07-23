# db_utils.py

# Este archivo contiene funciones de utilidad para interactuar con la base de datos.

import psycopg2
from config import DB_CONFIG  # Importa la configuración desde el archivo config.py

def get_db_connection():
    """
    Crea y devuelve una nueva conexión a la base de datos PostgreSQL.
    Utiliza la configuración definida en el archivo config.py.
    """
    conn = None
    try:
        # print("INFO: Conectando a la base de datos PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        # print("INFO: Conexión exitosa.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERROR: No se pudo conectar a la base de datos.")
        print(f"Detalle del error: {e}")
        print("Por favor, verifica que:")
        print("1. El servidor de PostgreSQL esté corriendo.")
        print("2. Los datos en tu archivo 'config.py' (dbname, user, password, etc.) sean correctos.")
        return None
    except Exception as e:
        print(f"ERROR: Ocurrió un error inesperado al conectar a la base de datos: {e}")
        return None

# --- Ejemplo de cómo usar la función (no es necesario para que funcione el otro script) ---
if __name__ == '__main__':
    # Esta parte solo se ejecuta si corres este archivo directamente
    conexion = get_db_connection()
    if conexion:
        print("Prueba de conexión realizada con éxito. Cerrando conexión.")
        conexion.close()
    else:
        print("Prueba de conexión fallida.")