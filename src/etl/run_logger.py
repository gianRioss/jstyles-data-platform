
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# =========================================================
# CONFIGURACION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "pipeline_runs"
)

TIMEZONE = ZoneInfo(
    "America/Argentina/Buenos_Aires"
)


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def current_time():
    """
    Devuelve fecha y hora timezone-aware.
    """

    return datetime.now(
        TIMEZONE
    )


def create_run_id():
    """
    Genera un identificador único para
    una ejecución del pipeline.
    """

    return str(
        uuid.uuid4()
    )


# =========================================================
# INICIALIZACION DE LA EJECUCION
# =========================================================

def create_run_record(
    pipeline_name="jstyles_etl",
):
    """
    Inicializa el registro de una ejecución.
    """

    started_at = current_time()

    return {
        "run_id": create_run_id(),
        "pipeline": pipeline_name,
        "started_at": started_at.isoformat(),
        "finished_at": None,
        "duration_seconds": None,
        "status": "RUNNING",

        # Extraccion
        "rows_extracted": 0,

        # Ingestion RAW
        "snapshot_id": None,
        "snapshot_created": None,
        "rows_inserted_raw": 0,

        # Transformacion y carga
        "rows_transformed": 0,
        "rows_saved": 0,
        "rows_loaded_db": 0,

        # Calidad de datos
        "quality_pass": 0,
        "quality_warn": 0,
        "quality_fail": 0,

        # Registro de errores
        "error_type": None,
        "error_message": None,
    }


# =========================================================
# FINALIZACION DE LA EJECUCION
# =========================================================

def finish_run(
    record,
    status,
    *,
    rows_extracted=None,
    snapshot_id=None,
    snapshot_created=None,
    rows_inserted_raw=None,
    rows_transformed=None,
    rows_saved=None,
    rows_loaded_db=None,
    quality_pass=None,
    quality_warn=None,
    quality_fail=None,
    error=None,
):
    """
    Finaliza una ejecución y completa
    sus métricas de extracción, ingestión RAW,
    transformación, calidad y carga PostgreSQL.
    """

    finished_at = current_time()

    started_at = datetime.fromisoformat(
        record["started_at"]
    )

    duration = (
        finished_at
        - started_at
    ).total_seconds()

    record["finished_at"] = (
        finished_at.isoformat()
    )

    record["duration_seconds"] = round(
        duration,
        3,
    )

    record["status"] = status

    # =====================================================
    # METRICAS NUMERICAS
    # =====================================================

    optional_values = {
        "rows_extracted": rows_extracted,
        "rows_inserted_raw": rows_inserted_raw,
        "rows_transformed": rows_transformed,
        "rows_saved": rows_saved,
        "rows_loaded_db": rows_loaded_db,
        "quality_pass": quality_pass,
        "quality_warn": quality_warn,
        "quality_fail": quality_fail,
    }

    for key, value in optional_values.items():

        if value is not None:

            record[key] = int(value)

    # =====================================================
    # METADATOS RAW
    # =====================================================

    if snapshot_id is not None:

        record["snapshot_id"] = str(
            snapshot_id
        )

    if snapshot_created is not None:

        record["snapshot_created"] = bool(
            snapshot_created
        )

    # =====================================================
    # REGISTRO DE ERRORES
    # =====================================================

    if error is not None:

        record["error_type"] = (
            type(error).__name__
        )

        record["error_message"] = str(
            error
        )

    return record


# =========================================================
# PERSISTENCIA DE AUDITORIA
# =========================================================

def save_run_record(record):
    """
    Guarda cada ejecución en formato JSONL.

    JSONL permite agregar ejecuciones sin
    reescribir el historial completo.
    """

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        REPORT_DIR
        / "pipeline_runs.jsonl"
    )

    with output_file.open(
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
        )

        file.write("\n")

    return output_file

# =========================================================
# TEST 4: NUEVO SNAPSHOT RAW
# =========================================================

def test_finish_run_with_new_raw_snapshot():

    record = create_run_record()

    snapshot_id = "a" * 64

    result = finish_run(
        record,
        "SUCCESS",
        rows_extracted=3333,
        snapshot_id=snapshot_id,
        snapshot_created=True,
        rows_inserted_raw=3333,
        rows_transformed=2102,
        rows_saved=2102,
        rows_loaded_db=2102,
    )

    assert result["status"] == "SUCCESS"
    assert result["snapshot_id"] == snapshot_id
    assert result["snapshot_created"] is True
    assert result["rows_inserted_raw"] == 3333
    assert result["rows_extracted"] == 3333
    assert result["rows_loaded_db"] == 2102


# =========================================================
# TEST 5: SNAPSHOT RAW REUTILIZADO
# =========================================================

def test_finish_run_with_existing_raw_snapshot():

    record = create_run_record()

    snapshot_id = "b" * 64

    result = finish_run(
        record,
        "SUCCESS",
        rows_extracted=3333,
        snapshot_id=snapshot_id,
        snapshot_created=False,
        rows_inserted_raw=0,
        rows_transformed=2102,
        rows_saved=2102,
        rows_loaded_db=2102,
    )

    assert result["status"] == "SUCCESS"
    assert result["snapshot_id"] == snapshot_id
    assert result["snapshot_created"] is False
    assert result["rows_inserted_raw"] == 0
    assert result["rows_extracted"] == 3333


# =========================================================
# TEST 6: FALLO ANTES DE COMPLETAR RAW
# =========================================================

def test_failed_run_before_raw_ingestion():

    record = create_run_record()

    error = RuntimeError(
        "Error simulado durante ingestion RAW"
    )

    result = finish_run(
        record,
        "FAILED",
        rows_extracted=3333,
        error=error,
    )

    assert result["status"] == "FAILED"
    assert result["snapshot_id"] is None
    assert result["snapshot_created"] is None
    assert result["rows_inserted_raw"] == 0
    assert result["rows_extracted"] == 3333
    assert result["rows_transformed"] == 0
    assert result["rows_loaded_db"] == 0
    assert result["error_type"] == "RuntimeError"
    assert result["error_message"] == str(error)
