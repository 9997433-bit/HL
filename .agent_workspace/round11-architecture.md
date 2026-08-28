> Model slug: claude-fable-5（Round 11 子代理 #1 · `cursor/r11-arch-contracts-9f67`）

# Round 11 · 洪恩体验打磨架构契约

> 基线：`cursor/openmoji-integration-9f67` @ `4236625`（撰写时远端 HEAD。注意基线已经
> 从 Brief 宣告的 `72fd438`「1/8」前移：`4236625` 合入了 #10 的 TTS 评估 + 反馈回路 +
> 商店清单，`check:round11` 在本基线实测 **2/8**——H7、H8 绿，H1–H6 红）。
> 性质：**只定数据契约与 API 边界，不含实现**。功能由子代理 #4–#10 按本契约落地，
> #3/#2 按第 9 节的门禁映射验收与审计。
> 关联：`ROUND11-BRIEF.md`、`scripts/check-round11.mjs` v1.0、`round10-architecture.md`、
> `round10-hongen-audit.md` §5「R11 归属」（8 项深度债全部在本文有落点，对账见 §11）。

基线八探针逐项水位（撰写时在 `4236625` 干净 worktree 实跑 `node scripts/check-round11.mjs`）：

| 探针 | 基线状态 | 缺口 |
|---|---|---|
| H1 跟读产品化 | ✗ freeze=**true**，harness=false，smoke=false | 评测集骨架 + Go/No-Go 文档/harness + `ROUND11_H1` |
| H2 OCR 矩阵 | ✗ real=**3**/5，ux=**true**，marker=false | 实拍扩样 ≥5 + `ROUND11_H2` + 行为级失败话术 |
| H3 周计划 | ✗ plan=false，parent=false，smoke=false | `week-plan.js` + 家长面板 + `ROUND11_H3_SMOKE` |
| H4 绘本场景 | ✗ scene=false，marker=false | 场景 DSL + `BookPageScene.vue` + `ROUND11_H4` |
| H5 儿歌过半 | ✗ audio=**3**/8，marker=false | **在途分支 `322f404` 已交付 8 首**，验收合并即绿 |
| H6 预算/趋势 | ✗ evidence=0/1，budget=false | **在途分支 `f8a76c0` 已交付**，验收合并即绿 |
| H7 TTS/分发 | ✓ 已合入（`4236625`） | 无缺口，本文 §7 据实冻结其契约 |
| H8 R10 不退化 | ✓ check:round10 8/8 | 每分支合并前保持 |

三个基线已亮/半亮的格子，交付者别重做、也别拿它们当免做的借口：

- **H1 的 freeze 半条件基线恒真**：R10 spike 落盘的 `public/asr/manifest.json` 自带
  5 条 `freezeChecklist` + `modelId`，探针的 `freezeOk` 在基线就是 true。H1 的真门槛
  只有 harness 与 smoke 两个半条件——#4 交付的实体是**评测集骨架 + Go/No-Go 证据 +
  可跑的校验脚本**（§1），不是再抄一遍清单；
- **H2 的 ux 半条件基线恒真**：`CameraOcrView.vue` 模板里现成的「换一张」按钮就命中
  `/失败|认不出|换一张|光线|ROUND11_H2/i`。所以失败话术必须按 §2.3 做成**行为**
  （零命中分支的具体建议 + 观测点），#3 在 v1.1 应堵掉这个恒真洞（§0.2 第 3 条）；
- **H7 的 store 半条件里 RELEASE-CHECKLIST 正则历史恒真**（「应用商店」字样 R9 起就
  在文首），真把关的是 `FEEDBACK-LOOP.md` 的存在——现已随 `4236625` 交付，连同
  103 行的 `r11-tts-evaluation.md`（>1500 字符，tts 半条件也独立成立）。#10 已收工，
  本轮任何人不得回改这三份文档的结论段（§7）。

---

## 0. 总原则（对 Round 11 全部交付生效）

### 0.1 探针即契约，匹配细节先点名

`scripts/check-round11.mjs` v1.0 已合入基线，固定 8 项输出，升 v1.1 归 #3 且**只许
加严**。逐行读探针源码得出的易踩细节：

- **剥注释口径**：H1 对 harness 脚本、H2 对 `CameraOcrView.vue` + `test-ocr-accuracy.mjs`、
  H3 对五份源文件、H4 对三份源文件、H5 对 `songs.js`，以及两份 smoke，一律先
  `stripComments` 再匹配——**所有标记词必须落在代码里**（标识符、字符串字面量或
  模板文本），写在注释里等于没写；
- **无后缀豁免的标记**：H2 `/\bROUND11_H2\b/`、H4 `/\bROUND11_H4\b/`、H5
  `/\bROUND11_H5\b/`、H3 `/\bROUND11_H3_SMOKE\b/`——词边界后跟下划线不算边界，
  `ROUND11_H4_SMOKE` 匹配不上 H4 的探针。只有 H1 是 `/\bROUND11_H1(_SMOKE)?\b/`
  两种形态都认；
- **H1 的 smoke 半条件测的是 `literacySmoke + doc` 拼接**——把 `ROUND11_H1` 写进
  harness 代码就同时点亮 harness 与 smoke 两个半条件。这是 v1.0 的宽松面：本契约
  仍要求 literacy smoke 落行为段（§1.5），#3 在 v1.1 收紧为必须命中 smoke 本体；
- **H2 的文件名前缀收紧为 `/^real/i`**：R10 探针认 `real|photo|capture|实拍` 子串，
  R11 只认 **`real` 开头**的 `.png`，且逐张校 PNG 魔数 + ≥4096 B，只数
  `apps/literacy-app/scripts/fixtures/ocr/` 一层目录（不递归）；
- **H3 探针读死五个路径**：`data/skill-graph.js`、`data/skill-practice.js`、
  **`data/week-plan.js`（新文件，路径锁定）**、`modules/skill-graph/SkillGraphView.vue`、
  `modules/parent/ParentView.vue`。parent 半条件只测 `ParentView.vue` 一个文件；
- **H4 探针读死三个路径**：`data/books.js`、**`components/BookPageScene.vue`（新组件，
  路径锁定）**、`views/BookReadView.vue`。场景数据本体放 `data/books/core.js` 是
  探针看不见的——`ROUND11_H4` 标记与 `sceneOfPage` 导出必须落在 `books.js`（§4.2）；
