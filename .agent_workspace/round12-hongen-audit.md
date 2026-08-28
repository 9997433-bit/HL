Model slug: claude-fable-5
# Round 12 · 洪恩模块对标审计（R11 闭合后体验口径复审）

> 审计人：Round 12 子代理 #2（fable）
> 审计基线：集成线 `cursor/openmoji-integration-9f67` @ **`7c2e6e7`**（R11 工程门禁 **8/8 闭合**；R12 编排已启动、八个 R12 功能分支在途未合入）
> 审计日期：2026-08-28 · Node 22.14.0 · worktree `cursor/r12-module-audit-9f67`（干净树，`npm ci` 后实跑）
> 方法：沿用 R10/R11 审计 §1 的「洪恩真实体验深度」五维杆（E1 看到 / E2 听到 / E3 摸到 / E4 家长 / E5 真机），对 R11 合入后的每个 ◐ 逐项复验一手证据，回答四个问题：**R11 把缺口收窄了多少、R11 闭合后孩子摸到的还差什么、R12 在途杆对哪一格、R12 落地后还剩什么归 R13**。
> **结论先行**：探针口径维持满盘（`check:round11` 本机实跑 **8/8 exit 0**；`check:round10` **8/8 exit 0** 不退化）；体验口径**计数不变，仍 ✅24/◐7/❌0**，但 7 个 ◐ 的成色**再次全部变化**——R11 按简报杆（清单/样张/20 页/8 首/预算/评估）逐项兑现，每个 ◐ 从「余量明确」推进到「敢上/能测/有样板」，其中 **M-M1（家长侧理由+采纳痕迹已闭合）** 与 **L-M5（20 页多元素场景样板）** 收窄一档。剩余余量与 ROUND12-BRIEF 八条深度债、八个在途功能分支一一对应，零悬空；R12 之后的尾巴逐项标注 R13 归属（§5.1）。

---

## 0. 门禁与关键数据实测（`7c2e6e7`，本机实跑，退出码为准）

### 0.1 门禁基线输出（审计快照， verbatim）

**`npm run check:round11`**（exit **0**）

```
  ✓ H1 跟读产品化：冻结清单 + Go/No-Go 实体 + 评测集实体 + ROUND11_H1_SMOKE
  ✓ H2 OCR 实拍矩阵 6 张（去重）+ 授权清单 6 条 + 失败话术 + ROUND11_H2
  ✓ H3 推荐周计划（数据/图谱侧）+ 家长侧理由/采纳 + ROUND11_H3_SMOKE
  ✓ H4 绘本多元素场景 20 页（scene ≥2 元素）+ 渲染接线 + ROUND11_H4
  ✓ H5 儿歌真实旋律 8 首（public 资产存在且 ≥10KB，去重）+ ROUND11_H5
  ✓ H6 evidence/r11 有效证据 1 份 + 路由预算实体（script=true/doc=true）
  ✓ H7 离线 TTS 评估（true）或 商店清单 + 反馈回路（false）已交付实体
  ✓ H8 Round 10 门禁 8/8 无退化

Round 11 体验门禁：8/8 项通过，0 项失败。
```

**`npm run check:round12`**（exit **1**，基线 **1/8**，仅 H8 绿——与 ROUND12-BRIEF 宣告一致）

```
  ✓ H8 Round 11 门禁 8/8 无退化

  ✗ H1 ASR 未落库：files=false，available=false，gonogo=true，marked=false —— r12-literacy-asr-ship
  ✗ H2 OCR 未系统化：real=6/8，tier=false，harness=false，ROUND12_H2=false —— r12-literacy-ocr-device
  ✗ H3 绘本未铺开：scenePages=20/60，ROUND12_H3=false —— r12-literacy-books-rollout
  ✗ H4 儿歌未全库：songs=13/13，audio=8/13，vocal=false，ROUND12_H4=false —— r12-literacy-songs-vocal
  ✗ H5 推荐度量未闭环：metrics=false，coverage=false，smoke=false —— r12-math-reco-metrics
  ✗ H6 真机/LH 未闭环：mobileLh=0/2，device=false —— r12-perf-device-lh
  ✗ H7 TTS/发布未闭环：tts=false，release=false，feedbackRun=true —— r12-tts-release-drill

Round 12 全量落地门禁：1/8 项通过，7 项失败。
说明：R12 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。
```

