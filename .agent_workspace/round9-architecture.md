> Model slug: claude-fable-5-thinking-xhigh（Round 9 子代理 #1 · `cursor/r9-arch-contracts-9f67`）

# Round 9 · 深度打磨与发布工程架构契约

> 基线：`cursor/openmoji-integration-9f67` @ `ec733bb`（Round 8 闭合：`check:round8` **8/8**、
> `check:round7` **8/8**、`check:round6` **7/7**；`check:round9` 基线 **1/8**——仅 H8 绿）。
> 性质：**只定数据契约与 API 边界，不含实现**。功能由子代理 #4–#10 按本契约落地，
> #3/#10 按第 9 节的门禁映射验收。
> 关联：`ROUND9-BRIEF.md`、`scripts/check-round9.mjs`、`round8-architecture.md`、
> `round8-hongen-audit.md` §R9 归属备忘、`acceptance-log-round9.md`。

基线八探针逐项水位（撰写时在 `ec733bb` 实测 `node scripts/check-round9.mjs`）：

| 探针 | 基线状态 | 缺口 |
|---|---|---|
| H1 儿歌 v2 | ✗ 7/10 首，v2 标记缺失 | +≥3 首 + `ROUND9_H1` 双落点 + smoke |
| H2 OCR 扩样 | ✗ 4/8 张，handwriting=false | +≥4 张（含手写 tier）+ 脚本 tier 化 |
| H3 图谱推荐 | ✗ reco=true（`nextSkills` 基线已有），smoke=false | `recommendPath()` + 视图展示 + `ROUND9_H3_SMOKE` |
| H4 跟读路线 | ✗（在途分支已交付，合入即绿，见 §4） | 契约追认 + 冻结面 |
| H5 绘本投稿 | ✗ 文档缺失 | `BOOK-COMMUNITY-SUBMISSION.md` |
| H6 LH CI 锁 | ✗ ci=false，json=0/2 | `scripts/lighthouse-ci.mjs` + `evidence/r9/` |
| H7 发布清单 | ✗ | `RELEASE-CHECKLIST.md` + 报告 Round 9 章 |
| H8 R8 不退化 | ✓ check:round8 8/8 | 每分支合并前保持 |

两个基线已亮的半格，交付者只须不退化、别重做：

- **H3 的关键词半条件基线已绿**：`skill-graph.js` L269 已导出 `nextSkills()`，
  「接下来练什么」清单已展示在 `SkillGraphView.vue` L280–295。#6 的活是把
  「下一步清单」升级成「有序推荐路径」并补 smoke，不是从零建图；
- **H4 在本文撰写时已由 #8 抢先合入集成分支**（`4da6a22`/`bcaf5ad`：评估文档 15 KB +
  `phonemeMarks`/`similarityV2` 纯函数 + 单测），且形状与 `round8-architecture.md`
  §5.2 当年预定的契约一致。§4 是追认契约：锁死导出面、划定后续 UI 接线红线。

---

## 0. 总原则（对 Round 9 全部交付生效）

1. **探针即契约**。`scripts/check-round9.mjs` 已合入基线（`ec733bb`），固定 8 项输出。
   本文档所有路径、导出名、标记词以该探针**逐行**能匹配为准，禁止另起路径再回头改探针
   （探针加严归 #3，放宽谁都不许）。四个易踩的匹配细节先点名：
   - H1 对 `SongsView.vue` 读**原文**、对 literacy `smoke.mjs` **先剥注释**——
     `ROUND9_H1` 标记两边都必须落在**代码**里（标识符、字符串或模板文本），
     smoke 侧写在注释里等于没写；
   - H2 数图只数 `apps/literacy-app/scripts/fixtures/ocr/` **一层目录**下的 `.png`
     （`readdirSync` 不递归），子目录里的图不算数；`/handwriting|手写/i` 在
     「精度脚本源码 + 文件名列表拼接」上匹配——**文件名前缀与脚本 tier 标签双落点**；
   - H3 的视图存在性写死绝对路径
     `apps/math-app/src/modules/skill-graph/SkillGraphView.vue`——该文件
     **禁止移动/改名**；`ROUND9_H3_SMOKE` 对 math smoke 读原文、对 literacy smoke
     剥注释，一律按更严口径落成**代码级常量**；
   - H6 的正则测「`scripts/lighthouse-ci.mjs` 文件内容 + 根 `package.json`」的拼接——
     只在 package.json 里写个含 `lighthouse-ci` 的脚本名而不建文件，正则也能碰绿。
     **禁止**这种作弊：脚本文件与 npm 注册必须双双真实存在且可跑（#3 验收人工复核）。
2. **内容脚本化，生成物禁手改**。OCR 基准图经 `gen-ocr-benchmark.mjs` 生成后
   **冻结入库，CI 不重画**；字源修稿只改 seed / 生成器再重新生成（§5.3）；
   儿歌与剧情是手写创作内容，由 `check:data` 既有规则自动兜底。
3. **预算红线**。识字入口 JS < 420 KB（`check-bundle.mjs` L24）；数学首屏 gzip
   < 250 KB（`acceptance.sh`，本轮 #9 把同名脚本落进数学侧，§6.6）。R9 全部运行时
   新增（儿歌 +3 首、图谱推荐函数与视图区）都在懒加载 chunk 域；`fixtures/`、
   `evidence/`、`.agent_workspace/` 均不进构建产物，APK/dist 零影响。
