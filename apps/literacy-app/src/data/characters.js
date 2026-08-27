/**
 * 识字语料库 —— 1000 个学前到小学中段的高频字，按「单元」分组。
 *
 * 字表以 `shared/data/common-hanzi.json` 为事实基线：那份 JSON 里的每个字都必须
 * 在这里出现，且拼音一致，`npm run check:data` 会守住这条。这里比基线多出来的
 * 字段（声调、部首、组词、例句、卡片图标）是识字 App 的教学包装。
 *
 * 字表长到上千个字之后，整份语料一次性进主包已经不合适了，于是拆成两层：
 *
 *   char-index.js   每个字的「轻」信息（拼音 / 声调 / 单元 / 部首 / 笔画 / 图标），
 *                   首页地图、字表卡片、复习队列、家长报表都只需要这一层，
 *                   它随主包一起加载，由 scripts/gen-char-corpus.mjs 生成。
 *   chars/uN.js     每个单元的「重」内容（释义 / 组词 / 例句），
 *                   由下面的加载器 import() 进来，翻到哪个单元才下载哪一包。
 *
 * 两层的字必须一一对应，check:data 会核对，缺一个都算失败。
 *
 * 字段用途：
 *   char      汉字本体
 *   pinyin    带声调拼音
 *   tone      声调（1-4，5 表示轻声），用于拼音色彩标注
 *   radical   部首（与 radicals.js 的 id 对应）
 *   strokes   笔画数（用于田字格提示，笔顺动画由 hanzi-writer 运行时提供）
 *   emoji     卡片图标，替代插画资源
 *   unit      所属单元
 *   meaning   儿童能懂的一句话释义     ← 详情层
 *   words     组词，每条含拼音          ← 详情层
 *   sentence  例句 + 拼音               ← 详情层
 *
 * 绘本（books.js）中出现的所有汉字都必须在这里能查到，
 * `verifyBookCoverage()` 会在开发模式下校验这一点。
 */

import { CHAR_INDEX } from './char-index.js'

