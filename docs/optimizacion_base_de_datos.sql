-- ==============================================================================
-- PLAN DE OPTIMIZACIÓN Y MANTENIMIENTO POSTGRESQL - SMARTBIDS
-- ==============================================================================
-- Ejecutar en el SQL Editor de Railway / Supabase / Neon o vía psql.
-- Nota: Las sentencias CREATE/DROP INDEX CONCURRENTLY deben ejecutarse
-- fuera de bloques de transacción (sin BEGIN / COMMIT).

-- ------------------------------------------------------------------------------
-- 1. MANTENIMIENTO INMEDIATO Y CONTROL DE BLOAT (Vacuum Health)
-- ------------------------------------------------------------------------------
-- Ajustar umbral de autovacuum para tablas pequeñas donde el threshold por defecto (50)
-- nunca se alcanza, causando porcentajes de filas muertas de hasta 140%.
ALTER TABLE core.smartbids_seguimiento_licitacion SET (autovacuum_vacuum_threshold = 10, autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE core.suscriptor SET (autovacuum_vacuum_threshold = 10, autovacuum_vacuum_scale_factor = 0.05);

-- Limpiar tuplas muertas y actualizar estadísticas del optimizador de consultas
VACUUM ANALYZE core.smartbids_seguimiento_licitacion;
VACUUM ANALYZE core.suscriptor;
VACUUM ANALYZE procurement.licitaciones_productos;
VACUUM ANALYZE procurement.licitacion;
VACUUM ANALYZE procurement.unidad_compra;
VACUUM ANALYZE dw.fact_orden_compra;

-- ------------------------------------------------------------------------------
-- 2. ÍNDICES DE ALTO IMPACTO (Solución a Seq Scans y ordenamientos lentos)
-- ------------------------------------------------------------------------------
-- Acelera los listados por fecha de publicación (la consulta más repetida en la app)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lic_fecha_public 
ON procurement.licitacion (lic_fecha_public DESC);

-- Acelera los filtros por fecha de cierre y "Cierre próximo (72h)"
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lic_fecha_cierre 
ON procurement.licitacion (lic_fecha_cierre);

-- Acelera los filtros por tipo de procedimiento
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lic_tipo 
ON procurement.licitacion (lic_tipo_licitacion);

-- Acelera el subquery IN de productos en licitaciones_productos
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lic_prod_codigo 
ON procurement.licitaciones_productos (codigo_producto);

-- Acelera los JOINs y filtros por comuna y organismo en UnidadCompra
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ucom_comuna 
ON procurement.unidad_compra (ucom_codigo_comuna);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ucom_organismo 
ON procurement.unidad_compra (ucom_codigo_organismo);

-- Acelera las consultas analíticas del Data Warehouse por producto y fecha
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fact_oc_prod_fecha 
ON dw.fact_orden_compra (producto_key, fecha_key) 
INCLUDE (monto_neto, cantidad_items);

-- ------------------------------------------------------------------------------
-- 3. BÚSQUEDAS DE TEXTO (Aceleración de búsquedas LIKE / icontains)
-- ------------------------------------------------------------------------------
-- Permite que búsquedas ILIKE '%termino%' usen índice en vez de Seq Scan completo
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_licitacion_nombre_trgm 
ON procurement.licitacion USING gin (lic_nombre gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_licitacion_desc_trgm 
ON procurement.licitacion USING gin (lic_descripcion gin_trgm_ops);

-- ------------------------------------------------------------------------------
-- 4. LIMPIEZA DE ÍNDICES INÚTILES (Unused Indexes identificados)
-- ------------------------------------------------------------------------------
-- Eliminar índices que ocupan memoria/disco y penalizan inserciones sin registrar lecturas
DROP INDEX CONCURRENTLY IF EXISTS catalog.idx_proveedor_rut_normalizado;
DROP INDEX CONCURRENTLY IF EXISTS catalog.stop_word_nombre_stop_word_87fde478_like;
DROP INDEX CONCURRENTLY IF EXISTS catalog.actividad_economica_codigo_actividad_d060bfe2_like;

-- ------------------------------------------------------------------------------
-- 5. TABLA RESUMEN / CACHÉ PARA KPIS DEL DW
-- ------------------------------------------------------------------------------
-- Si dw.mv_kpi_periodo no existe, crear la tabla resumen para evitar el escaneo
-- completo de fact_orden_compra (que tomaba hasta 122s por consulta):
CREATE TABLE IF NOT EXISTS dw.mv_kpi_periodo (
    gran VARCHAR(20) NOT NULL,
    periodo VARCHAR(20) NOT NULL,
    monto NUMERIC,
    items BIGINT,
    proveedores INT,
    compradores INT,
    ordenes BIGINT,
    actualizado_el TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (gran, periodo)
);

-- Poblar los KPIs globales del histórico:
INSERT INTO dw.mv_kpi_periodo (gran, periodo, monto, items, proveedores, compradores, ordenes)
SELECT 
    'historico' AS gran,
    '' AS periodo,
    COALESCE(SUM(monto_bruto), 0) AS monto,
    COALESCE(SUM(cantidad_items), 0) AS items,
    COUNT(DISTINCT proveedor_key) AS proveedores,
    COUNT(DISTINCT comprador_key) AS compradores,
    MAX(total_oc_procesadas) AS ordenes
FROM dw.fact_orden_compra
ON CONFLICT (gran, periodo) DO UPDATE 
SET monto = EXCLUDED.monto,
    items = EXCLUDED.items,
    proveedores = EXCLUDED.proveedores,
    compradores = EXCLUDED.compradores,
    ordenes = EXCLUDED.ordenes,
    actualizado_el = CURRENT_TIMESTAMP;
