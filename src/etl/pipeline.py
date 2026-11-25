
from extract import extract_data
from ingest_raw import ingest_raw_data
from load_incremental import load_incremental_data
from quality import (
    run_quality_checks,
    save_quality_report,
)
from run_logger import (
    create_run_record,
    finish_run,
    save_run_record,
)
from save import save_transformed_data
from transform import transform_data


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def count_rows(data):
    """
    Suma las filas de todas las tablas
    contenidas en un diccionario de DataFrames.
    """

    return sum(
        len(dataframe)
        for dataframe in data.values()
    )


# =========================================================
# PIPELINE PRINCIPAL
# =========================================================

def run_pipeline():
    """
    Ejecuta el pipeline principal:

    Extract
        ↓
    RAW Ingestion
        ↓
    Transform
        ↓
    Data Quality
        ↓
    Save processed CSVs
        ↓
    PostgreSQL UPSERT
        ↓
    Run Audit

    Cada ejecución queda auditada mediante
    un run_id compartido y métricas del proceso.
    """

    run = create_run_record(
        pipeline_name="jstyles_etl"
    )

    # Metricas de extraccion
    rows_extracted = 0

    # Metricas de ingestion RAW
    snapshot_id = None
    snapshot_created = None
    rows_inserted_raw = 0

    # Metricas de transformacion y carga
    rows_transformed = 0
    rows_saved = 0
    rows_loaded_db = 0

    # Metricas de calidad
    quality_pass = 0
    quality_warn = 0
    quality_fail = 0

    print()
    print("=" * 60)
    print("JSTYLES DATA PIPELINE")
    print("=" * 60)
    print(f"Run ID: {run['run_id']}")
    print()

    try:

        # =================================================
        # 1. EXTRACT
        # =================================================

        raw_data = extract_data()

        rows_extracted = count_rows(
            raw_data
        )

        # =================================================
        # 2. RAW INGESTION
        # =================================================

        raw_result = ingest_raw_data(
            raw_data,
            run_id=run["run_id"],
        )

        snapshot_id = raw_result[
            "snapshot_id"
        ]

        snapshot_created = raw_result[
            "snapshot_created"
        ]

        rows_inserted_raw = raw_result[
            "rows_inserted"
        ]

        # =================================================
        # 3. TRANSFORM
        # =================================================

        transformed_data = transform_data(
            raw_data
        )

        rows_transformed = count_rows(
            transformed_data
        )

        # =================================================
        # 4. DATA QUALITY
        # =================================================

        quality_report = run_quality_checks(
            transformed_data
        )

        quality_pass = int(
            quality_report["status"]
            .eq("PASS")
            .sum()
        )

        quality_warn = int(
            quality_report["status"]
            .eq("WARN")
            .sum()
        )

        quality_fail = int(
            quality_report["status"]
            .eq("FAIL")
            .sum()
        )

        save_quality_report(
            quality_report
        )

        print()
        print(
            "Quality Gate: "
            f"PASS={quality_pass} | "
            f"WARN={quality_warn} | "
            f"FAIL={quality_fail}"
        )

        if quality_fail > 0:

            failures = quality_report.loc[
                quality_report[
                    "status"
                ].eq("FAIL")
            ]

            raise ValueError(
                "Fallaron controles críticos "
                "de calidad:\n"
                + failures.to_string(
                    index=False
                )
            )

        # =================================================
        # 5. SAVE PROCESSED CSVs
        # =================================================

        rows_saved = save_transformed_data(
            transformed_data
        )

        # =================================================
        # 6. POSTGRESQL UPSERT
        # =================================================

        rows_loaded_db = (
            load_incremental_data()
        )

        # =================================================
        # 7. SUCCESS
        # =================================================

        finish_run(
            run,
            "SUCCESS",
            rows_extracted=rows_extracted,
            snapshot_id=snapshot_id,
            snapshot_created=snapshot_created,
            rows_inserted_raw=rows_inserted_raw,
            rows_transformed=rows_transformed,
            rows_saved=rows_saved,
            rows_loaded_db=rows_loaded_db,
            quality_pass=quality_pass,
            quality_warn=quality_warn,
            quality_fail=quality_fail,
        )

        output_file = save_run_record(
            run
        )

        print()
        print("=" * 60)
        print(
            "PIPELINE COMPLETADO CORRECTAMENTE"
        )
        print("=" * 60)

        print(
            f"Run ID: {run['run_id']}"
        )

        print(
            f"Snapshot ID: {snapshot_id}"
        )

        print(
            f"Snapshot nuevo: {snapshot_created}"
        )

        print(
            f"Filas extraídas: "
            f"{rows_extracted}"
        )

        print(
            f"Filas RAW insertadas: "
            f"{rows_inserted_raw}"
        )

        print(
            f"Filas transformadas: "
            f"{rows_transformed}"
        )

        print(
            f"Filas guardadas CSV: "
            f"{rows_saved}"
        )

        print(
            f"Filas procesadas PostgreSQL: "
            f"{rows_loaded_db}"
        )

        print(
            f"Quality Gate: "
            f"PASS={quality_pass} | "
            f"WARN={quality_warn} | "
            f"FAIL={quality_fail}"
        )

        print(
            f"Duración: "
            f"{run['duration_seconds']} segundos"
        )

        print(
            f"Auditoría: {output_file}"
        )

        print()

        return run

    except Exception as error:

        # Conservamos las metricas alcanzadas
        # hasta el momento del fallo.

        finish_run(
            run,
            "FAILED",
            rows_extracted=rows_extracted,
            snapshot_id=snapshot_id,
            snapshot_created=snapshot_created,
            rows_inserted_raw=rows_inserted_raw,
            rows_transformed=rows_transformed,
            rows_saved=rows_saved,
            rows_loaded_db=rows_loaded_db,
            quality_pass=quality_pass,
            quality_warn=quality_warn,
            quality_fail=quality_fail,
            error=error,
        )

        output_file = save_run_record(
            run
        )

        print()
        print("=" * 60)
        print("PIPELINE FALLIDO")
        print("=" * 60)

        print(
            f"Run ID: {run['run_id']}"
        )

        print(
            f"Snapshot ID: {snapshot_id}"
        )

        print(
            f"Tipo: {run['error_type']}"
        )

        print(
            f"Error: {run['error_message']}"
        )

        print(
            f"Auditoría: {output_file}"
        )

        print()

        raise


# =========================================================
# EJECUCION
# =========================================================

if __name__ == "__main__":
    run_pipeline()
