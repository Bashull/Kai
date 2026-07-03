# 🤖 Guía de Inicio Rápido - KAI Companion

## Opción 1: Instalación Local (Recomendado para Desarrollo)

### Windows

```powershell
# 1. Ir a la carpeta del proyecto
cd C:\Users\ASIER\OneDrive\Documentos\GitHub\Kai\companion

# 2. Instalar dependencias
npm install
cd frontend
npm install
cd ..

# 3. Iniciar (Backend + Frontend)
npm run dev
```

Accede a:
- **Backend**: http://localhost:5000
- **Frontend**: http://localhost:3000

### macOS / Linux

```bash
cd ~/path/to/companion

npm install
cd frontend
npm install
cd ..

npm run dev
```

## Opción 2: Docker (Recomendado para Producción)

```bash
# Construir imagen
docker build -t kai-companion .

# Ejecutar contenedor
docker run -p 5000:5000 -p 3000:3000 -v $(pwd)/data:/app/data kai-companion
```

O con Docker Compose:

```bash
docker-compose up
```

## Primeros Pasos

### 1. Habla con Kai
- Abre http://localhost:3000
- Escribe un mensaje en el chat
- ¡Kai responderá con gestos!

### 2. Crea tu primera herramienta
```bash
POST http://localhost:5000/api/tools/create
{
  "name": "Contar Caracteres",
  "description": "Cuenta caracteres en texto",
  "code": "return params.text.length;",
  "language": "javascript"
}
```

### 3. Sube tu primer archivo de conocimiento
- Ve a "Learning"
- Sube un PDF, TXT o JSON
- Kai absorberá esa información

### 4. Configura permisos
- Ve a "Permissions"
- Solicita acceso a recursos
- Aprueba o rechaza según necesidad

## Comandos Útiles

```bash
# Solo backend
npm run backend

# Solo frontend
npm run frontend

# Build para producción
npm run build

# Limpiar datos
rm -rf data/companion.db data/uploads/*
```

## Variables de Entorno (.env)

```env
PORT=5000                           # Puerto del servidor
NODE_ENV=development               # development o production
DATABASE_PATH=./data/companion.db   # Ubicación de BD
UPLOADS_PATH=./data/uploads         # Carpeta de uploads
ALLOWED_DIRS=./data/projects        # Directorios permitidos
MAX_FILE_SIZE=52428800             # 50MB máximo
COMPANION_NAME=Kai                  # Nombre del companion
DEBUG=true                          # Logs detallados
```

## Acceso a Archivos Seguro

El companion NO tiene acceso directo a tu sistema. Para permitir acceso:

1. **Copia archivos a `data/uploads/`**
2. **Ve a "Learning" → Upload**
3. **El companion absorbe el contenido**

Para dar acceso a carpetas específicas:
1. Ve a "Permissions"
2. Solicita permiso para `filesystem`
3. Aprueba con duración temporal

## Troubleshooting

**❌ "Cannot find module"**
```bash
rm -rf node_modules frontend/node_modules
npm install
cd frontend && npm install && cd ..
```

**❌ Puerto 5000 en uso**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :5000
kill -9 <PID>
```

**❌ Avatar no aparece**
- Abre DevTools (F12)
- Verifica Console para errores de Three.js
- Intenta con Ctrl+Shift+R para hard refresh

**❌ Base de datos corrupta**
```bash
rm data/companion.db
npm run backend  # Se recreará automáticamente
```

## API Rápida

### Chat
```bash
curl -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message":"Hola Kai"}'
```

### Crear Herramienta
```bash
curl -X POST http://localhost:5000/api/tools/create \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Mi Tool",
    "description":"Una herramienta útil",
    "code":"return 42;",
    "language":"javascript"
  }'
```

### Verificar Permiso
```bash
curl http://localhost:5000/api/permissions/check/filesystem/read
```

## Próximos Pasos

1. ✅ Instalar y ejecutar
2. ✅ Explorar la interfaz
3. ✅ Crear herramientas
4. ✅ Subir archivos
5. ✅ Configurar permisos
6. 🔄 Integrar con tu proyecto

## Soporte

- 📖 Lee el README.md completo
- 🐛 Verifica los logs en `logs/`
- 💬 Abre DevTools para debugging

---

**¡Bienvenido a KAI! 🤖✨**
