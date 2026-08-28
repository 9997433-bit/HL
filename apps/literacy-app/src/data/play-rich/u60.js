/**
 * 富互动 play 分片 u60 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u60'

export const UNIT_RICH_PLAYS = [
  {
    char: '己', unit: 'u60', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '镜子里的自己，点开瞧瞧。',
    props: { hero: '🙋', items: ['🪞'], goal: 1 },
    templateFallback: false
  },
  {
    char: '弓', unit: 'u60', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把弓弦往后一拉，绷紧了。',
    props: { hero: '🏹', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '刃', unit: 'u60', theme: 'object',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一样有刀刃？小心找出来。',
    props: { hero: '🔪', target: '🔪', decoys: ['🥄', '🧸', '🎈'], goal: 1 },
    templateFallback: false
  },
  {
    char: '丰', unit: 'u60', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '稻子越长越丰，沉甸甸的。',
    props: { hero: '🌾', stages: ['🌱', '🌿', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '王', unit: 'u60', theme: 'family',
    template: 'color-fill', interaction: 'tap',
    narration: '给国王的皇冠涂上金色。',
    props: { hero: '👑', color: '金', goal: 3 },
    templateFallback: false
  },
  {
    char: '夫', unit: 'u60', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '一家人配一配：谁跟谁一对。',
    props: { hero: '👨', pairs: [{ a: '👨', b: '👩' }, { a: '👴', b: '👵' }, { a: '👦', b: '👧' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '无', unit: 'u60', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '全都拿走，最后一个也不剩。',
    props: { hero: '🈳', items: ['🍎', '🍎'], goal: 2 },
    templateFallback: false
  },
  {
    char: '专', unit: 'u60', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '专心一点，只盯着靶心点三下。',
    props: { hero: '🎯', items: ['🎯', '🎯', '🎯'], goal: 3 },
    templateFallback: false
  },
  {
    char: '扎', unit: 'u60', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小旗扎进土里，站得稳稳。',
    props: { hero: '📌', parts: ['🚩', '🟫'], goal: 2 },
    templateFallback: false
  },
  {
    char: '艺', unit: 'u60', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '画画唱歌都是本领，点点看。',
    props: { hero: '🎨', items: ['🖌️', '🎵', '🩰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '区', unit: 'u60', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '分成两个小区：住人和停车。',
    props: { hero: '🗺️', items: [{ item: '🛏️', bucket: '住人' }, { item: '🍽️', bucket: '住人' }, { item: '🚗', bucket: '停车' }, { item: '🚲', bucket: '停车' }], buckets: [{ label: '住人', emoji: '🏠' }, { label: '停车', emoji: '🅿️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '历', unit: 'u60', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '日历一天撕一页，撕掉四页。',
    props: { hero: '📅', items: ['📅', '📅', '📅', '📅'], goal: 4 },
    templateFallback: false
  },
  {
    char: '尤', unit: 'u60', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一颗尤其亮？找最亮的星。',
    props: { hero: '⭐', target: '🌟', decoys: ['⭐', '✨', '💫'], goal: 1 },
    templateFallback: false
  },
  {
    char: '匹', unit: 'u60', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '一匹一匹数马，数满三匹。',
    props: { hero: '🐎', items: ['🐎', '🐎', '🐎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '巨', unit: 'u60', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '小象一口一口长成巨兽。',
    props: { hero: '🦣', stages: ['🐘', '🦣', '🏔️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '互', unit: 'u60', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '你帮我我帮你，互相配一对。',
    props: { hero: '🤝', pairs: [{ a: '🤝', b: '🤝' }, { a: '🧤', b: '🧤' }, { a: '🧦', b: '🧦' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '止', unit: 'u60', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '该停下了，找出停止的牌子。',
    props: { hero: '🛑', target: '🛑', decoys: ['🟢', '🟡', '➡️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '贝', unit: 'u60', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '沙滩上有小贝壳，挨个点。',
    props: { hero: '🐚', items: ['🐚', '🌊', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '冈', unit: 'u60', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '翻过小山冈，一路往上爬。',
    props: { hero: '🏔️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '见', unit: 'u60', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '眼睛一睁，看见好多东西。',
    props: { hero: '👀', items: ['🌳', '🐦', '🚗'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
