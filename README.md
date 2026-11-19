# JStyles Data Platform

Proyecto end-to-end de **Data Engineering, Analytics y evolución hacia Machine Learning e Inteligencia Artificial**, construido sobre datos reales de la barbería JStyles.

El objetivo es transformar una operación inicialmente administrada mediante Google Sheets/Excel en una plataforma de datos reproducible, auditable y preparada para crecer hacia PostgreSQL, Power BI, APIs, Machine Learning y agentes de IA.

---

## Objetivo

Construir una plataforma que permita:

- Centralizar ventas de servicios y productos.
- Normalizar clientes, barberos, servicios y productos.
- Preservar tarifas y reglas de comisión históricas.
- Controlar compras, inventario y gastos.
- Calcular resultados del negocio con reglas reproducibles.
- Detectar problemas de calidad de datos antes de cargar información.
- Cargar datos estructurados en PostgreSQL.
- Preparar modelos analíticos para Power BI.
- Incorporar posteriormente API, Machine Learning y agentes de IA.

---

# Arquitectura actual

La versión actual del proyecto implementa:

```text
Google Sheets / Excel
        ↓
     Extract
        ↓
    Transform
        ↓
 Validaciones
        ↓
      Save
        ↓
 CSV procesados
        ↓
   PostgreSQL
```

Actualmente PostgreSQL está diseñado mediante un esquema relacional inicial.

La evolución prevista será:

```text
Google Sheets
      ↓
Extract
      ↓
RAW
      ↓
Transform
      ↓
STAGING
      ↓
PostgreSQL CORE
      ↓
MARTS
      ↓
Power BI / API / ML / AI
```

Las capas `raw`, `staging`, `core` y `marts` forman parte del roadmap y todavía no están completamente implementadas.

---

# Fuente de datos

El origen del proyecto es el archivo operativo:

```text
data/raw/JStyles_OPERATIVO.xlsx
```

El archivo real no se versiona en GitHub.

## Hojas utilizadas por el ETL

- `barberos`
- `ventas`
- `Clientes`
- `gastos`
- `tarifas_servicios`
- `catalogo_servicios`
- `productos_ventas`
- `compras_mayorista`
- `inventario_productos`

## Hojas excluidas del ETL inicial

- `gian`
- `horarios`
- `productos para comprar`
- `servicios`

Estas hojas se conservan en la fuente original pero no forman parte del modelo analítico actual.

---

# Reglas principales del negocio

El ETL incorpora reglas reales de JStyles.

### Servicios

- La propina pertenece 100 % al barbero.
- Los descuentos reducen la base del servicio antes del cálculo de comisión.
- Las tarifas se modelan mediante períodos de vigencia.
- Las ventas históricas conservan el valor realmente registrado.

### Productos

- La comisión por venta de productos corresponde al 10 % del total cuando el vendedor es un barbero.
- Las ventas realizadas por el propietario o encargado no generan comisión para un barbero.
- La utilidad del producto se conserva independientemente del valor bruto vendido.
- Compras, ventas e inventario se relacionan mediante `producto_id`.

### Gastos

Los gastos se clasifican en:

```text
comercial
personal
```

Solo los gastos comerciales afectan el resultado operativo del local.

---

# ETL

El ETL principal se encuentra en:

```text
src/etl/
```

Actualmente incluye:

```text
extract.py
transform.py
save.py
load.py
```

## Extract

`extract.py` lee las hojas operativas del Excel y genera DataFrames para su procesamiento.

## Transform

`transform.py`:

- elimina filas vacías o auxiliares;
- normaliza nombres de columnas;
- convierte fechas y horas;
- estandariza tipos de datos;
- normaliza nombres de clientes, servicios, barberos y productos;
- identifica transacciones reales;
- corrige anomalías históricas documentadas;
- crea claves técnicas y relaciones;
- valida integridad referencial;
- genera catálogos maestros;
- preserva información histórica.

## Save

`save.py` genera los datasets procesados en:

```text
data/processed/
```

## Load

`load.py` prepara los datasets y los carga en PostgreSQL mediante SQLAlchemy.

La versión actual utiliza una estrategia de **full refresh**:

```text
TRUNCATE
    ↓
carga completa
```

La carga se ejecuta dentro de una única transacción.

Si una tabla falla, PostgreSQL revierte la operación completa para evitar estados parciales.

