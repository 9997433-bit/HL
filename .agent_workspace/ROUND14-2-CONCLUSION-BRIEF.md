Model slug: claude-fable-5
# Round 14-2 结论简报 · 差距复审（注入 Round 14-3）

标记：`ROUND14_R2_AUDIT`

> 审计人：Round 14-2 子代理 #7（fable，分支 `cursor/r14-round2-audit-9f67`）
> 审计基线：集成线 `cursor/openmoji-integration-9f67` @ **`c33caf4`**（R14-1 六路已合入 + 14-2 编排已启动、14-2 功能分支 #8–#12 全部在途未合入）
> 审计日期：2026-08-28 · Node v22.14.0 / npm 10.9.7 · 干净 VM 检出，依赖 `npm ci` 自装，门禁实跑退出码为准
> 方法：对照 `ROUND14-1-CONCLUSION.md` 与 R14-1 审计（`round14-hongen-audit.md`，基线 `0d70870`），对 6 个 ◐（L-M5 / L-M9 / L-M10 / L-M11 / L-M15 / M-M16）逐子信号复测；三探针 verbatim 落盘；给出 14-2 六路（#7–#12）集成验收判据与 R14-3 预判。
> **结论先行**：干净 VM 首跑 `check:round14` **0/8**、`check:round13` **6/8**——精确复现 R14-1 审计 P1（H6 对 APK 构建产物环境敏感）。本轮把 P1 处方从「文档警告」升级为「实操验证」：JDK 17 + SDK 34 自装 + `android:sim` 全链路 12 分钟重建双 APK 后，**`check:round14` 1/8（仅 H8 绿）· `check:round13` 7/8（仅 H7 红）· `check:round12` 8/8 · `npm test` 全绿（exit 0）**——与 R14-1 结论宣告基线完全一致，零退化。6◐ 进展：**L-M10（OCR）六腿绿五腿只剩 deviceB**，H1 跑道就位（harness/smoke 绿、冻结集 100 槽）但 recorded 仍 0，H6 record/隔离腿绿但 signoff 零证据，H3/H4/H5 零变动（对应 14-2 在途分支，预期内）。**最重要的结构性发现（§3-S2）：外部供给缺口有三类（实体设备 / 真人音频资产 / Play 账号），BRIEF 的 14-2 预期 5–6/8 隐含前两类到位；三类全缺时代理可达上限 3/8（H3+H5+H8），R14-1 审计 §2 的最坏情形 28✅/3◐ 需下修为 25✅/6◐（原地收窄不 flip）。**

---

## 0. 三探针实跑（本 VM，verbatim，退出码为准）

### 0.1 干净 VM 首跑（未重建 APK）——P1 复现实证

`npm run check:round14`（exit **1**，**0/8**，verbatim）：

```
> hongen-edu-apps@1.0.0 check:round14
> node scripts/check-round14.mjs


  ✗ H1 ASR 体验未放行：available=false，recorded=0/300，release=false，deviceRtf=false，harness=true，smoke=true —— r14-literacy-asr-finalize
  ✗ H2 OCR 体验未闭环：app=40/41，ocrSection=true，deviceB=false，queue=true，reflux=true，harness=true —— r14-literacy-ocr-device-b
  ✗ H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2
  ✗ H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full
  ✗ H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1
  ✗ H6 真机未签核：signoff=false，decision=false，record=true，noR13SimPath=true —— r14-android-device-matrix
  ✗ H7 商店内测未闭环：submit=false —— r14-store-internal-test
  ✗ H8 退化：round12=true，round13Pass=6/8

Round 14 体验门禁：0/8 项通过，8 项失败。
说明：R14 功能分支未全部合并时 FAIL 属预期红灯；体验 flip 目标 7/8 或 8/8。
```

同期 `check:round13` **6/8（exit 1）**——H6 `sim=false`（APK 产物不入库，磁盘无 `app-debug.apk` 可对账），H7 `submit=false`；其余六格绿。这与 R14-1 审计 §0.3 的预言逐字吻合：**换任何干净 VM 都复现 6/8 → round14-H8 连锁红**。

