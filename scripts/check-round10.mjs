/**
 * Round 10 洪恩深度对标硬门槛（v1.1 探针修订版）。
 * 标准：.agent_workspace/ROUND10-ACCEPTANCE.md（探针细则 §2，v1.1 修订记录见 §2 开头）
 *
 * 固定输出 8 个结果：H1–H8，结果数 ≠ 8 时门禁自身 FAIL。
 * 基线（R9 闭合 d89c455、R10 功能未合入）预期 1/8（仅 H8 绿）。
 *
 * `--json` 输出机读汇总（passed/failed/results）供编排器聚合。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const asJson = process.argv.includes('--json')
const results = []
const fails = []
const notes = []
const EXPECTED = 8

const check = (id, ok, passMsg, failMsg = passMsg) => {
  const msg = ok ? passMsg : failMsg
  results.push({ id, status: ok ? 'pass' : 'fail', msg })
  ;(ok ? notes : fails).push(`${ok ? '✓' : '✗'} ${msg}`)
}
const read = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}
const exists = (rel) => fs.existsSync(path.join(root, rel))
/** 剥 HTML / 块 / 整行 // 注释——探针信号必须写成代码（常量、断言名或行内尾注）。 */
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
const readStripped = (rel) => stripComments(read(rel))
const pkgVersion = (rel) => {
  try {
    return JSON.parse(read(rel)).version
  } catch {
    return ''
  }
}
const pkgScripts = (rel) => {
  try {
    return Object.values(JSON.parse(read(rel)).scripts ?? {}).join('\n')
  } catch {
    return ''
  }
}
const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
const validPng = (abs, minBytes) => {
  try {
    const buf = fs.readFileSync(abs)
    return buf.length >= minBytes && buf.subarray(0, 8).equals(PNG_MAGIC)
  } catch {
    return false
  }
}

const literacySmoke = readStripped('apps/literacy-app/scripts/smoke.mjs')
const mathSmoke = readStripped('apps/math-app/scripts/smoke.mjs')

