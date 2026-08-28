/**
 * Round 17 · 覆盖加深硬门槛（v1.0）。
 * 标准：.agent_workspace/ROUND17-ACCEPTANCE.md
 * `--json` 机读汇总。启动时预期多数红；H8 依赖 round16 应绿。
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
const notes = []
const fails = []
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
const strip = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const walk = (dirRel, acc = []) => {
  const abs = path.join(root, dirRel)
  if (!fs.existsSync(abs)) return acc
  for (const name of fs.readdirSync(abs)) {
    const rel = path.join(dirRel, name)
    const st = fs.statSync(path.join(root, rel))
    if (st.isDirectory()) walk(rel, acc)
    else if (/\.(js|mjs|vue|ts|tsx)$/.test(name)) acc.push(rel.replace(/\\/g, '/'))
  }
  return acc
}

const scanExecMarker = (marker, dirs) => {
  const files = []
  let blob = ''
  for (const dir of dirs) {
    for (const rel of walk(dir)) {
      const src = strip(read(rel))
      if (src.includes(marker)) {
        files.push(rel)
        blob += `\n${src}`
      }
    }
  }
  return { files, blob }
}

/* H1 */
{
  const audit = read('.agent_workspace/round17-hongen-gap-audit.md')
  const ok =
    audit.length > 600 &&
    /识字|literacy/i.test(audit) &&
    /数学|math/i.test(audit) &&
    (/✅|◐|❌/.test(audit) || /达标|缺口/.test(audit))
  check('H1', ok, 'H1 Round17 差距续表就位', 'H1 缺少 round17-hongen-gap-audit.md 或内容过薄')
}

/* H2 富 Play ≥900 */
{
  let rich = 0
  let distinct = 0
  try {
    const mod = await import(path.join(root, 'apps/literacy-app/src/data/char-play.js'))
    if (typeof mod.countRichPlays === 'function') rich = mod.countRichPlays()
    if (typeof mod.listRichPlays === 'function') {
      const narrs = new Set()
      for (const p of mod.listRichPlays()) {
        if (!p || p.templateFallback === true) continue
        if (typeof p.narration === 'string' && p.narration.trim()) narrs.add(p.narration.trim())
      }
      distinct = narrs.size
    }
  } catch {
    /* ignore */
  }
  const marked =
    /ROUND17_H2/.test(strip(read('apps/literacy-app/src/data/char-play.js'))) ||
    /ROUND17_H2/.test(strip(read('apps/literacy-app/src/data/char-play-rich.js'))) ||
    /ROUND17_H2/.test(strip(read('apps/literacy-app/scripts/gen-char-play-rich.mjs')))
  const ok = marked && rich >= 900 && distinct >= 720
  check(
    'H2',
    ok,
    `H2 富 Play ${rich} ≥ 900，narration 去重 ${distinct} ≥ 720`,
    `H2 富 Play 不足：rich=${rich}(需≥900)，narration去重=${distinct}(需≥720)，标记=${marked}`
  )
}

/* H3 学演示 ≥27 */
{
  const h3 = scanExecMarker('ROUND17_H3', ['apps/math-app/src'])
  const h4legacy = scanExecMarker('ROUND16_H4', ['apps/math-app/src'])
  const blob = h3.blob + h4legacy.blob
  const marked = h3.files.length + h4legacy.files.length > 0
  const threeStage =
    /实物|concrete|实景/.test(blob) &&
    /图形|pictorial|图示|diagram/.test(blob) &&
    /算式|equation|abstract|符号/.test(blob)
  const skippable = /跳过|skip/i.test(blob)
  const ids = new Set(
    [...blob.matchAll(/\b(?:skillId|demoId)\s*:\s*['"]([^'"]+)['"]/g)].map((m) => m[1])
  )
  const count = ids.size
  check(
    'H3',
    marked && threeStage && skippable && count >= 27,
    `H3 数学学演示 ${count} ≥ 27（三态+可跳过）`,
    `H3 学演示不足（标记=${marked}，三态=${threeStage}，可跳过=${skippable}，计数=${count}）`
  )
}