- **H5 的 audio 判定**是 `await import` 后逐条测字段命中 `/\.(mp3|ogg|wav|m4a)/i`
  **且 public 下真实文件 ≥10,240 B**（v1.0 就查存在性，比 R10 v1.0 严）——
  `songs.js` 及依赖链必须保持裸 Node 可载；
- **H6 的 evidence 只数 `.agent_workspace/evidence/r11/` 一层目录**下的
  `.json|.md`（不递归，子目录白干）；budget 半条件三选一：
  `apps/math-app/scripts/check-route-budget.mjs` 存在 / `r11-perf-budget.md` 存在 /
  正则命中。在途交付三路全占（§6）。

### 0.2 v1.1 加严清单（#3 的活，功能方按加严后口径交付，不赌 v1.0 的宽松）

1. **H1 smoke 半条件收紧**：`ROUND11_H1(_SMOKE)` 必须命中 literacy `smoke.mjs` 本体
   （剥注释），不再接受 doc 拼接命中；
2. **H1 harness 实跑**：`test-asr-eval-set.mjs` 存在且 `spawnSync` 退出码 0（评测集
   清单 schema 校验真实可跑，不是空壳文件）；
3. **H2 ux 恒真洞**：要求 `\bROUND11_H2\b` 或 `data-ocr-empty` 落在
   `CameraOcrView.vue` 剥注释文本里（失败话术必须接进视图，光在精度脚本里
   打标记不算）；
4. **H2 张数联动**：`test-ocr-accuracy.mjs` 里 real-photo tier 的最小张数常量 ≥5
   且与 BENCHMARK 实际条目数一致（防「图在目录里、基准不测它」）；
5. **H3 plan 正则过宽**（五文件拼接命中任意 `weekPlan` 字样即真）：收紧为
   `week-plan.js` 文件存在 + `buildWeekPlan` 导出在场 + `ParentView.vue` 模板级
   `data-week-plan`；
6. **H4 scene 正则自命中**（`BookPageScene.vue` 只要存在且内容含 `scene` 即真）：
   收紧为 import `books.js` 后 `BOOKS` 里带合法 `scene` 字段的页数 ≥5；
7. **H5 音频魔数**：抽验文件头（Ogg 的 `OggS` / MP3 的 `ID3`/0xFFFB），防拿文本
   文件凑字节数；
8. **H6 趋势 JSON schema**：断言 `math-lighthouse-trend.json` 可解析且含
   `sha256`/`budget`/`status` 类字段（在途交付已含，钉住不许退化成空壳）；
9. **H7 保持**（已交付，斟酌加严为结论章节含「录音」与「Piper」字样，防文档被
   掏空重写）。

已定契约的命中面（路径、导出名、标记词、文件名）如需变更，必须回改本文档。

### 0.3 预算红线

- 识字入口 JS < **420 KB**（literacy `check-bundle.mjs`）；数学首屏预算由
  `check-bundle.mjs` + 新增 `check-route-budget.mjs`（§6，入口 96 KiB、路由组各有
  gzip 上限）双层把守，**预算数值此后只许收紧**；识字 zip < 10 MiB；
- 儿歌音频总预算沿 R10 的 **≤2.0 MiB**：在途 8 首实测合计 228,790 B（≈224 KiB，
  sg1–sg3 三首 89,922 B + sg4–sg8 五首 138,868 B），余量充足；后续补满 13 首仍按
  此预算封顶；
- H4 场景 DSL 是纯数据，随绘本正文走既有懒加载链（`books.js` 不被首页 import 的
  纪律不变，首页仍走 `book-index.js`）；`BookPageScene.vue` 进 BookRead 路由 chunk，
  主包零增量；
- **模型与录音红线**：ASR 模型、TTS 引擎、真人录音资产本轮**零字节入库**——
  H1 交付的是清单/评测集/证据，H7 交付的是评估文档（§7 结论就是「不进 1.0 首包」）。

### 0.4 纯数据红线

被 Node 门禁 `await import` 或读源码的文件——`songs.js`（H5 探针 import）、
`books.js` 及 `books/*.js`（literacy `check:data` import；v1.1 H4 加严后探针也会
import）、`daily.js` / `skill-graph.js` / `skill-practice.js`（R10 探针 + math
`check-content.mjs`）、**`week-plan.js`（新，本轮起被 H3 探针读源码、被
check-content import）**——与其依赖链禁止 Vue / 浏览器 API 顶层调用、禁止
`Math.random` 直调、禁止 import 任何 store。

### 0.5 不退化

每个分支合并前 `npm test` 全绿 + `check:round10` **8/8**（= R11 H8，内含
`check:round9` 8/8 及 R8/R7/R6 级联）。既有标记词命中面一个不许碰坏：
`ROUND10_H1`/`ROUND10_H1_SMOKE`（跟读四档降级 smoke 段）、`ROUND10_H2`（精度脚本
与 supersedes 链）、`ROUND10_H3`（`skill-practice.js` 的 `practice-entry` 常量）与
`ROUND10_H3_SMOKE`、`ROUND10_H5`（songs.js 的 file-first 常量）。数值红线全数继承
R10 终态：字库 **1820**、绘本 **132 本/1121 页**、儿歌 **13 首**（其中带真实音频者
本轮 3→8）、字源 **808**、`SKILL_NODES` **34**、OCR 基准 **13 张 9 tier**（10 合成 +
3 实拍，本轮实拍 3→≥5）、LH mobile 双 App P ≥ 0.95、桌面档 P = 1.00、
`evidence/r8`–`r10` 整目录只读、axe 四主题 critical/serious 0/0、
`ANDROID-DEVICE-CHECKLIST.md` 零 `[待填]`。

### 0.6 存储向后兼容

- 识字主存档 `happy-literacy:v1` 顶层形状冻结，本轮零新增域；
- 数学 `mathquest/progress` 顶层**本轮唯一新增域 `weekPlan`**（§3.4）：
  `defaultState()` 与 `mergeState()` 同步补显式清洗分支（旧档缺省合并为 `{}`），
  家长页导出/导入向后兼容；`mathquest/settings` 的 sanitize 白名单不动；