export const UNITS = [
  { id: 'u1', name: '我和数字', emoji: '🔢', color: 'var(--seed-mango)', desc: '最先学会的十个字' },
  { id: 'u2', name: '大自然', emoji: '🌿', color: 'var(--seed-leaf)', desc: '日月山水，都在身边' },
  { id: 'u3', name: '身体和动物', emoji: '🐑', color: 'var(--seed-sky)', desc: '认识自己，认识小伙伴' },
  { id: 'u4', name: '会说话', emoji: '💬', color: 'var(--seed-grape)', desc: '把字连成句子' },
  { id: 'u5', name: '数字大家庭', emoji: '🔟', color: 'var(--seed-mint)', desc: '从四一直数到万' },
  { id: 'u6', name: '天气和大地', emoji: '🌦️', color: 'var(--seed-coral)', desc: '风雨云雪，脚下的土地' },
  { id: 'u7', name: '我的家人', emoji: '👨‍👩‍👧', color: 'var(--seed-mango)', desc: '一家人在一起' },
  { id: 'u8', name: '上学啦', emoji: '🎒', color: 'var(--seed-leaf)', desc: '学校里最常见的字' },
  { id: 'u9', name: '小动物', emoji: '🐟', color: 'var(--seed-sky)', desc: '水里游的，家里养的' },
  { id: 'u10', name: '五颜六色', emoji: '🎨', color: 'var(--seed-grape)', desc: '认识六种颜色' },
  { id: 'u11', name: '四季和时间', emoji: '🍂', color: 'var(--seed-mint)', desc: '春夏秋冬，早晚今明' },
  { id: 'u12', name: '出发去玩', emoji: '🚗', color: 'var(--seed-coral)', desc: '左右前后，出门啦' },
  { id: 'u13', name: '动起来', emoji: '🏃', color: 'var(--seed-mango)', desc: '走跑跳坐，身体的动作' },
  { id: 'u14', name: '家里的东西', emoji: '🛋️', color: 'var(--seed-leaf)', desc: '桌椅床灯，屋里都认得' },
  { id: 'u15', name: '好吃的', emoji: '🍚', color: 'var(--seed-sky)', desc: '米饭菜果，餐桌上的字' },
  { id: 'u16', name: '常用小词', emoji: '🔤', color: 'var(--seed-grape)', desc: '这那什么，说话离不开' },
  { id: 'u17', name: '学校里的字', emoji: '🏫', color: 'var(--seed-mint)', desc: '上课、写字、做作业' },
  { id: 'u18', name: '我的身体', emoji: '🧒', color: 'var(--seed-coral)', desc: '从头到脚都认得' },
  { id: 'u19', name: '家人和名字', emoji: '👪', color: 'var(--seed-mango)', desc: '叫得出每个人的称呼' },
  { id: 'u20', name: '动作大集合', emoji: '🤸', color: 'var(--seed-leaf)', desc: '手上的动作最好记' },
  { id: 'u21', name: '心情和感觉', emoji: '😊', color: 'var(--seed-sky)', desc: '说得出自己的感受' },
  { id: 'u22', name: '方位和数量', emoji: '🧭', color: 'var(--seed-grape)', desc: '多少、远近、里外' },
  { id: 'u23', name: '江河湖海', emoji: '🌊', color: 'var(--seed-mint)', desc: '三点水的字一大家子' },
  { id: 'u24', name: '花草树木', emoji: '🌳', color: 'var(--seed-coral)', desc: '木字旁和草字头' },
  { id: 'u25', name: '小动物园', emoji: '🦋', color: 'var(--seed-mango)', desc: '虫字旁、鸟字旁的朋友' },
  { id: 'u26', name: '厨房里的字', emoji: '🍲', color: 'var(--seed-leaf)', desc: '煮一煮，炒一炒' },
  { id: 'u27', name: '出发去远方', emoji: '🚢', color: 'var(--seed-sky)', desc: '走之旁带我们上路' },
  { id: 'u28', name: '城里城外', emoji: '🏙️', color: 'var(--seed-grape)', desc: '街市村庄，处处有字' },
  { id: 'u29', name: '时间和季节', emoji: '⏰', color: 'var(--seed-mint)', desc: '早晨、中午、星期天' },
  { id: 'u30', name: '说话的小词', emoji: '💭', color: 'var(--seed-coral)', desc: '因为所以，把话说顺' },
  { id: 'u31', name: '数一数', emoji: '🧮', color: 'var(--seed-mango)', desc: '加减和量词' },
  { id: 'u32', name: '我会学习', emoji: '📖', color: 'var(--seed-leaf)', desc: '练一练，就学会了' },
  { id: 'u33', name: '唱歌和游戏', emoji: '🎵', color: 'var(--seed-sky)', desc: '玩着玩着就认字了' },
  { id: 'u34', name: '学校与课堂', emoji: '🔔', color: 'var(--seed-grape)', desc: '上课铃一响就开始' },
  { id: 'u35', name: '说话和文章', emoji: '📝', color: 'var(--seed-mint)', desc: '把想说的写成一段话' },
  { id: 'u36', name: '车船去远方', emoji: '🚢', color: 'var(--seed-coral)', desc: '路上跑的，水里开的' },
  { id: 'u37', name: '穿在身上', emoji: '👕', color: 'var(--seed-mango)', desc: '衣裤鞋袜，布和线' },
  { id: 'u38', name: '天气变变变', emoji: '🌈', color: 'var(--seed-leaf)', desc: '晴阴霜露，冷暖来去' },
  { id: 'u39', name: '田野和庄稼', emoji: '🌾', color: 'var(--seed-sky)', desc: '种地打粮，山溪田头' },
  { id: 'u40', name: '好用的工具', emoji: '🔨', color: 'var(--seed-grape)', desc: '斧锯锤钉，样样趁手' },
  { id: 'u41', name: '看病和健康', emoji: '🏥', color: 'var(--seed-mint)', desc: '生病别怕，看医生去' },
  { id: 'u42', name: '逛商店', emoji: '🛒', color: 'var(--seed-coral)', desc: '买卖算账，一分一角' },
  { id: 'u43', name: '写信和消息', emoji: '✉️', color: 'var(--seed-mango)', desc: '把话送到很远的地方' },
  { id: 'u44', name: '过节和礼貌', emoji: '🎊', color: 'var(--seed-leaf)', desc: '节日团圆，见面问好' },
  { id: 'u45', name: '我们的国家', emoji: '🏯', color: 'var(--seed-sky)', desc: '京华山川，九州风物' },
  { id: 'u46', name: '荒野和大地', emoji: '🏜️', color: 'var(--seed-grape)', desc: '深浅宽窄，样样比一比' },
  { id: 'u47', name: '鸟兽虫鱼', emoji: '🦅', color: 'var(--seed-mint)', desc: '天上飞的，水里游的' },
  { id: 'u48', name: '花木和果子', emoji: '🍇', color: 'var(--seed-coral)', desc: '梅兰竹菊，葡萄柿子' },
  { id: 'u49', name: '房子里外', emoji: '🏠', color: 'var(--seed-mango)', desc: '墙顶梁柱，厅堂卧室' },
  { id: 'u50', name: '灶台和收拾', emoji: '🍳', color: 'var(--seed-leaf)', desc: '蒸炸煎烤，抹桌扫地' },
  { id: 'u51', name: '音乐和画画', emoji: '🎨', color: 'var(--seed-sky)', desc: '弹琴打鼓，描红涂色' },
  { id: 'u52', name: '运动会', emoji: '🏅', color: 'var(--seed-grape)', desc: '投掷攀登，比赛争先' },
  { id: 'u53', name: '用心想一想', emoji: '🤔', color: 'var(--seed-mint)', desc: '猜疑判断，观察探究' },
  { id: 'u54', name: '从前和现在', emoji: '🏺', color: 'var(--seed-coral)', desc: '古今世代，始终在变' },
  { id: 'u55', name: '量一量比一比', emoji: '⚖️', color: 'var(--seed-mango)', desc: '寸亩升斗，或多或少' },
  { id: 'u56', name: '科学和宇宙', emoji: '🚀', color: 'var(--seed-leaf)', desc: '技术器物，星辰宇宙' },
  { id: 'u57', name: '心情和身体', emoji: '😌', color: 'var(--seed-sky)', desc: '喜怒哀乐，眉眼手掌' },
  { id: 'u58', name: '讲故事', emoji: '🧚', color: 'var(--seed-grape)', desc: '神仙侠客，敲门搬家' }
]

