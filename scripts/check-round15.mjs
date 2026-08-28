/**
 * Round 15 · 一字一动画硬门槛探针（PROBE ROUND15-v1.1）。
 * 标准：.agent_workspace/ROUND15-ACCEPTANCE.md（v1.1 细则，与本探针一一对应）
 *
 * v1.1 相对 v1.0 的堵漏（误绿/漏检）：
 *  - H1 解析 PHASES 的 id 顺序（play 必须第 0 位，play→intro→listen→trace→quiz/speak），
 *    并要求默认 phase 从 play 起 + play 步真的挂 Play 舞台组件；堵「只改 label 不接舞台」。
 *  - H2 play 模块与 characters.js 分开导入、分开诊断，无关模块失败不再笼统报
 *    「加载失败」误导归因；有效 play 需 template 与 narration 双非空；报缺字样本。
 *  - H3 只计 templateFallback !== true 的条目、按 char 去重；narration 去重 ≥160
 *    防同一句话复制 200 份；不再信任 countRichPlays 等自报数字；全库 0 条打标
 *    且富计数 >400 视为「管道未打标」可疑，运行时计数作废退回源文件计数；
 *    纯 txt 字表（无 narration）不再能单独过线。
 *  - H4 需「EtymologyStage 挂载条件含 intro/phase」或「ROUND15_H4 标记 + 自动展开
 *    赋值信号」；堵 v1.0 里 /认[\s\S]{0,800}EtymologyStage/ 之类的偶然命中。
 *  - H5 gen 脚本需非平凡（去注释 >400 字符）+ 写盘信号 + 数据侧确有 templateFallback 打标。
 *  - H7 需断言信号（problems/process.exit/throw）+ play 全库覆盖 + reduced-motion 覆盖。
 *  - H8 沿用回归门禁岗的必绿项口径：round13 的 H1–H6 与 H8 逐项保持绿，
 *    仅 H7 可因外部 Play Console 账号红；不看总分，防 H7 翻绿掩盖其他退化。
 *
 * 标记约定：ROUND15_Hx 必须出现在可执行代码（标识符/字符串常量）里；
 * 探针会剥掉注释再匹配，写在注释里等于没写。
 *
 * 环境口径：round13 的 H6 校验不入库的双 APK 产物，干净检出下 H8 必红——
 * 属环境红不降门槛，先 `npm run android:sim` 重建产物再复测（ACCEPTANCE §H8）。
 * `--json` 输出机读汇总（含 probeVersion）。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

register('./alias-loader.mjs', import.meta.url)

const PROBE_VERSION = 'ROUND15-v1.1'

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
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const charDetail = stripComments(read('apps/literacy-app/src/views/CharDetailView.vue'))
const literacySmoke = stripComments(read('apps/literacy-app/scripts/smoke.mjs'))

/* ---- 共享运行时装载：play 模块与 characters 分开诊断（v1.1 H2 修订核心） ---- */
const PLAY_MODULE_CANDIDATES = [
  'apps/literacy-app/src/data/char-play.js',
  'apps/literacy-app/src/data/char-play/index.js',
  'apps/literacy-app/src/data/char-play-index.js',
  'apps/literacy-app/src/data/charPlay.js',
  'apps/literacy-app/src/data/play-index.js',
  'apps/literacy-app/src/play/char-play.js',
  'apps/literacy-app/src/utils/charPlay.js'
]
const runtime = {
  getCharPlay: null,
  playModulePath: '',
  playErr: '',
  chars: [],
  charsErr: '',
  /** [{ char, play, threw }]，与 chars 一一对应；仅在引擎+数据都就绪时填充 */
  resolved: []
}
{
  try {
    const charsMod = await import(path.join(root, 'apps/literacy-app/src/data/characters.js'))
    runtime.chars = charsMod.CHARACTERS || []
    if (!runtime.chars.length) runtime.charsErr = 'CHARACTERS 为空数组'
  } catch (e) {
    runtime.charsErr = e.message
  }
  for (const rel of PLAY_MODULE_CANDIDATES) {
    if (!exists(rel)) continue
    try {
      const mod = await import(path.join(root, rel))
      // ROUND18_H3 拆包后剧本按单元懒加载，启动时注册表是空的（架构契约 §2.7 主案）
      if (typeof mod.loadAllRichPlays === 'function') await mod.loadAllRichPlays()
      const fn = mod.getCharPlay || mod.default?.getCharPlay
      if (typeof fn === 'function') {
        runtime.getCharPlay = fn
        runtime.playModulePath = rel
        runtime.playErr = ''
        break
      }
      runtime.playErr = `${rel} 存在但未导出 getCharPlay 函数`
    } catch (e) {
      // 记录但继续尝试其余候选；报错必须归因到 play 模块自身依赖，
      // 不得因 characters.js 等无关模块失败而笼统甩锅。
      runtime.playErr = `${rel} 导入失败：${e.message}`
    }
  }
  if (runtime.getCharPlay && runtime.chars.length) {
    for (const c of runtime.chars) {
      let play = null
      let threw = false
      try {
        play = runtime.getCharPlay(c.char)
      } catch {
        threw = true
      }
      runtime.resolved.push({ char: c.char, play, threw })
    }
  }
}
/** 有效 play：对象 + template/narration 双非空字符串（契约见 ACCEPTANCE §H2） */
const validPlay = (p) =>
  Boolean(
    p &&
      typeof p === 'object' &&
      typeof p.template === 'string' &&
      p.template.trim() &&
      typeof p.narration === 'string' &&
      p.narration.trim()
  )

