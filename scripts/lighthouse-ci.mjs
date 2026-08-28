#!/usr/bin/env node

/**
 * Round 9/10 Lighthouse CI gate.
 *
 * Runs the repository acceptance suite with the calibrated Lighthouse version,
 * enforces Performance >= 0.95 for both apps, and archives raw mobile or
 * desktop reports. Mobile remains the backward-compatible default.
 */

import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const PINNED_LIGHTHOUSE_VERSION = '12.8.2'
const MIN_PERFORMANCE = 0.95
const REPORTS = ['literacy-app', 'math-app']
const SUPPORTED_PROFILES = new Set(['mobile', 'desktop'])

const fail = (message) => {
  console.error(`[lighthouse-ci] FAIL ${message}`)
  process.exit(1)
}

const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'))
if (packageJson.devDependencies?.lighthouse !== PINNED_LIGHTHOUSE_VERSION) {
  fail(
    `package.json 必须精确锁定 lighthouse=${PINNED_LIGHTHOUSE_VERSION}，` +
      `当前为 ${packageJson.devDependencies?.lighthouse ?? '未声明'}。`
  )
}

const lighthousePackagePath = path.join(root, 'node_modules', 'lighthouse', 'package.json')
const lighthouseBin = path.join(root, 'node_modules', '.bin', 'lighthouse')
if (!fs.existsSync(lighthousePackagePath) || !fs.existsSync(lighthouseBin)) {
  fail('未安装本地 Lighthouse；请先运行 npm ci。')
}

const installedVersion = JSON.parse(fs.readFileSync(lighthousePackagePath, 'utf8')).version
if (installedVersion !== PINNED_LIGHTHOUSE_VERSION) {
  fail(`Lighthouse 版本漂移：期望 ${PINNED_LIGHTHOUSE_VERSION}，实际 ${installedVersion}。`)
}

const requestedMinimum = Number(process.env.ACCEPTANCE_MIN_LH_PERFORMANCE ?? MIN_PERFORMANCE)
if (!Number.isFinite(requestedMinimum) || requestedMinimum < MIN_PERFORMANCE) {
  fail(`ACCEPTANCE_MIN_LH_PERFORMANCE 不得低于 ${MIN_PERFORMANCE}。`)
}

const profile = process.env.ACCEPTANCE_LH_PROFILE ?? 'mobile'
if (!SUPPORTED_PROFILES.has(profile)) {
  fail(`ACCEPTANCE_LH_PROFILE 必须是 mobile 或 desktop，当前为 ${profile}。`)
}

const evidenceDir = path.resolve(
  root,
  process.env.ACCEPTANCE_EVIDENCE_DIR ??
    `.agent_workspace/evidence/${profile === 'desktop' ? 'r10' : 'r9'}`
)
fs.mkdirSync(evidenceDir, { recursive: true })

console.log(
  `[lighthouse-ci] Lighthouse ${installedVersion}；profile=${profile}；` +
    `Performance 阈值 ${(requestedMinimum * 100).toFixed(0)}；证据目录 ${evidenceDir}`
)

const acceptance = spawnSync('bash', ['scripts/acceptance.sh'], {
  cwd: root,
  env: {
    ...process.env,
    ACCEPTANCE_EVIDENCE_DIR: evidenceDir,
    ACCEPTANCE_LH_PROFILE: profile,
    ACCEPTANCE_MIN_LH_PERFORMANCE: String(requestedMinimum),
    LIGHTHOUSE_BIN: lighthouseBin,
  },
  stdio: 'inherit',
})

if (acceptance.error) fail(`无法启动验收：${acceptance.error.message}`)
if (acceptance.status !== 0) fail(`test:acceptance 退出码 ${acceptance.status ?? 'unknown'}。`)

const scores = []
for (const app of REPORTS) {
  const suffix = profile === 'desktop' ? '-desktop' : ''
  const reportPath = path.join(evidenceDir, `lighthouse-${app}${suffix}.json`)
  if (!fs.existsSync(reportPath)) fail(`缺少原始报告 ${reportPath}。`)

  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'))
  const performance = report.categories?.performance?.score
  if (report.lighthouseVersion !== PINNED_LIGHTHOUSE_VERSION) {
    fail(`${app} 报告版本为 ${report.lighthouseVersion ?? 'unknown'}。`)
  }
  if (report.configSettings?.formFactor !== profile) {
    fail(
      `${app} 报告 formFactor=${report.configSettings?.formFactor ?? 'missing'}，` +
        `期望 ${profile}。`
    )
  }
  if (profile === 'desktop' && report.configSettings?.screenEmulation?.mobile !== false) {
    fail(`${app} desktop 报告未关闭 mobile screen emulation。`)
  }
  if (typeof performance !== 'number' || performance < requestedMinimum) {
    fail(`${app} Performance=${performance ?? 'missing'}，阈值=${requestedMinimum}。`)
  }
  scores.push(`${app}=${Math.round(performance * 100)}`)
}

console.log(`[lighthouse-ci] PASS profile=${profile}；${scores.join('，')}`)
