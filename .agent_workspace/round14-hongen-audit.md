Model slug: claude-fable-5-thinking-xhigh
# Round 14 · 洪恩体验 flip 审计（6◐ 基线实测 + R14 逐项 flip 判定标准）

标记：`ROUND14_AUDIT`

> 审计人：Round 14-1 子代理 #2（fable）
> 审计基线：集成线 `cursor/openmoji-integration-9f67` @ **`0d70870`**（R13 集成闭合 + R14 编排已启动、R14 功能分支全部在途未合入）
> 审计日期：2026-08-28 · Node v22.14.0 / npm 10.9.7 · 分支 `cursor/r14-module-audit-9f67`（干净检出，门禁实跑）
> 方法：继承 R10–R13 审计的「洪恩真实体验深度」五维杆（E1 看到 / E2 听到 / E3 摸到 / E4 家长 / E5 真机）。对 R13 审计（`round13-hongen-audit.md` §4）认定的 **6 个 ◐**（L-M5 / L-M9 / L-M10 / L-M11 / L-M15 / M-M16）逐项：**R13 实测数字（本 VM 一手）→ R14 flip 到 ✅ 的判定标准（照抄 `check-round14.mjs` v1.0 探针子信号 + W 走查体验终审）→ R14-1 可交付子集 → R15 尾巴**。
> **结论先行**：基线实测 `check:round13` **6/8（exit 1）**、`check:round14` **0/8（exit 1）**——两个数字都低于 ROUND14-BRIEF 宣告的「7/8 / 1/8」，差异不是代码退化，是 **H6 证据依赖 APK 构建产物**（不入库 + 本 VM 无 Android SDK 无法重建，§0.3 一手取证），连锁把 round14 H8 也拉红。**R14 集成终验若不先重建 APK，8/8 物理不可达**——这是本审计最重要的流程发现（§3-P1）。六个 ◐ 的一手基线：ASR `recorded=0/300`·`available:false`、OCR App 证据文件缺失（探针记 0/41，BRIEF 的 33/41 仓库内无出处，§3-P2）、范唱 `humanStudio 0/13`（vocal ref 3 首全 Piper）、绘本 scene **209/1121**（33/132 本）、真机 `evidence/r14/android/` 不存在 + 定案仍 NO-GO。体验口径基线 **✅25 / ◐6 / ❌0**；R14 全部按杆落地的目标 **✅30 / ◐1 / ❌0**（L-M5 按 BRIEF 明文留 ◐ 到 R15 全库）；真机/Play 账号双阻断的最坏情形 **✅28 / ◐3 / ❌0**（§2）。

---

## 0. 基线门禁实测（`0d70870`，本 VM 实跑，退出码为准）

### 0.1 `npm run check:round13`（exit **1**，**6/8**，verbatim）

```
> hongen-edu-apps@1.0.0 check:round13
> node scripts/check-round13.mjs

  ✓ H1 ASR 放行：files[] 落盘 37022120B + 放行/冻结集腿 + harness + ROUND13_H1_SMOKE
  ✓ H2 OCR Android 模拟 + 失败回流设计 + harness ROUND13_H2
  ✓ H3 绘本终局 209 页 scene（≥200）+ 渲染接线 + ROUND13_H3
  ✓ H4 范唱批次 3 首（≥3）+ 13/13 音频 + ROUND13_H4
  ✓ H5 lift 准实验口径 + ROUND13_H5_SMOKE
  ✓ H8 Round 12 门禁 8/8 无退化

  ✗ H6 Android 模拟未闭环：sim=false，record=true，harness=true —— r13-android-sim-harness
  ✗ H7 商店实提未闭环：submit=false —— r13-store-submit

Round 13 终局门禁：6/8 项通过，2 项失败。
说明：R13 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。
```

### 0.2 `npm run check:round14`（exit **1**，**0/8**，verbatim）

```
> hongen-edu-apps@1.0.0 check:round14
> node scripts/check-round14.mjs


  ✗ H1 ASR 体验未放行：available=false，recorded=0/300，release=false，deviceRtf=false，harness=false，smoke=false —— r14-literacy-asr-finalize
  ✗ H2 OCR 体验未闭环：app=0/41，deviceB=false，queue=false，reflux=false，harness=false —— r14-literacy-ocr-device-b
  ✗ H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2
  ✗ H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full
  ✗ H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1
  ✗ H6 真机未签核：signoff=false，decision=false，record=false —— r14-android-device-matrix
  ✗ H7 商店内测未闭环：submit=false —— r14-store-internal-test
  ✗ H8 退化：round12=true，round13Pass=6/8

Round 14 体验门禁：0/8 项通过，8 项失败。
说明：R14 功能分支未全部合并时 FAIL 属预期红灯；体验 flip 目标 7/8 或 8/8。
```

