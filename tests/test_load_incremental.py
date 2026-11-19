from datetime import date
from pathlib import Path
import os
import sys
import uuid

import pandas as pd
from sqlalchemy import text


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

from load import create_db_engine
from load_incremental import upsert_dataframe


def test_postgresql_upsert_insert_update_and_rollback():
    """
    Prueba el UPSERT real contra PostgreSQL.

    1. Inserta un gasto sintético.
    2. Vuelve a usar la misma PK con datos modificados.
    3. Comprueba que hace UPDATE y no duplica.
    4. Hace ROLLBACK para no alterar la base real.
    """

    engine = create_db_engine()

    schema = os.getenv(
        "DB_SCHEMA",
        "jstyles",
    )

    test_id = (
        "GAS-TEST-"
        + uuid.uuid4().hex[:12].upper()
    )

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                # =========================================
                # 1. INSERT
                # =========================================

                first_version = pd.DataFrame(
                    [
                        {
                            "gasto_id": test_id,
                            "fecha": date(2099, 1, 1),
                            "concepto": "test_upsert_insert",
                            "monto": 1000.00,
                            "metodo_pago": "efectivo",
                            "notas": "test automático",
                            "tipo_gasto": "comercial",
                            "categoria": "test",
                            "afecta_resultado_local": True,
                        }
                    ]
                )

                upsert_dataframe(
                    connection,
                    schema,
                    "gastos",
                    first_version,
                )

                inserted = connection.execute(
                    text(
                        f"""
                        SELECT
                            COUNT(*) AS cantidad,
                            MAX(monto) AS monto
                        FROM {schema}.gastos
                        WHERE gasto_id = :gasto_id
                        """
                    ),
                    {
                        "gasto_id": test_id,
                    },
                ).one()

                assert inserted.cantidad == 1
                assert float(inserted.monto) == 1000.00

                # =========================================
                # 2. UPDATE SOBRE LA MISMA PK
                # =========================================

                second_version = first_version.copy()

                second_version.loc[
                    0,
                    "concepto",
                ] = "test_upsert_update"

                second_version.loc[
                    0,
                    "monto",
                ] = 2500.00

                upsert_dataframe(
                    connection,
                    schema,
                    "gastos",
                    second_version,
                )

                updated = connection.execute(
                    text(
                        f"""
                        SELECT
                            COUNT(*) AS cantidad,
                            MAX(monto) AS monto,
                            MAX(concepto) AS concepto
                        FROM {schema}.gastos
                        WHERE gasto_id = :gasto_id
                        """
                    ),
                    {
                        "gasto_id": test_id,
                    },
                ).one()

                # La PK debe seguir apareciendo una sola vez.
                assert updated.cantidad == 1

                # El valor debe haberse actualizado.
                assert float(updated.monto) == 2500.00

                assert (
                    updated.concepto
                    == "test_upsert_update"
                )

            finally:
                # Nada de esta prueba queda guardado.
                transaction.rollback()

        # =============================================
        # 3. CONFIRMAR QUE EL ROLLBACK FUNCIONÓ
        # =============================================

        with engine.connect() as connection:
            remaining = connection.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM {schema}.gastos
                    WHERE gasto_id = :gasto_id
                    """
                ),
                {
                    "gasto_id": test_id,
                },
            ).scalar_one()

            assert remaining == 0

    finally:
        engine.dispose()