/* ---- H1 五步对齐：id 顺序 + 默认从玩起 + play 舞台真挂载 ---- */
{
  // PHASES 允许抽到 composable / data 文件，但必须仍叫 PHASES 且被 CharDetailView 用到
  const phasesSource =
    charDetail +
    stripComments(read('apps/literacy-app/src/composables/useCharPhases.js')) +
    stripComments(read('apps/literacy-app/src/data/char-phases.js'))
  const block = (phasesSource.match(/PHASES\s*=\s*\[([\s\S]*?)\n\]/) || [])[1] || ''
  const ids = [...block.matchAll(/\bid:\s*['"]([\w-]+)['"]/g)].map((m) => m[1])
  const at = (names) => ids.findIndex((x) => names.includes(x))
  const iPlay = at(['play'])
  const iIntro = at(['intro'])
  const iListen = at(['listen'])
  const iTrace = at(['trace'])
  const iSpeak = at(['speak', 'quiz'])
  const orderOk =
    iPlay === 0 && iIntro > iPlay && iListen > iIntro && iTrace > iListen && iSpeak > iTrace
  const defaultPlay =
    /phase\s*=\s*ref\(\s*['"]play['"]\s*\)/.test(charDetail) ||
    /phase\s*=\s*ref\(\s*PHASE_IDS\[0\]\s*\)/.test(charDetail) ||
    /ROUND15_H1/.test(charDetail)
  const stageWired =
    /phase === ['"]play['"]/.test(charDetail) &&
    /<(Char)?Play(Stage|Scene|Ground)\b/.test(charDetail)
  check(
    'H1',
    orderOk && defaultPlay && stageWired,
    'H1 五步 play→intro→listen→trace→说，默认从玩起且 play 舞台已挂载',
    `H1 五步未对齐：order=${orderOk}（ids=[${ids.join(',')}]），default=${defaultPlay}，stage=${stageWired}`
  )
}

/* ---- H2 Play 引擎 + 全库 resolve（template+narration 双非空） ---- */
{
  const engineHit =
    exists('apps/literacy-app/src/components/CharPlayStage.vue') ||
    exists('apps/literacy-app/src/components/PlayStage.vue') ||
    /CharPlayStage|getCharPlay/.test(charDetail)
  let coverageOk = false
  let coverMsg
  if (!runtime.getCharPlay) {
    coverMsg = `H2 play 模块未就绪：${runtime.playErr || `候选路径均不存在（${PLAY_MODULE_CANDIDATES[0]} 等）`}`
  } else if (!runtime.chars.length) {
    coverMsg = `H2 characters.js 加载失败（与 play 引擎无关，勿据此改引擎）：${runtime.charsErr}`
  } else if (runtime.chars.length < 1800) {
    coverMsg = `H2 CHARACTERS 仅 ${runtime.chars.length} 条（<1800），全库口径不成立`
  } else {
    const bad = runtime.resolved.filter((r) => r.threw || !validPlay(r.play))
    coverageOk = bad.length === 0
    const sample = bad
      .slice(0, 5)
      .map((r) => (r.threw ? `${r.char}(throw)` : r.char))
      .join(' ')
    coverMsg = coverageOk
      ? `H2 getCharPlay 全库 ${runtime.resolved.length}/${runtime.chars.length} template+narration 有效（${runtime.playModulePath}）`
      : `H2 无效/缺失 ${bad.length}/${runtime.chars.length}（样本：${sample}）`
  }
  if (!engineHit && coverageOk) coverMsg = 'H2 数据齐但缺 CharPlayStage 舞台组件'
  check('H2', engineHit && coverageOk, coverMsg, coverMsg)
}

/* ---- H3 富脚本 ≥200（templateFallback!==true，按 char 去重，narration 去重防复制） ---- */
{
  const measures = [] // { rich, distinct, src }
  // 运行时口径（首选）：直接数全库里没打 fallback 标的有效 play
  if (runtime.resolved.length) {
    const richNarr = new Map()
    let fallbackCount = 0
    for (const r of runtime.resolved) {
      if (!validPlay(r.play)) continue
      if (r.play.templateFallback === true) {
        fallbackCount += 1
      } else if (!richNarr.has(r.char)) {
        richNarr.set(r.char, r.play.narration.trim())
      }
    }
    const rich = richNarr.size
    const suspicious = fallbackCount === 0 && rich > 400
    if (suspicious) {
      measures.push({ rich: 0, distinct: 0, src: `runtime(可疑：0 条 templateFallback:true 却富 ${rich}，视为管道未打标)` })
    } else {
      measures.push({
        rich,
        distinct: new Set(richNarr.values()).size,
        src: `runtime(${runtime.playModulePath}，fallback=${fallbackCount})`
      })
    }
  }
  // 源文件口径（兜底）：富脚本源须结构化且含 narration；纯字表 txt 不再单独计入
  for (const rel of [
    'apps/literacy-app/src/data/char-play-rich.js',
    'apps/literacy-app/src/data/char-play-catalog.js',
    'apps/literacy-app/scripts/data/char-play-rich.json'
  ]) {
    const body = read(rel)
    if (!body) continue
    if (rel.endsWith('.json')) {
      try {
        const j = JSON.parse(body)
        const list = Array.isArray(j) ? j : Object.values(j)
        const chars = new Set()
        const narrs = new Set()
        for (const it of list) {
          if (!it || typeof it !== 'object') continue
          if (it.templateFallback === true) continue
          if (typeof it.narration !== 'string' || !it.narration.trim()) continue
          chars.add(it.char ?? chars.size)
          narrs.add(it.narration.trim())
        }
        measures.push({ rich: chars.size, distinct: narrs.size, src: rel })
      } catch {
        /* 非法 JSON 不计 */
      }
    } else {
      const src = stripComments(body)
      const chars = new Set([...src.matchAll(/\bchar\s*:\s*['"]([^'"]+)['"]/g)].map((m) => m[1]))
      const narrs = new Set(
        [...src.matchAll(/\bnarration\s*:\s*['"]([^'"]+)['"]/g)].map((m) => m[1].trim())
      )
      const fallbackTrue = (src.match(/templateFallback\s*:\s*true/g) || []).length
      measures.push({
        rich: Math.max(0, chars.size - fallbackTrue),
        distinct: narrs.size,
        src: rel
      })
    }
  }
  const best = measures.sort((a, b) => b.rich - a.rich)[0] || { rich: 0, distinct: 0, src: '无来源' }
  const ok = best.rich >= 200 && best.distinct >= 160
  check(
    'H3',
    ok,
    `H3 富 play 脚本 ${best.rich} ≥ 200，narration 去重 ${best.distinct} ≥ 160（${best.src}）`,
    `H3 富脚本不足：rich=${best.rich}(需≥200)，narration去重=${best.distinct}(需≥160)（${best.src}）`
  )
}

/* ---- H4 认步字源默认播：intro 门控挂载 或 标记+自动展开信号 ---- */
{
  const etyRef = /EtymologyStage/.test(charDetail)
  // 结构证据：某个 <EtymologyStage 的近旁（前 400 字符）挂载条件里出现 intro/phase
  let introGated = false
  let from = 0
  while (true) {
    const i = charDetail.indexOf('<EtymologyStage', from)
    if (i === -1) break
    const ctx = charDetail.slice(Math.max(0, i - 400), i + 200)
    if (/(v-if|v-show)="[^"]*(intro|phase)[^"]*"/.test(ctx) && /intro/.test(ctx)) {
      introGated = true
      break
    }
    from = i + 1
  }
  // 标记证据：ROUND15_H4 出现在可执行代码 + 自动展开赋值信号（非仅按钮 toggle）
  const markerRoute =
    /ROUND15_H4/.test(charDetail) &&
    /originOpen\.value\s*=\s*true|autoOrigin|autoPlayOrigin|:autoplay|auto-play|\bautoplay\b/.test(
      charDetail
    )
  check(
    'H4',
    etyRef && (introGated || markerRoute),
    'H4 认步默认挂载/播放字源舞台（intro 门控或 ROUND15_H4+自动展开）',
    `H4 认步仍把字源藏在可选按钮后：ety=${etyRef}，introGated=${introGated}，marker=${markerRoute}`
  )
}

/* ---- H5 自动补齐管道：非平凡 gen 脚本 + 写盘信号 + 数据侧真打标 ---- */
{
  const genRel = ['apps/literacy-app/scripts/gen-char-play.mjs', 'apps/literacy-app/scripts/gen-play.mjs'].find(
    exists
  )
  const genBody = genRel ? stripComments(read(genRel)) : ''
  // templateFallback 打标可以落在 gen 脚本里，也可以落在它委托的数据层
  //（如 char-play-templates.js）；打标是否真实生效由 dataFlagged 用运行时/源码兜底。
  const genOk =
    genBody.length > 400 && /writeFileSync|writeFile|createWriteStream/.test(genBody)
  const dataFlagged =
    runtime.resolved.some((r) => r.play?.templateFallback === true) ||
    [
      ...PLAY_MODULE_CANDIDATES,
      'apps/literacy-app/src/data/char-play-templates.js',
      'apps/literacy-app/src/data/char-play-generated.js'
    ].some((rel) => /templateFallback/.test(stripComments(read(rel))))
  check(
    'H5',
    Boolean(genRel) && genOk && dataFlagged,
    `H5 自动补齐管道就位（${genRel}，fallback 条目已打标）`,
    `H5 补齐管道未闭环：gen=${genRel || '缺'}，genOk=${genOk}，数据打标=${dataFlagged}`
  )
}

/* ---- H6 写步引导：显式「示范→描红」编排，仅手动按钮不算 ---- */
{
  const explicit =
    /ROUND15_H6/.test(charDetail) ||
    (/phase === ['"]trace['"]/.test(charDetail) &&
      /guideThenQuiz|demoBeforeQuiz|writeGuide|onEnterTrace|enterTrace/.test(charDetail)) ||
    (exists('apps/literacy-app/src/composables/useWriteGuide.js') &&
      /useWriteGuide/.test(charDetail))
  check('H6', explicit, 'H6 写步含引导示范再描红', 'H6 写步未见引导示范编排（需 ROUND15_H6 / enterTrace 类编排 / useWriteGuide 接线）')
}

/* ---- H7 smoke：play 全库覆盖 + 断言信号 + reduced-motion ---- */
{
  const assertSig = /problems|process\.exit\(1\)|throw new Error/.test(literacySmoke)
  const playCover =
    /getCharPlay/.test(literacySmoke) && /CHARACTERS|1820|全库/.test(literacySmoke)
  const markerRoute = /ROUND15_H7/.test(literacySmoke) && assertSig
  // reduced-motion 覆盖：smoke 或 literacy 的 test/spec 文件里必须出现
  let rmSig = /reduced?[-_]?motion|reduceMotion/i.test(literacySmoke)
  if (!rmSig) {
    const stack = [path.join(root, 'apps/literacy-app')]
    while (stack.length && !rmSig) {
      const dir = stack.pop()
      let entries = []
      try {
        entries = fs.readdirSync(dir, { withFileTypes: true })
      } catch {
        continue
      }
      for (const ent of entries) {
        if (ent.name === 'node_modules' || ent.name === 'dist' || ent.name.startsWith('.')) continue
        const p = path.join(dir, ent.name)
        if (ent.isDirectory()) stack.push(p)
        else if (/\.(test|spec)\.(mjs|js|ts)$/.test(ent.name)) {
          try {
            if (/reduced?[-_]?motion|reduceMotion/i.test(fs.readFileSync(p, 'utf8'))) {
              rmSig = true
              break
            }
          } catch {
            /* ignore */
          }
        }
      }
    }
  }
  check(
    'H7',
    (markerRoute || (playCover && assertSig)) && rmSig,
    'H7 literacy smoke 覆盖 play 全库 + reduced-motion，且有断言',
    `H7 smoke 覆盖不足：play=${playCover || markerRoute}，assert=${assertSig}，reducedMotion=${rmSig}`
  )
}

/*
 * ---- H8 往轮 ----
 * R13 的批准基线是 7/8：H1–H6 与 H8 必须保持绿，仅 H7 可因外部 Play
 * Console 账号继续红。不能只看总分，否则 H7 翻绿会掩盖其他必绿项退化。
 * H6 依赖不入库的双 APK；干净环境须先跑 npm run android:sim，缺产物不降门槛。
 */
{
  const r13 = spawnSync(process.execPath, ['scripts/check-round13.mjs', '--json'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 120000
  })
  const requiredIds = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H8']
  let pass = 0
  let requiredFailures = [...requiredIds]
  let parseError = ''
  try {
    const j = JSON.parse(r13.stdout || '{}')
    const priorResults = Array.isArray(j.results) ? j.results : []
    pass = priorResults.filter((result) => result.status === 'pass').length
    const byId = new Map(priorResults.map((result) => [result.id, result.status]))
    requiredFailures = requiredIds.filter((id) => byId.get(id) !== 'pass')
    if (priorResults.length !== 8) parseError = `结果数 ${priorResults.length}/8`
  } catch (error) {
    parseError = `JSON 解析失败：${error.message}`
  }
  const failureDetail = parseError || requiredFailures.join(', ') || '未知'
  const h6Hint = requiredFailures.includes('H6')
    ? '；H6 在干净环境需先 npm run android:sim 重建双 APK'
    : ''
  check(
    'H8',
    !parseError && requiredFailures.length === 0,
    `H8 check:round13 ${pass}/8；H1–H6/H8 保持绿（仅 H7 可因 Play 账号阻断）`,
    `H8 check:round13 ${pass}/8；必绿项失败：${failureDetail}（仅 H7 可红）${h6Hint}`
  )
}

/* ---- report ---- */
const passed = results.filter((r) => r.status === 'pass').length
const summary = {
  round: 15,
  probeVersion: PROBE_VERSION,
  passed,
  total: EXPECTED,
  results
}

if (asJson) {
  console.log(JSON.stringify(summary, null, 2))
} else {
  console.log(`\nRound 15 check (${PROBE_VERSION}): ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
}
if (passed < EXPECTED) process.exitCode = 1
