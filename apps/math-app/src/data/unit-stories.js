/**
 * 星球地图的章节叙事 —— 文案层的唯一真源。
 *
 * 学习地图上的六颗星球同时也是六个章节。孩子站在地图前会连着问三个问题，
 * 每个问题都要有一句现成的话答上：
 *
 *   「我现在在第几章？」     chapterNo / chapterName
 *   「到了那儿干什么？」     story（已解锁）/ lockedStory（还锁着时的预告）
 *   「怎样才能进去？」       unlockHint —— 说清做什么能攒够星星，而不是只报价格
 *   「学到什么算通关？」     goal —— 家长看得懂的一句目标，也是孩子的自检标准
 *   刚打开那一下播什么       unlockLine，只播一次
 *
 * 拆成独立文件的原因和识字侧 `unit-stories.js` 一样：`modules.js` 管的是玩法
 * 接线（路由、坐标、解锁星数、技能标签），文案改起来比接线频繁得多，混在一起
 * 每改一句话都要动玩法真源。这里只写话，不参与任何解锁判定——能不能进某颗星球
 * 由 `progress.isModuleUnlocked()` 按 `starsToUnlock` 说了算，改文案既锁不上门
 * 也开不了门。
 */

const CHAPTERS = {
  counting: {
    chapterNo: 1,
    chapterName: '第一章 · 起航云海',
    story: '星云里飘着数不清的小星星，先一颗一颗把它们数清楚。',
    lockedStory: '这里是所有航线的起点，飞船随时可以出发。',
    unlockHint: '起点章节不要星星，按下「继续冒险」就能出发。',
    goal: '通关标志：20 以内的数量看一眼就报得出、比得出大小。',
    unlockLine: '引擎点火，数量星云的雾气在舷窗外散开了。',
  },
  arithmetic: {
    chapterNo: 2,
    chapterName: '第二章 · 恒星燃料',
    story: '这颗恒星靠加减法发光，算得越快，它烧得越旺。',
    lockedStory: '远处有颗恒星忽明忽暗，攒够星星才有燃料靠近它。',
    unlockHint: '在数量星云答对六七道题，燃料表就满了。',
    goal: '通关标志：10 以内加减脱口而出，20 以内会用凑十法。',
    unlockLine: '燃料够了！算术恒星把整片舷窗照成了金色。',
  },
  geometry: {
    chapterNo: 3,
    chapterName: '第三章 · 陨石修理厂',
    story: '卫星被陨石撞散成了各种形状，把它们一块块认回来。',
    lockedStory: '一颗卫星卡在陨石带里，星星够多才开得出救援航道。',
    unlockHint: '在算术恒星连对几轮，救援航道的星星就攒齐了。',
    goal: '通关标志：常见平面图形叫得出名字，立体图形分得清。',
    unlockLine: '陨石带让开一条缝，形状卫星慢慢转到了你面前。',
  },
  logic: {
    chapterNo: 4,
    chapterName: '第四章 · 环带密码',
    story: '环带上的石头按规律排队，缺的那一颗要你补上。',
    lockedStory: '环带转得太快，看不清队形，得再攒些星星才追得上。',
    unlockHint: '每天做完今日冒险，四五天就能追上环带的转速。',
    goal: '通关标志：看三四项就能说出规律，并补出下一项。',
    unlockLine: '环带停住了，石头排成一列，等你接上下一颗。',
  },
  sudoku: {
    chapterNo: 5,
    chapterName: '第五章 · 空间站四舱',
    story: '空间站的四个舱室，每行每列都不许住重样的数字。',
    lockedStory: '空间站的舱门上着密码锁，星星就是配钥匙的材料。',
    unlockHint: '规律环带里全对一轮能多拿几颗星，钥匙很快配得出。',
    goal: '通关标志：4×4 数独能独立填完，说得清「为什么只能是它」。',
    unlockLine: '密码对上了，数独空间站的舱门朝你缓缓打开。',
  },
  word: {
    chapterNo: 6,
    chapterName: '第六章 · 归乡航线',
    story: '行星上的人天天遇到麻烦，你负责把它们翻译成算式。',
    lockedStory: '最远处有颗有云有海的行星，星星够多才飞得到那里。',
    unlockHint: '把前五章的错题本清干净，剩下的星星就够飞完全程。',
    goal: '通关标志：读完一段生活小事，能自己列出算式并算对。',
    unlockLine: '着陆成功，生活行星的居民排着队来问问题了。',
  },
}

/**
 * 兜底：新加星球还没配章节文案时，用它自己的 name / subtitle 顶上。
 * 宁可话说得平淡，也不能让地图上出现空白的一行。
 */
const fallback = (mod = {}, index = 0) => ({
  chapterNo: index + 1,
  chapterName: `第 ${index + 1} 章 · ${mod.name ?? '未知星域'}`,
  story: `${mod.subtitle ?? '新的星域'}，这一站的题都在这儿等你。`,
  lockedStory: `${mod.name ?? '这颗星球'}还在航线外，攒够星星才飞得到。`,
  unlockHint: `累计 ${mod.starsToUnlock ?? 0} ⭐ 就能解锁。`,
  goal: `通关标志：${mod.subtitle ?? '这一章的内容'}练熟。`,
  unlockLine: `${mod.name ?? '新星球'}解锁了，出发吧！`,
})

/** 某颗星球的全套章节文案；查不到就按兜底模板现编一份。 */
export const planetNarrative = (id, mod, index = 0) => CHAPTERS[id] ?? fallback(mod, index)

/** 章节名，例：「第二章 · 恒星燃料」。 */
export const planetChapterName = (id) => CHAPTERS[id]?.chapterName ?? ''

/** 还锁着时的解锁做法：说清「做什么」，星数差多少由地图当场算。 */
export const planetUnlockHint = (id) => CHAPTERS[id]?.unlockHint ?? ''

export const TOTAL_PLANET_STORIES = Object.keys(CHAPTERS).length
