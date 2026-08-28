/**
 * ROUND11_H1 —— 跟读离线 ASR 的评测跑道：冻结清单 + 儿童评测集骨架 + 五层 Go/No-Go。
 *
 * R10 只把 sherpa-onnx 的 Worker 接线做完了（`available:false`，仓库里一个模型字节都没有）。
 * 缺的不是代码，是「凭什么把 available 置成 true」这条路：靠什么数据测、按哪些线判、
 * 谁来测。这个脚本就是那条路，模型还没来之前它先跑空载——但跑的是同一条路：
 *
 *   1. 清单自检   public/asr/manifest.json 的 freezeChecklist / goNoGo 结构是否完整、
 *                 是否自洽。最要紧的一条：只要还有一条冻结项没做完，available 必须是 false；
 *                 反过来，谁想把 available 改成 true，就得先让这里全绿。
 *   2. 评测集骨架 scripts/data/asr-eval-set.json：≥30 条占位、目标 300 条，
 *                 说话人隔离、年龄/口音/设备/环境/异常类别的覆盖下限都在这里守。
 *                 占位阶段不许有音频进仓库（audio 恒为 null）。
 *   3. 指标管线   用占位条目里的「模拟转写」跑一遍真正的聚合器（speechEval 的逐字对齐），
 *                 算出字符召回、漏字检出、静音误判。**这些数字不是模型指标**——
 *                 它们证明的是「真模型来了以后，这条算分的路是通的、算得对」。
 *                 报表里一律标 simulated，Go/No-Go 里一律记「未实测」。
 *   4. 故障演练   R9 §5 的五类故障（飞行模式 / 模型 404 / wasm 初始化失败 / 麦克风拒绝 /
 *                 低内存杀 Worker），外加整包指纹不符与一次完整安装的正向对照。
 *                 用 fetch / CacheStorage / Worker 的替身在 Node 里跑接线层本身，
 *                 每一类都要在 2 秒内落到 recording 或 listen-only，且不许有跨源请求。
 *   5. Go/No-Go   把上面的实测值填进五层门槛表，算出 go / no-go 并说明卡在哪一层。
 *                 当前预期是 **no-go**：模型未冻结、冻结集未录制。
 *
 * 结论表同步在 .agent_workspace/r11-followread-gonogo.md；评测集设计在
 * .agent_workspace/r11-asr-eval-set.md。
 *
 * R13（ROUND13_H1）在这条路上又加了两段，都写在下面的 ROUND13_H1 常量旁：
 * 冻结集骨架的规模与结构守法（第 2b 段），以及「主机 RTF 基准不许冒充真机」
 * 那道闸（判定之后的 post 段）。口径见 .agent_workspace/r13-asr-freeze-set.md
 * 与 .agent_workspace/r13-asr-android-rtf-baseline.md。
 *
 * R14（ROUND14_H1）再加一段：录音批次 1 的槽位排布与落库闸自检（第 2c 段），
 * 外加一条「排位不是放行」的 post。口径见 .agent_workspace/r14-asr-recording-batch1.md。
 *
 * R14-2（ROUND14_H1，第 2d 段）守的是**放行证据本身**。H1 那三条腿——
 * 放行文档、真机 RTF 证据、实录条数——都是「写上去就算数」的东西，
 * 探针读的又只是其中几个字段。所以这一段把三条腿各配一道比探针严的闸：
 *
 *   - **真机 RTF**：`check-asr-device-rtf.mjs` 那个收货台的自检整段跑一遍，
 *     再撞一次最要紧的攻击——只填探针读的那五个字段。探针会绿，收货台必须红。
 *   - **落库管线**：`pilot-asr-ingest.mjs` 用合成 wav 走一遍完整落库（≤20 条），
 *     harness **重跑一遍再和落盘报表逐字段比对**。报表改不了，走查也进不了生产评测集。
 *   - **放行文档**：`r14-followread-release.md` 的 Go/No-Go 表必须逐条对得上
 *     harness 现算的门槛；实录不到 300 条时，文档里连探针认的那几个 GO 锚点词都不许出现。
 *
 * 口径见 .agent_workspace/r14-followread-release.md。
 *
 * 用法：node scripts/test-asr-eval-set.mjs [--json]
 */

import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'

import { POEM_MAP } from '../src/data/poems.js'
import {
  OFFLINE_ASR,
  PACK_ROLES,
  chooseTier,
  createOfflineRecognizer,
  installOfflinePack,
  packCacheName,
  parseManifest,
  probeOfflinePack
} from '../src/utils/offlineAsr.js'
import { alignChars, evaluate, gradeOf, normalizeTranscript } from '../src/utils/speechEval.js'
import * as deviceRtf from './check-asr-device-rtf.mjs'
import * as pilot from './pilot-asr-ingest.mjs'

const asJson = process.argv.includes('--json')
const appUrl = new URL('../', import.meta.url)
const repoUrl = new URL('../../', appUrl)

const manifestRaw = await readFile(new URL('public/asr/manifest.json', appUrl), 'utf8')
const manifest = JSON.parse(manifestRaw)
const evalSet = JSON.parse(await readFile(new URL('scripts/data/asr-eval-set.json', appUrl), 'utf8'))

/** 仓库里的旁证（文档、基准记录）；缺了就是空串/null，由各自的断言说话。 */
const readRepo = async (rel) => {
  try {
    return await readFile(new URL(rel, repoUrl), 'utf8')
  } catch {
    return ''
  }
}

/** 仓库里的 JSON 旁证；读不到就是 null，由断言说话。 */
const readRepoJson = (rel) => {
  try {
    return JSON.parse(readFileSync(new URL(rel, repoUrl), 'utf8'))
  } catch {
    return null
  }
}

const tests = []
const test = (name, fn) => tests.push({ name, fn })

/* ------------------------------------------------------------------ 约定 */

/** 冻结清单里每一条的合法状态；只有 done 才算这一条过了。 */
const FREEZE_STATUS = ['todo', 'doing', 'done']
/** 冻结清单至少要覆盖这些层，少一层就说明有一整类风险没人认领。 */
const FREEZE_LAYERS = [
  'license',
  'resource',
  'eval-set',
  'text',
  'diagnosis',
  'performance',
  'reliability',
  'governance'
]
/** R9 §5 的五类故障，一类都不许从演练里消失。 */
const FAULT_CLASSES = ['airplane', 'model-404', 'wasm-init', 'mic-denied', 'oom-worker']
/** 降档必须在这个时间内完成，否则孩子会盯着一个转圈的界面。 */
const DEGRADE_BUDGET_MS = 2000

/**
 * ROUND12_H1：模型落库这一轮新增的守法。
 * 落库不等于放行——文件齐全归 files[] 管，能不能给孩子用归 goNoGo 管。
 */
const ROUND12_H1 = Object.freeze({
  shipDoc: '.agent_workspace/r12-followread-ship.md',
  engineHarness: 'apps/literacy-app/scripts/test-asr-engine.mjs'
})

/**
 * ROUND13_H1 —— 这一轮要回答的是「什么时候才敢把 available 翻成 true」。
 *
 * R12 把 35 MiB 落了库，卡住放行的从此只剩两件事：**冻结集没录**（F4）、
 * **真机性能没测**（F7）。这一轮不假装解决它们，只把它们从「等着」变成「可开工」：
 *
 *   1. 冻结集从 36 条长到 ≥50 条，并且按 300 条的配额等比缩样——
 *      不是随手多堆几条，而是让每一格（划分 / 异常类别 / 年龄 / 环境 / 设备）
 *      在骨架阶段就按最终比例站好位。录的时候只往每一格里填，不用重排。
 *   2. 骨架里补上录制真正需要的那一层结构：每个孩子的**同意状态**、
 *      单人条数上限、语料横跨多少首诗。没有这些，录到一半才发现某个家长撤回、
 *      或者某个孩子的口音占了三分之一，整批就得重录。
 *   3. `recorded` / `stage` 这两个进度字段一律**现算核对**：
 *      谁想把「已录 200 条」写进 JSON 而 clips[] 里一条 recorded 都没有，这里当场红。
 *   4. Android RTF 有了主机基准（bench-asr-rtf.mjs）。这条最容易出事：
 *      主机上 RTF 0.12 很好看，但性能层那四条门槛写的是**中端 Android 真机**。
 *      所以主机数只以 `host` 字段出现在报表里，`value` 恒为 null——
 *      性能层必须继续显示「未实测」，Go/No-Go 必须继续 no-go。
 */
const ROUND13_H1 = Object.freeze({
  freezeSpec: '.agent_workspace/r13-asr-freeze-set.md',
  rtfBaselineDoc: '.agent_workspace/r13-asr-android-rtf-baseline.md',
  rtfBaselineEvidence: '.agent_workspace/evidence/r13/asr-rtf/host-baseline.json',
  /** 这几条只有真机说了算；主机基准再好看也不许往里填。 */
  deviceOnlyGates: [
    'p95LatencyMs',
    'rtf',
    'peakMemoryMiB',
    'longTaskMs',
    'offlineRestartPass',
    'faultDrillsOnDevice'
  ],
  freezeStages: ['skeleton', 'recording', 'frozen']
})

/**
 * ROUND14_H1 —— 从「可开工」到「可派工」。
 *
 * R13 交的是一张排好格子的表（骨架 + 同意/配额/上限的结构）。表排好了，
 * 录音这件事仍旧卡在一个很实际的地方：**没人知道第一批录哪 100 条、
 * 录回来凭什么让它进 clips[]**。这一轮补的就是这两件：
 *
 *   1. **批次 1 的 100 个槽位**。300 条拆三批，第一批的槽位全部排进 clips[]，
 *      每条挂 `batch: "B1"`，按 300 条配额的三分之一站位。录的人拿到的是
 *      「C037 找 S13，安静房间用手机，读《风》第一句，照着读完整句」这种指令，
 *      而不是「去录 100 条」。B2/B3 只留号段不排位——现在排出来只会变成一张过期的表。
 *   2. **落库闸**（`ingest-asr-freeze-batch.mjs`）。录音回来是一份交付清单，
 *      逐条过闸：同意书签了没、音频是不是仓库外的指针、双标注有没有走完、
 *      仲裁是不是在两版里挑的、定稿转写和类别对不对得上、单人有没有超配。
 *      这里把那个脚本的自检整段跑一遍——闸自己也得有人守。
 *
 * 这一轮**不会**有任何一条 recorded：VM 里录不出孩子的声音，写进去的就是假数据。
 * 所以最后那条 post 反过来守：基础设施到位不等于放行，`available` 仍旧是 false。
 */
const ROUND14_H1 = Object.freeze({
  batchPlanDoc: '.agent_workspace/r14-asr-recording-batch1.md',
  ingest: 'apps/literacy-app/scripts/ingest-asr-freeze-batch.mjs',
  batchId: 'B1',
  batchSlots: 100,
  /** 批次 1 的说话人下限：300 条要 ≥40 人，第一批先把 18 人推到这个数。 */
  minBatchSpeakers: 30,
  /** 三批号段加起来必须正好是冻结地板，多一条少一条都说明有格子没人认领。 */
  batchIds: ['B1', 'B2', 'B3'],
  /** 文档 §4 那份交付清单模板：它必须真的过得了闸，否则录音现场照着填只会白填一趟。 */
  deliveryExample: 'scripts/fixtures/asr/delivery-b1-example.json'
})

/**
 * ROUND14_H1（R14-2）—— 放行证据的三条腿。
 *
 * H1 变绿要同时满足：`available:true`、实录 ≥300、GO 文档、真机 RTF p95 ≤0.5。
 * 前三条都是文本/数字，探针只能读表面；这里给每一条配一道更严的闸，
 * 并把「什么时候允许说 GO」写成一条互锁——文档不许比数据跑得快。
 */
