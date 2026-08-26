/**
 * 音效门面 — 玩法层统一入口。
 *
 * 真正的合成实现在 @/core/audio/sound.js（Tone.js）。这里只做命名适配，
 * 让 useFeedback / TopBar / 各玩法视图共用同一个音频引擎和同一个静音开关，
 * 避免出现「设置里关了音效但某些音还在响」的情况。
 */
import { sound } from '@/core/audio/sound.js'

export function setSoundEnabled(value) {
  sound.setEnabled(value)
}

export const sfx = {
  tap: () => sound.click(),
  correct: () => sound.correct(),
  wrong: () => sound.wrong(),
  star: () => sound.star(),
  levelUp: () => sound.combo(),
}
