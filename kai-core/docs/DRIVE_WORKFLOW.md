# DRIVE WORKFLOW

Flujo seguro:

1. `scanFolder` para inventario.
2. `readFileText` para lectura.
3. Extracción + clasificación temática.
4. Propuesta de actualización de maestro.
5. Escritura solo con backup + aprobaciones + hash.
6. Registro de auditoría.
7. Solo mover a `00_COMPLETA_EXTRACCION_Y_REALOJO` cuando esté integrado.
