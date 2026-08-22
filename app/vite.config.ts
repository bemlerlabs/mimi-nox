import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    // Dev-Proxy: API + WS vom Vite-Port (same-origin) zum Backend (8765).
    // Damit läuft die PWA in Dev ohne hartkodierte API-URL (wie in Prod,
    // wo der Server die PWA selbst serviert). VITE_API_URL/VITE_WS_URL
    // überschreiben weiterhin für externe Setups.
    proxy: {
      '/api': {
        target: process.env.MIMI_API_TARGET || 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.MIMI_API_TARGET || 'http://127.0.0.1:8765',
        ws: true,
        changeOrigin: true,
      },
      '/audio': 'http://127.0.0.1:8765',
      '/images': 'http://127.0.0.1:8765',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // Route bundles are already split via React.lazy; split heavy vendors.
          if (id.includes('node_modules')) {
            // Markdown ecosystem: self-contained so the lazy markdown route
            // doesn't pull unrelated vendor code into the initial load.
            if (id.includes('react-markdown') || id.includes('remark-gfm') || id.includes('marked') || id.includes('dompurify') || id.includes('unified') || id.includes('micromark') || id.includes('remark') || id.includes('rehype') || id.includes('mdast') || id.includes('hast') || id.includes('vfile') || id.includes('decode-named') || id.includes('highlight') || id.includes('lowlight')) {
              return 'markdown'
            }
            if (id.includes('framer-motion')) {
              return 'motion'
            }
            if (id.includes('lucide-react') || id.includes('react-i18next') || id.includes('i18next')) {
              return 'ui-vendor'
            }
            // React 19 runtime (react/react-dom/scheduler) re-exports shared internals
            // across packages — it MUST stay together in the main chunk. Splitting it
            // into its own chunk creates a circular chunk (react-core <-> vendor).
            // Split only the genuinely independent UI/state libs instead.
            if (id.includes('react-router') || id.includes('@tanstack') || id.includes('zustand') || id.includes('idb-keyval') || id.includes('clsx') || id.includes('class-variance-authority')) {
              return 'app-vendor'
            }
          }
        },
      },
    },
  },
})
