#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hongen-benchmark.XXXXXX")"
BUILD_ROWS="$TMP_DIR/build.tsv"
LIGHTHOUSE_ROWS="$TMP_DIR/lighthouse.tsv"
PREVIEW_PID=""

cleanup() {
  if [[ -n "$PREVIEW_PID" ]]; then
    kill "$PREVIEW_PID" >/dev/null 2>&1 || true
    wait "$PREVIEW_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

fail() {
  printf 'benchmark: %s\n' "$*" >&2
  exit 1
}

command -v node >/dev/null 2>&1 || fail "未找到 Node.js。"
command -v npm >/dev/null 2>&1 || fail "未找到 npm。"

date_ms() {
  node -e 'process.stdout.write(String(Date.now()))'
}

format_bytes() {
  node -e '
    const bytes = Number(process.argv[1]);
    const units = ["B", "KiB", "MiB", "GiB"];
    let value = bytes;
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
      value /= 1024;
      index += 1;
    }
    process.stdout.write(`${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`);
  ' "$1"
}

measure_bundle() {
  node - "$1" <<'NODE'
const fs = require("node:fs")
const path = require("node:path")
const zlib = require("node:zlib")

const root = process.argv[2]
let rawBytes = 0
let gzipBytes = 0
let fileCount = 0
const compressible = /\.(?:css|html|js|json|svg|txt|xml)$/i

const visit = (directory) => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filepath = path.join(directory, entry.name)
    if (entry.isDirectory()) visit(filepath)
    if (!entry.isFile()) continue
    const content = fs.readFileSync(filepath)
    rawBytes += content.byteLength
    gzipBytes += compressible.test(entry.name)
      ? zlib.gzipSync(content, { level: 9 }).byteLength
      : content.byteLength
    fileCount += 1
  }
}

visit(root)
process.stdout.write(`${rawBytes}\t${gzipBytes}\t${fileCount}`)
NODE
}

build_app() {
  local label="$1"
  local app_dir="$2"
  local started_at finished_at duration raw_bytes gzip_bytes file_count

  [[ -f "$app_dir/package.json" ]] || fail "${label}缺少 package.json。"
  printf '\n[%s] 构建计时...\n' "$label"
  started_at="$(date_ms)"
  if [[ "${BENCHMARK_SKIP_BUILD:-0}" != "1" ]]; then
    if ! npm --prefix "$app_dir" run build; then
      finished_at="$(date_ms)"
      duration=$((finished_at - started_at))
      printf '%s\tFAIL\t%s\t-\t-\t-\n' "$label" "$duration" >>"$BUILD_ROWS"
      printf '[%s] 构建失败（%s ms），继续测量其他应用。\n' "$label" "$duration" >&2
      return 1
    fi
  fi
  finished_at="$(date_ms)"
  duration=$((finished_at - started_at))

  if [[ ! -f "$app_dir/dist/index.html" ]]; then
    printf '%s\tFAIL\t%s\t-\t-\t-\n' "$label" "$duration" >>"$BUILD_ROWS"
    printf '[%s] 未生成 dist/index.html，继续测量其他应用。\n' "$label" >&2
    return 1
  fi
  IFS=$'\t' read -r raw_bytes gzip_bytes file_count < <(measure_bundle "$app_dir/dist")
  printf '%s\tOK\t%s\t%s\t%s\t%s\n' \
    "$label" "$duration" "$raw_bytes" "$gzip_bytes" "$file_count" >>"$BUILD_ROWS"
  printf '[%s] %s ms，原始 %s，gzip 估算 %s（%s 个文件）\n' \
    "$label" "$duration" "$(format_bytes "$raw_bytes")" \
    "$(format_bytes "$gzip_bytes")" "$file_count"
}

find_lighthouse() {
  if [[ -n "${LIGHTHOUSE_BIN:-}" && -x "${LIGHTHOUSE_BIN}" ]]; then
    printf '%s' "$LIGHTHOUSE_BIN"
  elif [[ -x "$ROOT_DIR/node_modules/.bin/lighthouse" ]]; then
    printf '%s' "$ROOT_DIR/node_modules/.bin/lighthouse"
  elif command -v lighthouse >/dev/null 2>&1; then
    command -v lighthouse
  fi
  return 0
}

