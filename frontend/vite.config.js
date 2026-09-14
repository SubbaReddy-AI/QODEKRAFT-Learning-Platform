import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'QODEKRAFT Learning Platform',
        short_name: 'QODEKRAFT',
        description: 'Private learning platform with protected learning content.',
        theme_color: '#061b2b',
        background_color: '#f5f8fc',
        display: 'standalone',
        scope: '/',
        start_url: '/',
      },
    }),
  ],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: { '/api': { target: process.env.VITE_BACKEND_PROXY || 'http://localhost:8000', changeOrigin: true } },
  },
})
