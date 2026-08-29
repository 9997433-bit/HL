/**
 * Round 19 · 精美度补齐 + 全库富 Play + 剖析视频级硬门槛（v1.0）。
 * 标准：.agent_workspace/ROUND19-ACCEPTANCE.md
 * `--json` 机读汇总。启动时（功能未合入）预期 0–1/8；
 * H8 依赖 round18 → round17 → … → round13 链条，干净环境需先
 * `npm run android:sim` 重建双 APK，否则 H8 连锁红。
 *
 * v1.0 继承 round18 防误绿手法，并针对本轮新门槛加锁：
 *  - 标记判定一律「剥注释后扫描目录」——ROUND19_H* 写在注释里不算
 *    （红线 §禁止注释骗标）；
 *  - H2 全库 ≥1820 + narration 去重 ≥1600，且 loadAllRichPlays 必须
 *    仍可调用（分片管线不破）；
 *  - H3 精美度：可执行标记 + ≥3 类升级词证（多拍节/道具反馈/氛围）+
 *    reduced-motion 跳过/降级；
 *  - H4 播放器：可执行标记 + 播/暂停/进度词证 + 自动推进 +
 *    reduced-motion 降级手动点步；
 *  - H5 双口径：运行时逐条验 WORD_PROBLEM_EXPLAINS 的 steps 全是函数
 *    （空壳 steps:[] 不计）+ 静态去重中文讲解句 ≥400；
 *  - H6 截图必须真实落盘 ≥4 个且每个 ≥200B；H7 只认 evidence/r19/
 *    本轮台账，不继承 r13/r17/r18 旧报告；
 *  - H2 运行时计数 `await`——拆包后 countRichPlays/listRichPlays 允许
 *    返回 Promise，同步/异步都认。
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

/* H1 Round19 差距续表（相对洪恩 + 相对 R18，标本轮归属） */
{
  const audit = read('.agent_workspace/round19-hongen-gap-audit.md')
  const ok =
    audit.length > 600 &&
    /识字|literacy/i.test(audit) &&
    /数学|math/i.test(audit) &&
    (/✅|◐|❌/.test(audit) || /达标|缺口/.test(audit)) &&
    /R18|Round\s*18|18\s*轮|上轮/i.test(audit) &&
    /R19|Round\s*19|19\s*轮|本轮/i.test(audit)
  check(
    'H1',
    ok,
    'H1 Round19 差距续表就位（双基线 + 本轮归属）',
    'H1 缺 round19-hongen-gap-audit.md 或内容过薄 / 未标 R18 与 R19 双基线归属'
  )
}

/* H2 全库富 Play ≥1820（运行时口径 + narration 去重 ≥1600；标记须可执行；
   分片管线不破：loadAllRichPlays 必须仍可调用） */
{
  let rich = 0
  let distinct = 0
  let hasLoader = false
  try {
    const mod = await import(path.join(root, 'apps/literacy-app/src/data/char-play.js'))
    hasLoader = typeof mod.loadAllRichPlays === 'function'
    if (hasLoader) await mod.loadAllRichPlays()
    if (typeof mod.countRichPlays === 'function') rich = Number(await mod.countRichPlays()) || 0
    if (typeof mod.listRichPlays === 'function') {
      const rows = await mod.listRichPlays()
      const narrs = new Set()
      for (const p of Array.isArray(rows) ? rows : []) {
        if (!p || p.templateFallback === true) continue
        if (typeof p.narration === 'string' && p.narration.trim()) narrs.add(p.narration.trim())
      }
      distinct = narrs.size
    }
  } catch {
    /* ignore：导入失败按 0 计 */
  }
  const h2 = scanExecMarker('ROUND19_H2', [
    'apps/literacy-app/src/data',
    'apps/literacy-app/scripts'
  ])
  const marked = h2.files.length > 0
  const ok = marked && hasLoader && rich >= 1820 && distinct >= 1600
  check(
    'H2',
    ok,
    `H2 富 Play ${rich} ≥ 1820，narration 去重 ${distinct} ≥ 1600（可执行标记 ×${h2.files.length}，loader=${hasLoader}）`,
    `H2 富 Play 不足：rich=${rich}(需≥1820)，narration去重=${distinct}(需≥1600)，可执行标记=${marked}，loadAllRichPlays=${hasLoader}`
  )
}

