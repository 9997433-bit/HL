Model slug: claude-fable-5
# Round 13 验收标准 · 真机通道与体验终局

> 版本：Round 13 v1.1（2026-08-28，随探针修订同步）
> 依据：`.agent_workspace/ROUND13-BRIEF.md` + `round12-hongen-audit.md` §5.1 R13 尾巴
> 配套：`.agent_workspace/acceptance-log-round13.md`（实测回填模板）、`scripts/check-round13.mjs`（H1–H8 机读探针，固定 8 个结果，`--json` 供编排器聚合）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。Android 模拟证据必须标注 `simulated:true`，**不得冒充真机签核**。

## 0. 轮次门禁 G1–G6（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`test:speech`+`test:ocr`+`check:data`+build+`check:bundle`+smoke+投稿校验；数学 `check:content`+build+smoke；feedback 单测） |
| G2 | Round 13 硬门槛 | `npm run check:round13` | 退出码 0（**8/8**，见 §1；基线 `9f7ae90` + 探针 v1.1 为 **1/8 有意红灯**，见 §4.1） |
| G3 | Round 12 不退化 | `npm run check:round12` | 退出码 0（**8/8**，H8 同口径兜底）；抽查 `check:round11` 8/8 |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；axe critical/serious = 0 |
| G5 | 出包 + Android | `npm run build:all` + `npm run sync:android` + `npm run check:android` | zip 产出 + `check:android` **26/26** |
| G6 | Android 模拟全链路 | `node scripts/android-sim.mjs`（H6 联动） | 双 App `assembleDebug` + WebView UA smoke 全路由 + OCR A 段；证据入 `.agent_workspace/evidence/r13/android-sim/`（`simulated:true`） |

---

## 1. 八项硬门槛（H1–H8，固定 8 个结果）

`npm run check:round13` 逐项断言，任一 FAIL 即退出码 1。**固定输出 8 个结果**，结果数 ≠ 8 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）。模块不可读取、空文件占位、引用不落盘的资产、只在注释里写标记、BLOCKED 演练文档冒充真实提交，一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
|---|---|---|---|---|
| H1 | ASR 放行 | manifest `files[]` **落盘 sha256 一致**（R12 口径）+ **双轨之一**：`available:true` 且 R13 放行 Go/No-Go 实体 **或** 儿童冻结集 **≥50 条实体**（JSON `recorded` 或骨架 ≥50）+ harness `ROUND13_H1` 带断言 + smoke `ROUND13_H1_SMOKE` | 探针 §2.1 + 走查 W1 | r13-literacy-asr-release |
| H2 | OCR Android | android-sim **OCR 段** PASS + `ocr-device-a.log` + 失败样本**回流设计**实体 + harness `ROUND13_H2` 带 Android 断言 | 探针 §2.2 + 走查 W2 | r13-literacy-ocr-android |
| H3 | 绘本终局 | scene 页 **≥200**（每页 ≥2 对象元素）+ **渲染接线**不退化 + `ROUND13_H3` | 探针 §2.3 + 走查 W3 | r13-literacy-books-final |
| H4 | 范唱批次 | R12 **13/13 音频不退化** + **≥3 首**范唱人声资产（≥10KB 去重）+ 批次元数据文档 + `ROUND13_H4` | 探针 §2.4 + 走查 W4 | r13-literacy-vocal-batch |
| H5 | lift 实验 | 准实验/对照**实体**（文档 >600 + 因果/lift 数值 + **`ROUND13_H5` 字面**）+ 数学 smoke `ROUND13_H5_SMOKE` | 探针 §2.5 + 走查 W5 | r13-math-lift-experiment |
| H6 | Android 模拟 | 双 APK **落盘 sha256 与 report 一致** + 证据日志齐全 + android-sim 报告 `simulated:true` + **签核文档** + harness `ROUND13_H6` | 探针 §2.6 + G6 | r13-android-sim-harness |
| H7 | 商店实提 | **真实**提交/内测回执（非 BLOCKED 演练）+ 日期/SHA/版本 + **`ROUND13_H7` 字面** | 探针 §2.7 + 走查 W6 | r13-store-submit |
| H8 | R12 不退化 | `check:round12` 退出码 0 且输出 **8/8** | 探针 §2.8 | 全部分支合并前 |

