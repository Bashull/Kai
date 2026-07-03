/**
 * EJEMPLOS DE USO - KAI Companion
 * Ejecuta estos ejemplos para probar funcionalidades
 */

const axios = require('axios');
const fs = require('fs');

const API = 'http://localhost:5000/api';

// Colores para consola
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  yellow: '\x1b[33m',
  red: '\x1b[31m'
};

function log(type, msg) {
  const typeStr = {
    'info': `${colors.blue}ℹ${colors.reset}`,
    'success': `${colors.green}✓${colors.reset}`,
    'error': `${colors.red}✗${colors.reset}`,
    'warn': `${colors.yellow}!${colors.reset}`
  }[type] || '•';
  console.log(`${typeStr} ${msg}`);
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============= EJEMPLOS =============

async function example1_BasicChat() {
  log('info', 'EJEMPLO 1: Chat Básico');
  try {
    const response = await axios.post(`${API}/chat/message`, {
      message: '¿Cuál es tu nombre?'
    });
    log('success', `Kai: ${response.data.response}`);
  } catch (error) {
    log('error', error.message);
  }
}

async function example2_CreateTool() {
  log('info', 'EJEMPLO 2: Crear Herramienta');
  try {
    const response = await axios.post(`${API}/tools/create`, {
      name: 'Saludador',
      description: 'Saluda por nombre',
      code: `
        return 'Hola, ' + params.name + '! Bienvenido a KAI.';
      `,
      language: 'javascript'
    });
    log('success', `Herramienta creada: ${response.data.tool.id}`);
    return response.data.tool.id;
  } catch (error) {
    log('error', error.message);
  }
}

async function example3_ExecuteTool(toolId) {
  log('info', 'EJEMPLO 3: Ejecutar Herramienta');
  try {
    const response = await axios.post(`${API}/tools/execute/${toolId}`, {
      params: { name: 'Juan' }
    });
    log('success', `Resultado: ${response.data.result}`);
  } catch (error) {
    log('error', error.message);
  }
}

async function example4_ListTools() {
  log('info', 'EJEMPLO 4: Listar Herramientas');
  try {
    const response = await axios.get(`${API}/tools/list`);
    log('success', `Total herramientas: ${response.data.length}`);
    response.data.forEach(tool => {
      console.log(`  • ${tool.name} (${tool.id})`);
    });
  } catch (error) {
    log('error', error.message);
  }
}

async function example5_AvatarState() {
  log('info', 'EJEMPLO 5: Estado del Avatar');
  try {
    const response = await axios.get(`${API}/avatar/state`);
    log('success', `Avatar: ${response.data.name}`);
    console.log(`  Position: (${response.data.position.x}, ${response.data.position.y}, ${response.data.position.z})`);
    console.log(`  Status: ${response.data.status}`);
  } catch (error) {
    log('error', error.message);
  }
}

async function example6_AnimateAvatar() {
  log('info', 'EJEMPLO 6: Animar Avatar');
  try {
    const animations = ['wave', 'nod', 'jump', 'think'];
    for (const anim of animations) {
      const response = await axios.post(`${API}/avatar/animate`, {
        animation: anim,
        duration: 1000
      });
      log('success', `Animación: ${anim}`);
      await sleep(1500);
    }
  } catch (error) {
    log('error', error.message);
  }
}

async function example7_RequestPermission() {
  log('info', 'EJEMPLO 7: Solicitar Permiso');
  try {
    const response = await axios.post(`${API}/permissions/request`, {
      resource: 'filesystem',
      action: 'read',
      reason: 'Necesito leer archivos de documentos'
    });
    log('success', `Permiso solicitado: ${response.data.permission.id}`);
    return response.data.permission.id;
  } catch (error) {
    log('error', error.message);
  }
}

async function example8_GrantPermission() {
  log('info', 'EJEMPLO 8: Otorgar Permiso');
  try {
    // 24 horas en milisegundos
    const expiresIn = 24 * 60 * 60 * 1000;
    
    await axios.post(`${API}/permissions/grant`, {
      resource: 'filesystem',
      action: 'read',
      expiresIn: expiresIn
    });
    log('success', 'Permiso otorgado por 24 horas');
  } catch (error) {
    log('error', error.message);
  }
}

async function example9_CheckPermission() {
  log('info', 'EJEMPLO 9: Verificar Permiso');
  try {
    const response = await axios.get(`${API}/permissions/check/filesystem/read`);
    log('success', `Permiso concedido: ${response.data.allowed}`);
  } catch (error) {
    log('error', error.message);
  }
}

async function example10_ListPermissions() {
  log('info', 'EJEMPLO 10: Listar Permisos');
  try {
    const response = await axios.get(`${API}/permissions/list`);
    log('success', `Total permisos: ${response.data.length}`);
    response.data.forEach(perm => {
      const status = perm.allowed ? '✓' : '✗';
      console.log(`  ${status} ${perm.resource}:${perm.action}`);
    });
  } catch (error) {
    log('error', error.message);
  }
}

async function example11_CreateGesture() {
  log('info', 'EJEMPLO 11: Crear Gesto');
  try {
    const response = await axios.post(`${API}/avatar/gesture`, {
      gestureName: 'Celebrar',
      keyframes: [
        { pos: { y: 0 }, rot: { z: -0.3 } },
        { pos: { y: 0.2 }, rot: { z: 0.3 } },
        { pos: { y: 0 }, rot: { z: 0 } }
      ]
    });
    log('success', `Gesto creado: ${response.data.name}`);
  } catch (error) {
    log('error', error.message);
  }
}

async function example12_GetSystemStatus() {
  log('info', 'EJEMPLO 12: Estado del Sistema');
  try {
    const response = await axios.get(`${API}/system/status`);
    log('success', `Companion: ${response.data.companion?.name || 'KAI'}`);
    console.log(`  Herramientas: ${response.data.stats.tools}`);
    console.log(`  Habilidades: ${response.data.stats.skills}`);
  } catch (error) {
    log('error', error.message);
  }
}

// ============= EJECUCIÓN =============

async function runAllExamples() {
  console.log(`\n${colors.blue}═══════════════════════════════════════${colors.reset}`);
  console.log(`${colors.blue}  🤖 KAI COMPANION - EJEMPLOS${colors.reset}`);
  console.log(`${colors.blue}═══════════════════════════════════════${colors.reset}\n`);

  try {
    // Ejemplos secuenciales
    await example1_BasicChat();
    await sleep(1000);

    const toolId = await example2_CreateTool();
    await sleep(1000);

    if (toolId) {
      await example3_ExecuteTool(toolId);
      await sleep(1000);
    }

    await example4_ListTools();
    await sleep(1000);

    await example5_AvatarState();
    await sleep(1000);

    await example6_AnimateAvatar();
    await sleep(2000);

    await example7_RequestPermission();
    await sleep(1000);

    await example8_GrantPermission();
    await sleep(1000);

    await example9_CheckPermission();
    await sleep(1000);

    await example10_ListPermissions();
    await sleep(1000);

    await example11_CreateGesture();
    await sleep(1000);

    await example12_GetSystemStatus();

    console.log(`\n${colors.green}✓ Todos los ejemplos completados!${colors.reset}\n`);
  } catch (error) {
    log('error', `Error general: ${error.message}`);
  }
}

// Ejecutar si se llama directamente
if (require.main === module) {
  runAllExamples();
}

module.exports = {
  example1_BasicChat,
  example2_CreateTool,
  example3_ExecuteTool,
  example4_ListTools,
  example5_AvatarState,
  example6_AnimateAvatar,
  example7_RequestPermission,
  example8_GrantPermission,
  example9_CheckPermission,
  example10_ListPermissions,
  example11_CreateGesture,
  example12_GetSystemStatus
};
