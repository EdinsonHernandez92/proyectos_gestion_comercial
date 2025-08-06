# 00_ETL_TNS/cargar_productos_api.py

import pandas as pd
import requests
import os
import sys
import json

# Añadimos la ruta raíz del proyecto para poder importar nuestros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def extraer_productos_api():
    """
    Se conecta a la API de TNS para cada empresa configurada, extrae la lista
    detallada de productos y los consolida en un único DataFrame.
    """
    print("INFO: Iniciando extracción de productos desde la API de TNS...")
    
    lista_dfs_empresas = []
    
    # Mapeo de las claves de la API a los nombres de nuestras columnas
    # La clave es el nombre en el JSON de la API, el valor es el nombre que usaremos en Pandas
    MAPEO_COLUMNAS_API = {
        "OCODIGO": "codigo_erp",
        "OREFERENCIA": "referencia",
        "ODESCRIP": "descripcion_erp",
        "OCODGRUPO": "cod_grupo_erp",
        "OCODLINEA": "cod_linea_erp",
        "ODEPARTAMENTOCODIGO": "cod_dpto_sku_erp",
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
            productos_procesados = []
            for item_producto in lista_productos_api:
                if isinstance(item_producto, dict):
                    # Creamos un nuevo diccionario solo con las columnas que nos interesan
                    producto_limpio = {
                        nuestra_col: item_producto.get(api_col) 
                        for api_col, nuestra_col in MAPEO_COLUMNAS_API.items()
                    }
                    productos_procesados.append(producto_limpio)
            
            if productos_procesados:
                df_empresa = pd.DataFrame(productos_procesados)
                df_empresa['empresa_erp'] = nombre_empresa
                lista_dfs_empresas.append(df_empresa)
                print(f"¡ÉXITO! Se procesaron {len(df_empresa)} productos de {nombre_empresa}.")

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Falló la conexión a la API para {nombre_empresa}. Error: {e}")
        except json.JSONDecodeError:
            print(f"ERROR: La respuesta de la API para {nombre_empresa} no es un JSON válido. Contenido: {response.text[:200]}")
        except Exception as e:
            print(f"ERROR: Ocurrió un error inesperado al procesar los datos de {nombre_empresa}. Error: {e}")
            
    if lista_dfs_empresas:
        df_consolidado = pd.concat(lista_dfs_empresas, ignore_index=True)
        print(f"\nINFO: Extracción completada. Total de productos consolidados: {len(df_consolidado)}")
        return df_consolidado
    else:
        print("\nERROR: No se pudo extraer datos de ninguna empresa.")
        return None

# --- Las siguientes funciones las construiremos en los próximos pasos ---
def transformar_productos(df_crudo):
    print("INFO: (Pendiente) Transformando datos de productos...")
    return df_crudo

def cargar_productos_db(df_limpio, conn):
    print("INFO: (Pendiente) Cargando productos en la base de datos...")


if __name__ == '__main__':
    print("=== INICIO DEL PROCESO ETL DE PRODUCTOS ===")
    
    df_productos_crudo = extraer_productos_api()
    
    if df_productos_crudo is not None:
        print("\n--- Vista previa de los datos extraídos (primeras 5 filas) ---")
        print(df_productos_crudo.head())
        print("\n--- Columnas del DataFrame ---")
        print(df_productos_crudo.columns)
        print("\n--- Información del DataFrame consolidado ---")
        df_productos_crudo.info(verbose=False)
        
    print("\n=== FIN DEL PROCESO ETL DE PRODUCTOS ===")