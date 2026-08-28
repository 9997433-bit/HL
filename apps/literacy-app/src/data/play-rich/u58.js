/**
 * 富互动 play 分片 u58 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u58'

export const UNIT_RICH_PLAYS = [
  {
    char: '勤', unit: 'u58', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '小蜜蜂最勤劳，采满四朵花。',
    props: { hero: '🐝', items: ['🌻', '🌻', '🌻', '🌻'], goal: 4 },
    templateFallback: false
  },
  {
    char: '俭', unit: 'u58', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '省着点花，只用掉两个硬币。',
    props: { hero: '🪙', items: ['🪙', '🪙'], goal: 2 },
    templateFallback: false
  },
  {
    char: '谦', unit: 'u58', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '谦让一下，请你先过去。',
    props: { hero: '🙇', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '虚', unit: 'u58', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '罐子是空的吗？揭开瞧瞧。',
    props: { hero: '🫙', items: ['💨', '💨', '💨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '善', unit: 'u58', theme: 'feeling',
    template: 'sort-buckets', interaction: 'drag',
    narration: '善良的事一边，不好的事一边。',
    props: { hero: '😇', items: [{ item: '🤝', bucket: '善良' }, { item: '🎁', bucket: '善良' }, { item: '💢', bucket: '不好' }, { item: '🗑️', bucket: '不好' }], buckets: [{ label: '善良', emoji: '😇' }, { label: '不好', emoji: '😖' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '故', unit: 'u58', theme: 'school',
    template: 'morph-story', interaction: 'sequence',
    narration: '翻开故事书，故事开场了。',
    props: { hero: '📖', stages: ['📕', '📖', '🧚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '奇', unit: 'u58', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一样最稀奇？找出会发光的。',
    props: { hero: '✨', target: '✨', decoys: ['🪨', '🍂', '🧱'], goal: 1 },
    templateFallback: false
  },
  {
    char: '神', unit: 'u58', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '一阵烟冒出来，神仙现身了。',
    props: { hero: '🧞', stages: ['🫖', '💨', '🧞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '仙', unit: 'u58', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '小仙子踩着云往上飘。',
    props: { hero: '🧝', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '妖', unit: 'u58', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个是妖怪的脸？把它挑出来。',
    props: { hero: '👺', target: '👺', decoys: ['🙂', '🐰', '🌼'], goal: 1 },
    templateFallback: false
  },
  {
    char: '怪', unit: 'u58', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '影子晃啊晃，晃成个小怪物。',
    props: { hero: '👻', stages: ['🌫️', '👤', '👻'], goal: 3 },
    templateFallback: false
  },
  {
    char: '精', unit: 'u58', theme: 'animal',
    template: 'scene-poke', interaction: 'tap',
    narration: '花丛里住着小精灵，点点找。',
    props: { hero: '🧚', items: ['🌸', '🍄', '🦋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '灵', unit: 'u58', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '机灵的小家伙，把图配成对。',
    props: { hero: '🧚', pairs: [{ a: '🧚', b: '✨' }, { a: '🐿️', b: '🌰' }, { a: '🦊', b: '🍇' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '侠', unit: 'u58', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小侠客一挥手，冲上前去。',
    props: { hero: '🦸', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '紧', unit: 'u58', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把绳子拉紧，打一个结。',
    props: { hero: '🪢', parts: ['🧵', '🪢'], goal: 2 },
    templateFallback: false
  },
  {
    char: '搬', unit: 'u58', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一箱一箱往车上搬，搬三箱。',
    props: { hero: '📦', items: ['📦', '📦', '📦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '迷', unit: 'u58', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '走迷宫可别迷路，跟着走。',
    props: { hero: '🌀', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '扔', unit: 'u58', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一样一样扔进垃圾桶。',
    props: { hero: '🗑️', items: ['🍌', '📄', '🥤'], goal: 3 },
    templateFallback: false
  },
  {
    char: '敲', unit: 'u58', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '咚咚咚，敲敲这扇门。',
    props: { hero: '🚪', sound: '咚咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '甩', unit: 'u58', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '手往外一甩，水珠飞出去。',
    props: { hero: '🌀', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
