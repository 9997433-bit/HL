/**
 * 富互动 play 分片 u7 —— 这一单元的 14 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u7'

export const UNIT_RICH_PLAYS = [
  {
    char: '父', unit: 'u7', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '点点看，爸爸都会做什么。',
    props: { hero: '👨', items: ['🧰', '🚗', '🍳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '母', unit: 'u7', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '妈妈抱抱我，心里暖暖的。',
    props: { hero: '👩', items: ['🤱', '❤️', '🍲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '男', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '田里出力的是男，找出男孩子。',
    props: { hero: '👦', target: '👦', decoys: ['👧', '👵', '🧒'], goal: 1 },
    templateFallback: false
  },
  {
    char: '女', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找出女孩子，她扎着小辫子。',
    props: { hero: '👧', target: '👧', decoys: ['👦', '🧔', '👴'], goal: 1 },
    templateFallback: false
  },
  {
    char: '子', unit: 'u7', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '小娃娃一点点长大，变成小朋友。',
    props: { hero: '👶', stages: ['👶', '🧒', '👦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '你', unit: 'u7', theme: 'family',
    template: 'sound-tap', interaction: 'tap',
    narration: '指一指对面的小伙伴，说声你好。',
    props: { hero: '🫵', sound: '你好', goal: 3 },
    templateFallback: false
  },
  {
    char: '他', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '他说的是那个男孩，把他找出来。',
    props: { hero: '🧑', target: '🧑', decoys: ['👩', '👧', '👵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '她', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '她是女字旁，说的是那个女孩。',
    props: { hero: '👩‍🦰', target: '👩‍🦰', decoys: ['🧑', '👦', '👴'], goal: 1 },
    templateFallback: false
  },
  {
    char: '家', unit: 'u7', theme: 'family',
    template: 'drag-parts', interaction: 'drag',
    narration: '宝盖头是屋顶，屋顶下面就是家。',
    props: { hero: '🏠', parts: ['🏠', '👨', '👩', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '爱', unit: 'u7', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '抱一抱，心里的爱冒出小红心。',
    props: { hero: '❤️', items: ['💗', '💖', '💞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '哥', unit: 'u7', theme: 'family',
    template: 'sort-buckets', interaction: 'drag',
    narration: '哥哥比我大，把他放到大的那边。',
    props: { hero: '👦', items: [{ item: '👦', bucket: '大' }, { item: '🧔', bucket: '大' }, { item: '👶', bucket: '小' }, { item: '🧒', bucket: '小' }], buckets: [{ label: '大', emoji: '🔼' }, { label: '小', emoji: '🔽' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '姐', unit: 'u7', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '姐姐牵着我的手，看她在做什么。',
    props: { hero: '👧', items: ['📚', '🎀', '🤝'], goal: 3 },
    templateFallback: false
  },
  {
    char: '妹', unit: 'u7', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '妹妹比我小，她还在慢慢长大。',
    props: { hero: '🧒', stages: ['👶', '🧒', '👧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '国', unit: 'u7', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '大方框里住着好多人，那是我们的国。',
    props: { hero: '🏯', parts: ['囗', '玉'], goal: 2 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
