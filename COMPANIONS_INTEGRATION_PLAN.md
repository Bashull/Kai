# 🤝 Plan de Integración: Kai Companions

## Visión General

Fusionar la aplicación Kai existente (React/TypeScript) con un sistema de "Companions" - agentes de código interactivos con avatar animado que actúan como asistentes de programación vivientes.

---

## 🎯 Objetivos

1. **Mantener** toda la funcionalidad actual de Kai
2. **Añadir** un nuevo panel "Companions" con avatar interactivo
3. **Integrar** capacidades de asistencia de código y compilación
4. **Crear** una experiencia gamificada tipo IA Studio/VS Code

---

## 📐 Arquitectura Propuesta

### Estructura de Directorios Expandida

```
Kai/
├── src/
│   ├── components/
│   │   ├── panels/          (existentes)
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── LivePanel.tsx
│   │   │   ├── ForgePanel.tsx
│   │   │   └── **CompanionsPanel.tsx** (NUEVO)
│   │   ├── companions/      (NUEVO)
│   │   │   ├── AvatarEngine.tsx
│   │   │   ├── CodeAssistant.tsx
│   │   │   ├── VoiceInterface.tsx
│   │   │   └── AnimationController.tsx
│   │   └── ui/
│   ├── services/
│   │   ├── geminiService.ts (existente)
│   │   ├── **companionsService.ts** (NUEVO)
│   │   ├── **codeExecutor.ts** (NUEVO)
│   │   └── **avatarStates.ts** (NUEVO)
│   ├── store/
│   │   └── slices/
│   │       └── **createCompanionsSlice.ts** (NUEVO)
│   └── types.ts (actualizar)
└── docs/
    └── **COMPANIONS_SPEC.md** (NUEVO)
```

---

## 🧩 Módulos a Implementar

### 1. CompanionsPanel (Nuevo Panel en Sidebar)

**Ubicación**: `src/components/panels/CompanionsPanel.tsx`

**Funcionalidades**:
- Visualización del avatar 2D/3D
- Chat interactivo con el companion
- Panel de código con editor Monaco
- Consola de ejecución
- Estado emocional del avatar

**Tecnología**:
- React Three Fiber para avatar 3D (opción avanzada)
- O Canvas 2D con sprites animados (opción ligera)
- Monaco Editor para código
- WebSocket para comunicación en tiempo real

---

### 2. AvatarEngine Component

**Ubicación**: `src/components/companions/AvatarEngine.tsx`

**Responsabilidades**:
- Renderizar avatar animado
- Gestionar estados emocionales (pensando, hablando, feliz, error)
- Sincronizar animaciones con acciones
- Sistema de partículas para efectos visuales

**Estados del Avatar**:
```typescript
type AvatarState = 
  | 'idle'      // En reposo
  | 'listening' // Escuchando input
  | 'thinking'  // Procesando
  | 'coding'    // Generando código
  | 'happy'     // Éxito
  | 'error'     // Error
  | 'explaining'; // Explicando
```

---

### 3. CodeAssistant Service

**Ubicación**: `src/services/companionsService.ts`

**Funcionalidades**:
- Integración con Gemini API (ya existente)
- Generación de código asistida
- Análisis de repositorios
- Sugerencias contextuales
- Memoria de conversación

**API**:
```typescript
interface CompanionsService {
  generateCode(prompt: string, context: CodeContext): Promise<string>;
  explainCode(code: string): Promise<string>;
  suggestImprovements(code: string): Promise<string[]>;
  executeCode(code: string, language: string): Promise<ExecutionResult>;
}
```

---

### 4. CodeExecutor Service

**Ubicación**: `src/services/codeExecutor.ts`

**Funcionalidades**:
- Ejecutar código JavaScript/TypeScript en sandbox
- Mostrar resultados en consola
- Capturar errores y explicarlos
- Integración con servicios externos para otros lenguajes

