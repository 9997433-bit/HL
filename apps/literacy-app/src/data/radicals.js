/**
 * 偏旁部首资料。
 * `chars` 里列出的汉字应当出现在 characters.js 中，
 * 这样点击示例字就能直接跳到该字的学习页。
 */

export const RADICALS = [
  {
    id: 'ren',
    glyph: '亻',
    name: '单人旁',
    pinyin: 'dān rén páng',
    from: '人',
    emoji: '🧍',
    hint: '由「人」字变来，写在字的左边就变瘦了。',
    meaning: '带单人旁的字，多半和「人」有关系。',
    strokes: 2,
    chars: ['人', '会'],
    more: ['你', '他', '们', '住']
  },
  {
    id: 'shui',
    glyph: '氵',
    name: '三点水',
    pinyin: 'sān diǎn shuǐ',
    from: '水',
    emoji: '💧',
    hint: '三滴水珠往下滴，就是三点水。',
    meaning: '带三点水的字，几乎都和「水」有关。',
    strokes: 3,
    chars: ['水'],
    more: ['江', '河', '海', '汗']
  },
  {
    id: 'mu',
    glyph: '木',
    name: '木字旁',
    pinyin: 'mù zì páng',
    from: '木',
    emoji: '🌲',
    hint: '一棵树，有树干也有树枝。',
    meaning: '带木字旁的字，大多和树木、木头有关。',
    strokes: 4,
    chars: ['木', '来'],
    more: ['林', '树', '桌', '果']
  },
  {
    id: 'kou',
    glyph: '口',
    name: '口字旁',
    pinyin: 'kǒu zì páng',
    from: '口',
    emoji: '👄',
    hint: '一个方方的小嘴巴。',
    meaning: '带口字旁的字，常和嘴巴、说话、吃东西有关。',
    strokes: 3,
    chars: ['口'],
    more: ['吃', '叫', '唱', '和']
  },
  {
    id: 'ri',
    glyph: '日',
    name: '日字旁',
    pinyin: 'rì zì páng',
    from: '日',
    emoji: '☀️',
    hint: '太阳从方框里探出头来。',
    meaning: '带日字旁的字，多和太阳、时间有关。',
    strokes: 4,
    chars: ['日', '是'],
    more: ['明', '早', '晚', '时']
  },
  {
    id: 'cao',
    glyph: '艹',
    name: '草字头',
    pinyin: 'cǎo zì tóu',
    from: '草',
    emoji: '🌱',
    hint: '两棵小草并排长在字的头顶上。',
    meaning: '带草字头的字，几乎都是花草植物。',
    strokes: 3,
    chars: ['花'],
    more: ['草', '菜', '苗', '叶']
  },
  {
    id: 'shou',
    glyph: '扌',
    name: '提手旁',
    pinyin: 'tí shǒu páng',
    from: '手',
    emoji: '✋',
    hint: '由「手」字变来，最后一笔往上提。',
    meaning: '带提手旁的字，大多是手上的动作。',
    strokes: 3,
    chars: ['手'],
    more: ['打', '拿', '拉', '抱']
  },
  {
    id: 'xin',
    glyph: '忄',
    name: '竖心旁',
    pinyin: 'shù xīn páng',
    from: '心',
    emoji: '❤️',
    hint: '把「心」字立起来写在左边。',
    meaning: '带竖心旁的字，多和心情、想法有关。',
    strokes: 3,
    chars: ['心'],
    more: ['快', '慢', '怕', '情']
  },
  {
    id: 'huo',
    glyph: '火',
    name: '火字旁',
    pinyin: 'huǒ zì páng',
    from: '火',
    emoji: '🔥',
    hint: '火苗左右各一撇，中间往上窜。',
    meaning: '带火字旁的字，多和火、热有关。',
    strokes: 4,
    chars: ['火'],
    more: ['灯', '烧', '热', '炒']
  },
  {
    id: 'nv',
    glyph: '女',
    name: '女字旁',
    pinyin: 'nǚ zì páng',
    from: '女',
    emoji: '👧',
    hint: '像一个人跪坐着，双手交叉。',
    meaning: '带女字旁的字，常和女性、家人有关。',
    strokes: 3,
    chars: ['好'],
    more: ['妈', '姐', '妹', '她']
  },
  {
    id: 'yan',
    glyph: '讠',
    name: '言字旁',
    pinyin: 'yán zì páng',
    from: '言',
    emoji: '💬',
    hint: '由「言」字简化而来。',
    meaning: '带言字旁的字，基本都和说话有关。',
    strokes: 2,
    chars: ['说'],
    more: ['话', '读', '语', '谢']
  },
  {
    id: 'tu',
    glyph: '土',
    name: '提土旁',
    pinyin: 'tí tǔ páng',
    from: '土',
    emoji: '🟫',
    hint: '「土」写在左边，下面一横改成提。',
    meaning: '带提土旁的字，多和泥土、土地有关。',
    strokes: 3,
    chars: ['土', '在', '去'],
    more: ['地', '场', '坐', '城']
  },
  {
    id: 'mubu',
    glyph: '目',
    name: '目字旁',
    pinyin: 'mù zì páng',
    from: '目',
    emoji: '👁️',
    hint: '竖起来的眼睛，里面有两横。',
    meaning: '带目字旁的字，多和眼睛、看有关。',
    strokes: 5,
    chars: ['目', '看'],
    more: ['眼', '睡', '眨', '睛']
  },
  {
    id: 'shan',
    glyph: '山',
    name: '山字旁',
    pinyin: 'shān zì páng',
    from: '山',
    emoji: '⛰️',
    hint: '三座山尖，中间那座最高。',
    meaning: '带山字旁的字，多和山、高处有关。',
    strokes: 3,
    chars: ['山'],
    more: ['岛', '峰', '岩', '崖']
  }
]

export const RADICAL_MAP = new Map(RADICALS.map((r) => [r.id, r]))

/** 兜底部首：语料里出现但不在重点讲解列表中的，用它渲染。 */
const FALLBACK = {
  yi: { id: 'yi', glyph: '一', name: '横', pinyin: 'héng' },
  da: { id: 'da', glyph: '大', name: '大字头', pinyin: 'dà zì tóu' },
  xiao: { id: 'xiao', glyph: '小', name: '小字头', pinyin: 'xiǎo zì tóu' },
  ge: { id: 'ge', glyph: '戈', name: '戈字旁', pinyin: 'gē zì páng' },
  yue: { id: 'yue', glyph: '月', name: '月字旁', pinyin: 'yuè zì páng' },
  tian: { id: 'tian', glyph: '田', name: '田字旁', pinyin: 'tián zì páng' },
  er: { id: 'er', glyph: '耳', name: '耳字旁', pinyin: 'ěr zì páng' },
  niu: { id: 'niu', glyph: '牛', name: '牛字旁', pinyin: 'niú zì páng' },
  yang: { id: 'yang', glyph: '羊', name: '羊字头', pinyin: 'yáng zì tóu' },
  niao: { id: 'niao', glyph: '鸟', name: '鸟字旁', pinyin: 'niǎo zì páng' },
  shu: { id: 'shu', glyph: '丨', name: '竖', pinyin: 'shù' },
  bai: { id: 'bai', glyph: '白', name: '白字旁', pinyin: 'bái zì páng' }
}

export function getRadical(id) {
  return RADICAL_MAP.get(id) || FALLBACK[id] || null
}