4. **纯数据红线**。被 Node 门禁 `await import` 的文件——`songs.js`（R9 H1）、
   `skill-graph.js`（R8 H3）、`speechEval.js`（单测）——与其依赖链禁止 Vue /
   浏览器 API 顶层调用（`songs.js` 依赖的 `utils/audio.js` 顶层今天是裸 Node
   可载的，保持住）。
5. **不退化**。每个分支合并前 `npm test` 全绿 + `check:round8` **8/8**（= R9 H8，
   其内含 `check:round7` 8/8 与 `check:round6` 7/7 级联）。数值红线全数继承
   `round8-architecture.md` §0.5，并追加 R8 终态新水位：字源 **800**、单元剧情
   **99**、儿歌 **≥7**（本轮升至 ≥10）、`SKILL_NODES` **34**、LH **≥95/90/90**
   （`acceptance-log-round8.md` §2.1 斜杠三连是 R8 H6 的活探针，别碰坏格式）、
   `evidence/r8/` 整目录只读。
6. **存储向后兼容**。识字主存档 `happy-literacy:v1`：R8 已收 `songs` 顶层字段
   （`{ [songId]: { sung, times } }`，`markSongSung()` 唯一写入口）——该形状**冻结**，
   R9 不新增顶层字段、不改已有字段语义。数学 `mathquest/*` 不新增持久化键；
   图谱推荐只读 `settings.ageBand`、`progress.mastery`、`progress.wrongBook`，
   不写任何 store（§3.2）。
7. **并发纪律**。多个子代理共用一台 VM：不切 `/workspace` 共享树的分支，一律
   `git worktree`（`/tmp/wt-r9-<task>`）+ cherry-pick 合入；根 `node_modules` 是
   npm workspaces 提升安装，worktree 里跑门禁前先 `ln -s /workspace/node_modules`。
   根 `package.json` / `package-lock.json` 本轮**只有 #9 动**（§8），避免 lockfile
   三方冲突。
8. **全程离线**。Lighthouse 用 lockfile 锁版本、`npm ci` 可复现，CI 零联网；
   OCR 基准在本地跑 tesseract.js；ASR 本轮只交评估文档，任何 wasm 模型文件
   不入库、不下载、不进 SW 预缓存（§4.3）。

---

## 1. 契约一 · 儿歌 v2：曲库 ≥10 + 歌词同步动画（H1，所有者 #4）

### 1.1 探针拆解

H1 = `await import('apps/literacy-app/src/data/songs.js')` 后 `SONGS.length >= 10`
**且** `/ROUND9_H1|song.*v2|歌词同步/i` 命中「SongsView.vue 原文 + literacy smoke
剥注释文本」。同时 R8 H2 探针继续在跑：每首 `id` 唯一 + `title` + `lines` 有效、
儿歌 ≥3、`/songs` 动态路由存在——**加歌不许破坏旧探针**。基线 7 首（sg1–sg7），
缺口 ≥3 首 + v2 标记 + smoke。

### 1.2 数据：`songs.js`（追加 ≥3 首，schema 与导出面冻结）

- 新歌 id 顺延 `sg8`、`sg9`、`sg10`…（kebab/短编号沿现状）；字段与现状逐一一致：
  `id / title / titlePinyin / theme / emoji / palette(两色) / summary / tip /
  bpm(60–110) / audio(null) / lines[{ text, pinyin, notes }]`。
- 四条硬约束（`verifySongCoverage()` 现行规则，`check:data` 在跑，新歌自动被验）：
  1. 歌词逐字 ∈ `CHARACTER_MAP`——儿歌是原创内容，**不开 gloss 后门**（这条比古诗严，
     是 R8 定下的口径：孩子跟着唱的字必须全是学过或将学的字表字）；
  2. 每句拼音音节数 = 汉字数 = `notes` 数（标点不占位，错一个逐字高亮整句错位）；
  3. `notes` ∈ `NOTE_HZ`，旋律落 C 大调五声（C D E G A），音域 C4–C5；
  4. `theme` ∈ `SONG_THEMES` 且每个分区 ≥1 首（想加新主题必须同时带歌，
     否则分区页空白）。
- **原创红线**：不抄任何在版权期内的歌词；公版童谣可改写，但改写后逐字过字表。
- **导出面冻结**：`SONGS / SONG_THEMES / SONG_MAP / getSong / charsInSong /
  syllablesOfSongLine / melodyOfSong / verifySongCoverage` 一个不改（消费方
  SongsView + `check-data.mjs` + R8 H2/R9 H1 双探针）。`audio: null` 惯例保留——
  **零音频资产**照旧，旋律 `playMelody()` 合成、人声走系统 TTS。

### 1.3 v2 歌词同步动画（视图契约，全部落在 `SongsView.vue` 单文件）

基线已有：`activeLine` / `activeChar` 逐字推进（唱模式按 bpm × notes 时间轴）、
逐句点读、`syllablesOfSongLine` 的 `at` 协议。v2 定义为三件事：

1. **卡拉OK层**：当前字加动画 class（填色扫过或轻微放大，纯 CSS
   transform/opacity），「已唱过 / 正在唱 / 未唱到」三态可辨；三态**不只靠颜色**——
   当前字另配描边或字重差异（色弱可辨，axe 四主题 critical/serious 0/0 不退）。
   `reducedMotion()` 为真 → 去掉 transform 动画，仅保留三态配色与字重。
2. **读模式接入同一高亮协议**：`speak()` 没有逐字回调是事实——读模式做
   **句级高亮 + 已完成句打勾**，不假装字级精度（「界面如实说明能力边界」的
   既有口径）。
