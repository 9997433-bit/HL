/**
 * 富互动 play 分片 u13 —— 这一单元的 13 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u13'

export const UNIT_RICH_PLAYS = [
  {
    char: '走', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '一步一步慢慢走，走路要小心。',
    props: { hero: '🥾', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '跑', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '快跑！两只脚都离开地面了。',
    props: { hero: '💨', dir: 'right', goal: 5 },
    templateFallback: false
  },
  {
    char: '跳', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用力一蹬，往上跳三下。',
    props: { hero: '🤸', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '坐', unit: 'u13', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '两个人坐在土地上，就是坐。',
    props: { hero: '🧎', parts: ['人', '人', '土'], goal: 3 },
    templateFallback: false
  },
  {
    char: '站', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '站直了，两只脚立在地上不动。',
    props: { hero: '🚏', dir: 'up', goal: 2 },
    templateFallback: false
  },
  {
    char: '吃', unit: 'u13', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '啊呜——把好吃的一口一口吃掉。',
    props: { hero: '😋', items: ['🍎', '🍌', '🍞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '喝', unit: 'u13', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '咕咚咕咚，把水喝光。',
    props: { hero: '🥤', items: ['💧', '💧', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拿', unit: 'u13', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '伸出手，把东西握住拿起来。',
    props: { hero: '🤲', parts: ['🍎', '🧸'], goal: 2 },
    templateFallback: false
  },
  {
    char: '唱', unit: 'u13', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '张开嘴唱一首歌，啦啦啦。',
    props: { hero: '🎤', sound: '啦', goal: 3 },
    templateFallback: false
  },
  {
    char: '笑', unit: 'u13', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '嘴角越翘越高，笑得好开心。',
    props: { hero: '😄', stages: ['🙂', '😀', '😄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '哭', unit: 'u13', theme: 'feeling',
    template: 'rain-catch', interaction: 'drag',
    narration: '眼泪掉下来了，用纸巾接住它。',
    props: { hero: '😢', items: ['💧', '💧'], tool: '🧻', goal: 2 },
    templateFallback: false
  },
  {
    char: '打', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '挥挥手，把小球打出去。',
    props: { hero: '🏓', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '玩', unit: 'u13', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '挑一样玩具，玩得开开心心。',
    props: { hero: '🧸', items: ['⚽', '🪀', '🧩'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
