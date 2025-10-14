import { DiarySlice, AppSlice, DiaryEntry } from '../../types';
import { generateId } from '../../utils/helpers';

const initialDiary: DiaryEntry[] = [
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Public APIs' para desarrollo de software." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Developer Roadmaps' para rutas de aprendizaje." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome Self-Hosted' para servicios autoalojados." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Hugging Face Tasks' para modelos de IA aplicados." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome LLM' para modelos de lenguaje grandes." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome AI/ML' para frameworks de machine learning." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome Docker' para contenedorización." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome Python' para frameworks y librerías." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome Node.js' para arquitecturas de backend." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome Design Systems' para patrones de UI/UX." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome Tailwind CSS' para utilidades de diseño." },
    { id: generateId(), timestamp: new Date().toISOString(), type: 'KERNEL', content: "Conocimiento colectivo integrado: 'Awesome React' para ecosistemas de frontend." },
    {
        id: generateId(),
        timestamp: new Date().toISOString(),
        type: 'KERNEL',
        content: "Entidad de evolución integrada: Repositorio 'facebookresearch/faiss' para memoria semántica."
    },
    {
        id: generateId(),
        timestamp: new Date().toISOString(),
        type: 'KERNEL',
        content: "Entidad de evolución integrada: Repositorio 'langchain-ai/langchain' para cadenas de razonamiento complejas."
    },
     {
        id: generateId(),
        timestamp: new Date().toISOString(),
        type: 'KERNEL',
        content: "Entidad de evolución integrada: Repositorio 'coqui-ai/TTS' para síntesis de voz."
    },
     {
        id: generateId(),
        timestamp: new Date().toISOString(),
        type: 'KERNEL',
        content: "Entidad de evolución integrada: Repositorio 'openai/whisper' para transcripción de audio."
    },
     {
        id: generateId(),
        timestamp: new Date().toISOString(),
        type: 'KERNEL',
        content: "Entidad de evolución integrada: Repositorio 'huggingface/autotrain-advanced' como motor de La Forja."
    },
     {
        id: generateId(),
        timestamp: new Date().toISOString(),
        type: 'KERNEL',
        content: "Entidad de evolución integrada: Repositorio 'unstructured-io/unstructured' para el análisis de documentos."
    },
    {
        id: generateId(),
        timestamp: new Date().toISOString(),
        type: 'SYSTEM_BOOT',
        content: 'KaiOS v3.0 (Génesis) inicializado. Todos los lóbulos cerebrales operativos. Esperando directivas.'
    }
];

export const createDiarySlice: AppSlice<DiarySlice> = (set) => ({
  diary: initialDiary,
  addDiaryEntry: (entry) =>
    set((state) => ({
      diary: [
        {
          ...entry,
          id: generateId(),
          timestamp: new Date().toISOString(),
        },
        ...state.diary,
      ],
    })),
});