### 0.2 P1 处方实操后（本轮新增一手验证，集成/终验 VM 照方抓药）

本 VM 从零自备构建链，全程约 25 分钟，五步：

1. `npm ci`（否则 `android:sim` 的 `build:all` 步静默失败，不产任何 APK）；
2. `apt install openjdk-17-jdk-headless`（gradle 8.2.1 wrapper 不支持系统默认 JDK 21）；
3. `dl.google.com` 下载 cmdline-tools 至 `/opt/android-sdk`，`sdkmanager` 装 `platform-tools` + `platforms;android-34` + `build-tools;34.0.0`（`variables.gradle` compileSdk=34）；
4. `ANDROID_HOME=/opt/android-sdk JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 npm run android:sim`——本 VM 实测 **12 分钟**全链路绿：识字 APK 36,222,797 B / 数学 APK 4,261,568 B 落盘，`report.json` SHA256 对账刷新，识字 164 路由 / 数学 20 路由 smoke 0 问题；
5. 复跑三探针。刷新的 `evidence/r13/android-sim/` 六文件按既有惯例（`7b7cf73`/`7a2402e`/`b50e7a1` 三次先例）随本简报提交。

`npm run check:round14`（exit **1**，**1/8**，verbatim）：

```
> hongen-edu-apps@1.0.0 check:round14
> node scripts/check-round14.mjs

  ✓ H8 往轮不退化：round12 8/8 + round13 7/8

  ✗ H1 ASR 体验未放行：available=false，recorded=0/300，release=false，deviceRtf=false，harness=true，smoke=true —— r14-literacy-asr-finalize
  ✗ H2 OCR 体验未闭环：app=40/41，ocrSection=true，deviceB=false，queue=true，reflux=true，harness=true —— r14-literacy-ocr-device-b
  ✗ H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2
  ✗ H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full
  ✗ H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1
  ✗ H6 真机未签核：signoff=false，decision=false，record=true，noR13SimPath=true —— r14-android-device-matrix
  ✗ H7 商店内测未闭环：submit=false —— r14-store-internal-test

Round 14 体验门禁：1/8 项通过，7 项失败。
说明：R14 功能分支未全部合并时 FAIL 属预期红灯；体验 flip 目标 7/8 或 8/8。
```

`npm run check:round13`（exit **1**，**7/8**，verbatim）：

```
> hongen-edu-apps@1.0.0 check:round13
> node scripts/check-round13.mjs

  ✓ H1 ASR 放行：files[] 落盘 37022120B + 放行/冻结集腿 + harness + ROUND13_H1_SMOKE
  ✓ H2 OCR Android 模拟 + 失败回流设计 + harness ROUND13_H2
  ✓ H3 绘本终局 209 页 scene（≥200）+ 渲染接线 + ROUND13_H3
  ✓ H4 范唱批次 3 首（≥3）+ 13/13 音频 + ROUND13_H4
  ✓ H5 lift 准实验口径 + ROUND13_H5_SMOKE
  ✓ H6 Android 模拟：双 APK 落盘 + 证据日志 + 签核文档 + ROUND13_H6 harness
  ✓ H8 Round 12 门禁 8/8 无退化

  ✗ H7 商店实提未闭环：submit=false —— r13-store-submit

Round 13 终局门禁：7/8 项通过，1 项失败。
说明：R13 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。
```

`npm run check:round12`（exit **0**，**8/8**，verbatim）：

```
> hongen-edu-apps@1.0.0 check:round12
> node scripts/check-round12.mjs

  ✓ H1 ASR 落库：files[] 落盘校验 37022120B + R12 落库 Go/No-Go + harness + ROUND12_H1_SMOKE
  ✓ H2 OCR 系统化 10 张 + 授权 10 条 + tier 10 + harness + ROUND12_H2
  ✓ H3 绘本场景铺开 209 页（≥60）+ 渲染接线 + ROUND12_H3
  ✓ H4 儿歌 13/13（音频 13）+ 范唱试点 + ROUND12_H4
  ✓ H5 推荐度量 + 开练 34 节点覆盖 + ROUND12_H5_SMOKE
  ✓ H6 evidence/r12 mobile LH 2 份（P≥95）+ 真机通道定案文档
  ✓ H7 TTS 试点（true）或 商店提交演练 + R12 反馈运行（true）
  ✓ H8 Round 11 门禁 8/8 无退化

Round 12 全量落地门禁：8/8 项通过，0 项失败。
```

