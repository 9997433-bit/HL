#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAX_BUILD_SECONDS="${ACCEPTANCE_MAX_BUILD_SECONDS:-60}"
MAX_INITIAL_JS_GZIP_BYTES="${ACCEPTANCE_MAX_INITIAL_JS_GZIP_BYTES:-256000}"
MIN_LH_PERFORMANCE="${ACCEPTANCE_MIN_LH_PERFORMANCE:-0.90}"
MIN_LH_ACCESSIBILITY="${ACCEPTANCE_MIN_LH_ACCESSIBILITY:-0.90}"
MIN_LH_BEST_PRACTICES="${ACCEPTANCE_MIN_LH_BEST_PRACTICES:-0.90}"
PORT_BASE="${ACCEPTANCE_PORT_BASE:-43170}"
FAILED=0
TMP_DIR=""
SERVER_PID=""

fail() {
  printf 'acceptance: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  [[ -z "$TMP_DIR" ]] || rm -rf "$TMP_DIR"
}
trap cleanup EXIT

for command_name in node npm; do
  command -v "$command_name" >/dev/null 2>&1 ||
    fail "未找到 ${command_name}，请先运行 scripts/setup.sh。"
done

[[ "$MAX_BUILD_SECONDS" =~ ^[1-9][0-9]*$ ]] ||
  fail "ACCEPTANCE_MAX_BUILD_SECONDS 必须是正整数。"
[[ "$MAX_INITIAL_JS_GZIP_BYTES" =~ ^[1-9][0-9]*$ ]] ||
  fail "ACCEPTANCE_MAX_INITIAL_JS_GZIP_BYTES 必须是正整数。"