/* H1 跟读 v3：Worker 构造/引入信号 + 离线 ASR 信号（剥注释）+ ROUND10_H1_SMOKE（§2.1） */
{
  const pool = []
  for (const d of [
    'apps/literacy-app/src/composables',
    'apps/literacy-app/src/utils',
    'apps/literacy-app/src/workers',
  ]) {
    const abs = path.join(root, d)
    if (!fs.existsSync(abs)) continue
    for (const f of fs.readdirSync(abs))
      if (/speech|asr|follow|sherpa|worker/i.test(f)) pool.push(`${d}/${f}`)
  }
  const speech = pool.map(readStripped).join('\n')
  const workerWired = /new\s+Worker\s*\(|\?worker|\bROUND10_H1\b/.test(speech)
  const offlineSig = /sherpa|offline[\s_-]{0,3}asr|离线\s*ASR|\bROUND10_H1\b/i.test(speech)
  const smoke = /\bROUND10_H1_SMOKE\b/.test(literacySmoke)
  check(
    'H1',
    workerWired && offlineSig && smoke,
    'H1 跟读 v3 离线 ASR Worker 已接线（Worker 构造 + 离线信号 + smoke）',
    `H1 跟读 v3 未闭环：worker=${workerWired}，offline=${offlineSig}，smoke=${smoke} —— r10-literacy-followread-v3`
  )
}

/* H2 OCR 真样张：≥2 张 real 命名有效 PNG（魔数 + ≥4KB）+ 脚本 real tier 接线 + ROUND10_H2（§2.2） */
{
  const dir = path.join(root, 'apps/literacy-app/scripts/fixtures/ocr')
  const real = fs.existsSync(dir)
    ? fs
        .readdirSync(dir)
        .filter(
          (f) =>
            /real|photo|capture|实拍/i.test(f) &&
            f.endsWith('.png') &&
            validPng(path.join(dir, f), 4096)
        ).length
    : 0
  const acc = readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs')
  const tierWired = /real|真实|实拍/i.test(acc)
  const marked = /\bROUND10_H2\b/.test(acc)
  check(
    'H2',
    real >= 2 && tierWired && marked,
    `H2 OCR 真样张 ${real} 张有效（魔数 + ≥4KB）+ real tier 已接进精度脚本`,
    `H2 OCR 真样张未闭环：有效 real 图=${real}/2，脚本 tier=${tierWired}，ROUND10_H2=${marked} —— r10-literacy-ocr-real`
  )
}

/* H3 推荐闭环：R10 专属开练入口信号 + 同文件跨域接线 + ROUND10_H3_SMOKE（§2.3）
   注意：v1.0 的跨文件拼接匹配在基线恒真（skill-graph 出 recommend、daily.js 出 daily），已废弃。 */
{
  const pool = []
  const dataDir = path.join(root, 'apps/math-app/src/data')
  const modDir = path.join(root, 'apps/math-app/src/modules/skill-graph')
  if (fs.existsSync(dataDir))
    for (const f of fs.readdirSync(dataDir))
      if (/^(skill|daily).*\.js$/.test(f)) pool.push(`apps/math-app/src/data/${f}`)
  if (fs.existsSync(modDir))
    for (const f of fs.readdirSync(modDir)) pool.push(`apps/math-app/src/modules/skill-graph/${f}`)
  const src = pool.map(readStripped).join('\n')
  const entry = /\bROUND10_H3\b|一键开练|startRecommended|recommendToDaily|practiceFromReco/i.test(src)
  const view = readStripped('apps/math-app/src/modules/skill-graph/SkillGraphView.vue')
  const daily = readStripped('apps/math-app/src/data/daily.js')
  const crossWired = /daily|wrongBook|错题|日冒险/i.test(view) || /recommend|推荐/.test(daily)
  const smoke =
    /\bROUND10_H3_SMOKE\b/.test(mathSmoke) || /\bROUND10_H3_SMOKE\b/.test(literacySmoke)
  check(
    'H3',
    entry && crossWired && smoke,
    'H3 图谱推荐 × 日冒险/错题本一键开练已接线（入口 + 同文件跨域信号 + smoke）',
    `H3 推荐闭环未接线：entry=${entry}，crossWired=${crossWired}，smoke=${smoke} —— r10-math-reco-daily`
  )
}

/* H4 投稿 CI：import 脚本实体（ajv + validate + 退出断言，剥注释）+ 挂进 test/check 链（§2.4） */
{
  const script = readStripped('scripts/import-book-submission.mjs')
  const scriptOk =
    exists('scripts/import-book-submission.mjs') &&
    /ajv/i.test(script) &&
    /validate|compile/i.test(script) &&
    /process\.exit|assert/.test(script)
  const chains =
    pkgScripts('package.json') +
    pkgScripts('apps/literacy-app/package.json') +
    read('scripts/test-literacy.sh')
  const chainOk = /import-book-submission/.test(chains)
  check(
    'H4',
    scriptOk && chainOk,
    'H4 绘本投稿 import 脚本（ajv 校验 + 退出断言）已挂进测试链',
    `H4 投稿 CI 未闭环：script=${scriptOk}，chain=${chainOk} —— r10-book-import-ci`
  )
}

/* H5 儿歌旋律：≥3 首合规条目挂真实音频资产（public 下文件存在且 ≥10KB，去重）+ ROUND10_H5（§2.5） */
{
  const audioFiles = new Set()
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    const list = mod.SONGS ?? mod.default ?? []
    const seen = new Set()
    for (const s of Array.isArray(list) ? list : []) {
      if (!s || typeof s !== 'object' || !s.id || seen.has(s.id)) continue
      seen.add(s.id)
      if (!(s.title ?? s.name)) continue
      const ref = String(s.audio || s.src || s.melodyUrl || '')
      const m = ref.match(/^[^?#]+\.(mp3|ogg|wav|m4a)$/i)
      if (!m) continue
      const rel = m[0].replace(/^\//, '')
      try {
        if (fs.statSync(path.join(root, 'apps/literacy-app/public', rel)).size >= 10240)
          audioFiles.add(rel)
      } catch {
        /* 资产不存在不算 */
      }
    }
  } catch {
    /* 数据模块不可读即 0 */
  }
  const marked = /\bROUND10_H5\b/.test(
    readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke
  )
  check(
    'H5',
    audioFiles.size >= 3 && marked,
    `H5 儿歌真实旋律 ${audioFiles.size} 首（public 资产存在且 ≥10KB）+ ROUND10_H5`,
    `H5 儿歌旋律未闭环：有效音频=${audioFiles.size}/3，ROUND10_H5=${marked} —— r10-literacy-songs-melody`
  )
}

/* H6 双档 Perf：evidence/r10 desktop JSON（可解析 + >200B + desktop 信号）+ 真机清单全量回填（§2.6） */
{
  let desktopJson = 0
  if (exists('.agent_workspace/evidence/r10')) {
    const walk = (d) => {
      for (const f of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, f.name)
        if (f.isDirectory()) walk(p)
        else if (/desktop/i.test(f.name) && f.name.endsWith('.json')) {
          try {
            const raw = fs.readFileSync(p, 'utf8')
            if (raw.length > 200 && /desktop|formFactor/i.test(raw)) {
              JSON.parse(raw)
              desktopJson++
            }
          } catch {
            /* 无效 JSON 不算 */
          }
        }
      }
    }
    walk(path.join(root, '.agent_workspace/evidence/r10'))
  }
  const checklist = read('.agent_workspace/ANDROID-DEVICE-CHECKLIST.md')
  const pending = (checklist.match(/\[待填[^\]]*\]/g) ?? []).length
  const done =
    (checklist.match(/\[x\]/gi) ?? []).length + (checklist.match(/\[SKIP[^\]]*\]/gi) ?? []).length
  const filled = checklist.length > 500 && pending === 0 && done >= 8
  check(
    'H6',
    desktopJson >= 1 && filled,
    `H6 桌面 LH 证据 ${desktopJson} 份有效 JSON + 真机清单已全量回填（勾选/SKIP ${done} 处）`,
    `H6 双档 Perf 未闭环：desktop=${desktopJson}/1，checklist=${filled}（待填 ${pending} 处，勾选/SKIP ${done}/8） —— r10-perf-device-desktop`
  )
}