3. **自动跟随**：当前句滚动进视口（`scrollIntoView({ block: 'nearest' })`，
   reducedMotion 时 `behavior: 'auto'`）；sr-only `[aria-live]` 播报当前句文本。

标记（双保险，均为代码级）：`<script setup>` 里
`const ROUND9_H1 = 'lyrics-sync-v2'`（或等价常量）并在模板给同步容器落
`data-song-sync` 钩子（smoke 断言用）；「歌词同步」四字自然出现在界面或 aria 文案里
（三重冗余，探针任一命中即可，但三处都要真实在场）。

记账：沿用 `markSongSung(song.id)`（**唱完整首才记**，翻页不记），`songs` 存档
形状不动；不喂 FSRS（没有作答行为）。

### 1.4 smoke 与回归

- literacy `scripts/smoke.mjs` 追加代码级常量
  `const ROUND9_H1_SMOKE = ROUND8_H2_SMOKE`（沿 `ROUND8_H5_SMOKE` 的写法）+
  interact 段：打开 `/songs` → 断言歌卡 ≥10 → 展开一首 → 断言 `[data-song-sync]`
  在场、三态图例可见 → 无控制台报错。**不真播音频**（无头环境 AudioContext/TTS
  不可靠，断言 DOM 协议而不是声音）。R6/R8 既有 smoke 段一行不动。
- `songs.js` 只被 SongsView（懒加载 chunk）import，主包零增量；`check:bundle` 守。

---

## 2. 契约二 · OCR 基准扩样：手写/低光/复杂背景（H2，所有者 #5）

### 2.1 探针拆解

H2 三个与门：`fixtures/ocr/` 一层目录 `.png` **≥8** &&
`/handwriting|手写/i`（精度脚本源码 + 文件名拼接）&&
`/ROUND8_H4|ROUND9_H2/i`（精度脚本；基线 `ROUND8_H4` 已在头注释与 `--json`
marker 里——**保留它**，同时补 `ROUND9_H2` 双标记）。基线 4 张：
`book-page / warm-light / blackboard / blurry-note`。

### 2.2 图集扩样（`gen-ocr-benchmark.mjs` 追加 SHEETS，生成后冻结入库）

| 文件名（锁定） | tier | 版面要求 |
|---|---|---|
| `handwriting-01.png` | handwriting | 田字格手写体模拟：逐字 ±5° 随机旋转 + 基线抖动 + 字号/字重微变（CSS per-char transform），3–6 个大字 |
| `handwriting-02.png` | handwriting | 手写便签两行：8–10 字、整行轻微歪斜 |
| `lowlight-01.png` | lowlight | 低光照片：深色渐变底 + 低对比字 + 轻噪声 |
| `clutter-01.png` | clutter | 复杂背景：字卡叠在花纹/纹理底上，前景字对比正常 |

- 文件名**必须**以 `handwriting-` / `lowlight-` / `clutter-` 前缀开头
  （`handwriting` 是探针关键词落点之一）；全部直接放在 `fixtures/ocr/` 一层
  （探针不递归，放子目录=白干）。
- 生成约束沿 R8：puppeteer-core 渲染、字体栈固定（环境无真手写字体，
  手写感靠 per-char 几何扰动模拟，脚本注释如实写「模拟手写」——不冒充真实
  手写数据集）；**开发机跑一次、产物提交入库、CI 永不重画**（字体环境差异会让
  基准漂移，入库图 = 冻结基准）。
- 每张 `expect` 3–12 字、全部 ∈ `CHARACTER_MAP`（既有断言
  `splitByLibrary().unknown === 0` 自动覆盖）。

### 2.3 精度脚本 tier 化（`test-ocr-accuracy.mjs`）

- `BENCHMARK` 条目追加 `tier` 字段：既有 5 张（含 `sample-photo`）统一标
  `'print'`——**它们的 expect/keyword/recall/conf 阈值一个字节不动**；新 4 张分标
  `'handwriting' / 'lowlight' / 'clutter'`，脚本内出现中文标签「手写」「低光」
  「复杂背景」（关键词第二落点）。
- **阈值方法论冻结**：先实测、后定标，取实测值往下留一档写死在脚本里，
  **禁 env 放水，之后只许上调**。手写 tier 的召回预期显著低于印刷——如实定低线
  （哪怕 0.3 起步），不许为了分数好看去调 `utils/ocr.js` 运行时识别参数反向拟合
  （R8 §10 红线继承：基准适配引擎现状，不是反过来）。
- `OVERALL_RECALL = 0.9` 的统计范围**锁定为 `tier === 'print'` 集合**：
  难图并入总召回会把总线拉爆（假回归），并入后再调低总线又是放水——两个都不许。
  新 tier 各设独立下限，每张 keyword 至少 1 字。
- `--json` 输出追加 `marker: 'ROUND9_H2'` 与 per-tier 聚合行
  （`tier / images / recall`），供 `acceptance-log-round9.md` 与
  `evidence/r9/ocr/` 引用；`ROUND8_H4` 字样保留在头注释（R9 H2 备用命中 +
  历史可溯）。
- 挂载不变：`test:ocr:accuracy` 已在 literacy `test` 链；新增 4 张约 +4–8 s，
  全链 <90 s 的 R8 豁免线安全。

### 2.4 回归红线

既有 5 张图的字节、阈值、keyword 禁改（冻结基准的意义）；`utils/ocr.js` 的
`OEM.LSTM_ONLY` 与 `preprocess()` 链禁为过基准而调；`CharDetailView.vue` 的
`similarDistractors` 接线（R8 H4 / R7 H2 双探针命中面）不许碰。

