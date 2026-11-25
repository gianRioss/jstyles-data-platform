
from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ETL_DIR = PROJECT_ROOT / "src" / "etl"

sys.path.insert(0, str(ETL_DIR))

from extract import extract_data

from ingest_raw import (
    calculate_hash,
    prepare_raw_records,
)


# =========================================================
# FIXTURE
# =========================================================

@pytest.fixture(scope="module")
def raw_data():
    """
    Extrae los datos reales una sola vez para las pruebas.
    """

    return extract_data()


# =========================================================
# TEST 1: HASH DETERMINISTICO
# =========================================================

def test_hash_is_deterministic():

    first = {
        "servicio": "corte",
        "precio": 14000,
    }

    second = {
        "precio": 14000,
        "servicio": "corte",
    }

    first_hash = calculate_hash(first)
    second_hash = calculate_hash(second)

    assert first_hash == second_hash

    assert len(first_hash) == 64


# =========================================================
# TEST 2: ESTABILIDAD DEL SNAPSHOT
# =========================================================

def test_snapshot_is_deterministic(raw_data):

    first_id, first_records = prepare_raw_records(
        raw_data
    )

    second_id, second_records = prepare_raw_records(
        raw_data
    )

    assert first_id == second_id

    assert first_records == second_records

    assert len(first_id) == 64

    assert len(first_records) == 9

    expected_rows = sum(
        len(df)
        for df in raw_data.values()
    )

    prepared_rows = sum(
        len(records)
        for records in first_records.values()
    )

    assert prepared_rows == expected_rows


# =========================================================
# TEST 3: NUEVA VENTA SIMULADA
# =========================================================

def test_new_sale_creates_new_snapshot(raw_data):

    original_id, original_records = (
        prepare_raw_records(raw_data)
    )

    simulated_data = {
        sheet: df.copy(deep=True)
        for sheet, df in raw_data.items()
    }

    sales = simulated_data["ventas"]

    # Copiamos una fila para simular una nueva operacion.
    new_sale = sales.iloc[[0]].copy()

    new_sale["ticked id "] = "T-TEST-RAW"

    simulated_data["ventas"] = pd.concat(
        [sales, new_sale],
        ignore_index=True,
    )

    new_id, new_records = prepare_raw_records(
        simulated_data
    )

    # El contenido cambio, por lo tanto cambia el snapshot.
    assert new_id != original_id

    # Debe existir exactamente una fila adicional.
    assert len(new_records["ventas"]) == (
        len(original_records["ventas"]) + 1
    )

    # Los registros originales deben permanecer iguales.
    assert new_records["ventas"][:-1] == (
        original_records["ventas"]
    )

    # Las otras hojas no deben cambiar.
    for sheet in original_records:

        if sheet != "ventas":

            assert new_records[sheet] == (
                original_records[sheet]
            )

    # Repetir la simulacion genera el mismo snapshot.
    repeated_id, repeated_records = (
        prepare_raw_records(simulated_data)
    )

    assert repeated_id == new_id

    assert repeated_records == new_records

    # La fuente original no fue modificada en memoria.
    final_original_id, _ = prepare_raw_records(raw_data)

    assert final_original_id == original_id


# =========================================================
# TEST 4: MODIFICACION DE UN REGISTRO
# =========================================================

def test_modified_record_changes_snapshot(raw_data):

    original_id, original_records = (
        prepare_raw_records(raw_data)
    )

    simulated_data = {
        sheet: df.copy(deep=True)
        for sheet, df in raw_data.items()
    }

    simulated_data["ventas"].loc[
        simulated_data["ventas"].index[0],
        "ticked id ",
    ] = "T-TEST-MODIFIED"

    modified_id, modified_records = (
        prepare_raw_records(simulated_data)
    )

    # El snapshot debe cambiar.
    assert modified_id != original_id

    # No se agregaron ni eliminaron filas.
    assert len(modified_records["ventas"]) == (
        len(original_records["ventas"])
    )

    # La huella del registro modificado debe cambiar.
    assert modified_records["ventas"][0]["row_hash"] != (
        original_records["ventas"][0]["row_hash"]
    )

    # Los registros restantes deben conservarse.
    assert modified_records["ventas"][1:] == (
        original_records["ventas"][1:]
    )

# =========================================================
# TEST 5: INTEGRACION REAL CON POSTGRESQL
# =========================================================

