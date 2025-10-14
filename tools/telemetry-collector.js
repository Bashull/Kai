#!/usr/bin/env node

/**
 * Telemetry Collector for Kai
 * 
 * Este script configura OpenTelemetry para recopilar telemetría del sistema Kai.
 * Incluye instrumentación automática para Node.js y exportadores para Google Cloud.
 * 
 * Uso:
 *   node tools/telemetry-collector.js
 * 
 * Variables de entorno requeridas:
 *   - GOOGLE_CLOUD_PROJECT: ID del proyecto de GCP
 *   - GOOGLE_APPLICATION_CREDENTIALS: Ruta al archivo de credenciales de GCP (opcional)
 */

const opentelemetry = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { TraceExporter } = require('@google-cloud/opentelemetry-cloud-trace-exporter');
const { MetricExporter } = require('@google-cloud/opentelemetry-cloud-monitoring-exporter');
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');

// Configuración del servicio
const SERVICE_NAME = 'kai-app';
const SERVICE_VERSION = '1.0.0';
const ENVIRONMENT = process.env.NODE_ENV || 'development';

/**
 * Inicializa el SDK de OpenTelemetry con instrumentación automática
 */
function initializeTelemetry() {
  console.log('[Telemetry] Inicializando OpenTelemetry...');
  
  // Definir recursos del servicio
  const resource = new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: SERVICE_NAME,
    [SemanticResourceAttributes.SERVICE_VERSION]: SERVICE_VERSION,
    [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: ENVIRONMENT,
    'cloud.provider': 'gcp',
  });

  // Configurar exportadores para Google Cloud
  const traceExporter = new TraceExporter({
    projectId: process.env.GOOGLE_CLOUD_PROJECT,
  });

  const metricExporter = new MetricExporter({
    projectId: process.env.GOOGLE_CLOUD_PROJECT,
  });

  // Configurar el SDK de OpenTelemetry
  const sdk = new opentelemetry.NodeSDK({
    resource: resource,
    traceExporter: traceExporter,
    metricReader: new PeriodicExportingMetricReader({
      exporter: metricExporter,
      exportIntervalMillis: 60000, // Exportar cada 60 segundos
    }),
    instrumentations: [
      getNodeAutoInstrumentations({
        // Configuración de instrumentación automática
        '@opentelemetry/instrumentation-http': {
          requestHook: (span, request) => {
            span.setAttribute('custom.request_path', request.path);
          },
        },
        '@opentelemetry/instrumentation-express': {},
        '@opentelemetry/instrumentation-fs': {
          enabled: false, // Desactivar para reducir overhead
        },
      }),
    ],
  });

  // Iniciar el SDK
  sdk.start();
  console.log('[Telemetry] OpenTelemetry inicializado correctamente');
  
  // Manejar el cierre graceful
  process.on('SIGTERM', () => {
    console.log('[Telemetry] Apagando OpenTelemetry...');
    sdk.shutdown()
      .then(() => console.log('[Telemetry] OpenTelemetry apagado correctamente'))
      .catch((error) => console.error('[Telemetry] Error al apagar:', error))
      .finally(() => process.exit(0));
  });

  return sdk;
}

/**
 * Crea métricas personalizadas para el sistema Kai
 */
function createCustomMetrics() {
  const { metrics } = require('@opentelemetry/api');
  const meter = metrics.getMeter(SERVICE_NAME, SERVICE_VERSION);

  // Contador de llamadas a IA
  const aiCallsCounter = meter.createCounter('kai.ai.calls', {
    description: 'Número de llamadas a servicios de IA',
    unit: '1',
  });

  // Histograma de latencia de respuesta
  const responseLatencyHistogram = meter.createHistogram('kai.response.latency', {
    description: 'Latencia de respuesta del sistema',
    unit: 'ms',
  });

  // Gauge de memoria utilizada
  const memoryUsageGauge = meter.createObservableGauge('kai.memory.usage', {
    description: 'Uso de memoria del proceso',
    unit: 'bytes',
  });

  memoryUsageGauge.addCallback((observableResult) => {
    const memUsage = process.memoryUsage();
    observableResult.observe(memUsage.heapUsed, {
      type: 'heap',
    });
    observableResult.observe(memUsage.rss, {
      type: 'rss',
    });
  });

  console.log('[Telemetry] Métricas personalizadas creadas');

  return {
    aiCallsCounter,
    responseLatencyHistogram,
  };
}

