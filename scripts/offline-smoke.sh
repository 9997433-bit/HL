#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME_PATH="${CHROME_PATH:-/usr/local/bin/google-chrome}"

fail() {
  printf 'offline-smoke: %s\n' "$*" >&2
  exit 1
}

[[ -f "$ROOT_DIR/apps/literacy-app/dist/index.html" ]] ||
  fail "缺少识字 App 构建，请先运行 npm run build。"
[[ -f "$ROOT_DIR/apps/math-app/dist/index.html" ]] ||
  fail "缺少数学 App 构建，请先运行 npm run build。"
[[ -x "$CHROME_PATH" ]] || fail "找不到 Chrome: $CHROME_PATH"

cd "$ROOT_DIR"
CHROME_PATH="$CHROME_PATH" node --input-type=module - "$ROOT_DIR" <<'NODE'
import { createServer } from 'node:http'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { extname, join, resolve, sep } from 'node:path'
import puppeteer from 'puppeteer-core'

const ROOT = process.argv[2]
const CHROME = process.env.CHROME_PATH
const MIME = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
}

const assert = (condition, message) => {
  if (!condition) throw new Error(message)
}

const createStaticServer = (directory) =>
  createServer(async (request, response) => {
    const url = new URL(request.url, 'http://localhost')
    const relativePath =
      url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname).replace(/^\/+/, '')
    const file = resolve(directory, relativePath)

    if (!file.startsWith(`${resolve(directory)}${sep}`) || !existsSync(file)) {
      response.writeHead(404).end('not found')
      return
    }

    try {
      const body = await readFile(file)
      response.writeHead(200, {
        'cache-control': 'no-cache',
        'content-type': MIME[extname(file)] ?? 'application/octet-stream',
      })
      response.end(body)
    } catch {
      response.writeHead(500).end('read error')
    }
  })

async function listen(server) {
  await new Promise((resolveListen, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolveListen)
  })
}

async function stop(server) {
  await new Promise((resolveStop, reject) => {
    server.close((error) => (error ? reject(error) : resolveStop()))
    server.closeAllConnections?.()
  })
}

async function waitForWorker(page) {
  return page.evaluate(async () => {
    await navigator.serviceWorker.ready
    if (!navigator.serviceWorker.controller) {
      await new Promise((resolveController, reject) => {
        const timeout = setTimeout(
          () => reject(new Error('Service Worker 未接管页面')),
          15_000,
        )
        navigator.serviceWorker.addEventListener(
          'controllerchange',
          () => {
            clearTimeout(timeout)
            resolveController()
          },
          { once: true },
        )
      })
    }

    const names = await caches.keys()
    const precacheName = names.find((name) => name.includes('-app-precache-'))
    const cache = precacheName ? await caches.open(precacheName) : null
    const requests = cache ? await cache.keys() : []
    return {
      controlled: Boolean(navigator.serviceWorker.controller),
      precacheName,
      urls: requests.map((request) => request.url),
    }
  })
}

/**
 * 拍照识字的引擎包（worker + wasm 内核 + 语言包）不进预缓存，走的是 sw.js 里的
 * 按需缓存。第一次认字把它收下来，断网之后必须照样认得出——这条链路只有真的
 * 跑一遍 OCR 才验得了，所以这里认的是入库的那张示例照片。
 */
async function recognizeSample(page, baseUrl) {
  await page.goto(`${baseUrl}/#/ocr`, { waitUntil: 'networkidle0', timeout: 30_000 })
  await page.waitForSelector('.ocr[data-phase="idle"]', { timeout: 15_000 })
  await page.evaluate(() => {
    const start = [...document.querySelectorAll('button')].find((node) =>
      node.innerText.includes('试一张示例'),
    )
    if (!start) throw new Error('拍照识字页缺少「试一张示例」入口')
    start.click()
  })
  await page.waitForFunction(
    () => ['done', 'error'].includes(document.querySelector('.ocr')?.dataset.phase),
    { timeout: 120_000 },
  )
  return page.evaluate(() => ({
    phase: document.querySelector('.ocr')?.dataset.phase,
    chars: [...document.querySelectorAll('.ocr__hit')].map((node) => node.dataset.char),
  }))
}

