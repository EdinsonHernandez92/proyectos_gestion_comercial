# Proyecto de ETL y Data Warehouse para Gestión Comercial 📊

Este proyecto implementa un proceso completo de **ETL (Extracción, Transformación y Carga)** para centralizar y estructurar los datos comerciales de tres empresas distintas. El objetivo es crear un **Data Warehouse** robusto en PostgreSQL que sirva como una única fuente de verdad para el análisis de negocio, la generación de informes y el cálculo de comisiones.

---
## Arquitectura y Metodologías Clave 🧠

La solución está diseñada siguiendo las mejores prácticas de la ingeniería de datos:

1.  **Extracción:** Scripts de Python se conectan a una API de TNS para extraer datos crudos de productos, clientes y vendedores.
2.  **Transformación:** Los datos extraídos pasan por una capa de limpieza, estandarización y enriquecimiento. Se aplican reglas de negocio para corregir inconsistencias.
3.  **Carga:** Los datos limpios se cargan en una base de datos PostgreSQL, diseñada con un **Esquema en Estrella**.
4.  **Gestión y Auditoría:** Un conjunto de scripts de apoyo permite la gestión manual de clasificaciones de negocio y genera reportes para mantener la calidad de los datos.

###Metodologías Clave de Modelado de Datos 💡

La solución se basa en principios sólidos de ingeniería de datos para garantizar la integridad, eficiencia y escalabilidad del sistema.

### Esquema en Estrella (Star Schema)
Es el pilar de nuestro diseño. Consiste en separar los datos en dos tipos de tablas:

* **Tablas de Hechos (Fact Tables):** Almacenan las mediciones numéricas de los procesos de negocio. Son el centro de nuestro análisis y suelen ser las tablas más grandes.
    * **`hechos_ventas`:** Es la tabla principal del modelo. Cada fila representa una línea de detalle de una factura (un producto vendido a un cliente en un momento dado). Contiene métricas como `cantidad`, `valor_total`, `costo_total`, etc., y se conecta con todas las dimensiones (productos, clientes, vendedores, tiempo, bodegas).
    * **`hechos_inventario`:** Guarda "fotos" periódicas (snapshots) del inventario, idealmente a fin de mes. Su propósito es permitir el análisis de la evolución y tendencias de las existencias a lo largo del tiempo.
    * **`inventario_actual`:** Es una tabla de hechos especial que no guarda historial, sino que refleja el estado *actual* del inventario. Se actualiza cada día para consultas operativas rápidas sobre las existencias disponibles.

* **Tablas de Dimensión (Dimension Tables):** Contienen el contexto descriptivo ("quién, qué, cuándo, dónde") para los hechos. Son las tablas que usamos para filtrar y agrupar los datos en los reportes. Ejemplos: `dim_productos`, `maestro_clientes`, `dim_tiempo`, `dim_bodegas`.

### Dimensiones de Lenta Variación (SCD)
Los atributos de negocio cambian con el tiempo. Para manejar estos cambios sin perder el historial, implementamos la metodología **SCD Tipo 2**. En lugar de sobrescribir un registro, "cerramos" el antiguo con una `fecha_fin_validez` y creamos uno nuevo con una nueva `fecha_inicio_validez`. Esto nos permite reconstruir la historia con total precisión, como en el caso de la tabla `dim_roles_comerciales_historia`.

### Dimensiones Conformes
Son dimensiones que se comparten entre múltiples tablas de hechos. En nuestro caso, `Dim_Bodegas` es una dimensión conforme, ya que se utiliza tanto en `Hechos_Inventario` como en `Hechos_Ventas`. Esto asegura consistencia y permite realizar análisis cruzados entre diferentes procesos de negocio.

### Procesos Idempotentes
Nuestros scripts de carga y sincronización están diseñados para ser **idempotentes**. Esto significa que se pueden ejecutar múltiples veces con los mismos datos de entrada y el resultado final en la base de datos será el mismo, sin generar duplicados ni errores. Esto se logra mediante el uso de comandos `INSERT ... ON CONFLICT DO UPDATE` (UPSERT) o estrategias de `TRUNCATE` y recarga.

