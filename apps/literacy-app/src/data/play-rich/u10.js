/**
 * 富互动 play 分片 u10 —— 这一单元的 11 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u10'

export const UNIT_RICH_PLAYS = [
  {
    char: '红', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小苹果涂得红红的。',
    props: { hero: '🍎', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '黄', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小鸭子涂得黄黄的。',
    props: { hero: '🐤', color: 'yellow', goal: 3 },
    templateFallback: false
  },
  {
    char: '蓝', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把大海涂得蓝蓝的。',
    props: { hero: '🌊', color: 'blue', goal: 3 },
    templateFallback: false
  },
  {
    char: '绿', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小草涂得绿绿的。',
    props: { hero: '🌿', color: 'green', goal: 3 },
    templateFallback: false
  },
  {
    char: '白', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把云朵涂得白白的。',
    props: { hero: '☁️', color: 'white', goal: 3 },
    templateFallback: false
  },
  {
    char: '黑', unit: 'u10', theme: 'color',
    template: 'tap-reveal', interaction: 'tap',
    narration: '天黑了，打开手电看看藏着谁。',
    props: { hero: '⚫', items: ['🦉', '🦇', '⭐'], tool: '🔦', goal: 3 },
    templateFallback: false
  },
  {
    char: '色', unit: 'u10', theme: 'color',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把颜色分一分，红的一边蓝的一边。',
    props: { hero: '🎨', items: [{ item: '🍎', bucket: '红' }, { item: '🍓', bucket: '红' }, { item: '🌊', bucket: '蓝' }, { item: '🫐', bucket: '蓝' }], buckets: [{ label: '红', emoji: '🔴' }, { label: '蓝', emoji: '🔵' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '圆', unit: 'u10', theme: 'shape',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找出圆圆的、一个角也没有的。',
    props: { hero: '⭕', target: '⭕', decoys: ['🔷', '🔺', '⬜'], goal: 3 },
    templateFallback: false
  },
  {
    char: '方', unit: 'u10', theme: 'shape',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找出方方正正、四个角的。',
    props: { hero: '🔷', target: '⬜', decoys: ['⭕', '🔺', '💠'], goal: 3 },
    templateFallback: false
  },
  {
    char: '长', unit: 'u10', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '长的放这边，短的放那边。',
    props: { hero: '📏', items: [{ item: '🐍', bucket: '长' }, { item: '🚂', bucket: '长' }, { item: '🐛', bucket: '短' }, { item: '🚗', bucket: '短' }], buckets: [{ label: '长', emoji: '📏' }, { label: '短', emoji: '📎' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '高', unit: 'u10', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '高的往上摆，矮的往下摆。',
    props: { hero: '🗼', items: [{ item: '🦒', bucket: '高' }, { item: '🌲', bucket: '高' }, { item: '🐕', bucket: '矮' }, { item: '🌱', bucket: '矮' }], buckets: [{ label: '高', emoji: '🗼' }, { label: '矮', emoji: '🏠' }], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
