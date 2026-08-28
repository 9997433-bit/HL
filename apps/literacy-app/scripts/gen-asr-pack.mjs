/**
 * ROUND12_H1 —— 把跟读的离线评测包真正落进仓库。
 *
 * R11 交付的是「凭什么把 available 置成 true」那条路（冻结清单 + 五层门槛 + 评测跑道），
 * 仓库里一个模型字节都没有。这个脚本是那条路上的第一步 F1：**逐文件自托管**。
 *
 * 它做四件事，每一件都可复现：
 *
 *   1. 取运行时。sherpa-onnx 官方 release 的 WASM 产物（Apache-2.0），只留三个文件：
 *      Emscripten 胶水 JS、wasm 二进制、以及 createOnlineRecognizer 那层 JS API。
 *      官方产物里那份 190 MB 的 .data（英文大模型，--preload-file 打进去的）整个丢掉。
 *   2. 改一处胶水。胶水里 loadPackage() 的元数据写死了 .data 里每个文件的偏移；
 *      我们不带 .data，所以把它改成空包，改完由 Worker 在运行时用 FS_createDataFile
 *      把模型写进 MEMFS。**全文只改这一处**，改前改后的 sha256 都记在清单的 source 里，
 *      任何人都能用 --verify 复核。
 *   3. 取模型。中文流式 Zipformer transducer 的 **int8 量化档**（zh-14M，Apache-2.0），
 *      encoder / decoder / joiner / tokens 四个文件，按固定 revision 拉取。
 *   4. 写清单。public/asr/manifest.json 的 files[] 逐项 path/role/bytes/sha256 现算，
 *      整包超 60 MiB 当场报错——预算不是写在文档里的，是脚本会拦的。
 *
 * 用法：
 *   node scripts/gen-asr-pack.mjs            # 下载 + 落库 + 回写清单
 *   node scripts/gen-asr-pack.mjs --verify   # 不下载，只核对已落库文件与清单是否一致
 *
 * 下载缓存落在 .cache/asr-pack/（已 gitignore），重跑不会再拉一遍网络。
 */

import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import fsp from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const packDir = path.join(appRoot, 'public/asr/models')
const manifestPath = path.join(appRoot, 'public/asr/manifest.json')
const cacheDir = path.join(appRoot, '.cache/asr-pack')
const verifyOnly = process.argv.includes('--verify')

/** 换模型 = 换评分规则：这三个常量一动，modelVersion 必须跟着动（清单 F10）。 */
const RUNTIME = {
  project: 'k2-fsa/sherpa-onnx',
  tag: 'v1.12.15',
  asset: 'sherpa-onnx-wasm-simd-v1.12.15-en-asr-zipformer.tar.bz2',
  license: 'Apache-2.0'
}
const MODEL = {
  repo: 'csukuangfj/sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23',
  revision: '204ad334e2e683fd295359930cc16fc0432a23ac',
  license: 'Apache-2.0'
}
export const MODEL_ID = 'sherpa-onnx-streaming-zipformer-zh-14M-int8'
export const MODEL_VERSION = '2023-02-23+wasm1.12.15'
const MAX_PACK_BYTES = 60 * 1024 * 1024
/** files[].path 是站点根相对的——门禁、smoke、运行时三处都按发出去的那个路径找文件。 */
const PACK_PREFIX = 'asr/models/'

/**
 * 只带走这几个文件。角色名就是 Worker 装引擎时认的那几个 key，
 * 少一个都起不来（见 src/workers/sherpaAsrWorker.js 的 boot()）。
 */
const RUNTIME_FILES = [
  { member: 'sherpa-onnx-wasm-main-asr.js', out: 'sherpa-onnx-wasm-main-asr.js', role: 'wasm-glue', type: 'text/javascript', patch: true },
  { member: 'sherpa-onnx-wasm-main-asr.wasm', out: 'sherpa-onnx-wasm-main-asr.wasm', role: 'wasm-binary', type: 'application/wasm' },
  { member: 'sherpa-onnx-asr.js', out: 'sherpa-onnx-asr.js', role: 'asr-api', type: 'text/javascript' }
]
const MODEL_FILES = [
  { member: 'encoder-epoch-99-avg-1.int8.onnx', out: 'encoder.int8.onnx', role: 'model-encoder', type: 'application/octet-stream' },
  { member: 'decoder-epoch-99-avg-1.int8.onnx', out: 'decoder.int8.onnx', role: 'model-decoder', type: 'application/octet-stream' },
  { member: 'joiner-epoch-99-avg-1.int8.onnx', out: 'joiner.int8.onnx', role: 'model-joiner', type: 'application/octet-stream' },
  { member: 'tokens.txt', out: 'tokens.txt', role: 'tokens', type: 'text/plain' }
]
/** 引擎回归用的一条上游示例音频（同一个 Apache-2.0 仓库），不是儿童冻结集。 */
const ENGINE_FIXTURE = {
  member: 'test_wavs/0.wav',
  out: path.join(appRoot, 'scripts/fixtures/asr/upstream-zh-0.wav')
}

