from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ETL_DIR = (
    PROJECT_ROOT
    / "src"
    / "etl"
)

sys.path.insert(
    0,
    str(ETL_DIR),
)

from run_logger import (
    create_run_record,
    finish_run,
)


def test_create_run_record():
    record = create_run_record()

    assert record["run_id"]
    assert record["pipeline"] == "jstyles_etl"
    assert record["status"] == "RUNNING"

    assert record["started_at"] is not None
    assert record["finished_at"] is None

    assert record["rows_extracted"] == 0
    assert record["rows_transformed"] == 0
    assert record["rows_saved"] == 0

    assert record["quality_pass"] == 0
    assert record["quality_warn"] == 0
    assert record["quality_fail"] == 0


def test_finish_successful_run():
    record = create_run_record()

    finished = finish_run(
        record,
        "SUCCESS",
        rows_extracted=3337,
        rows_transformed=2100,
        rows_saved=2100,
        quality_pass=35,
        quality_warn=3,
        quality_fail=0,
    )

    assert finished["status"] == "SUCCESS"

    assert finished["finished_at"] is not None

    assert finished["duration_seconds"] >= 0

    assert finished["rows_extracted"] == 3337
    assert finished["rows_transformed"] == 2100
    assert finished["rows_saved"] == 2100

    assert finished["quality_pass"] == 35
    assert finished["quality_warn"] == 3
    assert finished["quality_fail"] == 0

    assert finished["error_type"] is None
    assert finished["error_message"] is None


def test_finish_failed_run():
    record = create_run_record()

    error = ValueError(
        "Error de prueba"
    )

    finished = finish_run(
        record,
        "FAILED",
        error=error,
    )

    assert finished["status"] == "FAILED"

    assert finished["error_type"] == "ValueError"

    assert (
        finished["error_message"]
        == "Error de prueba"
    )

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

