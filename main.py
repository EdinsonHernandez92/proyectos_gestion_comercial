# main.py

import sys
import os

# --- Configuración de Rutas ---
# Añadimos las carpetas de los scripts al path de Python para poder importarlos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '00_ETL_TNS')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '01_MODELO_DATOS_Y_AUXILIARES')))

# --- Importación de las Funciones Principales ---
# Cargas de API
from cargar_productos_api import ejecutar_etl_productos
from cargar_clientes_api import ejecutar_etl_clientes
from cargar_vendedores_api_crudo import sincronizar_vendedores_api
from cargar_inventario_api import ejecutar_etl_inventario
from cargar_ventas_api import ejecutar_etl_ventas

# Auditorías
from auditoria_gestion_productos import auditar_productos_sin_gestion
from auditoria_gestion_clientes import auditar_clientes_sin_gestion
from auditoria_gestion_vendedores import auditar_vendedores

# Sincronizaciones Manuales
from sincronizar_maestro_clientes import sincronizar_maestro_clientes
from sincronizar_clasificacion_clientes import sincronizar_clasificacion_clientes
from sincronizar_gestion_productos import sincronizar_gestion_productos
from sincronizar_maestro_personas import sincronizar_maestro_personas
from sincronizar_roles_vendedores import sincronizar_roles

# Tareas Ocasionales
from poblar_dimensiones_catalogo import poblar_catalogos
from generar_snapshot_inventario import generar_snapshot_inventario


def ejecutar_cargas_diarias_api():
    """Ejecuta todos los scripts que extraen datos de la API."""
    print("\n--- INICIANDO FASE 1: CARGAS DESDE LA API ---")
    try:
        ejecutar_etl_productos()
    except Exception as e:
        print(f"ERROR en cargar_productos_api.py: {e}")
    
    try:
        ejecutar_etl_clientes()
    except Exception as e:
        print(f"ERROR en cargar_clientes_api.py: {e}")
        
    try:
        sincronizar_vendedores_api()
    except Exception as e:
        print(f"ERROR en cargar_vendedores_api_crudo.py: {e}")

    try:
        ejecutar_etl_inventario()
    except Exception as e:
        print(f"ERROR en cargar_inventario_api.py: {e}")
    
    try:
        ejecutar_etl_ventas()
    except Exception as e:
        print(f"ERROR en cargar_ventas_api.py: {e}")

    print("\n--- FASE 1 COMPLETADA ---")

def ejecutar_auditorias():
    """Ejecuta todos los scripts de auditoría para generar los reportes de pendientes."""
    print("\n--- INICIANDO FASE 2: AUDITORÍA DE DATOS DE GESTIÓN ---")
    try:
        auditar_productos_sin_gestion()
    except Exception as e:
        print(f"ERROR en auditoria_gestion_productos.py: {e}")
    
    try:
        auditar_clientes_sin_gestion()
    except Exception as e:
        print(f"ERROR en auditoria_gestion_clientes.py: {e}")
        
    try:
        auditar_vendedores()
    except Exception as e:
        print(f"ERROR en auditoria_gestion_vendedores.py: {e}")
    print("\n--- FASE 2 COMPLETADA ---")

def ejecutar_sincronizaciones_manuales():
    """Ejecuta todos los scripts que sincronizan los archivos CSV manuales."""
    print("\n--- INICIANDO FASE 3: SINCRONIZACIÓN DE ARCHIVOS MANUALES ---")
    try:
        sincronizar_gestion_productos()
    except Exception as e:
        print(f"ERROR en sincronizar_gestion_productos.py: {e}")
    
    # Para clientes y vendedores, el orden es importante
    try:
        sincronizar_maestro_clientes()
    except Exception as e:
        print(f"ERROR en sincronizar_maestro_clientes.py: {e}")
    try:
        sincronizar_clasificacion_clientes()
    except Exception as e:
        print(f"ERROR en sincronizar_clasificacion_clientes.py: {e}")
        
    try:
        sincronizar_maestro_personas()
    except Exception as e:
        print(f"ERROR en sincronizar_maestro_personas.py: {e}")
    try:
        sincronizar_roles()
    except Exception as e:
        print(f"ERROR en sincronizar_roles_vendedores.py: {e}")
    print("\n--- FASE 3 COMPLETADA ---")

def ejecutar_tareas_ocasionales():
    """
    Muestra un submenú para las tareas que no son diarias.
    """
    while True:
        print("\n--- MENÚ DE TAREAS OCASIONALES ---")
        print("1. Poblar Catálogos Base (marcas, líneas, bodegas, departamentos, grupos)")
        print("2. Generar Snapshot Histórico de Inventario")
        print("3. Volver al menú principal")
        sub_opcion = input("Elige una opción: ")

        if sub_opcion == '1':
            try:
                poblar_catalogos()
            except Exception as e:
                print(f"ERROR en poblar_dimensiones_catalogo.py: {e}")
        elif sub_opcion == '2':
            try:
                generar_snapshot_inventario()
            except Exception as e:
                print(f"ERROR en generar_snapshot_inventario.py: {e}")
        elif sub_opcion == '3':
            break
        else:
            print("Opción no válida.")

def mostrar_menu():
    """Muestra el menú principal y maneja la selección del usuario."""
    while True:
        print("\n=============================================")
        print("   ORQUESTADOR DE PROCESOS DE GESTIÓN COMERCIAL   ")
        print("=============================================")
        print("1. Proceso Diario (Cargas de API + Auditorías)")
        print("2. Sincronizar Archivos Manuales (Después de editar CSVs)")
        print("3. Tareas de Mantenimiento Ocasional")
        print("4. Salir")
        
        opcion = input("Por favor, elige una opción (1-4): ")
        
        if opcion == '1':
            ejecutar_cargas_diarias_api()
            ejecutar_auditorias()
            print("\nProceso diario completado. Revisa los reportes en 'informes_generados/'.")
        elif opcion == '2':
            ejecutar_sincronizaciones_manuales()
            print("\nSincronización de archivos manuales completada.")
        elif opcion == '3':
            ejecutar_tareas_ocasionales()
        elif opcion == '4':
            print("Saliendo del orquestador.")
            break
        else:
            print("Opción no válida. Por favor, intenta de nuevo.")

if __name__ == '__main__':
    mostrar_menu()