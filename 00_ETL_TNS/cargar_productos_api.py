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
        df_marcas['llave_compuesta'] = df_marcas['nombre_marca_erp'] + '|' + df_marcas['empresa_erp']
        mapa_marcas = df_marcas.set_index('llave_compuesta')['cod_marca_unificado'].to_dict()

        mapeos = {
            "lineas": mapa_lineas,
            "grupos": mapa_grupos,
            "dptos": mapa_dpto,
            "marcas": mapa_marcas
        }
        print("INFO: Mapeos cargados exitosamente.")
        return mapeos
    
    except FileNotFoundError as e:
        print(f"ERROR CRÍTICO: No se encontró un archivo de mapeo esencial: {e}. El proceso no puede continuar.")
        return None
    except Exception as e:
        print(f"ERROR CRÍTICO: Ocurrió un error al cargar los mapeos: {e}")
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


def transformar_productos(df_crudo, mapeos):
    """
    Aplica las reglas de negocio y los mapeos para limpiar el DataFrame.
    Crea las nuevas columnas "_limpio" con los códigos de negocio unificados.
    """
    print("\nINFO: Iniciando transformando datos de productos...")
    if df_crudo is None or mapeos is None:
        print("ERROR: No se pueden transformar los datos por falta de DataFrame crudo o mapeos.")
        return None
    
    df =df_crudo.copy()

    # --- Aplicar mapeos simples (basados solo en 'codigo_erp') ---
    print("INFO: Aplicando correcciones para Líneas, Grupos y Departamentos...")
    df['cod_linea_erp_limpio'] = df['codigo_erp'].map(mapeos['lineas']).fillna(df['cod_linea_erp'])
    df['cod_grupo_limpio'] = df['codigo_erp'].map(mapeos['grupos']).fillna(df['cod_grupo_erp'])
    df['cod_dpto_sku_limpio'] = df['codigo_erp'].map(mapeos['dptos']).fillna(df['cod_dpto_sku_erp'])

    # --- Aplicar mapeo de marcas (basado en 'nombre_marca_erp' y 'empresa_epr') ---
    print("\nINFO: Aplicando correcciones para Marcas...")
    def mapear_marca(row):
        llave = f"{row['nombre_marca_erp']}|{row['empresa_erp']}"
        return mapeos['marcas'].get(llave, None) # Si no hay mapeo, devuelve None (o un valor por defecto)
    
    df['cod_marca_limpio'] = df.apply(mapear_marca, axis=1)

    print("INFO: Transformación completada.")
    return df

def cargar_productos_db(df_limpio, conn):
    print("INFO: (Pendiente) Cargando productos en la base de datos...")


if __name__ == '__main__':
    print("=== INICIO DEL PROCESO ETL DE PRODUCTOS ===")
    
    mapeos_cargados = leer_mapeos()

    # El procesos solo continúa si los mapeos se cargaron correctamente
    if mapeos_cargados:
        df_productos_crudo = extraer_productos_api()

        if df_productos_crudo is not None:
            df_productos_limpio = transformar_productos(df_productos_crudo, mapeos_cargados)

            print("\n--- Vista previa de los datos transformados (primeras 5 filas) ---")
            # Mostramos las columnas crudas y las limpias para comparar
            columnas_a_mostrar = [
                'codigo_erp', 'empresa_erp',
                'cod_linea_erp', 'cod_linea_erp',
                'nombre_marca_erp', 'cod_marca_limpio'
            ]
            print(df_productos_limpio[columnas_a_mostrar].head(10))

            # conn = get_db_connection()
            # if conn:
            #   cargar_productos_db(df_productos_limpio, conn)
            #   conn.close()
        
    print("\n=== FIN DEL PROCESO ETL DE PRODUCTOS ===")