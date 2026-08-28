#!/usr/bin/env node
/**
 * Android 模拟全链路（VM 可执行，simulated:true —— 不等价真机签核）。
 *
 * 1. build:all + sync:android + check:android
 * 2. 双 App assembleDebug（需 ANDROID_HOME）
 * 3. 注入并核验 WebView UA + 移动视口 smoke 全路由
 * 4. OCR device harness A 段
 * 5. 归档日志并输出 evidence/r13/android-sim/report.json
 *
 * 用法：node scripts/android-sim.mjs [--skip-apk]
 * 标记：ROUND13_H6
 */

import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const ROUND13_H6 = 'android-sim-harness-v2'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const skipApk = process.argv.includes('--skip-apk')
const evidenceDir = path.join(root, '.agent_workspace/evidence/r13/android-sim')

const run = (cmd, args, opts = {}) => {
  const startedAt = new Date().toISOString()
  const started = performance.now()
  const r = spawnSync(cmd, args, { cwd: root, encoding: 'utf8', stdio: 'pipe', ...opts })
  return {
    ok: r.status === 0,
    status: r.status ?? 1,
    stdout: r.stdout ?? '',
    stderr: `${r.stderr ?? ''}${r.error ? `${r.error.message}\n` : ''}`,
    command: [cmd, ...args].join(' '),
    cwd: opts.cwd ?? root,
    startedAt,
    durationMs: Math.round(performance.now() - started),
  }
}

const sha256File = (abs) => {
  const buf = fs.readFileSync(abs)
  return crypto.createHash('sha256').update(buf).digest('hex')
}

const archiveRunLog = (filename, result) => {
  const abs = path.join(evidenceDir, filename)
  const cwd = path.relative(root, result.cwd) || '.'
  const body = [
    `# marker: ROUND13_H6`,
    `# command: ${result.command}`,
    `# cwd: ${cwd}`,
    `# startedAt: ${result.startedAt}`,
    `# durationMs: ${result.durationMs}`,
    `# exit: ${result.status}`,
    '',
    result.stdout.trimEnd(),
    result.stderr ? `\n[stderr]\n${result.stderr.trimEnd()}` : '',
    '',
  ].join('\n')
  fs.writeFileSync(abs, body)
  return {
    path: path.relative(root, abs).split(path.sep).join('/'),
    sha256: sha256File(abs),
    bytes: fs.statSync(abs).size,
  }
}

const parseSmokeSummary = (out) => {
  const totalRoute = out.match(/共\s*(\d+)\s*条路由/)
  const interactMatch = out.match(/(\d+)\s*项交互/)
  const problemMatch = out.match(/(\d+)\s*项有问题/)
  const userAgentMatch = out.match(/\[ROUND13_H6\] WebView UA smoke PASS:\s*(.+)/)
  return {
    smokeRoutes: totalRoute ? Number(totalRoute[1]) : 0,
    smokeInteractions: interactMatch ? Number(interactMatch[1]) : 0,
    smokeProblems: problemMatch ? Number(problemMatch[1]) : 0,
    observedUserAgent: userAgentMatch?.[1]?.trim() ?? null,
  }
}

fs.mkdirSync(evidenceDir, { recursive: true })

console.log(`[${ROUND13_H6}] Android 模拟全链路开始…`)

const steps = []

const build = run('npm', ['run', 'build:all'], { env: { ...process.env, CI: '1' } })
steps.push({ step: 'build:all', pass: build.ok, exit: build.status })
if (!build.ok) {
  archiveRunLog('build-all.log', build)
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
    const g = run('./gradlew', ['--console=plain', 'assembleDebug'], {
      cwd: path.join(root, rel),
      env: { ...process.env, ANDROID_HOME: process.env.ANDROID_HOME },
    })
    const gradleLog = archiveRunLog(`gradle-${label}.log`, g)
    const apkPath = path.join(
      root,
      rel,
      'app/build/outputs/apk/debug/app-debug.apk'
    )
    const built = g.ok && fs.existsSync(apkPath)
    apk[label] = built
      ? {
          path: path.relative(root, apkPath).split(path.sep).join('/'),
          sha256: sha256File(apkPath),
          bytes: fs.statSync(apkPath).size,
          gradleLog,
        }
      : { error: g.stderr.slice(-2000), exit: g.status, gradleLog }
    steps.push({
      step: `gradle:${label}`,
      pass: built,
      exit: g.status,
      durationMs: g.durationMs,
      log: gradleLog.path,
    })
  }
} else {
  steps.push({
    step: 'gradle',
    pass: skipApk,
    skip: skipApk ? '--skip-apk' : 'ANDROID_HOME is not set',
  })
}

