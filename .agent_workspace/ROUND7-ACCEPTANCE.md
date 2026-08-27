# Round 7 验收标准 · 全面超越终验

## 1. 轮次门禁

| # | 命令 | 要求 |
|---|---|---|
| G1 | `npm test` | 全绿 |
| G2 | `npm run check:round6` | 7/7 不退化 |
| G3 | `npm run check:round7` | 七项硬门槛全绿 |
| G4 | `npm run test:round3` | 全绿 |
| G5 | `npm run build:all` + `npm run sync:android` | zip + Android 同步 |
| G6 | Lighthouse | 双 App Perf/A11y/BP ≥ 90 |

## 2. 七项硬门槛

| ID | 检查 | 阈值 |
|---|---|---|
| H1 | 拍照识字 | 路由 + tesseract pipeline + smoke |
| H2 | 形近干扰 | distractors 非纯随机取样 |
| H3 | 字源动画 | ≥ 200 字 |
| H4 | 年龄档联动 | ≥ 5 模块读 settings.ageBand |
| H5 | 逻辑小游戏 | 配对或迷宫路由 + smoke |
| H6 | 第 4 主题 | aurora 主题可切换 + tokens |
| H7 | 全局报告 | GLOBAL-SUMMARY-REPORT 无 ❌ 模块行 |

## 3. 记录

合并后更新 `.agent_workspace/acceptance-log-round7.md`。
