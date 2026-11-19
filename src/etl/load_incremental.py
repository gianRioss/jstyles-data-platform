from sqlalchemy import MetaData, Table
from sqlalchemy.dialects.postgresql import insert as pg_insert

from load import (
    create_db_engine,
    prepare_barberos,
    prepare_clientes,
    prepare_servicios,
    prepare_tarifas_servicios,
    prepare_ventas_servicios,
    prepare_productos,
    prepare_ventas_productos,
    prepare_compras_productos,
    prepare_inventario_productos,
    prepare_gastos,
    prepare_comisiones_barberos,
    replace_nan_with_none,
)

import os


def prepare_datasets():
    """
    Devuelve todos los datasets en orden
    de dependencia referencial.
    """

    return [
        ("barberos", prepare_barberos()),
        ("clientes", prepare_clientes()),
        ("servicios", prepare_servicios()),
        ("productos", prepare_productos()),
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
        ("gastos", prepare_gastos()),
    ]


def upsert_dataframe(
    connection,
    schema,
    table_name,
    dataframe,
):
    """
    Ejecuta INSERT ... ON CONFLICT DO UPDATE
    utilizando la Primary Key real de PostgreSQL.
    """

    dataframe = replace_nan_with_none(
        dataframe
    )

    metadata = MetaData()

    table = Table(
        table_name,
        metadata,
        schema=schema,
        autoload_with=connection,
    )

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
            "columnas que no existen en PostgreSQL: "
            f"{sorted(extra_columns)}"
        )

    records = dataframe.to_dict(
        orient="records"
    )

    if not records:
        return 0

    primary_keys = [
        column.name
        for column in table.primary_key.columns
    ]

    if not primary_keys:
        raise ValueError(
            f"La tabla '{table_name}' "
            "no tiene Primary Key."
        )

    statement = pg_insert(
        table
    ).values(
        records
    )

    update_columns = {
        column: statement.excluded[column]
        for column in dataframe.columns
        if column not in primary_keys
    }

    if update_columns:
        statement = (
            statement.on_conflict_do_update(
                index_elements=[
                    table.c[column]
                    for column in primary_keys
                ],
                set_=update_columns,
            )
        )

    else:
        statement = (
            statement.on_conflict_do_nothing(
                index_elements=[
                    table.c[column]
                    for column in primary_keys
                ]
            )
        )

    connection.execute(
        statement
    )

    return len(records)


def load_incremental_data():
    """
    Carga los datasets mediante UPSERT.

    - IDs nuevos -> INSERT
    - IDs existentes -> UPDATE
    - No realiza TRUNCATE
    - No genera duplicados por Primary Key
    """

    print()
    print(
        "Iniciando carga incremental "
        "a PostgreSQL..."
    )
    print()

    engine = create_db_engine()

    schema = os.getenv(
        "DB_SCHEMA",
        "jstyles",
    )

    datasets = prepare_datasets()

    total_processed = 0

    try:
        with engine.begin() as connection:

            for table_name, dataframe in datasets:

                processed = upsert_dataframe(
                    connection,
                    schema,
                    table_name,
                    dataframe,
                )

                total_processed += processed

                print(
                    f"[OK] {table_name:<24} "
                    f"{processed:>5} filas procesadas"
                )

        print()
        print(
            "Carga incremental completada "
            "correctamente."
        )

        print(
            f"Filas procesadas: "
            f"{total_processed}"
        )

        return total_processed

    finally:
        engine.dispose()


if __name__ == "__main__":
    load_incremental_data()