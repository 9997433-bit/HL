# Round 6 验收标准 · 洪恩体量对齐

## 1. 轮次门禁

| # | 命令 | 要求 |
|---|---|---|
| G1 | `npm test` | 全绿 |
| G2 | `npm run check:round5` | 不退化 |
| G3 | `npm run check:round6` | 六项硬门槛全绿 |
| G4 | `npm run test:round3` | 全绿 |
| G5 | `npm run build:all` | zip 产出并记录体积 |

## 2. 六项硬门槛

| ID | 检查 | 阈值 |
|---|---|---|
| H1 | 字库 | ≥ 1800 |
| H2 | 绘本 | ≥ 130，零越界 |
| H3 | 古诗 | ≥ 20 |
| H4 | 跟读评测 | 路由 + smoke 断言 |
| H5 | 小游戏 | ≥ 5（不含 listen） |
| H6 | 母题 | ≥ 185 |

## 3. 记录

合并后更新 `.agent_workspace/acceptance-log-round6.md`。