export const UNIT_MAP = new Map(UNITS.map((u) => [u.id, u]))

/** 全部 1000 个字的轻量信息，顺序即课程顺序。 */
export const CHARACTERS = CHAR_INDEX

export const CHARACTER_MAP = new Map(CHARACTERS.map((c) => [c.char, c]))

export const TOTAL_CHARACTERS = CHARACTERS.length

export function charsOfUnit(unitId) {
  return CHARACTERS.filter((c) => c.unit === unitId)
}

/** 轻量条目（没有释义 / 组词 / 例句）。需要课文内容请用 loadCharacter()。 */
export function getCharacter(char) {
  return CHARACTER_MAP.get(char) ?? null
}

/**
 * 单元详情包。写成显式的 import() 映射而不是 import.meta.glob，
 * 是为了让 Node 脚本（check-data / gen-hanzi-data）也能直接跑。
 */
const DETAIL_LOADERS = {
  u1: () => import('./chars/u1.js'),
  u2: () => import('./chars/u2.js'),
  u3: () => import('./chars/u3.js'),
  u4: () => import('./chars/u4.js'),
  u5: () => import('./chars/u5.js'),
  u6: () => import('./chars/u6.js'),
  u7: () => import('./chars/u7.js'),
  u8: () => import('./chars/u8.js'),
  u9: () => import('./chars/u9.js'),
  u10: () => import('./chars/u10.js'),
  u11: () => import('./chars/u11.js'),
  u12: () => import('./chars/u12.js'),
  u13: () => import('./chars/u13.js'),
  u14: () => import('./chars/u14.js'),
  u15: () => import('./chars/u15.js'),
  u16: () => import('./chars/u16.js'),
  u17: () => import('./chars/u17.js'),
  u18: () => import('./chars/u18.js'),
  u19: () => import('./chars/u19.js'),
  u20: () => import('./chars/u20.js'),
  u21: () => import('./chars/u21.js'),
  u22: () => import('./chars/u22.js'),
  u23: () => import('./chars/u23.js'),
  u24: () => import('./chars/u24.js'),
  u25: () => import('./chars/u25.js'),
  u26: () => import('./chars/u26.js'),
  u27: () => import('./chars/u27.js'),
  u28: () => import('./chars/u28.js'),
  u29: () => import('./chars/u29.js'),
  u30: () => import('./chars/u30.js'),
  u31: () => import('./chars/u31.js'),
  u32: () => import('./chars/u32.js'),
  u33: () => import('./chars/u33.js'),
  u34: () => import('./chars/u34.js'),
  u35: () => import('./chars/u35.js'),
  u36: () => import('./chars/u36.js'),
  u37: () => import('./chars/u37.js'),
  u38: () => import('./chars/u38.js'),
  u39: () => import('./chars/u39.js'),
  u40: () => import('./chars/u40.js'),
  u41: () => import('./chars/u41.js'),
  u42: () => import('./chars/u42.js'),
  u43: () => import('./chars/u43.js'),
  u44: () => import('./chars/u44.js'),
  u45: () => import('./chars/u45.js'),
  u46: () => import('./chars/u46.js'),
  u47: () => import('./chars/u47.js'),
  u48: () => import('./chars/u48.js'),
  u49: () => import('./chars/u49.js'),
  u50: () => import('./chars/u50.js'),
  u51: () => import('./chars/u51.js'),
  u52: () => import('./chars/u52.js'),
  u53: () => import('./chars/u53.js'),
  u54: () => import('./chars/u54.js'),
  u55: () => import('./chars/u55.js'),
  u56: () => import('./chars/u56.js'),
  u57: () => import('./chars/u57.js'),
  u58: () => import('./chars/u58.js')
}

