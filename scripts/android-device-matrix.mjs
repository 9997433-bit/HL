#!/usr/bin/env node
/**
 * Round 14 Android physical-device QA evidence harness.
 *
 * Capture never declares QA PASS. It records physical-device facts and creates a
 * PENDING manual result template. Finalize emits device-signoff.json only after
 * two device classes, all required checks, evidence references and approvals
 * have been validated.
 *
 * Marker: ROUND14_H6
 */

import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const MARKER = 'ROUND14_H6'
const EXIT_FAILURE = 1
const EXIT_SKIP = 2
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const evidenceRoot = path.join(root, '.agent_workspace/evidence/r14/android')
const adb = process.env.ADB || 'adb'

const APPS = {
  literacy: {
    appId: 'com.hongen.literacy',
    defaultApk: 'apps/literacy-app/android/app/build/outputs/apk/debug/app-debug.apk',
  },
  math: {
    appId: 'com.hongen.mathquest',
    defaultApk: 'apps/math-app/android/app/build/outputs/apk/debug/app-debug.apk',
  },
}

const REQUIRED_CHECKS = [
  'common.clean-install',
  'common.upgrade-install',
  'common.cold-start',
  'common.background-resume',
  'common.system-back',
  'common.touch-and-gestures',
  'common.font-scale-130',
  'common.talkback',
  'common.four-themes',
  'common.audio-routing',
  'common.offline-cold-start',
  'common.progress-recovery',
  'common.offline-stability-30min',
  'common.no-crash-anr-white-screen',
  'literacy.learning-loop',
  'literacy.ocr-permissions-and-camera',
  'literacy.follow-read-microphone',
  'literacy.songs-and-books',
  'literacy.games',
  'math.routes-and-back',
  'math.answer-interactions',
  'math.manipulatives',
  'math.progress-and-wrongbook',
  'math.parent-controls',
]

const QA_ATTESTATION =
  'I executed every listed check on this physical device and linked the supporting evidence.'
const APPROVAL_ATTESTATION =
  'I reviewed both physical-device records, blocking defects, build hashes, and approve Android GO.'

const usage = () => {
  console.log(`Usage:
  node scripts/android-device-matrix.mjs capture [options]
  node scripts/android-device-matrix.mjs finalize

Capture options:
  --serial <adb-serial>       Capture one connected physical device
  --install                   Install both APKs with adb install -r
  --literacy-apk <path>       Literacy APK (default: ${APPS.literacy.defaultApk})
  --math-apk <path>           Math APK (default: ${APPS.math.defaultApk})
  --help                      Show this help

Exit codes:
  0  Evidence captured or signoff finalized
  1  Harness, evidence, or QA validation failed
  2  SKIP: adb unavailable or no authorized physical device

Capture output is CAPTURED/PENDING, never PASS. See:
  .agent_workspace/ANDROID-DEVICE-QA-CHECKLIST.md`)
}

const fail = (message, details = []) => {
  console.error(`[${MARKER}] FAIL: ${message}`)
  for (const detail of details) console.error(`  - ${detail}`)
  process.exit(EXIT_FAILURE)
}

const skip = (message, details = []) => {
  console.log(`[${MARKER}] SKIP: ${message}`)
  for (const detail of details) console.log(`  - ${detail}`)
  console.log(`[${MARKER}] No QA pass or device-signoff.json was produced.`)
  process.exit(EXIT_SKIP)
}

const sha256 = (value) => crypto.createHash('sha256').update(value).digest('hex')
const sha256File = (file) => sha256(fs.readFileSync(file))
const toRepoPath = (file) => path.relative(root, file).split(path.sep).join('/')
const normalizeText = (value) => String(value ?? '').replace(/\r/g, '').trim()

const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? root,
    encoding: options.binary ? null : 'utf8',
    maxBuffer: 24 * 1024 * 1024,
    stdio: 'pipe',
    ...options,
  })
  return {
    status: result.status,
    ok: result.status === 0,
    stdout: result.stdout ?? (options.binary ? Buffer.alloc(0) : ''),
    stderr: result.stderr ?? (options.binary ? Buffer.alloc(0) : ''),
    error: result.error,
  }
}

const adbRun = (serial, args, options = {}) =>
  run(adb, serial ? ['-s', serial, ...args] : args, options)

const adbText = (serial, args) => {
  const result = adbRun(serial, args)
  return {
    ...result,
    stdout: normalizeText(result.stdout),
    stderr: normalizeText(result.stderr),
  }
}

