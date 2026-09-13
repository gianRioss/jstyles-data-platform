import hashlib
import re
import unicodedata

import pandas as pd
from extract import extract_data


# =========================================================
# MAPEO CANÓNICO DE SERVICIOS
# =========================================================

SERVICE_ALIAS_TO_ID = {
    # Corte
    "corte": "SER-001",
    "corte_new": "SER-001",
    "corte_new1": "SER-001",
    "corte promo": "SER-001",
    "corte_promo_j.s": "SER-001",
    "corte_promo_lm": "SER-001",

    # Barba
    "barba": "SER-002",
    "barba_new": "SER-002",

    # Corte + barba
    "corte+barba": "SER-003",
    "corte+barba_new": "SER-003",
    "corte+barba_new1": "SER-003",
    "corte+barba_promo_j.s": "SER-003",
    "corte+barba_promo_lm": "SER-003",

    # Jubilado
    "jubilado": "SER-004",
    "jubilados": "SER-004",
    "jubilados_new": "SER-004",
    "jubilados_new1": "SER-004",
    "jubilados_new2": "SER-004",

    # Servicios actuales
    "claritos": "SER-005",
    "global": "SER-006",

    # Servicios históricos especiales
    "corte_y_diseño": "SER-007",
    "color": "SER-008",
    "global nathan": "SER-009",
    "corte+color": "SER-010",
    "color agus": "SER-011",
    "banderita_nene": "SER-012",
}


# =========================================================
# FUNCIONES GENERALES
# =========================================================

def normalize_column_name(name: str) -> str:
    """
    Normaliza nombres de columnas.

    Ejemplo:
    'Medio de Pago' -> 'medio_de_pago'
    """

    text = str(name).strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    text = re.sub(r"[^a-z0-9]+", "_", text)

    return text.strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve una copia del DataFrame con nombres
    de columnas normalizados.
    """

    df = df.copy()

    df.columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    return df


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia espacios innecesarios en columnas de texto.
    """

    df = df.copy()

    for column in df.select_dtypes(include="object").columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    return df


# =========================================================
# VENTAS DE SERVICIOS
# =========================================================

