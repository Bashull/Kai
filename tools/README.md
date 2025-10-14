# Tools - Herramientas de Observabilidad y Monitoreo

Este directorio contiene scripts y herramientas para la observabilidad, monitoreo y mantenimiento del sistema Kai.

## 📋 Contenido

### 🔭 Telemetría

- **`telemetry-collector.cjs`**: Configuración de OpenTelemetry para recopilación de métricas, logs y trazas
  - Auto-instrumentación de Node.js
  - Exportadores para Google Cloud Monitoring y Cloud Trace
  - Métricas personalizadas para llamadas a IA
- **`telemetry-integration-example.cjs`**: Ejemplos de integración de telemetría en la aplicación

### 🚨 Alertas

- **`setup-alerts.cjs`**: Configuración de políticas de alertas en Google Cloud Monitoring
  - Alertas de latencia, errores, recursos y disponibilidad
  - Definición de SLIs/SLOs
  - Integración con canales de notificación

### 📊 Reportes

- **`generate-reports.cjs`**: Generador de reportes automatizados
  - Reportes de rendimiento, disponibilidad, seguridad y CI/CD
  - Múltiples formatos de salida (Markdown, JSON, HTML)
  - Métricas DORA para CI/CD

## 🚀 Uso

### Prerequisitos

Instala las dependencias necesarias:

```bash
npm install --save-dev \
  @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/resources \
  @opentelemetry/semantic-conventions \
  @google-cloud/opentelemetry-cloud-trace-exporter \
  @google-cloud/opentelemetry-cloud-monitoring-exporter \
  @opentelemetry/sdk-metrics \
  @google-cloud/monitoring
```

### Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
GOOGLE_CLOUD_PROJECT=tu-proyecto-gcp
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
NOTIFICATION_CHANNEL_ID=tu-canal-id
```

### Telemetría

#### Inicializar en tu aplicación

```javascript
// En el punto de entrada de tu aplicación
const { initializeTelemetry } = require('./tools/telemetry-collector.cjs');

// Inicializar telemetría
initializeTelemetry();

// Tu código de aplicación...
```

#### Ejecutar ejemplo standalone

```bash
node tools/telemetry-collector.cjs
node tools/telemetry-integration-example.cjs
```

#### Usar tracing personalizado

```javascript
const { setupCustomTracing } = require('./tools/telemetry-collector.cjs');
const { traceAsync } = setupCustomTracing();

// Envolver operaciones con tracing
await traceAsync('mi-operacion', async (span) => {
  // Tu código aquí
  span.setAttribute('custom.attribute', 'valor');
  return resultado;
}, {
  'operation.type': 'database',
  'operation.name': 'query',
});
```

### Alertas

#### Configurar políticas de alertas

```bash
# Modo dry-run (sin crear cambios reales)
node tools/setup-alerts.cjs --dry-run

# Crear políticas
node tools/setup-alerts.cjs

# Limpiar políticas antiguas y crear nuevas
node tools/setup-alerts.cjs --clean
```

#### Crear canal de notificación

```javascript
const { createEmailNotificationChannel } = require('./tools/setup-alerts.cjs');

