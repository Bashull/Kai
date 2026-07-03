# 🏗️ Arquitectura de KAI Companion

## Visión General

```
┌─────────────────────────────────────────────────────────────┐
│                     NAVEGADOR WEB                            │
├──────────────────────────────────┬──────────────────────────┤
│   FRONTEND (React + Three.js)    │                          │
│  - Avatar 3D Interactivo         │  - Chat Panel            │
│  - Animaciones en Tiempo Real    │  - Tools Manager         │
│  - Voice I/O (Web Speech API)    │  - Learning Panel        │
│                                  │  - Permissions Panel     │
└──────────────────┬───────────────┴──────────────────────────┘
                   │ WebSocket / REST API
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (Node.js + Express)                    │
├──────────────┬──────────────┬─────────────┬────────────────┤
│  Chat Routes │  Tool Routes │  Learning   │  Permission    │
│              │              │  Routes     │  Routes        │
├──────────────┴──────────────┴─────────────┴────────────────┤
│                    Core Engines                             │
├──────────────────────────────────────────────────────────────┤
│  - ToolEngine       (Crear/Ejecutar herramientas)           │
│  - LearningEngine   (Ingesta y consulta de conocimiento)    │
│  - PermissionSystem (Control de acceso granular)            │
│  - AvatarController (Gestionar animaciones y gestos)        │
├──────────────────────────────────────────────────────────────┤
│                    Base de Datos                             │
│  SQLite con tablas: companion, tools, knowledge_base,       │
│  permissions, skills, animations, audit_log                │
└──────────────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. **Frontend (React)**

#### Estructura
```
frontend/src/
├── App.js                 # Componente raíz
├── App.css               # Estilos globales
└── components/
    ├── Avatar3D.js       # Avatar 3D con Three.js/Fiber
    ├── ChatPanel.js      # Interface de chat
    ├── ToolsPanel.js     # Gestor de herramientas
    ├── LearningPanel.js  # Panel de aprendizaje
    └── PermissionsPanel.js # Panel de permisos
```

#### Avatar3D.js
- Renderizado 3D con Three.js via React Three Fiber
- Geometrías básicas (esferas, cubos)
- Animaciones con loop de frame
- Responde a eventos WebSocket

#### ChatPanel.js
- Input de texto y voz
- Historial de mensajes
- WebSocket para comunicación bidireccional
- Integration con Web Speech API

### 2. **Backend (Node.js)**

#### server.js
- Express como framework HTTP
- Socket.IO para comunicación real-time
- CORS habilitado
- Multer para file uploads

#### database.js
- SQLite3 como base de datos
- Inicialización automática de tablas
- Promisified para async/await
- Rutas de datos persistentes

#### Engines

**ToolEngine.js**
```javascript
// Crear herramientas dinámicas
createTool(config) -> Promise<Tool>

// Ejecutar en contexto seguro
executeTool(toolId, params) -> Promise<Result>

// Gestión CRUD
listTools() -> Promise<Tool[]>
deleteTool(toolId) -> Promise<void>
```

**LearningEngine.js**
```javascript
// Ingesta de archivos
ingestFile(filePath, type) -> Promise<{ id, chunks }>

// Búsqueda semántica
queryKnowledge(query) -> Promise<Result[]>

// Sistema de skills
learnSkill(name, proficiency) -> Promise<Skill>
improveSkill(skillId, increment) -> Promise<Skill>
```

**PermissionSystem.js**
```javascript
// Solicitar/Otorgar permisos
requestPermission(resource, action)
grantPermission(resource, action, expiresIn)
revokePermission(resource, action)

// Verificación
hasPermission(resource, action) -> Promise<boolean>

// Auditoría
logAction(action, resource, status, details)
```

#### Controllers

**avatarController.js**
- Gestión de estado del avatar
- Creación de gestos personalizados
- Procesamiento de input de usuario

**toolController.js**
- CRUD operations para tools
- Ejecución segura de código

**fileController.js**
- Upload y procesamiento de archivos
- Integración con LearningEngine

### 3. **Base de Datos (SQLite)**

#### Tablas

```sql
-- Información del companion
companion {
  id, name, personality, created_at, updated_at
}

-- Herramientas disponibles
tools {
  id, name, description, code, language, 
  created_at, updated_at, enabled
}

