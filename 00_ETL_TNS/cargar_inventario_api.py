# 00_ETL_TNS/cargar_inventario_api.py

import pandas as pd
import requests
import os
import sys
from datetime import datetime
from psycopg2 import extras

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def extraer_y_transformar_inventario():
    """
    Extrae y transforma los datos de inventario desde la API, aplicando la lógica de negocio.
    """
    print("INFO: Iniciando extracción y transformación de inventario...")
    
    lista_dfs_finales = []
    
    for empresa_config in config.API_CONFIG_TNS:
        nombre_empresa = empresa_config["nombre_corto"]
        url_productos = config.API_URLS["productos"]
        print(f"--- Procesando inventario para: {nombre_empresa} ---")
        
        params = { "empresa": empresa_config["empresa_tns"], "usuario": empresa_config["usuario_tns"], "password": empresa_config["password_tns"], "tnsapitoken": empresa_config["tnsapitoken"], "codsuc": "00"}
        
        try:
            response = requests.get(url_productos, params=params, timeout=300)
            response.raise_for_status()
            datos_api_raw = response.json()
            
            if not (isinstance(datos_api_raw, dict) and datos_api_raw.get("status") == "OK"):
                continue

            # --- LÓGICA DE EXTRACCIÓN SIMPLIFICADA Y CORREGIDA ---
            # Aplanamos el JSON directamente
            df_empresa = pd.json_normalize(
                datos_api_raw.get("results", []),
                record_path='Bodegas',
                meta=['OCODIGO', 'OREFERENCIA', 'Items'],
                errors='ignore' # Ignora productos sin la estructura de Bodegas
            )
            if df_empresa.empty: continue
            
            # Añadimos la columna de la empresa
            df_empresa['empresa_erp'] = nombre_empresa
            
            # Aplicamos los filtros de negocio
            bodegas_permitidas = empresa_config.get("bodegas_permitidas", [])
            df_empresa = df_empresa[df_empresa['OCODBODEGA'].isin(bodegas_permitidas)]
            
            if nombre_empresa in ["CAMDUN", "GMD"]:
                lista_precio_permitida = empresa_config.get("lista_precio_permitida", "1")
                mask = df_empresa['Items'].apply(lambda items: isinstance(items, list) and any(str(item.get("OCODLISTA", "")).strip() == lista_precio_permitida for item in items))
                df_empresa = df_empresa[mask]
            
            if not df_empresa.empty:
                lista_dfs_finales.append(df_empresa)
                print(f"¡ÉXITO! Se procesaron {len(df_empresa)} registros de inventario para {nombre_empresa}.")

        except Exception as e:
            print(f"ERROR al procesar {nombre_empresa}: {e}")

    if lista_dfs_finales:
        df_consolidado = pd.concat(lista_dfs_finales, ignore_index=True)
        df_consolidado = df_consolidado.rename(columns={
            'OCODIGO': 'codigo_erp', 'OREFERENCIA': 'referencia',
            'OCODBODEGA': 'cod_bodega_erp', 'OEXISTENCIA': 'cantidad_disponible'
        })
        columnas_finales = ['codigo_erp', 'referencia', 'empresa_erp', 'cod_bodega_erp', 'cantidad_disponible']
        df_consolidado = df_consolidado[columnas_finales]
        
        print(f"\nINFO: Extracción completada. Total de registros de inventario: {len(df_consolidado)}")
        return df_consolidado
    return None

def cargar_inventario_db(df_inventario, conn):
    """Carga el DataFrame de inventario en la tabla Inventario_Actual."""
    print("\nINFO: Iniciando carga de inventario en la base de datos...")
    if df_inventario is None or df_inventario.empty:
        print("ADVERTENCIA: No hay datos de inventario para cargar.")
        return

    try:
        # --- PASO 1: Crear mapas para buscar los FKs ---
        mapa_productos = pd.read_sql("SELECT id_producto, codigo_erp, referencia, empresa_erp FROM dim_productos", conn)
        mapa_productos_dict = {(row.codigo_erp, row.referencia, row.empresa_erp): row.id_producto for row in mapa_productos.itertuples(index=False)}
        
        mapa_bodegas = pd.read_sql("SELECT id_bodega, cod_bodega_erp FROM dim_bodegas", conn)
        mapa_bodegas_dict = mapa_bodegas.set_index('cod_bodega_erp')['id_bodega'].to_dict()

        # --- PASO 2: Enriquecer el DataFrame con los FKs ---
        df_inventario['id_producto_fk'] = df_inventario.apply(lambda row: mapa_productos_dict.get((row['codigo_erp'], row['referencia'], row['empresa_erp'])), axis=1)
        df_inventario['id_bodega_fk'] = df_inventario['cod_bodega_erp'].map(mapa_bodegas_dict)

        df_para_carga = df_inventario.dropna(subset=['id_producto_fk', 'id_bodega_fk']).copy()
        print(f"INFO: {len(df_para_carga)} registros de inventario válidos para cargar.")
        if df_para_carga.empty: return

        # --- CORRECCIÓN DEFINITIVA para SettingWithCopyWarning ---
        # Usamos .loc para asignar la nueva columna de forma explícita
        df_para_carga.loc[:, 'fecha_ultima_actualizacion'] = datetime.now()
        df_para_carga.loc[:, 'id_producto_fk'] = df_para_carga['id_producto_fk'].astype(int)
        df_para_carga.loc[:, 'id_bodega_fk'] = df_para_carga['id_bodega_fk'].astype(int)

        # --- PASO 3: Cargar los datos usando UPSERT ---
        columnas_db = ['id_producto_fk', 'id_bodega_fk', 'empresa_erp', 'cantidad_disponible', 'fecha_ultima_actualizacion']
        datos_para_upsert = [tuple(row) for row in df_para_carga[columnas_db].itertuples(index=False)]

        query = f"""
            INSERT INTO Inventario_Actual ({", ".join(columnas_db)}) VALUES %s
            ON CONFLICT (id_producto_fk, id_bodega_fk, empresa_erp) DO UPDATE SET
                cantidad_disponible = EXCLUDED.cantidad_disponible,
                fecha_ultima_actualizacion = EXCLUDED.fecha_ultima_actualizacion;
        """
        
        with conn.cursor() as cursor:
            extras.execute_values(cursor, query, datos_para_upsert, page_size=1000)
            conn.commit()
            print(f"¡ÉXITO! La tabla 'Inventario_Actual' ha sido actualizada. {cursor.rowcount} filas afectadas.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la carga de inventario: {e}")
        conn.rollback()

def ejecutar_etl_inventario():
    print("=== INICIO DEL PROCESO ETL DE INVENTARIO ===")
    df_inventario = extraer_y_transformar_inventario()

    if df_inventario is not None and not df_inventario.empty:
        conn = get_db_connection()
        if conn:
            try:
                cargar_inventario_db(df_inventario, conn)
            finally:
                conn.close()
    print("\n=== FIN DEL PROCESO ETL DE INVENTARIO ===")

if __name__ == '__main__':
    ejecutar_etl_inventario()