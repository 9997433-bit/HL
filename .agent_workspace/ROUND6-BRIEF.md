# Round 6 简报 · 洪恩体量对齐

> 基线：`cursor/openmoji-integration-9f67` @ Round 5 闭合
> 集成分支：`cursor/openmoji-integration-9f67`
> 门禁：`npm test` 全绿 → `npm run check:round6` → `npm run test:round3`

## P0 必交付

### 识字
- **L-M1** 字库 1000→**1800**（脚本化扩充 `char-seed.txt` + `gen-char-corpus.mjs`）
- **L-M5** 绘本 30→**130**（仅用已学字，`verifyBookCoverage` 零越界）
- **L-M8** 古诗 **20 首**（朗读+点字+拼音）
- **L-M9** 跟读评测 v1（Web Speech API 比对 + 录音回放降级）
- **L-M12** **再增 2 款**小游戏（累计 ≥5 款，不含 listen）

### 数学
- **M-M3** 母题 118→**185+**（语义模板 × 场景皮肤）
- **M-M4/M-M11** 比较/速算/生活应用专题入口接线
- **M-M12** 地图叙事升级（Matific 级：章节名+解锁条件+当前关呼吸）

## 硬门槛（`check:round6.mjs`）

| 探针 | 阈值 |
|---|---|
| H1 字库 | ≥ 1800 |
| H2 绘本 | ≥ 130 |
| H3 古诗 | ≥ 20 |
| H4 跟读评测 | pipeline 接线（路由+smoke） |
| H5 小游戏 | ≥ 5（不含 listen） |
| H6 母题 | ≥ 185 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r6-arch-contracts-9f67` | Round 6 架构契约（1800字/130绘本/185母题/古诗/跟读） |
| 2 | fable | `cursor/r6-module-audit-9f67` | 洪恩对标 Round 6 增量审计 |
| 3 | fable | `cursor/r6-acceptance-spec-9f67` | ROUND6-ACCEPTANCE + check-round6 + acceptance-log |
| 4 | opus-fast | `cursor/r6-literacy-1800chars-9f67` | 1000→1800 字 |
| 5 | opus-fast | `cursor/r6-literacy-books-130-9f67` | 绘本 30→130 |
| 6 | opus-fast | `cursor/r6-literacy-poems-speech-9f67` | 古诗 20 首 + 跟读评测 v1 |
| 7 | opus-fast | `cursor/r6-literacy-minigames-9f67` | 再增 2 款识字小游戏 |
| 8 | opus-fast | `cursor/r6-math-problems-185-9f67` | 母题 118→185+ |
| 9 | opus-fast | `cursor/r6-math-map-narrative-9f67` | 星球地图叙事 + 比较/速算专题 |
| 10 | gpt-sol | `cursor/r6-regression-gate-9f67` | check:round6 + test:round3 + zip 重打 |

## 规则

- 内容脚本化生成 + `check:data` / `check:content` 扩展
- 字库/绘本扩量不得拖垮首屏（保持懒加载 + `check:bundle` 预算）
- 分支 `cursor/<name>-9f67`；首行 Model slug