-- Base de conocimiento
knowledge_base {
  id, source, content, embeddings, type, 
  created_at, relevance
}

-- Control de permisos
permissions {
  id, resource, action, allowed, 
  expires_at, created_at
}

-- Habilidades aprendidas
skills {
  id, name, proficiency, category, 
  learned_from, created_at, updated_at
}

-- Animaciones personalizadas
animations {
  id, name, frames, duration, created_at
}

-- Registro de auditoría
audit_log {
  id, action, resource, status, 
  details, created_at
}
```

## Flujo de Datos

### 1. Chat con Kai
```
Usuario -> Input → Frontend
  ↓
Frontend → WebSocket → Backend
  ↓
Backend → processInput() → Response
  ↓
Response → WebSocket → Frontend
  ↓
Frontend → Actualizar Avatar + Mensaje
```

### 2. Crear Herramienta
```
Usuario → Formulario → Frontend
  ↓
Frontend → POST /api/tools/create → Backend
  ↓
Backend → ToolEngine.createTool()
  ↓
BD (SQLite) ← Guardar tool
  ↓
Archivo ← Guardar código
  ↓
Response → Frontend
```

### 3. Subir Archivo de Conocimiento
```
Usuario → Selecciona archivo → Frontend
  ↓
Frontend → Multipart POST /api/learning/upload → Backend
  ↓
Backend → LearningEngine.ingestFile()
  ↓
Parse (PDF/TXT/JSON) → Embeddings
  ↓
BD (SQLite) ← Guardar en knowledge_base
  ↓
Response con chunks procesados → Frontend
```

### 4. Sistema de Permisos
```
Tool/Engine → Necesita acceso → requestPermission()
  ↓
BD ← Registrar en tabla permissions
  ↓
Frontend ← Notificar usuario
  ↓
Usuario → Aprueba/Rechaza
  ↓
BD ← Actualizar estado
  ↓
Tool ← Continua si allowed
```

## Seguridad

### Aislamiento de Código
```javascript
// Las tools se ejecutan en un contexto limitado
const fn = new Function('params', code);
// No tienen acceso a require, fs, network
```

### Control de Permisos
- Cada acción verifica permisos antes de ejecutarse
- Permisos pueden expirar automáticamente
- Auditoría completa de acciones

### Validación de Input
- Multer limita tamaño de archivos
- Validación de tipos de archivo
- Sanitización de código

## Escalabilidad

### Actuales (MVP)
- SQLite (OK para desarrollo)
- Embeddings simples (hashing básico)
- Single process

### Futuros (Producción)
- PostgreSQL o MongoDB
- Sentence Transformers para embeddings
- Redis para caché
- Load balancing con múltiples procesos
- Microservicios por dominio

## Performance

### Optimizaciones Actuales
- Caché de gestos en memoria
- Lazy loading de componentes React
- Compresión automática de request/response

### Posibles Mejoras
- Web Workers para procesamiento pesado
- Paginación de resultados de búsqueda
- Índices de BD para queries frecuentes
- Code splitting en frontend

## Extensibilidad

### Agregar Nuevo Panel
```javascript
// 1. Crear componente
frontend/src/components/NewPanel.js

// 2. Registrar en App.js
<NewPanel /> en tab-content

// 3. Crear rutas API si es necesario
backend/routes/newRoutes.js
```

### Agregar Nuevo Engine
```javascript
// 1. Crear engine
backend/newEngine.js

// 2. Integrar en server.js
app.use('/api/new', require('./routes/newRoutes'));

// 3. Crear controlador
backend/controllers/newController.js
```

## Deployment

### Docker
```bash
docker build -t kai-companion .
docker run -p 5000:5000 -p 3000:3000 kai-companion
```

### Kubernetes (Futuro)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kai-companion
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: kai-companion
        image: kai-companion:latest
        ports:
        - containerPort: 5000
```

## Monitoreo

### Logs
- Backend: Salida de consola + archivo
- Frontend: Browser DevTools
- BD: query logs

### Métricas
- Acciones por usuario
- Herramientas más usadas
- Errores más frecuentes
- Performance de queries

---

**Fecha de creación**: 2024
**Versión**: 1.0.0
**Estado**: MVP Funcional