| 门禁 | 退出码 | 结果 | 说明 |
|---|---|---|---|
| `check:round10` | **0** | **8/8** | R11 H8 链式兜底，本机复跑无退化 |
| `check:round11` | **0** | **8/8** | R11 集成闭合；见上 verbatim |
| `check:round12` | **1** | **1/8** | 仅 H8 绿；H1–H7 逐条对应 R12 在途分支 |
| `npm test` | **0** | 全链 exit 0 | 识字 164 路由 + 36 交互 0 问题；数学 20 路由 + 34 交互 0 问题（`7c2e6e7` 干净树实跑） |

### 0.2 内容水位（`node --input-type=module` + 探针 import，一手数字）

| 指标 | 本轮实测（`7c2e6e7`） | 与 R11 审计基线对照 |
|---|---|---|
| 识字字库 / 单元 | **1820 字 / 99 单元** | = |
| 分级绘本 | **132 本 / 1121 页**；**scene 页 20 / 3 本**（b1/b10/b14，`BookPageScene.vue` 接线） | 0 → 20 页（R11 H4） |
| 儿歌 | **13 首 / 52 句**；**8 首挂静态 `.ogg` 资产**（28–30KB，合成渲染管线） | 3 → 8 首 |
| 字源 / 形近 / 成语 / 古诗 / 单元剧情 / 徽章 | 808 / 1817 / 60 / 24 / 99 / 11 | = |
| 应用题母题 | **214 个** | = |
| 技能图谱 | **34 节点 / 30 边**；`canDailyFocus` **10/34**；`practiceEntry()` daily 10 / planet 24 | 家长侧空白 → 周计划+采纳面板（R11 H3） |
| OCR real tier | **6 张** CC BY-SA 去重 PNG（≥4KB+魔数）；`real-samples.json` 授权 **6 条** | 3 → 6 张 |
| ASR manifest | `available:false`、`files:[]`；`freezeChecklist` **10 条** + Go/No-Go **NO-GO** | 5 → 10 条清单 |
| 数学 mobile LH 趋势 | `evidence/r11/math-lighthouse-trend.json`：R8→R9 P **0.99→0.98**（-1pp，仍 ≥0.95） | R11 H6 新增 |
| 桌面 LH | `evidence/r10/` 双 App **100/100/100**（R10 已定标） | = |

### 0.3 R11 交付物一手复测（不只查存在，实际读/跑）

| 项 | 实测 | 说明 |
|---|---|---|
| 跟读 Go/No-Go | **NO-GO**（15 处未达标）；harness **24/24 + 7 场故障演练**；`precacheModelBytes=0` smoke 实测 | 模型零字节，`available:false`——孩子体验与 R10 相同（录音回放+响度分） |
| OCR 失败话术 | `CameraOcrView.vue` 三种失败共用卡片 + 低光/取景/换一张三条指引（ROUND11_H2 注释） | 比 R10「换一张」通用出口收窄；**仍无按 OCR 引擎错误码分支** |
| 周计划 + 家长采纳 | `week-plan.js` + `ParentView.vue`「推荐理由与采纳痕迹」面板实查存在；`ROUND11_H3_SMOKE` 在 math smoke | E4 对标缺口闭合；**无掌握度 lift / 采纳率因果度量**（progress store 无 `recommendationMetrics`） |
| 绘本场景 | 20 页 scene ≥2 元素；`BookPageScene.vue` 渲染接线 | 1/99 单元样板区，翻两页即出区 |
| 儿歌音频 | 8 × `.ogg` 落盘（README 自证加法合成离线渲染） | 音色仍合成；范唱仍 TTS |
| TTS 评估 | `.agent_workspace/r11-tts-evaluation.md`：真人录音首选、Piper/VITS No-Go 首包 | X1 选型文档闭合，**零试点资产** |
| 商店/反馈 | `FEEDBACK-LOOP.md` + `store-checklist` 骨架 | H7 store 腿；**无提交演练、无运行记录** |

