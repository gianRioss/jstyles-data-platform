# JStyles Data Platform

Proyecto end-to-end de **Data Engineering, Analytics y evolución hacia Machine Learning e Inteligencia Artificial**, construido sobre datos operativos reales de la barbería JStyles.

El objetivo es transformar una operación inicialmente administrada mediante Google Sheets/Excel en una plataforma de datos **reproducible, auditable, incremental y preparada para crecer** hacia PostgreSQL, Power BI, APIs, Machine Learning y agentes de IA.

---

## Objetivo

Construir una plataforma que permita:

- Centralizar ventas de servicios y productos.
- Normalizar clientes, barberos, servicios y productos.
- Preservar tarifas y reglas de comisión históricas.
- Controlar compras, inventario y gastos.
- Calcular resultados del negocio mediante reglas reproducibles.
- Detectar problemas de calidad antes de cargar información.
- Ejecutar cargas incrementales e idempotentes en PostgreSQL.
- Auditar cada ejecución del pipeline.
- Preparar modelos analíticos para Power BI.
- Incorporar posteriormente APIs, Machine Learning y agentes de IA.

---

# Arquitectura actual

La versión actual implementa un pipeline end-to-end:

```text
Google Sheets / Excel
        ↓
     Extract
        ↓
    Transform
        ↓
 Data Quality Gate
        ↓
 Save processed CSVs
        ↓
 PostgreSQL UPSERT
        ↓
   Run Audit
```

El flujo principal puede ejecutarse desde un único comando:

```powershell
python src/etl/pipeline.py
```

Actualmente PostgreSQL utiliza un esquema relacional inicial denominado `jstyles`.

La evolución arquitectónica prevista es:

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

El origen principal del proyecto es:

```text
data/raw/JStyles_OPERATIVO.xlsx
```

El archivo operativo real no se versiona en GitHub.

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

Estas hojas se conservan en la fuente original, pero no forman parte del modelo analítico actual.

---

# Reglas principales del negocio

El ETL implementa reglas reales de funcionamiento de JStyles.

## Servicios

- La propina pertenece 100 % al barbero.
- Los descuentos reducen la base del servicio antes del cálculo de comisión.
- Las tarifas se modelan mediante períodos de vigencia.
- Las ventas históricas conservan el valor registrado originalmente.
- Los servicios mantienen una identidad estable aunque su precio cambie.

## Productos

- La comisión por venta de productos corresponde al 10 % cuando el vendedor es un barbero.
- Las ventas realizadas por el propietario o encargado no generan comisión para un barbero.
- La utilidad del producto se conserva independientemente del valor bruto vendido.
- Compras, ventas e inventario se relacionan mediante `producto_id`.

## Gastos

Los gastos se clasifican en:

```text
comercial
personal
```

Solo los gastos comerciales afectan el resultado operativo del local.

---

# ETL

Los módulos principales se encuentran en:

```text
src/etl/
```

La estructura actual incluye:

```text
extract.py
transform.py
quality.py
save.py
load.py
load_incremental.py
run_logger.py
pipeline.py
```

---

## Extract

`extract.py` lee las hojas operativas del workbook y genera DataFrames para su procesamiento.

En el snapshot actualmente utilizado se extraen:

```text
9 hojas
3333 filas raw
```

---

## Transform

`transform.py` se encarga de:

- eliminar filas vacías o auxiliares;
- normalizar nombres de columnas;
- convertir fechas y horas;
- estandarizar tipos de datos;
- normalizar clientes, servicios, barberos y productos;
- identificar transacciones reales;
- corregir anomalías históricas cuando existe evidencia;
- crear claves técnicas;
- construir relaciones entre entidades;
- validar integridad referencial;
- generar catálogos maestros;
- preservar información histórica;
- construir configuraciones históricas de comisiones.

La transformación actual genera:

```text
11 tablas
2102 filas transformadas
```

---

# Data Quality

`quality.py` implementa un Data Quality Gate posterior a la transformación.

Se validan, entre otros aspectos:

- Primary Keys nulas.
- Primary Keys duplicadas.
- Foreign Keys.
- Ventas relacionadas con barberos.
- Ventas relacionadas con clientes.
- Ventas relacionadas con servicios.
- Tarifas relacionadas con servicios.
- Ventas de productos relacionadas con productos.
- Compras relacionadas con productos.
- Inventario relacionado con productos.
- Configuraciones de comisión relacionadas con barberos.
- Precios no negativos.
- Totales no negativos.
- Propinas no negativas.
- Comisiones no negativas.
- Descuentos entre 0 y 1.
- Rangos de vigencia de tarifas.
- Cantidades de productos.
- Costos de compras.
- Tipos de gastos.
- Porcentajes de comisión.
- Suma de porcentajes barbero + local.
- Existencia de una única configuración actual por barbero.

Una ejecución real actualmente produce:

```text
PASS = 35
WARN = 3
FAIL = 0
```

Los warnings corresponden a anomalías conocidas que se conservan para revisión:

```text
1 fecha inválida histórica en ventas de productos
6 productos pendientes de revisión
2 conflictos de precio detectados en inventario
```

Si aparece al menos un control crítico con estado `FAIL`, el pipeline se detiene antes de cargar PostgreSQL.

Los problemas de datos no se eliminan silenciosamente: se corrigen cuando existe evidencia suficiente o se conservan identificados para revisión.

---

# Datasets procesados

`save.py` genera 11 datasets en:

```text
data/processed/
```

Archivos actuales:

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

En la última ejecución validada:

```text
2102 filas transformadas
2102 filas guardadas
```

---

# Modelo de entidades

## Barberos

Clave principal:

```text
barbero_id
```

Incluye información de configuración actual, estado y condición de propietario.

---

## Clientes

Clave principal:

```text
cliente_id
```

Los clientes históricos que nunca fueron registrados individualmente no se inventan ni se asignan artificialmente.

---

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

---

# Tarifas de servicios

Las tarifas incluyen:

```text
tarifa_id
servicio_id
precio
fecha_desde
fecha_hasta
vigente
```

Esto permite preservar cambios de precio sin modificar ventas históricas.

---

# Comisiones históricas

Las configuraciones de comisión se almacenan en:

```text
comisiones_barberos
```

Incluyen:

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

El diseño utiliza principios de **historización temporal**, relacionados con patrones de Slowly Changing Dimensions.

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

Actualmente el catálogo contiene:

```text
146 productos
```

Los productos que no pueden relacionarse con seguridad se mantienen y se marcan para revisión en lugar de eliminarlos o fusionarlos arbitrariamente.

---

# Claves transaccionales

Las principales operaciones utilizan identificadores propios:

```text
ticket_id
venta_producto_id
compra_id
gasto_id
```

Los identificadores derivados son determinísticos cuando corresponde.

Esto permite:

- identificar transacciones;
- evitar duplicados;
- mantener estabilidad entre ejecuciones;
- implementar cargas incrementales;
- ejecutar UPSERT sobre PostgreSQL.

---

# PostgreSQL

La definición relacional inicial se encuentra en:

```text
sql/schema.sql
```

Actualmente el esquema `jstyles` contiene:

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

- Primary Keys.
- Foreign Keys.
- `CHECK constraints`.
- Restricciones de porcentajes.
- Restricciones de fechas.
- Índices.
- Unicidad de configuraciones actuales de comisión.

---

# Carga incremental PostgreSQL

La carga utilizada actualmente por el pipeline se encuentra en:

```text
src/etl/load_incremental.py
```

Implementa:

```text
INSERT ... ON CONFLICT DO UPDATE
```

Comportamiento:

```text
PK nueva
   ↓
INSERT

PK existente
   ↓
UPDATE

misma ejecución repetida
   ↓
sin duplicar la PK
```

La carga incremental:

- no ejecuta `TRUNCATE`;
- inserta registros nuevos;
- actualiza registros ya existentes;
- utiliza las Primary Keys reales de PostgreSQL;
- se ejecuta dentro de una transacción;
- respeta el orden de dependencias entre tablas.

`load.py` permanece como módulo base para conexión, preparación de datasets y soporte de la implementación inicial de carga completa.

El flujo productivo actual utiliza `load_incremental.py`.

---

# Idempotencia e incrementalidad

La estrategia incremental fue validada tanto a nivel de transformación como directamente sobre PostgreSQL.

## Estabilidad del ETL

Existe una prueba automática que agrega operaciones simuladas posteriores al snapshot original y valida que:

- los registros históricos permanezcan;
- los IDs históricos no cambien;
- nuevos registros aparezcan una sola vez;
- no se generen duplicados;
- tarifas históricas permanezcan estables;
- configuraciones de comisión permanezcan estables;
- una segunda ejecución genere exactamente los mismos identificadores.

Archivo:

```text
tests/test_incremental_stability.py
```

---

## UPSERT real en PostgreSQL

También existe una prueba contra PostgreSQL real:

```text
tests/test_load_incremental.py
```

La prueba:

1. inserta una fila sintética con una PK nueva;
2. vuelve a enviar la misma PK con valores modificados;
3. valida que PostgreSQL actualice el registro;
4. confirma que siga existiendo una única fila;
5. ejecuta `ROLLBACK`;
6. comprueba que la base real quede intacta.

Por lo tanto se encuentran validados:

```text
INSERT por PK nueva
UPDATE por PK existente
ausencia de duplicados por PK
ROLLBACK
idempotencia del snapshot actual
```

---

# Auditoría del pipeline

Cada ejecución del pipeline genera un identificador único:

```text
run_id
```

El módulo responsable es:

```text
src/etl/run_logger.py
```

Los registros se almacenan en formato JSONL en:

```text
reports/pipeline_runs/pipeline_runs.jsonl
```

El archivo generado no se versiona en GitHub.

Cada ejecución registra:

```text
run_id
pipeline
started_at
finished_at
duration_seconds
status

rows_extracted
rows_transformed
rows_saved
rows_loaded_db

quality_pass
quality_warn
quality_fail

error_type
error_message
```

Esto permite conocer el estado y las métricas alcanzadas incluso si el pipeline falla a mitad de ejecución.

---

# Última ejecución validada

Una ejecución end-to-end real produjo:

```text
Filas extraídas:             3333
Filas transformadas:         2102
Filas guardadas CSV:         2102
Filas procesadas PostgreSQL: 2102

Quality Gate:
PASS = 35
WARN = 3
FAIL = 0

Status:
SUCCESS
```

La carga PostgreSQL conserva:

```text
barberos:               13
clientes:                6
comisiones_barberos:    14
compras_productos:     145
gastos:                  5
inventario_productos:  140
productos:             146
servicios:              12
tarifas_servicios:      12
ventas_productos:      583
ventas_servicios:     1026
```

Total:

```text
2102 filas
```

---

# Tests automatizados

La suite actual se ejecuta mediante:

```powershell
python -m pytest -v
```

Estado validado:

```text
8 passed
```

La suite cubre:

```text
tests/test_incremental_stability.py
tests/test_load_incremental.py
tests/test_quality.py
tests/test_run_logger.py
```

Actualmente existen dos `FutureWarning` de pandas asociados al helper utilizado por `test_incremental_stability.py`.

Los warnings no representan fallos funcionales del pipeline.

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

# Variables de entorno

PostgreSQL utiliza variables definidas localmente.

Ejemplo:

```text
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_SCHEMA=
```

Puede utilizarse:

```text
.env.example
```

como referencia.

Las credenciales reales del archivo `.env` no deben almacenarse en GitHub.

---

# Ejecución

## Pipeline completo

La forma recomendada de ejecutar el proyecto es:

```powershell
python src/etl/pipeline.py
```

Esto ejecuta:

```text
Extract
   ↓
Transform
   ↓
Data Quality
   ↓
Save CSV
   ↓
PostgreSQL UPSERT
   ↓
Run Audit
```

---

## Solo extracción / transformación

```powershell
python src/etl/transform.py
```

---

## Solo generación de datasets procesados

```powershell
python src/etl/save.py
```

---

## Solo carga incremental PostgreSQL

```powershell
python src/etl/load_incremental.py
```

---

## Tests

```powershell
python -m pytest -v
```

---

# Auditoría del workbook original

También se mantienen herramientas separadas para analizar la fuente original.

Auditoría estructural:

```powershell
python src/audit_workbook.py
```

Auditoría de calidad sobre datos raw:

```powershell
python src/audit_quality.py
```

Los resultados se almacenan en:

```text
reports/auditoria/
reports/auditoria_calidad/
```

Estas auditorías son independientes del Data Quality Gate posterior a la transformación.

