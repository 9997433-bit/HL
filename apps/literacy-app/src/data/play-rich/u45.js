/**
 * 富互动 play 分片 u45 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u45'

export const UNIT_RICH_PLAYS = [
  {
    char: '京', unit: 'u45', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '城楼一层层盖高，就是京城。',
    props: { hero: '🏯', stages: ['🧱', '🏛️', '🏯'], goal: 3 },
    templateFallback: false
  },
  {
    char: '华', unit: 'u45', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把灯笼涂得红彤彤，真华丽。',
    props: { hero: '🏮', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '汉', unit: 'u45', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '「汉」和「字」凑成一个词。',
    props: { hero: '🈶', parts: ['汉', '字'], word: '汉字', goal: 2 },
    templateFallback: false
  },
  {
    char: '族', unit: 'u45', theme: 'family',
    template: 'count-tap', interaction: 'tap',
    narration: '一家人排排站，数数几口。',
    props: { hero: '👨‍👩‍👧‍👦', items: ['👦', '👧', '👨', '👩'], goal: 4 },
    templateFallback: false
  },
  {
    char: '民', unit: 'u45', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '种地的、做工的，都是老百姓。',
    props: { hero: '🧑‍🌾', items: ['🧑‍🌾', '🧑‍🏭', '🧑‍🍳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '州', unit: 'u45', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '水中间的那块陆地，连成州。',
    props: { hero: '🗺️', parts: ['🟩', '🟦', '🟩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '省', unit: 'u45', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '城市归城市，村子归村子。',
    props: { hero: '🗺️', items: [{ item: '🏢', bucket: '城里' }, { item: '🚇', bucket: '城里' }, { item: '🌾', bucket: '村里' }, { item: '🐄', bucket: '村里' }], buckets: [{ label: '城里', emoji: '🏙️' }, { label: '村里', emoji: '🏘️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '县', unit: 'u45', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '小城什么样？把它挑出来。',
    props: { hero: '🏘️', target: '🏘️', decoys: ['🏙️', '🏝️', '🏜️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '界', unit: 'u45', theme: 'shape',
    template: 'trace-path', interaction: 'drag',
    narration: '沿着这条线画，两边分界。',
    props: { hero: '〰️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '洲', unit: 'u45', theme: 'place',
    template: 'pair-match', interaction: 'drag',
    narration: '每块大洲配上它的动物。',
    props: { hero: '🌏', pairs: [{ a: '🌏', b: '🐼' }, { a: '🌍', b: '🦁' }, { a: '🌎', b: '🦥' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '旗', unit: 'u45', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '风一吹，旗子往右飘起来。',
    props: { hero: '🚩', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '陆', unit: 'u45', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '陆上走的、海里游的，分开。',
    props: { hero: '🌍', items: [{ item: '🐘', bucket: '陆地' }, { item: '🐎', bucket: '陆地' }, { item: '🐬', bucket: '海里' }, { item: '🐙', bucket: '海里' }], buckets: [{ label: '陆地', emoji: '🌍' }, { label: '海里', emoji: '🌊' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '岭', unit: 'u45', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '一座连一座，连成一道岭。',
    props: { hero: '⛰️', stages: ['🌄', '⛰️', '🏞️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '峰', unit: 'u45', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '顺着山坡往上，爬到山峰。',
    props: { hero: '🏔️', dir: 'up', goal: 4 },
    templateFallback: false
  },
  {
    char: '峡', unit: 'u45', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '两边山夹一条水，就是峡。',
    props: { hero: '🏞️', parts: ['⛰️', '🌊', '⛰️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '崖', unit: 'u45', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '站在崖边往下看，好高啊。',
    props: { hero: '🧗', stages: ['🧗', '🪨', '🕳️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '沟', unit: 'u45', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '水顺着小沟一路流走。',
    props: { hero: '💧', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '原', unit: 'u45', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '大草原上有什么？点点看。',
    props: { hero: '🌾', items: ['🐑', '🐎', '🏕️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '野', unit: 'u45', theme: 'nature',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '野地里藏着小兔子，找到它。',
    props: { hero: '🌿', target: '🐇', decoys: ['🌿', '🌾', '🍄'], goal: 1 },
    templateFallback: false
  },
  {
    char: '迹', unit: 'u45', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '雪地上一串脚印，数四个。',
    props: { hero: '👣', items: ['👣', '👣', '👣', '👣'], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
