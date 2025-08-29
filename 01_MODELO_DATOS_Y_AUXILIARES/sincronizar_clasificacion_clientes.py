# 01_MODELO_DATOS_Y_AUXILIARES/sincronizar_clasificacion_clientes.py

import pandas as pd
import sys
import os
from io import StringIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection, execute_query

def sincronizar_clasificacion_clientes():
    """
    Lee el CSV de clasificación histórica y lo carga en la tabla
    dim_clientes_clasificacion_historia.
    Este método TRUNCATE e INSERT asume que el CSV es la fuente de verdad completa.
    """
    print("=== INICIO DE LA SINCRONIZACIÓN DE CLASIFICACIÓN DE CLIENTES ===")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        # --- PASO 1: Leer el archivo CSV de clasificación ---
        ruta_csv = os.path.join(config.DATOS_ENTRADA_DIR, 'dim_clientes_clasificacion_historia.csv')
        df_csv = pd.read_csv(ruta_csv, dtype=str).where(pd.notnull(pd.read_csv(ruta_csv, dtype=str)), None)
        print(f"INFO: Se leyeron {len(df_csv)} filas del archivo de clasificación.")

        # --- PASO 2: Obtener el mapa de IDs desde maestro_clientes ---
        print("INFO: Creando mapa de clientes maestros desde la base de datos...")
        mapa_maestro = pd.read_sql("SELECT id_maestro_cliente, cod_cliente_maestro FROM maestro_clientes", conn)
        mapa_maestro.rename(columns={'id_maestro_cliente': 'id_maestro_cliente_fk'}, inplace=True)
        
        # --- PASO 3: Enriquecer el CSV con el id_maestro_cliente_fk ---
        df_para_carga = pd.merge(df_csv, mapa_maestro, on='cod_cliente_maestro', how='left')

        # Validar que todos los clientes del CSV fueron encontrados en el maestro
        clientes_no_encontrados = df_para_carga[df_para_carga['id_maestro_cliente_fk'].isnull()]
        if not clientes_no_encontrados.empty:
            print("\nERROR CRÍTICO: Los siguientes 'cod_cliente_maestro' de tu CSV no existen en la tabla 'maestro_clientes'.")
            print(clientes_no_encontrados[['cod_cliente_maestro']])
            print("Por favor, ejecute primero el script para sincronizar los clientes maestros.")
            return

        df_para_carga['id_maestro_cliente_fk'] = df_para_carga['id_maestro_cliente_fk'].astype(int)

        # --- PASO 4: Cargar los datos en la tabla ---
        # Para tablas de gestión como esta, un método simple y robusto es borrar y recargar.
        # Esto asegura que la tabla sea siempre un reflejo exacto de tu CSV.
        
        # 4.1: Vaciar la tabla
        execute_query(conn, 'TRUNCATE TABLE dim_clientes_clasificacion_historia RESTART IDENTITY;')
        print("INFO: La tabla 'dim_clientes_clasificacion_historia' ha sido vaciada.")

        # 4.2: Cargar los nuevos datos
        columnas_db = [
            'id_maestro_cliente_fk', 'canal', 'subcanal', 'sucursal', 
            'dia_visita', 'fecha_inicio_validez', 'fecha_fin_validez'
        ]
        
        # Asegurarnos de que solo usamos las columnas que existen
        columnas_presentes = [col for col in columnas_db if col in df_para_carga.columns]
        df_final = df_para_carga[columnas_presentes]
        
        buffer = StringIO()
        df_final.to_csv(buffer, index=False, header=False, sep=',')
        buffer.seek(0)
        
        with conn.cursor() as cursor:
            copy_sql = f'COPY dim_clientes_clasificacion_historia ({",".join(columnas_presentes)}) FROM STDIN WITH (FORMAT CSV, DELIMITER \',\')'
            cursor.copy_expert(copy_sql, buffer)
        
        conn.commit()
        print(f"¡ÉXITO! Se han cargado {len(df_final)} registros en 'dim_clientes_clasificacion_historia'.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la sincronización: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("INFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    sincronizar_clasificacion_clientes()