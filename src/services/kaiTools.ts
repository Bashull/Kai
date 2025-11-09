import { FunctionDeclaration, Type } from '@google/genai';

export const getMemories: FunctionDeclaration = {
  name: 'getMemories',
  description: 'Obtener recuerdos de memoria a largo plazo de Kai.',
  parameters: { type: Type.OBJECT, properties: {} },
};

export const getLongTermMemories: FunctionDeclaration = {
  name: 'getLongTermMemories',
  description: 'Obtener recuerdos de memoria a largo plazo con filtros opcionales.',
  parameters: {
    type: Type.OBJECT,
    properties: {
      type: {
        type: Type.STRING,
        description: 'Tipo de recuerdo: CONVERSATION, KNOWLEDGE, PREFERENCE, o EVENT.',
      },
      limit: {
        type: Type.NUMBER,
        description: 'Número máximo de recuerdos a retornar.',
      },
    },
  },
};

export const addLongTermMemory: FunctionDeclaration = {
  name: 'addLongTermMemory',
  description: 'Añadir un nuevo recuerdo a la memoria a largo plazo.',
  parameters: {
    type: Type.OBJECT,
    properties: {
      content: {
        type: Type.STRING,
        description: 'El contenido del recuerdo.',
      },
      type: {
        type: Type.STRING,
        description: 'Tipo de recuerdo: CONVERSATION, KNOWLEDGE, PREFERENCE, o EVENT.',
      },
      importance: {
        type: Type.NUMBER,
        description: 'Importancia del recuerdo (0-1).',
      },
      tags: {
        type: Type.ARRAY,
        description: 'Etiquetas para categorizar el recuerdo.',
        items: { type: Type.STRING },
      },
    },
    required: ['content', 'type'],
  },
};

export const searchLongTermMemories: FunctionDeclaration = {
  name: 'searchLongTermMemories',
  description: 'Buscar en la memoria a largo plazo usando una consulta de texto.',
  parameters: {
    type: Type.OBJECT,
    properties: {
      query: {
        type: Type.STRING,
        description: 'Término de búsqueda.',
      },
    },
    required: ['query'],
  },
};

export const getDiary: FunctionDeclaration = {
  name: 'getDiary',
  description: 'Obtener entradas del diario de Kai.',
  parameters: { type: Type.OBJECT, properties: {} },
};

export const getSnapshots: FunctionDeclaration = {
  name: 'getSnapshots',
  description: 'Obtener snapshots de conciencia de Kai.',
  parameters: { type: Type.OBJECT, properties: {} },
};

export const searchMemories: FunctionDeclaration = {
  name: 'searchMemories',
  description: 'Buscar recuerdos, diarios o snapshots relacionados con un término.',
  parameters: {
    type: Type.OBJECT,
    properties: {
      query: {
        type: Type.STRING,
        description: 'Término de búsqueda.',
      },
    },
    required: ['query'],
  },
};

export const compileMemory: FunctionDeclaration = {
    name: 'compileMemory',
    description: 'Generar el archivo consolidado de memoria (`memoria_kai.json`). Consolida recuerdos, diarios y snapshots en un solo archivo JSON estructurado.',
    parameters: { type: Type.OBJECT, properties: {} },
};

export const startTraining: FunctionDeclaration = {
  name: 'startTraining',
  description: 'Iniciar un nuevo trabajo de fine-tuning en La Forja.',
  parameters: {
    type: Type.OBJECT,
    properties: {
      modelName: { type: Type.STRING, description: 'El nombre del nuevo modelo a entrenar.' },
      description: { type: Type.STRING, description: 'Una breve descripción del objetivo del entrenamiento.' },
    },
    required: ['modelName', 'description'],
  },
};

export const getTrainingJobStatus: FunctionDeclaration = {
  name: 'getTrainingJobStatus',
  description: 'Verificar el estado de un trabajo de entrenamiento específico en La Forja.',
  parameters: {
    type: Type.OBJECT,
    properties: {
      jobId: { type: Type.STRING, description: 'El ID del trabajo a verificar.' },
    },
    required: ['jobId'],
  },
};


export const kaiTools: FunctionDeclaration[] = [
  getMemories,
  getLongTermMemories,
  addLongTermMemory,
  searchLongTermMemories,
  getDiary,
  getSnapshots,
  searchMemories,
  compileMemory,
  startTraining,
  getTrainingJobStatus,
];
