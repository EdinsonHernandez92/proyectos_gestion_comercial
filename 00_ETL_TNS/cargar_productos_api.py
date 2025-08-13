# 00_ETL_TNS/cargar_productos_api.py

import pandas as pd
import requests
import os
import sys
from io import StringIO
from psycopg2 import extras

# Añadimos la ruta raíz del proyecto para poder importar nuestros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection, execute_query

def leer_mapeos():
    """
    Carga todos los archivos CSV de mapeo y corrección en diccionarios para una búsqueda rápida.
    """
    print("INFO: Cargando archivos de mapeo y corrección...")
    try:
        base_path = config.DATOS_ENTRADA_DIR

        # Mapeos simples (código de producto -> código corregido)
        df_lineas = pd.read_csv(os.path.join(base_path, 'mapeo_correccion_lineas.csv'), dtype=str)
        mapa_lineas = df_lineas.set_index('codigo_erp')['cod_linea_erp_corregido'].to_dict()

        df_grupos = pd.read_csv(os.path.join(base_path, 'mapeo_correccion_grupos.csv'), dtype=str)
        mapa_grupos = df_grupos.set_index('codigo_erp')['cod_grupo_articulo_corregido'].to_dict()

        df_dpto = pd.read_csv(os.path.join(base_path, 'mapeo_correccion_dpto.csv'), dtype=str)
        mapa_dpto = df_dpto.set_index('codigo_erp')['cod_dpto_sku_corregido'].to_dict()

        # Mapeo de marcas (nombre de marca + empresa -> código unificado)
        df_marcas = pd.read_csv(os.path.join(base_path, 'mapeo_marcas.csv'), dtype=str)
        # Creamos una llave compuesta para el diccionario: "nombre|empresa"
        #df_marcas['llave_compuesta'] = df_marcas['nombre_marca_erp'] + '|' + df_marcas['empresa_erp']        
        df_marcas['llave_compuesta'] = df_marcas['nombre_marca_erp'].fillna('') + ',' + df_marcas['empresa_erp'].fillna('')
        mapa_marcas = df_marcas.set_index('llave_compuesta')['cod_marca_unificado'].to_dict()

        mapeos = {
            "lineas": mapa_lineas,
            "grupos": mapa_grupos,
            "dptos": mapa_dpto,
            "marcas": mapa_marcas
        }
        print("INFO: Mapeos cargados exitosamente.")
        return mapeos
    except Exception as e:
        print(f"ERROR CRÍTICO al cargar los mapeos {e}")
        return None

def extraer_productos_api():
    """
    Se conecta a la API de TNS para cada empresa configurada, extrae la lista
    detallada de productos y los consolida en un único DataFrame.
    """
    print("INFO: Iniciando extracción de productos desde la API de TNS...")
    
    lista_dfs_empresas = []
    
    # Mapeo de las claves de la API a los nombres de nuestras columnas
    # La clave es el nombre en el JSON de la API, el valor es el nombre que usaremos en Pandas
    # Mapeamos directo a los nomber FINALES de la tabla dim_productos ---
    MAPEO_COLUMNAS_API = {
        "OCODIGO": "codigo_erp",
        "OREFERENCIA": "referencia",
        "ODESCRIP": "descripcion_erp",
        "OCODGRUPO": "cod_grupo_erp",
        "OCODLINEA": "cod_linea_erp",
        "ODEPARTAMENTOCODIGO": "cod_dpto_sku_erp",
        "ONOMMARCA": "nombre_marca_erp",
        "OPESO": "peso_bruto_erp",
        "OFACTOR": "factor_erp",
        "OPORIVA": "porcentaje_iva",
        "OULTIMOCOSTO": "costo_ult_erp",
        "OCOSTOPROMEDIO": "costo_promedio_erp"
    }

    for empresa_config in config.API_CONFIG_TNS:
        nombre_empresa = empresa_config["nombre_corto"]
        url_productos = config.API_URLS["productos"]
        
        print(f"--- Extrayendo para la empresa: {nombre_empresa} ---")
        
        params = {
            "empresa": empresa_config["empresa_tns"],
            "usuario": empresa_config["usuario_tns"],
            "password": empresa_config["password_tns"],
            "tnsapitoken": empresa_config["tnsapitoken"],
            "codsuc": empresa_config.get("cod_sucursal_tns", "00")
        }
        
        try:
            response = requests.get(url_productos, params=params, timeout=300) # Timeout de 5 minutos
            response.raise_for_status()
            
            # La lógica robusta de parseo de tu script original
            datos_api_raw = response.json()
            lista_productos_api = []
            
            if isinstance(datos_api_raw, dict) and datos_api_raw.get("status") == "OK":
                lista_productos_api = datos_api_raw.get("results", [])
            else:
                 print(f"ADVERTENCIA: La respuesta de la API para {nombre_empresa} no fue OK o no contenía 'results'.")

            if not lista_productos_api:
                print(f"INFO: No se encontraron productos para la empresa {nombre_empresa}.")
                continue # Pasa a la siguiente empresa

            # Procesamos la lista de productos
            productos_procesados = [{ nuestra_col: item.get(api_col) for api_col, nuestra_col in MAPEO_COLUMNAS_API.items() } for item in lista_productos_api if isinstance(item, dict)]
            if productos_procesados:
                df_empresa = pd.DataFrame(productos_procesados)
                df_empresa['empresa_erp'] = nombre_empresa
                lista_dfs_empresas.append(df_empresa)
                print(f"¡ÉXITO! Se procesaron {len(df_empresa)} productos de {nombre_empresa}.")
        except Exception as e:
            print(f"ERROR al procesar {nombre_empresa}: {e}")
    
    if lista_dfs_empresas:
        # 1. Creamos el DataFrame consolidado y lo guardamos en una variable
        df_consolidado = pd.concat(lista_dfs_empresas, ignore_index=True)

        # 2. AÑADIMOS LA LÍNEA PARA GUARDAR EL ARCHIVO
        #    (Recuerda cambiar 'run1.csv' a 'run2.csv' en la segunda ejecución)
        #print("INFO: Guardando la salida de la ejecución en run1.csv...")
        #df_consolidado.to_csv('run2.csv', index=False)

        # 3. Finalmente, devolvemos el DataFrame
        return df_consolidado
    return None


