from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "pipeline_runs"
)

TIMEZONE = ZoneInfo(
    "America/Argentina/Buenos_Aires"
)


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

        "rows_extracted": 0,
        "rows_transformed": 0,
        "rows_saved": 0,
        "rows_loaded_db": 0,

        "quality_pass": 0,
        "quality_warn": 0,
        "quality_fail": 0,

        "error_type": None,
        "error_message": None,
    }


def finish_run(
    record,
    status,
    *,
    rows_extracted=None,
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
    sus métricas.
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

    optional_values = {
        "rows_extracted": rows_extracted,
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

    if error is not None:
        record["error_type"] = (
            type(error).__name__
        )

        record["error_message"] = str(
            error
        )

    return record


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