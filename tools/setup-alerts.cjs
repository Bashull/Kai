#!/usr/bin/env node

/**
 * Setup Alerts for Kai
 * 
 * Este script configura políticas de alertas en Google Cloud Monitoring
 * para monitorear el estado del sistema Kai y notificar ante anomalías.
 * 
 * Uso:
 *   node tools/setup-alerts.js [--dry-run]
 * 
 * Variables de entorno requeridas:
 *   - GOOGLE_CLOUD_PROJECT: ID del proyecto de GCP
 *   - NOTIFICATION_CHANNEL_ID: ID del canal de notificación (email/slack)
 */

const { MonitoringClient } = require('@google-cloud/monitoring');

const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT;
const DRY_RUN = process.argv.includes('--dry-run');

// Cliente de Monitoring
const client = new MonitoringClient();

/**
 * Definición de políticas de alertas
 */
const ALERT_POLICIES = [
  {
    name: 'kai-high-latency-alert',
    displayName: 'Kai - Alta Latencia',
    description: 'Alerta cuando la latencia de respuesta supera 2 segundos en el percentil 95',
    conditions: [{
      displayName: 'Latencia > 2s (p95)',
      conditionThreshold: {
        filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies"',
        aggregations: [{
          alignmentPeriod: '300s',
          perSeriesAligner: 'ALIGN_DELTA',
          crossSeriesReducer: 'REDUCE_PERCENTILE_95',
          groupByFields: ['resource.service_name'],
        }],
        comparison: 'COMPARISON_GT',
        thresholdValue: 2000, // 2 segundos en ms
        duration: '300s',
      },
    }],
    severity: 'WARNING',
  },
  {
    name: 'kai-error-rate-alert',
    displayName: 'Kai - Alta Tasa de Errores',
    description: 'Alerta cuando la tasa de errores supera el 1% en 5 minutos',
    conditions: [{
      displayName: 'Error Rate > 1%',
      conditionThreshold: {
        filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class="5xx"',
        aggregations: [{
          alignmentPeriod: '300s',
          perSeriesAligner: 'ALIGN_RATE',
          crossSeriesReducer: 'REDUCE_SUM',
        }],
        comparison: 'COMPARISON_GT',
        thresholdValue: 0.01, // 1%
        duration: '300s',
      },
    }],
    severity: 'ERROR',
  },
  {
    name: 'kai-high-cpu-alert',
    displayName: 'Kai - Uso Alto de CPU',
    description: 'Alerta cuando el uso de CPU supera el 80% por 10 minutos',
    conditions: [{
      displayName: 'CPU > 80%',
      conditionThreshold: {
        filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/container/cpu/utilizations"',
        aggregations: [{
          alignmentPeriod: '60s',
          perSeriesAligner: 'ALIGN_MEAN',
          crossSeriesReducer: 'REDUCE_MEAN',
        }],
        comparison: 'COMPARISON_GT',
        thresholdValue: 0.8, // 80%
        duration: '600s', // 10 minutos
      },
    }],
    severity: 'WARNING',
  },
  {
    name: 'kai-high-memory-alert',
    displayName: 'Kai - Uso Alto de Memoria',
    description: 'Alerta cuando el uso de memoria supera el 85% por 10 minutos',
    conditions: [{
      displayName: 'Memoria > 85%',
      conditionThreshold: {
        filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/container/memory/utilizations"',
        aggregations: [{
          alignmentPeriod: '60s',
          perSeriesAligner: 'ALIGN_MEAN',
          crossSeriesReducer: 'REDUCE_MEAN',
        }],
        comparison: 'COMPARISON_GT',
        thresholdValue: 0.85, // 85%
        duration: '600s',
      },
    }],
    severity: 'WARNING',
  },
  {
    name: 'kai-uptime-alert',
    displayName: 'Kai - Disponibilidad Baja',
    description: 'Alerta cuando el uptime cae por debajo del 99.9% en 24 horas',
    conditions: [{
      displayName: 'Uptime < 99.9%',
      conditionThreshold: {
        filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count"',
        aggregations: [{
          alignmentPeriod: '86400s', // 24 horas
          perSeriesAligner: 'ALIGN_RATE',
          crossSeriesReducer: 'REDUCE_SUM',
        }],
        comparison: 'COMPARISON_LT',
        thresholdValue: 0.999, // 99.9%
        duration: '86400s',
      },
    }],
    severity: 'CRITICAL',
  },
];

/**
 * Definición de SLIs (Service Level Indicators)
 */
const SLI_DEFINITIONS = {
  availability: {
    name: 'Disponibilidad',
    description: 'Porcentaje de solicitudes exitosas (no 5xx)',
    target: 99.9, // 99.9%
    measurement: 'success_rate',
  },
  latency: {
    name: 'Latencia',
    description: 'Porcentaje de solicitudes con latencia < 500ms',
    target: 95.0, // 95%
    measurement: 'latency_threshold',
  },
  errorRate: {
    name: 'Tasa de Errores',
    description: 'Porcentaje de solicitudes sin errores del servidor',
    target: 99.0, // 99%
    measurement: 'error_free',
  },
};

/**
 * Crea o actualiza una política de alerta en Google Cloud Monitoring
 * @param {Object} policy - Definición de la política de alerta
 * @returns {Promise<Object>} Política creada
 */
