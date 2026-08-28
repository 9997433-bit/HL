Model slug: claude-fable-5
# Round 13 · 洪恩模块对标审计（R12 闭合后 7◐ 复验）

> 审计人：Round 13 子代理 #2（fable）
> 审计基线：集成线 `cursor/openmoji-integration-9f67` @ **`7bc74c7`**（R12 工程门禁 **8/8 闭合**；R13 编排已启动、九个 R13 功能分支在途未合入）
> 审计日期：2026-08-28 · Node 22.14.0 · worktree `cursor/r13-module-audit-9f67`（干净树，门禁实跑）
> 方法：沿用 R10–R12 审计 §1 的「洪恩真实体验深度」五维杆（E1 看到 / E2 听到 / E3 摸到 / E4 家长 / E5 真机），对 R12 合入后的每个 ◐ 逐项复验一手证据，回答四个问题：**R12 把缺口收窄了多少、R12 闭合后孩子摸到的还差什么、R13 在途杆对哪一格、R13 落地后还剩什么归 R14**。
> **结论先行**：探针口径满盘（`check:round12` 本机实跑 **8/8 exit 0**；`check:round11` / `check:round10` **8/8 exit 0** 不退化）；`check:round13` 基线 **2/8 exit 1**（H6 Android 模拟 + H8 链式绿——比 ROUND13-BRIEF 宣告的 1/8 多一格，因 `7bc74c7` 已合入 VM 双 APK + android-sim 首跑）。体验口径 **✅25 / ◐6 / ❌0**：R12 按八条深度债逐项兑现后，**M-M1 对标口径回 ✅**（34/34 开练 + 采纳率/lift 字段进 progress 导出）；其余 6 个 ◐ 成色**再次全部变化**——模型落库、OCR 矩阵、harness A 段、105 页 scene、13/13 旋律、mobile LH、Kokoro TTS 试点、Android 模拟首条证据均已到位，但孩子当场能感知的洪恩级差距**每一项都还在或仅收窄半档**（跟读仍录音回放、绘本 105/1121、范唱 1/13 且 Piper 非真人、真机签核仍 NO-GO）。剩余余量与 ROUND13-BRIEF 七条深度债、九个在途功能分支一一对应；R14 尾巴逐项标注 §5.2。

---

## 0. 门禁与关键数据实测（`7bc74c7`，本机实跑，退出码为准）

### 0.1 门禁基线输出（审计快照，verbatim）

**`npm run check:round12`**（exit **0**）

```
  ✓ H1 ASR 落库：files[] 落盘校验 37022120B + R12 落库 Go/No-Go + harness + ROUND12_H1_SMOKE
  ✓ H2 OCR 系统化 10 张 + 授权 10 条 + tier 10 + harness + ROUND12_H2
  ✓ H3 绘本场景铺开 105 页（≥60）+ 渲染接线 + ROUND12_H3
  ✓ H4 儿歌 13/13（音频 13）+ 范唱试点 + ROUND12_H4
  ✓ H5 推荐度量 + 开练 34 节点覆盖 + ROUND12_H5_SMOKE
  ✓ H6 evidence/r12 mobile LH 2 份（P≥95）+ 真机通道定案文档
  ✓ H7 TTS 试点（true）或 商店提交演练 + R12 反馈运行（true）
  ✓ H8 Round 11 门禁 8/8 无退化

Round 12 全量落地门禁：8/8 项通过，0 项失败。
```

**`npm run check:round13`**（exit **1**，基线 **2/8**，H6+H8 绿——`7bc74c7` 已合入 android-sim 首跑，非简报模板 1/8）

```
  ✓ H6 Android 模拟：双 APK + android-sim 报告 + ROUND13_H6
  ✓ H8 Round 12 门禁 8/8 无退化

  ✗ H1 ASR 未放行：available=false，freeze=false，files=true，marked=false
  ✗ H2 OCR Android 未闭环：sim=true，reflux=false，marked=false
  ✗ H3 绘本未终局：scenePages=105/200，marked=false
  ✗ H4 范唱未批次：vocal=1/3，marked=false
  ✗ H5 lift 未闭环：exp=false，smoke=false
  ✗ H7 商店实提未闭环：submit=false

Round 13 终局门禁：2/8 项通过，6 项失败。
说明：R13 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。
```