**Seguridad**:
- Sandbox aislado
- Límites de tiempo de ejecución
- Restricciones de API

---

### 5. CompanionsSlice (Estado Global)

**Ubicación**: `src/store/slices/createCompanionsSlice.ts`

**Estado**:
```typescript
interface CompanionsSlice {
  // Avatar
  avatarState: AvatarState;
  avatarMood: number; // 0-1
  
  // Conversación
  messages: CompanionMessage[];
  isProcessing: boolean;
  
  // Código
  currentCode: string;
  codeLanguage: string;
  executionOutput: string;
  
  // Configuración
  voiceEnabled: boolean;
  animationsEnabled: boolean;
  
  // Métodos
  sendMessage: (text: string) => Promise<void>;
  generateCode: (prompt: string) => Promise<void>;
  executeCurrentCode: () => Promise<void>;
  setAvatarState: (state: AvatarState) => void;
}
```

---

## 🎨 UI/UX Design

### CompanionsPanel Layout

```
┌─────────────────────────────────────┐
│  Kai Companion                   [⚙] │
├──────────────┬──────────────────────┤
│              │                      │
│   Avatar     │   Code Editor        │
│   (3D/2D)    │   (Monaco)           │
│              │                      │
│   [Estado]   │   [Ejecutar] [Limpiar]│
│              │                      │
├──────────────┴──────────────────────┤
│  Chat Interface                     │
│  > User: Crea una función que...    │
│  < Companion: ¡Claro! Aquí está...  │
│  [___________________________] [📤]  │
└─────────────────────────────────────┘
```

---

## 🔄 Flujo de Interacción

### Escenario 1: Generación de Código

1. Usuario escribe: "Crea una función que calcule fibonacci"
2. Avatar cambia a estado `thinking`
3. CompanionsService llama a Gemini API
4. Código se genera y aparece en Monaco Editor
5. Avatar cambia a estado `happy` y explica el código
6. Usuario puede ejecutar o modificar

### Escenario 2: Ejecución de Código

1. Usuario presiona "Ejecutar"
2. Avatar cambia a estado `coding`
3. CodeExecutor ejecuta en sandbox
4. Resultados aparecen en consola
5. Si error: Avatar cambia a `error` y explica
6. Si éxito: Avatar cambia a `happy` y celebra

---

## 📋 Fases de Implementación

### Fase 1: Estructura Base (Semana 1)
- [x] Documento de planificación
- [ ] Crear CompanionsPanel básico
- [ ] Añadir al sidebar navigation
- [ ] Integrar con sistema de routing
- [ ] Setup store slice

### Fase 2: Avatar Básico (Semana 2)
- [ ] Implementar AvatarEngine con Canvas 2D
- [ ] Sistema de estados básicos
- [ ] Animaciones simples
- [ ] Integración con mensajes

### Fase 3: Asistencia de Código (Semana 3)
- [ ] CompanionsService con Gemini
- [ ] Generación de código
- [ ] Monaco Editor integration
- [ ] Sistema de contexto

### Fase 4: Ejecución (Semana 4)
- [ ] CodeExecutor service
- [ ] Sandbox JavaScript
- [ ] Consola de output
- [ ] Manejo de errores

### Fase 5: Mejoras Avanzadas (Opcional)
- [ ] Upgrade a React Three Fiber (3D)
- [ ] Voice interface
- [ ] Memoria persistente
- [ ] Multi-lenguaje support
- [ ] Gamificación

---

## 🔧 Tecnologías Requeridas

### Nuevas Dependencias

```json
{
  "dependencies": {
    "@react-three/fiber": "^8.15.0",      // 3D (opcional)
    "@react-three/drei": "^9.88.0",       // 3D helpers
    "monaco-editor": "^0.45.0",           // Ya en @monaco-editor/react
    "web-worker": "^1.2.0"                // Para sandbox
  }
}
```

