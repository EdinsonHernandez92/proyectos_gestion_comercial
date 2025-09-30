--CREATE DATABASE gestion_comercial
--    WITH
--    OWNER = postgres
--    TEMPLATE = template0  -- <-- ESTA ES LA LÍNEA CLAVE
--    ENCODING = 'UTF8'
--    LC_COLLATE = 'es_CO.UTF-8'
--    LC_CTYPE = 'es_CO.UTF-8'
--    LOCALE_PROVIDER = 'libc'
--    CONNECTION LIMIT = -1;

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

CREATE TABLE Dim_Bodegas (
    id_bodega SERIAL PRIMARY KEY,
    cod_bodega_erp VARCHAR(50) UNIQUE NOT NULL,
    nombre_bodega VARCHAR(100)
);

COMMENT ON TABLE Dim_Bodegas IS 'Catálogo único de las bodegas físicas o virtuales.';

DROP TABLE IF EXISTS Dim_Geografia CASCADE;
CREATE TABLE Dim_Geografia (
    id_geografia SERIAL PRIMARY KEY,
    barrio VARCHAR(150),
    ciudad VARCHAR(100) NOT NULL,
    departamento VARCHAR(100),
    CONSTRAINT uq_geografia UNIQUE (barrio, ciudad, departamento)
);
COMMENT ON TABLE Dim_Geografia IS 'Catálogo único de ubicaciones geográficas (barrio, ciudad, departamento).';

DROP TABLE IF EXISTS Maestro_Personas CASCADE;
CREATE TABLE Maestro_Personas (
    id_persona SERIAL PRIMARY KEY,
    numero_documento VARCHAR(50) UNIQUE NOT NULL, -- La llave de negocio que identifica a una persona única.
    nombre_completo VARCHAR(255) NOT NULL
);
COMMENT ON TABLE Maestro_Personas IS 'Catálogo maestro con una entrada única por persona física. Contiene datos que no cambian con el tiempo.';

DROP TABLE IF EXISTS Dim_Tiempo CASCADE;
CREATE TABLE Dim_Tiempo (
    fecha_sk DATE PRIMARY KEY, -- Usamos la fecha misma como llave primaria (Surrogate Key).
    fecha_completa DATE NOT NULL,
    anio INT NOT NULL,
    mes_del_anio INT NOT NULL,
    nombre_mes VARCHAR(20) NOT NULL,
    trimestre_del_anio INT NOT NULL,
    bimestre_del_anio INT NOT NULL,
    semana_del_anio INT NOT NULL,
    dia_del_mes INT NOT NULL,
    nombre_dia VARCHAR(20) NOT NULL,
    es_fin_de_semana BOOLEAN NOT NULL,
    es_dia_habil BOOLEAN NOT NULL,
    es_festivo BOOLEAN,
    dia_habil_del_mes INT,
    total_dias_habiles_mes INT
);

COMMENT ON TABLE Dim_Tiempo IS 'Dimensión de calendario para análisis de tiempo. Una fila por cada día.';

DROP TABLE IF EXISTS Dim_Productos CASCADE;
CREATE TABLE Dim_Productos (
    id_producto SERIAL PRIMARY KEY,
    codigo_erp VARCHAR(30) NOT NULL,
    referencia VARCHAR(30),
    empresa_erp VARCHAR(50) NOT NULL,
    descripcion_erp VARCHAR(255),
    cod_grupo_erp VARCHAR(50),
    cod_linea_erp VARCHAR(50),
    cod_dpto_sku_erp VARCHAR(50),
    cod_marca_erp VARCHAR(50),
    peso_bruto_erp NUMERIC(10, 4),
    factor_erp NUMERIC(10, 3),
    porcentaje_iva NUMERIC,
    costo_promedio_erp NUMERIC(18, 6),
    costo_ult_erp NUMERIC(18, 6),
    CONSTRAINT uq_producto_empresa UNIQUE (codigo_erp, referencia, empresa_erp)
);
COMMENT ON TABLE Dim_Productos IS 'Tabla maestra de productos tal como existen en el ERP para cada empresa.';

CREATE TABLE Inventario_Actual (
    id_producto_fk INT NOT NULL REFERENCES dim_productos(id_producto),
    id_bodega_fk INT NOT NULL REFERENCES Dim_Bodegas(id_bodega),
    empresa_erp VARCHAR(50) NOT NULL,
    cantidad_disponible NUMERIC(18, 4) NOT NULL,
    fecha_ultima_actualizacion TIMESTAMP WITH TIME ZONE NOT NULL,
    -- La llave primaria asegura una sola fila por producto, bodega y empresa
    PRIMARY KEY (id_producto_fk, id_bodega_fk, empresa_erp)
);

COMMENT ON TABLE Inventario_Actual IS 'Almacena el estado actual y más reciente del inventario por producto, bodega y empresa.';

