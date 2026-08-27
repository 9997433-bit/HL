#!/usr/bin/env bash
# 构建 Web 产物后，将 dist 同步到 Capacitor Android 工程。
# 用法：bash scripts/sync-android.sh [literacy|math|all]
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-all}"

fail() {
  printf 'sync-android: %s\n' "$*" >&2
  exit 1
}

command -v npx >/dev/null 2>&1 || fail "未找到 npx。"
command -v node >/dev/null 2>&1 || fail "未找到 node。"

ensure_android() {
  local app_dir="$1"
  local label="$2"
  if [[ ! -d "$app_dir/android" ]]; then
    printf '[%s] 初始化 Android 工程...\n' "$label"
    (cd "$app_dir" && npx cap add android)
  fi
}

sync_app() {
  local label="$1"
  local app_dir="$2"

  [[ -f "$app_dir/package.json" ]] || fail "${label}缺少 package.json"
  [[ -f "$app_dir/capacitor.config.json" ]] || fail "${label}缺少 capacitor.config.json"

  printf '\n[%s] 构建 Web 产物...\n' "$label"
  npm --prefix "$app_dir" run build

  [[ -f "$app_dir/dist/index.html" ]] ||
    fail "${label}构建未生成 dist/index.html。"

  ensure_android "$app_dir" "$label"

  printf '[%s] 同步到 Android (cap copy + cap sync)...\n' "$label"
  (cd "$app_dir" && npx cap copy android && npx cap sync android)

  printf '[%s] Android 同步完成: %s/android/\n' "$label" "$app_dir"
}

case "$TARGET" in
  literacy)
    sync_app "识字 App" "$ROOT_DIR/apps/literacy-app"
    ;;
  math)
    sync_app "数学 App" "$ROOT_DIR/apps/math-app"
    ;;
  all)
    sync_app "识字 App" "$ROOT_DIR/apps/literacy-app"
    sync_app "数学 App" "$ROOT_DIR/apps/math-app"
    ;;
  *)
    fail "未知目标: $TARGET（可用 literacy | math | all）"
    ;;
esac

printf '\n全部 Android 同步完成。本地编译 APK：cd apps/<app>/android && ./gradlew assembleDebug\n'
