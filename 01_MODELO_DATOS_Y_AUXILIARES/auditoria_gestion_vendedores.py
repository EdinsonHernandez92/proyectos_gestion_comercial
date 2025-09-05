# 01_MODELO_DATOS_Y_AUXILIARES/auditoria_gestion_vendedores.py

import pandas as pd
import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection

def auditar_vendedores():
    """
    Compara los datos de vendedores de la API (api_vendedores_crudo) con los
    datos de gestión (dim_roles_comerciales_historia) y genera un reporte
    de diferencias (nuevos, faltantes, inconsistencias).
    """
    print("=== INICIO DE LA AUDITORÍA DE GESTIÓN DE VENDEDORES ===")
    conn = get_db_connection()
    if not conn: return

    try:
        # --- PASO 1: Leer los datos crudos de la API ---
        query_api = "SELECT cod_cliente_erp AS cod_rol_erp, empresa_erp, nit_documento FROM api_vendedores_crudo;"
        df_api = pd.read_sql_query(query_api, conn)
        print(f"INFO: Se leyeron {len(df_api)} vendedores activos de la tabla de la API.")

        # --- PASO 2: Leer los datos de gestión actuales ---
        # Unimos los roles con las personas para obtener el número de documento
        query_gestion = """
            SELECT
                r.cod_rol_erp,
                r.empresa_erp,
                p.numero_documento
            FROM dim_roles_comerciales_historia AS r
            JOIN maestro_personas AS p ON r.id_persona_fk = p.id_persona
            WHERE r.fecha_fin_validez >= CURRENT_DATE;
        """
        df_gestion = pd.read_sql_query(query_gestion, conn)
        print(f"INFO: Se leyeron {len(df_gestion)} roles activos de la tabla de gestión.")

        # --- PASO 3: Comparar ambos conjuntos de datos ---
        df_merged = pd.merge(
            df_gestion,
            df_api,
            on=['cod_rol_erp', 'empresa_erp'],
            how='outer',
            indicator=True,
            suffixes=('_gestion', '_api')
        )

        # --- PASO 4: Identificar las diferencias ---
        nuevos_en_api = df_merged[df_merged['_merge'] == 'right_only']
        faltantes_en_api = df_merged[df_merged['_merge'] == 'left_only']
        
        ambos = df_merged[df_merged['_merge'] == 'both']
        # Una inconsistencia es cuando el rol existe en ambos lados, pero el documento asignado es diferente
        inconsistencias = ambos[
            ambos['numero_documento'].str.strip() != ambos['nit_documento'].str.strip()
        ].copy()
        
        # --- PASO 5: Generar el reporte ---
        if not (nuevos_en_api.empty and faltantes_en_api.empty and inconsistencias.empty):
            reporte = []
            
            for _, row in nuevos_en_api.iterrows():
                reporte.append({
                    'estado': 'NUEVO EN API',
                    'cod_rol_erp': row['cod_rol_erp'],
                    'empresa_erp': row['empresa_erp'],
                    'documento_en_api': row['nit_documento'],
                    'documento_gestionado': 'No existe'
                })
            
            for _, row in faltantes_en_api.iterrows():
                reporte.append({
                    'estado': 'FALTA EN API (INACTIVO?)',
                    'cod_rol_erp': row['cod_rol_erp'],
                    'empresa_erp': row['empresa_erp'],
                    'documento_en_api': 'No encontrado',
                    'documento_gestionado': row['numero_documento']
                })
                
            for _, row in inconsistencias.iterrows():
                reporte.append({
                    'estado': 'INCONSISTENCIA DE DOCUMENTO',
                    'cod_rol_erp': row['cod_rol_erp'],
                    'empresa_erp': row['empresa_erp'],
                    'documento_en_api': row['nit_documento'],
                    'documento_gestionado': row['numero_documento']
                })

            df_reporte = pd.DataFrame(reporte)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_reporte = os.path.join(config.INFORMES_GENERADOS_DIR, f'reporte_cambios_vendedores_{timestamp}.csv')
            df_reporte.to_csv(ruta_reporte, index=False)
            
            print(f"\n¡ALERTA! Se detectaron {len(df_reporte)} cambios o inconsistencias.")
            print(f"Se ha generado un reporte en: {ruta_reporte}")

        else:
            print("\n¡EXCELENTE! Tus datos de gestión de vendedores están perfectamente sincronizados con la API.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la auditoría de vendedores: {e}")
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    auditar_vendedores()