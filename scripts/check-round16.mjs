/**
 * Round 16 · 体验密度反超硬门槛（v1.1）。
 * 标准：.agent_workspace/ROUND16-ACCEPTANCE.md
 * `--json` 机读汇总。启动时（功能未合入）预期 0–1/8；H8 依赖 round15 应绿
 * （干净环境需先 `npm run android:sim` 重建双 APK，否则 round13 H6 → round15 H8 连锁红）。
 *
 * v1.0 → v1.1 堵住的误绿：
 *  - H2/H4/H5/H6/H7 的 ROUND16_H* 标记改为「剥注释后仍在」——注释里写标记不再算数；
 *  - H3 去掉 char-play-seed.txt 行数抄近路，只认运行时 countRichPlays() + narration 去重；
 *  - H4 不再因目录/文件「存在」记 hit（空目录误绿），全部信号（三态/可跳过/计数）
 *    只从带可执行 ROUND16_H4 的文件里取——旧组件蹭词证、evidence 登记表顶数都不算；
 *  - H5 删除无标记的 OR 分支：必须可执行 ROUND16_H5 + 剖析 + 分步 + 变式词证；
 *  - H6 台词按「去重后的中文串」计数（同一句复制 40 遍只算 1），并要求 ≥3 类阶段场景词
 *    出现在可执行代码里；
 *  - H7 删除无标记的 OR 分支：必须可执行 ROUND16_H7 + 弱项 + 建议 + 周报词证。
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
const readExec = (rel) => strip(read(rel))

/** 递归列出目录下的源码文件（.js/.mjs/.ts/.vue/.json）；目录不存在返回 []。 */
const walk = (rel) => {
  const abs = path.join(root, rel)
  const out = []
  const visit = (dir) => {
    let entries
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      const p = path.join(dir, e.name)
      if (e.isDirectory()) visit(p)
      else if (/\.(js|mjs|ts|vue|json)$/.test(e.name)) out.push(path.relative(root, p))
    }
  }
  visit(abs)
  return out
}

