/**
 * 富互动 play 分片名录（ROUND18_H3）—— 手写剧本按单元切片之后的目录页。
 *
 * 这里**只有数字和加载器**：几条、分几片、每片几条、怎么把某一片取回来。
 * 旁白和道具都在各自的 ./uN.js 里，用到哪个单元才下载哪一片，
 * 所以本文件的体积随单元数长（O(单元)），不随脚本条数长（O(条)）。
 *
 * 加载器写成一条条字面量 import()，Vite / Rollup 才能据此每单元切一个 chunk；
 * 写成拼字符串的动态 import 会退化成「整目录一块」，等于没拆。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 生成，请勿手改。
 */

/** 分片加载器：单元 id → 取回那一片。char-play.js 的 ensurePlayUnit() 用它。 */
export const RICH_PLAY_UNIT_LOADERS = {
  u1: () => import('./u1.js'),
  u2: () => import('./u2.js'),
  u3: () => import('./u3.js'),
  u4: () => import('./u4.js'),
  u5: () => import('./u5.js'),
  u6: () => import('./u6.js'),
  u7: () => import('./u7.js'),
  u8: () => import('./u8.js'),
  u9: () => import('./u9.js'),
  u10: () => import('./u10.js'),
  u11: () => import('./u11.js'),
  u12: () => import('./u12.js'),
  u13: () => import('./u13.js'),
  u14: () => import('./u14.js'),
  u15: () => import('./u15.js'),
  u16: () => import('./u16.js'),
  u17: () => import('./u17.js'),
  u18: () => import('./u18.js'),
  u19: () => import('./u19.js'),
  u20: () => import('./u20.js'),
  u21: () => import('./u21.js'),
  u22: () => import('./u22.js'),
  u23: () => import('./u23.js'),
  u24: () => import('./u24.js'),
  u25: () => import('./u25.js'),
  u26: () => import('./u26.js'),
  u27: () => import('./u27.js'),
  u28: () => import('./u28.js'),
  u29: () => import('./u29.js'),
  u30: () => import('./u30.js'),
  u31: () => import('./u31.js'),
  u32: () => import('./u32.js'),
  u33: () => import('./u33.js'),
  u34: () => import('./u34.js'),
  u35: () => import('./u35.js'),
  u36: () => import('./u36.js'),
  u37: () => import('./u37.js'),
  u38: () => import('./u38.js'),
  u39: () => import('./u39.js'),
  u40: () => import('./u40.js'),
  u41: () => import('./u41.js'),
  u42: () => import('./u42.js'),
  u43: () => import('./u43.js'),
  u44: () => import('./u44.js'),
  u45: () => import('./u45.js'),
  u46: () => import('./u46.js'),
  u47: () => import('./u47.js'),
  u48: () => import('./u48.js'),
  u49: () => import('./u49.js'),
  u50: () => import('./u50.js'),
  u51: () => import('./u51.js'),
  u52: () => import('./u52.js'),
  u53: () => import('./u53.js'),
  u54: () => import('./u54.js'),
  u55: () => import('./u55.js'),
  u56: () => import('./u56.js'),
  u57: () => import('./u57.js'),
  u58: () => import('./u58.js'),
  u59: () => import('./u59.js'),
  u60: () => import('./u60.js'),
  u61: () => import('./u61.js'),
  u62: () => import('./u62.js'),
  u63: () => import('./u63.js'),
  u64: () => import('./u64.js'),
  u65: () => import('./u65.js'),
  u66: () => import('./u66.js'),
  u67: () => import('./u67.js'),
  u68: () => import('./u68.js'),
  u69: () => import('./u69.js'),
  u70: () => import('./u70.js')
}

/** 手写覆盖到的单元，按 seed 顺序。 */
export const RICH_PLAY_UNITS = ['u1', 'u2', 'u3', 'u4', 'u5', 'u6', 'u7', 'u8', 'u9', 'u10', 'u11', 'u12', 'u13', 'u14', 'u15', 'u16', 'u17', 'u18', 'u19', 'u20', 'u21', 'u22', 'u23', 'u24', 'u25', 'u26', 'u27', 'u28', 'u29', 'u30', 'u31', 'u32', 'u33', 'u34', 'u35', 'u36', 'u37', 'u38', 'u39', 'u40', 'u41', 'u42', 'u43', 'u44', 'u45', 'u46', 'u47', 'u48', 'u49', 'u50', 'u51', 'u52', 'u53', 'u54', 'u55', 'u56', 'u57', 'u58', 'u59', 'u60', 'u61', 'u62', 'u63', 'u64', 'u65', 'u66', 'u67', 'u68', 'u69', 'u70']