find_vite() {
  local app_dir="$1"
  if [[ -x "$app_dir/node_modules/.bin/vite" ]]; then
    printf '%s' "$app_dir/node_modules/.bin/vite"
  elif [[ -x "$ROOT_DIR/node_modules/.bin/vite" ]]; then
    printf '%s' "$ROOT_DIR/node_modules/.bin/vite"
  fi
  return 0
}

wait_for_url() {
  local url="$1"
  local attempt
  for attempt in {1..40}; do
    if node -e '
      fetch(process.argv[1])
        .then((response) => process.exit(response.ok ? 0 : 1))
        .catch(() => process.exit(1))
    ' "$url"; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

lighthouse_app() {
  local label="$1"
  local app_dir="$2"
  local port="$3"
  local lighthouse_bin="$4"
  local vite_bin url report metrics performance lcp tbt cls

  vite_bin="$(find_vite "$app_dir")"
  if [[ -z "$vite_bin" ]]; then
    printf '%s\tSKIP\t-\t-\t-\tVite executable missing\n' "$label" >>"$LIGHTHOUSE_ROWS"
    return
  fi

  url="http://127.0.0.1:${port}"
  "$vite_bin" preview --host 127.0.0.1 --port "$port" --strictPort \
    >"$TMP_DIR/preview-${port}.log" 2>&1 &
  PREVIEW_PID=$!

  if ! wait_for_url "$url"; then
    printf '%s\tFAIL\t-\t-\t-\tPreview failed to start\n' "$label" >>"$LIGHTHOUSE_ROWS"
    kill "$PREVIEW_PID" >/dev/null 2>&1 || true
    wait "$PREVIEW_PID" >/dev/null 2>&1 || true
    PREVIEW_PID=""
    return
  fi

  report="$TMP_DIR/lighthouse-${port}.json"
  printf '[%s] 运行 Lighthouse 探针...\n' "$label"
  if "$lighthouse_bin" "$url" \
    --output=json \
    --output-path="$report" \
    --only-categories=performance \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --quiet; then
    metrics="$(
      node - "$report" <<'NODE'
const report = require(process.argv[2])
const audit = (id) => report.audits?.[id]?.numericValue
const value = (input, digits = 0) =>
  Number.isFinite(input) ? Number(input).toFixed(digits) : "-"
const score = report.categories?.performance?.score
process.stdout.write([
  Number.isFinite(score) ? Math.round(score * 100) : "-",
  value(audit("largest-contentful-paint")),
  value(audit("total-blocking-time")),
  value(audit("cumulative-layout-shift"), 3),
].join("\t"))
NODE
    )"
    IFS=$'\t' read -r performance lcp tbt cls <<<"$metrics"
    printf '%s\t%s\t%s\t%s\t%s\tOK\n' \
      "$label" "$performance" "$lcp" "$tbt" "$cls" >>"$LIGHTHOUSE_ROWS"
  else
    printf '%s\tFAIL\t-\t-\t-\tLighthouse command failed\n' "$label" >>"$LIGHTHOUSE_ROWS"
  fi

  kill "$PREVIEW_PID" >/dev/null 2>&1 || true
  wait "$PREVIEW_PID" >/dev/null 2>&1 || true
  PREVIEW_PID=""
}

write_report() {
  local output="$1"
  {
    printf '# 性能基准探针\n\n'
    printf -- '- 记录时间（UTC）：`%s`\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf -- '- Node.js：`%s`\n' "$(node --version)"
    printf -- '- npm：`%s`\n\n' "$(npm --version)"
    printf '## 构建与包体积\n\n'
    printf '| 应用 | 状态 | 构建时间 | 原始体积 | gzip 估算 | 文件数 |\n'
    printf '| --- | --- | ---: | ---: | ---: | ---: |\n'
    while IFS=$'\t' read -r label status duration raw_bytes gzip_bytes file_count; do
      if [[ "$status" == "OK" ]]; then
        raw_bytes="$(format_bytes "$raw_bytes")"
        gzip_bytes="$(format_bytes "$gzip_bytes")"
      fi
      printf '| %s | %s | %s ms | %s | %s | %s |\n' \
        "$label" "$status" "$duration" "$raw_bytes" "$gzip_bytes" "$file_count"
    done <"$BUILD_ROWS"

    printf '\n## Lighthouse\n\n'
    printf '| 应用 | Performance | LCP (ms) | TBT (ms) | CLS | 状态 |\n'
    printf '| --- | ---: | ---: | ---: | ---: | --- |\n'
    while IFS=$'\t' read -r label performance lcp tbt cls status; do
      printf '| %s | %s | %s | %s | %s | %s |\n' \
        "$label" "$performance" "$lcp" "$tbt" "$cls" "$status"
    done <"$LIGHTHOUSE_ROWS"
  } >"$output"
}