| 门禁 | 退出码 | 结果 | 说明 |
|---|---|---|---|
| `check:round10` | **0** | **8/8** | R12 H8 链式兜底，本机复跑无退化 |
| `check:round11` | **0** | **8/8** | R11 集成闭合 |
| `check:round12` | **0** | **8/8** | R12 全量落地闭合；见上 verbatim |
| `check:round13` | **1** | **2/8** | H6 因 `7bc74c7` android-sim 已绿；H1–H5/H7 对应 R13 在途分支 |
| `npm test` | **0** | 全链 exit 0 | 识字 164 路由 + 41 交互 0 问题；数学 20 路由 + 36 交互 0 问题；OCR 精度子链 43/44 项（99.0% 召回，1 项边界 FAIL 不阻断总链） |

### 0.2 内容水位（`node --input-type=module` + 探针 import + 实读，一手数字）

| 指标 | 本轮实测（`7bc74c7`） | 与 R12 审计基线（`7c2e6e7`）对照 |
|---|---|---|
| 识字字库 / 单元 | **1820 字 / 99 单元** | = |
| 分级绘本 | **132 本 / 1121 页**；**scene 页 105 / 17 本**（`BookPageScene.vue` 接线） | 20 → **105** 页（R12 H3 超额探针杆） |
| 儿歌 | **13 首 / 52 句**；**13/13 挂静态 `.ogg` 旋律**；**范唱人声 ref 1 首**（sg5 Piper 试点） | 8 → 13 旋律；范唱 0 → 1 |
| 字源 / 形近 / 成语 / 古诗 / 单元剧情 / 徽章 | 808 / 1817 / 60 / 24 / 99 / 11 | = |
| 应用题母题 | **214 个** | = |
| 技能图谱 | **34 节点 / 30 边**；`canDailyFocus` **10/34** + `PLANET_SKILL_TARGETS` **24/34** → **`practiceCoverage().covered=34`**；`recommendationMetrics` 进 progress 导出 | 10/34 → **34/34 开练**（R12 H5）；度量字段 R12 新增 |
| OCR real tier | **10 张** CC 去重 PNG（≥4KB+魔数）；`real-samples.json` 授权 **10 条** + **tier 10** | 6 → 10 张 |
| ASR manifest | **`files[]` 7 文件 / 35.31 MiB 逐文件 sha256  verified**；`available:false`；`freezeChecklist` **10 条** + R12 ship **NO-GO** | files=[] → **落库闭合** |
| 数学 mobile LH | literacy **P 97** / math **P 95**（`evidence/r12/*-mobile.json`） | R11 趋势 → **R12 原始 JSON 落盘** |
| Android 模拟 | `evidence/r13/android-sim/report.json`：`simulated:true`；双 APK sha256；识字 smoke **164** 路由 / 数学 **20** 路由；OCR A 段 **pass** | **新增**（`7bc74c7`） |
| X1 TTS 试点 | Kokoro《静夜思》4 句 Opus **33KB** + 离线链 + 系统 TTS 回退 | 文档 → **随包资产**（R12 H7） |

### 0.3 R12 交付物一手复测（不只查存在，实际读/跑）

| 项 | 实测 | 说明 |
|---|---|---|
| 跟读 ASR | **35.31 MiB 落库**；`test:asr:engine` 可解中文；**`available:false`**；manifest note 明确 F4/F7 未闭合 | 工程/Product 化半档；**孩子点「我来读」仍录音回放 + 响度分** |
| OCR 矩阵 | **10 张 real + tier 10**；精度 **99.0%**（10 张 real）；`test-ocr-device.mjs` **A 段 VM 可跑绿** | B 段 adb 仍 SKIP；android-sim 已跑 A 段，**不等于 E5 真机拍照** |
| 绘本 scene | **105 页 / 17 本**；高频单元样板区显著扩大 | 仍 **1016/1121 页**旧表现力；翻出 17 本即感知边界 |
| 儿歌 | **13/13 旋律**；sg5 **Piper「啦」音范唱试点** 75KB | 音色仍合成/ Piper；**中文歌词真人范唱 0** |
| 推荐度量 | `progress.js` **`adoptionRate`/`recoLift`/`recommendationCohorts`**；导出含 `recommendationEffect`；**观察性 cohort 对照，非准实验** | E4 对标 + E3 34/34 闭合；**因果 lift 仍 R13 H5** |
| mobile LH + 定案 | P **97/95**；`r12-android-device-decision.md` **三选一 → 发布 NO-GO** | Web 仿真档闭合；**`evidence/r12/android/` 仍空** |
| TTS 试点 | 《静夜思》离线 Opus 可播 + smoke 回退链 | 单 poem 试点；字卡/全库仍 X1 |
| Android 模拟 | 双 APK 构建 + android-sim 报告 **`simulated:true`** | 解 **NO-GO 前工程验证**；**不得冒充真机签核** |

