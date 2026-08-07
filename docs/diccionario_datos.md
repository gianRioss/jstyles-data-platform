# Diccionario de datos inicial

Este documento se completará después de ejecutar la auditoría automática.

## Tablas operativas previstas

### ventas

Transacciones de servicios de barbería. Incluye fecha, servicio, tarifa histórica,
barbero, medio de pago, propina, descuento, total cobrado, comisión y cliente.

### productos_ventas

Ventas minoristas de productos. La utilidad se obtiene de `utilidad(auto)`.
La comisión del vendedor es del 10 % solo para barberos.

### barberos

Catálogo de personas vinculadas con servicios y porcentajes de comisión.
`elias` representa al dueño y no es un barbero comisionista.

### Clientes

Catálogo de clientes creado desde agosto de 2026. El histórico anterior no
permite identificar clientes individualmente.

### gastos

Gastos comerciales y personales. Los comerciales reducen el resultado del local.
El registro sistemático comienza el 04/08/2026.

### catalogo_servicios

Catálogo estable de servicios con códigos `SER-001` a `SER-006`.

### tarifas_servicios

Historial de precios de servicios por fecha de vigencia.
