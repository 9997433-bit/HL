/**
 * 内容自检，不需要浏览器。
 *
 * 最重要的一条是绘本的用字约束：分级绘本的价值就在于「只用孩子学过的字」，
 * 一旦有人加了一句超纲的话，孩子就会卡住。这条必须自动化守住。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  CHARACTER_MAP,
  TOTAL_CHARACTERS,
  UNITS,
  loadAllCharacters
} from '../src/data/characters.js'
import { BOOKS, charsInBook, verifyBookCoverage } from '../src/data/books.js'
import { IDIOMS } from '../src/data/idioms.js'
import { TOTAL_IDIOMS } from '../src/data/idiom-index.js'
import { RADICALS, getRadical } from '../src/data/radicals.js'
import { ETYMOLOGY, ETYMOLOGY_KINDS } from '../src/data/etymology.js'
import { ETYMOLOGY_CHARS } from '../src/data/etymology-index.js'
import { validateShape } from '../src/utils/etymologySketch.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const baselineFile = path.resolve(here, '..', '..', '..', 'shared', 'data', 'common-hanzi.json')

const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))

/**
 * 字表分成「索引」和「按单元切开的详情包」两层，运行时按需加载。
 * 内容自检要看的是完整语料，所以这里把详情包全拉起来合并一遍——
 * 顺带也就验证了每个单元的详情包都存在、都能解析。
 */
const CHARACTERS = await loadAllCharacters()

/* ----------------------------------------------------------------- 字表 */
check(TOTAL_CHARACTERS >= 500, `字表 ${TOTAL_CHARACTERS} 个字（要求 ≥ 500）`)

const noDetail = CHARACTERS.filter((c) => !c.meaning || !c.words || !c.sentence)
check(
  noDetail.length === 0,
  `每个字都能在单元详情包里找到课文${noDetail.length ? `（缺：${noDetail.map((c) => c.char).join('')}）` : ''}`
)

const strayDetails = []
for (const unit of UNITS) {
  const pack = await import(`../src/data/chars/${unit.id}.js`).then((m) => m.default).catch(() => null)
  if (!pack) continue
  for (const char of Object.keys(pack)) {
    const light = CHARACTER_MAP.get(char)
    if (!light || light.unit !== unit.id) strayDetails.push(`${unit.id}:${char}`)
  }
}
check(
  strayDetails.length === 0,
  `详情包里没有索引之外的字${strayDetails.length ? `（${strayDetails.join('、')}）` : ''}`
)

const dupes = CHARACTERS.map((c) => c.char).filter((c, i, a) => a.indexOf(c) !== i)
check(dupes.length === 0, `字表无重复${dupes.length ? `（重复：${dupes.join('')}）` : ''}`)

const badFields = CHARACTERS.filter(
  (c) => !c.pinyin || !c.meaning || !c.radical || !c.strokes || !c.words?.length || !c.sentence?.text
)
check(badFields.length === 0, `每个字都有拼音/释义/部首/笔画/组词/例句${badFields.length ? `（缺失：${badFields.map((c) => c.char).join('')}）` : ''}`)

const badUnit = CHARACTERS.filter((c) => !UNITS.some((u) => u.id === c.unit))
check(badUnit.length === 0, `每个字都归属到已定义的单元`)

const badRadical = CHARACTERS.filter((c) => !getRadical(c.radical))
check(badRadical.length === 0, `每个字的部首都能查到${badRadical.length ? `（${badRadical.map((c) => `${c.char}:${c.radical}`).join(', ')}）` : ''}`)

// 拼音色标按声调着色，缺声调会退化成灰色；emoji 是卡片上唯一的图形，两者都不能少。
const badTone = CHARACTERS.filter((c) => !(c.tone >= 1 && c.tone <= 5) || !c.emoji)
check(badTone.length === 0, `每个字都有 1–5 的声调和卡片图标${badTone.length ? `（${badTone.map((c) => c.char).join('')}）` : ''}`)

const badWords = CHARACTERS.filter(
  (c) => c.words.length < 2 || c.words.some((w) => !w.w || !w.p) || !c.sentence.p
)
check(badWords.length === 0, `每个字至少 2 个带拼音的组词，例句也有拼音${badWords.length ? `（${badWords.map((c) => c.char).join('')}）` : ''}`)

const thinUnits = UNITS.filter((u) => CHARACTERS.filter((c) => c.unit === u.id).length < 5)
check(thinUnits.length === 0, `每个单元至少 5 个字${thinUnits.length ? `（${thinUnits.map((u) => u.name).join('、')}）` : ''}`)

