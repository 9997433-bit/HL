/**
 * 富互动 play 分片 u19 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u19'

export const UNIT_RICH_PLAYS = [
  {
    char: '爸', unit: 'u19', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '爸爸举高高，点点他在做什么。',
    props: { hero: '👨', items: ['🤾', '🍳', '🚗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '妈', unit: 'u19', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '妈妈抱一抱，暖暖的。',
    props: { hero: '👩', items: ['🤱', '🍲', '❤️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弟', unit: 'u19', theme: 'family',
    template: 'sort-buckets', interaction: 'drag',
    narration: '弟弟比我小，放到小的那边。',
    props: { hero: '👦', items: [{ item: '🧔', bucket: '大' }, { item: '👨', bucket: '大' }, { item: '👦', bucket: '小' }, { item: '👶', bucket: '小' }], buckets: [{ label: '大', emoji: '🔼' }, { label: '小', emoji: '🔽' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '爷', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '爷爷是爸爸的爸爸，连一连。',
    props: { hero: '👴', pairs: [{ a: '👴', b: '👨' }, { a: '👵', b: '👩' }], goal: 2 },
    templateFallback: false
  },
  {
    char: '叔', unit: 'u19', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '叔叔是爸爸的弟弟，找出叔叔。',
    props: { hero: '🧔', target: '🧔', decoys: ['👴', '👦', '👶'], goal: 1 },
    templateFallback: false
  },
  {
    char: '姑', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '姑姑是爸爸的姐妹，配一配。',
    props: { hero: '👩‍🦰', pairs: [{ a: '👨', b: '👩‍🦰' }, { a: '👩', b: '🧑‍🦱' }], goal: 2 },
    templateFallback: false
  },
  {
    char: '姨', unit: 'u19', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '阿姨是妈妈的姐妹，点出阿姨。',
    props: { hero: '🧑‍🦱', target: '🧑‍🦱', decoys: ['👴', '👦', '🧒'], goal: 1 },
    templateFallback: false
  },
  {
    char: '亲', unit: 'u19', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '亲一亲抱一抱，最亲的人在身边。',
    props: { hero: '🤗', items: ['❤️', '💞', '💗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '客', unit: 'u19', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '客人来啦，请他喝茶、坐下。',
    props: { hero: '🛎️', items: ['🍵', '🪑', '🍪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '伴', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '好伙伴要两个人，配成一对。',
    props: { hero: '👯', pairs: [{ a: '🧒', b: '🧒' }, { a: '👦', b: '👧' }, { a: '👯', b: '👯' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '伙', unit: 'u19', theme: 'family',
    template: 'count-tap', interaction: 'tap',
    narration: '一群小伙伴，数数一共几个。',
    props: { hero: '🧑‍🤝‍🧑', items: ['🧒', '🧒', '🧒', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '邻', unit: 'u19', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '隔壁邻居家，去打个招呼。',
    props: { hero: '🏘️', items: ['🚪', '🔔', '👋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '众', unit: 'u19', theme: 'family',
    template: 'count-tap', interaction: 'tap',
    narration: '三个人叠在一起，人多就是众。',
    props: { hero: '👥', items: ['🧍', '🧍', '🧍'], goal: 3 },
    templateFallback: false
  },
  {
    char: '婆', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '外婆是妈妈的妈妈，连一连。',
    props: { hero: '👵', pairs: [{ a: '👵', b: '👩' }, { a: '👴', b: '👨' }], goal: 2 },
    templateFallback: false
  },
  {
    char: '孙', unit: 'u19', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '小孙子一点点长大。',
    props: { hero: '🧒', stages: ['👶', '🧒', '👦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '娃', unit: 'u19', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '小娃娃睡着了，轻轻拍一拍。',
    props: { hero: '👶', items: ['🍼', '🧸', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '姓', unit: 'u19', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '每个人都有姓，姓在名字前面。',
    props: { hero: '🏷️', parts: ['姓', '名'], word: '姓名', goal: 2 },
    templateFallback: false
  },
  {
    char: '名', unit: 'u19', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '写下自己的名字，念一念。',
    props: { hero: '📛', parts: ['名', '字'], word: '名字', goal: 2 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