find_chrome() {
  local candidate
  if [[ -n "${CHROME_PATH:-}" && -x "$CHROME_PATH" ]]; then
    printf '%s\n' "$CHROME_PATH"
    return 0
  fi

  for candidate in \
    /usr/local/bin/google-chrome \
    /usr/bin/google-chrome \
    /usr/bin/google-chrome-stable \
    /usr/bin/chromium \
    /usr/bin/chromium-browser; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

find_lighthouse() {
  if [[ -n "${LIGHTHOUSE_BIN:-}" ]]; then
    if [[ -x "$LIGHTHOUSE_BIN" ]]; then
      printf '%s\n' "$LIGHTHOUSE_BIN"
      return 0
    fi
    command -v "$LIGHTHOUSE_BIN" 2>/dev/null && return 0
    return 1
  fi

  if command -v lighthouse >/dev/null 2>&1; then
    command -v lighthouse
    return 0
  fi
  if [[ -x "$ROOT_DIR/node_modules/.bin/lighthouse" ]]; then
    printf '%s\n' "$ROOT_DIR/node_modules/.bin/lighthouse"
    return 0
  fi
  return 1
}

now_ms() {
  node -e 'process.stdout.write(String(Date.now()))'
}

run_build() {
  local label="$1"
  local app_dir="$2"
  local started finished elapsed_ms elapsed_seconds

  printf '\n[%s] 构建（阈值 %ss）...\n' "$label" "$MAX_BUILD_SECONDS"
  started="$(now_ms)"
  if ! npm --prefix "$app_dir" run build; then
    printf '[%s] FAIL 构建命令失败。\n' "$label" >&2
    FAILED=1
    return
  fi
  finished="$(now_ms)"
  elapsed_ms=$((finished - started))
  elapsed_seconds=$(((elapsed_ms + 999) / 1000))
  printf '[%s] 构建耗时: %dms\n' "$label" "$elapsed_ms"

  if (( elapsed_seconds > MAX_BUILD_SECONDS )); then
    printf '[%s] FAIL 构建耗时 %ss，超过 %ss 阈值。\n' \
      "$label" "$elapsed_seconds" "$MAX_BUILD_SECONDS" >&2
    FAILED=1
  else
    printf '[%s] PASS 构建时间阈值。\n' "$label"
  fi
}

check_bundle() {
  local label="$1"
  local dist_dir="$2"

  if [[ ! -f "$dist_dir/index.html" ]]; then
    printf '[%s] FAIL 缺少 dist/index.html，无法检查包体积。\n' "$label" >&2
    FAILED=1
    return
  fi

  printf '[%s] 首屏 JS gzip 阈值: < %s bytes\n' "$label" "$MAX_INITIAL_JS_GZIP_BYTES"
  if ! node --input-type=module - "$label" "$dist_dir" "$MAX_INITIAL_JS_GZIP_BYTES" <<'NODE'
import { readFile } from 'node:fs/promises'
import { resolve, sep } from 'node:path'
import { gzipSync } from 'node:zlib'

const [, , label, distArg, maxArg] = process.argv
const dist = resolve(distArg)
const max = Number(maxArg)
const html = await readFile(resolve(dist, 'index.html'), 'utf8')
const sources = [...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)]
  .map((match) => match[1])
  .filter((source) => /\.m?js(?:[?#]|$)/i.test(source))

if (sources.length === 0) {
  console.error(`[${label}] FAIL index.html 没有首屏 JavaScript 入口。`)
  process.exit(1)
}

let totalRaw = 0
let totalGzip = 0
for (const source of new Set(sources)) {
  const pathname = decodeURIComponent(new URL(source, 'http://local/').pathname).replace(/^\/+/, '')
  const file = resolve(dist, pathname)
  if (file !== dist && !file.startsWith(`${dist}${sep}`)) {
    throw new Error(`入口路径越出 dist: ${source}`)
  }
  const bytes = await readFile(file)
  const gzipBytes = gzipSync(bytes, { level: 9 }).byteLength
  totalRaw += bytes.byteLength
  totalGzip += gzipBytes
  console.log(`[${label}]   ${source}: ${bytes.byteLength} bytes raw / ${gzipBytes} bytes gzip`)
}

console.log(`[${label}] 首屏 JS 合计: ${totalRaw} bytes raw / ${totalGzip} bytes gzip`)
if (totalGzip >= max) {
  console.error(`[${label}] FAIL 首屏 JS gzip ${totalGzip} bytes，不满足 < ${max} bytes。`)
  process.exit(1)
}
console.log(`[${label}] PASS 首屏 JS gzip 阈值。`)
NODE
  then
    FAILED=1
  fi
}

start_static_server() {
  local dist_dir="$1"
  local port="$2"
  local log_file="$3"

  node --input-type=module - "$dist_dir" "$port" >"$log_file" 2>&1 <<'NODE' &
import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, resolve, sep } from 'node:path'
import { gzipSync } from 'node:zlib'

const [, , distArg, portArg] = process.argv
const dist = resolve(distArg)
const mime = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
}
const compressible = new Set(['.css', '.html', '.js', '.json', '.svg'])

const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://local/').pathname)
    const relative = pathname.replace(/^\/+/, '')
    let file = resolve(dist, relative || 'index.html')
    if (file !== dist && !file.startsWith(`${dist}${sep}`)) file = resolve(dist, 'index.html')
    if (!(await stat(file).catch(() => null))?.isFile()) file = resolve(dist, 'index.html')
    const extension = extname(file)
    const body = await readFile(file)
    const headers = {
      'content-type': mime[extension] ?? 'application/octet-stream',
      'vary': 'Accept-Encoding',
    }
    const acceptsGzip = /\bgzip\b/i.test(request.headers['accept-encoding'] ?? '')
    const responseBody = acceptsGzip && compressible.has(extension) ? gzipSync(body, { level: 9 }) : body
    if (responseBody !== body) headers['content-encoding'] = 'gzip'
    headers['content-length'] = String(responseBody.byteLength)
    response.writeHead(200, headers)
    response.end(responseBody)
  } catch (error) {
    response.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' })
    response.end(String(error))
  }
})

server.listen(Number(portArg), '127.0.0.1', () => console.log('ready'))
NODE
  SERVER_PID=$!

  if ! node --input-type=module - "$port" <<'NODE'
