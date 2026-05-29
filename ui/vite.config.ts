import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/auth': 'http://localhost:8085',
      '/alerts': 'http://localhost:8085',
      '/targets': 'http://localhost:8085',
      '/domains': 'http://localhost:8085',
      '/users': 'http://localhost:8085',
      '/health': 'http://localhost:8085',
      '/metrics': 'http://localhost:8085',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})
