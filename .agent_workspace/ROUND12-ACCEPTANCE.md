Model slug: claude-fable-5
# Round 12 验收标准 · 洪恩级体验全量落地

> 版本：Round 12 v1.1（2026-08-28，随探针修订同步）
> 依据：`.agent_workspace/ROUND12-BRIEF.md` + `round11-hongen-audit.md` §5 R12 归属备忘
> 配套：`.agent_workspace/acceptance-log-round12.md`（实测回填模板）、`scripts/check-round12.mjs`（H1–H8 机读探针，固定 8 个结果，`--json` 供编排器聚合）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁 G1–G6（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`test:speech`+`test:ocr`+`check:data`+build+`check:bundle`+smoke+投稿校验；数学 `check:content`+build+smoke；feedback 单测） |
| G2 | Round 12 硬门槛 | `npm run check:round12` | 退出码 0（**8/8**，见 §1；基线 `7c2e6e7` + 探针 v1.1 为 **1/8 有意红灯**，见 §4.1） |
| G3 | Round 11 不退化 | `npm run check:round11` | 退出码 0（**8/8**，H8 同口径兜底）；抽查 `check:round10` 8/8、`check:round9` 8/8 |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；axe critical/serious = 0 |
| G5 | 出包 + Android | `npm run build:all` + `npm run sync:android` + `npm run check:android` | zip 产出 + `check:android` **26/26** |
| G6 | Lighthouse mobile 复测 | `node scripts/lighthouse-ci.mjs`（mobile 档）+ desktop 记录（R11 口径） | 双 App mobile **P ≥ 95**、A/BP ≥ 90；分数落 log §2.1；原始 JSON 入 `evidence/r12/`（H6 联动） |

---

## 1. 八项硬门槛（H1–H8，固定 8 个结果）

`npm run check:round12` 逐项断言，任一 FAIL 即退出码 1。**固定输出 8 个结果**，结果数 ≠ 8 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）。模块不可读取、空文件占位、引用不落盘的资产、只在注释里写标记，一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
|---|---|---|---|---|
| H1 | ASR 模型落库 | manifest `files[]` **≥1 项落盘且 sha256 一致**（整包 ≤60MiB）+ R12 落库 Go/No-Go **实体**（>600 + 落库信号 + 结论/指标 + `ROUND12_H1`）+ harness `ROUND12_H1` 带断言 + 识字 smoke `ROUND12_H1_SMOKE` | 探针 §2.1 + 走查 W1 | r12-literacy-asr-ship |
| H2 | OCR 系统化 | `real*.png` 去重 **≥8** + `real-samples.json` 授权 **≥8** + **结构化 tier**（每样张 light+angle+paper 或矩阵文档）+ 真机 harness **带断言** + `ROUND12_H2` | 探针 §2.2 + 走查 W2 | r12-literacy-ocr-device |
| H3 | 绘本铺开 | **数据探针**：scene 页 **≥60**（每页 ≥2 对象元素）+ **渲染接线**（BookPageScene 实体或 BookReadView scene 信号）+ `ROUND12_H3` | 探针 §2.3 + 走查 W3 | r12-literacy-books-rollout |
| H4 | 儿歌全库 | SONGS **13/13** 合规条目 + public 去重音频 **13/13**（≥10KB）+ **范唱试点实体**（落盘资产或文档）+ `ROUND12_H4` | 探针 §2.4 + 走查 W4 | r12-literacy-songs-vocal |
| H5 | 推荐度量 | 效果度量**实体**（文档或 progress store，**池不含家长面板**）+ skill-practice **34 节点开练覆盖** + 数学 smoke `ROUND12_H5_SMOKE` | 探针 §2.5 + 走查 W5 | r12-math-reco-metrics |
| H6 | 真机/LH | `evidence/r12/` **≥2 份有效 mobile LH JSON**（P≥95）+ 真机通道**三选一定案**文档（含 `ROUND12_H6`） | 探针 §2.6 + G6 | r12-perf-device-lh |
| H7 | TTS/发布 | **TTS 试点**（落盘资产或接线实体）**或**（商店提交演练 + **R12 反馈运行**说明） | 探针 §2.7 + 走查 W6 | r12-tts-release-drill |
| H8 | R11 不退化 | `check:round11` 退出码 0 且输出 **8/8**（链式兜底 R10/R9…） | 探针 §2.8 | 全部分支合并前 |

