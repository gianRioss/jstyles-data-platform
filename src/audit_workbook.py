from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = PROJECT_ROOT / "data" / "raw" / "JStyles_OPERATIVO.xlsx"
REPORT_DIR = PROJECT_ROOT / "reports" / "auditoria"

SHEETS_OPERATIONAL = {
    "barberos",
    "ventas",
    "Clientes",
    "gastos",
    "productos_ventas",
    "compras_mayorista",
    "inventario_productos",
    "catalogo_servicios",
    "tarifas_servicios",
}

SHEETS_RESULTS = {"liquidacion", "resultado_local", "resumen"}

SHEETS_EXCLUDED = {
    "gian": "Histórico separado de vapers; fuera del ETL inicial.",
    "horarios": "Fuera del alcance inicial.",
    "productos para comprar": "Lista operativa, no tabla transaccional.",
    "servicios": "Catálogo histórico reemplazado por catálogo y tarifas normalizadas.",
}


def normalize_column_name(value: Any) -> str:
    """Return a stable snake_case representation for audit purposes."""
    text = "" if value is None else str(value).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return text or "columna_sin_nombre"


def classify_sheet(sheet_name: str) -> tuple[str, str]:
    if sheet_name in SHEETS_OPERATIONAL:
        return "operativa", "Incluida en el ETL inicial."
    if sheet_name in SHEETS_RESULTS:
        return "resultado", "Se recalculará desde PostgreSQL; no es fuente primaria."
    if sheet_name in SHEETS_EXCLUDED:
        return "excluida", SHEETS_EXCLUDED[sheet_name]
    return "revision", "Requiere clasificación manual."


def dataframe_profile(sheet_name: str, df: pd.DataFrame) -> dict[str, Any]:
    normalized_columns = [normalize_column_name(col) for col in df.columns]
    duplicate_column_names = len(normalized_columns) - len(set(normalized_columns))

    non_empty_rows = int(df.dropna(how="all").shape[0])
    duplicate_rows = int(df.dropna(how="all").duplicated().sum()) if non_empty_rows else 0

    column_details: list[dict[str, Any]] = []
    for original, normalized in zip(df.columns, normalized_columns):
        series = df[original]
        non_null = int(series.notna().sum())
        nulls = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        sample_values = [
            str(value)
            for value in series.dropna().astype(str).head(3).tolist()
        ]
        column_details.append(
            {
                "hoja": sheet_name,
                "columna_original": str(original),
                "columna_normalizada": normalized,
                "tipo_detectado": str(series.dtype),
                "filas_no_nulas": non_null,
                "filas_nulas": nulls,
                "valores_unicos": unique,
                "ejemplos": " | ".join(sample_values),
            }
        )

    return {
        "filas_totales": int(df.shape[0]),
        "filas_con_datos": non_empty_rows,
        "columnas": int(df.shape[1]),
        "filas_duplicadas": duplicate_rows,
        "columnas_normalizadas_duplicadas": duplicate_column_names,
        "column_details": column_details,
    }


def main() -> None:
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {WORKBOOK_PATH}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    excel = pd.ExcelFile(WORKBOOK_PATH, engine="openpyxl")

    sheet_summary: list[dict[str, Any]] = []
    column_summary: list[dict[str, Any]] = []

    for sheet_name in excel.sheet_names:
        scope, note = classify_sheet(sheet_name)

        try:
            df = pd.read_excel(
                WORKBOOK_PATH,
                sheet_name=sheet_name,
                engine="openpyxl",
            )
            profile = dataframe_profile(sheet_name, df)

            sheet_summary.append(
                {
                    "hoja": sheet_name,
                    "clasificacion": scope,
                    "decision": note,
                    "filas_totales": profile["filas_totales"],
                    "filas_con_datos": profile["filas_con_datos"],
                    "columnas": profile["columnas"],
                    "filas_duplicadas": profile["filas_duplicadas"],
                    "columnas_normalizadas_duplicadas": profile[
                        "columnas_normalizadas_duplicadas"
                    ],
                    "estado_lectura": "OK",
                }
            )
            column_summary.extend(profile["column_details"])

        except Exception as exc:  # Keep the audit running even if one sheet fails.
            sheet_summary.append(
                {
                    "hoja": sheet_name,
                    "clasificacion": scope,
                    "decision": note,
                    "filas_totales": None,
                    "filas_con_datos": None,
                    "columnas": None,
                    "filas_duplicadas": None,
                    "columnas_normalizadas_duplicadas": None,
                    "estado_lectura": f"ERROR: {type(exc).__name__}: {exc}",
                }
            )

    sheets_df = pd.DataFrame(sheet_summary)
    columns_df = pd.DataFrame(column_summary)

    sheets_df.to_csv(REPORT_DIR / "resumen_hojas.csv", index=False, encoding="utf-8-sig")
    columns_df.to_csv(
        REPORT_DIR / "detalle_columnas.csv", index=False, encoding="utf-8-sig"
    )

    summary_json = {
        "archivo": str(WORKBOOK_PATH.relative_to(PROJECT_ROOT)),
        "cantidad_hojas": len(excel.sheet_names),
        "hojas": sheet_summary,
    }
    (REPORT_DIR / "resumen_auditoria.json").write_text(
        json.dumps(summary_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    markdown_lines = [
        "# Auditoría inicial de JStyles",
        "",
        f"- Archivo: `{WORKBOOK_PATH.name}`",
        f"- Hojas detectadas: **{len(excel.sheet_names)}**",
        "",
        "## Resumen por hoja",
        "",
        "| Hoja | Clasificación | Filas con datos | Columnas | Duplicadas | Estado |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for row in sheet_summary:
        markdown_lines.append(
            "| {hoja} | {clasificacion} | {filas} | {columnas} | {duplicadas} | {estado} |".format(
                hoja=row["hoja"],
                clasificacion=row["clasificacion"],
                filas=row["filas_con_datos"] if row["filas_con_datos"] is not None else "-",
                columnas=row["columnas"] if row["columnas"] is not None else "-",
                duplicadas=row["filas_duplicadas"] if row["filas_duplicadas"] is not None else "-",
                estado=row["estado_lectura"],
            )
        )

    markdown_lines.extend(
        [
            "",
            "## Criterio de alcance",
            "",
            "- Las hojas operativas son fuentes del ETL.",
            "- Las hojas de resultados se recalcularán desde la base de datos.",
            "- `gian` y `horarios` se conservan, pero se excluyen inicialmente.",
            "- El archivo de `data/raw` nunca debe modificarse desde el pipeline.",
            "",
        ]
    )

    (REPORT_DIR / "auditoria_inicial.md").write_text(
        "\n".join(markdown_lines),
        encoding="utf-8",
    )

    print("Auditoría completada.")
    print(f"Reporte: {REPORT_DIR / 'auditoria_inicial.md'}")
    print(f"Resumen CSV: {REPORT_DIR / 'resumen_hojas.csv'}")
    print(f"Detalle de columnas: {REPORT_DIR / 'detalle_columnas.csv'}")


if __name__ == "__main__":
    main()