- 技能图谱浏览路径继续满足 R8 起的 **localStorage 字节级只读断言**——周计划的
  采纳痕迹只在家长面板 / 落点页的显式动作里写入（§3.4），逛图谱、看周计划本身
  不写一个字节。

### 0.7 并发纪律

多个子代理共用一台 VM。**本轮实测发现共享树 `/workspace` 被并发直改**（撰写期间
`asr-eval-set.json`、`week-plan.js`、`try-crop.tmp.mjs` 等在途文件在共享树出没又
消失）——重申铁律：不切共享树的分支、不在共享树留未提交文件，一律
`git worktree`（`/tmp/wt-r11-<task>`）+ cherry-pick 合入；worktree 里跑门禁前先
`ln -s /workspace/node_modules`。package.json 写者本轮各归一人：
**literacy `package.json` 只有 #4 动**（挂 `test:asr-eval` 链，§1.4）；
**math `package.json` 只有 #9 动**（已随 `f8a76c0` 交付 `check:route-budget` 挂链）；
根 `package.json` 与 lockfile 本轮**无人动**。

### 0.8 全程离线

CI 零联网：H1 harness 用仓库内清单与 mock 后端，不下载模型；H2 的
`gen-ocr-real-samples.mjs` 联网只发生在样张生成期（不在构建/测试链上），产物 PNG
与溯源清单入库后 CI 全程离线；H5 音频是仓库内静态资产；H6 趋势脚本只读本地
evidence JSON。

---

## 1. 契约一 · 跟读产品化：评测集骨架 + Go/No-Go 证据（H1，所有者 #4）

### 1.1 探针拆解

H1 = `freezeOk`（基线恒真，见文首）&& `/ROUND11_H1|Go.?No.?Go|冻结集|eval.?set/i`
命中「`r11-followread-gonogo.md` + `r11-asr-eval-set.md` + `test-asr-eval-set.mjs`
剥注释」拼接 && `/\bROUND11_H1(_SMOKE)?\b/` 命中「literacy smoke + 前述 doc」。
真交付实体是三份新文件 + smoke 行为段；R10 H1 的四档降级、`ROUND10_H1_SMOKE`
断言、`available:false` 语义全部冻结不动。

### 1.2 评测集骨架：`.agent_workspace/r11-asr-eval-set.md` + `scripts/data/asr-eval-set.json`

- **机读清单** `apps/literacy-app/scripts/data/asr-eval-set.json`（新建，#4 独占）：

  ```jsonc
  {
    "schema": "literacy-asr-eval/1",          // 冻结
    "marker": "ROUND11_H1",                    // 代码级标记落点之一
    "target": { "total": 300, "quiet": 200, "noisy": 100 },  // 终态规模（R9 评估 §5 口径）
    "thresholds": {                            // Go/No-Go 判分线，只许上调
      "quietCharRecall": 0.90, "noisyCharRecall": 0.80,
      "missRecall": 0.85, "silenceFalseRate": 0.01
    },
    "entries": [ /* 本轮骨架 ≥30 条 */ ]
  }
  ```

  `entries[]` 条目 schema（冻结为本形状，后续只许追加可选字段）：
  `id`（`ev-NNN`，唯一）· `text`（3–12 字，逐字 ∈ `CHARACTER_MAP`）· `pinyin`
  （空格分隔，字数对齐）· `ageBand`（`4-6|7-8|9-10`）· `scene`（`quiet|noisy`）·
  `durationSec`（3–10 的目标时长）· `status`（**本轮一律 `scripted`**——只有脚本
  文本，没有音频；真实录音后升 `recorded`，字段含义写死在文档里，不许拿
  `scripted` 冒充已采集）· `source`（语料出处：字表单元 / 儿歌句 / 绘本句的引用）。
  **音频零入库**：骨架阶段只冻结「录谁、录什么、怎么判」，采集协议（家长书面同意、
  说话人隔离、双标注仲裁、去标识存储）写进 md 文档，是 R11 之后真实采集的执行依据；
- **人读文档** `.agent_workspace/r11-asr-eval-set.md`（新建，#4 独占）：评测集
  设计说明——分层抽样表（年龄档 × 场景 × 句长）、标注规范（字符召回怎么数、
  漏字怎么算、静音段怎么判）、采集协议全文、与 `asr-eval-set.json` 的对应关系
  （文档是人读副本，harness 校验的是 JSON）。

### 1.3 Go/No-Go 证据：`.agent_workspace/r11-followread-gonogo.md`

新建，#4 独占。五层门槛逐层记录，**判定只有三种取值：Go / No-Go / 未测**——
未测的层如实写「未测：<原因>」，不许留空或含混：

| 层 | 门槛（继承 spike §5 与 R9 评估 §5，一条不放宽） | 本轮预期判定 |
|---|---|---|
| 1 模型冻结 | URL/SHA-256/tokens/量化档/许可证齐 + THIRD_PARTY_NOTICES + SBOM | No-Go（模型未冻结，如实记录候选与卡点） |
| 2 儿童冻结集 | ≥300 条双标注；安静 ≥90% / 噪声 ≥80% / 漏字 ≥85% / 静音误判 ≤1% | 未测（骨架已立，规模 30/300） |
| 3 设备基准 | 中档 Android P95 ≤2.5 s、RTF ≤0.5、峰值内存 ≤300 MiB | 未测 |
| 4 故障演练 | 五类故障 2 s 内降档 | 部分（R10 已验「清单不可用」一类，其余四类如实列） |
| 5 音素诊断 | tone/near 精确率 ≥90% 前不逐字展示 | No-Go（维持 R9 PoC 不接界面） |

`available` 翻 true 的前置条件 = 五层全 Go——本文把这条从 spike 备忘升格为契约：
**任何人在五层全 Go 之前把 manifest 的 `available` 置 true，按破坏 H8 处理**。

### 1.4 harness：`apps/literacy-app/scripts/test-asr-eval-set.mjs`

新建，#4 独占。纯 Node、零网络、<1 s：

- 读 `scripts/data/asr-eval-set.json` → 断言 schema 版本、`marker === 'ROUND11_H1'`、
  条目 ≥30、id 唯一、`text` 逐字 ∈ `CHARACTER_MAP`（import `characters.js`）、
  pinyin 字数对齐、`ageBand`/`scene`/`status` 枚举合法、thresholds 只升不降
  （与文件内写死的下限比较）；