## 2. 探针细则（机读接线契约，逐项与 `check-round13.mjs` v1.1 对齐）

探针分两类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（顶部 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，**剥注释后**匹配，无 node_modules 可跑）。剥注释规则：HTML `<!-- -->`、块 `/* */`、整行 `//` 全剥——**信号必须写成代码**（常量、断言名或行内尾注），单独一行 `// ROUND13_XX` 会被剥掉导致 FAIL。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

> **v1.1 探针修订记录**（相对 v1.0 堵掉的漏洞，全部经基线/负向实测取证）：
> 1. **H1 available||freeze 短路 + files 只数 length + 文档词表即过**：v1.0 `(available || freezeOk) && filesOk` 允许只 flip `available:true`；`freezeOk` 只查 md 词表（≥50 字样）不认 JSON 实体数；`filesOk` 仅 `files.length≥1`；`marked` 认 harness OR smoke。现：`files[]` 须 **R12 同款 sha256 落盘校验**；放行腿 = `available:true` + `.agent_workspace/r13-followread-release.md`（>600 + Go/No-Go/PASS + RTF/Android + **`ROUND13_H1`**）；冻结腿 = `asr-eval-set.json` **`recorded≥50` 或骨架 clips≥50** + `r13-asr-freeze-set.md`（>800 + **`ROUND13_H1`** + RTF/实录信号）；harness 须 `ROUND13_H1` + `assert|process.exit` + 跑分/RTF 信号；smoke 收紧为字面 **`ROUND13_H1_SMOKE`**（负向实测：基线 `available=false`、`skeleton=36/50` → freeze=false）。
> 2. **H2 手搓 report.json + 回流短文即过**：v1.0 只查 `report.ocr.pass` 与 md >400 词表；harness 只查 `ROUND13_H2` 无 assert/Android。现：report 须 `simulated:true` + `steps` 含 **`ocr-device-a` pass** + **`ocr-device-a.log` >200B**；回流 = `r13-ocr-regression-loop.md` >600 + 回流/失败样本/**`ROUND13_H2`** + 采集/闭环信号；harness 须 **assert + Android/WebView/adb** 信号。
> 3. **H3 只数页数不查渲染（R12 H3 同款第三次）**：v1.0 仅 `scenePages≥200` + 标记。现加 **渲染腿**：`BookPageScene.vue` >300 字符 **或** `BookReadView.vue` scene 消费信号；标记池扩至 `data/books/*`（基线 `9f7ae90`：`scenePages=105/200`，`ROUND13_H3=false`）。
> 4. **H4 vocal 路径蹭绿 + 不查 R12 全库**：v1.0 `vocal` 路径含字样且 ≥8KB 即计，**不要求批次文档**；不查 13/13 音频腿。现：须 **13/13 合规音频不退化**（R12 H4 口径）+ **≥3 去重范唱 ≥10KB** + **`r13-songs-vocal-batch.md`**（>500 + 人声/批次 + **`ROUND13_H4`**）；标记在 `songs.js` 或 smoke。
> 5. **H5 progress.js 跨文件蹭绿**：v1.0 `expOk` 池拼接 `progress.js`——store 写 `adoptionRate` 即点亮 exp。现：exp **只认** `r13-reco-lift-experiment.md` 自身（>600 + 对照/准实验/lift + 数值/% + **`ROUND13_H5` 字面**）；smoke 维持 **`ROUND13_H5_SMOKE`**。
> 6. **H6 手搓 report + 无签核文档（基线 v1.0 假绿风险）**：v1.0 只查 report JSON 字段与 harness 注释块 **`ROUND13_H6`**；不要求 APK 落盘校验/证据日志/签核 md。现：report 须 **五步链全 pass**（build/sync/check/gradle×2）+ smoke **0 问题** + 路由阈值 + **APK 相对路径落盘 sha256 实测一致** + 四份日志 >200B（literacy smoke >500B）；**`r13-android-sim-record.md`** >800 + simulated Disclaimer + evidence 引用 + **`ROUND13_H6`**；harness 须 **`ROUND13_H6` 在剥注释代码中** + `spawnSync|process.exit` + `simulated:true` 写入报告。
> 7. **H7 BLOCKED 演练文档即过**：v1.0 词表 + `ROUND13_H7 OR 日期/SHA/版本`——**dry-run BLOCKED 记录可蹭绿**。现：须 **结论非 BLOCKED/NO-GO** +（§6 回执区填实日期 **或** `状态：SUBMITTED|VERIFIED`）；`[待填]` 模板不算交付（负向实测：r13-store-submit 分支 BLOCKED 记录 → v1.1 `submit=false`）。
> 8. **保持项**：固定 8 结果自检、`--json`、H8 子进程 `check:round12` 8/8、H3 scene 计数口径（≥2 对象元素）均保留。

### 2.1 H1 ASR 放行（文件探针 + 接线探针）

- **files[] 落盘**：`manifest.json` 严格 JSON；`files[]` ≥1 项 path/sha256/bytes **实测一致**；整包 ≤60MiB（R12 已绿，此腿为不退化约束）。
- **放行腿**（二选一）：`available:true` + `.agent_workspace/r13-followread-release.md`（>600 + Go/No-Go/PASS + RTF/Android 基准 + **`ROUND13_H1`**）。
- **冻结腿**（二选一）：`scripts/data/asr-eval-set.json` 中 `status=recorded` 且含音频路径 **≥50**，**或** 骨架 clips（id+spoken）**≥50** + `.agent_workspace/r13-asr-freeze-set.md`（>800 + 冻结集 + RTF/实录 + **`ROUND13_H1`**）。基线 36 条 placeholder **不算** recorded。
- **harness**：`test-asr-eval-set.mjs` 剥注释含 **`ROUND13_H1`** + `assert|process.exit` + 跑分/RTF/WER 信号。
- **smoke**：识字 smoke 字面 **`ROUND13_H1_SMOKE`**。
- 真机 RTF 基准写入 evidence；VM 可标 `[SKIP owner: Android QA]`，但文档不可缺。

### 2.2 H2 OCR Android 模拟 + 失败回流（文件探针 + 接线探针）

- **模拟证据**：`.agent_workspace/evidence/r13/android-sim/report.json` 中 `simulated:true`、`ocr.pass:true`、`steps` 含 **`ocr-device-a` pass**；同目录 **`ocr-device-a.log` >200B**。
- **回流设计**：`.agent_workspace/r13-ocr-regression-loop.md` >600 + 失败样本/tier 回流/采集闭环 + **`ROUND13_H2`**。
- **harness**：`test-ocr-device.mjs` 剥注释含 **`ROUND13_H2`** + `assert|process.exit` + Android/WebView/adb 信号。
- **不退化**：R12 的 8 张 real + tier 由 H8 链兜底。

### 2.3 H3 绘本终局 ≥200 scene 页（数据探针 + 接线探针）

- **数据腿**：`import` `books.js`，统计 scene/sceneElements **≥2 对象元素**页数 **≥200**（基线 R12 闭合 **105 页**）。
- **渲染腿**：`BookPageScene.vue` >300 字符 **或** `BookReadView.vue` scene 信号（R12 已绿，不得删）。
- **标记**：`ROUND13_H3` 字面落在 `books.js`、`data/books/*` 或识字 smoke；建议导出 **`ROUND13_H3` 台账常量**（books/pages 计数）供 `check:data` 联动。
- **体积**：scene DSL 增量不得把识字首屏 gzip 拖过 420KB（G1 `check:bundle` 兜底）。

### 2.4 H4 范唱批次 ≥3 + R12 13/13 不退化（数据探针 + 文件探针）

- **旋律腿**：R12 H4 同款——合规 SONGS 13 条、public **去重音频 13/13 ≥10KB**。
- **范唱批次**：`songs.js`/`public/audio/vocal-batch/` 等 **≥3 去重范唱 ≥10KB** + `.agent_workspace/r13-songs-vocal-batch.md`（>500 + 人声/真人/批次 + **`ROUND13_H4`**）。
- **标记**：`songs.js` 或识字 smoke 含字面 **`ROUND13_H4`**。
- **降级**：无范唱曲目仍走合成旋律（§6 不退化）。

### 2.5 H5 lift 准实验 + 报表趋势（接线探针）

- **实验实体**：`.agent_workspace/r13-reco-lift-experiment.md` >600 + 对照/准实验/A/B/lift/因果 + 数值/%/趋势/报表 + **`ROUND13_H5` 字面**（**不含** `progress.js` 跨文件拼接）。
- **smoke**：数学 smoke 字面 **`ROUND13_H5_SMOKE`**（34 节点开练 + lift/采纳可见）。
- **写回边界**：度量只读展示；自动写 FSRS/解锁仍禁止。

### 2.6 H6 Android 模拟 harness 首条证据（文件探针 + 接线探针）

- **报告**：`evidence/r13/android-sim/report.json`：`simulated:true`；literacy/math **`smokePass:true`、`smokeProblems:0`**；路由 literacy **≥100**、math **≥15**；双 APK sha256 与 **`apps/*/android/.../app-debug.apk` 落盘实测一致**。
- **日志**：同目录 `smoke-literacy.log`（>500B）、`smoke-math.log`、`gradle-literacy.log`、`gradle-math.log`（各 >200B）。
- **签核文档**：`.agent_workspace/r13-android-sim-record.md` >800 + **不等价真机**声明 + evidence 路径 + **`ROUND13_H6`**。
- **harness**：`scripts/android-sim.mjs` 剥注释含 **`ROUND13_H6`** + `spawnSync|process.exit` + 写入 `simulated:true`。
- **边界**：模拟只解工程验证；发布阻断仍看 H7 真提交 + 真机项 `[SKIP owner: Android QA]`。

### 2.7 H7 商店真实提交/内测（文件探针）

- **记录实体**：`.agent_workspace/r13-store-submission-record.md` >600 + Play/TestFlight/内测轨道 + 日期/SHA/版本 + **`ROUND13_H7`**。
- **真实提交**：结论 **不得** 为 `BLOCKED/NO-GO`；§6 回执须填 **实日期**（非 `[待填]`）**或** 正文含 `状态：SUBMITTED|VERIFIED`。
- **禁止**：debug APK / android-sim 报告 / 探针绿灯 **冒充** Console 接收成功。

### 2.8 H8 Round 12 不退化（子进程探针）

- 子进程跑 `scripts/check-round12.mjs`：退出码 0 **且**输出含 `8/8`。

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

标记写法同 R9–R12：探针剥整行 `//` 注释——标记要写成常量/断言名或**行内尾注**。Round 13 增量：

