# 00_ETL_TNS/cargar_ventas_api.py

import pandas as pd
import requests
import os
import sys
from datetime import date, timedelta, datetime
from psycopg2 import extras

# --- Configuración del Proyecto ---
# Añade la ruta raíz del proyecto al path de Python para poder importar nuestros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config  # Importa nuestras configuraciones (URLs, credenciales)
from db_utils import get_db_connection, execute_query # Importa nuestras funciones de base de datos

def extraer_ventas_api(fecha_desde, fecha_hasta):
    """
    Paso 1: EXTRACCIÓN
    Se conecta a la API de TNS y extrae los datos de ventas crudos para un rango de fechas.
    """
    print(f"INFO: Iniciando extracción de ventas desde {fecha_desde} hasta {fecha_hasta}...")
    
    # Creamos una lista vacía para guardar los datos de cada empresa
    lista_dfs_empresas = []
    
    # Diccionario "traductor". La clave es el nombre del campo en la API,
    # el valor es el nombre que le daremos temporalmente en nuestro script.
    MAPEO_COLUMNAS_API = {
        'DEKARDEXID': 'id_transaccion_erp', 'NUMFACTURA': 'numero_factura_erp',
        'FECHA': 'fecha_str', 'CODCLIENTE': 'cod_cliente_erp',
        'CODIGO': 'codigo_producto_erp', 'REFERENCIA': 'referencia_erp',
        'CODVENDEDOR': 'cod_vendedor_erp', 'CANT': 'cantidad',
        'PREBASE': 'valor_base', 'DESCUENTO': 'valor_descuento',
        'PREIVA': 'valor_iva', 'PRECIOTOT': 'valor_total',
        'COSTOPROMEDIO': 'costo_total', 'PRECIOLISTA': 'precio_lista',
        'FORMAPAGO': 'forma_pago_erp', 'CODBODEGA': 'bodega_erp',
        'LISTAPRECIO': 'lista_precio_erp', 'OBSERV': 'observaciones_erp',
        'MOTIVODEVOLUCION': 'motivo_devolucion_erp', 'PEDIDO': 'pedido_tiendapp'
    }

    # Hacemos un bucle para procesar cada empresa definida en nuestro config.py
    for empresa_config in config.API_CONFIG_TNS:
        nombre_empresa = empresa_config["nombre_corto"]
        url_ventas = config.API_URLS["ventas"]
        print(f"--- Extrayendo para la empresa: {nombre_empresa} ---")
        
        # Preparamos los parámetros para la llamada a la API
        params = {
            "empresa": empresa_config["empresa_tns"],
            "usuario": empresa_config["usuario_tns"],
            "password": empresa_config["password_tns"],
            "tnsapitoken": empresa_config["tnsapitoken"],
            "CodSucursal": "00",
            # La API espera el formato MM/DD/YYYY, así que lo convertimos
            "fechaInicial": datetime.strptime(fecha_desde, "%Y-%m-%d").strftime("%m/%d/%Y"),
            "fechaFin": datetime.strptime(fecha_hasta, "%Y-%m-%d").strftime("%m/%d/%Y"),
        }
        
        try:
            # Hacemos la llamada a la API
            response = requests.get(url_ventas, params=params, timeout=600)
            response.raise_for_status() # Lanza un error si la respuesta no es exitosa (ej. 404, 500)
            datos_api_raw = response.json()
            
            # Verificamos que la respuesta tenga el formato esperado y extraemos la lista de ventas
            if isinstance(datos_api_raw, dict) and (datos_api_raw.get("Data") or datos_api_raw.get("results")):
                lista_ventas = datos_api_raw.get("Data") or datos_api_raw.get("results")
                df_empresa = pd.DataFrame(lista_ventas)
                
                if not df_empresa.empty:
                    # Etiquetamos cada fila con el nombre de la empresa para poder identificarla
                    df_empresa['empresa_erp'] = nombre_empresa
                    lista_dfs_empresas.append(df_empresa)
                    print(f"¡ÉXITO! Se extrajeron {len(df_empresa)} registros de ventas de {nombre_empresa}.")
        except Exception as e:
            print(f"ERROR al procesar {nombre_empresa}: {e}")

    # Si no obtuvimos datos de ninguna empresa, terminamos el proceso
    if not lista_dfs_empresas:
        print("INFO: No se encontraron ventas para el período especificado.")
        return None
        
    # Unimos los datos de todas las empresas en una sola tabla grande
    df_consolidado = pd.concat(lista_dfs_empresas, ignore_index=True)
    # Aplicamos el renombrado de columnas que definimos en el diccionario
    df_consolidado = df_consolidado.rename(columns=MAPEO_COLUMNAS_API)
    print(f"\nINFO: Extracción completada. Total de registros de ventas: {len(df_consolidado)}")
    
    return df_consolidado