const shellText = (serial, ...args) => adbText(serial, ['shell', ...args])

const parseArgs = () => {
  const args = process.argv.slice(2)
  if (args.includes('--help') || args.includes('-h')) return { help: true }

  let mode = 'capture'
  if (args[0] === 'capture' || args[0] === 'finalize') mode = args.shift()

  const parsed = { mode, install: false, serial: null, apk: {} }
  while (args.length) {
    const arg = args.shift()
    if (arg === '--install') {
      parsed.install = true
      continue
    }
    const valueOptions = {
      '--serial': 'serial',
      '--literacy-apk': 'literacy',
      '--math-apk': 'math',
    }
    const key = valueOptions[arg]
    if (!key) fail(`Unknown argument: ${arg}`)
    const value = args.shift()
    if (!value || value.startsWith('--')) fail(`${arg} requires a value`)
    if (key === 'serial') parsed.serial = value
    else parsed.apk[key] = value
  }
  if (mode === 'finalize' && (parsed.install || parsed.serial || Object.keys(parsed.apk).length))
    fail('finalize does not accept capture options')
  return parsed
}

const parseAdbDevices = (stdout) =>
  normalizeText(stdout)
    .split('\n')
    .slice(1)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [serial, state = '', ...metadata] = line.split(/\s+/)
      return { serial, state, metadata: metadata.join(' ') }
    })

const getProp = (serial, property) => shellText(serial, 'getprop', property).stdout

const isPhysicalDevice = (device) => {
  if (device.state !== 'device') return { physical: false, reason: `state=${device.state}` }
  if (/^emulator-\d+$/i.test(device.serial))
    return { physical: false, reason: 'emulator serial' }
  const qemu = getProp(device.serial, 'ro.kernel.qemu')
  const bootQemu = getProp(device.serial, 'ro.boot.qemu')
  const hardware = getProp(device.serial, 'ro.hardware')
  if (qemu === '1' || bootQemu === '1')
    return { physical: false, reason: 'qemu property is 1', qemu, bootQemu, hardware }
  if (/^(goldfish|ranchu)$/i.test(hardware))
    return { physical: false, reason: `emulator hardware=${hardware}`, qemu, bootQemu, hardware }
  return { physical: true, qemu, bootQemu, hardware }
}

const discoverPhysicalDevices = (requestedSerial) => {
  const result = adbText(null, ['devices', '-l'])
  if (result.error?.code === 'ENOENT')
    skip(`adb executable not found (${adb})`)
  if (!result.ok)
    skip('adb could not enumerate devices', [result.stderr || `exit=${result.status}`])

  const listed = parseAdbDevices(result.stdout)
  const classified = listed.map((device) => ({ ...device, ...isPhysicalDevice(device) }))
  let physical = classified.filter((device) => device.physical)

  if (requestedSerial) {
    const requested = classified.find((device) => device.serial === requestedSerial)
    if (!requested)
      skip(`requested device ${requestedSerial} is not connected`, classified.map(describeDevice))
    if (!requested.physical)
      skip(`requested device ${requestedSerial} is not an authorized physical device`, [
        requested.reason,
      ])
    physical = [requested]
  }

  if (!physical.length) {
    const details = classified.length
      ? classified.map(describeDevice)
      : ['adb devices returned no entries']
    skip('no authorized physical Android device detected', details)
  }
  return physical
}

const describeDevice = (device) =>
  `${device.serial}: ${device.physical ? 'physical' : 'excluded'} (${device.reason || device.state})`

const safeSlug = (value) =>
  normalizeText(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 36) || 'android'

const readJson = (file) => {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'))
  } catch (error) {
    throw new Error(`${toRepoPath(file)}: ${error.message}`)
  }
}