- 用 `speechEval.js` 的 `evaluate({ mode:'recognition', reference, heard })` 对每条
  entry 跑一遍**自转写基线**（heard = text 原文，模拟完美识别）断言得分满档——
  这是把「评测集 → 评分链」接通的最小可测闭环，不需要真 ASR；
- 代码级落 `const ROUND11_H1 = 'asr-eval-set'` 并真实使用（如作为 `--json` 输出的
  `marker` 字段值）；
- **挂链**（literacy `package.json`，#4 本轮唯一写者）：注册
  `"test:asr-eval": "node scripts/test-asr-eval-set.mjs"` 并串进 literacy `test`
  链（`test:speech` 之后）。

### 1.5 smoke 与冻结面

- literacy `smoke.mjs` 追加代码级常量 `const ROUND11_H1_SMOKE = '/follow-read'` +
  interact 段：开跟读页 → 断言 `.fr__pack` 的 `[data-status]` 取值合法且
  `[data-model]` 非空（= manifest `modelId`，评测包冻结状态对家长可见）→ 断言
  R10 的 `[data-tier]`/`[data-mode]` 观测点仍在场且档位落在合法枚举 → 全程零跨源
  请求。R6/R8/R9/R10 既有 smoke 段一行不动；
- `manifest.json` 只许**追加** `evalSet` 字段（`{ "path": "scripts/data/asr-eval-set.json",
  "schema": "literacy-asr-eval/1" }` 形态的指针），`freezeChecklist` 既有 5 条与
  `available:false` 逐字不动；`offlineAsr.js` / `useSpeechEval.js` / `speechEval.js`
  导出面冻结只许追加；三档默认值（`allowRecognition` 默认关）不动。

---

## 2. 契约二 · OCR 实拍矩阵扩样 + 失败降级话术（H2，所有者 #5）

### 2.1 探针拆解

H2 = `fixtures/ocr/` 一层目录下 `^real` 前缀的有效 PNG（魔数 + ≥4096 B）**≥5**
&& ux 正则（基线恒真）&& `/\bROUND11_H2\b/` 命中 `test-ocr-accuracy.mjs` 剥注释
文本。同时 R10 H2（≥2 张 + `ROUND10_H2`）与 R9/R8 的基准探针继续在跑——
**加图不许破坏旧探针，既有 13 张的字节与阈值冻结**。

### 2.2 样张契约（沿 R10 已立的 Commons 裁剪管线，矩阵化扩样）

- 走既有 `gen-ocr-real-samples.mjs` 管线：`real-samples.json` 追加条目 ≥2（总数
  ≥5），字段冻结为现状 12 项（`name/text/scene/commons/page/file/author/license/
  licenseUrl/sha256/crop/width`），`name` 必须 `real-` 开头（探针前缀）；自摄照片
  同样走清单登记（`commons/page/file` 换成 `selfShot: true` + 设备型号字段，管线
  跳过下载直接裁剪——如启用此路径须同步扩展 gen 脚本并在清单 `$comment` 说明）；
- **矩阵覆盖**（本轮核心增量，光照 × 角度 × 载体三维）：既有 3 张覆盖
  「自然光×正拍×标牌」「室内反光×仰拍×警示锥」「散射光×正拍×喷漆墙」；新增
  ≥2 张必须落在**未覆盖的组合**上（候选优先级：暖光/低光 × 印刷纸质、
  侧拍/透视 × 标牌），使矩阵至少 5 个不同组合。逐张在
  `.agent_workspace/r11-ocr-matrix-log.md`（新建，#5 独占）登记：文件名 · 矩阵
  坐标（光照/角度/载体）· 来源与许可 · 裁剪参数 · 实测召回 · 失败字与失败模式；
- **合规**：画面零人脸、零儿童、零个人信息；每张 `text` 逐字 ∈ `CHARACTER_MAP`
  （既有断言自动覆盖）；CC 署名同步进 `THIRD_PARTY_NOTICES.md`（沿 R10 条目格式）；
- **禁止**合成图改名冒充（R10 红线原文继承）；**禁止**为过基准调 `utils/ocr.js`
  的识别参数与 `preprocess()` 链。

### 2.3 精度脚本与失败话术（行为级，不是正则姿态）

- `test-ocr-accuracy.mjs`（纯追加）：real-photo tier 的最小张数常量 2 → **5**
  （钉死，删图当场红）；新样张逐张先实测、后定线（往下留一档写死，只许上调）；
  `--json` 的 `marker` 升为 `'ROUND11_H2'` 并保留 `supersedes: 'ROUND10_H2'` 链
  （`ROUND10_H2`/`ROUND9_H2`/`ROUND8_H4` 字样继续在代码里在场）；
- **失败降级话术**（写进视图行为）：`useOcr.js` 的 `hint` 逻辑追加**零命中分支**——
  `phase === 'done'` 且 `known` 与 `unknown` 皆空时，给出从矩阵失败样本归纳的
  具体建议（顺序固定：光线不够→挪到亮处；字太小→凑近一点；歪了→把字摆正；
  仍认不出→换一张试试），`CameraOcrView.vue` 话术区落 `[data-ocr-empty]`
  （值 = `'ROUND11_H2'`，一石二鸟满足 v1.1 加严），「换一张」按钮既有行为不动；
  话术条目与失败样本的对应关系记入 matrix-log（话术不是拍脑袋，是失败模式的
  用户语言翻译）；
- literacy smoke 复用既有 OCR 段零改动（话术分支依赖真实识别结果，无头环境不
  强测；Node 侧由精度脚本的 real tier 覆盖）。

---

## 3. 契约三 · 推荐周计划 + 家长侧理由/采纳痕迹（H3，所有者 #6）

### 3.1 探针拆解

H3 = `/weekPlan|周计划|weeklyPlan|ROUND11_H3/i` 命中五文件拼接 &&
`/推荐理由|采纳|weekPlan|周计划/i` 命中 `ParentView.vue` 单文件 &&
`/\bROUND11_H3_SMOKE\b/` 命中 math smoke。同时 R10 H3（`ROUND10_H3` 常量、
`practiceEntry` 落点、smoke 行为段）与 R9/R8 图谱探针继续在跑——
`skill-practice.js` / `skill-graph.js` / `daily.js` 旧导出面全部冻结。

### 3.2 数据契约：`apps/math-app/src/data/week-plan.js`（新文件，路径被探针锁定）