链式旁证：`npm test` 本 VM 实跑 **exit 0 全绿**（feedback + 识字 + 数学三套，约 11 分钟；数学侧「基础测试通过：62 个构建文件」）。

---

## 1. 6◐ 逐项：R14-1 基线（`0d70870`）→ R14-2 起点（`c33caf4`）进展对比

一手数字（本 VM 探针同口径复测）：绘本 **132 本 / 1121 页 / scene 209 页 / 33 本带 scene**（零变动）；儿歌 **13 首 / humanStudio 0**（零变动）；ASR `manifest.available=false`、冻结集 clips **58 → 100 槽**、recorded **0 → 0**；OCR `app-webview-matrix.json` **首次落盘 40/41**（字级，样张 10 张）；回流队列 **5 条（4 closed + 1 engine-limit，无逾期 new/triaged）**；`evidence/r14/` 现有 `ocr/` 一个子目录，`android/`、`asr/`、`tts-l1/` 均不存在。

| ◐ 模块 | 探针 | 子信号 R14-1 → R14-2 | 判定 |
|---|---|---|---|
| L-M9 跟读 | H1 | harness **false→true**、smoke **false→true**、冻结集 58→**100 槽**（批次 1 排位 + 落库闸）；available false→false、recorded **0→0**、release false→false、deviceRtf false→false | **收窄 2/6 腿**：跑道与闸就位，三条核心腿（实录 / 放行 / 真机 RTF）零证据，全押 #8 + 外部供给 |
| L-M10 OCR | H2 | app **0/41→40/41**（首次一手落盘，顶替 P2「33/41 无出处」债）、ocrSection **→true**、queue **false→true**（无逾期）、reflux **false→true**、harness **false→true**；deviceB false→false | **收窄 5/6 腿，全线最接近 flip**：只剩真机 B 段一腿（#12 + 实体设备） |
| L-M5 绘本 | H3 | scene **209→209**、rendered true→true、ROUND14_H3 false→false | **零变动（预期内）**：batch2 是 14-2 #9 在途分支 |
| L-M11 儿歌 | H4 | humanVocal **0/13→0/13**、doc false→false | **零变动（预期内）**：#10 在途；真人音源属外部供给（§3-S2） |
| L-M15 识字真机 | H6 | record **false→true**（`r14-android-device-record.md`：harness scaffold + 诚实 SKIP 账）、matrix harness 741 行落盘、noR13SimPath **→true**（v1.1 隔离闸绿）；signoff false→false、decision false→false、`evidence/r14/android/` 仍不存在 | **收窄文档/工具腿**：签核三腿（signoff JSON / GO 定案 / 2 台真机）零证据，等实体设备 |
| M-M16 数学真机 | H6 | 与 L-M15 完全同源；数学 APK 本轮重建 4,261,568 B、20 路由 smoke 0 问题（sim 侧健康） | 同上，随 L-M15 共判 |

X1（H5，非 6◐ 但在探针内）：assets 0/20、doc false、smoke false——零变动，#11 在途。H7：submit=false，Play 账号阻断延续。

---

## 2. Round 14-2 六路验收判据（集成 cherry-pick 前逐路把关）

通用闸（每路合入前）：`npm test` 全绿 + `check:round13` ≥7/8（须先按 §0.2 处方重建 APK）+ `check:round12` 8/8 + 对应 `check:round14` H 行子信号按下表核对。

