import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // When `VITE_API_URL` is unset, the app uses relative paths (e.g. `/status`).
      // Proxy those API calls to the Flask bridge during `npm run dev`.
      '^/(status|logs|validate|server|librarian|nexus|export|injector|forge|system|project|mcp)(/|$)': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
    },
  },
})
