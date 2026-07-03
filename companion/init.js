#!/usr/bin/env node

// Inicializador del proyecto Kai Companion
// Uso: node init.js

const fs = require('fs-extra');
const path = require('path');
const { exec } = require('child_process');

const projectRoot = __dirname;
const requiredDirs = [
  'data',
  'data/uploads',
  'data/tools',
  'logs'
];

console.log('🚀 Inicializando Kai Companion...\n');

// Crear directorios
console.log('📁 Creando directorios...');
requiredDirs.forEach(dir => {
  const fullPath = path.join(projectRoot, dir);
  fs.ensureDirSync(fullPath);
  console.log(`   ✅ ${dir}`);
});

// Crear .env si no existe
const envPath = path.join(projectRoot, '.env');
if (!fs.existsSync(envPath)) {
  console.log('\n⚙️  Creando archivo .env...');
  fs.copySync(path.join(projectRoot, '.env.example'), envPath);
  console.log('   ✅ .env creado');
}

console.log('\n✨ Inicialización completada!');
console.log('\n📖 Próximos pasos:');
console.log('   1. npm install          # Instalar dependencias backend');
console.log('   2. cd frontend && npm install  # Instalar dependencias frontend');
console.log('   3. npm run dev          # Iniciar en modo desarrollo');
console.log('\n🌐 El servidor estará disponible en http://localhost:5000');
console.log('   La interfaz estará en http://localhost:3000\n');
