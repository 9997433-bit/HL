/**
 * 汉字笔顺数据加载器。
 *
 * 优先读取 public/hanzi-data/ 下由 scripts/gen-hanzi-data.mjs 裁剪出来的离线数据；
 * 只有当某个字不在离线集合里时，才回退到 jsDelivr CDN。
 * 这样断网时核心字表依然能画出笔顺动画。
 */

const CDN = 'https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1'

/** char -> Promise<data|null>，避免同一个字被重复请求。 */
const cache = new Map()

/** 离线索引，首次用到时加载一次。 */
let indexPromise = null

function dataUrl(file) {
  // base 是 './'，用 baseURI 拼相对路径，子目录部署与 file:// 都能工作。
  return new URL(`hanzi-data/${file}`, document.baseURI).href
}

function loadIndex() {
  if (!indexPromise) {
    indexPromise = fetch(dataUrl('index.json'))
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => new Set(json?.chars ?? []))
      .catch(() => new Set())
  }
  return indexPromise
}

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

/**
 * 取一个字的笔顺数据。
 * @param {string} char 单个汉字
 * @returns {Promise<{strokes: string[], medians: number[][][]}|null>} 取不到时为 null
 */
export function loadCharData(char) {
  if (cache.has(char)) return cache.get(char)

  const task = (async () => {
    const local = await loadIndex()
    const codepoint = `u${char.codePointAt(0).toString(16)}`

    if (local.has(char)) {
      try {
        return await fetchJson(dataUrl(`${codepoint}.json`))
      } catch {
        /* 本地文件意外缺失，继续走 CDN */
      }
    }

    try {
      return await fetchJson(`${CDN}/${encodeURIComponent(char)}.json`)
    } catch {
      return null
    }
  })()

  cache.set(char, task)
  return task
}

/** 交给 hanzi-writer 的 charDataLoader，签名由库规定。 */
export function charDataLoader(char, onLoad, onError) {
  loadCharData(char).then((data) => {
    if (data) onLoad(data)
    else onError?.(new Error(`没有找到「${char}」的笔顺数据`))
  })
}

/** 该字是否有离线笔顺数据（用于提前隐藏「描红」入口）。 */
export async function hasStrokeData(char) {
  return (await loadCharData(char)) !== null
}
