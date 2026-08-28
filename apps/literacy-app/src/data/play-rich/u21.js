/**
 * 富互动 play 分片 u21 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u21'

export const UNIT_RICH_PLAYS = [
  {
    char: '快', unit: 'u21', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小兔子跑得飞快，一下就冲到头。',
    props: { hero: '🐇', dir: 'right', goal: 5 },
    templateFallback: false
  },
  {
    char: '慢', unit: 'u21', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '小蜗牛慢吞吞，一点一点往前挪。',
    props: { hero: '🐌', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '怕', unit: 'u21', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '黑屋子里有点怕，点开看看是谁。',
    props: { hero: '😨', items: ['🐈', '🧸', '🕯️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '急', unit: 'u21', theme: 'feeling',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '快迟到啦，急急忙忙一件件收好。',
    props: { hero: '😰', items: ['🎒', '👟', '🧢'], goal: 3 },
    templateFallback: false
  },
  {
    char: '累', unit: 'u21', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '玩了一整天，眼皮越来越沉。',
    props: { hero: '😪', stages: ['🙂', '😪', '😴'], goal: 3 },
    templateFallback: false
  },
  {
    char: '饿', unit: 'u21', theme: 'feeling',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '肚子咕咕叫，吃点东西就不饿了。',
    props: { hero: '🍽️', items: ['🍞', '🍎', '🥛'], goal: 3 },
    templateFallback: false
  },
  {
    char: '渴', unit: 'u21', theme: 'feeling',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '嗓子干干的，咕咚咕咚喝三口。',
    props: { hero: '🥤', items: ['💧', '💧', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '病', unit: 'u21', theme: 'feeling',
    template: 'scene-poke', interaction: 'tap',
    narration: '生病要看医生，点点用得上的。',
    props: { hero: '🤒', items: ['🌡️', '💊', '🩺'], goal: 3 },
    templateFallback: false
  },
  {
    char: '痛', unit: 'u21', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '哪里痛？贴张创可贴就不痛了。',
    props: { hero: '🤕', items: ['🩹', '🩹', '🩹'], goal: 3 },
    templateFallback: false
  },
  {
    char: '甜', unit: 'u21', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '甜的进糖罐，酸的放到另一边。',
    props: { hero: '🍬', items: [{ item: '🍬', bucket: '甜' }, { item: '🍭', bucket: '甜' }, { item: '🍋', bucket: '酸' }, { item: '🥝', bucket: '酸' }], buckets: [{ label: '甜', emoji: '🍯' }, { label: '酸', emoji: '🍋' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '苦', unit: 'u21', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一样最苦？把苦的那个点出来。',
    props: { hero: '😖', target: '☕', decoys: ['🍬', '🍦', '🍯'], goal: 1 },
    templateFallback: false
  },
  {
    char: '香', unit: 'u21', theme: 'food',
    template: 'scene-poke', interaction: 'tap',
    narration: '饭菜的香味飘出来，点点是什么。',
    props: { hero: '🍲', items: ['🍞', '🍜', '🍗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '臭', unit: 'u21', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '捏住鼻子，找出臭臭的那一个。',
    props: { hero: '🤢', target: '🗑️', decoys: ['🌸', '🍎', '🧼'], goal: 1 },
    templateFallback: false
  },
  {
    char: '冷', unit: 'u21', theme: 'weather',
    template: 'morph-story', interaction: 'sequence',
    narration: '温度一降再降，水冷得结成冰。',
    props: { hero: '🥶', stages: ['🌡️', '🥶', '冷'], goal: 3 },
    templateFallback: false
  },
  {
    char: '热', unit: 'u21', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '太阳越晒越热，汗都冒出来了。',
    props: { hero: '🥵', stages: ['🌤️', '🌞', '🥵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '暖', unit: 'u21', theme: 'feeling',
    template: 'color-fill', interaction: 'tap',
    narration: '小手伸进手套，暖得红扑扑。',
    props: { hero: '🧤', color: 'orange', goal: 3 },
    templateFallback: false
  },
  {
    char: '亮', unit: 'u21', theme: 'nature',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一盏一盏点上，屋里亮堂堂。',
    props: { hero: '🔆', items: ['🕯️', '💡', '🏮'], goal: 3 },
    templateFallback: false
  },
  {
    char: '静', unit: 'u21', theme: 'feeling',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '嘘——把吵人的声音一个个关掉。',
    props: { hero: '🤫', items: ['📢', '🔔', '📻'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
