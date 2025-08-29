# Proyecto de ETL y Data Warehouse para Gestión Comercial 📊

Este proyecto implementa un proceso completo de **ETL (Extracción, Transformación y Carga)** para centralizar, limpiar y estructurar los datos comerciales de tres empresas distintas (dos distribuidoras y una fábrica). El objetivo final es crear un **Data Warehouse** robusto en PostgreSQL que sirva como una única fuente de verdad para el análisis de negocio, la generación de informes y el cálculo de comisiones.

---
## Arquitectura de la Solución 🏗️

La solución está diseñada siguiendo las mejores prácticas de la ingeniería de datos:

1.  **Extracción:** Scripts de Python se conectan a una API de TNS para extraer datos crudos de productos y clientes.
2.  **Transformación:** Los datos extraídos pasan por una capa de limpieza, estandarización y enriquecimiento. Se aplican reglas de negocio para corregir inconsistencias.
3.  **Carga:** Los datos limpios se cargan en una base de datos PostgreSQL, diseñada con un **Esquema en Estrella**.
4.  **Gestión y Auditoría:** Un conjunto de scripts de apoyo permite la gestión manual de clasificaciones de negocio y genera reportes para mantener la calidad de los datos.

---
## Conceptos Clave de Modelado de Datos 💡

Este proyecto utiliza varios conceptos fundamentales para asegurar que la información sea íntegra y eficiente.

* **Esquema en Estrella (Star Schema):** Separa los datos en **Tablas de Hechos** (métricas, números) y **Tablas de Dimensión** (contexto descriptivo).
* **Dimensiones de Lenta Variación (SCD) Tipo 2:** En lugar de sobrescribir datos que cambian con el tiempo, se crean nuevos registros con un período de validez. Esto nos permite mantener un historial completo (ej. para clasificaciones de clientes o roles de vendedores).
* **Llaves Sustitutas vs. de Negocio:** Usamos IDs numéricos internos (`id_producto`) para la eficiencia de la base de datos (Llave Sustituta) y mantenemos los códigos del mundo real (`codigo_erp`) para el análisis y la lógica de negocio (Llave de Negocio).

---
## Estructura del Repositorio 📂

```
proyectos-gestion-comercial/
│
├── .env                  # (Archivo local) Credenciales y secretos.
├── config.py             # Configuración central del proyecto.
├── db_utils.py           # Funciones reutilizables para la base de datos.
├── requirements.txt      # Dependencias de Python.
├── README.md             # Este archivo.
│
├── sql/
│   └── gestion_comercial_schema.sql # Blueprint completo de la base de datos.
│
├── datos_entrada/        # Archivos CSV para la carga y gestión manual.
│
├── informes_generados/   # Reportes automáticos (cambios, pendientes, etc.).
│
├── 00_ETL_TNS/           # Scripts principales que extraen datos de la API.
│   ├── cargar_productos_api.py
│   └── cargar_clientes_api.py
│
└── 01_MODELO_DATOS_Y_AUXILIARES/ # Scripts de apoyo, auditoría y sincronización.
    ├── poblar_dimensiones_catalogo.py
    ├── auditoria_gestion_productos.py
    ├── sincronizar_gestion_productos.py
    ├── auditoria_gestion_clientes.py
    ├── sincronizar_maestro_clientes.py
    └── sincronizar_clasificacion_clientes.py
```

---
## Cómo Empezar (Guía de Instalación) 🚀

1.  **Clonar el Repositorio:** `git clone https://github.com/EdinsonHernandez92/proyectos_gestion_comercial.git`
2.  **Entorno Virtual:** `python -m venv venv` y actívalo.
3.  **Archivo `.env`:** Crea el archivo `.env` en la raíz y rellénalo con las credenciales de la base de datos y de la API.
4.  **Instalar Dependencias:** `pip install -r requirements.txt`
5.  **Crear Base de Datos:** Crea una base de datos en PostgreSQL llamada `gestion_comercial` y ejecuta el script `sql/gestion_comercial_schema.sql` para crear todas las tablas.

---
## Flujo de Trabajo de los Scripts ETL

El proyecto se divide en procesos automáticos (para datos de la API) y procesos manuales (para tus datos de gestión).

### 1. Proceso Diario (Automático)
Estos scripts deben ejecutarse diariamente para mantener los datos maestros sincronizados.

* **`cargar_productos_api.py`:**
    * **Misión:** Sincroniza la tabla `dim_productos` con la API. Inserta productos nuevos y actualiza los existentes.
    * **Reporte:** Genera un CSV en `informes_generados/` con los productos nuevos o modificados detectados en la API.
* **`cargar_clientes_api.py`:**
    * **Misión:** Sincroniza la tabla `dim_clientes_empresa` con la API.
    * **Reporte:** Genera un CSV en `informes_generados/` con los clientes nuevos o modificados detectados en la API.

### 2. Proceso de Gestión (Manual)
Este es tu flujo de trabajo para clasificar los datos nuevos.

* **Paso A: Auditoría**
    * **`auditoria_gestion_productos.py`:** Encuentra los productos **activos y con ventas recientes** que aún no has clasificado. Genera el archivo `productos_pendientes_por_clasificar.csv`.
    * **`auditoria_gestion_clientes.py`:** Encuentra los clientes **activos y con ventas recientes** que aún no has añadido al maestro. Genera el archivo `clientes_pendientes_por_clasificar.csv`.
* **Paso B: Tu Acción Manual**
    * Usando los reportes de la auditoría, actualizas tus archivos CSV maestros en la carpeta `datos_entrada/`.
* **Paso C: Sincronización**
    * **`sincronizar_gestion_productos.py`:** Lee tu `gestion_productos_aux.csv` y actualiza la tabla en la base de datos.
    * **`sincronizar_maestro_clientes.py`:** Lee tu `maestro_clientes.csv` y actualiza la tabla `maestro_clientes`.
    * **`sincronizar_clasificacion_clientes.py`:** Lee tu `dim_clientes_clasificacion_historia.csv` y actualiza las clasificaciones en la base de datos.