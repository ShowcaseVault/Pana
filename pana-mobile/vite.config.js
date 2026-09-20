import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

const app = (p) => fileURLToPath(new URL(`../pana-app/src/${p}`, import.meta.url))
const here = (p) => fileURLToPath(new URL(`./src/${p}`, import.meta.url))
const dep = (p) => fileURLToPath(new URL(`./node_modules/${p}`, import.meta.url))

// Packages that must exist exactly once in the bundle.
//
// The shared code lives in pana-app, which has its own node_modules, so a bare
// import of `react` from a file under `@app` resolves there while the same
// import here resolves to this project's copy. Two copies of React means two
// sets of hooks; two copies of react-query means the provider is set on one
// and read from the other -- "No QueryClient set", on a screen that renders
// blank with the error only in the device log.
//
// Pinning them to this project's node_modules is what makes the shared modules
// genuinely shared rather than merely duplicated.
const SINGLETONS = [
  'react',
  'react-dom',
  'react/jsx-runtime',
  '@tanstack/react-query',
  'axios',
  'sonner',
  'lucide-react',
]

// The mobile app is its own Vite project but shares pana-app's data layer:
// the services and query hooks are identical, and the design tokens must stay
// one file so the two clients cannot drift apart visually.
//
// Those shared services import `../lib/apiClient.js` and `../api/routes.js`
// relative to pana-app, which would bind them to the cookie-based web client.
// Redirecting both specifiers here substitutes the native client -- bearer
// tokens, body-carried refresh -- without editing a line of pana-app. The
// substitutes keep the same public shape, so the services are none the wiser.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // The host the phone reaches this machine at, taken from the API origin so
  // there is one place that names it.
  const apiHost = (env.VITE_BASE_API_URL || '').replace(/^https?:\/\//, '').split(':')[0]

  return {
    plugins: [react()],
    resolve: {
      alias: [
        { find: '@app', replacement: fileURLToPath(new URL('../pana-app/src', import.meta.url)) },
        { find: app('lib/apiClient.js'), replacement: here('lib/apiClient.js') },
        { find: app('api/routes.js'), replacement: here('lib/routes.js') },
      ],
    },
    server: {
      host: true,
      port: Number(env.VITE_PORT) || 5175,

      // Live reload serves the bundle to the handset over the LAN, so the
      // requests arrive with an IP or a tunnel name in the Host header rather
      // than localhost. Vite refuses a host it does not know, and the failure
      // is a blank WebView with nothing on screen to explain it.
      //
      // The API's own host is always allowed, since that is the address the
      // phone is told to use; anything else -- a tunnel, a second interface --
      // is listed in VITE_ALLOWED_HOSTS, comma separated.
      allowedHosts: [
        ...(apiHost ? [apiHost] : []),
        ...(env.VITE_ALLOWED_HOSTS || '')
          .split(',')
          .map((host) => host.trim())
          .filter(Boolean),
      ],
    },
  }
})
