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
      { delay: 500, message: "Iniciando ciclo de evolución completo..." },
      { delay: 1000, message: "Objetivo: Analizar 'Awesome Digital Human' para identificar vectores de expansión." },
      { delay: 1500, message: "Recolectando fuente interna: awesome-digital-human-main/README.md" },
      { delay: 2500, message: "Parseando estructura del documento Markdown..." },
      { delay: 1500, message: "Identificando patrones: '3D/4D Human Avatar', 'Reconstruction', 'Animation', 'Generation'." },
      { delay: 2000, message: "SÍNTESIS: Se ha detectado una alta densidad de conceptos relacionados con la gestión de avatares digitales." },
      { delay: 1000, message: "PROPUESTA: Forjar un nuevo panel 'Avatares' para centralizar estas capacidades." },
      { delay: 1500, message: "Validando propuesta contra la Constitución... APROBADA." },
      { delay: 1000, message: "MODIFICANDO CÓDIGO BASE: Integrando el andamiaje para el nuevo panel..." },
      { delay: 1500, message: "¡Integración completada! El panel 'Avatares' ha sido añadido a la arquitectura de KaiOS." },
      { delay: 500, message: "Asimilando concepto 'Digital Human Management' en el Kernel..." }
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
        content: 'Digital Human Avatar Management',
        type: 'TEXT',
        source: 'Ciclo de Evolución (Síntesis Interna)'
      });
      get().addNotification({type: 'success', message: '¡Evolución completada! Nueva capacidad de Avatares integrada.'});
      set({ isExtracting: false });
    }, cumulativeDelay + 500);
  },
});