/* H3 精美度升级（可执行标记 + ≥3 类升级词证 + reduced-motion 跳过/降级） */
{
  const h3 = scanExecMarker('ROUND19_H3', [LIT_SRC])
  const marked = h3.files.length > 0
  const blob = h3.blob
  const cats = [
    /timeline|多拍|拍节|beat/i.test(blob),
    /命中|反馈|hitFeedback|propHit|道具/i.test(blob),
    /氛围|atmosphere|主题|themeLayer|ambience/i.test(blob)
  ].filter(Boolean).length
  const motionOk =
    /reduced-motion|reduceMotion|prefers-reduced-motion/i.test(blob) &&
    /skip|跳过|降级|fallback/i.test(blob)
  const ok = marked && cats >= 3 && motionOk
  check(
    'H3',
    ok,
    `H3 精美度升级就位（升级词证 ${cats}/3，reduced-motion 降级，可执行标记 ×${h3.files.length}）`,
    `H3 精美度未达标（标记=${marked}，升级词证=${cats}/3(需≥3)，reduced-motion降级=${motionOk}）`
  )
}

/* H4 剖析视频级播放器（播/暂停/进度 + 自动推进 + reduced-motion→手动点步） */
{
  const h4 = scanExecMarker('ROUND19_H4', [MATH_SRC])
  const marked = h4.files.length > 0
  const blob = h4.blob
  const playOk = /播放|\bplay\b|playing/i.test(blob)
  const pauseOk = /暂停|\bpause\b|paused/i.test(blob)
  const progressOk = /进度|progress|currentTime|\bseek\b/i.test(blob)
  const autoOk =
    /自动|autoplay|autoAdvance|setInterval|requestAnimationFrame|\bgsap\b|timeline/i.test(blob)
  const motionOk =
    /reduced-motion|reduceMotion|prefers-reduced-motion/i.test(blob) &&
    /手动|nextStep|点步|click/i.test(blob)
  const ok = marked && playOk && pauseOk && progressOk && autoOk && motionOk
  check(
    'H4',
    ok,
    `H4 剖析播放器词证齐（播/暂停/进度 + 自动推进 + reduced-motion 手动降级，可执行标记 ×${h4.files.length}）`,
    `H4 播放器未达标（标记=${marked}，播=${playOk}，暂停=${pauseOk}，进度=${progressOk}，自动=${autoOk}，reduced-motion手动=${motionOk}）`
  )
}

/* H5 精品剖析 ≥150（运行时逐条验 WORD_PROBLEM_EXPLAINS 的 steps 全是
   函数——空壳 steps:[] 不计；静态去重中文讲解句 ≥400；标记须可执行） */
{
  let masters = 0
  try {
    const ex = await import(path.join(root, 'apps/math-app/src/data/word-problem-explains.js'))
    const rows = Array.isArray(ex.WORD_PROBLEM_EXPLAINS) ? ex.WORD_PROBLEM_EXPLAINS : []
    const ids = new Set()
    for (const e of rows) {
      if (!e || typeof e.id !== 'string' || !e.id) continue
      if (!Array.isArray(e.steps) || e.steps.length < 1) continue
      if (!e.steps.every((fn) => typeof fn === 'function')) continue
      ids.add(e.id)
    }
    masters = ids.size
  } catch {
    /* ignore：导入失败按 0 计 */
  }
  const h5 = scanExecMarker('ROUND19_H5', [MATH_SRC])
  const marked = h5.files.length > 0
  // 按引号切分再数中文，避免引号配对错位漏数（同 round17/18 口径）
  const zh = new Set()
  for (const frag of h5.blob.split(/['"“”']/)) {
    const t = frag.trim()
    if (t.length >= 10 && (t.match(/[\u3400-\u9fff]/g) || []).length >= 8) zh.add(t)
  }
  const ok = marked && masters >= 150 && zh.size >= 400
  check(
    'H5',
    ok,
    `H5 精品剖析 ${masters} ≥ 150（去重中文讲解句 ${zh.size} ≥ 400，可执行标记 ×${h5.files.length}）`,
    `H5 精品剖析不足（可执行标记=${marked}，母题=${masters}(需≥150，空壳不计)，中文讲解句=${zh.size}(需≥400)）`
  )
}