纯函数模块，零随机、零 store import、裸 Node 可载：

```js
/** ROUND11_H3 —— 推荐 → 周计划：把「下一步练什么」摊到一周七天。 */
export const ROUND11_H3 = 'week-plan'

export const WEEK_PLAN_DAYS = 7

/** 周锚点：给定日期所在周的周一 dateKey（YYYY-MM-DD，UTC 口径与 dailyDateKey 一致）。 */
export function weekStartKey(date = new Date())

/**
 * 生成一周计划。确定性：同一 (mastery, wrongBook, ageBand, weekStart) 输出逐字节相同。
 * 内部复用 skill-graph 的 recommend() 与 skill-practice 的 practiceEntries()——
 * 排序、理由、落点三层现成逻辑一个不重造，周计划只做「摊到七天」这一件事。
 * 分配规则（写死，check-content 验）：
 *   - 推荐项按 recommend() 原序循环填入周一至周五；
 *   - 周六 = 错题清账日（wrongBook 非空时 kind 固定 wrongBook，否则复习首推技能）；
 *   - 周日 = rest（无技能，文案「自由玩 + 讲给家长听」）；
 *   - 无可推荐技能的天数为 rest。
 */
export function buildWeekPlan({ mastery = {}, wrongBook = {}, ageBand, weekStart = weekStartKey() } = {})
// → { weekStart, days: [{ dateKey, dow, skill|null, skillName, kind, reason, reasonHint, to }] }
//   kind ∈ PRACTICE_KINDS 的 id ∪ 'rest'；reason ∈ RECOMMEND_REASONS 的 id ∪ 'rest'；
//   reasonHint = RECOMMEND_REASON_MAP[reason].hint（家长侧展示的推荐理由文案，同一出处）；
//   to = practiceEntry 的路由对象（rest 天为 null）。
```

### 3.3 视图契约

- **家长面板**（`ParentView.vue`，纯追加一个 panel，位置在「技能雷达」之后）：
  「📅 本周计划」——容器落 `[data-week-plan]`（值 = weekStart）；逐天渲染
  `[data-week-plan-day]`（值 = dateKey）：星期 · 技能名 · **推荐理由**
  （`reasonHint` 原文，模板级「推荐理由」四字在场即命中探针 parent 半条件）·
  **采纳痕迹**（`adopted` 有记录 → 「✓ 已按计划练过」+ 时间；无 → 「还没练」）·
  非 rest 天给「去开练」`router-link`（`to` 原样用，家长代孩子发起也走同一落点）。
  面板在口算门之内（家长区既有解锁流程不动）；
- **图谱侧**（`SkillGraphView.vue`，纯追加一行）：推荐区尾部加「📅 看本周计划」
  `router-link` 到 `/parent`（进家长区仍要过口算门，这是设计而非缺陷——周计划
  是家长侧视图）。推荐区既有结构、`data-reco-*` 观测点、只读声明逐字不动；
- **孩子侧不做周计划视图**（本轮 out of scope，§10）：孩子的入口仍是图谱推荐位的
  既有「去练」，周计划是家长的掌控面。

### 3.4 采纳痕迹的持久化契约（`mathquest/progress` 顶层唯一新增域）

```js
weekPlan: {
  [weekStartKey]: {                    // 只留最近 8 周，超量按周键排序淘汰最旧
    adopted: { [dateKey]: { skill, at } }   // at = Date.now()
  }
}
```

- **唯一写入口** = progress store 新 action `adoptWeekPlanDay(dateKey, skill)`，
  调用点只有两处：家长面板「去开练」点击时、以及落点页（daily focus / 错题重练）
  完成当日计划技能的记账路径回填（复用既有完成回调，不新增第二套记账）；
- `defaultState()` 追加 `weekPlan: {}`；`mergeState()` 追加显式清洗分支
  `weekPlan: mergeWeekPlan(saved.weekPlan)`（丢非法周键/技能、限 8 周），旧档与
  旧备份导入向后兼容；**不新增 localStorage 键**（域挂在既有 `mathquest/progress`
  之内）；
- 图谱浏览与家长面板**浏览**不写入（R8 起的字节级只读断言范围划在任何点击动作
  之前，继续成立）。

### 3.5 校验与 smoke

- math `check-content.mjs` 追加规则段（既有规则只加不改）：① 同参两次
  `buildWeekPlan` 深比较相等（确定性）；② `days.length === 7` 且 `dateKey` 连续；
  ③ 非 rest 天 `skill ∈ SKILL_NODE_MAP`、`kind ∈ PRACTICE_KINDS ∪ rest`、
  `reason ∈ RECOMMEND_REASONS ∪ rest`；④ 周日恒 rest；⑤ `week-plan.js` 源文本无
  `Math.random` 直调、无 store import；⑥ 空存档（零 mastery 零错题）下
  `buildWeekPlan` 不抛错且至少给出 rest 兜底；
- math `smoke.mjs`：`const ROUND11_H3_SMOKE = '/parent'`（完整词，§0.1）+ interact
  段：种含 learning 技能与 1 条错题的存档 → 过口算门进家长面板 → 断言
  `[data-week-plan]` 与七个 `[data-week-plan-day]` 在场、至少一天展示推荐理由
  文案与「还没练」→ 点某天「去开练」→ 落 `/daily?focus=…` 或
  `/progress?wrong=…` → 回家长面板断言该天翻成「✓ 已按计划练过」（采纳痕迹
  写入生效）→ 全程无控制台报错。R9/R10 smoke 段不动，跳转前的 localStorage
  只读断言口径继承。

---

## 4. 契约四 · 绘本页级多元素场景（H4，所有者 #7）

### 4.1 探针拆解

H4 = `/scene|scenes|多元素|ROUND11_H4|BookPageScene/i` 命中「`books.js` +
`BookPageScene.vue` + `BookReadView.vue`」剥注释拼接 && `/\bROUND11_H4\b/` 命中
「同拼接 + literacy smoke」。审计 §5.2-X2 的方向写进契约：**程序化增密**——
先做 1 本样板量化「表现力/体积」比值，不铺开、不引入手绘素材。

### 4.2 场景 DSL（数据契约，落 `books/core.js`，标记与工具落 `books.js`）

