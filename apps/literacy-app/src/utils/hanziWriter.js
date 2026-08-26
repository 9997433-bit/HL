/**
 * 按需从 CDN 加载 hanzi-writer（笔顺动画库）。
 *
 * 之所以走 CDN 而不是打进 bundle：笔顺数据是按字拆分的 JSON，
 * hanzi-writer 默认就从 jsdelivr 上按需取 `hanzi-writer-data/<字>.json`，
 * 本地打包只会把库塞进来、数据仍然要联网，收益不大。
 *
 * 离线时 load() 会 reject，调用方（HanziStrokeBox）会退化成静态字形展示。
 */

const CDN_SOURCES = [
  'https://cdn.jsdelivr.net/npm/hanzi-writer@3.5.0/dist/hanzi-writer.min.js',
  'https://unpkg.com/hanzi-writer@3.5.0/dist/hanzi-writer.min.js'
]

const SCRIPT_TIMEOUT = 8000

let loadPromise = null

function injectScript(src) {
  return new Promise((resolve, reject) => {
    const el = document.createElement('script')
    el.src = src
    el.async = true
    const timer = setTimeout(() => {
      el.remove()
      reject(new Error(`hanzi-writer 加载超时: ${src}`))
    }, SCRIPT_TIMEOUT)

    el.onload = () => {
      clearTimeout(timer)
      if (window.HanziWriter) resolve(window.HanziWriter)
      else reject(new Error('hanzi-writer 已加载但未挂载到 window'))
    }
    el.onerror = () => {
      clearTimeout(timer)
      el.remove()
      reject(new Error(`hanzi-writer 加载失败: ${src}`))
    }
    document.head.appendChild(el)
  })
}

export function loadHanziWriter() {
  if (window.HanziWriter) return Promise.resolve(window.HanziWriter)
  if (loadPromise) return loadPromise

  loadPromise = CDN_SOURCES.reduce(
    (chain, src) => chain.catch(() => injectScript(src)),
    Promise.reject(new Error('init'))
  ).catch((err) => {
    // 允许下次进入其它字时重试（可能只是暂时断网）
    loadPromise = null
    throw err
  })

  return loadPromise
}

export function isHanziWriterReady() {
  return Boolean(window.HanziWriter)
}
