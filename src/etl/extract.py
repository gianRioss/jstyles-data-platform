from pathlib import Path
import warnings

import pandas as pd


# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = PROJECT_ROOT / "data" / "raw" / "JStyles_OPERATIVO.xlsx"


SHEETS_ETL = [
    "barberos",
    "ventas",
    "Clientes",
    "gastos",
    "tarifas_servicios",
    "catalogo_servicios",
    "productos_ventas",
    "compras_mayorista",
    "inventario_productos",
]


# ---------------------------------------------------------
# EXTRACT
# ---------------------------------------------------------

def extract_data() -> dict[str, pd.DataFrame]:
    """
    Extrae las hojas operativas del archivo Excel de JStyles.

    Returns
    -------
    dict[str, pd.DataFrame]
        Diccionario donde:
        - la clave es el nombre de la hoja
        - el valor es un DataFrame de pandas
    """

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo fuente: {RAW_FILE}"
        )

    print("Iniciando extracción de datos...")
    print(f"Archivo fuente: {RAW_FILE}")
    print()

    dataframes = {}

    for sheet in SHEETS_ETL:

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)

            df = pd.read_excel(
                RAW_FILE,
                sheet_name=sheet,
                engine="openpyxl",
            )

        dataframes[sheet] = df

        print(
            f"[OK] {sheet:<25} "
            f"{len(df):>6} filas | "
            f"{len(df.columns):>2} columnas"
        )

    print()
    print(f"Extracción completada: {len(dataframes)} hojas cargadas.")

    return dataframes


# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------

if __name__ == "__main__":
    extract_data()