---

## 3. 契约三 · 技能图谱推荐路径（H3，所有者 #6）

### 3.1 探针拆解与路径锁定

H3 = `/recommend|nextSkills|推荐|ROUND9_H3/i`（`skill-graph.js` +
`SkillGraphView.vue` 拼接，基线已绿——别把 `nextSkills` 弄丢）&&
`modules/skill-graph/SkillGraphView.vue` **存在于该绝对路径**（禁移动改名）&&
`\bROUND9_H3_SMOKE\b`（math `smoke.mjs` 代码级常量）。R8 H3 同时在跑：
`/skill-graph` 动态路由 + `SKILL_NODES ≥ 10` + `SKILL_EDGES ≥ 1` + 视图联动
ageBand/progress——四条件全部不许退。

### 3.2 数据契约：`skill-graph.js` 追加 `recommendPath`（旧导出面冻结）

既有导出 `SKILL_NODES / SKILL_NODE_MAP / SKILL_LANES / SKILL_EDGES / GRAPH_SIZE /
SKILL_STATUSES / STATUS_MAP / skillStatus / buildSkillGraph / nextSkills` 的签名与
行为**一个不动**（`nextSkills` 既是探针关键词命中面，也是视图「接下来练什么」区的
消费源）。追加：

```js
/**
 * ROUND9_H3 —— 推荐学习路径：从当前存档到「本档该会」的一条有序路线。
 * 与 nextSkills 的区别：next 是「现在就能点开的 4 个入口」，path 是
 * 「按依赖顺序排好的整条路」——先补哪个、再开哪个、最后到哪个目标。
 * 纯函数、确定性（零随机）、只读——推荐永远不写 store：看图谱 ≠ 刷进度。
 *
 * @param {{ mastery?: Record<string, number>, ageBand?: string,
 *           wrongSkills?: Record<string, number>, limit?: number }} input
 *   wrongSkills：技能 id → 错题本未清计数（视图侧从 progress.wrongBookList
 *   按 entry.skill 聚合后传入，函数本身不 import store），可缺省；limit 默认 6。
 * @returns {{ goal: string|null, steps: Array<{ id, name, status,
 *   reason: 'review'|'continue'|'ready'|'prereq', route }> }}
 */
export function recommendPath({ mastery = {}, ageBand, wrongSkills = {}, limit = 6 } = {})
```

算法契约（行为可测，实现自由）：

1. **目标选取**：`inBand`（本档及以下，口径同 `buildSkillGraph`）且未 mastered 的
   节点里，取依赖深度最浅者为 `goal`；全部 mastered → `goal = null`，`steps`
   只含 review 项或为空；
2. **路径展开**：goal 的未掌握依赖链按**拓扑序**排列——任何步骤必须出现在它的
   未掌握 deps 之后；
3. **步骤语义**：learning 节点 → `'continue'`（补弱优先，排最前）；mastered 但
   `wrongSkills[id] > 0` → `'review'`（至多 2 条，错题多者优先）；ready →
   `'ready'`；还锁着但在必经之路上 → `'prereq'`；
4. **确定性**：同输入必同输出；tiebreaker 固定为（depth 升序, mastery 升序,
   id 字典序），**禁 Math.random / 禁 Date**；
5. `steps` 无重复、长度 ≤ limit，每步带 `route`（沿 `SKILL_NODES` 既有字段，
   指向该泳道星球）。

语义红线继承 R7/R8：`ageBand` 只影响目标选取视角，**不锁任何节点**；
「只读推荐，不写回作弊」= 函数零副作用 + 视图不因展示/点击推荐而调用任何
progress action（跳转到星球后照常由玩法页记账）。

### 3.3 视图、校验与 smoke

- `SkillGraphView.vue` 新增「推荐路线」区：有序列表 `<ol data-reco-path>`，
  每步 = 序号 + 技能名 + reason 中文标签（补一补 / 接着练 / 可开练 / 先修）+
  「去练」链接（router-link 到 `step.route`）；`aria-label="推荐路线第 n 步：…"`；
  「接下来练什么」区**保留**（两区语义不同：清单 vs 路线）。reducedMotion 无进场
  动画。图上给路径节点/连线加高亮描边属于可选增强，不设门禁。
- math `check-content.mjs` 追加规则段（既有规则只加不改）：
  ① 空存档 → `steps[0]` 是无依赖 inBand 节点、reason ∈ {ready, prereq}；
  ② 全满存档 → steps 为空或全 review；
  ③ 任意步的未掌握 deps 不出现在它之后（拓扑序断言）；
  ④ 两次同参调用深比较相等（确定性）；
  ⑤ `skill-graph.js` 源文本无 `Math.random`、无 store import。
- math `smoke.mjs`：`const ROUND9_H3_SMOKE = '/skill-graph'`（= 基线实际注册的
  路由 path，math router L112）+ interact 段：断言
  `[data-reco-path]` 在场、至少 1 步、第一步链接可点且路由跳转成功、无控制台
  报错。R8 的技能图谱交互段保留。
- 体积：`skill-graph.js` 仍只被 SkillGraphView（懒加载 chunk）与 Node 门禁引用，
  主包零增量；不新增持久化键。

---

## 4. 契约四 · 跟读 v3 ASR/音素路线（H4，所有者 #8）——追认与冻结

### 4.1 探针拆解与现状追认