---

## 1. 口径说明：这一轮复审在验什么

R12 审计把杆从「R11 产品化/样板」抬到「R12 全量落地/矩阵/落库」。本轮 R12 已合入且 `check:round12` 8/8，复审回答的是：**按 R12 简报杆交付之后，五维上孩子和家长真实摸到的东西变了没有**。判定规则不变：与洪恩存在孩子当场能感知的差距、且不是设计取舍的合理代价，记 ◐；E2 合成语音仍作横切债 X1 统一记账（试点改善听感上限但不逐项 flip）。

R13 九个功能分支在途未合入，`check:round13` 2/8 是预期基线红（H6 已因 android-sim 首跑占一格）——本轮不预支在途分支交付，只审 **`7bc74c7` HEAD** 上摸得到的。

---

## 2. 识字 App 复审（L-M1 … L-M15）

图例：✅ 体验深度达标 / ◐ 探针绿但体验深度未到洪恩 / ❌ 未实现。非 ◐ 项本轮抽查无退化，只列结论。

| 模块 | 洪恩能力 | 体验 | R12 后现状与证据 | 归属 |
|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ✅ | 1820 字/99 单元实测维持 | 维护 |
| L-M2 | 认-读-写-玩闭环 | ✅ | PHASES 状态机维持；古诗试点 Kokoro，其余范读仍记 X1 | 维护 + X1 |
| L-M3 | 笔顺+描红判定 | ✅ | hanzi-writer 真笔顺 + 双无障碍出口维持 | 维护 |
| L-M4 | 听音识字+形近干扰 | ✅ | 1817 组双接线维持 | 维护 |
| L-M5 | 130 本分级绘本 | **◐** | **R12 收窄一档：105 页多元素 scene / 17 本** + 渲染接线 + `ROUND12_H3`。**未动的**：**1016/1121 页**仍是单 emoji + TTS；高频外仍「旧样子」 | **R13 #6 在途**（≥200 scene）；R14 见 §5.2-4 |
| L-M6 | 800+ 字源互动 | ✅ | 两帧真演变 + reduced-motion 契约维持 | 维护 |
| L-M7 | 记忆曲线复习 | ✅ | FSRS-lite + 透明调度维持 | 维护 |
| L-M8 | 成语/古诗国学 | ✅ | 60+24 维持；《静夜思》离线 TTS 试点，其余朗读记 X1 | 维护 + X1 |
| L-M9 | AI 学伴/跟读评测 | **◐** | **R12 收窄（工程侧）：35.31 MiB 落库 + sha256 + 引擎回归 + R12 ship NO-Go 表**。**未动的**：`available:false`（实查 manifest），**孩子体验与 R10/R11 相同** | **R13 #4 在途**（冻结集≥50 + RTF）；R14 见 §5.2-1 |
| L-M10 | 拍照识字 | **◐** | **R12 收窄：10 张 real + tier + A 段 harness + 99% 精度**；android-sim OCR A 段 PASS。**未动的**：**E5 真机端到端零签核**；无用户实拍回流；B 段 adb SKIP | **R13 #5 在途**（Android 模拟闭环 + 回流设计）；R14 见 §5.2-2 |
| L-M11 | 动画儿歌/IP | **◐** | **R12 收窄：13/13 旋律 + sg5 Piper 范唱试点**。**未动的**：旋律仍加法合成；**真人中文范唱 0**；无 MV/IP 演出 | **R13 #7 在途**（≥3 范唱批次）；R14 见 §5.2-3 |
| L-M12 | 小游戏 ≥5 | ✅ | 6 款维持 | 维护 |
| L-M13 | 家长控制/防沉迷 | ✅ | 口算门 + 导出导入 + 时长维持 | 维护 |
| L-M14 | 奖励/徽章 | ✅ | 11 枚 + dailyQuest 维持 | 维护 |
| L-M15 | 性能/无障碍/离线 | **◐** | **R12 收窄：mobile LH 97/95 + 路由预算 + NO-GO 定案**；**R13 基线 H6：android-sim 双 APK + 164/20 smoke**。**未动的**：**真机签核仍 NO-GO**；`evidence/r12/android/` 空 | **R13 #9 在途**（harness 深化）；R14 见 §5.2-6 |
| L-M16 | — | — | （识字无 M-M16 对应项） | — |