/* --------------------------------------------------------- 与共享基线对齐
 *
 * shared/data/common-hanzi.json 是 monorepo 里这套字库的事实基线，别的 App
 * 和验收脚本都读它。字表可以在基线之上加教学包装，但不能少字、更不能改拼音，
 * 否则两边一分叉，孩子在不同入口看到的读音就会打架。
 */
const baseline = JSON.parse(fs.readFileSync(baselineFile, 'utf8')).characters ?? []
check(baseline.length >= 500, `共享字库基线 ${baseline.length} 个字（要求 ≥ 500）`)

const missingFromTable = baseline.filter((b) => !CHARACTER_MAP.has(b.character))
check(
  missingFromTable.length === 0,
  `基线里的字都在字表里${missingFromTable.length ? `（缺：${missingFromTable.map((b) => b.character).join('')}）` : ''}`
)

const pinyinDrift = baseline.filter(
  (b) => CHARACTER_MAP.has(b.character) && CHARACTER_MAP.get(b.character).pinyin !== b.pinyin
)
check(
  pinyinDrift.length === 0,
  `字表拼音与基线一致${pinyinDrift.length ? `（${pinyinDrift.map((b) => `${b.character}:${b.pinyin}≠${CHARACTER_MAP.get(b.character).pinyin}`).join('、')}）` : ''}`
)

/* ----------------------------------------------------------------- 绘本 */
check(BOOKS.length >= 5, `绘本 ${BOOKS.length} 本（要求 ≥ 5）`)

const bookDupes = BOOKS.map((b) => b.id).filter((v, i, a) => a.indexOf(v) !== i)
check(bookDupes.length === 0, `绘本 id 无重复${bookDupes.length ? `（${bookDupes.join(',')}）` : ''}`)

const levels = [...new Set(BOOKS.map((b) => b.level))]
check(levels.length >= 3, `绘本覆盖 ${levels.length} 个分级（要求 ≥ 3）`)

const coverage = verifyBookCoverage()
check(
  coverage.length === 0,
  coverage.length
    ? `绘本用字越界：${coverage.map((p) => `《${p.book}》→ ${p.missing.join('')}`).join('；')}`
    : '绘本正文只用了字表内的汉字'
)

for (const b of BOOKS) {
  check(b.pages.length >= 3, `《${b.title}》有 ${b.pages.length} 页`)
  const noPinyin = b.pages.filter((p) => !p.p)
  check(noPinyin.length === 0, `《${b.title}》每页都有拼音`)
}

/* ----------------------------------------------------------------- 成语 */
check(IDIOMS.length >= 60, `成语 ${IDIOMS.length} 个（要求 ≥ 60）`)

const idiomWordDupes = IDIOMS.map((i) => i.word).filter((v, i, a) => a.indexOf(v) !== i)
check(
  idiomWordDupes.length === 0,
  `成语正文无重复${idiomWordDupes.length ? `（${idiomWordDupes.join('、')}）` : ''}`
)

// 逐字拆解卡是按成语正文一格一格摆的，两边对不上就会出现「拆解里没有这个字」。
const charDrift = IDIOMS.filter((i) => (i.chars ?? []).map((c) => c.c).join('') !== i.word)
check(
  charDrift.length === 0,
  `逐字拆解与成语正文逐字对应${charDrift.length ? `（${charDrift.map((i) => i.word).join('、')}）` : ''}`
)

check(
  TOTAL_IDIOMS === IDIOMS.length,
  `首页用的成语总数索引与语料一致（idiom-index=${TOTAL_IDIOMS}，语料=${IDIOMS.length}）`
)

const idiomDupes = IDIOMS.map((i) => i.id).filter((v, i, a) => a.indexOf(v) !== i)
check(idiomDupes.length === 0, `成语 id 无重复${idiomDupes.length ? `（${idiomDupes.join(',')}）` : ''}`)

const idiomName = (i) => i.word ?? i.idiom ?? i.id
const idiomScenes = (i) => i.story ?? i.scenes ?? []

const badIdiom = IDIOMS.filter(
  (i) => !i.pinyin || !i.meaning || !i.lesson || idiomScenes(i).length < 2
)
check(
  badIdiom.length === 0,
  `每个成语都有拼音/释义/寓意和至少 2 段故事${badIdiom.length ? `（${badIdiom.map(idiomName).join('、')}）` : ''}`
)

const badChars = IDIOMS.filter((i) => (i.chars?.length ?? 0) !== 4)
check(badChars.length === 0, `每个成语都做了四字拆解${badChars.length ? `（${badChars.map(idiomName).join('、')}）` : ''}`)

const noQuiz = IDIOMS.filter((i) => !i.quiz)
check(noQuiz.length === 0, `每个成语都配了情景题${noQuiz.length ? `（${noQuiz.map(idiomName).join('、')}）` : ''}`)

