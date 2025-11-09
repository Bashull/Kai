# 🧠 Sistema de Memoria a Largo Plazo - Kai

## Descripción General

El sistema de memoria a largo plazo de Kai permite almacenar, recuperar y utilizar información importante de manera persistente a través de sesiones. Este sistema mejora significativamente la capacidad de Kai para mantener contexto y proporcionar respuestas más personalizadas y relevantes.

## Arquitectura

### Componentes Principales

#### 1. Tipos de Datos (`src/types.ts`)
- **Memory**: Interfaz principal para los recuerdos
- **MemoryType**: Tipos de recuerdos (CONVERSATION, KNOWLEDGE, PREFERENCE, EVENT)
- **MemorySlice**: Slice de Zustand para el estado de memoria

#### 2. Estado y Persistencia (`src/store/slices/createMemorySlice.ts`)
- Gestión del estado de memoria usando Zustand
- Operaciones CRUD para recuerdos
- Funciones de búsqueda y filtrado
- Persistencia automática en localStorage

#### 3. Integración con IA (`src/services/geminiService.ts`)
- Función `getRelevantMemories`: Encuentra recuerdos relevantes para el contexto
- Scoring basado en:
  - Coincidencia de palabras clave
  - Importancia del recuerdo
  - Antigüedad (recuerdos recientes tienen mayor peso)
- Inyección automática de contexto en conversaciones

#### 4. API de Herramientas (`src/services/kaiTools.ts`)
- `getLongTermMemories`: Obtener recuerdos con filtros
- `addLongTermMemory`: Añadir nuevo recuerdo
- `searchLongTermMemories`: Buscar recuerdos

#### 5. Interfaz de Usuario (`src/components/panels/MemoryPanel.tsx`)
- Vista de lista de recuerdos con filtrado
- Formulario de creación de recuerdos
- Búsqueda por contenido y etiquetas
- Estadísticas de memoria
- Gestión de recuerdos (eliminar, ver detalles)

## Tipos de Recuerdos

### CONVERSATION (Conversación)
Almacena resúmenes de conversaciones importantes. Se crean automáticamente al usar la función "Resumir y Archivar" en el chat.

**Ejemplo:**
```typescript
{
  content: "Discutimos sobre implementar un sistema de autenticación JWT en Node.js",
  type: "CONVERSATION",
  importance: 0.7,
  tags: ["desarrollo", "backend", "seguridad"]
}
```

### KNOWLEDGE (Conocimiento)
Información factual y conocimientos que Kai debe recordar.

**Ejemplo:**
```typescript
{
  content: "El usuario prefiere usar TypeScript sobre JavaScript para proyectos nuevos",
  type: "KNOWLEDGE",
  importance: 0.8,
  tags: ["programación", "preferencias"]
}
```

### PREFERENCE (Preferencia)
Gustos, preferencias y configuraciones del usuario.

**Ejemplo:**
```typescript
{
  content: "Prefiere sesiones de D&D los viernes por la noche",
  type: "PREFERENCE",
  importance: 0.6,
  tags: ["d&d", "horario"]
}
```

### EVENT (Evento)
Eventos significativos que ocurrieron.

**Ejemplo:**
```typescript
{
  content: "Completó el tutorial de React Hooks el 15 de enero",
  type: "EVENT",
  importance: 0.5,
  tags: ["aprendizaje", "react"]
}
```

## Uso del Sistema

### Creación Automática de Recuerdos

Los recuerdos se crean automáticamente cuando:
1. El usuario resume una conversación en el chat (botón "Archivar")
2. Se guarda el resumen en el Kernel
3. Se crea un recuerdo de tipo CONVERSATION con el resumen

```typescript
// En createChatSlice.ts
addMemory({
  content: summary,
  type: 'CONVERSATION',
  importance: 0.7,
  tags: ['chat', 'conversation', 'summary'],
  metadata: {
    messageCount: chatHistory.length,
    date: new Date().toISOString(),
  },
});
```

### Creación Manual de Recuerdos

Los usuarios pueden crear recuerdos manualmente desde el Panel de Memoria:

1. Navegar al panel "Memoria" en la barra lateral
2. Hacer clic en "Nuevo Recuerdo"
3. Completar el formulario:
   - Contenido del recuerdo
   - Tipo (KNOWLEDGE, PREFERENCE, EVENT, CONVERSATION)
   - Importancia (0-1)
   - Etiquetas (separadas por comas)
4. Guardar

### Recuperación de Recuerdos en Conversaciones

Cuando el usuario envía un mensaje:

1. Se extraen palabras clave del mensaje
2. Se buscan recuerdos relevantes usando `getRelevantMemories()`
3. Se asigna un score a cada recuerdo basado en:
   - Coincidencia de palabras clave
   - Importancia del recuerdo
   - Antigüedad (recuerdos recientes = mayor peso)
4. Los top 3 recuerdos más relevantes se añaden al contexto
5. Kai usa este contexto para generar una respuesta más informada