La evolución hacia `UPSERT`, incrementalidad e idempotencia completa forma parte del próximo bloque del proyecto.

---

# Datasets procesados

Actualmente el pipeline genera 11 datasets:

```text
ventas.csv
barberos.csv
clientes.csv
catalogo_servicios.csv
tarifas_servicios.csv
catalogo_productos.csv
productos_ventas.csv
compras_mayorista.csv
inventario_productos.csv
gastos.csv
comisiones_barberos.csv
```

---

# Modelo de entidades

## Barberos

Clave principal:

```text
barbero_id
```

Incluye configuración actual, estado y condición de propietario.

## Clientes

Clave principal:

```text
cliente_id
```

Los clientes históricos que no fueron registrados individualmente no se inventan ni se asignan artificialmente.

## Servicios

Los nombres históricos se normalizan hacia servicios estables.

Ejemplo:

```text
corte
corte_new
corte_new1
corte_promo
        ↓
SER-001
```

Esto permite separar:

```text
identidad del servicio
≠
precio histórico
```

## Tarifas de servicios

Las tarifas incluyen:

```text
tarifa_id
servicio_id
precio
fecha_desde
fecha_hasta
vigente
```

Esto preserva cambios de precio a lo largo del tiempo.

---

# Comisiones históricas

Las comisiones de los barberos se modelan mediante una tabla independiente:

```text
comisiones_barberos
```

Incluye:

```text
comision_config_id
barbero_id
porcentaje_barbero
porcentaje_local
esquema
fecha_desde
fecha_hasta
observado_desde
observado_hasta
origen
es_configuracion_actual
```

Esto permite distinguir entre:

- configuración actual;
- evidencia histórica observada;
- vigencia contractual conocida;
- vigencia desconocida.

El enfoque utiliza principios de **historización temporal**, relacionados con patrones de Slowly Changing Dimensions.

No se inventan fechas de vigencia cuando no existe evidencia suficiente.

---

# Productos

Se construye un catálogo maestro:

```text
catalogo_productos
```

Los productos encontrados en:

```text
inventario
compras
ventas
```

se consolidan mediante `producto_id`.

Los productos que no pueden relacionarse con seguridad se mantienen y se marcan para revisión en lugar de eliminarlos o fusionarlos arbitrariamente.

---

# Claves transaccionales

El proyecto ya utiliza identificadores propios para las principales operaciones:

```text
ticket_id
venta_producto_id
compra_id
gasto_id
```

Esto permite preparar las tablas para integridad de datos y futuras cargas incrementales.

---

# Calidad de datos

El pipeline valida, entre otras cosas:

- tickets duplicados;
- IDs duplicados;
- relaciones barbero → venta;
- relaciones cliente → venta;
- relaciones servicio → venta;
- relaciones producto → venta;
- relaciones producto → compra;
- relaciones producto → inventario;
- cantidades válidas;
- porcentajes de comisión;
- fechas inválidas;
- rangos de tarifas;
- consistencia entre comisión del barbero y comisión del local.

La filosofía del proyecto es:

```text
Fuente
   ↓
Validación
   ↓
Transformación
   ↓
Validación
   ↓
PostgreSQL
```

Los problemas de datos no se eliminan silenciosamente: se corrigen cuando existe evidencia o se conservan como anomalías identificadas.

---

# PostgreSQL

El esquema inicial se encuentra en:

```text
sql/schema.sql
```

Actualmente incluye las tablas:

```text
barberos
clientes
servicios
tarifas_servicios
ventas_servicios
productos
ventas_productos
compras_productos
inventario_productos
gastos
comisiones_barberos
```

El modelo incorpora:

- Primary Keys;
- Foreign Keys;
- `CHECK constraints`;
- restricciones de porcentaje;
- restricciones de fechas;
- índices para consultas frecuentes;
- unicidad de configuraciones actuales de comisión.

---

# Instalación

Crear entorno virtual:

```powershell
python -m venv .venv
```

Activarlo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Actualizar pip:

```powershell
python -m pip install --upgrade pip
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

---

# Auditoría inicial

Ejecutar:

```powershell
python src/audit_workbook.py
```

Los resultados de auditoría se generan en:

```text
reports/auditoria/
```

---

# Ejecutar transformación

```powershell
python src/etl/transform.py
```

---

# Generar datasets procesados

```powershell
python src/etl/save.py
```

Los archivos resultantes se generan en:

```text
data/processed/
```

---

# PostgreSQL

La conexión utiliza variables de entorno.

Ejemplo de configuración:

```text
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_SCHEMA=
```

Las credenciales reales no deben almacenarse en GitHub.

La estructura de tablas está definida en:

```text
sql/schema.sql
```

La carga se ejecuta mediante:

```powershell
python src/etl/load.py
```

---

# Estado actual

## Implementado

- Auditoría del workbook.
- Extracción de 9 hojas operativas.
- Transformación y normalización con Python.
- Catálogo estable de servicios.
- Historial de tarifas.
- Catálogo maestro de productos.
- Relaciones mediante claves técnicas.
- Limpieza de ventas de servicios.
- Limpieza de ventas de productos.
- Limpieza de compras.
- Limpieza de inventario.
- Clasificación de gastos.
- Historización de configuraciones de comisión.
- Validaciones de integridad.
- Generación de 11 datasets procesados.
- Esquema relacional inicial de PostgreSQL.
- Loader PostgreSQL mediante SQLAlchemy.
- Carga completa dentro de una transacción.

## En desarrollo

- Pruebas automáticas de calidad.
- Prueba formal de idempotencia.
- Prueba con nuevos registros posteriores al snapshot inicial.
- Cargas incrementales.
- Estrategia `UPSERT`.
- Auditoría de ejecuciones del pipeline.
- Arquitectura PostgreSQL por capas.

## Roadmap

```text
ETL actual
    ↓
Pruebas de calidad
    ↓
Idempotencia + incrementalidad
    ↓
PostgreSQL
raw → staging → core → marts
    ↓
Modelo dimensional
    ↓
Power BI
    ↓
FastAPI
    ↓
Machine Learning
    ↓
AI Agent
    ↓
Docker
    ↓
CI/CD
```

---

# Analytics

La futura capa analítica incluirá modelos orientados a:

- facturación;
- ganancia neta;
- margen;
- comisiones;
- ticket promedio;
- rentabilidad por barbero;
- servicios más demandados;
- ventas de productos;
- inventario;
- compras;
- clientes recurrentes;
- clientes inactivos.

Power BI consumirá principalmente modelos analíticos y marts, no tablas operativas sin modelar.

---

# Machine Learning

Machine Learning se incorporará únicamente cuando exista una pregunta de negocio respaldada por suficientes datos.

Un posible caso es:

```text
predicción de churn / abandono de clientes
```

Algunas features futuras:

```text
dias_desde_ultima_visita
visitas_90_dias
ticket_promedio
frecuencia
servicio_favorito
barbero_frecuente
descuentos_utilizados
```

---

# Agente de IA

La evolución final contempla un agente que utilice herramientas y datos reales.

Ejemplos:

```text
¿Cuánto ganó el local este mes?

¿Qué barbero generó mayor facturación?

¿Qué productos necesitan reposición?

¿Qué clientes llevan más de 45 días sin venir?

¿Cuáles tienen mayor riesgo de abandono?
```

El agente deberá consultar PostgreSQL, APIs y modelos de Machine Learning antes de responder.

No se utilizará un chatbot que invente valores.

---

# Escalabilidad futura

La arquitectura actual está diseñada deliberadamente con tecnologías adecuadas para el volumen real de JStyles:

```text
Python + PostgreSQL
```

Una futura versión experimental podrá estudiar cómo escalar la plataforma si JStyles tuviera múltiples sucursales y millones de operaciones utilizando tecnologías como:

```text
Databricks
PySpark
Data Lake
Lakehouse
Bronze / Silver / Gold
```

Estas tecnologías corresponden a una posible V2 y no forman parte de la implementación actual.

---

# Principio del proyecto

JStyles Data Platform busca demostrar cómo evolucionar datos operativos reales hacia una plataforma profesional:

```text
Datos reales
    ↓
Data Engineering
    ↓
Data Quality
    ↓
PostgreSQL
    ↓
Analytics
    ↓
Machine Learning
    ↓
AI Engineering
```

El proyecto prioriza reproducibilidad, trazabilidad, calidad de datos y decisiones técnicas justificadas por encima de agregar tecnologías sin necesidad.