/**
 * Emscripten `--preload-file` 会把 .data 里每个文件的字节区间写死在胶水里。
 * 我们不带官方那份 .data（里面是 190 MB 的英文模型），所以把包改成空的；
 * 模型改由 Worker 在 onRuntimeInitialized 之后 FS_createDataFile 写进 MEMFS。
 */
const PACKAGE_RE = /loadPackage\(\{"files":\[.*?\],"remote_package_size":\d+\}\)/
const EMPTY_PACKAGE = 'loadPackage({"files":[],"remote_package_size":0})'

const sha256 = (buffer) => createHash('sha256').update(buffer).digest('hex')
const mib = (bytes) => `${(bytes / 1048576).toFixed(2)} MiB`

async function download(url, into) {
  if (fs.existsSync(into)) return fsp.readFile(into)
  await fsp.mkdir(path.dirname(into), { recursive: true })
  process.stdout.write(`  ↓ ${url}\n`)
  const response = await fetch(url)
  if (!response.ok) throw new Error(`${url} 下载失败（HTTP ${response.status}）`)
  const body = Buffer.from(await response.arrayBuffer())
  await fsp.writeFile(into, body)
  return body
}

function untar(archive, into, members) {
  fs.mkdirSync(into, { recursive: true })
  // 归档里的条目形如 ./sherpa-onnx-wasm-simd-…/file，前导 ./ 也算一层
  const args = ['xjf', archive, '-C', into, '--strip-components=2', '--wildcards']
  const result = spawnSync('tar', [...args, ...members.map((m) => `*/${m}`)], { encoding: 'utf8' })
  if (result.status !== 0) throw new Error(`解包失败：${result.stderr || result.stdout}`)
}

function patchGlue(source) {
  const original = source.toString('utf8')
  const found = original.match(PACKAGE_RE)
  if (!found) throw new Error('胶水里找不到 loadPackage 元数据——上游产物结构变了，先读一遍再改脚本')
  if (original.split(PACKAGE_RE).length !== 2) throw new Error('胶水里有多处 loadPackage，拒绝盲改')
  return {
    patched: Buffer.from(original.replace(PACKAGE_RE, EMPTY_PACKAGE), 'utf8'),
    replaced: found[0].slice(0, 120)
  }
}

