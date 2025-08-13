# comparar_extracciones.py

import pandas as pd
import os

def comparar_archivos(file1='run1.csv', file2='run2.csv'):
    """
    Compara dos archivos CSV para encontrar registros que existen en el segundo
    pero no en el primero, basándose en una llave única.
    """
    print("--- Iniciando Comparación de Extracciones ---")

    # --- PASO 1: Verificar que los archivos existan ---
    if not os.path.exists(file1):
        print(f"ERROR CRÍTICO: No se encontró el archivo '{file1}'.")
        print("Por favor, asegúrate de haber generado este archivo desde el script principal.")
        return
    if not os.path.exists(file2):
        print(f"ERROR CRÍTICO: No se encontró el archivo '{file2}'.")
        print("Por favor, asegúrate de haber generado este archivo desde el script principal.")
        return
        
    print(f"INFO: Archivos '{file1}' y '{file2}' encontrados.")

    try:
        # --- PASO 2: Leer los CSV forzando todos los datos a tipo texto (string) ---
        # Esto evita problemas si pandas interpreta una columna como número en un archivo y texto en otro.
        df1 = pd.read_csv(file1, dtype=str).fillna('')
        df2 = pd.read_csv(file2, dtype=str).fillna('')
        print(f"INFO: Se leyeron {len(df1)} filas de '{file1}' y {len(df2)} filas de '{file2}'.")

        # --- PASO 3: Verificar que las columnas clave existan en ambos archivos ---
        key_cols = ['codigo_erp', 'referencia', 'empresa_erp']
        for col in key_cols:
            if col not in df1.columns:
                print(f"ERROR CRÍTICO: La columna clave '{col}' no se encontró en el archivo '{file1}'.")
                print("Revisa el diccionario 'MAPEO_COLUMNAS_API' en tu script principal.")
                return
            if col not in df2.columns:
                print(f"ERROR CRÍTICO: La columna clave '{col}' no se encontró en el archivo '{file2}'.")
                print("Revisa el diccionario 'MAPEO_COLUMNAS_API' en tu script principal.")
                return

        # --- PASO 4: Realizar la comparación (merge) ---
        # Hacemos un "merge" para encontrar las filas que están en df2 pero no en df1
        df_merged = pd.merge(df1, df2, on=key_cols, how='right', indicator=True, suffixes=('_run1', '_run2'))
        
        # Filtramos para quedarnos solo con los registros que son únicos de la segunda ejecución
        df_nuevos = df_merged[df_merged['_merge'] == 'right_only']

        print("\n--- RESULTADO DE LA COMPARACIÓN ---")
        print(f"Se encontraron {len(df_nuevos)} registros 'nuevos' en la segunda ejecución.")
        
        if not df_nuevos.empty:
            print("\n--- Mostrando los primeros 20 registros nuevos ---")
            # Seleccionamos las columnas relevantes para mostrar, incluyendo las de ambos runs para comparar
            cols_run2 = [col for col in df_nuevos.columns if col.endswith('_run2') or col in key_cols]
            print(df_nuevos[cols_run2].head(20).to_string())

    except Exception as e:
        print(f"\nERROR INESPERADO: Ocurrió un error durante la comparación: {e}")

if __name__ == '__main__':
    comparar_archivos()