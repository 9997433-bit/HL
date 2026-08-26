#!/usr/bin/env node

'use strict'

const fs = require('node:fs')
const path = require('node:path')
const { performance } = require('node:perf_hooks')

const ROOT_DIR = path.resolve(__dirname, '..')
const DATA_DIR = path.join(ROOT_DIR, 'shared', 'data')

const positiveInteger = (name, fallback) => {
  const raw = process.env[name]
  if (raw === undefined || raw === '') return fallback
  const value = Number(raw)
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${name} 必须是正整数，收到：${raw}`)
  }
  return value
}

const config = {
  round: 2,
  hanziCount: positiveInteger('STRESS_HANZI_COUNT', 50_000),
  mathCount: positiveInteger('STRESS_MATH_COUNT', 250_000),
  seed: positiveInteger('STRESS_SEED', 20_260_826),
  maxDurationMs: positiveInteger('STRESS_MAX_DURATION_MS', 2_000),
  maxHeapMb: positiveInteger('STRESS_MAX_HEAP_MB', 128),
  minHanziDataset: positiveInteger('STRESS_MIN_HANZI_DATASET', 100),
  minMathDataset: positiveInteger('STRESS_MIN_MATH_DATASET', 80),
  minMathTypes: positiveInteger('STRESS_MIN_MATH_TYPES', 9),
}

const readJson = (filename) => {
  const filepath = path.join(DATA_DIR, filename)
  try {
    return JSON.parse(fs.readFileSync(filepath, 'utf8'))
  } catch (error) {
    throw new Error(`无法读取 ${path.relative(ROOT_DIR, filepath)}：${error.message}`)
  }
}

const formatBytes = (bytes) => {
  const units = ['B', 'KiB', 'MiB', 'GiB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`
}

const escapeHtml = (value) =>
  String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')

const heapUsed = () => process.memoryUsage().heapUsed

const createRandom = (initialSeed) => {
  let seed = initialSeed >>> 0
  return () => {
    seed ^= seed << 13
    seed ^= seed >>> 17
    seed ^= seed << 5
    return (seed >>> 0) / 0x1_0000_0000
  }
}

const randomInteger = (random, min, max) =>
  Math.floor(random() * (max - min + 1)) + min

function validateData(charactersData, mathData) {
  const errors = []
  const characters = charactersData.characters
  const problems = mathData.problems

  if (!Array.isArray(characters) || characters.length < config.minHanziDataset) {
    errors.push(`common-hanzi.json 至少需要 ${config.minHanziDataset} 个汉字`)
  }
  if (!Array.isArray(problems) || problems.length < config.minMathDataset) {
    errors.push(`math-problems.json 至少需要 ${config.minMathDataset} 道题`)
  }
  if (Array.isArray(characters)) {
    const values = characters.map((item) => item.character)
    if (new Set(values).size !== values.length) errors.push('汉字数据存在重复项')
    if (values.some((value) => [...String(value)].length !== 1)) {
      errors.push('character 字段必须恰好包含一个 Unicode 字符')
    }
  }
  if (Array.isArray(problems)) {
    const ids = problems.map((item) => item.id)
    if (new Set(ids).size !== ids.length) errors.push('数学题 id 存在重复项')
    const problemTypes = new Set(problems.map((item) => item.type))
    if (problemTypes.size < config.minMathTypes) {
      errors.push(`数学题至少需要覆盖 ${config.minMathTypes} 类题型`)
    }
    for (const problem of problems) {
      if (!['number', 'string'].includes(typeof problem.answer)) {
        errors.push(`数学题 ${problem.id || '(无 id)'} 缺少有效答案`)
      }
      if (
        problem.choices !== undefined &&
        (!Array.isArray(problem.choices) || !problem.choices.includes(problem.answer))
      ) {
        errors.push(`数学题 ${problem.id || '(无 id)'} 的答案不在 choices 中`)
      }
    }
  }

  if (errors.length) throw new Error(errors.join('；'))
  return { characters, problems }
}

function stressHanziMarkup(characters, count) {
  const beforeHeap = heapUsed()
  const startedAt = performance.now()
  const cards = new Array(count)

  for (let index = 0; index < count; index += 1) {
    const entry = characters[index % characters.length]
    cards[index] =
      `<article class="hanzi-card" data-index="${index}">` +
      `<b aria-label="${escapeHtml(entry.meaning)}">${escapeHtml(entry.character)}</b>` +
      `<ruby>${escapeHtml(entry.example)}<rt>${escapeHtml(entry.pinyin)}</rt></ruby>` +
      '</article>'
  }

  const markup = `<main class="hanzi-grid">${cards.join('')}</main>`
  const durationMs = performance.now() - startedAt
  const heapDeltaBytes = Math.max(0, heapUsed() - beforeHeap)
  const payloadBytes = Buffer.byteLength(markup)
  const integrityPassed =
    cards.length === count &&
    markup.startsWith('<main') &&
    markup.endsWith('</main>') &&
    !markup.includes('undefined')

  return {
    count,
    durationMs,
    heapDeltaBytes,
    payloadBytes,
    integrityPassed,
    checksum: `${markup.slice(0, 32)}…${markup.slice(-32)}`,
  }
}