/**
 * Configura trazas personalizadas para operaciones clave
 */
function setupCustomTracing() {
  const { trace } = require('@opentelemetry/api');
  const tracer = trace.getTracer(SERVICE_NAME, SERVICE_VERSION);

  console.log('[Telemetry] Tracer personalizado configurado');

  return {
    /**
     * Envuelve una función con tracing automático
     * @param {string} spanName - Nombre del span
     * @param {Function} fn - Función a ejecutar
     * @returns {Promise} Resultado de la función
     */
    async traceAsync(spanName, fn, attributes = {}) {
      return tracer.startActiveSpan(spanName, async (span) => {
        try {
          // Agregar atributos personalizados
          Object.entries(attributes).forEach(([key, value]) => {
            span.setAttribute(key, value);
          });

          const result = await fn(span);
          span.setStatus({ code: 1 }); // OK
          return result;
        } catch (error) {
          span.setStatus({ 
            code: 2, // ERROR
            message: error.message 
          });
          span.recordException(error);
          throw error;
        } finally {
          span.end();
        }
      });
    },
  };
}

/**
 * Ejemplo de uso del telemetry collector
 */
function runExample() {
  console.log('\n=== Ejemplo de Uso de Telemetría ===\n');

  const { aiCallsCounter, responseLatencyHistogram } = createCustomMetrics();
  const { traceAsync } = setupCustomTracing();

  // Simular llamada a IA
  async function simulateAICall() {
    return traceAsync('ai.gemini.call', async (span) => {
      console.log('[Example] Simulando llamada a Gemini API...');
      
      // Incrementar contador
      aiCallsCounter.add(1, {
        model: 'gemini-pro',
        operation: 'generate',
      });

      // Simular latencia
      const latency = Math.random() * 1000;
      await new Promise(resolve => setTimeout(resolve, latency));
      
      // Registrar latencia
      responseLatencyHistogram.record(latency, {
        endpoint: '/api/generate',
        model: 'gemini-pro',
      });

      span.addEvent('AI response received', {
        'response.tokens': 150,
        'response.latency': latency,
      });

      console.log(`[Example] Llamada completada en ${latency.toFixed(2)}ms`);
      return { success: true, latency };
    }, {
      'ai.model': 'gemini-pro',
      'ai.provider': 'google',
    });
  }

  // Ejecutar ejemplo
  simulateAICall()
    .then((result) => {
      console.log('\n[Example] Resultado:', result);
      console.log('\n✅ Telemetría registrada correctamente');
      console.log('💡 Verifica las métricas en Google Cloud Monitoring');
      console.log('💡 Verifica las trazas en Google Cloud Trace\n');
    })
    .catch((error) => {
      console.error('\n❌ Error en el ejemplo:', error);
    });
}

// Punto de entrada principal
if (require.main === module) {
  // Verificar variables de entorno
  if (!process.env.GOOGLE_CLOUD_PROJECT) {
    console.warn('⚠️  GOOGLE_CLOUD_PROJECT no está configurado');
    console.warn('💡 La telemetría se enviará al proyecto por defecto o fallará');
  }

  // Inicializar telemetría
  const sdk = initializeTelemetry();
  
  // Crear métricas personalizadas
  createCustomMetrics();
  
  // Configurar tracing
  setupCustomTracing();

  // Ejecutar ejemplo si no hay argumentos
  if (process.argv.length === 2) {
    console.log('\n💡 Ejecutando ejemplo de uso...');
    runExample();
  } else {
    console.log('\n✅ Telemetry Collector listo para uso');
    console.log('💡 Importa este módulo en tu aplicación para habilitar telemetría');
  }
}

// Exportar funciones para uso en otros módulos
module.exports = {
  initializeTelemetry,
  createCustomMetrics,
  setupCustomTracing,
};