- **H1 ASR 放行**：识字 smoke 增 `ROUND13_H1_SMOKE`——冻结集/RTF 可见或 `available:true` 时跟读链路断言，否则明确降级。
- **H3 绘本终局**：识字 smoke 抽检多本 scene 页无 pageerror；`ROUND13_H3` 台账常量与 `check:data` 联动。
- **H4 范唱批次**：识字 smoke 遍历 ≥3 首范唱入口可播/可停，旁注 `ROUND13_H4`。
- **H5 lift 实验**：数学 smoke 增 `ROUND13_H5_SMOKE`——lift/采纳率只读面板可见。
- **H2/H6**：OCR/device 与 android-sim 真机项 VM 标 SKIP，脚本本体须带断言骨架。

## 4. 基线与预验证

### 4.1 基线红灯记录（有意红灯）+ v1.1 负向实测

基线 `cursor/openmoji-integration-9f67` @ `9f7ae90`（R12 闭合 8/8、R13 未合并），v1.1 探针实测：

```
  ✓ H8 Round 12 门禁 8/8 无退化

  ✗ H1 ASR 未放行：files=true，release=false，freeze=false（recorded=0，skeleton=36），harness=false，smoke=false —— r13-literacy-asr-release
  ✗ H2 OCR Android 未闭环：sim=false，reflux=false，harness=false —— r13-literacy-ocr-android
  ✗ H3 绘本未终局：scenePages=105/200，rendered=true，ROUND13_H3=false —— r13-literacy-books-final
  ✗ H4 范唱未批次：songs=13/13，audio=13/13，vocal=1/3，batch=false，ROUND13_H4=false —— r13-literacy-vocal-batch
  ✗ H5 lift 未闭环：exp=false，smoke=false —— r13-math-lift-experiment
  ✗ H6 Android 模拟未闭环：sim=false，record=false，harness=false —— r13-android-sim-harness
  ✗ H7 商店实提未闭环：submit=false —— r13-store-submit

Round 13 终局门禁：1/8 项通过，7 项失败。 → 退出码 1
```