---

## 1. 口径说明：这一轮复审在验什么

R11 审计把杆从「R10 spike 是否接线」抬到「R11 产品化/样板是否到位」。本轮 R11 已合入且 `check:round11` 8/8，复审回答的是：**按 R11 简报杆交付之后，五维上孩子和家长真实摸到的东西变了没有**。判定规则不变：与洪恩存在孩子当场能感知的差距、且不是设计取舍的合理代价，记 ◐；E2 合成语音仍作横切债 X1 统一记账不逐项降级。

R12 八个功能分支在途未合入，`check:round12` 1/8 是预期基线红——本轮不预支在途分支的交付，只审 **`7c2e6e7` HEAD** 上摸得到的。

---

## 2. 识字 App 复审（L-M1 … L-M15）

图例：✅ 体验深度达标 / ◐ 探针绿但体验深度未到洪恩 / ❌ 未实现。非 ◐ 项本轮抽查无退化，只列结论。

| 模块 | 洪恩能力 | 体验 | R11 后现状与证据 | 归属 |
|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ✅ | 1820 字/99 单元实测维持 | 维护 |
| L-M2 | 认-读-写-玩闭环 | ✅ | PHASES 状态机维持；范读机器音记 X1 | 维护 + X1 |
| L-M3 | 笔顺+描红判定 | ✅ | hanzi-writer 真笔顺 + 双无障碍出口维持 | 维护 |
| L-M4 | 听音识字+形近干扰 | ✅ | 1817 组双接线维持 | 维护 |
| L-M5 | 130 本分级绘本 | **◐** | **R11 收窄一档：20 页多元素场景样板**——b1/b10/b14 共 20 页 `{scene:[≥2 元素]}` + `BookPageScene.vue` 渲染接线 + `ROUND11_H4` smoke。**未动的**：其余 **1101/1121 页**仍是 `{emoji,text,p}` 单 emoji + TTS；孩子翻出 3 本样板书即感知「这里不一样、那里还是旧样子」 | **R12 #6 在途**（≥60 scene 页）；R13 见 §5.1-4 |
| L-M6 | 800+ 字源互动 | ✅ | 两帧真演变 + reduced-motion 契约维持 | 维护 |
| L-M7 | 记忆曲线复习 | ✅ | FSRS-lite + 透明调度维持 | 维护 |
| L-M8 | 成语/古诗国学 | ✅ | 60+24 维持；朗读记 X1 | 维护 + X1 |
| L-M9 | AI 学伴/跟读评测 | **◐** | **R11 收窄（工程侧）：冻结清单 10 条 + Go/No-Go 五层门槛表 + 评测集 36 条骨架 + harness 24/24 + 7 场故障演练**——「敢上模型的路」第一次完整。**未动的**：`files:[]`、`available:false`（实查 manifest），**孩子点「我来读」仍落录音回放 + 响度分封顶 85**，与 R10 体验相同 | **R12 #4 在途**（模型落库 + 儿童冻结集跑分）；R13 见 §5.1-1 |
| L-M10 | 拍照识字 | **◐** | **R11 收窄：6 张 real + 失败话术 UI**——去重 PNG 6/6、授权 6 条、三条指引话术。**未动的**：E5 相机端到端零实测；无光照×角度×纸质结构化 tier；精度脚本本 VM **tesseract wasm 缺失未能重跑**（依赖 `npm ci` 完整树，非回归） | **R12 #5 在途**（≥8 张矩阵 + 真机 harness）；R13 见 §5.1-2 |
| L-M11 | 动画儿歌/IP | **◐** | **R11 收窄：8/13 旋律落静态资产**——`.ogg` 28–30KB，file-first-with-synth-fallback。**必须挑明**：仍是**加法合成离线渲染**，非录音室；范唱仍 TTS；sg9–sg13 五首仍振荡器兜底 | **R12 #7 在途**（13/13 + 范唱人声试点）；R13 见 §5.1-3 |
| L-M12 | 小游戏 ≥5 | ✅ | 6 款维持 | 维护 |
| L-M13 | 家长控制/防沉迷 | ✅ | 口算门 + 导出导入 + 时长维持 | 维护 |
| L-M14 | 奖励/徽章 | ✅ | 11 枚 + dailyQuest 维持 | 维护 |
| L-M15 | 性能/无障碍/离线 | **◐** | **R11 收窄：路由预算 + evidence/r11 趋势冻结**——数学 R8→R9 mobile P 99→98 有数、路由级 gzip 预算脚本进链。**未动的**：**mobile LH 本 VM 未新跑**（`evidence/r12/` 空）；真机维度仍零实测（清单 VM/owner 分账维持） | **R12 #9 在途**（mobile LH + 三选一定案）；R13 见 §5.1-6 |
| L-M16 | — | — | （识字无 M-M16 对应项） | — |

