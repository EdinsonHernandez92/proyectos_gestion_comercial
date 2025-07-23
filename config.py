# config.py

# Este archivo contiene la configuración central para el proyecto.

# Configuración para la conexión a la base de datos PostgreSQL
DB_CONFIG = {
    "dbname": "gestion_comercial",  # <-- Reemplaza con el nombre de tu base de datos
    "user": "postgres",             # <-- Reemplaza con tu usuario de PostgreSQL
    "password": "Aprendizaje", # <-- Reemplaza con tu contraseña
    "host": "localhost",            # O la IP si no es local
    "port": "5432"                  # El puerto estándar de PostgreSQL
}

# Aquí también podríamos añadir otras configuraciones en el futuro,
# como credenciales de API, rutas de archivos, etc.