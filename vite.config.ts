import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.API_KEY),
      },
      resolve: {
        alias: {
          '@': path.resolve('./src'),
        }
      },
      build: {
        rollupOptions: {
          output: {
            manualChunks: {
              // Split vendor libraries
              'react-vendor': ['react', 'react-dom'],
              'ui-vendor': ['framer-motion', 'lucide-react'],
              'editor-vendor': ['@monaco-editor/react'],
              'markdown-vendor': ['react-markdown', 'react-syntax-highlighter'],
              'utils-vendor': ['date-fns', 'zustand'],
            }
          }
        },
        chunkSizeWarningLimit: 1000,
      }
    };
});