**识字小计（体验口径）：✅ 10 / ◐ 5 / ❌ 0**（计数同 R11/R12 审计，5 个 ◐ 全部再收窄）

---

## 3. 数学 App 复审（M-M1 … M-M16）

| 模块 | 洪恩能力 | 体验 | R12 后现状与证据 | 归属 |
|---|---|---|---|---|
| M-M1 | L1–L5 年龄档 + 技能图谱 | **✅** | **R12 对标闭合：34/34 `practiceEntry` 覆盖**（daily 10 + planet 24）；周计划 + 采纳痕迹（R11 E4）；**`recommendationMetrics` 进导出**（观察性 cohort lift）。文档自承非随机对照——**超越线准实验仍 R13** | 维护；**超越线 → R13 #8** |
| M-M2 | 1000+ 互动/无限题 | ✅ | mulberry32 + questionId 维持 | 维护 |
| M-M3 | 185 应用题母题 | ✅ | 214 个维持 | 维护 |
| M-M4 | 数感/比较/运算 | ✅ | 四路由 + 3000 道维持 | 维护 |
| M-M5 | 几何/空间+七巧板 | ✅ | 维持 | 维护 |
| M-M6 | 逻辑/规律+配对/迷宫 | ✅ | 内容门禁维持 | 维护 |
| M-M7 | 数独专项 | ✅ | 4/6/9 三档唯一解维持 | 维护 |
| M-M8 | 数形结合演示 | ✅ | 8 类三段契约维持；表现力密度记 X2 | 维护 + X2 |
| M-M9 | 自适应难度 | ✅ | 弱项 + 错题优先维持 | 维护 |
| M-M10 | 错题本 | ✅ | questionId 级维持 | 维护 |
| M-M11 | 计算专题/速算 | ✅ | sprint + 竖式维持 | 维护 |
| M-M12 | 剧情地图+日冒险 | ✅ | 章节契约 + 全图谱专项入口 | 维护 |
| M-M13 | 互动教具 ≥3 | ✅ | 计数/数轴/分与合维持 | 维护 |
| M-M14 | 家长面板 | ✅ | 口算门 + 雷达 + 错因 + 导出；推荐理由并 M-M1 | 维护 |
| M-M15 | 奖励/成就 | ✅ | 18 项维持 | 维护 |
| M-M16 | 性能/无障碍/离线 | **◐** | 同 L-M15：desktop LH 100 落袋、mobile 97/95、android-sim 工程证据；**真机 E5 仍零签核** | **R13 #9 在途**；R14 见 §5.2-6 |

**数学小计（体验口径）：✅ 15 / ◐ 1 / ❌ 0**（**M-M1 自 R12 审计预判 flip ✅**）

---

## 4. 总览：7◐ 复验 — 计数 -1，成色再变

| 口径 | ✅ | ◐ | ❌ | 说明 |
|---|---|---|---|---|
| 探针口径 | **31** | 0 | 0 | `check:round12` 8/8 + `check:round11` 8/8 + `check:round10` 8/8 + `npm test` 全链（`7bc74c7` 实跑） |
| **体验口径（E1–E5 杆）** | **25** | **6** | **0** | 6 个 ◐ = L-M5/L-M9/L-M10/L-M11/L-M15 + M-M16；**M-M1 对标回 ✅** |

**7◐ 复验台账**（对照 R12 审计 §4 同名单 + 本轮一手证据）：

| ◐ 模块 | R11 后（R12 审计原话） | R12 后（本轮一手证据） | 收窄评级 | 本轮判定 |
|---|---|---|---|---|
| L-M9 | harness 可跑；体验仍不变 | **35.31 MiB 落库 + 引擎解中文**；**体验仍不变** | 半（工程） | **仍 ◐** |
| L-M10 | 6 张 + 话术 | **10 张 tier + 99% + harness A + sim OCR pass** | 一档 | **仍 ◐（E5）** |
| L-M11 | 8/13 合成 | **13/13 旋律 + 1 Piper 范唱** | 一档 | **仍 ◐（E2）** |
| L-M5 | 20 页 scene 样板 | **105 页 / 17 本 scene** | **一档+（E1 可见面扩大）** | **仍 ◐** |
| M-M1 | 10/34 + 无 lift | **34/34 开练 + cohort lift 字段** | **对标闭合** | **→ ✅** |
| L-M15/M-M16 | 趋势文档；真机零 | **mobile LH JSON + NO-GO 定案 + android-sim** | 半（Web+工程模拟） | **仍 ◐（E5）** |
| X1（横切） | 零试点 | **《静夜思》Kokoro 4 句** | 试点侧 | 横切改善，不 flip 模块 |

