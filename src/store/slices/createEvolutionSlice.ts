import { AppSlice, EvolutionSlice } from '../../types';
import { generateId } from '../../utils/helpers';

export const createEvolutionSlice: AppSlice<EvolutionSlice> = (set, get) => ({
  isExtracting: false,
  extractionLogs: [],
  runExtractionCycle: () => {
    if (get().isExtracting) return;

    set({ isExtracting: true, extractionLogs: [] });

    const addLog = (message: string) => {
      set(state => ({
        extractionLogs: [...state.extractionLogs, { id: generateId(), timestamp: new Date().toISOString(), message }]
      }));
    };
    
    const extractionSteps = [
      { delay: 500, message: "Iniciando ciclo de extracción de conocimiento..." },
      { delay: 1000, message: "Objetivo de la directiva: Repositorio de Deep Learning." },
      { delay: 1500, message: "Recolectando fuente: github :: awesome-machine-learning" },
      { delay: 3000, message: "Respuesta de API recibida. Analizando metadatos y README." },
      { delay: 1500, message: "Extrayendo palabras clave: 'deep-learning', 'tensorflow', 'pytorch', 'neural-networks'..." },
      { delay: 1000, message: "Compilando entidad para el Kernel." },
      { delay: 500, message: "Validación de coherencia superada." },
      { delay: 1000, message: "Integrando nueva entidad en la base de conocimiento..." },
      { delay: 500, message: "¡Integración completada!" },
      { delay: 1000, message: "Ciclo de extracción finalizado. Sistema bajo control." }
    ];

    let cumulativeDelay = 0;
    extractionSteps.forEach(step => {
      cumulativeDelay += step.delay;
      setTimeout(() => {
        addLog(step.message);
      }, cumulativeDelay);
    });

    // Final action: add to kernel and reset state
    setTimeout(() => {
      get().addEntity({
        content: 'https://github.com/josephmisiti/awesome-machine-learning',
        type: 'URL',
        source: 'Ciclo de Evolución'
      });
      get().addNotification({type: 'success', message: 'Nuevo conocimiento de Deep Learning integrado en el Kernel.'});
      set({ isExtracting: false });
    }, cumulativeDelay + 500);
  },
});