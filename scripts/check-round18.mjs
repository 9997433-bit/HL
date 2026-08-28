/**
 * Round 18 · 密度收口 + 拆包性能 + 剖析对齐硬门槛（v1.0）。
 * 标准：.agent_workspace/ROUND18-ACCEPTANCE.md
 * `--json` 机读汇总。启动时（功能未合入）预期 0–1/8；
 * H8 依赖 round17 → round16 → round15 → round13 链条，干净环境需先
 * `npm run android:sim` 重建双 APK，否则 H8 连锁红。
 *
 * v1.0 就带上 round17 v1.1 已验证的防误绿手法，并针对本轮新门槛加锁：
 *  - 标记判定一律「剥注释后扫描目录」——ROUND18_H* 写在注释里不算
 *    （红线 §禁止注释骗标）；
 *  - H3 拆包不信口头：可执行标记 + 动态加载词证、全 src 无整包静态
 *    import、分片 ≥5 个且合计 ≥100KB 四道锁——「留整包 + 摆空壳分片」
 *    或「单片懒加载整包」都过不去；
 *  - H4 步数对齐是运行时口径：reseed 后逐母题连抽 2 个实例跑
 *    buildAnalysis，一致率 ≥90%；同时题库 ≥200 防「删掉不一致母题
 *    凑比例」；
 *  - H5 双口径：运行时逐条验 WORD_PROBLEM_EXPLAINS 的 steps 全是函数
 *    （空壳 steps:[] 不计）+ 静态去重中文讲解句 ≥200；
 *  - H6 截图必须真实落盘 ≥4 个且每个 ≥200B（沿用 v1.1，无 doc-only
 *    OR 分支）；H7 只认 evidence/r18/ 本轮台账，不继承 r13/r17 旧报告；
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

/* H1 Round18 差距续表（相对洪恩 + 相对 R17，标本轮归属） */
{
  const audit = read('.agent_workspace/round18-hongen-gap-audit.md')
  const ok =
    audit.length > 600 &&
    /识字|literacy/i.test(audit) &&
    /数学|math/i.test(audit) &&
    (/✅|◐|❌/.test(audit) || /达标|缺口/.test(audit)) &&
    /R17|Round\s*17|17\s*轮|上轮/i.test(audit) &&
    /R18|Round\s*18|18\s*轮|本轮/i.test(audit)
  check(
    'H1',
    ok,
    'H1 Round18 差距续表就位（双基线 + 本轮归属）',
    'H1 缺 round18-hongen-gap-audit.md 或内容过薄 / 未标 R17 与 R18 双基线归属'
  )
}

