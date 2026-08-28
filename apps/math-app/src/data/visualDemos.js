/**
 * 数形演示注册表的旧入口。
 *
 * Round 16 起真正的数据在 data/learn-demos.js（每条多挂一个技能点，
 * 见那里的说明）。这里只留一层别名，让 Round 5 起就存在的
 * `VISUAL_DEMOS` 调用方——含 scripts/check-round5.mjs——继续读得到同一份表。
 * 新代码请直接用 learn-demos.js。
 */
import { LEARN_DEMOS, LEARN_DEMO_MAP, learnDemoById } from '@/data/learn-demos.js'

export const VISUAL_DEMOS = LEARN_DEMOS
export const VISUAL_DEMO_MAP = LEARN_DEMO_MAP
export const visualDemoById = learnDemoById

export default VISUAL_DEMOS