/* H7 发布就绪：MIT LICENSE 实体 + 隐私路由与视图 + 三包版本 1.0.0 统一（§2.7） */
{
  const license = read('LICENSE')
  const licenseOk = license.length > 200 && /MIT/.test(license) && /copyright/i.test(license)
  const router = readStripped('apps/literacy-app/src/router/index.js')
  const routeOk = /privacy|隐私/.test(router)
  const viewsDir = path.join(root, 'apps/literacy-app/src/views')
  const viewOk =
    fs.existsSync(viewsDir) && fs.readdirSync(viewsDir).some((f) => /privacy/i.test(f))
  const verOk =
    pkgVersion('package.json') === '1.0.0' &&
    pkgVersion('apps/literacy-app/package.json') === '1.0.0' &&
    pkgVersion('apps/math-app/package.json') === '1.0.0'
  check(
    'H7',
    licenseOk && routeOk && viewOk && verOk,
    'H7 MIT LICENSE + 隐私路由与视图 + 三包版本 1.0.0 统一',
    `H7 发布未就绪：LICENSE=${licenseOk}，route=${routeOk}，view=${viewOk}，ver=${verOk} —— r10-global-release`
  )
}

/* H8 R9 不退化（§2.8） */
{
  const r9 = spawnSync(process.execPath, ['scripts/check-round9.mjs'], { cwd: root, encoding: 'utf8' })
  const ok = r9.status === 0 && /8\/8/.test(r9.stdout + r9.stderr)
  check('H8', ok, 'H8 Round 9 门禁 8/8 无退化', `H8 Round 9 退化 exit=${r9.status}`)
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}，请修复 check-round10.mjs`
  results.push({ id: 'meta', status: 'fail', msg })
  fails.push(`✗ ${msg}`)
}

if (asJson) {
  console.log(JSON.stringify({ passed: notes.length, failed: fails.length, results }, null, 2))
} else {
  notes.forEach((n) => console.log(' ', n))
  if (fails.length) {
    console.log('')
    fails.forEach((f) => console.log(' ', f))
  }
  console.log(`\nRound 10 深度门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
  if (fails.length) console.log('说明：R10 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
}

process.exit(fails.length ? 1 : 0)
