import assert from 'node:assert/strict'
import {
  GRADES,
  LOUDNESS_SCORE_CAP,
  alignChars,
  evaluate,
  gradeOf,
  normalizeTranscript,
  scoreFromLoudness,
  scoreFromSimilarity,
  similarity
} from '../src/utils/speechEval.js'

const tests = []
const test = (name, fn) => tests.push({ name, fn })

const REF = '床前明月光'

test('识别结果只留汉字，标点和英文都不参与判分', () => {
  assert.equal(normalizeTranscript('床前，明月光。'), REF)
  assert.equal(normalizeTranscript('床前 ok 明月光 123'), REF)
  assert.equal(normalizeTranscript(null), '')
})

test('念全对是满分', () => {
  assert.equal(similarity(REF, '床前明月光'), 1)
  assert.equal(scoreFromSimilarity(similarity(REF, '床前，明月光。')), 100)
})

test('漏字只扣漏掉的那几个字，后面的字不会被连坐', () => {
  // 漏了「前」，剩下四个字仍应判对
  const { chars, hits, total } = alignChars(REF, '床明月光')
  assert.equal(total, 5)
  assert.equal(hits, 4)
  assert.deepEqual(
    chars.map((c) => c.status),
    ['hit', 'miss', 'hit', 'hit', 'hit']
  )
})

test('多念出来的字只轻罚，不会把一遍好的跟读判成不及格', () => {
  const score = scoreFromSimilarity(similarity(REF, '床前明月光读完啦'))
  assert.ok(score >= 80, `多读三个字后得 ${score} 分，罚得太重`)
  assert.ok(score < 100, '多读了字还给满分，等于不看多读')
})

test('念的完全是别的内容判 0 分', () => {
  assert.equal(similarity(REF, '今天天气真好'), 0)
  assert.equal(scoreFromSimilarity(similarity(REF, '')), 0)
})

test('响度档封顶 85 分，不会给出它其实听不出来的满分', () => {
  const best = scoreFromLoudness({ voicedRatio: 1, durationRatio: 1.5, peak: 1 })
  assert.equal(best, LOUDNESS_SCORE_CAP)
})

test('响度档：没出声就是 0 分', () => {
  assert.equal(scoreFromLoudness({ voicedRatio: 0, durationRatio: 1, peak: 0 }), 0)
  assert.equal(scoreFromLoudness({ voicedRatio: 0.5, durationRatio: 1, peak: 0.01 }), 0)
  assert.equal(scoreFromLoudness(), 0)
})

test('响度档：读得越久越响分越高', () => {
  const quiet = scoreFromLoudness({ voicedRatio: 0.2, durationRatio: 0.3, peak: 0.1 })
  const loud = scoreFromLoudness({ voicedRatio: 0.8, durationRatio: 0.9, peak: 0.4 })
  assert.ok(loud > quiet, `认真读完 ${loud} 分没有高过敷衍 ${quiet} 分`)
})

test('分档阈值单调，且 0 分也有一句话可说', () => {
  assert.equal(gradeOf(100).id, 'gold')
  assert.equal(gradeOf(85).id, 'gold')
  assert.equal(gradeOf(84).id, 'silver')
  assert.equal(gradeOf(70).id, 'silver')
  assert.equal(gradeOf(50).id, 'bronze')
  assert.equal(gradeOf(0).id, 'again')
  for (const grade of GRADES) assert.ok(grade.label && grade.tip, `${grade.id} 缺少文案`)
})

test('evaluate：识别档给出逐字标记，响度档如实说明分数怎么来的', () => {
  const heard = evaluate({ mode: 'recognition', reference: REF, heard: '床前明月光' })
  assert.equal(heard.score, 100)
  assert.equal(heard.chars.length, 5)
  assert.ok(heard.chars.every((c) => c.status === 'hit'))

  const loud = evaluate({
    mode: 'loudness',
    reference: REF,
    sample: { voicedRatio: 0.7, durationRatio: 0.9, peak: 0.35 }
  })
  assert.ok(loud.score > 0 && loud.score <= LOUDNESS_SCORE_CAP)
  assert.ok(loud.chars.every((c) => c.status === 'unknown'), '响度档不该假装知道哪个字念对了')
  assert.ok(loud.note.includes('大声读完'), '响度档没有说明这一分是怎么来的')
})

let passed = 0
for (const { name, fn } of tests) {
  try {
    await fn()
    passed += 1
    console.log(`  ✓ ${name}`)
  } catch (error) {
    console.error(`  ✗ ${name}`)
    throw error
  }
}

console.log(`跟读评测单元测试：${passed}/${tests.length} 通过。`)
