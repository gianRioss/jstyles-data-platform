-- =========================================================
-- JSTYLES DATA PLATFORM
-- Esquema relacional principal
-- =========================================================

CREATE SCHEMA IF NOT EXISTS jstyles;

SET search_path TO jstyles;


-- =========================================================
-- 1. BARBEROS
-- =========================================================

CREATE TABLE IF NOT EXISTS barberos (
    barbero_id VARCHAR(20) PRIMARY KEY,
    nombre TEXT NOT NULL,
    porcentaje_comision_servicio NUMERIC(5,4) NOT NULL,
    esquema VARCHAR(20) NOT NULL,
    activo BOOLEAN NOT NULL,
    es_propietario BOOLEAN NOT NULL,

    CONSTRAINT chk_barberos_porcentaje
        CHECK (
            porcentaje_comision_servicio
            BETWEEN 0 AND 1
        )
);


-- =========================================================
-- 2. CLIENTES
-- =========================================================

CREATE TABLE IF NOT EXISTS clientes (
    cliente_id VARCHAR(20) PRIMARY KEY,
    nombre TEXT NOT NULL,
    telefono TEXT,
    fecha_alta DATE NOT NULL,
    acepta_promociones BOOLEAN NOT NULL,
    observaciones TEXT,
    activo BOOLEAN NOT NULL
);


-- =========================================================
-- 3. SERVICIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS servicios (
    servicio_id VARCHAR(20) PRIMARY KEY,
    servicio TEXT NOT NULL,
    duracion_min INTEGER,
    activo BOOLEAN NOT NULL,

    CONSTRAINT chk_servicios_duracion
        CHECK (
            duracion_min IS NULL
            OR duracion_min > 0
        )
);


-- =========================================================
-- 4. TARIFAS DE SERVICIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS tarifas_servicios (
    tarifa_id VARCHAR(20) PRIMARY KEY,
    servicio_id VARCHAR(20) NOT NULL,
    precio NUMERIC(12,2) NOT NULL,
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE,
    vigente BOOLEAN NOT NULL,

    CONSTRAINT fk_tarifas_servicio
        FOREIGN KEY (servicio_id)
        REFERENCES servicios(servicio_id),

    CONSTRAINT chk_tarifas_precio
        CHECK (precio > 0),

    CONSTRAINT chk_tarifas_fechas
        CHECK (
            fecha_hasta IS NULL
            OR fecha_hasta >= fecha_desde
        )
);


-- =========================================================
-- 5. VENTAS DE SERVICIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS ventas_servicios (
    ticket_id VARCHAR(30) PRIMARY KEY,

    fecha DATE NOT NULL,
    hora TIME NOT NULL,

    servicio_id VARCHAR(20) NOT NULL,
    barbero_id VARCHAR(20) NOT NULL,
    cliente_id VARCHAR(20),

    precio NUMERIC(12,2) NOT NULL,
    medio_de_pago TEXT NOT NULL,
    propina NUMERIC(12,2) NOT NULL DEFAULT 0,
    descuento NUMERIC(7,4) NOT NULL DEFAULT 0,
    total_cobrado NUMERIC(12,2) NOT NULL,
    comision NUMERIC(12,2) NOT NULL,

    cliente_nombre_origen TEXT,
    cliente_selector TEXT,

    nro_factura TEXT,
    facturado BOOLEAN,

    CONSTRAINT fk_ventas_servicio
        FOREIGN KEY (servicio_id)
        REFERENCES servicios(servicio_id),

    CONSTRAINT fk_ventas_barbero
        FOREIGN KEY (barbero_id)
        REFERENCES barberos(barbero_id),

    CONSTRAINT fk_ventas_cliente
        FOREIGN KEY (cliente_id)
        REFERENCES clientes(cliente_id),

    CONSTRAINT chk_ventas_precio
        CHECK (precio >= 0),

    CONSTRAINT chk_ventas_propina
        CHECK (propina >= 0),

    CONSTRAINT chk_ventas_descuento
        CHECK (descuento BETWEEN 0 AND 1),

    CONSTRAINT chk_ventas_total
        CHECK (total_cobrado >= 0),

    CONSTRAINT chk_ventas_comision
        CHECK (comision >= 0)
);


