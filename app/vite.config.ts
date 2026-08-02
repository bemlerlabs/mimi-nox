import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
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
            if (id.includes('react-markdown') || id.includes('remark-gfm') || id.includes('marked') || id.includes('dompurify')) {
              return 'markdown'
            }
            if (id.includes('framer-motion')) {
              return 'motion'
            }
            if (id.includes('lucide-react') || id.includes('react-i18next') || id.includes('i18next')) {
              return 'ui-vendor'
            }
            // React core is unavoidable on the initial load; split it from the rest
            // so secondary libs (router, state, idb, clsx, cva) live in a separate chunk
            // that can be fetched once and cached.
            if (id.includes('/react/') || id.includes('/react-dom/') || id.includes('/scheduler/')) {
              return 'react-core'
            }
            return 'vendor'
          }
        },
      },
    },
  },
})
