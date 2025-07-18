-- =================================================================
-- ESQUEMA PARA: gestion_comercial
-- SECCIÓN 1: DIMENSIONES DE PRODUCTO (Versión 3 - Corregida)
-- =================================================================

-- Tablas de catálogos (Dim_Lineas, Dim_Marcas, Dim_Dpto_sku, Dim_Grupos)
-- (Estas 4 tablas se mantienen exactamente igual que en la versión anterior)

DROP TABLE IF EXISTS Dim_Lineas CASCADE;
CREATE TABLE Dim_Lineas (
    id_linea SERIAL PRIMARY KEY,
    cod_linea_erp VARCHAR(50) UNIQUE NOT NULL,
    desc_linea VARCHAR(255) NOT NULL
);
COMMENT ON TABLE Dim_Lineas IS 'Catálogo único de Líneas/Proveedores.';

DROP TABLE IF EXISTS Dim_Marcas CASCADE;
CREATE TABLE Dim_Marcas (
    id_marca SERIAL PRIMARY KEY,
    cod_marca VARCHAR(50) UNIQUE NOT NULL,
    nombre_marca VARCHAR(100) NOT NULL UNIQUE
);
COMMENT ON TABLE Dim_Marcas IS 'Catálogo único de Marcas de productos.';

DROP TABLE IF EXISTS Dim_Dpto_sku CASCADE;
CREATE TABLE Dim_Dpto_sku (
    id_dpto_sku SERIAL PRIMARY KEY,
    cod_dpto_sku VARCHAR(50) UNIQUE NOT NULL,
    desc_dpto_sku VARCHAR(255) NOT NULL
);
COMMENT ON TABLE Dim_Dpto_sku IS 'Catálogo único de Departamentos de productos.';

DROP TABLE IF EXISTS Dim_Grupos CASCADE;
CREATE TABLE Dim_Grupos (
    id_grupo SERIAL PRIMARY KEY,
    cod_grupo_articulo VARCHAR(50) UNIQUE,
    nombre_grupo_articulo VARCHAR(100)
);
COMMENT ON TABLE Dim_Grupos IS 'Catálogo de Grupos de Artículos según el ERP.';