/** 在若干目录里找「剥注释后仍含 marker」的文件，返回 { files, blob }。 */
const scanExecMarker = (marker, dirs) => {
  const files = []
  let blob = ''
  for (const dir of dirs) {
    for (const rel of walk(dir)) {
      const src = readExec(rel)
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

const charDetail = readExec('apps/literacy-app/src/views/CharDetailView.vue')

/* H1 双 App 洪恩体验总表 */
{
  const audit = read('.agent_workspace/round16-hongen-gap-audit.md')
  const ok =
    audit.length > 800 &&
    /识字|literacy/i.test(audit) &&
    /数学|math/i.test(audit) &&
    (/✅|◐|❌/.test(audit) || /达标|缺口/.test(audit))
  check('H1', ok, 'H1 双 App 洪恩体验总表就位', 'H1 缺少 round16-hongen-gap-audit.md 或内容过薄')
}

/* H2 无字源认步默认动画（标记须可执行） */
{
  const h2 = scanExecMarker('ROUND16_H2', [LIT_SRC])
  const marked = h2.files.length > 0
  const stageBlob = charDetail + h2.blob
  const wired =
    (/phase === ['"]intro['"]/.test(stageBlob) || /认/.test(stageBlob)) &&
    (/IntroFallback|CharIntroStage|部首|零件|组词/.test(stageBlob) ||
      /!hasOrigin|noEty|hasEtymology/.test(stageBlob))
  check(
    'H2',
    marked && wired,
    `H2 无字源认步默认动画已接线（可执行标记 ×${h2.files.length}）`,
    'H2 无字源认步仍可能空白（缺可执行 ROUND16_H2 或回退舞台未接 intro）'
  )
}

/* H3 富 Play ≥500（运行时口径 + narration 去重；不认种子 txt 行数） */
{
  let rich = 0
  let distinct = 0
  let src = 'apps/literacy-app/src/data/char-play.js'
  try {
    const mod = await import(path.join(root, src))
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
    src += '（导入失败）'
  }
  const ok = rich >= 500 && distinct >= 400
  check(
    'H3',
    ok,
    `H3 富 Play ${rich} ≥ 500，narration 去重 ${distinct} ≥ 400（${src}）`,
    `H3 富 Play 不足：rich=${rich}(需≥500)，narration去重=${distinct}(需≥400)（${src}）`
  )
}

/* H4 数学「学」演示 ≥12（只认带可执行标记的文件——空目录、纯登记表、旧组件蹭词证都不算） */
{
  const h4 = scanExecMarker('ROUND16_H4', [MATH_SRC])
  const blob = h4.blob
  const marked = h4.files.length > 0
  const threeStage =
    /实物|concrete|实景/.test(blob) && /图形|pictorial|图示|diagram/.test(blob) && /算式|equation|abstract|符号/.test(blob)
  const skippable = /跳过|skip/i.test(blob)
  const ids = new Set(
    [...blob.matchAll(/\b(?:skillId|demoId)\s*:\s*['"]([^'"]+)['"]/g)].map((m) => m[1])
  )
  if (ids.size === 0)
    for (const m of blob.matchAll(/\bid\s*:\s*['"]([^'"]+)['"]/g)) ids.add(m[1])
  const count = ids.size
  const regCount = (read('.agent_workspace/evidence/r16/learn-demo-registry.md').match(/^- \S+/gm) || [])
    .length
  check(
    'H4',
    marked && threeStage && skippable && count >= 12,
    `H4 数学学演示 ${count} ≥ 12（三态+可跳过，登记表参考 ${regCount}）`,
    `H4 数学学演示不足（可执行标记=${marked}，三态=${threeStage}，可跳过=${skippable}，代码计数=${count}，登记表仅参考 ${regCount}）`
  )
}

/* H5 应用题剖析壳（标记须可执行 + 剖析 + 分步 + 变式） */
{
  const h5 = scanExecMarker('ROUND16_H5', [MATH_SRC])
  const marked = h5.files.length > 0
  const blob = h5.blob
  const ok =
    marked && /剖析|analysis/i.test(blob) && /分步|step/i.test(blob) && /变式|variant/i.test(blob)
  check(
    'H5',
    ok,
    `H5 应用题剖析壳就位（可执行标记 ×${h5.files.length}）`,
    'H5 缺应用题剖析壳：需可执行 ROUND16_H5 且含 剖析+分步+变式'
  )
}

/* H6 学伴人格 ≥40 条去重台词（标记须可执行，须覆盖 ≥3 类阶段场景） */
{
  const h6 = scanExecMarker('ROUND16_H6', [LIT_SRC, MATH_SRC])
  const marked = h6.files.length > 0
  const blob = h6.blob
  const quotes = new Set()
  for (const m of blob.matchAll(/['"“]([^'"“”\n]{6,})['"”]/g)) {
    if (/[\u3400-\u9fff]/.test(m[1])) quotes.add(m[1].trim())
  }
  const stages = ['新字|new', '连对|连击|combo|streak', '复习|review', '疲劳|累|fatigue|休息'].filter(
    (kw) => new RegExp(kw).test(blob)
  ).length
  check(
    'H6',
    marked && quotes.size >= 40 && stages >= 3,
    `H6 学伴人格台词 ${quotes.size} ≥ 40（去重，阶段场景 ${stages}/4，标记 ×${h6.files.length}）`,
    `H6 学伴人格不足（可执行标记=${marked}，去重台词=${quotes.size}(需≥40)，阶段场景=${stages}(需≥3)）`
  )
}

/* H7 家长可解释周报（标记须可执行 + 弱项 + 建议 + 周报） */
{
  const h7 = scanExecMarker('ROUND16_H7', [LIT_SRC, MATH_SRC])
  const marked = h7.files.length > 0
  const blob = h7.blob
  const ok =
    marked && /弱项|weak/i.test(blob) && /建议|suggest|recommend/i.test(blob) && /周报|本周|weekly/i.test(blob)
  check(
    'H7',
    ok,
    `H7 家长可解释周报就位（可执行标记 ×${h7.files.length}）`,
    'H7 缺家长周报：需可执行 ROUND16_H7 且含 弱项+建议+周报'
  )
}

/* H8 往轮不退化：check:round15 8/8 */
{
  const r15 = spawnSync(process.execPath, ['scripts/check-round15.mjs', '--json'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 180000
  })
  let passed = 0
  let total = 8
  try {
    const j = JSON.parse(r15.stdout || '{}')
    const list = Array.isArray(j.results) ? j.results : []
    passed = list.filter((r) => r.status === 'pass').length
    total = j.total || list.length || 8
  } catch {
    const m = (r15.stdout || '').match(/(\d+)\s*\/\s*(\d+)/)
    if (m) {
      passed = Number(m[1])
      total = Number(m[2])
    }
  }
  check(
    'H8',
    passed >= 8 && total >= 8,
    `H8 check:round15 ${passed}/${total}`,
    `H8 check:round15 ${passed}/${total}（需 8/8；干净环境先 npm run android:sim 重建双 APK）`
  )
}

const passed = results.filter((r) => r.status === 'pass').length
const summary = { round: 16, probe: 'ROUND16-v1.1', passed, total: EXPECTED, results }
if (asJson) console.log(JSON.stringify(summary, null, 2))
else {
  console.log(`\nRound 16 check (ROUND16-v1.1): ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
  if (passed < EXPECTED) process.exitCode = 1
}
