/**
 * 富互动 play 分片 u22 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u22'

export const UNIT_RICH_PLAYS = [
  {
    char: '内', unit: 'u22', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '掀开门帘，屋内的东西露出来。',
    props: { hero: '🏠', items: ['🪑', '🛏️', '🕯️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '间', unit: 'u22', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '门里放一个日，当中就是间。',
    props: { hero: '🚪', parts: ['门', '日'], goal: 2 },
    templateFallback: false
  },
  {
    char: '旁', unit: 'u22', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '挪到小树旁边去，靠边站好。',
    props: { hero: '🧍', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '对', unit: 'u22', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '算得对打勾，算错了打叉。',
    props: { hero: '✅', items: [{ item: '1+1=2', bucket: '对' }, { item: '3+1=4', bucket: '对' }, { item: '2+2=5', bucket: '错' }, { item: '5-1=9', bucket: '错' }], buckets: [{ label: '对', emoji: '✅' }, { label: '错', emoji: '❌' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '每', unit: 'u22', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '每人分一个苹果，谁也不落下。',
    props: { hero: '🍎', items: ['🍎', '🍎', '🍎', '🍎'], goal: 4 },
    templateFallback: false
  },
  {
    char: '几', unit: 'u22', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '树上停了几只小鸟？数数看。',
    props: { hero: '🐦', items: ['🐦', '🐦', '🐦', '🐦', '🐦'], goal: 5 },
    templateFallback: false
  },
  {
    char: '只', unit: 'u22', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '一只手套配一只手，成双成对。',
    props: { hero: '🐦', pairs: [{ a: '🧤', b: '✋' }, { a: '🧦', b: '🦶' }, { a: '👒', b: '🙂' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '群', unit: 'u22', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '一群小羊挤在一起，数数几只。',
    props: { hero: '🐑', items: ['🐑', '🐑', '🐑', '🐑', '🐑', '🐑'], goal: 6 },
    templateFallback: false
  },
  {
    char: '些', unit: 'u22', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '摘走一些葡萄，剩下的还有好多。',
    props: { hero: '🍇', items: ['🍇', '🍇', '🍇', '🍇'], goal: 4 },
    templateFallback: false
  },
  {
    char: '全', unit: 'u22', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '全家人都到齐了，点点谁来了。',
    props: { hero: '👨‍👩‍👧', items: ['👨', '👩', '👧', '👴'], goal: 4 },
    templateFallback: false
  },
  {
    char: '共', unit: 'u22', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '你两个我两个，一共是四个。',
    props: { hero: '➕', items: ['🍎', '🍎', '🍐', '🍐'], goal: 4 },
    templateFallback: false
  },
  {
    char: '空', unit: 'u22', theme: 'place',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '把箱子里的东西搬完，箱子空了。',
    props: { hero: '📦', items: ['🧸', '🪀', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '满', unit: 'u22', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一杯一杯往里倒，水装满了。',
    props: { hero: '🥛', items: ['💧', '💧', '💧', '💧', '💧'], goal: 5 },
    templateFallback: false
  },
  {
    char: '重', unit: 'u22', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '重的沉下去，轻的浮上来。',
    props: { hero: '🏋️', items: [{ item: '🪨', bucket: '重' }, { item: '🐘', bucket: '重' }, { item: '🎈', bucket: '轻' }, { item: '🪶', bucket: '轻' }], buckets: [{ label: '重', emoji: '⬇️' }, { label: '轻', emoji: '⬆️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '轻', unit: 'u22', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '羽毛轻飘飘，一吹就往上飞。',
    props: { hero: '🪶', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '远', unit: 'u22', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪座山最远？点看着最小的那座。',
    props: { hero: '🏔️', target: '🏔️', decoys: ['🌳', '🏠', '🐕'], goal: 1 },
    templateFallback: false
  },
  {
    char: '近', unit: 'u22', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把小狗牵到身边，靠得近近的。',
    props: { hero: '🐕', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '平', unit: 'u22', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '平平的一堆，坑坑洼洼的一堆。',
    props: { hero: '➖', items: [{ item: '🛣️', bucket: '平' }, { item: '📄', bucket: '平' }, { item: '⛰️', bucket: '不平' }, { item: '🪨', bucket: '不平' }], buckets: [{ label: '平', emoji: '➖' }, { label: '不平', emoji: '⛰️' }], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
