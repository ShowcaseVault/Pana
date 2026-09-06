import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // 5174 by default, so the landing page and the app can run side by side.
  const port = Number(env.VITE_PORT) || 5174

  // Host headers the dev server will answer to. Needed when the page is reached
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
