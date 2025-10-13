import { KernelSlice, AppSlice, Entity } from '../../types';
import { generateId } from '../../utils/helpers';

const initialEntities: Entity[] = [
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