**对齐性检查**：6 个 ◐ 的剩余余量与 ROUND13-BRIEF 七条深度债、分支 #4–#10 一一对应，零悬空（X1→#4/#7、发布→#10、其余见 §5.1）。

---

## 5. 仍 ◐ 的项与 R13 杆 / R14 尾巴（本审计核心交付）

前提口径：下表「R13 在途杆」照抄 ROUND13-BRIEF 硬门槛；**R13 落地后预判**假定九分支按杆合入且 `check:round13` 8/8 之后的体验口径预判；「R14 尾巴」是那之后仍然剩下的部分。

### 5.1 逐项 R13 归属

| # | 模块 | R12 后现状（`7bc74c7` 一手） | R13 在途杆（分支） | R13 落地后预判 | **R14 尾巴（仍剩什么）** |
|---|---|---|---|---|---|
| 1 | L-M9 跟读 | 35.31 MiB 落库；`available:false`；F4/F7 卡死 | 儿童冻结集 **≥50 条实体** 或 `available:true`+PASS + `ROUND13_H1`（#4） | **仍 ◐ 或边界 ✅**——50 条骨架 + RTF 后，**300 条双标注 + 噪声集阈值**决定 flip | **300 条儿童冻结集实录双标注**；低端 Android RTF/五类故障 device 腿；声调声学级验证；模型换版横比治理 |
| 2 | L-M10 OCR | 10 张 tier + A 段绿 + sim OCR pass | android-sim OCR 段 PASS + 回流设计 + `ROUND13_H2`（#5） | **仍 ◐（E5 真机）**——模拟闭工程链，**adb B 段 + 用户实拍**仍须 QA | 用户实拍失败样本回流回归集；WebView 相机权限三路径长稳；wasm OCR 低档机耗时边界 |
| 3 | L-M11 儿歌 | 13/13 合成旋律 + 1 Piper 范唱 | **≥3 首**范唱人声 + `ROUND13_H4`（#7） | **仍 ◐（E2 听感）**——3 首批次 ≠ 洪恩级全库真人演播 | 全曲 **真人演播批次**；角色动画 MV；IP 化周边 |
| 4 | L-M5 绘本 | 105/1121 scene（17 本） | scene **≥200** + `ROUND13_H3`（#6） | **仍 ◐**——200 页 ≠ 全库 | **132 本全库场景化**分批；X1 朗读音质；外部真投稿端到端演练 |
| 5 | M-M1 推荐（超越线） | 对标 ✅；观察性 lift | 准实验/对照口径 + `ROUND13_H5_SMOKE`（#8） | **超越线文档闭合**；对标维持 ✅ | **A/B 或准实验因果推断**；采纳率报表趋势；推荐策略自迭代 |
| 6 | L-M15 / M-M16 | mobile LH + NO-GO + android-sim 首跑 | 双 APK 报告深化 + `ROUND13_H6`（#9，基线已部分绿） | **仍 ◐ 直至真机签核**——sim 只解 NO-GO 前工程验证 | **`evidence/r*/android/` 真机首条证据**；低档机每轮回归；mobile P 下行止血 |
| 7 | X1 合成语音 | 《静夜思》Kokoro 试点 | 第二批离线 TTS/真人朗读 ≥1 模块（#4/#7 交叉） | 横切改善；字卡/古诗听感上限抬升 | **1800 字分批真人录音**；Piper/VITS 家长主动下载包（三道门过） |
| 8 | 发布/分发 | R12 提交演练 + FEEDBACK-LOOP R12 标记 | 真实提交/内测轨道 + `ROUND13_H7`（#10） | **流程闭合**——内测 ≠ 上架 | 生产商店提交 + 第一批真实用户反馈 issue；多浏览器/真机浏览器矩阵 |

### 5.2 横切体验债（R13 执行级 → R14）