**识字小计（体验口径）：✅ 10 / ◐ 5 / ❌ 0**（与 R10/R11 审计同计数，5 个 ◐ 全部再收窄）

---

## 3. 数学 App 复审（M-M1 … M-M16）

| 模块 | 洪恩能力 | 体验 | R11 后现状与证据 | 归属 |
|---|---|---|---|---|
| M-M1 | L1–L5 年龄档 + 技能图谱 | **◐** | **R11 收窄（E4）：周计划 + 家长侧理由/采纳痕迹闭合**——`week-plan.js` + `ParentView.vue` 面板实查；`ROUND11_H3_SMOKE` 探针绿。**未动的（E3）**：`canDailyFocus` 仍 **10/34**，24 技能「开练」落 planet 首页；**无推荐效果度量**（掌握度 lift / 采纳率因果字段未进 progress store）——洪恩侧「推荐→一键专项」对全图谱更无缝 | **R12 #8 在途**（34 节点覆盖 + 度量实体）；R13 见 §5.1-5 |
| M-M2 | 1000+ 互动/无限题 | ✅ | mulberry32 + questionId 维持 | 维护 |
| M-M3 | 185 应用题母题 | ✅ | 214 个维持 | 维护 |
| M-M4 | 数感/比较/运算 | ✅ | 四路由 + 3000 道维持 | 维护 |
| M-M5 | 几何/空间+七巧板 | ✅ | 维持 | 维护 |
| M-M6 | 逻辑/规律+配对/迷宫 | ✅ | 内容门禁维持 | 维护 |
| M-M7 | 数独专项 | ✅ | 4/6/9 三档唯一解维持 | 维护 |
| M-M8 | 数形结合演示 | ✅ | 8 类三段契约维持；表现力密度记 X2 | 维护 + X2 |
| M-M9 | 自适应难度 | ✅ | 弱项 + 错题优先维持 | 维护 |
| M-M10 | 错题本 | ✅ | questionId 级维持；wrongBook 仍为开练第一优先 | 维护 |
| M-M11 | 计算专题/速算 | ✅ | sprint + 竖式维持 | 维护 |
| M-M12 | 剧情地图+日冒险 | ✅ | 章节契约 + `?focus=` 专项入口（10 技能） | 维护 |
| M-M13 | 互动教具 ≥3 | ✅ | 计数/数轴/分与合维持 | 维护 |
| M-M14 | 家长面板 | ✅ | 口算门 + 雷达 + 错因 + 导出导入；推荐理由已并进 M-M1 | 维护 |
| M-M15 | 奖励/成就 | ✅ | 18 项维持 | 维护 |
| M-M16 | 性能/无障碍/离线 | **◐** | 同 L-M15：desktop LH 100 落袋、真机零实测；R11 补 mobile 趋势文档但 **无 R12 mobile JSON** | **R12 #9 在途**；R13 见 §5.1-6 |

**数学小计（体验口径）：✅ 14 / ◐ 2 / ❌ 0**（与 R10/R11 审计同计数，2 个 ◐ 均再收窄）

---

## 4. 总览：计数不变，成色再变