CREATE TABLE Hechos_Inventario (
    id_inventario BIGSERIAL PRIMARY KEY,
    fecha_snapshot DATE NOT NULL,
    id_producto_fk INT NOT NULL REFERENCES dim_productos(id_producto),
    id_bodega_fk INT NOT NULL REFERENCES Dim_Bodegas(id_bodega),
    empresa_erp VARCHAR(50) NOT NULL,
    cantidad_disponible NUMERIC(18, 4) NOT NULL,
    -- La restricción de unicidad asegura una sola "foto" por día, producto, bodega y empresa
    CONSTRAINT uq_inventario_snapshot UNIQUE (fecha_snapshot, id_producto_fk, id_bodega_fk, empresa_erp)
);

COMMENT ON TABLE Hechos_Inventario IS 'Tabla de hechos histórica para almacenar snapshots del inventario en momentos específicos.';

DROP TABLE IF EXISTS Maestro_Clientes CASCADE;
CREATE TABLE Maestro_Clientes (
    id_maestro_cliente SERIAL PRIMARY KEY,
    cod_cliente_maestro VARCHAR(50) UNIQUE NOT NULL,
    nombre_unificado VARCHAR(255) NOT NULL
);
COMMENT ON TABLE Maestro_Clientes IS 'Catálogo maestro con una entrada única por punto de venta/sucursal real.';

DROP TABLE IF EXISTS Dim_Clientes_Empresa CASCADE;
CREATE TABLE Dim_Clientes_Empresa (
    id_cliente_empresa SERIAL PRIMARY KEY,
    
    -- Llave Foránea al cliente maestro. ¡Esta es la conexión clave!
    id_maestro_cliente_fk INT REFERENCES Maestro_Clientes(id_maestro_cliente),
    
    -- Datos específicos del cliente EN ESA EMPRESA
    cod_cliente_erp VARCHAR(50) NOT NULL,
    empresa_erp VARCHAR(50) NOT NULL,
    
    -- Otros datos del ERP que pueden variar por empresa
    nit VARCHAR(50),
    nombre_erp VARCHAR(255),
    cod_clasificacion_erp VARCHAR(10),
    clasificacion_erp VARCHAR(55),
    direccion_erp VARCHAR(255),
    telefono_erp VARCHAR(55),
    ciudad_erp VARCHAR(55),
    inactivo_erp VARCHAR(10),
    
    -- Restricción de unicidad para la llave de negocio del sistema origen.
    CONSTRAINT uq_cliente_por_empresa UNIQUE (cod_cliente_erp, empresa_erp)
);
COMMENT ON TABLE Dim_Clientes_Empresa IS 'Registros de clientes por empresa, tal como vienen del ERP. Se enlazan a un único cliente maestro.';

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

DROP TABLE IF EXISTS Dim_Portafolio CASCADE;
CREATE TABLE Dim_Portafolio (
    -- La llave primaria es la combinación de ambas columnas.
    cod_vendedor_erp VARCHAR(50) NOT NULL,
    id_linea_fk INT NOT NULL REFERENCES Dim_Lineas(id_linea),
    PRIMARY KEY (cod_vendedor_erp, id_linea_fk)
);
COMMENT ON TABLE Dim_Portafolio IS 'Mapea los roles de venta con las líneas de producto que componen su portafolio.';

DROP TABLE IF EXISTS Reglas_Comision_Conjunto CASCADE;
CREATE TABLE Reglas_Comision_Conjunto (
    id_conjunto SERIAL PRIMARY KEY,
    nombre_conjunto VARCHAR(255) NOT NULL, -- Ej: "Liquidación Vendedor V01 - 2024-04"
    
    -- El contexto que define a quién aplica este conjunto de reglas
    rol VARCHAR(100),
    canal VARCHAR(100),
    portafolio VARCHAR(100),
    empresa_erp VARCHAR(50),
    
    -- El factor comisional base (puede ser nulo si es variable)
    factor_comisional_base NUMERIC(18, 2),
    es_factor_variable BOOLEAN DEFAULT FALSE,
    
    -- Periodo de validez
    periodo DATE NOT NULL,
    
    CONSTRAINT uq_conjunto UNIQUE (rol, canal, portafolio, empresa_erp, periodo)
);
COMMENT ON TABLE Reglas_Comision_Conjunto IS 'Define un "paquete" de liquidación, a quién aplica y su factor base.';