## 2. 探针细则（机读接线契约，逐项与 `check-round12.mjs` v1.1 对齐）

探针分两类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（顶部 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，**剥注释后**匹配，无 node_modules 可跑）。剥注释规则：HTML `<!-- -->`、块 `/* */`、整行 `//` 全剥——**信号必须写成代码**（常量、断言名或行内尾注），单独一行 `// ROUND12_XX` 会被剥掉导致 FAIL。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

> **v1.1 探针修订记录**（相对 v1.0 堵掉的漏洞，全部经基线/负向实测取证）：
> 1. **H1 r11 文档回退 + available 短路 + manifest 写标记**：v1.0 `gonogoOk` 回退 `r11-followread-gonogo.md`（>800 且含 `available`/`files[]`——基线 **gonogo 恒真**，实测 `gonogo=true` 而 `files=false`）；`filesOk || available` 允许只 flip `available:true` 不交字节；`marked` 认 `manifest.json` 原文——note 里写 `ROUND12_H1` 即过。现：`files[]` 须 **落盘文件 sha256 实测一致**且整包 ≤60MiB（`available` 不再是短路 OR）；Go/No-Go 只认 **R12 专属** `.agent_workspace/r12-followread-ship.md`（>600 + 落库信号 + 结论/指标 + 字面 `ROUND12_H1`）；harness 须 `test-asr-eval-set.mjs` 剥注释含 `ROUND12_H1` **且** `assert|process.exit` **且** 跑分信号；smoke 收紧为字面 `ROUND12_H1_SMOKE`（负向实测：v1.0 基线 `gonogo=true` → v1.1 `ship=false`）。
> 2. **H2 tier 词表即过 + harness 长度即过 + 授权不查**：v1.0 `tierOk` 只要 `real-samples.json` 文本含 `light|angle`（$comment 即命中）或矩阵 doc 单信号；harness 为 `test-ocr-device.mjs` **>200 字符**或 doc 词表——空壳即过；授权仍停留在 R11 的 6 条、**tier 结构化字段零校验**。现：`samples[]` 授权 **≥8**；tier 须 **≥8 样张**各含 `tier.light`+`tier.angle`+纸质字段（或矩阵 doc >500 且 **光照+角度+矩阵**三信号同现）；harness 须脚本 **assert/process.exit + adb|WebView|真机**（或 doc >500 含命令/步骤）；`ROUND12_H2` 维持精度脚本字面标记（负向实测：JSON 只加 tier 词到 comment → v1.1 `tier=false`）。
> 3. **H3 只数页数不查渲染（R11 H4 同款复发）**：v1.0 仅 `scenePages >= 60` + 标记——数据堆 60 页、BookPageScene 零改可蹭绿（基线 `rendered=true` 来自 R11 样板但 `scenePages=20` 仍红）。现加 **渲染腿**：`BookPageScene.vue` 剥注释 >300 字符 **或** `BookReadView.vue` 含 scene 消费信号；标记池同 R11（`books.js`/`data/books/*`/smoke）。
> 4. **H4 vocal 文档/词表即过**：v1.0 `vocalOk = doc>400 || songs.js 含 vocal|范唱`——短文或数据常量一行即过，**不要求范唱落盘**。现：范唱 = `public/audio/vocal-pilot/` **≥1 份 ≥10KB 音频** **或** `r12-songs-vocal-pilot.md` >500 + 范唱/人声信号 + 引擎/录音信号 + 字面 `ROUND12_H4`；13/13 音频口径沿用 R11 H5（合规条目 + 锚定扩展名 + 去重 + 拒 `://`/`..`）。
> 5. **H5 跨文件拼接 + 文档「34」即过（R9/R10/R11 H3 第四次）**：v1.0 `metricsOk` 池拼接 `progress+parent+skillPractice`——家长面板写 `adoptionRate` **同时点亮 metrics**；`coverageOk` 允许 `r12-reco-metrics.md` 含「34」而无 `skill-practice.js` 改代码。现：metrics = R12 文档实体（>600 + lift/采纳 + 数值）**或** **`progress.js` 自身**（不含 ParentView）；coverage 只认 **`skill-practice.js`**（`ROUND12_H5` 或 dailyFocus/allSkills + 34 节点信号，或 SKILLS 实数 ≥34）；smoke 维持 `ROUND12_H5_SMOKE`。
> 6. **H6 空 LH JSON 占位 + 定案词表即过**：v1.0 JSON >500B 且 filename/formFactor 含 mobile 即算 1 份——**无 P 分阈值**；定案 doc 词表即过、无 R12 标记。现：mobile LH 须 `JSON.parse` 通过 + `categories.performance.score ≥ 0.95` + mobile 形态；**≥2 份**；定案 doc >800 + 三选一/定案/真机信号 + **`ROUND12_H6` 字面**（负向实测：空 mobile JSON 占位 → v1.1 `mobileLh=0`）。
> 7. **H7 简报 OR 被写成 AND + R11 反馈蹭绿 + 空目录/touch 即过**：v1.0 要求 `ttsPilot && releaseOk && feedbackRun` 三 AND（与简报「TTS **或** 提交演练+反馈」不符）；`feedbackRun` 基线 **R11 FEEDBACK-LOOP >800 恒真**（实测 v1.0 `feedbackRun=true`）；`exists('tts-pilot')` 空目录或 `offlineTts.js>300` 骨架即过。现：`H7 = ttsLeg || (releaseOk && feedbackRun)`；tts = 落盘 ≥10KB 资产 **或** R12 pilot 文档/接线（含 `ROUND12_H7`）；release = `r12-store-submission-drill.md` 实体 + `ROUND12_H7`；feedback 须 **R12 更新**（`ROUND12_H7` 或「R12 反馈运行」字样，基线 false）（负向实测：v1.0 `feedbackRun=true` → v1.1 `false`）。
> 8. **保持项**：固定 8 结果自检、`--json`、H8 子进程口径、H2 PNG 魔数 + ≥4KB + sha1 去重、H4 音频 R11 H5 口径均保留不动。

