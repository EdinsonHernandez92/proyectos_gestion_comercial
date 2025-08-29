# 01_MODELO_DATOS_Y_AUXILIARES/sincronizar_maestro_clientes.py

import pandas as pd
import sys
import os
from psycopg2 import extras

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def sincronizar_maestro_clientes():
    """
    Lee el CSV maestro de clientes y lo carga en la tabla maestro_clientes,
    actualizando si ya existe un registro con el mismo cod_cliente_maestro.
    """
    print("=== INICIO DE LA SINCRONIZACIÓN DE maestro_clientes ===")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        # --- PASO 1: Leer el archivo CSV maestro ---
        ruta_csv = os.path.join(config.DATOS_ENTRADA_DIR, 'maestro_clientes.csv')
        df_maestro = pd.read_csv(ruta_csv, dtype=str)
        print(f"INFO: Se leyeron {len(df_maestro)} filas del CSV 'maestro_clientes.csv'.")

        # --- PASO 2: Preparar y cargar los datos ---
        # Aseguramos que los nombres de columna en el CSV sean: cod_cliente_maestro, nombre_unificado
        datos_maestro = [
            tuple(row) for row in df_maestro[['cod_cliente_maestro', 'nombre_unificado']].itertuples(index=False)
        ]

        # Consulta UPSERT (INSERT o UPDATE)
        query_maestro = """
            INSERT INTO maestro_clientes (cod_cliente_maestro, nombre_unificado)
            VALUES %s
            ON CONFLICT (cod_cliente_maestro) DO UPDATE SET
                nombre_unificado = EXCLUDED.nombre_unificado;
        """
        
        with conn.cursor() as cursor:
            extras.execute_values(cursor, query_maestro, datos_maestro, page_size=1000)
            conn.commit()
            print(f"¡ÉXITO! La tabla 'maestro_clientes' ha sido sincronizada. {cursor.rowcount} filas afectadas.")

    except FileNotFoundError:
        print(f"ERROR CRÍTICO: No se encontró el archivo en la ruta: {ruta_csv}")
    except Exception as e:
        print(f"ERROR CRÍTICO durante la sincronización: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("INFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    sincronizar_maestro_clientes()