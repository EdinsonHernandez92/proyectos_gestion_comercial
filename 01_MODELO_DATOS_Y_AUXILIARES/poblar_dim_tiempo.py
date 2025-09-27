# 01_MODELO_DATOS_Y_AUXILIARES/poblar_dim_tiempo.py

# --- Importación de Librerías ---
import pandas as pd  # Importamos Pandas para el manejo de datos en tablas (DataFrames).
import sys  # Módulo del sistema para interactuar con el intérprete de Python.
import os  # Módulo para interactuar con el sistema operativo, como manejar rutas de archivos.
import locale  # Módulo para manejar configuraciones regionales (idioma, formato de números).
from psycopg2 import extras  # Importamos herramientas adicionales de psycopg2 para cargas masivas.
import holidays  # Importamos la librería para identificar días festivos.

# --- Configuración del Proyecto ---
# Añadimos la ruta raíz del proyecto al path de Python.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config  # Importa nuestras configuraciones (URLs, credenciales).
from db_utils import get_db_connection, execute_query  # Importa nuestras funciones de base de datos.

def poblar_dim_tiempo():
    """
    Genera y carga un rango de fechas en la tabla dim_tiempo, incluyendo
    el cálculo de los días hábiles del mes.
    Asegúrate de haber instalado la librería: pip install holidays
    """
    # Imprime un mensaje de inicio en la consola.
    print("=== INICIO DE LA CARGA DE LA DIMENSIÓN DE TIEMPO ===")
    
    # Obtiene una conexión a la base de datos usando nuestra función de utilidad.
    conn = get_db_connection()
    # Si la conexión falla, la función get_db_connection devuelve None y terminamos el script.
    if not conn:
        return

    try:
        # --- PASO 1: Definir el rango de fechas ---
        # Define la fecha de inicio para nuestra dimensión de tiempo.
        start_date = '2020-01-01'
        # Define la fecha de fin.
        end_date = '2030-12-31'
        # Informa al usuario el rango que se está generando.
        print(f"INFO: Generando fechas desde {start_date} hasta {end_date}...")

        # --- PASO 2: Generar Fechas y Atributos con Pandas ---
        # Crea un rango de fechas con frecuencia diaria ('D').
        date_range = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D'))
        # Crea un DataFrame vacío para almacenar nuestros datos.
        df_tiempo = pd.DataFrame()
        # Asigna el rango de fechas a la columna 'fecha_sk'. .date extrae solo la parte de la fecha.
        df_tiempo['fecha_sk'] = date_range.date
        
        # Crea la lista de festivos para Colombia para los años de nuestro rango.
        co_holidays = holidays.country_holidays('CO', years=range(int(start_date[:4]), int(end_date[:4]) + 1))
        # Convierte la lista a un 'set' para que las búsquedas sean mucho más rápidas.
        holiday_dates = set(co_holidays.keys())

        # --- PASO 3: Calcular todos los atributos de la dimensión ---

        # --- Cálculo de atributos básicos ---
        # Extrae el año de cada fecha.
        df_tiempo['anio'] = date_range.year
        # Extrae el número del mes de cada fecha (1 para Enero, 2 para Febrero, etc.).
        df_tiempo['mes_del_anio'] = date_range.month
        # Crea una columna booleana (True/False) si la fecha está en nuestra lista de festivos.
        df_tiempo['es_festivo'] = df_tiempo['fecha_sk'].isin(holiday_dates)        
        # Es día hábil si es de Lunes a Sábado (código < 6) Y no es festivo.
        df_tiempo['es_dia_habil'] = (date_range.weekday < 6) & (~df_tiempo['es_festivo'])

        # --- Cálculo de días hábiles del mes ---
        # Creamos una columna temporal para identificar cada mes (ej. '2024-01')
        df_tiempo['anio_mes'] = date_range.to_period('M')
        # Creamos una columna que es 1 si el día es hábil y 0 si no lo es
        df_tiempo['es_habil_int'] = df_tiempo['es_dia_habil'].astype(int)
        # Calculamos el día hábil acumulado dentro de cada grupo de mes
        df_tiempo['dia_habil_del_mes'] = df_tiempo.groupby('anio_mes')['es_habil_int'].cumsum()
        # Calculamos el total de días hábiles para cada grupo de mes
        transform_total_habiles = df_tiempo.groupby('anio_mes')['es_habil_int'].transform('sum')
        df_tiempo['total_dias_habiles_mes'] = transform_total_habiles
        # Si un día no es hábil, su 'dia_habil_del_mes' debe ser nulo
        df_tiempo.loc[~df_tiempo['es_dia_habil'], 'dia_habil_del_mes'] = None

        # --- Cálculo de atributos restantes ---
        # Asigna la fecha completa (es igual a la llave primaria 'fecha_sk').
        df_tiempo['fecha_completa'] = df_tiempo['fecha_sk']

        # Intenta configurar el idioma a español de Colombia para los nombres de mes y día.
        try:
            locale.setlocale(locale.LC_TIME, 'es_CO.UTF-8')
        except locale.Error:
            # Si falla (ej. el paquete de idioma no está en el sistema), usa la configuración por defecto.
            locale.setlocale(locale.LC_TIME, '')
        
        # Extrae el nombre completo del mes y pone la primera letra en mayúscula.
        df_tiempo['nombre_mes'] = date_range.strftime('%B').str.capitalize()
        # Extrae el trimestre del año (1, 2, 3 o 4).
        df_tiempo['trimestre_del_anio'] = date_range.quarter
        # Extrae el día del mes (del 1 al 31).
        df_tiempo['dia_del_mes'] = date_range.day
        # Extrae el nombre completo del día de la semana y pone la primera letra en mayúscula.
        df_tiempo['nombre_dia'] = date_range.strftime('%A').str.capitalize()

        # Es fin de semana si el día es Domingo (código 6).
        df_tiempo['es_fin_de_semana'] = date_range.weekday == 6

        # Calcula el bimestre del año.
        df_tiempo['bimestre_del_anio'] = (df_tiempo['mes_del_anio'] - 1) // 2 + 1
        # Usamos strftime('%V') que es un método más directo para obtener la semana ISO 8601
        # y lo convertimos a entero para asegurar el tipo de dato correcto.
        df_tiempo['semana_del_anio'] = date_range.strftime('%V').astype(int)
        
        # Informa al usuario cuántos registros se crearon en memoria.
        print(f"INFO: Se generaron {len(df_tiempo)} registros para la dimensión de tiempo.")
        
        # Línea clave para corregir el error 'NAType'. Convierte los tipos especiales de Pandas a None.
        df_tiempo = df_tiempo.astype(object).where(pd.notnull(df_tiempo), None)

        # --- PASO 4: Cargar los datos en la base de datos ---
        # Define la lista de columnas en el orden correcto de la tabla.
        columnas_db = [
            'fecha_sk', 'fecha_completa', 'anio', 'mes_del_anio', 'nombre_mes',
            'trimestre_del_anio', 'bimestre_del_anio', 'semana_del_anio',
            'dia_del_mes', 'nombre_dia', 'es_fin_de_semana', 'es_dia_habil',
            'es_festivo', 'dia_habil_del_mes', 'total_dias_habiles_mes'
        ]
        
        # Convierte el DataFrame en una lista de tuplas, que es el formato que psycopg2 espera.
        datos_para_insertar = [tuple(row) for row in df_tiempo[columnas_db].itertuples(index=False)]
        
        # Prepara la parte SET de la consulta para actualizar registros si ya existen.
        update_cols = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columnas_db if col != 'fecha_sk'])
        
        # Construye la consulta SQL final de tipo "UPSERT".
        query = f"""
            INSERT INTO dim_tiempo ({", ".join(f'"{c}"' for c in columnas_db)}) VALUES %s
            ON CONFLICT (fecha_sk) DO UPDATE SET {update_cols};
        """
        
        # Abre un "cursor" para ejecutar comandos en la base de datos.
        with conn.cursor() as cursor:
            # Primero vaciamos la tabla para asegurar una recarga completa con los nuevos cálculos
            #cursor.execute("TRUNCATE TABLE dim_tiempo;")
            #print("INFO: Tabla dim_tiempo vaciada para la recarga.")
            # Usa execute_values para una inserción masiva y eficiente de todos los datos.
            extras.execute_values(cursor, query, datos_para_insertar, page_size=1000)
            # Confirma la transacción para que los cambios se guarden permanentemente.
            conn.commit()
            # Informa al usuario del éxito de la operación.
            print(f"¡ÉXITO! La tabla 'dim_tiempo' ha sido actualizada. {cursor.rowcount} filas afectadas.")
    
    # Si ocurre cualquier error en el bloque 'try', este bloque se ejecuta.
    except Exception as e:
        # Informa al usuario del error específico.
        print(f"ERROR CRÍTICO durante la carga de dim_tiempo: {e}")
        # Revierte cualquier cambio parcial que se haya hecho en la transacción.
        conn.rollback()
    # Este bloque se ejecuta siempre, haya o no haya error.
    finally:
        # Si la conexión a la base de datos sigue abierta, la cierra.
        if conn:
            conn.close()
            # Informa al usuario que la conexión ha sido cerrada.
            print("INFO: Conexión a la base de datos cerrada.")

# Este bloque se asegura de que el código solo se ejecute cuando corres el script directamente.
if __name__ == '__main__':
    # Llama a la función principal para iniciar el proceso.
    poblar_dim_tiempo()