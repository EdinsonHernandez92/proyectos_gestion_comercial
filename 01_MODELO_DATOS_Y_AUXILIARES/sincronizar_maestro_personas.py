# 01_MODELO_DATOS_Y_AUXILIARES/sincronizar_maestro_personas.py
import pandas as pd
import sys
import os
from psycopg2 import extras
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def sincronizar_maestro_personas():
    print("=== INICIO DE LA SINCRONIZACIÓN DE maestro_personas ===")
    conn = get_db_connection()
    if not conn: return
    try:
        ruta_csv = os.path.join(config.DATOS_ENTRADA_DIR, 'maestro_personas.csv')
        df_maestro = pd.read_csv(ruta_csv, dtype=str)
        print(f"INFO: Se leyeron {len(df_maestro)} filas del CSV 'maestro_personas.csv'.")
        
        datos = [tuple(row) for row in df_maestro.itertuples(index=False)]
        query = """
            INSERT INTO maestro_personas (numero_documento, nombre_completo) VALUES %s
            ON CONFLICT (numero_documento) DO UPDATE SET nombre_completo = EXCLUDED.nombre_completo;
        """
        with conn.cursor() as cursor:
            extras.execute_values(cursor, query, datos)
            conn.commit()
            print(f"¡ÉXITO! La tabla 'maestro_personas' ha sido sincronizada. {cursor.rowcount} filas afectadas.")
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    sincronizar_maestro_personas()