| # | 债 | R12 后现状 | R13 在途 | **R14 归属** |
|---|---|---|---|---|
| **X1** | 合成语音 vs 真实录音 | 1 poem Kokoro；儿歌仍合成/Piper | 第二批试点 + 范唱批次 | 见 §5.1-7 |
| **X2** | 美术表现力密度 | 105 页 scene | ≥200 页 | 全库 + GSAP 演出点增密 |
| **X3** | 真机是体验的地基 | NO-GO 定案 + **android-sim `simulated:true`** | harness 深化 | 定案后 **真机 `evidence/r*/android/`**；sim 永不等价签核 |

### 5.3 流程债（R12 遗留，R13 编排内清）

| # | 债 | 证据 | 动作 |
|---|---|---|---|
| P1 | `acceptance-log-round12.md` §2 量化格仍大量 `[待填]` | 实查全文 | R13 编排终验回填 |
| P2 | `acceptance-log-round13.md` 仍为模板 | 实查 | R13 集成后按 §0 verbatim 回填 |
| P3 | R12 手动走查 W1–W6 未勾 | acceptance-log-round12 §4 | R13 终验勾选 |
| P4 | `check:round13` 基线 **2/8** 与简报 **1/8** 文案差 | H6 已在 `7bc74c7` 绿 | 更新 ROUND13-BRIEF / ACCEPTANCE 基线表述 |

---

## 6. `check-round13.mjs` v1.1 收紧建议（给 #3 验收子代理）

通读 v1.0 全文（233 行，`7bc74c7` 基线实跑 **2/8**）+ ROUND13-BRIEF 硬门槛，以下建议供 #3 终稿时采纳。**负向实测原则**：每条建议须附「基线 v1.0 恒真/可骗过 → v1.1 负向样例转红」取证句。

### 6.1 相对 v1.0 必堵

| # | 探针 | v1.0 漏洞 | v1.1 收紧要点 | 基线负向取证 |
|---|---|---|---|---|
| 1 | H1 | `freezeOk` 只查 doc 字数 + 「≥50」regex，**不计 JSON 条目**；`filesOk` 只查 `files.length≥1` **无 sha256**；`available\|\|freezeOk` 可只 flip 布尔 | 冻结集须 **`asr-eval-set.json` 或等价 JSON ≥50 条可解析实体**；files 沿用 R12 **逐文件 sha256 + ≤60MiB**；若 `available:true` 须 **Go/No-Go PASS 实体 + `ROUND13_H1` harness 跑分** | v1.0：`freeze=false, files=true, marked=false` |
| 2 | H2 | `simOk` 只读 `report.json` 的 `ocr.pass`——**手填 JSON 可骗**；`refluxOk` doc>400 词表；`marked` 只查 `ROUND13_H2` 字面 | 须 **spawn `android-sim.mjs` 或校验 report 与 `steps[]`/`commit` 一致**；回流 doc 须 **Issue 模板 + 字段表 + `ROUND13_H2`**；OCR 段须与 **harness A 段 exit 0 交叉验证** | v1.0：`sim=true, reflux=false, marked=false`（sim 已从 android-sim 来，但缺回流/mark） |
| 3 | H3 | 只数 scenePages≥2，**不查渲染/质量**（R12 H3 v1.0 同款） | ≥200 + **`BookPageScene.vue` 消费信号** + scene 元素 **`type`/`id` 非空** spot-check 3 页 + `ROUND13_H3` | v1.0：`scenePages=105, marked=false` |
| 4 | H4 | `vocalFiles` ≥8192B **无魔数**；只认 `songs.js` vocal 字段 | ≥3 首 **OggS/RIFF 魔数抽验** + 去重路径；须 **非 Piper-only 文档**（≥1 首标 `humanStudio:true` 或授权演播 doc）+ `ROUND13_H4` | v1.0：`vocal=1/3` |
| 5 | H5 | `expOk` 池拼接 `progress.js`（**R12 观察性字段即过**）；无 smoke 行为断言 | 准实验 doc 须 **对照组/干预组/混杂声明** 三节；metrics **排除** R12 cohort 观察性定义重复充数；须 **`ROUND13_H5_SMOKE` 导出 JSON 含 `experimentDesign`** | v1.0：`exp=false, smoke=false` |
| 6 | H6 | `simOk` 只验 JSON 字段——**可伪造 apkSha256**；基线已绿须防退化 | 须 **`gradlew assembleDebug` 日志存在** 或 report.steps 含 gradle 步且 **SHA256 与 APK 文件现核**；`simulated:true` **强制**；识字 routes **≥164**、数学 **≥20**；禁止 `evidence/r12/android/` 路径冒充 | v1.0：H6 已绿——负向：**删 APK 只留 JSON → FAIL** |
| 7 | H7 | doc>600 + 关键词即过 | 须 **Play Console / TestFlight 截图或 ticket id** + 构建 SHA + **`ROUND13_H7`**；区分「演练 doc」与「实提 record」 | v1.0：`submit=false` |
| 8 | H8 | 只 spawn `check-round12` + `/8\/8/` | 维持链式；建议 **stderr 捕获退化项 id**；JSON 增 **`baseline:'7bc74c7'`** | — |

