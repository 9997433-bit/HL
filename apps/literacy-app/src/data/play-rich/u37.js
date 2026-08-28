/**
 * 富互动 play 分片 u37 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u37'

export const UNIT_RICH_PLAYS = [
  {
    char: '服', unit: 'u37', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把衣服分好，上身的下身的。',
    props: { hero: '👔', items: [{ item: '🧥', bucket: '上身' }, { item: '👚', bucket: '上身' }, { item: '🩳', bucket: '下身' }, { item: '👖', bucket: '下身' }], buckets: [{ label: '上身', emoji: '👕' }, { label: '下身', emoji: '👖' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '衬', unit: 'u37', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '里面先穿衬衣，再套上外套。',
    props: { hero: '👔', items: ['👕', '👔', '🧥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '衫', unit: 'u37', theme: 'object',
    template: 'color-fill', interaction: 'tap',
    narration: '给小衬衫涂上淡淡的蓝。',
    props: { hero: '👕', color: 'lightblue', goal: 3 },
    templateFallback: false
  },
  {
    char: '裤', unit: 'u37', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '两条裤腿缝到一起，成一条裤。',
    props: { hero: '👖', parts: ['🦵', '🦵'], goal: 2 },
    templateFallback: false
  },
  {
    char: '裙', unit: 'u37', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '转个圈，裙子就飘起来了。',
    props: { hero: '👗', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '袜', unit: 'u37', theme: 'object',
    template: 'pair-match', interaction: 'drag',
    narration: '一只一只配好，袜子成对。',
    props: { hero: '🧦', pairs: [{ a: '🧦', b: '🧦' }, { a: '🩰', b: '🩰' }, { a: '🥾', b: '🥾' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '袋', unit: 'u37', theme: 'object',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '口袋里掏出小东西，一件一件。',
    props: { hero: '👝', items: ['🔑', '🍬', '🪙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '扣', unit: 'u37', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一颗一颗系扣子，系好四颗。',
    props: { hero: '🔘', items: ['🔘', '🔘', '🔘', '🔘'], goal: 4 },
    templateFallback: false
  },
  {
    char: '领', unit: 'u37', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '翻好衣领，脖子那圈才整齐。',
    props: { hero: '👔', items: ['👔', '🧣', '🧥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '袖', unit: 'u37', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把袖子往上一撸，准备干活。',
    props: { hero: '💪', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '布', unit: 'u37', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '一匹布铺开，从这头拉到那头。',
    props: { hero: '🧵', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '棉', unit: 'u37', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '棉花开了，白白的一朵朵。',
    props: { hero: '☁️', stages: ['🌱', '🌿', '☁️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '丝', unit: 'u37', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '蚕吐出细细的丝，绕成一圈。',
    props: { hero: '🕸️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '绸', unit: 'u37', theme: 'object',
    template: 'color-fill', interaction: 'tap',
    narration: '把光滑的绸子涂成粉红色。',
    props: { hero: '🎀', color: 'pink', goal: 3 },
    templateFallback: false
  },
  {
    char: '线', unit: 'u37', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '捏住线头，从针眼里穿过去。',
    props: { hero: '🧵', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '针', unit: 'u37', theme: 'object',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '草堆里找针，把细细的找出来。',
    props: { hero: '📍', target: '📌', decoys: ['🌾', '🍂', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '缝', unit: 'u37', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '一针上一针下，把破口缝好。',
    props: { hero: '🪡', dir: 'up', goal: 4 },
    templateFallback: false
  },
  {
    char: '补', unit: 'u37', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '衣服破了，贴块布补起来。',
    props: { hero: '👕', parts: ['👕', '🟦'], goal: 2 },
    templateFallback: false
  },
  {
    char: '织', unit: 'u37', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一行一行织毛衣，织满五行。',
    props: { hero: '🧶', items: ['🧶', '🧶', '🧶', '🧶', '🧶'], goal: 5 },
    templateFallback: false
  },
  {
    char: '染', unit: 'u37', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '白布放进染缸，染成紫的。',
    props: { hero: '🧻', color: 'purple', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