const ROUND14_H1_RELEASE = Object.freeze({
  releaseDoc: '.agent_workspace/r14-followread-release.md',
  deviceRtfEvidence: '.agent_workspace/evidence/r14/asr/device-rtf.json',
  deviceRtfSchema: '.agent_workspace/evidence/r14/asr/device-rtf.schema.json',
  deviceRtfExample: '.agent_workspace/evidence/r14/asr/device-rtf.example.json',
  evidenceReadme: '.agent_workspace/evidence/r14/asr/README.md',
  pilotReport: '.agent_workspace/evidence/r14/asr/pilot-ingest.json',
  contract: 'apps/literacy-app/scripts/check-asr-device-rtf.mjs',
  pilotTool: 'apps/literacy-app/scripts/pilot-asr-ingest.mjs',
  /** 走查条数的硬上限：它不是配置，是「别拿走查数据充录音进度」那条闸。 */
  pilotCap: 20,
  pilotFloor: 8,
  /**
   * `check-round14.mjs` H1 判「文档是不是 GO」时，拿这三个词当段落锚点
   * （见该脚本 H1 段 releaseOk 那一行）。实录没到 300 条之前，
   * 放行文档里一个都不许出现——否则那条腿会在数据还没到位时误绿。
   */
  goAnchors: /操作结论|verdict|当前决策/i
})

const freezeSpecDoc = await readRepo(ROUND13_H1.freezeSpec)
const rtfBaselineDoc = await readRepo(ROUND13_H1.rtfBaselineDoc)
const batchPlanDoc = await readRepo(ROUND14_H1.batchPlanDoc)
const releaseDoc = await readRepo(ROUND14_H1_RELEASE.releaseDoc)
const evidenceReadme = await readRepo(ROUND14_H1_RELEASE.evidenceReadme)
const deviceRtfDoc = readRepoJson(ROUND14_H1_RELEASE.deviceRtfEvidence)
const deviceRtfSchema = readRepoJson(ROUND14_H1_RELEASE.deviceRtfSchema)
const deviceRtfExample = readRepoJson(ROUND14_H1_RELEASE.deviceRtfExample)
const pilotReport = readRepoJson(ROUND14_H1_RELEASE.pilotReport)
const ingest = await import('./ingest-asr-freeze-batch.mjs')
const rtfBaseline = (() => {
  try {
    return JSON.parse(readFileSync(new URL(ROUND13_H1.rtfBaselineEvidence, repoUrl), 'utf8'))
  } catch {
    return null
  }
})()

/** 孩子读了的那些条目——只有这些能进字符召回。 */
const READ_CATEGORIES = ['normal', 'miss', 'extra', 'repeat', 'tone', 'initial']
/** 孩子没读的那些条目：静音、只有旁人说话。判成「读得好」就是误判。 */
const SILENT_CATEGORIES = ['silence', 'bystander']

/** 评测集的规模与覆盖下限：扩样可以，缩回去当场红灯。 */
const MIN_SPEAKERS_PER_SPLIT = 3
const MIN_CLIPS_PER_SPLIT = 6
const SPLITS = ['dev', 'threshold', 'final']
const REQUIRED_AGE_BANDS = ['4-6', '7-9']
const REQUIRED_ENVIRONMENTS = ['quiet', 'tv', 'far']
const REQUIRED_DEVICES = ['phone', 'tablet']
const CLIP_SECONDS = [3, 10]

const speakerMap = new Map(evalSet.speakers.map((s) => [s.id, s]))
const referenceOf = (clip) => {
  const poem = POEM_MAP.get(clip.poem)
  return normalizeTranscript(poem?.lines?.[clip.line]?.text ?? '')
}
const clipsOf = (categories) => evalSet.clips.filter((c) => categories.includes(c.category))
const ratio = (hit, total) => (total ? hit / total : null)
const pct = (value) => (value === null ? '未实测' : `${(value * 100).toFixed(1)}%`)

/* ------------------------------------------------- 1. 冻结清单（manifest） */

test('清单的 freezeChecklist 每一条都写清了「要做什么、拿什么当证据、卡住什么」', () => {
  const list = manifest.freezeChecklist
  assert.ok(Array.isArray(list), 'freezeChecklist 不是数组')
  assert.ok(list.length >= 8, `冻结项只剩 ${list.length} 条（下限 8）`)
  const seen = new Set()
  for (const item of list) {
    assert.ok(item.id && !seen.has(item.id), `冻结项 id 缺失或重复：${item.id}`)
    seen.add(item.id)
    for (const field of ['layer', 'must', 'evidence', 'status', 'blocks']) {
      assert.ok(item[field], `${item.id} 缺 ${field}——没有证据的清单只是愿望清单`)
    }
    assert.ok(
      FREEZE_STATUS.includes(item.status),
      `${item.id} 的 status「${item.status}」不在 ${FREEZE_STATUS.join('/')} 里`
    )
    assert.ok(FREEZE_LAYERS.includes(item.layer), `${item.id} 的 layer「${item.layer}」没登记`)
  }
  const layers = new Set(list.map((i) => i.layer))
  const missing = FREEZE_LAYERS.filter((l) => !layers.has(l))
  assert.equal(missing.length, 0, `冻结清单少了这些层：${missing.join('、')}`)
})

test('冻结项没做完，available 就必须是 false——清单不许比模型跑得快', () => {
  const pending = manifest.freezeChecklist.filter(
    (item) => item.status !== 'done' && /available=true/.test(item.blocks)
  )
  if (pending.length) {
    assert.equal(
      manifest.available,
      false,
      `还有 ${pending.length} 条冻结项没做完（${pending.map((i) => i.id).join('、')}），` +
        'available 却是 true'
    )
    assert.equal(
      manifest.goNoGo.verdict,
      'no-go',
      '冻结项没做完，goNoGo.verdict 却不是 no-go'
    )
  }
})

/**
 * ROUND12_H1 —— R11 这一条原本写的是「available=false 时 files 必须是空的」。
 * 那条规矩在「一个模型字节都没有」的时候是对的，现在它挡的是正确的事：
 * 落库（文件在包里、指纹冻结、许可证核过）和放行（孩子真用上这一档）本来就该分开——
 * 前者是后者的前置，硬绑在一起只会逼着人要么不落库、要么提前放行。
 *
 * 新规矩：files[] 随时可以齐全，但每一项都要在磁盘上核得上，
 * 而 available 仍旧由 Go/No-Go 说了算（下面那条「结论一致」的断言守着）。
 */
test('落库的文件逐项核得上：路径、字节数、sha256 与清单一致，整包不超预算', () => {
  if (!manifest.files.length) {
    assert.equal(manifest.available, false, 'files 是空的，available 却是 true')
    return
  }
  let total = 0
  for (const file of manifest.files) {
    assert.ok(
      file.path?.startsWith('asr/') && !file.path.includes('..'),
      `文件路径不合法：${file.path}`
    )
    const body = readFileSync(new URL(`public/${file.path}`, appUrl))
    assert.equal(body.length, file.bytes, `${file.path} 实际 ${body.length} 字节，清单写 ${file.bytes}`)
    assert.equal(
      createHash('sha256').update(body).digest('hex'),
      file.sha256,
      `${file.path} 指纹对不上——落库的不是清单里那一份`
    )
    total += body.length
  }
  assert.ok(
    total <= OFFLINE_ASR.maxPackBytes,
    `整包 ${(total / 1048576).toFixed(2)} MiB 超过 60 MiB 预算`
  )
  const roles = new Set(manifest.files.map((f) => f.role))
  const missing = PACK_ROLES.filter((role) => !roles.has(role))
  assert.equal(missing.length, 0, `落库了却少角色：${missing.join('、')}——Worker 起不来`)
})

test('落库的每个文件都写明了上游出处、上游 sha256 与许可证', () => {
  if (!manifest.files.length) return
  const sources = manifest.source?.files ?? []
  assert.ok(manifest.source?.generator, '没写生成脚本，别人复现不了这个包')
  for (const file of manifest.files) {
    const source = sources.find((s) => s.path === file.path)
    assert.ok(source, `${file.path} 没有出处记录`)
    assert.match(source.upstreamSha256 ?? '', /^[a-f0-9]{64}$/, `${file.path} 没记上游 sha256`)
    assert.ok(source.license, `${file.path} 没记许可证`)
  }
})

test('一旦 available 置 true，整份清单必须当场经得起 parseManifest 校验', () => {
  if (manifest.available !== true) {
    // 现在这一档不可用，验的是「不可用要被拒绝」这条路本身没坏
    // （许可证空着就已经被挡下，轮不到 available 那一关）
    assert.throws(() => parseManifest(manifest), /还没有冻结|许可证/)
    return
  }
  const parsed = parseManifest(manifest)
  assert.ok(parsed.bytes <= OFFLINE_ASR.maxPackBytes, '整包超过 60 MiB 预算')
  assert.ok(manifest.license, 'available=true 却没有许可证')
  const notDone = manifest.freezeChecklist.filter((i) => i.status !== 'done')
  assert.equal(notDone.length, 0, `available=true 却还有冻结项没做完：${notDone.map((i) => i.id)}`)
  assert.equal(manifest.goNoGo.verdict, 'go', 'available=true 却没有 go 结论')
})

test('五层门槛表齐全，每条门槛都写明阈值和「谁来测」', () => {
  const layers = manifest.goNoGo?.layers ?? []
  assert.equal(layers.length, 5, `Go/No-Go 只剩 ${layers.length} 层（应为五层）`)
  const names = layers.map((l) => l.name)
  for (const want of ['文本层', '诊断层', '性能层', '资源层', '可靠性层']) {
    assert.ok(names.includes(want), `五层门槛里少了${want}`)
  }
  for (const layer of layers) {
    assert.ok(layer.gates?.length, `${layer.name}一条门槛都没有`)
    for (const gate of layer.gates) {
      assert.ok(gate.metric, `${layer.name}有门槛没写 metric`)
      assert.ok(['>=', '<='].includes(gate.op), `${gate.metric} 的比较符不合法：${gate.op}`)
      assert.equal(typeof gate.threshold, 'number', `${gate.metric} 的阈值不是数字`)
      assert.ok(
        ['eval-set', 'device', 'harness', 'smoke'].includes(gate.measuredBy),
        `${gate.metric} 没说谁来测（measuredBy=${gate.measuredBy}）`
      )
      assert.ok(!('measured' in gate), `${gate.metric} 把实测值写进了清单——实测值会过期，交给 harness 现算`)
    }
  }
})

test('清单指得到评测集、harness、Go/No-Go 三份文件，路径不许飘', () => {
  assert.equal(manifest.evalSet?.spec, 'apps/literacy-app/scripts/data/asr-eval-set.json')
  assert.equal(manifest.evalSet?.harness, 'apps/literacy-app/scripts/test-asr-eval-set.mjs')
  assert.equal(manifest.evalSet?.goNoGo, '.agent_workspace/r11-followread-gonogo.md')
  if (manifest.files.length) {
    assert.equal(
      manifest.evalSet?.engineHarness,
      'apps/literacy-app/scripts/test-asr-engine.mjs',
      '落库了却没挂引擎回归 harness——没人守「这堆字节还跑得动」'
    )
    assert.equal(manifest.evalSet?.ship, ROUND12_H1.shipDoc)
  }
  assert.equal(
    manifest.evalSet?.freezeSpec,
    ROUND13_H1.freezeSpec,
    '清单没挂冻结集口径文档——家长界面上的「冻结集进度」就没有出处'
  )
  assert.equal(manifest.evalSet?.rtfBaseline, ROUND13_H1.rtfBaselineDoc, '清单没挂 RTF 基准文档')
  assert.equal(
    manifest.evalSet.minClips,
    evalSet.freezeSet.skeletonFloor,
    `清单写下限 ${manifest.evalSet.minClips}，评测集写 ${evalSet.freezeSet.skeletonFloor}`
  )
  assert.ok(manifest.evalSet.minClips >= 50, '评测集下限被调到 50 条以下')
  assert.equal(manifest.evalSet.targetClips, 300, '目标规模不再是 300 条')
})

/* --------------------------------------------------------- 2. 评测集骨架 */