| # | 分支 | 验收判据（工程腿） | 诚实红线（供给腿缺位时） |
|---|---|---|---|
| 7 | r14-round2-audit（本路） | 本简报在库 + `ROUND14_R2_AUDIT` 可 rg + 三探针 verbatim 与集成 VM 复跑一致 + 刷新的 r13 android-sim 证据随简报提交 | —（纯审计路，无供给腿） |
| 8 | r14-literacy-asr-finalize | 冻结集扩到 **≥300 槽**且排位/落库闸随扩；`ROUND14_H1`/`ROUND14_H1_SMOKE` 标记保持；放行文档骨架（>600 字，GO 判定留待实录齐）；`evidence/r14/asr/device-rtf.json` 结构按 v1.1（onDevice:true + simulated:false + 非空 device 身份 + 0≤p95≤0.5） | recorded<300 时**禁止** flip `available:true`；禁合成/成人代录充儿童实录（W1 盲测防）；设备缺位按 H7 先例记 owner+阻断+签字路径，H1 保持诚实红 |
| 9 | r14-literacy-books-batch2 | scenePages **≥400**（探针口径：页内 ≥2 个对象元素，import 实数）+ rendered 不退化 + `ROUND14_H3` 落 books 数据或 smoke；旧 209 页无回归（132 本/1121 页总量不减）；随机 10 页抽查 ≥9 页多元素（W3 预演） | 防「加页但元素结构不合探针口径」空转——合入前跑 §1 同款 import 计数自证 |
| 10 | r14-literacy-vocal-7-13 | 增量 ≥7 首 `humanStudio:true` 且 vocal 文件 ≥10,240 B；许可留痕（CONTENT_LICENSE / THIRD_PARTY_NOTICES 同步）；探针 H4 在 <13/13 时保持红**属预期**，验收看增量与来源 | `humanStudio:true` 仅限真人演播资产（盲听抽查）；VM 无真人音源时**诚实 0 增量 + 文档记供给缺口**，禁 Piper 换标 |
| 11 | r14-literacy-tts-l1 | `public/audio/tts-l1/` **≥20 资产**落盘 + `r14-tts-l1-batch.md`（>阈值字数，含 `ROUND14_H5`）+ smoke 带 `ROUND14_H5_SMOKE`——BRIEF 明文「真人**或**高质量离线 TTS」，故 **H5 是 14-2 内代理可达的一格**，验收要求 H5 行直接翻绿 + W5 听感抽查 | 资产须可播放且非空壳（逐个 ≥1KB 级抽查）；音质不过 W5 则记收窄不记 flip |
| 12 | r14-literacy-ocr-device-b | `evidence/r14/android/ocr-device-b.json`：`pass:true` + `onDevice:true` + `simulated:false`；队列保持无逾期（当前 4 closed + 1 engine-limit 为合格基线）；`ROUND14_H2` 保持 | 设备缺位→沿 `62c2291` 先例 scaffold + 诚实 SKIP，deviceB 保持 false、H2 保持红并记 owner；**禁把 r13 sim 或本 VM 跑的结果写进 `evidence/r14/android/`**（noR13SimPath + simulated:false 双闸会红，但防绕行意识仍须人审） |

---

## 3. 结构性发现（本轮新增）

- **S1（P1 收口）**：APK 重建处方经本轮实操验证（§0.2 五步，干净 VM 约 25 分钟、重建本体 12 分钟）。round13-H6/round14-H8 不再是「物理不可达」，是「照方抓药」。建议 #18 集成收官把该处方固化进 `RELEASE-CHECKLIST.md` 或 `r13-android-sim-record.md`，且**终验 VM 跑探针前必执行**。
- **S2（P5 扩展，最重要）**：外部供给缺口有**三类**，不止 R14-1 审计建模的设备一类——(a) **实体 Android 设备** → H1-deviceRtf / H2-deviceB / H6-signoff；(b) **真人音频资产**（300 条儿童实录、7–13 首真人演唱）→ H1-recorded / H4-humanVocal；(c) **Play 账号** → H7。BRIEF 的 14-2 预期 **5–6/8 隐含 (a)(b) 至少部分到位**；三类全缺时 14-2 代理可达上限 = **H3 + H5 + H8 = 3/8**（H2 五腿绿但整格红）。R14-1 审计 §2 最坏情形 28✅/3◐ 只建模了 (a)(c)，**若 (b) 也缺则 L-M9/L-M11 同样 flip 不了，最坏情形应下修为 25✅/6◐**（多项大幅收窄但零 flip）。14-3 编排应把六路交付显式分「代理可达」「用户供给」两栏，并向用户明确征集 (a)(b)(c)。
- **S3（P2 收口）**：R14-1 审计记的「App 33/41 仓库无出处」债已被 `app-webview-matrix.json` 一手 40/41（字级、样张 10 张、逐例非空 + 汇总对账）顶替；唯一失败例 R14-OCR-005 在队列标 `engine-limit`（dueRound null，非逾期），符合 v1.1 无逾期判定。

