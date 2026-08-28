/**
 * 在 Node 里按 src/workers/sherpaAsrWorker.js 的 boot() 装起落库的那一包。
 *
 * 抽出来是因为现在有两个脚本要用它：`test-asr-engine.mjs`（落库回归，问的是
 * 「这堆字节还跑不跑得动」）和 `bench-asr-rtf.mjs`（性能基准，问的是「跑多快」）。
 * 装法必须只有一份——两个脚本各抄一遍的话，哪天 Worker 改了装法，
 * 走岔的会是其中一个，而另一个还在报绿。
 *
 * 装法与 Worker 保持逐条一致：非模块胶水用 new Function 递 Module、
 * 空包 getPreloadedPackage、模型运行时写进 MEMFS、createOnlineRecognizer
 * 从 asr-api 那份 JS 里取。
 */

import assert from 'node:assert/strict'
import fs from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
export const publicRoot = path.join(appRoot, 'public')
export const asrRoot = path.join(publicRoot, 'asr')

/** 与 sherpaAsrWorker.js 的 FS_NAMES 保持一致；两边不同步就解不出字。 */
export const FS_NAMES = {
  'model-encoder': 'encoder.onnx',
  'model-decoder': 'decoder.onnx',
  'model-joiner': 'joiner.onnx',
  tokens: 'tokens.txt'
}

export const readManifest = () =>
  JSON.parse(fs.readFileSync(path.join(asrRoot, 'manifest.json'), 'utf8'))

export const bytesOf = (rel) => fs.readFileSync(path.join(publicRoot, rel))

export async function bootEngine(files) {
  const pick = (role) => files.find((f) => f.role === role)
  const glue = bytesOf(pick('wasm-glue').path).toString('utf8')
  const wasm = bytesOf(pick('wasm-binary').path)

  const Module = {
    wasmBinary: wasm.buffer.slice(wasm.byteOffset, wasm.byteOffset + wasm.byteLength),
    getPreloadedPackage: () => new ArrayBuffer(0),
    print: () => {},
    printErr: () => {}
  }
  const started = new Promise((resolve, reject) => {
    Module.onRuntimeInitialized = resolve
    Module.onAbort = (reason) => reject(new Error(`wasm 起不来：${reason}`))
  })
  // 胶水是非模块脚本，跑起来就地改 Module；Node 分支要用到 require/__dirname
  new Function('Module', 'require', '__dirname', glue)(Module, createRequire(import.meta.url), asrRoot)
  await started

  for (const [role, name] of Object.entries(FS_NAMES)) {
    Module.FS_createDataFile('/', name, new Uint8Array(bytesOf(pick(role).path)), true, true, true)
  }

  const api = new Function(
    'module',
    `${bytesOf(pick('asr-api').path).toString('utf8')}\n;return createOnlineRecognizer;`
  )({ exports: {} })
  return { Module, createOnlineRecognizer: api }
}

/** 只认 16 kHz 单声道 16-bit PCM——跟读链送进引擎的也是这个格式。 */
export function readWav(file) {
  const raw = fs.readFileSync(file)
  let offset = 12
  let sampleRate = 0
  let channels = 0
  let bits = 0
  let data = null
  while (offset + 8 <= raw.length) {
    const id = raw.toString('ascii', offset, offset + 4)
    const size = raw.readUInt32LE(offset + 4)
    if (id === 'fmt ') {
      channels = raw.readUInt16LE(offset + 10)
      sampleRate = raw.readUInt32LE(offset + 12)
      bits = raw.readUInt16LE(offset + 22)
    } else if (id === 'data') {
      data = raw.subarray(offset + 8, offset + 8 + size)
    }
    offset += 8 + size + (size % 2)
  }
  assert.equal(channels, 1, 'fixture 不是单声道')
  assert.equal(bits, 16, 'fixture 不是 16-bit PCM')
  const samples = new Float32Array(data.length / 2)
  for (let i = 0; i < samples.length; i += 1) samples[i] = data.readInt16LE(i * 2) / 32768
  return { sampleRate, samples }
}