test(`评测集不少于 ${evalSet.minClips} 条，目标 ${evalSet.targetClips} 条，id 不重复`, () => {
  assert.equal(evalSet.schema, 'literacy-asr-eval-set/1')
  assert.ok(
    evalSet.clips.length >= evalSet.minClips,
    `只剩 ${evalSet.clips.length} 条（下限 ${evalSet.minClips}）`
  )
  assert.ok(evalSet.targetClips >= 300, '目标规模不该低于 R9 §5 定的 300 条')
  assert.equal(new Set(evalSet.clips.map((c) => c.id)).size, evalSet.clips.length, 'clip id 重复')
  assert.equal(
    new Set(evalSet.speakers.map((s) => s.id)).size,
    evalSet.speakers.length,
    'speaker id 重复'
  )
})

test('每条都能对上一句真实诗句、一个登记过的说话人，时长落在 3–10 秒', () => {
  for (const clip of evalSet.clips) {
    const speaker = speakerMap.get(clip.speaker)
    assert.ok(speaker, `${clip.id} 的说话人 ${clip.speaker} 不在名册里`)
    assert.ok(SPLITS.includes(speaker.split), `${speaker.id} 的 split 不合法：${speaker.split}`)
    const reference = referenceOf(clip)
    assert.ok(reference, `${clip.id} 指向的诗句不存在：${clip.poem} 第 ${clip.line} 句`)
    assert.ok(
      clip.seconds >= CLIP_SECONDS[0] && clip.seconds <= CLIP_SECONDS[1],
      `${clip.id} 时长 ${clip.seconds}s 不在 ${CLIP_SECONDS.join('–')}s 内`
    )
    assert.ok(evalSet.environments[clip.env], `${clip.id} 的环境「${clip.env}」没登记`)
    assert.ok(REQUIRED_DEVICES.includes(clip.device), `${clip.id} 的设备「${clip.device}」没登记`)
    assert.ok(evalSet.categories[clip.category], `${clip.id} 的类别「${clip.category}」没登记`)
  }
})

test('说话人隔离：dev / threshold / final 三份不共用同一个孩子', () => {
  const bySplit = new Map(SPLITS.map((s) => [s, new Set()]))
  for (const clip of evalSet.clips) {
    bySplit.get(speakerMap.get(clip.speaker).split).add(clip.speaker)
  }
  const seen = new Map()
  for (const [split, speakers] of bySplit) {
    assert.ok(
      speakers.size >= MIN_SPEAKERS_PER_SPLIT,
      `${split} 只有 ${speakers.size} 个说话人（下限 ${MIN_SPEAKERS_PER_SPLIT}）`
    )
    const clips = evalSet.clips.filter((c) => speakerMap.get(c.speaker).split === split)
    assert.ok(
      clips.length >= MIN_CLIPS_PER_SPLIT,
      `${split} 只有 ${clips.length} 条（下限 ${MIN_CLIPS_PER_SPLIT}）`
    )
    assert.ok(
      clips.some((c) => SILENT_CATEGORIES.includes(c.category)),
      `${split} 一条静音/旁人说话的负样本都没有——静音误判这条线就成了摆设`
    )
    for (const id of speakers) {
      assert.ok(!seen.has(id), `${id} 同时出现在 ${seen.get(id)} 和 ${split}，说话人泄漏了`)
      seen.set(id, split)
    }
  }
})

test('覆盖面：两个年龄段、三种环境、两种设备、八类异常一个都不少', () => {
  const ages = new Set(evalSet.speakers.map((s) => s.ageBand))
  for (const band of REQUIRED_AGE_BANDS) assert.ok(ages.has(band), `没有 ${band} 岁的孩子`)
  const envs = new Set(evalSet.clips.map((c) => c.env))
  for (const env of REQUIRED_ENVIRONMENTS) assert.ok(envs.has(env), `没有${evalSet.environments[env] ?? env}的样本`)
  const devices = new Set(evalSet.clips.map((c) => c.device))
  for (const device of REQUIRED_DEVICES) assert.ok(devices.has(device), `没有 ${device} 录的样本`)
  const categories = new Set(evalSet.clips.map((c) => c.category))
  for (const category of Object.keys(evalSet.categories)) {
    assert.ok(categories.has(category), `「${evalSet.categories[category]}」这一类一条样本都没有`)
  }
  const genders = new Set(evalSet.speakers.map((s) => s.gender))
  assert.ok(genders.size >= 2, '说话人只有一种性别，子组差距根本算不出来')
})

test('占位阶段一个字节的音频都不进仓库，同意与保存期限写在明处', () => {
  for (const clip of evalSet.clips) {
    if (clip.status === 'placeholder') {
      assert.equal(clip.audio, null, `${clip.id} 还是占位却挂了音频路径`)
      assert.equal(typeof clip.mock, 'string', `${clip.id} 缺少模拟转写，管线自检跑不了`)
    } else {
      assert.equal(clip.status, 'recorded', `${clip.id} 的 status 不合法：${clip.status}`)
      assert.ok(clip.audio, `${clip.id} 标成 recorded 却没有音频`)
      assert.ok(
        !String(clip.audio).startsWith('apps/') && !String(clip.audio).startsWith('/workspace'),
        `${clip.id} 的音频落进了仓库目录：${clip.audio}`
      )
      for (const who of ['a', 'b', 'arbiter']) {
        assert.ok(clip.labels?.[who] !== undefined, `${clip.id} 缺 ${who} 标注——双标注仲裁没走完`)
      }
      assert.equal(clip.mock, undefined, `${clip.id} 已经录到了真音频，模拟转写必须删掉`)
    }
  }
  assert.equal(evalSet.consent.storage, 'out-of-repo', '同意书/音频的存放位置不是仓库外')
  assert.ok(evalSet.consent.retentionMonths > 0, '没写保存期限')
  assert.equal(evalSet.consent.deidentified, true, '没声明去标识化')
})

test('异常样本名副其实：漏字真的短了、多读真的长了、静音真的没出声', () => {
  for (const clip of evalSet.clips) {
    const reference = referenceOf(clip)
    const spoken = normalizeTranscript(clip.spoken)
    if (clip.category === 'silence' || clip.category === 'bystander') {
      assert.equal(spoken, '', `${clip.id} 标成没出声，spoken 却有内容`)
      continue
    }
    if (clip.category === 'normal') {
      assert.equal(spoken, reference, `${clip.id} 标成读全对，内容却和原文不一致`)
    }
    if (clip.category === 'miss') {
      assert.ok(spoken.length < reference.length, `${clip.id} 标成漏字却没少字`)
    }
    if (clip.category === 'extra' || clip.category === 'repeat') {
      assert.ok(spoken.length > reference.length, `${clip.id} 标成多读/重复却没多字`)
    }
    if (clip.category === 'tone' || clip.category === 'initial') {
      assert.equal(spoken, reference, `${clip.id} 是发音错，读的字数和原文该一样`)
      assert.notEqual(
        normalizeTranscript(clip.mock),
        reference,
        `${clip.id} 是发音错，模拟转写却和原文一模一样，测不出东西`
      )
    }
  }
})

/* ------------------------------------- 2b. 冻结集骨架（ROUND13_H1 新增守法） */

const freeze = evalSet.freezeSet ?? {}
const recordedClips = evalSet.clips.filter((c) => c.status === 'recorded')
const clipsBySpeaker = new Map()
for (const clip of evalSet.clips) {
  clipsBySpeaker.set(clip.speaker, (clipsBySpeaker.get(clip.speaker) ?? 0) + 1)
}

test('ROUND13_H1 冻结集骨架 ≥50 条，且 stage / recorded 由 clips[] 现算核对', () => {
  assert.ok(freeze.id, '冻结集没有批次 id——将来无从说清「这批分数是哪一批录的」')
  assert.ok(freeze.skeletonFloor >= 50, `骨架下限被调到 ${freeze.skeletonFloor}（不许低于 50）`)
  assert.equal(
    evalSet.minClips,
    freeze.skeletonFloor,
    `minClips=${evalSet.minClips} 与骨架下限 ${freeze.skeletonFloor} 对不上，两个地板会互相拆台`
  )
  assert.ok(
    evalSet.clips.length >= freeze.skeletonFloor,
    `骨架只剩 ${evalSet.clips.length} 条（下限 ${freeze.skeletonFloor}）`
  )
  assert.equal(freeze.recordedFloor, evalSet.targetClips, '冻结下限与目标条数写成了两个数')
  assert.equal(
    freeze.recorded,
    recordedClips.length,
    `freezeSet.recorded 写 ${freeze.recorded}，clips[] 里实际 recorded ${recordedClips.length} 条——进度不许手写`
  )
  assert.ok(
    ROUND13_H1.freezeStages.includes(freeze.stage),
    `stage「${freeze.stage}」不在 ${ROUND13_H1.freezeStages.join('/')} 里`
  )
  if (freeze.stage === 'frozen') {
    assert.ok(
      recordedClips.length >= freeze.recordedFloor,
      `stage 已经写成 frozen，实录却只有 ${recordedClips.length} 条（下限 ${freeze.recordedFloor}）`
    )
  } else {
    assert.equal(manifest.available, false, `冻结集还停在 ${freeze.stage}，available 却是 true`)
  }
  assert.ok(freezeSpecDoc.length > 800, `冻结集口径文档 ${ROUND13_H1.freezeSpec} 缺失或太薄`)
})

test('ROUND13_H1 骨架按 300 条配额等比缩样：三份划分和八类异常都不许缩成摆设', () => {
  const total = evalSet.clips.length
  const bySplit = new Map(SPLITS.map((s) => [s, 0]))
  for (const clip of evalSet.clips) {
    const split = speakerMap.get(clip.speaker).split
    bySplit.set(split, bySplit.get(split) + 1)
  }
  for (const split of SPLITS) {
    const want = freeze.splitQuota?.[split]
    assert.equal(typeof want, 'number', `${split} 没写配额`)
    const got = bySplit.get(split) / total
    assert.ok(
      Math.abs(got - want) <= freeze.splitTolerance,
      `${split} 占 ${(got * 100).toFixed(1)}%，配额 ${(want * 100).toFixed(0)}%，` +
        `超出 ±${(freeze.splitTolerance * 100).toFixed(0)} 个百分点的容差`
    )
  }
  const counts = new Map()
  for (const clip of evalSet.clips) counts.set(clip.category, (counts.get(clip.category) ?? 0) + 1)
  for (const [category, quota] of Object.entries(freeze.categoryQuota ?? {})) {
    assert.ok(evalSet.categories[category], `配额表里的「${category}」没在 categories 登记`)
    // 等比缩样后再打个折：骨架阶段允许稀，但不许把某一类砍成一条样本充数
    const floor = Math.max(1, Math.round((quota / freeze.recordedFloor) * total * freeze.skeletonFloorRatio))
    assert.ok(
      (counts.get(category) ?? 0) >= floor,
      `「${evalSet.categories[category]}」只有 ${counts.get(category) ?? 0} 条，等比缩样下限 ${floor} 条`
    )
  }
})

test('ROUND13_H1 每个孩子都有同意状态：没签就不许有他的录音，撤回的一条都不许留', () => {
  const states = freeze.consentStates ?? []
  assert.ok(states.length >= 3, '同意状态只写了 ' + states.length + ' 种，撤回这条路没登记')
  for (const speaker of evalSet.speakers) {
    assert.ok(
      states.includes(speaker.consent),
      `${speaker.id} 的同意状态「${speaker.consent}」不在 ${states.join('/')} 里`
    )
    const mine = evalSet.clips.filter((c) => c.speaker === speaker.id)
    if (speaker.consent === 'withdrawn') {
      assert.equal(mine.length, 0, `${speaker.id} 已撤回同意，却还留着 ${mine.length} 条片段`)
    }
    if (speaker.consent !== 'signed') {
      const recorded = mine.filter((c) => c.status === 'recorded')
      assert.equal(
        recorded.length,
        0,
        `${speaker.id} 还没签同意书（${speaker.consent}），却已经有 ${recorded.length} 条实录`
      )
    }
  }
  for (const [id, count] of clipsBySpeaker) {
    assert.ok(
      count <= freeze.maxClipsPerSpeaker,
      `${id} 一个人占了 ${count} 条（上限 ${freeze.maxClipsPerSpeaker}）——他的口音会主导整份分数`
    )
  }
})