### APIs Existentes a Reutilizar
- ✅ Gemini API (geminiService.ts)
- ✅ Zustand store
- ✅ Framer Motion (animaciones)
- ✅ Lucide React (iconos)

---

## 🎮 Características Gamificadas

### Sistema de Progreso
- **Nivel de Afinidad**: Aumenta con interacciones
- **Logros**: "Primer código ejecutado", "10 bugs resueltos"
- **Personalización**: Elegir apariencia del avatar
- **Misiones**: Retos de código diarios

### Reacciones Contextuales
- Código correcto → Avatar celebra
- Error de sintaxis → Avatar muestra confusión
- Optimización sugerida → Avatar hace gesto de "idea"

---

## 🔐 Consideraciones de Seguridad

1. **Sandbox de Ejecución**:
   - Aislar código en Web Worker
   - Timeouts estrictos
   - Sin acceso a localStorage/cookies

2. **Validación de Input**:
   - Sanitizar prompts
   - Limitar tamaño de código
   - Rate limiting en API calls

3. **Privacidad**:
   - Código no se envía a servidores externos
   - Solo prompts a Gemini API
   - Opción de modo offline

---

## 📊 Métricas de Éxito

- ✅ Panel Companions integrado sin romper funcionalidad existente
- ✅ Avatar responde en <2 segundos
- ✅ Código ejecutable sin errores de sandbox
- ✅ Experiencia fluida 60fps
- ✅ Bundle size incremento <500kb

---

## 🚀 Próximos Pasos Inmediatos

1. **Crear estructura base**:
   - `CompanionsPanel.tsx`
   - `createCompanionsSlice.ts`
   - `companionsService.ts`

2. **Actualizar tipos**:
   - Añadir `Panel = ... | 'companions'`
   - Definir interfaces de Companions

3. **Actualizar sidebar**:
   - Añadir ícono y navegación

4. **Implementar MVP**:
   - Chat básico
   - Avatar estático inicial
   - Integración con Gemini

---

**Autor**: Kai Development Team  
**Versión**: 1.0 - Plan Inicial  
**Fecha**: 14 Nov 2025  
**Estado**: 📋 En Planificación

---

## 🧬 CHI-Genome Integration

### Sistema de Física Cognitiva

El avatar Companions incluye el sistema **CHI-Genome v0.1** - física cognitiva que define cómo "respira" y evoluciona el avatar.

#### Variables CHI

- **Energía (E)**: Capacidad de procesar (0-1)
- **Coherencia (C)**: Claridad de pensamiento (0-1)
- **Entropía (H)**: Creatividad/caos (0-1)
- **Fatiga**: Cansancio acumulado (0-1)

#### Integración en Companions

```typescript
// CompanionsSlice incluye CHI state
interface CompanionsSlice {
  // ... campos existentes
  chiEngine: CHIEngine;
  chiState: CHIState;
  emotionalState: EmotionalState;
}

// Avatar reacciona al CHI state
const AvatarEngine = () => {
  const { chiState } = useCompanions();
  const visuals = calculateVisualEffects(chiState);
  
  return <Avatar visuals={visuals} />;
};
```

#### Actualización Automática

- Cada input del usuario actualiza CHI state
- Estado emocional deriva de E/C/H
- Animaciones reflejan estado interno
- Auto-adaptación cada 10 minutos
- Persistencia en localStorage

#### Efectos Visuales CHI

| Variable | Efecto Visual |
|----------|---------------|
| Alta Energía | Partículas rápidas, brillo |
| Alta Coherencia | Anillo de enfoque, estabilidad |
| Alta Entropía | Partículas caóticas, colores |
| Alta Fatiga | Opacidad reducida, temblor |

#### Documentación

- **docs/CHI_GENOME_SPEC.md**: Especificación completa
- **src/services/chiEngine.ts**: Implementación TypeScript

---

**Actualizado**: 14 Nov 2025  
**CHI-Genome**: v0.1 Integrado
