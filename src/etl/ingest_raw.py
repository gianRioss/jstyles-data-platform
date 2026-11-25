
from __future__ import annotations

import hashlib
import json
import uuid

from datetime import date, datetime, time

import numpy as np
import pandas as pd

from sqlalchemy import text

from extract import (
    extract_data,
    RAW_FILE,
    SHEETS_ETL,
)

from load import create_db_engine


# =========================================================
# CONFIGURACION
# =========================================================

RAW_SCHEMA = "raw"

SHEET_TABLE_MAP = {
    sheet: sheet.lower()
    for sheet in SHEETS_ETL
}


# =========================================================
# SERIALIZACION
# =========================================================

def normalize_value(value):
    """
    Convierte valores extraidos por pandas
    a tipos compatibles con JSON.
    """

    if pd.isna(value):
        return None

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, pd.Timedelta):
        return value.isoformat()

    return value


def canonical_json(payload):
    """
    Genera una representacion JSON deterministica.
    """

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


# =========================================================
# HASHING
# =========================================================

def calculate_hash(payload):
    """
    Calcula una huella SHA-256.
    """

    serialized = canonical_json(payload)

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


# =========================================================
# PREPARACION DE REGISTROS RAW
# =========================================================

def prepare_raw_records(dataframes):
    """
    Prepara los registros RAW y calcula
    el identificador del snapshot completo.
    """

    expected = set(SHEETS_ETL)
    received = set(dataframes)

    if expected != received:
        raise ValueError(
            f"Hojas faltantes: {expected - received}. "
            f"Hojas inesperadas: {received - expected}."
        )

    prepared = {}
    manifest = {}

    for sheet_name in SHEETS_ETL:

        dataframe = dataframes[sheet_name]

        columns = [
            str(column)
            for column in dataframe.columns
        ]

        if len(columns) != len(set(columns)):
            raise ValueError(
                f"Columnas duplicadas en {sheet_name}"
            )

        records = []

        for source_row, values in enumerate(
            dataframe.itertuples(
                index=False,
                name=None,
            ),
            start=2,
        ):

            payload = {
                column: normalize_value(value)
                for column, value in zip(
                    columns,
                    values,
                )
            }

            row_hash = calculate_hash(payload)

            records.append(
                {
                    "source_sheet": sheet_name,
                    "source_row": source_row,
                    "row_hash": row_hash,
                    "payload": canonical_json(payload),
                }
            )

        prepared[sheet_name] = records

        manifest[sheet_name] = {
            "columns": columns,
            "row_hashes": [
                record["row_hash"]
                for record in records
            ],
        }

    snapshot_id = calculate_hash(manifest)

    return snapshot_id, prepared


# =========================================================
# INGESTION RAW
# =========================================================

def ingest_raw_data(
    dataframes,
    run_id=None,
    source_file=None,
):
    """
    Persiste un snapshot en PostgreSQL.

    Si el snapshot ya existe, reutiliza sus datos
    y registra la nueva ejecucion de ingestion.
    """

    if run_id is None:
        run_id = str(uuid.uuid4())

    if source_file is None:
        source_file = RAW_FILE.name

    run_id = str(uuid.UUID(str(run_id)))
    source_file = str(source_file)

    snapshot_id, prepared = prepare_raw_records(
        dataframes
    )

    rows_extracted = sum(
        len(records)
        for records in prepared.values()
    )

    rows_inserted = 0

    engine = create_db_engine()

    print()
    print("Iniciando ingestion RAW...")
    print(f"Run ID: {run_id}")
    print(f"Snapshot ID: {snapshot_id}")
    print()

    try:
        with engine.begin() as connection:

            # =============================================
            # 1. REGISTRAR SNAPSHOT
            # =============================================

            result = connection.execute(
                text("""
                    INSERT INTO raw.workbook_snapshots (
                        snapshot_id,
                        sheet_count,
                        rows_extracted
                    )
                    VALUES (
                        :snapshot_id,
                        :sheet_count,
                        :rows_extracted
                    )
                    ON CONFLICT (snapshot_id)
                    DO NOTHING
                    RETURNING snapshot_id
                """),
                {
                    "snapshot_id": snapshot_id,
                    "sheet_count": len(prepared),
                    "rows_extracted": rows_extracted,
                },
            ).scalar_one_or_none()

            snapshot_created = result is not None

            # =============================================
            # 2. INSERTAR DATOS SI EL SNAPSHOT ES NUEVO
            # =============================================

            if snapshot_created:

                print("Nuevo snapshot detectado.")
                print()

                for sheet_name, records in prepared.items():

                    table_name = SHEET_TABLE_MAP[
                        sheet_name
                    ]

                    if records:

                        parameters = [
                            {
                                **record,
                                "snapshot_id": snapshot_id,
                            }
                            for record in records
                        ]

                        statement = text(f"""
                            INSERT INTO {RAW_SCHEMA}.{table_name} (
                                snapshot_id,
                                source_sheet,
                                source_row,
                                row_hash,
                                payload
                            )
                            VALUES (
                                :snapshot_id,
                                :source_sheet,
                                :source_row,
                                :row_hash,
                                CAST(:payload AS JSONB)
                            )
                        """)

                        connection.execute(
                            statement,
                            parameters,
                        )

                    rows_inserted += len(records)

                    print(
                        f"[OK] raw.{table_name:<25} "
                        f"{len(records):>6} filas"
                    )

            else:

                print("El snapshot ya existe.")
                print("No se duplicaran los datos RAW.")

            # =============================================
            # 3. REGISTRAR EJECUCION
            # =============================================

            connection.execute(
                text("""
                    INSERT INTO raw.ingestion_runs (
                        run_id,
                        snapshot_id,
                        source_file
                    )
                    VALUES (
                        CAST(:run_id AS UUID),
                        :snapshot_id,
                        :source_file
                    )
                    ON CONFLICT (run_id)
                    DO NOTHING
                """),
                {
                    "run_id": run_id,
                    "snapshot_id": snapshot_id,
                    "source_file": source_file,
                },
            )

            existing_run = connection.execute(
                text("""
                    SELECT
                        snapshot_id,
                        source_file
                    FROM raw.ingestion_runs
                    WHERE run_id = CAST(:run_id AS UUID)
                """),
                {
                    "run_id": run_id,
                },
            ).one()

            if (
                existing_run.snapshot_id != snapshot_id
                or existing_run.source_file != source_file
            ):
                raise ValueError(
                    "El run_id ya esta asociado "
                    "a otra ingestion."
                )

        # =============================================
        # 4. RESULTADO
        # =============================================

        result = {
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "snapshot_created": snapshot_created,
            "sheet_count": len(prepared),
            "rows_extracted": rows_extracted,
            "rows_inserted": rows_inserted,
        }

        print()
        print("=" * 60)
        print("INGESTION RAW COMPLETADA")
        print("=" * 60)

        print(f"Snapshot nuevo: {snapshot_created}")
        print(f"Hojas procesadas: {len(prepared)}")
        print(f"Filas extraidas: {rows_extracted}")
        print(f"Filas RAW insertadas: {rows_inserted}")

        return result

    finally:
        engine.dispose()


# =========================================================
# EJECUCION INDEPENDIENTE
# =========================================================

if __name__ == "__main__":

    raw_data = extract_data()

    ingest_raw_data(raw_data)
