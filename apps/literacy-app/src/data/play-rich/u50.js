/**
 * 富互动 play 分片 u50 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u50'

export const UNIT_RICH_PLAYS = [
  {
    char: '蒸', unit: 'u50', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '水开了，蒸汽把包子蒸熟。',
    props: { hero: '♨️', stages: ['💧', '♨️', '🥟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '炸', unit: 'u50', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '下锅炸，一根根捞出来。',
    props: { hero: '🍟', items: ['🍟', '🍟', '🍟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '煎', unit: 'u50', theme: 'food',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把鸡蛋翻个面，两面都煎。',
    props: { hero: '🍳', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '烤', unit: 'u50', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '烤箱里越烤越香，颜色变深。',
    props: { hero: '🔥', stages: ['🥖', '🍞', '🥐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拌', unit: 'u50', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '加点酱，把菜拌一拌。',
    props: { hero: '🥗', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '切', unit: 'u50', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '刀往下一切，分成两半。',
    props: { hero: '🔪', dir: 'down', goal: 4 },
    templateFallback: false
  },
  {
    char: '削', unit: 'u50', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '拿刀顺着皮，削苹果一圈。',
    props: { hero: '🍎', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '剥', unit: 'u50', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '花生壳一个个剥开，吃仁。',
    props: { hero: '🥜', items: ['🥜', '🥜', '🥜'], goal: 3 },
    templateFallback: false
  },
  {
    char: '涮', unit: 'u50', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '肉片下锅涮三下就熟。',
    props: { hero: '🍲', items: ['🥩', '🥩', '🥩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '炖', unit: 'u50', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '小火慢慢炖，汤越炖越浓。',
    props: { hero: '🍲', stages: ['🥕', '🍲', '🍜'], goal: 3 },
    templateFallback: false
  },
  {
    char: '熬', unit: 'u50', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '米粥熬得稠稠的，冒起泡。',
    props: { hero: '🥣', stages: ['🍚', '🥣', '♨️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '酱', unit: 'u50', theme: 'food',
    template: 'color-fill', interaction: 'tap',
    narration: '把酱涂在面包上，褐褐的。',
    props: { hero: '🫙', color: 'brown', goal: 3 },
    templateFallback: false
  },
  {
    char: '醋', unit: 'u50', theme: 'food',
    template: 'sound-tap', interaction: 'tap',
    narration: '尝一口醋，酸得直咂嘴。',
    props: { hero: '🍶', sound: '酸酸', goal: 3 },
    templateFallback: false
  },
  {
    char: '洒', unit: 'u50', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '水珠洒出来，一滴滴擦掉。',
    props: { hero: '💦', items: ['💧', '💧', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '盖', unit: 'u50', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把盖子往下一扣，盖严实。',
    props: { hero: '🫙', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '铺', unit: 'u50', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '把床单从这头铺到那头。',
    props: { hero: '🛏️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '擦', unit: 'u50', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿抹布来回擦，擦干净。',
    props: { hero: '🧽', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '拖', unit: 'u50', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拖把往后一拖，地就亮了。',
    props: { hero: '🧹', dir: 'left', goal: 4 },
    templateFallback: false
  },
  {
    char: '摔', unit: 'u50', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '手一松，杯子摔到地上。',
    props: { hero: '💥', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '挤', unit: 'u50', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把牙膏往外挤一点点。',
    props: { hero: '🫸', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