test('ROUND13_H1 语料与子组：骨架横跨足够多首诗，每份划分都算得出子组', () => {
  const poems = new Set(evalSet.clips.map((c) => c.poem))
  assert.ok(
    poems.size >= freeze.minPoems,
    `骨架只用了 ${poems.size} 首诗（下限 ${freeze.minPoems}）——语料太窄，分数会跟着几句话走`
  )
  for (const split of SPLITS) {
    const clips = evalSet.clips.filter((c) => speakerMap.get(c.speaker).split === split)
    const speakers = clips.map((c) => speakerMap.get(c.speaker))
    const uniq = (list) => new Set(list).size
    assert.ok(uniq(speakers.map((s) => s.ageBand)) >= 2, `${split} 只有一个年龄段，子组切不开`)
    assert.ok(uniq(speakers.map((s) => s.gender)) >= 2, `${split} 只有一种性别，子组切不开`)
    assert.ok(uniq(speakers.map((s) => s.accent)) >= 2, `${split} 只有一种口音`)
    assert.ok(uniq(clips.map((c) => c.device)) >= 2, `${split} 只有一种设备`)
    assert.equal(
      REQUIRED_ENVIRONMENTS.filter((env) => !clips.some((c) => c.env === env)).length,
      0,
      `${split} 少了环境：${REQUIRED_ENVIRONMENTS.filter((env) => !clips.some((c) => c.env === env)).join('、')}`
    )
  }
})

test('ROUND13_H1 Android RTF 有基准记录，且白纸黑字写明「不是真机」', () => {
  assert.ok(rtfBaselineDoc.length > 800, `RTF 基准文档 ${ROUND13_H1.rtfBaselineDoc} 缺失或太薄`)
  assert.match(rtfBaselineDoc, /RTF|实时因子/, 'RTF 基准文档里找不到 RTF')
  assert.match(
    rtfBaselineDoc,
    /SKIP owner|真机|未实测/,
    'RTF 基准文档没有标明真机那一段仍未实测——这份文档就成了放行的假证据'
  )
  assert.ok(rtfBaseline, `没有主机基准记录 ${ROUND13_H1.rtfBaselineEvidence}，跑一次 npm run bench:asr:rtf`)
  assert.equal(rtfBaseline.onDevice, false, '主机基准把自己标成了真机测量')
  assert.equal(rtfBaseline.marker, 'ROUND13_H1', '主机基准没有挂 ROUND13_H1 标记')
  assert.ok(rtfBaseline.decode?.rtf?.p95 > 0, '主机基准里没有 RTF p95')
  assert.ok(
    rtfBaseline.projection?.deviceVerdict !== 'pass',
    '主机基准替真机下了 pass 结论——推算不是实测'
  )
})

/* --------------------------------- 2c. 录音批次 1（ROUND14_H1 新增守法） */

const batchPlan = freeze.batchPlan ?? {}
const batches = Array.isArray(batchPlan.batches) ? batchPlan.batches : []
const batchOne = batches.find((b) => b.id === ROUND14_H1.batchId)
const batchOneSlots = evalSet.clips.filter((c) => c.batch === ROUND14_H1.batchId)

test('ROUND14_H1 三批号段加起来正好 300 条，每条槽位都认领了一个批次', () => {
  assert.equal(batchPlan.marker, 'ROUND14_H1', '批次计划没挂 ROUND14_H1 标记')
  assert.deepEqual(
    batches.map((b) => b.id),
    ROUND14_H1.batchIds,
    `批次号段是 ${batches.map((b) => b.id).join('/')}，约定的是 ${ROUND14_H1.batchIds.join('/')}`
  )
  const slots = batches.reduce((n, b) => n + b.slots, 0)
  assert.equal(
    slots,
    freeze.recordedFloor,
    `三批加起来 ${slots} 条，冻结地板是 ${freeze.recordedFloor} 条——有格子没人认领`
  )
  for (const clip of evalSet.clips) {
    assert.ok(
      ROUND14_H1.batchIds.includes(clip.batch),
      `${clip.id} 没挂批次（batch=${clip.batch}）——派工时不知道它归谁录`
    )
  }
  // 号段不许交叠：C001–C100 是 B1 的，谁也不能把 B2 的条目塞进第一批
  for (const batch of batches) {
    const [from, to] = batch.range
    const inRange = evalSet.clips.filter((c) => c.id >= from && c.id <= to)
    assert.equal(
      inRange.filter((c) => c.batch !== batch.id).length,
      0,
      `${batch.id} 的号段 ${from}–${to} 里混进了别的批次`
    )
  }
})

test('ROUND14_H1 批次 1 的 100 个槽位全排进了 clips[]，allocated 不许手写', () => {
  assert.ok(batchOne, `批次计划里没有 ${ROUND14_H1.batchId}`)
  assert.equal(batchOne.slots, ROUND14_H1.batchSlots, `批次 1 声明 ${batchOne.slots} 个槽位`)
  assert.equal(
    batchOne.allocated,
    batchOneSlots.length,
    `批次 1 写 allocated=${batchOne.allocated}，clips[] 里实际 ${batchOneSlots.length} 条——排位进度不许手写`
  )
  assert.equal(
    batchOne.allocated,
    batchOne.slots,
    `批次 1 只排了 ${batchOne.allocated}/${batchOne.slots} 个槽位，剩下的没法派工`
  )
  assert.equal(
    batchOne.recorded,
    batchOneSlots.filter((c) => c.status === 'recorded').length,
    '批次 1 的 recorded 与 clips[] 对不上——进度不许手写'
  )
  for (const batch of batches.filter((b) => b.id !== ROUND14_H1.batchId)) {
    assert.equal(
      batch.allocated,
      evalSet.clips.filter((c) => c.batch === batch.id).length,
      `${batch.id} 的 allocated 与 clips[] 对不上`
    )
  }
  const speakers = new Set(batchOneSlots.map((c) => c.speaker))
  assert.ok(
    speakers.size >= ROUND14_H1.minBatchSpeakers,
    `批次 1 只排了 ${speakers.size} 个孩子（下限 ${ROUND14_H1.minBatchSpeakers}）——18 人的口音分布撑不起子组比较`
  )
  assert.equal(
    batchOne.speakers,
    speakers.size,
    `批次 1 写 ${batchOne.speakers} 人，槽位里实际 ${speakers.size} 人`
  )
})

test('ROUND14_H1 批次 1 按 300 条配额的三分之一站位：每一类都排够，录的时候只往格子里填', () => {
  const counts = new Map()
  for (const clip of batchOneSlots) counts.set(clip.category, (counts.get(clip.category) ?? 0) + 1)
  for (const [category, quota] of Object.entries(freeze.categoryQuota ?? {})) {
    const share = (quota / freeze.recordedFloor) * batchOne.slots
    // 允许围着等比值往下浮 40%（tone/initial 是故意往上浮的，见 r13-asr-freeze-set.md §2.1 记的债）
    const floor = Math.max(1, Math.floor(share * 0.6))
    const got = counts.get(category) ?? 0
    assert.ok(
      got >= floor,
      `批次 1 的「${evalSet.categories[category]}」只排了 ${got} 条，等比 ${share.toFixed(1)} 条、下限 ${floor} 条`
    )
  }
  const bySplit = new Map(SPLITS.map((s) => [s, 0]))
  for (const clip of batchOneSlots) {
    const split = speakerMap.get(clip.speaker).split
    bySplit.set(split, bySplit.get(split) + 1)
  }
  for (const split of SPLITS) {
    const got = bySplit.get(split) / batchOneSlots.length
    const want = freeze.splitQuota[split]
    assert.ok(
      Math.abs(got - want) <= freeze.splitTolerance,
      `批次 1 的 ${split} 占 ${(got * 100).toFixed(1)}%，配额 ${(want * 100).toFixed(0)}%`
    )
  }
  const poems = new Set(batchOneSlots.map((c) => c.poem))
  assert.ok(
    poems.size >= freeze.minPoems,
    `批次 1 只用了 ${poems.size} 首诗（下限 ${freeze.minPoems}）`
  )
})

test('ROUND14_H1 落库闸自检全绿：每一条拒收闸都还拦得住它该拦的那种偷懒', () => {
  assert.equal(batchPlan.ingest, ROUND14_H1.ingest, '批次计划没挂落库工具的路径')
  assert.equal(batchPlan.plan, ROUND14_H1.batchPlanDoc, '批次计划没挂批次 1 的口径文档')
  const result = ingest.runSelfTest()
  assert.ok(result.passed, `落库闸自检有 ${result.failures.length} 条没过：${result.failures.join('；')}`)
  assert.ok(
    result.cases >= ingest.SELF_TEST_CASES.length,
    '自检样例比拒收闸还少——有闸没人守着它自己'
  )
  // 每一个拒收码都必须至少有一条反例，否则那条闸删掉也没人知道
  const covered = new Set(ingest.SELF_TEST_CASES.map(([code]) => code))
  for (const code of Object.values(ingest.REJECT_CODES)) {
    assert.ok(covered.has(code), `拒收码 ${code} 没有对应的反例样例`)
  }
})

test('ROUND14_H1 落库闸对着真数据也讲得通：批次 1 的缺口现算得出来', () => {
  const gaps = ingest.planGaps(evalSet, ROUND14_H1.batchId)
  assert.ok(gaps, '落库闸算不出批次 1 的缺口')
  assert.equal(gaps.slots, batchOne.slots, `缺口视图看到 ${gaps.slots} 个槽位`)
  assert.equal(
    gaps.recorded + gaps.pending,
    gaps.slots,
    '已录 + 待录对不上槽位总数——缺口视图自己算错了'
  )
  assert.equal(
    gaps.consentPending.length,
    [...new Set(batchOneSlots.map((c) => c.speaker))].filter(
      (id) => speakerMap.get(id).consent !== 'signed'
    ).length,
    '同意书未签回的人数与名册对不上'
  )
  assert.ok(
    batchPlanDoc.length > 1200,
    `批次 1 口径文档 ${ROUND14_H1.batchPlanDoc} 缺失或太薄——没有它，录的人不知道每一格要填什么`
  )
  assert.match(batchPlanDoc, /\bROUND14_H1\b/, '批次 1 文档没挂 ROUND14_H1 标记')
  assert.match(batchPlanDoc, /同意|consent/i, '批次 1 文档没写同意书怎么走')
  assert.match(batchPlanDoc, /双标注|仲裁/, '批次 1 文档没写双标注与仲裁')
  assert.match(batchPlanDoc, /仓库外|out-of-repo/i, '批次 1 文档没写音频存哪儿')
})

test('ROUND14_H1 文档里那份交付清单模板，拿到闸前面跑一遍是过得去的', () => {
  // 模板过不了闸是最气人的一种错：录音现场照着填一百条，回来发现字段名都对不上
  const example = JSON.parse(readFileSync(new URL(ROUND14_H1.deliveryExample, appUrl), 'utf8'))
  const result = ingest.validateDelivery({ evalSet, delivery: example, referenceOf })
  assert.equal(result.errors.length, 0, `模板本身不合规：${result.errors.join('；')}`)
  assert.equal(
    result.rejected.length,
    0,
    `模板被自己的闸拦下了：${result.rejected.map((r) => `${r.clipId} ${r.code}`).join('、')}`
  )
  assert.ok(result.accepted.length >= 3, `模板只示范了 ${result.accepted.length} 条，讲不清仲裁与改类别`)
  // 三种情形都得示范到：两位一致、两位不一致走仲裁、录出来和排的类别不一样
  assert.ok(
    result.accepted.some((a) => a.labels.arbiter !== null),
    '模板没示范「两位标注不一致时怎么写仲裁」'
  )
  assert.ok(result.accepted.some((a) => a.categoryChanged), '模板没示范「录出来和排的类别不一样」')
  // 模板终究是模板：指纹是编的，别让它有机会真落库
  assert.ok(
    /编|模板|example/i.test(String(example.note ?? '')),
    '交付模板没写明自己是模板——迟早有人拿它 --apply'
  )
})

/* ------------------------------- 2d. 放行证据（ROUND14_H1 · R14-2 新增守法） */