-- =========================================================
-- 6. PRODUCTOS
-- =========================================================

CREATE TABLE IF NOT EXISTS productos (
    producto_id VARCHAR(30) PRIMARY KEY,
    producto TEXT NOT NULL,

    en_inventario BOOLEAN NOT NULL,
    en_compras BOOLEAN NOT NULL,
    en_ventas BOOLEAN NOT NULL,
    requiere_revision BOOLEAN NOT NULL
);


-- =========================================================
-- 7. VENTAS DE PRODUCTOS
-- =========================================================

CREATE TABLE IF NOT EXISTS ventas_productos (
    venta_producto_id VARCHAR(40) PRIMARY KEY,

    fecha DATE,
    fecha_invalida BOOLEAN NOT NULL,

    producto_id VARCHAR(30) NOT NULL,
    producto_nombre_origen TEXT NOT NULL,

    cantidad NUMERIC(12,3) NOT NULL,
    precio_unitario NUMERIC(12,2),
    total NUMERIC(12,2) NOT NULL,
    utilidad NUMERIC(12,2),

    vendedor TEXT,
    comision_vendedor NUMERIC(12,2),

    medio_de_pago TEXT,
    notas TEXT,

    CONSTRAINT fk_ventas_productos_producto
        FOREIGN KEY (producto_id)
        REFERENCES productos(producto_id),

    CONSTRAINT chk_ventas_productos_cantidad
        CHECK (cantidad > 0),

    CONSTRAINT chk_ventas_productos_precio
        CHECK (
            precio_unitario IS NULL
            OR precio_unitario >= 0
        ),

    CONSTRAINT chk_ventas_productos_total
        CHECK (total >= 0),

    CONSTRAINT chk_ventas_productos_comision
        CHECK (
            comision_vendedor IS NULL
            OR comision_vendedor >= 0
        )
);


-- =========================================================
-- 8. COMPRAS DE PRODUCTOS
-- =========================================================

CREATE TABLE IF NOT EXISTS compras_productos (
    compra_id VARCHAR(40) PRIMARY KEY,

    fecha DATE NOT NULL,
    proveedor TEXT NOT NULL,

    producto_id VARCHAR(30) NOT NULL,
    producto_nombre_origen TEXT NOT NULL,

    cantidad NUMERIC(12,3) NOT NULL,
    costo_unitario NUMERIC(12,2) NOT NULL,
    total NUMERIC(12,2) NOT NULL,

    notas TEXT,
    comprar_mas_productos NUMERIC(12,2),

    CONSTRAINT fk_compras_producto
        FOREIGN KEY (producto_id)
        REFERENCES productos(producto_id),

    CONSTRAINT chk_compras_cantidad
        CHECK (cantidad > 0),

    CONSTRAINT chk_compras_costo
        CHECK (costo_unitario >= 0),

    CONSTRAINT chk_compras_total
        CHECK (total >= 0)
);


-- =========================================================
-- 9. INVENTARIO
-- =========================================================

CREATE TABLE IF NOT EXISTS inventario_productos (
    producto_id VARCHAR(30) PRIMARY KEY,

    producto_nombre_origen TEXT NOT NULL,

    entradas NUMERIC(12,3),
    salidas NUMERIC(12,3),
    stock_actual NUMERIC(12,3),

    costo_promedio NUMERIC(12,2),
    valor_stock NUMERIC(14,2),

    precio_venta NUMERIC(12,2),

    precio_conflicto BOOLEAN NOT NULL,
    precios_observados TEXT,

    notas TEXT,
    margen NUMERIC(12,4),

    CONSTRAINT fk_inventario_producto
        FOREIGN KEY (producto_id)
        REFERENCES productos(producto_id),

    CONSTRAINT chk_inventario_entradas
        CHECK (
            entradas IS NULL
            OR entradas >= 0
        ),

    CONSTRAINT chk_inventario_salidas
        CHECK (
            salidas IS NULL
            OR salidas >= 0
        )
);


-- =========================================================
-- 10. GASTOS
-- =========================================================

