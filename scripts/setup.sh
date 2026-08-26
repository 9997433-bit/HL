#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIN_NODE_MAJOR=20
MIN_NODE_20_MINOR=19
MIN_NODE_22_MINOR=12
MAX_NODE_MAJOR=25
MIN_NPM_MAJOR=10

fail() {
  printf 'setup: %s\n' "$*" >&2
  exit 1
}

command -v node >/dev/null 2>&1 ||
  fail "未找到 Node.js；请安装 Node.js ^20.19 或 >=22.12 且 <25。"
command -v npm >/dev/null 2>&1 ||
  fail "未找到 npm；请先安装 npm >=10。"

NODE_VERSION="$(node --version | sed 's/^v//')"
IFS=. read -r NODE_MAJOR NODE_MINOR _ <<<"$NODE_VERSION"
NODE_MAJOR=$((10#$NODE_MAJOR))
NODE_MINOR=$((10#$NODE_MINOR))
if ! (( (NODE_MAJOR == MIN_NODE_MAJOR && NODE_MINOR >= MIN_NODE_20_MINOR) ||
        (NODE_MAJOR >= 22 && NODE_MAJOR < MAX_NODE_MAJOR &&
         (NODE_MAJOR != 22 || NODE_MINOR >= MIN_NODE_22_MINOR)) )); then
  fail "Node.js v${NODE_VERSION} 不受支持；要求 ^20.19 或 >=22.12 且 <25。"
fi

NPM_VERSION="$(npm --version)"
NPM_MAJOR="${NPM_VERSION%%.*}"
if (( NPM_MAJOR < MIN_NPM_MAJOR )); then
  fail "npm ${NPM_VERSION} 不受支持；要求 npm >=10。"
fi

if ! command -v zip >/dev/null 2>&1 &&
   ! command -v python3 >/dev/null 2>&1; then
  fail "打包需要 zip，或作为后备的 Python 3。"
fi

for app in apps/literacy-app apps/math-app; do
  [[ -f "$ROOT_DIR/$app/package.json" ]] ||
    fail "缺少工作区 $app/package.json。"
done

cd "$ROOT_DIR"
printf '环境: Node.js v%s, npm %s\n' "$NODE_VERSION" "$NPM_VERSION"

if [[ -f package-lock.json ]]; then
  printf '使用 package-lock.json 安装依赖...\n'
  npm ci --include=dev
else
  printf '首次安装依赖并生成 package-lock.json...\n'
  npm install --include=dev
fi

printf '环境安装完成。运行 npm test 或 npm run build:all 继续。\n'
