/**
 * 富互动 play 分片 u3 —— 这一单元的 13 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u3'

export const UNIT_RICH_PLAYS = [
  {
    char: '手', unit: 'u3', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '数数小手，一根一根点手指。',
    props: { hero: '✋', items: ['👆', '👆', '👆', '👆', '👆'], goal: 5 },
    templateFallback: false
  },
  {
    char: '目', unit: 'u3', theme: 'body',
    template: 'morph-story', interaction: 'sequence',
    narration: '把眼睛竖起来，就变成目字。',
    props: { hero: '👁️', stages: ['👁️', '👀', '目'], goal: 3 },
    templateFallback: false
  },
  {
    char: '耳', unit: 'u3', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '捂住耳朵再放开，听听什么在响。',
    props: { hero: '👂', sound: '叮咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '心', unit: 'u3', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '手放在胸口，心怦怦怦地跳。',
    props: { hero: '❤️', sound: '怦怦', goal: 3 },
    templateFallback: false
  },
  {
    char: '牛', unit: 'u3', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '摸摸牛角，大牛哞地叫一声。',
    props: { hero: '🐄', sound: '哞', goal: 3 },
    templateFallback: false
  },
  {
    char: '羊', unit: 'u3', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '数数草地上的小羊，咩咩咩。',
    props: { hero: '🐑', items: ['🐑', '🐑', '🐑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '鸟', unit: 'u3', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '轻轻往上一挥，小鸟飞起来了。',
    props: { hero: '🐦', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '中', unit: 'u3', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁正好在正中间？点中它。',
    props: { hero: '🎯', target: '🎯', decoys: ['⬅️', '➡️', '⬆️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '不', unit: 'u3', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '摇摇头说不，分清能做和不能做。',
    props: { hero: '🙅', items: [{ item: '📚', bucket: '可以' }, { item: '🧸', bucket: '可以' }, { item: '🔥', bucket: '不可以' }, { item: '🔌', bucket: '不可以' }], buckets: [{ label: '可以', emoji: '👍' }, { label: '不可以', emoji: '🙅' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '好', unit: 'u3', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '女和子放在一起，心里就觉得好。',
    props: { hero: '👍', items: ['👧', '👶'], goal: 2 },
    templateFallback: false
  },
  {
    char: '头', unit: 'u3', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '点点头上都有什么：头发眼睛嘴巴。',
    props: { hero: '🙂', items: ['💇', '👁️', '👄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '牙', unit: 'u3', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '张开嘴，把白牙齿一颗颗刷干净。',
    props: { hero: '🦷', items: ['🦷', '🦷', '🦷'], tool: '🪥', goal: 3 },
    templateFallback: false
  },
  {
    char: '兔', unit: 'u3', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小兔子一蹦一蹦，往上跳三下。',
    props: { hero: '🐰', dir: 'up', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
