/**
 * ROUND14_H1 —— 真机 RTF 证据的**收货台**。
 *
 * `check-round14.mjs` 的 H1 有一条腿读的是
 * `.agent_workspace/evidence/r14/asr/device-rtf.json`：只要这份文件里
 * `onDevice:true`、`simulated:false`、有个像样的 `device` 身份、`rtfP95` 落在 0–0.5，
 * 那条腿就绿。**这五个字段谁都能在十秒钟内敲出来。**
 *
 * 所以这个脚本管的是另一件事：一份能让那条腿变绿的文件，凭什么算数。
 * 它把「真机上真的跑过一遍」拆成可核对的痕迹——
 *
 *   - 测的是**发出去的那个包**：`pack.sha256` 必须等于 `public/asr/manifest.json`
 *     里的整包指纹。换了模型不重测，这里当场对不上。
 *   - 测的是**一台具体的机器**：型号、Android 版本、芯片、WebView 版本、
 *     内存，外加一个设备序列号的哈希（不落明文序列号）。「Android 手机」不算身份。
 *   - 测的是**一段够长的音**：≥20 句、≥60 秒。三句话的 p95 是个笑话。
 *   - `rtfP95` 只是 `rtf.p95` 的镜像，两处对不上就是有人只改了给探针看的那一个数。
 *   - 四条真机门槛（RTF / 句末延迟 / 峰值内存 / 长任务）外加离线重启与故障复演，
 *     一条都不许缺；每条的 `verdict` 必须和阈值算出来的一致。
 *   - 有**执行痕迹**：adb 日志落盘、跑的是哪条命令、谁签的字。
 *
 * 还有一条反着来的闸：`.agent_workspace/evidence/r13/asr-rtf/host-baseline.json`
 * 那份主机基准长得很像这份文件（也有 rtf.p95、也有 memory），改个文件名就能冒充真机。
 * 只要文档里出现 `host` 或 `projection`，这里就认定它是主机基准，直接拒。
 *
 * ## 两种合法状态
 *
 *   status: "not-measured"  真机还没跑。`onDevice` 必须是 false、`rtfP95` 必须是 null，
 *                           而且要写清谁欠着这件事（`owner`）、它卡住了什么（`blockedBy`）。
 *                           这是**当前**仓库里那份文件的状态——H1 那条腿因此红着，红得对。
 *   status: "measured"      真机跑过了。上面所有痕迹一个都不能少。
 *
 * ## 不变式
 *
 *   **任何能让 H1 那条腿变绿的文件（`probeWouldPass`），在这里必须零错误。**
 *   `test-asr-eval-set.mjs` 用这条不变式守着：伪造一份只填五个字段的 JSON，
 *   探针会绿，这里会红——于是 harness 红，于是这条捷径走不通。
 *
 * 用法：
 *   node scripts/check-asr-device-rtf.mjs            # 验仓库里那一份
 *   node scripts/check-asr-device-rtf.mjs --file x.json --json
 *   node scripts/check-asr-device-rtf.mjs --self-test
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = path.resolve(appRoot, '../..')

export const DEVICE_RTF_SCHEMA = 'literacy-asr-device-rtf/1'
export const MARKER = 'ROUND14_H1'

export const PATHS = Object.freeze({
  evidence: '.agent_workspace/evidence/r14/asr/device-rtf.json',
  schema: '.agent_workspace/evidence/r14/asr/device-rtf.schema.json',
  example: '.agent_workspace/evidence/r14/asr/device-rtf.example.json',
  manifest: 'apps/literacy-app/public/asr/manifest.json',
  readme: '.agent_workspace/evidence/r14/asr/README.md'
})

/** 六条只有真机说了算的门槛；阈值与 manifest.goNoGo 同源，harness 逐条核对。 */
export const DEVICE_GATES = Object.freeze([
  { metric: 'rtf', op: '<=', threshold: 0.5 },
  { metric: 'p95LatencyMs', op: '<=', threshold: 2500 },
  { metric: 'peakMemoryMiB', op: '<=', threshold: 300 },
  { metric: 'longTaskMs', op: '<=', threshold: 100 },
  { metric: 'offlineRestartPass', op: '>=', threshold: 20 },
  { metric: 'faultDrillsOnDevice', op: '>=', threshold: 5 }
])

