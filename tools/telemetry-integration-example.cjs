/**
 * Ejemplo de Integración de Telemetría en Kai
 * 
 * Este archivo muestra cómo integrar la telemetría de OpenTelemetry
 * en la aplicación Kai para monitorear operaciones clave.
 */

// Importar el telemetry collector
const { initializeTelemetry, createCustomMetrics, setupCustomTracing } = require('./telemetry-collector');

/**
 * Configuración inicial de telemetría
 * Debe llamarse al inicio de la aplicación
 */
function setupTelemetry() {
  console.log('🔭 Inicializando telemetría para Kai...');
  
  // Inicializar el SDK de OpenTelemetry
  const sdk = initializeTelemetry();
  
  // Crear métricas personalizadas
  const metrics = createCustomMetrics();
  
  // Configurar tracing personalizado
  const { traceAsync } = setupCustomTracing();
  
  console.log('✅ Telemetría configurada correctamente');
  
  return { sdk, metrics, traceAsync };
}

/**
 * Ejemplo: Monitorear llamadas a Gemini API
 */
async function monitorGeminiCall(traceAsync, aiCallsCounter, responseLatencyHistogram) {
  return await traceAsync('ai.gemini.generateContent', async (span) => {
    const startTime = Date.now();
    
    try {
      // Simular llamada a Gemini
      // const result = await geminiClient.generateContent(prompt);
      
      span.setAttribute('ai.model', 'gemini-pro');
      span.setAttribute('ai.provider', 'google');
      span.setAttribute('ai.operation', 'generate');
      
      // Incrementar contador de llamadas
      aiCallsCounter.add(1, {
        model: 'gemini-pro',
        operation: 'generate',
        status: 'success',
      });
      
      const latency = Date.now() - startTime;
      
      // Registrar latencia
      responseLatencyHistogram.record(latency, {
        endpoint: '/api/ai/generate',
        model: 'gemini-pro',
      });
      
      span.addEvent('Content generated', {
        'response.tokens': 150,
        'response.latency_ms': latency,
      });
      
      return { success: true, latency };
      
    } catch (error) {
      span.recordException(error);
      span.setAttribute('error', true);
      
      aiCallsCounter.add(1, {
        model: 'gemini-pro',
        operation: 'generate',
        status: 'error',
      });
      
      throw error;
    }
  }, {
    'service.operation': 'ai_generation',
  });
}

/**
 * Ejemplo: Monitorear operaciones de La Forja
 */
async function monitorTrainingJob(traceAsync, metrics) {
  return await traceAsync('forge.training.start', async (span) => {
    span.setAttribute('training.job_id', 'job-12345');
    span.setAttribute('training.model_name', 'kai-custom-v2');
    
    // Simular inicio de entrenamiento
    span.addEvent('Training job created');
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    span.addEvent('Training job started', {
      'training.dataset_size': 1000,
      'training.epochs': 10,
    });
    
    return { jobId: 'job-12345', status: 'TRAINING' };
  }, {
    'component': 'la-forja',
  });
}

/**
 * Ejemplo: Monitorear consultas a memoria
 */
async function monitorMemoryQuery(traceAsync) {
  return await traceAsync('memory.search', async (span) => {
    span.setAttribute('query.type', 'semantic_search');
    span.setAttribute('query.term', 'recuerdos recientes');
    
    // Simular búsqueda
    await new Promise(resolve => setTimeout(resolve, 200));
    
    span.addEvent('Search completed', {
      'results.count': 15,
      'results.relevant': 8,
    });
    
    return { count: 15, relevant: 8 };
  });
}

/**
 * Ejemplo: Middleware de Express para auto-instrumentación
 */
function createTelemetryMiddleware(traceAsync) {
  return async (req, res, next) => {
    const startTime = Date.now();
    
    // Crear un span para la request
    await traceAsync(`http.${req.method} ${req.path}`, async (span) => {
      span.setAttribute('http.method', req.method);
      span.setAttribute('http.url', req.url);
      span.setAttribute('http.route', req.path);
      
      // Continuar con el siguiente middleware
      res.on('finish', () => {
        const duration = Date.now() - startTime;
        
        span.setAttribute('http.status_code', res.statusCode);
        span.setAttribute('http.response_time_ms', duration);
        
        span.addEvent('Request completed', {
          'response.status': res.statusCode,
          'response.size': res.get('Content-Length') || 0,
        });
        
        span.end();
      });
      
      next();
    }, {
      'component': 'http-server',
    });
  };
}

/**
 * Ejemplo de uso completo
 */
async function exampleUsage() {
  console.log('\n=== Ejemplo de Integración de Telemetría ===\n');
  
  // 1. Configurar telemetría
  const { metrics, traceAsync } = setupTelemetry();
  const { aiCallsCounter, responseLatencyHistogram } = metrics;
  
  // 2. Monitorear llamada a IA
  console.log('📞 Monitoreando llamada a Gemini...');
  const geminiResult = await monitorGeminiCall(
    traceAsync, 
    aiCallsCounter, 
    responseLatencyHistogram
  );
  console.log('✅ Llamada completada:', geminiResult);
  
  // 3. Monitorear operación de entrenamiento
  console.log('\n🔥 Monitoreando trabajo de La Forja...');
  const trainingResult = await monitorTrainingJob(traceAsync, metrics);
  console.log('✅ Entrenamiento iniciado:', trainingResult);
  
  // 4. Monitorear consulta a memoria
  console.log('\n🧠 Monitoreando consulta a memoria...');
  const memoryResult = await monitorMemoryQuery(traceAsync);
  console.log('✅ Búsqueda completada:', memoryResult);
  
  console.log('\n📊 Telemetría enviada a Google Cloud');
  console.log('💡 Verifica las métricas en Cloud Monitoring');
  console.log('💡 Verifica las trazas en Cloud Trace\n');
}

// Ejecutar ejemplo si se ejecuta directamente
if (require.main === module) {
  exampleUsage()
    .then(() => {
      console.log('✅ Ejemplo completado exitosamente');
      // Dar tiempo para que se exporten las métricas
      setTimeout(() => process.exit(0), 2000);
    })
    .catch((error) => {
      console.error('❌ Error en el ejemplo:', error);
      process.exit(1);
    });
}

// Exportar funciones para uso en la aplicación
module.exports = {
  setupTelemetry,
  monitorGeminiCall,
  monitorTrainingJob,
  monitorMemoryQuery,
  createTelemetryMiddleware,
};
