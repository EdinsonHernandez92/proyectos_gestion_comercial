# 01_MODELO_DATOS_Y_AUXILIARES/sincronizar_gestion_productos.py

import pandas as pd
import sys
import os
from io import StringIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection, execute_query

def sincronizar_gestion_productos():
    """
    Lee el CSV maestro de gestión, busca los IDs correspondientes en dim_productos,
    y sincroniza (INSERT/UPDATE) la tabla gestion_productos_aux.
    NO MODIFICA LA TABLA dim_productos.
    """
    print("=== INICIO DE LA SINCRONIZACIÓN DE gestion_productos_aux ===")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        # --- PASO 1: Leer tu archivo CSV maestro ---
        ruta_csv = os.path.join(config.DATOS_ENTRADA_DIR, 'gestion_productos_aux.csv')
        df_csv = pd.read_csv(ruta_csv, dtype=str).where(pd.notnull(pd.read_csv(ruta_csv, dtype=str)), None)
        print(f"INFO: Se leyeron {len(df_csv)} filas del archivo 'gestion_productos_aux.csv'.")

        # --- PASO 2: Obtener el mapa de productos desde dim_productos para buscar IDs ---
        print("INFO: Creando mapa de productos desde la tabla dim_productos...")
        query_mapa = "SELECT id_producto, codigo_erp, referencia FROM dim_productos;"
        productos_db = execute_query(conn, query_mapa, fetch='all')
        
        # Como la clasificación es global, solo nos interesa la primera aparición del id
        mapa_productos = {}
        for id_prod, cod_erp, ref in productos_db:
            llave = (str(cod_erp), str(ref))
            if llave not in mapa_productos:
                mapa_productos[llave] = id_prod
        
        print(f"INFO: Mapa creado con {len(mapa_productos)} productos únicos para la búsqueda.")

        # --- PASO 3: "Traducir" los códigos de tu CSV a los IDs de la base de datos ---
        def obtener_id_producto(row):
            llave = (str(row['codigo_erp']), str(row['referencia']))
            return mapa_productos.get(llave)

        df_csv['id_producto_fk'] = df_csv.apply(obtener_id_producto, axis=1)

        # --- PASO 4: VALIDACIÓN MODIFICADA ---
        productos_no_encontrados = df_csv[df_csv['id_producto_fk'].isnull()]
        if not productos_no_encontrados.empty:
            print(f"\nADVERTENCIA: Se encontraron {len(productos_no_encontrados)} productos en tu CSV que no coinciden con 'dim_productos'.")
            
            # Generamos el archivo CSV de reporte
            ruta_reporte = os.path.join(config.INFORMES_GENERADOS_DIR, 'productos_no_encontrados.csv')
            
            # Seleccionamos las columnas originales del CSV que son relevantes para la corrección
            columnas_reporte = [col for col in df_csv.columns if col != 'id_producto_fk']
            productos_no_encontrados[columnas_reporte].to_csv(ruta_reporte, index=False)
            
            print("---------------------------------------------------------------------------------")
            print(f"Se ha generado un reporte en: {ruta_reporte}")
            print("Por favor, revisa ese archivo. Puede que solo necesites ajustar la 'referencia' en tu 'gestion_productos_aux.csv' para que coincida con la de 'dim_productos'.")
            print("---------------------------------------------------------------------------------")
            print("Proceso de sincronización cancelado hasta que se corrijan las inconsistencias.")
            return # Detenemos el script de forma controlada


        df_para_carga = df_csv.copy()
        df_para_carga.loc[:, 'id_producto_fk'] = df_para_carga['id_producto_fk'].astype(int)

        # --- PASO 5: Cargar y sincronizar ÚNICAMENTE la tabla gestion_productos_aux ---
        staging_table = "staging_gestion_productos"
        
        columnas_gestion = [
            'id_producto_fk', 'categoria_gestion', 'subcategoria_1_gestion', 
            'subcategoria_2_gestion', 'descripcion_guia', 'clasificacion_py', 
            'equivalencia_py', 'peso_neto'
        ]
        
        columnas_presentes = [col for col in columnas_gestion if col in df_para_carga.columns]
        df_final = df_para_carga[columnas_presentes]
        
        execute_query(conn, f'CREATE TEMP TABLE "{staging_table}" (LIKE gestion_productos_aux INCLUDING DEFAULTS);')

        buffer = StringIO()
        df_final.to_csv(buffer, index=False, header=False, sep=',')
        buffer.seek(0)
        
        columnas_sql = ",".join([f'"{c}"' for c in columnas_presentes])
        copy_sql = f'COPY "{staging_table}" ({columnas_sql}) FROM STDIN WITH (FORMAT CSV, DELIMITER \',\')'
        with conn.cursor() as cursor:
            cursor.copy_expert(copy_sql, buffer)
        
        columnas_update = [col for col in columnas_presentes if col != 'id_producto_fk']
        columnas_update_sql = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columnas_update])
        
        merge_sql = f"""
            INSERT INTO gestion_productos_aux ({columnas_sql})
            SELECT {columnas_sql}
            FROM "{staging_table}"
            ON CONFLICT (id_producto_fk) DO UPDATE SET {columnas_update_sql};
        """
        execute_query(conn, merge_sql)
        print("\n¡ÉXITO! La tabla 'gestion_productos_aux' ha sido sincronizada con tu archivo CSV.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la sincronización: {e}")
    finally:
        if conn:
            conn.close()
            print("INFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    sincronizar_gestion_productos()