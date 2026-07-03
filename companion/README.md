# 🤖 KAI - Advanced AI Companion

Un companion IA avanzado con avatar 3D animado, capacidad de crear herramientas dinámicas, aprendizaje absorbiendo archivos externos, y sistema de permisos seguro.

## 🌟 Características

### 🎯 Avatar 3D Interactivo
- Personaje 3D animado en tiempo real
- Gestos y emociones dinámicas
- Movimiento fluido con animaciones
- Expresiones faciales interactivas
- Interfaz immersiva con Three.js

### 🧠 Sistema de Aprendizaje
- Ingesta de archivos externos (PDF, TXT, JSON, Markdown)
- Base de conocimiento persistente
- Búsqueda semántica de información
- Embeddings para relevancia contextual
- Mejora continua de habilidades

### 🛠️ Creación Dinámica de Herramientas
- El companion crea sus propias herramientas
- Ejecución segura de código
- Gestor de herramientas inteligente
- Versionado y auditoría
- Extensible con plugins

### 🔐 Sistema de Permisos Granular
- Permisos basados en recursos y acciones
- Control temporal de accesos
- Auditoría completa de operaciones
- Aprobación manual de permisos
- Revocación en tiempo real

### 🎤 Interacción Multimodal
- Chat de texto en tiempo real
- Reconocimiento de voz (Web Speech API)
- Síntesis de voz
- WebSocket para comunicación bidireccional
- Respuestas contextuales

## 📋 Requisitos

- Node.js 14+
- npm o yarn
- 200MB de espacio en disco

## 🚀 Instalación

### 1. Clonar o descargar el repositorio
```bash
cd companion
```

### 2. Instalar dependencias del backend
```bash
npm install
```

### 3. Instalar dependencias del frontend
```bash
cd frontend
npm install
cd ..
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env según necesidad
```

## 🎬 Inicio Rápido

### Modo Desarrollo (Backend + Frontend simultáneo)
```bash
npm run dev
```

- Backend: http://localhost:5000
- Frontend: http://localhost:3000

### Solo Backend
```bash
npm run backend
```

### Solo Frontend
```bash
npm run frontend
```

## 📖 Guía de Uso

### 1. Chat con Kai
- Escribe un mensaje en el panel de chat
- Usa el botón 🎤 para input de voz
- El companion responderá con gestos animados

### 2. Crear Herramientas
- Ve a la pestaña "Tools"
- Haz clic en "➕ New Tool"
- Define nombre, descripción y código JavaScript
- El companion puede ahora usar esa herramienta

Ejemplo de herramienta:
```javascript
// Convertir texto a mayúsculas
params.text.toUpperCase()
```

### 3. Entrenar con Archivos
- Ve a la pestaña "Learning"
- Carga archivos (PDF, TXT, JSON, MD)
- El companion absorberá el conocimiento
- Usa "Query Knowledge Base" para buscar información

### 4. Gestionar Permisos
- Ve a la pestaña "Permissions"
- Solicita permisos específicos
- Aprueba o rechaza según sea necesario
- Revoca permisos en cualquier momento

## 📁 Estructura del Proyecto

```
companion/
├── backend/
│   ├── server.js              # Servidor principal Express
│   ├── database.js            # Gestión de SQLite
│   ├── permissions.js         # Sistema de permisos
│   ├── toolEngine.js          # Motor de herramientas
│   ├── learningEngine.js      # Motor de aprendizaje
│   ├── controllers/           # Controladores API
│   └── routes/                # Rutas API
├── frontend/
│   ├── src/
│   │   ├── App.js             # Componente principal
│   │   ├── App.css            # Estilos
│   │   └── components/
│   │       ├── Avatar3D.js    # Avatar 3D con Three.js
│   │       ├── ChatPanel.js   # Panel de chat
│   │       ├── ToolsPanel.js  # Gestor de herramientas
│   │       ├── LearningPanel.js
│   │       └── PermissionsPanel.js
│   ├── public/
│   └── package.json
├── data/                      # Base de datos y uploads
├── docs/                      # Documentación
└── package.json
```

