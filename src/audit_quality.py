from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import warnings
from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = PROJECT_ROOT / "data" / "raw" / "JStyles_OPERATIVO.xlsx"
REPORT_DIR = PROJECT_ROOT / "reports" / "auditoria_calidad"


def normalizar_nombre(valor: Any) -> str:
    texto = "" if valor is None else str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", texto.lower()).strip("_")


def leer_hoja(nombre: str) -> pd.DataFrame:
    # openpyxl puede advertir sobre fechas corruptas y convertirlas a NaT.
    # Suprimimos aquí la advertencia porque la auditamos explícitamente más abajo.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        df = pd.read_excel(WORKBOOK_PATH, sheet_name=nombre, engine="openpyxl")
    df.columns = [normalizar_nombre(col) for col in df.columns]
    return df


def errores_excel_en_fecha(nombre_hoja: str) -> pd.DataFrame:
    """
    Detecta errores de Excel en la columna A (fecha), por ejemplo una celda
    formateada como fecha cuyo serial está fuera del rango permitido.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        wb = load_workbook(WORKBOOK_PATH, data_only=False, read_only=False)

    ws = wb[nombre_hoja]
    registros = []

    for cell in ws["A"][1:]:  # omite encabezado A1
        if cell.data_type == "e":
            registros.append(
                {
                    "fila_excel": cell.row,
                    "celda": cell.coordinate,
                    "error_excel": cell.value,
                    "producto_o_servicio": ws.cell(cell.row, 2).value,
                    "cantidad": ws.cell(cell.row, 3).value if nombre_hoja == "productos_ventas" else None,
                }
            )

    wb.close()
    return pd.DataFrame(registros)


def columna(df: pd.DataFrame, *candidatas: str) -> str | None:
    for candidata in candidatas:
        candidata = normalizar_nombre(candidata)
        if candidata in df.columns:
            return candidata
    return None


def tiene_valor(serie: pd.Series) -> pd.Series:
    return serie.notna() & serie.astype(str).str.strip().ne("")


def parsear_fecha_segura(valor: Any) -> pd.Timestamp:
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (pd.Timestamp, datetime)):
        return pd.Timestamp(valor)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        numero = float(valor)
        if 1 <= numero <= 60000:
            return pd.Timestamp("1899-12-30") + pd.to_timedelta(numero, unit="D")
        return pd.NaT
    return pd.to_datetime(str(valor).strip(), dayfirst=True, errors="coerce")


def auditar_ventas() -> dict[str, Any]:
    df = leer_hoja("ventas")

    c_ticket = columna(df, "ticket_id", "ticket")
    c_fecha = columna(df, "fecha")
    c_servicio = columna(df, "servicio")
    c_medio = columna(df, "medio_de_pago", "medio de pago")
    c_total = columna(df, "total_cobrado_auto", "total_cobrado", "total cobrado (auto)")
    c_cliente_id = columna(df, "cliente_id")

    if c_ticket:
        reales = df[tiene_valor(df[c_ticket])].copy()
    else:
        mascara = pd.Series(False, index=df.index)
        if c_fecha:
            mascara |= tiene_valor(df[c_fecha])
        if c_servicio:
            mascara |= tiene_valor(df[c_servicio])
        reales = df[mascara].copy()

    reales["fila_excel"] = reales.index + 2

    duplicados_ticket = pd.DataFrame()
    if c_ticket:
        duplicados_ticket = reales[
            tiene_valor(reales[c_ticket]) & reales[c_ticket].duplicated(keep=False)
        ].copy()

    fechas_invalidas = pd.DataFrame()
    fechas_sospechosas = pd.DataFrame()
    if c_fecha:
        reales["_fecha_parseada"] = reales[c_fecha].apply(parsear_fecha_segura)
        fechas_invalidas = reales[
            tiene_valor(reales[c_fecha]) & reales["_fecha_parseada"].isna()
        ].copy()

        hoy = pd.Timestamp.today().normalize()
        fechas_sospechosas = reales[
            reales["_fecha_parseada"].notna()
            & (
                (reales["_fecha_parseada"] < pd.Timestamp("2025-01-01"))
                | (reales["_fecha_parseada"] > hoy + pd.Timedelta(days=2))
            )
        ].copy()

    medios = []
    if c_medio:
        medios = sorted(
            reales.loc[tiene_valor(reales[c_medio]), c_medio]
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

    servicios = []
    if c_servicio:
        servicios = sorted(
            reales.loc[tiene_valor(reales[c_servicio]), c_servicio]
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

    total_nulo = int(reales[c_total].isna().sum()) if c_total else 0
    clientes_identificados = int(tiene_valor(reales[c_cliente_id]).sum()) if c_cliente_id else 0

    errores_excel_fecha = errores_excel_en_fecha("ventas")

    return {
        "cantidad_real": len(reales),
        "duplicados_ticket": duplicados_ticket,
        "fechas_invalidas": fechas_invalidas,
        "errores_excel_fecha": errores_excel_fecha,
        "fechas_sospechosas": fechas_sospechosas,
        "medios_pago": medios,
        "servicios_historicos": servicios,
        "totales_nulos": total_nulo,
        "clientes_identificados": clientes_identificados,
    }


def auditar_productos_ventas() -> dict[str, Any]:
    df = leer_hoja("productos_ventas")

    c_fecha = columna(df, "fecha")
    c_producto = columna(df, "producto")
    c_cantidad = columna(df, "cantidad")
    c_precio = columna(df, "precio_unitario_auto", "precio_unitario")
    c_total = columna(df, "total_auto", "total")
    c_utilidad = columna(df, "utilidad_auto", "utilidad")
    c_vendedor = columna(df, "barbero", "vendedor")
    c_comision = columna(df, "comision_barbero_auto")

    # Una venta real de producto puede seguir siendo una transacción aunque
    # la fecha esté corrupta. Por eso la identificamos principalmente por producto
    # y cantidad/importe, no por exigir una fecha válida.
    mascara = pd.Series(True, index=df.index)
    if c_producto:
        mascara &= tiene_valor(df[c_producto])

    if c_cantidad:
        cantidad_num = pd.to_numeric(df[c_cantidad], errors="coerce")
        mascara &= cantidad_num.fillna(0).gt(0)

    reales = df[mascara].copy()
    reales["fila_excel"] = reales.index + 2

    fechas_invalidas = pd.DataFrame()
    if c_fecha:
        reales["_fecha_parseada"] = reales[c_fecha].apply(parsear_fecha_segura)
        fechas_invalidas = reales[
            tiene_valor(reales[c_fecha]) & reales["_fecha_parseada"].isna()
        ].copy()

    errores_excel_fecha = errores_excel_en_fecha("productos_ventas")

    subset = [
        col for col in [c_fecha, c_producto, c_cantidad, c_precio, c_total, c_vendedor]
        if col is not None
    ]
    posibles_duplicados = (
        reales[reales.duplicated(subset=subset, keep=False)].copy()
        if subset else pd.DataFrame()
    )

    cantidades_invalidas = pd.DataFrame()
    if c_cantidad:
        cantidad_num = pd.to_numeric(reales[c_cantidad], errors="coerce")
        cantidades_invalidas = reales[cantidad_num.isna() | (cantidad_num <= 0)].copy()

    utilidades_nulas = int(reales[c_utilidad].isna().sum()) if c_utilidad else 0

    vendedores_faltantes = pd.DataFrame()
    if c_vendedor:
        vendedores_faltantes = reales[
            (reales["fila_excel"] >= 587) & ~tiene_valor(reales[c_vendedor])
        ].copy()

    comisiones_inconsistentes = pd.DataFrame()
    if c_vendedor and c_comision and c_total:
        vendedor = reales[c_vendedor].astype(str).str.strip().str.lower()
        total = pd.to_numeric(reales[c_total], errors="coerce").fillna(0)
        comision = pd.to_numeric(reales[c_comision], errors="coerce").fillna(0)

        es_no_comisionista = vendedor.isin(["elias", "encargado", ""])
        esperado = total * 0.10

        mascara_inconsistente = (
            (reales["fila_excel"] >= 587)
            & (
                (es_no_comisionista & (comision != 0))
                | (
                    ~es_no_comisionista
                    & tiene_valor(reales[c_vendedor])
                    & ((comision - esperado).abs() > 0.01)
                )
            )
        )
        comisiones_inconsistentes = reales[mascara_inconsistente].copy()

    return {
        "cantidad_real": len(reales),
        "fechas_invalidas": fechas_invalidas,
        "errores_excel_fecha": errores_excel_fecha,
        "posibles_duplicados": posibles_duplicados,
        "cantidades_invalidas": cantidades_invalidas,
        "utilidades_nulas": utilidades_nulas,
        "vendedores_faltantes_desde_587": vendedores_faltantes,
        "comisiones_inconsistentes": comisiones_inconsistentes,
    }


def guardar_csv(df: pd.DataFrame, nombre: str) -> None:
    if df.empty:
        return
    df.drop(columns=[c for c in df.columns if c.startswith("_")], errors="ignore").to_csv(
        REPORT_DIR / nombre, index=False, encoding="utf-8-sig"
    )


def main() -> None:
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(f"No se encontró {WORKBOOK_PATH}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    ventas = auditar_ventas()
    productos = auditar_productos_ventas()

    guardar_csv(ventas["duplicados_ticket"], "ventas_tickets_duplicados.csv")
    guardar_csv(ventas["fechas_invalidas"], "ventas_fechas_invalidas.csv")
    guardar_csv(ventas["errores_excel_fecha"], "ventas_errores_excel_fecha.csv")
    guardar_csv(ventas["fechas_sospechosas"], "ventas_fechas_sospechosas.csv")
    guardar_csv(productos["fechas_invalidas"], "productos_fechas_invalidas.csv")
    guardar_csv(productos["errores_excel_fecha"], "productos_errores_excel_fecha.csv")
    guardar_csv(productos["posibles_duplicados"], "productos_posibles_duplicados.csv")
    guardar_csv(productos["cantidades_invalidas"], "productos_cantidades_invalidas.csv")
    guardar_csv(
        productos["vendedores_faltantes_desde_587"],
        "productos_vendedor_faltante_desde_587.csv",
    )
    guardar_csv(
        productos["comisiones_inconsistentes"],
        "productos_comisiones_inconsistentes.csv",
    )

    lineas = [
        "# Auditoría de calidad de datos de JStyles",
        "",
        "Esta auditoría diferencia filas preparadas con fórmulas de transacciones reales.",
        "No elimina ni modifica ningún dato del archivo `data/raw`.",
        "",
        "## Ventas de servicios",
        "",
        f"- Transacciones reales detectadas: **{ventas['cantidad_real']}**",
        f"- Tickets duplicados reales: **{len(ventas['duplicados_ticket'])} filas involucradas**",
        f"- Fechas inválidas parseables: **{len(ventas['fechas_invalidas'])}**",
        f"- Errores de Excel en celdas de fecha: **{len(ventas['errores_excel_fecha'])}**",
        f"- Fechas sospechosas (< 2025 o futuras): **{len(ventas['fechas_sospechosas'])}**",
        f"- Ventas con total nulo: **{ventas['totales_nulos']}**",
        f"- Ventas asociadas a cliente_id: **{ventas['clientes_identificados']}**",
        f"- Medios de pago encontrados: **{', '.join(ventas['medios_pago']) or 'Ninguno'}**",
        f"- Nombres históricos de servicios encontrados: **{len(ventas['servicios_historicos'])}**",
        "",
        "## Ventas de productos",
        "",
        f"- Transacciones reales detectadas: **{productos['cantidad_real']}**",
        f"- Fechas inválidas parseables: **{len(productos['fechas_invalidas'])}**",
        f"- Errores de Excel en celdas de fecha: **{len(productos['errores_excel_fecha'])}**",
        f"- Filas marcadas como posibles duplicados: **{len(productos['posibles_duplicados'])}**",
        f"- Cantidades inválidas: **{len(productos['cantidades_invalidas'])}**",
        f"- Ventas con utilidad nula: **{productos['utilidades_nulas']}**",
        f"- Ventas desde fila 587 sin vendedor: **{len(productos['vendedores_faltantes_desde_587'])}**",
        f"- Comisiones inconsistentes desde fila 587: **{len(productos['comisiones_inconsistentes'])}**",
        "",
        "## Interpretación",
        "",
        "- Un ticket repetido en `ventas` sí requiere revisión porque `ticket_id` debe identificar una venta.",
        "- En `productos_ventas`, sin un ID histórico, los duplicados son solo candidatos a revisión.",
        "- Las filas futuras preparadas con fórmulas no se consideran transacciones reales.",
        "- Las anomalías se exportan a CSV para revisarlas una por una.",
        "",
    ]

    (REPORT_DIR / "reporte_calidad_datos.md").write_text(
        "\n".join(lineas), encoding="utf-8"
    )

    print("Auditoría de calidad completada.")
    print(f"Reporte: {REPORT_DIR / 'reporte_calidad_datos.md'}")
    print(f"Transacciones reales de servicios: {ventas['cantidad_real']}")
    print(f"Transacciones reales de productos: {productos['cantidad_real']}")
    print(f"Tickets duplicados: {len(ventas['duplicados_ticket'])} filas involucradas")
    total_fechas_producto = (
        len(productos["fechas_invalidas"])
        + len(productos["errores_excel_fecha"])
    )
    print(f"Fechas inválidas en productos: {total_fechas_producto}")


if __name__ == "__main__":
    main()
