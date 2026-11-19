import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, URL, create_engine, text


# =========================================================
# CONFIGURACIÓN
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ENV_FILE = PROJECT_ROOT / ".env"


# =========================================================
# CONEXIÓN
# =========================================================

def create_db_engine():
    """
    Crea la conexión SQLAlchemy con PostgreSQL utilizando
    las variables almacenadas en .env.
    """

    load_dotenv(ENV_FILE)

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_SCHEMA",
    ]

    missing = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing:
        raise ValueError(
            "Faltan variables de entorno: "
            f"{missing}"
        )

    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(
        url,
        future=True,
    )


# =========================================================
# UTILIDADES
# =========================================================

def read_processed_csv(filename):
    """
    Lee un CSV procesado desde data/processed.
    """

    path = PROCESSED_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {path}"
        )

    return pd.read_csv(path)


def convert_dates(df, columns):
    """
    Convierte columnas de fecha a objetos date de Python.
    """

    df = df.copy()

    for column in columns:
        if column in df.columns:
            parsed = pd.to_datetime(
                df[column],
                errors="coerce",
            )

            df[column] = parsed.dt.date

    return df


def replace_nan_with_none(df):
    """
    Convierte NaN/NaT/pd.NA a None para que PostgreSQL
    los reciba como NULL.
    """

    return df.astype(object).where(
        pd.notna(df),
        None,
    )


# =========================================================
# PREPARACIÓN DE TABLAS
# =========================================================

def prepare_barberos():
    return read_processed_csv(
        "barberos.csv"
    )


def prepare_clientes():
    df = read_processed_csv(
        "clientes.csv"
    )

    df = convert_dates(
        df,
        ["fecha_alta"],
    )

    return df


def prepare_servicios():
    df = read_processed_csv(
        "catalogo_servicios.csv"
    )

    # PostgreSQL espera INTEGER para duracion_min.
    # Los servicios históricos pueden no tener duración.
    df["duracion_min"] = pd.to_numeric(
        df["duracion_min"],
        errors="coerce",
    )

    df["duracion_min"] = df["duracion_min"].apply(
        lambda value: (
            int(value)
            if pd.notna(value)
            else None
        )
    )

    return df


def prepare_tarifas_servicios():
    df = read_processed_csv(
        "tarifas_servicios.csv"
    )

    # El texto del servicio ya está en la tabla servicios.
    df = df.drop(
        columns=["servicio"],
        errors="ignore",
    )

    df = convert_dates(
        df,
        [
            "fecha_desde",
            "fecha_hasta",
        ],
    )

    return df


def prepare_ventas_servicios():
    df = read_processed_csv(
        "ventas.csv"
    )

    # Conservar el nombre original del cliente solamente
    # como trazabilidad histórica.
    df = df.rename(
        columns={
            "cliente": "cliente_nombre_origen",
        }
    )

    # Servicio y barbero se relacionan mediante IDs.
    df = df.drop(
        columns=[
            "servicio",
            "barbero",
        ],
        errors="ignore",
    )

    df = convert_dates(
        df,
        ["fecha"],
    )

    # PostgreSQL espera TIME.
    df["hora"] = (
        pd.to_datetime(
            df["hora"],
            format="%H:%M:%S",
            errors="coerce",
        )
        .dt.time
    )

    # PostgreSQL tiene nro_factura como TEXT.
    if "nro_factura" in df.columns:
        df["nro_factura"] = (
            df["nro_factura"]
            .astype("string")
        )

    # Puede venir completamente vacío.
    if "facturado" in df.columns:
        df["facturado"] = df[
            "facturado"
        ].map(
            {
                1: True,
                0: False,
                1.0: True,
                0.0: False,
                True: True,
                False: False,
            }
        )

    return df


def prepare_productos():
    return read_processed_csv(
        "catalogo_productos.csv"
    )


def prepare_ventas_productos():
    df = read_processed_csv(
        "productos_ventas.csv"
    )

    df = df.rename(
        columns={
            "producto": "producto_nombre_origen",
        }
    )

    df = convert_dates(
        df,
        ["fecha"],
    )

    return df


def prepare_compras_productos():
    df = read_processed_csv(
        "compras_mayorista.csv"
    )

    df = df.rename(
        columns={
            "producto": "producto_nombre_origen",
        }
    )

    df = convert_dates(
        df,
        ["fecha"],
    )

    return df


