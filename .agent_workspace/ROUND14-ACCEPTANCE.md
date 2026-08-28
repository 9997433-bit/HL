# Round 14 验收标准 · 洪恩体验对齐（E1–E5）

> 版本：Round 14 v1.1（2026-08-28，随探针负向加固同步）
> 依据：`.agent_workspace/ROUND14-BRIEF.md` + `round13-hongen-audit.md` §5.1 R14 尾巴
> 配套：`.agent_workspace/acceptance-log-round14.md`、`scripts/check-round14.mjs`（H1–H8，固定 8 结果）
> 判定原则：**体验 flip** 须孩子/家长可感知；真机 evidence 与 `simulated:true` 分目录，**禁止冒充**。

## 0. 轮次门禁 G1–G7

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测 | `npm test` | 全绿 |
| G2 | Round 14 硬门槛 | `npm run check:round14` | **8/8**（基线 R13 集成后预期 **1/8**，仅 H8 绿） |
| G3 | Round 13 不退化 | `npm run check:round13` | **≥7/8**（H7 BLOCKED 可接受） |
| G4 | Round 12 不退化 | `npm run check:round12` | **8/8** |
| G5 | 出包 + Android | `build:all` + `sync:android` + `check:android` | 26/26 |
| G6 | 真机签核（H6） | 真机矩阵脚本 + `evidence/r14/android/` | `device-signoff.json` onDevice=true |
| G7 | 体验走查 | W1–W6 人工勾选 | 6/6 + owner 签字 |

## 1. 八项硬门槛（H1–H8）

| ID | 交付物 | PASS 标准 | 体验 flip |
|---|---|---|---|
| H1 | ASR 体验 | `available:true` + recorded≥300 + GO 文档 + **带 device 身份**的真机 RTF p95≤0.5 + `ROUND14_H1` + smoke | L-M9 ✅ |
| H2 | OCR 体验 | App **逐例非空矩阵**≥40/41 + 真机 B 段 JSON + 队列无逾期 + `ROUND14_H2` | L-M10 ✅ |
| H3 | 绘本密度 | scene≥400 + 渲染 + `ROUND14_H3` | L-M5 大幅收窄 |
| H4 | 范唱全库 | 13/13 humanStudio 范唱 + `r14-songs-vocal-full.md` + `ROUND14_H4` | L-M11 ✅ |
| H5 | L1 朗读 | `r14-tts-l1-batch.md` + ≥20 资产 + `ROUND14_H5_SMOKE` | X1 收窄 |
| H6 | 真机签核 | `evidence/r14/android/device-signoff.json` + GO 定案 + `ROUND14_H6`；**不得引用 r13 android-sim** | L-M15/M-M16 ✅ |
| H7 | 商店内测 | 真实 Console 回执 + `ROUND14_H7` | 发布 ✅ |
| H8 | 往轮不退化 | round12 8/8 + round13 ≥7/8 | 链式兜底 |

### 1.1 v1.1 探针接线契约

`scripts/check-round14.mjs` 固定输出 H1–H8 八项；结果数异常时门禁自身 FAIL。`--json` 必须保留 `passed`、`failed`、`results[]`。v1.1 在 v1.0 基础上加三条不可由汇总数字或旧轮证据替代的实体约束：

1. **H1 device RTF 实体**：只认 `.agent_workspace/evidence/r14/asr/device-rtf.json`，文件 ≥100B；须同时满足 `onDevice:true`、`simulated:false`、`rtfP95` 为有限数且 `0≤p95≤0.5`，并有非空 `device` 身份（字符串，或对象的 `model`/`name`/`deviceModel`/`product`）。只有布尔值和 p95、没有 device 身份的占位 JSON 一律 FAIL。
2. **H2 OCR 逐例矩阵**：只认 `.agent_workspace/evidence/r14/ocr/app-webview-matrix.json`，不回退读取 R13 `android-sim`。矩阵须有 `ocrSection`（兼容键名 `ocr-section`），其本体为数组，或含 `cases`/`rows`/`results` 数组；有效对象行 ≥41，逐行 `pass:true` 或 `status/result:"pass"` ≥40，且 section/顶层声明的 `passCount`、`total` 与逐行实数完全一致。空 section 配 `40/41` 汇总不得蹭绿。
3. **H6 真机/模拟隔离**：`device-signoff.json` 须显式 `simulated:false`；signoff、GO 定案、签核记录任一处引用 `.agent_workspace/evidence/r13/android-sim/`（或等价相对路径）即 FAIL。R13 VM 证据只能由 H8 继承验证，不得充当 R14 真机签核腿。