def test_raw_postgresql_snapshots_and_rollback(monkeypatch):

    import uuid

    from contextlib import contextmanager

    from sqlalchemy import text

    import ingest_raw

    from extract import SHEETS_ETL
    from load import create_db_engine

    marker = uuid.uuid4().hex

    # Creamos datos sinteticos para las nueve hojas.
    original_data = {
        sheet: pd.DataFrame(
            [
                {
                    "test_marker": marker,
                    "valor": 100,
                }
            ]
        )
        for sheet in SHEETS_ETL
    }

    modified_data = {
        sheet: df.copy(deep=True)
        for sheet, df in original_data.items()
    }

    # Simulamos una nueva venta.
    modified_data["ventas"] = pd.concat(
        [
            modified_data["ventas"],
            pd.DataFrame(
                [
                    {
                        "test_marker": marker,
                        "valor": 200,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    snapshot_a, _ = prepare_raw_records(
        original_data
    )

    snapshot_b, _ = prepare_raw_records(
        modified_data
    )

    assert snapshot_a != snapshot_b

    run_a = str(uuid.uuid4())
    run_b = str(uuid.uuid4())
    run_c = str(uuid.uuid4())

    engine = create_db_engine()

    try:

        with engine.connect() as connection:

            transaction = connection.begin()

            # Adaptador para ejecutar la ingestion real
            # dentro de una transaccion controlada.

            class TestEngine:

                @contextmanager
                def begin(self):

                    with connection.begin_nested():
                        yield connection

                def dispose(self):
                    pass

            monkeypatch.setattr(
                ingest_raw,
                "create_db_engine",
                lambda: TestEngine(),
            )

            try:

                # =========================================
                # 1. PRIMER SNAPSHOT
                # =========================================

                first = ingest_raw.ingest_raw_data(
                    original_data,
                    run_id=run_a,
                    source_file="test_raw.xlsx",
                )

                assert first["snapshot_created"] is True

                assert first["rows_inserted"] == 9

                assert first["snapshot_id"] == snapshot_a

                # =========================================
                # 2. REPETICION DEL MISMO SNAPSHOT
                # =========================================

                repeated = ingest_raw.ingest_raw_data(
                    original_data,
                    run_id=run_b,
                    source_file="test_raw.xlsx",
                )

                assert repeated["snapshot_created"] is False

                assert repeated["rows_inserted"] == 0

                assert repeated["snapshot_id"] == snapshot_a

                # =========================================
                # 3. SNAPSHOT MODIFICADO
                # =========================================

                modified = ingest_raw.ingest_raw_data(
                    modified_data,
                    run_id=run_c,
                    source_file="test_raw.xlsx",
                )

                assert modified["snapshot_created"] is True

                assert modified["rows_inserted"] == 10

                assert modified["snapshot_id"] == snapshot_b

                # =========================================
                # 4. VERIFICAR SNAPSHOTS Y EJECUCIONES
                # =========================================

                snapshots = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.workbook_snapshots
                        WHERE snapshot_id IN (:a, :b)
                    """),
                    {
                        "a": snapshot_a,
                        "b": snapshot_b,
                    },
                ).scalar_one()

                assert snapshots == 2

                runs = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM raw.ingestion_runs
                        WHERE snapshot_id IN (:a, :b)
                    """),
                    {
                        "a": snapshot_a,
                        "b": snapshot_b,
                    },
                ).scalar_one()

                assert runs == 3

                # =========================================
                # 5. VERIFICAR REGISTROS PERSISTIDOS
                # =========================================

                total_a = 0
                total_b = 0

                for sheet in SHEETS_ETL:

                    table = sheet.lower()

                    for snapshot in [snapshot_a, snapshot_b]:

                        count = connection.execute(
                            text(f"""
                                SELECT COUNT(*)
                                FROM raw.{table}
                                WHERE snapshot_id = :snapshot
                            """),
                            {
                                "snapshot": snapshot,
                            },
                        ).scalar_one()

                        expected = (
                            2
                            if sheet == "ventas"
                            and snapshot == snapshot_b
                            else 1
                        )

                        assert count == expected

                        if snapshot == snapshot_a:
                            total_a += count
                        else:
                            total_b += count

                assert total_a == 9
                assert total_b == 10

            finally:

                # Revertimos todos los datos sinteticos.
                transaction.rollback()

        # =============================================
        # 6. CONFIRMAR ROLLBACK
        # =============================================

        with engine.connect() as connection:

            remaining_snapshots = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM raw.workbook_snapshots
                    WHERE snapshot_id IN (:a, :b)
                """),
                {
                    "a": snapshot_a,
                    "b": snapshot_b,
                },
            ).scalar_one()

            assert remaining_snapshots == 0

            remaining_runs = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM raw.ingestion_runs
                    WHERE snapshot_id IN (:a, :b)
                """),
                {
                    "a": snapshot_a,
                    "b": snapshot_b,
                },
            ).scalar_one()

            assert remaining_runs == 0

            for sheet in SHEETS_ETL:

                table = sheet.lower()

                remaining_rows = connection.execute(
                    text(f"""
                        SELECT COUNT(*)
                        FROM raw.{table}
                        WHERE snapshot_id IN (:a, :b)
                    """),
                    {
                        "a": snapshot_a,
                        "b": snapshot_b,
                    },
                ).scalar_one()

                assert remaining_rows == 0

    finally:

        engine.dispose()
