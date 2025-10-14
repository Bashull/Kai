#!/usr/bin/env node

/**
 * Report Generator for Kai
 * 
 * Este script genera reportes automatizados del estado del sistema,
 * métricas de rendimiento, seguridad y CI/CD.
 * 
 * Uso:
 *   node tools/generate-reports.js [--type=TYPE] [--format=FORMAT] [--output=PATH]
 * 
 * Tipos de reporte:
 *   - performance: Métricas de rendimiento y latencia
 *   - availability: Uptime y disponibilidad
 *   - security: Vulnerabilidades y compliance
 *   - cicd: Métricas DORA
 *   - all: Todos los reportes
 * 
 * Formatos:
 *   - markdown: Formato Markdown (default)
 *   - json: Formato JSON
 *   - html: Formato HTML
 */

const fs = require('fs');
const path = require('path');

// Configuración
const REPORT_TYPES = ['performance', 'availability', 'security', 'cicd', 'all'];
const FORMATS = ['markdown', 'json', 'html'];
const DEFAULT_OUTPUT_DIR = './reports';

// Parsear argumentos
const args = process.argv.slice(2).reduce((acc, arg) => {
  const [key, value] = arg.replace('--', '').split('=');
  acc[key] = value || true;
  return acc;
}, {});

const reportType = args.type || 'all';
const format = args.format || 'markdown';
const outputPath = args.output || DEFAULT_OUTPUT_DIR;

/**
 * Genera datos simulados de rendimiento
 */
function generatePerformanceData() {
  return {
    period: 'Last 7 days',
    timestamp: new Date().toISOString(),
    metrics: {
      latency: {
        p50: 120,
        p95: 450,
        p99: 890,
        unit: 'ms',
      },
      throughput: {
        average: 150,
        peak: 320,
        unit: 'req/s',
      },
      errorRate: {
        rate: 0.5,
        count: 125,
        unit: '%',
      },
      errorBudget: {
        consumed: 15,
        available: 85,
        unit: '%',
      },
    },
    trends: {
      latency: '+5%',
      throughput: '-3%',
      errorRate: '-10%',
    },
  };
}

/**
 * Genera datos simulados de disponibilidad
 */
function generateAvailabilityData() {
  return {
    period: 'Last 30 days',
    timestamp: new Date().toISOString(),
    uptime: {
      percentage: 99.95,
      totalMinutes: 43200,
      downtimeMinutes: 21.6,
    },
    incidents: [
      {
        id: 'INC-001',
        date: '2025-10-10',
        duration: '15m',
        severity: 'MEDIUM',
        description: 'Alta latencia en API de Gemini',
        status: 'RESOLVED',
      },
      {
        id: 'INC-002',
        date: '2025-10-07',
        duration: '6m',
        severity: 'LOW',
        description: 'Reinicio programado de servicios',
        status: 'RESOLVED',
      },
    ],
    mttr: '10.5 minutes',
    mtbf: '720 hours',
    sloCompliance: {
      availability: {
        target: 99.9,
        actual: 99.95,
        status: 'MET',
      },
      latency: {
        target: 95.0,
        actual: 96.5,
        status: 'MET',
      },
      errorRate: {
        target: 99.0,
        actual: 99.5,
        status: 'MET',
      },
    },
  };
}

/**
 * Genera datos simulados de seguridad
 */
function generateSecurityData() {
  return {
    period: 'Last 7 days',
    timestamp: new Date().toISOString(),
    vulnerabilities: {
      critical: 0,
      high: 1,
      medium: 3,
      low: 8,
      total: 12,
    },
    resolved: {
      critical: 0,
      high: 2,
      medium: 5,
      low: 10,
      total: 17,
    },
    dependencies: {
      total: 42,
      outdated: 5,
      upToDate: 37,
    },
    secrets: {
      exposed: 0,
      scanned: 1250,
    },
    complianceScore: 92,
    recommendations: [
      'Actualizar dependencia @types/node a la última versión',
      'Revisar configuración de CORS',
      'Implementar rate limiting en endpoints públicos',
    ],
  };
}

/**
 * Genera datos simulados de CI/CD (DORA metrics)
 */
function generateCICDData() {
  return {
    period: 'Last 30 days',
    timestamp: new Date().toISOString(),
    doraMetrics: {
      deploymentFrequency: {
        value: 5,
        unit: 'per week',
        classification: 'Elite',
      },
      leadTimeForChanges: {
        value: 45,
        unit: 'minutes',
        classification: 'High',
      },
      changeFailureRate: {
        value: 8,
        unit: '%',
        classification: 'High',
      },
      timeToRestore: {
        value: 30,
        unit: 'minutes',
        classification: 'Elite',
      },
    },
    pipelineMetrics: {
      totalRuns: 156,
      successful: 142,
      failed: 14,
      averageDuration: '4.2 minutes',
      successRate: 91,
    },
    deployments: {
      production: 20,
      staging: 45,
      failed: 3,
    },
  };
}