链式兜底旁证：`npm run check:round12` 本 VM 实跑 **exit 0，「Round 12 全量落地门禁：8/8 项通过，0 项失败」**（round14 H8 的 `round12=true` 子信号与之一致）。

### 0.3 与 BRIEF 宣告基线（7/8 · 1/8）的差异根因（一手取证，非推断）

ROUND14-BRIEF 与 `acceptance-log-round13.md` 宣告基线 `check:round13` **7/8**（仅 H7 红）、`check:round14` **1/8**（仅 H8 绿）。本 VM 实测 **6/8 · 0/8**，多红的一格都是 **round13-H6**，取证链：

1. `check-round13.mjs` H6 的 `simOk` 腿要求双 APK **在磁盘落盘且 SHA256 与 `report.json` 对账一致**（`litApkOk`/`matApkOk`，探针 349–356 行）；
2. 本 VM 实查：`apps/literacy-app/android/app/build/outputs/apk/debug/` 与 `apps/math-app/android/app/build/outputs/apk/debug/` **均不存在**（`ls` 报 No such file or directory）——APK 是构建产物不入库，`report.json` 里的 `apkSha256`（literacy `f15e47b6…`、math `14ec403b…`，commit `834fe72` 时落盘）只剩单边记录；
3. 本 VM 无重建条件：`java -version` = OpenJDK **21**（android-sim 记录要求 JDK 17）、`$HOME/android-sdk` 不存在、`ANDROID_HOME` 为空、根/子包 `node_modules` 均未安装；
4. 因此 round13 H6 红 → round14 H8 的 `round13Pass=6/8 < 7` 也红。

**定性**：这不是 R13 交付退化（`report.json`、四份日志、`r13-android-sim-record.md` 均在库且 H6 的 `record=true，harness=true`），而是 **H6 判定对构建产物的环境敏感性**。R13 台账的 7/8 是在 JDK 17 + SDK 34 就绪、`android-sim.mjs` 全链路跑过的集成 VM 上实测的（`acceptance-log-round13.md` §2.1 有记录）；换任何干净 VM 都会复现本审计的 6/8。**给编排的硬结论见 §3-P1**。

### 0.4 六模块一手数字汇总（本 VM `node --input-type=module` 探针 import + 实读文件系统）

| 指标 | 实测值（`0d70870`） | 命令/来源 |
|---|---|---|
| 绘本 | **132 本 / 1121 页；scene 页 209；带 scene 的书 33 本** | import `books.js` 逐页数（≥2 个对象元素判 scene 页，与探针同口径） |
| 儿歌 | **13 首 / 13 挂旋律音频 / 3 首 vocal ref / humanStudio=0** | import `songs.js`；vocal 文件实测 sg1 82,289B · sg3 93,353B · sg5 75,842B（均在 `audio/songs/`，非 vocal-batch 目录——该目录不存在） |
| ASR manifest | **available=false；files=7；合计 37,022,120 B** | 实读 `apps/literacy-app/public/asr/manifest.json` |
| ASR 冻结集 | **clips=58；skeleton（id+spoken）=50；recorded（status=recorded+audio）=0** | 实读 `apps/literacy-app/scripts/data/asr-eval-set.json` |
| ASR RTF | **host p50 0.134 / p95 0.276（`onDevice:false`）；device 未实测** | `r13-asr-android-rtf-baseline.md` + `evidence/r13/asr-rtf/host-baseline.json`（R13 实录） |
| OCR 样张 | **real 10 张 / tier 10 条** | 实读 `real-samples.json` |
| OCR A/B 段 | **A 段 37 项通过 0 失败；B 段 4 项 SKIP（owner: Android QA，无设备）** | 实读 `evidence/r13/android-sim/ocr-device-a.log` 尾部汇总行 |
| OCR App 证据 | **`evidence/r14/ocr/app-webview-matrix.json` 与 `evidence/r13/android-sim/ocr-section.json` 均不存在 → 探针 app=0/41** | `check:round14` H2 输出 + `ls` |
| OCR 回流队列 | **`apps/literacy-app/scripts/fixtures/ocr/regressions/` 不存在 → queue=false** | `ls` |
| L1 朗读（X1/H5） | **`public/audio/tts-l1/` 不存在 → assets=0/20** | `ls` |
| android-sim 报告 | **`simulated:true`；commit `834fe72`；识字 164 路由/42 交互/0 问题；数学 20 路由/36 交互/0 问题；8 步全 PASS** | 实读 `evidence/r13/android-sim/report.json` |
| 真机证据 | **`.agent_workspace/evidence/r14/` 不存在**；定案文档仍 `r12-android-device-decision.md`（NO-GO） | `ls evidence/`（只有 r8–r13 与 r9-math-graph-reco） |
| mobile LH | **literacy performance 0.97 / math 0.95** | 实读 `evidence/r12/lighthouse-*-mobile.json` 的 `categories.performance.score` |
| R14 文档/标记 | **`r14-*.md` 零个存在；`test-asr-eval-set.mjs`/`test-ocr-device.mjs` 无 `ROUND14_H1`/`ROUND14_H2` 标记** | `ls` + `rg -c`（无匹配） |