### 2.1 H1 ASR 模型落库（文件探针 + 接线探针）

- **files[] 落盘**：`apps/literacy-app/public/asr/manifest.json` 严格 JSON 解析；`files[]` 中 ≥1 项含 `path`/`sha256`(64hex)/`bytes`，对应文件在 `public/` 下**存在且 sha256 实测一致**；累计 ≤60MiB。基线 `files=[]`——此腿是 R12 净增量核心。
- **R12 落库 Go/No-Go**：`.agent_workspace/r12-followread-ship.md` >600 字符 + 落库/files/sha256 信号 + 结论/判定/指标/阈值 + 字面 **`ROUND12_H1`**。R11 Go/No-Go **不能代填**。
- **跑分 harness**：`apps/literacy-app/scripts/test-asr-eval-set.mjs` 剥注释后含 **`ROUND12_H1`** + `assert|process.exit` + 跑分/WER/CER/评测信号。
- **smoke**：识字 `scripts/smoke.mjs` 剥注释后含字面 **`ROUND12_H1_SMOKE`**（模型可用或降级链路断言）。
- 模型许可证须写 THIRD_PARTY_NOTICES；禁 CDN；懒加载不进 SW 首屏 precache（§6）。

### 2.2 H2 OCR 系统化（文件探针 + 接线探针）

