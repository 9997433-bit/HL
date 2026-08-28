/**
 * 富互动 play 分片 u53 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u53'

export const UNIT_RICH_PLAYS = [
  {
    char: '思', unit: 'u53', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '低头想一想，念头冒出来。',
    props: { hero: '💭', stages: ['🤔', '💭', '💡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '忆', unit: 'u53', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '想起来了吗？把图配成对。',
    props: { hero: '🧠', pairs: [{ a: '🎂', b: '🕯️' }, { a: '🎒', b: '📚' }, { a: '🌧️', b: '☂️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '猜', unit: 'u53', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '盒子里是什么？猜猜看再揭。',
    props: { hero: '❓', items: ['🍎', '🧸', '🔑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '疑', unit: 'u53', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个眼神在怀疑？找出来。',
    props: { hero: '🤨', target: '🤨', decoys: ['😀', '😴', '😮'], goal: 1 },
    templateFallback: false
  },
  {
    char: '惑', unit: 'u53', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '越看越糊涂，脸上都是问号。',
    props: { hero: '😕', stages: ['🙂', '😕', '❓'], goal: 3 },
    templateFallback: false
  },
  {
    char: '悟', unit: 'u53', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '突然想通了，脑袋亮起来。',
    props: { hero: '💡', stages: ['😕', '🤔', '💡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '断', unit: 'u53', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用力一掰，树枝断成两截。',
    props: { hero: '🪵', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '判', unit: 'u53', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '裁判来判：能吃的和不能吃的。',
    props: { hero: '⚖️', items: [{ item: '🍎', bucket: '能吃' }, { item: '🍞', bucket: '能吃' }, { item: '🪨', bucket: '不能吃' }, { item: '🔩', bucket: '不能吃' }], buckets: [{ label: '能吃', emoji: '✅' }, { label: '不能吃', emoji: '❌' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '析', unit: 'u53', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把「析」拆开，看清楚零件。',
    props: { hero: '🔬', parts: ['木', '斤'], goal: 2 },
    templateFallback: false
  },
  {
    char: '观', unit: 'u53', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '站在窗前观景，看到什么？',
    props: { hero: '👁️', items: ['🌳', '🐦', '🌈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '察', unit: 'u53', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '仔细察一察，哪片叶子有虫？',
    props: { hero: '🔎', target: '🐛', decoys: ['🍃', '🍂', '🌿'], goal: 1 },
    templateFallback: false
  },
  {
    char: '探', unit: 'u53', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '拿手电往洞里探，照出什么。',
    props: { hero: '🔦', items: ['🦇', '💎', '🕷️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '究', unit: 'u53', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一遍遍试，试满四次弄明白。',
    props: { hero: '🧪', items: ['🧪', '🧪', '🧪', '🧪'], goal: 4 },
    templateFallback: false
  },
  {
    char: '智', unit: 'u53', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '动动脑筋，把形状配成对。',
    props: { hero: '🧠', pairs: [{ a: '🔺', b: '🔺' }, { a: '🟦', b: '🟦' }, { a: '⭕', b: '⭕' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '慧', unit: 'u53', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '想明白以后，眼睛都亮了。',
    props: { hero: '✨', stages: ['💭', '🧠', '✨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '情', unit: 'u53', theme: 'feeling',
    template: 'sort-buckets', interaction: 'drag',
    narration: '开心的一堆，难过的一堆。',
    props: { hero: '💗', items: [{ item: '😊', bucket: '开心' }, { item: '🥳', bucket: '开心' }, { item: '😭', bucket: '难过' }, { item: '😞', bucket: '难过' }], buckets: [{ label: '开心', emoji: '😄' }, { label: '难过', emoji: '😢' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '景', unit: 'u53', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '这幅风景里有什么？点点看。',
    props: { hero: '🏞️', items: ['⛰️', '🌊', '🌅'], goal: 3 },
    templateFallback: false
  },
  {
    char: '境', unit: 'u53', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '山里的景和海边的景，分开。',
    props: { hero: '🌍', items: [{ item: '🌲', bucket: '山里' }, { item: '🪨', bucket: '山里' }, { item: '🐚', bucket: '海边' }, { item: '⛵', bucket: '海边' }], buckets: [{ label: '山里', emoji: '⛰️' }, { label: '海边', emoji: '🏖️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '待', unit: 'u53', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '排队等待，数三下就到你。',
    props: { hero: '⏳', items: ['⏳', '⏳', '⏳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '忽', unit: 'u53', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '忽地一下，风把纸吹跑了。',
    props: { hero: '⚡', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
