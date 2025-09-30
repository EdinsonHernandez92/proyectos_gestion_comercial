# 00_ETL_TNS/cargar_clientes_api.py

import pandas as pd
import requests
import os
import sys
from datetime import datetime
from psycopg2 import extras

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def detectar_y_reportar_cambios(df_api, conn):
    """
    Compara el DataFrame de la API con el estado actual de dim_clientes_empresa
    y genera un reporte con los cambios reales, ignorando diferencias sutiles.
    """
    print("\nINFO: Iniciando detección de cambios en clientes...")
    try:
        query_db = "SELECT cod_cliente_erp, empresa_erp, nit, nombre_erp, direccion_erp FROM dim_clientes_empresa;"
        df_db = pd.read_sql_query(query_db, conn)
        print(f"INFO: Se leyeron {len(df_db)} registros existentes de dim_clientes_empresa.")

        # --- LÓGICA DE ESTANDARIZACIÓN ---
        columnas_a_comparar = ['nit', 'nombre_erp', 'direccion_erp']
        
        for col in columnas_a_comparar:
            # Estandarizamos ambas fuentes: convertimos a texto, rellenamos nulos, quitamos espacios y ponemos en mayúsculas.
            df_api[col] = df_api[col].astype(str).fillna('').str.strip().str.upper()
            df_db[col] = df_db[col].astype(str).fillna('').str.strip().str.upper()
        # ------------------------------------

        key_cols = ['cod_cliente_erp', 'empresa_erp']
        df_merged = pd.merge(df_db, df_api, on=key_cols, how='outer', indicator=True, suffixes=('_db', '_api'))

        nuevos = df_merged[df_merged['_merge'] == 'right_only']
        modificados = df_merged[df_merged['_merge'] == 'both']
        
        # Ahora la comparación se hace sobre los datos ya estandarizados
        modificados = modificados[
            (modificados['nit_db'] != modificados['nit_api']) |
            (modificados['nombre_erp_db'] != modificados['nombre_erp_api']) |
            (modificados['direccion_erp_db'] != modificados['direccion_erp_api'])
        ].copy()

        # ... (El resto del código para generar el reporte se mantiene igual) ...
        if not nuevos.empty or not modificados.empty:
            reporte = []
            for _, row in nuevos.iterrows():
                reporte.append({'estado': 'NUEVO', 'cod_cliente_erp': row['cod_cliente_erp'], 'empresa_erp': row['empresa_erp'], 'nombre_nuevo': row['nombre_erp_api']})
            for _, row in modificados.iterrows():
                reporte.append({'estado': 'MODIFICADO', 'cod_cliente_erp': row['cod_cliente_erp'], 'empresa_erp': row['empresa_erp'], 'nombre_anterior': row['nombre_erp_db'], 'nombre_nuevo': row['nombre_erp_api']})
            df_reporte = pd.DataFrame(reporte)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_reporte = os.path.join(config.INFORMES_GENERADOS_DIR, f'reporte_cambios_clientes_{timestamp}.csv')
            df_reporte.to_csv(ruta_reporte, index=False)
            print(f"\n¡ALERTA! Se detectaron {len(df_reporte)} cambios reales (nuevos o modificados).")
            print(f"Se ha generado un reporte en: {ruta_reporte}")
        else:
            print("INFO: No se detectaron clientes nuevos o modificados en la API.")

    except Exception as e:
        print(f"ERROR: Ocurrió un error durante la detección de cambios de clientes: {e}")

