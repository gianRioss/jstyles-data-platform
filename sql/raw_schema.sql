-- =========================================================
-- JSTYLES DATA PLATFORM
-- Capa RAW: snapshots e ingestion de datos
-- =========================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS raw;


-- =========================================================
-- 1. REGISTRO DE SNAPSHOTS
-- =========================================================

CREATE TABLE IF NOT EXISTS raw.workbook_snapshots (

    snapshot_id TEXT PRIMARY KEY,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    sheet_count INTEGER NOT NULL,

    rows_extracted INTEGER NOT NULL,

    CONSTRAINT chk_snapshot_hash
        CHECK (snapshot_id ~ '^[0-9a-f]{64}$'),

    CONSTRAINT chk_snapshot_sheet_count
        CHECK (sheet_count > 0),

    CONSTRAINT chk_snapshot_rows
        CHECK (rows_extracted >= 0)

);


-- =========================================================
-- 2. REGISTRO DE EJECUCIONES DE INGESTION
-- =========================================================

CREATE TABLE IF NOT EXISTS raw.ingestion_runs (

    run_id UUID PRIMARY KEY,

    snapshot_id TEXT NOT NULL,

    source_file TEXT NOT NULL,

    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ingestion_snapshot
        FOREIGN KEY (snapshot_id)
        REFERENCES raw.workbook_snapshots(snapshot_id)

);

CREATE INDEX IF NOT EXISTS idx_ingestion_snapshot
    ON raw.ingestion_runs(snapshot_id);


-- =========================================================
-- 3. TABLAS RAW DE LAS HOJAS OPERATIVAS
-- =========================================================

DO $$
DECLARE
    table_name TEXT;
    sheet_name TEXT;

BEGIN

    FOREACH sheet_name IN ARRAY ARRAY[
        'barberos',
        'ventas',
        'Clientes',
        'gastos',
        'tarifas_servicios',
        'catalogo_servicios',
        'productos_ventas',
        'compras_mayorista',
        'inventario_productos'
    ]

    LOOP

        table_name := LOWER(sheet_name);

        EXECUTE FORMAT(
            'CREATE TABLE IF NOT EXISTS raw.%I (

                snapshot_id TEXT NOT NULL,

                source_sheet TEXT NOT NULL,

                source_row INTEGER NOT NULL,

                row_hash TEXT NOT NULL,

                payload JSONB NOT NULL,

                PRIMARY KEY (
                    snapshot_id,
                    source_row
                ),

                FOREIGN KEY (snapshot_id)
                    REFERENCES raw.workbook_snapshots(snapshot_id),

                CHECK (source_sheet = %L),

                CHECK (source_row >= 2),

                CHECK (row_hash ~ ''^[0-9a-f]{64}$''),

                CHECK (jsonb_typeof(payload) = ''object'')

            )',
            table_name,
            sheet_name
        );

    END LOOP;

END;
$$;


COMMIT;