-- Tabla Dim_Productos (Datos "crudos" de la API)
-- (Esta tabla se mantiene exactamente igual)
DROP TABLE IF EXISTS Dim_Productos CASCADE;
CREATE TABLE Dim_Productos (
    id_producto SERIAL PRIMARY KEY,
    codigo_erp VARCHAR(30) NOT NULL,
    referencia VARCHAR(30) NOT NULL,
    empresa_erp VARCHAR(50) NOT NULL,
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
COMMENT ON TABLE Dim_Productos IS 'Tabla maestra de productos tal como existen en el ERP para cada empresa.';

-- Sistema para gestionar convenios y acuerdos comerciales
-- (Este sistema se mantiene exactamente igual)
DROP TABLE IF EXISTS Acuerdos_Comerciales CASCADE;
CREATE TABLE Acuerdos_Comerciales (
    id_acuerdo SERIAL PRIMARY KEY,
    nombre_acuerdo VARCHAR(255) NOT NULL,
    id_linea_fk INT REFERENCES Dim_Lineas(id_linea),
    fecha_inicio_validez DATE NOT NULL,
    fecha_fin_validez DATE NOT NULL,
    descripcion TEXT
);
COMMENT ON TABLE Acuerdos_Comerciales IS 'Define las versiones de los acuerdos comerciales y su periodo de vigencia.';

DROP TABLE IF EXISTS Acuerdo_Categorias CASCADE;
CREATE TABLE Acuerdo_Categorias (
    id_acuerdo_categoria SERIAL PRIMARY KEY,
    id_acuerdo_fk INT NOT NULL REFERENCES Acuerdos_Comerciales(id_acuerdo) ON DELETE CASCADE,
    nombre_categoria_acuerdo VARCHAR(255) NOT NULL
);
COMMENT ON TABLE Acuerdo_Categorias IS 'Define las categorías que componen una versión de un acuerdo (ej: "NORAVER GRIPA", "SR Tiendas Colgate").';

DROP TABLE IF EXISTS Acuerdo_Surtido_Productos CASCADE;
CREATE TABLE Acuerdo_Surtido_Productos (
    id_acuerdo_categoria_fk INT NOT NULL REFERENCES Acuerdo_Categorias(id_acuerdo_categoria) ON DELETE CASCADE,
    id_producto_fk INT NOT NULL REFERENCES Dim_Productos(id_producto) ON DELETE CASCADE,
    PRIMARY KEY (id_acuerdo_categoria_fk, id_producto_fk)
);
COMMENT ON TABLE Acuerdo_Surtido_Productos IS 'Tabla de enlace que especifica el surtido de productos para cada categoría de un acuerdo.';


-- Tabla Gestion_Productos_Aux (¡CORREGIDA!)
DROP TABLE IF EXISTS Gestion_Productos_Aux CASCADE;
CREATE TABLE Gestion_Productos_Aux (
    id_gestion_producto SERIAL PRIMARY KEY,
    id_producto_fk INT NOT NULL UNIQUE REFERENCES Dim_Productos(id_producto) ON DELETE CASCADE,

    -- Tus clasificaciones de negocio
    categoria_gestion VARCHAR(100),
    subcategoria_1_gestion VARCHAR(100),
    subcategoria_2_gestion VARCHAR(100),
    
    -- Atributos de gestión y negocio
    descripcion_guia VARCHAR(255),
    clasificacion_py VARCHAR(100),
    equivalencia_py VARCHAR(50),
    peso_neto NUMERIC(10, 4),
    grupo_tq VARCHAR(100),
    activo_compra BOOLEAN DEFAULT TRUE,

    -- COLUMNAS sr_tat, sr_mm, sr_ssm ELIMINADAS.
    -- Esta lógica ahora se gestiona a través del sistema de Acuerdos_Comerciales
    -- para mayor flexibilidad y precisión histórica.

    -- Llave foránea a la dimensión de marca que tú gestionas
    id_marca_fk INT REFERENCES Dim_Marcas(id_marca)
);
COMMENT ON TABLE Gestion_Productos_Aux IS 'Contiene las clasificaciones y atributos de negocio gestionados manualmente. Enriquece la data de Dim_Productos.';


-- =================================================================
-- SECCIÓN 2: DIMENSIONES DE CLIENTES (Versión 2 - Modelo de Cliente Maestro)
-- =================================================================

-- Tabla Dim_Geografia
-- Catálogo único de ubicaciones geográficas, incluyendo el barrio.
DROP TABLE IF EXISTS Dim_Geografia CASCADE;
CREATE TABLE Dim_Geografia (
    id_geografia SERIAL PRIMARY KEY,
    barrio VARCHAR(150),
    ciudad VARCHAR(100) NOT NULL,
    departamento VARCHAR(100),
    CONSTRAINT uq_geografia UNIQUE (barrio, ciudad, departamento)
);
COMMENT ON TABLE Dim_Geografia IS 'Catálogo único de ubicaciones geográficas (barrio, ciudad, departamento).';


-- Tabla Maestro_Clientes
-- Contiene UNA fila por cada PUNTO DE VENTA, con la información que NUNCA cambia.
DROP TABLE IF EXISTS Maestro_Clientes CASCADE;
CREATE TABLE Maestro_Clientes (
    id_maestro_cliente SERIAL PRIMARY KEY,
    cod_cliente_maestro VARCHAR(50) UNIQUE NOT NULL,
    nombre_unificado VARCHAR(255) NOT NULL
);
COMMENT ON TABLE Maestro_Clientes IS 'Catálogo maestro con una entrada única por punto de venta/sucursal real.';

-- ¡NUEVA TABLA! Dim_Clientes_Clasificacion_Historia (SCD Tipo 2)
-- Almacena el historial de clasificaciones para cada cliente maestro.
DROP TABLE IF EXISTS Dim_Clientes_Clasificacion_Historia CASCADE;
CREATE TABLE Dim_Clientes_Clasificacion_Historia (
    id_clasificacion_historia SERIAL PRIMARY KEY,
    id_maestro_cliente_fk INT NOT NULL REFERENCES Maestro_Clientes(id_maestro_cliente),

    -- Tus clasificaciones de negocio que pueden cambiar con el tiempo:
    canal VARCHAR(100),
    subcanal VARCHAR(100),
    sucursal VARCHAR(55),
    dia_visita VARCHAR(50),
    id_geografia_fk INT REFERENCES Dim_Geografia(id_geografia),

    -- Columnas para manejar el historial
    fecha_inicio_validez DATE NOT NULL,
    fecha_fin_validez DATE NOT NULL
);
COMMENT ON TABLE Dim_Clientes_Clasificacion_Historia IS 'Tabla histórica (SCD Tipo 2) que registra las clasificaciones de un cliente a lo largo del tiempo.';

-- Tabla Dim_Clientes_Empresa
-- Contiene los registros de clientes tal como aparecen en la API para cada empresa.
DROP TABLE IF EXISTS Dim_Clientes_Empresa CASCADE;
CREATE TABLE Dim_Clientes_Empresa (
    id_cliente_empresa SERIAL PRIMARY KEY,
    
    -- Llave Foránea al cliente maestro. ¡Esta es la conexión clave!
    id_maestro_cliente_fk INT NOT NULL REFERENCES Maestro_Clientes(id_maestro_cliente),
    
    -- Datos específicos del cliente EN ESA EMPRESA
    cod_cliente_erp VARCHAR(50) NOT NULL,
    empresa_erp VARCHAR(50) NOT NULL,
    
    -- Otros datos del ERP que pueden variar por empresa
    nit VARCHAR(50),
    nombre_erp VARCHAR(255),
    clasificacion_erp VARCHAR(55),
    direccion_erp VARCHAR(255),
    telefono_erp VARCHAR(55),
    ciudad_erp VARCHAR(55),
    inactivo_erp VARCHAR(10),
    
    -- Restricción de unicidad para la llave de negocio del sistema origen.
    CONSTRAINT uq_cliente_por_empresa UNIQUE (cod_cliente_erp, empresa_erp)
);
COMMENT ON TABLE Dim_Clientes_Empresa IS 'Registros de clientes por empresa, tal como vienen del ERP. Se enlazan a un único cliente maestro.';

-- =================================================================
-- SECCIÓN 3: DIMENSIONES DE VENDEDORES (Versión 2 - Con SCD Tipo 2 para Historial)
-- =================================================================

-- Tabla Maestro_Personas
-- Contiene UNA fila por cada persona física (vendedores, supervisores, etc.).
-- Esta es la fuente de verdad para los datos de una persona.
DROP TABLE IF EXISTS Maestro_Personas CASCADE;
CREATE TABLE Maestro_Personas (
    id_persona SERIAL PRIMARY KEY,
    numero_documento VARCHAR(50) UNIQUE NOT NULL, -- La llave de negocio que identifica a una persona única.
    nombre_completo VARCHAR(255) NOT NULL
);
COMMENT ON TABLE Maestro_Personas IS 'Catálogo maestro con una entrada única por persona física. Contiene datos que no cambian con el tiempo.';


-- Tabla Dim_Vendedores_Historia (Dimensión de Lenta Variación Tipo 2)
-- Cada fila representa un "contrato" o un periodo en el que una persona ocupó un rol de venta.
-- Renombrada para ser más genérica y con la nueva columna 'cargo'
DROP TABLE IF EXISTS Dim_Roles_Comerciales_Historia CASCADE;
CREATE TABLE Dim_Roles_Comerciales_Historia (
    id_rol_historia SERIAL PRIMARY KEY,
    cod_rol_erp VARCHAR(50) NOT NULL, -- Código del rol/puesto (ej. 'V01', 'SUPTATP1')
    empresa_erp VARCHAR(50) NOT NULL,
    cargo VARCHAR(100),               -- ¡NUEVA COLUMNA! Ej: 'Supervisor TAT P1', 'Vendedor Tiendas'
    
    id_persona_fk INT NOT NULL REFERENCES Maestro_Personas(id_persona),
    id_supervisor_fk INT REFERENCES Maestro_Personas(id_persona), 
    
    fecha_inicio_validez DATE NOT NULL,
    fecha_fin_validez DATE NOT NULL,
    
    CONSTRAINT uq_rol_periodo UNIQUE (cod_rol_erp, empresa_erp, fecha_inicio_validez)
);
COMMENT ON TABLE Dim_Roles_Comerciales_Historia IS 'Tabla histórica (SCD Tipo 2) que registra qué persona ocupó un rol/cargo comercial y durante qué periodo.';


-- Tabla Dim_Portafolio
-- Mapea un ROL de venta con las LÍNEAS de producto que está autorizado a vender.
DROP TABLE IF EXISTS Dim_Portafolio CASCADE;
CREATE TABLE Dim_Portafolio (
    -- La llave primaria es la combinación de ambas columnas.
    cod_vendedor_erp VARCHAR(50) NOT NULL,
    id_linea_fk INT NOT NULL REFERENCES Dim_Lineas(id_linea),
    PRIMARY KEY (cod_vendedor_erp, id_linea_fk)
);
COMMENT ON TABLE Dim_Portafolio IS 'Mapea los roles de venta con las líneas de producto que componen su portafolio.';