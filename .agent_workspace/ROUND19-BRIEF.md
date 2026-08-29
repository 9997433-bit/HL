# Round 19 简报 · 精美度补齐 + 全库富 Play + 剖析「视频级」

> 基线：`cursor/r18-orchestration-9f67` @ `1e8b2ae`（`check:round18` **8/8**）
> 编排分支：`cursor/r19-orchestration-9f67`
> 模型 SOP（永久）：**fable ×3 + opus-fast ×5 + gpt-sol ×2**
> 用户指令：精美度补齐；剩余模板字全补成手写富脚本；剖析做到**视频级**讲解体验

## 现状快照（R18 后实测）

| 项 | 数 |
|---|---|
| 字库 | 1820（99 单元） |
| 富 Play | **1240**（u1–u70） |
| 仍模板回填 | **580**（u71–u99）——用户口中的「880」是 R17 末口径；R18 已消化 300 |
| 精品剖析手写 | 85 / 214 母题 |
| 剖析形态 | 静态面板（图示+分步），**无自动播放/时间轴**，不像「看一节短视频」 |

## 洪恩对标一句话

| 维度 | R18 | R19 目标 |
|---|---|---|
| 覆盖 | 前 70 单元手写 | **1820/1820 富脚本**（消灭模板断崖） |
| 精美度 | 16 模板 + 基础舞台 | **舞台表现升级**（多拍节/层次动效/道具反馈，可降级） |
| 剖析 | 老师文案 + 静态步 | **可播放的讲解时间轴**（播/暂停/进度，像短视频课） |

不复制洪恩 IP；视频级 = **程序化讲解播放器**（GSAP/CSS 时间轴 + TTS），不强制每题 MP4 大文件。

## 硬门槛（`check-round19.mjs`，启动预期 0–1/8）

| 探针 | 阈值 |
|---|---|
| **H1** 差距续表 | `.agent_workspace/round19-hongen-gap-audit.md`：相对洪恩 + 相对 R18，标归属 |
| **H2** 全库富 Play | `countRichPlays()≥1820` 且 narration 去重 ≥1600；可执行 `ROUND19_H2`；分片管线不破（仍按单元懒加载） |
| **H3** 精美度升级 | CharPlayStage（或等价）可执行 `ROUND19_H3`：至少 **3** 类可感知升级（多拍节 timeline / 道具命中反馈增强 / 主题氛围层），且 **reduced-motion 可跳过/降级** |
| **H4** 剖析视频级播放器 | 应用题剖析支持「讲解播放」：自动推进步骤 + 播放/暂停 + 进度；可执行 `ROUND19_H4`；reduced-motion 下降级为手动点步 |
| **H5** 精品剖析 ≥150 | 去重母题手写链 ≥150，去重中文讲解句 ≥400；`ROUND19_H5`（可与 R17/R18 同文件续写） |
| **H6** 走查证据包 | `.agent_workspace/evidence/r19/walkthrough.md` + ≥4 真实落盘图（全库富玩抽查 / 精美舞台 / 剖析播放器 / 周报或学伴） |
| **H7** 真机或模拟台账 | `evidence/r19/android-sim-report.md` 或 `device-blocked.md`（BLOCKED + 复现命令） |
| **H8** 往轮不退化 | `check:round18` **8/8** |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r19-arch-contracts-9f67` | 全库 seed 契约、精美度舞台协议、剖析播放器状态机、与分片生成器兼容 |
| 2 | fable | `cursor/r19-hongen-gap-audit-9f67` | 差距表：精美度/覆盖/视频级剖析 vs 洪恩 |
| 3 | fable | `cursor/r19-acceptance-spec-9f67` | ROUND19-ACCEPTANCE + `check-round19.mjs` + log |
| 4 | opus-fast | `cursor/r19-play-rich-full-9f67` | seed 续 u71–u99 → 富 Play ≥1820，narration 不撞句；重生分片 |
| 5 | opus-fast | `cursor/r19-play-polish-9f67` | CharPlayStage 精美度（H3）：多拍节/反馈/氛围，reduced-motion |
| 6 | opus-fast | `cursor/r19-wp-video-player-9f67` | WpAnalysisPanel「讲解播放」时间轴（H4） |
| 7 | opus-fast | `cursor/r19-wp-explain-150-9f67` | 手写剖析 85→≥150（H5） |
| 8 | opus-fast | `cursor/r19-walkthrough-bundle-9f67` | evidence/r19 走查包 |
| 9 | gpt-sol | `cursor/r19-smoke-tests-9f67` | smoke/单测覆盖播放器与全库 play |
| 10 | gpt-sol | `cursor/r19-regression-gate-9f67` | 往轮门禁 + r19 台账 |

## 规则

- 分支 `cursor/<task>-9f67`；**worktree** 开发；勿污染 `/workspace` 共享检出
- 合入本编排分支；基线 `origin/cursor/r19-orchestration-9f67`
- 不复制洪恩 IP；OpenMoji + 程序化动效
- reduced-motion / 可跳过必须保留
- 证据：`.agent_workspace/evidence/r19/`
- **缺了立马补**（同模型同职责）
- 探针标记必须可执行代码内；禁止假路径截图 / 注释骗标
- H2 与 H3 可能都碰舞台：H2 主攻 seed/生成物，H3 主攻 Stage UI；冲突时 Stage 以 H3 为准、数据以 H2 为准
- H4 与 H5：播放器吃手写 `explain` 步文案；H5 扩写时保持 steps 与 `buildAnalysis` 步数对齐（R18 红线）

## 成功体验

1. 点开任意字（含 u99）：玩关都是手写旁白，不再「模板脸」  
2. 玩关能感到拍节与反馈，不像静态贴图点一点  
3. 应用题点「播放讲解」：像看 20–40 秒短课，可暂停  
4. ≥150 道题讲解读起来像老师  
5. 走查包能证明以上不是只骗探针  