H4 = `.agent_workspace/r9-followread-asr-evaluation.md` 长度 >800 **或**
`/phonemeMarks|similarityV2|ROUND9_H4/i` 命中 `useSpeechEval.js` + `speechEval.js`。
#8 已在 `4da6a22`/`bcaf5ad` 合入集成分支：评估文档 15 KB（sherpa-onnx 首选 /
Vosk 轻量对照 / whisper.cpp 上限对照的评估矩阵，以及「不把汉字转写冒充音素评分」
的口径结论）+ `speechEval.js` 追加 `phonemeMarks` / `similarityV2`（带 `ROUND9_H4`
标记）+ `test-speech-eval.mjs` 断言——**探针双通道已双命中**，且与
`round8-architecture.md` §5.2 当年预定的形状一致。本节追认其为 R9 正式契约。

### 4.2 冻结面

- 文档路径与文件名锁死 `.agent_workspace/r9-followread-asr-evaluation.md`
  （探针写死该路径）：后续增补只许追加章节，不许改名、搬家或删减到 800 字符以下。
- `phonemeMarks(reference, heard, lookupPinyin)` / `similarityV2(...)` 导出签名
  冻结；逐字 status 四态 `'hit' | 'tone' | 'near' | 'miss'` 语义冻结
  （tone = 去调同音；near = 声母或韵母同；查不到拼音如实 miss，不猜）；
  `lookupPinyin` 由调用方注入，`speechEval.js` 保持零数据依赖。
- 旧导出（`GRADES` … `evaluate`、`companionReplyForResult`）与既有单测断言
  零改动——它们是 R8 H5 的命中面。

### 4.3 后续接线红线（本轮或后续轮把 PoC 接进 UI 时生效）

- **三档能力链（recognition / recording / listen-only）与隐私契约一字不动**：
  `allowRecognition` 默认 `false`、`VoiceNotice` 在线识别提示不退、录音只存
  内存 Blob；
- `evaluate()` 只在调用方显式传 `lookupPinyin` 时启用 v2 产出，不传则与今天
  逐字节一致（旧单测的结构保证）；
- recording / listen-only 档**不假装有音素信息**；低置信度界面说「没听清」，
  不标红「错误」（评估文档 §1 的口径写进代码行为）；
- 任何 wasm ASR 运行时与模型文件**不入库、不进 `public/`、不进 SW 预缓存清单**
  （离线包 10 MiB 红线）；若做端上试验，模型走显式「按需下载」UI +
  CacheStorage/IndexedDB 缓存，默认关闭、可整体删除。

---

## 5. 契约五 · 绘本社区投稿文档 + 内容质量修稿（H5，所有者 #7）

### 5.1 探针拆解

H5 = `.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md` 长度 >1500 字符 &&
`/投稿|schema|JSON/i`。这是 R6→R7→R8 三轮备忘未清的欠账（`round8-hongen-audit.md`
§R9 备忘 #1「必办或正式除名」），本轮走「必办」。

### 5.2 文档契约：`BOOK-COMMUNITY-SUBMISSION.md` 必备章节

实际长度预期 5 KB+（1500 是探针下限不是目标）：

1. **投稿流程**：GitHub PR / Issue 模板双通道；评审角色（内容审 + 技术审）；
   v1 只定格式与流程，**不开线上上传通道**；
2. **数据 schema**：与 `books/core.js` 实际字段逐一对齐的全字段表——
   `id`（社区段用 `c` 前缀如 `c1`，避开既有 `b` 段）、`title`、`pinyin`、
   `level`(1–6)、`levelName`、`cover`（单个 emoji）、`palette`（两个色值）、
   `summary`、`newChars`、`pages[{ emoji, text, p }]`——并附**一个完整合法的
   JSON 示例**（可直接复制去校验）；
3. **硬约束**（原样引用现行校验器口径，不另造）：正文逐字 ∈ 1820 字表
   （`verifyBookCoverage()` 零越界）、标点白名单 = `books.js` 的 `PUNCTUATION` 集、
   注音 `p` 字段音节-汉字逐一对应、分级语感标准照抄 `books.js` 头注释的六级口径、
   页数建议 4–8 页每页 ≤2 句；
4. **内容红线**：原创或公版改写、无广告与品牌植入、无恐吓暴力、价值观审查点清单；
5. **授权**：投稿即授予项目按仓库 LICENSE（§7.3）分发的许可、署名规则；
6. **合入机制**：维护者把过审 JSON 转成 books/ 侧条目并跑 `check:data` 全绿才算
   收录——本轮**零代码**：不新建 `community.js`、不改 `books.js`（文档轮，
   代码接线归后续轮次）。

### 5.3 质量修稿（Brief 质量项，≤20 条；无探针，入验收记录）

- **字源批量文案抽查**：从 `DERIVED`（735 字）抽查模板感过重条目（origin/evolve
  两句与 `SEMANTIC` 形旁语义表逐字雷同、读来像填空的）。**修法只有一条路**：
  改 `scripts/data/etymology-seed.txt` 对应行或 `gen-etymology.mjs` 的 `SEMANTIC`
  表 / 成句模板 → `npm run gen:etymology` 重新生成 → `check:data` 61 项全绿、
  `ETYMOLOGY_CHARS` ≥800（R8 H1 探针）不动。**禁手改生成物**（`etymology-derived.js`
  / `etymology-index.js` 文件头「请勿手改」声明现行有效）。
- **u59–u99 剧情走查**：与 u1–u58 手写质感一致性——直接改 `unit-stories.js`
  字面值；**键一个不动**（R8 H2 用 `/\bu(\d+)\s*:/` 扫源码）、长度守 12–44 字
  （`check-data.mjs` 现行规则）、不出现兜底句式。
