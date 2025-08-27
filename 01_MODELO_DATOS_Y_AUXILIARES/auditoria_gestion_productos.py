# 01_MODELO_DATOS_Y_AUXILIARES/auditoria_gestion_productos.py

import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def auditar_productos_sin_gestion():
    """
    Compara los productos con actividad reciente (ventas o inventario) con
    gestion_productos_aux y genera un CSV con los pendientes por clasificar.
    """
    print("=== INICIO DE LA AUDITORÍA DE PRODUCTOS SIN GESTIÓN ===")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        # --- PASO 1: Obtener productos con actividad reciente (Ventas O Inventario) ---
        # Los intervalos ('12 months', '3 months') son ajustables.
        print("INFO: Buscando productos con actividad reciente (ventas o inventario)...")
        query_activos = """
            -- Productos con ventas en los últimos 12 meses
            SELECT DISTINCT dp.codigo_erp, dp.referencia, dp.descripcion_erp
            FROM dim_productos AS dp
            JOIN hechos_ventas AS hv ON dp.id_producto = hv.id_producto_fk
            WHERE hv.fecha_sk >= NOW() - INTERVAL '12 months'

            UNION

            -- Productos con movimiento de inventario en los últimos 3 meses
            SELECT DISTINCT dp.codigo_erp, dp.referencia, dp.descripcion_erp
            FROM dim_productos AS dp
            JOIN Inventario_Actual AS ia ON dp.id_producto = ia.id_producto_fk
            WHERE ia.fecha_ultima_actualizacion >= NOW() - INTERVAL '3 months';
        """
        df_activos = pd.read_sql_query(query_activos, conn)
        print(f"INFO: Se encontraron {len(df_activos)} productos únicos con actividad reciente.")

        # --- El resto del script se mantiene sin cambios ---
        query_gestionados = """
            SELECT DISTINCT dp.codigo_erp, dp.referencia
            FROM gestion_productos_aux gpa
            JOIN dim_productos dp ON gpa.id_producto_fk = dp.id_producto;
        """
        df_gestionados = pd.read_sql_query(query_gestionados, conn)
        print(f"INFO: Se encontraron {len(df_gestionados)} productos ya clasificados.")

        if df_gestionados.empty:
            df_pendientes = df_activos
        else:
            df_merged = pd.merge(
                df_activos, df_gestionados,
                on=['codigo_erp', 'referencia'],
                how='left', indicator=True
            )
            df_pendientes = df_merged[df_merged['_merge'] == 'left_only'].drop(columns=['_merge'])

        if not df_pendientes.empty:
            print(f"\nALERTA: Se encontraron {len(df_pendientes)} productos activos pendientes por clasificar.")
            
            # (El resto del código para generar el CSV se mantiene igual)
            columnas_finales_csv = ['codigo_erp', 'referencia', 'categoria_gestion', 'subcategoria_1_gestion','subcategoria_2_gestion', 'descripcion_guia', 'clasificacion_py','equivalencia_py', 'peso_neto']
            df_salida = pd.DataFrame()
            df_salida['codigo_erp'] = df_pendientes['codigo_erp']
            df_salida['referencia'] = df_pendientes['referencia']
            df_salida['descripcion_guia'] = df_pendientes['descripcion_erp']
            for col in columnas_finales_csv:
                if col not in df_salida.columns:
                    df_salida[col] = ''
            df_salida = df_salida[columnas_finales_csv]
            ruta_salida = os.path.join(config.INFORMES_GENERADOS_DIR, 'productos_pendientes_por_clasificar.csv')
            df_salida.to_csv(ruta_salida, index=False)
            print(f"\n¡ÉXITO! Se ha generado tu 'lista de trabajo' en: {ruta_salida}")

        else:
            print("\n¡EXCELENTE! Todos los productos con actividad reciente están clasificados.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la auditoría: {e}")
    finally:
        if conn:
            conn.close()
            print("\nINFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    auditar_productos_sin_gestion()