- **样张**：`fixtures/ocr/` 下 `^real` 命名 `.png`，PNG 魔数 + ≥4096B，**sha1 去重 ≥8**（基线 6）。
- **授权清单**：`real-samples.json` 严格解析，`samples[]` 含 `name`+`license` **≥8**（基线 6）。
- **tier 矩阵**：≥8 样张各含结构化 tier（`tier.light`+`tier.angle`+纸质/paper 字段），**或** `.agent_workspace/r12-ocr-matrix.md` >500 且光照+角度+矩阵三信号同现。
- **真机 harness**：`test-ocr-device.mjs` 剥注释 >200 + `assert|process.exit` + adb/WebView/真机信号，**或** `r12-ocr-device-harness.md` >500 含可执行步骤/命令。
- **脚本标记**：`test-ocr-accuracy.mjs` 剥注释含字面 **`ROUND12_H2`**。
- **不退化**：R11 的 6 张 real 与 `ROUND11_H2` 由 H8 链兜底。

### 2.3 H3 绘本场景批量铺开（数据探针 + 接线探针）

- **数据腿**：`import` `books.js`，统计 `pages[]` 中 scene/sceneElements **≥2 对象元素**的页数 **≥60**（基线 20，R11 样板 3 本）。
- **渲染腿**：`BookPageScene.vue` 剥注释 >300 字符 **或** `BookReadView.vue` 含 scene 消费信号（R11 已绿，R12 扩页不得删）。
- **标记**：`ROUND12_H3` 字面落在 `books.js`、`data/books/*` 或识字 smoke（剥注释后）。
- **体积**：scene DSL 增量不得把识字首屏 gzip 拖过 420KB（G1 `check:bundle` 兜底）。

### 2.4 H4 儿歌 13/13 + 范唱试点（数据探针 + 文件探针）

- **曲目口径**：R11 H5 同款——合规 SONGS 13 条、锚定扩展名、拒 `://`/`..`、public ≥10KB、**去重 13 份**（基线 audio=8）。
- **范唱试点**：`public/audio/vocal-pilot/` ≥1 份 ≥10KB 音频 **或** `r12-songs-vocal-pilot.md` >500 + 范唱/人声 + 引擎/录音 + **`ROUND12_H4`**。
- **标记**：`songs.js`（剥注释）或识字 smoke 含字面 **`ROUND12_H4`**。
- **降级**：无范唱曲目仍走合成旋律 `playMelody()`（§6 不退化）。

### 2.5 H5 推荐效果度量 + 34 节点开练（接线探针）

- **metrics 腿**：`.agent_workspace/r12-reco-metrics.md` >600 + lift/掌握度/采纳率 + 数值/% **或** `stores/progress.js` **自身**含 recoLift/adoptionRate 等（**ParentView 字样不能代填**）。
- **coverage 腿**：`data/skill-practice.js` 含 `ROUND12_H5` 或 dailyFocus/allSkills + 34 节点/全图谱信号（或 SKILLS 实数 ≥34）。
- **smoke**：数学 `scripts/smoke.mjs` 含字面 **`ROUND12_H5_SMOKE`**（开练覆盖 + 度量可见）。
- **写回边界**：度量只读展示；自动写 FSRS/解锁仍禁止（走查 W5）。

### 2.6 H6 mobile LH 复测 + 真机通道定案（文件探针）

- **证据**：`.agent_workspace/evidence/r12/` ≥2 份 `.json`：可解析、>500B、mobile 形态、`categories.performance.score ≥ 0.95`（识字+数学各 1 份建议）。
- **定案文档**：`.agent_workspace/r12-android-device-decision.md` >800 + 三选一/定案/云真机/Android QA + evidence/r12 引用 + 字面 **`ROUND12_H6`**。
- VM 不可测项标 `[SKIP owner: Android QA]`，但**定案文档不可缺**（简报红线）。

### 2.7 H7 TTS 试点 或 发布演练（文件探针）

