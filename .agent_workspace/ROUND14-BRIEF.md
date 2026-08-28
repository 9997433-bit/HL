# Round 14 简报 · 洪恩体验对齐（E1–E5 终局）

> 基线：`cursor/openmoji-integration-9f67` @ R13 集成（`check:round13` **7/8**，仅 H7 BLOCKED 预期红）
> 集成分支：`cursor/openmoji-integration-9f67`（R14 功能分支 cherry-pick 合入）
> 目标：把 R13 审计 **6 个 ◐** 推到 **体验口径 ✅**——「用起来和洪恩一样」

## 为何还要 Round 14

R13 闭合了**工程债务**（探针 7/8），但洪恩终审（`round13-hongen-audit.md` §5.1）已预判：**R13 落地后多数模块仍 ◐**。孩子/家长当场能感知的差距：

| 模块 | R13 已交付 | R14 体验目标（flip ◐→✅） |
|---|---|---|
| **L-M9 跟读** | 骨架 56 条 + 主机 RTF；`available:false` | **`available:true`** + **300 条儿童实录双标注** + **真机 RTF p95≤0.5** |
| **L-M10 OCR** | VM 模拟 + 回流队列；App 33/41 | **预处理修复** App≥40/41 + **真机 B 段** + 队列 `closed` |
| **L-M11 儿歌** | 3 首范唱批次 | **13/13 真人演播**（`humanStudio:true`） |
| **L-M5 绘本** | 209 页 scene | **≥400 页**（Round 14）→ 终局 **1121/1121**（R15 分批） |
| **X1 朗读** | 《静夜思》Kokoro 试点 | **L1 单元字卡真人/高质量离线 TTS 批次** |
| **L/M-M15/16** | android-sim `simulated:true` | **`evidence/r14/android/` 真机签核** + NO-GO→GO |
| **H7 发布** | BLOCKED（无 Play 账号） | **内测轨道真实提交** 或签字接受 7/8 |

横切债：**X3 真机是体验地基**——sim 永不等价签核；R14 所有 E5 项以真机 evidence 为准。

## 三阶段递进（对应 3-Round Loop）

| 阶段 | 体验重点 | 探针预期 |
|---|---|---|
| **Round 14-1** | 真机矩阵 + OCR 预处理 + ASR 录音启动 + 范唱 4–7 首 + scene +200 页 | `check:round14` 2–3/8 |
| **Round 14-2** | ASR 300 条 + device RTF + OCR B 段 + 范唱 8–13 + scene +200 页 | 5–6/8 |
| **Round 14-3** | W1–W6 走查 + H7 实提 + 低档机回归 + 体验 flip 表 | **7/8 或 8/8**（H7 解阻则 8/8） |

## 硬门槛（`check-round14.mjs` 基线 1/8，仅 H8 绿）

| 探针 | 阈值 | 体验 flip |
|---|---|---|
| H1 ASR 体验放行 | `available:true` + **recorded≥300** + Go/No-Go **GO** + 真机 RTF 证据 + `ROUND14_H1` | L-M9 ✅ |
| H2 OCR 体验闭环 | App 召回 **≥40/41** + **真机 B 段** JSON + 队列无逾期 `new/triaged` + `ROUND14_H2` | L-M10 ✅ |
| H3 绘本密度 | scene 页 **≥400** + 渲染不退化 + `ROUND14_H3` | L-M5 收窄（全库 1121 归 R15） |
| H4 范唱全库 | **13/13** 真人范唱 ≥10KB + `r14-songs-vocal-full.md` + `ROUND14_H4` | L-M11 ✅ |
| H5 L1 朗读批次 | L1 单元 TTS/真人批次文档 + 资产落盘 + `ROUND14_H5` | X1 收窄 |
| H6 真机签核 | `evidence/r14/android/` **非 simulated** + GO 定案 + `ROUND14_H6` | L-M15/M-M16 ✅ |
| H7 商店内测 | 真实 Console/TestFlight 回执 + `ROUND14_H7` | 发布流程 ✅ |
| H8 往轮不退化 | `check:round13` **≥7/8** + `check:round12` **8/8** | 链式兜底 |

## 子代理分工（18 = 3 轮 × 6，推荐 SOP）

每轮固定 **6 并发**（2 fable + 2 opus-fast + 2 gpt-sol）：

### Round 14-1（基线探索）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r14-arch-contracts-9f67` | R14 体验终局架构 + E1–E5 契约 |
| 2 | fable | `cursor/r14-module-audit-9f67` | 洪恩体验 flip 表（◐→✅ 判定） |
| 3 | opus-fast | `cursor/r14-literacy-ocr-preprocess-9f67` | OCR 预处理修复 + App/引擎对齐 |
| 4 | opus-fast | `cursor/r14-literacy-asr-recording-9f67` | 冻结集录音启动（批次 1–100） |
| 5 | gpt-sol | `cursor/r14-android-device-matrix-9f67` | 真机矩阵 harness + device evidence |
| 6 | gpt-sol | `cursor/r14-acceptance-spec-9f67` | ROUND14-ACCEPTANCE + check-round14 v1.0 |

### Round 14-2（靶向优化）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 7 | fable | `cursor/r14-round2-audit-9f67` | Round 1 结论 → 差距复审 |
| 8 | opus-fast | `cursor/r14-literacy-asr-finalize-9f67` | 实录 300 条 + device RTF + flip available |
| 9 | opus-fast | `cursor/r14-literacy-books-batch2-9f67` | 绘本 scene +200 页（→400+） |
| 10 | gpt-sol | `cursor/r14-literacy-vocal-7-13-9f67` | 范唱 7–13 首真人演播 |
| 11 | gpt-sol | `cursor/r14-literacy-tts-l1-9f67` | L1 单元朗读批次 |
| 12 | opus-fast | `cursor/r14-literacy-ocr-device-b-9f67` | OCR 真机 B 段 + 队列消化 |

### Round 14-3（SOTA 打磨）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 13 | fable | `cursor/r14-final-audit-9f67` | 体验口径 ◐ 清零终审 |
| 14 | opus-fast | `cursor/r14-literacy-vocal-full-9f67` | 13/13 范唱收尾 + 许可 |
| 15 | gpt-sol | `cursor/r14-store-internal-test-9f67` | Play 内测轨道实提（H7） |
| 16 | gpt-sol | `cursor/r14-android-lowend-9f67` | 低档机 30min 回归 |
| 17 | fable | `cursor/r14-walkthrough-signoff-9f67` | W1–W6 走查签字 |
| 18 | opus-fast | `cursor/r14-integration-close-9f67` | 集成 + acceptance-log 回填 |

## 规则

- worktree 开发；cherry-pick 合入 `cursor/openmoji-integration-9f67`
- **`evidence/r14/android/` 与 `evidence/r13/android-sim/` 分目录**——禁止把 `simulated:true` 写入 r14 真机证据
- 合并前 `check:round13` ≥7/8 + `check:round12` 8/8 不退化
- 每轮结束产出《Round N 结论简报》注入下一轮（见 `PROGRESS.md` §R14 Loop）

## 体验终验清单（比探针更严，W1–W6）

1. 跟读：`available:true`，实时评分（非回放）
2. 绘本：随机 10 页 ≥9 页多元素 scene
3. 儿歌：13 首盲听可接受真人主唱
4. OCR：真机 10 张日常场景 ≥9 张首屏认对
5. 字卡 L1：真人或高质量离线 TTS
6. 真机：2 设备 × 双 App × 离线 30min 无 crash
7. 商店：内测轨道可安装
8. W1–W6 人工勾选 + owner 签字