/** 校验一份真机 RTF 证据；日志落盘那一条对着真仓库查。 */
const checkDeviceRtf = (doc) =>
  deviceRtf.validateDeviceRtf({
    doc,
    manifest,
    fileExists: (rel) => {
      try {
        readFileSync(new URL(`.agent_workspace/${rel}`, repoUrl))
        return true
      } catch {
        try {
          readFileSync(new URL(rel, repoUrl))
          return true
        } catch {
          return false
        }
      }
    }
  })

test('ROUND14_H1 真机 RTF 收货台自检全绿，每条拒收码都有反例，阈值与清单同源', () => {
  const result = deviceRtf.runSelfTest()
  assert.ok(result.passed, `收货台自检有 ${result.failures.length} 条没过：${result.failures.join('；')}`)
  const covered = new Set(deviceRtf.RTF_SELF_TEST_CASES.map(([code]) => code))
  for (const code of Object.values(deviceRtf.RTF_REJECT_CODES)) {
    assert.ok(covered.has(code), `拒收码 ${code} 没有对应的反例样例——那条闸删掉也没人知道`)
  }
  // 六条真机门槛的阈值只有一个来源：清单。收货台自带一份是为了能独立运行，
  // 但它必须和清单一个字不差，否则「真机达标」这句话在两处会是两个意思。
  const fromManifest = new Map(
    manifest.goNoGo.layers.flatMap((l) => l.gates).map((g) => [g.metric, g])
  )
  for (const gate of deviceRtf.DEVICE_GATES) {
    const spec = fromManifest.get(gate.metric)
    assert.ok(spec, `清单里没有 ${gate.metric} 这条门槛，收货台却守着它`)
    assert.equal(spec.op, gate.op, `${gate.metric} 的比较符两处不一致`)
    assert.equal(spec.threshold, gate.threshold, `${gate.metric} 的阈值两处不一致`)
    assert.equal(spec.measuredBy, 'device', `${gate.metric} 在清单里不是由 device 测的`)
  }
})

test('ROUND14_H1 真机 RTF 证据三件套齐全：schema / 模板 / 落盘那一份，模板不许被当证据交上去', () => {
  assert.ok(deviceRtfSchema, `缺 ${ROUND14_H1_RELEASE.deviceRtfSchema}`)
  assert.equal(deviceRtfSchema.$id, deviceRtf.DEVICE_RTF_SCHEMA, 'schema 的 $id 和收货台认的对不上')
  assert.ok(
    Array.isArray(deviceRtfSchema.required) && deviceRtfSchema.required.includes('status'),
    'schema 没把 status 列为必填——两种合法状态就分不开了'
  )
  assert.ok(deviceRtfExample, `缺 ${ROUND14_H1_RELEASE.deviceRtfExample}`)
  assert.equal(deviceRtfExample.example, true, '模板没标 example:true——迟早有人直接把它当证据交上去')
  assert.equal(checkDeviceRtf(deviceRtfExample).verdict, 'example', '模板本身不合规，照着填只会白填一趟')

  // 去掉 example 这个字段，模板必须立刻红：它没有真机、没有日志、没人签字
  const asEvidence = structuredClone(deviceRtfExample)
  delete asEvidence.example
  delete asEvidence.exampleNote
  const posing = checkDeviceRtf(asEvidence)
  assert.equal(posing.ok, false, '模板去掉 example 之后居然过了收货台')
  assert.ok(
    posing.errors.some((e) => e.code === deviceRtf.RTF_REJECT_CODES.EVIDENCE_LOG),
    `模板冒充证据时该报「日志没落盘」，实得 ${posing.errors.map((e) => e.code).join('、')}`
  )
  assert.ok(evidenceReadme.length > 800, `缺 ${ROUND14_H1_RELEASE.evidenceReadme} 或太薄`)
})

test('ROUND14_H1 落盘的那份真机证据过得了收货台，且探针能放行的必定收货台也放行', () => {
  assert.ok(deviceRtfDoc, `缺 ${ROUND14_H1_RELEASE.deviceRtfEvidence}`)
  assert.equal(deviceRtfDoc.example, undefined, '落盘证据带着 example 字段——那是模板不是证据')
  const result = checkDeviceRtf(deviceRtfDoc)
  assert.equal(result.ok, true, `落盘证据不合规：${result.errors.map((e) => `${e.code} ${e.message}`).join('；')}`)
  assert.ok(
    ['awaiting-device', 'measured-pass'].includes(result.verdict),
    `落盘证据结论是 ${result.verdict}——要么诚实写着没测，要么真测过且四条门槛都过`
  )

  // 不变式：能点亮 H1 那条腿的文件，收货台必须零错误。
  assert.ok(
    !result.probeWouldPass || result.verdict === 'measured-pass',
    '这份文件足以让 H1 的 deviceRtf 腿变绿，收货台却没给 measured-pass——放行绕过了收货台'
  )

  // 最要紧的一次攻击：只填探针读的那五个字段
  const forged = checkDeviceRtf({
    onDevice: true,
    simulated: false,
    device: { model: 'Android 真机' },
    rtfP95: 0.21
  })
  assert.equal(forged.probeWouldPass, true, '五字段伪证连探针都骗不过，这条攻击样例该改了')
  assert.equal(forged.ok, false, '五字段伪证过了收货台——H1 那条腿等于没有闸')
})

test('ROUND14_H1 真机没跑就得写在明处：性能层四条继续未实测，主机基准只当参考', () => {
  if (deviceRtfDoc?.status === 'measured') return
  assert.equal(deviceRtfDoc.status, 'not-measured', `status 是 ${deviceRtfDoc.status}`)
  assert.equal(deviceRtfDoc.onDevice, false, '没测却写了 onDevice:true')
  assert.equal(deviceRtfDoc.rtfP95, null, `没测却填了 rtfP95=${deviceRtfDoc.rtfP95}`)
  assert.ok(deviceRtfDoc.owner, '没写谁欠着这件事')
  assert.equal(manifest.available, false, '真机没测，available 却是 true')
  const f7 = manifest.freezeChecklist.find((i) => i.id === 'F7')
  assert.notEqual(f7.status, 'done', 'F7 标成 done，可真机 RTF 证据还停在 not-measured')
  // 主机基准可以躺在旁边当锚点，但不许被当成这一条的实测值
  assert.notEqual(
    deviceRtfDoc.rtfP95,
    rtfBaseline?.decode?.rtf?.p95 ?? -1,
    '真机证据里的 rtfP95 就是主机基准那个数——推算不是实测'
  )
})

test('ROUND14_H1 落库管线走查：重跑一遍，和落盘报表逐字段对得上', () => {
  assert.ok(pilotReport, `缺 ${ROUND14_H1_RELEASE.pilotReport}——跑 npm run pilot:asr:ingest -- --write`)
  assert.equal(pilotReport.schema, pilot.PILOT.schema, 'pilot 报表的 schema 不对')
  assert.equal(pilotReport.marker, 'ROUND14_H1', 'pilot 报表没挂 ROUND14_H1 标记')
  assert.ok(
    pilotReport.count >= ROUND14_H1_RELEASE.pilotFloor && pilotReport.count <= ROUND14_H1_RELEASE.pilotCap,
    `走查 ${pilotReport.count} 条，约定的区间是 ${ROUND14_H1_RELEASE.pilotFloor}–${ROUND14_H1_RELEASE.pilotCap} 条`
  )
  assert.equal(pilot.PILOT.cap, ROUND14_H1_RELEASE.pilotCap, '走查上限被改了——它是闸不是配置')

  const fresh = pilot.stableReport(pilot.runPilot({ count: pilotReport.count, keep: false }))
  const committed = structuredClone(pilotReport)
  delete committed.generatedAt
  const drift = [...new Set([...Object.keys(fresh), ...Object.keys(committed)])].filter(
    (key) => JSON.stringify(fresh[key]) !== JSON.stringify(committed[key])
  )
  assert.deepEqual(
    drift,
    [],
    `重跑走查和落盘报表对不上，差在：${drift.join('、')}——报表是手改的，或者波形不再可复现`
  )

  assert.equal(pilotReport.gate.rejected, 0, '走查自己的交付被闸拦下了')
  assert.equal(pilotReport.verifyAudio.problems, 0, '走查的音频指纹核对没通过')
  assert.equal(
    pilotReport.verifyAudio.tamperDetected,
    true,
    '改掉一个字节之后指纹核对居然没发现——--verify-audio 是摆设'
  )
  const codes = new Set(pilotReport.negativeDemo.map((c) => c.code))
  for (const code of pilot.NEGATIVE_CODES) {
    assert.ok(codes.has(code), `负向演示没覆盖 ${code}`)
  }
  assert.ok(pilotReport.gate.arbitrated >= 1, '走查没演到仲裁')
  assert.ok(pilotReport.gate.categoryChanged >= 1, '走查没演到类别漂移')
})

test('ROUND14_H1 走查不是录音：合成音、无人听、一条都没混进生产评测集', () => {
  assert.equal(pilotReport.pilot, true, 'pilot 报表没标自己是走查')
  assert.equal(pilotReport.childRecorded, false, 'pilot 报表把合成音说成了儿童实录')
  assert.equal(pilotReport.countsTowardFreezeSet, false, 'pilot 报表声称自己计入冻结集')
  assert.equal(pilotReport.audio.speech, false, 'pilot 音频被标成了语音')
  assert.equal(pilotReport.audio.kind, 'synthetic-tone', `pilot 音频类型写成了 ${pilotReport.audio.kind}`)
  assert.equal(pilotReport.audio.inRepo, false, 'pilot 音频指针指进了仓库')
  assert.equal(pilotReport.annotations.humanListened, false, 'pilot 标注声称是人听出来的')
  assert.equal(pilotReport.consent.realFamilies, 0, 'pilot 声称有真实家庭参与')
  assert.ok(/合成|非儿童|不是.*儿童/.test(pilotReport.disclaimer), 'pilot 报表没写明自己不是儿童实录')

  assert.equal(pilotReport.sandbox.writesProductionEvalSet, false, 'pilot 声称写了生产评测集')
  assert.notEqual(
    pilotReport.sandbox.freezeSetId,
    freeze.id,
    '走查用的冻结集 id 和生产那份是同一个——分数迟早会被横比到一起'
  )
  assert.ok(
    pilotReport.sandbox.recordedAfter <= ROUND14_H1_RELEASE.pilotCap,
    `沙箱落库 ${pilotReport.sandbox.recordedAfter} 条，超过走查上限`
  )

  const byId = new Map(evalSet.clips.map((c) => [c.id, c]))
  for (const clip of pilotReport.clips) {
    const production = byId.get(clip.clipId)
    assert.ok(production, `走查用了一个不存在的槽位 ${clip.clipId}`)
    assert.equal(production.status, 'placeholder', `${clip.clipId} 在生产评测集里已经是 ${production.status}`)
    assert.equal(production.audio, null, `${clip.clipId} 在生产评测集里挂上了音频指针`)
    assert.equal(production.sha256, undefined, `${clip.clipId} 在生产评测集里留下了走查的指纹`)
    assert.equal(
      ingest.pointsIntoRepo(clip.audio),
      false,
      `${clip.clipId} 的走查音频指针「${clip.audio}」写法上指着仓库`
    )
  }
  assert.equal(pilotReport.production.recorded, 0, '走查报表记下的生产实录不是 0')
  assert.equal(recordedClips.length, 0, '生产评测集里出现了实录——这一轮不该有')
})