DROP TABLE IF EXISTS Reglas_Comision_Item CASCADE;
CREATE TABLE Reglas_Comision_Item (
    id_item_regla SERIAL PRIMARY KEY,
    id_conjunto_fk INT NOT NULL REFERENCES Reglas_Comision_Conjunto(id_conjunto),
    
    -- Enlace para la jerarquía. Si es un indicador principal, este campo es NULO.
    id_item_padre_fk INT REFERENCES Reglas_Comision_Item(id_item_regla),

    -- Descripción de la regla/item
    nombre_item VARCHAR(255) NOT NULL, -- Ej: "Profundidad", "PRO PLAN GATOS SECO", "Volumen Ventas"
    
    -- Pesos
    peso_sobre_padre NUMERIC(5, 4) NOT NULL, -- El peso de este item DENTRO de su padre. Para indicadores principales, es el peso sobre el total.
                                             -- Corresponde a tu `peso_indicador` o `peso_sub_indicador`.
    
    -- Ámbito de aplicación
    linea_aplicacion VARCHAR(255), -- La `linea` de tu tabla (ej: 'LA SOBERANA', 'TOTAL')
    
    -- Umbrales de cumplimiento
    min_cumplimiento NUMERIC(5, 4),
    max_cumplimiento NUMERIC(5, 4),

    -- Cómo se debe calcular este item
    -- Ej: 'SUMA_VALOR_BASE', 'CONTEO_IMPACTOS_CLIENTE', 'PROMEDIO_PONDERADO_HIJOS'
    tipo_calculo VARCHAR(100) NOT NULL,
    
    -- Parámetros adicionales para el cálculo
    -- Ej: para 'Impactos', podría ser una lista de SKUs. Para 'Profundidad Soberana', el peso de cada sub-indicador.
    parametros_json JSONB,
    
    -- Notas y dependencias
    observacion TEXT
);
COMMENT ON TABLE Reglas_Comision_Item IS 'Tabla jerárquica para almacenar cada item de una regla de comisión (indicadores y sub-indicadores).';

DROP TABLE IF EXISTS Metas_Asignadas CASCADE;
CREATE TABLE Metas_Asignadas (
    id_meta_asignada SERIAL PRIMARY KEY,

    -- Enlace al item de regla para el cual se está asignando la meta.
    id_item_regla_fk INT NOT NULL REFERENCES Reglas_Comision_Item(id_item_regla),
    
    -- Enlace al rol/vendedor y periodo histórico al que se le asigna la meta.
    id_rol_historia_fk INT NOT NULL REFERENCES Dim_Roles_Comerciales_Historia(id_rol_historia),
    
    -- El valor del objetivo
    valor_meta NUMERIC(18, 2) NOT NULL,
    
    -- Periodo al que corresponde esta meta
    periodo DATE NOT NULL,

    CONSTRAINT uq_meta_por_rol_item_periodo UNIQUE (id_item_regla_fk, id_rol_historia_fk, periodo)
);

COMMENT ON TABLE Metas_Asignadas IS 'Almacena las metas u objetivos asignados a cada vendedor para cada indicador en un periodo específico. Poblada desde un proceso externo (ej. Google Sheets).';

CREATE TABLE Resultados_Liquidacion_Comision (
    id_resultado SERIAL PRIMARY KEY,
    id_rol_historia_fk INT NOT NULL REFERENCES Dim_Roles_Comerciales_Historia(id_rol_historia),
    id_conjunto_fk INT NOT NULL REFERENCES Reglas_Comision_Conjunto(id_conjunto),
    id_indicador_fk INT NOT NULL REFERENCES Reglas_Comision_Item(id_item_regla),
    valor_logrado NUMERIC(18, 4),
    porcentaje_cumplimiento NUMERIC(7, 4),
    porcentaje_liquidacion_final NUMERIC(7, 4)
);

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
    --grupo_tq VARCHAR(100), Se crea un módulo dedicado para tq
    --activo_compra BOOLEAN DEFAULT TRUE, Se crea una tabla dedicada

    -- COLUMNAS sr_tat, sr_mm, sr_ssm ELIMINADAS.
    -- Esta lógica ahora se gestiona a través del sistema de Acuerdos_Comerciales
    -- para mayor flexibilidad y precisión histórica.
);
COMMENT ON TABLE Gestion_Productos_Aux IS 'Contiene las clasificaciones y atributos de negocio gestionados manualmente. Enriquece la data de Dim_Productos.';

