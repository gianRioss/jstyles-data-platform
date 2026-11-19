from pathlib import Path

import pandas as pd

from extract import extract_data
from transform import transform_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "data_quality"
)


# =========================================================
# UTILIDADES
# =========================================================

def get_table(data, *names):
    """
    Devuelve una tabla buscando distintos nombres posibles.
    """

    for name in names:
        if name in data:
            return data[name]

    raise KeyError(
        f"No se encontró ninguna tabla entre: {names}"
    )


def add_result(
    results,
    table,
    check,
    failed_rows,
    severity="error",
    detail="",
):
    """
    Agrega el resultado de un control de calidad.
    """

    if failed_rows == 0:
        status = "PASS"

    elif severity == "warning":
        status = "WARN"

    else:
        status = "FAIL"

    results.append(
        {
            "table": table,
            "check": check,
            "status": status,
            "severity": severity.upper(),
            "failed_rows": int(failed_rows),
            "detail": detail,
        }
    )


def check_primary_key(
    results,
    dataframe,
    table,
    column,
):
    """
    Valida que una clave no sea nula ni duplicada.
    """

    invalid = (
        dataframe[column].isna()
        | dataframe[column].duplicated(
            keep=False
        )
    )

    add_result(
        results,
        table,
        f"{column}_unique_not_null",
        invalid.sum(),
        detail=(
            f"{column} debe identificar "
            "unívocamente cada registro."
        ),
    )


def check_foreign_key(
    results,
    source,
    source_table,
    source_column,
    target,
    target_column,
):
    """
    Valida integridad referencial.
    Los NULL de la FK están permitidos.
    """

    source_values = source[
        source_column
    ]

    target_values = set(
        target[target_column]
        .dropna()
        .tolist()
    )

    invalid = (
        source_values.notna()
        & ~source_values.isin(
            target_values
        )
    )

    add_result(
        results,
        source_table,
        (
            f"{source_column}_fk_"
            f"{target_column}"
        ),
        invalid.sum(),
        detail=(
            f"{source_column} debe existir en "
            f"{target_column}."
        ),
    )


def check_condition(
    results,
    dataframe,
    table,
    check,
    condition,
    severity="error",
    detail="",
):
    """
    Valida una condición booleana por fila.
    """

    valid = (
        condition
        .fillna(False)
        .astype(bool)
    )

    failed = (~valid).sum()

    add_result(
        results,
        table,
        check,
        failed,
        severity=severity,
        detail=detail,
    )


# =========================================================
# QUALITY CHECKS
# =========================================================