/**
 * Formatea el reporte en Markdown
 */
function formatMarkdown(data) {
  let markdown = `# 📊 Reporte del Sistema Kai\n\n`;
  markdown += `**Generado**: ${new Date().toLocaleString()}\n\n`;
  markdown += `---\n\n`;

  if (data.performance) {
    markdown += `## ⚡ Rendimiento\n\n`;
    markdown += `**Período**: ${data.performance.period}\n\n`;
    markdown += `### Latencia\n`;
    markdown += `- P50: ${data.performance.metrics.latency.p50}ms\n`;
    markdown += `- P95: ${data.performance.metrics.latency.p95}ms\n`;
    markdown += `- P99: ${data.performance.metrics.latency.p99}ms\n\n`;
    markdown += `### Throughput\n`;
    markdown += `- Promedio: ${data.performance.metrics.throughput.average} req/s\n`;
    markdown += `- Pico: ${data.performance.metrics.throughput.peak} req/s\n\n`;
    markdown += `### Error Rate\n`;
    markdown += `- Tasa: ${data.performance.metrics.errorRate.rate}%\n`;
    markdown += `- Count: ${data.performance.metrics.errorRate.count} errores\n\n`;
    markdown += `### Tendencias\n`;
    markdown += `- Latencia: ${data.performance.trends.latency}\n`;
    markdown += `- Throughput: ${data.performance.trends.throughput}\n`;
    markdown += `- Error Rate: ${data.performance.trends.errorRate}\n\n`;
  }

  if (data.availability) {
    markdown += `## 🟢 Disponibilidad\n\n`;
    markdown += `**Uptime**: ${data.availability.uptime.percentage}%\n`;
    markdown += `**MTTR**: ${data.availability.mttr}\n`;
    markdown += `**MTBF**: ${data.availability.mtbf}\n\n`;
    markdown += `### Cumplimiento de SLOs\n`;
    Object.entries(data.availability.sloCompliance).forEach(([key, slo]) => {
      markdown += `- **${key}**: ${slo.actual}% (target: ${slo.target}%) - ${slo.status}\n`;
    });
    markdown += `\n### Incidentes Recientes\n`;
    data.availability.incidents.forEach(inc => {
      markdown += `- **${inc.id}** (${inc.date}): ${inc.description} - ${inc.duration} - ${inc.status}\n`;
    });
    markdown += `\n`;
  }

  if (data.security) {
    markdown += `## 🔒 Seguridad\n\n`;
    markdown += `**Compliance Score**: ${data.security.complianceScore}/100\n\n`;
    markdown += `### Vulnerabilidades\n`;
    markdown += `- 🔴 Críticas: ${data.security.vulnerabilities.critical}\n`;
    markdown += `- 🟠 Altas: ${data.security.vulnerabilities.high}\n`;
    markdown += `- 🟡 Medias: ${data.security.vulnerabilities.medium}\n`;
    markdown += `- 🟢 Bajas: ${data.security.vulnerabilities.low}\n\n`;
    markdown += `### Dependencias\n`;
    markdown += `- Total: ${data.security.dependencies.total}\n`;
    markdown += `- Actualizadas: ${data.security.dependencies.upToDate}\n`;
    markdown += `- Desactualizadas: ${data.security.dependencies.outdated}\n\n`;
    markdown += `### Recomendaciones\n`;
    data.security.recommendations.forEach(rec => {
      markdown += `- ${rec}\n`;
    });
    markdown += `\n`;
  }

  if (data.cicd) {
    markdown += `## 🚀 CI/CD - Métricas DORA\n\n`;
    markdown += `### Deployment Frequency\n`;
    markdown += `- **${data.cicd.doraMetrics.deploymentFrequency.value}** ${data.cicd.doraMetrics.deploymentFrequency.unit}\n`;
    markdown += `- Clasificación: ${data.cicd.doraMetrics.deploymentFrequency.classification}\n\n`;
    markdown += `### Lead Time for Changes\n`;
    markdown += `- **${data.cicd.doraMetrics.leadTimeForChanges.value}** ${data.cicd.doraMetrics.leadTimeForChanges.unit}\n`;
    markdown += `- Clasificación: ${data.cicd.doraMetrics.leadTimeForChanges.classification}\n\n`;
    markdown += `### Change Failure Rate\n`;
    markdown += `- **${data.cicd.doraMetrics.changeFailureRate.value}**${data.cicd.doraMetrics.changeFailureRate.unit}\n`;
    markdown += `- Clasificación: ${data.cicd.doraMetrics.changeFailureRate.classification}\n\n`;
    markdown += `### Time to Restore\n`;
    markdown += `- **${data.cicd.doraMetrics.timeToRestore.value}** ${data.cicd.doraMetrics.timeToRestore.unit}\n`;
    markdown += `- Clasificación: ${data.cicd.doraMetrics.timeToRestore.classification}\n\n`;
    markdown += `### Pipeline\n`;
    markdown += `- Runs totales: ${data.cicd.pipelineMetrics.totalRuns}\n`;
    markdown += `- Exitosos: ${data.cicd.pipelineMetrics.successful}\n`;
    markdown += `- Fallidos: ${data.cicd.pipelineMetrics.failed}\n`;
    markdown += `- Tasa de éxito: ${data.cicd.pipelineMetrics.successRate}%\n`;
    markdown += `- Duración promedio: ${data.cicd.pipelineMetrics.averageDuration}\n\n`;
  }

  markdown += `---\n\n`;
  markdown += `*Reporte generado automáticamente por Kai Reports*\n`;

  return markdown;
}

