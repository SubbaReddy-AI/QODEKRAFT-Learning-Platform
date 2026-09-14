import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['qodekraft-icon-192.png', 'qodekraft-icon-512.png', 'qodekraft-logo.png'],
      manifest: {
        name: 'QODEKRAFT Learning Platform',
        short_name: 'QODEKRAFT',
        description: 'Private learning platform with protected learning content.',
        theme_color: '#061b2b',
        background_color: '#f5f8fc',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: '/qodekraft-icon-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable',
          },
          {
            src: '/qodekraft-icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: { '/api': { target: process.env.VITE_BACKEND_PROXY || 'https://qodekraft-learning-platform.onrender.com', changeOrigin: true } },
  },
})