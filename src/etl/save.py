from pathlib import Path

from extract import extract_data
from transform import transform_data


# =========================================================
# CONFIGURACIÓN
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# =========================================================
# SAVE
# =========================================================

def save_processed_data():
    """
    Ejecuta Extract + Transform y guarda las tablas
    procesadas y validadas hasta el momento.
    """

    # Crear data/processed si no existe
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("Generando datasets procesados...")
    print()

    # -----------------------------------------------------
    # 1. EXTRAER
    # -----------------------------------------------------

    raw_data = extract_data()

    # -----------------------------------------------------
    # 2. TRANSFORMAR
    # -----------------------------------------------------

    transformed_data = transform_data(raw_data)

    # =====================================================
    # VENTAS DE SERVICIOS
    # =====================================================

    ventas = transformed_data["ventas"].copy()

    # Esta columna pertenece al modelo histórico de Sheets
    # y no la necesitamos en el dataset procesado.
    if "cliente_ocasional_legacy" in ventas.columns:
        ventas = ventas.drop(
            columns=["cliente_ocasional_legacy"]
        )

    ventas_file = PROCESSED_DIR / "ventas.csv"

    ventas.to_csv(
        ventas_file,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    print(
        f"[OK] ventas.csv "
        f"| {len(ventas)} filas "
        f"| {len(ventas.columns)} columnas"
    )

    # =====================================================
    # BARBEROS
    # =====================================================

    barberos = transformed_data["barberos"].copy()

    barberos_file = PROCESSED_DIR / "barberos.csv"

    barberos.to_csv(
        barberos_file,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"[OK] barberos.csv "
        f"| {len(barberos)} filas "
        f"| {len(barberos.columns)} columnas"
    )

    # =====================================================
    # CLIENTES
    # =====================================================

    clientes = transformed_data["Clientes"].copy()

    clientes_file = PROCESSED_DIR / "clientes.csv"

    clientes.to_csv(
        clientes_file,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    print(
        f"[OK] clientes.csv "
        f"| {len(clientes)} filas "
        f"| {len(clientes.columns)} columnas"
    )

    # =====================================================
    # CATÁLOGO DE SERVICIOS
    # =====================================================

    catalogo_servicios = transformed_data[
        "catalogo_servicios"
    ].copy()

    catalogo_servicios_file = (
        PROCESSED_DIR / "catalogo_servicios.csv"
    )

    catalogo_servicios.to_csv(
        catalogo_servicios_file,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"[OK] catalogo_servicios.csv "
        f"| {len(catalogo_servicios)} filas "
        f"| {len(catalogo_servicios.columns)} columnas"
    )

    # =====================================================
    # TARIFAS DE SERVICIOS
    # =====================================================

    tarifas_servicios = transformed_data[
        "tarifas_servicios"
    ].copy()

    tarifas_servicios_file = (
        PROCESSED_DIR / "tarifas_servicios.csv"
    )

    tarifas_servicios.to_csv(
        tarifas_servicios_file,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    print(
        f"[OK] tarifas_servicios.csv "
        f"| {len(tarifas_servicios)} filas "
        f"| {len(tarifas_servicios.columns)} columnas"
    )

    # =====================================================
    # CATÁLOGO DE PRODUCTOS
    # =====================================================

    catalogo_productos = transformed_data[
        "catalogo_productos"
    ].copy()

    catalogo_productos_file = (
        PROCESSED_DIR / "catalogo_productos.csv"
    )

    catalogo_productos.to_csv(
        catalogo_productos_file,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"[OK] catalogo_productos.csv "
        f"| {len(catalogo_productos)} filas "
        f"| {len(catalogo_productos.columns)} columnas"
    )

    # =====================================================
    # VENTAS DE PRODUCTOS
    # =====================================================

    productos_ventas = transformed_data[
        "productos_ventas"
    ].copy()

    productos_ventas_file = (
        PROCESSED_DIR / "productos_ventas.csv"
    )

    productos_ventas.to_csv(
        productos_ventas_file,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    print(
        f"[OK] productos_ventas.csv "
        f"| {len(productos_ventas)} filas "
        f"| {len(productos_ventas.columns)} columnas"
    )

    # =====================================================
    # COMPRAS MAYORISTAS
    # =====================================================

    compras_mayorista = transformed_data[
        "compras_mayorista"
    ].copy()

    compras_mayorista_file = (
        PROCESSED_DIR / "compras_mayorista.csv"
    )

    compras_mayorista.to_csv(
        compras_mayorista_file,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    print(
        f"[OK] compras_mayorista.csv "
        f"| {len(compras_mayorista)} filas "
        f"| {len(compras_mayorista.columns)} columnas"
    )

    # =====================================================
    # INVENTARIO DE PRODUCTOS
    # =====================================================

    inventario_productos = transformed_data[
        "inventario_productos"
    ].copy()

    inventario_productos_file = (
        PROCESSED_DIR / "inventario_productos.csv"
    )

    inventario_productos.to_csv(
        inventario_productos_file,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"[OK] inventario_productos.csv "
        f"| {len(inventario_productos)} filas "
        f"| {len(inventario_productos.columns)} columnas"
    )
    
    # =====================================================
    # GASTOS
    # =====================================================

    gastos = transformed_data["gastos"].copy()

    gastos_file = PROCESSED_DIR / "gastos.csv"

    gastos.to_csv(
        gastos_file,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    print(
        f"[OK] gastos.csv "
        f"| {len(gastos)} filas "
        f"| {len(gastos.columns)} columnas"
    )
    
        # =====================================================
    # COMISIONES DE BARBEROS
    # =====================================================

    comisiones_barberos = transformed_data[
        "comisiones_barberos"
    ].copy()

    comisiones_barberos_file = (
        PROCESSED_DIR / "comisiones_barberos.csv"
    )

    comisiones_barberos.to_csv(
        comisiones_barberos_file,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    print(
        f"[OK] comisiones_barberos.csv "
        f"| {len(comisiones_barberos)} filas "
        f"| {len(comisiones_barberos.columns)} columnas"
    )
    

    # =====================================================
    # FIN
    # =====================================================

    print()
    print(
        f"Archivos generados en: {PROCESSED_DIR}"
    )


# =========================================================
# EJECUCIÓN
# =========================================================

if __name__ == "__main__":
    save_processed_data()