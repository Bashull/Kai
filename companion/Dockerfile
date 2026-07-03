FROM node:18-alpine

WORKDIR /app

# Copiar package.json
COPY package.json package-lock.json ./

# Instalar dependencias backend
RUN npm install

# Copiar código backend
COPY backend ./backend
COPY init.js .

# Copiar frontend
COPY frontend ./frontend
WORKDIR /app/frontend
RUN npm install
WORKDIR /app

# Exponemos puertos
EXPOSE 5000 3000

# Crear directorios necesarios
RUN node init.js

# Comando por defecto
CMD ["npm", "start"]
