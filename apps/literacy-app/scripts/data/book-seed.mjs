/**
 * 扩展绘本的正文种子总表。
 *
 * 按分级拆成六个文件，每个文件只写「书名 / 副标题 / 封面 / 简介 / 一页一句」，
 * 分级号在这里统一贴上，拼音、重点字、配色由 scripts/gen-books.mjs 生成。
 */

import { SEED_L1 } from './book-seed-l1.mjs'
import { SEED_L2 } from './book-seed-l2.mjs'
import { SEED_L3 } from './book-seed-l3.mjs'
import { SEED_L4 } from './book-seed-l4.mjs'
import { SEED_L5 } from './book-seed-l5.mjs'
import { SEED_L6 } from './book-seed-l6.mjs'

const withLevel = (level, list) => list.map((b) => ({ ...b, level }))

export const BOOK_SEED = [
  ...withLevel(1, SEED_L1),
  ...withLevel(2, SEED_L2),
  ...withLevel(3, SEED_L3),
  ...withLevel(4, SEED_L4),
  ...withLevel(5, SEED_L5),
  ...withLevel(6, SEED_L6)
]