function generateMathProblem(random, index) {
  const operation = index % 5
  let left
  let right
  let answer
  let operator

  if (operation === 0) {
    left = randomInteger(random, 0, 100)
    right = randomInteger(random, 0, 100 - left)
    answer = left + right
    operator = '+'
  } else if (operation === 1) {
    left = randomInteger(random, 0, 100)
    right = randomInteger(random, 0, left)
    answer = left - right
    operator = '-'
  } else if (operation === 2) {
    left = randomInteger(random, 1, 12)
    right = randomInteger(random, 1, 12)
    answer = left * right
    operator = '×'
  } else if (operation === 3) {
    right = randomInteger(random, 1, 12)
    answer = randomInteger(random, 1, 12)
    left = right * answer
    operator = '÷'
  } else {
    left = randomInteger(random, 0, 100)
    right = randomInteger(random, 0, 100)
    answer = left === right ? '=' : left < right ? '<' : '>'
    operator = '○'
  }

  return { id: index, left, right, operator, answer }
}

function verifyGeneratedProblem(problem) {
  const { left, right, operator, answer } = problem
  if (operator === '+') return left + right === answer && answer <= 100
  if (operator === '-') return left - right === answer && answer >= 0
  if (operator === '×') return left * right === answer
  if (operator === '÷') return right !== 0 && left / right === answer
  if (operator === '○') {
    return answer === (left === right ? '=' : left < right ? '<' : '>')
  }
  return false
}

function stressMathGeneration(count, seed) {
  const random = createRandom(seed)
  const beforeHeap = heapUsed()
  const startedAt = performance.now()
  const problems = new Array(count)
  let invalidCount = 0

  for (let index = 0; index < count; index += 1) {
    const problem = generateMathProblem(random, index)
    problems[index] = problem
    if (!verifyGeneratedProblem(problem)) invalidCount += 1
  }

  const durationMs = performance.now() - startedAt
  const heapDeltaBytes = Math.max(0, heapUsed() - beforeHeap)
  return {
    count,
    durationMs,
    heapDeltaBytes,
    invalidCount,
    operationsPerSecond: count / (durationMs / 1000),
  }
}

function report(result) {
  console.log(`Round ${config.round} 边界压力测试`)
  console.log(`Node.js: ${process.version} | seed: ${config.seed}`)
  console.log(
    `预算: 单项 ≤ ${config.maxDurationMs} ms | 堆增量 ≤ ${config.maxHeapMb} MiB | ` +
      `数据集 ≥ ${config.minHanziDataset} 字 / ${config.minMathDataset} 题 / ${config.minMathTypes} 类`,
  )
  console.log(
    `汉字标记生成: ${result.hanzi.count.toLocaleString('en-US')} 张卡片 | ` +
      `${result.hanzi.durationMs.toFixed(2)} ms | ` +
      `HTML ${formatBytes(result.hanzi.payloadBytes)} | ` +
      `堆增量 ${formatBytes(result.hanzi.heapDeltaBytes)}`,
  )
  console.log(
    `数学题生成: ${result.math.count.toLocaleString('en-US')} 题 | ` +
      `${result.math.durationMs.toFixed(2)} ms | ` +
      `${Math.round(result.math.operationsPerSecond).toLocaleString('en-US')} 题/秒 | ` +
      `堆增量 ${formatBytes(result.math.heapDeltaBytes)} | ` +
      `无效题 ${result.math.invalidCount}`,
  )
  console.log(
    `静态题库: ${result.dataset.characterCount} 字 / ${result.dataset.problemCount} 题 / ` +
      `${result.dataset.problemTypes} 类`,
  )

  if (result.warnings.length) {
    console.log('边界提示:')
    result.warnings.forEach((warning) => console.log(`- ${warning}`))
  }
  console.log(result.passed ? '结果: PASS' : '结果: FAIL')
}

function main() {
  const charactersData = readJson('common-hanzi.json')
  const mathData = readJson('math-problems.json')
  const { characters, problems } = validateData(charactersData, mathData)
  const hanzi = stressHanziMarkup(characters, config.hanziCount)
  const math = stressMathGeneration(config.mathCount, config.seed)
  const warnings = []

  if (hanzi.payloadBytes >= 5 * 1024 * 1024) {
    warnings.push(
      '一次挂载全部汉字卡片会产生超过 5 MiB 的 HTML；真实页面应分页或使用虚拟列表。',
    )
  }
  warnings.push(
    'Node 探针只测量标记构造，不包含浏览器样式计算、布局与绘制；应另用浏览器性能面板确认帧率。',
  )
  if (math.durationMs > config.maxDurationMs) {
    warnings.push(`数学题生成超过 ${config.maxDurationMs} ms 预算。`)
  }
  if (hanzi.durationMs > config.maxDurationMs) {
    warnings.push(`汉字标记生成超过 ${config.maxDurationMs} ms 预算。`)
  }

  const peakHeapDelta = Math.max(hanzi.heapDeltaBytes, math.heapDeltaBytes)
  const passed =
    hanzi.integrityPassed &&
    math.invalidCount === 0 &&
    hanzi.durationMs <= config.maxDurationMs &&
    math.durationMs <= config.maxDurationMs &&
    peakHeapDelta <= config.maxHeapMb * 1024 * 1024

  const result = {
    config,
    dataset: {
      characterCount: characters.length,
      problemCount: problems.length,
      problemTypes: new Set(problems.map((problem) => problem.type)).size,
    },
    hanzi,
    math,
    warnings,
    passed,
  }

  report(result)
  if (process.env.STRESS_JSON === '1') console.log(JSON.stringify(result, null, 2))
  if (!passed) process.exitCode = 1
}

try {
  main()
} catch (error) {
  console.error(`stress-test: ${error.message}`)
  process.exitCode = 1
}
