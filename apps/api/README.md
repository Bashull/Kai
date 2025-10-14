# Kai API Server

API server para monitorear el estado y salud del sistema Kai.

## Instalación

```bash
npm install
```

## Scripts Disponibles

### Desarrollo
```bash
npm run api:dev
```
Inicia el servidor en modo desarrollo.

### Producción
```bash
npm run api:start
```
Inicia el servidor en modo producción.

### Tests
```bash
npm run test        # Ejecuta tests en modo watch
npm run test:run    # Ejecuta tests una vez
npm run test:ui     # Ejecuta tests con interfaz UI
```

## Endpoints

### GET /status

Retorna información sobre el estado de salud del sistema.

**Respuesta exitosa (200):**
```json
{
  "status": "ok",
  "mode": "development",
  "uptime": 3600,
  "memory": {
    "rss": 50,
    "heapTotal": 30,
    "heapUsed": 20,
    "external": 5
  },
  "timestamp": "2025-10-14T01:33:02.406Z"
}
```

**Campos:**
- `status`: Estado general del sistema ("ok")
- `mode`: Modo de ejecución (development, production, test)
- `uptime`: Tiempo de actividad en segundos
- `memory`: Información de uso de memoria en MB
  - `rss`: Resident Set Size - Memoria total
  - `heapTotal`: Heap total asignado
  - `heapUsed`: Heap utilizado
  - `external`: Memoria externa
- `timestamp`: Timestamp ISO 8601 de la respuesta

### GET /health

Health check simple para verificar que el servidor está respondiendo.

**Respuesta exitosa (200):**
```json
{
  "status": "ok"
}
```

## Documentación Swagger/OpenAPI

La documentación completa de la API está disponible en `openapi.json` en formato OpenAPI 3.1.0.

## Seguridad

- No se expone información sensible (API keys, passwords, tokens, variables de entorno)
- Las respuestas están sanitizadas para evitar fugas de información
- Se validan todas las entradas (aunque /status no recibe parámetros)

## Variables de Entorno

- `PORT`: Puerto en el que escucha el servidor (default: 3000)
- `NODE_ENV`: Modo de ejecución (development, production, test)

## Testing

Los tests unitarios verifican:
- Códigos de respuesta HTTP correctos
- Estructura de datos en las respuestas
- Tipos de datos apropiados
- Ausencia de información sensible
- Consistencia en múltiples llamadas
- Formato correcto de timestamps

Todos los tests están implementados con Vitest y Supertest.
