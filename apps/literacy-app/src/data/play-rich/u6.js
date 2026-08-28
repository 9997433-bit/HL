/**
 * 富互动 play 分片 u6 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u6'

export const UNIT_RICH_PLAYS = [
  {
    char: '风', unit: 'u6', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '呼——手指一划，风把树叶吹跑。',
    props: { hero: '🍃', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '雨', unit: 'u6', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '下雨啦，撑起小伞接住雨滴。',
    props: { hero: '🌧️', items: ['💧', '💧', '💧', '💧'], tool: '☂️', goal: 4 },
    templateFallback: false
  },
  {
    char: '云', unit: 'u6', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '白云飘飘，推着它慢慢走。',
    props: { hero: '☁️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '雪', unit: 'u6', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '雪花飘下来，用手心接住它。',
    props: { hero: '❄️', items: ['❄️', '❄️', '❄️'], tool: '🧤', goal: 3 },
    templateFallback: false
  },
  {
    char: '地', unit: 'u6', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '脚下的大地上，都长着什么。',
    props: { hero: '🌍', items: ['🌱', '🌳', '🐛'], goal: 3 },
    templateFallback: false
  },
  {
    char: '石', unit: 'u6', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小石头一块一块摞高。',
    props: { hero: '🪨', parts: ['🪨', '🪨', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '草', unit: 'u6', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '春天到，小草从土里钻出来。',
    props: { hero: '🌱', stages: ['🟫', '🌱', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '树', unit: 'u6', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '树苗长成大树，还结了果子。',
    props: { hero: '🌳', stages: ['🌱', '🌳', '🍎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '星', unit: 'u6', theme: 'nature',
    template: 'tap-reveal', interaction: 'tap',
    narration: '夜里点一点，星星一闪一闪亮。',
    props: { hero: '⭐', items: ['⭐', '⭐', '⭐', '⭐', '⭐'], goal: 5 },
    templateFallback: false
  },
  {
    char: '光', unit: 'u6', theme: 'nature',
    template: 'tap-reveal', interaction: 'tap',
    narration: '打开灯，光照到哪里哪里亮。',
    props: { hero: '🔆', items: ['💡', '🕯️', '🔦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '冰', unit: 'u6', theme: 'weather',
    template: 'morph-story', interaction: 'sequence',
    narration: '水冷得发抖，冻成硬硬的一块冰。',
    props: { hero: '🧊', stages: ['💧', '🧊', '❄️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '沙', unit: 'u6', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '沙滩上的沙细细的，挖挖看。',
    props: { hero: '🏖️', items: ['🐚', '🦀', '🪣'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
