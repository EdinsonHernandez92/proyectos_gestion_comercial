# 01_MODELO_DATOS_Y_AUXILIARES/auditoria_gestion_productos.py

import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def auditar_productos_sin_gestion():
    """
    Compara dim_productos con gestion_productos_aux y genera un CSV con los
    productos que faltan por clasificar.
    """
    print("=== INICIO DE LA AUDITORÍA DE PRODUCTOS SIN GESTIÓN ===")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        # --- PASO 1: Obtener todos los productos únicos de la tabla maestra ---
        # Como la clasificación es global, solo necesitamos una instancia de cada (codigo_erp, referencia)
        query_todos = """
            SELECT DISTINCT codigo_erp, referencia, descripcion_erp
            FROM dim_productos;
        """
        df_todos = pd.read_sql_query(query_todos, conn)
        print(f"INFO: Se encontraron {len(df_todos)} productos únicos en 'dim_productos'.")

        # --- PASO 2: Obtener todos los productos que YA están clasificados ---
        query_gestionados = """
            SELECT DISTINCT dp.codigo_erp, dp.referencia
            FROM gestion_productos_aux gpa
            JOIN dim_productos dp ON gpa.id_producto_fk = dp.id_producto;
        """
        df_gestionados = pd.read_sql_query(query_gestionados, conn)
        print(f"INFO: Se encontraron {len(df_gestionados)} productos ya clasificados en 'gestion_productos_aux'.")

        # --- PASO 3: Encontrar los productos que faltan por clasificar ---
        if df_gestionados.empty:
            df_pendientes = df_todos
        else:
            # Hacemos un "merge" para encontrar las filas de df_todos que no están en df_gestionados
            df_merged = pd.merge(
                df_todos,
                df_gestionados,
                on=['codigo_erp', 'referencia'],
                how='left',
                indicator=True
            )
            df_pendientes = df_merged[df_merged['_merge'] == 'left_only'].drop(columns=['_merge'])

        # --- PASO 4: Preparar y generar el archivo CSV de salida ---
        if not df_pendientes.empty:
            print(f"\nALERTA: Se encontraron {len(df_pendientes)} productos pendientes por clasificar.")
            
            # Definimos la estructura completa de nuestro archivo CSV de gestión
            columnas_finales_csv = [
                'codigo_erp', 'referencia', 'categoria_gestion', 'subcategoria_1_gestion',
                'subcategoria_2_gestion', 'descripcion_guia', 'clasificacion_py',
                'equivalencia_py', 'peso_neto'
            ]
            
            # Creamos un nuevo DataFrame para la salida
            df_salida = pd.DataFrame()
            
            # Pasamos las columnas que ya tenemos
            df_salida['codigo_erp'] = df_pendientes['codigo_erp']
            df_salida['referencia'] = df_pendientes['referencia']
            # Usamos la descripción del ERP como punto de partida para la descripción guía
            df_salida['descripcion_guia'] = df_pendientes['descripcion_erp']
            
            # Rellenamos las columnas de clasificación que tú debes completar
            for col in columnas_finales_csv:
                if col not in df_salida.columns:
                    df_salida[col] = '' # O None
            
            # Reordenamos las columnas para que coincidan con tu archivo maestro
            df_salida = df_salida[columnas_finales_csv]
            
            # Guardamos el archivo
            ruta_salida = os.path.join(config.DATOS_ENTRADA_DIR, 'productos_pendientes_por_clasificar.csv')
            df_salida.to_csv(ruta_salida, index=False)
            
            print(f"\n¡ÉXITO! Se ha generado el archivo de pendientes en:")
            print(ruta_salida)
            print("Por favor, abre este archivo, rellena las columnas de clasificación y luego copia las filas a tu archivo 'gestion_productos_aux.csv'.")

        else:
            print("\n¡EXCELENTE! No se encontraron productos nuevos pendientes de clasificación. Todo está al día.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la auditoría: {e}")
    finally:
        if conn:
            conn.close()
            print("\nINFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    auditar_productos_sin_gestion()