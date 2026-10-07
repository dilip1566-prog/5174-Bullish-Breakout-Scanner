import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    // Bind every interface, not just the IPv6 loopback. Vite's default
    // ("localhost") resolves to ::1 here, so browsers that resolve localhost
    // to 127.0.0.1 -- Chrome on Windows, typically -- get connection refused.
    host: true,
  },
  preview: {
    port: 5174,
    strictPort: true,
  },
})
