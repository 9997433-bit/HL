/**
 * 扩展绘本汇总 —— 由 scripts/gen-books.mjs 生成，请勿手改。
 */

import { LEVEL_1_BOOKS } from './l1.js'
import { LEVEL_2_BOOKS } from './l2.js'
import { LEVEL_3_BOOKS } from './l3.js'
import { LEVEL_4_BOOKS } from './l4.js'
import { LEVEL_5_BOOKS } from './l5.js'

export const EXTENDED_BOOKS = [
  ...LEVEL_1_BOOKS,
  ...LEVEL_2_BOOKS,
  ...LEVEL_3_BOOKS,
  ...LEVEL_4_BOOKS,
  ...LEVEL_5_BOOKS
]
