const express = require('express');
const cors = require('cors');
const http = require('http');
const socketIO = require('socket.io');
const multer = require('multer');
require('dotenv').config();

const db = require('./database');
const avatarController = require('./controllers/avatarController');
const toolController = require('./controllers/toolController');
const fileController = require('./controllers/fileController');

const app = express();
const server = http.createServer(app);
const io = socketIO(server, {
  cors: { origin: '*', methods: ['GET', 'POST'] }
});

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

const upload = multer({
  dest: process.env.UPLOADS_PATH || './data/uploads',
  limits: { fileSize: parseInt(process.env.MAX_FILE_SIZE || '52428800', 10) }
});

(async () => {
  try {
    await db.init();
    console.log('✅ Database initialized');
  } catch (error) {
    console.error('❌ Database init failed:', error);
  }
})();

app.use('/api/avatar', require('./routes/avatarRoutes'));
app.use('/api/tools', require('./routes/toolRoutes'));
app.use('/api/learning', require('./routes/learningRoutes'));
app.use('/api/files', require('./routes/fileRoutes'));
app.use('/api/permissions', require('./routes/permissionRoutes'));
app.use('/api/chat', require('./routes/chatRoutes'));
app.use('/api/system', require('./routes/systemRoutes'));

io.on('connection', (socket) => {
  console.log('👤 Client connected:', socket.id);

  socket.on('companion:speak', async (data) => {
    const response = await avatarController.processInput(data);
    socket.emit('companion:response', response);
  });

  socket.on('companion:animate', (data) => {
    io.emit('companion:animation', data);
  });

  socket.on('tool:create', async (data) => {
    const tool = await require('./toolEngine').createTool(data);
    io.emit('tool:created', tool);
  });

  socket.on('disconnect', () => {
    console.log('👋 Client disconnected:', socket.id);
  });
});

app.use((err, req, res, next) => {
  console.error('❌ Error:', err);
  res.status(500).json({ error: err.message || 'Internal server error' });
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`🚀 Companion running on http://localhost:${PORT}`);
  console.log('📡 WebSocket ready for real-time communication');
});

module.exports = { app, io };