/* H2 富 Play ≥1200（运行时口径 + narration 去重 ≥960；标记须可执行；
   拆包后 countRichPlays/listRichPlays 允许返回 Promise，一律 await） */
{
  let rich = 0
  let distinct = 0
  try {
    const mod = await import(path.join(root, 'apps/literacy-app/src/data/char-play.js'))
    // H3 落地后剧本按单元懒加载，两个计数口径都是「已注册条数」，
    // 不先装全就只能数到 0——架构契约 §2.7 主案的那一行加载适配，阈值不动。
    if (typeof mod.loadAllRichPlays === 'function') await mod.loadAllRichPlays()
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
  const h2 = scanExecMarker('ROUND18_H2', [
    'apps/literacy-app/src/data',
    'apps/literacy-app/scripts'
  ])
  const marked = h2.files.length > 0
  const ok = marked && rich >= 1200 && distinct >= 960
  check(
    'H2',
    ok,
    `H2 富 Play ${rich} ≥ 1200，narration 去重 ${distinct} ≥ 960（可执行标记 ×${h2.files.length}）`,
    `H2 富 Play 不足：rich=${rich}(需≥1200)，narration去重=${distinct}(需≥960)，可执行标记=${marked}`
  )
}

/* H3 富脚本按单元拆包（四道锁：可执行标记+动态加载词证 / 无整包静态
   import / 分片 ≥5 / 分片合计 ≥100KB——空壳分片、单片懒加载整包都不算） */
{
  const h3 = scanExecMarker('ROUND18_H3', [LIT_SRC])
  const marked = h3.files.length > 0
  const loaderOk =
    (/import\s*\(/.test(h3.blob) || /import\.meta\.glob/.test(h3.blob)) &&
    /rich|富脚本/i.test(h3.blob) &&
    /unit|单元/i.test(h3.blob)
  // specifier 以 char-play-rich(.js) 结尾才算整包；char-play-rich/index.js 等分片索引不在此列
  const staticRe =
    /(?:^|\n)\s*(?:import|export)[^\n]*?from\s*['"][^'"]*char-play-rich(?:\.js)?['"]|(?:^|\n)\s*import\s*['"][^'"]*char-play-rich(?:\.js)?['"]/
  const staticHits = []
  const chunkFiles = []
  let chunkBytes = 0
  for (const rel of walk(LIT_SRC)) {
    if (staticRe.test(strip(read(rel)))) staticHits.push(rel)
    if (/play-rich/.test(rel) && !/(^|\/)char-play-rich\.js$/.test(rel)) {
      chunkFiles.push(rel)
      try {
        chunkBytes += fs.statSync(path.join(root, rel)).size
      } catch {
        /* ignore */
      }
    }
  }
  const ok =
    marked && loaderOk && staticHits.length === 0 && chunkFiles.length >= 5 && chunkBytes >= 100000
  check(
    'H3',
    ok,
    `H3 富脚本已按单元拆包（分片 ${chunkFiles.length} ≥ 5，合计 ${Math.round(chunkBytes / 1024)}KB ≥ 100KB，无整包静态 import）`,
    `H3 拆包未达标（标记=${marked}，loader=${loaderOk}，整包静态import=${staticHits.length}处${staticHits.length ? `[${staticHits.slice(0, 3).join(', ')}]` : ''}，分片=${chunkFiles.length}(需≥5)，分片体量=${Math.round(chunkBytes / 1024)}KB(需≥100KB)）`
  )
}

/* H4 剖析步数对齐 ≥90%（运行时全量：reseed 后逐母题连抽 2 个实例跑
   buildAnalysis；题库 ≥200 防删题凑比例；标记须可执行） */
{
  let total = 0
  let aligned = 0
  let importErr = ''
  try {
    const rnd = await import(path.join(root, 'apps/math-app/src/utils/random.js'))
    if (typeof rnd.reseed === 'function') rnd.reseed(20260828)
    const wp = await import(path.join(root, 'apps/math-app/src/data/wordProblems.js'))
    const wa = await import(path.join(root, 'apps/math-app/src/utils/wpAnalysis.js'))
    const list = Array.isArray(wp.WORD_PROBLEMS) ? wp.WORD_PROBLEMS : []
    for (const p of list) {
      total += 1
      let ok = Number.isInteger(p?.steps) && p.steps >= 1
      for (let k = 0; ok && k < 2; k += 1) {
        try {
          const a = wa.buildAnalysis(p.make())
          if ((a?.steps?.length ?? 0) !== p.steps) ok = false
        } catch {
          ok = false
        }
      }
      if (ok) aligned += 1
    }
  } catch (e) {
    importErr = String(e?.message ?? e).slice(0, 80)
  }
  const rate = total ? aligned / total : 0
  const pct = (rate * 100).toFixed(1)
  const h4 = scanExecMarker('ROUND18_H4', [MATH_SRC])
  const marked = h4.files.length > 0
  const ok = marked && total >= 200 && rate >= 0.9
  check(
    'H4',
    ok,
    `H4 步数对齐 ${aligned}/${total} = ${pct}% ≥ 90%（题库 ≥200，可执行标记 ×${h4.files.length}）`,
    `H4 步数未对齐：${aligned}/${total} = ${pct}%(需≥90%)，题库=${total}(需≥200)，可执行标记=${marked}${importErr ? `，导入失败：${importErr}` : ''}`
  )
}

/* H5 精品剖析 ≥80（运行时逐条验 WORD_PROBLEM_EXPLAINS 的 steps 全是
   函数——空壳 steps:[] 不计；静态去重中文讲解句 ≥200；标记须可执行） */
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
  const h5 = scanExecMarker('ROUND18_H5', [MATH_SRC])
  const marked = h5.files.length > 0
  // 按引号切分再数中文，避免引号配对错位漏数（同 round17 v1.1 口径）
  const zh = new Set()
  for (const frag of h5.blob.split(/['"“”]/)) {
    const t = frag.trim()
    if (t.length >= 10 && (t.match(/[\u3400-\u9fff]/g) || []).length >= 8) zh.add(t)
  }
  const ok = marked && masters >= 80 && zh.size >= 200
  check(
    'H5',
    ok,
    `H5 精品剖析 ${masters} ≥ 80（去重中文讲解句 ${zh.size} ≥ 200，可执行标记 ×${h5.files.length}）`,
    `H5 精品剖析不足（可执行标记=${marked}，母题=${masters}(需≥80，空壳不计)，中文讲解句=${zh.size}(需≥200)）`
  )
}

/* H6 走查证据包（截图/录屏必须真实落盘 ≥4 个且每个 ≥200B；
   富玩/拆包/剖析对齐/周报或学伴 四类场景词齐；只列路径不落盘不算） */
{
  const doc = read('.agent_workspace/evidence/r18/walkthrough.md')
  const refs = [
    ...new Set(
      [...doc.matchAll(/evidence\/r18\/[^\s)'"`]+\.(?:png|jpe?g|webp|gif|mp4|webm)/gi)].map(
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
    '富玩|富脚本|rich',
    '拆包|懒加载|分片|chunk|codesplit',
    '剖析|对齐|analysis',
    '周报|weekly|学伴|mascot'
  ].filter((kw) => new RegExp(kw, 'i').test(doc)).length
  check(
    'H6',
    doc.length > 400 && scenes >= 4 && fileHits >= 4,
    `H6 走查证据包就位（引用 ${refs.length}，落盘 ${fileHits} ≥ 4，场景 ${scenes}/4）`,
    `H6 走查证据不足（doc=${doc.length}，引用=${refs.length}，落盘=${fileHits}(需≥4)，场景=${scenes}(需4)）`
  )
}

/* H7 真机或模拟闭环 / 诚实 BLOCKED 台账（必须是 r18 自己的台账；
   只继承 r13/r17 旧 report 不算） */
{
  const sim =
    read('.agent_workspace/evidence/r18/android-sim-report.md') +
    read('.agent_workspace/evidence/r18/android-sim/report.json')
  const blocked = read('.agent_workspace/evidence/r18/device-blocked.md')
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
    'H7 r18 真机/模拟闭环或诚实 BLOCKED 台账就位',
    'H7 缺 r18 台账：需 evidence/r18/android-sim-report.md（可引用重跑的 report.json）或 device-blocked.md（BLOCKED+复现命令）；仅继承 r13/r17 旧报告不算'
  )
}

/* H8 往轮不退化：check:round17 8/8（v1.1） */
{
  const r17 = spawnSync(process.execPath, ['scripts/check-round17.mjs', '--json'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 300000
  })
  let passed = 0
  let total = 8
  try {
    const j = JSON.parse(r17.stdout || '{}')
    const list = Array.isArray(j.results) ? j.results : []
    passed = list.filter((r) => r.status === 'pass').length
    total = j.total || list.length || 8
  } catch {
    const m = (r17.stdout || '').match(/(\d+)\s*\/\s*(\d+)/)
    if (m) {
      passed = Number(m[1])
      total = Number(m[2])
    }
  }
  check(
    'H8',
    passed >= 8 && total >= 8,
    `H8 check:round17 ${passed}/${total}`,
    `H8 check:round17 ${passed}/${total}（需 8/8；干净环境先 npm run android:sim 重建双 APK）`
  )
}

const passed = results.filter((r) => r.status === 'pass').length
const summary = { round: 18, probe: 'ROUND18-v1.0', passed, total: EXPECTED, results }
if (asJson) console.log(JSON.stringify(summary, null, 2))
else {
  console.log(`\nRound 18 check (ROUND18-v1.0): ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
  console.log('')
}
process.exitCode = passed === EXPECTED ? 0 : 1
