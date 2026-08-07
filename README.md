# JStyles Data Platform

Proyecto end-to-end de Ingeniería de Datos, Analytics, Machine Learning y agentes de IA basado en la operación real de la barbería JStyles.

## Objetivo

Transformar el Google Sheets operativo de JStyles en una plataforma de datos reproducible que permita:

- Centralizar ventas de servicios y productos.
- Conservar precios históricos por vigencia.
- Automatizar liquidaciones de barberos.
- Calcular el resultado real del local.
- Analizar clientes, recurrencia y fidelización.
- Cargar datos normalizados en PostgreSQL.
- Construir dashboards, API, modelos predictivos y un agente de IA.

## Fuente inicial

El archivo original se conserva sin modificaciones en:

```text
data/raw/JStyles_OPERATIVO.xlsx
```

### Hojas operativas iniciales

- `barberos`
- `ventas`
- `Clientes`
- `gastos`
- `productos_ventas`
- `compras_mayorista`
- `inventario_productos`
- `catalogo_servicios`
- `tarifas_servicios`

### Hojas de resultados

- `liquidacion`
- `resultado_local`
- `resumen`

### Hojas excluidas del ETL inicial

- `gian`: registro histórico separado de vapers.
- `horarios`: fuera del alcance inicial.
- `productos para comprar`: lista operativa, no tabla transaccional.
- `servicios`: catálogo histórico reemplazado por `catalogo_servicios` y `tarifas_servicios`.

Los nuevos vapers se integrarán en el flujo general de productos mediante una categoría `Vapers`.

## Reglas principales del negocio

- La propina pertenece 100 % al barbero.
- El descuento reduce la base del servicio antes de calcular la comisión.
- La comisión por venta de productos es 10 % del total vendido únicamente cuando vende un barbero.
- Si vende `elias` (dueño) o `Encargado`, la comisión de productos es $0.
- La ganancia de productos usa únicamente `utilidad(auto)`.
- No se vuelve a descontar la compra de mercadería si la utilidad ya considera el costo.
- Los gastos comerciales reducen la ganancia del local; los personales no.
- El registro sistemático de gastos comienza el 04/08/2026.
- Los resultados históricos anteriores a esa fecha son aproximados.

## Etapas del proyecto

1. Auditoría del Excel.
2. Limpieza y normalización con Python.
3. Pipeline ETL reproducible.
4. Modelo relacional y PostgreSQL.
5. Pruebas de calidad de datos.
6. Dashboard de gestión.
7. API para consultas y carga.
8. Machine Learning.
9. Agente de IA para consultas operativas.
10. Docker, documentación y despliegue.

## Instalación inicial

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar la auditoría

```powershell
python src/audit_workbook.py
```

Los resultados se guardan en:

```text
reports/auditoria/
```
