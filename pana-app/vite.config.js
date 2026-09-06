import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env without the VITE_ prefix filter, so server-only settings stay out
  // of the client bundle.
  const env = loadEnv(mode, process.cwd(), '')

  const port = Number(env.VITE_PORT) || 5173

  // Host headers the dev server will answer to. Needed when the app is reached
  // through anything other than localhost (a tunnel, a LAN address, a container
  // name); Vite rejects unknown hosts otherwise.
  const allowedHosts = (env.VITE_ALLOWED_HOSTS || '')
    .split(',')
    .map((host) => host.trim())
    .filter(Boolean)

  return {
    plugins: [react()],
    server: {
      port,
      ...(allowedHosts.length > 0 && { allowedHosts }),
    },
  }
})
