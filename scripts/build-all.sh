#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"

fail() {
  printf 'build-all: %s\n' "$*" >&2
  exit 1
}

command -v node >/dev/null 2>&1 || fail "未找到 Node.js，请先运行 scripts/setup.sh。"
command -v npm >/dev/null 2>&1 || fail "未找到 npm，请先运行 scripts/setup.sh。"
mkdir -p "$DIST_DIR"

create_archive() {
  local source_dir="$1"
  local archive_path="$2"

  rm -f "$archive_path"
  if command -v zip >/dev/null 2>&1; then
    (
      cd "$source_dir"
      zip -q -r -X "$archive_path" .
    )
    zip -T "$archive_path" >/dev/null
    return
  fi

  command -v python3 >/dev/null 2>&1 ||
    fail "未找到 zip 或 Python 3，无法创建压缩包。"
  python3 - "$source_dir" "$archive_path" <<'PY'
from pathlib import Path
import sys
import zipfile

source = Path(sys.argv[1])
archive = Path(sys.argv[2])
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    for item in sorted(source.rglob("*")):
        if item.is_file():
            output.write(item, item.relative_to(source))
PY
}

build_app() {
  local label="$1"
  local app_dir="$2"
  local archive_name="$3"
  local build_dir="$app_dir/dist"
  local archive_path="$DIST_DIR/$archive_name"

  [[ -f "$app_dir/package.json" ]] ||
    fail "${label}工作区缺少 package.json: $app_dir"

  printf '\n[%s] 构建生产版本...\n' "$label"
  npm --prefix "$app_dir" run build

  [[ -f "$build_dir/index.html" ]] ||
    fail "${label}构建未生成 dist/index.html。"

  # 产物里打包了 MIT/GSAP/APL 组件，第三方声明必须随 zip 分发（合规项 C-2）。
  [[ -f "$ROOT_DIR/THIRD_PARTY_NOTICES.md" ]] ||
    fail "缺少 THIRD_PARTY_NOTICES.md，不能出包。"
  cp "$ROOT_DIR/THIRD_PARTY_NOTICES.md" "$build_dir/THIRD_PARTY_NOTICES.md"

  printf '[%s] 打包 %s...\n' "$label" "$archive_name"
  create_archive "$build_dir" "$archive_path"
  [[ -s "$archive_path" ]] || fail "${label}压缩包为空。"
  printf '[%s] 完成: %s\n' "$label" "$archive_path"
}

build_app "识字 App" "$ROOT_DIR/apps/literacy-app" "hongen-literacy-app.zip"
build_app "数学 App" "$ROOT_DIR/apps/math-app" "hongen-math-app.zip"

printf '\n全部构建与打包完成。\n'
