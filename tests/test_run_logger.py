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