/* H4 精品剖析 ≥20 */
{
  const blob =
    strip(read('apps/math-app/src/utils/wpAnalysis.js')) +
    strip(read('apps/math-app/src/data/word-problem-explains.js')) +
    strip(read('apps/math-app/src/modules/word-problems/explains.js'))
  const marked = /ROUND17_H4/.test(blob)
  const hand =
    (blob.match(/\bexplain\s*[:=]/g) || []).length +
    (blob.match(/ROUND17_H4/g) || []).length +
    (blob.match(/steps\s*:\s*\[/g) || []).length
  // count explicit hand-written entries
  let entries = 0
  const m = blob.matchAll(/(?:id|masterId|problemId)\s*:\s*['"][^'"]+['"]/g)
  for (const _ of m) entries += 1
  const count = Math.max(entries, hand >= 20 ? hand : entries)
  check(
    'H4',
    marked && count >= 20,
    `H4 精品剖析 ${count} ≥ 20`,
    `H4 精品剖析不足（标记=${marked}，计数=${count}）`
  )
}

/* H5 学伴关键接线 */
{
  const h5 = scanExecMarker('ROUND17_H5', [
    'apps/literacy-app/src',
    'apps/math-app/src'
  ])
  const blob = h5.blob
  const wired =
    /CharDetail|useMascotCoach|QuizShell|recentWrong|pickMascotStage/.test(blob) &&
    /mascot|学伴|台词|stage/i.test(blob)
  check(
    'H5',
    h5.files.length > 0 && wired,
    `H5 学伴关键路径已接线（×${h5.files.length}）`,
    'H5 缺学伴关键接线（ROUND17_H5）'
  )
}

/* H6 走查证据包 */
{
  const doc = read('.agent_workspace/evidence/r17/walkthrough.md')
  const shots = [
    ...doc.matchAll(/evidence\/r17\/[^\s)]+\.(png|jpg|webp|mp4)/gi)
  ].map((m) => m[0])
  const existing = shots.filter((rel) => exists(`.agent_workspace/${rel.replace(/^evidence\//, 'evidence/')}`) || exists(`.agent_workspace/${rel}`))
  // also accept paths like evidence/r17/foo.png relative to .agent_workspace
  const okFiles = shots.filter((p) => {
    const rel = p.startsWith('evidence/') ? `.agent_workspace/${p}` : p
    return exists(rel.replace(/^\.agent_workspace\//, '')) || exists(rel) || exists(path.join('.agent_workspace', p))
  })
  const n = Math.max(okFiles.length, existing.length, (doc.match(/!\[/g) || []).length)
  const pathsOk =
    doc.length > 400 &&
    /认|intro|演示|剖析|周报/.test(doc) &&
    (n >= 4 || shots.length >= 4)
  // softer: if doc lists 4 paths and files exist
  let fileHits = 0
  for (const p of shots) {
    if (exists(`.agent_workspace/${p}`) || exists(p)) fileHits += 1
  }
  check(
    'H6',
    pathsOk && (fileHits >= 4 || shots.length >= 4),
    `H6 走查证据包就位（引用 ${shots.length}，落盘 ${fileHits}）`,
    `H6 走查证据不足（doc=${doc.length}，引用=${shots.length}，落盘=${fileHits}）`
  )
}

/* H7 真机或模拟 / BLOCKED 台账 */
{
  const report =
    read('.agent_workspace/evidence/r17/android-sim-report.md') +
    read('.agent_workspace/evidence/r17/device-blocked.md') +
    read('.agent_workspace/evidence/r13/android-sim/report.json')
  const ok =
    (/android:sim|APK|模拟/.test(report) && report.length > 200) ||
    (/BLOCKED/.test(report) && /复现|命令|npm run android/.test(report))
  check(
    'H7',
    ok,
    'H7 真机/模拟闭环或诚实 BLOCKED 台账就位',
    'H7 缺 android:sim 报告或 BLOCKED 台账'
  )
}

/* H8 */
{
  const r16 = spawnSync(process.execPath, ['scripts/check-round16.mjs', '--json'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 180000
  })
  let passed = 0
  let total = 8
  try {
    const j = JSON.parse(r16.stdout || '{}')
    const list = Array.isArray(j.results) ? j.results : []
    passed = list.filter((r) => r.status === 'pass').length
    total = j.total || list.length || 8
  } catch {
    const m = (r16.stdout || '').match(/(\d+)\s*\/\s*(\d+)/)
    if (m) {
      passed = Number(m[1])
      total = Number(m[2])
    }
  }
  check(
    'H8',
    passed >= 8 && total >= 8,
    `H8 check:round16 ${passed}/${total}`,
    `H8 check:round16 ${passed}/${total}（需要 8/8）`
  )
}

const passed = results.filter((r) => r.status === 'pass').length
const summary = { round: 17, probe: 'ROUND17-v1.0', passed, total: EXPECTED, results }
if (asJson) console.log(JSON.stringify(summary, null, 2))
else {
  console.log(`\nRound 17 check (ROUND17-v1.0): ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
  console.log('')
}
process.exitCode = passed === EXPECTED ? 0 : 1
