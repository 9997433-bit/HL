/**
 * 拍照识字的状态机，把 utils/ocr.js 的流水线包成界面能直接绑的几个 ref。
 *
 *   idle → loading（装引擎，只有第一次会经过）→ reading（认字）→ done / error
 *
 * 界面只关心 phase、progress 和 hint 三样东西；引擎装没装、语言包多大、
 * 哪一步在跑，都在这里收敛成一句中文提示，读屏用户和家长看到的是同一句话。
 */

import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import { describeStep, readPack, recognizePhoto, releaseOcr } from '@/utils/ocr.js'

export function useOcr() {
  const phase = ref('idle')
  const progress = ref(0)
  const step = ref('')
  const error = ref('')
  const result = shallowRef(null)
  const pack = shallowRef({ ready: null, bytes: 0 })

  /** 引擎装好一次就一直在，第二张照片不再经过 loading 这一步。 */
  const engineReady = ref(false)
  const busy = computed(() => phase.value === 'loading' || phase.value === 'reading')

  const packMb = computed(() => (pack.value.bytes / 1024 / 1024).toFixed(1))

  const hint = computed(() => {
    if (phase.value === 'error') return error.value
    if (phase.value === 'loading') return `${step.value || '正在装认字引擎'}…（第一次要等几秒）`
    if (phase.value === 'reading') return `${step.value || '正在看照片里的字'}…`
    if (phase.value === 'done') {
      const hits = result.value?.known.length ?? 0
      return hits ? `认出了 ${hits} 个字，点一个看讲解吧` : '这张没认出字库里的字，换一张试试'
    }
    return '拍一张有汉字的照片，我来认认看'
  })

  async function checkPack() {
    pack.value = await readPack()
    return pack.value.ready
  }

  function onStep(message) {
    step.value = describeStep(message.status)
    const reading = message.status === 'recognizing text'
    if (reading) phase.value = 'reading'
    // 装引擎和认字各占进度条的一半：孩子看到的是一条一直在走的条，而不是两次归零
    progress.value = Math.min(1, (reading ? 0.5 : 0) + (message.progress ?? 0) * 0.5)
  }

  async function run(source) {
    if (busy.value) return null
    error.value = ''
    result.value = null
    progress.value = 0
    step.value = ''
    phase.value = engineReady.value ? 'reading' : 'loading'

    try {
      if (pack.value.ready === null) await checkPack()
      if (pack.value.ready === false) {
        throw new Error('识字包没装上：请重新构建一次 App（npm run build 会自动备好）。')
      }
      const data = await recognizePhoto(source, { onStep })
      engineReady.value = true
      progress.value = 1
      result.value = data
      phase.value = 'done'
      return data
    } catch (err) {
      // wasm 起不来最常见的原因是浏览器太老（没有 SIMD），说清楚比抛堆栈有用
      error.value =
        err?.message?.includes('SIMD') || err?.name === 'CompileError'
          ? '这台设备的浏览器太旧，装不下认字引擎，换新版 Chrome 或 Safari 再试。'
          : `没认成：${err?.message ?? err}`
      phase.value = 'error'
      return null
    }
  }

  function reset() {
    if (busy.value) return
    phase.value = 'idle'
    progress.value = 0
    step.value = ''
    error.value = ''
    result.value = null
  }

  onScopeDispose(() => {
    releaseOcr()
  })

  return { busy, checkPack, error, hint, pack, packMb, phase, progress, reset, result, run, step }
}