// Crear canal de email
const channelId = await createEmailNotificationChannel('tu-email@example.com');
console.log('Canal creado:', channelId);
```

## 📊 Métricas Recopiladas

### Métricas de Sistema
- **CPU**: Utilización de CPU por contenedor
- **Memoria**: Uso de memoria heap y RSS
- **Red**: Tráfico de entrada/salida

### Métricas de Aplicación
- **Latencia**: Tiempo de respuesta de requests (p50, p95, p99)
- **Tasa de Errores**: Porcentaje de errores 4xx/5xx
- **Throughput**: Requests por segundo
- **Llamadas a IA**: Contador y latencia de llamadas a Gemini/DeepSeek

### Trazas Distribuidas
- Llamadas HTTP entrantes y salientes
- Operaciones de base de datos
- Llamadas a servicios externos (APIs de IA)
- Operaciones de archivos

## 🚨 Alertas Configuradas

| Alerta | Condición | Severidad | Duración |
|--------|-----------|-----------|----------|
| Alta Latencia | p95 > 2s | WARNING | 5 min |
| Alta Tasa de Errores | Error rate > 1% | ERROR | 5 min |
| Uso Alto de CPU | CPU > 80% | WARNING | 10 min |
| Uso Alto de Memoria | Memoria > 85% | WARNING | 10 min |
| Disponibilidad Baja | Uptime < 99.9% | CRITICAL | 24h |

## 📈 SLIs/SLOs

### Disponibilidad
- **SLI**: % de requests exitosos (no 5xx)
- **SLO**: 99.9%

### Latencia
- **SLI**: % de requests < 500ms
- **SLO**: 95%

### Tasa de Errores
- **SLI**: % de requests sin errores
- **SLO**: 99%

## 🔍 Visualización

### Dashboards de Google Cloud

Accede a tus dashboards en:
- [Cloud Monitoring](https://console.cloud.google.com/monitoring)
- [Cloud Trace](https://console.cloud.google.com/traces)
- [Cloud Logging](https://console.cloud.google.com/logs)

### Consultas de Ejemplo

#### Latencia promedio por endpoint
```sql
fetch cloud_run_revision
| metric 'run.googleapis.com/request_latencies'
| group_by 1m, [percentile(value.request_latencies, 95)]
```

#### Tasa de errores
```sql
fetch cloud_run_revision
| metric 'run.googleapis.com/request_count'
| filter metric.response_code_class == '5xx'
| group_by 5m, [value_request_count_aggregate: aggregate(value.request_count)]
```

## 🛠️ Desarrollo

### Generar Reportes

```bash
# Generar reporte completo en Markdown
node tools/generate-reports.cjs --type=all --format=markdown

# Generar solo reporte de rendimiento en JSON
node tools/generate-reports.cjs --type=performance --format=json

# Generar reporte de seguridad
node tools/generate-reports.cjs --type=security --format=markdown

# Especificar directorio de salida
node tools/generate-reports.cjs --type=all --output=./custom-reports
```

### Agregar Métricas Personalizadas

```javascript
const { createCustomMetrics } = require('./tools/telemetry-collector.cjs');
const { aiCallsCounter } = createCustomMetrics();

// Incrementar contador
aiCallsCounter.add(1, {
  model: 'gemini-pro',
  operation: 'generate',
  status: 'success',
});
```

### Agregar Alertas Personalizadas

Edita `tools/setup-alerts.cjs` y agrega tu política al array `ALERT_POLICIES`:

```javascript
{
  name: 'mi-alerta-personalizada',
  displayName: 'Mi Alerta',
  description: 'Descripción de la alerta',
  conditions: [{
    displayName: 'Condición',
    conditionThreshold: {
      filter: 'tu_filtro_aqui',
      comparison: 'COMPARISON_GT',
      thresholdValue: 100,
      duration: '300s',
    },
  }],
  severity: 'WARNING',
}
```

## 🔗 Referencias

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Google Cloud Monitoring](https://cloud.google.com/monitoring/docs)
- [Google Cloud Trace](https://cloud.google.com/trace/docs)
- [SRE Book - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

## 📝 Notas

- Las métricas se exportan cada 60 segundos por defecto
- Los spans de tracing se muestrean al 100% en desarrollo, 10% en producción
- Las alertas tienen un período de gracia para evitar falsos positivos
- Recuerda configurar los canales de notificación antes de activar alertas

## 🤝 Contribuir

Para agregar nuevas herramientas o mejorar las existentes:

1. Crea un nuevo script en este directorio
2. Documenta su uso en este README
3. Agrega tests si es aplicable
4. Actualiza el plan en `docs/observabilidad-cicd-plan.md`

---

**Última actualización**: 2025-10-14  
**Mantenedor**: Equipo Kai