```typescript
const relevantMemories = getRelevantMemories(memories, prompt);
// Se añaden al historial como contexto para la IA
```

### Búsqueda y Filtrado

El Panel de Memoria ofrece:
- **Búsqueda por texto**: Busca en contenido y etiquetas
- **Filtrado por tipo**: Muestra solo un tipo de recuerdo
- **Ordenación**: Los recuerdos se muestran del más reciente al más antiguo

## Persistencia

Los recuerdos se persisten automáticamente en localStorage usando Zustand Persist:

```typescript
// En useAppStore.ts
partialize: (state) => ({
  // ... otros estados
  memories: state.memories,
})
```

Esto significa que:
- Los recuerdos sobreviven a recargas de página
- Se mantienen entre sesiones del navegador
- No se pierden al cerrar la aplicación

## Mejores Prácticas

### Para Usuarios

1. **Etiqueta tus recuerdos**: Usa etiquetas descriptivas para facilitar la búsqueda
2. **Ajusta la importancia**: Asigna mayor importancia a información crítica
3. **Resume conversaciones largas**: Usa el botón "Archivar" regularmente
4. **Revisa periódicamente**: Elimina recuerdos obsoletos del Panel de Memoria

### Para Desarrolladores

1. **Importancia razonable**: Asigna importancia entre 0.5-0.8 para contenido general
2. **Metadatos útiles**: Incluye metadatos relevantes en el campo `metadata`
3. **Tipos apropiados**: Usa el tipo correcto para cada recuerdo
4. **Límite de contexto**: Actualmente se usan máximo 3 recuerdos por conversación

## Limitaciones Actuales

1. **Búsqueda Simple**: La búsqueda actual es basada en coincidencia de texto, no semántica
2. **Sin FAISS**: Aunque está planeado, FAISS no está integrado en el frontend actualmente
3. **Límite de Contexto**: Solo 3 recuerdos se incluyen por conversación
4. **localStorage**: Limitado por cuotas del navegador (típicamente 5-10MB)

## Roadmap Futuro

### Próximas Mejoras

1. **Integración FAISS**: 
   - Búsqueda vectorial semántica
   - Mejor relevancia en recuperación
   - Embeddings para cada recuerdo

2. **Backend Persistente**:
   - Base de datos dedicada
   - Sin límites de almacenamiento
   - Sincronización entre dispositivos

3. **Importancia Adaptativa**:
   - Ajuste automático basado en uso
   - Degradación de recuerdos antiguos
   - Promoción de recuerdos útiles

4. **Categorización Automática**:
   - IA determina tipo de recuerdo
   - Extracción automática de etiquetas
   - Detección de información importante

5. **Visualización Mejorada**:
   - Timeline de recuerdos
   - Gráficos de relaciones
   - Mapas de conocimiento

## API de Desarrollo

### Añadir un Recuerdo

```typescript
import { useAppStore } from '@/store/useAppStore';

const { addMemory } = useAppStore();

addMemory({
  content: "Mi información importante",
  type: "KNOWLEDGE",
  importance: 0.8,
  tags: ["tag1", "tag2"],
  metadata: { source: "manual" }
});
```

### Buscar Recuerdos

```typescript
const { searchMemories } = useAppStore();

const results = searchMemories("JavaScript");
console.log(results); // Array de recuerdos coincidentes
```

### Obtener Recuerdos Recientes

```typescript
const { getRecentMemories } = useAppStore();

const recent = getRecentMemories(5);
console.log(recent); // Últimos 5 recuerdos
```

### Filtrar por Tipo

```typescript
const { getMemoriesByType } = useAppStore();

const conversations = getMemoriesByType("CONVERSATION");
console.log(conversations); // Solo recuerdos de conversaciones
```

## Preguntas Frecuentes

### ¿Los recuerdos se comparten entre usuarios?
No, los recuerdos están vinculados a la sesión del navegador local y no se comparten.

### ¿Cuántos recuerdos puedo almacenar?
El límite está dado por localStorage del navegador (típicamente 5-10MB). En la práctica, esto permite miles de recuerdos.

### ¿Puedo exportar mis recuerdos?
Actualmente no, pero está en el roadmap. Por ahora, los datos están en localStorage y pueden ser exportados manualmente.

### ¿Los recuerdos afectan el rendimiento?
El impacto es mínimo. La búsqueda es eficiente y solo se procesan los recuerdos necesarios para cada conversación.

### ¿Cómo elimino todos mis recuerdos?
Puedes limpiar localStorage del navegador o eliminarlos uno por uno desde el Panel de Memoria.

## Conclusión

El sistema de memoria a largo plazo convierte a Kai en un compañero verdaderamente personalizado que aprende y se adapta con el tiempo. A medida que uses Kai, el sistema construirá una base de conocimiento rica que mejorará la calidad de las interacciones futuras.

---

**Última actualización**: 2025-11-09
**Versión**: 3.0.0
