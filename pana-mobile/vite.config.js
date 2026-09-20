import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

const app = (p) => fileURLToPath(new URL(`../pana-app/src/${p}`, import.meta.url))
const here = (p) => fileURLToPath(new URL(`./src/${p}`, import.meta.url))

/**
 * Modules of pana-app that this app replaces with its own.
 *
 * The two clients differ in exactly one respect: how credentials travel. A
 * browser holds httpOnly cookies and sends them automatically; a device holds
 * the token pair itself and sends a bearer header, and its auth endpoints are
 * the `/auth/mobile/*` group. Everything above that -- the services, the query
 * hooks, the cache keys -- is identical, and is imported from pana-app rather
 * than copied.
 *
 * Substituting these two modules is what lets that shared code run unchanged
 * on either client.
 */
const SUBSTITUTES = new Map([
  [app('lib/apiClient.js'), here('lib/apiClient.js')],
  [app('api/routes.js'), here('lib/routes.js')],
])

/**
 * Redirect the substituted modules.
 *
 * This has to be a plugin rather than a `resolve.alias` entry. An alias is
 * matched against the import specifier as written -- the literal
 * `'../lib/apiClient.js'` inside a pana-app service -- and an absolute path
 * never matches that string, so the alias silently does nothing and both the
 * web and the native client end up in the bundle. `resolveId` sees the
 * resolved absolute path, which is the thing actually worth matching on.
 */
function substituteTransport() {
  return {
    name: 'pana-substitute-transport',
    enforce: 'pre',
    async resolveId(source, importer, options) {
      // Let the default resolver do the work, then check what it landed on.
      const resolved = await this.resolve(source, importer, { ...options, skipSelf: true })
      if (!resolved) return null

      const substitute = SUBSTITUTES.get(resolved.id)
      return substitute ? { id: substitute } : null
    },
  }
}

// The mobile app is its own Vite project but shares pana-app's data layer: the
// services and query hooks are identical, and the design tokens must stay one
// file so the two clients cannot drift apart visually.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // The host the phone reaches this machine at, taken from the API origin so
  // there is one place that names it.
  const apiHost = (env.VITE_BASE_API_URL || '').replace(/^https?:\/\//, '').split(':')[0]

  return {
    plugins: [substituteTransport(), react()],
    resolve: {
      alias: {
        '@app': fileURLToPath(new URL('../pana-app/src', import.meta.url)),
      },
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
