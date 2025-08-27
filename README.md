# Proyecto de ETL y Data Warehouse para Gestión Comercial 📊

Este proyecto implementa un proceso completo de **ETL (Extracción, Transformación y Carga)** para centralizar, limpiar y estructurar los datos comerciales de tres empresas distintas (dos distribuidoras y una fábrica). El objetivo final es crear un **Data Warehouse** robusto en PostgreSQL que sirva como una única fuente de verdad para el análisis de negocio y la generación de informes en herramientas como Power BI.

---
## Arquitectura de la Solución 🏗️

La solución está diseñada siguiendo las mejores prácticas de la ingeniería de datos:

1.  **Extracción:** Scripts de Python se conectan a una API de TNS para extraer datos crudos de productos, clientes, vendedores, ventas e inventario.
2.  **Transformación:** Los datos extraídos pasan por una capa de limpieza, estandarización y enriquecimiento. Se aplican reglas de negocio para corregir inconsistencias y se enlazan los datos con catálogos de negocio gestionados manualmente.
3.  **Carga:** Los datos limpios y estructurados se cargan en una base de datos PostgreSQL, diseñada con un **Esquema en Estrella**.

---
## Conceptos Clave de Modelado de Datos 💡

Este proyecto utiliza varios conceptos fundamentales de modelado de datos para asegurar que la información sea íntegra, eficiente y fácil de consultar.

### Esquema en Estrella (Star Schema)
Es el pilar de nuestro diseño. Consiste en separar los datos en dos tipos de tablas:
* **Tablas de Hechos (Fact Tables):** Contienen las métricas y números de los eventos de negocio (ej. `hechos_ventas`, `inventario_actual`). Son tablas grandes, pero numéricas y optimizadas.
* **Tablas de Dimensión (Dimension Tables):** Contienen el contexto descriptivo de los hechos (ej. `dim_productos`, `maestro_clientes`). Responden a las preguntas "quién", "qué", "cuándo" y "dónde".



### Dimensiones de Lenta Variación (Slowly Changing Dimensions - SCD)
Los atributos de negocio no siempre son estáticos. Un cliente puede cambiar de clasificación o un vendedor puede cambiar de supervisor. Las SCD son técnicas para manejar estos cambios a lo largo del tiempo. En este proyecto, utilizamos principalmente el **Tipo 2**.

* **SCD Tipo 1 - Sobrescribir:** Simplemente se actualiza el registro con el nuevo valor, perdiendo el historial. *Ej: Corregir un error ortográfico en el nombre de un producto.*
* **SCD Tipo 2 - Añadir Nueva Fila:** Es la técnica que implementamos. En lugar de sobrescribir, se "cierra" el registro antiguo (actualizando su `fecha_fin_validez`) y se crea un **nuevo registro** con el nuevo atributo y su propio período de validez. Esto nos permite reconstruir la historia con total precisión. *Ej: `dim_roles_comerciales_historia` y `dim_clientes_clasificacion_historia`.*

### Llaves Sustitutas vs. Llaves de Negocio
Distinguimos entre dos tipos de identificadores:
* **Llave de Negocio (Business Key):** Es el código que se usa en el mundo real y que tú conoces (ej. `codigo_erp`, `referencia`). Puede ser inconsistente entre sistemas.
* **Llave Sustituta (Surrogate Key):** Es un número entero (`SERIAL`) que la base de datos genera automáticamente (`id_producto`, `id_cliente`). No tiene significado de negocio, pero es la forma más eficiente para que la base de datos realice las relaciones (`JOINs`).

Nuestro proceso ETL actúa como el "traductor" que convierte las llaves de negocio del mundo real en las llaves sustitutas que usa nuestro Data Warehouse.

---
## Estructura del Repositorio 📂

```
proyectos-gestion-comercial/
│
├── .env                  # (Archivo local, NO en GitHub) Credenciales y secretos.
├── config.py             # Configuración central del proyecto.
├── db_utils.py           # Funciones reutilizables para la base de datos.
├── requirements.txt      # Lista de dependencias de Python.
├── README.md             # Este archivo.
│
├── sql/                  # Contiene los scripts para crear el esquema de la BD.
│   └── gestion_comercial_schema.sql
│
├── datos_entrada/        # Archivos CSV manuales (catálogos, mapeos, gestión).
│
├── 00_ETL_TNS/           # Scripts que se conectan a la API de TNS.
│   └── cargar_productos_api.py
│
└── 01_MODELO_DATOS_Y_AUXILIARES/ # Scripts de apoyo, auditoría y sincronización.
    ├── poblar_dimensiones_catalogo.py
    └── sincronizar_gestion_productos.py
```

---
## Cómo Empezar (Guía de Instalación) 🚀

Sigue estos pasos para configurar el proyecto en un nuevo entorno.

### 1. Clonar el Repositorio
```bash
git clone [https://github.com/EdinsonHernandez92/proyectos_gestion_comercial.git](https://github.com/EdinsonHernandez92/proyectos_gestion_comercial.git)
cd proyectos_gestion_comercial
```

### 2. Configurar el Entorno Virtual (Recomendado)
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Crear el Archivo de Entorno `.env`
Crea un archivo llamado `.env` en la raíz del proyecto y copia la siguiente plantilla, rellenando con tus credenciales reales. **Este archivo nunca debe subirse a GitHub.**

```env
# --- Base de Datos ---
DB_NAME="gestion_comercial"
DB_USER="postgres"
DB_PASSWORD="TU_PASSWORD_DE_POSTGRESQL"
DB_HOST="localhost"
DB_PORT="5432"

# --- API TNS ---
TNS_API_BASE_URL="[https://api.tns.co/api](https://api.tns.co/api)"

# Credenciales para CAMDUN
TNS_API_EMPRESA_CAMDUN="CODIGO_EMPRESA_CAMDUN"
# ... (y el resto de tus credenciales de API)
```

### 4. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 5. Crear la Base de Datos y las Tablas
1.  Asegúrate de tener un servidor PostgreSQL corriendo.
2.  Crea una nueva base de datos llamada `gestion_comercial`.
3.  Abre el archivo `sql/gestion_comercial_schema.sql`, copia todo su contenido y ejecútalo en pgAdmin (o tu cliente de SQL preferido) sobre la base de datos recién creada.

### 6. Ejecutar los Scripts de ETL
Ejecuta los scripts en el siguiente orden para realizar la carga inicial de datos:
1.  **Poblar catálogos:** `python 01_MODELO_DATOS_Y_AUXILIARES/poblar_dimensiones_catalogo.py`
2.  **Cargar productos desde API:** `python 00_ETL_TNS/cargar_productos_api.py`
3.  **Sincronizar gestión de productos:** `python 01_MODELO_DATOS_Y_AUXILIARES/sincronizar_gestion_productos.py`