---

## 1. 六个 ◐ 模块逐项：R13 实测 → R14 flip 判定 → R14-1 子集 → R15 尾巴

口径：「R14 flip 条件」= `check-round14.mjs` v1.0 探针子信号（工程杆，全部满足才亮对应 H 格）**加** ROUND14-ACCEPTANCE §3 对应 W 走查（体验终审杆，探针绿≠flip，两杆都过才在终审记 ✅）。「R14-1 可交付子集」按 ROUND14-BRIEF 14-1 派发的 6 个子代理与阶段表（探针预期 2–3/8）划界。

### 1.1 L-M9 跟读评测（→ round14 H1）

- **R13 实测**：落库 files=7 / 37,022,120 B（探针 verified）；`available:false`；冻结集 58 clips 中 skeleton 50、**recorded 0**；host RTF p50 0.134 / p95 0.276（`onDevice:false`）；device RTF 零证据。孩子点「我来读」仍是录音回放 + 响度分——体验与 R10 相同。
- **R14 flip 条件（全部满足）**：
  1. `manifest.json` `available === true`；
  2. `asr-eval-set.json` 中 `status:'recorded'` 且带 `audio|audioPath|wav` 的 clips **≥300**；
  3. `r14-followread-release.md`（或 r13 同名）>600 字 + `ROUND14_H1` + **GO 结论**（结论区不得含 NO-GO/BLOCKED）；
  4. `evidence/r14/asr/device-rtf.json`：`onDevice:true` + `rtfP95 ≤ 0.5` + 非 `simulated`——**host 0.276 不能充数，必须真机**；
  5. `test-asr-eval-set.mjs` 带 `ROUND14_H1` + assert；smoke 带 `ROUND14_H1_SMOKE`（当前两者皆无）；
  6. 体验终审 W1：儿童跟读 3 首诗盲测，实时评分非回放。
- **R14-1 可交付子集**（分支 #4 `r14-literacy-asr-recording`）：录音启动批次 1–100（recorded 0→≥100）+ 录制规范/双标注流程文档 + harness/smoke 标记先落。**H1 在 14-1 保持红属预期**（recorded<300、无 device RTF）；300 条补齐 + device RTF + flip available 归 14-2 分支 #8。
- **R15 尾巴**：300 条实录的儿童真人双标注成色复审（合成/成人代录充数则终审打回）；低端 Android 五类故障真机演练；声调声学级验证；模型换版横比治理。

### 1.2 L-M10 拍照识字（→ round14 H2）

- **R13 实测**：real 样张 10 张 / tier 10；A 段 37 断言 0 失败；B 段 4 项 SKIP（无设备）；引擎侧矩阵 40/41（`r12-ocr-matrix.md` 文档值）；**App/WebView 侧召回证据文件缺失 → 探针 app=0/41**；回流队列 `regressions/queue.json` 不存在；`ROUND14_H2` 标记不存在。BRIEF 写的基线「App 33/41」在仓库无 evidence 出处（§3-P2）。
- **R14 flip 条件（全部满足）**：
  1. `evidence/r14/ocr/app-webview-matrix.json`：`passCount ≥ 40`、`total ≥ 41`（App 侧实测 JSON，非引擎文档值）；
  2. `evidence/r14/android/ocr-device-b.json`：`pass:true` + `onDevice:true` + 非 `simulated`——B 段 4 项 SKIP 必须在真机清掉；
  3. `apps/literacy-app/scripts/fixtures/ocr/regressions/queue.json`：≥1 条目且 **无 `dueRound ≤ 14` 的 `new/triaged` 逾期项**；
  4. 回流文档（`r14-ocr-experience-loop.md` 或 r13 版）>600 字 + `ROUND14_H2` + 采集/标注/复现/闭环四要素；
  5. `test-ocr-device.mjs` 带 `ROUND14_H2` + assert + android/device 信号（当前只有 ROUND13_H2）；
  6. 体验终审 W2：真机拍 10 张日常场景 ≥9 张首屏认对 + 回流路径可演示。