def transform_ventas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y estandariza la tabla de ventas de servicios.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. NORMALIZAR NOMBRES DE COLUMNAS
    # -----------------------------------------------------

    df = df.rename(
        columns={
            "ticked_id": "ticket_id",
            "precio_auto": "precio",
            "total_cobrado_auto": "total_cobrado",
            "comision_auto": "comision",
            "facturado_si_no_auto": "facturado",
            "cliente_ocasional": "cliente_ocasional_legacy",
        }
    )

    # -----------------------------------------------------
    # 2. CONSERVAR SOLO TRANSACCIONES REALES
    # -----------------------------------------------------

    if "ticket_id" in df.columns:
        df = df[
            df["ticket_id"].notna()
            & df["ticket_id"].ne("")
        ].copy()

    # -----------------------------------------------------
    # 3. CONVERTIR FECHA
    # -----------------------------------------------------

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(
            df["fecha"],
            errors="coerce",
            dayfirst=True,
        )

    # -----------------------------------------------------
    # 4. CORRECCIÓN HISTÓRICA DOCUMENTADA
    # -----------------------------------------------------

    # En la fuente original:
    # T-0133 tiene fecha 2002-11-11.
    #
    # Secuencia verificada:
    # T-0132 -> 2025-11-11 14:00
    # T-0133 -> 15:00
    # T-0134 -> 2025-11-11 17:30
    #
    # Fecha correcta: 2025-11-11.

    if "ticket_id" in df.columns and "fecha" in df.columns:
        df.loc[
            df["ticket_id"].eq("T-0133"),
            "fecha",
        ] = pd.Timestamp("2025-11-11")

    # -----------------------------------------------------
    # 5. CONVERTIR COLUMNAS NUMÉRICAS
    # -----------------------------------------------------

    numeric_columns = [
        "precio",
        "propina",
        "descuento",
        "total_cobrado",
        "comision",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # -----------------------------------------------------
    # 6. NORMALIZAR VALORES CATEGÓRICOS
    # -----------------------------------------------------

    text_columns = [
        "servicio",
        "barbero",
        "medio_de_pago",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
                .str.lower()
            )

    # -----------------------------------------------------
    # 7. NORMALIZAR CLIENTE_ID
    # -----------------------------------------------------

    if "cliente_id" in df.columns:
        df["cliente_id"] = (
            df["cliente_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        # Los valores vacíos continúan siendo nulos.
        # No asignamos clientes históricos inventados.
        df["cliente_id"] = df["cliente_id"].replace(
            "",
            pd.NA,
        )

    # -----------------------------------------------------
    # 8. CONTROL DE TICKET_ID
    # -----------------------------------------------------

    if "ticket_id" in df.columns:
        duplicated = df["ticket_id"].duplicated().sum()

        if duplicated > 0:
            raise ValueError(
                f"Se encontraron {duplicated} ticket_id duplicados."
            )

    return df.reset_index(drop=True)


# =========================================================
# VENTAS DE PRODUCTOS
# =========================================================

def transform_productos_ventas(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Limpia y estandariza las ventas de productos.

    Se conservan únicamente los datos propios de cada
    transacción. Los acumulados calculados en Google Sheets
    se eliminan porque podrán recalcularse posteriormente.

    Las transacciones con fecha inválida NO se eliminan.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. NORMALIZAR NOMBRES DE COLUMNAS
    # -----------------------------------------------------

    df = df.rename(
        columns={
            "precio_unit_auto": "precio_unitario",
            "total_auto": "total",
            "utilidad_auto": "utilidad",
            "barbero": "vendedor",
            "comision_barbero_auto": "comision_vendedor",
            "medio_de_pago": "medio_de_pago",
        }
    )

    # -----------------------------------------------------
    # 2. CONSERVAR SOLO VENTAS REALES
    # -----------------------------------------------------

    if "producto" in df.columns:
        df = df[
            df["producto"].notna()
            & df["producto"].ne("")
        ].copy()

    # -----------------------------------------------------
    # 3. CONVERTIR CANTIDAD
    # -----------------------------------------------------

    if "cantidad" in df.columns:
        df["cantidad"] = pd.to_numeric(
            df["cantidad"],
            errors="coerce",
        )

        df = df[
            df["cantidad"].fillna(0) > 0
        ].copy()

    # -----------------------------------------------------
    # 4. FECHA
    # -----------------------------------------------------

    # La celda A400 de la fuente contiene un serial de fecha
    # inválido. OpenPyXL/Pandas la convierte a NaT.
    #
    # Conservamos la transacción y marcamos el problema para
    # poder corregirlo posteriormente sin perder la venta.

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(
            df["fecha"],
            errors="coerce",
            dayfirst=True,
        )

        df["fecha_invalida"] = (
            df["fecha"].isna()
        ).astype("boolean")

    # -----------------------------------------------------
    # 5. COLUMNAS NUMÉRICAS
    # -----------------------------------------------------

    numeric_columns = [
        "precio_unitario",
        "total",
        "utilidad",
        "comision_vendedor",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # -----------------------------------------------------
    # 6. NORMALIZAR TEXTO
    # -----------------------------------------------------

    text_columns = [
        "producto",
        "vendedor",
        "medio_de_pago",
        "notas",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    if "producto" in df.columns:
        df["producto"] = (
            df["producto"]
            .str.lower()
        )

    if "vendedor" in df.columns:
        df["vendedor"] = (
            df["vendedor"]
            .str.lower()
        )

    if "medio_de_pago" in df.columns:
        df["medio_de_pago"] = (
            df["medio_de_pago"]
            .str.lower()
        )

    # -----------------------------------------------------
    # 7. COLUMNAS FINALES
    # -----------------------------------------------------
    #
    # No conservamos:
    #
    # ganancia_acum_auto
    # ganancia_dia_auto
    # unnamed_8
    #
    # porque son cálculos derivados de Google Sheets.

    final_columns = [
        "fecha",
        "fecha_invalida",
        "producto",
        "cantidad",
        "precio_unitario",
        "total",
        "utilidad",
        "vendedor",
        "comision_vendedor",
        "medio_de_pago",
        "notas",
    ]

    df = df[
        [
            column
            for column in final_columns
            if column in df.columns
        ]
    ].copy()

    return df.reset_index(drop=True)

# =========================================================
# BARBEROS
# =========================================================

def transform_barberos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y estandariza la tabla maestra de barberos.

    IMPORTANTE:
    porcentaje_comision_servicio y esquema reflejan
    valores de la hoja operativa actual.

    No deben interpretarse como todo el historial de
    comisiones del barbero.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. CONSERVAR COLUMNAS DEL MODELO
    # -----------------------------------------------------

    columns_to_keep = [
        "id",
        "barbero",
        "barbero_0_1",
        "esquema",
        "activo_true_false",
    ]

    df = df[
        [
            column
            for column in columns_to_keep
            if column in df.columns
        ]
    ].copy()

    # -----------------------------------------------------
    # 2. RENOMBRAR COLUMNAS
    # -----------------------------------------------------

    df = df.rename(
        columns={
            "barbero": "nombre",
            "barbero_0_1": "porcentaje_comision_servicio",
            "activo_true_false": "activo",
        }
    )

    # -----------------------------------------------------
    # 3. CREAR BARBERO_ID
    # -----------------------------------------------------

    df["barbero_id"] = (
        "BAR-"
        + pd.to_numeric(
            df["id"],
            errors="coerce",
        )
        .astype("Int64")
        .astype("string")
        .str.zfill(3)
    )

    df = df.drop(columns=["id"])

    # -----------------------------------------------------
    # 4. NORMALIZAR TIPOS
    # -----------------------------------------------------

    df["porcentaje_comision_servicio"] = pd.to_numeric(
        df["porcentaje_comision_servicio"],
        errors="coerce",
    )

    df["activo"] = (
        df["activo"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
            }
        )
    )

    df["nombre"] = (
        df["nombre"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # -----------------------------------------------------
    # 5. PROPIETARIO
    # -----------------------------------------------------

    df["es_propietario"] = (
        df["nombre"].eq("elias")
    )

    # -----------------------------------------------------
    # 6. CONTROL DE ID
    # -----------------------------------------------------

    if df["barbero_id"].duplicated().any():
        duplicated = df["barbero_id"].duplicated().sum()

        raise ValueError(
            f"Se encontraron {duplicated} barbero_id duplicados."
        )
        
        # -----------------------------------------------------
    # CORRECCIÓN DOCUMENTADA DE CONFIGURACIÓN ACTUAL
    # -----------------------------------------------------

    # Tino trabajó históricamente al 50%, pero su
    # configuración posterior/currente es 60/40.
    #
    # La fecha exacta del cambio no puede determinarse
    # con el dataset histórico disponible, por lo que
    # NO se modifican las ventas históricas.

    mask_tino = df["nombre"].eq("tino")

    df.loc[
        mask_tino,
        "porcentaje_comision_servicio",
    ] = 0.60

    df.loc[
        mask_tino,
        "esquema",
    ] = "60/40"    

    # -----------------------------------------------------
    # 7. ORDEN FINAL
    # -----------------------------------------------------

    df = df[
        [
            "barbero_id",
            "nombre",
            "porcentaje_comision_servicio",
            "esquema",
            "activo",
            "es_propietario",
        ]
    ]

    return df.reset_index(drop=True)


# =========================================================
# CLIENTES
# =========================================================

def transform_clientes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y estandariza la tabla maestra de clientes.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. CONSERVAR COLUMNAS DEL MODELO
    # -----------------------------------------------------

    columns_to_keep = [
        "cliente_id",
        "nombre",
        "telefono",
        "fecha_alta",
        "acepta_promociones",
        "observaciones",
        "activo",
    ]

    df = df[
        [
            column
            for column in columns_to_keep
            if column in df.columns
        ]
    ].copy()

    # -----------------------------------------------------
    # 2. CLIENTE_ID
    # -----------------------------------------------------

    df["cliente_id"] = (
        df["cliente_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # -----------------------------------------------------
    # 3. NOMBRE
    # -----------------------------------------------------

    df["nombre"] = (
        df["nombre"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # Corrección documentada del cliente genérico
    df.loc[
        df["cliente_id"].eq("CLI-0006"),
        "nombre",
    ] = "cliente ocasional"

    # -----------------------------------------------------
    # 4. TELÉFONO
    # -----------------------------------------------------

    if "telefono" in df.columns:
        df["telefono"] = (
            df["telefono"]
            .astype("string")
            .str.strip()
        )

    # -----------------------------------------------------
    # 5. FECHA DE ALTA
    # -----------------------------------------------------

    if "fecha_alta" in df.columns:
        df["fecha_alta"] = pd.to_datetime(
            df["fecha_alta"],
            errors="coerce",
            dayfirst=True,
        )

    # -----------------------------------------------------
    # 6. CONSENTIMIENTO DE PROMOCIONES
    # -----------------------------------------------------

    if "acepta_promociones" in df.columns:
        df["acepta_promociones"] = (
            df["acepta_promociones"]
            .astype("string")
            .str.strip()
            .str.lower()
            .map(
                {
                    "si": True,
                    "sí": True,
                    "no": False,
                }
            )
        )

    # -----------------------------------------------------
    # 7. ACTIVO
    # -----------------------------------------------------

    if "activo" in df.columns:
        df["activo"] = (
            df["activo"]
            .astype("string")
            .str.strip()
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False,
                }
            )
        )

    # -----------------------------------------------------
    # 8. CONTROL DE CLIENTE_ID
    # -----------------------------------------------------

    if df["cliente_id"].duplicated().any():
        duplicated = df["cliente_id"].duplicated().sum()

        raise ValueError(
            f"Se encontraron {duplicated} cliente_id duplicados."
        )

    return df.reset_index(drop=True)


# =========================================================
# CATÁLOGO DE SERVICIOS
# =========================================================

def transform_catalogo_servicios(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye el catálogo canónico de servicios.

    La hoja operativa utiliza TAR-xxx como servicio_id,
    pero TAR-xxx también se utiliza para tarifas.

    El modelo procesado utiliza SER-xxx para identificar
    servicios de forma independiente.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. CONSERVAR COLUMNAS ÚTILES
    # -----------------------------------------------------

    columns_to_keep = [
        "servicio",
        "duracion_min",
        "activo",
    ]

    df = df[
        [
            column
            for column in columns_to_keep
            if column in df.columns
        ]
    ].copy()

    # -----------------------------------------------------
    # 2. NORMALIZAR SERVICIO
    # -----------------------------------------------------

    df["servicio"] = (
        df["servicio"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # -----------------------------------------------------
    # 3. ASIGNAR SERVICIO_ID CANÓNICO
    # -----------------------------------------------------

    current_service_ids = {
        "corte": "SER-001",
        "barba": "SER-002",
        "corte+barba": "SER-003",
        "jubilado": "SER-004",
        "claritos": "SER-005",
        "global": "SER-006",
    }

    df["servicio_id"] = df["servicio"].map(
        current_service_ids
    )

    # -----------------------------------------------------
    # 4. TIPOS
    # -----------------------------------------------------

    df["duracion_min"] = pd.to_numeric(
        df["duracion_min"],
        errors="coerce",
    ).astype("Int64")

    df["activo"] = (
        df["activo"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
            }
        )
    )
    df["activo"] = df["activo"].astype("boolean")

    # -----------------------------------------------------
    # 5. SERVICIOS HISTÓRICOS ESPECIALES
    # -----------------------------------------------------

    historical_services = pd.DataFrame(
        {
            "servicio_id": pd.Series(
                [
                    "SER-007",
                    "SER-008",
                    "SER-009",
                    "SER-010",
                    "SER-011",
                    "SER-012",
                ],
                dtype="string",
            ),
            "servicio": pd.Series(
                [
                    "corte_y_diseño",
                    "color",
                    "global nathan",
                    "corte+color",
                    "color agus",
                    "banderita_nene",
                ],
                dtype="string",
            ),
            "duracion_min": pd.Series(
                [
                    pd.NA,
                    pd.NA,
                    pd.NA,
                    pd.NA,
                    pd.NA,
                    pd.NA,
                ],
                dtype="Int64",
            ),
            "activo": pd.Series(
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                dtype="boolean",
            ),
        }
    )

    df = pd.concat(
        [
            df,
            historical_services,
        ],
        ignore_index=True,
    )

    # -----------------------------------------------------
    # 6. CONTROLES
    # -----------------------------------------------------

    if df["servicio_id"].isna().any():
        servicios_sin_id = (
            df.loc[
                df["servicio_id"].isna(),
                "servicio",
            ]
            .dropna()
            .tolist()
        )

        raise ValueError(
            "Hay servicios del catálogo sin servicio_id: "
            f"{servicios_sin_id}"
        )

    if df["servicio_id"].duplicated().any():
        raise ValueError(
            "Se encontraron servicio_id duplicados "
            "en el catálogo."
        )

    # -----------------------------------------------------
    # 7. ORDEN FINAL
    # -----------------------------------------------------

    df = df[
        [
            "servicio_id",
            "servicio",
            "duracion_min",
            "activo",
        ]
    ]

    return df.reset_index(drop=True)

# =========================================================
# TARIFAS DE SERVICIOS
# =========================================================

def transform_tarifas_servicios(
    df: pd.DataFrame,
    catalogo_servicios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Limpia y estandariza el historial de tarifas.

    La vigencia se recalcula a partir de fecha_hasta
    porque el campo 'vigente' de la fuente presenta
    inconsistencias.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. CONSERVAR COLUMNAS
    # -----------------------------------------------------

    columns_to_keep = [
        "tarifa_id",
        "servicio",
        "precio",
        "fecha_desde",
        "fecha_hasta",
        "vigente",
    ]

    df = df[
        [
            column
            for column in columns_to_keep
            if column in df.columns
        ]
    ].copy()

    # -----------------------------------------------------
    # 2. NORMALIZAR TARIFA_ID
    # -----------------------------------------------------

    df["tarifa_id"] = (
        df["tarifa_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # -----------------------------------------------------
    # 3. NORMALIZAR SERVICIO
    # -----------------------------------------------------

    df["servicio"] = (
        df["servicio"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # -----------------------------------------------------
    # 4. PRECIO
    # -----------------------------------------------------

    df["precio"] = pd.to_numeric(
        df["precio"],
        errors="coerce",
    )

    # -----------------------------------------------------
    # 5. FECHAS
    # -----------------------------------------------------

    df["fecha_desde"] = pd.to_datetime(
        df["fecha_desde"],
        errors="coerce",
        dayfirst=True,
    )

    df["fecha_hasta"] = pd.to_datetime(
        df["fecha_hasta"],
        errors="coerce",
        dayfirst=True,
    )

    # -----------------------------------------------------
    # 6. SERVICIO_ID
    # -----------------------------------------------------

    current_service_ids = {
        "corte": "SER-001",
        "barba": "SER-002",
        "corte+barba": "SER-003",
        "jubilado": "SER-004",
        "claritos": "SER-005",
        "global": "SER-006",
    }

    df["servicio_id"] = (
       df["servicio"]
       .map(current_service_ids)
       .astype("string")
    )
    # -----------------------------------------------------
    # 7. RECALCULAR VIGENCIA
    # -----------------------------------------------------
    #
    # Una tarifa sin fecha_hasta sigue abierta.
    # No confiamos en 'vigente' de la hoja original.

    df["vigente"] = (
        df["fecha_hasta"].isna()
    ).astype("boolean")

    # -----------------------------------------------------
    # 8. CONTROLES
    # -----------------------------------------------------

    if df["tarifa_id"].duplicated().any():
        duplicated = df["tarifa_id"].duplicated().sum()

        raise ValueError(
            f"Se encontraron {duplicated} tarifa_id duplicados."
        )

    if df["servicio_id"].isna().any():
        servicios_faltantes = (
            df.loc[
                df["servicio_id"].isna(),
                "servicio",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            "Hay tarifas con servicios sin servicio_id: "
            f"{servicios_faltantes}"
        )

    ids_catalogo = set(
        catalogo_servicios["servicio_id"]
        .dropna()
        .astype(str)
    )

    ids_tarifas = set(
        df["servicio_id"]
        .dropna()
        .astype(str)
    )

    faltantes_catalogo = sorted(
        ids_tarifas - ids_catalogo
    )

    if faltantes_catalogo:
        raise ValueError(
            "Hay servicio_id de tarifas que no existen "
            "en el catálogo: "
            f"{faltantes_catalogo}"
        )

    # La fecha final no puede ser anterior a la inicial
    fechas_invalidas = df[
        df["fecha_hasta"].notna()
        & (
            df["fecha_hasta"]
            < df["fecha_desde"]
        )
    ]

    if not fechas_invalidas.empty:
        raise ValueError(
            "Existen tarifas con fecha_hasta "
            "anterior a fecha_desde."
        )

    # -----------------------------------------------------
    # 9. ORDEN FINAL
    # -----------------------------------------------------

    df = df[
        [
            "tarifa_id",
            "servicio_id",
            "servicio",
            "precio",
            "fecha_desde",
            "fecha_hasta",
            "vigente",
        ]
    ]

    return df.reset_index(drop=True)
# =========================================================
# RELACIÓN VENTAS -> BARBEROS
# =========================================================

def add_barbero_id_to_ventas(
    ventas: pd.DataFrame,
    barberos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Agrega barbero_id a cada venta usando
    la tabla maestra de barberos.
    """

    ventas = ventas.copy()

    catalogo_barberos = barberos[
        [
            "barbero_id",
            "nombre",
        ]
    ].copy()

    # -----------------------------------------------------
    # 1. CONTROL DE NOMBRES ÚNICOS
    # -----------------------------------------------------

    if catalogo_barberos["nombre"].duplicated().any():
        duplicated = (
            catalogo_barberos["nombre"]
            .duplicated()
            .sum()
        )

        raise ValueError(
            "Se encontraron "
            f"{duplicated} nombres de barberos duplicados."
        )

    # -----------------------------------------------------
    # 2. AGREGAR BARBERO_ID
    # -----------------------------------------------------

    ventas = ventas.merge(
        catalogo_barberos,
        how="left",
        left_on="barbero",
        right_on="nombre",
        validate="many_to_one",
    )

    # -----------------------------------------------------
    # 3. CONTROL DE INTEGRIDAD
    # -----------------------------------------------------

    faltantes = ventas[
        ventas["barbero_id"].isna()
    ]

    if not faltantes.empty:
        nombres_faltantes = (
            faltantes["barbero"]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            "Hay ventas con barberos sin barbero_id: "
            f"{nombres_faltantes}"
        )

    ventas = ventas.drop(
        columns=["nombre"]
    )

    return ventas


# =========================================================
# VALIDACIÓN VENTAS -> CLIENTES
# =========================================================

def validate_clientes_in_ventas(
    ventas: pd.DataFrame,
    clientes: pd.DataFrame,
) -> None:
    """
    Verifica que todos los cliente_id utilizados
    en ventas existan en la tabla maestra de clientes.

    Los cliente_id nulos son válidos porque
    históricamente no siempre se registraban clientes.
    """

    ids_ventas = set(
        ventas["cliente_id"]
        .dropna()
        .astype(str)
    )

    ids_clientes = set(
        clientes["cliente_id"]
        .dropna()
        .astype(str)
    )

    faltantes = sorted(
        ids_ventas - ids_clientes
    )

    if faltantes:
        raise ValueError(
            "Hay cliente_id utilizados en ventas "
            "que no existen en clientes: "
            f"{faltantes}"
        )


# =========================================================
# RELACIÓN VENTAS -> SERVICIOS
# =========================================================

def add_servicio_id_to_ventas(
    ventas: pd.DataFrame,
    catalogo_servicios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Asigna un servicio_id canónico a cada venta.

    La columna servicio original se conserva para
    mantener trazabilidad histórica.
    """

    ventas = ventas.copy()

    # -----------------------------------------------------
    # 1. MAPEAR SERVICIO HISTÓRICO -> SERVICIO_ID
    # -----------------------------------------------------

    ventas["servicio_id"] = (
        ventas["servicio"]
        .map(SERVICE_ALIAS_TO_ID)
        .astype("string")
    )

    # -----------------------------------------------------
    # 2. CONTROL DE SERVICIOS SIN MAPEO
    # -----------------------------------------------------

    faltantes = ventas[
        ventas["servicio_id"].isna()
    ]

    if not faltantes.empty:
        servicios_faltantes = (
            faltantes["servicio"]
            .value_counts()
            .to_dict()
        )

        raise ValueError(
            "Hay servicios históricos sin mapeo: "
            f"{servicios_faltantes}"
        )

    # -----------------------------------------------------
    # 3. CONTROL CONTRA CATÁLOGO
    # -----------------------------------------------------

    ids_catalogo = set(
        catalogo_servicios["servicio_id"]
        .dropna()
        .astype(str)
    )

    ids_ventas = set(
        ventas["servicio_id"]
        .dropna()
        .astype(str)
    )

    ids_inexistentes = sorted(
        ids_ventas - ids_catalogo
    )

    if ids_inexistentes:
        raise ValueError(
            "Hay servicio_id utilizados en ventas "
            "que no existen en el catálogo: "
            f"{ids_inexistentes}"
        )

    return ventas

# =========================================================
# INVENTARIO DE PRODUCTOS
# =========================================================

def transform_inventario_productos(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Limpia y consolida el inventario de productos.

    - Elimina filas sin producto.
    - Normaliza nombres.
    - Elimina columnas auxiliares.
    - Consolida nombres duplicados.
    - Si un mismo producto tiene precios distintos,
      conserva el conflicto sin inventar cuál es vigente.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # La columna original '<' queda con nombre vacío
    # después de normalize_column_name().
    if "" in df.columns:
        df = df.rename(
            columns={
                "": "producto",
            }
        )

    # -----------------------------------------------------
    # 1. RENOMBRAR COLUMNAS
    # -----------------------------------------------------

    df = df.rename(
        columns={
            "entradas_auto": "entradas",
            "salidas_auto": "salidas",
            "stock_actual_auto": "stock_actual",
            "costo_promedio_auto": "costo_promedio",
            "valor_stock_auto": "valor_stock",
            "margen": "margen",
        }
    )

    # -----------------------------------------------------
    # 2. CONSERVAR SOLO PRODUCTOS REALES
    # -----------------------------------------------------

    df = df[
        df["producto"].notna()
        & df["producto"].ne("")
    ].copy()

    # -----------------------------------------------------
    # 3. NORMALIZAR NOMBRE DEL PRODUCTO
    # -----------------------------------------------------

    df["producto"] = (
        df["producto"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # -----------------------------------------------------
    # 4. COLUMNAS NUMÉRICAS
    # -----------------------------------------------------

    numeric_columns = [
        "entradas",
        "salidas",
        "stock_actual",
        "costo_promedio",
        "valor_stock",
        "precio_venta",
        "margen",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # -----------------------------------------------------
    # 5. CONSOLIDAR PRODUCTOS DUPLICADOS
    # -----------------------------------------------------

    registros = []

    for producto, grupo in df.groupby(
        "producto",
        sort=False,
        dropna=False,
    ):

        precios = sorted(
            grupo["precio_venta"]
            .dropna()
            .unique()
            .tolist()
        )

        precio_conflicto = len(precios) > 1

        # Si hay un único precio, lo usamos.
        # Si hay varios, no inventamos cuál es vigente.
        precio_venta = (
            precios[0]
            if len(precios) == 1
            else pd.NA
        )

        # Los demás valores del inventario deben coincidir
        # entre las filas duplicadas.
        def unique_value(column):
            values = (
                grupo[column]
                .dropna()
                .unique()
                .tolist()
            )

            if len(values) <= 1:
                return values[0] if values else pd.NA

            raise ValueError(
                f"El producto '{producto}' tiene "
                f"valores conflictivos en '{column}': "
                f"{values}"
            )

        registros.append(
            {
                "producto": producto,
                "entradas": unique_value("entradas"),
                "salidas": unique_value("salidas"),
                "stock_actual": unique_value("stock_actual"),
                "costo_promedio": unique_value(
                    "costo_promedio"
                ),
                "valor_stock": unique_value("valor_stock"),
                "precio_venta": precio_venta,
                "precio_conflicto": precio_conflicto,
                "precios_observados": " | ".join(
                    str(int(precio))
                    if float(precio).is_integer()
                    else str(precio)
                    for precio in precios
                ),
                "notas": unique_value("notas"),
                "margen": (
                    unique_value("margen")
                    if not precio_conflicto
                    else pd.NA
                ),
            }
        )

    result = pd.DataFrame(registros)

    # -----------------------------------------------------
    # 6. TIPOS
    # -----------------------------------------------------

    result["producto"] = result[
        "producto"
    ].astype("string")

    result["precio_conflicto"] = result[
        "precio_conflicto"
    ].astype("boolean")

    result["precios_observados"] = result[
        "precios_observados"
    ].astype("string")

    # -----------------------------------------------------
    # 7. CONTROL FINAL
    # -----------------------------------------------------

    if result["producto"].duplicated().any():
        raise ValueError(
            "El inventario procesado todavía contiene "
            "productos duplicados."
        )

    return result.reset_index(drop=True)

# =========================================================
# COMPRAS MAYORISTAS
# =========================================================

def transform_compras_mayorista(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Limpia y estandariza las compras de productos.

    Se conserva la información transaccional real.
    Las filas completamente vacías no forman parte
    de las compras y se eliminan.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. NORMALIZAR NOMBRES DE COLUMNAS
    # -----------------------------------------------------

    # La primera columna original tiene como nombre
    # solamente un espacio. Después de normalizar,
    # queda con nombre vacío.
    if "" in df.columns:
        df = df.rename(
            columns={
                "": "fecha",
            }
        )

    df = df.rename(
        columns={
            "total_auto": "total",
        }
    )

    # -----------------------------------------------------
    # 2. CONSERVAR SOLO COMPRAS REALES
    # -----------------------------------------------------

    df = df[
        df["producto"].notna()
        & df["producto"].ne("")
    ].copy()

    # -----------------------------------------------------
    # 3. FECHA
    # -----------------------------------------------------

    df["fecha"] = pd.to_datetime(
        df["fecha"],
        errors="coerce",
        dayfirst=True,
    )

    # -----------------------------------------------------
    # 4. NORMALIZAR TEXTO
    # -----------------------------------------------------

    text_columns = [
        "proveedor",
        "producto",
        "notas",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    if "proveedor" in df.columns:
        df["proveedor"] = (
            df["proveedor"]
            .str.lower()
        )

    if "producto" in df.columns:
        df["producto"] = (
            df["producto"]
            .str.lower()
        )

    # -----------------------------------------------------
    # 5. COLUMNAS NUMÉRICAS
    # -----------------------------------------------------

    numeric_columns = [
        "cantidad",
        "costo_unitario",
        "total",
        "comprar_mas_productos",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # -----------------------------------------------------
    # 6. VALIDACIONES BÁSICAS
    # -----------------------------------------------------

    if df["fecha"].isna().any():
        raise ValueError(
            "Existen compras reales con fecha inválida."
        )

    if df["cantidad"].isna().any():
        raise ValueError(
            "Existen compras sin cantidad."
        )

    if (df["cantidad"] <= 0).any():
        raise ValueError(
            "Existen compras con cantidad menor o igual a cero."
        )

    if df["costo_unitario"].isna().any():
        raise ValueError(
            "Existen compras sin costo_unitario."
        )

    # -----------------------------------------------------
    # 7. COLUMNAS FINALES
    # -----------------------------------------------------

    final_columns = [
        "fecha",
        "proveedor",
        "producto",
        "cantidad",
        "costo_unitario",
        "total",
        "notas",
        "comprar_mas_productos",
    ]

    df = df[
        [
            column
            for column in final_columns
            if column in df.columns
        ]
    ].copy()

    return df.reset_index(drop=True)

# =========================================================
# CATÁLOGO MAESTRO DE PRODUCTOS
# =========================================================

def build_catalogo_productos(
    inventario: pd.DataFrame,
    compras: pd.DataFrame,
    ventas: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye el catálogo maestro de productos usando
    inventario, compras y ventas.

    Los nombres diferentes NO se fusionan automáticamente,
    aunque puedan parecer productos similares.
    """

    inventario_productos = set(
        inventario["producto"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    compras_productos = set(
        compras["producto"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    ventas_productos = set(
        ventas["producto"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # -----------------------------------------------------
    # 1. UNIÓN DE TODAS LAS FUENTES
    # -----------------------------------------------------

    todos_productos = sorted(
        inventario_productos
        | compras_productos
        | ventas_productos
    )

    registros = []

    for producto in todos_productos:

        en_inventario = producto in inventario_productos
        en_compras = producto in compras_productos
        en_ventas = producto in ventas_productos

        registros.append(
            {
                "producto_id": generate_producto_id(
                    producto
                ),
                "producto": producto,
                "en_inventario": en_inventario,
                "en_compras": en_compras,
                "en_ventas": en_ventas,
                "requiere_revision": not en_inventario,
            }
        )

    catalogo = pd.DataFrame(registros)

    # -----------------------------------------------------
    # 2. TIPOS
    # -----------------------------------------------------

    catalogo["producto_id"] = (
        catalogo["producto_id"]
        .astype("string")
    )

    catalogo["producto"] = (
        catalogo["producto"]
        .astype("string")
    )

    boolean_columns = [
        "en_inventario",
        "en_compras",
        "en_ventas",
        "requiere_revision",
    ]

    for column in boolean_columns:
        catalogo[column] = (
            catalogo[column]
            .astype("boolean")
        )

    # -----------------------------------------------------
    # 3. CONTROLES
    # -----------------------------------------------------

    if catalogo["producto"].duplicated().any():
        raise ValueError(
            "El catálogo contiene productos duplicados."
        )

    if catalogo["producto_id"].duplicated().any():
        raise ValueError(
            "Se produjo una colisión de producto_id."
        )

    return catalogo.reset_index(drop=True)

# =========================================================
# RELACIÓN TABLAS -> CATÁLOGO DE PRODUCTOS
# =========================================================

def add_producto_id(
    df: pd.DataFrame,
    catalogo_productos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Agrega producto_id utilizando el catálogo maestro.
    """

    df = df.copy()

    mapa = dict(
        zip(
            catalogo_productos["producto"],
            catalogo_productos["producto_id"],
        )
    )

    df["producto_id"] = (
        df["producto"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map(mapa)
        .astype("string")
    )

    faltantes = df[
        df["producto_id"].isna()
    ]

    if not faltantes.empty:
        productos_faltantes = (
            faltantes["producto"]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            "Hay productos sin producto_id: "
            f"{productos_faltantes}"
        )

    return df

# =========================================================
# GASTOS
# =========================================================

def transform_gastos(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Limpia y estandariza los gastos de JStyles.

    Los gastos históricos que no tenían tipo/categoría
    se completan mediante una clasificación documentada.

    Los valores futuros cargados en Google Sheets
    tienen prioridad y no son reemplazados.
    """

    df = normalize_columns(df)
    df = clean_text_columns(df)

    # -----------------------------------------------------
    # 1. RENOMBRAR COLUMNAS
    # -----------------------------------------------------

    df = df.rename(
        columns={
            "conceptos": "concepto",
            "metodo": "metodo_pago",
        }
    )

    # -----------------------------------------------------
    # 2. CONSERVAR SOLO GASTOS REALES
    # -----------------------------------------------------

    df = df[
        df["concepto"].notna()
        & df["concepto"].ne("")
    ].copy()

    # -----------------------------------------------------
    # 3. FECHA
    # -----------------------------------------------------

    df["fecha"] = pd.to_datetime(
        df["fecha"],
        errors="coerce",
        dayfirst=True,
    )

    # -----------------------------------------------------
    # 4. MONTO
    # -----------------------------------------------------

    df["monto"] = pd.to_numeric(
        df["monto"],
        errors="coerce",
    )

    # -----------------------------------------------------
    # 5. NORMALIZAR TEXTO
    # -----------------------------------------------------

    for column in [
        "concepto",
        "metodo_pago",
        "notas",
        "tipo_gasto",
        "categoria",
    ]:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    df["concepto"] = (
        df["concepto"]
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )

    df["metodo_pago"] = (
        df["metodo_pago"]
        .str.lower()
    )

    df["tipo_gasto"] = (
        df["tipo_gasto"]
        .str.lower()
    )

    df["categoria"] = (
        df["categoria"]
        .str.lower()
    )

    # -----------------------------------------------------
    # 6. CLASIFICACIÓN HISTÓRICA DOCUMENTADA
    # -----------------------------------------------------

    clasificacion_historica = {
        "comida": (
            "personal",
            "alimentacion",
        ),
        "zapatilla enchufe": (
            "comercial",
            "mantenimiento_equipamiento",
        ),
        "acido salicilico , termometro (noah, austin)": (
            "personal",
            "salud_personal",
        ),
        "pago de flyers a la grafica": (
            "comercial",
            "marketing_publicidad",
        ),
        "crema oxigenada de 5 litros": (
            "comercial",
            "insumos",
        ),
    }

    for concepto, (
        tipo_historico,
        categoria_historica,
    ) in clasificacion_historica.items():

        mask = df["concepto"].eq(concepto)

        # Solo completar si la fuente no tenía valor.
        df.loc[
            mask & df["tipo_gasto"].isna(),
            "tipo_gasto",
        ] = tipo_historico

        df.loc[
            mask & df["categoria"].isna(),
            "categoria",
        ] = categoria_historica

    # -----------------------------------------------------
    # 7. AFECTA RESULTADO DEL NEGOCIO
    # -----------------------------------------------------

    df["afecta_resultado_local"] = (
        df["tipo_gasto"]
        .eq("comercial")
        .astype("boolean")
    )

    # -----------------------------------------------------
    # 8. VALIDACIONES
    # -----------------------------------------------------

    if df["fecha"].isna().any():
        raise ValueError(
            "Existen gastos reales con fecha inválida."
        )

    if df["monto"].isna().any():
        raise ValueError(
            "Existen gastos reales sin monto."
        )

    if (df["monto"] <= 0).any():
        raise ValueError(
            "Existen gastos con monto menor o igual a cero."
        )

    tipos_validos = {
        "comercial",
        "personal",
    }

    tipos_invalidos = set(
        df["tipo_gasto"]
        .dropna()
        .unique()
    ) - tipos_validos

    if tipos_invalidos:
        raise ValueError(
            "Existen tipos de gasto inválidos: "
            f"{sorted(tipos_invalidos)}"
        )

    # -----------------------------------------------------
    # 9. COLUMNAS FINALES
    # -----------------------------------------------------

    final_columns = [
        "fecha",
        "concepto",
        "monto",
        "metodo_pago",
        "notas",
        "tipo_gasto",
        "categoria",
        "afecta_resultado_local",
    ]

    return (
        df[final_columns]
        .reset_index(drop=True)
    )
    
# =========================================================
# IDENTIFICADORES DE VENTAS DE PRODUCTOS
# =========================================================

def add_venta_producto_id(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera un ID determinístico para cada venta de producto.

    Si existen operaciones con exactamente los mismos datos,
    se agrega un número de ocurrencia para mantenerlas como
    transacciones independientes.
    """

    df = df.copy()

    campos_id = [
        "fecha",
        "producto",
        "cantidad",
        "precio_unitario",
        "total",
        "utilidad",
        "vendedor",
        "comision_vendedor",
        "medio_de_pago",
        "notas",
    ]

    # -----------------------------------------------------
    # 1. CONSTRUIR REPRESENTACIÓN ESTABLE
    # -----------------------------------------------------

    base = df[campos_id].copy()

    base["fecha"] = (
        pd.to_datetime(base["fecha"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
        .fillna("<NA>")
    )

    for column in campos_id:
        if column != "fecha":
            base[column] = (
                base[column]
                .astype("string")
                .fillna("<NA>")
                .str.strip()
                .str.lower()
            )

    fingerprint_text = base.astype(str).agg(
        "|".join,
        axis=1,
    )

    # -----------------------------------------------------
    # 2. HASH DE LA OPERACIÓN
    # -----------------------------------------------------

    fingerprint = fingerprint_text.map(
        lambda value: hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:10].upper()
    )

    # -----------------------------------------------------
    # 3. DISTINGUIR OPERACIONES IDÉNTICAS
    # -----------------------------------------------------

    ocurrencia = (
        fingerprint
        .groupby(fingerprint)
        .cumcount()
        .add(1)
    )

    df["venta_producto_id"] = (
        "VP-"
        + fingerprint
        + "-"
        + ocurrencia.astype(str).str.zfill(2)
    ).astype("string")

    # -----------------------------------------------------
    # 4. VALIDAR
    # -----------------------------------------------------

    if df["venta_producto_id"].isna().any():
        raise ValueError(
            "Existen ventas de productos sin ID."
        )

    if df["venta_producto_id"].duplicated().any():
        raise ValueError(
            "Se generaron venta_producto_id duplicados."
        )

    # Poner ID como primera columna
    columnas = [
        "venta_producto_id",
        *[
            column
            for column in df.columns
            if column != "venta_producto_id"
        ],
    ]

    return df[columnas]

# =========================================================
# IDENTIFICADORES DE COMPRAS
# =========================================================

def add_compra_id(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera un ID determinístico para cada compra mayorista.
    """

    df = df.copy()

    campos_id = [
        "fecha",
        "proveedor",
        "producto",
        "cantidad",
        "costo_unitario",
        "total",
        "notas",
        "comprar_mas_productos",
    ]

    base = df[campos_id].copy()

    base["fecha"] = (
        pd.to_datetime(base["fecha"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
        .fillna("<NA>")
    )

    for column in campos_id:
        if column != "fecha":
            base[column] = (
                base[column]
                .astype("string")
                .fillna("<NA>")
                .str.strip()
                .str.lower()
            )

    fingerprint_text = base.astype(str).agg(
        "|".join,
        axis=1,
    )

    fingerprint = fingerprint_text.map(
        lambda value: hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:12].upper()
    )

    df["compra_id"] = (
        "COM-" + fingerprint
    ).astype("string")

    if df["compra_id"].isna().any():
        raise ValueError(
            "Existen compras sin compra_id."
        )

    if df["compra_id"].duplicated().any():
        raise ValueError(
            "Se generaron compra_id duplicados."
        )

    columnas = [
        "compra_id",
        *[
            column
            for column in df.columns
            if column != "compra_id"
        ],
    ]

    return df[columnas]

# =========================================================
# IDENTIFICADORES DE GASTOS
# =========================================================

def add_gasto_id(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera un ID determinístico para cada gasto.
    """

    df = df.copy()

    campos_id = [
        "fecha",
        "concepto",
        "monto",
        "metodo_pago",
        "notas",
        "tipo_gasto",
        "categoria",
    ]

    base = df[campos_id].copy()

    base["fecha"] = (
        pd.to_datetime(base["fecha"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
        .fillna("<NA>")
    )

    for column in campos_id:
        if column != "fecha":
            base[column] = (
                base[column]
                .astype("string")
                .fillna("<NA>")
                .str.strip()
                .str.lower()
            )

    fingerprint_text = base.astype(str).agg(
        "|".join,
        axis=1,
    )

    fingerprint = fingerprint_text.map(
        lambda value: hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:12].upper()
    )

    df["gasto_id"] = (
        "GAS-" + fingerprint
    ).astype("string")

    if df["gasto_id"].isna().any():
        raise ValueError(
            "Existen gastos sin gasto_id."
        )

    if df["gasto_id"].duplicated().any():
        raise ValueError(
            "Se generaron gasto_id duplicados."
        )

    columnas = [
        "gasto_id",
        *[
            column
            for column in df.columns
            if column != "gasto_id"
        ],
    ]

    return df[columnas]

# =========================================================
# HISTORIAL / CONFIGURACIÓN DE COMISIONES DE BARBEROS
# =========================================================

def build_comisiones_barberos(
    barberos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye una tabla de configuraciones de comisión.

    - Se genera una configuración actual para cada barbero.
    - Se conserva la evidencia histórica conocida de Tino
      al 50/50.
    - No se inventan fechas de vigencia cuando no existen.
    """

    registros = []

    # -----------------------------------------------------
    # 1. CONFIGURACIONES ACTUALES / ÚLTIMAS CONOCIDAS
    # -----------------------------------------------------

    for _, row in barberos.iterrows():

        porcentaje_barbero = float(
            row["porcentaje_comision_servicio"]
        )

        porcentaje_local = round(
            1 - porcentaje_barbero,
            4,
        )

        texto_id = (
            f"{row['barbero_id']}|"
            f"configuracion_actual|"
            f"{porcentaje_barbero:.4f}"
        )

        digest = hashlib.sha256(
            texto_id.encode("utf-8")
        ).hexdigest()[:12].upper()

        registros.append(
            {
                "comision_config_id": f"CB-{digest}",
                "barbero_id": row["barbero_id"],
                "porcentaje_barbero": porcentaje_barbero,
                "porcentaje_local": porcentaje_local,
                "esquema": row["esquema"],

                # No conocemos necesariamente la fecha
                # exacta en que comenzó esta configuración.
                "fecha_desde": pd.NaT,
                "fecha_hasta": pd.NaT,

                # Fechas de evidencia histórica,
                # no equivalen a vigencia contractual.
                "observado_desde": pd.NaT,
                "observado_hasta": pd.NaT,

                "origen": "configuracion_actual",
                "es_configuracion_actual": True,
            }
        )

    # -----------------------------------------------------
    # 2. HISTÓRICO DOCUMENTADO: TINO
    # -----------------------------------------------------

    tino = barberos[
        barberos["barbero_id"].eq("BAR-002")
    ]

    if len(tino) != 1:
        raise ValueError(
            "No se pudo identificar de forma única a Tino."
        )

    texto_id = (
        "BAR-002|historico_observado|"
        "0.5000|2025-09-30|2025-11-01"
    )

    digest = hashlib.sha256(
        texto_id.encode("utf-8")
    ).hexdigest()[:12].upper()

    registros.append(
        {
            "comision_config_id": f"CB-{digest}",
            "barbero_id": "BAR-002",
            "porcentaje_barbero": 0.50,
            "porcentaje_local": 0.50,
            "esquema": "50/50",

            # No conocemos las fechas reales exactas
            # de inicio y final de esta configuración.
            "fecha_desde": pd.NaT,
            "fecha_hasta": pd.NaT,

            # Lo que sí sabemos es que existen ventas
            # observadas con este porcentaje en este rango.
            "observado_desde": pd.Timestamp(
                "2025-09-30"
            ),
            "observado_hasta": pd.Timestamp(
                "2025-11-01"
            ),

            "origen": "historico_observado",
            "es_configuracion_actual": False,
        }
    )

    df = pd.DataFrame(registros)

    # -----------------------------------------------------
    # 3. TIPOS
    # -----------------------------------------------------

    string_columns = [
        "comision_config_id",
        "barbero_id",
        "esquema",
        "origen",
    ]

    for column in string_columns:
        df[column] = df[column].astype("string")

    df["es_configuracion_actual"] = (
        df["es_configuracion_actual"]
        .astype("boolean")
    )

    for column in [
        "fecha_desde",
        "fecha_hasta",
        "observado_desde",
        "observado_hasta",
    ]:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce",
        )

    # -----------------------------------------------------
    # 4. VALIDACIONES
    # -----------------------------------------------------

    if df["comision_config_id"].duplicated().any():
        raise ValueError(
            "Hay comision_config_id duplicados."
        )

    if not df["porcentaje_barbero"].between(
        0, 1
    ).all():
        raise ValueError(
            "Hay porcentajes de barbero inválidos."
        )

    if not df["porcentaje_local"].between(
        0, 1
    ).all():
        raise ValueError(
            "Hay porcentajes del local inválidos."
        )

    suma = (
        df["porcentaje_barbero"]
        + df["porcentaje_local"]
    )

    if not suma.round(4).eq(1.0).all():
        raise ValueError(
            "Las comisiones de barbero y local "
            "no suman 100%."
        )

    return df.reset_index(drop=True)

# =========================================================
# TRANSFORMACIÓN GENÉRICA
# =========================================================

def transform_generic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza básica para tablas que todavía
    no tienen transformación específica.
    """

    df = normalize_columns(df)

    df = df.dropna(how="all")

    df = clean_text_columns(df)

    return df.reset_index(drop=True)



# =========================================================
# IDENTIFICADORES DE PRODUCTOS
# =========================================================

def generate_producto_id(producto: str) -> str:
    """
    Genera un identificador determinístico para un producto.

    El mismo nombre normalizado siempre genera
    el mismo producto_id.
    """

    producto_normalizado = (
        str(producto)
        .strip()
        .lower()
    )

    digest = hashlib.sha256(
        producto_normalizado.encode("utf-8")
    ).hexdigest()[:12].upper()

    return f"PRO-{digest}"


# =========================================================
# ORQUESTADOR DE TRANSFORMACIONES
# =========================================================

def transform_data(
    dataframes: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Ejecuta las transformaciones de las fuentes de JStyles.
    """

    print()
    print("Iniciando transformación de datos...")
    print()

    transformed = {}

    # -----------------------------------------------------
    # 1. TRANSFORMAR CADA FUENTE
    # -----------------------------------------------------

    for sheet, df in dataframes.items():

        original_rows = len(df)

        if sheet == "ventas":
            clean_df = transform_ventas(df)

        elif sheet == "barberos":
            clean_df = transform_barberos(df)

        elif sheet == "Clientes":
            clean_df = transform_clientes(df)
        
        elif sheet == "gastos":
            clean_df = transform_gastos(df)    

        elif sheet == "catalogo_servicios":
            clean_df = transform_catalogo_servicios(df)
        
        elif sheet == "tarifas_servicios":
            clean_df = transform_generic(df)

        elif sheet == "productos_ventas":
            clean_df = transform_productos_ventas(df)
            
        elif sheet == "compras_mayorista":
            clean_df = transform_compras_mayorista(df)
        
        elif sheet == "inventario_productos":
            clean_df = transform_inventario_productos(df)

        else:
            clean_df = transform_generic(df)

        transformed[sheet] = clean_df

        print(
            f"[OK] {sheet:<25} "
            f"{original_rows:>6} -> "
            f"{len(clean_df):>6} filas"
        )

    # -----------------------------------------------------
    # 2. RELACIONAR VENTAS -> BARBEROS
    # -----------------------------------------------------

    transformed["ventas"] = add_barbero_id_to_ventas(
        transformed["ventas"],
        transformed["barberos"],
    )

    print()
    print(
        "[OK] Integridad ventas -> barberos validada."
    )

    # -----------------------------------------------------
    # 3. VALIDAR VENTAS -> CLIENTES
    # -----------------------------------------------------

    validate_clientes_in_ventas(
        transformed["ventas"],
        transformed["Clientes"],
    )

    print(
        "[OK] Integridad ventas -> clientes validada."
    )

    # -----------------------------------------------------
    # 4. RELACIONAR VENTAS -> SERVICIOS
    # -----------------------------------------------------

    transformed["ventas"] = add_servicio_id_to_ventas(
        transformed["ventas"],
        transformed["catalogo_servicios"],
    )

    print(
        "[OK] Integridad ventas -> servicios validada."
    )
    
    # -----------------------------------------------------
    # 5. TRANSFORMAR TARIFAS DE SERVICIOS
    # -----------------------------------------------------

    transformed["tarifas_servicios"] = (
        transform_tarifas_servicios(
            transformed["tarifas_servicios"],
            transformed["catalogo_servicios"],
        )
    )

    print(
        "[OK] Integridad tarifas -> servicios validada."
    )

    # -----------------------------------------------------
    # FIN
    # -----------------------------------------------------
    # -----------------------------------------------------
    # 6. CONSTRUIR CATÁLOGO MAESTRO DE PRODUCTOS
    # -----------------------------------------------------

    transformed["catalogo_productos"] = (
        build_catalogo_productos(
            transformed["inventario_productos"],
            transformed["compras_mayorista"],
            transformed["productos_ventas"],
        )
    )

    print(
        "[OK] Catálogo maestro de productos construido."
    )

    # -----------------------------------------------------
    # 7. RELACIONAR VENTAS DE PRODUCTOS
    # -----------------------------------------------------

    transformed["productos_ventas"] = add_producto_id(
        transformed["productos_ventas"],
        transformed["catalogo_productos"],
    )
    
    transformed["productos_ventas"] = (
        add_venta_producto_id(
        transformed["productos_ventas"] )
    
    )

    print(
        "[OK] Integridad productos_ventas -> "
        "catalogo_productos validada."
    )

    # -----------------------------------------------------
    # 8. RELACIONAR COMPRAS MAYORISTAS
    # -----------------------------------------------------

    transformed["compras_mayorista"] = add_producto_id(
        transformed["compras_mayorista"],
        transformed["catalogo_productos"],
    )
    
    transformed["compras_mayorista"] = (
    add_compra_id(
        transformed["compras_mayorista"])
    )

    print(
        "[OK] Integridad compras_mayorista -> "
        "catalogo_productos validada."
    )

    # -----------------------------------------------------
    # 9. RELACIONAR INVENTARIO
    # -----------------------------------------------------

    transformed["inventario_productos"] = add_producto_id(
        transformed["inventario_productos"],
        transformed["catalogo_productos"],
    )

    print(
        "[OK] Integridad inventario_productos -> "
        "catalogo_productos validada."
    )
    
    transformed["gastos"] = add_gasto_id(
        transformed["gastos"]
    )

    print(
    "[OK] Identificadores de gastos validados."
    )
    
        # -----------------------------------------------------
    # CONFIGURACIONES DE COMISIONES
    # -----------------------------------------------------

    transformed["comisiones_barberos"] = (
        build_comisiones_barberos(
            transformed["barberos"]
        )
    )

    print(
        "[OK] Configuraciones de comisiones "
        "de barberos construidas."
    )
    
    print()
    print(
        f"Transformación completada: "
        f"{len(transformed)} tablas."
    )

    return transformed


# =========================================================
# EJECUCIÓN MANUAL / INSPECCIÓN
# =========================================================

if __name__ == "__main__":

    raw_data = extract_data()

    transformed_data = transform_data(raw_data)

    ventas = transformed_data["ventas"]

    print()
    print("=" * 60)
    print("INSPECCIÓN DE VENTAS TRANSFORMADAS")
    print("=" * 60)

    print()
    print("COLUMNAS:")
    print(ventas.columns.tolist())

    print()
    print("TIPOS DE DATOS:")
    print(ventas.dtypes)

    print()
    print("PRIMERAS 5 FILAS:")
    print(ventas.head())

    print()
    print("VALORES NULOS:")
    print(ventas.isna().sum())