1/8 属**有意红灯**。`--json` 实测 `passed=1 failed=7 results=8`。

**v1.0 → v1.1 负向抽查**（占位/伪造应红灯）：

| 伪造手段 | v1.0 | v1.1 |
|---|---|---|
| 只 flip `available:true` 无冻结集/放行 md | H1 可能绿 | `release=false`，H1 红 |
| `r13-asr-freeze-set.md` 写「≥50」无 JSON 实体 | `freeze=true` | `freeze=false`（须 clips≥50） |
| 手搓 `report.json` 无日志/APK | H6 可能绿 | `sim=false` |
| BLOCKED 商店演练 + `ROUND13_H7` | H7 可能绿 | `submit=false` |
| `progress.js` 写 adoptionRate | H5 `exp=true` | `exp=false`（只认实验 md） |

**绿灯路径预验证**：各责任分支按 §2 最小交付物合入后预期 **8/8 → 退出码 0**。并行分支未合并时局部子信号（如 H6 `sim=true`）可绿，**整轮仍必须 8/8 才可出包**。

### 4.2 Android 模拟与体积（集成后回填 acceptance-log §2.1 / §2.3）

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| literacy smoke 路由 / 问题 | android-sim ≥100 / 0 | log §2.1 | `[P/F]` |
| math smoke 路由 / 问题 | android-sim ≥15 / 0 | log §2.1 | `[P/F]` |
| 双 APK SHA256 | report 与落盘一致 | log §2.1 | `[P/F]` |
| 识字首屏 JS gzip | < 420 KB | log §2.3 | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | log §2.3 | `[P/F]` |
| scene 页增量 | R12 105 → R13 ≥200 | log §2.3 | `[P/F]` |

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
|---|---|---|
| W1 | ASR 放行复核 | 冻结集/RTF 文档可复核；`available:true` 时儿童可跟读；降级不退化 |
| W2 | OCR Android + 回流 | android-sim OCR 段可复现；失败样本回流路径清晰；弱光话术仍有效 |
| W3 | 绘本终局观感 | ≥200 页 scene 无破版；旧单 emoji 页不回归；高频单元覆盖合理 |
| W4 | 范唱批次 | ≥3 首范唱可播；13/13 旋律不退化；许可逐条记录 |
| W5 | lift 实验可信 | 对照口径清楚；34 节点可开练；仅用户操作写记录 |
| W6 | 模拟/商店走查 | android-sim 证据标注 simulated；H7 为真实 Console 回执非 BLOCKED；真机项 owner 分账 |

