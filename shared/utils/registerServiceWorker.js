const STARTUP_GRACE_MS = 8_000
const IDLE_TIMEOUT_MS = 4_000

/**
 * Keep first paint and route hydration ahead of the large offline precache.
 * Existing workers still serve immediately; only installation/update work is
 * deferred until the page has been stable for a few seconds.
 */
export function registerServiceWorkerAfterStartup(basePath) {
  if (!('serviceWorker' in navigator)) return

  const register = () => {
    const baseUrl = new URL(basePath, document.baseURI)
    navigator.serviceWorker
      .register(new URL('sw.js', baseUrl), { scope: baseUrl.href })
      .catch((error) => console.warn('[offline] Service Worker 注册失败：', error))
  }

  const afterGracePeriod = () => {
    window.setTimeout(() => {
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(register, { timeout: IDLE_TIMEOUT_MS })
      } else {
        register()
      }
    }, STARTUP_GRACE_MS)
  }

  if (document.readyState === 'complete') {
    afterGracePeriod()
  } else {
    window.addEventListener('load', afterGracePeriod, { once: true })
  }
}