def run_quality_checks(data):
    """
    Ejecuta controles de calidad sobre las tablas
    ya transformadas.
    """

    results = []

    barberos = get_table(
        data,
        "barberos",
    )

    ventas = get_table(
        data,
        "ventas",
    )

    clientes = get_table(
        data,
        "Clientes",
        "clientes",
    )

    servicios = get_table(
        data,
        "catalogo_servicios",
    )

    tarifas = get_table(
        data,
        "tarifas_servicios",
    )

    productos = get_table(
        data,
        "catalogo_productos",
    )

    ventas_productos = get_table(
        data,
        "productos_ventas",
    )

    compras = get_table(
        data,
        "compras_mayorista",
    )

    inventario = get_table(
        data,
        "inventario_productos",
    )

    gastos = get_table(
        data,
        "gastos",
    )

    comisiones = get_table(
        data,
        "comisiones_barberos",
    )

    # =====================================================
    # PRIMARY KEYS
    # =====================================================

    primary_keys = [
        (
            barberos,
            "barberos",
            "barbero_id",
        ),
        (
            ventas,
            "ventas",
            "ticket_id",
        ),
        (
            clientes,
            "clientes",
            "cliente_id",
        ),
        (
            servicios,
            "catalogo_servicios",
            "servicio_id",
        ),
        (
            tarifas,
            "tarifas_servicios",
            "tarifa_id",
        ),
        (
            productos,
            "catalogo_productos",
            "producto_id",
        ),
        (
            ventas_productos,
            "productos_ventas",
            "venta_producto_id",
        ),
        (
            compras,
            "compras_mayorista",
            "compra_id",
        ),
        (
            gastos,
            "gastos",
            "gasto_id",
        ),
        (
            comisiones,
            "comisiones_barberos",
            "comision_config_id",
        ),
    ]

    for dataframe, table, column in primary_keys:
        check_primary_key(
            results,
            dataframe,
            table,
            column,
        )

    # =====================================================
    # FOREIGN KEYS
    # =====================================================

    check_foreign_key(
        results,
        ventas,
        "ventas",
        "barbero_id",
        barberos,
        "barbero_id",
    )

    check_foreign_key(
        results,
        ventas,
        "ventas",
        "servicio_id",
        servicios,
        "servicio_id",
    )

    check_foreign_key(
        results,
        ventas,
        "ventas",
        "cliente_id",
        clientes,
        "cliente_id",
    )

    check_foreign_key(
        results,
        tarifas,
        "tarifas_servicios",
        "servicio_id",
        servicios,
        "servicio_id",
    )

    check_foreign_key(
        results,
        ventas_productos,
        "productos_ventas",
        "producto_id",
        productos,
        "producto_id",
    )

    check_foreign_key(
        results,
        compras,
        "compras_mayorista",
        "producto_id",
        productos,
        "producto_id",
    )

    check_foreign_key(
        results,
        inventario,
        "inventario_productos",
        "producto_id",
        productos,
        "producto_id",
    )

    check_foreign_key(
        results,
        comisiones,
        "comisiones_barberos",
        "barbero_id",
        barberos,
        "barbero_id",
    )

    # =====================================================
    # VENTAS DE SERVICIOS
    # =====================================================

    check_condition(
        results,
        ventas,
        "ventas",
        "precio_non_negative",
        ventas["precio"] >= 0,
    )

    check_condition(
        results,
        ventas,
        "ventas",
        "propina_non_negative",
        ventas["propina"] >= 0,
    )

    check_condition(
        results,
        ventas,
        "ventas",
        "descuento_between_0_and_1",
        ventas["descuento"].between(
            0,
            1,
        ),
    )

    check_condition(
        results,
        ventas,
        "ventas",
        "total_cobrado_non_negative",
        ventas["total_cobrado"] >= 0,
    )

    check_condition(
        results,
        ventas,
        "ventas",
        "comision_non_negative",
        ventas["comision"] >= 0,
    )

    # =====================================================
    # TARIFAS
    # =====================================================

    check_condition(
        results,
        tarifas,
        "tarifas_servicios",
        "precio_positive",
        tarifas["precio"] > 0,
    )

    fechas_tarifa_validas = (
        tarifas["fecha_hasta"].isna()
        | (
            tarifas["fecha_hasta"]
            >= tarifas["fecha_desde"]
        )
    )

    check_condition(
        results,
        tarifas,
        "tarifas_servicios",
        "fecha_hasta_after_fecha_desde",
        fechas_tarifa_validas,
    )

    # =====================================================
    # PRODUCTOS
    # =====================================================

    check_condition(
        results,
        ventas_productos,
        "productos_ventas",
        "cantidad_positive",
        ventas_productos["cantidad"] > 0,
    )

    check_condition(
        results,
        compras,
        "compras_mayorista",
        "cantidad_positive",
        compras["cantidad"] > 0,
    )

    check_condition(
        results,
        compras,
        "compras_mayorista",
        "costo_unitario_non_negative",
        compras["costo_unitario"] >= 0,
    )

    # =====================================================
    # GASTOS
    # =====================================================

    check_condition(
        results,
        gastos,
        "gastos",
        "monto_positive",
        gastos["monto"] > 0,
    )

    check_condition(
        results,
        gastos,
        "gastos",
        "tipo_gasto_valid",
        gastos["tipo_gasto"].isin(
            [
                "comercial",
                "personal",
            ]
        ),
    )

    # =====================================================
    # COMISIONES
    # =====================================================

    check_condition(
        results,
        comisiones,
        "comisiones_barberos",
        "porcentaje_barbero_valid",
        comisiones[
            "porcentaje_barbero"
        ].between(
            0,
            1,
        ),
    )

    check_condition(
        results,
        comisiones,
        "comisiones_barberos",
        "porcentaje_local_valid",
        comisiones[
            "porcentaje_local"
        ].between(
            0,
            1,
        ),
    )

    suma_comisiones = (
        comisiones["porcentaje_barbero"]
        + comisiones["porcentaje_local"]
    )

    check_condition(
        results,
        comisiones,
        "comisiones_barberos",
        "porcentajes_sum_100_percent",
        suma_comisiones.round(4).eq(1.0),
    )

    actuales = comisiones.loc[
        comisiones[
            "es_configuracion_actual"
        ].eq(True)
    ]

    duplicados_actuales = (
        actuales["barbero_id"]
        .duplicated(
            keep=False
        )
        .sum()
    )

    add_result(
        results,
        "comisiones_barberos",
        "one_current_configuration_per_barber",
        duplicados_actuales,
        detail=(
            "Un barbero no puede tener más de "
            "una configuración actual."
        ),
    )

    barberos_sin_config_actual = (
        set(barberos["barbero_id"])
        - set(actuales["barbero_id"])
    )

    add_result(
        results,
        "comisiones_barberos",
        "all_barbers_have_current_configuration",
        len(barberos_sin_config_actual),
        detail=(
            "Cada barbero debe tener una "
            "configuración actual."
        ),
    )

    # =====================================================
    # WARNINGS / ANOMALÍAS CONOCIDAS
    # =====================================================

    if "fecha_invalida" in ventas_productos.columns:
        add_result(
            results,
            "productos_ventas",
            "invalid_dates_detected",
            ventas_productos[
                "fecha_invalida"
            ].fillna(False).sum(),
            severity="warning",
            detail=(
                "Una fecha inválida no elimina "
                "automáticamente la transacción."
            ),
        )

    if "requiere_revision" in productos.columns:
        add_result(
            results,
            "catalogo_productos",
            "products_requiring_review",
            productos[
                "requiere_revision"
            ].fillna(False).sum(),
            severity="warning",
            detail=(
                "Productos conservados que requieren "
                "revisión manual de correspondencia."
            ),
        )

    if "precio_conflicto" in inventario.columns:
        add_result(
            results,
            "inventario_productos",
            "price_conflicts_detected",
            inventario[
                "precio_conflicto"
            ].fillna(False).sum(),
            severity="warning",
            detail=(
                "Productos con más de un precio "
                "observado en la fuente."
            ),
        )

    return pd.DataFrame(results)


# =========================================================
# REPORTE
# =========================================================

def save_quality_report(report):
    """
    Guarda los resultados de calidad.
    """

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        REPORT_DIR
        / "quality_checks.csv"
    )

    report.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    return output_file


# =========================================================
# EJECUCIÓN
# =========================================================

def main():
    print()
    print("Ejecutando controles de calidad...")
    print()

    raw_data = extract_data()

    transformed_data = transform_data(
        raw_data
    )

    report = run_quality_checks(
        transformed_data
    )

    output_file = save_quality_report(
        report
    )

    print()
    print(report.to_string(index=False))
    print()

    passes = (
        report["status"]
        .eq("PASS")
        .sum()
    )

    warnings = (
        report["status"]
        .eq("WARN")
        .sum()
    )

    failures = (
        report["status"]
        .eq("FAIL")
        .sum()
    )

    print(
        f"PASS: {passes} | "
        f"WARN: {warnings} | "
        f"FAIL: {failures}"
    )

    print(
        f"Reporte: {output_file}"
    )

    if failures > 0:
        raise SystemExit(
            "Fallaron controles críticos "
            "de calidad."
        )


if __name__ == "__main__":
    main()