: >"$BUILD_ROWS"
: >"$LIGHTHOUSE_ROWS"
BUILD_FAILURES=0
if build_app "识字 App" "$ROOT_DIR/apps/literacy-app"; then
  LITERACY_BUILD_OK=1
else
  LITERACY_BUILD_OK=0
  BUILD_FAILURES=$((BUILD_FAILURES + 1))
fi
if build_app "数学 App" "$ROOT_DIR/apps/math-app"; then
  MATH_BUILD_OK=1
else
  MATH_BUILD_OK=0
  BUILD_FAILURES=$((BUILD_FAILURES + 1))
fi

if [[ "${BENCHMARK_SKIP_LIGHTHOUSE:-0}" == "1" ]]; then
  [[ "$LITERACY_BUILD_OK" == "1" ]] &&
    printf '识字 App\tSKIP\t-\t-\t-\tBENCHMARK_SKIP_LIGHTHOUSE=1\n' >>"$LIGHTHOUSE_ROWS" ||
    printf '识字 App\tSKIP\t-\t-\t-\tBuild failed\n' >>"$LIGHTHOUSE_ROWS"
  [[ "$MATH_BUILD_OK" == "1" ]] &&
    printf '数学 App\tSKIP\t-\t-\t-\tBENCHMARK_SKIP_LIGHTHOUSE=1\n' >>"$LIGHTHOUSE_ROWS" ||
    printf '数学 App\tSKIP\t-\t-\t-\tBuild failed\n' >>"$LIGHTHOUSE_ROWS"
else
  LIGHTHOUSE_EXECUTABLE="$(find_lighthouse)"
  if [[ -z "$LIGHTHOUSE_EXECUTABLE" ]]; then
    printf '\nLighthouse 未安装，记录为 SKIP（可设置 LIGHTHOUSE_BIN 后重跑）。\n'
    [[ "$LITERACY_BUILD_OK" == "1" ]] &&
      printf '识字 App\tSKIP\t-\t-\t-\tLighthouse not installed\n' >>"$LIGHTHOUSE_ROWS" ||
      printf '识字 App\tSKIP\t-\t-\t-\tBuild failed\n' >>"$LIGHTHOUSE_ROWS"
    [[ "$MATH_BUILD_OK" == "1" ]] &&
      printf '数学 App\tSKIP\t-\t-\t-\tLighthouse not installed\n' >>"$LIGHTHOUSE_ROWS" ||
      printf '数学 App\tSKIP\t-\t-\t-\tBuild failed\n' >>"$LIGHTHOUSE_ROWS"
  else
    if [[ "$LITERACY_BUILD_OK" == "1" ]]; then
      lighthouse_app "识字 App" "$ROOT_DIR/apps/literacy-app" 4173 "$LIGHTHOUSE_EXECUTABLE"
    else
      printf '识字 App\tSKIP\t-\t-\t-\tBuild failed\n' >>"$LIGHTHOUSE_ROWS"
    fi
    if [[ "$MATH_BUILD_OK" == "1" ]]; then
      lighthouse_app "数学 App" "$ROOT_DIR/apps/math-app" 4174 "$LIGHTHOUSE_EXECUTABLE"
    else
      printf '数学 App\tSKIP\t-\t-\t-\tBuild failed\n' >>"$LIGHTHOUSE_ROWS"
    fi
  fi
fi

REPORT_PATH="$TMP_DIR/report.md"
write_report "$REPORT_PATH"
printf '\n'
while IFS= read -r line; do printf '%s\n' "$line"; done <"$REPORT_PATH"

if [[ -n "${BENCHMARK_REPORT:-}" ]]; then
  mkdir -p "$(dirname "$BENCHMARK_REPORT")"
  cp "$REPORT_PATH" "$BENCHMARK_REPORT"
  printf '\n报告已写入 %s\n' "$BENCHMARK_REPORT"
fi

if ((BUILD_FAILURES > 0)); then
  printf '\nbenchmark: %s 个应用构建失败。\n' "$BUILD_FAILURES" >&2
  exit 1
fi
