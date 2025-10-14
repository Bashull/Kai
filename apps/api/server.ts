import express, { Request, Response } from 'express';

const app = express();
const PORT = process.env.PORT || 3000;

// Store the start time to calculate uptime
const startTime = Date.now();

// Middleware
app.use(express.json());

// GET /status endpoint
app.get('/status', (_req: Request, res: Response) => {
  try {
    // Calculate uptime in seconds
    const uptimeSeconds = Math.floor((Date.now() - startTime) / 1000);
    
    // Get memory usage (in MB)
    const memoryUsage = process.memoryUsage();
    const memoryInfo = {
      rss: Math.round(memoryUsage.rss / 1024 / 1024), // Resident Set Size in MB
      heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024), // Total heap allocated in MB
      heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024), // Heap actually used in MB
      external: Math.round(memoryUsage.external / 1024 / 1024), // External memory in MB
    };
    
    // Get mode from environment variable (default to 'development')
    const mode = process.env.NODE_ENV || 'development';
    
    res.status(200).json({
      status: 'ok',
      mode,
      uptime: uptimeSeconds,
      memory: memoryInfo,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: 'Internal server error',
    });
  }
});

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

// Start server only if not in test environment
if (process.env.NODE_ENV !== 'test') {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export default app;