test('ROUND14_H1 放行文档结构齐：五层门槛逐条列到、十条冻结项逐条列到、两类证据都指得到', () => {
  assert.ok(
    releaseDoc.length > 2500,
    `放行文档 ${ROUND14_H1_RELEASE.releaseDoc} 缺失或太薄（${releaseDoc.length} 字）`
  )
  assert.match(releaseDoc, /\bROUND14_H1\b/, '放行文档没挂 ROUND14_H1 标记')
  for (const heading of [
    '## 1.',
    '## 2.',
    '## 3.',
    '## 4.',
    '## 5.',
    '## 6.',
    '## 7.',
    '## 8.'
  ]) {
    assert.ok(releaseDoc.includes(heading), `放行文档缺 ${heading} 那一节`)
  }
  // Go/No-Go 表要逐条列到——少一条就说明有一层门槛没人盯着
  for (const layer of manifest.goNoGo.layers) {
    assert.ok(releaseDoc.includes(layer.name), `放行文档的门槛表里没有${layer.name}`)
    for (const gate of layer.gates) {
      assert.ok(releaseDoc.includes(gate.metric), `放行文档的门槛表里没有 ${gate.metric} 这一条`)
    }
  }
  for (const item of manifest.freezeChecklist) {
    assert.ok(releaseDoc.includes(item.id), `放行文档的冻结清单里没有 ${item.id}`)
  }
  for (const ref of [
    ROUND14_H1_RELEASE.deviceRtfEvidence.replace('.agent_workspace/', ''),
    ROUND14_H1_RELEASE.pilotReport.replace('.agent_workspace/', ''),
    ROUND14_H1_RELEASE.contract,
    ROUND14_H1_RELEASE.pilotTool
  ]) {
    assert.ok(releaseDoc.includes(ref), `放行文档没指到 ${ref}`)
  }
  assert.match(releaseDoc, /pilot/i, '放行文档没提走查')
  assert.match(releaseDoc, /合成|非儿童|不是.*儿童/, '放行文档没写明走查不是儿童实录')
  assert.match(releaseDoc, /真机|onDevice/, '放行文档没写真机那一段')
})

/* ------------------------------------------------- 3. 指标管线（模拟转写） */

/**
 * 用占位条目的模拟转写跑一遍真正的聚合器。
 *
 * 再说一次：这些数字**不是模型指标**。模拟转写是我们自己写的，模型换成谁都不会变。
 * 它证明的是三件事——分组切得对（安静 / 噪声）、漏字能被逐字对齐标出来、
 * 没出声的那些条目不会被判成「读得好」。真模型来了，把 mock 换成引擎输出，
 * 同一段代码就出真实指标。
 */
function aggregate(clips, hypothesisOf) {
  const quiet = { hit: 0, total: 0 }
  const noisy = { hit: 0, total: 0 }
  let missDesigned = 0
  let missCaught = 0
  let silentTotal = 0
  let silentAccepted = 0

  for (const clip of clips) {
    const reference = referenceOf(clip)
    const heard = hypothesisOf(clip)

    if (READ_CATEGORIES.includes(clip.category)) {
      const { hits, total } = alignChars(reference, heard)
      const bucket = clip.env === 'quiet' ? quiet : noisy
      bucket.hit += hits
      bucket.total += total
    }

    if (clip.category === 'miss') {
      // 设计上漏掉的是哪几个位置，由「原文 vs 孩子实际读的」定；
      // 能不能查出来，看「原文 vs 识别结果」在同样的位置上是不是也标了 miss。
      const designed = alignChars(reference, normalizeTranscript(clip.spoken)).chars
      const detected = alignChars(reference, heard).chars
      designed.forEach((mark, index) => {
        if (mark.status !== 'miss') return
        missDesigned += 1
        if (detected[index]?.status === 'miss') missCaught += 1
      })
    }

    if (SILENT_CATEGORIES.includes(clip.category)) {
      silentTotal += 1
      const { score } = evaluate({ mode: 'recognition', reference, heard })
      // 「读得好」= 至少拿到铜牌；again 档是「再来一次」，不算误判
      if (gradeOf(score).id !== 'again') silentAccepted += 1
    }
  }

  return {
    quietCharRecall: ratio(quiet.hit, quiet.total),
    noisyCharRecall: ratio(noisy.hit, noisy.total),
    missDetectionRecall: ratio(missCaught, missDesigned),
    silenceFalseAccept: ratio(silentAccepted, silentTotal),
    counts: {
      quiet: quiet.total,
      noisy: noisy.total,
      missDesigned,
      silent: silentTotal
    }
  }
}

const simulated = aggregate(evalSet.clips, (clip) => normalizeTranscript(clip.mock ?? ''))

test('聚合器把安静集和噪声集分开算，两边都有足够的字撑住分母', () => {
  assert.ok(simulated.counts.quiet >= 40, `安静集只有 ${simulated.counts.quiet} 个字`)
  assert.ok(simulated.counts.noisy >= 40, `噪声集只有 ${simulated.counts.noisy} 个字`)
  assert.notEqual(simulated.quietCharRecall, null, '安静集字符召回算不出来')
  assert.notEqual(simulated.noisyCharRecall, null, '噪声集字符召回算不出来')
})

test('漏字检出：设计上漏掉的那几个字，逐字对齐一个不落地标出来', () => {
  assert.ok(simulated.counts.missDesigned >= 5, `漏字样本只标出 ${simulated.counts.missDesigned} 个漏字`)
  assert.equal(
    simulated.missDetectionRecall,
    1,
    `模拟转写与孩子实际读的完全一致时，漏字检出应当是 100%，实得 ${pct(simulated.missDetectionRecall)}`
  )
})

test('静音与旁人说话一律不判「读得好」，误判率为 0', () => {
  assert.ok(simulated.counts.silent >= 4, `没出声的负样本只有 ${simulated.counts.silent} 条`)
  assert.equal(
    simulated.silenceFalseAccept,
    0,
    `静音误判率 ${pct(simulated.silenceFalseAccept)}，孩子没读却被夸了`
  )
})

test('管线对退化敏感：把识别结果换成空串，召回立刻掉到 0', () => {
  const blind = aggregate(evalSet.clips, () => '')
  assert.equal(blind.quietCharRecall, 0, '识别什么都没给，安静集召回却不是 0——聚合器在自说自话')
  assert.equal(blind.noisyCharRecall, 0, '识别什么都没给，噪声集召回却不是 0')
  assert.equal(blind.silenceFalseAccept, 0, '空转写不该被判成读得好')
})

/* --------------------------------------------------------- 4. 故障演练 */

/** 极小的 CacheStorage 替身：只实现 offlineAsr.js 用到的 open/match/put/keys/delete。 */
function cacheShim() {
  const stores = new Map()
  return {
    stores,
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map())
      const store = stores.get(name)
      return {
        async match(url) {
          return store.get(String(url))
        },
        async put(url, response) {
          store.set(String(url), response)
        }
      }
    },
    async keys() {
      return [...stores.keys()]
    },
    async delete(name) {
      return stores.delete(name)
    }
  }
}

const BASE_URI = 'http://127.0.0.1:4173/literacy/'
/** 所有演练发出的请求都记在这里：跨源一个都不许有。 */
const allRequests = []
const crossOrigin = (requests) =>
  requests.filter((url) => !url.startsWith(new URL(BASE_URI).origin)).length

/** 在 Node 里给接线层搭一套浏览器替身；每次演练用完就还原，互不串味。 */
async function withBrowserShims({ fetchImpl, WorkerImpl }, run) {
  const saved = {
    document: globalThis.document,
    caches: globalThis.caches,
    fetch: globalThis.fetch,
    Worker: globalThis.Worker
  }
  const requests = []
  globalThis.document = { baseURI: BASE_URI }
  globalThis.caches = cacheShim()
  globalThis.Worker = WorkerImpl ?? saved.Worker
  globalThis.fetch = async (input, init) => {
    const url = String(input)
    requests.push(url)
    allRequests.push(url)
    if (!fetchImpl) throw new TypeError('这次演练没有准备网络')
    return fetchImpl(url, init)
  }
  try {
    return await run({ requests, caches: globalThis.caches })
  } finally {
    globalThis.document = saved.document
    globalThis.caches = saved.caches
    globalThis.fetch = saved.fetch
    globalThis.Worker = saved.Worker
  }
}

const sha256 = (text) => createHash('sha256').update(text).digest('hex')

/**
 * 一份「什么都对」的清单，用来演练下载成功与整包作废两条路。
 * ROUND12_H1 之后整包是七个角色，演练包也跟着长——少一个角色 parseManifest 就该拒绝，
 * 这正是 D6/D7 要证明的那条线。
 */
const DRILL_ROLES = {
  'wasm-glue': 'asr/models/glue.js',
  'wasm-binary': 'asr/models/engine.wasm',
  'asr-api': 'asr/models/api.js',
  'model-encoder': 'asr/models/encoder.int8.onnx',
  'model-decoder': 'asr/models/decoder.int8.onnx',
  'model-joiner': 'asr/models/joiner.int8.onnx',
  tokens: 'asr/models/tokens.txt'
}

function frozenPack() {
  const files = {}
  const entries = []
  for (const [role, path] of Object.entries(DRILL_ROLES)) {
    const body = `drill-${role}-payload`
    files[path] = body
    entries.push({ path, role, bytes: body.length, sha256: sha256(body) })
  }
  return {
    files,
    manifest: {
      schema: OFFLINE_ASR.schema,
      engine: OFFLINE_ASR.engine,
      available: true,
      modelId: 'drill-zipformer-zh',
      modelVersion: '2026-08-27',
      license: 'Apache-2.0',
      files: entries
    }
  }
}

/** 按脚本行事的 Worker 替身：init 之后怎么表现，由每场演练自己定。 */
function workerShim(behaviour) {
  return class DrillWorker {
    constructor(url, options) {
      this.url = String(url)
      this.options = options
      this.terminated = false
      this.posted = []
    }
    postMessage(message) {
      this.posted.push(message)
      behaviour(message, this)
    }
    terminate() {
      this.terminated = true
    }
  }
}

const drills = []
const drill = (id, faultClass, layer, name, fn) =>
  drills.push({ id, faultClass, layer, name, fn })

/** 默认隐私姿态：家长没打开浏览器识别，所以降档只能落到录音/自评。 */
const DEFAULT_TIER_INPUT = { canRecognize: true, allowRecognition: false, canRecord: true }

drill('D1', 'airplane', 'reliability', '飞行模式：清单都读不到，落回录音档且不触网兜底', async () => {
  return withBrowserShims(
    { fetchImpl: () => Promise.reject(new TypeError('Failed to fetch')) },
    async ({ requests }) => {
      const started = Date.now()
      const probe = await probeOfflinePack()
      const tier = chooseTier({ ...DEFAULT_TIER_INPUT, offlineReady: probe.status === 'ready' })
      const ms = Date.now() - started
      assert.equal(probe.status, 'unavailable', `飞行模式下探测结果是 ${probe.status}`)
      assert.ok(probe.note, '没告诉家长为什么用不了')
      assert.equal(tier, 'recording', `飞行模式降到了 ${tier}`)
      assert.equal(crossOrigin(requests), 0, `演练里出现了跨源请求：${requests.join('、')}`)
      return { ms, detail: `probe=${probe.status} → ${tier}`, requests: requests.length }
    }
  )
})

drill('D2', 'model-404', 'reliability', '模型 404：整包作废、缓存清空，当场降录音档', async () => {
  const pack = frozenPack()
  return withBrowserShims(
    {
      fetchImpl: async (url) => {
        if (url.endsWith('manifest.json')) return new Response(JSON.stringify(pack.manifest))
        if (url.endsWith('glue.js')) return new Response(pack.files['asr/models/glue.js'])
        return new Response('not found', { status: 404 })
      }
    },
    async ({ requests, caches }) => {
      const started = Date.now()
      let failure = null
      try {
        await installOfflinePack()
      } catch (error) {
        failure = error
      }
      const tier = chooseTier({ ...DEFAULT_TIER_INPUT, offlineReady: false, offlineFault: true })
      const ms = Date.now() - started
      assert.ok(failure, '模型 404 了，安装却报成功')
      assert.match(failure.message, /下载失败|HTTP 404/, `失败原因说不清：${failure.message}`)
      assert.equal(caches.stores.size, 0, '半截的包留在了缓存里——下次会在孩子读到一半时崩')
      assert.equal(tier, 'recording', `模型 404 后降到了 ${tier}`)
      assert.equal(crossOrigin(requests), 0, '下载走了第三方地址')
      return { ms, detail: `install 失败「${failure.message}」→ ${tier}`, requests: requests.length }
    }
  )
})