def transformar_y_enriquecer_ventas(df_ventas, conn):
    """
    Paso 2: TRANSFORMACIÓN Y ENRIQUECIMIENTO
    Toma los datos crudos, los limpia y los enriquece con los IDs de las tablas de dimensión.
    Toma el DF de ventas y lo enriquece con los Foreign Keys de las dimensiones.
    """
    print("\nINFO: Iniciando transformación y enriquecimiento de datos de ventas...")
    df = df_ventas.copy() # Hacemos una copia para no modificar el DataFrame original

    # --- 1. Limpieza y Aplicación de Reglas de Negocio ---
    # Convertimos la columna de fecha (texto) a un objeto de fecha real
    df['fecha_sk'] = pd.to_datetime(df['fecha_str'], format='%d/%m/%Y', errors='coerce').dt.date
    # Rellenamos valores nulos en la referencia para poder hacer la búsqueda
    df['referencia_erp'] = df['referencia_erp'].fillna('')
    # Aplicamos la regla de negocio: si la referencia está vacía, usamos el código del producto
    df.loc[df['referencia_erp'] == '', 'referencia_erp'] = df['codigo_producto_erp']
    
    # --- 2. Creación de Mapas de Búsqueda desde las Dimensiones ---
    print("INFO: Creando mapas de dimensiones para el enriquecimiento...")
    mapa_productos = pd.read_sql("SELECT id_producto, codigo_erp, referencia, empresa_erp FROM dim_productos", conn)
    mapa_clientes = pd.read_sql("SELECT id_cliente_empresa, cod_cliente_erp, empresa_erp FROM dim_clientes_empresa", conn)
    mapa_roles = pd.read_sql("SELECT id_rol_historia, cod_rol_erp, empresa_erp, fecha_inicio_validez, fecha_fin_validez FROM dim_roles_comerciales_historia", conn)
    
    
    ############## mapeo bodegas ###########
    mapa_bodegas = pd.read_sql("SELECT id_bodega, cod_bodega_erp FROM dim_bodegas", conn)
    ############# -------------  ###########
    
    # --- 3. Enriquecimiento del DataFrame con los Foreign Keys (FKs) ---
    print("INFO: Uniendo ventas con dimensiones para obtener los IDs...")
    # Unimos con productos para obtener id_producto_fk
    df = pd.merge(df, mapa_productos, left_on=['codigo_producto_erp', 'referencia_erp', 'empresa_erp'], right_on=['codigo_erp', 'referencia', 'empresa_erp'], how='left')
    df.rename(columns={'id_producto': 'id_producto_fk'}, inplace=True)
    
    # Unimos con clientes para obtener id_cliente_empresa_fk
    df = pd.merge(df, mapa_clientes, on=['cod_cliente_erp', 'empresa_erp'], how='left')
    df.rename(columns={'id_cliente_empresa': 'id_cliente_empresa_fk'}, inplace=True)
    
    ########## Union con dim_bodegas para obtener el id_bodega_fk ############
    # Usamos left_on y right_on para especificar los nombres de columna diferentes en cada tabla
    df = pd.merge(df, mapa_bodegas, left_on='bodega_erp', right_on='cod_bodega_erp', how='left')
    df.rename(columns={'id_bodega': 'id_bodega_fk'}, inplace=True)

    # Unimos con roles para obtener el id_rol_historia (este es el más complejo por las fechas)
    df = pd.merge(df, mapa_roles, left_on=['cod_vendedor_erp', 'empresa_erp'], right_on=['cod_rol_erp', 'empresa_erp'], how='left')
    # Después de unir, filtramos para quedarnos solo con el rol que estaba activo en la fecha de la venta
    df['id_rol_historia_fk'] = df.apply(
        lambda row: row['id_rol_historia'] if pd.notnull(row['id_rol_historia']) and row['fecha_inicio_validez'] <= row['fecha_sk'] <= row['fecha_fin_validez'] else None,
        axis=1
    )

    # --- 4. Preparación Final ---
    # Eliminamos las filas que no pudieron ser enriquecidas (ej. una venta de un producto que no existe)
    ############### SE AGREGA id_bodega_fk ###########
    fks_a_validar = ['id_producto_fk', 'id_cliente_empresa_fk', 'id_rol_historia_fk', 'id_bodega_fk']
    df_final = df.dropna(subset=fks_a_validar)
    print(f"INFO: {len(df_final)} filas de ventas enriquecidas y válidas para la carga.")
    
    # Seleccionamos y ordenamos las columnas finales para que coincidan con la tabla hechos_ventas
    columnas_hechos = [
        'fecha_sk', 'id_producto_fk', 'id_cliente_empresa_fk', 'id_rol_historia_fk',
        'codigo_producto_erp', 'cod_cliente_erp', 'cod_rol_erp', 'empresa_erp',
        'cantidad', 'valor_base','valor_descuento', 'valor_iva', 'valor_total',
        'costo_total', 'precio_lista', 'id_transaccion_erp', 'numero_factura_erp',
        'forma_pago_erp', 'id_bodega_fk', 'bodega_erp', 'lista_precio_erp',
        'observaciones_erp', 'motivo_devolucion_erp', 'pedido_tiendapp'
    ]
    
    # Aseguramos que solo seleccionamos las columnas que realmente existen en el DataFrame
    columnas_presentes = [col for col in columnas_hechos if col in df_final.columns]
    
    return df_final[columnas_presentes]