- **R14-1 可交付子集**（分支 #3 `r14-literacy-ocr-preprocess`）：预处理修复 + `app-webview-matrix.json` 首次落盘（目标 ≥40/41）+ `queue.json` 建队 + `ROUND14_H2` 标记。**deviceB 腿 14-1 无法交付**（无设备），归 14-2 分支 #12——H2 在 14-1 保持红属预期。
- **R15 尾巴**：用户实拍失败样本回流常态化（队列有真实来源而非自造）；低档机 wasm 耗时边界；拍照/相册/引擎包三路径长稳。

### 1.3 L-M11 动画儿歌（→ round14 H4）

- **R13 实测**：13 首 / 13 挂旋律；vocal ref 3 首（sg1 82,289B / sg3 93,353B / sg5 75,842B）**全部 Piper 合成、humanStudio=0/13**；`vocal-batch/` 目录不存在。盲听即穿帮——E2 差距整档。
- **R14 flip 条件（全部满足）**：
  1. `songs.js` 13 首歌**逐首** `humanStudio: true` 且 vocal 文件（`vocal|vocalAudio` ref）落盘 ≥10,240 B——探针按 Set 去重实数，13/13；
  2. `r14-songs-vocal-full.md` >500 字 + `ROUND14_H4` + 全库/真人字样 + 许可留痕（CONTENT_LICENSE/THIRD_PARTY_NOTICES 同步）；
  3. 体验终审 W4：13 首盲听家长问卷可接受真人主唱。
  4. 诚实红线：`humanStudio:true` 只能标注真人演播资产；Piper/合成置换必须标 false——探针防不了说谎，终审盲听防。
- **R14-1 可交付子集**（阶段表目标：范唱 4–7 首）：14-1 派发表无专属分支，实际落点在 14-2 分支 #10（7–13 首）与 14-3 分支 #14（收尾+许可）；14-1 若有余力先交 4–7 首 humanStudio 资产与命名/许可规范。**H4 在 14-1/14-2 保持红属预期**（探针只认 13/13）。
- **R15 尾巴**：角色动画 MV、IP 化演出；若 R14 以「高质量置换」过盲听，全曲真人演播批次归 R15。

### 1.4 L-M5 分级绘本（→ round14 H3）

- **R13 实测**：scene 页 **209 / 1121**（18.6%），覆盖 **33 / 132** 本；`rendered=true`（BookPageScene 接线不退化）；`ROUND14_H3` 标记未落。翻出高频 33 本即见「单 emoji + TTS」旧表现力。
- **R14 flip 条件**：
  1. 探针杆：scene 页 **≥400** + rendered 不退化 + `ROUND14_H3` 落在 books 数据或 smoke；
  2. 体验终审 W3：随机翻 10 页 ≥9 页多元素 scene + 旧页不回归。
  3. **计数口径注意**：探针只数「≥2 个对象元素」的页；R14-1 增页须走同口径自测（import books.js 逐页数），防「加了 200 页但元素结构不合探针」的空转。
- **R14-1 可交付子集**：阶段表明文「scene +200 页」（209→≥400）——**H3 是 14-1 探针预期 2–3/8 中最可达的一格**；分支表把 books-batch2 排在 14-2（#9），14-1 内以哪路交付由编排定，杆不变。
- **R15 尾巴**：BRIEF 明文——**终局 1121/1121 全库归 R15 分批**；故 **R14 终审 L-M5 按 ◐（大幅收窄）记，不 flip ✅**（§2 计数表按此口径）；X1 朗读音质与外部投稿演练随行。

### 1.5 L-M15 识字端性能/离线/真机（→ round14 H6，与 M-M16 同源）