/** 一段够长的音才算量过：三句话的 p95 说明不了任何事。 */
export const MIN_SESSION = Object.freeze({ utterances: 20, audioSeconds: 60, sampleRate: 16000 })

/** 拒收码稳定不变：报表、README、自检样例三处按它对账。 */
export const RTF_REJECT_CODES = Object.freeze({
  SCHEMA: 'schema-mismatch',
  MARKER: 'marker-missing',
  STATUS: 'status-invalid',
  SIMULATED: 'simulated-true',
  HOST_REUSED: 'host-baseline-reused',
  PREMATURE_DEVICE: 'on-device-true-without-measurement',
  PREMATURE_RTF: 'rtf-without-measurement',
  OWNER: 'owner-missing',
  NOT_ON_DEVICE: 'on-device-false',
  DEVICE_IDENTITY: 'device-identity-missing',
  DEVICE_TIER: 'device-tier-not-mid',
  SERIAL_PLACEHOLDER: 'serial-placeholder',
  PACK_MISMATCH: 'pack-sha-mismatch',
  MEASURED_AT: 'measured-at-invalid',
  RTF_MIRROR: 'rtf-mirror-mismatch',
  RTF_RANGE: 'rtf-out-of-range',
  SESSION: 'samples-too-few',
  GATE_MISSING: 'gate-missing',
  GATE_INCONSISTENT: 'gate-inconsistent',
  EVIDENCE_LOG: 'evidence-log-missing',
  ATTESTATION: 'attestation-missing'
})

