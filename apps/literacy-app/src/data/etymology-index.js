/**
 * 字源语料的「轻」索引。
 *
 * 单字页要判断「这个字有没有字源可看」，才决定要不要显示那个入口按钮。
 * 为这一句判断把整份 etymology.js 拉进单字页的分块不值当——真正的语料
 * 连同 GSAP 演变动画一起，等孩子点了按钮再 import()。
 *
 * 这里只留一串汉字。顺序和 etymology.js 一致，`npm run check:data` 会核对
 * 两边不会走散。
 */

/** 有字源动画的字，按 etymology.js 里的顺序排。 */
export const ETYMOLOGY_CHARS =
  '一二三上下中大小天本日月山水火木田土人口手目耳心牛羊鸟鱼虫门车足石云雨女子' +
  '明林森休从众好男看家问间河江湖池海洋花草桃松妈星眼唱蚊猫'

const CHAR_SET = new Set(ETYMOLOGY_CHARS)

export const TOTAL_ETYMOLOGY = ETYMOLOGY_CHARS.length

/** 这个字有没有字源动画可看。 */
export function hasEtymology(char) {
  return CHAR_SET.has(char)
}