drill('D3', 'wasm-init', 'reliability', 'wasm 初始化失败：Worker 报错即降档，不改用在线识别', async () => {
  const Worker = workerShim((message, worker) => {
    if (message.type === 'init') {
      queueMicrotask(() => worker.onmessage?.({ data: { type: 'error', message: 'wasm 起不来' } }))
    }
  })
  return withBrowserShims({ WorkerImpl: Worker }, async () => {
    const started = Date.now()
    const engine = createOfflineRecognizer(parseManifest(frozenPack().manifest), { timeoutMs: 800 })
    let failure = null
    try {
      await engine.ready
    } catch (error) {
      failure = error
    }
    engine.dispose()
    // 家长此前打开过浏览器识别也不算数：本地引擎崩了不等于允许把音频送上网
    const tier = chooseTier({
      ...DEFAULT_TIER_INPUT,
      allowRecognition: true,
      offlineReady: true,
      offlineFault: true
    })
    const ms = Date.now() - started
    assert.ok(failure, 'Worker 报了错，ready 却还是成功的')
    assert.equal(tier, 'recording', `wasm 起不来之后落到了 ${tier}`)
    return { ms, detail: `ready 失败「${failure.message}」→ ${tier}` }
  })
})

drill('D4', 'mic-denied', 'reliability', '麦克风拒绝：没有音频就没有任何识别档，直接自评', async () => {
  const started = Date.now()
  const denied = chooseTier({ ...DEFAULT_TIER_INPUT, micDenied: true })
  const deniedWithPack = chooseTier({ ...DEFAULT_TIER_INPUT, offlineReady: true, micDenied: true })
  const noMic = chooseTier({ canRecord: false })
  const ms = Date.now() - started
  assert.equal(denied, 'listen-only', `麦克风被拒绝后落到了 ${denied}`)
  assert.equal(
    deniedWithPack,
    'listen-only',
    `离线包装好了但麦克风被拒绝，仍然停在 ${deniedWithPack}——没有音频的识别档是假的`
  )
  assert.equal(noMic, 'listen-only', `没有麦克风的设备落到了 ${noMic}`)
  return { ms, detail: `拒绝→${denied}；装了包也→${deniedWithPack}` }
})

drill('D5', 'oom-worker', 'reliability', '低内存杀 Worker：读到一半没了，收尾也要交出结果并降档', async () => {
  let live = null
  const Worker = workerShim((message, worker) => {
    live = worker
    if (message.type === 'init') {
      queueMicrotask(() => worker.onmessage?.({ data: { type: 'ready' } }))
    }
    if (message.type === 'audio') {
      queueMicrotask(() => worker.onmessage?.({ data: { type: 'partial', text: '床前' } }))
    }
  })
  return withBrowserShims({ WorkerImpl: Worker }, async () => {
    const engine = createOfflineRecognizer(parseManifest(frozenPack().manifest), { timeoutMs: 800 })
    await engine.ready
    engine.accept(new Int16Array(1600))
    await new Promise((r) => setTimeout(r, 10))
    const started = Date.now()
    // 系统把 Worker 杀了：浏览器给的是一个 error 事件，不是一句解释
    live.onerror?.({ message: 'Worker 被系统回收' })
    const tail = await engine.finish(600)
    const tier = chooseTier({ ...DEFAULT_TIER_INPUT, offlineReady: true, offlineFault: true })
    const ms = Date.now() - started
    engine.dispose()
    assert.equal(tail.degraded, true, 'Worker 死了，收尾却报正常')
    assert.equal(tail.text, '床前', '已经听到的那半句被丢了，孩子这一遍白读了')
    assert.equal(tier, 'recording', `Worker 被杀之后落到了 ${tier}`)
    return { ms, detail: `收尾拿回「${tail.text}」(degraded) → ${tier}` }
  })
})

drill('D6', 'hash-mismatch', 'resource', '指纹不符：整包作废，绝不装一份来路不明的模型', async () => {
  const pack = frozenPack()
  const tampered = { ...pack.manifest }
  return withBrowserShims(
    {
      fetchImpl: async (url) => {
        if (url.endsWith('manifest.json')) return new Response(JSON.stringify(tampered))
        if (url.endsWith('glue.js')) return new Response(pack.files['asr/models/glue.js'])
        return new Response('被掉包的二进制')
      }
    },
    async ({ caches }) => {
      const started = Date.now()
      let failure = null
      try {
        await installOfflinePack()
      } catch (error) {
        failure = error
      }
      const ms = Date.now() - started
      assert.ok(failure, '文件被掉包了，安装却报成功')
      assert.match(failure.message, /指纹对不上/, `失败原因说不清：${failure.message}`)
      assert.equal(caches.stores.size, 0, '被掉包的包留在了缓存里')
      return { ms, detail: `install 失败「${failure.message}」`, }
    }
  )
})

drill('D7', 'install-ok', 'resource', '正向对照：清单齐全时整包装得上、探测转 ready、档位升到离线', async () => {
  const pack = frozenPack()
  const fetchImpl = async (url) => {
    if (url.endsWith('manifest.json')) return new Response(JSON.stringify(pack.manifest))
    for (const [path, body] of Object.entries(pack.files)) {
      if (url.endsWith(path)) return new Response(body)
    }
    return new Response('not found', { status: 404 })
  }
  return withBrowserShims({ fetchImpl }, async ({ requests, caches }) => {
    const started = Date.now()
    const steps = []
    const installed = await installOfflinePack({ onProgress: ({ step }) => steps.push(step) })
    const probe = await probeOfflinePack()
    const tier = chooseTier({ ...DEFAULT_TIER_INPUT, offlineReady: probe.status === 'ready' })
    const ms = Date.now() - started
    assert.equal(installed.modelId, 'drill-zipformer-zh')
    assert.ok(steps.includes('verifying'), '装包过程没有核对指纹这一步')
    assert.equal(probe.status, 'ready', `装完之后探测结果是 ${probe.status}`)
    assert.ok(caches.stores.has(packCacheName(installed)), '缓存名没有跟着模型版本走')
    assert.equal(tier, 'offline-asr', `装好了包却停在 ${tier}`)
    assert.equal(crossOrigin(requests), 0, '装包过程走了第三方地址')
    return {
      ms,
      detail: `${installed.files.length} 个文件校验通过 → ${tier}`,
      requests: requests.length
    }
  })
})

const drillRows = []
for (const item of drills) {
  test(`故障演练 ${item.id} · ${item.name}`, async () => {
    const outcome = await item.fn()
    drillRows.push({ ...item, ...outcome })
    if (item.layer === 'reliability') {
      assert.ok(
        outcome.ms <= DEGRADE_BUDGET_MS,
        `${item.id} 用了 ${outcome.ms} ms 才降档（预算 ${DEGRADE_BUDGET_MS} ms）`
      )
    }
  })
}

test(`R9 §5 的五类故障一类都不许少（${FAULT_CLASSES.join('、')}）`, () => {
  const covered = new Set(drillRows.map((r) => r.faultClass))
  const missing = FAULT_CLASSES.filter((c) => !covered.has(c))
  assert.equal(missing.length, 0, `这些故障没有演练：${missing.join('、')}`)
})

/* ------------------------------------------------------------ 先跑测试 */

let failed = 0
const failures = []
for (const { name, fn } of tests) {
  try {
    await fn()
    if (!asJson) console.log(`  ✓ ${name}`)
  } catch (error) {
    failed += 1
    failures.push(`${name}：${error.message}`)
    if (!asJson) console.log(`  ✗ ${name}\n      ${error.message}`)
  }
}

/* --------------------------------------------------------- 5. Go / No-Go */

/**
 * 实测值表。
 *
 * 只往里填**这一轮真跑出来的数**：
 *   - harness 能跑的（故障演练、跨源请求）填真值；
 *   - 需要真模型或真机的（文本层、诊断层、性能层）一律 null，
 *     模拟值单独放在 simulated 字段里，绝不参与判定。
 */
function measure() {
  const reliability = drillRows.filter((r) => r.layer === 'reliability')
  const faultClasses = new Set(drillRows.map((r) => r.faultClass))
  return {
    quietCharRecall: { value: null, simulated: simulated.quietCharRecall },
    noisyCharRecall: { value: null, simulated: simulated.noisyCharRecall },
    missDetectionRecall: { value: null, simulated: simulated.missDetectionRecall },
    silenceFalseAccept: { value: null, simulated: simulated.silenceFalseAccept },
    toneNearPrecision: { value: null },
    subgroupGap: { value: null },
    // ROUND13_H1：性能层这四条只有中端 Android 真机说了算。主机基准放在 host 字段里
    // 供人参考（也给「真机比主机慢多少」留个锚点），value 恒为 null——它不参与判定。
    p95LatencyMs: { value: null, host: rtfBaseline?.tailMs?.p95 ?? null },
    rtf: { value: null, host: rtfBaseline?.decode?.rtf?.p95 ?? null },
    peakMemoryMiB: { value: null, host: rtfBaseline?.memory?.peakRssDeltaMiB ?? null },
    longTaskMs: { value: null, host: rtfBaseline?.chunkMs?.max ?? null },
    packBytesMiB: {
      value: manifest.files.length
        ? manifest.files.reduce((n, f) => n + (f.bytes ?? 0), 0) / 1048576
        : null
    },
    precacheModelBytes: { value: null },
    offlineRestartPass: { value: null },
    faultDrillsProtocol: { value: FAULT_CLASSES.filter((c) => faultClasses.has(c)).length },
    degradeMs: { value: reliability.length ? Math.max(...reliability.map((r) => r.ms)) : null },
    faultDrillsOnDevice: { value: null },
    crossOriginRequests: { value: crossOrigin(allRequests) }
  }
}

function verdictOf(gate, measured) {
  const entry = measured[gate.metric]
  if (!entry || entry.value === null || entry.value === undefined) return 'unmeasured'
  const ok = gate.op === '>=' ? entry.value >= gate.threshold : entry.value <= gate.threshold
  return ok ? 'pass' : 'fail'
}

const measured = measure()
const layerRows = manifest.goNoGo.layers.map((layer) => {
  const gates = layer.gates.map((gate) => ({
    ...gate,
    measured: measured[gate.metric]?.value ?? null,
    simulated: measured[gate.metric]?.simulated ?? null,
    host: measured[gate.metric]?.host ?? null,
    verdict: verdictOf(gate, measured)
  }))
  const status = gates.some((g) => g.verdict === 'fail')
    ? 'fail'
    : gates.every((g) => g.verdict === 'pass')
      ? 'pass'
      : 'unmeasured'
  return { id: layer.id, name: layer.name, status, gates }
})

const blockers = [
  ...manifest.freezeChecklist.filter((i) => i.status !== 'done').map((i) => `${i.id} ${i.must}`),
  ...layerRows
    .filter((l) => l.status !== 'pass')
    .map((l) => `${l.name}：${l.gates.filter((g) => g.verdict !== 'pass').map((g) => g.metric).join('、')}`)
]
const verdict = blockers.length ? 'no-go' : 'go'

/** 判定跑完之后才能验的几条；和上面的 test() 一样计入总数与退出码。 */
const afterVerdict = []
const post = (name, fn) => afterVerdict.push({ name, fn })

post('清单里写死的结论要和这次实测算出来的结论一致', () => {
  assert.equal(
    manifest.goNoGo.verdict,
    verdict,
    `清单写着 ${manifest.goNoGo.verdict}，这次实测算出来是 ${verdict}`
  )
  if (verdict === 'no-go') {
    assert.equal(manifest.available, false, '结论是 no-go，available 却是 true')
  }
})

/**
 * ROUND13_H1 最后一道闸。前面那条守的是「清单别和实测说两套话」，
 * 这条守的是**放行只有一个入口**：available 为真，当且仅当这次实测算出来是 go。
 * 少了它，「清单写 go、available 写 true、可是冻结集一条没录」也能自洽——
 * 因为两份谎话是一致的。
 */
post('ROUND13_H1 available 只能由 Go/No-Go 说了算，没有第二个开关', () => {
  assert.equal(
    manifest.available === true,
    verdict === 'go',
    `available=${manifest.available}，本次实测结论 ${verdict} —— 放行与判定脱钩了`
  )
  if (verdict !== 'go') {
    assert.ok(blockers.length > 0, '结论不是 go，却一条阻塞都列不出来')
  }
})

