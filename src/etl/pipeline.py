from extract import extract_data
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


def count_rows(data):
    """
    Suma las filas de todas las tablas
    contenidas en un diccionario de DataFrames.
    """

    return sum(
        len(dataframe)
        for dataframe in data.values()
    )


def run_pipeline():
    """
    Ejecuta el pipeline principal:

    Extract
        ↓
    Transform
        ↓
    Data Quality
        ↓
    Save

    Cada ejecución queda auditada mediante
    un run_id y métricas del proceso.
    """

    run = create_run_record(
        pipeline_name="jstyles_etl"
    )

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
        # 2. TRANSFORM
        # =================================================

        transformed_data = transform_data(
            raw_data
        )

        rows_transformed = count_rows(
            transformed_data
        )

        # =================================================
        # 3. DATA QUALITY
        # =================================================

        quality_report = run_quality_checks(
            transformed_data
        )

        save_quality_report(
            quality_report
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
        # 4. SAVE
        # =================================================

        rows_saved = save_transformed_data(
            transformed_data
        )

        # =================================================
        # 5. SUCCESS
        # =================================================

        finish_run(
            run,
            "SUCCESS",
            rows_extracted=rows_extracted,
            rows_transformed=rows_transformed,
            rows_saved=rows_saved,
            quality_pass=quality_pass,
            quality_warn=quality_warn,
            quality_fail=quality_fail,
        )

        output_file = save_run_record(
            run
        )

        print()
        print("=" * 60)
        print("PIPELINE COMPLETADO CORRECTAMENTE")
        print("=" * 60)
        print(
            f"Filas extraídas: "
            f"{rows_extracted}"
        )
        print(
            f"Filas transformadas: "
            f"{rows_transformed}"
        )
        print(
            f"Filas guardadas: "
            f"{rows_saved}"
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
        finish_run(
            run,
            "FAILED",
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


if __name__ == "__main__":
    run_pipeline()