const CACHE_PREFIX = 'math-app-precache-'
const CACHE_NAME = `${CACHE_PREFIX}__PRECACHE_VERSION__`
const PRECACHE_URLS = [
  './',
  /* __PRECACHE_MANIFEST__ */
]

const scopeUrl = new URL(self.registration.scope)
const indexUrl = new URL('./index.html', scopeUrl).href
const precacheRequests = PRECACHE_URLS.map(
  (path) => new Request(new URL(path, scopeUrl), { cache: 'reload' }),
)

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(precacheRequests))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
            .map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== scopeUrl.origin) return

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const cache = await caches.open(CACHE_NAME)
        return (await cache.match(request, { ignoreSearch: true })) ?? cache.match(indexUrl)
      }),
    )
    return
  }

  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then((cached) => cached ?? fetch(request)),
  )
})