| 口径 | ✅ | ◐ | ❌ | 说明 |
|---|---|---|---|---|
| 探针口径 | **31** | 0 | 0 | `check:round11` 8/8 + `check:round10` 8/8 + `npm test` 全链（`7c2e6e7` 实跑） |
| **体验口径（E1–E5 杆）** | **24** | **7** | **0** | 7 个 ◐ = L-M5/L-M9/L-M10/L-M11/L-M15 + M-M1/M-M16，**与 R10/R11 审计同名单** |

**为什么计数没动**：R11 简报杆是清单/6 张/20 页/8 首/预算/评估——它把每个 ◐ 从「余量明确」推进到「敢上/能测/有样板」，但按 E1–E5 杆逐项对表，孩子当场能感知的差距**每一项都还在**（跟读还是录音回放、绘本 20/1121、儿歌 8/13 且音色合成、真机还是零、开练 10/34、无 lift 度量）。诚实的记法是维持 ◐、把「收窄量」写进台账：

| ◐ 模块 | R10 后（R11 审计原话） | R11 后（本轮一手证据） | 收窄评级 |
|---|---|---|---|
| L-M9 | 四档全链进码；模型未分发，孩子体验未变 | 10 条 freezeChecklist + Go/No-Go + 36 条评测骨架 + harness 可跑；**体验仍不变** | 半（工程/Product 化） |
| L-M10 | 3 张 92%；无失败话术 | 6 张 + 三条指引话术 UI | 一档 |
| L-M11 | 3/13 静态资产 | 8/13 静态资产；音色仍合成 | 一档 |
| L-M5 | 投稿自动化；页面表现力未动 | 20 页 scene 样板 + 渲染接线 | **一档（E1 可见）** |
| M-M1 | 开练 10/34；家长侧空白 | 周计划 + 采纳痕迹；**仍 10/34 + 无 lift** | **一档（E4 闭合，E3 仍差）** |
| L-M15/M-M16 | desktop 100；真机零 | + 路由预算 + R8→R9 趋势冻结 | 半（Web 侧） |
| X1（横切） | 全线 SpeechSynthesis | TTS 评估文档闭合；**零试点音频** | 文档侧 |

**M-M1 边界说明**：R11 审计 §5.1-5 预判 R11 落地后可回 ✅（对标口径）。本轮复验：**E4（家长理由/采纳）已对标**，但 **E3（10/34 一键专项）仍显著差于洪恩全图谱体验**，且 R12 H5 要求的因果度量未起步——故维持 ◐，余量明确归 R12「超越线」。

**对齐性检查**：7 个 ◐ 的剩余余量与 ROUND12-BRIEF 八条深度债、八个在途功能分支一一对应，零悬空（X1→#10、发布→#10、其余→#4–#9）。

---

## 5. 仍 ◐ 的项与 R12/R13 归属（本审计核心交付）

前提口径：下表「R12 在途杆」照抄 ROUND12-BRIEF 硬门槛；**R12 落地后预判**假定八分支按杆合入且 `check:round12` 8/8 之后的体验口径预判；「R13 尾巴」是那之后仍然剩下的部分。

### 5.1 逐项 R12 归属

