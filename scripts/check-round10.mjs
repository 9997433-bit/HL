/**
 * Round 10 洪恩深度对标硬门槛（v1.0 基线版）。
 * 标准：.agent_workspace/ROUND10-BRIEF.md（#3 子代理交付 ROUND10-ACCEPTANCE 后升 v1.1）
 *
 * 基线（R9 闭合、R10 功能未合入）预期 1/8（仅 H8 绿）。
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
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
const readStripped = (rel) => stripComments(read(rel))

const literacySmoke = readStripped('apps/literacy-app/scripts/smoke.mjs')
const mathSmoke = readStripped('apps/math-app/scripts/smoke.mjs')

/* H1 跟读 v3：离线 ASR Worker 接线 + ROUND10_H1 标记 */
{
  const speech = readStripped('apps/literacy-app/src/composables/useSpeechEval.js') +
    readStripped('apps/literacy-app/src/utils/speechEval.js')
  const wired = /Worker|sherpa|offline.*ASR|ROUND10_H1/i.test(speech)
  const smoke = /\bROUND10_H1(_SMOKE)?\b/.test(literacySmoke)
  check(
    'H1',
    wired && smoke,
    'H1 跟读 v3 离线 ASR 已接线 + smoke',
    `H1 跟读 v3 未闭环：worker=${wired}，smoke=${smoke} —— r10-literacy-followread-v3`
  )
}

/* H2 OCR 真样张：≥2 张 real 命名 + ROUND10_H2 */
{
  const dir = path.join(root, 'apps/literacy-app/scripts/fixtures/ocr')
  const real = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((f) => /real|photo|capture/i.test(f) && f.endsWith('.png')).length
    : 0
  const acc = readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs')
  const marked = /\bROUND10_H2\b/.test(acc)
  check(
    'H2',
    real >= 2 && marked,
    `H2 OCR 真样张 ${real} 张 + ROUND10_H2`,
    `H2 OCR 真样张未闭环：real=${real}/2，ROUND10_H2=${marked} —— r10-literacy-ocr-real`
  )
}

/* H3 推荐闭环：daily/wrongBook 跳转 + ROUND10_H3_SMOKE */
{
  const src =
    readStripped('apps/math-app/src/data/daily.js') +
    readStripped('apps/math-app/src/modules/skill-graph/SkillGraphView.vue') +
    readStripped('apps/math-app/src/data/skill-graph.js')
  const wired = /recommend|推荐/.test(src) && /daily|wrongBook|错题|日冒险/i.test(src)
  const smoke = /\bROUND10_H3_SMOKE\b/.test(mathSmoke)
  check(
    'H3',
    wired && smoke,
    'H3 图谱推荐 × 日冒险/错题本闭环 + smoke',
    `H3 推荐闭环未接线：wired=${wired}，smoke=${smoke} —— r10-math-reco-daily`
  )
}

/* H4 投稿 CI：import 脚本 + ajv */
{
  const script = exists('scripts/import-book-submission.mjs')
  const pkg = read('package.json')
  const ajv = /import-book-submission|ajv/i.test(pkg + read('apps/literacy-app/package.json'))
  check(
    'H4',
    script && ajv,
    'H4 绘本投稿 import 脚本 + ajv 已挂链',
    `H4 投稿 CI 未闭环：script=${script}，ajv=${ajv} —— r10-book-import-ci`
  )
}

/* H5 儿歌旋律：≥3 首真实音频 + ROUND10_H5 */
{
  let withAudio = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    const list = mod.SONGS ?? mod.default ?? []
    if (Array.isArray(list)) {
      withAudio = list.filter(
        (s) => s && (s.audio || s.src || s.melodyUrl) && /\.(mp3|ogg|wav|m4a)/i.test(String(s.audio || s.src || s.melodyUrl))
      ).length
    }
  } catch {
    withAudio = 0
  }
  const marked = /\bROUND10_H5\b/.test(
    readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke
  )
  check(
    'H5',
    withAudio >= 3 && marked,
    `H5 儿歌真实旋律 ${withAudio} 首 + ROUND10_H5`,
    `H5 儿歌旋律未闭环：audio=${withAudio}/3，ROUND10_H5=${marked} —— r10-literacy-songs-melody`
  )
}

/* H6 双档 Perf：evidence/r10 desktop JSON + 设备清单非空模板 */
{
  let desktopJson = 0
  if (exists('.agent_workspace/evidence/r10')) {
    for (const f of fs.readdirSync(path.join(root, '.agent_workspace/evidence/r10'))) {
      if (f.includes('desktop') && f.endsWith('.json')) desktopJson++
    }
  }
  const checklist = read('.agent_workspace/ANDROID-DEVICE-CHECKLIST.md')
  const filled = checklist.length > 500 && !/\[待填\]/.test(checklist.slice(0, 2000))
  check(
    'H6',
    desktopJson >= 1 && filled,
    `H6 桌面 LH 证据 ${desktopJson} 份 + 真机清单已回填`,
    `H6 双档 Perf 未闭环：desktop=${desktopJson}/1，checklist=${filled} —— r10-perf-device-desktop`
  )
}

/* H7 发布就绪：LICENSE + privacy 路由 + 版本统一 */
{
  const license = exists('LICENSE')
  const router = readStripped('apps/literacy-app/src/router/index.js')
  const privacy = /privacy|隐私/.test(router)
  const rootPkg = JSON.parse(read('package.json') || '{}')
  const litPkg = JSON.parse(read('apps/literacy-app/package.json') || '{}')
  const verOk = rootPkg.version === '1.0.0' && litPkg.version === rootPkg.version
  check(
    'H7',
    license && privacy && verOk,
    'H7 LICENSE + 隐私页 + 版本 1.0.0 统一',
    `H7 发布未就绪：LICENSE=${license}，privacy=${privacy}，ver=${verOk} —— r10-global-release`
  )
}

/* H8 R9 不退化 */
{
  const r9 = spawnSync(process.execPath, ['scripts/check-round9.mjs'], { cwd: root, encoding: 'utf8' })
  const ok = r9.status === 0 && /8\/8/.test(r9.stdout + r9.stderr)
  check('H8', ok, 'H8 Round 9 门禁 8/8 无退化', `H8 Round 9 退化 exit=${r9.status}`)
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}`
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
  console.log('说明：R10 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
}

process.exit(fails.length ? 1 : 0)
