import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    // FIX: Replaced process.cwd() with '.' to avoid errors when Node.js types are not available.
    const env = loadEnv(mode, '.', '');
    return {
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.API_KEY),
      },
      resolve: {
        alias: {
          // FIX: Replaced __dirname with a relative path resolve to avoid errors when Node.js types are not available.
          '@': path.resolve('./src'),
        }
      }
    };
});