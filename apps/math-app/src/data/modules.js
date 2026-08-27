/**
 * 玩法模块（星球）定义 —— 玩法层的唯一真源。
 *
 * id  : 进度统计与成就判定使用的模块键
 * route: 路由路径，与 curriculum.js 中的架构模块 id 对齐
 * node : 学习地图上的坐标（百分比）
 * starsToUnlock: 解锁该星球所需的累计星星数
 *
 * 三条叙事文案对应星球在地图上的三种状态，缺一条孩子就会看到空白：
 *   lockedStory 还没解锁时的一句话预告，要说清「为什么现在去不了」
 *   story       解锁之后的一句话介绍，说清「到了那儿干什么」
 *   unlockLine  刚解锁那一下的过场台词，只播一次
 */
export const MODULES = [
  {
    id: 'counting',
    curriculumId: 'number-sense',
    name: '数量星云',
    subtitle: '1–20 数与量启蒙',
    blurb: '把小星星拖进货舱，学会点数与数量对应。',
    route: '/number-sense',
    emoji: '🪐',
    icon: '🪐',
    color: '#5ee7ff',
    accent: '#9b8cff',
    node: { x: 12, y: 72 },
    starsToUnlock: 0,
    skills: ['点数', '数量对应', '数序'],
    story: '星云里飘着数不清的小星星，先一颗一颗把它们数清楚。',
    lockedStory: '这里是所有航线的起点，飞船随时可以出发。',
    unlockLine: '引擎点火，数量星云的雾气在舷窗外散开了。',
  },
  {
    id: 'arithmetic',
    curriculumId: 'arithmetic',
    name: '算术恒星',
    subtitle: '加减法练习',
    blurb: '10 以内与 100 以内自由切换，越算越快。',
    route: '/arithmetic',
    emoji: '☀️',
    icon: '☀️',
    color: '#ffce4d',
    accent: '#ff9f45',
    node: { x: 30, y: 30 },
    starsToUnlock: 3,
    skills: ['加法', '减法', '心算'],
    story: '这颗恒星靠加减法发光，算得越快，它烧得越旺。',
    lockedStory: '远处有颗恒星忽明忽暗，攒够星星才有燃料靠近它。',
    unlockLine: '燃料够了！算术恒星把整片舷窗照成了金色。',
  },
  {
    id: 'geometry',
    curriculumId: 'geometry',
    name: '形状卫星',
    subtitle: '几何认知',
    blurb: '在陨石群里找出正确的图形。',
    route: '/geometry',
    emoji: '🛰️',
    icon: '🛰️',
    color: '#ff7ac6',
    accent: '#9b8cff',
    node: { x: 48, y: 70 },
    starsToUnlock: 6,
    skills: ['平面图形', '立体图形', '观察力'],
    story: '卫星被陨石撞散成了各种形状，把它们一块块认回来。',
    lockedStory: '一颗卫星卡在陨石带里，星星够多才开得出救援航道。',
    unlockLine: '陨石带让开一条缝，形状卫星慢慢转到了你面前。',
  },
  {
    id: 'logic',
    curriculumId: 'logic',
    name: '规律环带',
    subtitle: '逻辑推理',
    blurb: '找出序列中缺失的那一环。',
    route: '/logic',
    emoji: '🌀',
    icon: '🌀',
    color: '#55e6a5',
    accent: '#5ee7ff',
    node: { x: 64, y: 26 },
    starsToUnlock: 10,
    skills: ['找规律', '归纳', '推理'],
    story: '环带上的石头按规律排队，缺的那一颗要你补上。',
    lockedStory: '环带转得太快，看不清队形，得再攒些星星才追得上。',
    unlockLine: '环带停住了，石头排成一列，等你接上下一颗。',
  },
  {
    id: 'sudoku',
    curriculumId: 'sudoku',
    name: '数独空间站',
    subtitle: '4×4 数独入门',
    blurb: '每行每列每宫，1–4 只出现一次。',
    route: '/sudoku',
    emoji: '🧩',
    icon: '🧩',
    color: '#9b8cff',
    accent: '#ff7ac6',
    node: { x: 80, y: 64 },
    starsToUnlock: 14,
    skills: ['约束推理', '专注力'],
    story: '空间站的四个舱室，每行每列都不许住重样的数字。',
    lockedStory: '空间站的舱门上着密码锁，星星就是配钥匙的材料。',
    unlockLine: '密码对上了，数独空间站的舱门朝你缓缓打开。',
  },
  {
    id: 'word',
    curriculumId: 'word-problems',
    name: '生活行星',
    subtitle: '应用题练习',
    blurb: '把生活里的问题变成算式。',
    route: '/word-problems',
    emoji: '🌍',
    icon: '🌍',
    color: '#ff9f45',
    accent: '#ffce4d',
    node: { x: 93, y: 24 },
    starsToUnlock: 18,
    skills: ['读题', '建模', '两步应用题'],
    story: '行星上的人天天遇到麻烦，你负责把它们翻译成算式。',
    lockedStory: '最远处有颗有云有海的行星，星星够多才飞得到那里。',
    unlockLine: '着陆成功，生活行星的居民排着队来问问题了。',
  },
]

export const MODULE_MAP = Object.fromEntries(MODULES.map((m) => [m.id, m]))

/**
 * 不占学习地图星球位、但会写进度与历史记录的玩法。
 * 少了这份登记，成就墙的历史列表里就会冒出裸 id。
 */
export const SIDE_MODULES = {
  daily: { id: 'daily', name: '今日冒险', icon: '🗓️', route: '/daily' },
  compare: { id: 'compare', name: '比大小擂台', icon: '⚖️', route: '/compare' },
}

/** 玩法 id → 展示信息，星球与非星球玩法都能查到。 */
export const moduleInfo = (id) => MODULE_MAP[id] ?? SIDE_MODULES[id] ?? null

/** 玩法模块 id → curriculum.js 中的架构模块 id */
export const CURRICULUM_ID = Object.fromEntries(MODULES.map((m) => [m.id, m.curriculumId]))

export const moduleName = (id) => moduleInfo(id)?.name ?? id