## 🔌 API Endpoints

### Avatar
- `GET /api/avatar/state` - Obtener estado del avatar
- `POST /api/avatar/animate` - Animar avatar
- `GET /api/avatar/gestures` - Listar gestos
- `POST /api/avatar/gesture` - Crear gesto

### Herramientas
- `GET /api/tools/list` - Listar herramientas
- `POST /api/tools/create` - Crear herramienta
- `POST /api/tools/execute/:toolId` - Ejecutar herramienta
- `DELETE /api/tools/:toolId` - Eliminar herramienta

### Aprendizaje
- `POST /api/learning/upload` - Subir archivo
- `POST /api/learning/query` - Consultar base de conocimiento
- `GET /api/learning/stats` - Estadísticas

### Permisos
- `GET /api/permissions/list` - Listar permisos
- `POST /api/permissions/request` - Solicitar permiso
- `POST /api/permissions/grant` - Otorgar permiso
- `POST /api/permissions/revoke` - Revocar permiso
- `GET /api/permissions/check/:resource/:action` - Verificar permiso

### Chat
- `POST /api/chat/message` - Enviar mensaje

### Sistema
- `GET /api/system/status` - Estado del sistema

## 🎨 Personalización

### Cambiar apariencia del avatar
Edita `frontend/src/components/Avatar3D.js`:
```javascript
// Cambiar color de piel
<meshStandardMaterial color="#fdbcb4" />

// Cambiar ropa
<meshStandardMaterial color="#4a90e2" />
```

### Agregar nuevas animaciones
En la pestaña Permissions, crea gestos personalizados con keyframes.

### Modificar comportamiento del aprendizaje
Ajusta `backend/learningEngine.js` para cambiar la forma de procesar documentos.

## 🔒 Seguridad

- ✅ Aislamiento de código (ejecuta en contexto limitado)
- ✅ Permisos granulares por recurso
- ✅ Auditoría completa de acciones
- ✅ Sin acceso directo al sistema de archivos
- ✅ Validación de entrada en todos los endpoints

## 📊 Base de Datos

SQLite con las siguientes tablas:
- `companion` - Información del companion
- `tools` - Herramientas creadas
- `knowledge_base` - Base de conocimiento
- `permissions` - Permisos otorgados
- `skills` - Habilidades aprendidas
- `animations` - Animaciones y gestos
- `audit_log` - Registro de auditoría

## 🔧 Desarrollo

### Agregar nueva ruta API
1. Crear archivo en `backend/routes/`
2. Agregar router en `backend/server.js`
3. Crear controlador correspondiente

### Agregar nuevo panel UI
1. Crear componente en `frontend/src/components/`
2. Importar en `App.js`
3. Agregar tab en la sección de tabs

## 📝 Ejemplos de Uso

### Crear herramienta de cálculo
```javascript
// Name: Math Evaluator
// Code:
return eval(params.expression)
```

### Subir documentación
- Ve a Learning
- Sube tu PDF/TXT
- El companion recordará la información

### Solicitar acceso a archivos
- Companion pide permiso para leer archivos
- Apruebas con duración temporal
- Después se revoca automáticamente

## 🐛 Troubleshooting

**Avatar no aparece:**
- Verifica que Three.js esté cargado
- Comprueba la consola del navegador

**Backend no conecta:**
- Asegúrate de que el puerto 5000 esté disponible
- Verifica las variables de `.env`

**Archivos no suben:**
- Comprueba los permisos de carpeta `data/uploads/`
- Verifica el tamaño máximo en `.env`

## 📞 Soporte

Para problemas o sugerencias, crea un issue o contacta al desarrollador.

## 📄 Licencia

MIT License - Libre para uso personal y comercial

## 🚀 Roadmap

- [ ] Integración con IA generativa (GPT, Claude, etc.)
- [ ] Sincronización multi-dispositivo
- [ ] Exportación de habilidades
- [ ] Interfaz móvil nativa
- [ ] Multiplayer collaboration
- [ ] Análisis avanzado de embeddings

---

**Hecho con ❤️ para acompañar tu viaje tecnológico**