async function verifyOfflineApp(browser, app) {
  const directory = join(ROOT, 'apps', app.directory, 'dist')
  const builtWorker = await readFile(join(directory, 'sw.js'), 'utf8')
  assert(!builtWorker.includes('__PRECACHE_'), `${app.label}: sw.js 未注入预缓存清单`)

  const server = createStaticServer(directory)
  let serverRunning = false
  let warmPage
  let offlinePage

  try {
    await listen(server)
    serverRunning = true
    const baseUrl = `http://127.0.0.1:${server.address().port}`

    warmPage = await browser.newPage()
    await warmPage.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })
    await warmPage.goto(`${baseUrl}/#/`, { waitUntil: 'networkidle0', timeout: 30_000 })
    const worker = await waitForWorker(warmPage)

    assert(worker.controlled, `${app.label}: 首次加载后未被 Service Worker 接管`)
    assert(worker.precacheName, `${app.label}: 未创建版本化预缓存`)
    assert(
      worker.urls.some((url) => /\/assets\/.+\.js$/.test(url)),
      `${app.label}: JS assets 未进入预缓存`,
    )
    assert(
      worker.urls.some((url) => url.endsWith('/index.html')),
      `${app.label}: index.html 未进入预缓存`,
    )

    if (app.hanzi) {
      const hanziFiles = worker.urls.filter((url) => url.includes('/hanzi-data/'))
      assert(hanziFiles.length > 100, `${app.label}: hanzi-data 预缓存不完整`)
      assert(
        worker.urls.some((url) => url.endsWith('/hanzi-data/index.json')),
        `${app.label}: hanzi-data/index.json 未进入预缓存`,
      )
    }

    if (app.ocr) {
      const warmOcr = await recognizeSample(warmPage, baseUrl)
      assert(warmOcr.phase === 'done', `${app.label}: 联网时示例照片就没认成`)
      const packed = await warmPage.evaluate(async () => {
        const cache = await caches.open('literacy-app-ocr-pack')
        return (await cache.keys()).map((request) => request.url)
      })
      assert(
        packed.length >= 3 && packed.some((url) => url.includes('chi_sim.traineddata')),
        `${app.label}: 认过一次字之后引擎包没有落进按需缓存（${packed.length} 项）`,
      )
      const precached = worker.urls.filter((url) => /\/ocr\/(?:worker|tesseract-core|chi_sim)/.test(url))
      assert(
        precached.length === 0,
        `${app.label}: 5.5 MB 的引擎包混进了预缓存（${precached.join('、')}）`,
      )
    }

    await warmPage.close()
    warmPage = null
    await stop(server)
    serverRunning = false

    // HTTP 服务已彻底关闭；新页面只能由已安装的 Service Worker 启动。
    offlinePage = await browser.newPage()
    await offlinePage.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })
    const failures = []
    offlinePage.on('requestfailed', (request) => {
      failures.push(`${request.url()}: ${request.failure()?.errorText ?? 'request failed'}`)
    })

    await offlinePage.goto(`${baseUrl}${app.route}`, {
      waitUntil: 'networkidle0',
      timeout: 30_000,
    })
    await offlinePage.waitForFunction(
      () => (document.querySelector('#app')?.innerText ?? '').replace(/\s+/g, '').length > 20,
      { timeout: 10_000 },
    )

    const rendered = await offlinePage.evaluate(() => ({
      children: document.querySelector('#app')?.children.length ?? 0,
      controlled: Boolean(navigator.serviceWorker.controller),
      textLength: (document.querySelector('#app')?.innerText ?? '').replace(/\s+/g, '').length,
    }))
    assert(rendered.controlled, `${app.label}: 断网启动页面未被 Service Worker 接管`)
    assert(rendered.children > 0 && rendered.textLength > 20, `${app.label}: 断网启动渲染失败`)
    assert(failures.length === 0, `${app.label}: 断网时仍有资源请求失败\n${failures.join('\n')}`)

    if (app.hanzi) {
      const hanzi = await offlinePage.evaluate(async () => {
        const [indexResponse, characterResponse] = await Promise.all([
          fetch('./hanzi-data/index.json'),
          fetch('./hanzi-data/u65e5.json'),
        ])
        const index = await indexResponse.json()
        const character = await characterResponse.json()
        return {
          characterOk: characterResponse.ok && Array.isArray(character.strokes),
          count: index.chars?.length ?? 0,
          indexOk: indexResponse.ok,
        }
      })
      assert(
        hanzi.indexOk && hanzi.characterOk && hanzi.count > 100,
        `${app.label}: 断网读取 hanzi-data 失败`,
      )
    }

    if (app.ocr) {
      const offlineOcr = await recognizeSample(offlinePage, baseUrl)
      assert(
        offlineOcr.phase === 'done' && offlineOcr.chars.length >= 3,
        `${app.label}: 断网后认不出示例照片（${offlineOcr.phase}，${offlineOcr.chars.join('') || '零个字'}）`,
      )
      assert(
        failures.length === 0,
        `${app.label}: 断网认字时仍有资源请求失败\n${failures.join('\n')}`,
      )
      console.log(`  · 断网拍照识字认出「${offlineOcr.chars.join('')}」`)
    }

    console.log(
      `✓ ${app.label}: 服务关闭后 ${app.route} 启动成功，预缓存 ${worker.urls.length} 项`,
    )
  } finally {
    if (warmPage) await warmPage.close().catch(() => {})
    if (offlinePage) await offlinePage.close().catch(() => {})
    if (serverRunning) await stop(server).catch(() => {})
  }
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
})

try {
  await verifyOfflineApp(browser, {
    directory: 'literacy-app',
    hanzi: true,
    label: '识字 App',
    ocr: true,
    route: `/#/learn/${encodeURIComponent('日')}`,
  })
  await verifyOfflineApp(browser, {
    directory: 'math-app',
    hanzi: false,
    label: '数学 App',
    route: '/#/sudoku',
  })
  console.log('offline-smoke: 双 App 断网启动验证通过。')
} finally {
  await browser.close()
}
NODE
