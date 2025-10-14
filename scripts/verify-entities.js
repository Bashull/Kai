#!/usr/bin/env node

/**
 * Verification script for kernel entities
 * Validates that all entities are properly integrated
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Read the createKernelSlice.ts file
const slicePath = join(__dirname, '../src/store/slices/createKernelSlice.ts');
const sliceContent = readFileSync(slicePath, 'utf-8');

// Extract entity definitions using regex
const entityPattern = /{\s*id:\s*['"]([^'"]+)['"]\s*,\s*content:\s*['"]([^'"]+)['"]\s*,\s*type:\s*['"]([^'"]+)['"]\s*,\s*source:\s*['"]([^'"]+)['"]\s*,\s*status:\s*['"]([^'"]+)['"]/g;

const entities = [];
let match;

while ((match = entityPattern.exec(sliceContent)) !== null) {
  entities.push({
    id: match[1],
    content: match[2],
    type: match[3],
    source: match[4],
    status: match[5]
  });
}

console.log('🔍 Entity Verification Report\n');
console.log('━'.repeat(60));

// Group entities by source
const groupedEntities = entities.reduce((acc, entity) => {
  if (!acc[entity.source]) {
    acc[entity.source] = [];
  }
  acc[entity.source].push(entity);
  return acc;
}, {});

// Display grouped results
Object.entries(groupedEntities).forEach(([source, entities]) => {
  console.log(`\n📦 ${source} (${entities.length} entities)`);
  entities.forEach(entity => {
    const statusIcon = entity.status === 'INTEGRATED' ? '✅' : '❌';
    console.log(`  ${statusIcon} ${entity.id}: ${entity.content}`);
  });
});

// Validation checks
console.log('\n' + '━'.repeat(60));
console.log('\n🔬 Validation Checks:\n');

let allValid = true;

// Check 1: All entities have INTEGRATED status
const nonIntegrated = entities.filter(e => e.status !== 'INTEGRATED');
if (nonIntegrated.length === 0) {
  console.log('✅ All entities have INTEGRATED status');
} else {
  console.log(`❌ Found ${nonIntegrated.length} entities without INTEGRATED status`);
  allValid = false;
}

// Check 2: All entities have valid URLs
const invalidUrls = entities.filter(e => 
  !e.content.startsWith('http://') && !e.content.startsWith('https://')
);
if (invalidUrls.length === 0) {
  console.log('✅ All entities have valid URLs');
} else {
  console.log(`❌ Found ${invalidUrls.length} entities with invalid URLs`);
  allValid = false;
}

// Check 3: All IDs are unique
const uniqueIds = new Set(entities.map(e => e.id));
if (uniqueIds.size === entities.length) {
  console.log('✅ All entity IDs are unique');
} else {
  console.log(`❌ Found duplicate entity IDs`);
  allValid = false;
}

// Check 4: Verify recommended repositories are included
const requiredRepos = [
  'https://github.com/chroma-core/chroma',
  'https://github.com/RasaHQ/rasa',
  'https://github.com/botpress/botpress',
  'https://github.com/Significant-Gravitas/AutoGPT',
  'https://github.com/microsoft/semantic-kernel',
  'https://github.com/bentoml/BentoML',
  'https://github.com/oobabooga/text-generation-webui',
  'https://github.com/pgvector/pgvector',
  'https://github.com/StanGirard/quivr',
];

const entityUrls = entities.map(e => e.content);
const missingRepos = requiredRepos.filter(repo => !entityUrls.includes(repo));

if (missingRepos.length === 0) {
  console.log('✅ All required recommended repositories are included');
} else {
  console.log(`❌ Missing ${missingRepos.length} required repositories:`);
  missingRepos.forEach(repo => console.log(`   - ${repo}`));
  allValid = false;
}

// Summary
console.log('\n' + '━'.repeat(60));
console.log(`\n📊 Summary: ${entities.length} total entities loaded\n`);

if (allValid) {
  console.log('✨ All validation checks passed!\n');
  process.exit(0);
} else {
  console.log('⚠️  Some validation checks failed. Please review the issues above.\n');
  process.exit(1);
}