- **tts 腿**：`public/audio/tts-pilot/` ≥1 份 ≥10KB 资产 **或** `r12-tts-pilot.md` >600（试点+引擎信号+**`ROUND12_H7`**）**或** `offlineTts.js` 接线（>300 + 合成信号+**`ROUND12_H7`**）。
- **发布腿**（与反馈合取）：`r12-store-submission-drill.md` >600 + 提交/演练/商店 + **`ROUND12_H7`** + 日期/SHA/版本。
- **反馈腿**：`FEEDBACK-LOOP.md` >800 + 运行/SLA/工单 + **`ROUND12_H7` 或「R12 反馈运行」**（R11 骨架不算 R12 交付）。
- **H7 = tts 或 (release 且 feedback)**（简报 OR 口径）。

### 2.8 H8 Round 11 不退化（子进程探针）

- 探针以子进程跑 `scripts/check-round11.mjs`：退出码 0 **且**输出含 `8/8`。R11 八结果再链式兜底 R10/R9 及更早；R12 任何分支合并如碰坏其一，此处红灯。

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

标记写法同 R9–R11：探针剥整行 `//` 注释——标记要写成常量/断言名或**行内尾注**。Round 12 增量：

- **H1 ASR 落库**：识字 smoke 增断言：manifest `files[]` 可读、模型懒加载不阻塞首屏、`available:true` 时跟读链路可用或明确降级，旁注 `ROUND12_H1_SMOKE`。
- **H3 绘本铺开**：识字 smoke 随机抽 3 本含 scene 页绘本，断言多元素渲染无 pageerror，标记 `ROUND12_H3` 可落数据常量。
- **H4 儿歌全库**：识字 smoke 遍历 13 首入口可播（或合成降级），旁注 `ROUND12_H4`。
- **H5 推荐度量**：数学 smoke 增断言：34 节点均可开练、度量面板可见 lift/采纳信号，旁注 `ROUND12_H5_SMOKE`。
- **H2**：`test-ocr-device.mjs` 真机项 VM 标 SKIP，但脚本本体须带断言骨架。

## 4. 基线与预验证

### 4.1 基线红灯记录（有意红灯）+ v1.1 负向实测

基线 `cursor/openmoji-integration-9f67` @ `7c2e6e7`（R11 闭合 8/8、R12 未合并），v1.1 探针实测：

```
  ✓ H8 Round 11 门禁 8/8 无退化

  ✗ H1 ASR 未落库：files=false，ship=false，harness=false，smoke=false —— r12-literacy-asr-ship
  ✗ H2 OCR 未系统化：real=6/8，samples=6/8，tier=false（tagged=0），harness=false，ROUND12_H2=false —— r12-literacy-ocr-device
  ✗ H3 绘本未铺开：scenePages=20/60，rendered=true，ROUND12_H3=false —— r12-literacy-books-rollout
  ✗ H4 儿歌未全库：songs=13/13，audio=8/13， vocal=false，ROUND12_H4=false —— r12-literacy-songs-vocal
  ✗ H5 推荐度量未闭环：metrics=false，coverage=false，smoke=false —— r12-math-reco-metrics
  ✗ H6 真机/LH 未闭环：mobileLh=0/2，device=false —— r12-perf-device-lh
  ✗ H7 TTS/发布未闭环：tts=false，release=false，feedbackRun=false —— r12-tts-release-drill

Round 12 全量落地门禁：1/8 项通过，7 项失败。 → 退出码 1
```

1/8 属**有意红灯**。`--json` 实测 `passed=1 failed=7 results=8`。相对 v1.0 基线同输出 1/8，但 v1.0 子信号存在**假绿**（H1 `gonogo=true`、H7 `feedbackRun=true`）——v1.1 已全部打回 false。

**v1.0 → v1.1 负向抽查**（占位/伪造应红灯）：

| 伪造手段 | v1.0 | v1.1 |
|---|---|---|
| 仅依赖 r11 Go/No-Go（含 available 字样） | H1 `gonogo=true` | `ship=false`，H1 仍红 |
| manifest.note 写 `ROUND12_H1` | `marked=true` 可能绿 | 不认 manifest 原文，`marked=false` |
| real-samples.json $comment 写 light/angle | `tier=true` 可能绿 | `tier=false`（须结构化字段） |
| `mkdir tts-pilot` 空目录 | `ttsPilot=true` | `tts=false`（须 ≥10KB 资产） |
| R11 FEEDBACK-LOOP 无 R12 标记 | `feedbackRun=true` | `feedbackRun=false` |
| evidence/r12 空 mobile JSON >500B | 可能计 1 份 | `mobileLh=0`（须 P≥95） |