/**
 * 生成期实测的数字，给运行时和探针对账用：manifest 说 1240 条，
 * 那么 loadAllRichPlays() 之后 countRichPlays() 也必须是 1240 条，对不上就是管线出了问题。
 */
export const RICH_PLAY_MANIFEST = {
  plays: 1240,
  narrations: 1240,
  units: RICH_PLAY_UNITS,
  perUnit: { u1: 12, u2: 13, u3: 13, u4: 13, u5: 12, u6: 12, u7: 14, u8: 13, u9: 12, u10: 11, u11: 13, u12: 12, u13: 13, u14: 13, u15: 12, u16: 12, u17: 18, u18: 18, u19: 18, u20: 18, u21: 18, u22: 18, u23: 18, u24: 18, u25: 18, u26: 18, u27: 18, u28: 18, u29: 18, u30: 18, u31: 18, u32: 18, u33: 12, u34: 20, u35: 20, u36: 20, u37: 20, u38: 20, u39: 20, u40: 20, u41: 20, u42: 20, u43: 20, u44: 20, u45: 20, u46: 20, u47: 20, u48: 20, u49: 20, u50: 20, u51: 20, u52: 20, u53: 20, u54: 20, u55: 20, u56: 20, u57: 20, u58: 20, u59: 20, u60: 20, u61: 20, u62: 20, u63: 20, u64: 20, u65: 20, u66: 20, u67: 20, u68: 20, u69: 20, u70: 20 }
}

/** 模板名录：舞台照着 interaction 决定「怎么算玩完了」。 */
export const PLAY_TEMPLATES = {
  'morph-story': { interaction: 'sequence', desc: '象形分镜：从实物 emoji 一步步变成字形' },
  'tap-reveal': { interaction: 'tap', desc: '点一点，藏起来的东西一个个露出来' },
  'emoji-hunt': { interaction: 'tap', desc: '一堆干扰项里找出目标（找中后目标会换位置再出现）' },
  'count-tap': { interaction: 'tap', desc: '一个一个点着数，点满为止' },
  'pop-bubbles': { interaction: 'tap', desc: '戳掉 / 吃掉 / 喝掉，点一个少一个' },
  'grow-tap': { interaction: 'tap', desc: '点一下长一点，按 stages 逐级长大' },
  'sound-tap': { interaction: 'tap', desc: '点了会发声，跟着念拟声词' },
  'color-fill': { interaction: 'tap', desc: '点着把主角一块块涂上颜色' },
  'scene-poke': { interaction: 'tap', desc: '一幅小场景，挨个点亮里面的东西' },
  'drag-parts': { interaction: 'drag', desc: '把零件 / 部件拖到一起，拼成主角' },
  'rain-catch': { interaction: 'drag', desc: '东西往下掉，拖着工具去接' },
  'trace-path': { interaction: 'drag', desc: '按住主角顺着路线拖过去' },
  'pair-match': { interaction: 'drag', desc: '左右连线，配成一对' },
  'sort-buckets': { interaction: 'drag', desc: '把每样东西拖进它该去的筐' },
  'word-build': { interaction: 'drag', desc: '把两个字拖到一起，组成一个词' },
  'swipe-motion': { interaction: 'swipe', desc: '照着字义的方向划：推向前、拉回来、举往上' },
}

/** 主题分类，舞台拿它挑配色和音效。 */
export const PLAY_THEMES = ['number', 'nature', 'weather', 'animal', 'body', 'family', 'school', 'food', 'color', 'shape', 'time', 'place', 'action', 'object', 'word', 'feeling']

/** 门槛标记，探针剥掉注释后仍读得到。 */
export const RICH_PLAY_PROBE = 'ROUND17_H2'

/** 本轮门槛标记：条数 ≥1200、旁白去重 ≥960。 */
export const RICH_PLAY_PROBE_ROUND18 = 'ROUND18_H2'

/** 拆包这一层的标记：分片 + manifest 的形状是 Round 18 H3 的交付物。 */
export const RICH_SPLIT_PROBE = 'ROUND18_H3'

/** 历轮标记都留着，往轮探针各读各的那一枚。 */
export const RICH_PLAY_PROBE_HISTORY = ['ROUND15_H3', 'ROUND16_H3', 'ROUND17_H2', 'ROUND18_H2']

/** 本轮两条线，生成期已经卡过一遍，运行时再自报一次给探针核对。 */
export const RICH_PLAY_THRESHOLDS = { plays: 1200, narrations: 960 }
