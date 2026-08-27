import assert from 'node:assert/strict'
import { createCard, dueCards, isDue, retention, schedule } from '../src/utils/srs.js'

const DAY_MS = 24 * 60 * 60 * 1000
const NOW = Date.UTC(2026, 7, 26, 8)

const tests = []

function test(name, fn) {
  tests.push({ name, fn })
}

function closeTo(actual, expected, epsilon = 1e-12) {
  assert.ok(
    Math.abs(actual - expected) <= epsilon,
    `期望 ${actual} 与 ${expected} 的误差不超过 ${epsilon}`
  )
}

test('createCard 创建立即到期的初始卡片', () => {
  assert.deepEqual(createCard('山', NOW), {
    charId: '山',
    due: NOW,
    stability: 0,
    difficulty: 5,
    reps: 0,
    lapses: 0,
    lastRating: 0,
    lastReviewAt: 0
  })
})

test('四档评分使用确定的稳定性和到期时间', () => {
  const base = {
    ...createCard('水', NOW - DAY_MS),
    stability: 10,
    difficulty: 5,
    reps: 3,
    lapses: 1
  }
  const cases = [
    { rating: 1, stability: 4, difficulty: 5.8, lapses: 2 },
    { rating: 2, stability: 14, difficulty: 5.3, lapses: 1 },
    { rating: 3, stability: 23, difficulty: 5, lapses: 1 },
    { rating: 4, stability: 32, difficulty: 4.7, lapses: 1 }
  ]

  for (const expected of cases) {
    const next = schedule(base, expected.rating, NOW)
    closeTo(next.stability, expected.stability)
    closeTo(next.difficulty, expected.difficulty)
    assert.equal(next.due, NOW + Math.round(expected.stability * DAY_MS))
    assert.equal(next.reps, 4)
    assert.equal(next.lapses, expected.lapses)
    assert.equal(next.lastRating, expected.rating)
    assert.equal(next.lastReviewAt, NOW)
  }
})

test('首次成功复习使用 0.5 天作为稳定性基线', () => {
  const hard = schedule(createCard('日', NOW), 2, NOW)
  const good = schedule(createCard('月', NOW), 3, NOW)
  const easy = schedule(createCard('火', NOW), 4, NOW)

  closeTo(hard.stability, 0.7)
  closeTo(good.stability, 1.15)
  closeTo(easy.stability, 1.6)
})

test('遗忘会回退稳定性、增加难度和 lapse', () => {
  const card = {
    ...createCard('木', NOW),
    stability: 0.4,
    difficulty: 9.8,
    reps: 7,
    lapses: 2
  }
  const snapshot = structuredClone(card)
  const next = schedule(card, 1, NOW)

  assert.deepEqual(card, snapshot, 'schedule 不应修改传入卡片')
  assert.equal(next.stability, 0.5)
  assert.equal(next.difficulty, 10)
  assert.equal(next.reps, 8)
  assert.equal(next.lapses, 3)
})

test('难度会影响成功复习增长并限制在 1~10', () => {
  const low = { ...createCard('人', NOW), stability: 10, difficulty: 1.1 }
  const high = { ...createCard('口', NOW), stability: 10, difficulty: 10 }

  const lowNext = schedule(low, 4, NOW)
  const highNext = schedule(high, 3, NOW)

  closeTo(lowNext.stability, 38.24)
  assert.equal(lowNext.difficulty, 1)
  closeTo(highNext.stability, 17.25)
  assert.equal(highNext.difficulty, 10)
})

test('isDue 在到期边界为 true', () => {
  assert.equal(isDue({ due: NOW - 1 }, NOW), true)
  assert.equal(isDue({ due: NOW }, NOW), true)
  assert.equal(isDue({ due: NOW + 1 }, NOW), false)
})

test('dueCards 只返回到期卡片并按 due 升序排列', () => {
  const cards = {
    future: { ...createCard('天', NOW), due: NOW + DAY_MS },
    newest: { ...createCard('地', NOW), due: NOW },
    oldest: { ...createCard('人', NOW), due: NOW - 3 * DAY_MS },
    middle: { ...createCard('和', NOW), due: NOW - DAY_MS }
  }
  const snapshot = structuredClone(cards)

  assert.deepEqual(
    dueCards(cards, NOW).map((card) => card.charId),
    ['人', '和', '地']
  )
  assert.deepEqual(cards, snapshot, 'dueCards 不应修改卡片集合')
})

test('retention 使用指数遗忘曲线并处理未复习卡片', () => {
  assert.equal(retention(createCard('山', NOW), NOW), 0)
  assert.equal(retention({ ...createCard('水', NOW), stability: 0, lastReviewAt: NOW }, NOW), 0)

  const card = {
    ...createCard('火', NOW),
    stability: 4,
    lastReviewAt: NOW
  }
  assert.equal(retention(card, NOW), 1)
  closeTo(retention(card, NOW + 4 * DAY_MS), Math.exp(-0.9))
  closeTo(retention(card, NOW + 8 * DAY_MS), Math.exp(-1.8))
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

console.log(`FSRS 单元测试：${passed}/${tests.length} 通过。`)