def prepare_inventario_productos():
    df = read_processed_csv(
        "inventario_productos.csv"
    )

    df = df.rename(
        columns={
            "producto": "producto_nombre_origen",
        }
    )

    return df


def prepare_gastos():
    df = read_processed_csv(
        "gastos.csv"
    )

    df = convert_dates(
        df,
        ["fecha"],
    )

    return df


def prepare_comisiones_barberos():
    df = read_processed_csv(
        "comisiones_barberos.csv"
    )

    df = convert_dates(
        df,
        [
            "fecha_desde",
            "fecha_hasta",
            "observado_desde",
            "observado_hasta",
        ],
    )

    return df


# =========================================================
# CARGA
# =========================================================

def load_data():
    """
    Carga todos los datasets procesados en PostgreSQL.

    Toda la carga se realiza dentro de una única transacción.

    Si una tabla falla, PostgreSQL revierte toda la carga
    y evita dejar la base parcialmente actualizada.
    """

    print()
    print("Iniciando carga a PostgreSQL...")
    print()

    engine = create_db_engine()

    schema = os.getenv(
        "DB_SCHEMA",
        "jstyles",
    )

    # -----------------------------------------------------
    # TABLAS EN ORDEN DE DEPENDENCIA
    # -----------------------------------------------------

    datasets = [
        (
            "barberos",
            prepare_barberos(),
        ),
        (
            "clientes",
            prepare_clientes(),
        ),
        (
            "servicios",
            prepare_servicios(),
        ),
        (
            "productos",
            prepare_productos(),
        ),
        (
            "tarifas_servicios",
            prepare_tarifas_servicios(),
        ),
        (
            "comisiones_barberos",
            prepare_comisiones_barberos(),
        ),
        (
            "ventas_servicios",
            prepare_ventas_servicios(),
        ),
        (
            "ventas_productos",
            prepare_ventas_productos(),
        ),
        (
            "compras_productos",
            prepare_compras_productos(),
        ),
        (
            "inventario_productos",
            prepare_inventario_productos(),
        ),
        (
            "gastos",
            prepare_gastos(),
        ),
    ]

    try:

        # =================================================
        # TRANSACCIÓN
        # =================================================

        with engine.begin() as connection:

            # ---------------------------------------------
            # 1. VACIAR TABLAS
            # ---------------------------------------------

            connection.execute(
                text(
                    f"""
                    TRUNCATE TABLE
                        {schema}.ventas_servicios,
                        {schema}.ventas_productos,
                        {schema}.compras_productos,
                        {schema}.inventario_productos,
                        {schema}.gastos,
                        {schema}.comisiones_barberos,
                        {schema}.tarifas_servicios,
                        {schema}.clientes,
                        {schema}.barberos,
                        {schema}.servicios,
                        {schema}.productos
                    RESTART IDENTITY CASCADE;
                    """
                )
            )

            print(
                "[OK] Tablas vaciadas antes de la carga."
            )
            print()

            # ---------------------------------------------
            # 2. CARGAR DATASETS
            # ---------------------------------------------

            for table_name, dataframe in datasets:

                dataframe = replace_nan_with_none(
                    dataframe
                )

                # Leer la estructura REAL de PostgreSQL.
                # Esto hace que SQLAlchemy conozca los
                # tipos INTEGER, BOOLEAN, DATE, NUMERIC,
                # VARCHAR, etc. definidos en schema.sql.
                metadata = MetaData()

                table = Table(
                    table_name,
                    metadata,
                    schema=schema,
                    autoload_with=connection,
                )

                # Validar que Python no intente insertar
                # columnas inexistentes en PostgreSQL.
                postgres_columns = {
                    column.name
                    for column in table.columns
                }

                dataframe_columns = set(
                    dataframe.columns
                )

                extra_columns = (
                    dataframe_columns
                    - postgres_columns
                )

                if extra_columns:
                    raise ValueError(
                        f"La tabla '{table_name}' contiene "
                        "columnas que no existen en "
                        f"PostgreSQL: {sorted(extra_columns)}"
                    )

                records = dataframe.to_dict(
                    orient="records"
                )

                if records:
                    connection.execute(
                        table.insert(),
                        records,
                    )

                print(
                    f"[OK] {table_name:<24} "
                    f"{len(dataframe):>5} filas"
                )

        print()
        print(
            "Carga a PostgreSQL completada correctamente."
        )

    finally:
        engine.dispose()


# =========================================================
# EJECUCIÓN
# =========================================================

if __name__ == "__main__":
    load_data()