| # | 模块 | R11 后现状（`7c2e6e7` 一手） | R12 在途杆（分支） | R12 落地后预判 | **R13 尾巴（仍剩什么）** |
|---|---|---|---|---|---|
| 1 | L-M9 跟读 | freezeChecklist 10 条 + Go/No-Go NO-GO + 评测集 36 条占位 + harness 24/24；**`files:[]`、`available:false`**；孩子仍录音回放 | `files[]` 落盘 sha256 一致（≤60MiB）+ R12 Go/No-Go 更新 + `ROUND12_H1` + 儿童冻结集跑分（#4） | **仍 ◐ 或边界 ✅**——模型落库 + 占位集跑分后，**安静集/噪声集阈值是否真达标**决定能否 flip `available:true`；声调逐字展示仍最远一格 | **300 条儿童冻结集实录双标注**（F4）；低端 Android RTF/真机五类故障复演（F7/F8 device 腿）；声调评分声学级验证；模型换版横比治理 |
| 2 | L-M10 OCR | 6 张 real + 6 条授权 + 失败话术 UI；无结构化 tier；E5 零 | real **≥8** 去重 + 光照/角度/纸质 tier + 真机 harness + `ROUND12_H2`（#5） | **仍 ◐（E5）**——矩阵与 harness 闭「样本层+脚本层」，**真机拍照端到端**仍须 X3 通道 | 用户实拍失败样本回流回归集；Android WebView 相机权限三路径长稳； wasm OCR 低档机耗时边界 |
| 3 | L-M11 儿歌 | 8/13 合成渲染 `.ogg`；sg9–13 振荡器；范唱 TTS | 13/13 音频 + 范唱人声试点 + `ROUND12_H4`（#7） | **仍 ◐（E2 音色）**——13/13 闭合覆盖率，但「洪恩级录音室」听感取决于 X1 试点成色 | 全曲 **真人演播批次**替换合成渲染；角色动画 MV（墨墨出镜）；IP 化周边演出点 |
| 4 | L-M5 绘本 | 20/1121 页 scene（3 本）；其余单 emoji | scene **≥60 页** + `ROUND12_H3`（#6） | **仍 ◐**——60 页 ≠ 全库，高频单元外仍是旧表现力 | **132 本全库场景化**（按表现力/体积比值分批）；X1 朗读音质；外部真投稿端到端演练（R10 自动化已好、未真走一遍） |
| 5 | M-M1 推荐 | 周计划 + 家长采纳痕迹 ✅（E4）；**daily 10/34**；无 lift 度量 | 34 节点开练覆盖 + 效果度量实体 + `ROUND12_H5_SMOKE`（#8） | **可回 ✅（对标口径）**——全图谱一键专项 + 度量进导出后，洪恩可感差距闭合 | **超越线**：lift 因果推断（A/B 或准实验设计）；家长采纳率进报表趋势；推荐策略自迭代 |
| 6 | L-M15 / M-M16 性能 | desktop LH 100；R11 趋势/预算文档；**mobile LH 无 R12 新数；真机零** | `evidence/r12/` mobile LH ≥2 + 三选一定案 + `ROUND12_H6`（#9） | **仍 ◐ 直至 X3 定案执行**——mobile LH 闭 Web 侧；**APK/WebView/触控/音频/温升**仍须真机 owner | 真机矩阵 **每轮低档机回归**常态化；数学 mobile P 若再下行须路由预算止血验证 |
| 7 | X1 合成语音 | R11 TTS 评估：真人录音首选、模型 No-Go 首包；**零试点资产** | TTS 试点（古诗/儿歌 ≥1 条离线链）+ 商店演练（#10） | **横切改善**——试点成功则 L-M2/L-M5/L-M8/L-M11 听感上限抬升；未试点则 X1 原状 | 1800 字分批真人录音批次；可选 Piper/VITS **家长主动下载包**（若三道门过） |
| 8 | 发布/分发 | 商店清单 + FEEDBACK-LOOP 骨架（H7 store 腿） | 提交演练文档 + 反馈回路运行说明 + `ROUND12_H7`（#10） | **流程闭合**——不等于已上架 | 真实商店提交 + 第一批真实用户反馈回流 issue；多浏览器/真机浏览器矩阵（并入 X3） |

### 5.2 横切体验债（R12 执行级）

| # | 债 | R11 后现状 | R12 在途 | **R13 归属** |
|---|---|---|---|---|
| **X1** | 合成语音 vs 真实录音 | 评估文档闭合；8 首儿歌仍是合成渲染；范读/范唱仍 SpeechSynthesis | #10 TTS 试点 | 见 §5.1-7 |
| **X2** | 美术表现力密度 | 20 页 scene 样板 | #6 批量铺开 | 全库 + GSAP 演出点增密 |
| **X3** | 真机是体验的地基 | 诚实化维持；**仍零实测** | #9 三选一定案 | 定案后 **evidence/r*/android/** 首条真机证据；未定案则 L-M9/L-M10/L-M15/M-M16 的 E5 腿永封不了口 |

### 5.3 流程债（R11 遗留，R12 编排内清）