async function build() {
  await fsp.mkdir(packDir, { recursive: true })
  await fsp.mkdir(path.dirname(ENGINE_FIXTURE.out), { recursive: true })

  /* 1. 运行时 */
  const archive = path.join(cacheDir, RUNTIME.asset)
  await download(
    `https://github.com/${RUNTIME.project}/releases/download/${RUNTIME.tag}/${RUNTIME.asset}`,
    archive
  )
  const extracted = path.join(cacheDir, 'runtime')
  if (!fs.existsSync(path.join(extracted, RUNTIME_FILES[0].member))) {
    untar(archive, extracted, RUNTIME_FILES.map((f) => f.member))
  }

  const entries = []
  const sources = []

  for (const file of RUNTIME_FILES) {
    const raw = await fsp.readFile(path.join(extracted, file.member))
    let body = raw
    let note = '原样自托管'
    if (file.patch) {
      const { patched, replaced } = patchGlue(raw)
      body = patched
      note = `仅改写 loadPackage 元数据为空包（原值前 120 字符：${replaced}…）`
    }
    await fsp.writeFile(path.join(packDir, file.out), body)
    entries.push({ path: `${PACK_PREFIX}${file.out}`, role: file.role, bytes: body.length, sha256: sha256(body), type: file.type })
    sources.push({
      path: `${PACK_PREFIX}${file.out}`,
      from: `${RUNTIME.project}@${RUNTIME.tag}/${RUNTIME.asset}!${file.member}`,
      upstreamSha256: sha256(raw),
      license: RUNTIME.license,
      note
    })
  }

  /* 2. 模型 */
  const base = `https://huggingface.co/${MODEL.repo}/resolve/${MODEL.revision}`
  for (const file of MODEL_FILES) {
    const raw = await download(`${base}/${file.member}`, path.join(cacheDir, 'model', file.member))
    await fsp.writeFile(path.join(packDir, file.out), raw)
    entries.push({ path: `${PACK_PREFIX}${file.out}`, role: file.role, bytes: raw.length, sha256: sha256(raw), type: file.type })
    sources.push({
      path: `${PACK_PREFIX}${file.out}`,
      from: `hf:${MODEL.repo}@${MODEL.revision}/${file.member}`,
      upstreamSha256: sha256(raw),
      license: MODEL.license,
      note: '原样自托管（int8 量化档）'
    })
  }

  /* 3. 引擎回归音频（上游示例，成人朗读，只验引擎不验模型好坏） */
  const wav = await download(`${base}/${ENGINE_FIXTURE.member}`, path.join(cacheDir, 'model', ENGINE_FIXTURE.member))
  await fsp.writeFile(ENGINE_FIXTURE.out, wav)

  const total = entries.reduce((n, e) => n + e.bytes, 0)
  if (total > MAX_PACK_BYTES) {
    throw new Error(`整包 ${mib(total)} 超过 60 MiB 预算——换更小的量化档，别改预算`)
  }

  /* 4. 回写清单 */
  const manifest = JSON.parse(await fsp.readFile(manifestPath, 'utf8'))
  manifest.modelId = MODEL_ID
  manifest.modelVersion = MODEL_VERSION
  manifest.license = MODEL.license
  manifest.sha256 = sha256(Buffer.concat(entries.map((e) => Buffer.from(e.sha256, 'hex'))))
  manifest.files = entries
  manifest.source = {
    runtime: { ...RUNTIME, url: `https://github.com/${RUNTIME.project}/releases/tag/${RUNTIME.tag}` },
    model: { ...MODEL, url: `https://huggingface.co/${MODEL.repo}/tree/${MODEL.revision}` },
    generator: 'apps/literacy-app/scripts/gen-asr-pack.mjs',
    engineFixture: {
      path: 'apps/literacy-app/scripts/fixtures/asr/upstream-zh-0.wav',
      from: `hf:${MODEL.repo}@${MODEL.revision}/${ENGINE_FIXTURE.member}`,
      sha256: sha256(wav),
      note: '上游示例音频（成人普通话），只用于引擎回归；不属于儿童冻结集'
    },
    files: sources
  }
  await fsp.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)

  console.log('')
  for (const entry of entries) console.log(`  ${entry.role.padEnd(14)} ${entry.path.padEnd(38)} ${mib(entry.bytes).padStart(10)}  ${entry.sha256.slice(0, 16)}…`)
  console.log(`\n  整包 ${mib(total)} / 预算 60 MiB；清单已回写（available 仍由 Go/No-Go 决定，本脚本不碰）。`)
}

async function verify() {
  const manifest = JSON.parse(await fsp.readFile(manifestPath, 'utf8'))
  let total = 0
  let bad = 0
  for (const file of manifest.files ?? []) {
    const full = path.join(appRoot, 'public', file.path)
    let body
    try {
      body = await fsp.readFile(full)
    } catch {
      console.log(`  ✗ ${file.path} 不在磁盘上`)
      bad += 1
      continue
    }
    const okBytes = body.length === file.bytes
    const okHash = sha256(body) === file.sha256
    total += body.length
    if (okBytes && okHash) console.log(`  ✓ ${file.path} ${mib(body.length)}`)
    else {
      console.log(`  ✗ ${file.path} bytes=${okBytes} sha256=${okHash}`)
      bad += 1
    }
  }
  console.log(`\n  整包 ${mib(total)} / 预算 60 MiB；${bad ? `${bad} 项对不上` : '逐文件核对通过'}。`)
  if (bad || total > MAX_PACK_BYTES) process.exit(1)
}

if (verifyOnly) await verify()
else await build()
