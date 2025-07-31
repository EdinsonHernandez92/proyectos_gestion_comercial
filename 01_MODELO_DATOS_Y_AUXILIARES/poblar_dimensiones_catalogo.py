# 01_MODELO_DATOS_Y_AUXILIARES/poblar_dimensiones_catalogo.py

import pandas as pd
import psycopg2
from psycopg2 import extras
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_CONFIG
from db_utils import get_db_connection

def cargar_csv_a_tabla(ruta_csv, nombre_tabla, mapeo_columnas, columna_conflicto, conn, dtypes=None):
    """
    Función genérica para cargar un archivo CSV en una tabla de la base de datos.
    Ignora las filas que ya existen basadas en la columna de conflicto.
    Acepta un diccionario de dtypes para forzar tipos de dato en la lectura del CSV.
    """
    try:
        cursor = conn.cursor()
        
        # --- CAMBIO IMPORTANTE AQUÍ ---
        # Usamos el parámetro dtype para forzar que las columnas de código se lean como texto (str).
        df = pd.read_csv(ruta_csv, dtype=dtypes)
        
        df.rename(columns=mapeo_columnas, inplace=True)
        
        columnas_bd = ', '.join([f'"{col}"' for col in df.columns])
        
        query = f"""
            INSERT INTO public.{nombre_tabla} ({columnas_bd}) VALUES %s
            ON CONFLICT ("{columna_conflicto}") DO NOTHING;
        """
        
        datos_para_insertar = [tuple(row) for row in df.itertuples(index=False)]
        
        if not datos_para_insertar:
            print(f"INFO: No hay datos para procesar en '{os.path.basename(ruta_csv)}' para la tabla '{nombre_tabla}'.")
            return

        print(f"INFO: Insertando/actualizando {len(datos_para_insertar)} registros en la tabla '{nombre_tabla}'...")
        extras.execute_values(cursor, query, datos_para_insertar)
        
        conn.commit()
        print(f"¡ÉXITO! La tabla '{nombre_tabla}' ha sido actualizada.")
        
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo CSV en la ruta: {ruta_csv}")
    except Exception as e:
        print(f"ERROR: Ocurrió un error al cargar datos en '{nombre_tabla}': {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()

def poblar_catalogos():
    """
    Función principal que orquesta la carga de todas las tablas de catálogo.
    """
    conn = get_db_connection()
    if not conn:
        print("ERROR: No se pudo establecer conexión con la base de datos. Proceso cancelado.")
        return

    base_path = os.path.join(os.path.dirname(__file__), '..', 'datos_entrada')

    try:
        # --- Cargar Dim_Lineas ---
        print("\n--- Iniciando carga de Dim_Lineas ---")
        ruta_lineas = os.path.join(base_path, 'dim_lineas.csv')
        mapeo_lineas = {"cod_linea_erp": "cod_linea_erp", "desc_linea": "desc_linea"}
        dtypes_lineas = {"cod_linea_erp": str} # Le decimos a Pandas que lea el código como texto
        cargar_csv_a_tabla(ruta_lineas, 'Dim_Lineas', mapeo_lineas, "cod_linea_erp", conn, dtypes=dtypes_lineas)

        # --- Cargar Dim_Marcas ---
        print("\n--- Iniciando carga de Dim_Marcas ---")
        ruta_marcas = os.path.join(base_path, 'dim_marcas.csv')
        mapeo_marcas = {"cod_marca": "cod_marca", "nombre_marca": "nombre_marca"}
        dtypes_marcas = {"cod_marca": str} # Le decimos a Pandas que lea el código como texto
        cargar_csv_a_tabla(ruta_marcas, 'Dim_Marcas', mapeo_marcas, "cod_marca", conn, dtypes=dtypes_marcas)

        # --- Cargar Dim_Dpto_sku ---
        print("\n--- Iniciando carga de Dim_Dpto_sku ---")
        ruta_dpto = os.path.join(base_path, 'dim_dpto_sku.csv')
        mapeo_dpto = {"cod_dpto_sku": "cod_dpto_sku", "desc_dpto_sku": "desc_dpto_sku"}
        dtypes_dpto = {"cod_dpto_sku": str} # Le decimos a Pandas que lea el código como texto
        cargar_csv_a_tabla(ruta_dpto, 'Dim_Dpto_sku', mapeo_dpto, "cod_dpto_sku", conn, dtypes=dtypes_dpto)
        
        # --- Cargar Dim_Grupos ---
        print("\n--- Iniciando carga de Dim_Grupos ---")
        ruta_grupos = os.path.join(base_path, 'dim_grupos.csv')
        mapeo_grupos = {"cod_grupo_articulo": "cod_grupo_articulo", "nombre_grupo_articulo": "nombre_grupo_articulo"}
        dtypes_grupos = {"cod_grupo_articulo": str} # Le decimos a Pandas que lea el código como texto
        cargar_csv_a_tabla(ruta_grupos, 'Dim_Grupos', mapeo_grupos, "cod_grupo_articulo", conn, dtypes=dtypes_grupos)

    finally:
        if conn:
            conn.close()
            print("\nINFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    print("=== INICIO DEL PROCESO DE CARGA DE DIMENSIONES CATÁLOGO ===")
    poblar_catalogos()
    print("\n=== FIN DEL PROCESO DE CARGA ===")