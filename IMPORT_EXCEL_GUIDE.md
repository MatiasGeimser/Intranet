# Guía de Importación de Excel - Inventario IT

## Descripción

La funcionalidad de importación de Excel permite cargar masivamente:
- **Software** con nombres, variantes, versiones y vendors
- **VLANs** con IDs, nombres, descripciones, redes y gateways

## Estructura del Archivo Excel

El archivo debe contener **exactamente 2 hojas** con los siguientes nombres y columnas:

### Hoja 1: "SOFTWARE"

| Columna | Nombre | Tipo | Requerido | Ejemplo |
|---------|--------|------|-----------|---------|
| A | Nombre | String | ✓ | Microsoft Office 365 |
| B | Variantes | String | | Pro, Standard, Home |
| C | Versión | String | | 2024 |
| D | Vendor | String | | Microsoft |
| E | Estado | String | | Activo |

**Notas:**
- El **Nombre** es obligatorio; sin él, la fila se saltará
- El estado puede ser: "Activo", "Inactivo" o "Mantenimiento"
- Las variantes se guardarán en la descripción del software
- Si la fila ya existe (mismo nombre + tipo SOFTWARE), se actualiza

### Hoja 2: "VLAN"

| Columna | Nombre | Tipo | Requerido | Ejemplo |
|---------|--------|------|-----------|---------|
| A | ID VLAN | Número | ✓ | 10 |
| B | Nombre | String | ✓ | Administración |
| C | Descripción | String | | Red de administradores |
| D | Red | String | | 192.168.1.0/24 |
| E | Gateway | String | | 192.168.1.1 |
| F | Estado | String | | Activo |

**Notas:**
- El **ID VLAN** y **Nombre** son obligatorios
- El ID VLAN debe estar entre 1 y 4094
- El estado puede ser: "Activo" o "Inactivo"
- Si la VLAN ya existe (mismo ID), se actualiza

## Validaciones

### Errores Comunes

❌ **Fila omitida - Software sin nombre**
```
Solution: Asegúrate de que cada software tenga un nombre en la columna A
```

❌ **Fila omitida - VLAN sin ID o Nombre**
```
Solution: Completa los campos obligatorios de VLAN
```

❌ **ID VLAN debe estar entre 1 y 4094**
```
Solution: El ID VLAN debe ser un número válido en ese rango
```

❌ **Error de integridad en base de datos**
```
Solution: Puede existir duplicado o problema de conexión; revisa logs del servidor
```

## Ejemplo de Archivo Excel

### Hoja "SOFTWARE"
```
Nombre                      | Variantes        | Versión | Vendor      | Estado
---------------------------|------------------|---------|-------------|----------
Microsoft Office 365        | Pro, Standard    | 2024    | Microsoft   | Activo
Adobe Creative Cloud        | Premium          | 2024    | Adobe       | Activo
Visual Studio Code          |                  | 1.95    | Microsoft   | Activo
```

### Hoja "VLAN"
```
ID VLAN | Nombre          | Descripción                | Red              | Gateway      | Estado
--------|-----------------|----------------------------|------------------|--------------|--------
10      | Administración  | Red de administradores     | 192.168.1.0/24   | 192.168.1.1  | Activo
20      | Usuarios        | Red general de usuarios    | 192.168.2.0/24   | 192.168.2.1  | Activo
30      | Invitados       | Red para visitantes        | 192.168.3.0/24   | 192.168.3.1  | Activo
```

## Cómo Usar

1. **Preparar el archivo Excel**
   - Crea un archivo .xlsx con las dos hojas: "SOFTWARE" y "VLAN"
   - Completa los datos siguiendo la estructura anterior

2. **Acceder a la Importación**
   - Navega a "Inventario IT" en la aplicación
   - Haz clic en el botón "Importar Excel"

3. **Cargar el archivo**
   - Selecciona tu archivo Excel
   - Haz clic en "Procesar y Cargar"

4. **Revisar Resultados**
   - La aplicación mostrará un resumen:
     - Software importado: X
     - VLANs importadas: X
     - Errores encontrados: X
   - Los registros exitosos aparecerán en el inventario inmediatamente

## Actualizaciones

Si cargas un software o VLAN que ya existe (mismo nombre para software, mismo ID para VLAN):
- ✓ Los datos existentes se **actualizarán** con los nuevos valores
- ✓ No se crearán duplicados
- ✓ El historial de auditoría registrará la actualización

## Limitaciones y Consideraciones

- ⚠ El archivo debe tener exactamente las hojas "SOFTWARE" y "VLAN"
- ⚠ Máximo 10MB por archivo
- ⚠ Los registros se insertan/actualizan en transacción (todo o nada por hoja)
- ⚠ Es recomendable hacer backup de la base de datos antes de importaciones masivas
- ⚠ Todas las importaciones se registran en auditoría del sistema

## Resolución de Problemas

### El archivo no se acepta
- Verifica que sea Excel (.xlsx o .xls)
- Comprueba que no exceda 10MB
- Intenta abrirlo en Excel para verificar que no está corrupto

### Algunas filas se saltan
- Revisa la columna de errores en la respuesta
- Verifica que los campos obligatorios estén completos
- Asegúrate de que los IDs de VLAN sean numéricos y estén en rango

### La importación es lenta
- Si tienes miles de registros, considera dividirlo en múltiples archivos
- La importación se procesa una fila a la vez para validación

---
**Última actualización:** 2024
**Versión:** 1.0
