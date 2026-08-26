#!/usr/bin/env node
/**
 * check-tokens.mjs — 设计令牌迁移防回归门禁
 *
 * 依据：
 *   .agent_workspace/design-tokens-migration.md  §5 Phase 3 门禁 a/b/c
 *   .agent_workspace/round2-acceptance-plan.md   第 5 步（令牌与主题一致性）+ Round 3 章节
 *   .agent_workspace/ui-ux-design-spec.md        §11 令牌落地方式
 *
 * 用法：
 *   node scripts/check-tokens.mjs                # 全量门禁（Round 3 验收档，Phase 0–3 全部收口后必须 PASS）
 *   node scripts/check-tokens.mjs --wiring-only  # 仅第 C 段接线检查（Phase 0 合入门禁）
 *
 * 检查分段（对应迁移文档 §5 a/b/c，顺序按依赖排列）：
 *   C. 接线：两 App 入口 CSS 以 design-tokens.css 开头（其后紧跟 components.css）、
 *      vite `@shared` 别名就位、被引用文件真实存在、math index.html 静态挂 data-theme="cosmos"、
 *      令牌源文件含语义层与 cosmos 主题块。
 *   A. 旧令牌名归零：apps/ 源码内不得再出现 var(--seed-* / --space-0..3 / --ink* / --cyan …)；
 *      令牌源 §11 兼容别名节已删除。
 *   B. 硬编码色值预算：.vue 内十六进制色值 literacy = 0、math ≤ 10；
 *      行内含 `token-ok` 注释标记的白名单行豁免（需注明理由）。
 *
 * 退出码：0 = 所检各段全部 PASS；1 = 任一段 FAIL。
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const WIRING_ONLY = process.argv.includes('--wiring-only');

/* ------------------------------------------------------------------ 配置 */

const TOKENS_FILE = 'shared/styles/design-tokens.css';
const COMPONENTS_FILE = 'shared/styles/components.css';

const APPS = [
  {
    name: 'literacy-app',
    entryCss: 'apps/literacy-app/src/styles/base.css',
    viteConfig: 'apps/literacy-app/vite.config.js',
    srcDir: 'apps/literacy-app/src',
    indexHtml: 'apps/literacy-app/index.html',
    // literacy 的 data-theme 由 progress store 动态写入，不检查静态 index.html
    staticTheme: null,
    hexBudget: 0
  },
  {
    name: 'math-app',
    entryCss: 'apps/math-app/src/styles/main.css',
    viteConfig: 'apps/math-app/vite.config.js',
    srcDir: 'apps/math-app/src',
    indexHtml: 'apps/math-app/index.html',
    staticTheme: 'cosmos',
    hexBudget: 10
  }
];

// 迁移文档 §5.a 旧名清单（literacy --seed-* + math 别名 + math 骨架期变量）。
// 尾部限定 [),\s：] 中的 ) 与 , 覆盖 var(--x) / var(--x, fallback) 两种写法，
// 且避免误伤令牌自身的 --ink-900、--space-… 等合法名。
const OLD_NAME_BODY =
  'seed-[a-z]+|space-[0-3]|ink(?:-soft|-dim)?|cyan|violet|pink|gold|green|red|orange' +
  '|radius-[sml]|shadow-card|bg-deep|bg-card|text-main|text-dim|star-gold|radius-card|font-kid';
const OLD_NAME_USE_RE = new RegExp(`var\\(\\s*--(?:${OLD_NAME_BODY})\\s*[),]`, 'g');
// §11 别名定义形态（design-tokens.css 内 `--旧名:` 声明），Phase 3 应整节删除
const OLD_NAME_DEF_RE = new RegExp(`^\\s*--(?:${OLD_NAME_BODY})\\s*:`, 'm');

// 旧名扫描范围：两 App 的 src + index.html；不含 shared/（令牌源单独用定义检查约束）
const SCAN_EXTENSIONS = new Set(['.vue', '.css', '.js', '.mjs', '.html']);
const SKIP_DIRS = new Set(['node_modules', 'dist', '.git']);