- 修稿清单落 `.agent_workspace/r9-content-quality-log.md`：逐条
  「字/单元 · 问题 · 改法」。≤20 条是范围控制不是 KPI——宁缺毋滥，
  没毛病的不硬挑。

---

## 6. 契约六 · Lighthouse 版本锁 CI + 证据包 + Android 清单 + math check-bundle（H6，所有者 #9）

### 6.1 探针拆解与问题定位

H6 = `/lighthouse-ci|ACCEPTANCE_MIN_LH/i`（`scripts/lighthouse-ci.mjs` 内容 +
根 `package.json` 拼接）&& `evidence/r9/` 递归 `.json` ≥2。本轮要堵的洞（基线实测）：
**lighthouse 不在 lockfile**（`which lighthouse` 为空、`package-lock.json` 零命中），
`acceptance.sh` 找不到 CLI 时打 `[SKIP]` 继续放行——「版本没锁」+「缺席即跳过」
是两个 CI 假绿源，R7/R8 的 95 分记录全靠当时手工装的全局 CLI。

### 6.2 版本锁（两件套，必须同一 commit）

1. 根 `package.json` devDependencies 加 `"lighthouse": "12.8.2"`
   （**精确版本，无 `^`**；12.8.2 = R7/R8 实测记录版本。若该版本在当前 npm 环境
   装不上，以实际锁定版为准并在 evidence README 与本文档补记）→ lockfile 锁定，
   `npm ci` 零猜测可复现；
2. `scripts/lighthouse-ci.mjs`（新，根 scripts/）：启动即断言
   `node_modules/lighthouse/package.json` 的 `version === LOCKED_LH_VERSION`
   （脚本内写死的常量），不匹配或缺席一律 **exit 1——没有 SKIP 分支**。
   升级 LH = 改常量 + lockfile + 重新定标三件事一个 commit。

### 6.3 `lighthouse-ci.mjs` 行为契约

- 测法口径与 `acceptance.sh` 逐项一致：build 后 gzip 静态服 + headless Chrome +
  mobile simulate。实现推荐直接设
  `ACCEPTANCE_EVIDENCE_DIR=.agent_workspace/evidence/r9/lighthouse` 复用
  `bash scripts/acceptance.sh` 子流程（它本就会把 `lighthouse-<slug>.json` 原始
  报告落进该目录），独立起服跑 CLI 亦可——**两条路都必须把双 App 原始 JSON 落进
  `evidence/r9/`**（≥2 份 JSON 探针由此满足）；
- 阈值写死：P ≥ 0.95、A ≥ 0.90、BP ≥ 0.90（= R8 验收线；比 `acceptance.sh` 的
  `ACCEPTANCE_MIN_LH_*` 默认 0.90 更严），**只许上调、不读 env 放水**；
- 输出人读汇总行（`识字 P/A/BP：97 / 100 / 100` 形态）供 log 回填引用；
- 根 `package.json` 注册 `"check:lh": "node scripts/lighthouse-ci.mjs"`
  （脚本值里的 `lighthouse-ci` 字样天然命中探针）；**不串进 `npm test`**
  （LH 一跑数分钟，挂 test 链拖死日常开发）——挂终验链：
  `npm test → check:round9 → check:round8 → check:lh → test:round3 → build:all`。
- `acceptance.sh` 本身**不改行为**（它的 SKIP 语义留给无 Chrome 的裸环境；
  强制性由 `check:lh` 承担）。

### 6.4 `evidence/r9/` 路径规范（锁定，全体引用这一份）

```text
.agent_workspace/evidence/r9/
  README.md                        ← #10：逐文件索引 + SHA-256 + 工具版本 + 复现命令
  lighthouse/lighthouse-literacy-app.json   ← #9（acceptance.sh 原生命名）
  lighthouse/lighthouse-math-app.json       ← #9
  axe/…                            ← #9（四主题 axe 输出，可选但建议——顺手清 D-4 备忘）
  checks/round8.txt round9.txt android.txt  ← #10：门禁逐行输出快照
  ocr/accuracy.json                ← #5（test-ocr-accuracy --json 快照，可选）
```

JSON 原样入库不精简；文件名小写连字符；所有权按子目录分区，两人不碰同一文件。

### 6.5 Android 真机走查清单：`.agent_workspace/r9-android-device-checklist.md`

每项「预期 / 实测 / 判定」三列模板（文档先行，真机实测由人工回填，回填前判定列
写「未测」而不是留空——别造出新的占位符探针命中）。覆盖面：相机权限流
（首拒 / 再授权 / 系统设置回跳）、OCR wasm 在 WebView 的耗时与内存、TTS 中文
语音有无与降级提示、儿歌 WebAudio 自动播放策略、跟读麦克风权限、返回键导航栈、
断网离线全功能、深色/护眼主题渲染、低端机（≤4 GB）帧率观感。机型矩阵至少
「低端 + 中端」两档。

### 6.6 math check-bundle（清 R8 审计门禁联动提醒 #7 的流程债）

`apps/math-app/scripts/check-bundle.mjs`（新）：范式照抄 literacy 同名脚本
（入口 chunk + 同步依赖），预算写死**首屏 gzip < 250 KB**（对齐 `acceptance.sh`
既有红线；当前实测 ~77 KB，余量 3×）；math `package.json` 注册 `"check:bundle"`
并串进 math `test` 链（build 之后）。预算只许下调。

### 6.7 红线