async function createAlertPolicy(policy) {
  const projectPath = client.projectPath(PROJECT_ID);
  
  const alertPolicy = {
    displayName: policy.displayName,
    documentation: {
      content: policy.description,
      mimeType: 'text/markdown',
    },
    conditions: policy.conditions,
    combiner: 'OR',
    enabled: true,
    notificationChannels: process.env.NOTIFICATION_CHANNEL_ID 
      ? [`projects/${PROJECT_ID}/notificationChannels/${process.env.NOTIFICATION_CHANNEL_ID}`]
      : [],
  };

  if (DRY_RUN) {
    console.log(`[DRY RUN] Crearía política: ${policy.displayName}`);
    console.log(JSON.stringify(alertPolicy, null, 2));
    return { name: 'dry-run-policy' };
  }

  try {
    const [createdPolicy] = await client.createAlertPolicy({
      name: projectPath,
      alertPolicy: alertPolicy,
    });
    console.log(`✅ Política creada: ${policy.displayName}`);
    return createdPolicy;
  } catch (error) {
    console.error(`❌ Error al crear política ${policy.displayName}:`, error.message);
    throw error;
  }
}

/**
 * Lista todas las políticas de alertas existentes
 * @returns {Promise<Array>} Lista de políticas
 */
async function listAlertPolicies() {
  const projectPath = client.projectPath(PROJECT_ID);
  
  try {
    const [policies] = await client.listAlertPolicies({ name: projectPath });
    return policies;
  } catch (error) {
    console.error('❌ Error al listar políticas:', error.message);
    return [];
  }
}

/**
 * Elimina políticas de alertas por nombre
 * @param {string} namePrefix - Prefijo del nombre de las políticas a eliminar
 */
async function deleteAlertPoliciesByPrefix(namePrefix) {
  const policies = await listAlertPolicies();
  const toDelete = policies.filter(p => p.displayName.startsWith(namePrefix));

  if (DRY_RUN) {
    console.log(`[DRY RUN] Eliminaría ${toDelete.length} políticas`);
    toDelete.forEach(p => console.log(`  - ${p.displayName}`));
    return;
  }

  for (const policy of toDelete) {
    try {
      await client.deleteAlertPolicy({ name: policy.name });
      console.log(`🗑️  Política eliminada: ${policy.displayName}`);
    } catch (error) {
      console.error(`❌ Error al eliminar ${policy.displayName}:`, error.message);
    }
  }
}

/**
 * Configura un canal de notificación por email
 * @param {string} email - Dirección de email
 * @returns {Promise<string>} ID del canal creado
 */
async function createEmailNotificationChannel(email) {
  const projectPath = client.projectPath(PROJECT_ID);

  const channel = {
    type: 'email',
    displayName: `Kai Alerts - ${email}`,
    description: 'Canal de notificación por email para alertas de Kai',
    labels: {
      email_address: email,
    },
    enabled: true,
  };

  if (DRY_RUN) {
    console.log(`[DRY RUN] Crearía canal de email para: ${email}`);
    return 'dry-run-channel-id';
  }

  try {
    const [createdChannel] = await client.createNotificationChannel({
      name: projectPath,
      notificationChannel: channel,
    });
    console.log(`✅ Canal de notificación creado: ${email}`);
    return createdChannel.name.split('/').pop();
  } catch (error) {
    console.error(`❌ Error al crear canal de notificación:`, error.message);
    throw error;
  }
}

/**
 * Imprime el resumen de SLIs configurados
 */
function printSLISummary() {
  console.log('\n📊 Resumen de SLIs (Service Level Indicators)\n');
  console.log('─'.repeat(70));
  
  Object.entries(SLI_DEFINITIONS).forEach(([key, sli]) => {
    console.log(`\n${sli.name}:`);
    console.log(`  Descripción: ${sli.description}`);
    console.log(`  Target SLO: ${sli.target}%`);
    console.log(`  Medición: ${sli.measurement}`);
  });
  
  console.log('\n' + '─'.repeat(70));
  console.log('\n💡 Los SLIs se calculan automáticamente en los dashboards');
  console.log('💡 Los SLOs definen el nivel de servicio esperado\n');
}

/**
 * Función principal
 */
async function main() {
  console.log('🚀 Configurando Alertas para Kai\n');

  if (!PROJECT_ID) {
    console.error('❌ Error: GOOGLE_CLOUD_PROJECT no está configurado');
    process.exit(1);
  }

  if (DRY_RUN) {
    console.log('🔍 Modo DRY RUN activado - No se realizarán cambios reales\n');
  }

  try {
    // Listar políticas existentes
    console.log('📋 Listando políticas existentes...');
    const existingPolicies = await listAlertPolicies();
    console.log(`   Encontradas ${existingPolicies.length} políticas\n`);

    // Opcional: Eliminar políticas antiguas de Kai
    if (process.argv.includes('--clean')) {
      console.log('🧹 Limpiando políticas antiguas de Kai...');
      await deleteAlertPoliciesByPrefix('Kai -');
      console.log();
    }

    // Crear nuevas políticas de alerta
    console.log('📝 Creando políticas de alerta...\n');
    for (const policy of ALERT_POLICIES) {
      await createAlertPolicy(policy);
    }

    console.log('\n✅ Configuración de alertas completada\n');

    // Imprimir resumen de SLIs
    printSLISummary();

    console.log('📌 Próximos pasos:');
    console.log('   1. Verifica las políticas en Google Cloud Console');
    console.log('   2. Configura canales de notificación (email, Slack, etc.)');
    console.log('   3. Prueba las alertas con métricas simuladas');
    console.log('   4. Ajusta los umbrales según tus necesidades\n');

  } catch (error) {
    console.error('\n❌ Error durante la configuración:', error);
    process.exit(1);
  }
}

// Ejecutar si es el módulo principal
if (require.main === module) {
  main();
}

// Exportar funciones para uso en otros módulos
module.exports = {
  createAlertPolicy,
  listAlertPolicies,
  deleteAlertPoliciesByPrefix,
  createEmailNotificationChannel,
  SLI_DEFINITIONS,
  ALERT_POLICIES,
};
