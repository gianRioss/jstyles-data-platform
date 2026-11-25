-- =========================================================
-- JSTYLES DATA PLATFORM
-- Creación inicial de arquitectura por capas
-- =========================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;

COMMIT;
