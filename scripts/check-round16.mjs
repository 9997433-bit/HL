/**
 * Round 16 · 体验密度反超硬门槛（v1.0）。
 * 标准：.agent_workspace/ROUND16-ACCEPTANCE.md
 * `--json` 机读汇总。启动时（功能未合入）预期多数红；H8 依赖 round15 应绿。
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

const charDetail = strip(read('apps/literacy-app/src/views/CharDetailView.vue'))

/* H1 */
{
  const audit = read('.agent_workspace/round16-hongen-gap-audit.md')
  const ok =
    audit.length > 800 &&
    /识字|literacy/i.test(audit) &&
    /数学|math/i.test(audit) &&
    (/✅|◐|❌/.test(audit) || /达标|缺口/.test(audit))
  check('H1', ok, 'H1 双 App 洪恩体验总表就位', 'H1 缺少 round16-hongen-gap-audit.md 或内容过薄')
}

/* H2 */
{
  const marked =
    /ROUND16_H2/.test(charDetail) ||
    /ROUND16_H2/.test(read('apps/literacy-app/src/components/IntroFallbackStage.vue')) ||
    /ROUND16_H2/.test(read('apps/literacy-app/src/components/CharIntroStage.vue'))
  const wired =
    (/phase === ['"]intro['"]/.test(charDetail) || /认/.test(charDetail)) &&
    (/IntroFallback|CharIntroStage|noEty|hasOrigin[\s\S]{0,400}else/.test(charDetail) ||
      /!hasOrigin[\s\S]{0,300}(Stage|动画|radical)/.test(charDetail))
  check(
    'H2',
    marked && wired,
    'H2 无字源认步默认动画已接线',
    'H2 无字源认步仍可能空白（缺 ROUND16_H2 或回退舞台）'
  )
}

/* H3 */
{
  let rich = 0
  try {
    const mod = await import(path.join(root, 'apps/literacy-app/src/data/char-play.js'))
    if (typeof mod.countRichPlays === 'function') rich = mod.countRichPlays()
    else if (Array.isArray(mod.RICH_PLAY)) rich = mod.RICH_PLAY.length
    else if (Array.isArray(mod.CHAR_PLAY_RICH)) rich = mod.CHAR_PLAY_RICH.length
  } catch {
    /* ignore */
  }
  const seedLines = read('apps/literacy-app/scripts/data/char-play-seed.txt')
    .split('\n')
    .filter((l) => l.trim() && !l.trim().startsWith('#')).length
  rich = Math.max(rich, seedLines >= 500 ? seedLines : rich)
  check('H3', rich >= 500, `H3 富 Play ${rich} ≥ 500`, `H3 富 Play ${rich} < 500`)
}

/* H4 */
{
  const demoFiles = [
    'apps/math-app/src/components/LearnDemo.vue',
    'apps/math-app/src/components/SkillLearnDemo.vue',
    'apps/math-app/src/modules/visual-demos',
    'apps/math-app/src/data/learn-demos.js',
    'apps/math-app/src/data/skill-learn-demos.js'
  ]
  let hit = demoFiles.some((rel) => exists(rel))
  let count = 0
  const blob =
    read('apps/math-app/src/data/learn-demos.js') +
    read('apps/math-app/src/data/skill-learn-demos.js') +
    read('apps/math-app/src/modules/visual-demos/index.js')
  const m = blob.match(/ROUND16_H4/g)
  if (m) hit = true
  const ids = blob.match(/skillId\s*:/g) || blob.match(/id:\s*['"][^'"]+['"]/g)
  if (ids) count = ids.length
  // also count markdown registry
  const reg = read('.agent_workspace/evidence/r16/learn-demo-registry.md')
  const regCount = (reg.match(/^- \S+/gm) || []).length
  count = Math.max(count, regCount)
  check(
    'H4',
    hit && count >= 12,
    `H4 数学学演示 ${count} ≥ 12`,
    `H4 数学学演示不足（hit=${hit}, count=${count}）`
  )
}

/* H5 */
{
  const wp =
    read('apps/math-app/src/modules/word-problems') +
    read('apps/math-app/src/components/WpAnalysisPanel.vue') +
    read('apps/math-app/src/components/WordProblemAnalysis.vue')
  const ok =
    /ROUND16_H5/.test(wp) ||
    (/剖析|analysis|分步/.test(wp) && /变式|variant|hint/.test(wp) && exists('apps/math-app/src/components/WpAnalysisPanel.vue')) ||
    (/ROUND16_H5/.test(read('apps/math-app/src/modules/word-problems/WordProblemsView.vue')) &&
      /剖析|Analysis/.test(read('apps/math-app/src/modules/word-problems/WordProblemsView.vue')))
  check('H5', ok, 'H5 应用题剖析壳就位', 'H5 缺少应用题剖析壳（ROUND16_H5）')
}

/* H6 */
{
  const lines =
    read('apps/literacy-app/src/data/mascotLines.js') +
    read('apps/math-app/src/data/mascotLines.js') +
    read('apps/literacy-app/src/composables/useMascotCoach.js')
  const arrMatches = lines.match(/['"][^'"]{8,}['"]/g) || []
  const marked = /ROUND16_H6/.test(lines)
  const enough = arrMatches.length >= 40 || (lines.match(/:/g) || []).length >= 40
  check(
    'H6',
    marked && enough,
    `H6 学伴人格台词充足（标记=${marked}）`,
    'H6 学伴人格台词不足或缺 ROUND16_H6'
  )
}

/* H7 */
{
  const parent =
    read('apps/literacy-app/src/views/ParentView.vue') +
    read('apps/math-app/src/modules/parent') +
    read('apps/literacy-app/src/composables/useWeeklyReport.js') +
    read('apps/math-app/src/composables/useWeeklyReport.js') +
    read('apps/literacy-app/src/utils/weeklyReport.js') +
    read('apps/math-app/src/utils/weeklyReport.js')
  const ok =
    /ROUND16_H7/.test(parent) ||
    (/弱项|本周|建议/.test(parent) && /周报|weekly|WeeklyReport/.test(parent))
  check('H7', ok, 'H7 家长可解释周报就位', 'H7 缺少家长弱项一句话+建议练习周报')
}

/* H8 */
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
    `H8 check:round15 ${passed}/${total}（需要 8/8）`
  )
}

const passed = results.filter((r) => r.status === 'pass').length
const summary = { round: 16, probe: 'ROUND16-v1.0', passed, total: EXPECTED, results }
if (asJson) console.log(JSON.stringify(summary, null, 2))
else {
  console.log(`\nRound 16 check (ROUND16-v1.0): ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
  if (passed < EXPECTED) process.exitCode = 1
}