const badQuiz = IDIOMS.filter((i) => {
  if (!i.quiz) return false
  const { options, answer } = i.quiz
  return !Array.isArray(options) || !(answer >= 0 && answer < options.length)
})
check(badQuiz.length === 0, `成语情景题的正确答案下标都在选项范围内${badQuiz.length ? `（${badQuiz.map(idiomName).join('、')}）` : ''}`)

/* ----------------------------------------------------------------- 字源
 *
 * 字源动画的第二帧直接用离线笔顺数据画，所以字源语料只能收字表里的字——
 * 收了字表外的字，那一帧就会在断网时开天窗。
 */
check(ETYMOLOGY.length >= 50, `字源演变 ${ETYMOLOGY.length} 个字（要求 ≥ 50）`)

const etyDupes = ETYMOLOGY.map((e) => e.c).filter((v, i, a) => a.indexOf(v) !== i)
check(etyDupes.length === 0, `字源语料无重复字${etyDupes.length ? `（${etyDupes.join('')}）` : ''}`)

const etyStray = ETYMOLOGY.filter((e) => !CHARACTER_MAP.has(e.c))
check(
  etyStray.length === 0,
  `字源语料里的字都在字表里${etyStray.length ? `（${etyStray.map((e) => e.c).join('')}）` : ''}`
)

const etyKinds = new Set(ETYMOLOGY_KINDS.map((k) => k.id))
const etyBadKind = ETYMOLOGY.filter((e) => !etyKinds.has(e.kind))
check(
  etyBadKind.length === 0,
  `每个字都归到了象形/指事/会意/形声${etyBadKind.length ? `（${etyBadKind.map((e) => e.c).join('')}）` : ''}`
)

const etyNoText = ETYMOLOGY.filter((e) => !e.origin || !e.evolve)
check(
  etyNoText.length === 0,
  `每个字都写了「本来是什么」和「怎么变的」${etyNoText.length ? `（${etyNoText.map((e) => e.c).join('')}）` : ''}`
)

// 第一帧要么是小图要么是零件，两样都没有的话舞台上会是一块空白
const etyNoFrame = ETYMOLOGY.filter((e) => !e.sketch?.length && !(e.parts?.length >= 2))
check(
  etyNoFrame.length === 0,
  `每个字都有小图或至少两个零件${etyNoFrame.length ? `（${etyNoFrame.map((e) => e.c).join('')}）` : ''}`
)

const etyBadShape = []
for (const e of ETYMOLOGY) {
  for (const shape of e.sketch ?? []) {
    const problem = validateShape(shape)
    if (problem) etyBadShape.push(`${e.c}:${problem}`)
  }
}
check(
  etyBadShape.length === 0,
  `每张字源小图都画得出来${etyBadShape.length ? `（${etyBadShape.join('；')}）` : ''}`
)

check(
  ETYMOLOGY_CHARS === ETYMOLOGY.map((e) => e.c).join(''),
  '单字页用的字源索引与语料逐字对齐'
)

// 每一类都得有几个字，不然「原来这一类字都长这样」的规律看不出来
const thinKinds = ETYMOLOGY_KINDS.filter((k) => ETYMOLOGY.filter((e) => e.kind === k.id).length < 5)
check(
  thinKinds.length === 0,
  `象形/指事/会意/形声每类至少 5 个字${thinKinds.length ? `（${thinKinds.map((k) => k.name).join('、')}）` : ''}`
)

/* ------------------------------------------------------------- 偏旁部首 */
check(RADICALS.length >= 8, `偏旁部首 ${RADICALS.length} 个`)

const badExample = RADICALS.flatMap((r) =>
  (r.chars ?? []).filter((c) => !CHARACTERS.some((x) => x.char === c)).map((c) => `${r.name}:${c}`)
)
check(badExample.length === 0, `部首的「学过的字」示例都在字表里${badExample.length ? `（${badExample.join(', ')}）` : ''}`)

/* ----------------------------------------------------------------- 输出 */
notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\n内容自检：${notes.length} 项通过，${fails.length} 项失败。`)

/* 附带一份统计，方便写验收报告 */
console.log(
  `\n统计：${TOTAL_CHARACTERS} 字 / ${UNITS.length} 单元 / ${RADICALS.length} 偏旁 / ` +
    `${BOOKS.length} 本绘本（共 ${BOOKS.reduce((n, b) => n + b.pages.length, 0)} 页，` +
    `${new Set(BOOKS.flatMap(charsInBook)).size} 个不重复用字） / ${IDIOMS.length} 个成语 / ` +
    `${ETYMOLOGY.length} 个字有字源演变`
)

process.exit(fails.length ? 1 : 0)
