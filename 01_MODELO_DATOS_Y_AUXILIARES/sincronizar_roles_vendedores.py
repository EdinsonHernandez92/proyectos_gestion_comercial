# 01_MODELO_DATOS_Y_AUXILIARES/sincronizar_roles_vendedores.py

###### ATENCIÓN: AJUSTAR ESTE SCRIPT PARA QUE UNA VEZ RALIZADA LA CARGA INICIAL NO SE BORRE LA TABLA DE METAS ASIGNADAS

import pandas as pd
import sys
import os
from psycopg2 import extras
from io import StringIO
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection, execute_query

def sincronizar_roles():
    print("=== INICIO DE LA SINCRONIZACIÓN DE dim_roles_comerciales_historia ===")
    conn = get_db_connection()
    if not conn: return
    try:
        ruta_csv = os.path.join(config.DATOS_ENTRADA_DIR, 'dim_roles_comerciales_historia.csv')
        df_csv = pd.read_csv(ruta_csv, dtype=str).where(pd.notnull(pd.read_csv(ruta_csv, dtype=str)), None)
        
        print("INFO: Creando mapa de personas desde la base de datos...")
        mapa_personas = pd.read_sql("SELECT id_persona, numero_documento FROM maestro_personas", conn)
        mapa_personas_dict = mapa_personas.set_index('numero_documento')['id_persona'].to_dict()

        def get_id(doc):
            return mapa_personas_dict.get(str(doc))

        df_csv['id_persona_fk'] = df_csv['documento_persona'].apply(get_id)
        df_csv['id_supervisor_fk'] = df_csv['documento_supervisor'].apply(get_id)
        
        no_encontrados = df_csv[df_csv['id_persona_fk'].isnull()]
        if not no_encontrados.empty:
            print("ERROR CRÍTICO: Las siguientes personas en 'documento_persona' no existen en 'maestro_personas':")
            print(no_encontrados['documento_persona'].tolist())
            return
        
        execute_query(conn, 'TRUNCATE TABLE dim_roles_comerciales_historia RESTART IDENTITY CASCADE;')
        
        columnas_db = ['id_persona_fk', 'id_supervisor_fk', 'cod_rol_erp', 'empresa_erp', 'cargo', 'fecha_inicio_validez', 'fecha_fin_validez']
        df_final = df_csv[columnas_db]
        
        buffer = StringIO()
        df_final.to_csv(buffer, index=False, header=False, sep=',')
        buffer.seek(0)
        
        with conn.cursor() as cursor:
            copy_sql = f'COPY dim_roles_comerciales_historia ({",".join(columnas_db)}) FROM STDIN WITH (FORMAT CSV, DELIMITER \',\')'
            cursor.copy_expert(copy_sql, buffer)
        
        conn.commit()
        print(f"¡ÉXITO! Se han cargado {len(df_final)} registros en 'dim_roles_comerciales_historia'.")

    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    sincronizar_roles()