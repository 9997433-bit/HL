/**
 * 徽章体系 v1。
 *
 * 每一枚徽章都是「某个指标攒够了」，而不是隐藏成就：
 * 孩子在成就墙上能看见还差多少，家长在报告里能看见孩子最近在往哪个方向走。
 *
 * 字段说明：
 *   id      稳定标识，写进存档，改名不会丢徽章
 *   metric  对应 progress store `badgeStats` 里的一个指标名
 *   goal    指标达到多少就解锁
 *   unit    进度文案的量词（「3 / 5 字」里的「字」）
 *   tier    只影响配色，bronze < silver < gold
 *
 * 只用「单指标 + 阈值」这一种规则是有意的：徽章要能在界面上画出进度条，
 * 复合条件（比如「连续 3 天且每天 5 个字」）没法用一根进度条说清楚。
 */

export const BADGE_TIERS = {
  bronze: { label: '铜', color: 'var(--seed-mango)' },
  silver: { label: '银', color: 'var(--seed-sky)' },
  gold: { label: '金', color: 'var(--seed-grape)' }
}

export const BADGES = [
  {
    id: 'first-step',
    name: '启蒙芽',
    emoji: '🌱',
    tier: 'bronze',
    metric: 'learned',
    goal: 1,
    unit: '字',
    desc: '认识第一个汉字',
    hint: '打开任意一个字的学习页，听一听它的读音'
  },
  {
    id: 'ten-chars',
    name: '识字小星',
    emoji: '⭐',
    tier: 'bronze',
    metric: 'learned',
    goal: 10,
    unit: '字',
    desc: '认识 10 个汉字',
    hint: '每天学几个字，很快就够了'
  },
  {
    id: 'fifty-chars',
    name: '识字达人',
    emoji: '📚',
    tier: 'gold',
    metric: 'learned',
    goal: 50,
    unit: '字',
    desc: '认识 50 个汉字',
    hint: '按单元一路学下去'
  },
  {
    id: 'master-five',
    name: '掌握小能手',
    emoji: '🏆',
    tier: 'silver',
    metric: 'mastered',
    goal: 5,
    unit: '字',
    desc: '把 5 个字练到「真掌握」',
    hint: '写一遍、再答对两次，字就掌握了'
  },
  {
    id: 'brush-hand',
    name: '小小书法家',
    emoji: '✍️',
    tier: 'silver',
    metric: 'traced',
    goal: 10,
    unit: '遍',
    desc: '在田字格里描红 10 遍',
    hint: '单字页点「我来写」，写完一整个字算一遍'
  },
  {
    id: 'full-loop',
    name: '五步全通',
    emoji: '🧭',
    tier: 'silver',
    metric: 'flows',
    goal: 3,
    unit: '次',
    desc: '走完 3 次「认一认 → 写一写 → 听一听 → 考一考 → 领奖励」',
    hint: '在单字页跟着上面的五步一路走到底'
  },
  {
    id: 'sharp-ear',
    name: '顺风耳',
    emoji: '👂',
    tier: 'bronze',
    metric: 'listenStreak',
    goal: 5,
    unit: '连对',
    desc: '听音识字连对 5 题',
    hint: '去听音识字玩一局'
  },
  {
    id: 'streak-three',
    name: '三天不断',
    emoji: '🔥',
    tier: 'bronze',
    metric: 'streak',
    goal: 3,
    unit: '天',
    desc: '连续 3 天来学习',
    hint: '每天来一小会儿就算数'
  },
  {
    id: 'bookworm',
    name: '小书虫',
    emoji: '📖',
    tier: 'silver',
    metric: 'books',
    goal: 3,
    unit: '本',
    desc: '读完 3 本分级绘本',
    hint: '绘本只用学过的字写成，读得完'
  },
  {
    id: 'idiom-friend',
    name: '成语小友',
    emoji: '🏮',
    tier: 'gold',
    metric: 'idioms',
    goal: 3,
    unit: '个',
    desc: '看懂 3 个成语小剧场',
    hint: '成语启蒙里每个故事只有四格'
  },
  {
    id: 'little-poet',
    name: '小诗人',
    emoji: '📜',
    tier: 'gold',
    metric: 'poems',
    goal: 3,
    unit: '首',
    desc: '跟读过 3 首古诗',
    hint: '古诗长廊里点「跟着读」，听完范读自己读一遍'
  }
]

export const BADGE_MAP = new Map(BADGES.map((b) => [b.id, b]))

export const TOTAL_BADGES = BADGES.length

export const getBadge = (id) => BADGE_MAP.get(id) ?? null

export const badgeColor = (badge) =>
  BADGE_TIERS[badge?.tier]?.color ?? BADGE_TIERS.bronze.color
