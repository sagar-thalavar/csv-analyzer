import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/pdf': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/upload': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/upload_csv': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/clean': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/clean_data': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/summary': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/chart': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/filter': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/download': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/download_cleaned': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/preview': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
    },
  },
});