const writeJson = (file, value) => {
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`)
}

const artifact = (file) => ({
  path: toRepoPath(file),
  bytes: fs.statSync(file).size,
  sha256: sha256File(file),
})

const writeTextArtifact = (directory, name, value, serial) => {
  const file = path.join(directory, name)
  const redacted = normalizeText(value).split(serial).join('[REDACTED_ADB_SERIAL]')
  fs.writeFileSync(file, `${redacted}\n`)
  return artifact(file)
}

const resolveApk = (provided, fallback) => {
  const candidate = provided ?? fallback
  return path.isAbsolute(candidate) ? candidate : path.resolve(root, candidate)
}

const apkMetadata = (file) => {
  if (!fs.existsSync(file)) return null
  const stat = fs.statSync(file)
  if (!stat.isFile() || stat.size === 0) return null
  return { path: toRepoPath(file), bytes: stat.size, sha256: sha256File(file) }
}

const packageVersion = (dump) => ({
  versionName: dump.match(/\bversionName=([^\s]+)/)?.[1] ?? null,
  versionCode: dump.match(/\bversionCode=(\d+)/)?.[1] ?? null,
})

const sleep = (milliseconds) => {
  const cell = new Int32Array(new SharedArrayBuffer(4))
  Atomics.wait(cell, 0, 0, milliseconds)
}

const captureApp = ({ key, config, serial, directory, install, apk }) => {
  const appDirectory = path.join(directory, key)
  fs.mkdirSync(appDirectory, { recursive: true })
  const details = {
    appId: config.appId,
    apk,
    installedByHarness: false,
    installed: false,
    version: null,
    launch: { attempted: false, ok: false },
    artifacts: {},
  }

  if (install) {
    const installResult = adbText(serial, ['install', '-r', apk.path])
    details.artifacts.install = writeTextArtifact(
      appDirectory,
      'install.txt',
      [installResult.stdout, installResult.stderr].filter(Boolean).join('\n'),
      serial
    )
    if (!installResult.ok || !/Success/i.test(installResult.stdout))
      throw new Error(`${key}: adb install failed (exit ${installResult.status})`)
    details.installedByHarness = true
  }

  const packagePath = shellText(serial, 'pm', 'path', config.appId)
  details.installed = packagePath.ok && /^package:/m.test(packagePath.stdout)
  if (!details.installed) return details

  const packageDump = shellText(serial, 'dumpsys', 'package', config.appId)
  details.version = packageVersion(packageDump.stdout)
  details.artifacts.package = writeTextArtifact(
    appDirectory,
    'package.txt',
    [
      `appId=${config.appId}`,
      `versionName=${details.version.versionName ?? ''}`,
      `versionCode=${details.version.versionCode ?? ''}`,
      packagePath.stdout,
    ].join('\n'),
    serial
  )

  adbText(serial, ['logcat', '-c'])
  const launch = shellText(
    serial,
    'monkey',
    '-p',
    config.appId,
    '-c',
    'android.intent.category.LAUNCHER',
    '1'
  )
  details.launch = {
    attempted: true,
    ok: launch.ok && /Events injected:\s*1/i.test(launch.stdout),
  }
  details.artifacts.launch = writeTextArtifact(
    appDirectory,
    'launch.txt',
    [launch.stdout, launch.stderr].filter(Boolean).join('\n'),
    serial
  )
  sleep(3000)

  const screenshot = adbRun(serial, ['exec-out', 'screencap', '-p'], { binary: true })
  if (
    screenshot.ok &&
    Buffer.isBuffer(screenshot.stdout) &&
    screenshot.stdout.length > 8 &&
    screenshot.stdout.subarray(1, 4).toString('ascii') === 'PNG'
  ) {
    const screenshotFile = path.join(appDirectory, 'launch.png')
    fs.writeFileSync(screenshotFile, screenshot.stdout)
    details.artifacts.screenshot = artifact(screenshotFile)
  }

  const logcat = adbText(serial, ['logcat', '-d', '-t', '2000', '-v', 'threadtime'])
  details.artifacts.logcat = writeTextArtifact(
    appDirectory,
    'logcat.txt',
    [logcat.stdout, logcat.stderr].filter(Boolean).join('\n'),
    serial
  )

  const meminfo = shellText(serial, 'dumpsys', 'meminfo', config.appId)
  details.artifacts.meminfo = writeTextArtifact(
    appDirectory,
    'meminfo.txt',
    [meminfo.stdout, meminfo.stderr].filter(Boolean).join('\n'),
    serial
  )
  return details
}

const captureDevice = (device, options, apks, commit) => {
  const manufacturer = getProp(device.serial, 'ro.product.manufacturer')
  const model = getProp(device.serial, 'ro.product.model')
  const serialHash = sha256(device.serial)
  const deviceSlug = `${safeSlug(`${manufacturer}-${model}`)}-${serialHash.slice(0, 12)}`
  const directory = path.join(evidenceRoot, deviceSlug)
  fs.mkdirSync(directory, { recursive: true })

  const sdkText = getProp(device.serial, 'ro.build.version.sdk')
  const deviceInfo = {
    marker: MARKER,
    capturedAt: new Date().toISOString(),
    onDevice: true,
    simulated: false,
    physicalDeviceVerified: true,
    adbSerialSha256: serialHash,
    deviceSlug,
    manufacturer,
    model,
    product: getProp(device.serial, 'ro.product.name'),
    device: getProp(device.serial, 'ro.product.device'),
    androidRelease: getProp(device.serial, 'ro.build.version.release'),
    sdk: Number(sdkText) || null,
    buildFingerprint: getProp(device.serial, 'ro.build.fingerprint'),
    securityPatch: getProp(device.serial, 'ro.build.version.security_patch'),
    hardware: device.hardware || getProp(device.serial, 'ro.hardware'),
    socModel: getProp(device.serial, 'ro.soc.model'),
    kernelQemu: false,
    qemuProperties: {
      kernel: device.qemu || null,
      boot: device.bootQemu || null,
    },
    ram: shellText(device.serial, 'sh', '-c', "grep MemTotal /proc/meminfo").stdout,
    display: {
      size: shellText(device.serial, 'wm', 'size').stdout,
      density: shellText(device.serial, 'wm', 'density').stdout,
    },
    webViewPackage: shellText(
      device.serial,
      'cmd',
      'webviewupdate',
      'getCurrentWebViewPackage'
    ).stdout,
  }
  const deviceInfoFile = path.join(directory, 'device-info.json')
  writeJson(deviceInfoFile, deviceInfo)

  const apps = {}
  for (const [key, config] of Object.entries(APPS)) {
    apps[key] = captureApp({
      key,
      config,
      serial: device.serial,
      directory,
      install: options.install,
      apk: apks[key],
    })
  }

  const capture = {
    marker: MARKER,
    status: 'CAPTURED',
    qaVerdict: 'PENDING',
    pass: false,
    note: 'Physical-device facts captured; manual QA and approvals are still required.',
    capturedAt: new Date().toISOString(),
    onDevice: true,
    simulated: false,
    physicalDeviceVerified: true,
    privacyReviewRequired: true,
    deviceSlug,
    adbSerialSha256: serialHash,
    commit,
    deviceInfo: artifact(deviceInfoFile),
    apps,
  }
  const captureFile = path.join(directory, 'capture.json')
  writeJson(captureFile, capture)

  const templateFile = path.join(directory, 'qa-result.template.json')
  writeJson(templateFile, {
    marker: MARKER,
    status: 'PENDING',
    verdict: 'NO-GO',
    onDevice: true,
    simulated: false,
    deviceSlug,
    matrixClass: 'FILL: low-end-old OR modern',
    binding: {
      captureSha256: sha256File(captureFile),
      commit,
      apkSha256: Object.fromEntries(
        Object.entries(apks).map(([key, value]) => [key, value?.sha256 ?? null])
      ),
    },
    checks: Object.fromEntries(
      REQUIRED_CHECKS.map((id) => [id, { status: 'PENDING', evidence: [], note: '' }])
    ),
    blockingDefects: [],
    nonBlockingDefects: [],
    privacyReviewComplete: false,
    tester: {
      name: '',
      testedAt: '',
      attestation: QA_ATTESTATION,
    },
  })

  console.log(
    `[${MARKER}] CAPTURED ${manufacturer} ${model} as ${deviceSlug}; QA verdict remains PENDING.`
  )
  console.log(`  ${toRepoPath(captureFile)}`)
  console.log(`  Copy qa-result.template.json to qa-result.json only after executing the checklist.`)
}

const capture = (options) => {
  const devices = discoverPhysicalDevices(options.serial)
  const apks = Object.fromEntries(
    Object.entries(APPS).map(([key, config]) => {
      const file = resolveApk(options.apk[key], config.defaultApk)
      return [key, apkMetadata(file)]
    })
  )
  if (options.install) {
    const missing = Object.entries(apks)
      .filter(([, value]) => !value)
      .map(([key]) => `${key} APK is missing or empty`)
    if (missing.length) fail('--install requires both non-empty APKs', missing)
  }

  const commit = normalizeText(run('git', ['rev-parse', 'HEAD']).stdout)
  if (!/^[a-f0-9]{40}$/i.test(commit)) fail('could not resolve the current git commit')

  fs.mkdirSync(evidenceRoot, { recursive: true })
  let failures = 0
  for (const device of devices) {
    try {
      captureDevice(device, options, apks, commit)
    } catch (error) {
      failures++
      console.error(`[${MARKER}] FAIL ${device.serial}: ${error.message}`)
    }
  }
  if (failures) fail(`${failures}/${devices.length} device captures failed`)
  console.log(
    `[${MARKER}] Capture complete. This is not QA PASS; finalize requires two device classes and signed results.`
  )
}

const isIsoDate = (value) =>
  typeof value === 'string' &&
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value) &&
  Number.isFinite(Date.parse(value))

const verifyArtifact = (deviceDirectory, reference) => {
  if (typeof reference !== 'string' || !reference || path.isAbsolute(reference)) return false
  const resolved = path.resolve(deviceDirectory, reference)
  const prefix = `${path.resolve(deviceDirectory)}${path.sep}`
  if (!resolved.startsWith(prefix)) return false
  try {
    return fs.statSync(resolved).isFile() && fs.statSync(resolved).size >= 100
  } catch {
    return false
  }
}

const validateDeviceResult = (deviceDirectory) => {
  const errors = []
  const captureFile = path.join(deviceDirectory, 'capture.json')
  const resultFile = path.join(deviceDirectory, 'qa-result.json')
  let captured
  let result
  try {
    captured = readJson(captureFile)
    result = readJson(resultFile)
  } catch (error) {
    return { errors: [error.message] }
  }

  const deviceInfo = readJson(path.join(deviceDirectory, 'device-info.json'))
  if (
    captured.marker !== MARKER ||
    captured.status !== 'CAPTURED' ||
    captured.onDevice !== true ||
    captured.simulated !== false ||
    captured.physicalDeviceVerified !== true ||
    captured.pass !== false
  )
    errors.push('capture.json is not a non-signing physical-device capture')
  if (
    deviceInfo.onDevice !== true ||
    deviceInfo.simulated !== false ||
    deviceInfo.physicalDeviceVerified !== true ||
    deviceInfo.kernelQemu !== false
  )
    errors.push('device-info.json does not verify a non-QEMU physical device')
  if (result.marker !== MARKER || result.onDevice !== true || result.simulated !== false)
    errors.push('qa-result.json marker/device flags are invalid')
  if (result.status !== 'PASSED' || result.verdict !== 'GO')
    errors.push('qa-result.json must explicitly be status=PASSED and verdict=GO')
  if (result.deviceSlug !== captured.deviceSlug || result.deviceSlug !== deviceInfo.deviceSlug)
    errors.push('deviceSlug does not match capture and device info')
  if (result.binding?.captureSha256 !== sha256File(captureFile))
    errors.push('qa-result binding does not match capture.json SHA-256')
  if (result.binding?.commit !== captured.commit)
    errors.push('qa-result commit does not match capture')

  for (const app of Object.keys(APPS)) {
    const appCapture = captured.apps?.[app]
    if (!appCapture?.apk?.sha256)
      errors.push(`${app}: capture has no APK SHA-256`)
    if (result.binding?.apkSha256?.[app] !== appCapture?.apk?.sha256)
      errors.push(`${app}: qa-result APK SHA-256 does not match capture`)
    if (!appCapture?.installed || !appCapture?.launch?.ok)
      errors.push(`${app}: install/launch capture is incomplete`)
    for (const name of ['screenshot', 'logcat', 'meminfo']) {
      const item = appCapture?.artifacts?.[name]
      if (!item?.path || !fs.existsSync(path.join(root, item.path)))
        errors.push(`${app}: missing ${name} capture artifact`)
      else if (sha256File(path.join(root, item.path)) !== item.sha256)
        errors.push(`${app}: ${name} capture artifact hash mismatch`)
    }
  }

  for (const id of REQUIRED_CHECKS) {
    const check = result.checks?.[id]
    if (check?.status !== 'PASS') errors.push(`${id}: status is not PASS`)
    if (!Array.isArray(check?.evidence) || !check.evidence.length)
      errors.push(`${id}: no evidence reference`)
    else if (check.evidence.some((reference) => !verifyArtifact(deviceDirectory, reference)))
      errors.push(`${id}: evidence reference is missing, too small, or escapes device directory`)
  }
  if (!Array.isArray(result.blockingDefects) || result.blockingDefects.length)
    errors.push('blockingDefects must be an empty array')
  if (result.privacyReviewComplete !== true)
    errors.push('privacyReviewComplete must be true')
  if (
    !normalizeText(result.tester?.name) ||
    !isIsoDate(result.tester?.testedAt) ||
    result.tester?.attestation !== QA_ATTESTATION
  )
    errors.push('tester identity, timestamp, or exact attestation is missing')

  const sdk = Number(deviceInfo.sdk)
  if (result.matrixClass === 'low-end-old') {
    if (sdk < 26 || sdk > 29) errors.push('low-end-old device must use Android API 26–29')
  } else if (result.matrixClass === 'modern') {
    if (sdk < 33) errors.push('modern device must use Android API 33+')
  } else {
    errors.push('matrixClass must be low-end-old or modern')
  }

  return { errors, captured, result, deviceInfo, captureFile, resultFile }
}

const validateApproval = () => {
  const file = path.join(evidenceRoot, 'release-approval.json')
  const approval = readJson(file)
  const errors = []
  if (approval.marker !== MARKER || approval.verdict !== 'GO')
    errors.push('release approval marker/verdict is invalid')
  for (const role of ['qaLead', 'releaseManager']) {
    const signer = approval[role]
    if (
      !normalizeText(signer?.name) ||
      !isIsoDate(signer?.signedAt) ||
      signer?.attestation !== APPROVAL_ATTESTATION
    )
      errors.push(`${role} identity, timestamp, or exact attestation is missing`)
  }
  return { file, approval, errors }
}

const finalize = () => {
  if (!fs.existsSync(evidenceRoot))
    fail('evidence directory does not exist; run capture on physical devices first')

  const directories = fs
    .readdirSync(evidenceRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(evidenceRoot, entry.name))
  const validated = directories
    .filter((directory) => fs.existsSync(path.join(directory, 'qa-result.json')))
    .map(validateDeviceResult)
  const errors = validated.flatMap((item) => item.errors)
  if (validated.length < 2) errors.push(`only ${validated.length}/2 signed device results found`)

  const classes = new Set(validated.filter((item) => !item.errors.length).map((item) => item.result.matrixClass))
  if (!classes.has('low-end-old')) errors.push('low-end-old Android 8–10 result is missing')
  if (!classes.has('modern')) errors.push('modern Android 13+ result is missing')

  const uniqueDevices = new Set(validated.map((item) => item.captured?.adbSerialSha256).filter(Boolean))
  if (uniqueDevices.size !== validated.length) errors.push('device captures are not unique')

  const buildBindings = validated.map((item) =>
    JSON.stringify({
      commit: item.captured?.commit,
      literacy: item.captured?.apps?.literacy?.apk?.sha256,
      math: item.captured?.apps?.math?.apk?.sha256,
    })
  )
  if (new Set(buildBindings).size > 1)
    errors.push('all devices must test the same commit and APK hashes')

  let approvalResult
  try {
    approvalResult = validateApproval()
    errors.push(...approvalResult.errors)
  } catch (error) {
    errors.push(error.message)
  }
  if (errors.length) fail('device matrix is not eligible for signoff', errors)

  const signoff = {
    marker: MARKER,
    status: 'SIGNED_OFF',
    verdict: 'GO',
    pass: true,
    onDevice: true,
    simulated: false,
    signedAt: new Date().toISOString(),
    commit: validated[0].captured.commit,
    apkSha256: {
      literacy: validated[0].captured.apps.literacy.apk.sha256,
      math: validated[0].captured.apps.math.apk.sha256,
    },
    devices: validated.map((item) => ({
      deviceSlug: item.captured.deviceSlug,
      matrixClass: item.result.matrixClass,
      manufacturer: item.deviceInfo.manufacturer,
      model: item.deviceInfo.model,
      androidRelease: item.deviceInfo.androidRelease,
      sdk: item.deviceInfo.sdk,
      capture: artifact(item.captureFile),
      qaResult: artifact(item.resultFile),
      tester: item.result.tester,
    })),
    qaLead: approvalResult.approval.qaLead,
    releaseManager: approvalResult.approval.releaseManager,
    releaseApproval: artifact(approvalResult.file),
  }
  const signoffFile = path.join(evidenceRoot, 'device-signoff.json')
  writeJson(signoffFile, signoff)
  console.log(`[${MARKER}] SIGNED_OFF: ${toRepoPath(signoffFile)}`)
  console.log(
    `[${MARKER}] Complete the separate GO decision document before claiming the Round 14 H6 gate.`
  )
}

const options = parseArgs()
if (options.help) {
  usage()
  process.exit(0)
}

try {
  if (options.mode === 'finalize') finalize()
  else capture(options)
} catch (error) {
  fail(error.message)
}