## 2. 体验 flip 判定表（终审用）

| 模块 | R13 后 | R14 目标 | 终验方法 |
|---|---|---|---|
| L-M9 | ◐ 录音回放 | ✅ 实时 ASR 评分 | 儿童跟读 3 首诗盲测 |
| L-M10 | ◐ VM sim | ✅ 真机拍照认字 | 10 张日常场景 |
| L-M11 | ◐ 3/13 范唱 | ✅ 13/13 真人 | 盲听家长问卷 |
| L-M5 | ◐ 209/1121 | ◐→✅ 高频全覆 | 随机翻 10 页 |
| X1 | ◐ 1 poem | ◐ L1 真人/TTS | L1 单元点读 |
| E5 | ◐ NO-GO | ✅ GO | 2 设备 30min |

## 3. 手动走查 W1–W6

- W1 ASR 体验：跟读实时反馈，非回放
- W2 OCR 体验：真机拍照 + 回流路径可演示
- W3 绘本观感：≥400 scene 页 + 旧页不回归
- W4 范唱全库：13 首真人主唱
- W5 L1 朗读：字卡听感可接受
- W6 真机/商店：真机 evidence + Console 回执（非 BLOCKED）

## 4. 基线与 v1.1 负向实测（R13 集成 @ 7/8）

| 探针 | v1.1 基线实测 | 原因 |
|---|---|---|
| H1 | FAIL | available=false，recorded=0 |
| H2 | FAIL | 无 r14 device B，逐例矩阵 0/0（R13 旧值 33/41 不再回退） |
| H3 | FAIL | scene=209<400 |
| H4 | FAIL | humanVocal=0–3/13 |
| H5 | FAIL | 无 L1 批次 |
| H6 | FAIL | 无 r14 真机 signoff |
| H7 | FAIL | BLOCKED 延续 |
| H8 | PASS | 刷新 android-sim 落盘 APK 后：round12 8/8 + round13 7/8 |

**v1.0 → v1.1 正/负向抽查**（正向先补齐该 H 的其余所有腿，只改变表中攻击面）：

| 伪造/对照手段 | v1.0 审阅 | v1.1 实测 |
|---|---|---|
| H1 正向：合规 `device-rtf.json`（device 身份 + `simulated:false`） | H1 绿 | **H1 PASS** |
| H1 负向：同一 JSON 删除 `device` 身份 | H1 可绿 | **H1 FAIL**，`deviceRtf=false` |
| H2 正向：41 条逐例结果（40 pass）且汇总相符 | H2 绿 | **H2 PASS**，App 40/41 |
| H2 负向：`ocrSection:[]` 但顶层手填 `passCount:40,total:41` | H2 可绿 | **H2 FAIL**，`app=0/0`、`ocrSection=false` |
| H6 正向：纯 R14 真机路径 + 显式 `simulated:false` | H6 绿 | **H6 PASS** |
| H6 负向：签核记录追加 `evidence/r13/android-sim/report.json` | H6 可绿 | **H6 FAIL**，`noR13SimPath=false` |

逐字命令输出与退出码见 `.agent_workspace/r14-acceptance-probe-baseline.md`。v1.1 基线实测 **1/8（仅 H8）**，`--json` 为 `passed=1`、`failed=7`、`results.length=8`；三组攻击探针均保持固定八项，相对正向对照只打红目标 H。