const WEBVIEW_UA =
  'Mozilla/5.0 (Linux; Android 13; Pixel 7 Build/TQ3A.230805.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Mobile Safari/537.36'

const literacySmoke = run('node', ['scripts/smoke.mjs'], {
  cwd: path.join(root, 'apps/literacy-app'),
  env: { ...process.env, ANDROID_SIM_UA: WEBVIEW_UA, ROUND13_H6: '1' },
})
const lit = parseSmokeSummary(literacySmoke.stdout + literacySmoke.stderr)
const literacySmokeLog = archiveRunLog('smoke-literacy.log', literacySmoke)
const literacyUaPass = lit.observedUserAgent === WEBVIEW_UA
steps.push({
  step: 'smoke:literacy:webview-ua',
  pass: literacySmoke.ok && literacyUaPass,
  exit: literacySmoke.status,
  routes: lit.smokeRoutes,
  problems: lit.smokeProblems,
  log: literacySmokeLog.path,
})

const mathSmoke = run('node', ['scripts/smoke.mjs'], {
  cwd: path.join(root, 'apps/math-app'),
  env: { ...process.env, ANDROID_SIM_UA: WEBVIEW_UA, ROUND13_H6: '1' },
})
const mat = parseSmokeSummary(mathSmoke.stdout + mathSmoke.stderr)
const mathSmokeLog = archiveRunLog('smoke-math.log', mathSmoke)
const mathUaPass = mat.observedUserAgent === WEBVIEW_UA
steps.push({
  step: 'smoke:math:webview-ua',
  pass: mathSmoke.ok && mathUaPass,
  exit: mathSmoke.status,
  routes: mat.smokeRoutes,
  problems: mat.smokeProblems,
  log: mathSmokeLog.path,
})

// --section=a：这个 step 问的是「真机走查的前提条件绿不绿」，不是「真机验过了」。
// R14 起 harness 在 B 段没跑成时走 exit 2（SKIP 自己一档），不加这个参数的话
// VM 上永远没有设备，这一步会被判红——而它守的 A 段其实一条都没红。
const ocrDevice = run('node', ['scripts/test-ocr-device.mjs', '--section=a'], {
  cwd: path.join(root, 'apps/literacy-app'),
})
steps.push({ step: 'ocr-device-a', pass: ocrDevice.ok, exit: ocrDevice.status })
const ocrLog = archiveRunLog('ocr-device-a.log', ocrDevice)

const report = {
  simulated: true,
  marker: ROUND13_H6,
  note: 'VM WebView 模拟 + Capacitor APK 构建；不等价 Android QA 真机签核',
  timestamp: new Date().toISOString(),
  commit: run('git', ['rev-parse', '--short', 'HEAD']).stdout.trim(),
  webViewUserAgent: WEBVIEW_UA,
  webView: {
    requestedUserAgent: WEBVIEW_UA,
    literacyObservedUserAgent: lit.observedUserAgent,
    mathObservedUserAgent: mat.observedUserAgent,
    pass: literacyUaPass && mathUaPass,
  },
  steps,
  literacy: {
    smokePass: literacySmoke.ok,
    smokeRoutes: lit.smokeRoutes,
    smokeInteractions: lit.smokeInteractions,
    smokeProblems: lit.smokeProblems,
    webViewUaPass: literacyUaPass,
    smokeLog: literacySmokeLog,
    apkSha256: apk.literacy?.sha256 ?? null,
    apkBytes: apk.literacy?.bytes ?? null,
    apkPath: apk.literacy?.path ?? null,
    gradleLog: apk.literacy?.gradleLog ?? null,
  },
  math: {
    smokePass: mathSmoke.ok,
    smokeRoutes: mat.smokeRoutes,
    smokeInteractions: mat.smokeInteractions,
    smokeProblems: mat.smokeProblems,
    webViewUaPass: mathUaPass,
    smokeLog: mathSmokeLog,
    apkSha256: apk.math?.sha256 ?? null,
    apkBytes: apk.math?.bytes ?? null,
    apkPath: apk.math?.path ?? null,
    gradleLog: apk.math?.gradleLog ?? null,
  },
  ocr: { pass: ocrDevice.ok, log: ocrLog },
  androidHome: process.env.ANDROID_HOME ?? null,
}

fs.writeFileSync(path.join(evidenceDir, 'report.json'), JSON.stringify(report, null, 2))

console.log(JSON.stringify(report, null, 2))

const ok =
  build.ok &&
  sync.ok &&
  check.ok &&
  (skipApk || Boolean(apk.literacy?.sha256 && apk.math?.sha256)) &&
  literacySmoke.ok &&
  literacyUaPass &&
  mathSmoke.ok &&
  mathUaPass &&
  ocrDevice.ok

process.exit(ok ? 0 : 1)