- 页对象追加**可选**字段 `scene`（缺省 = 现状单 emoji，全库 131 本零感知）：

  ```js
  // books/core.js —— 样板书选 b1《我看大自然》，5 页全配（≥1 单元的「单元」= 一本书）
  {
    emoji: '🌅',                          // 保留：无 scene 消费方与投稿链的兜底
    text: '天上有日，天上有月。', p: '…',   // 冻结：一字不动（注音/覆盖率门禁）
    scene: {
      bg: ['#ffe6b3', '#c8ebff'],         // 可选，缺省用书 palette
      items: [                            // 2–8 个元素，画布 100×100（与字源 sketch 同规）
        { e: '🌅', x: 50, y: 62, s: 3.2 },            // e=emoji x/y=中心坐标 s=相对缩放
        { e: '☀️', x: 24, y: 22, s: 1.6, anim: 'pop' },
        { e: '🌙', x: 76, y: 20, s: 1.4, anim: 'float', flip: true }
      ]
    }
  }
  ```

  `anim` 枚举冻结：`'float' | 'pop' | 'drift' | 'sway'`（缺省静止）；`z` 可选层级；
  坐标/缩放越界（x,y ∉ 0–100、s ∉ 0.5–6、items ∉ 2–8）由校验器拦截；
- `books.js` 追加导出（旧导出面冻结）：

  ```js
  /** ROUND11_H4 —— 页级多元素场景 DSL（样板：b1 全 5 页）。 */
  export const ROUND11_H4 = 'page-scene-dsl'
  export const SCENE_ANIMS = ['float', 'pop', 'drift', 'sway']
  /** 归一化：无 scene 的页由 emoji 合成单元素场景，视图端零分叉。 */
  export function sceneOfPage(page, book) // → { bg, items } 恒非空
  /** check:data 挂链的形状校验器：返回 [{ book, page, error }]，零错为过。 */
  export function verifySceneShapes()
  ```

### 4.3 视图契约

- 新组件 `apps/literacy-app/src/components/BookPageScene.vue`（#7 独占，探针路径
  锁定）：props `{ scene, reduceMotion }`；emoji 一律经 `OpenMojiIcon` 渲染（署名
  义务已由 THIRD_PARTY_NOTICES 覆盖）；入场与循环动画走 GSAP，
  `reduceMotion === true` 时全静态铺开不丢元素；根节点落 `[data-book-scene]`
  （值 = items 个数）；
- `BookReadView.vue`：页面插画区改为 `<BookPageScene :scene="sceneOfPage(page, book)" …>`
  ——对无 scene 的 131 本，渲染结果是「书 palette 渐变 + 单 emoji 大图」，与现状
  视觉等价；逐句朗读、点字发音、翻页动画、`markRead()` 记账全部不动。

### 4.4 校验与 smoke

- literacy `check-data.mjs` 追加规则段：`verifySceneShapes()` 零错 + 带 scene 的页
  数 ≥5 + `anim` 全 ∈ `SCENE_ANIMS`（对齐 v1.1 加严第 6 条）；
- literacy `smoke.mjs` 追加 `const ROUND11_H4 = 'book-page-scene'`（**精确此形，
  无后缀**，§0.1）+ interact 段：开 `/books/b1` 阅读页 → 断言 `[data-book-scene]`
  在场且值 ≥2 → 翻一页断言场景随页切换 → 开 reduced-motion 重载断言元素仍
  全数在场 → 无控制台报错。既有绘本 smoke 段不动。

### 4.5 红线

`pages[].text/p` 一字不动；131 本无 scene 的书渲染路径视觉等价；`gen-books.mjs`
与种子文件零改动；投稿 schema `hongen-book/1` 不动（scene 不进投稿面，社区稿仍
单 emoji，schema 升版留给后续轮次）；`book-index.js` 轻量索引不长胖（scene 只在
正文链）。

---

## 5. 契约五 · 儿歌真实音频过半（H5，所有者 #8）——在途已交付，据实冻结

分支 `cursor/r11-literacy-songs-expand-9f67` @ `322f404` 已推送。本节把交付形状
冻结为契约，合并时按 §5.3 验收：

### 5.1 已交付面（实测自分支 diff）

- `sg4`–`sg8` 五首新增 Ogg（`audio/songs/<id>-<slug>-melody.ogg`，26,227–30,441 B/首），
  与既有 `sg1`–`sg3` 合计 **8 首 / 228,790 B**（预算 2.0 MiB 余量充足）；
- 全部由 `generate-song-audio.py` 从 `notes` 谱面离线渲染（bpm 对齐 v2 歌词同步的
  时间轴，零第三方旋律/录音——版权链与 R10 一致，自有谱面自渲染）；
- `songs.js`：五首 `audio: null` → 路径字符串；头注「前三首」改「前八首」；追加
  `export const ROUND11_H5 = 'eight-file-first-with-synth-fallback'`（代码级，
  命中探针）；`ROUND10_H5` 常量与其余导出面未动；
- `SongsView.vue` 小改（文件优先 + 合成降级的既有双轨语义不变）。

### 5.2 冻结红线（对后续任何触碰生效）

歌词 `lines`/`notes`/`bpm` 冻结；`markSongSung()` 记账语义不变（存档 `songs` 域
形状 R8 口径）；文件命名 `audio/songs/<songId>-<slug>-melody.ogg` 锁定；剩余 5 首
（`sg9`–`sg13`）补齐归后续轮次，同一管线同一预算。

### 5.3 合并验收

cherry-pick 后：literacy `check:data` 儿歌六探针零感知通过；smoke 的
`ROUND10_H5` 段（阈值 ≥3）与新八首兼容；`check:round11` H5 报
`audio=8/8 + ROUND11_H5=true`；`check:round10` H5 仍 ≥3 绿。

---

## 6. 契约六 · 路由级预算 + LH 趋势冻结（H6，所有者 #9）——在途已交付，据实冻结

分支 `cursor/r11-perf-budget-trend-9f67` @ `f8a76c0` 已推送。据实冻结：

### 6.1 已交付面

- `apps/math-app/scripts/check-route-budget.mjs`：从生产 `dist` 计算「首次进入
  路由新增的 JS 静态依赖 + 同名 CSS」gzip 总和；入口预算 **96 KiB**，`/` 首页
  eager，其余 19 条路径归 17 个 lazy 组各带上限（24–48 KiB 档）；已注册
  `check:route-budget` 并串进 math `test` 链（math `package.json` 本轮唯一写者
  #9，已兑现）；