不调 `acceptance.sh` 的 `MIN_LH_*` 默认与任何既有阈值；不删 aria 结构换分；
不动 `vite-offline-plugin`；axe 四主题 critical/serious 0/0 维持；识字 420 KB
预算不放；`evidence/r8/` 只读。

---

## 7. 契约七 · 发布工程：R8 闭合 + Round 9 报告 + RELEASE-CHECKLIST + LICENSE（H7，所有者 #10）

### 7.1 R8 编排闭合（Brief P0，先于 Round 9 章动手）

- `GLOBAL-SUMMARY-REPORT.md` 基线还有 **9 处 ⏳**：模块表 7 行
  （L-M6 #4、L-M9 #8、L-M10 #7、L-M11 #5、L-M15 #9、M-M1 #6、M-M16 #9）+
  差异化维度表 D-4 一行 + 图例句。全部翻 `✅`（D-4 以 #9 落盘的四主题 axe 证据
  为翻转依据），图例句同步改写成历史注记；31/31 全 ✅。
- **连环雷点名**：`check:round7` H7 的状态正则只认 `✅` 或
  `⏳ 待 R(7|8) 子代理 #4-10`——**写「⏳ 待 R9 …」= R7 H7 红 → R8 H8 红 →
  R9 H8 红，三连杀**。R9 终态没有合法的「在途」写法，只能全 ✅；这就是 #10 必须
  最后合并、翻行必须以对应功能已合入为前提的原因。每行证据列必须含反引号代码
  引用（R7 H7 逐行验 `row.evidence.includes('\`')`）。
- 占位反向命中面并集（R7 + R8 探针）：`待回填 / TODO / TBD / [P/F] / ⬜` 与 `❌`
  全文为零；`evidence/r8` 字样保留（R8 H7 还在跑）；首行 Model slug、
  round6/round7 两份审计文件名引用不删。
- 终验链重跑（`npm test → test:round3 → build:all → sync:android →
  check:android`）并复核 `acceptance-log-round8.md`——§2.1 斜杠三连格式是
  R8 H6 的活探针，别在「识字/数学」字样前新增数字三连行。

### 7.2 Round 9 章（R9 H7 上半）

`GLOBAL-SUMMARY-REPORT.md` 追加 Round 9 终态章：含字面 `Round 9`；对标叙事聚焦
本轮五个翻转位（L-M5 投稿文档、L-M11 儿歌 v2、L-M10 扩样、L-M9 v3 路线、
M-M1 推荐路径）+ `check:round9` 8/8 输出全文粘贴 + `evidence/r9` 索引。
历史数字不删改；实测值只认终验链输出。

### 7.3 `RELEASE-CHECKLIST.md`（R9 H7 下半：>800 字符 + LICENSE/发布/证据关键词）

必备章节（>800 是探针下限，预期 3 KB+）：

1. **版本与冻结**：版本号方案（建议 `v0.9.0`+tag 约定，或语义化自定并记录）、
   冻结 SHA；
2. **发布门禁链**（逐项附全绿证据路径）：`npm test → check:round9 →
   check:round8 → check:lh → test:round3 → build:all → sync:android →
   check:android`；
3. **LICENSE 确认**：基线仓库根**无 LICENSE 文件**（实测）——本轮必须落根
   `LICENSE`。默认建议 MIT（与全部依赖兼容、工程惯例）；清单里留 owner 复核项：
   「若另选许可证，替换文件 + 本行打钩」。原创内容资产（剧情/儿歌/绘本文本）随
   仓库许可或单独 CC BY 4.0，清单记录决定。`THIRD_PARTY_NOTICES.md` 复核：
   tesseract.js（Apache-2.0）、OpenMoji（CC BY-SA 4.0 **署名义务**）、
   hanzi-writer、字体条款；
4. **对外声明草案**：教育定位与适用年龄、全程离线与隐私（录音不出端、无账号
   无采集无遥测）、非替代教学的边界表述、OpenMoji 署名、开源致谢；
5. **证据包冻结**：`evidence/r8` + `evidence/r9` 索引、SHA-256、工具版本；
6. **Android 产物**：APK 体积表、真机清单（§6.5）结果引用、最低系统版本；
7. **已知限制与除名项**：社区投稿线上通道（v1 文档只定格式）、真·声学音素诊断
   （引用 §4 评估文档的口径边界）等，如实列出。

### 7.4 顺序纪律

#10 分两拍：R8 闭合动作（§7.1）不依赖 R9 功能可先行；Round 9 章与 31/31 翻行
必须等 #4–#9 全部合入、`check:round9` 前 7 项全绿后收口。`LICENSE` 文件随
第一拍落地即可（不依赖功能）。

---

## 8. 文件所有权与冲突矩阵