/* H6 走查证据包（截图/录屏必须真实落盘 ≥4 个且每个 ≥200B；
   全库富玩/精美舞台/剖析播放器/周报或学伴 四类场景词齐） */
{
  const doc = read('.agent_workspace/evidence/r19/walkthrough.md')
  const refs = [
    ...new Set(
      [...doc.matchAll(/evidence\/r19\/[^\s)'"`]+\.(?:png|jpe?g|webp|gif|mp4|webm)/gi)].map(
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
  const scenes = [
    '富玩|富脚本|rich|全库',
    '精美|舞台|polish|CharPlayStage',
    '播放器|讲解播放|timeline|剖析',
    '周报|weekly|学伴|mascot'
  ].filter((kw) => new RegExp(kw, 'i').test(doc)).length
  check(
    'H6',
    doc.length > 400 && scenes >= 4 && fileHits >= 4,
    `H6 走查证据包就位（引用 ${refs.length}，落盘 ${fileHits} ≥ 4，场景 ${scenes}/4）`,
    `H6 走查证据不足（doc=${doc.length}，引用=${refs.length}，落盘=${fileHits}(需≥4)，场景=${scenes}(需4)）`
  )
}

/* H7 真机或模拟闭环 / 诚实 BLOCKED 台账（必须是 r19 自己的台账；
   只继承 r13/r17/r18 旧 report 不算） */
{
  const sim =
    read('.agent_workspace/evidence/r19/android-sim-report.md') +
    read('.agent_workspace/evidence/r19/android-sim/report.json')
  const blocked = read('.agent_workspace/evidence/r19/device-blocked.md')
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
    'H7 r19 真机/模拟闭环或诚实 BLOCKED 台账就位',
    'H7 缺 r19 台账：需 evidence/r19/android-sim-report.md（可引用重跑的 report.json）或 device-blocked.md（BLOCKED+复现命令）；仅继承 r13/r17/r18 旧报告不算'
  )
}

/* H8 往轮不退化：check:round18 8/8 */
{
  const r18 = spawnSync(process.execPath, ['scripts/check-round18.mjs', '--json'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 300000
  })
  let passed = 0
  let total = 8
  try {
    const j = JSON.parse(r18.stdout || '{}')
    const list = Array.isArray(j.results) ? j.results : []
    passed = list.filter((r) => r.status === 'pass').length
    total = j.total || list.length || 8
  } catch {
    const m = (r18.stdout || '').match(/(\d+)\s*\/\s*(\d+)/)
    if (m) {
      passed = Number(m[1])
      total = Number(m[2])
    }
  }
  check(
    'H8',
    passed >= 8 && total >= 8,
    `H8 check:round18 ${passed}/${total}`,
    `H8 check:round18 ${passed}/${total}（需 8/8；干净环境先 npm run android:sim 重建双 APK）`
  )
}

const passed = results.filter((r) => r.status === 'pass').length
const summary = { round: 19, probe: 'ROUND19-v1.0', passed, total: EXPECTED, results }
if (asJson) console.log(JSON.stringify(summary, null, 2))
else {
  console.log(`\nRound 19 check (ROUND19-v1.0): ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
  console.log('')
}
process.exitCode = passed === EXPECTED ? 0 : 1