- **R13 实测**：mobile LH literacy **0.97**；android-sim `simulated:true`（识字 164 路由 / 42 交互 / 0 问题，双 APK SHA 记录在 report）；**`evidence/r14/android/` 不存在**；定案文档停在 `r12-android-device-decision.md` = **NO-GO**；且本 VM 上 APK 产物缺失导致 round13-H6 都翻红（§0.3）。E5 真机签核零进展——sim 永不等价签核（X3）。
- **R14 flip 条件（全部满足）**：
  1. `evidence/r14/android/device-signoff.json`：`pass:true` + `onDevice:true` + `devices[]` **≥2 台** + 非 `simulated`；
  2. `r14-android-device-decision.md` >600 字 + `ROUND14_H6` + **GO 结论**（结论区不得含 NO-GO/BLOCKED；r12 版 NO-GO 不能充数——探针 fallback 读 r12 但 GO 判定过不了）；
  3. `r14-android-device-record.md` >800 字 + 真机声明 + `evidence/r14/android` 路径引用 + `ROUND14_H6`；
  4. 体验终审 W6/终验清单 6：2 台真机 × 双 App × 离线 30min 无 crash。
- **R14-1 可交付子集**（分支 #5 `r14-android-device-matrix`）：真机矩阵 harness（脚本化采集 device-signoff 所需字段）+ `evidence/r14/android/` 目录规范与 signoff 模板 + 阻塞点识别。**真设备是外部依赖**：VM 无 adb 设备（A 段日志 B1–B4 SKIP 实证）——若 R14 全程无实体设备，H6 与 H1-deviceRtf、H2-deviceB 三腿同时物理阻断，须像 H7 一样走「用户供给设备或签字接受」的诚实红灯路径，**禁止用 sim 数据填 r14 真机目录**（BRIEF 红线）。
- **R15 尾巴**：低档机每轮 30min 回归常态化；mobile P 下行止血线;真机证据滚动（r15 目录）。

### 1.6 M-M16 数学端性能/离线/真机（→ round14 H6，与 L-M15 共判）

- **R13 实测**：mobile LH math **0.95**；android-sim 数学 20 路由 / 36 交互 / 0 问题；APK 4,299,368 B（report 记录，磁盘无产物，同 §0.3）；`evidence/r14/android/` 不存在。数学侧无独立缺口，红灯与 L-M15 完全同源。
- **R14 flip 条件**：与 §1.5 同一组子信号——`device-signoff.json` 的 `devices≥2` 与离线 30min 走查须**覆盖双 App**（数学 20 路由 smoke 与识字同跑），缺数学腿则 M-M16 不随 L-M15 flip。
- **R14-1 可交付子集**：随 §1.5 分支 #5；矩阵 harness 须显式含数学 APK 安装/冷启/离线段。
- **R15 尾巴**：同 §1.5；另有数学首屏 gzip 预算（<250 KB）在近两轮未单测（R13 台账「记录」项），R15 回归补测。

---

## 2. 体验口径计数表（基线 vs R14 目标）

31 个对标模块（识字 L-M1–M15 计 15 + 数学 M-M1–M16 计 16），判定杆与 R13 审计 §4 完全一致：

| 口径 | ✅ | ◐ | ❌ | 依据 |
|---|---|---|---|---|
| 探针口径（基线，本 VM `0d70870` 实跑） | round12 **8/8** · round13 **6/8** · round14 **0/8** | — | — | §0.1–0.2 verbatim；round13-H6 环境敏感见 §0.3 |
| 体验口径 · 基线 | **25** | **6**（L-M5 / L-M9 / L-M10 / L-M11 / L-M15 / M-M16） | **0** | R13 审计 §4 名单，本轮 §0.4 一手数字逐项复核无一 flip（R14 分支零合入，符合预期） |
| 体验口径 · R14-1 结束预期 | **25** | **6** | **0** | 14-1 只交付子集（recorded≤100、范唱≤7、deviceB 缺）——**无模块 flip，探针预期 2–3/8**（H3 最可达 + H8 需集成 VM 重建 APK 后回 1 格） |
| 体验口径 · R14 目标（探针 8/8 + W1–W6 全过） | **30** | **1**（仅 L-M5，按 BRIEF 明文留 R15 全库） | **0** | L-M9/L-M10/L-M11/L-M15/M-M16 五项 flip（§1 逐项杆） |
| 体验口径 · R14 最坏情形（真机 + Play 账号双阻断） | **28** | **3**（L-M5 + L-M15 + M-M16） | **0** | H6 三腿物理阻断走诚实红灯（§1.5）；H7 沿用 R13 签字接受路径；L-M9/L-M10 若仅 device 腿卡则降级判定由终审裁量，本表按「device 证据缺则不 flip」的严杆计 |