| 热点文件 | 触碰者 | 隔离规则 |
|---|---|---|
| literacy `data/songs.js`、`views/SongsView.vue` | #4 独占 | 导出面与存档 `songs` 形状冻结，只加歌与 v2 层 |
| literacy `scripts/smoke.mjs` | #4（`ROUND9_H1_SMOKE` 常量 + 交互段） | 纯追加，R6/R8 既有段不动 |
| literacy `scripts/gen-ocr-benchmark.mjs`、`scripts/fixtures/ocr/*`、`scripts/test-ocr-accuracy.mjs` | #5 独占 | 既有 5 图字节与阈值冻结，只追加 |
| literacy `data/unit-stories.js`（修稿）、`scripts/data/etymology-seed.txt`、`scripts/gen-etymology.mjs`、`data/etymology-*.js`（重生成） | #7 独占 | 键与导出面不动；生成物只经生成器 |
| `.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md`、`r9-content-quality-log.md` | #7 新建 | — |
| `.agent_workspace/r9-followread-asr-evaluation.md`、literacy `utils/speechEval.js`、`scripts/test-speech-eval.mjs` | #8 独占（已合入，只许追加） | 旧导出与旧断言冻结（§4.2） |
| math `data/skill-graph.js`、`modules/skill-graph/SkillGraphView.vue` | #6 独占 | 旧导出冻结，追加 `recommendPath` 与推荐区 |
| math `scripts/check-content.mjs`、`scripts/smoke.mjs` | #6（各一段） | 既有规则只加不改 |
| math `scripts/check-bundle.mjs`、math `package.json` | #9 新建/独占 | — |
| 根 `package.json`、`package-lock.json`、`scripts/lighthouse-ci.mjs` | #9 独占 | **别的分支不碰根 package.json**（lockfile 冲突高发区） |
| `.agent_workspace/evidence/r9/` | #9（lighthouse/ axe/）、#5（ocr/ 可选）、#10（checks/ README.md） | 按子目录分区（§6.4） |
| `.agent_workspace/r9-android-device-checklist.md` | #9 新建 | — |
| `GLOBAL-SUMMARY-REPORT.md`、`RELEASE-CHECKLIST.md`、根 `LICENSE`、`acceptance-log-round8.md`（复核）、`acceptance-log-round9.md` | #10 独占 | #2 审计只写自己的 audit 文件 |

**合并顺序**：#8 已入 → #4 / #5 / #6 / #7 四条线互不依赖可乱序（smoke/check 文件
交叉点按上表「各自追加」先到先得）→ #9（要在全量功能上量分，且动根
package.json/lockfile，压到功能组之后合以减冲突）→ #10 收口（§7.4 两拍）。
#3 的验收强化随时可合，但**探针只许加严**：已定契约的命中面（路径、导出名、
标记词、格式）如需变更，必须回改本文档。

---

## 9. 契约 → 门禁映射

| 契约 | check:round9 探针 | 所有者 | 回归红线 |
|---|---|---|---|
| §1 儿歌 v2 | H1：`SONGS.length ≥ 10` + `ROUND9_H1`（视图 + smoke 代码级） | #4 | R8 H2 儿歌三条件不退；`songs` 存档形状冻结；零音频资产；歌词逐字过字表 |
| §2 OCR 扩样 | H2：fixtures 一层 ≥8 张 + handwriting 双落点 + `ROUND8_H4`/`ROUND9_H2` | #5 | 既有 5 图与阈值冻结；总召回只统计 print tier；运行时识别参数不动 |
| §3 图谱推荐 | H3：关键词（基线已绿）+ 视图路径锁死 + `ROUND9_H3_SMOKE` | #6 | R8 H3 四条件不退；`recommendPath` 纯函数确定性；不写任何 store |
| §4 跟读路线 | H4：评估文档 >800 或 `phonemeMarks`/`similarityV2`（已双命中） | #8 | 三档链与隐私默认不退；旧单测冻结；模型不入库 |
| §5 投稿文档 | H5：BOOK-COMMUNITY-SUBMISSION >1500 + `/投稿\|schema\|JSON/i` | #7 | 本轮零代码；修稿只走生成器/字面值；R8 H1/H2 水位不动 |
| §6 Perf CI | H6：lighthouse-ci 文件+注册双真实 + evidence/r9 ≥2 JSON | #9 | 版本锁死无 SKIP；阈值只升；根 package.json 独占；evidence/r8 只读 |
| §7 发布 | H7：报告含 `Round 9` + RELEASE-CHECKLIST >800 + 关键词 | #10 | R7 H7 / R8 H7 / R9 H7 三重探针并集合规；「⏳ 待 R9」三连杀禁写 |
| 全体 | H8：`check:round8` 8/8（内含 R7 8/8、R6 7/7 级联） | 每个分支 | 合并前 `npm test` 全绿 |

---

## 10. 明确不做（Out of scope）

- 儿歌不引入音频资产/在线曲库、不做录音跟唱评分（跟读的地盘）、不为 v2 动画引入
  新动画库依赖、不动 `songs` 存档形状之外的持久化；
- OCR 不为过基准调运行时识别参数、不做拍照端到端 UI 自动化精度回归（基准量引擎，
  UI 链归 smoke）、不把 fixtures 挪进 `public/`、不采集真实儿童手写样本
  （合成模拟并如实标注）；
- 图谱推荐不写任何 store、不做自动开练（推荐 ≠ 代点）、不动 `curriculum.js` 节点
  与 deps、不动星球解锁经济（`starsToUnlock`）、不引图算法库；
- 跟读本轮不把 wasm ASR 接进生产 UI、不下载/入库任何模型、不改三档能力链与
  `allowRecognition` 默认值、不把汉字转写冒充音素评分（评估文档口径）；
- 绘本投稿本轮不写上传代码、不建 `community.js`、不改 `books.js`；
- Perf 不调 `acceptance.sh` 既有阈值、不删无障碍结构换分、不动
  `vite-offline-plugin`；LH 版本升级必须「常量 + lockfile + 重定标」三件套同
  commit；
- 发布不写「⏳ 待 R9」、不删改历史数字、不伪造实测；LICENSE 的许可证选择保留
  owner 复核项，但根 LICENSE 文件本轮必须落地；
- 不改识字主存档 `happy-literacy:v1` 顶层结构与 FSRS 参数；不动数学
  `mathquest/settings` 的 sanitize 白名单。