/** 已经下载过的单元详情：unitId → { 汉字: { meaning, words, sentence } }。 */
const detailCache = new Map()
const inFlight = new Map()

export async function loadUnitDetails(unitId) {
  if (detailCache.has(unitId)) return detailCache.get(unitId)
  const load = DETAIL_LOADERS[unitId]
  if (!load) return null
  if (!inFlight.has(unitId)) {
    inFlight.set(
      unitId,
      load().then((mod) => {
        detailCache.set(unitId, mod.default)
        inFlight.delete(unitId)
        return mod.default
      })
    )
  }
  return inFlight.get(unitId)
}

/** 已经加载进内存的单元详情；没加载过返回 null，不会触发下载。 */
export function getUnitDetails(unitId) {
  return detailCache.get(unitId) ?? null
}

/** 轻量条目 + 课文内容。字不在表里时返回 null。 */
export async function loadCharacter(char) {
  const base = CHARACTER_MAP.get(char)
  if (!base) return null
  const details = await loadUnitDetails(base.unit)
  return { ...base, ...(details?.[char] ?? {}) }
}

/** 同上，但只看已经下载过的包，适合渲染时的乐观读取。 */
export function getLoadedCharacter(char) {
  const base = CHARACTER_MAP.get(char)
  if (!base) return null
  const details = detailCache.get(base.unit)
  return details?.[char] ? { ...base, ...details[char] } : null
}

/** 整份语料（会把所有详情包全下下来），内容自检和导出报表用。 */
export async function loadAllCharacters() {
  const units = [...new Set(CHARACTERS.map((c) => c.unit))]
  await Promise.all(units.map((unit) => loadUnitDetails(unit)))
  return CHARACTERS.map((c) => ({ ...c, ...(detailCache.get(c.unit)?.[c.char] ?? {}) }))
}
