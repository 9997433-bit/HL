/**
 * 中文朗读的兼容出口，实现见 utils/audio.js。
 * 保留这些旧名字是为了不动已经在用它们的页面，新代码请直接用 audio.js。
 */

import { cancelSpeech, speak as audioSpeak, speechSupported } from './audio.js'

export function isSpeechSupported() {
  return speechSupported
}

export function speak(text, opts = {}) {
  return audioSpeak(text, opts)
}

export function stopSpeaking() {
  cancelSpeech()
}

/** 旧接口：嗓音列表由 audio.js 内部按需加载，这里不需要再做预热。 */
export function primeSpeech() {}