- `scripts/check-r11-perf-trend.mjs`（根 scripts/）：趋势冻结检查；
- `.agent_workspace/evidence/r11/math-lighthouse-trend.json`：机读冻结——三份
  原始 LH 报告的 SHA-256、口径、原始值、差值、预算、PASS/FAIL（R8→R9 mobile
  同口径差分：P 0.99→0.98 判 PASS 但记为退化在案；R10 desktop P=1.00 冻结为
  独立基线，**不做跨 profile 差分**）；
- `.agent_workspace/r11-perf-budget.md`：`ROUND11_H6` 标记 + 预算表 + 趋势口径
  （相对退化 ≤10%、分数差 ≤3 pp 等判线写死在文档与 JSON）。

### 6.2 冻结红线

路由组预算与趋势判线**只许收紧**；`evidence/r8`–`r10` 只读、`r11` 新增文件不
覆盖既有；趋势 JSON 里的历史原始值不删改（新轮次追加记录）；mobile LH 阈值
0.95 与 `lighthouse-ci.mjs` 三重版本锁不动；R11 期间若合并顺序导致路由组变化
（本轮无人新增数学路由，预期零冲突），预算表更新必须与路由变更同 commit。

### 6.3 合并验收

cherry-pick 后 `npm test`（math 链含新 `check:route-budget`，需先 `npm run build`
的既有顺序已由 test 链保证）全绿；`check:round11` H6 报 `evidence=1 + budget=true`。

---

## 7. 契约七 · TTS 评估 + 商店/反馈骨架（H7，所有者 #10）——已合入，据实冻结

`4236625` 已合入三份文档，H7 基线即绿。冻结其**结论与结构**（后续轮次只许追加
执行记录，不许回改结论）：

- `.agent_workspace/r11-tts-evaluation.md`（`ROUND11_H7` 标记在场）：三维对比
  （包体/授权/音质）结论——**Piper/VITS 不进 1.0 首包**（普通话权重 ~63.2 MB +
  GPL-3.0 运行时 + 模型卡训练数据许可不明 = 当前 No-Go）；**首选「高频闭集分批
  真人录音 + SpeechSynthesis 兜底」**，首批 300–500 高频单字 + 30–50 条固定反馈，
  首包增量 ≤5 MiB，动态插值句留系统 TTS + 字幕降级。这条结论是 X1 横切债的
  方案级定案，影响 L-M2/L-M5/L-M8/L-M11 的后续资产路线；
- `.agent_workspace/FEEDBACK-LOOP.md`：T0–T3 四轮试用骨架（主问题/人群/成功信号/
  退出条件表 + 九步闭环），数据红线写死：儿童最小数据、默认零遥测、禁第三方
  行为分析 SDK、家长同意先行；
- `RELEASE-CHECKLIST.md` §7「Round 11 商店与分发清单」：签名密钥管理、商店元数据、
  儿童政策申报、崩溃/反馈责任人矩阵——未勾选项保持未勾选（骨架不是完成状态），
  `[待填]` 只出现在责任人矩阵（该文件不在 R10 H6 清单探针范围内，无占位冲突；
  #3 在 ROUND11-ACCEPTANCE 里记录这个边界，避免误伤）。

后续义务挂账：真人录音一旦立项，资产按 `CONTENT_LICENSE.md` 记账、演播授权合同
归档进 evidence；商店提交当天重查政策条款（文档自身已写明）。

---

## 8. 文件所有权与冲突矩阵

| 热点文件 | 触碰者 | 隔离规则 |
|---|---|---|
| `public/asr/manifest.json`（追加 evalSet 指针）、`scripts/data/asr-eval-set.json`、`scripts/test-asr-eval-set.mjs`、**literacy `package.json`**、`.agent_workspace/r11-asr-eval-set.md`、`r11-followread-gonogo.md` | #4 独占 | `freezeChecklist`/`available:false` 逐字不动；literacy pkg 本轮唯一写者 |
| `fixtures/ocr/real-*.png`（新增）、`fixtures/ocr/real-samples.json`、`gen-ocr-real-samples.mjs`、`test-ocr-accuracy.mjs`、`composables/useOcr.js`、`views/CameraOcrView.vue`、`THIRD_PARTY_NOTICES.md`（OCR 段）、`.agent_workspace/r11-ocr-matrix-log.md` | #5 独占 | 既有 13 张字节/阈值冻结；识别参数不动 |
| `data/week-plan.js`（新）、`stores/progress.js`（weekPlan 域）、`modules/parent/ParentView.vue`（周计划 panel）、`modules/skill-graph/SkillGraphView.vue`（入口一行）、math `check-content.mjs`（追加段）、math `smoke.mjs`（`ROUND11_H3_SMOKE` 段） | #6 独占 | `daily.js`/`skill-graph.js`/`skill-practice.js` 零改动；math pkg 不碰 |
| `data/books.js`（追加导出）、`data/books/core.js`（b1 五页 scene）、`components/BookPageScene.vue`（新）、`views/BookReadView.vue`（插画区）、literacy `check-data.mjs`（追加段） | #7 独占 | 正文/注音一字不动；`book-index.js` 不动 |
| literacy `scripts/smoke.mjs` | #4（`ROUND11_H1_SMOKE` 段）+ #7（`ROUND11_H4` 段） | 各自纯追加独立 interact 段，先到先得；R6–R10 段不动 |
| `data/songs.js`、`views/SongsView.vue`、`public/audio/songs/*`、`generate-song-audio.py` | #8（已交付 `322f404`） | §5.2 冻结面 |
| math `scripts/check-route-budget.mjs`、**math `package.json`**、根 `scripts/check-r11-perf-trend.mjs`、`evidence/r11/math-lighthouse-trend.json`、`.agent_workspace/r11-perf-budget.md` | #9（已交付 `f8a76c0`） | math pkg 本轮唯一写者；预算只许收紧 |
| `r11-tts-evaluation.md`、`FEEDBACK-LOOP.md`、`RELEASE-CHECKLIST.md` §7 | #10（已合入 `4236625`） | 结论段冻结，只许追加执行记录 |
| `.agent_workspace/round11-architecture.md`（本文） | #1 | 契约变更须回改本文 |
| `ROUND11-ACCEPTANCE.md`、`check-round11.mjs` v1.1 | #3 | 探针只许加严（§0.2 清单） |