const port = process.argv[2]
for (let attempt = 0; attempt < 40; attempt += 1) {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/`)
    if (response.ok) process.exit(0)
  } catch {}
  await new Promise((resolve) => setTimeout(resolve, 100))
}
process.exit(1)
NODE
  then
    printf 'acceptance: 静态服务器启动失败，日志位于 %s\n' "$log_file" >&2
    return 1
  fi
}

run_lighthouse() {
  local label="$1"
  local dist_dir="$2"
  local port="$3"
  local lighthouse_bin="$4"
  local chrome_path="$5"
  local slug report_path server_log

  slug="$(printf '%s' "$label" | tr '[:upper:] ' '[:lower:]-')"
  report_path="$TMP_DIR/lighthouse-${slug}.json"
  server_log="$TMP_DIR/server-${slug}.log"
  printf '\n[%s] Lighthouse（Performance/Accessibility/Best Practices）...\n' "$label"

  if ! start_static_server "$dist_dir" "$port" "$server_log"; then
    FAILED=1
    return
  fi

  if ! CHROME_PATH="$chrome_path" "$lighthouse_bin" "http://127.0.0.1:${port}/" \
    --quiet \
    --output=json \
    --output-path="$report_path" \
    --only-categories=performance,accessibility,best-practices \
    --form-factor=mobile \
    --throttling-method=simulate \
    --chrome-flags="--headless=new --no-sandbox --disable-dev-shm-usage --mute-audio"; then
    printf '[%s] FAIL Lighthouse 执行失败。\n' "$label" >&2
    FAILED=1
  elif ! node --input-type=module - \
    "$label" "$report_path" \
    "$MIN_LH_PERFORMANCE" "$MIN_LH_ACCESSIBILITY" "$MIN_LH_BEST_PRACTICES" <<'NODE'
import { readFile } from 'node:fs/promises'

const [, , label, reportPath, performanceMin, accessibilityMin, bestPracticesMin] = process.argv
const report = JSON.parse(await readFile(reportPath, 'utf8'))
const checks = [
  ['Performance', 'performance', Number(performanceMin)],
  ['Accessibility', 'accessibility', Number(accessibilityMin)],
  ['Best Practices', 'best-practices', Number(bestPracticesMin)],
]
let failed = false

for (const [name, key, minimum] of checks) {
  const score = report.categories?.[key]?.score
  if (typeof score !== 'number') {
    console.error(`[${label}] FAIL Lighthouse 缺少 ${name} 分数。`)
    failed = true
    continue
  }
  const status = score >= minimum ? 'PASS' : 'FAIL'
  console.log(`[${label}] ${status} ${name}: ${Math.round(score * 100)}（阈值 ${Math.round(minimum * 100)}）`)
  if (score < minimum) failed = true
}
process.exit(failed ? 1 : 0)
NODE
  then
    FAILED=1
  fi

  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
}

run_build "识字 App" "$ROOT_DIR/apps/literacy-app"
run_build "数学 App" "$ROOT_DIR/apps/math-app"
check_bundle "识字 App" "$ROOT_DIR/apps/literacy-app/dist"
check_bundle "数学 App" "$ROOT_DIR/apps/math-app/dist"

TMP_DIR="$(mktemp -d)"
if LIGHTHOUSE_EXECUTABLE="$(find_lighthouse)" && CHROME_EXECUTABLE="$(find_chrome)"; then
  printf '\n检测到 Lighthouse: %s\n' "$LIGHTHOUSE_EXECUTABLE"
  run_lighthouse \
    "literacy-app" "$ROOT_DIR/apps/literacy-app/dist" "$((PORT_BASE + 1))" \
    "$LIGHTHOUSE_EXECUTABLE" "$CHROME_EXECUTABLE"
  run_lighthouse \
    "math-app" "$ROOT_DIR/apps/math-app/dist" "$((PORT_BASE + 2))" \
    "$LIGHTHOUSE_EXECUTABLE" "$CHROME_EXECUTABLE"
else
  printf '\n[SKIP] 未同时检测到 Lighthouse CLI 与 Chrome；跳过 Lighthouse，其他门槛继续执行。\n'
fi

printf '\n运行 axe-core 双 App 扫描（critical 必须为 0）...\n'
if ! node "$ROOT_DIR/scripts/axe-check.mjs"; then
  FAILED=1
fi

# 上面扫的是「每条路由刚打开、默认主题」。描红、答题反馈、庆祝浮层要操作几步
# 才出现，护眼与夜间又是另一整套颜色，这一轮把它们全铺开，serious 也必须为 0。
printf '\n运行识字 App 状态级 axe 扫描（三套主题 × 交互态，critical/serious 必须为 0）...\n'
if ! node "$ROOT_DIR/scripts/axe-states.mjs"; then
  FAILED=1
fi

if (( FAILED != 0 )); then
  printf '\n验收失败：至少一个自动化门槛未通过。\n' >&2
  exit 1
fi
printf '\n验收通过：所有已执行的自动化门槛均通过。\n'