| # | 债 | 证据 | 动作 |
|---|---|---|---|
| P1 | `acceptance-log-round11.md` §2 量化格仍大量 `[待填]` | 实查全文 | R12 编排终验回填；§0 门禁 verbatim 可直接引用 |
| P2 | OCR 精度脚本 VM wasm 缺失 | 本 VM `tesseract-core-relaxedsimd.wasm` ENOENT | `npm ci` 完整性或文档 `[SKIP owner: CI image]` |
| P3 | R11 手动走查 W1–W6 未勾 | acceptance-log-round11 §4 | R12 #3 终验勾选 |

---

## 6. `check-round12.mjs` v1.1 收紧建议（给 #3 验收子代理）

通读 v1.0 全文（301 行，`7c2e6e7` 基线实跑）+ `ROUND12-ACCEPTANCE.md` v1.1 修订草案（`bc90d66` 已部分落地），以下建议供 #3 终稿时采纳或增补。**负向实测原则**：每条建议须附「基线 v1.0 恒真/可骗过 → v1.1 负向样例转红」取证句。

### 6.1 相对 v1.0 必堵（ACCEPTANCE §2 已列，审计复验优先级）

| # | 探针 | v1.0 漏洞 | v1.1 收紧要点 | 基线负向取证 |
|---|---|---|---|---|
| 1 | H1 | `gonogoOk` 回退 `r11-followread-gonogo.md`（含 `available/files[]` → **基线 gonogo=true**）；`filesOk \|\| available` 可只 flip 布尔；`marked` 认 manifest note | 只认 `r12-followread-ship.md`；**逐文件 sha256 实测** + 整包 ≤60MiB；harness 须 `ROUND12_H1` + 跑分信号；smoke 字面 `ROUND12_H1_SMOKE` | v1.0：`files=false, gonogo=true` |
| 2 | H2 | tier 词表在 JSON 注释即过；harness >200 字符空壳；授权仍 6 条 | real **≥8** + samples **≥8 授权** + 每样 **`tier.light`+`tier.angle`+纸质**；harness 须 `assert` + adb/WebView | v1.0：`real=6, tier=false` |
| 3 | H3 | 只数 scenePages，不查渲染 | ≥60 页 + **`BookPageScene.vue` >300B 或 BookReadView scene 消费信号** | v1.0：`scenePages=20` |
| 4 | H4 | `vocalOk` doc>400 或 songs.js 词表 | 范唱 = `public/audio/vocal-pilot/` **≥1 份 ≥10KB** 或 pilot doc >500 + 引擎信号 + `ROUND12_H4` | v1.0：`vocal=false, audio=8/13` |
| 5 | H5 | metrics 池拼接 ParentView（`adoptionRate` 一行即 metrics）；coverage 文档含「34」即过 | metrics **仅** `progress.js` 或 R12 doc（**排除 ParentView 拼接**）；coverage **仅** `skill-practice.js` 实改 + `ROUND12_H5_SMOKE` | v1.0：`metrics=false`；警惕并行 worktree 只改 ParentView 不改 store |
| 6 | H6 | JSON >500B + 文件名含 mobile 即算；无 P 分阈值 | `categories.performance.score ≥ 0.95` + formFactor=mobile；定案 doc 字面 **`ROUND12_H6`** | v1.0：`mobileLh=0` |
| 7 | H7 | 三 AND 与简报 OR 不符；`feedbackRun` **R11 FEEDBACK-LOOP >800 基线恒真** | `H7 = ttsLeg \|\| (releaseOk && feedbackRunR12)`；feedback 须 **R12 更新标记** | v1.0：`feedbackRun=true, release=false` |

### 6.2 审计新增建议（v1.1 草案未覆盖或需加强）

8. **H1 `available:true` 短路禁令（加强）**：即使 v1.1 去掉 OR，仍建议显式断言：若 `available:true` 则 **`files[]` 非空且 verified≥1**，否则 FAIL——防止只改布尔不交字节。

9. **H1 儿童冻结集跑分腿**：除 ship 文档外，要求 `test-asr-eval-set.mjs` 在 `--with-model` 或等价 flag 下 **exit 0** 且 JSON 输出含 `quietCharRecall` 实测值（占位模拟值须标 `simulated:true` 且 **不得**参与 pass）。

