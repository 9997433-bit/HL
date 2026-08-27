/**
 * Round 9 深度打磨硬门槛。
 * 基线（R9 功能未合入）预期 1/8（仅 H8 绿）。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
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

const literacySmoke = read('apps/literacy-app/scripts/smoke.mjs').replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')

/* H1 儿歌 v2 */
{
  let count = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    const list = mod.SONGS ?? []
    count = Array.isArray(list) ? list.length : 0
  } catch {
    count = 0
  }
  const v2 = /ROUND9_H1|song.*v2|歌词同步/i.test(read('apps/literacy-app/src/views/SongsView.vue') + literacySmoke)
  check(
    'H1',
    count >= 10 && v2,
    `H1 儿歌 v2：${count} 首 + v2 标记/smoke`,
    `H1 儿歌 v2 未闭环：${count}/10 首，v2=${v2 ? '有' : '缺失'} —— r9-literacy-songs`
  )
}

/* H2 OCR 扩样 */
{
  const acc = read('apps/literacy-app/scripts/test-ocr-accuracy.mjs')
  const fixtures = fs.existsSync(path.join(root, 'apps/literacy-app/scripts/fixtures/ocr'))
    ? fs.readdirSync(path.join(root, 'apps/literacy-app/scripts/fixtures/ocr')).filter((f) => f.endsWith('.png'))
    : []
  const handwriting = /handwriting|手写/i.test(acc + fixtures.join(' '))
  check(
    'H2',
    fixtures.length >= 8 && handwriting && /ROUND8_H4|ROUND9_H2/i.test(acc),
    `H2 OCR 扩样 ${fixtures.length} 张含 handwriting tier`,
    `H2 OCR 扩样未闭环：${fixtures.length}/8 张，handwriting=${handwriting} —— r9-literacy-ocr-expand`
  )
}

/* H3 图谱推荐 */
{
  const graphSrc = read('apps/math-app/src/data/skill-graph.js') + read('apps/math-app/src/modules/skill-graph/SkillGraphView.vue')
  const reco = /recommend|nextSkills|推荐|ROUND9_H3/i.test(graphSrc)
  const smoke = /\bROUND9_H3_SMOKE\b/.test(literacySmoke) || /\bROUND9_H3_SMOKE\b/.test(read('apps/math-app/scripts/smoke.mjs'))
  check(
    'H3',
    reco && exists('apps/math-app/src/modules/skill-graph/SkillGraphView.vue') && smoke,
    'H3 技能图谱推荐路径已接线 + smoke',
    `H3 图谱推荐未闭环：reco=${reco}，smoke=${smoke} —— r9-math-graph-reco`
  )
}

/* H4 跟读 ASR 路线 */
{
  const doc = read('.agent_workspace/r9-followread-asr-evaluation.md')
  const src = read('apps/literacy-app/src/composables/useSpeechEval.js') + read('apps/literacy-app/src/utils/speechEval.js')
  const wired = doc.length > 800 || /phonemeMarks|similarityV2|ROUND9_H4/i.test(src)
  check(
    'H4',
    wired,
    'H4 跟读 ASR/音素路线文档或 PoC 已交付',
    'H4 跟读路线未闭环 —— r9-literacy-followread-asr'
  )
}

/* H5 绘本投稿文档 */
{
  const doc = read('.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md')
  check(
    'H5',
    doc.length > 1500 && /投稿|schema|JSON/i.test(doc),
    'H5 绘本社区投稿格式文档已交付',
    'H5 绘本投稿文档缺失 —— r9-content-quality'
  )
}

/* H6 LH CI 锁 */
{
  const ci = read('scripts/lighthouse-ci.mjs') + read('package.json')
  const evidence = exists('.agent_workspace/evidence/r9')
  const jsonCount = evidence
    ? (() => {
        let n = 0
        const walk = (d) => {
          for (const f of fs.readdirSync(d, { withFileTypes: true })) {
            const p = path.join(d, f.name)
            if (f.isDirectory()) walk(p)
            else if (f.name.endsWith('.json')) n++
          }
        }
        walk(path.join(root, '.agent_workspace/evidence/r9'))
        return n
      })()
    : 0
  check(
    'H6',
    /lighthouse-ci|ACCEPTANCE_MIN_LH/i.test(ci) && jsonCount >= 2,
    `H6 Lighthouse CI 锁 + evidence/r9 ${jsonCount} 份 JSON`,
    `H6 Perf CI 未闭环：ci=${/lighthouse-ci/i.test(ci)}，json=${jsonCount}/2 —— r9-perf-ci-device`
  )
}

/* H7 发布清单 */
{
  const report = read('.agent_workspace/GLOBAL-SUMMARY-REPORT.md')
  const rel = read('.agent_workspace/RELEASE-CHECKLIST.md')
  check(
    'H7',
    /Round\s*9/i.test(report) && rel.length > 800 && /LICENSE|发布|证据/i.test(rel),
    'H7 Round 9 报告 + RELEASE-CHECKLIST',
    'H7 发布清单未终验 —— r9-global-release'
  )
}

/* H8 R8 不退化 */
{
  const r8 = spawnSync(process.execPath, ['scripts/check-round8.mjs'], { cwd: root, encoding: 'utf8' })
  const ok = r8.status === 0 && /8\/8/.test(r8.stdout + r8.stderr)
  check('H8', ok, 'H8 Round 8 门禁 8/8 无退化', `H8 Round 8 退化 exit=${r8.status}`)
}

notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\nRound 9 深度门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
if (fails.length) console.log('说明：R9 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
process.exit(fails.length ? 1 : 0)
