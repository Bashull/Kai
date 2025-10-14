# 🚀 Quick Start - Observabilidad y CI/CD

Esta guía de inicio rápido te ayudará a poner en marcha las soluciones de observabilidad y CI/CD implementadas para Kai.

## 📋 Contenido

- [Estructura del Proyecto](#estructura-del-proyecto)
- [Inicio Rápido](#inicio-rápido)
- [Configuración](#configuración)
- [Uso](#uso)
- [Próximos Pasos](#próximos-pasos)

## 📁 Estructura del Proyecto

```
Kai/
├── .github/
│   ├── workflows/
│   │   ├── ci-cd.yml              # Pipeline CI/CD paralelo
│   │   └── README.md              # Documentación de workflows
│   └── dependabot.yml             # Configuración de Dependabot
├── docs/
│   └── observabilidad-cicd-plan.md # Plan detallado en 5 pasos
├── tools/
│   ├── telemetry-collector.cjs    # Recopilación de telemetría
│   ├── telemetry-integration-example.cjs  # Ejemplos de integración
│   ├── setup-alerts.cjs           # Configuración de alertas
│   ├── generate-reports.cjs       # Generador de reportes
│   └── README.md                  # Documentación de herramientas
└── package.json                   # Dependencias de OpenTelemetry
```

## 🚀 Inicio Rápido

### 1. Instalar Dependencias

```bash
npm install
```

Las dependencias de OpenTelemetry ya están incluidas en `package.json`:
- `@opentelemetry/sdk-node`
- `@opentelemetry/auto-instrumentations-node`
- `@google-cloud/opentelemetry-cloud-trace-exporter`
- `@google-cloud/opentelemetry-cloud-monitoring-exporter`
- `@google-cloud/monitoring`

### 2. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
# Google Cloud Project
GOOGLE_CLOUD_PROJECT=tu-proyecto-gcp

# Opcional: Ruta a credenciales
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Opcional: Canal de notificación
NOTIFICATION_CHANNEL_ID=canal-123
```

### 3. Probar Telemetría

```bash
# Ejecutar ejemplo de telemetría
node tools/telemetry-collector.cjs

# Ejecutar ejemplo de integración
node tools/telemetry-integration-example.cjs
```

### 4. Generar un Reporte

```bash
# Generar reporte completo
node tools/generate-reports.cjs --type=all --format=markdown

# Ver el reporte generado
cat reports/kai-report-all-*.md
```

## ⚙️ Configuración

### Telemetría en tu Aplicación

Para habilitar telemetría en tu aplicación, agrega al inicio de tu archivo principal:

```javascript
// En src/index.js o tu punto de entrada
const { initializeTelemetry } = require('./tools/telemetry-collector.cjs');

// Inicializar telemetría
initializeTelemetry();

// Tu código de aplicación...
```

### Configurar Alertas en Google Cloud

```bash
# Modo dry-run (previsualizar cambios)
node tools/setup-alerts.cjs --dry-run

# Crear políticas de alertas
node tools/setup-alerts.cjs

# Limpiar políticas antiguas y crear nuevas
node tools/setup-alerts.cjs --clean
```

### CI/CD con GitHub Actions

El pipeline de CI/CD se ejecuta automáticamente en:
- Push a `main`, `develop`, `feat/**`
- Pull Requests a `main`, `develop`

**Configurar Secrets en GitHub**:

1. Ve a Settings > Secrets and variables > Actions
2. Agrega los siguientes secrets:
   - `GCP_PROJECT_ID`: ID de tu proyecto GCP
   - `GCP_SA_KEY`: Clave de cuenta de servicio
   - `SNYK_TOKEN`: Token de Snyk (opcional)

## 📊 Uso

### Dashboards de Monitoreo

Accede a tus dashboards en Google Cloud:

- **Monitoring**: https://console.cloud.google.com/monitoring
- **Trace**: https://console.cloud.google.com/traces
- **Logging**: https://console.cloud.google.com/logs

### Métricas Capturadas

El sistema recopila automáticamente:

- ✅ **Latencia**: p50, p95, p99 de todas las requests
- ✅ **Throughput**: Requests por segundo
- ✅ **Error Rate**: Tasa de errores 4xx/5xx
- ✅ **Recursos**: CPU, memoria, red
- ✅ **AI Calls**: Llamadas a Gemini/DeepSeek
- ✅ **Trazas**: Distributed tracing de todas las operaciones

### Alertas Configuradas

| Alerta | Condición | Acción |
|--------|-----------|--------|
| Alta Latencia | P95 > 2s | Notificación |
| Error Rate | > 1% en 5min | Notificación |
| CPU Alta | > 80% por 10min | Notificación |
| Memoria Alta | > 85% por 10min | Notificación |
| Baja Disponibilidad | < 99.9% uptime | Alerta crítica |

### Reportes Automatizados

Genera reportes periódicos:

```bash
# Reporte de rendimiento
node tools/generate-reports.cjs --type=performance

# Reporte de disponibilidad
node tools/generate-reports.cjs --type=availability

# Reporte de seguridad
node tools/generate-reports.cjs --type=security

# Reporte de CI/CD (métricas DORA)
node tools/generate-reports.cjs --type=cicd

# Reporte completo
node tools/generate-reports.cjs --type=all
```

Formatos disponibles:
- `--format=markdown` (default)
- `--format=json`
- `--format=html` (próximamente)

### CI/CD Pipeline

El pipeline ejecuta los siguientes jobs en paralelo:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    Lint     │  │    Tests    │  │    Build    │  │  Security   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
       ↓                ↓                 ↓                ↓
       └────────────────┴─────────────────┴────────────────┘
                            ↓
                    ┌─────────────┐
                    │   Deploy    │
                    └─────────────┘
                            ↓
                    ┌─────────────┐
                    │   Report    │
                    └─────────────┘
```

**Tiempo de ejecución**: ~4 minutos (vs ~19 minutos secuencial)

## 📚 Documentación Detallada

Para más información, consulta:

- **Plan Completo**: [`docs/observabilidad-cicd-plan.md`](docs/observabilidad-cicd-plan.md)
  - Arquitectura detallada
  - Diagrama ASCII
  - 5 pasos de implementación
  - Roadmap y métricas de éxito

- **Herramientas**: [`tools/README.md`](tools/README.md)
  - Guía de uso de cada herramienta
  - Ejemplos de código
  - Referencia de APIs
  - Troubleshooting

- **Workflows**: [`.github/workflows/README.md`](.github/workflows/README.md)
  - Configuración de CI/CD
  - Personalización de workflows
  - Métricas y optimizaciones

## 🎯 Próximos Pasos

### Corto Plazo (1-2 semanas)

- [ ] Configurar credenciales de GCP
- [ ] Activar telemetría en producción
- [ ] Configurar canales de notificación
- [ ] Validar alertas con datos reales
- [ ] Automatizar generación de reportes

### Medio Plazo (1-2 meses)

- [ ] Crear dashboards personalizados
- [ ] Implementar reportes semanales automáticos
- [ ] Optimizar umbrales de alertas
- [ ] Agregar más métricas de negocio
- [ ] Integrar con herramientas de incident management

### Largo Plazo (3+ meses)

- [ ] Implementar SLO tracking automático
- [ ] Crear playbooks de respuesta a incidentes
- [ ] Automatizar rollbacks basados en métricas
- [ ] Implementar chaos engineering
- [ ] Capacitación del equipo en observabilidad

## 🆘 Soporte

Si tienes preguntas o problemas:

1. **Documentación**: Revisa los archivos README en cada directorio
2. **Issues**: Abre un issue en GitHub
3. **Logs**: Revisa los logs de Google Cloud
4. **Equipo**: Contacta al equipo de Kai

## 🤝 Contribuir

Para agregar nuevas funcionalidades:

1. Lee el plan en `docs/observabilidad-cicd-plan.md`
2. Implementa tu cambio
3. Actualiza la documentación
4. Crea un PR con descripción detallada

---

**Versión**: 1.0  
**Última actualización**: 2025-10-14  
**Autor**: Equipo Kai

¡Buena suerte con tu implementación! 🚀
