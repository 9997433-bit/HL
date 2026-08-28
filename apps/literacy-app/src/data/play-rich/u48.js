/**
 * 富互动 play 分片 u48 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u48'

export const UNIT_RICH_PLAYS = [
  {
    char: '梅', unit: 'u48', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '下雪天，梅花一朵朵开了。',
    props: { hero: '🌸', stages: ['❄️', '🌿', '🌸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '兰', unit: 'u48', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '给兰花的花瓣涂上淡紫。',
    props: { hero: '🌷', color: 'violet', goal: 3 },
    templateFallback: false
  },
  {
    char: '菊', unit: 'u48', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '秋天的菊花，数满五朵。',
    props: { hero: '🌼', items: ['🌼', '🌼', '🌼', '🌼', '🌼'], goal: 5 },
    templateFallback: false
  },
  {
    char: '莲', unit: 'u48', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '水里钻出一支莲，开花了。',
    props: { hero: '🪷', stages: ['💧', '🌿', '🪷'], goal: 3 },
    templateFallback: false
  },
  {
    char: '藕', unit: 'u48', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '莲藕一节接一节，接起来。',
    props: { hero: '🥔', parts: ['🥔', '🥔', '🥔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '葡', unit: 'u48', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一颗颗摘葡萄，摘满五颗。',
    props: { hero: '🍇', items: ['🍇', '🍇', '🍇', '🍇', '🍇'], goal: 5 },
    templateFallback: false
  },
  {
    char: '萄', unit: 'u48', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '「葡」和「萄」合起来是水果。',
    props: { hero: '🍇', parts: ['葡', '萄'], word: '葡萄', goal: 2 },
    templateFallback: false
  },
  {
    char: '橘', unit: 'u48', theme: 'food',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把橘子皮往下一剥，露出瓣。',
    props: { hero: '🍊', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '柚', unit: 'u48', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '大的是柚子，小的是橘子。',
    props: { hero: '🍈', items: [{ item: '🍈', bucket: '大' }, { item: '🥥', bucket: '大' }, { item: '🍊', bucket: '小' }, { item: '🫐', bucket: '小' }], buckets: [{ label: '大', emoji: '🍈' }, { label: '小', emoji: '🍊' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '柿', unit: 'u48', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '柿子熟了，涂成橙红色。',
    props: { hero: '🍅', color: 'orangered', goal: 3 },
    templateFallback: false
  },
  {
    char: '栗', unit: 'u48', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '栗子壳一个个剥开，吃掉。',
    props: { hero: '🌰', items: ['🌰', '🌰', '🌰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '榆', unit: 'u48', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '榆树苗长成大树，一年年高。',
    props: { hero: '🌳', stages: ['🌱', '🌿', '🌳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '槐', unit: 'u48', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '槐树上有什么？点亮看看。',
    props: { hero: '🌳', items: ['🌸', '🐦', '🐝'], goal: 3 },
    templateFallback: false
  },
  {
    char: '杨', unit: 'u48', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '风吹杨树，叶子哗哗往左倒。',
    props: { hero: '🌲', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '椒', unit: 'u48', theme: 'food',
    template: 'sound-tap', interaction: 'tap',
    narration: '辣椒真辣，辣得直哈气。',
    props: { hero: '🌶️', sound: '哈哈', goal: 3 },
    templateFallback: false
  },
  {
    char: '葱', unit: 'u48', theme: 'food',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把葱一根根往上拔出来。',
    props: { hero: '🧅', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '蒜', unit: 'u48', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '蒜瓣一瓣瓣掰开，凑一头。',
    props: { hero: '🧄', parts: ['🧄', '🧄', '🧄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '姜', unit: 'u48', theme: 'food',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '老姜切一片，往锅里放。',
    props: { hero: '🫚', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '粉', unit: 'u48', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把花瓣涂成淡淡的粉。',
    props: { hero: '🌸', color: 'pink', goal: 3 },
    templateFallback: false
  },
  {
    char: '摘', unit: 'u48', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '伸手摘果子，摘满四个。',
    props: { hero: '🧺', items: ['🍎', '🍐', '🍊', '🍑'], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
