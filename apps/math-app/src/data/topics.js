/**
 * 专题挑战 —— 不占星球位、但要在首页与成就墙都摆出入口的三条专线。
 *
 * 星球地图讲的是「按章节一路飞下去」，专题讲的是「今天想专门补哪一块」：
 * 比较、速算、生活应用各是一种独立的数学动作，孩子（和家长）会点着找，
 * 埋在某个星球里面就等于没有。三处入口（首页专题区、成就墙专题行、
 * 星球内部的专题条）都读这一份表，改一次三处同步。
 *
 * record: 这条专线的答题记在哪个模块名下。专题复用星球的玩法壳，
 *         掌握度也就并进对应星球，不另开一份对不上号的统计。
 */
export const TOPICS = [
  {
    id: 'compare',
    name: '比大小擂台',
    route: '/compare',
    emoji: '⚖️',
    record: 'counting',
    tagline: '整轮只出 > < =',
    blurb: '两边各有多少？开口永远朝着大的那一边。',
    skills: ['比较', '数序', '等号'],
  },
  {
    id: 'sprint',
    name: '速算冲刺',
    route: '/sprint',
    emoji: '⚡',
    record: 'arithmetic',
    tagline: '15 题连答 · 秒答加星',
    blurb: '三秒内答对多拿一颗星，练的是脱口而出的口算。',
    skills: ['口算', '连击', '专注力'],
  },
  {
    id: 'life',
    name: '生活应用',
    route: '/word-problems',
    emoji: '🛒',
    record: 'word',
    tagline: '买东西 · 分东西 · 排队',
    blurb: '把一段生活里的小事，翻译成一道算得出来的算式。',
    skills: ['读题', '建模', '两步计算'],
  },
]

export const TOPIC_MAP = Object.fromEntries(TOPICS.map((t) => [t.id, t]))
