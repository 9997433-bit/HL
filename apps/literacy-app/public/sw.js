const CACHE_PREFIX = 'literacy-app-precache-'
const CACHE_NAME = `${CACHE_PREFIX}__PRECACHE_VERSION__`
const PRECACHE_URLS = [
  './',
  /* __PRECACHE_MANIFEST__ */
]

/**
 * 拍照识字的引擎包（worker + wasm 内核 + chi_sim 语言包）不进预缓存：
 * 近 6 MB，多数访客根本不会打开这一页。改成第一次用到时才下，
 * 下完就留在这个缓存里，之后断网照样能认字。
 * 名字不带版本号，也不以 CACHE_PREFIX 开头，换版本时不会被 activate 清掉。
 */
const OCR_CACHE = 'literacy-app-ocr-pack'

const scopeUrl = new URL(self.registration.scope)
const indexUrl = new URL('./index.html', scopeUrl).href
const ocrPrefix = new URL('./ocr/', scopeUrl).pathname
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

  if (url.pathname.startsWith(ocrPrefix)) {
    event.respondWith(cacheOnFirstUse(request))
    return
  }

  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then((cached) => cached ?? fetch(request)),
  )
})

async function cacheOnFirstUse(request) {
  // 先查全部缓存：清单和示例图体积小，还是走预缓存的，别让它们白跑一趟网络
  const cached = await caches.match(request, { ignoreSearch: true })
  if (cached) return cached

  const response = await fetch(request)
  // 只收成功的整份响应：把 404 或半截的 range 响应存下来，离线时会一直坏下去
  if (response.ok && response.status === 200) {
    const cache = await caches.open(OCR_CACHE)
    await cache.put(request, response.clone())
  }
  return response
}
