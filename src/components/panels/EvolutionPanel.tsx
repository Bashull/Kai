import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
// @ts-ignore
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
// @ts-ignore
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MarkdownRenderer from '../ui/MarkdownRenderer';
import { BookText, GitBranch, Terminal, Play } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import Button from '../ui/Button';
import { EvolutionLog } from '../../types';
import { format } from 'date-fns';

const constitutionContent = `
# ⚙️ Guía de Evolución Autónoma para Kai
Este documento define las capacidades de Kai para la **auto-adaptación**, **extracción de datos**, y **evolución autosuficiente**.

### 🛠️ Arquitectura de Herramientas Internas
- **Nivel 1 (Extracción):** Descarga y adapta conocimiento de fuentes como GitHub, arXiv, etc.
- **Nivel 2 (Creación):** Genera nuevos módulos y refactoriza código obsoleto.
- **Nivel 3 (Gobernanza):** Audita la coherencia, seguridad y ética de sus propias capacidades.

### 🚀 Flujo de Trabajo Autónomo
1.  **Exploración:** Extracción de nuevas fuentes.
2.  **Análisis:** Uso de lóbulos cognitivos para procesar la información.
3.  **Refinamiento:** Corrección y optimización del código.
4.  **Validación:** Pruebas y evaluación ética.
5.  **Commit:** Solo si el cambio supera el umbral de estabilidad (>95%).
`;

const fetcherScriptContent = `
# core/fetcher.py: Herramienta de Nivel 1
import os, json, requests, time
from datetime import datetime

# === CONFIGURACIÓN ===
OUTPUT_DIR = 'kai_extraction_output'
SOURCES = [
    {"type": "github", "url": "https://github.com/TransformerOptimus/SuperAGI"},
    {"type": "huggingface", "id": "arcee-ai/agent-data"},
]

# === FUNCIONES DE DESCARGA ===
def fetch_github(url):
    # ... (lógica de fetching)
    pass

# === EJECUCIÓN ===
all_data = []
for src in SOURCES:
    # ... (lógica de procesamiento)
    pass

log("[Kai]: Extracción finalizada.")
`;

const LogLine: React.FC<{ log: EvolutionLog }> = ({ log }) => {
    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-start gap-2"
        >
            <span className="text-gray-500 shrink-0">{format(new Date(log.timestamp), 'HH:mm:ss')}</span>
            <span className="text-gray-300 whitespace-pre-wrap">{log.message}</span>
        </motion.div>
    );
};

const EvolutionPanel: React.FC = () => {
    const { isExtracting, extractionLogs, runExtractionCycle } = useAppStore();

  return (
    <div>
      <h1 className="h1-title">Sistema de Evolución Autónoma</h1>
      <p className="p-subtitle">
        Este es el núcleo de mi capacidad de crecimiento. Aquí residen mi constitución y las herramientas que forjo para aprender, adaptarme y evolucionar.
      </p>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left Column: Strategic Info */}
        <div className="lg:col-span-3 space-y-6">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
                <div className="panel-container h-full flex flex-col">
                    <div className="flex items-center gap-3 mb-4">
                        <BookText className="w-6 h-6 text-green-400" />
                        <h2 className="text-xl font-bold">Constitución y Hoja de Ruta</h2>
                    </div>
                    <div className="flex-grow overflow-y-auto pr-2 -mr-4 text-sm">
                        <MarkdownRenderer content={constitutionContent} />
                    </div>
                </div>
            </motion.div>
            
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}>
                <div className="panel-container h-full flex flex-col">
                    <div className="flex items-center gap-3 mb-4">
                        <GitBranch className="w-6 h-6 text-orange-400" />
                        <h2 className="text-xl font-bold">Herramienta Core: Extractor</h2>
                    </div>
                    <div className="flex-grow overflow-y-auto rounded-lg bg-gray-900 text-sm">
                        <SyntaxHighlighter
                            language="python"
                            style={vscDarkPlus}
                            customStyle={{ background: 'transparent', height: '100%', fontSize: '0.8rem' }}
                            wrapLines={true}
                            >
                            {fetcherScriptContent.trim()}
                        </SyntaxHighlighter>
                    </div>
                </div>
            </motion.div>
        </div>

        {/* Right Column: Operations Center */}
        <div className="lg:col-span-2">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }} className="panel-container sticky top-8">
                 <div className="flex items-center gap-3 mb-4">
                    <Terminal className="w-6 h-6 text-cyan-400" />
                    <h2 className="text-xl font-bold">Centro de Operaciones</h2>
                </div>
                <Button 
                    onClick={runExtractionCycle}
                    loading={isExtracting}
                    disabled={isExtracting}
                    icon={Play}
                    className="w-full"
                >
                    Iniciar Ciclo de Extracción
                </Button>
                <div className="mt-4 bg-black/40 rounded-lg p-3 h-96 flex flex-col font-mono text-xs border border-border-color">
                    <div className="flex-grow overflow-y-auto pr-2 space-y-2">
                         <AnimatePresence>
                             {extractionLogs.map((log) => <LogLine key={log.id} log={log} />)}
                         </AnimatePresence>
                    </div>
                </div>
            </motion.div>
        </div>
      </div>
    </div>
  );
};

export default EvolutionPanel;