10. **H2 OCR 精度回归腿**：spawn `apps/literacy-app/scripts/test-ocr-accuracy.mjs`，断言 real tier 召回 ≥ 基线（R11 约 92%）且输出含 `ROUND12_H2`——防止只堆图不跑精度。

11. **H3 scene 元素质量**：除 ≥2 对象外，要求每页 scene 元素含 **`type` 或 `id` 字段**（非空字符串数组蹭数）；import 后 spot-check 3 页。

12. **H4 音频魔数 + 去重（沿用 R11 H5）**：OggS/RIFF/ID3 魔数抽验；**同一文件路径不得计多歌**；sg9–13 五首降级须 smoke 实测可播（振荡器兜底也算「可播」但须 `ROUND12_H4` 注释声明）。

13. **H5 开练覆盖行为级断言**：对 34 节点逐调 `practiceEntry()`，统计 `kind==='daily'` 数量 **≥34**（或 wrongBook+daily 合计 ≥34）；纯 regex `dailyFocus.*34` 不足。

14. **H5 度量导出腿**：断言 `progress` 导出 JSON schema 含 `recommendationMetrics` 且 **`adoptionRate`/`recoLift` 为 number**——与 ParentView 解耦，防止 UI 硬编码。

15. **H6 双 App mobile LH**：要求 literacy + math **各 ≥1 份** mobile JSON（共 ≥2），防单 App 堆两份。

16. **H7 TTS 试点可播腿**：若走 ttsLeg，要求 `public/audio/tts-pilot/manifest.json` 解析通过 + **≥1 条音频 sha256 一致** + 识字 smoke 含 **`ROUND12_H7_TTS_SMOKE`** 播放断言。

17. **H8 链式深度**：维持 spawn `check-round11`；建议加 **stderr 捕获**打印退化项 id，便于编排日志。

18. **meta 自检**：保持 `results.length === 8`；建议 `--json` 增 **`baseline: '7c2e6e7'`** 与 **`probeVersion: '1.1'`** 字段供 GLOBAL-SUMMARY 聚合。

### 6.3 建议 #3 交付时附带的负向测试包

| 探针 | 负向样例 | 期望 |
|---|---|---|
| H1 | 只改 manifest `note` 写 `ROUND12_H1` | FAIL files |
| H2 | real-samples.json 只在 `$comment` 写 light/angle | FAIL tier |
| H3 | 数据层堆 60 页 scene 但删 BookPageScene.vue | FAIL render |
| H5 | 只在 ParentView 写 `adoptionRate` | FAIL metrics |
| H6 | 空 mobile JSON 501 字节 | FAIL mobileLh |
| H7 | 仅 R11 FEEDBACK-LOOP 不更新 | FAIL feedbackRun |

---

## 7. 审计方法备注

- 门禁实跑：`/workspace` @ **`7c2e6e7`** 干净树 · `check:round11` **exit 0（8/8）** · `check:round12` **exit 1（1/8，预期基线红）** · `check:round10` **exit 0（8/8）** · `npm test` **exit 0**（识字 164+36、数学 20+34 全绿）。
- 一手计数：`books.js` import → scenePages=20/booksWithScene=3；`songs.js` → 13 首/8 audio ref；OCR fixtures → 6 real PNG；`manifest.json` → files=[]/available=false/freezeChecklist 10 条。
- 体验走读：`CameraOcrView.vue`（ROUND11_H2 话术）、`BookPageScene.vue`、`ParentView.vue`（math，周计划+采纳）、`week-plan.js`、`r11-followread-gonogo.md`、`r11-tts-evaluation.md`、`FEEDBACK-LOOP.md`、`check-round12.mjs` v1.0 全文、`ROUND12-ACCEPTANCE.md` v1.1 草案。
- 未重测：OCR 精度全量（wasm 缺失）、Lighthouse mobile 新跑、axe/zip（引 evidence/r9–r11）；R12 在途分支交付质量不在本轮范围（合入后由 #3 探针 v1.1 与编排终验把关）。
