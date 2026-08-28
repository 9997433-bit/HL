#!/usr/bin/env node

/**
 * ROUND11_H6 数学 App 路由拆包预算。
 *
 * 从生产构建的入口与各路由块出发，计算“首次进入该路由”新增的 JS/CSS gzip
 * 传输量。入口已同步加载的依赖会从懒路由成本中扣除；路由块的静态依赖及同名
 * CSS 会计入，避免只看单个 Vue 输出块而漏算共享玩法壳。
 *
 * 用法：
 *   npm run build
 *   npm run check:route-budget
 *   npm run check:route-budget -- --json
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const here = path.dirname(fileURLToPath(import.meta.url))
const appRoot = path.resolve(here, '..')
const dist = path.join(appRoot, 'dist')
const assetsDir = path.join(dist, 'assets')
const routerPath = path.join(appRoot, 'src/router/index.js')
const asJson = process.argv.includes('--json')

const INITIAL_BUDGET_KIB = 96
const ROUTE_GROUPS = [
  {
    paths: ['/number-sense', '/compare'],
    source: 'modules/number-sense/NumberSenseView.vue',
    chunk: 'NumberSenseView',
    budgetKib: 48,
  },
  {
    paths: ['/compose-ten'],
    source: 'modules/number-sense/ComposeTenView.vue',
    chunk: 'ComposeTenView',
    budgetKib: 24,
  },
  {
    paths: ['/daily'],
    source: 'modules/daily/DailyView.vue',
    chunk: 'DailyView',
    budgetKib: 48,
  },
  {
    paths: ['/arithmetic', '/sprint'],
    source: 'modules/arithmetic/ArithmeticView.vue',
    chunk: 'ArithmeticView',
    budgetKib: 48,
  },
  {
    paths: ['/column-arithmetic'],
    source: 'modules/arithmetic/ColumnArithmeticView.vue',
    chunk: 'ColumnArithmeticView',
    budgetKib: 32,
  },
  {
    paths: ['/geometry'],
    source: 'modules/geometry/GeometryView.vue',
    chunk: 'GeometryView',
    budgetKib: 48,
  },
  {
    paths: ['/tangram'],
    source: 'modules/geometry/TangramView.vue',
    chunk: 'TangramView',
    budgetKib: 32,
  },
  {
    paths: ['/visual-demos'],
    source: 'modules/visual-demos/VisualDemosView.vue',
    chunk: 'VisualDemosView',
    budgetKib: 24,
  },
  {
    paths: ['/logic'],
    source: 'modules/logic/LogicView.vue',
    chunk: 'LogicView',
    budgetKib: 48,
  },
  {
    paths: ['/memory-pairs'],
    source: 'modules/logic/MemoryPairsView.vue',
    chunk: 'MemoryPairsView',
    budgetKib: 32,
  },
  {
    paths: ['/maze'],
    source: 'modules/logic/MazeView.vue',
    chunk: 'MazeView',
    budgetKib: 40,
  },
  {
    paths: ['/sudoku'],
    source: 'modules/sudoku/SudokuView.vue',
    chunk: 'SudokuView',
    budgetKib: 40,
  },
  {
    paths: ['/word-problems'],
    source: 'modules/word-problems/WordProblemsView.vue',
    chunk: 'WordProblemsView',
    budgetKib: 40,
  },
  {
    paths: ['/skill-graph'],
    source: 'modules/skill-graph/SkillGraphView.vue',
    chunk: 'SkillGraphView',
    budgetKib: 32,
  },
  {
    paths: ['/progress'],
    source: 'modules/progress/ProgressView.vue',
    chunk: 'ProgressView',
    budgetKib: 64,
  },
  {
    paths: ['/parent'],
    source: 'modules/parent/ParentView.vue',
    chunk: 'ParentView',
    budgetKib: 64,
  },
  {
    paths: ['/privacy'],
    source: 'modules/privacy/PrivacyView.vue',
    chunk: 'PrivacyView',
    budgetKib: 16,
  },
]

const errors = []
const results = []
const gzipCache = new Map()

const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const relative = (absolute) => path.relative(dist, absolute).split(path.sep).join('/')
const exists = (absolute) => fs.existsSync(absolute)

const toDistPath = (source, importer = 'index.html') => {
  const base = new URL(importer, 'http://route-budget.local/')
  const pathname = decodeURIComponent(new URL(source, base).pathname).replace(/^\/+/, '')
  const absolute = path.resolve(dist, pathname)
  if (absolute !== dist && !absolute.startsWith(`${dist}${path.sep}`)) {
    throw new Error(`构建依赖越出 dist：${source}`)
  }
  return relative(absolute)
}

const staticImports = (file) => {
  const code = fs.readFileSync(path.join(dist, file), 'utf8')
  const imports = []
  const pattern =
    /(?:^|[;\n])\s*(?:import(?!\s*\()|export)\s*(?:[^"'`;]*?\sfrom\s*)?["']([^"']+\.m?js)["']/g
  for (const match of code.matchAll(pattern)) {
    imports.push(toDistPath(match[1], `http://route-budget.local/${file}`))
  }
  return imports
}

const collectStaticClosure = (entry) => {
  const seen = new Set()
  const queue = [entry]
  while (queue.length > 0) {
    const file = queue.shift()
    if (seen.has(file)) continue
    const absolute = path.join(dist, file)
    if (!exists(absolute)) throw new Error(`构建依赖不存在：${file}`)
    seen.add(file)
    for (const dependency of staticImports(file)) {
      if (!seen.has(dependency)) queue.push(dependency)
    }
  }
  return seen
}

const gzipBytes = (file) => {
  if (!gzipCache.has(file)) {
    gzipCache.set(
      file,
      gzipSync(fs.readFileSync(path.join(dist, file)), { level: 9 }).byteLength
    )
  }
  return gzipCache.get(file)
}

const addCompanionCss = (files, allAssets) => {
  const withCss = new Set(files)
  for (const file of files) {
    if (!file.endsWith('.js')) continue
    const name = path.posix.basename(file)
    // Vite 5 的默认文件名为 <source>-<8-char hash>.js。
    const stem = name.length > 12 ? name.slice(0, -12) : ''
    if (!stem) continue
    const cssPattern = new RegExp(`^${escapeRegex(stem)}-[A-Za-z0-9_-]{8}\\.css$`)
    for (const asset of allAssets) {
      if (cssPattern.test(asset)) withCss.add(`assets/${asset}`)
    }
  }
  return withCss
}

try {
  const htmlPath = path.join(dist, 'index.html')
  if (!exists(htmlPath) || !exists(assetsDir)) {
    throw new Error('缺少生产构建；请先运行 npm run build。')
  }

  const html = fs.readFileSync(htmlPath, 'utf8')
  const moduleEntry = html.match(
    /<script\b[^>]*\btype=["']module["'][^>]*\bsrc=["']([^"']+\.m?js)["'][^>]*>/i
  )?.[1]
  if (!moduleEntry) throw new Error('dist/index.html 里找不到 module 入口。')

  const routerSource = fs.readFileSync(routerPath, 'utf8')
  const allAssets = fs.readdirSync(assetsDir)
  const initialJs = collectStaticClosure(toDistPath(moduleEntry))
  const initialFiles = addCompanionCss(initialJs, allAssets)
  for (const match of html.matchAll(/<link\b[^>]*\bhref=["']([^"']+\.css)["'][^>]*>/gi)) {
    initialFiles.add(toDistPath(match[1]))
  }

  const initialBytes = [...initialFiles].reduce((total, file) => total + gzipBytes(file), 0)
  const initialBudgetBytes = INITIAL_BUDGET_KIB * 1024
  results.push({
    paths: ['/'],
    mode: 'eager',
    chunk: 'app-shell + HomeView',
    files: [...initialFiles].sort(),
    gzipBytes: initialBytes,
    budgetBytes: initialBudgetBytes,
    headroomBytes: initialBudgetBytes - initialBytes,
    status: initialBytes <= initialBudgetBytes ? 'pass' : 'fail',
  })

  for (const route of ROUTE_GROUPS) {
    const sourceRef = `@/${route.source}`
    const importPattern = new RegExp(
      `component\\s*:\\s*\\(\\)\\s*=>\\s*import\\(["']${escapeRegex(sourceRef)}["']\\)`
    )
    if (!importPattern.test(routerSource)) {
      errors.push(`${route.paths.join('、')} 不再按路由懒加载 ${sourceRef}`)
      continue
    }
    for (const routePath of route.paths) {
      const pathPattern = new RegExp(`path\\s*:\\s*["']${escapeRegex(routePath)}["']`)
      if (!pathPattern.test(routerSource)) errors.push(`路由表缺少 ${routePath}`)
    }

    const chunkPattern = new RegExp(`^${escapeRegex(route.chunk)}-[A-Za-z0-9_-]{8}\\.js$`)
    const matches = allAssets.filter((file) => chunkPattern.test(file))
    if (matches.length !== 1) {
      errors.push(
        `${route.paths.join('、')} 预期恰好一个 ${route.chunk} 构建块，实际 ${matches.length}`
      )
      continue
    }

    const closure = collectStaticClosure(`assets/${matches[0]}`)
    const incrementalJs = new Set([...closure].filter((file) => !initialJs.has(file)))
    const incrementalFiles = addCompanionCss(incrementalJs, allAssets)
    const totalBytes = [...incrementalFiles].reduce(
      (total, file) => total + gzipBytes(file),
      0
    )
    const budgetBytes = route.budgetKib * 1024
    results.push({
      paths: route.paths,
      mode: 'lazy',
      chunk: route.chunk,
      files: [...incrementalFiles].sort(),
      gzipBytes: totalBytes,
      budgetBytes,
      headroomBytes: budgetBytes - totalBytes,
      status: totalBytes <= budgetBytes ? 'pass' : 'fail',
    })
  }
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error))
}

for (const result of results) {
  if (result.status === 'fail') {
    errors.push(
      `${result.paths.join('、')} gzip ${result.gzipBytes} B 超出预算 ${result.budgetBytes} B`
    )
  }
}

const report = {
  modelSlug: 'gpt-5.6-sol',
  marker: 'ROUND11_H6',
  unit: 'bytes (gzip level 9)',
  passed: errors.length === 0 && results.length === ROUTE_GROUPS.length + 1,
  routes: results,
  errors,
}

if (asJson) {
  console.log(JSON.stringify(report, null, 2))
} else {
  for (const result of results) {
    const usedKib = (result.gzipBytes / 1024).toFixed(1)
    const budgetKib = (result.budgetBytes / 1024).toFixed(0)
    const headroomKib = (result.headroomBytes / 1024).toFixed(1)
    console.log(
      ` ${result.status === 'pass' ? '✓' : '✗'} ${result.paths.join('、')}: ` +
        `${usedKib} KiB / ${budgetKib} KiB gzip（余量 ${headroomKib} KiB）`
    )
  }
  errors.forEach((error) => console.error(` ✗ ${error}`))
  console.log(
    `\n数学路由拆包预算：${results.filter((item) => item.status === 'pass').length}/` +
      `${ROUTE_GROUPS.length + 1} 组通过。`
  )
}

process.exit(report.passed ? 0 : 1)
