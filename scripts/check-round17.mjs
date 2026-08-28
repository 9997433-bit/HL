/**
 * Round 17 · 覆盖加深硬门槛（v1.1）。
 * 标准：.agent_workspace/ROUND17-ACCEPTANCE.md
 * `--json` 机读汇总。启动时（功能未合入）预期 0/8；
 * H8 依赖 round16 → round15 → round13 链条，干净环境需先
 * `npm run android:sim` 重建双 APK，否则 H8 连锁红。
 *
 * v1.0 → v1.1 堵住的误绿：
 *  - H4 不再把 `ROUND17_H4` 出现次数 / `explain:`·`steps:[` 撞词直接计入条数
 *    （v1.0 里写 20 遍标记字符串即绿）；只认剥注释后带可执行标记文件内的
 *    去重母题 id，且要求手写中文分步内容（去重中文句 ≥60）——空壳
 *    `explain()` 返回空数组凑 id 不算（红线 §禁止空壳凑数）；
 *  - H6 删除「doc 引用 ≥4 条路径即可过」的 OR 分支（v1.0 列 4 条假路径
 *    即绿，直接违反红线 §禁止伪造走查截图路径）；截图/录屏必须真实落盘
 *    ≥4 个且每个 ≥200 字节，且 认步/学演示/剖析/周报 四类场景词齐；
 *  - H7 不再继承 r13 report 自动绿（v1.0 启动即绿，架空本轮台账任务）；
 *    必须有 r17 台账：android-sim-report.md 或 device-blocked.md（含复现命令）；
 *  - H2/H5 标记判定统一走「剥注释后扫描目录」，不再硬编码三个文件路径；
 *    H5 场景词里去掉裸 `stage`（单个钩子名不再同时满足两条正则）。
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
/** 剥掉 HTML / 块 / 行注释——标记只有写在可执行代码里才算（红线 §禁止注释骗标）。 */
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
    else if (/\.(js|mjs|vue|ts|tsx|json)$/.test(name)) acc.push(rel.replace(/\\/g, '/'))
  }
  return acc
}

/** 在若干目录里找「剥注释后仍含 marker」的文件，返回 { files, blob }。 */
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

const LIT_SRC = 'apps/literacy-app/src'
const MATH_SRC = 'apps/math-app/src'

/* H1 Round17 差距续表 */
{
  const audit = read('.agent_workspace/round17-hongen-gap-audit.md')
  const ok =
    audit.length > 600 &&
    /识字|literacy/i.test(audit) &&
    /数学|math/i.test(audit) &&
    (/✅|◐|❌/.test(audit) || /达标|缺口/.test(audit))
  check('H1', ok, 'H1 Round17 差距续表就位', 'H1 缺少 round17-hongen-gap-audit.md 或内容过薄')
}

/* H2 富 Play ≥900（运行时口径 + narration 去重 ≥720；标记须可执行） */
{
  let rich = 0
  let distinct = 0
  try {
    const mod = await import(path.join(root, 'apps/literacy-app/src/data/char-play.js'))
    // ROUND18_H3 拆包后剧本按单元懒加载，启动时注册表是空的（架构契约 §2.7 主案）
    if (typeof mod.loadAllRichPlays === 'function') await mod.loadAllRichPlays()
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
    /* ignore：导入失败按 0 计 */
  }
  const h2 = scanExecMarker('ROUND17_H2', [
    'apps/literacy-app/src/data',
    'apps/literacy-app/scripts'
  ])
  const marked = h2.files.length > 0
  const ok = marked && rich >= 900 && distinct >= 720
  check(
    'H2',
    ok,
    `H2 富 Play ${rich} ≥ 900，narration 去重 ${distinct} ≥ 720（可执行标记 ×${h2.files.length}）`,
    `H2 富 Play 不足：rich=${rich}(需≥900)，narration去重=${distinct}(需≥720)，可执行标记=${marked}`
  )
}

