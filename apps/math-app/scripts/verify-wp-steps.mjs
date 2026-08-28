#!/usr/bin/env node
/**
 * Round 18 H4 word-problem step alignment probe.
 *
 * Every template is instantiated several times and its declared `steps` value
 * is compared with the number of steps produced by buildAnalysis(). Before the
 * alignment implementation lands, the metric is printed without making the
 * existing baseline red. An exported Round 18 marker (or --enforce) upgrades
 * the 90% target to a hard assertion.
 */

import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import './register-alias.mjs'

const [problemData, analysisData] = await Promise.all([
  import('../src/data/wordProblems.js'),
  import('../src/utils/wpAnalysis.js'),
])

const { WORD_PROBLEMS } = problemData
const { buildAnalysis } = analysisData
const READY_MARKER = ['ROUND18', 'H4'].join('_')
const TARGET_RATE = 0.9

const samplesArg = process.argv.find((arg) => arg.startsWith('--samples='))
const samples = samplesArg ? Number(samplesArg.slice('--samples='.length)) : 3
const enforce = process.argv.includes('--enforce')
const requireReady = process.argv.includes('--require-ready')

assert.ok(Number.isInteger(samples) && samples >= 1, '--samples must be a positive integer')

export function auditWordProblemSteps(templates = WORD_PROBLEMS, sampleCount = samples) {
  assert.ok(Array.isArray(templates) && templates.length > 0, 'WORD_PROBLEMS must not be empty')

  const rows = templates.map((template) => {
    assert.ok(template?.id, 'every word-problem template needs an id')
    assert.ok(
      Number.isInteger(template.steps) && template.steps >= 1,
      `${template.id} has invalid declared steps: ${template.steps}`,
    )
    assert.equal(typeof template.make, 'function', `${template.id} has no make() function`)

    const observed = new Set()
    for (let index = 0; index < sampleCount; index += 1) {
      const question = { ...template.make(), id: template.id }
      const actual = buildAnalysis(question).steps.length
      assert.ok(actual >= 1, `${template.id} produced no analysis steps: ${question.equation}`)
      observed.add(actual)
    }

    const actualSteps = [...observed].sort((a, b) => a - b)
    return {
      id: template.id,
      declaredSteps: template.steps,
      actualSteps,
      matches: actualSteps.length === 1 && actualSteps[0] === template.steps,
    }
  })

  const matched = rows.filter((row) => row.matches).length
  return {
    rows,
    matched,
    total: rows.length,
    rate: matched / rows.length,
    mismatches: rows.filter((row) => !row.matches),
    samples: sampleCount,
  }
}

export function hasRound18StepMarker() {
  return [problemData, analysisData].some((module) =>
    Object.prototype.hasOwnProperty.call(module, READY_MARKER),
  )
}

export function assertWordProblemStepTarget(result, target = TARGET_RATE) {
  assert.ok(
    result.rate >= target,
    `${READY_MARKER} alignment ${(result.rate * 100).toFixed(1)}% is below ${(target * 100).toFixed(0)}% ` +
      `(${result.matched}/${result.total})`,
  )
}

async function main() {
  const result = auditWordProblemSteps()
  const ready = hasRound18StepMarker()
  const percentage = (result.rate * 100).toFixed(1)

  console.log(
    `${READY_MARKER}: ${result.matched}/${result.total} templates aligned (${percentage}%), ` +
      `${result.samples} sample(s) each`,
  )
  for (const row of result.mismatches.slice(0, 12)) {
    console.log(
      `  - ${row.id}: declared=${row.declaredSteps}, analysis=${row.actualSteps.join('/')}`,
    )
  }
  if (result.mismatches.length > 12) {
    console.log(`  … ${result.mismatches.length - 12} more mismatch(es)`)
  }

  if (requireReady) {
    assert.ok(ready, `${READY_MARKER} marker is not available yet`)
  }
  if (ready || enforce || requireReady) {
    assertWordProblemStepTarget(result)
    console.log(`✓ ${READY_MARKER} target met (≥${TARGET_RATE * 100}%)`)
  } else {
    console.log(`○ ${READY_MARKER} PENDING: marker not available; metric and stable assertions passed`)
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  await main()
}
