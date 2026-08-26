/**
 * 学习地图上的星球（模块）定义。
 * order 决定地图上的解锁顺序，starsToUnlock 为进入该星球所需的累计星星数。
 */
export const MODULES = [
  {
    id: 'counting',
    name: '数量星云',
    subtitle: '1–20 数与量启蒙',
    blurb: '把小星星拖进飞船，学会点数与数量对应。',
    route: '/counting',
    emoji: '🪐',
    color: '#5ee7ff',
    accent: '#9b8cff',
    starsToUnlock: 0,
    skills: ['点数', '数量对应', '数序'],
  },
  {
    id: 'arithmetic',
    name: '算术恒星',
    subtitle: '加减法练习',
    blurb: '10 以内与 100 以内自由切换，越算越快。',
    route: '/arithmetic',
    emoji: '☀️',
    color: '#ffce4d',
    accent: '#ff9f45',
    starsToUnlock: 3,
    skills: ['加法', '减法', '心算'],
  },
  {
    id: 'geometry',
    name: '形状卫星',
    subtitle: '几何认知',
    blurb: '在陨石群里找出正确的图形。',
    route: '/geometry',
    emoji: '🛰️',
    color: '#ff7ac6',
    accent: '#9b8cff',
    starsToUnlock: 6,
    skills: ['平面图形', '立体图形', '观察力'],
  },
  {
    id: 'logic',
    name: '规律环带',
    subtitle: '逻辑推理',
    blurb: '找出序列中缺失的一环。',
    route: '/logic',
    emoji: '🌀',
    color: '#55e6a5',
    accent: '#5ee7ff',
    starsToUnlock: 10,
    skills: ['找规律', '归纳', '推理'],
  },
  {
    id: 'sudoku',
    name: '数独空间站',
    subtitle: '4×4 数独入门',
    blurb: '每行每列每宫，1–4 只出现一次。',
    route: '/sudoku',
    emoji: '🧩',
    color: '#9b8cff',
    accent: '#ff7ac6',
    starsToUnlock: 14,
    skills: ['约束推理', '专注力'],
  },
  {
    id: 'word',
    name: '生活行星',
    subtitle: '应用题练习',
    blurb: '把生活里的问题变成算式。',
    route: '/word-problems',
    emoji: '🌍',
    color: '#ff9f45',
    accent: '#ffce4d',
    starsToUnlock: 18,
    skills: ['读题', '建模', '两步应用题'],
  },
]

export const MODULE_MAP = Object.fromEntries(MODULES.map((m) => [m.id, m]))

/** 地图上每个星球的坐标（百分比），用于绘制轨道路径。 */
export const MAP_NODES = {
  counting: { x: 12, y: 72 },
  arithmetic: { x: 30, y: 32 },
  geometry: { x: 48, y: 70 },
  logic: { x: 64, y: 28 },
  sudoku: { x: 80, y: 64 },
  word: { x: 93, y: 26 },
}
