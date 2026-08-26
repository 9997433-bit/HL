/**
 * 内容自检，不需要浏览器。
 *
 * 最重要的一条是绘本的用字约束：分级绘本的价值就在于「只用孩子学过的字」，
 * 一旦有人加了一句超纲的话，孩子就会卡住。这条必须自动化守住。
 */

import { CHARACTERS, TOTAL_CHARACTERS, UNITS } from '../src/data/characters.js'
import { BOOKS, charsInBook, verifyBookCoverage } from '../src/data/books.js'
import { IDIOMS } from '../src/data/idioms.js'
import { RADICALS, getRadical } from '../src/data/radicals.js'

const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))

/* ----------------------------------------------------------------- 字表 */
check(TOTAL_CHARACTERS >= 20, `字表 ${TOTAL_CHARACTERS} 个字（要求 ≥ 20）`)

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

/* ----------------------------------------------------------------- 绘本 */
check(BOOKS.length >= 2, `绘本 ${BOOKS.length} 本（要求 ≥ 2）`)

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
check(IDIOMS.length >= 5, `成语 ${IDIOMS.length} 个（要求 ≥ 5）`)

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

const badQuiz = IDIOMS.filter((i) => {
  if (!i.quiz) return false
  const { options, answer } = i.quiz
  return !Array.isArray(options) || !(answer >= 0 && answer < options.length)
})
check(badQuiz.length === 0, `成语情景题的正确答案下标都在选项范围内${badQuiz.length ? `（${badQuiz.map(idiomName).join('、')}）` : ''}`)

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
    `${new Set(BOOKS.flatMap(charsInBook)).size} 个不重复用字） / ${IDIOMS.length} 个成语`
)

process.exit(fails.length ? 1 : 0)
