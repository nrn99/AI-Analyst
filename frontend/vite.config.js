import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': 'http://localhost:8080',
      '/chat': 'http://localhost:8080',
      '/categories': 'http://localhost:8080',
      '/audit': 'http://localhost:8080',
      '/ingest': 'http://localhost:8080',
    }
  }
})
