# proyectos_gestion_comercial
Suite de scripts de Python y modelos de datos para la inteligencia de negocio y automatización del área comercial.

Modelo de Datos: gestion_comercial

Este documento detalla la arquitectura de las tablas de dimensiones para la base de datos centralizada. El diseño sigue un modelo de Esquema en Estrella, separando las Dimensiones (que describen las entidades de negocio) de las futuras Tablas de Hechos (que registran las transacciones).

Sección 1: Dimensiones de Producto

El diseño separa los datos en tres tipos de tablas:
Catálogos (Dim_...): Tablas pequeñas que contienen listas únicas de atributos como líneas, marcas, etc.
Maestra de API (Dim_Productos): Contiene los datos "crudos" de los productos tal como existen en el sistema origen (API de TNS) para cada empresa.
Gestión y Reglas de Negocio (Gestion_... y Acuerdos_...): Tablas que almacenan las clasificaciones, reglas y atributos que tú gestionas manualmente para enriquecer los datos crudos.

1.1. Tablas de Catálogo

Propósito: Almacenar listas únicas de atributos para evitar redundancia y asegurar la consistencia.

SQL


-- Catálogo único de Líneas/Proveedores.
CREATE TABLE Dim_Lineas (
    id_linea SERIAL PRIMARY KEY,
    cod_linea_erp VARCHAR(50) UNIQUE NOT NULL,
    desc_linea VARCHAR(255) NOT NULL
);

-- Catálogo único de Marcas de productos.
CREATE TABLE Dim_Marcas (
    id_marca SERIAL PRIMARY KEY,
    cod_marca VARCHAR(50) UNIQUE NOT NULL, -- Código de marca creado para unificar.
    nombre_marca VARCHAR(100) NOT NULL UNIQUE
);

-- Catálogo único de Departamentos de productos.
CREATE TABLE Dim_Dpto_sku (
    id_dpto_sku SERIAL PRIMARY KEY,
    cod_dpto_sku VARCHAR(50) UNIQUE NOT NULL,
    desc_dpto_sku VARCHAR(255) NOT NULL
);

-- Catálogo de Grupos de Artículos según el ERP.
CREATE TABLE Dim_Grupos (
    id_grupo SERIAL PRIMARY KEY,
    cod_grupo_articulo VARCHAR(50) UNIQUE,
    nombre_grupo_articulo VARCHAR(100)
);




1.2. Tabla Maestra de Productos (API)

Propósito: Servir como la "fuente de verdad" de los productos tal como existen en el sistema origen para cada una de tus empresas.

SQL


-- Tabla maestra de productos tal como existen en el ERP para cada empresa.
CREATE TABLE Dim_Productos (
    id_producto SERIAL PRIMARY KEY,
    codigo_erp VARCHAR(30) NOT NULL,
    referencia VARCHAR(30) NOT NULL,
    empresa_erp VARCHAR(50) NOT NULL, -- Clave para diferenciar productos entre CAMDUN, GLOBAL, YERMAN.
    descripcion_erp VARCHAR(255),
    cod_grupo_erp VARCHAR(50),
    cod_linea_erp VARCHAR(50),
    cod_dpto_sku_erp VARCHAR(50),
    peso_bruto_erp NUMERIC(10, 4),
    factor_erp INT,
    porcentaje_iva NUMERIC,
    costo_promedio_erp MONEY,
    costo_ult_erp MONEY,
    CONSTRAINT uq_producto_empresa UNIQUE (codigo_erp, referencia, empresa_erp)
);




1.3. Tablas de Gestión y Reglas de Negocio

Propósito: Almacenar las clasificaciones, reglas de convenios y atributos de negocio que tú gestionas. Este sistema es flexible y permite que las reglas cambien con el tiempo.

SQL


-- Define las versiones de los acuerdos comerciales y su periodo de vigencia.
CREATE TABLE Acuerdos_Comerciales (
    id_acuerdo SERIAL PRIMARY KEY,
    nombre_acuerdo VARCHAR(255) NOT NULL,       -- Ej: "Convenio Tecnoquímicas T3 2025"
    id_linea_fk INT REFERENCES Dim_Lineas(id_linea),
    fecha_inicio_validez DATE NOT NULL,
    fecha_fin_validez DATE NOT NULL,
    descripcion TEXT
);