def cargar_ventas_db(df_enriquecido, fecha_desde, fecha_hasta, conn):
    """
    Paso 3: CARGA
    Implementa la estrategia de 'Borrar y Cargar' para sincronizar los datos.
    """
    print("\nINFO: Iniciando carga de ventas en la base de datos...")
    if df_enriquecido is None or df_enriquecido.empty:
        print("ADVERTENCIA: No hay datos de ventas para cargar.")
        return

    try:
        # Paso 1: Borrar los datos existentes para el rango de fechas
        delete_query = "DELETE FROM hechos_ventas WHERE fecha_sk BETWEEN %s AND %s;"
        execute_query(conn, delete_query, params=(fecha_desde, fecha_hasta))
        print(f"INFO: Registros de ventas eliminados para el período {fecha_desde} a {fecha_hasta}.")

        # Paso 2: Cargar los nuevos datos
        columnas_db = list(df_enriquecido.columns)
        datos_para_insertar = [tuple(row) for row in df_enriquecido.itertuples(index=False)]
        
        query_insert = f"INSERT INTO hechos_ventas ({', '.join(f'\"{c}\"' for c in columnas_db)}) VALUES %s;"
        #query_insert = f"INSERT INTO hechos_ventas ({', '.join(columnas_db)}) VALUES %s;"
        
        with conn.cursor() as cursor:
            extras.execute_values(cursor, query_insert, datos_para_insertar, page_size=1000)
            conn.commit()
            print(f"¡ÉXITO! Se han insertado {cursor.rowcount} nuevos registros en 'hechos_ventas'.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la carga de ventas: {e}")
        conn.rollback() # Revertimos cualquier cambio si hay un error

def ejecutar_etl_ventas():
    print("=== INICIO DEL PROCESO ETL DE VENTAS")

    # Por defecto, el script buscará las ventas desde ayer hasta hoy
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=1)
    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')

    # --- Orquestación del Proceso ---
    # 1. Extraer
    df_ventas_crudo = extraer_ventas_api(fecha_inicio_str, fecha_fin_str)

    # 2. Transformar y Cargar (solo si la extracción fue exitosa)
    if df_ventas_crudo is not None and not df_ventas_crudo.empty:
        conn = get_db_connection()
        if conn:
            try:
                df_ventas_enriquecido = transformar_y_enriquecer_ventas(df_ventas_crudo, conn)
                cargar_ventas_db(df_ventas_enriquecido, fecha_inicio_str, fecha_fin_str, conn)
            finally:
                conn.close()
    print("\n=== FIN DEL PROCESO ETL DE VENTAS ===")

if __name__ == '__main__':
    ejecutar_etl_ventas()