/* H3 学演示 ≥27（可执行 ROUND16_H4/ROUND17_H3 标记文件内 skillId 去重；三态+可跳过） */
{
  const h3 = scanExecMarker('ROUND17_H3', [MATH_SRC])
  const h4legacy = scanExecMarker('ROUND16_H4', [MATH_SRC])
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

/* H4 精品剖析 ≥20（只认可执行 ROUND17_H4 文件内去重母题 id；
   手写分步链须有真实中文讲解——去重中文句 ≥60（约 ≥3 句/题）；
   标记出现次数、explain:/steps:[ 撞词一律不计入条数） */
{
  const h4 = scanExecMarker('ROUND17_H4', [MATH_SRC])
  const blob = h4.blob
  const marked = h4.files.length > 0
  let ids = new Set(
    [...blob.matchAll(/\b(?:masterId|problemId)\s*:\s*['"]([^'"]+)['"]/g)].map((m) => m[1])
  )
  if (ids.size < 20)
    ids = new Set([...blob.matchAll(/\bid\s*:\s*['"]([^'"]+)['"]/g)].map((m) => m[1]))
  const count = ids.size
  // 按引号切分再数中文，避免引号配对错位漏数（如 masterId 短串吞掉后续开引号）
  const zh = new Set()
  for (const frag of blob.split(/['"“”]/)) {
    const t = frag.trim()
    if (t.length >= 10 && (t.match(/[\u3400-\u9fff]/g) || []).length >= 8) zh.add(t)
  }
  const stepwise = /分步|步骤|steps/i.test(blob)
  const skippable =
    /跳过|skip/i.test(blob) ||
    /跳过|skip/i.test(scanExecMarker('ROUND16_H5', [MATH_SRC]).blob)
  check(
    'H4',
    marked && count >= 20 && zh.size >= 60 && stepwise && skippable,
    `H4 精品剖析 ${count} ≥ 20（去重中文讲解句 ${zh.size} ≥ 60，分步+可跳过）`,
    `H4 精品剖析不足（可执行标记=${marked}，母题=${count}(需≥20)，中文讲解句=${zh.size}(需≥60)，分步=${stepwise}，可跳过=${skippable}）`
  )
}

/* H5 学伴关键接线（标记须可执行；须命中接线点 + 学伴词证） */
{
  const h5 = scanExecMarker('ROUND17_H5', [LIT_SRC, MATH_SRC])
  const blob = h5.blob
  const wired =
    /CharDetail|useMascotCoach|QuizShell|recentWrong|pickMascotStage/.test(blob) &&
    /mascot|学伴|台词/i.test(blob)
  check(
    'H5',
    h5.files.length > 0 && wired,
    `H5 学伴关键路径已接线（可执行标记 ×${h5.files.length}）`,
    'H5 缺学伴关键接线（需可执行 ROUND17_H5 + 接线点 + 学伴词证）'
  )
}

/* H6 走查证据包（截图/录屏必须真实落盘 ≥4 个且每个 ≥200B；
   认步/学演示/剖析/周报 四类场景词齐；只列路径不落盘不算） */
{
  const doc = read('.agent_workspace/evidence/r17/walkthrough.md')
  const refs = [
    ...new Set(
      [...doc.matchAll(/evidence\/r17\/[^\s)'"`]+\.(?:png|jpe?g|webp|gif|mp4|webm)/gi)].map(
        (m) => m[0]
      )
    )
  ]
  const fileHits = refs.filter((p) => {
    try {
      return fs.statSync(path.join(root, '.agent_workspace', p)).size >= 200
    } catch {
      return false
    }
  }).length
  const scenes = ['认步|认一认|intro', '学演示|演示|learn-?demo', '剖析|explain|analysis', '周报|weekly'].filter(
    (kw) => new RegExp(kw, 'i').test(doc)
  ).length
  check(
    'H6',
    doc.length > 400 && scenes >= 4 && fileHits >= 4,
    `H6 走查证据包就位（引用 ${refs.length}，落盘 ${fileHits} ≥ 4，场景 ${scenes}/4）`,
    `H6 走查证据不足（doc=${doc.length}，引用=${refs.length}，落盘=${fileHits}(需≥4)，场景=${scenes}(需4)）`
  )
}

/* H7 真机或模拟闭环 / 诚实 BLOCKED 台账（必须是 r17 自己的台账；
   只继承 r13 旧 report 不算） */
{
  const sim =
    read('.agent_workspace/evidence/r17/android-sim-report.md') +
    read('.agent_workspace/evidence/r17/android-sim/report.json')
  const blocked = read('.agent_workspace/evidence/r17/device-blocked.md')
  const simOk =
    sim.length > 200 &&
    /android:sim|APK|模拟/i.test(sim) &&
    /sha256|report\.json|exit|simulated/i.test(sim)
  const blockedOk =
    blocked.length > 200 &&
    /BLOCKED/.test(blocked) &&
    /复现/.test(blocked) &&
    /npm run android|android:sim|gradle/i.test(blocked)
  check(
    'H7',
    simOk || blockedOk,
    'H7 r17 真机/模拟闭环或诚实 BLOCKED 台账就位',
    'H7 缺 r17 台账：需 evidence/r17/android-sim-report.md（可引用重跑的 report.json）或 device-blocked.md（BLOCKED+复现命令）；仅继承 r13 旧报告不算'
  )
}

/* H8 往轮不退化：check:round16 8/8 */
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
    `H8 check:round16 ${passed}/${total}（需 8/8；干净环境先 npm run android:sim 重建双 APK）`
  )
}

const passed = results.filter((r) => r.status === 'pass').length
const summary = { round: 17, probe: 'ROUND17-v1.1', passed, total: EXPECTED, results }
if (asJson) console.log(JSON.stringify(summary, null, 2))
else {
  console.log(`\nRound 17 check (ROUND17-v1.1): ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
  console.log('')
}
process.exitCode = passed === EXPECTED ? 0 : 1