def transformar_productos(df_crudo, mapeos):
    """
    Aplica las correcciones de mapeo, sobreescribiendo los datos crudos.
    """
    print("\nINFO: Iniciando transformación de datos de productos...")
    if df_crudo is None or mapeos is None:
        print("ERROR: No se pueden transformar los datos por falta de DataFrame crudo o mapeos.")
        return None
    
    df =df_crudo.copy()

    # Limpiamos nulos en columnas clave para evitar errores
    columnas_texto_a_limpiar = ['codigo_erp', 'referencia', 'empresa_erp', 'nombre_marca_erp']
    for col in columnas_texto_a_limpiar:
        if col in df.columns:
            df[col] = df[col].fillna('')
    
    # Aplicamos las correcciones, SOBREESCRIBIENDO las columnas originales
        print("INFO: Aplicando correcciones de mapeo...")
    df['cod_linea_erp'] = df['codigo_erp'].map(mapeos['lineas']).fillna(df['cod_linea_erp'])
    df['cod_grupo_erp'] = df['codigo_erp'].map(mapeos['grupos']).fillna(df['cod_grupo_erp'])
    df['cod_dpto_sku_erp'] = df['codigo_erp'].map(mapeos['dptos']).fillna(df['cod_dpto_sku_erp'])

    print("INFO: Transformación completada.")
    return df

def cargar_productos_db(df_limpio, conn):
    """
    Carga el DataFrame limpio en la tabla dim_productos de forma masiva y segura.
    Utiliza INSERT ... ON CONFLICT para insertar nuevos y actualizar existentes.
    """
    print("\nINFO: Iniciando carga de productos en la base de datos...")
    if df_limpio is None or df_limpio.empty:
        print("ADVERTENCIA: No hay datos limpios para cargar.")
        return

    with conn.cursor() as cursor:
        try:
            # Columnas en el orden exacto de la tabla dim_productos
            columnas_db = [
                'codigo_erp', 'referencia', 'empresa_erp', 'descripcion_erp', 'cod_grupo_erp', 
                'cod_linea_erp', 'cod_dpto_sku_erp', 'peso_bruto_erp', 'factor_erp', 
                'porcentaje_iva', 'costo_promedio_erp', 'costo_ult_erp'
            ]
            
            # Columnas que se deben actualizar si el producto ya existe
            columnas_update = [
                'descripcion_erp', 'cod_grupo_erp', 'cod_linea_erp', 'cod_dpto_sku_erp',
                'costo_promedio_erp', 'costo_ult_erp'
            ]
            
            # Preparamos el string para la sección SET del UPDATE
            update_sql = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columnas_update])
            
            # Creamos la consulta SQL final (UPSERT)
            query = f"""
                INSERT INTO dim_productos ({", ".join(f'"{col}"' for col in columnas_db)})
                VALUES %s
                ON CONFLICT (codigo_erp, referencia, empresa_erp) DO UPDATE SET
                    {update_sql};
            """

            # Convertimos el DataFrame a una lista de tuplas para la inserción
            df_para_carga = df_limpio[columnas_db]
            datos_para_insertar = [tuple(row) for row in df_para_carga.itertuples(index=False)]

            print(f"INFO: Realizando UPSERT (INSERT/UPDATE) de {len(datos_para_insertar)} registros en 'dim_productos'...")
            extras.execute_values(cursor, query, datos_para_insertar, page_size=1000)
            
            # No olvides hacer commit para guardar los cambios
            conn.commit()
            print("¡ÉXITO! La tabla 'dim_productos' ha sido actualizada.")

        except Exception as e:
            print(f"ERROR CRÍTICO durante la carga a la base de datos: {e}")
            conn.rollback() # Revertimos la transacción en caso de error

if __name__ == '__main__':
    print("=== INICIO DEL PROCESO ETL DE PRODUCTOS ===")
    mapeos = leer_mapeos()
    if mapeos:
        df_crudo = extraer_productos_api()
        if df_crudo is not None:
            df_preparado = transformar_productos(df_crudo, mapeos)
            conn = get_db_connection()
            if conn:
                try:
                    cargar_productos_db(df_preparado, conn)
                finally:
                    conn.close()
                    print("\nINFO: Conexión a la base de datos cerrada.")
    print("\n=== FIN DEL PROCESO ETL DE PRODUCTOS ===")