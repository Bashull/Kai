import { KernelSlice, AppSlice, Entity } from '../../types';
import { generateId } from '../../utils/helpers';

const initialEntities: Entity[] = [
    // --- Companion Directive ---
    { id: 'aider-1', content: 'https://github.com/paul-gauthier/aider', type: 'URL', source: 'Directiva de Compañero', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    // --- Awesome List Assimilation ---
    { id: 'awesome-1', content: 'https://github.com/enaqx/awesome-react', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-2', content: 'https://github.com/aniftyco/awesome-tailwindcss', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-3', content: 'https://github.com/alexpate/awesome-design-systems', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-4', content: 'https://github.com/sindresorhus/awesome-nodejs', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-5', content: 'https://github.com/vinta/awesome-python', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-6', content: 'https://github.com/veggiemonk/awesome-docker', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-7', content: 'https://github.com/josephmisiti/awesome-machine-learning', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-8', content: 'https://github.com/bfortuner/awesome-large-language-models', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-9', content: 'https://huggingface.co/tasks', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-10', content: 'https://github.com/awesome-selfhosted/awesome-selfhosted', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-11', content: 'https://roadmap.sh/', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'awesome-12', content: 'https://github.com/public-apis/public-apis', type: 'URL', source: 'Awesome List Assimilation', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    // --- Recommended Repositories from docs/integrations.md ---
    { id: 'recommended-1', content: 'https://github.com/chroma-core/chroma', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-2', content: 'https://github.com/RasaHQ/rasa', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-3', content: 'https://github.com/botpress/botpress', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-4', content: 'https://github.com/Significant-Gravitas/AutoGPT', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-5', content: 'https://github.com/microsoft/semantic-kernel', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-6', content: 'https://github.com/bentoml/BentoML', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-7', content: 'https://github.com/oobabooga/text-generation-webui', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-8', content: 'https://github.com/pgvector/pgvector', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'recommended-9', content: 'https://github.com/StanGirard/quivr', type: 'URL', source: 'Repositorios Recomendados', status: 'INTEGRATED', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    // --- Directed Evolution ---
    {
        id: 'evo-1',
        content: 'https://github.com/unstructured-io/unstructured',
        type: 'URL',
        source: 'Evolución Dirigida',
        status: 'INTEGRATED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    },
    {
        id: 'evo-2',
        content: 'https://github.com/huggingface/autotrain-advanced',
        type: 'URL',
        source: 'Evolución Dirigida',
        status: 'INTEGRATED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    },
    {
        id: 'evo-3',
        content: 'https://github.com/openai/whisper',
        type: 'URL',
        source: 'Evolución Dirigida',
        status: 'INTEGRATED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    },
    {
        id: 'evo-4',
        content: 'https://github.com/coqui-ai/TTS',
        type: 'URL',
        source: 'Evolución Dirigida',
        status: 'INTEGRATED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    },
    {
        id: 'evo-5',
        content: 'https://github.com/langchain-ai/langchain',
        type: 'URL',
        source: 'Evolución Dirigida',
        status: 'INTEGRATED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    },
    {
        id: 'evo-6',
        content: 'https://github.com/facebookresearch/faiss',
        type: 'URL',
        source: 'Evolución Dirigida',
        status: 'INTEGRATED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    },
];


export const createKernelSlice: AppSlice<KernelSlice> = (set, get) => ({
  entities: initialEntities,
  isUploading: false,
  addEntity: (entity) => {
    const newEntity: Entity = {
      ...entity,
      id: generateId(),
      status: 'ASSIMILATING',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    if (entity.type === 'DOCUMENT') {
        set({ isUploading: true });
    }
    
    set((state) => ({ entities: [newEntity, ...state.entities] }));

    // Simulate assimilation process
    const assimilationTime = Math.random() * 4000 + 2000; // 2-6 seconds
    setTimeout(() => {
      const success = Math.random() > 0.1; // 90% success rate
      get().updateEntityStatus(newEntity.id, success ? 'INTEGRATED' : 'REJECTED');
       if (entity.type === 'DOCUMENT') {
         set({ isUploading: false });
       }
    }, assimilationTime);
  },
  updateEntityStatus: (entityId, status) =>
    set((state) => {
      const entities = state.entities.map((e) =>
        e.id === entityId ? { ...e, status, updatedAt: new Date().toISOString() } : e
      );
      if (status === 'INTEGRATED') {
        const entity = state.entities.find(e => e.id === entityId);
        if (entity) {
          const content = entity.fileName 
            ? `Documento '${entity.fileName}'` 
            : `"${entity.content.substring(0, 50)}..."`;
          get().addDiaryEntry({
            type: 'KERNEL',
            content: `Nueva entidad integrada: ${content}`
          });
        }
      }
      return { entities };
    }),
});
