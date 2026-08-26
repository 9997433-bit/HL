/**
 * 音效的兼容出口。
 *
 * 实现只有一份，在 utils/audio.js 里。早期这里有一套独立的 WebAudio 实现，
 * 结果是家长面板里关掉「音效」只能静音其中一套，另一套照响；
 * 现在统一转发过去，静音开关对全站生效。
 *
 * 新代码请直接 import '@/utils/audio.js'。
 */

import { sfx as audioSfx, setSoundEnabled } from './audio.js'

export const sfx = {
  ...audioSfx,
  /** 旧名字：升级 / 通关的欢呼声。 */
  levelUp: audioSfx.celebrate
}

export function setSfxMuted(muted) {
  setSoundEnabled(!muted)
}
