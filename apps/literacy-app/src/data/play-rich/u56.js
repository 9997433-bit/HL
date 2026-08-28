/**
 * 富互动 play 分片 u56 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u56'

export const UNIT_RICH_PLAYS = [
  {
    char: '科', unit: 'u56', theme: 'school',
    template: 'sort-buckets', interaction: 'drag',
    narration: '科学课上分一分：动物和植物。',
    props: { hero: '🔬', items: [{ item: '🐰', bucket: '动物' }, { item: '🐟', bucket: '动物' }, { item: '🌵', bucket: '植物' }, { item: '🍀', bucket: '植物' }], buckets: [{ label: '动物', emoji: '🐾' }, { label: '植物', emoji: '🌿' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '技', unit: 'u56', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '学一门手艺，先把家什凑齐。',
    props: { hero: '🛠️', parts: ['🔨', '🔧', '🪛'], goal: 3 },
    templateFallback: false
  },
  {
    char: '器', unit: 'u56', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '这些器具都会帮忙，点点看。',
    props: { hero: '⚙️', items: ['🍶', '🥄', '🔧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '磁', unit: 'u56', theme: 'object',
    template: 'rain-catch', interaction: 'drag',
    narration: '磁铁一凑近，铁家伙全贴上来。',
    props: { hero: '🧲', items: ['🔩', '📎', '🔑'], tool: '🧲', goal: 3 },
    templateFallback: false
  },
  {
    char: '源', unit: 'u56', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '顺着小溪往上找，找到水源头。',
    props: { hero: '💧', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '宇', unit: 'u56', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '从小屋顶看到大星空，那是宇。',
    props: { hero: '🌌', stages: ['🏠', '🌌', '✨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '宙', unit: 'u56', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '从很久很久以前，一直数到现在。',
    props: { hero: '🪐', stages: ['🕰️', '🪐', '宙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '卫', unit: 'u56', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁在天上守着地球？找出卫星。',
    props: { hero: '🛰️', target: '🛰️', decoys: ['🌙', '⭐', '☁️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '箭', unit: 'u56', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '数三下，火箭嗖地射上天。',
    props: { hero: '🚀', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '另', unit: 'u56', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '这一堆搁这边，另一堆搁那边。',
    props: { hero: '➕', items: [{ item: '🍎', bucket: '这边' }, { item: '🍐', bucket: '这边' }, { item: '🥕', bucket: '那边' }, { item: '🥔', bucket: '那边' }], buckets: [{ label: '这边', emoji: '📦' }, { label: '那边', emoji: '🧺' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '某', unit: 'u56', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '某个盒子里有惊喜，挨个揭。',
    props: { hero: '❔', items: ['🎁', '🧸', '🍬'], goal: 3 },
    templateFallback: false
  },
  {
    char: '逆', unit: 'u56', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '大家往前，它偏要逆着走。',
    props: { hero: '↩️', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '破', unit: 'u56', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一戳一个，泡泡全破掉。',
    props: { hero: '💥', items: ['🫧', '🫧', '🫧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '挖', unit: 'u56', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '拿小铲子挖一挖，挖出宝贝。',
    props: { hero: '⛏️', items: ['🥔', '🦴', '💎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '埋', unit: 'u56', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把种子埋进土里，盖上泥。',
    props: { hero: '🌱', parts: ['🌰', '🟫'], goal: 2 },
    templateFallback: false
  },
  {
    char: '堆', unit: 'u56', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一块一块往上堆，堆成小山。',
    props: { hero: '🗻', items: ['🧱', '🧱', '🧱', '🧱'], goal: 4 },
    templateFallback: false
  },
  {
    char: '决', unit: 'u56', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '拿定主意，决定就选这一个。',
    props: { hero: '✔️', target: '✔️', decoys: ['❌', '❔', '➖'], goal: 1 },
    templateFallback: false
  },
  {
    char: '选', unit: 'u56', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '挑一挑，选中喜欢的那几样。',
    props: { hero: '☑️', items: ['🍦', '🎈', '🧸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '择', unit: 'u56', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '择菜啦：好的留下，坏的丢掉。',
    props: { hero: '🔀', items: [{ item: '🥬', bucket: '好的' }, { item: '🥦', bucket: '好的' }, { item: '🍂', bucket: '坏的' }, { item: '🐛', bucket: '坏的' }], buckets: [{ label: '好的', emoji: '✅' }, { label: '坏的', emoji: '🗑️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '参', unit: 'u56', theme: 'family',
    template: 'count-tap', interaction: 'tap',
    narration: '举手参加，一个一个报上名。',
    props: { hero: '🙋', items: ['🙋', '🙋', '🙋'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