---

## 4. R14-3 预判

- **探针算术**：14-2 收官（#8–#12 全合入）时——**3/8 稳**（H8 处方就绪 + H3 高置信 + H5 高置信）；**+1 格看 (a)**（#12 拿到真机则 H2 翻绿，五腿已就位）；H1 双供给依赖（(a)+(b)）、H4 供给依赖（(b)，且探针只认 13/13，BRIEF 把收尾排在 14-3 #14）、H6 供给依赖（(a)）、H7 供给依赖（(c)）。**BRIEF 宣告的 5–6/8 只在 (a)(b) 到位时可达；全缺时 3/8 即为诚实上限，14-3 复审不得把该差距记为 14-2 欠交**。
- **14-3 优先级**：(1) #13 终审按 S2 三类供给逐项记「诚实红灯 + owner + 签字接受路径」（H7 的 R13 先例推广到 H1/H2/H4/H6）；(2) #18 集成收官先按 §0.2 处方重建 APK 再跑三探针，并回填 P4（`acceptance-log-round13.md` §2.4 三处 `[待填]` 与 W 走查勾选）；(3) W1–W6 分两栏：W3/W5 代理可达（随 H3/H5 落地即可勾），W1/W2/W4/W6 供给依赖；(4) H7 沿签字接受先例，7/8 + 签字即可收口 R14，8/8 需 Play 账号实提。
- **体验口径预判**：全供给到位 → **30✅/1◐**（R14-1 审计 §2 目标行，L-M5 按 BRIEF 留 R15）；仅 (a) 到位 → **28✅/3◐**；(a)(b)(c) 全缺 → **25✅/6◐ 原地**（但 L-M10 五腿、H3/H5 落地后 L-M5/X1 大幅收窄——收窄要在 flip 表里如实记「收窄」行，防止「原地」被误读为「空转」）。
- **R15 交接面预判**：绘本全库 1121（R15 分批既定）+ ASR 双标注成色复审 + 范唱 IP 化 + 低档机常态回归——14-3 结论简报应把 S2 的供给征集清单作为 R15 前置条件显式移交。

---

## 5. 审计方法备注

- 实跑：`/workspace` @ `c33caf4` 干净检出 → `npm ci` → 首跑三探针（§0.1）→ §0.2 五步处方（JDK 17 / SDK 34 / cmdline-tools 自装 + `android:sim` 全链路）→ 复跑三探针 + `npm test`。全部退出码一手：r14 **exit 1（1/8）**、r13 **exit 1（7/8）**、r12 **exit 0（8/8）**、test **exit 0**。
- 一手计数：探针同口径 import `books.js`（BOOKS：132/1121/209/33）与 `songs.js`（SONGS：13/humanStudio 0）；`fs` 实读 `manifest.json`（available:false / files 7）、`asr-eval-set.json`（clips 100 / recorded 0）、`app-webview-matrix.json`（40/41 / 样张 10）、`regressions/queue.json`（4 closed + 1 engine-limit）；`ls` 实证 `evidence/r14/` 仅 `ocr/`、`tts-l1/` 不存在。
- 引用而非重测：R14-1 审计 `0d70870` 基线子信号（§1 对比左列）、v1.1 正/负向攻击抽查（`ROUND14-ACCEPTANCE.md` §4）。
- 边界：本审计只审集成线 HEAD，**不预支 #8–#12 在途分支内容**；§2 判据供集成合入时逐路核对。刷新的 `evidence/r13/android-sim/` 六文件（report.json 对账 + 四份日志）随本简报按先例提交，APK 本体照旧不入库。