/**
 * Genera el reporte completo
 */
function generateReport(type) {
  const data = {};

  if (type === 'all' || type === 'performance') {
    data.performance = generatePerformanceData();
  }

  if (type === 'all' || type === 'availability') {
    data.availability = generateAvailabilityData();
  }

  if (type === 'all' || type === 'security') {
    data.security = generateSecurityData();
  }

  if (type === 'all' || type === 'cicd') {
    data.cicd = generateCICDData();
  }

  return data;
}

/**
 * Guarda el reporte en archivo
 */
function saveReport(content, filename) {
  // Crear directorio si no existe
  if (!fs.existsSync(outputPath)) {
    fs.mkdirSync(outputPath, { recursive: true });
  }

  const filePath = path.join(outputPath, filename);
  fs.writeFileSync(filePath, content, 'utf8');
  
  return filePath;
}

/**
 * Función principal
 */
function main() {
  console.log('📊 Generador de Reportes de Kai\n');

  // Validar tipo de reporte
  if (!REPORT_TYPES.includes(reportType)) {
    console.error(`❌ Tipo de reporte inválido: ${reportType}`);
    console.log(`💡 Tipos válidos: ${REPORT_TYPES.join(', ')}`);
    process.exit(1);
  }

  // Validar formato
  if (!FORMATS.includes(format)) {
    console.error(`❌ Formato inválido: ${format}`);
    console.log(`💡 Formatos válidos: ${FORMATS.join(', ')}`);
    process.exit(1);
  }

  console.log(`📝 Generando reporte tipo: ${reportType}`);
  console.log(`📄 Formato: ${format}`);
  console.log(`📁 Salida: ${outputPath}\n`);

  // Generar datos del reporte
  const data = generateReport(reportType);

  // Formatear según el formato solicitado
  let content;
  let extension;

  switch (format) {
    case 'json':
      content = JSON.stringify(data, null, 2);
      extension = 'json';
      break;
    case 'markdown':
      content = formatMarkdown(data);
      extension = 'md';
      break;
    case 'html':
      // TODO: Implementar formato HTML
      console.warn('⚠️  Formato HTML no implementado, usando Markdown');
      content = formatMarkdown(data);
      extension = 'md';
      break;
    default:
      content = formatMarkdown(data);
      extension = 'md';
  }

  // Generar nombre de archivo
  const timestamp = new Date().toISOString().split('T')[0];
  const filename = `kai-report-${reportType}-${timestamp}.${extension}`;

  // Guardar reporte
  const filePath = saveReport(content, filename);

  console.log(`✅ Reporte generado exitosamente`);
  console.log(`📄 Archivo: ${filePath}\n`);

  // Imprimir resumen
  console.log('📊 Resumen del Reporte:\n');
  if (data.performance) {
    console.log(`⚡ Rendimiento: P95 latency ${data.performance.metrics.latency.p95}ms`);
  }
  if (data.availability) {
    console.log(`🟢 Disponibilidad: ${data.availability.uptime.percentage}% uptime`);
  }
  if (data.security) {
    console.log(`🔒 Seguridad: ${data.security.complianceScore}/100 compliance score`);
  }
  if (data.cicd) {
    console.log(`🚀 CI/CD: ${data.cicd.doraMetrics.deploymentFrequency.value} deploys/week`);
  }
  console.log();
}

// Ejecutar si es el módulo principal
if (require.main === module) {
  main();
}

// Exportar funciones
module.exports = {
  generateReport,
  formatMarkdown,
  saveReport,
};
