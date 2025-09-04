# 00_ETL_TNS/cargar_vendedores_api_crudo.py

import pandas as pd
import requests
import os
import sys
from psycopg2 import extras

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection, execute_query

def sincronizar_vendedores_api():
    """
    Extrae los terceros que son vendedores desde la API y los carga en la tabla
    temporal api_vendedores_crudo para su posterior auditoría.
    """
    print("=== INICIO DE LA SINCRONIZACIÓN DE VENDEDORES DESDE LA API ===")
    conn = get_db_connection()
    if not conn: return

    try:
        # --- PASO 1: Extraer todos los terceros de la API ---
        lista_dfs_empresas = []
        MAPEO_COLUMNAS_API = {'OCODIGO': 'cod_cliente_erp', 'ONIT': 'nit_documento', 'ONOMBRE': 'nombre_vendedor'}
        
        for empresa_config in config.API_CONFIG_TNS:
            nombre_empresa = empresa_config["nombre_corto"]
            url_terceros = config.API_URLS["terceros"]
            print(f"--- Extrayendo terceros para la empresa: {nombre_empresa} ---")
            params = { "empresa": empresa_config["empresa_tns"], "usuario": empresa_config["usuario_tns"], "password": empresa_config["password_tns"], "tnsapitoken": empresa_config["tnsapitoken"], "codsuc": "00"}
            
            try:
                response = requests.get(url_terceros, params=params, timeout=300)
                response.raise_for_status()
                datos_api_raw = response.json()
                
                if isinstance(datos_api_raw, dict) and datos_api_raw.get("status") == "OK":
                    df_empresa = pd.DataFrame(datos_api_raw.get("results", []))
                    if not df_empresa.empty:
                        df_empresa['empresa_erp'] = nombre_empresa
                        lista_dfs_empresas.append(df_empresa)
            except Exception as e:
                print(f"ERROR al procesar {nombre_empresa}: {e}")

        if not lista_dfs_empresas:
            print("ADVERTENCIA: No se extrajeron datos de terceros de ninguna empresa.")
            return

        df_consolidado = pd.concat(lista_dfs_empresas, ignore_index=True)
        print(f"INFO: Se extrajeron {len(df_consolidado)} terceros en total.")

        # --- PASO 2: Filtrar para quedarnos solo con los vendedores ---
        # Aplicamos los filtros que definiste
        df_vendedores = df_consolidado[
            (df_consolidado['OINACTIVO'].fillna('1') != '0') &
            (df_consolidado['OCODIGO'].str.startswith('V', na=False))
        ].copy()
        
        # Mapeamos y seleccionamos solo las columnas que necesitamos
        df_vendedores = df_vendedores.rename(columns=MAPEO_COLUMNAS_API)
        columnas_finales = list(MAPEO_COLUMNAS_API.values()) + ['empresa_erp']
        df_para_carga = df_vendedores[columnas_finales]

        print(f"INFO: Se identificaron {len(df_para_carga)} registros de vendedores activos.")

        # --- PASO 3: Cargar en la tabla api_vendedores_crudo ---
        # Vaciamos la tabla primero para tener siempre los datos más frescos
        execute_query(conn, 'TRUNCATE TABLE api_vendedores_crudo;')
        
        datos_para_insertar = [tuple(row) for row in df_para_carga.itertuples(index=False)]
        
        query_insert = f"""
            INSERT INTO api_vendedores_crudo ({", ".join(columnas_finales)})
            VALUES %s;
        """
        with conn.cursor() as cursor:
            extras.execute_values(cursor, query_insert, datos_para_insertar)
            conn.commit()
            print(f"¡ÉXITO! La tabla 'api_vendedores_crudo' ha sido actualizada con {cursor.rowcount} registros.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la sincronización de vendedores desde la API: {e}")
        conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    sincronizar_vendedores_api()