## 6. 不回归红线（继承 Round 3–12，抽查即可）

- `check:round12` 8/8（H8 硬门槛）、`check:round11` 8/8；更早轮次 G3 抽查
- 首屏 JS gzip 识字 < 420 KB、数学 < 250 KB；模型/音频/样张懒加载，不进 SW 首屏 precache
- axe critical = 0 且 serious = 0（`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）
- 运行时零第三方域名请求；禁止未授权商业模型/曲库
- FSRS、解锁规则、母题阈值不动；度量只读展示
- Android：`sync:android` 后 `check:android` 26/26
- **模拟证据目录** `evidence/r13/android-sim/` 与真机 `evidence/r*/android/` **分目录**；禁止把 VM 模拟写成「真机通过」
- worktree 开发（`.agent_workspace/r13-*` 或 `/tmp/wt-r13-*`），禁止在共享 `/workspace` 切功能分支

## 7. 回填要求

每条 H1–H8 在 `acceptance-log-round13.md` 对应小节必须有**实测数据或命令输出**。集成回填必须带：集成 SHA、`check:round13` 全文（8/8）、android-sim 报告摘要（路由/APK SHA/simulated）、ASR 冻结集/RTF 表、OCR 回流设计、scene 页统计、范唱批次清单、lift 对照表、商店回执、走查勾选。禁止「应该可以」。未达标项进 log §3。