### 6.2 审计新增建议（v1.1 草案应覆盖）

9. **H1 RTF 腿**：`test-asr-engine.mjs` 或 R13 等价脚本输出 **`androidRtf` 或 `rtfSimulated`** 字段；`simulated:true` 须标注且 **不得单独 flip `available:true`**。

10. **H1 `available:true` 短路禁令（继承 R12）**：flip 时 **`files[]` verified≥1 + quietCharRecall 实测非 simulated**。

11. **H2 与 H6 交叉**：H2 OCR pass 须 **引用同一份 `report.json` commit SHA** 与 H6 一致，防分支报告拼贴。

12. **H3 高频单元覆盖**：除 200 页总数外，要求 **≥5 个单元各 ≥10 scene 页**（防单书堆页）。

13. **H4 范唱与旋律解耦**：范唱资产不得与 melody `.ogg` **同路径**；须独立 `vocalAudio` ref。

14. **H5 报表趋势腿**：`progress` 导出或 R13 doc 含 **≥2 个时间窗口的 adoptionRate 序列**（防单点快照）。

15. **H6 权限/离线静态断言**：`android-sim.mjs` 须 assert **CAMERA 权限声明 + SW OCR 缓存键**（继承 OCR A 段关键条）。

16. **H7 与 R12 演练解耦**：`r12-store-submission-drill.md` **不得**充当 H7 pass；须新 `r13-store-submission-record.md`。

17. **meta 自检**：`results.length === 8`；`--json` 增 **`probeVersion:'1.1'`**、`expectedBaseline:'2/8'`（`7bc74c7`）。

### 6.3 建议 #3 交付时附带的负向测试包

| 探针 | 负向样例 | 期望 |
|---|---|---|
| H1 | 只在 freeze doc 写「≥50 条」无 JSON | FAIL freeze |
| H2 | 手填 `report.json` 无对应 android-sim 步骤 | FAIL sim |
| H3 | 200 页 scene 但删 BookPageScene.vue | FAIL render |
| H4 | 3 份 Piper 合成范唱无 `humanStudio` 标记 | FAIL vocalQuality |
| H5 | 复用 R12 `r12-reco-metrics.md` 观察性定义 | FAIL exp |
| H6 | JSON 写 simulated:false | FAIL honesty |
| H7 | 仅 R12 drill 文档 | FAIL submit |

---

## 7. 审计方法备注

- 门禁实跑：`/workspace` @ **`7bc74c7`** 干净树 · `check:round12` **exit 0（8/8）** · `check:round13` **exit 1（2/8，预期基线红）** · `check:round11` / `check:round10` **exit 0（8/8）** · `npm test` **exit 0**（识字 164+41、数学 20+36 全绿）。
- 一手计数：`books.js` import → scenePages=105/booksWithScene=17；`songs.js` → 13 首/13 audio/1 vocal ref；OCR fixtures → 10 real PNG；`manifest.json` → files=7/35.31MiB/available=false；`evidence/r13/android-sim/report.json` → simulated:true/ocr.pass:true。
- 体验走读：`r12-followread-ship.md`、`r12-android-device-decision.md`、`r12-reco-metrics.md`、`r12-tts-pilot.md`、`r12-songs-vocal-pilot.md`、`android-sim.mjs`、`check-round13.mjs` v1.0 全文、ROUND13-BRIEF。
- 未重测：OCR B 段 adb、Lighthouse 新跑、axe/zip 全量；R13 在途分支交付质量不在本轮范围（合入后由 #3 探针 v1.1 与编排终验把关）。