**合并顺序**：#10 已在基线；**#8、#9 已推送，先行合入**（#9 动 math package.json，
单独一拍，其后合入的分支重跑 math test 链即可，无 lockfile 变更）→ #4 / #5 /
#6 / #7 四条功能线互不依赖可乱序（唯一交叉点 literacy smoke 按「各自追加段」
先到先得）→ #2 审计、#3 验收强化随时可合，但探针加严若改变命中面必须回改本文。
每个分支合并前：`npm test` 全绿 + `check:round10` 8/8。

---

## 9. 契约 → 门禁映射

| 契约 | check:round11 探针 | 所有者 | 回归红线 |
|---|---|---|---|
| §1 跟读产品化 | H1：freeze（基线恒真）+ harness 文档/脚本命中 + `ROUND11_H1(_SMOKE)` | #4 | `available:false` 不翻；四档语义/默认值不动；模型音频零入库；R10 smoke 段不动 |
| §2 OCR 矩阵 | H2：`^real` PNG ≥5（魔数+4KB）+ ux（基线恒真→行为化）+ `\bROUND11_H2\b` | #5 | 13 张基准字节/阈值冻结；识别参数不动；来源逐张溯源 |
| §3 周计划 | H3：五文件 plan 信号 + ParentView 理由/采纳 + `\bROUND11_H3_SMOKE\b` | #6 | 三个数据文件旧导出冻结；weekPlan 是 progress 唯一新增域；图谱浏览零写入 |
| §4 绘本场景 | H4：三文件 scene 信号 + `\bROUND11_H4\b`（books.js 代码级） | #7 | 正文注音冻结；无 scene 书视觉等价；投稿 schema 不动 |
| §5 儿歌过半 | H5：audio ≥8（public 实文件 ≥10KB）+ `\bROUND11_H5\b` | #8（已交付） | 歌词/notes/bpm 冻结；≤2.0 MiB；合成降级双轨不动 |
| §6 预算/趋势 | H6：evidence/r11 一层 ≥1 + budget 三选一 | #9（已交付） | 预算/判线只收紧；r8–r10 证据只读；历史值不删改 |
| §7 TTS/分发 | H7：tts 文档 >1500 字符 ∨（清单正则 + FEEDBACK-LOOP 存在） | #10（已合入） | 三文档结论冻结；零遥测红线 |
| 全体 | H8：`check:round10` 8/8（内含 R9/R8/R7/R6 级联） | 每个分支 | 合并前 `npm test` 全绿 |

---

## 10. 明确不做（Out of scope）

- 跟读不提交任何模型/音频字节、不把 `available` 翻 true、不做后台采集、评测集
  条目本轮全部 `scripted`（不冒充已录音）、音素诊断维持不接界面；
- OCR 不采集儿童手写/人像、不为过基准调运行时参数、不删合成图 tier（两类并存
  各测各的边界）、失败话术不做「假装再试一次就能成」的空转重试；
- 周计划不做孩子侧周视图、不代点开练、不写图谱浏览路径、不新增 localStorage 键
  （域内新增走 mergeState 清洗）、不改 `recommend()`/`practiceEntry()` 签名与语义、
  聚焦练习仍不顶替每日任务；
- 绘本场景本轮只做 b1 一本样板、不铺开全库、不引入位图/手绘素材、不动投稿
  schema、不改任何书的正文与注音、不做页面音效；
- 儿歌不引入第三方旋律/录音、不自动播放、剩余 5 首不赶工（归后续轮次）；
- 性能不降既有阈值、不做跨 profile 的 LH 差分、不动 `acceptance.sh`；
- TTS/分发不接任何遥测 SDK、不启动真实商店提交（清单是骨架）、不录音（评估
  文档先行，资产后续立项）；
- 全体：不改识字主存档顶层结构与 FSRS 参数、不动 axe 四主题 0/0 水位、不动
  `ANDROID-DEVICE-CHECKLIST.md`（R10 已回填，R11 真机常态化的流程升格归 #2/#3
  在验收文档记账，不在本轮改清单本体）。

---

## 11. R10 审计「R11 归属」对账（§5.1 六项 + §5.2 三债 + §5.3 → 本文落点）

| # | 审计条目 | 本文落点 |
|---|---|---|
| 5.1-1 | L-M9 跟读：真模型选型定案、儿童冻结集、Go/No-Go | §1（#4）——冻结集骨架 + 五层 Go/No-Go 证据；真模型挂载仍留后续轮（五层全 Go 才动 `available`） |
| 5.1-2 | L-M10 OCR：实拍矩阵 tier 化、失败降级话术 | §2（#5）；Android WebView 相机端到端归 X3 常态化，本轮不设门禁（如实记录） |
| 5.1-3 | L-M11 儿歌：全曲库真实旋律 | §5（#8）——8/13 过半；范唱/MV/IP 化不在本轮（§10） |
| 5.1-4 | L-M5 绘本：页面表现力 | §4（#7）——多元素场景 DSL 样板 1 本；朗读音质归 X1（§7 定案） |
| 5.1-5 | M-M1 推荐：周计划 + 家长理由/采纳 + 效果度量 | §3（#6）——周计划与采纳痕迹落地；「掌握度提升 vs 对照」的效果度量**本轮除名**（需要多周真实使用数据，骨架先行，不装作有人能测） |
| 5.1-6 | L-M15/M-M16 性能：路由级预算、趋势止血 | §6（#9）——预算表 + 趋势冻结（0.99→0.98 记退化在案，判线 ≤3 pp 起看住） |
| 5.2-X1 | 合成语音方案评估 | §7（#10）——三维定案：录音首选、Piper 现状 No-Go |
| 5.2-X2 | 美术表现力程序化增密 | §4（#7）——审计建议的「1 个单元样板量化比值」原样执行 |
| 5.2-X3 | 真机常态化 | §6 趋势冻结是流程化第一步；「低档机每轮走查升格门禁」归 #3 在 ROUND11-ACCEPTANCE 立项，本文不越权定真机门禁（无人在本轮有真机执行面） |
| 5.3 | 商店/分发 + 反馈回路 | §7（#10）——已合入 |
