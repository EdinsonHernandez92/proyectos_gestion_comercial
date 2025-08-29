# 01_MODELO_DATOS_Y_AUXILIARES/auditoria_gestion_clientes.py

import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def auditar_clientes_sin_gestion():
    """
    Busca clientes con ventas recientes que aún no han sido enlazados
    a un registro maestro y genera un CSV con los pendientes.
    """
    print("=== INICIO DE LA AUDITORÍA DE CLIENTES SIN GESTIÓN ===")
    conn = get_db_connection()
    if not conn: return

    try:
        # --- CONSULTA MODIFICADA ---
        # Ahora solo trae clientes con ventas en los últimos 24 meses.
        # Puedes ajustar el intervalo '24 months' según tus necesidades.
        query_pendientes = """
            SELECT DISTINCT dce.nit, dce.nombre_erp, dce.cod_cliente_erp, dce.empresa_erp
            FROM dim_clientes_empresa dce
            JOIN hechos_ventas hv ON dce.id_cliente_empresa = hv.id_cliente_empresa_fk
            WHERE dce.id_maestro_cliente_fk IS NULL
              AND hv.fecha_sk >= NOW() - INTERVAL '24 months';
        """
        df_pendientes = pd.read_sql_query(query_pendientes, conn)
        
        if not df_pendientes.empty:
            print(f"\nALERTA: Se encontraron {len(df_pendientes)} clientes con ventas recientes pendientes por enlazar al maestro.")
            
            df_salida = pd.DataFrame()
            df_salida['cod_cliente_maestro'] = df_pendientes['cod_cliente_erp']
            df_salida['nit'] = df_pendientes['nit']
            df_salida['nombre_unificado'] = df_pendientes['nombre_erp']
            df_salida['canal'] = ''
            df_salida['subcanal'] = ''
            df_salida['cod_cliente_erp_origen'] = df_pendientes['cod_cliente_erp']
            df_salida['empresa_erp_origen'] = df_pendientes['empresa_erp']

            ruta_salida = os.path.join(config.INFORMES_GENERADOS_DIR, 'clientes_pendientes_por_clasificar.csv')
            df_salida.to_csv(ruta_salida, index=False)
            
            print(f"\n¡ÉXITO! Se ha generado tu 'lista de trabajo' en: {ruta_salida}")
        else:
            print("\n¡EXCELENTE! Todos los clientes con actividad reciente ya están enlazados a un registro maestro.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la auditoría de clientes: {e}")
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    auditar_clientes_sin_gestion()