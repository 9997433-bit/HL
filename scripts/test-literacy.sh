#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/apps/literacy-app"

[[ -f "$APP_DIR/package.json" ]] || {
  printf 'test-literacy: 缺少 %s/package.json\n' "$APP_DIR" >&2
  exit 1
}

printf '[识字 App] 校验绘本社区投稿（ajv schema + A 类规则）...\n'
node "$ROOT_DIR/scripts/import-book-submission.mjs" --check-all

if node -e 'const p=require(process.argv[1]); process.exit(p.scripts?.test ? 0 : 1)' \
  "$APP_DIR/package.json"; then
  printf '[识字 App] 运行项目测试...\n'
  npm --prefix "$APP_DIR" run test
else
  printf '[识字 App] 未定义单元测试，执行生产构建冒烟测试。\n'
fi

npm --prefix "$APP_DIR" run build

node - "$APP_DIR" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");

const appDir = process.argv[2];
const packageJson = JSON.parse(
  fs.readFileSync(path.join(appDir, "package.json"), "utf8"),
);
if (!packageJson.scripts?.build) {
  throw new Error("package.json 缺少 build 脚本");
}

const outputDir = path.join(appDir, "dist");
const indexPath = path.join(outputDir, "index.html");
if (!fs.existsSync(indexPath)) {
  throw new Error("生产构建缺少 dist/index.html");
}

const files = [];
const visit = (directory) => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) visit(fullPath);
    if (entry.isFile()) files.push(path.relative(outputDir, fullPath));
  }
};
visit(outputDir);

if (!files.some((file) => file.endsWith(".js"))) {
  throw new Error("生产构建未生成 JavaScript 资源");
}

const html = fs.readFileSync(indexPath, "utf8");
if (/["']\/?src\//.test(html)) {
  throw new Error("dist/index.html 仍引用开发源码 /src/");
}

console.log(`[识字 App] 基础测试通过：${files.length} 个构建文件。`);
NODE
