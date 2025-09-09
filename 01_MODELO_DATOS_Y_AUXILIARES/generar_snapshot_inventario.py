# 01_MODELO_DATOS_Y_AUXILIARES/generar_snapshot_inventario.py

import sys
import os
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from db_utils import get_db_connection, execute_query

def generar_snapshot_inventario():
    """
    Toma una "foto" del estado actual del inventario (desde la tabla Inventario_Actual)
    y la inserta como un registro histórico en la tabla Hechos_Inventario.
    """
    print(f"=== INICIO DEL SNAPSHOT DE INVENTARIO PARA LA FECHA: {date.today()} ===")
    
    conn = get_db_connection()
    if not conn:
        return

    try:
        # La consulta SQL hace todo el trabajo:
        # 1. Selecciona todos los datos de la tabla de inventario actual.
        # 2. Les asigna la fecha de hoy como 'fecha_snapshot'.
        # 3. Inserta esos registros en la tabla histórica.
        # 4. ON CONFLICT previene que se inserte un duplicado si el script
        #    se ejecuta más de una vez en el mismo día.
        query_snapshot = """
            INSERT INTO Hechos_Inventario 
                (fecha_snapshot, id_producto_fk, id_bodega_fk, empresa_erp, cantidad_disponible)
            SELECT 
                CURRENT_DATE,
                id_producto_fk,
                id_bodega_fk,
                empresa_erp,
                cantidad_disponible
            FROM 
                Inventario_Actual
            ON CONFLICT (fecha_snapshot, id_producto_fk, id_bodega_fk, empresa_erp) 
            DO NOTHING;
        """

        print("INFO: Tomando snapshot y guardando en Hechos_Inventario...")
        with conn.cursor() as cursor:
            cursor.execute(query_snapshot)
            conn.commit()
            print(f"¡ÉXITO! Snapshot completado. {cursor.rowcount} nuevos registros históricos de inventario guardados.")

    except Exception as e:
        print(f"ERROR CRÍTICO durante la generación del snapshot de inventario: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("INFO: Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    generar_snapshot_inventario()