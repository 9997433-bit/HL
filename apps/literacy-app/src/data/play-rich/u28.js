/**
 * 富互动 play 分片 u28 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u28'

export const UNIT_RICH_PLAYS = [
  {
    char: '街', unit: 'u28', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '走在街上，街边都有些什么。',
    props: { hero: '🏙️', items: ['🚦', '🏪', '🌳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '市', unit: 'u28', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '逛菜市场，把菜和肉分开放。',
    props: { hero: '🏬', items: [{ item: '🥕', bucket: '菜' }, { item: '🥦', bucket: '菜' }, { item: '🍗', bucket: '肉' }, { item: '🥩', bucket: '肉' }], buckets: [{ label: '菜', emoji: '🥬' }, { label: '肉', emoji: '🍖' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '店', unit: 'u28', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '推开小店的门，看看卖什么。',
    props: { hero: '🏪', items: ['🍞', '🥛', '🍭'], goal: 3 },
    templateFallback: false
  },
  {
    char: '村', unit: 'u28', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '小村子安安静静，谁在那里。',
    props: { hero: '🏡', items: ['🐓', '🌾', '🐕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '城', unit: 'u28', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '一块一块砌起城墙，围成城。',
    props: { hero: '🏰', parts: ['🧱', '🧱', '🧱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '乡', unit: 'u28', theme: 'nature',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一张画的是乡下？找田野。',
    props: { hero: '🌾', target: '🌾', decoys: ['🏙️', '🏢', '🚇'], goal: 1 },
    templateFallback: false
  },
  {
    char: '园', unit: 'u28', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '走进公园，里面能玩些什么。',
    props: { hero: '🏞️', items: ['🛝', '⛲', '🌳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '公', unit: 'u28', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '公家的东西大家一起用。',
    props: { hero: '🚌', items: ['🏞️', '🚏', '📚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '医', unit: 'u28', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '去医院看病，医生要用什么。',
    props: { hero: '🩺', items: ['💉', '💊', '🩹'], goal: 3 },
    templateFallback: false
  },
  {
    char: '院', unit: 'u28', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '围上院墙，屋子前面就有院。',
    props: { hero: '🏘️', parts: ['🧱', '🏠', '🧱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '楼', unit: 'u28', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '一层一层往上盖，盖成高楼。',
    props: { hero: '🏢', stages: ['🏠', '🏢', '🏙️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '屋', unit: 'u28', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '先立起四面墙，再盖上屋顶。',
    props: { hero: '🏠', parts: ['🧱', '🧱', '🔺'], goal: 3 },
    templateFallback: false
  },
  {
    char: '馆', unit: 'u28', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一个是图书馆？把它找出来。',
    props: { hero: '🏛️', target: '📚', decoys: ['🏥', '🏫', '🏦'], goal: 1 },
    templateFallback: false
  },
  {
    char: '厂', unit: 'u28', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '工厂里机器转，正在造什么。',
    props: { hero: '🏭', items: ['🚗', '🧱', '👕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '农', unit: 'u28', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '农民伯伯下田，要带上什么。',
    props: { hero: '🧑‍🌾', items: ['🪣', '🌾', '🧢'], goal: 3 },
    templateFallback: false
  },
  {
    char: '工', unit: 'u28', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '工人叔叔干活，点点他的工具。',
    props: { hero: '🧑‍🔧', items: ['🔨', '🔧', '🪛'], goal: 3 },
    templateFallback: false
  },
  {
    char: '邮', unit: 'u28', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把信投进邮筒，寄给好朋友。',
    props: { hero: '✉️', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '银', unit: 'u28', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小勺子涂成亮亮的银色。',
    props: { hero: '🥄', color: 'silver', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
