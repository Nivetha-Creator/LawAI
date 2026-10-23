import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy API routes to FastAPI on the same machine. Browser requests stay
// same-origin (works with Cursor Cloud Agent port forwarding).
const apiProxy = {
  '/chat': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/debate': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/conversations': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/health': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/strategy': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // Cloud Agent forwarded hostnames change per pod; allow them all.
    allowedHosts: true,
    proxy: apiProxy,
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: apiProxy,
  },
})