CREATE TABLE IF NOT EXISTS gastos (
    gasto_id VARCHAR(40) PRIMARY KEY,

    fecha DATE NOT NULL,
    concepto TEXT NOT NULL,
    monto NUMERIC(12,2) NOT NULL,

    metodo_pago TEXT,
    notas TEXT,

    tipo_gasto VARCHAR(20) NOT NULL,
    categoria TEXT NOT NULL,

    afecta_resultado_local BOOLEAN NOT NULL,

    CONSTRAINT chk_gastos_monto
        CHECK (monto > 0),

    CONSTRAINT chk_gastos_tipo
        CHECK (
            tipo_gasto IN (
                'comercial',
                'personal'
            )
        )
);


-- =========================================================
-- 11. COMISIONES DE BARBEROS
-- =========================================================

CREATE TABLE IF NOT EXISTS comisiones_barberos (
    comision_config_id VARCHAR(40) PRIMARY KEY,

    barbero_id VARCHAR(20) NOT NULL,

    porcentaje_barbero NUMERIC(5,4) NOT NULL,
    porcentaje_local NUMERIC(5,4) NOT NULL,

    esquema VARCHAR(20) NOT NULL,

    fecha_desde DATE,
    fecha_hasta DATE,

    observado_desde DATE,
    observado_hasta DATE,

    origen VARCHAR(30) NOT NULL,

    es_configuracion_actual BOOLEAN NOT NULL,

    CONSTRAINT fk_comisiones_barbero
        FOREIGN KEY (barbero_id)
        REFERENCES barberos(barbero_id),

    CONSTRAINT chk_comisiones_porcentaje_barbero
        CHECK (
            porcentaje_barbero
            BETWEEN 0 AND 1
        ),

    CONSTRAINT chk_comisiones_porcentaje_local
        CHECK (
            porcentaje_local
            BETWEEN 0 AND 1
        ),

    CONSTRAINT chk_comisiones_suma
        CHECK (
            ROUND(
                porcentaje_barbero
                + porcentaje_local,
                4
            ) = 1.0000
        ),

    CONSTRAINT chk_comisiones_fechas
        CHECK (
            fecha_hasta IS NULL
            OR fecha_desde IS NULL
            OR fecha_hasta >= fecha_desde
        ),

    CONSTRAINT chk_comisiones_observadas
        CHECK (
            observado_hasta IS NULL
            OR observado_desde IS NULL
            OR observado_hasta >= observado_desde
        ),

    CONSTRAINT chk_comisiones_origen
        CHECK (
            origen IN (
                'configuracion_actual',
                'historico_observado'
            )
        )
);


-- =========================================================
-- ÍNDICES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_ventas_servicios_fecha
    ON ventas_servicios(fecha);

CREATE INDEX IF NOT EXISTS idx_ventas_servicios_barbero
    ON ventas_servicios(barbero_id);

CREATE INDEX IF NOT EXISTS idx_ventas_servicios_servicio
    ON ventas_servicios(servicio_id);

CREATE INDEX IF NOT EXISTS idx_ventas_servicios_cliente
    ON ventas_servicios(cliente_id);


CREATE INDEX IF NOT EXISTS idx_tarifas_servicio
    ON tarifas_servicios(servicio_id);


CREATE INDEX IF NOT EXISTS idx_ventas_productos_fecha
    ON ventas_productos(fecha);

CREATE INDEX IF NOT EXISTS idx_ventas_productos_producto
    ON ventas_productos(producto_id);


CREATE INDEX IF NOT EXISTS idx_compras_productos_fecha
    ON compras_productos(fecha);

CREATE INDEX IF NOT EXISTS idx_compras_productos_producto
    ON compras_productos(producto_id);


CREATE INDEX IF NOT EXISTS idx_gastos_fecha
    ON gastos(fecha);

CREATE INDEX IF NOT EXISTS idx_gastos_tipo
    ON gastos(tipo_gasto);


CREATE INDEX IF NOT EXISTS idx_comisiones_barbero
    ON comisiones_barberos(barbero_id);


-- Solo puede existir una configuración marcada como actual
-- por cada barbero.

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_comisiones_barberos_actual
ON comisiones_barberos(barbero_id)
WHERE es_configuracion_actual = TRUE;