-- Define las categorías que componen una versión de un acuerdo (ej: "NORAVER GRIPA", "SR Tiendas Colgate").
CREATE TABLE Acuerdo_Categorias (
    id_acuerdo_categoria SERIAL PRIMARY KEY,
    id_acuerdo_fk INT NOT NULL REFERENCES Acuerdos_Comerciales(id_acuerdo) ON DELETE CASCADE,
    nombre_categoria_acuerdo VARCHAR(255) NOT NULL
);

-- Tabla de enlace que especifica el surtido de productos para cada categoría de un acuerdo.
CREATE TABLE Acuerdo_Surtido_Productos (
    id_acuerdo_categoria_fk INT NOT NULL REFERENCES Acuerdo_Categorias(id_acuerdo_categoria) ON DELETE CASCADE,
    id_producto_fk INT NOT NULL REFERENCES Dim_Productos(id_producto) ON DELETE CASCADE,
    PRIMARY KEY (id_acuerdo_categoria_fk, id_producto_fk)
);

-- Contiene las clasificaciones y atributos de negocio gestionados manualmente. Enriquece la data de Dim_Productos.
CREATE TABLE Gestion_Productos_Aux (
    id_gestion_producto SERIAL PRIMARY KEY,
    id_producto_fk INT NOT NULL UNIQUE REFERENCES Dim_Productos(id_producto) ON DELETE CASCADE,
    categoria_gestion VARCHAR(100),
    subcategoria_1_gestion VARCHAR(100),
    subcategoria_2_gestion VARCHAR(100),
    descripcion_guia VARCHAR(255),
    clasificacion_py VARCHAR(100),
    equivalencia_py VARCHAR(50),
    peso_neto NUMERIC(10, 4),
    grupo_tq VARCHAR(100),
    activo_compra BOOLEAN DEFAULT TRUE,
    id_marca_fk INT REFERENCES Dim_Marcas(id_marca)
);



Sección 2: Dimensiones de Cliente y Geografía

Este diseño utiliza un modelo de Cliente Maestro para resolver el desafío de tener un mismo cliente (punto de venta) con diferentes códigos en tus empresas, permitiendo una clasificación unificada.

2.1. Dimensión Geográfica

Propósito: Centralizar todas las ubicaciones en un catálogo único para evitar redundancia y facilitar el análisis geográfico.

SQL


-- Catálogo único de ubicaciones geográficas (barrio, ciudad, departamento).
CREATE TABLE Dim_Geografia (
    id_geografia SERIAL PRIMARY KEY,
    barrio VARCHAR(150),
    ciudad VARCHAR(100) NOT NULL,
    departamento VARCHAR(100),
    CONSTRAINT uq_geografia UNIQUE (barrio, ciudad, departamento)
);




2.2. Modelo de Cliente Maestro

Propósito: Crear una única "ficha" por cada punto de venta real. Esta ficha contiene la clasificación de negocio unificada que se aplicará a ese cliente, sin importar en cuántas de tus empresas esté registrado.

SQL


-- Catálogo maestro con una entrada única por punto de venta/sucursal de cliente.
CREATE TABLE Maestro_Clientes (
    id_maestro_cliente SERIAL PRIMARY KEY,
    cod_cliente_maestro VARCHAR(50) UNIQUE NOT NULL, -- El código MAESTRO que unifica un punto de venta.
    nombre_unificado VARCHAR(255) NOT NULL,    -- El nombre comercial principal que tú defines.
    canal VARCHAR(100),
    subcanal VARCHAR(100),
    sucursal VARCHAR(55),
    dia_visita VARCHAR(50),
    id_geografia_fk INT REFERENCES Dim_Geografia(id_geografia)
);

-- Registros de clientes por empresa, tal como vienen del ERP. Se enlazan a un único cliente maestro.
CREATE TABLE Dim_Clientes_Empresa (
    id_cliente_empresa SERIAL PRIMARY KEY,
    id_maestro_cliente_fk INT NOT NULL REFERENCES Maestro_Clientes(id_maestro_cliente),
    cod_cliente_erp VARCHAR(50) NOT NULL,
    empresa_erp VARCHAR(50) NOT NULL,
    nit VARCHAR(50),
    nombre_erp VARCHAR(255),
    clasificacion_erp VARCHAR(55),
    direccion_erp VARCHAR(255),
    telefono_erp VARCHAR(55),
    ciudad_erp VARCHAR(55),
    inactivo_erp VARCHAR(10),
    CONSTRAINT uq_cliente_por_empresa UNIQUE (cod_cliente_erp, empresa_erp)
);