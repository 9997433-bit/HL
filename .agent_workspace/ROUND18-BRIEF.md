# Round 18 简报 · 密度收口 + 拆包性能 + 剖析对齐

> 基线：`cursor/openmoji-integration-9f67` @ `08f13a0`（`check:round15|16|17` 均为 **8/8**）
> 编排分支：`cursor/r18-orchestration-9f67`
> 模型 SOP（永久）：**fable ×3 + opus-fast ×5 + gpt-sol ×2**
> 目标：把「门槛绿」再推一档——富 Play 过半库、富脚本按单元拆包、应用题 `steps` 与剖析步对齐、精品讲解扩覆盖

## 洪恩对标一句话（给产品）

| 维度 | 结论 |
|---|---|
| **骨架/闭环** | 已接近：玩→认→练→写→说全通；认步动画 100%；学演示 27；剖析壳+50 手写链；学伴接线；离线/无订阅反超 |
| **精美度** | **还没齐**：洪恩是精选付费「一字一动画」；我们 940/1820 富脚本 + 880 模板回填，手感在中后段仍有断崖 |
| **数学讲题** | 壳及格、精品半成：50 母题手写；仍有 **56** 题 `template.steps`≠剖析步数，104 题剖析仅 1 步 |

**R18 不宣称「全面反超洪恩」**；宣称「高频路径密度再抬一档 + 性能可背」。

## 为何 Round 18

| R17 已绿 | 仍弱（体验/工程） | R18 翻的牌 |
|---|---|---|
| 富 Play 940 | 仍有 ~880 字模板；CharDetail 同步吃进 ~256KB rich | **富 Play ≥1200** + **按单元懒加载拆包** |
| 剖析 50 手写 | 56 题步数不一致；大量 1 步公式翻译 | **步数对齐 ≥90%** + **手写链 ≥80** |
| 学演示 27 | 图谱适合三段契约的技能基本齐 | **回归保护**；可选再 +2～3 若审计发现缺口 |
| 走查/模拟台账 | 需本轮新证据目录 | **evidence/r18/** |

## 硬门槛（`check-round18.mjs`，启动预期 0–1/8）

| 探针 | 阈值 |
|---|---|
| **H1** 差距续表 | `.agent_workspace/round18-hongen-gap-audit.md`：相对洪恩 + 相对 R17，标本轮归属 |
| **H2** 富 Play ≥1200 | `countRichPlays()≥1200` 且 narration 去重 ≥960；可执行 `ROUND18_H2` |
| **H3** 富脚本拆包 | `char-play-rich` 不再整包同步进首屏/单字关键路径；按单元（或等价）懒加载；可执行 `ROUND18_H3`；`check:bundle` 不退化超预算 |
| **H4** 剖析步数对齐 | 对 `WORD_PROBLEMS` 全量：`template.steps` 与 `buildAnalysis(make()).steps.length` 一致率 ≥**90%**；可执行 `ROUND18_H4` |
| **H5** 精品剖析 ≥80 | 去重母题手写链 ≥80，去重中文讲解句 ≥200；`ROUND18_H5`（可与 ROUND17_H4 同文件续写） |
| **H6** 走查证据包 | `.agent_workspace/evidence/r18/walkthrough.md` + ≥4 张真实落盘截图（富玩 / 拆包后单字 / 剖析对齐 / 周报或学伴） |
| **H7** 真机或模拟台账 | `evidence/r18/android-sim-report.md` 或 `device-blocked.md`（含 BLOCKED + 复现命令）；不继承仅 r13/r17 旧报告冒充 |
| **H8** 往轮不退化 | `check:round17` **8/8**（v1.1） |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r18-arch-contracts-9f67` | 拆包契约、seed→分片索引、步数对齐协议、探针标记落点 |
| 2 | fable | `cursor/r18-hongen-gap-audit-9f67` | 续写差距表（诚实：仍未全面反超） |
| 3 | fable | `cursor/r18-acceptance-spec-9f67` | ROUND18-ACCEPTANCE + `check-round18.mjs` v1.0 + log |
| 4 | opus-fast | `cursor/r18-play-rich-1200-9f67` | seed 续写 → ≥1200（约 u56–u75），narration 全库不撞句 |
| 5 | opus-fast | `cursor/r18-play-codesplit-9f67` | rich 按单元懒加载 + 索引；`ROUND18_H3` |
| 6 | opus-fast | `cursor/r18-wp-steps-align-9f67` | 修 `analyzeEquation`/母题 `steps` 使一致率 ≥90% |
| 7 | opus-fast | `cursor/r18-wp-explain-80-9f67` | 手写剖析 50→≥80 |
| 8 | opus-fast | `cursor/r18-walkthrough-bundle-9f67` | evidence/r18 走查包 |
| 9 | gpt-sol | `cursor/r18-smoke-tests-9f67` | smoke/单测覆盖拆包与步数对齐 |
| 10 | gpt-sol | `cursor/r18-regression-gate-9f67` | 往轮门禁 + android:sim/BLOCKED 台账 |

## 规则

- 分支 `cursor/<task>-9f67`；**worktree** 开发；合入本编排分支
- 基线从 `cursor/r18-orchestration-9f67`（或 openmoji tip）拉出
- 不复制洪恩 IP；reduced-motion / 可跳过保留
- 证据：`.agent_workspace/evidence/r18/`
- **缺了立马补**（同模型同职责）
- 探针标记必须可执行代码内（剥注释仍在），禁止注释骗标 / 假路径截图

## 成功体验

1. 前 ~1200 字玩关旁白不撞句、能讲字义  
2. 打开单字详情：首包不再吞整份 rich；切单元才加载对应片  
3. 应用题「几步题」与剖析列表步数一致，孩子不会看到「标 3 步只讲 1 句」  
4. ≥80 道精品剖析读起来像老师讲  
5. 走查包能证明以上不是只骗探针  
