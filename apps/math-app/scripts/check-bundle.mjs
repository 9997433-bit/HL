/**
 * 数学 App 首屏 JavaScript 预算门禁。
 *
 * 从 dist/index.html 的 module 入口出发，只跟随静态 import/export；路由级
 * import() 块不计入首屏。每个实际 HTTP 资源分别 gzip 后合计，必须小于 250 KiB。
 *
 * 用法：npm run build && npm run check:bundle
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const here = path.dirname(fileURLToPath(import.meta.url))
const dist = path.resolve(here, '..', 'dist')
const budgetBytes = 250 * 1024

const fail = (message) => {
  console.error(`✗ ${message}`)
  process.exit(1)
}

if (!fs.existsSync(path.join(dist, 'index.html'))) {
  fail('缺少 dist/index.html；请先运行 npm run build。')
}

const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8')
const entrySources = [
  ...html.matchAll(/<script\b[^>]*\btype=["']module["'][^>]*\bsrc=["']([^"']+\.m?js)["'][^>]*>/gi),
  ...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+\.m?js)["'][^>]*\btype=["']module["'][^>]*>/gi),
].map((match) => match[1])

if (entrySources.length === 0) fail('index.html 里找不到 module 入口脚本。')

const toDistPath = (source, importer = 'index.html') => {
  const base = new URL(importer, 'http://bundle.local/')
  const pathname = decodeURIComponent(new URL(source, base).pathname).replace(/^\/+/, '')
  const absolute = path.resolve(dist, pathname)
  if (absolute !== dist && !absolute.startsWith(`${dist}${path.sep}`)) {
    fail(`入口依赖越出 dist：${source}`)
  }
  return path.relative(dist, absolute).split(path.sep).join('/')
}

const queue = [...new Set(entrySources.map((source) => toDistPath(source)))]
const initialFiles = new Set()
while (queue.length > 0) {
  const file = queue.shift()
  if (initialFiles.has(file)) continue

  const absolute = path.join(dist, file)
  if (!fs.existsSync(absolute)) fail(`首屏依赖不存在：${file}`)
  initialFiles.add(file)

  const code = fs.readFileSync(absolute, 'utf8')
  const staticImports =
    /(?:^|[;\n])\s*(?:import(?!\s*\()|export)\s*(?:[^"'`;]*?\sfrom\s*)?["']([^"']+\.m?js)["']/g
  for (const match of code.matchAll(staticImports)) {
    const dependency = toDistPath(match[1], `http://bundle.local/${file}`)
    if (!initialFiles.has(dependency)) queue.push(dependency)
  }
}

let totalRaw = 0
let totalGzip = 0
for (const file of [...initialFiles].sort()) {
  const bytes = fs.readFileSync(path.join(dist, file))
  const gzipBytes = gzipSync(bytes, { level: 9 }).byteLength
  totalRaw += bytes.byteLength
  totalGzip += gzipBytes
  console.log(`  ${file}: ${bytes.byteLength} B raw / ${gzipBytes} B gzip`)
}

console.log(
  `\n数学首屏 JS：${initialFiles.size} 个同步资源，` +
    `${totalRaw} B raw / ${totalGzip} B gzip（预算 < ${budgetBytes} B / 250 KiB）`
)
if (totalGzip >= budgetBytes) {
  fail(`首屏 JS gzip ${totalGzip} B 超出 250 KiB 预算。`)
}
console.log('✓ 数学首屏 JS gzip 预算通过。')
