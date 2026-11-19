from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ETL_DIR = (
    PROJECT_ROOT
    / "src"
    / "etl"
)

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "JStyles_OPERATIVO.xlsx"
)

sys.path.insert(
    0,
    str(ETL_DIR),
)

from extract import extract_data
from transform import transform_data
from quality import run_quality_checks


def test_transformed_data_has_no_critical_quality_failures():
    """
    El dataset transformado no debe contener
    fallos críticos de calidad.
    """

    if not RAW_FILE.exists():
        pytest.skip(
            "El Excel operativo real no está disponible."
        )

    raw_data = extract_data()

    transformed_data = transform_data(
        raw_data
    )

    report = run_quality_checks(
        transformed_data
    )

    failures = report.loc[
        report["status"].eq("FAIL")
    ]

    assert failures.empty, (
        "\nFallaron controles críticos:\n"
        + failures.to_string(index=False)
    )


def test_quality_report_contains_checks():
    """
    El quality gate debe producir controles
    estructurados y no un reporte vacío.
    """

    if not RAW_FILE.exists():
        pytest.skip(
            "El Excel operativo real no está disponible."
        )

    raw_data = extract_data()

    transformed_data = transform_data(
        raw_data
    )

    report = run_quality_checks(
        transformed_data
    )

    assert not report.empty

    required_columns = {
        "table",
        "check",
        "status",
        "severity",
        "failed_rows",
        "detail",
    }

    assert required_columns.issubset(
        report.columns
    )


def test_known_anomalies_are_warnings_not_failures():
    """
    Las anomalías conocidas deben quedar visibles
    como WARN sin bloquear el pipeline.
    """

    if not RAW_FILE.exists():
        pytest.skip(
            "El Excel operativo real no está disponible."
        )

    raw_data = extract_data()

    transformed_data = transform_data(
        raw_data
    )

    report = run_quality_checks(
        transformed_data
    )

    warning_checks = set(
        report.loc[
            report["status"].eq("WARN"),
            "check",
        ]
    )

    expected_warnings = {
        "invalid_dates_detected",
        "products_requiring_review",
        "price_conflicts_detected",
    }

    assert expected_warnings.issubset(
        warning_checks
    )