**绿灯路径预验证**：在验收分支以最小伪造交付物模拟集成——ASR files[] 落盘 + ship md + harness + smoke（H1）、2 张新 real PNG + tier 字段 ×2 + harness 脚本（H2）、books 扩至 60 scene 页 + 标记（H3）、5 份新音频 + vocal-pilot 资产（H4）、reco-metrics md + skill-practice ROUND12_H5 + smoke（H5）、2 份 LH JSON P≥95 + 定案 doc（H6）、tts-pilot 资产或 release+feedback R12 段（H7）——预期 **8/8 → 退出码 0**。伪造物回滚不入库。

### 4.2 Lighthouse / 体积（集成后回填 acceptance-log §2.1 / §2.3）

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| mobile 识字 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90 | log §2.1 | `[P/F]` |
| mobile 数学 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90 | log §2.1 | `[P/F]` |
| desktop 识字 / 数学 P | 记录 + 对比 R11 | log §2.1 | 记录 |
| 识字首屏 JS gzip | < 420 KB | log §2.3 | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | log §2.3 | `[P/F]` |
| ASR 模型包 | ≤ 60 MiB，不进首屏 precache | log §2.3 | `[P/F]` |
| zip 体积 | R11 值 + 模型/音频/scene Δ | log §2.3 | 记录 |

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
|---|---|---|
| W1 | ASR 落库复核 | files[] 哈希与落盘一致；Go/No-Go 有跑分数据；`available:true` 时儿童可跟读且 ≤60MiB；降级不退化 |
| W2 | OCR 矩阵复核 | 8 张确为真实拍摄且 tier 标签可信；真机 harness 可复现；弱光/模糊失败话术仍有效 |
| W3 | 绘本铺开观感 | ≥60 页 scene 多元素无破版；旧单 emoji 页不回归；高频单元覆盖合理；滚动不卡 |
| W4 | 儿歌全库 + 范唱 | 13 首均可进可播可退；范唱与合成旋律切换自然；来源许可逐条记录 |
| W5 | 推荐度量可信 | 34 节点均可开练；lift/采纳率有对照数据；仅用户操作写记录；键盘可达 |
| W6 | 真机/TTS/发布走查 | LH 与定案文档一致；TTS 试点可离线播；提交演练步骤可执行；反馈回路有 R12 运行记录 |

## 6. 不回归红线（继承 Round 3–11，抽查即可）

- `check:round11` 8/8（H8 硬门槛）、`check:round10` 8/8、`check:round9` 8/8；更早轮次 G3 抽查
- 首屏 JS gzip 识字 < 420 KB、数学 < 250 KB；ASR/音频/模型/样张懒加载，不进 SW 预缓存首屏
- axe critical = 0 且 serious = 0（`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）
- 运行时零第三方域名请求；禁止未授权商业模型/曲库
- FSRS、解锁规则、母题阈值不动；周计划/度量只读展示；家长面板、每日冒险、吉祥物不缺席
- Android：`sync:android` 后 `check:android` 26/26
- worktree 开发（`.agent_workspace/r12-*` 或 `/tmp/wt-r12-*`），禁止在共享 `/workspace` 切功能分支

## 7. 回填要求

每条 H1–H8 在 `acceptance-log-round12.md` 对应小节必须有**实测数据或命令输出**。集成回填必须带：集成 SHA、`check:round12` 全文（8/8）、mobile LH 分数、ASR 模型清单（path/sha256/bytes）、OCR tier 矩阵表、scene 页统计、13 首音频+范唱清单、reco 度量对照表、真机定案结论、zip/bundle/模型体积、走查勾选。禁止「应该可以」。未达标项进 log §3。
