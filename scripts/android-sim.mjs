#!/usr/bin/env node
/**
 * Android 模拟全链路（VM 可执行，simulated:true —— 不等价真机签核）。
 *
 * 1. build:all + sync:android + check:android
 * 2. 双 App assembleDebug（需 ANDROID_HOME）
 * 3. WebView UA + 移动视口 smoke 全路由
 * 4. OCR device harness A 段
 * 5. 输出 evidence/r13/android-sim/report.json
 *
 * 用法：node scripts/android-sim.mjs [--skip-apk]
 * 标记：ROUND13_H6
 */

import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const ROUND13_H6 = 'android-sim-harness-v1'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const skipApk = process.argv.includes('--skip-apk')
const evidenceDir = path.join(root, '.agent_workspace/evidence/r13/android-sim')

const run = (cmd, args, opts = {}) => {
  const r = spawnSync(cmd, args, { cwd: root, encoding: 'utf8', stdio: 'pipe', ...opts })
  return { ok: r.status === 0, status: r.status ?? 1, stdout: r.stdout ?? '', stderr: r.stderr ?? '' }
}

const sha256File = (abs) => {
  const buf = fs.readFileSync(abs)
  return crypto.createHash('sha256').update(buf).digest('hex')
}

const parseSmokeSummary = (out) => {
  const routeMatch = out.match(/(\d+)\s*条路由/)
  const interactMatch = out.match(/(\d+)\s*项交互/)
  const problemMatch = out.match(/(\d+)\s*项有问题/)
  return {
    smokeRoutes: routeMatch ? Number(routeMatch[1]) : 0,
    smokeInteractions: interactMatch ? Number(interactMatch[1]) : 0,
    smokeProblems: problemMatch ? Number(problemMatch[1]) : 0,
  }
}

fs.mkdirSync(evidenceDir, { recursive: true })

console.log(`[${ROUND13_H6}] Android 模拟全链路开始…`)

const steps = []

const build = run('npm', ['run', 'build:all'], { env: { ...process.env, CI: '1' } })
steps.push({ step: 'build:all', pass: build.ok, exit: build.status })
if (!build.ok) {
  fs.writeFileSync(path.join(evidenceDir, 'build-all.log'), build.stdout + build.stderr)
  console.error('build:all 失败')
  process.exit(1)
}

const sync = run('npm', ['run', 'sync:android'])
steps.push({ step: 'sync:android', pass: sync.ok, exit: sync.status })

const check = run('npm', ['run', 'check:android'])
steps.push({ step: 'check:android', pass: check.ok, exit: check.status })

const apk = { literacy: null, math: null }

if (!skipApk && process.env.ANDROID_HOME) {
  for (const [label, rel] of [
    ['literacy', 'apps/literacy-app/android'],
    ['math', 'apps/math-app/android']
  ]) {
    const g = run('./gradlew', ['assembleDebug'], {
      cwd: path.join(root, rel),
      env: { ...process.env, ANDROID_HOME: process.env.ANDROID_HOME },
    })
    const apkPath = path.join(
      root,
      rel,
      'app/build/outputs/apk/debug/app-debug.apk'
    )
    const built = g.ok && fs.existsSync(apkPath)
    apk[label] = built
      ? { path: apkPath, sha256: sha256File(apkPath), bytes: fs.statSync(apkPath).size }
      : { error: g.stderr.slice(-2000), exit: g.status }
    fs.writeFileSync(path.join(evidenceDir, `gradle-${label}.log`), g.stdout + g.stderr)
    steps.push({ step: `gradle:${label}`, pass: built, exit: g.status })
  }
} else {
  steps.push({ step: 'gradle', pass: false, skip: skipApk ? 'flag' : 'no ANDROID_HOME' })
}

const WEBVIEW_UA =
  'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 Version/4.0'

const literacySmoke = run('node', ['scripts/smoke.mjs'], {
  cwd: path.join(root, 'apps/literacy-app'),
  env: { ...process.env, ANDROID_SIM_UA: WEBVIEW_UA, ROUND13_H6: '1' },
})
const lit = parseSmokeSummary(literacySmoke.stdout + literacySmoke.stderr)
fs.writeFileSync(path.join(evidenceDir, 'smoke-literacy.log'), literacySmoke.stdout + literacySmoke.stderr)

const mathSmoke = run('node', ['scripts/smoke.mjs'], {
  cwd: path.join(root, 'apps/math-app'),
  env: { ...process.env, ANDROID_SIM_UA: WEBVIEW_UA, ROUND13_H6: '1' },
})
const mat = parseSmokeSummary(mathSmoke.stdout + mathSmoke.stderr)
fs.writeFileSync(path.join(evidenceDir, 'smoke-math.log'), mathSmoke.stdout + mathSmoke.stderr)

const ocrDevice = run('node', ['scripts/test-ocr-device.mjs'], {
  cwd: path.join(root, 'apps/literacy-app'),
})
steps.push({ step: 'ocr-device-a', pass: ocrDevice.ok, exit: ocrDevice.status })
fs.writeFileSync(path.join(evidenceDir, 'ocr-device-a.log'), ocrDevice.stdout + ocrDevice.stderr)

const report = {
  simulated: true,
  marker: ROUND13_H6,
  note: 'VM WebView 模拟 + Capacitor APK 构建；不等价 Android QA 真机签核',
  timestamp: new Date().toISOString(),
  commit: run('git', ['rev-parse', '--short', 'HEAD']).stdout.trim(),
  webViewUserAgent: WEBVIEW_UA,
  steps,
  literacy: {
    smokePass: literacySmoke.ok,
    smokeRoutes: lit.smokeRoutes,
    smokeInteractions: lit.smokeInteractions,
    smokeProblems: lit.smokeProblems,
    apkSha256: apk.literacy?.sha256 ?? null,
    apkBytes: apk.literacy?.bytes ?? null,
  },
  math: {
    smokePass: mathSmoke.ok,
    smokeRoutes: mat.smokeRoutes,
    smokeInteractions: mat.smokeInteractions,
    smokeProblems: mat.smokeProblems,
    apkSha256: apk.math?.sha256 ?? null,
    apkBytes: apk.math?.bytes ?? null,
  },
  ocr: { pass: ocrDevice.ok },
  androidHome: process.env.ANDROID_HOME ?? null,
}

fs.writeFileSync(path.join(evidenceDir, 'report.json'), JSON.stringify(report, null, 2))

console.log(JSON.stringify(report, null, 2))

const ok =
  build.ok &&
  sync.ok &&
  check.ok &&
  literacySmoke.ok &&
  mathSmoke.ok &&
  ocrDevice.ok

process.exit(ok ? 0 : 1)