**flip 判定的两杆原则（终审必须双过）**：探针格绿（`check:round14` 对应 H 格）+ 对应 W 走查过（W1 跟读实时 / W2 真机拍照 / W3 随机翻页 / W4 盲听 / W5 L1 点读 / W6 真机+商店）。任何一杆缺失，终审只记「收窄」不记 flip——与 R12/R13 两轮「探针绿但体验仍 ◐」的教训一致。

---

## 3. 流程债与给编排的硬提醒（本审计新发现）

| # | 债 | 一手证据 | 动作 |
|---|---|---|---|
| **P1** | **round13-H6 / round14-H8 对 APK 构建产物环境敏感**：干净 VM 上 `check:round13` 恒 6/8 → `check:round14` H8 恒红 → **8/8 物理不可达** | §0.3 四步取证（APK 路径不存在 + JDK 21 + 无 SDK + 无 node_modules） | R14 集成终验 VM 必须先备 JDK 17 + SDK 34 并跑 `node scripts/android-sim.mjs` 重建双 APK 刷新 report 对账，再跑 `check:round13`/`check:round14`；或由 #6 验收子代理在 round14-H8 判定中显式声明「须构建产物就绪」的前置条件，防终验误判退化 |
| **P2** | BRIEF/ACCEPTANCE 宣称的基线「App 33/41」**仓库内无 evidence 出处**（全库检索仅 BRIEF/ACCEPTANCE 自引；`ocr-section.json` 与 `app-webview-matrix.json` 均不存在） | `rg` 全库 + `ls` | #3 OCR 子代理首次落盘 `app-webview-matrix.json` 时同步记录测量方法，让 33→40 的「修复前后」对照有一手锚点；文档引用该数字处标注「待证」 |
| **P3** | BRIEF 阶段表与分支表不一致：14-1 阶段重点含「范唱 4–7 首 + scene +200 页」，但对应分支（#9/#10）排在 14-2 | ROUND14-BRIEF §三阶段 vs §子代理分工对读 | 编排在 14-1 结论简报中明确这两项的实际落轮，避免 14-2 复审时误判「14-1 欠交」 |
| **P4** | `acceptance-log-round13.md` §2.4 资产清单仍 `[待填]`×3、W1/W3/W4/W5 走查未勾 | 实读该文件 §2.4/§4 | R14 终验回填或显式关闭（H7 类比：不填则注明 owner 与阻断原因） |
| **P5** | R14 三个 device 腿（H1-deviceRtf / H2-deviceB / H6-signoff）共享同一外部依赖「实体 Android 设备」，BRIEF 未给设备到位的负向路径 | §1.1/1.2/1.5 探针子信号对读 | 编排提前定裁量口径：设备缺位时按 H7 先例走诚实红灯 + 签字接受，明确最坏情形计数（§2 末行），禁止 sim 冒充（BRIEF 红线重申） |

---

## 4. 审计方法备注

- 门禁实跑：`/workspace` @ `0d70870` 干净检出 · `check:round13` **exit 1（6/8）** · `check:round14` **exit 1（0/8）** · `check:round12` **exit 0（8/8）**——§0.1/0.2 为 tee 落盘的 verbatim。
- 一手计数命令：`node --input-type=module` 探针 import `books.js`（132 本/1121 页/209 scene 页/33 本带 scene）与 `songs.js`（13/13/3/0）；`fs.readFileSync` 实读 `manifest.json`（7 files/37,022,120B/available:false）、`asr-eval-set.json`（58/50/0）、`real-samples.json`（10/10）、`report.json`（simulated:true/164/20）、r12 两份 mobile LH JSON（0.97/0.95）；`ls` 实证 APK/`evidence/r14/`/`tts-l1/`/`regressions/`/`vocal-batch/` 缺失；`rg` 实证 `ROUND14_H1`/`ROUND14_H2` 标记缺失与「33/41」无出处。
- 引用而非重测：host RTF（R13 落盘 evidence）、OCR A 段 37 断言（R13 日志尾行）、R13 台账 7/8（SDK 就绪集成 VM 历史实测，与本 VM 6/8 的差异已在 §0.3 归因）。
- 未重测：`npm test` 全链（本 VM 未装依赖且非本审计交付项，最近一手记录见 `acceptance-log-round13.md` 结论区）、Lighthouse 新跑、android-sim 重跑（无 SDK，见 P1）。
- 本审计不预支任何在途 R14 分支交付；六模块判定全部以 `0d70870` HEAD 摸得到的为准。
