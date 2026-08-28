# Round 17 简报 · 覆盖加深 + 精品讲解 + 真机证据

> 基线：`cursor/r16-orchestration-9f67`（`check:round16` **v1.1 · 8/8**）
> 编排分支：`cursor/r17-orchestration-9f67`
> 模型 SOP（永久）：**fable ×3 + opus-fast ×5 + gpt-sol ×2**
> 目标：把 R16「门槛绿」推进到「高频路径更像精品课」——富脚本再扩、学演示补缺、应用题精品剖析、真机证据补台账

## 为何 Round 17

| R16 已绿 | 仍弱（体验） | R17 翻的牌 |
|---|---|---|
| 富 Play 640 / 1820 | 后半仍靠模板 | **富 Play ≥900**（优先高频/前 55 单元） |
| 学演示 21 | 图谱仍有缺口技能 | **再 +≥6** 适合格的技能演示 |
| 剖析壳通用推导 | 缺「题题能讲清」的精品 | **≥20 母题手写剖析链** |
| 探针环境可绿 | 真机 ASR/OCR/APK 台账薄 | **android:sim + 走查证据包** |
| 学伴/周报已有 | 接线未遍及单字页/QuizShell | **关键路径全接线** |

商店上架/外网 ASR 密钥仍可不作硬绿；本轮 **H8 要求 `check:round16` 8/8**。

## 硬门槛（`check-round17.mjs`，启动预期 0–1/8）

| 探针 | 阈值 |
|---|---|
| **H1** 差距续表 | `.agent_workspace/round17-hongen-gap-audit.md`：在 R16 表上标出本轮归属与仍 ❌/◐ |
| **H2** 富 Play ≥900 | `countRichPlays()≥900` 且 narration 去重 ≥720；`ROUND17_H2` |
| **H3** 学演示 ≥27 | 可执行 `ROUND16_H4`/`ROUND17_H3` 标记文件内 skillId 去重 ≥27；三态+可跳过仍成立 |
| **H4** 精品剖析 ≥20 | ≥20 母题有手写 `explain`/`ROUND17_H4` 分步链（非仅公式兜底） |
| **H5** 学伴关键路径接线 | CharDetail 或等价单字路径 + QuizShell/`recentWrong` 至少一侧接到阶段台词；`ROUND17_H5` |
| **H6** 走查证据包 | `.agent_workspace/evidence/r17/walkthrough.md` + ≥4 张截图/录屏路径引用（H2 认步 / 学演示 / 剖析 / 周报） |
| **H7** 真机或模拟闭环 | `android:sim` 报告或明确 BLOCKED 台账（含复现命令）；双 APK 或诚实 BLOCKED |
| **H8** 往轮不退化 | `check:round16` **8/8**（v1.1） |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r17-arch-contracts-9f67` | 富脚本增量契约、精品剖析数据协议、接线点清单 |
| 2 | fable | `cursor/r17-hongen-gap-audit-9f67` | 续写差距表（相对洪恩 + 相对 R16） |
| 3 | fable | `cursor/r17-acceptance-spec-9f67` | ROUND17-ACCEPTANCE + check-round17 + log |
| 4 | opus-fast | `cursor/r17-play-rich-900-9f67` | 富 Play → ≥900（优先高频） |
| 5 | opus-fast | `cursor/r17-math-learn-demo-plus-9f67` | 学演示再 +≥6 |
| 6 | opus-fast | `cursor/r17-wp-explain-hand-9f67` | ≥20 母题手写剖析 |
| 7 | opus-fast | `cursor/r17-mascot-wire-9f67` | 单字页/QuizShell 学伴接线 |
| 8 | opus-fast | `cursor/r17-walkthrough-bundle-9f67` | 走查证据包（可与编排并行补） |
| 9 | gpt-sol | `cursor/r17-smoke-tests-9f67` | smoke/单测覆盖新门槛 |
| 10 | gpt-sol | `cursor/r17-regression-gate-9f67` | 往轮 + android:sim/BLOCKED 台账 |

## 规则

- 分支 `cursor/<task>-9f67`；worktree；合入本编排分支
- 不复制洪恩 IP；reduced-motion / 可跳过保留
- 证据：`.agent_workspace/evidence/r17/`
- **缺了立马补**（同模型同职责）

## 成功体验

1. 前 ~900 字玩关旁白不撞句、能讲字义  
2. 图谱里多数「数量/算理」技能都有演示按钮  
3. 至少 20 道应用题剖析读起来像老师讲，不像公式翻译  
4. 家长周报 + 孩子关键刷题路径都能听到学伴阶段话  
5. 走查包能证明上述四条不是只骗探针  
