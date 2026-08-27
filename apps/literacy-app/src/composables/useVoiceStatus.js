/**
 * 把 audio.js 的朗读能力探测包成响应式的。
 *
 * 嗓音列表是异步到位的：Chrome 冷启动时第一次 `getVoices()` 返回空数组，
 * 之后才发 `voiceschanged`；而少数 WebView 压根不发这个事件。
 * 所以这里既订阅事件，也在头几秒轮询几次兜底，
 * 避免界面永远停在「还在找嗓音」或者错误地断言「没有中文嗓音」。
 */

import { getCurrentScope, onScopeDispose, ref } from 'vue'
import { onVoicesChanged, voiceStatus } from '@/utils/audio.js'

const POLL_INTERVAL = 500
const POLL_TRIES = 8

export function useVoiceStatus() {
  const status = ref(voiceStatus())

  const unsubscribe = onVoicesChanged((next) => {
    status.value = next
  })

  let tries = 0
  const timer = setInterval(() => {
    status.value = voiceStatus()
    if (status.value !== 'pending' || ++tries >= POLL_TRIES) clearInterval(timer)
  }, POLL_INTERVAL)

  const stop = () => {
    unsubscribe()
    clearInterval(timer)
  }

  if (getCurrentScope()) onScopeDispose(stop)

  return { status, stop }
}