// 硬编码色值：3–8 位十六进制；白名单标记行豁免
const HEX_RE = /#[0-9a-fA-F]{3,8}\b/g;
const HEX_WHITELIST_MARK = 'token-ok';

const MAX_SHOWN = 20; // 每段违例明细最多打印行数

/* ------------------------------------------------------------------ 工具 */

const read = (relPath) => readFileSync(join(ROOT, relPath), 'utf8');

function* walk(relDir) {
  const abs = join(ROOT, relDir);
  if (!existsSync(abs)) return;
  for (const name of readdirSync(abs)) {
    if (SKIP_DIRS.has(name)) continue;
    const rel = join(relDir, name);
    if (statSync(join(ROOT, rel)).isDirectory()) {
      yield* walk(rel);
    } else if (SCAN_EXTENSIONS.has(name.slice(name.lastIndexOf('.')))) {
      yield rel;
    }
  }
}

const stripCssComments = (css) => css.replace(/\/\*[\s\S]*?\*\//g, '');

/** 返回入口 CSS 顶部连续的 @import 目标列表（遇到首条非 import 规则即停止） */
function leadingImports(cssRelPath) {
  const lines = stripCssComments(read(cssRelPath)).split('\n');
  const imports = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (line === '' || line.startsWith('@charset')) continue;
    const m = line.match(/^@import\s+(?:url\(\s*)?['"]([^'"]+)['"]/);
    if (!m) break;
    imports.push(m[1]);
  }
  return imports;
}

/** 将 CSS @import 说明符解析为仓库相对路径（支持 @shared 别名与相对路径） */
function resolveImport(spec, fromCssRelPath) {
  if (spec.startsWith('@shared/')) return join('shared', spec.slice('@shared/'.length));
  return relative(ROOT, resolve(ROOT, dirname(fromCssRelPath), spec));
}

const results = []; // { section, ok, label, details[] }
function record(section, ok, label, details = []) {
  results.push({ section, ok, label, details });
  const mark = ok ? 'PASS' : 'FAIL';
  console.log(`  [${mark}] ${label}`);
  for (const d of details.slice(0, MAX_SHOWN)) console.log(`         ${d}`);
  if (details.length > MAX_SHOWN) console.log(`         … 共 ${details.length} 条，仅显示前 ${MAX_SHOWN} 条`);
}

/* ---------------------------------------------------------- C. 接线检查 */

function checkWiring() {
  console.log('\n== C. 接线（design-tokens.css 引入与主题挂载） ==');

  for (const f of [TOKENS_FILE, COMPONENTS_FILE]) {
    record('C', existsSync(join(ROOT, f)), `共享样式文件存在：${f}`);
  }

  if (existsSync(join(ROOT, TOKENS_FILE))) {
    const tokens = read(TOKENS_FILE);
    record(
      'C',
      tokens.includes('--bg-page') && /\[data-theme=['"]cosmos['"]\]/.test(tokens),
      '令牌源完整性：含语义层（--bg-page）与 cosmos 主题块'
    );
  }

  for (const app of APPS) {
    const missing = [app.entryCss, app.viteConfig].filter((f) => !existsSync(join(ROOT, f)));
    if (missing.length) {
      record('C', false, `${app.name}: 关键文件缺失`, missing);
      continue;
    }

    const imports = leadingImports(app.entryCss);
    const first = imports[0] ?? '(无 @import)';
    const second = imports[1] ?? '(无第二条 @import)';

    const firstOk = first.includes('design-tokens.css');
    record(
      'C',
      firstOk,
      `${app.name}: 入口 ${app.entryCss} 首个生效语句引入 design-tokens.css`,
      firstOk ? [] : [`实际首条：${first}`]
    );

    const secondOk = second.includes('components.css');
    record(
      'C',
      secondOk,
      `${app.name}: 第二条 @import 引入共享组件层 components.css`,
      secondOk ? [] : [`实际第二条：${second}`]
    );

    if (firstOk) {
      const resolved = resolveImport(first, app.entryCss);
      record(
        'C',
        existsSync(join(ROOT, resolved)),
        `${app.name}: design-tokens 引用路径可解析（${resolved}）`
      );
    }

    record(
      'C',
      /['"]@shared['"]\s*:/.test(read(app.viteConfig)),
      `${app.name}: vite.config.js 含 @shared 别名`
    );

    if (app.staticTheme) {
      const html = existsSync(join(ROOT, app.indexHtml)) ? read(app.indexHtml) : '';
      record(
        'C',
        new RegExp(`<html[^>]*data-theme=["']${app.staticTheme}["']`).test(html),
        `${app.name}: index.html 静态挂 data-theme="${app.staticTheme}"（避免首帧闪白）`
      );
    }
  }
}

/* ------------------------------------------------------ A. 旧令牌名归零 */

function checkOldNames() {
  console.log('\n== A. 旧令牌名归零（apps/ 源码 + §11 别名删除） ==');

  for (const app of APPS) {
    const hits = [];
    for (const file of [...walk(app.srcDir), app.indexHtml]) {
      if (!existsSync(join(ROOT, file))) continue;
      read(file).split('\n').forEach((line, i) => {
        for (const m of line.matchAll(OLD_NAME_USE_RE)) {
          hits.push(`${file}:${i + 1}  ${m[0]}`);
        }
      });
    }
    record('A', hits.length === 0, `${app.name}: 旧令牌名引用 = ${hits.length}（要求 0）`, hits);
  }

  if (existsSync(join(ROOT, TOKENS_FILE))) {
    const defHit = read(TOKENS_FILE).match(OLD_NAME_DEF_RE);
    record(
      'A',
      !defHit,
      `令牌源 §11 兼容别名已删除（${TOKENS_FILE} 无旧名定义）`,
      defHit ? [`仍存在定义：${defHit[0].trim()}`] : []
    );
  }
}

/* -------------------------------------------------- B. 硬编码色值预算 */

function checkHexBudget() {
  console.log('\n== B. .vue 硬编码色值预算（白名单标记：' + HEX_WHITELIST_MARK + '） ==');

  for (const app of APPS) {
    const hits = [];
    let whitelisted = 0;
    for (const file of walk(app.srcDir)) {
      if (!file.endsWith('.vue')) continue;
      read(file).split('\n').forEach((line, i) => {
        const matches = line.match(HEX_RE);
        if (!matches) return;
        if (line.includes(HEX_WHITELIST_MARK)) {
          whitelisted += matches.length;
          return;
        }
        hits.push(`${file}:${i + 1}  ${matches.join(' ')}`);
      });
    }
    record(
      'B',
      hits.length <= app.hexBudget,
      `${app.name}: 非白名单硬编码色值 = ${hits.length}（预算 ≤ ${app.hexBudget}，白名单豁免 ${whitelisted}）`,
      hits.length <= app.hexBudget ? [] : hits
    );
  }
}

/* ------------------------------------------------------------------ 主流程 */

console.log(`check:tokens — 设计令牌迁移门禁（模式：${WIRING_ONLY ? '仅接线 --wiring-only' : '全量'}）`);

checkWiring();
if (!WIRING_ONLY) {
  checkOldNames();
  checkHexBudget();
}

const failed = results.filter((r) => !r.ok);
const bySection = {};
for (const r of results) {
  bySection[r.section] ??= { pass: 0, fail: 0 };
  bySection[r.section][r.ok ? 'pass' : 'fail']++;
}

console.log('\n== 汇总 ==');
for (const [section, { pass, fail }] of Object.entries(bySection)) {
  console.log(`  段 ${section}: ${fail === 0 ? 'PASS' : 'FAIL'}（${pass} 过 / ${fail} 挂）`);
}
if (failed.length) {
  console.log(`\ncheck:tokens FAIL — ${failed.length} 项未过。修复指引见 .agent_workspace/round3-tokens-checklist.md`);
  process.exit(1);
}
console.log('\ncheck:tokens PASS — 全部门禁通过');
