/**
 * 富互动 play 分片 u20 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u20'

export const UNIT_RICH_PLAYS = [
  {
    char: '拉', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '使劲往自己这边拉。',
    props: { hero: '🤝', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '推', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '双手往前推，小车动起来。',
    props: { hero: '🛒', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '提', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用手拎起水桶，往上提。',
    props: { hero: '🧺', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '抱', unit: 'u20', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '张开两只手，把小熊抱住。',
    props: { hero: '🤱', parts: ['🧸', '✋', '✋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '洗', unit: 'u20', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '打开水龙头，把小手洗干净。',
    props: { hero: '🧼', items: ['🚿', '🧴', '🤲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '扫', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿起扫把，把地上的土扫走。',
    props: { hero: '🧹', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '拍', unit: 'u20', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '拍拍手，啪啪啪。',
    props: { hero: '👏', sound: '啪', goal: 3 },
    templateFallback: false
  },
  {
    char: '摸', unit: 'u20', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '闭上眼摸一摸，猜猜是什么。',
    props: { hero: '🖐️', items: ['🧸', '🐱', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '找', unit: 'u20', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '钥匙不见了，快把它找出来。',
    props: { hero: '🔍', target: '🔑', decoys: ['🧦', '📕', '🧸'], goal: 1 },
    templateFallback: false
  },
  {
    char: '抓', unit: 'u20', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一把抓住气球，别让它飞走。',
    props: { hero: '🫳', items: ['🎈', '🎈', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '放', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '轻轻把东西放下来。',
    props: { hero: '🫴', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '开', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把门打开，请进。',
    props: { hero: '🔓', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '关', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '出门记得把门关上。',
    props: { hero: '🔒', dir: 'left', goal: 2 },
    templateFallback: false
  },
  {
    char: '送', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把礼物送给好朋友。',
    props: { hero: '🎁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '收', unit: 'u20', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '玩具玩完了，一件件收回箱子。',
    props: { hero: '📦', parts: ['🧸', '🪀', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '挂', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把画往上挂到墙上。',
    props: { hero: '🖼️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '举', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '会回答的小朋友，把手高高举起。',
    props: { hero: '🙋', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '摆', unit: 'u20', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把碗筷一样一样摆整齐。',
    props: { hero: '🪑', items: [{ item: '🥣', bucket: '桌上' }, { item: '🥢', bucket: '桌上' }, { item: '🫖', bucket: '柜里' }, { item: '🍶', bucket: '柜里' }], buckets: [{ label: '桌上', emoji: '🍽️' }, { label: '柜里', emoji: '🗄️' }], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