/** 模板里那几个「（填…）」留到证据里，等于没人签字。 */
const PLACEHOLDER = /待填|（填|\(填|TODO|TBD|xxx/i

const isHex64 = (v) => typeof v === 'string' && /^[a-f0-9]{64}$/i.test(v)
const isText = (v, min = 3) => typeof v === 'string' && v.trim().length >= min
const isNum = (v) => typeof v === 'number' && Number.isFinite(v)

/**
 * 探针那条腿的判定，原样抄自 `check-round14.mjs` 的 H1。
 * 抄一遍是有意的：不变式要成立，两边算的必须是同一件事。
 */
export function probeWouldPass(doc) {
  const device = doc?.device
  const identified =
    isText(device) ||
    (device &&
      typeof device === 'object' &&
      !Array.isArray(device) &&
      ['model', 'name', 'deviceModel', 'product'].some((k) => isText(device[k])))
  return Boolean(
    doc &&
      doc.onDevice === true &&
      doc.simulated === false &&
      identified &&
      isNum(doc.rtfP95) &&
      doc.rtfP95 >= 0 &&
      doc.rtfP95 <= 0.5
  )
}

/**
 * 核一份真机 RTF 证据。
 *
 * `manifest` 与 `fileExists` 由调用方注入：自检时换成假的，好让这段逻辑
 * 不依赖磁盘也能撞一遍；`doc.example === true` 时跳过整包指纹与日志落盘两条
 * ——模板本来就配不上一台真机。
 */
export function validateDeviceRtf({ doc, manifest, fileExists = () => false }) {
  const errors = []
  const add = (code, message) => errors.push({ code, message })
  const isExample = doc?.example === true

  if (doc?.schema !== DEVICE_RTF_SCHEMA) {
    add(RTF_REJECT_CODES.SCHEMA, `schema 是「${doc?.schema}」，认的是 ${DEVICE_RTF_SCHEMA}`)
  }
  if (doc?.marker !== MARKER) add(RTF_REJECT_CODES.MARKER, `没挂 ${MARKER} 标记`)
  if (doc?.host !== undefined || doc?.projection !== undefined) {
    add(
      RTF_REJECT_CODES.HOST_REUSED,
      '文档里有 host / projection——这是 R13 的主机基准，改个文件名不会让它变成真机测量'
    )
  }
  if (doc?.simulated !== false) {
    add(RTF_REJECT_CODES.SIMULATED, `simulated=${doc?.simulated}，真机证据必须显式写 false`)
  }

  const status = doc?.status
  if (status !== 'measured' && status !== 'not-measured') {
    add(RTF_REJECT_CODES.STATUS, `status 是「${status}」，只认 measured / not-measured`)
    return finish({ doc, errors, verdict: 'invalid', gates: [] })
  }

  if (status === 'not-measured') {
    if (doc.onDevice !== false) {
      add(RTF_REJECT_CODES.PREMATURE_DEVICE, 'status 还是 not-measured，onDevice 却写了 true')
    }
    if (doc.rtfP95 !== null && doc.rtfP95 !== undefined) {
      add(RTF_REJECT_CODES.PREMATURE_RTF, `没测就填了 rtfP95=${doc.rtfP95}`)
    }
    if (!isText(doc.owner) || !isText(doc.blockedBy)) {
      add(RTF_REJECT_CODES.OWNER, '没写清谁欠着这件事（owner）、它卡住了什么（blockedBy）')
    }
    return finish({ doc, errors, verdict: 'awaiting-device', gates: [] })
  }

  if (doc.onDevice !== true) add(RTF_REJECT_CODES.NOT_ON_DEVICE, 'status 是 measured，onDevice 却不是 true')

  const device = doc.device
  const identityFields = ['model', 'androidVersion', 'chipset', 'webView']
  if (!device || typeof device !== 'object' || Array.isArray(device)) {
    add(RTF_REJECT_CODES.DEVICE_IDENTITY, 'device 不是对象——「一台 Android 手机」不算身份')
  } else {
    // androidVersion 短到 "13" 也是合法版本号，别的几项要看得出是什么东西
    const missing = identityFields.filter((k) => !isText(device[k], k === 'androidVersion' ? 1 : 3))
    if (missing.length || !isNum(device.ramGiB)) {
      add(
        RTF_REJECT_CODES.DEVICE_IDENTITY,
        `device 缺 ${[...missing, isNum(device.ramGiB) ? null : 'ramGiB'].filter(Boolean).join('、')}`
      )
    }
    if (device.tier !== 'mid') {
      add(
        RTF_REJECT_CODES.DEVICE_TIER,
        `device.tier=${device.tier}——门槛写的是中端机；高端机跑得快证明不了中端机跑得动`
      )
    }
    if (!isHex64(device.serialHash) || /^(.)\1{63}$/.test(String(device.serialHash))) {
      add(RTF_REJECT_CODES.SERIAL_PLACEHOLDER, 'device.serialHash 不是一个像样的序列号哈希')
    }
  }

  if (!isExample) {
    const pack = doc.pack ?? {}
    if (
      pack.sha256 !== manifest?.sha256 ||
      pack.modelId !== manifest?.modelId ||
      pack.modelVersion !== manifest?.modelVersion
    ) {
      add(
        RTF_REJECT_CODES.PACK_MISMATCH,
        `测的不是随包发出去的那一份：证据 ${pack.modelId}@${pack.modelVersion}/${String(pack.sha256).slice(0, 12)}…，` +
          `清单 ${manifest?.modelId}@${manifest?.modelVersion}/${String(manifest?.sha256).slice(0, 12)}…`
      )
    }
  }

  if (!isText(doc.measuredAt) || Number.isNaN(Date.parse(doc.measuredAt))) {
    add(RTF_REJECT_CODES.MEASURED_AT, `measuredAt「${doc.measuredAt}」不是可解析的时间戳`)
  }

  const rtf = doc.rtf ?? {}
  if (!isNum(rtf.p95) || !isNum(doc.rtfP95) || Math.abs(rtf.p95 - doc.rtfP95) > 1e-9) {
    add(
      RTF_REJECT_CODES.RTF_MIRROR,
      `rtfP95=${doc.rtfP95} 与 rtf.p95=${rtf.p95} 对不上——顶层那个数是给探针看的镜像，不是第二个来源`
    )
  }
  if (!isNum(rtf.p95) || rtf.p95 < 0 || rtf.p95 > 5) {
    add(RTF_REJECT_CODES.RTF_RANGE, `rtf.p95=${rtf.p95} 不是一个说得通的实时因子`)
  }

  const session = doc.session ?? {}
  if (
    !isNum(session.utterances) ||
    session.utterances < MIN_SESSION.utterances ||
    !isNum(session.audioSeconds) ||
    session.audioSeconds < MIN_SESSION.audioSeconds ||
    session.sampleRate !== MIN_SESSION.sampleRate
  ) {
    add(
      RTF_REJECT_CODES.SESSION,
      `采样太少：${session.utterances} 句 / ${session.audioSeconds} 秒 @ ${session.sampleRate} Hz，` +
        `下限 ${MIN_SESSION.utterances} 句 / ${MIN_SESSION.audioSeconds} 秒 @ ${MIN_SESSION.sampleRate} Hz`
    )
  }

  const gates = Array.isArray(doc.gates) ? doc.gates : []
  const gateRows = []
  for (const spec of DEVICE_GATES) {
    const row = gates.find((g) => g && g.metric === spec.metric)
    if (!row) {
      add(RTF_REJECT_CODES.GATE_MISSING, `少了 ${spec.metric} 这条门槛`)
      continue
    }
    if (row.op !== spec.op || row.threshold !== spec.threshold || !isNum(row.measured)) {
      add(
        RTF_REJECT_CODES.GATE_INCONSISTENT,
        `${spec.metric} 的阈值/实测写法不对：${row.op} ${row.threshold}，实测 ${row.measured}`
      )
      continue
    }
    const ok = spec.op === '<=' ? row.measured <= spec.threshold : row.measured >= spec.threshold
    const want = ok ? 'pass' : 'fail'
    if (row.verdict !== want) {
      add(
        RTF_REJECT_CODES.GATE_INCONSISTENT,
        `${spec.metric} 实测 ${row.measured} ${spec.op} ${spec.threshold} 应当是 ${want}，文档里写的是 ${row.verdict}`
      )
    }
    gateRows.push({ ...spec, measured: row.measured, verdict: want })
  }
  if (isNum(rtf.p95) && gateRows.some((g) => g.metric === 'rtf' && g.measured !== rtf.p95)) {
    add(RTF_REJECT_CODES.GATE_INCONSISTENT, 'gates 里的 rtf 实测值与 rtf.p95 不是同一个数')
  }

  const evidence = doc.evidence ?? {}
  if (!isText(evidence.log) || !isText(evidence.command) || !isText(evidence.harness)) {
    add(RTF_REJECT_CODES.EVIDENCE_LOG, 'evidence 缺 log / command / harness——没有执行痕迹的数字不算实测')
  } else if (!isExample && !fileExists(evidence.log)) {
    add(RTF_REJECT_CODES.EVIDENCE_LOG, `evidence.log 指的 ${evidence.log} 不在仓库里`)
  }

  const attestation = doc.attestation ?? {}
  if (!isText(attestation.measuredBy) || !isText(attestation.role) || !isText(attestation.signedAt)) {
    add(RTF_REJECT_CODES.ATTESTATION, 'attestation 缺 measuredBy / role / signedAt——真机测量要有人签字')
  } else if (!isExample && PLACEHOLDER.test(attestation.measuredBy)) {
    add(RTF_REJECT_CODES.ATTESTATION, `attestation.measuredBy 还是模板里的占位「${attestation.measuredBy}」`)
  }

  const verdict = errors.length
    ? 'invalid'
    : isExample
      ? 'example'
      : gateRows.every((g) => g.verdict === 'pass')
        ? 'measured-pass'
        : 'measured-fail'
  return finish({ doc, errors, verdict, gates: gateRows })
}

function finish({ doc, errors, verdict, gates }) {
  return {
    ok: errors.length === 0,
    verdict,
    /** 探针那条腿看这份文件会不会绿。收货台永远比它严：绿而不 ok 的文件就是伪证。 */
    probeWouldPass: probeWouldPass(doc),
    errors,
    gates
  }
}

/* ---------------------------------------------------------------- 自检 */

const FAKE_MANIFEST = Object.freeze({
  sha256: 'b'.repeat(64),
  modelId: 'fake-zipformer-zh',
  modelVersion: '2026-01-01'
})

/** 一份什么都对的真机证据（自检基准）。每条闸都是从它身上改坏出来的。 */
export function goodDeviceRtf() {
  return {
    schema: DEVICE_RTF_SCHEMA,
    marker: MARKER,
    status: 'measured',
    onDevice: true,
    simulated: false,
    measuredAt: '2026-09-20T09:12:44.000Z',
    device: {
      model: 'Redmi Note 12',
      tier: 'mid',
      androidVersion: '13',
      chipset: 'Snapdragon 685',
      ramGiB: 6,
      webView: 'Chrome WebView 126.0.6478.122',
      serialHash: 'c'.repeat(63) + 'd'
    },
    pack: {
      modelId: FAKE_MANIFEST.modelId,
      modelVersion: FAKE_MANIFEST.modelVersion,
      sha256: FAKE_MANIFEST.sha256,
      bytes: 37022120
    },
    session: { utterances: 24, audioSeconds: 118.4, sampleRate: 16000, env: 'quiet', source: 'freeze-set B1' },
    rtfP95: 0.31,
    rtf: { runs: 24, min: 0.19, p50: 0.24, p95: 0.31, max: 0.36 },
    gates: [
      { metric: 'rtf', op: '<=', threshold: 0.5, measured: 0.31, verdict: 'pass' },
      { metric: 'p95LatencyMs', op: '<=', threshold: 2500, measured: 1180, verdict: 'pass' },
      { metric: 'peakMemoryMiB', op: '<=', threshold: 300, measured: 214, verdict: 'pass' },
      { metric: 'longTaskMs', op: '<=', threshold: 100, measured: 82, verdict: 'pass' },
      { metric: 'offlineRestartPass', op: '>=', threshold: 20, measured: 20, verdict: 'pass' },
      { metric: 'faultDrillsOnDevice', op: '>=', threshold: 5, measured: 5, verdict: 'pass' }
    ],
    evidence: {
      log: 'evidence/r14/asr/device-rtf.logcat.txt',
      command: 'npm run test:asr:device -- --serial <adb-serial>',
      harness: 'apps/literacy-app/scripts/bench-asr-rtf.mjs --on-device'
    },
    attestation: { measuredBy: 'QA-03', role: 'Android QA', signedAt: '2026-09-20' }
  }
}

/** 每条闸一个反例：左边是拒收码，右边是「怎么把证据改坏到该被这条拦下」。 */
export const RTF_SELF_TEST_CASES = [
  [RTF_REJECT_CODES.SCHEMA, (d) => { d.schema = 'literacy-asr-rtf-baseline/1' }],
  [RTF_REJECT_CODES.MARKER, (d) => { delete d.marker }],
  [RTF_REJECT_CODES.STATUS, (d) => { d.status = 'done' }],
  [RTF_REJECT_CODES.SIMULATED, (d) => { d.simulated = true }],
  [RTF_REJECT_CODES.HOST_REUSED, (d) => { d.projection = { deviceVerdict: 'unmeasured' } }],
  [RTF_REJECT_CODES.HOST_REUSED, (d) => { d.host = { kind: 'ci-vm' } }],
  [RTF_REJECT_CODES.PREMATURE_DEVICE, (d) => { d.status = 'not-measured'; d.owner = 'Android QA'; d.blockedBy = 'F7' }],
  [RTF_REJECT_CODES.PREMATURE_RTF, (d) => {
    d.status = 'not-measured'
    d.onDevice = false
    d.owner = 'Android QA'
    d.blockedBy = 'F7'
  }],
  [RTF_REJECT_CODES.OWNER, (d) => { d.status = 'not-measured'; d.onDevice = false; d.rtfP95 = null }],
  [RTF_REJECT_CODES.NOT_ON_DEVICE, (d) => { d.onDevice = false }],
  [RTF_REJECT_CODES.DEVICE_IDENTITY, (d) => { d.device = 'Android 手机' }],
  [RTF_REJECT_CODES.DEVICE_IDENTITY, (d) => { delete d.device.chipset }],
  [RTF_REJECT_CODES.DEVICE_TIER, (d) => { d.device.tier = 'high' }],
  [RTF_REJECT_CODES.SERIAL_PLACEHOLDER, (d) => { d.device.serialHash = '0'.repeat(64) }],
  [RTF_REJECT_CODES.PACK_MISMATCH, (d) => { d.pack.sha256 = 'a'.repeat(64) }],
  [RTF_REJECT_CODES.MEASURED_AT, (d) => { d.measuredAt = '待填' }],
  [RTF_REJECT_CODES.RTF_MIRROR, (d) => { d.rtfP95 = 0.12 }],
  [RTF_REJECT_CODES.RTF_RANGE, (d) => { d.rtf.p95 = -1; d.rtfP95 = -1 }],
  [RTF_REJECT_CODES.SESSION, (d) => { d.session.utterances = 3 }],
  [RTF_REJECT_CODES.GATE_MISSING, (d) => { d.gates = d.gates.filter((g) => g.metric !== 'longTaskMs') }],
  [RTF_REJECT_CODES.GATE_INCONSISTENT, (d) => {
    d.gates = d.gates.map((g) => (g.metric === 'peakMemoryMiB' ? { ...g, measured: 512 } : g))
  }],
  [RTF_REJECT_CODES.EVIDENCE_LOG, (d) => { delete d.evidence.log }],
  [RTF_REJECT_CODES.ATTESTATION, (d) => { delete d.attestation.measuredBy }],
  [RTF_REJECT_CODES.ATTESTATION, (d) => { d.attestation.measuredBy = '（填测的人）' }]
]

export function runSelfTest() {
  const failures = []
  const manifest = FAKE_MANIFEST
  const fileExists = (rel) => rel === 'evidence/r14/asr/device-rtf.logcat.txt'

  const clean = validateDeviceRtf({ doc: goodDeviceRtf(), manifest, fileExists })
  if (!clean.ok) failures.push(`干净的证据没过：${clean.errors.map((e) => e.code).join('、')}`)
  if (clean.verdict !== 'measured-pass') failures.push(`干净的证据结论是 ${clean.verdict}`)
  if (!clean.probeWouldPass) failures.push('干净的证据连探针那条腿都点不亮')

  /** 探针会放行、收货台却拦下的那些改法——收货台严过探针，这条是它存在的全部理由。 */
  let stricterThanProbe = 0
  for (const [code, breakIt] of RTF_SELF_TEST_CASES) {
    const doc = goodDeviceRtf()
    breakIt(doc)
    const result = validateDeviceRtf({ doc, manifest, fileExists })
    if (!result.errors.some((e) => e.code === code)) {
      failures.push(`${code} 这条闸没拦住：实得 ${result.errors.map((e) => e.code).join('、') || '全部放行'}`)
    }
    if (result.probeWouldPass && !result.ok) stricterThanProbe += 1
  }
  if (stricterThanProbe < 8) {
    failures.push(
      `只有 ${stricterThanProbe} 种改法能骗过探针却被收货台拦下——收货台没比探针严多少，白装了`
    )
  }

  // 最要紧的一次攻击：只填探针读的那五个字段
  const minimal = {
    onDevice: true,
    simulated: false,
    device: { model: 'Android 真机' },
    rtfP95: 0.21
  }
  const forged = validateDeviceRtf({ doc: minimal, manifest, fileExists })
  if (!forged.probeWouldPass) failures.push('五字段伪证连探针都骗不过，这条攻击样例该改了')
  if (forged.ok) failures.push('五字段伪证在收货台过了——H1 那条腿等于没有闸')

  // 诚实占位：真机没跑，但写清了谁欠着
  const waiting = validateDeviceRtf({
    doc: {
      schema: DEVICE_RTF_SCHEMA,
      marker: MARKER,
      status: 'not-measured',
      onDevice: false,
      simulated: false,
      rtfP95: null,
      owner: 'SKIP owner: Android QA',
      blockedBy: 'freezeChecklist F7 → available=true'
    },
    manifest,
    fileExists
  })
  if (!waiting.ok || waiting.verdict !== 'awaiting-device') {
    failures.push(`诚实占位被拒了：${waiting.errors.map((e) => e.code).join('、')}`)
  }
  if (waiting.probeWouldPass) failures.push('诚实占位居然点亮了探针那条腿')

  return { passed: failures.length === 0, cases: RTF_SELF_TEST_CASES.length + 3, failures }
}

/* ---------------------------------------------------------------- CLI */

export function loadAndValidate(relOrAbs = PATHS.evidence) {
  const abs = path.isAbsolute(relOrAbs) ? relOrAbs : path.join(repoRoot, relOrAbs)
  const doc = JSON.parse(fs.readFileSync(abs, 'utf8'))
  const manifest = JSON.parse(fs.readFileSync(path.join(repoRoot, PATHS.manifest), 'utf8'))
  return validateDeviceRtf({
    doc,
    manifest,
    fileExists: (rel) => fs.existsSync(path.join(repoRoot, '.agent_workspace', rel)) || fs.existsSync(path.join(repoRoot, rel))
  })
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])
if (isMain) {
  const argv = process.argv.slice(2)
  const asJson = argv.includes('--json')
  const at = argv.indexOf('--file')
  const file = at >= 0 ? argv[at + 1] : PATHS.evidence

  if (argv.includes('--self-test')) {
    const result = runSelfTest()
    if (asJson) console.log(JSON.stringify({ marker: MARKER, ...result }, null, 2))
    else {
      for (const failure of result.failures) console.log(`  ✗ ${failure}`)
      console.log(`\n真机 RTF 收货台自检（${MARKER}）：${result.cases - result.failures.length} / ${result.cases} 条通过。`)
    }
    process.exit(result.passed ? 0 : 1)
  }

  const result = loadAndValidate(file)
  if (asJson) {
    console.log(JSON.stringify({ marker: MARKER, file, ...result }, null, 2))
  } else {
    for (const error of result.errors) console.log(`  ✗ [${error.code}] ${error.message}`)
    for (const gate of result.gates) {
      console.log(`  ${gate.metric} ${gate.op} ${gate.threshold} · 实测 ${gate.measured} · ${gate.verdict}`)
    }
    console.log(`\n  ${file}：${result.verdict}（探针那条腿 ${result.probeWouldPass ? '会绿' : '仍红'}）`)
    if (result.verdict === 'awaiting-device') {
      console.log('  真机还没跑——这是当前预期状态，H1 的 deviceRtf 腿红得对。')
    }
  }
  process.exit(result.ok ? 0 : 1)
}