DROP TABLE IF EXISTS Hechos_Ventas CASCADE;
CREATE TABLE Hechos_Ventas (
    -- Llave primaria de la tabla de hechos
    id_venta BIGSERIAL PRIMARY KEY, -- Usamos BIGSERIAL por si tienes miles de millones de filas a futuro.

    -- --- Claves Foráneas (FK) a las Dimensiones ---
    -- Se usan para los JOINS grandes y el rendimiento.
    fecha_sk DATE NOT NULL REFERENCES Dim_Tiempo(fecha_sk),
    id_producto_fk INT NOT NULL REFERENCES Dim_Productos(id_producto),
    id_cliente_empresa_fk INT NOT NULL REFERENCES Dim_Clientes_Empresa(id_cliente_empresa),
    id_rol_historia_fk INT NOT NULL REFERENCES Dim_Roles_Comerciales_Historia(id_rol_historia),

    -- --- Llaves de Negocio (Business Keys) ---
    -- Redundantes a propósito para facilitar el filtrado y análisis ad-hoc, como tú lo pediste.
    codigo_producto_erp VARCHAR(30),
    cod_cliente_erp VARCHAR(50),
    cod_rol_erp VARCHAR(50),
    empresa_erp VARCHAR(50),

    -- --- Medidas Numéricas (Los Hechos) ---
    cantidad NUMERIC(18, 4) NOT NULL,
    valor_base NUMERIC(18, 4) NOT NULL,
    valor_descuento NUMERIC(18, 4) DEFAULT 0,
    valor_iva NUMERIC(18, 4) DEFAULT 0,
    valor_total NUMERIC(18, 4) NOT NULL,
    costo_total NUMERIC(18, 4),
    precio_lista NUMERIC(18, 4),
    
    -- --- Atributos Degenerados (Contexto adicional de la transacción) ---
    id_transaccion_erp BIGINT, -- Tu 'id_erp'
    numero_factura_erp VARCHAR(50) NOT NULL,
    forma_pago_erp VARCHAR(10),
    id_bodega_fk INT,
    bodega_erp VARCHAR(20),
    lista_precio_erp VARCHAR(20),
    observaciones_erp VARCHAR(255),
    motivo_devolucion_erp VARCHAR(255),
    pedido_tiendapp VARCHAR(20)
);

COMMENT ON TABLE Hechos_Ventas IS 'Tabla de hechos central que registra cada línea de venta. Conecta todas las dimensiones y contiene las medidas de negocio.';

CREATE TABLE Dim_Producto_Estado_Historia (
    id_estado_historia SERIAL PRIMARY KEY,
    id_producto_fk INT NOT NULL REFERENCES dim_productos(id_producto),
    estado VARCHAR(50) NOT NULL, -- Ej: 'Activo para Compra', 'Descontinuado', 'Suspendido'
    fecha_inicio_validez DATE NOT NULL,
    fecha_fin_validez DATE NOT NULL,
    observacion TEXT -- Para añadir notas como "Descontinuado por proveedor"
);

COMMENT ON TABLE Dim_Producto_Estado_Historia IS 'Tabla histórica (SCD Tipo 2) que registra el ciclo de vida y estado de compra de un producto.';

CREATE TABLE Dim_TQ_Negocios (
    id_negocio_tq SERIAL PRIMARY KEY,
    cod_negocio_tq VARCHAR(50) UNIQUE NOT NULL, -- Ej: '018'
    nombre_negocio_tq VARCHAR(100) NOT NULL   -- Ej: 'Respiratorio'
);

COMMENT ON TABLE Dim_TQ_Negocios IS 'Catálogo maestro de los "Negocios" de Tecnoquímicas.';

CREATE TABLE Dim_TQ_Categorias (
    id_categoria_tq SERIAL PRIMARY KEY,
    id_negocio_tq_fk INT NOT NULL REFERENCES Dim_TQ_Negocios(id_negocio_tq), -- Enlace al padre
    cod_categoria_tq VARCHAR(50) UNIQUE NOT NULL, -- Ej: '183'
    nombre_categoria_tq VARCHAR(100) NOT NULL   -- Ej: 'Noraver Garganta'
);

COMMENT ON TABLE Dim_TQ_Categorias IS 'Catálogo de las "Categorías" de Tecnoquímicas, enlazadas a un Negocio.';

CREATE TABLE Map_Producto_TQ_Categoria (
    id_map_tq SERIAL PRIMARY KEY,
    id_producto_fk INT NOT NULL REFERENCES dim_productos(id_producto),
    id_categoria_tq_fk INT NOT NULL REFERENCES Dim_TQ_Categorias(id_categoria_tq),
    
    -- Columnas para el seguimiento histórico
    fecha_inicio_validez DATE NOT NULL,
    fecha_fin_validez DATE NOT NULL,

    CONSTRAINT uq_producto_tq_periodo UNIQUE (id_producto_fk, fecha_inicio_validez)
);

COMMENT ON TABLE Map_Producto_TQ_Categoria IS 'Tabla histórica que mapea un producto a su categoría TQ para un periodo de tiempo.';

CREATE TABLE Api_Vendedores_Crudo (
    cod_cliente_erp VARCHAR(50),
    empresa_erp VARCHAR(50),
    nit_documento VARCHAR(50),
    nombre_vendedor VARCHAR(255),
    fecha_carga DATE DEFAULT CURRENT_DATE,
    PRIMARY KEY (cod_cliente_erp, empresa_erp)
);

COMMENT ON TABLE Api_Vendedores_Crudo IS 'Tabla temporal que guarda el estado diario de los vendedores según la API de TNS.';