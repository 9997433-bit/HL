/**
 * 富互动 play 分片 u33 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u33'

export const UNIT_RICH_PLAYS = [
  {
    char: '声', unit: 'u33', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '张开嘴发出声，大声喊一喊。',
    props: { hero: '📣', sound: '喂', goal: 3 },
    templateFallback: false
  },
  {
    char: '音', unit: 'u33', theme: 'school',
    template: 'pair-match', interaction: 'drag',
    narration: '每样东西都有自己的声音。',
    props: { hero: '🎵', pairs: [{ a: '🐄', b: '哞' }, { a: '🚗', b: '嘀' }, { a: '🔔', b: '叮' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '歌', unit: 'u33', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '一起唱首歌，啦啦啦啦啦。',
    props: { hero: '🎶', sound: '啦啦', goal: 3 },
    templateFallback: false
  },
  {
    char: '曲', unit: 'u33', theme: 'school',
    template: 'trace-path', interaction: 'drag',
    narration: '跟着弯弯曲曲的调子画一条线。',
    props: { hero: '🎼', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '舞', unit: 'u33', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '举起手转个圈，跳支小舞。',
    props: { hero: '💃', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '球', unit: 'u33', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用力一踢，把球踢进球门。',
    props: { hero: '⚽', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '戏', unit: 'u33', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '做游戏啦，点点要用上什么。',
    props: { hero: '🎭', items: ['🎲', '🃏', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '力', unit: 'u33', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '使出力气，把石头一点点举高。',
    props: { hero: '💪', stages: ['🪨', '💪', '🏋️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '气', unit: 'u33', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '吹一口气，气球越吹越大。',
    props: { hero: '🌬️', stages: ['💨', '🫧', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '睡', unit: 'u33', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '躺到床上，眼睛闭着睡着了。',
    props: { hero: '😴', stages: ['🛏️', '😪', '😴'], goal: 3 },
    templateFallback: false
  },
  {
    char: '醒', unit: 'u33', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '闹钟一响，小朋友就醒过来。',
    props: { hero: '⏰', stages: ['⏰', '😴', '醒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '休', unit: 'u33', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '一个人靠着树，就是休息的休。',
    props: { hero: '🌳', parts: ['亻', '木'], goal: 2 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