# --- El resto de las funciones (extraer_clientes_api, cargar_dim_clientes_empresa) se mantienen igual ---
def extraer_clientes_api():
    # ... (código existente)
    print("INFO: Iniciando extracción de clientes desde la API de TNS...")
    lista_dfs_empresas = []
    MAPEO_COLUMNAS_API = { 'OCODIGO': 'cod_cliente_erp', 'ONIT': 'nit', 'ONOMBRE': 'nombre_erp', 'OCODCLASIFICACION1': 'cod_clasificacion_erp', 'ONOMCLASIFICACION1': 'clasificacion_erp', 'ODIRECC1': 'direccion_erp', 'OTELEF1': 'telefono_erp', 'OCODCIUDAD': 'ciudad_erp', 'OINACTIVO': 'inactivo_erp'}
    for empresa_config in config.API_CONFIG_TNS:
        nombre_empresa = empresa_config["nombre_corto"]
        url_terceros = config.API_URLS["terceros"]
        print(f"--- Extrayendo para la empresa: {nombre_empresa} ---")
        params = { "empresa": empresa_config["empresa_tns"], "usuario": empresa_config["usuario_tns"], "password": empresa_config["password_tns"], "tnsapitoken": empresa_config["tnsapitoken"], "codsuc": empresa_config.get("cod_sucursal_tns", "00")}
        try:
            response = requests.get(url_terceros, params=params, timeout=300)
            response.raise_for_status()
            datos_api_raw = response.json()
            lista_terceros_api = []
            if isinstance(datos_api_raw, dict) and datos_api_raw.get("status") == "OK":
                lista_terceros_api = datos_api_raw.get("results", [])
            if not lista_terceros_api: continue
            terceros_procesados = [ {nuestra_col: item.get(api_col) for api_col, nuestra_col in MAPEO_COLUMNAS_API.items()} for item in lista_terceros_api if isinstance(item, dict) ]
            if terceros_procesados:
                df_empresa = pd.DataFrame(terceros_procesados)
                df_empresa['empresa_erp'] = nombre_empresa
                lista_dfs_empresas.append(df_empresa)
                print(f"¡ÉXITO! Se procesaron {len(df_empresa)} clientes de {nombre_empresa}.")
        except Exception as e:
            print(f"ERROR al procesar {nombre_empresa}: {e}")
            
    if lista_dfs_empresas:
        df_consolidado = pd.concat(lista_dfs_empresas, ignore_index=True)
        print(f"\nINFO: Extracción completada. Total de clientes consolidados: {len(df_consolidado)}")
        return df_consolidado
    return None

def cargar_dim_clientes_empresa(df_crudo, conn):
    # ... (código existente)
    print("\nINFO: Sincronizando datos de la API con la tabla 'dim_clientes_empresa'...")
    if df_crudo is None or df_crudo.empty:
        print("ADVERTENCIA: No hay datos de clientes para cargar.")
        return
    try:
        columnas_dim = ['cod_cliente_erp', 'empresa_erp', 'nit', 'nombre_erp', 'cod_clasificacion_erp', 'clasificacion_erp', 'direccion_erp', 'telefono_erp', 'ciudad_erp', 'inactivo_erp']
        datos_dim = [tuple(row) for row in df_crudo[columnas_dim].itertuples(index=False)]
        columnas_update = columnas_dim[2:]
        update_sql = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columnas_update])
        query_dim = f"""
            INSERT INTO dim_clientes_empresa ({", ".join(f'"{c}"' for c in columnas_dim)})
            VALUES %s
            ON CONFLICT (cod_cliente_erp, empresa_erp) DO UPDATE SET {update_sql};
        """
        with conn.cursor() as cursor:
            extras.execute_values(cursor, query_dim, datos_dim, page_size=1000)
            conn.commit()
            print(f"¡ÉXITO! {cursor.rowcount} registros afectados en 'dim_clientes_empresa'.")
    except Exception as e:
        print(f"ERROR CRÍTICO durante la carga a dim_clientes_empresa: {e}")
        conn.rollback()

def ejecutar_etl_clientes():
    """
    Función principal orquesta el proceso completo de ETL para clientes.
    """
    print("=== INICIO DEL PROCESO ETL DE CLIENTES (API -> dim_clientes_empresa) ===")

    df_clientes_crudo = extraer_clientes_api()

    if df_clientes_crudo is not None:
        conn = get_db_connection()
        if conn:
            try:
                detectar_y_reportar_cambios(df_clientes_crudo.copy(), conn)
                cargar_dim_clientes_empresa(df_clientes_crudo, conn)
            finally:
                conn.close()
                print("\nINFO: Conexión a la base de datos cerrada.")
    
    print("\n=== FIN DEL PROCESO ETL DE CLIENTES ===")

if __name__ == '__main__':
    ejecutar_etl_clientes()