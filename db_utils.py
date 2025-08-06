# db_utils.py
# Funciones de utilidad para interactuar con la base de datos.

import psycopg2
from psycopg2 import extras
import config

def get_db_connection():
    """Establece y retorna una conexión a la base de datos PostgreSQL."""
    try:
        if not config.DB_CONFIG.get("password"):
            raise ValueError("La contraseña de la BD (DB_PASSWORD) no está en el archivo .env")
        
        conn = psycopg2.connect(**config.DB_CONFIG)
        return conn
    except (psycopg2.Error, ValueError) as e:
        print(f"ERROR CRÍTICO: No se pudo conectar a la base de datos: {e}")
        return None

def execute_query(conn, query, params=None, fetch=None):
    """
    Ejecuta una consulta SQL.
    :param fetch: 'one' para un resultado, 'all' para todos, None para no obtener resultados.
    """
    with conn.cursor() as cursor:
        try:
            cursor.execute(query, params)
            if fetch == 'one':
                return cursor.fetchone()
            elif fetch == 'all':
                return cursor.fetchall()
            else:
                conn.commit()
        except psycopg2.Error as e:
            print(f"ERROR al ejecutar query: {e}")
            conn.rollback()
            raise

def clear_table(conn, table_name):
    """
    Vacía una tabla usando TRUNCATE. Es rápido y reinicia las secuencias (SERIAL).
    ADVERTENCIA: Elimina todos los datos de forma irreversible.
    """
    print(f"INFO: Vaciando la tabla '{table_name}'...")
    query = f'TRUNCATE TABLE public."{table_name}" RESTART IDENTITY CASCADE;'
    try:
        execute_query(conn, query)
        print(f"¡ÉXITO! La tabla '{table_name}' ha sido vaciada.")
    except psycopg2.Error as e:
        print(f"ERROR: No se pudo vaciar la tabla '{table_name}'. Error: {e}")
        raise

def copy_csv_to_db(conn, csv_filepath, table_name):
    """
    Carga datos desde un archivo CSV a una tabla de PostgreSQL usando COPY FROM.
    Es el método más rápido para cargas masivas.
    """
    print(f"INFO: Iniciando carga masiva (COPY) a la tabla '{table_name}' desde '{csv_filepath}'...")
    with conn.cursor() as cursor:
        try:
            with open(csv_filepath, 'r', encoding='utf-8') as f:
                # El CSV debe tener cabecera y coincidir con las columnas de la tabla
                cursor.copy_expert(f"COPY public.\"{table_name}\" FROM STDIN WITH CSV HEADER", f)
            conn.commit()
            print(f"¡ÉXITO! Datos cargados a la tabla '{table_name}'.")
        except FileNotFoundError:
            print(f"ERROR: Archivo CSV no encontrado en {csv_filepath}")
            raise
        except psycopg2.Error as e:
            print(f"ERROR al ejecutar COPY en la tabla '{table_name}': {e}")
            conn.rollback()
            raise