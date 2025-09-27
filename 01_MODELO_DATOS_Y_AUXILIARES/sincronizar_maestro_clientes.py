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
    Lee el CSV maestro y sincroniza la tabla maestro_clientes.
    Luego, enlaza los registros correspondientes en dim_clientes_empresa
    basándose en la igualdad entre cod_cliente_erp y cod_cliente_maestro.
    """
    print("=== INICIO DE LA SINCRONIZACIÓN DE maestro_clientes ===")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        # --- PASO 1: Sincronizar la tabla `maestro_clientes` desde el CSV ---
        # Este paso solo se preocupa por la tabla maestra.
        
        ruta_csv = os.path.join(config.DATOS_ENTRADA_DIR, 'maestro_clientes.csv')
        # Leemos solo las columnas que nos interesan para evitar errores
        df_maestro_csv = pd.read_csv(ruta_csv, dtype=str, usecols=['cod_cliente_maestro', 'nombre_unificado'])
        print(f"INFO: Se leyeron {len(df_maestro_csv)} filas del CSV 'maestro_clientes.csv'.")

        # Preparamos los datos para la carga masiva.
        datos_maestro = [
            tuple(row) for row in df_maestro_csv[['cod_cliente_maestro', 'nombre_unificado']].itertuples(index=False)
        ]

        # Consulta UPSERT que solo afecta a las columnas de la tabla maestra.
        query_maestro = """
            INSERT INTO maestro_clientes (cod_cliente_maestro, nombre_unificado)
            VALUES %s
            ON CONFLICT (cod_cliente_maestro) DO UPDATE SET
                nombre_unificado = EXCLUDED.nombre_unificado;
        """
        
        with conn.cursor() as cursor:
            extras.execute_values(cursor, query_maestro, datos_maestro, page_size=1000)
            print(f"INFO: La tabla 'maestro_clientes' ha sido sincronizada. {cursor.rowcount} filas afectadas.")

        # --- PASO 2: Enlazar los registros en `dim_clientes_empresa` ---
        # Este es el paso que rellena los espacios en blanco.
        
        print("INFO: Enlazando registros de 'dim_clientes_empresa' con el maestro...")
        
        # La consulta une las dos tablas por el código y actualiza el FK solo donde sea nulo.
        link_query = """
            UPDATE dim_clientes_empresa dce
            SET id_maestro_cliente_fk = mc.id_maestro_cliente
            FROM maestro_clientes mc
            WHERE dce.cod_cliente_erp = mc.cod_cliente_maestro 
              AND dce.id_maestro_cliente_fk IS NULL;
        """
        with conn.cursor() as cursor:
            cursor.execute(link_query)
            # cursor.rowcount nos dirá cuántos "espacios en blanco" se rellenaron.
            print(f"INFO: {cursor.rowcount} registros de 'dim_clientes_empresa' fueron enlazados al maestro.")
        
        # Guardamos todos los cambios en la base de datos.
        conn.commit()
        print("¡ÉXITO! El proceso de sincronización y enlace ha finalizado.")

    except FileNotFoundError:
        print(f"ERROR CRÍTICO: No se encontró el archivo en la ruta: {ruta_csv}")
    except KeyError as e:
        print(f"ERROR CRÍTICO: Falta una columna esperada en tu archivo CSV: {e}. Revisa 'maestro_clientes.csv'.")
    except Exception as e:
        print(f"ERROR CRÍTICO durante la sincronización: {e}")
        # Revertimos cualquier cambio si ocurre un error.
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("INFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    sincronizar_maestro_clientes()