---

# Estado actual

## Implementado

- Auditoría del workbook.
- Extracción de 9 hojas operativas.
- Transformación y normalización con Python.
- Catálogo estable de servicios.
- Historial de tarifas.
- Catálogo maestro de productos.
- Claves técnicas estables.
- Limpieza de ventas de servicios.
- Limpieza de ventas de productos.
- Limpieza de compras.
- Limpieza de inventario.
- Clasificación de gastos.
- Historización de configuraciones de comisión.
- Validaciones de integridad referencial.
- Generación de 11 datasets procesados.
- Data Quality Gate automatizado.
- 35 controles de calidad aprobados en el snapshot actual.
- Manejo explícito de warnings de calidad.
- Esquema relacional PostgreSQL.
- Loader PostgreSQL mediante SQLAlchemy.
- Carga incremental mediante UPSERT.
- Eliminación de `TRUNCATE` del flujo incremental.
- Idempotencia del snapshot actual.
- Prueba de estabilidad con nuevas operaciones simuladas.
- Test de INSERT y UPDATE real en PostgreSQL.
- Rollback automático del test de integración.
- Pipeline end-to-end ejecutable desde un único comando.
- Auditoría de ejecuciones mediante `run_id`.
- Métricas de extracción, transformación, guardado y carga PostgreSQL.
- Registro de errores.
- Suite automatizada con 8 tests.

---

## Próximo bloque

La siguiente evolución arquitectónica será separar PostgreSQL en capas:

```text
raw
 ↓
staging
 ↓
core
 ↓
marts
```

El esquema `jstyles` actual funciona como primer modelo relacional cercano a una capa `core`, pero todavía no se ha realizado la separación física completa.

---

# Roadmap

```text
ETL end-to-end
      ✅
Data Quality
      ✅
Idempotencia
      ✅
UPSERT incremental
      ✅
Auditoría de ejecuciones
      ✅
PostgreSQL por capas
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

La futura capa analítica estará orientada a métricas como:

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

Power BI consumirá principalmente modelos analíticos y marts en lugar de tablas operativas sin modelar.

---

# Modelo dimensional futuro

La capa analítica contempla un modelo similar a:

```text
fact_ventas
dim_fecha
dim_cliente
dim_barbero
dim_servicio
dim_producto
```

Esto permitirá desacoplar las consultas analíticas del modelo operacional.

---

# FastAPI

Una futura API permitirá exponer datos y servicios de la plataforma desde PostgreSQL.

Entre los posibles endpoints:

```text
ventas
clientes
barberos
servicios
productos
inventario
resultados
predicciones
```

La API se incorporará después de consolidar las capas analíticas y el modelo PostgreSQL.

---

# Machine Learning

Machine Learning se incorporará únicamente cuando exista una pregunta de negocio respaldada por suficientes datos.

Uno de los posibles casos es:

```text
predicción de churn / abandono de clientes
```

Features potenciales:

```text
dias_desde_ultima_visita
visitas_90_dias
ticket_promedio
frecuencia
servicio_favorito
barbero_frecuente
descuentos_utilizados
```

No se implementará un modelo únicamente para agregar tecnología al proyecto: deberá responder a una necesidad real del negocio.

---

# Agente de IA

La evolución final contempla un agente capaz de utilizar herramientas y datos reales.

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

La arquitectura actual utiliza tecnologías adecuadas al volumen real del negocio:

```text
Python
PostgreSQL
```

Una futura versión experimental podría estudiar cómo escalar la plataforma ante múltiples sucursales o millones de operaciones mediante tecnologías como:

```text
Databricks
PySpark
Data Lake
Lakehouse
Bronze / Silver / Gold
```

Estas tecnologías corresponden a una posible V2 y no forman parte de la implementación actual.

---

# Principios del proyecto

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

El proyecto prioriza:

- reproducibilidad;
- trazabilidad;
- calidad de datos;
- idempotencia;
- integridad referencial;
- reglas de negocio documentadas;
- decisiones técnicas justificadas;
- pruebas automatizadas;
- evolución incremental de la arquitectura.

El objetivo no es agregar tecnologías sin necesidad, sino construir una solución que pueda crecer manteniendo consistencia, auditabilidad y valor real para el negocio.