Este proyecto utiliza varios conceptos fundamentales para asegurar que la información sea íntegra y eficiente.

* **Llaves Sustitutas vs. de Negocio:** Usamos IDs numéricos internos (`id_producto`) para la eficiencia de la base de datos (Llave Sustituta) y mantenemos los códigos del mundo real (`codigo_erp`) para el análisis y la lógica de negocio (Llave de Negocio).

---
## Estructura del Repositorio 📂

```
proyectos-gestion-comercial/
│
├── .env                  # (Local) Archivo para guardar credenciales de forma segura.
├── config.py             # Módulo de configuración central (rutas, URLs, credenciales).
├── db_utils.py           # Funciones de utilidad para la conexión a la base de datos.
├── requirements.txt      # Dependencias de Python para el proyecto.
├── README.md
│
├── sql/
│   └── gestion_comercial_schema.sql # Script SQL para crear toda la estructura de la base de datos.
│
├── datos_entrada/        # Archivos CSV para la carga y gestión manual.
│
├── informes_generados/   # Carpeta donde los scripts de auditoría guardan los reportes.
│
├── 00_ETL_TNS/           # Scripts que se conectan a la API para la carga diaria de datos crudos.
│   ├── cargar_productos_api.py                 # Sincroniza la tabla `dim_productos`.
│   ├── cargar_clientes_api.py                  # Sincroniza la tabla `dim_clientes_empresa`.
│   ├── cargar_vendedores_api_crudo.py          # Guarda un snapshot diario de los vendedores de la API.
│   ├── cargar_inventario_api.py                # Sincroniza la tabla `inventario_actual`.
│   └── cargar_ventas_api.py                    # Sincroniza y actualiza la tabla de hechos_ventas.
│
└── 01_MODELO_DATOS_Y_AUXILIARES/               # Scripts de apoyo, auditoría y sincronización.
    ├── poblar_dimensiones_catalogo.py          # Para la carga inicial de catálogos (líneas, marcas, etc.).
    │
    ├── poblar_dim_tiempo.py                    # Script que pobla la tabla de dimensión de tiempo.
    │
    ├── auditoria_gestion_productos.py          # Genera un reporte de productos activos sin clasificar.
    ├── sincronizar_gestion_productos.py        # Sincroniza el CSV de gestión de productos con la BD.
    │
    ├── auditoria_gestion_clientes.py           # Genera un reporte de clientes activos sin gestionar.
    ├── sincronizar_maestro_clientes.py         # Sincroniza el CSV maestro de clientes con la BD.
    ├── sincronizar_clasificacion_clientes.py   # Sincroniza las clasificaciones históricas de clientes.
    │
    ├── auditoria_gestion_vendedores.py         # Genera un reporte de vendedores activos sin gestionar.
    ├── sincronizar_maestro_personas.py         # Sincroniza el CSV maestro de personas con la BD.
    ├── sincronizar_roles_vendedores.py         # Sincroniza el CSV roles comerciales histórico con la BD.
    │
    └── generar_snapshot_inventario.py          # Consume la información del inventario actual para agregar al histórico de inventarios.
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
Estos scripts deben ejecutarse diariamente para mantener los datos maestros sincronizados con la API.

* **`cargar_productos_api.py`:**
    * **Misión:** Se conecta a la API, extrae la lista completa de productos para las tres empresas y la carga en la tabla `dim_productos` usando una lógica de **UPSERT** (inserta si es nuevo, actualiza si existe).
    * **Reporte:** Antes de cargar, compara los datos de la API con los existentes en la base de datos y genera un reporte en `informes_generados/` con los productos nuevos o modificados detectados en la API.
* **`cargar_clientes_api.py`:**
    * **Misión:** Sincroniza la tabla `dim_clientes_empresa` con la API.
    * **Reporte:** Genera un CSV en `informes_generados/` con los clientes nuevos o modificados detectados en la API.
* **`cargar_vendedores_api_crudo.py`**
    * **Acción:** Extrae de la API solo los terceros que son vendedores activos (código empieza con 'V' y no están inactivos) y los guarda en la tabla `api_vendedores_crudo`. Esta tabla se vacía y se recarga cada día para tener un "espejo" de la realidad de la API.
* **`cargar_inventario_api.py`:** Actualiza la tabla `Inventario_Actual` con las existencias del día.
* **`cargar_ventas_api.py`:** Carga las transacciones de ventas del día en la tabla `hechos_ventas`.

### 2. Proceso de Gestión (Manual) - Clasificación y Calidad
Este es el flujo de trabajo para clasificar y mantener la calidad de los datos maestros.

#### Flujo para Productos
1.  **Auditoría:** Ejecutas `auditoria_gestion_productos.py`. El script busca productos con ventas o inventario reciente que aún no están en tu tabla `gestion_productos_aux` y te genera el CSV `productos_pendientes_por_clasificar.csv`.
2.  **Acción Manual:** Editas tu archivo maestro `gestion_productos_aux.csv`, añadiendo los nuevos productos y rellenando sus clasificaciones.
3.  **Sincronización:** Ejecutas `sincronizar_gestion_productos.py`. El script lee tu CSV actualizado, busca los IDs correspondientes en `dim_productos` y sincroniza (UPSERT) la tabla `gestion_productos_aux`.

#### Flujo para Clientes
1.  **Auditoría:** Ejecutas `auditoria_gestion_clientes.py`. El script busca clientes activos en `dim_clientes_empresa` que aún no tienen un `id_maestro_cliente_fk` asignado y te genera el CSV `clientes_pendientes_por_clasificar.csv`.
2.  **Acción Manual:** Editas tus dos archivos maestros:
    * `maestro_clientes.csv`: Añades los nuevos clientes, asignándoles un `cod_cliente_maestro` único.
    * `dim_clientes_clasificacion_historia.csv`: Añades las filas de clasificación para estos nuevos clientes.
3.  **Sincronización:** Ejecutas en orden:
    * `sincronizar_maestro_clientes.py`: Para actualizar la lista de clientes maestros.
    * `sincronizar_clasificacion_clientes.py`: Para actualizar sus clasificaciones.

#### Flujo para Vendedores
1.  **Auditoría:** (Pendiente de creación) `auditoria_gestion_vendedores.py` comparará `api_vendedores_crudo` con tus tablas de gestión para reportar inconsistencias.
2.  **Acción Manual:** Editas tus archivos maestros:
    * `maestro_personas.csv`: Para añadir nuevos empleados (vendedores, supervisores).
    * `dim_roles_comerciales_historia.csv`: Para asignar roles, supervisores y periodos de validez.
3.  **Sincronización:** Ejecutas en orden:
    * `sincronizar_maestro_personas.py`: Para actualizar la lista de personal.
    * `sincronizar_roles_vendedores.py`: Para actualizar el historial de roles.

#### Flujo para Inventario

Este flujo mantiene actualizadas las tablas de existencias.

1.  **`cargar_inventario_api.py` (Diario/Programado):**
    * **Misión:** Se conecta al endpoint de la API que contiene los productos, "aplana" la información anidada de las bodegas y aplica los filtros de negocio (bodegas permitidas, lista de precios).
    * **Acción:** Actualiza la tabla `Inventario_Actual` con las existencias más recientes para cada producto en cada bodega, usando una lógica de **UPSERT**.

2.  **`generar_snapshot_inventario.py` (Periódico, ej. mensual):**
    * **Misión:** Crea un registro histórico del inventario.
    * **Acción:** Toma una "foto" de todo el contenido de la tabla `Inventario_Actual` y la inserta en la tabla `Hechos_Inventario` con la fecha del día en que se ejecuta. Esto permite el análisis de tendencias de inventario a lo largo del tiempo.