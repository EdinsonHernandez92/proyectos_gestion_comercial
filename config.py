# config.py
# Archivo central de configuración del proyecto.

import os
from dotenv import load_dotenv

# --- Carga de Variables de Entorno ---
# Busca un archivo .env en la raíz del proyecto y carga sus variables.
# Es fundamental para mantener las contraseñas y tokens fuera del código.
load_dotenv()
print("INFO: Archivo .env cargado.")

# --- Configuración de la Base de Datos PostgreSQL ---
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "gestion_comercial"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# --- Configuración de la API de TNS para cada Empresa ---
API_CONFIG_TNS = [
    {
        "nombre_corto": "CAMDUN",
        "empresa_tns": os.getenv("TNS_API_EMPRESA_CAMDUN"),
        "usuario_tns": os.getenv("TNS_API_USER_CAMDUN"),
        "password_tns": os.getenv("TNS_API_PASS_CAMDUN"),
        "tnsapitoken": os.getenv("TNS_API_TOKEN_CAMDUN"),
        "cod_sucursal_tns": "00"
    },
    {
        "nombre_corto": "GMD",
        "empresa_tns": os.getenv("TNS_API_EMPRESA_GLOBAL"),
        "usuario_tns": os.getenv("TNS_API_USER_GLOBAL"),
        "password_tns": os.getenv("TNS_API_PASS_GLOBAL"),
        "tnsapitoken": os.getenv("TNS_API_TOKEN_GLOBAL"),
        "cod_sucursal_tns": "00"
    },
    {
        "nombre_corto": "PY",
        "empresa_tns": os.getenv("TNS_API_EMPRESA_YERMAN"),
        "usuario_tns": os.getenv("TNS_API_USER_YERMAN"),
        "password_tns": os.getenv("TNS_API_PASS_YERMAN"),
        "tnsapitoken": os.getenv("TNS_API_TOKEN_YERMAN"),
        "cod_sucursal_tns": "00"
    }
]

# --- URLs de la API TNS ---
API_BASE_URL = os.getenv("TNS_API_BASE_URL", "https://api.tns.co/api")
API_URLS = {
    "productos": f"{API_BASE_URL}/Material/Listar",
    "terceros": f"{API_BASE_URL}/Tercero/Listar",
    "ventas": f"{API_BASE_URL}/Ventas/ObtenerVentasDetallada"
    # Añadiremos más URLs aquí si son necesarias
}

# --- Rutas de Directorios del Proyecto ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATOS_ENTRADA_DIR = os.path.join(BASE_DIR, "datos_entrada")
INFORMES_GENERADOS_DIR = os.path.join(BASE_DIR, "informes_generados")
SQL_DIR = os.path.join(BASE_DIR, "sql")

# --- Creación de Directorios (Buena práctica) ---
try:
    os.makedirs(DATOS_ENTRADA_DIR, exist_ok=True)
    os.makedirs(INFORMES_GENERADOS_DIR, exist_ok=True)
    print("INFO: Directorios del proyecto verificados.")
except OSError as e:
    print(f"ERROR: No se pudieron crear los directorios: {e}")