/**
 * ROUND13_H1：主机基准不许冒充真机。
 * bench-asr-rtf.mjs 在这台 VM 上量出的 RTF 好看得很，但性能层写的是中端 Android。
 * 只要真机没跑，这四条就必须停在「未实测」，性能层就必须继续拖着 Go/No-Go。
 */
post('ROUND13_H1 主机基准只当参考：真机那几条门槛仍旧未实测', () => {
  for (const metric of ROUND13_H1.deviceOnlyGates) {
    assert.equal(
      measured[metric]?.value ?? null,
      null,
      `${metric} 被填上了实测值，可这一轮一台真机都没跑`
    )
  }
  const perf = layerRows.find((l) => l.name === '性能层')
  assert.equal(perf?.status, 'unmeasured', `性能层状态是 ${perf?.status}，真机没测就不该有结论`)
  if (rtfBaseline) {
    assert.ok(
      perf.gates.some((g) => g.metric === 'rtf' && g.host !== null),
      '主机 RTF 基准没有出现在报表里——白测了'
    )
  }
})

/**
 * ROUND14_H1：把格子排好、把闸装上，都不等于可以放行。
 *
 * 这条守的是这一轮最容易被误读的地方——批次 1 有 100 个槽位、有落库工具、
 * 有交付清单模板，看上去「录音这件事做完了」。实际上一条录音都没有：
 * VM 里录不出孩子的声音。所以 F4 必须还是 todo，实录必须还是 0，
 * stage 必须还没离开 skeleton，available 必须还是 false。
 */
post('ROUND14_H1 排位与落库工具都不是放行凭据：实录仍是 0，available 仍是 false', () => {
  assert.equal(recordedClips.length, 0, `clips[] 里出现了 ${recordedClips.length} 条实录——这一轮不该有`)
  assert.equal(batchOne.recorded, 0, '批次 1 声称录了东西，可 clips[] 里一条都没有')
  assert.equal(batchOne.stage, 'planned', `批次 1 的 stage 是 ${batchOne.stage}，没落库就不该往前走`)
  assert.equal(freeze.stage, 'skeleton', `冻结集 stage 是 ${freeze.stage}，实录 0 条就不该离开 skeleton`)
  assert.equal(manifest.available, false, '基础设施到位就把 available 翻成了 true')
  const f4 = manifest.freezeChecklist.find((i) => i.id === 'F4')
  assert.equal(f4.status, 'todo', `F4 标成了 ${f4.status}，可实录还是 0/${freeze.recordedFloor}`)
})

/**
 * ROUND14_H1（R14-2）—— **文档不许比数据跑得快。**
 *
 * `check-round14.mjs` 判「放行文档算不算 GO」时，拿三个词当段落锚点
 * （`操作结论` / `verdict` / `当前决策`）。那段正则有个缝：只要文档里
 * 随便哪儿出现过其中一个词，那条腿就会绿——哪怕整篇写的都是 NO-GO。
 *
 * 缝在探针里，补在这里：实录没到 300 条、`available` 还是 false 的时候，
 * 放行文档里一个锚点词都不许出现，而且开头 400 字内必须写着 NO-GO。
 * 于是 H1 的 release 腿在数据到位之前**红得确定**，不是靠谁自觉。
 *
 * 真到了可以放行的那天，把结论小节的标题改成锚点词、把 NO-GO 换成 GO，
 * 这条断言的前置条件（实录 ≥300）也已经不成立了——两边同时松开，顺序不会反。
 */
post('ROUND14_H1 放行文档与数据互锁：实录没到 300 条，文档里不许出现 GO 锚点词', () => {
  const releaseReady = manifest.available === true && recordedClips.length >= freeze.recordedFloor
  if (releaseReady) {
    assert.match(releaseDoc, ROUND14_H1_RELEASE.goAnchors, '数据到位了，放行文档却还没写结论小节')
    return
  }
  const found = releaseDoc.match(ROUND14_H1_RELEASE.goAnchors)
  assert.equal(
    found,
    null,
    `实录 ${recordedClips.length}/${freeze.recordedFloor}、available=${manifest.available}，` +
      `放行文档里却出现了 GO 锚点词「${found?.[0]}」——H1 的 release 腿会因此误绿`
  )
  assert.match(
    releaseDoc.slice(0, 400),
    /NO-GO/i,
    '放行文档开头 400 字里没有 NO-GO——探针拿这一段判结论，写在末尾等于没写'
  )
})

/**
 * ROUND14_H1（R14-2）—— 走查与模板都不是放行凭据。
 *
 * 这一轮多了两样看上去很像「做完了」的东西：一份跑通了的落库走查（12 条实录！）
 * 和一份填得满满当当的真机 RTF 模板。它们都不能让 `available` 动一下：
 * 走查用的是合成音，模板测的是一台不存在的机器。
 */
post('ROUND14_H1 走查与模板都不是放行凭据：available 仍是 false，真机仍未实测', () => {
  assert.equal(manifest.available, false, '合成音走查和真机模板把 available 翻成了 true')
  assert.equal(freeze.recorded, 0, `冻结集实录写着 ${freeze.recorded}——走查数据不计入 300 条`)
  assert.equal(pilotReport.production.available, false, '走查报表记下的 available 不是 false')
  const rtfResult = checkDeviceRtf(deviceRtfDoc)
  assert.notEqual(
    rtfResult.verdict,
    'measured-pass',
    '真机 RTF 证据给出了 measured-pass，可这一轮一台真机都没跑'
  )
  assert.equal(
    measured.rtf.value,
    null,
    'rtf 被填上了实测值——真机证据还停在 not-measured'
  )
})

for (const { name, fn } of afterVerdict) {
  tests.push({ name })
  try {
    fn()
    if (!asJson) console.log(`  ✓ ${name}`)
  } catch (error) {
    failed += 1
    failures.push(`${name}：${error.message}`)
    if (!asJson) console.log(`  ✗ ${name}\n      ${error.message}`)
  }
}

/* ------------------------------------------------------------------ 输出 */

const VERDICT_LABEL = { pass: '达标', fail: '未达标', unmeasured: '未实测' }
const fmt = (metric, value) => {
  if (value === null || value === undefined) return '—'
  if (/Recall|Accept|Precision|Gap|rtf/i.test(metric)) return Number(value).toFixed(3)
  return String(Number(value.toFixed ? value.toFixed(2) : value))
}

if (asJson) {
  console.log(
    JSON.stringify(
      {
        marker: 'ROUND14_H1',
        lineage: ['ROUND11_H1', 'ROUND12_H1', 'ROUND13_H1', 'ROUND14_H1'],
        manifest: {
          available: manifest.available,
          modelId: manifest.modelId,
          modelVersion: manifest.modelVersion,
          freezeDone: manifest.freezeChecklist.filter((i) => i.status === 'done').length,
          freezeTotal: manifest.freezeChecklist.length
        },
        evalSet: {
          clips: evalSet.clips.length,
          speakers: evalSet.speakers.length,
          target: evalSet.targetClips,
          stage: evalSet.stage
        },
        freezeSet: {
          id: freeze.id,
          stage: freeze.stage,
          skeleton: evalSet.clips.length,
          skeletonFloor: freeze.skeletonFloor,
          recorded: recordedClips.length,
          recordedFloor: freeze.recordedFloor,
          poems: new Set(evalSet.clips.map((c) => c.poem)).size,
          consentSigned: evalSet.speakers.filter((s) => s.consent === 'signed').length,
          batches: batches.map((b) => ({
            id: b.id,
            slots: b.slots,
            allocated: evalSet.clips.filter((c) => c.batch === b.id).length,
            recorded: evalSet.clips.filter((c) => c.batch === b.id && c.status === 'recorded').length,
            stage: b.stage
          }))
        },
        rtfBaseline: rtfBaseline && {
          onDevice: rtfBaseline.onDevice,
          hostRtfP95: rtfBaseline.decode?.rtf?.p95 ?? null,
          projection: rtfBaseline.projection ?? null
        },
        simulated,
        drills: drillRows.map((r) => ({
          id: r.id,
          faultClass: r.faultClass,
          layer: r.layer,
          name: r.name,
          ms: r.ms,
          detail: r.detail
        })),
        goNoGo: { verdict, layers: layerRows, blockers },
        passed: tests.length - failed,
        tests: tests.length,
        failures
      },
      null,
      2
    )
  )
} else {
  console.log('')
  console.log(
    `  评测集：${evalSet.clips.length} 条占位 / 目标 ${evalSet.targetClips} 条，` +
      `${evalSet.speakers.length} 个说话人，dev/threshold/final 说话人隔离`
  )
  console.log(
    `  冻结集 ${freeze.id}（${freeze.stage}）：骨架 ${evalSet.clips.length}/${freeze.skeletonFloor} 条 · ` +
      `实录 ${recordedClips.length}/${freeze.recordedFloor} 条 · ` +
      `${new Set(evalSet.clips.map((c) => c.poem)).size} 首诗 · ` +
      `同意已签 ${evalSet.speakers.filter((s) => s.consent === 'signed').length}/${evalSet.speakers.length} 人`
  )
  console.log(
    `  批次计划（ROUND14_H1）：` +
      batches
        .map(
          (b) =>
            `${b.id} ${evalSet.clips.filter((c) => c.batch === b.id && c.status === 'recorded').length}` +
            `/${evalSet.clips.filter((c) => c.batch === b.id).length} 已录（槽位 ${b.slots}，${b.stage}）`
        )
        .join(' · ') +
      ` —— 落库走 ${ROUND14_H1.ingest}`
  )
  console.log(
    `  管线自检（模拟转写，不是模型指标）：安静 ${pct(simulated.quietCharRecall)} · ` +
      `噪声 ${pct(simulated.noisyCharRecall)} · 漏字检出 ${pct(simulated.missDetectionRecall)} · ` +
      `静音误判 ${pct(simulated.silenceFalseAccept)}`
  )
  console.log('')
  for (const row of drillRows) {
    console.log(`  [演练 ${row.id}] ${row.name}：${row.detail}（${row.ms} ms）`)
  }
  console.log('')
  for (const layer of layerRows) {
    console.log(`  ${layer.name}（${VERDICT_LABEL[layer.status]}）`)
    for (const gate of layer.gates) {
      const line =
        `    ${gate.metric} ${gate.op} ${gate.threshold}` +
        ` · 实测 ${fmt(gate.metric, gate.measured)}` +
        (gate.simulated !== null ? `（模拟 ${fmt(gate.metric, gate.simulated)}）` : '') +
        (gate.host !== null ? `（主机 ${fmt(gate.metric, gate.host)}，不计入）` : '') +
        ` · ${VERDICT_LABEL[gate.verdict]} · 由 ${gate.measuredBy} 测`
      console.log(line)
    }
  }
  const done = manifest.freezeChecklist.filter((i) => i.status === 'done').length
  console.log('')
  console.log(
    `  冻结清单：${done}/${manifest.freezeChecklist.length} 条完成；` +
      `模型 ${manifest.modelId}@${manifest.modelVersion}，available=${manifest.available}`
  )
  console.log(`  Go/No-Go：${verdict.toUpperCase()}${blockers.length ? `，卡在 ${blockers.length} 处` : ''}`)
  for (const item of blockers.slice(0, 6)) console.log(`    · ${item}`)
  if (blockers.length > 6) console.log(`    · …另有 ${blockers.length - 6} 处`)
  if (rtfBaseline) {
    console.log(
      `  主机 RTF 基准（${ROUND13_H1.rtfBaselineEvidence}，onDevice=${rtfBaseline.onDevice}）：` +
        `p95 ${rtfBaseline.decode?.rtf?.p95} · 推算中端 Android ` +
        `${rtfBaseline.projection?.androidRtfBand?.join('–') ?? '—'}（${rtfBaseline.projection?.deviceVerdict}）`
    )
  }
  console.log(
    `\n跟读评测跑道（ROUND14_H1）：${tests.length - failed} / ${tests.length} 项通过，` +
      `${drillRows.length} 场故障演练。`
  )
}

process.exit(failed ? 1 : 0)
