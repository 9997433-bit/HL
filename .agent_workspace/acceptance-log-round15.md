# Round 15 验收回填日志

> 编排启动时基线：功能未合入时 `check:round15` 红  
> 往轮：`check:round13` 以集成线为准（H7 Play 账号可 BLOCKED）  
> 集成目标：H1–H7 绿；H8 往轮不退化（R13 ≥7/8，仅 H7 可红）

## 基线

| 门禁 | 实测 | 证据 |
|---|---|---|
| `npm run check:round15`（编排初测） | **1/8**（仅宽松 H8）→ gate 收紧后见下 | `evidence/r15/baseline-check.txt` |
| `npm run check:round13`（gate 工作树） | **6/8**（缺 APK 时 H6 红） | 同文件；干净环境需 `npm run android:sim` |

| 探针 | 状态 | 证据 / 命令摘录 | Owner 分支 |
|---|---|---|---|
| H1 五步对齐 | ⬜ | | r15-phase-remap |
| H2 Play 全库 | ⬜ | | r15-play-engine / autofill |
| H3 富脚本 ≥200 | ⬜ | | r15-play-catalog-rich |
| H4 认步字源默认播 | ⬜ | | r15-phase-remap |
| H5 自动补齐管道 | ⬜ | | r15-play-autofill |
| H6 写步引导 | ⬜ | | r15-write-guide |
| H7 smoke / a11y | 🟡 smoke 已合入 | cherry-pick `06452f2` | r15-play-smoke-tests |
| H8 往轮 | 🟡 | 以 openmoji-integration 实测为准；缺 APK 先 android:sim | r15-regression-gate |

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-28 | v1.0 编排启动，十路子代理发射 |
| 2026-08-28 | 探针基线实测 **1/8**（仅 H8）；十路 Task 已并发启动 |
| 2026-08-28 | v1.1 合入 audit / smoke / gate；明确 H8 与 APK 环境前置 |

## 十路子代理（已发射）

| # | 模型 | 分支 | Agent |
|---|---|---|---|
| 1 | fable | r15-arch-contracts | bc-188efcbb… ✅ 已合入 |
| 2 | fable | r15-hongen-play-audit | bc-38b7e636… ✅ 已合入 |
| 3 | fable | r15-acceptance-spec | bc-b2d836d8… |
| 4 | opus-fast | r15-play-engine | bc-90f4bdab… |
| 5 | opus-fast | r15-phase-remap | bc-d5a7b171… |
| 6 | opus-fast | r15-play-catalog-rich | bc-8a247b69… |
| 7 | opus-fast | r15-play-autofill | bc-1d0514a6… |
| 8 | opus-fast | r15-write-guide | bc-1b3f921d… |
| 9 | gpt-sol | r15-play-smoke-tests | bc-9b92bbee… ✅ 已合入 |
| 10 | gpt-sol | r15-regression-gate | bc-53e189ed… ✅ 已合入 |

## 后续轮次固定模型配比（SOP）

**每轮 10 子代理：fable ×3 + opus-fast ×5 + gpt-sol ×2**

| 槽位 | 模型 slug | 典型职责 |
|---|---|---|
| 1–3 | `claude-fable-5-thinking-high` | 架构契约、竞品/模块审计、验收与探针 |
| 4–8 | `claude-opus-5-thinking-high-fast` | 功能实现（引擎/UI/内容/管线） |
| 9–10 | `gpt-5.6-sol-high` | 测试 smoke、回归门禁与证据回填 |

规则：缺路立刻按同配比补发；合入顺序见 `ROUND15-INTEGRATION.md`。
