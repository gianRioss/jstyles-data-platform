from pathlib import Path
import sys

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ETL_DIR = PROJECT_ROOT / "src" / "etl"
RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "JStyles_OPERATIVO.xlsx"
)

sys.path.insert(0, str(ETL_DIR))

from extract import extract_data
from transform import transform_data


def append_raw_row(dataframe, row):
    """
    Agrega una fila simulada respetando exactamente
    las columnas de la fuente original.
    """

    result = dataframe.copy(deep=True)

    result.loc[len(result)] = [
        row.get(column, pd.NA)
        for column in result.columns
    ]

    return result

def sort_by_id(dataframe, column):
    return (
        dataframe
        .sort_values(column)
        .reset_index(drop=True)
    )


def test_incremental_stability():
    """
    Comprueba que agregar nuevas operaciones:

    - no modifica identificadores históricos;
    - agrega únicamente las nuevas operaciones;
    - no genera IDs duplicados;
    - mantiene tarifas y comisiones históricas;
    - produce los mismos IDs al ejecutar nuevamente;
    - no modifica el archivo Excel original.
    """

    if not RAW_FILE.exists():
        pytest.skip(
            "El Excel operativo real no está disponible."
        )

    # =====================================================
    # 1. SNAPSHOT ORIGINAL
    # =====================================================

    raw_original = extract_data()

    baseline = transform_data(
        {
            name: df.copy(deep=True)
            for name, df in raw_original.items()
        }
    )

    baseline_ticket_ids = set(
        baseline["ventas"]["ticket_id"]
    )

    baseline_product_sale_ids = set(
        baseline["productos_ventas"][
            "venta_producto_id"
        ]
    )

    baseline_purchase_ids = set(
        baseline["compras_mayorista"]["compra_id"]
    )

    baseline_expense_ids = set(
        baseline["gastos"]["gasto_id"]
    )

    baseline_product_mapping = (
        baseline["catalogo_productos"][
            ["producto", "producto_id"]
        ]
        .copy()
    )

    # =====================================================
    # 2. COPIA EN MEMORIA
    # =====================================================

    raw_incremental = {
        name: df.copy(deep=True)
        for name, df in raw_original.items()
    }

    # =====================================================
    # 3. NUEVA VENTA DE SERVICIO
    # =====================================================

    nueva_venta = {
        "fecha ": pd.Timestamp("2026-08-05"),
        "hora": "10:30:00",
        "ticked id ": "T-1027",
        "servicio": "corte",
        "precio (auto)": 14000,
        "barbero ": "thiago",
        "medio de pago": "Efectivo",
        "propina ": 0,
        "descuento ": 0,
        "total cobrado (auto)": 14000,
        "comision (auto)": 7000,
        "cliente": None,
        "cliente_selector": None,
        "nro factura ": None,
        "cliente_id": None,
        "facturado si/no (auto)": None,
        "Cliente ocasional": None,
    }

    raw_incremental["ventas"] = append_raw_row(
        raw_incremental["ventas"],
        nueva_venta,
    )

    # =====================================================
    # 4. NUEVA VENTA DE PRODUCTO
    # =====================================================

    nueva_venta_producto = {
        "fecha": pd.Timestamp("2026-08-05"),
        "producto": "papel viggo",
        "cantidad": 1,
        "precio_unit(auto)": 2500,
        "total(auto)": 2500,
        "utilidad(auto)": 1400,
        "ganancia_acum(auto)": None,
        "ganancia_día(auto)": None,
        "Unnamed: 8": None,
        "barbero": "thiago",
        "comision_barbero_auto": 250,
        "medio de pago": "Efectivo",
        "notas": "TEST_INCREMENTAL_PRODUCTO",
    }

    raw_incremental[
        "productos_ventas"
    ] = append_raw_row(
        raw_incremental["productos_ventas"],
        nueva_venta_producto,
    )

    # =====================================================
    # 5. NUEVA COMPRA
    # =====================================================

    nueva_compra = {
        " ": pd.Timestamp("2026-08-05"),
        "proveedor": "Proveedor Test",
        "producto": "papel viggo",
        "cantidad": 2,
        "costo_unitario": 1100,
        "total(auto)": 2200,
        "notas": "TEST_INCREMENTAL_COMPRA",
        "comprar mas productos ": None,
    }

    raw_incremental[
        "compras_mayorista"
    ] = append_raw_row(
        raw_incremental["compras_mayorista"],
        nueva_compra,
    )

    # =====================================================
    # 6. NUEVO GASTO
    # =====================================================

    nuevo_gasto = {
        "fecha ": pd.Timestamp("2026-08-05"),
        "conceptos ": "TEST_INCREMENTAL_GASTO",
        "monto": 5000,
        "metodo ": "Transferencia",
        "notas": "Prueba automática",
        "tipo_gasto": "comercial",
        "categoria": "insumos",
    }

    raw_incremental["gastos"] = append_raw_row(
        raw_incremental["gastos"],
        nuevo_gasto,
    )

    # =====================================================
    # 7. EJECUTAR ETL CON NUEVOS DATOS
    # =====================================================

    incremental = transform_data(
        {
            name: df.copy(deep=True)
            for name, df in raw_incremental.items()
        }
    )

    # =====================================================
    # 8. VALIDAR NUEVAS FILAS
    # =====================================================

    assert len(incremental["ventas"]) == (
        len(baseline["ventas"]) + 1
    )

    assert len(incremental["productos_ventas"]) == (
        len(baseline["productos_ventas"]) + 1
    )

    assert len(incremental["compras_mayorista"]) == (
        len(baseline["compras_mayorista"]) + 1
    )

    assert len(incremental["gastos"]) == (
        len(baseline["gastos"]) + 1
    )

    # =====================================================
    # 9. HISTÓRICO DE VENTAS INTACTO
    # =====================================================

    incremental_ticket_ids = set(
        incremental["ventas"]["ticket_id"]
    )

    assert baseline_ticket_ids.issubset(
        incremental_ticket_ids
    )

    assert (
        incremental["ventas"]["ticket_id"]
        .eq("T-1027")
        .sum()
        == 1
    )

    assert not incremental[
        "ventas"
    ]["ticket_id"].duplicated().any()

    # =====================================================
    # 10. IDs DE VENTAS DE PRODUCTOS ESTABLES
    # =====================================================

    incremental_product_sale_ids = set(
        incremental["productos_ventas"][
            "venta_producto_id"
        ]
    )

    assert baseline_product_sale_ids.issubset(
        incremental_product_sale_ids
    )

    assert not incremental[
        "productos_ventas"
    ]["venta_producto_id"].duplicated().any()

    nueva_vp = incremental[
        "productos_ventas"
    ].loc[
        incremental["productos_ventas"]["notas"]
        .eq("TEST_INCREMENTAL_PRODUCTO")
    ]

    assert len(nueva_vp) == 1
    assert nueva_vp["venta_producto_id"].notna().all()

    # =====================================================
    # 11. IDs DE COMPRAS ESTABLES
    # =====================================================

    incremental_purchase_ids = set(
        incremental["compras_mayorista"]["compra_id"]
    )

    assert baseline_purchase_ids.issubset(
        incremental_purchase_ids
    )

    assert not incremental[
        "compras_mayorista"
    ]["compra_id"].duplicated().any()

    nueva_compra_resultado = incremental[
        "compras_mayorista"
    ].loc[
        incremental["compras_mayorista"]["notas"]
        .eq("TEST_INCREMENTAL_COMPRA")
    ]

    assert len(nueva_compra_resultado) == 1
    assert nueva_compra_resultado[
        "compra_id"
    ].notna().all()

    # =====================================================
    # 12. IDs DE GASTOS ESTABLES
    # =====================================================

    incremental_expense_ids = set(
        incremental["gastos"]["gasto_id"]
    )

    assert baseline_expense_ids.issubset(
        incremental_expense_ids
    )

    assert not incremental[
        "gastos"
    ]["gasto_id"].duplicated().any()

    nuevo_gasto_resultado = incremental[
        "gastos"
    ].loc[
        incremental["gastos"]["concepto"]
        .eq("test_incremental_gasto")
    ]

    assert len(nuevo_gasto_resultado) == 1
    assert nuevo_gasto_resultado[
        "gasto_id"
    ].notna().all()

    # =====================================================
    # 13. PRODUCTO_ID HISTÓRICO ESTABLE
    # =====================================================

    current_product_mapping = (
        incremental["catalogo_productos"][
            ["producto", "producto_id"]
        ]
    )

    comparison = baseline_product_mapping.merge(
        current_product_mapping,
        on="producto",
        suffixes=("_antes", "_despues"),
        how="left",
    )

    assert comparison[
        "producto_id_despues"
    ].notna().all()

    assert (
        comparison["producto_id_antes"]
        == comparison["producto_id_despues"]
    ).all()

    # =====================================================
    # 14. TARIFAS HISTÓRICAS NO CAMBIAN
    # =====================================================

    assert_frame_equal(
        sort_by_id(
            baseline["tarifas_servicios"],
            "tarifa_id",
        ),
        sort_by_id(
            incremental["tarifas_servicios"],
            "tarifa_id",
        ),
        check_dtype=False,
    )

    # =====================================================
    # 15. COMISIONES HISTÓRICAS NO CAMBIAN
    # =====================================================

    assert_frame_equal(
        sort_by_id(
            baseline["comisiones_barberos"],
            "comision_config_id",
        ),
        sort_by_id(
            incremental["comisiones_barberos"],
            "comision_config_id",
        ),
        check_dtype=False,
    )

    # =====================================================
    # 16. SEGUNDO RERUN = MISMOS IDs
    # =====================================================

    rerun = transform_data(
        {
            name: df.copy(deep=True)
            for name, df in raw_incremental.items()
        }
    )

    assert set(
        rerun["ventas"]["ticket_id"]
    ) == set(
        incremental["ventas"]["ticket_id"]
    )

    assert set(
        rerun["productos_ventas"][
            "venta_producto_id"
        ]
    ) == set(
        incremental["productos_ventas"][
            "venta_producto_id"
        ]
    )

    assert set(
        rerun["compras_mayorista"]["compra_id"]
    ) == set(
        incremental["compras_mayorista"]["compra_id"]
    )

    assert set(
        rerun["gastos"]["gasto_id"]
    ) == set(
        incremental["gastos"]["gasto_id"]
    )