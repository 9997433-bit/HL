/**
 * 形状卫星使用的图形词库。
 * sides / corners 为 0 表示该图形没有直边或顶点（如圆形、球体）。
 */
export const SHAPES = [
  { id: 'circle', name: '圆形', dim: '2d', sides: 0, corners: 0, fact: '圆形没有角，所以滚得最顺。' },
  { id: 'oval', name: '椭圆形', dim: '2d', sides: 0, corners: 0, fact: '椭圆像被轻轻压扁的圆。' },
  { id: 'semicircle', name: '半圆', dim: '2d', sides: 1, corners: 2, fact: '半圆是圆形从中间切开的一半。' },
  { id: 'sector', name: '扇形', dim: '2d', sides: 2, corners: 2, fact: '扇形像切下来的一块披萨。' },
  { id: 'triangle', name: '三角形', dim: '2d', sides: 3, corners: 3, fact: '三角形最稳固，桥梁里常常见到。' },
  { id: 'rightTriangle', name: '直角三角形', dim: '2d', sides: 3, corners: 3, fact: '它有一个方方正正的直角。' },
  { id: 'square', name: '正方形', dim: '2d', sides: 4, corners: 4, fact: '正方形四条边一样长。' },
  { id: 'rectangle', name: '长方形', dim: '2d', sides: 4, corners: 4, fact: '长方形对边一样长，像门和书本。' },
  { id: 'rhombus', name: '菱形', dim: '2d', sides: 4, corners: 4, fact: '菱形像立起来的正方形。' },
  { id: 'trapezoid', name: '梯形', dim: '2d', sides: 4, corners: 4, fact: '梯形只有一组对边互相平行。' },
  { id: 'parallelogram', name: '平行四边形', dim: '2d', sides: 4, corners: 4, fact: '平行四边形推一推就会变形。' },
  { id: 'pentagon', name: '五边形', dim: '2d', sides: 5, corners: 5, fact: '五边形有五条边，足球上就有它。' },
  { id: 'hexagon', name: '六边形', dim: '2d', sides: 6, corners: 6, fact: '蜂巢就是用六边形拼出来的。' },
  { id: 'octagon', name: '八边形', dim: '2d', sides: 8, corners: 8, fact: '停车标志就是八边形。' },
  { id: 'star', name: '五角星', dim: '2d', sides: 10, corners: 10, fact: '五角星有五个尖尖的角。' },
  { id: 'cube', name: '正方体', dim: '3d', sides: 12, corners: 8, faces: 6, fact: '正方体有 6 个一样的正方形面。' },
  { id: 'cuboid', name: '长方体', dim: '3d', sides: 12, corners: 8, faces: 6, fact: '长方体像纸巾盒和积木。' },
  { id: 'sphere', name: '球体', dim: '3d', sides: 0, corners: 0, faces: 1, fact: '球体从哪个方向看都是圆的。' },
  { id: 'cylinder', name: '圆柱', dim: '3d', sides: 2, corners: 0, faces: 3, fact: '圆柱上下是两个一样的圆。' },
  { id: 'cone', name: '圆锥', dim: '3d', sides: 1, corners: 1, faces: 2, fact: '圆锥像甜筒，顶上是一个尖。' },
  { id: 'pyramid', name: '金字塔（棱锥）', dim: '3d', sides: 8, corners: 5, faces: 5, fact: '棱锥的侧面都是三角形。' },
]

export const SHAPE_MAP = Object.fromEntries(SHAPES.map((s) => [s.id, s]))

export const SHAPES_2D = SHAPES.filter((s) => s.dim === '2d')
export const SHAPES_3D = SHAPES.filter((s) => s.dim === '3d')

/** 现实生活中的物品 → 对应图形，用于「生活中的形状」题型。 */
export const REAL_OBJECTS = [
  { emoji: '⚽', label: '足球', shape: 'sphere' },
  { emoji: '🥫', label: '罐头', shape: 'cylinder' },
  { emoji: '🍦', label: '甜筒', shape: 'cone' },
  { emoji: '🎲', label: '骰子', shape: 'cube' },
  { emoji: '📚', label: '课本', shape: 'cuboid' },
  { emoji: '🍕', label: '一块披萨', shape: 'sector' },
  { emoji: '🪟', label: '窗户', shape: 'rectangle' },
  { emoji: '🚸', label: '警示牌', shape: 'triangle' },
  { emoji: '🛑', label: '停车标志', shape: 'octagon' },
  { emoji: '🍯', label: '蜂巢格子', shape: 'hexagon' },
  { emoji: '⭐', label: '星星贴纸', shape: 'star' },
  { emoji: '🕐', label: '钟面', shape: 'circle' },
  { emoji: '🥚', label: '鸡蛋轮廓', shape: 'oval' },
  { emoji: '🪁', label: '风筝', shape: 'rhombus' },
]
