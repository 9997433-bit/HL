/**
 * 字源小图的形状 DSL。
 *
 * 字源演变的第一帧是「古人看见的东西」——太阳、山峰、一只手。这些小图
 * 如果直接写成 SVG 的 path d 字符串，六十多个字就是六十多行谁也读不懂的
 * 坐标；改一笔要在脑子里重新画一遍。所以语料里只写形状，路径由这里生成：
 *
 *   ['O', 50, 50, 30]   一个圆
 *   ['P', 10, 82, 50, 24, 90, 82]   一条折线
 *
 * 画布统一是 100 × 100，左上角是原点，和 SVG 的习惯一致。
 * 这一层是纯函数，不碰 DOM，`npm run check:data` 可以在 Node 里直接校验
 * 每个字的小图画不画得出来。
 *
 * 支持的形状：
 *   L x1 y1 x2 y2                 线段
 *   P x1 y1 x2 y2 …               折线（至少三个点）
 *   Q x1 y1 cx cy x2 y2           二次曲线
 *   C x1 y1 c1x c1y c2x c2y x2 y2 三次曲线
 *   O cx cy r                     圆（描边）
 *   D cx cy r                     实心点
 *   R x y w h                     矩形（描边）
 *   A cx cy r a0 a1               圆弧，角度按度数，0° 指向右，顺时针为正
 */

/** 形状 -> 参数个数；-1 表示「个数可变，另有规则」。 */
const ARITY = { L: 4, P: -1, Q: 6, C: 8, O: 3, D: 3, R: 4, A: 5 }

/** 实心形状：动画时用缩放淡入，而不是「一笔画出来」。 */
const FILLED = new Set(['D'])

export const SKETCH_SIZE = 100

const n = (v) => Math.round(v * 100) / 100

/**
 * 校验一个形状，返回错误说明；没问题时返回 null。
 * 坐标允许略微出界（-10 ~ 110），给圆弧和线帽留一点余量。
 */
export function validateShape(shape) {
  if (!Array.isArray(shape) || shape.length < 2) return '形状必须是 [op, ...数字] 数组'
  const [op, ...args] = shape
  const arity = ARITY[op]
  if (arity === undefined) return `未知形状「${op}」`
  if (args.some((v) => typeof v !== 'number' || !Number.isFinite(v))) {
    return `形状「${op}」的参数必须都是有限数字`
  }
  if (arity === -1) {
    if (op === 'P' && (args.length < 6 || args.length % 2 !== 0)) {
      return '折线 P 至少要三个点，且坐标成对出现'
    }
  } else if (args.length !== arity) {
    return `形状「${op}」需要 ${arity} 个参数，实际给了 ${args.length} 个`
  }
  // 角度不受画布限制，半径也不是坐标，逐一挑出真正的坐标来看
  const coords = op === 'A' ? args.slice(0, 3) : op === 'O' || op === 'D' ? args : args
  if (coords.some((v) => v < -10 || v > 110)) return `形状「${op}」的坐标超出了 100×100 的画布`
  return null
}

const polar = (cx, cy, r, deg) => {
  const rad = (deg * Math.PI) / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

/** 一个形状 -> { d, fill }。d 是 SVG 路径，fill 表示这个形状要填实。 */
export function shapeToPath(shape) {
  const [op, ...a] = shape
  const fill = FILLED.has(op)
  switch (op) {
    case 'L':
      return { d: `M${n(a[0])} ${n(a[1])}L${n(a[2])} ${n(a[3])}`, fill }
    case 'P': {
      const pts = []
      for (let i = 0; i < a.length; i += 2) pts.push(`${n(a[i])} ${n(a[i + 1])}`)
      return { d: `M${pts[0]}L${pts.slice(1).join('L')}`, fill }
    }
    case 'Q':
      return {
        d: `M${n(a[0])} ${n(a[1])}Q${n(a[2])} ${n(a[3])} ${n(a[4])} ${n(a[5])}`,
        fill
      }
    case 'C':
      return {
        d:
          `M${n(a[0])} ${n(a[1])}C${n(a[2])} ${n(a[3])} ` +
          `${n(a[4])} ${n(a[5])} ${n(a[6])} ${n(a[7])}`,
        fill
      }
    case 'O':
    case 'D': {
      const [cx, cy, r] = a
      // 两段半圆首尾相接，比 <circle> 更好统一成 path 做描边动画
      return {
        d:
          `M${n(cx - r)} ${n(cy)}A${n(r)} ${n(r)} 0 1 1 ${n(cx + r)} ${n(cy)}` +
          `A${n(r)} ${n(r)} 0 1 1 ${n(cx - r)} ${n(cy)}Z`,
        fill
      }
    }
    case 'R': {
      const [x, y, w, h] = a
      return { d: `M${n(x)} ${n(y)}H${n(x + w)}V${n(y + h)}H${n(x)}Z`, fill }
    }
    case 'A': {
      const [cx, cy, r, a0, a1] = a
      const [sx, sy] = polar(cx, cy, r, a0)
      const [ex, ey] = polar(cx, cy, r, a1)
      const sweep = a1 >= a0 ? 1 : 0
      const large = Math.abs(a1 - a0) > 180 ? 1 : 0
      return {
        d: `M${n(sx)} ${n(sy)}A${n(r)} ${n(r)} 0 ${large} ${sweep} ${n(ex)} ${n(ey)}`,
        fill
      }
    }
    default:
      return { d: '', fill: false }
  }
}

/** 一整张小图 -> 路径数组，顺序就是「先画哪一笔」。 */
export function sketchPaths(shapes = []) {
  return shapes.map((shape, i) => ({ key: `s${i}`, ...shapeToPath(shape) }))
}

/**
 * 笔顺数据的中线（medians）是折线，长度可以直接算出来，
 * 不必等 DOM 里的 <path> 挂上去再问 getTotalLength()。
 * 「写字」动画就靠这个长度做 stroke-dashoffset。
 */
export function medianPath(median = []) {
  if (median.length === 0) return { d: '', length: 0 }
  const pts = median.map(([x, y]) => `${n(x)} ${n(y)}`)
  let length = 0
  for (let i = 1; i < median.length; i += 1) {
    const [x0, y0] = median[i - 1]
    const [x1, y1] = median[i]
    length += Math.hypot(x1 - x0, y1 - y0)
  }
  // 只有一个点的笔画（某些短点）画不出线，给它一段极短的位移撑住动画
  const d = median.length === 1 ? `M${pts[0]}l0.01 0` : `M${pts[0]}L${pts.slice(1).join('L')}`
  return { d, length: Math.max(length, 1) }
}
