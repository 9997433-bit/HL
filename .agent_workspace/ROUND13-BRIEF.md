# Round 13 简报 · 真机通道与体验终局

> 基线：`cursor/openmoji-integration-9f67` @ R12 闭合（`check:round12` 8/8 · `9f7ae90`）
> 集成分支：`cursor/openmoji-integration-9f67`
> 目标：闭合 R12 审计 §5.1 的 **R13 尾巴**；**VM 内 Android 模拟跑通双 App 全链路**

## 为何还要 Round 13

R12 工程门禁已绿，体验审计预判 **◐7 仍存**（见 `round12-hongen-audit.md` §5.1 R13 尾巴）：

| 深度债 | R12 已交付 | R13 目标 |
|---|---|---|
| L-M9 跟读 | 模型 35.31 MiB 落库；`available:false` | **儿童冻结集实录骨架 + Android RTF 基准**；条件满足时 flip `available:true` |
| L-M10 OCR | 10 张 tier 矩阵 + harness A 段 | **Android 相机/WebView 模拟跑通** + 失败样本回流设计 |
| L-M11 儿歌 | 13/13 合成 + 1 首 Piper 范唱 | **≥3 首真人/高质量范唱批次** |
| L-M5 绘本 | 105 页 scene（17 本） | **≥200 页 scene** 或高频单元全覆 |
| M-M1 推荐 | 34/34 开练 + lift/采纳率字段 | **lift 准实验口径 + 导出报表趋势** |
| L/M-M15/16 | mobile LH + 发布 NO-GO 定案 | **Android 模拟 harness 首条证据**（APK 构建 + WebView 矩阵） |
| X1 TTS | 古诗 Kokoro 试点 | **第二批离线 TTS/真人朗读**（字卡/古诗 ≥1 模块） |
| 发布 | 提交演练文档 | **商店草稿包/内部测试轨道一次真实提交** |

## Android 模拟（R13 横切 · 用户明确要求）

VM **无 adb/真机**，但可执行：

1. `npm run build:all` + `sync:android` + `check:android` 26/26
2. 安装 Android SDK → `./gradlew assembleDebug` 双 APK + SHA256
3. `scripts/android-sim.mjs`：WebView UA + 移动视口 + 触控/离线/权限静态断言 + 双 App smoke 全路由
4. 证据归档：`.agent_workspace/evidence/r13/android-sim/`（**不得冒充真机签核**）

真机项仍标 `[SKIP owner: Android QA]`；模拟证据只解 **NO-GO 前的工程验证**，不解发布阻断。

## 硬门槛（`check-round13.mjs` 基线 1/8，仅 H8 绿）

| 探针 | 阈值 |
|---|---|
| H1 ASR 放行 | 儿童冻结集 ≥50 条实体 **或** `available:true` + Go/No-Go PASS + `ROUND13_H1` |
| H2 OCR Android | android-sim OCR 段 PASS + 失败回流设计 + `ROUND13_H2` |
| H3 绘本终局 | scene 页 ≥200 + `ROUND13_H3` |
| H4 范唱批次 | ≥3 首范唱人声资产 + `ROUND13_H4` |
| H5 lift 实验 | 准实验/对照口径实体 + `ROUND13_H5_SMOKE` |
| H6 Android 模拟 | 双 APK 构建日志 + android-sim 报告 + `evidence/r13/android-sim/` + `ROUND13_H6` |
| H7 商店实提 | 真实提交/内测轨道记录 + `ROUND13_H7` |
| H8 往轮不退化 | `check:round12` 8/8 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r13-arch-contracts-9f67` | R13 真机/终局架构契约 |
| 2 | fable | `cursor/r13-module-audit-9f67` | 洪恩体验终审（R12 后） |
| 3 | fable | `cursor/r13-acceptance-spec-9f67` | ROUND13-ACCEPTANCE + check-round13 v1.1 |
| 4 | opus-fast | `cursor/r13-literacy-asr-release-9f67` | 冻结集骨架 + RTF + available 判定 |
| 5 | opus-fast | `cursor/r13-literacy-ocr-android-9f67` | OCR Android 模拟 + 回流设计 |
| 6 | opus-fast | `cursor/r13-literacy-books-final-9f67` | 绘本 scene ≥200 页 |
| 7 | opus-fast | `cursor/r13-literacy-vocal-batch-9f67` | 范唱批次 ≥3 首 |
| 8 | gpt-sol | `cursor/r13-math-lift-experiment-9f67` | lift 准实验 + 报表趋势 |
| 9 | gpt-sol | `cursor/r13-android-sim-harness-9f67` | **Android SDK 出包 + android-sim 全链路** |
| 10 | gpt-sol | `cursor/r13-store-submit-9f67` | 商店真实提交/内测 |

## 规则

- worktree 开发；cherry-pick 合入；合并前 `check:round12` 8/8 不退化
- Android 模拟证据必须标注 `simulated:true`，与真机 `evidence/r*/android/` 分目录
- 禁止把 VM 模拟结果写成「真机通过」
