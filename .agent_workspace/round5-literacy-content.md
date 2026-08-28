# Round 5 架构契约 · 识字内容体量（L-M1 / L-M5 / L-M8 / L-M6 / L-M12）

> 面向实现子代理 #4（1000 字）、#6（60 成语 + 字源）、#7（3 小游戏）的**实现契约**，
> 并对已合入的 #5 成果（30 绘本，commit 64f93ac）做**契约固化**。
> 本文只定义数据 schema、文件边界、门禁口径与路由契约；文案、故事情节、视觉细节由实现方自由发挥。
> 基线：`cursor/openmoji-integration-9f67` @ aacd996（撰写时集成分支已推进至 804df86，
> 本文所有「已落地」标注以 804df86 实测为准）· App：`apps/literacy-app/`
> 关联：`SURPASS-HONGEN-MASTER-PLAN.md` §2、`ROUND5-BRIEF.md`、
> `round4-literacy-statemachine.md`（状态机契约，字源播放器必须与其兼容）

---

## 0. 现状与目标差距

| 模块 | 现状（804df86 实测） | Round 5 目标 |
|---|---|---|
| L-M1 字库 | 500 字：`char-index.js`（轻索引，进主包）+ `chars/u1–u33.js`（详情懒加载） | **1000 字**，两层结构不变，新增 u34–u66（未落地，§1） |
| L-M5 绘本 | ✅ **已合入 64f93ac**：30 本 · 6 级 × 5 本 · 240 页 · 正文 351 个不重复字全落在 500 字表内 | 契约固化 + 门禁补强（§2） |
| L-M8 成语 | `idioms.js` 20 条（四字 + 三段故事 + 情景 quiz） | **60 条**，schema 不变（未落地，§3） |
| L-M6 字源 | 无字源动画（部首模块只有静态讲解） | pipeline v1：**≥50 字**可播放「实物→古字形→楷书」（未落地，§4） |
| L-M12 游戏 | 仅 `/listen` 听音识字 | **+3 款**：迷宫 / 配对 / 拼字，路由可达 + smoke 断言（未落地，§5） |

**不变式（全部实现子代理必须保持）**：
- `characters.js` 对外 API 不变：`CHARACTERS / CHARACTER_MAP / TOTAL_CHARACTERS / UNITS / UNIT_MAP /
  charsOfUnit / getCharacter / loadUnitDetails / getUnitDetails / loadCharacter / getLoadedCharacter / loadAllCharacters`。
  全 App（进度、FSRS、家长报表、状态机、绘本校验）都消费这一层，只加数据不改签名。
- progress store 以 `char` 为键记录学习事件，加字**零迁移**；`migrate()` 只在引入新 state 字段时补回落。
- 既有门禁全绿是 push 前提：`npm test`（= test:srs + check:data + build + check:bundle + smoke）。
- 首屏 JS 预算 `check-bundle.mjs` 的 `ENTRY_JS_BUDGET_KB = 420` **不放宽**。任何人不得在主包
  静态 import `chars/*.js` 或其他大数据新文件（绘本正文现状在主包，见 §2.4 体积预案）。
- 内容一律「脚本可校验」：新增数据必须被 `check:data` 新断言覆盖，禁止手搓无校验 JSON。

---

## 1. L-M1 · 字库 500 → 1000（子代理 #4）

### 1.1 两层结构的扩展方式（延续 Round 4 设计，不另起炉灶）

```
char-index.js      ROWS 追加 500 行（u34–u66），字段顺序不变：
                   [汉字, 拼音, 声调, 单元, 部首 id, 笔画, 卡片图标]
chars/u34.js …     每单元一个详情包，default export：
chars/u66.js       { 汉字: { meaning, words: [{w,p}...], sentence: {t,p} } }（与 u1–u33 同形）
characters.js      UNITS 追加 u34–u66 条目（id/name/emoji/color/desc，color 轮转既有 5 个 seed token）；
                   DETAIL_LOADERS 显式追加 33 行 `u34: () => import('./chars/u34.js')`
                   —— 保持显式映射，禁用 import.meta.glob（Node 门禁脚本要能直接 import）。
```

- 新单元 **u34–u66 共 33 个**，每单元 12–16 字、合计恰好 500 字（与现有密度 500/33 一致）。
- 单元主题延续「生活场景聚类」命名法（如：菜市场 / 天气播报 / 交通工具 / 反义词对对碰 /
  形声字家族…），主题文案实现方定，但 **desc 必填**（首页地图卡片渲染依赖）。
- 家长中心「学习计划」的单元选择（Round 4 成果 ec1cfdc）直接消费 UNITS，新单元自动出现，零改动。

### 1.2 选字标准（可被审计）

1. 基线序：《通用规范汉字表》一级字 × 儿童高频语料序，排除已收录的 500 字。
2. **笔顺数据覆盖是硬条件**：`gen-hanzi-data.mjs` 的 `requiredChars()` 缺笔顺即构建失败，
   所以每个候选字必须存在于 `hanzi-writer-data`（devDependency，makemeahanzi 派生）。
   选字脚本先过一遍覆盖检查再定稿，不许上线后靠回退兜底。
3. 声调轻声记 `5`；多音字取该单元语境读音（与组词/例句一致，check:data 会对拼音）。

### 1.3 事实基线同步：`shared/data/common-hanzi.json`

- 该文件是 monorepo 字表事实基线（`schemaVersion/title/language/license/source/characters[]`），
  当前 500 条。**必须同步扩到 1000 条**，每条至少 `character` + `pinyin`，与 char-index 一致。
- `check-data.mjs` 现有交叉校验（基线字必须在语料且拼音一致）自动覆盖新字，不需要新写。
- 扩充必须走脚本：新增 `apps/literacy-app/scripts/gen-charset.mjs`（一次性也要进库），
  输入候选字清单 → 输出 char-index 行模板 + common-hanzi 条目，人工补教学包装后由 check:data 定稿。

### 1.4 门禁与体积

| 门禁 | 改动 |
|---|---|
| `check-data.mjs` | `TOTAL_CHARACTERS >= 500` 阈值提到 **1000**；其余断言（详情包全覆盖、stray 检查、拼音交叉）自动生效 |
| `check-round5.mjs` | 已就绪（读 `TOTAL_CHARACTERS >= 1000`），不改 |
| `check-bundle.mjs` | 420 KB 预算不变。char-index 新增 500 行 ≈ 27 KB 源码（gzip 后 ~8 KB），预算内；若实测超线，把 ROWS 按 u1–u33 / u34–u66 拆两个文件再在 char-index 拼接（导出不变），不许直接调预算 |
| `gen-hanzi-data.mjs` | 零改动，自动跟随 CHARACTERS + 基线裁剪笔顺 JSON（1000 字 ≈ 3–4 MB public 静态资源，不进 JS 包） |

### 1.5 顺手清理（P1，可选）

`src/data/character-index.js` 是 16 单元时代的遗留副本，**全仓无引用**——确认后删除，
避免后来者把新字加错文件。

---

## 2. L-M5 · 分级绘本 30 本（已落地 64f93ac，本节为契约固化 + 补强）

### 2.1 落地形态（后续加书者必须遵守的 schema）

```js
{
  id: 'b6',                    // b1..b30 连续编号，不复用不跳号
  title, pinyin,               // 书名 + 整句拼音
  level: 1..6,                 // 阅读分级（§2.2）
  levelName: '第 N 级 · xxx',  // 书架分组标题
  cover: '📚', palette: [c1, c2],
  summary,                     // 一句话导读
  newChars: ['字', ...],       // 本书重点生字，必须 ∈ CHARACTER_MAP
  pages: [{ emoji, text, p }]  // ≥5 页；每页 emoji / 正文 / 整页拼音必填
}
```

### 2.2 分级口径（落地定案，取代早期「单元前缀上限」草案）

分级 = **叙事复杂度阶梯**，6 级 × 5 本：
L1 一句一行 → L2 出现对话 → L3 写完整的一天 → L4 起承转合 → L5 多角色 → L6 接近小小章节书。

用字的硬约束只有一条（也是 brief 的验收口径）：**正文与 newChars 全部 ∈ `CHARACTER_MAP`
∪ `PUNCTUATION` 白名单，`verifyBookCoverage` 零越界**。分级不与单元序挂钩——
30 本全部落在稳定的 u1–u33（500 字）内，**刻意不使用 #4 的 u34+ 新字**，
使绘本与 1000 字扩展的合并顺序完全解耦；Round 6 扩到 130 本时新增书目才允许消费新字。

### 2.3 已落地门禁（64f93ac 写入 `check-data.mjs`，任何人不得回退）

```
✓ BOOKS.length ≥ 30
✓ 分级覆盖 ≥3 级，且每级 ≥3 本（书架不断层）
✓ 每本 ≥5 页；每页有 emoji / text / 拼音
✓ 每本 title/pinyin/summary/cover/levelName 齐全，palette 恰 2 色
✓ newChars 全部 ∈ CHARACTER_MAP（越界即门禁失败）
✓ 正文逐字过字表（verifyBookCoverage 同源逻辑）
```

### 2.4 补强项（P1，收尾子代理 #10 或后续加书者带上）

1. `newChars ⊆ 正文实际出现的字`（当前只查「在表内」，没查「在书内」——重点字点开
   却不在故事里，教学动线是断的）。
2. 每页 text 长度上限断言（建议 ≤ 26 字，L6 放宽到 32），防止后续投稿书爆版式。
3. 体积预案：30 本 ≈ 60 KB 源码可留主包；Round 6 冲 130 本前必须拆
   `books-index.js`（书架轻信息）+ `books/bN.js`（正文懒加载，复制 DETAIL_LOADERS 模式），
   `BooksView/BookReadView` 改 `loadBook(id)`。本轮不做，先立此存照。

---

## 3. L-M8 · 成语 20 → 60（子代理 #6）

### 3.1 schema 不变，规则重申

- 只收**四字**成语（逐字拆解卡固定四格）；`chars` 恰好 4 项且拼接 == `word`。
- `story` 恰好三段（起因/经过/道理），每段带 emoji；`quiz.options` 3 项、`answer` 为合法下标、`tip` 必填。
- `id` 用拼音首字母缩写（如 `wybl`），撞车时尾缀数字；40 条新增 id 不得与现有 20 条冲突。
- 候选池：`shared/data/idioms.json` 现有条目优先，不足 60 时**同步扩充该 JSON**（它是共享基线），
  仍只收四字条目。
- 主题覆盖建议（非门禁）：寓言 / 动物 / 数字 / 自然 / 品格五类都有分布，方便 IdiomsView 之后做筛选。

### 3.2 门禁增量（`check-data.mjs`，现有成语断言旁追加）

```
✓ IDIOMS.length ≥ 60；id、word 双唯一
✓ 每条 word 恰 4 字且全为汉字；chars 长度 4 且逐字等于 word
✓ story 恰 3 段；quiz.answer ∈ [0, options.length)；pinyin 按空格切分恰 4 个音节
```

成语用字超字表属预期（现状注释已定调：只认读不书写），`gen-hanzi-data.mjs` 的
`extraChars()` 会自动带上有笔顺数据的成语字，缺的只降级不阻断——零改动。

---

## 4. L-M6 · 字源动画 pipeline v1（子代理 #6）

### 4.1 目标与总体设计

≥50 个字可播放「实物 → 古字形 → 楷书」三段演变。**不引入位图/视频资源**，三段素材全部
程序化：emoji（已有 OpenMoji 体系）→ 手工/脚本整理的古字形 SVG path → hanzi-writer 现场
绘制楷书（已有离线笔顺数据）。GSAP 编排，离线可用，包体可控。

### 4.2 数据契约（新文件 `src/data/etymology.js`，**懒加载**）

```js
// 由 EtymologyPlayer 动态 import()，不进主包。
export const ETYMOLOGIES = {
  日: {
    type: 'pictograph',            // pictograph 象形 | ideograph 指事 | compound 会意 | phonosemantic 形声
    typeLabel: '象形字',
    hint: '像一轮圆圆的太阳',       // 一句儿童语言的字源解说
    emoji: '☀️',                    // 第一幕：实物
    glyph: { path: 'M…', viewBox: '0 0 100 100' },  // 第二幕：古字形（单条 SVG path，线稿风格）
    narration: [                    // 三幕各一句，live region + TTS 复用
      '古人抬头看到圆圆的太阳。',
      '就把它画成一个圈，中间加一点。',
      '慢慢写着写着，变成了今天的「日」。'
    ]
  },
  // …
}
export const ETYMOLOGY_CHARS = Object.keys(ETYMOLOGIES)
```

- 第三幕不存数据：楷书由 `HanziStrokeBox` 同款 hanzi-writer `animateCharacter()` 现场画。
- 主包按钮显隐需要一份轻量字集：新增 `src/data/etymology-index.js`（仅导出
  `ETYMOLOGY_CHARS` 字符串数组 + `hasEtymology(char)`，<1 KB 进主包），
  与 `etymology.js` 的 keys 一致由 check:data 核对。

### 4.3 生产管线（脚本必须进库）

```
scripts/gen-etymology.mjs
  输入1  makemeahanzi dictionary.txt 的 etymology 字段（type/hint 底稿）
         —— 数据 vendored 成 shared/data/etymology-source.json（只留字表内 ≥50 字的条目）
  输入2  人工儿童化改写的 narration / glyph path（维护在同一 JSON）
  输出   src/data/etymology.js + etymology-index.js（生成文件带「勿手改」头注释）
```

- 选字优先级：象形/指事 > 会意 > 形声；优先取 u1–u10 高频字（日月山水火木口目耳手…），
  孩子最早学的字最值得配故事。
- **License 义务**：makemeahanzi（Arphic Public License / GFDL）派生数据入库时，
  `NOTICES` 文件必须新增条目（Round 3 已有 NOTICES 体系，照格式补一行）。

### 4.4 播放器契约（新组件 `components/EtymologyPlayer.vue`）

| 项 | 约定 |
|---|---|
| props | `char: String`（内部自查 ETYMOLOGIES，无数据渲染空状态） |
| emits | `done` / `skipped` |
| 三幕编排 | GSAP timeline：emoji 入场停留 → 交叉淡化到 glyph path 描线（stroke-dashoffset）→ 淡出、hanzi-writer 楷书动画收尾 |
| 跳过 | 常驻「跳过 ⏭」按钮；`data-motion="reduced"` 时**不建 timeline**，三幕并排静态展示 + 文字，行为语义一致（沿用 R4 §4 usePhaseTransition 的姿态） |
| a11y | 每幕切换向 `role="status"` live region 写 narration 该句；按钮可聚焦、Esc 关闭浮层 |
| 卸载 | timeline `kill()`，hanzi-writer 实例销毁 |

### 4.5 挂载点（与 Round 4 状态机契约兼容）

- `CharDetailView` **intro 阶段**内加「📜 字的故事」按钮（`hasEtymology(char)` 为真才显示），
  点开浮层播放。**不新增 phase、不改 useCharFlow 转移表**——字源是 intro 的可选增强，
  看完/跳过都回到 intro，照常 `ADVANCE`。
- `RadicalsView` 部首详情页可复用同一播放器（P1 可选）。

### 4.6 门禁增量（`check-data.mjs`）

```
✓ ETYMOLOGY_CHARS.length ≥ 50，且与 etymology.js keys 完全一致
✓ 每条 char ∈ CHARACTER_MAP；type ∈ 四类枚举；narration 恰 3 句非空
✓ glyph.path 非空且以 M 开头（防呆），viewBox 合法
```

---

## 5. L-M12 · 3 款新识字小游戏（子代理 #7）

### 5.1 路由契约（`router/index.js` 追加，全部懒加载）

| 路由 | name | 视图 | meta | 玩法一句话 |
|---|---|---|---|---|
| `/game/maze` | `game-maze` | `views/GameMazeView.vue` | `{ title: '汉字迷宫', emoji: '🌀' }` | 5×5 网格走迷宫：每步按提示音/图从相邻格里踩正确的字铺路，6 步到终点 |
| `/game/match` | `game-match` | `views/GameMatchView.vue` | `{ title: '翻牌配对', emoji: '🎴' }` | 4×4 翻牌记忆：字 ↔ emoji（或字 ↔ 拼音）8 对配对 |
| `/game/build` | `game-build` | `views/GameBuildView.vue` | `{ title: '拼字工坊', emoji: '🧩' }` | 部首 + 部件拼合体字（氵+可=河），6 题一局 |

既有 `/listen` 不动；`/game/listen` 重定向不动。HomeView 增「游戏乐园」分区，
听音 + 3 款新游戏共 4 张入口卡（含各自 bestStreak/plays 小字）。

### 5.2 出题字池（三款共用规则）

```
pool = progress 已学字（learnedChars，课程顺序） → 不足 12 个时用 CHARACTERS 前缀补足
干扰项 = 形近字（char-index 同部首/同笔画邻近） > 同单元字 > 池内随机
```

一局固定题量：迷宫 6 步 / 配对 8 对 / 拼字 6 题。答错不罚站：错了抖动 + 提示重选，
连错 2 次自动高亮正确项（挫败感控制，延续 R4 描红示范精神）。

### 5.3 拼字工坊数据（新文件 `src/data/compounds.js`）

```js
export const COMPOUNDS = [
  // { result: '河', parts: ['氵', '可'], radicalId: 'shui', hint: '和水有关' },
]
```

- ≥40 组；`result` 必须 ∈ CHARACTER_MAP；`radicalId` 必须过 `getRadical`；
  parts 用显示用部件字符（不要求都在字表）。check:data 逐条校验以上三点。

### 5.4 进度记账（`stores/progress.js` 增量，字段名以本契约为准）

```js
// state 新增（migrate 回落各计数为 0 的骨架，与 listen 同款）
games: {
  maze:  { plays: 0, right: 0, wrong: 0, bestStreak: 0 },
  match: { plays: 0, right: 0, wrong: 0, bestStreak: 0 },
  build: { plays: 0, right: 0, wrong: 0, bestStreak: 0 },
},
// 新增动作：一局结束调用一次；对错逐题仍走既有 recordAnswer(char, ok)（喂 FSRS/掌握度）
function recordGameRound(gameId, { right, wrong, bestStreak }) {}
```

- 逐题判定继续用 `recordAnswer(char, ok)`——三款游戏都是真实学习事件，必须进掌握度与
  复习队列；`recordGameRound` 只管游戏侧统计与徽章素材。
- 徽章联动（P1）：`data/badges.js` 加「三款游戏各玩一局」「配对零失误」两枚，走 R4 §3 机制。

### 5.5 a11y 与动效底线（继承 R3/R4 成果，不回退）

- 全键盘可玩：迷宫方向键移动 + Enter 确认；配对 Tab/Enter 翻牌；拼字部件为 `<button>`。
- 判定结果写 live region；`data-motion="reduced"` 时去除位移动画，逻辑完整。
- 音效走既有 `sfx`，庆祝走 `CelebrationLayer` 且可跳过。

### 5.6 smoke 断言（`scripts/smoke.mjs`）

ROUTES 追加三条路由；每款游戏至少一个交互断言（点击一个选项/翻一张牌，控制台零报错）。
这是 brief 的「路由可达 + smoke 断言」验收口径。

---

## 6. 验收清单（供子代理 #3 acceptance-log-round5 引用）

| # | 验收项 | 验证方式 |
|---|---|---|
| C1 | 字库 ≥1000，索引/详情包/基线 JSON 三方一致 | `check:data` + `check:round5` |
| C2 | 首屏 JS ≤ 420 KB，chars 详情包全部为独立 chunk | `check:bundle` |
| C3 | 绘本 ≥30、零越界，64f93ac 已落地断言不回退 | `check:data`（§2.3） |
| C4 | 成语 ≥60，schema 断言全过 | `check:data`（§3.2） |
| C5 | 字源 ≥50 字可播放，reduceMotion 静态降级，NOTICES 已补 | `check:data`（§4.6）+ smoke + 人工抽查 |
| C6 | 三款游戏路由可达、可交互、零控制台报错 | smoke（§5.6） |
| C7 | 游戏逐题进 FSRS（recordAnswer），老档导入 games 回落不炸 | test-srs + migrate 单测 |
| C8 | `npm test` 全绿 → `check:round5` 识字三项全过 | CI 链 |

## 7. 文件清单与并行冲突

```
apps/literacy-app/
├── src/data/char-index.js        [#4 改] +500 行 ROWS
├── src/data/chars/u34–u66.js     [#4 增] 33 个详情包
├── src/data/characters.js        [#4 改] UNITS + DETAIL_LOADERS 追加
├── src/data/character-index.js   [#4 删] 无引用遗留（P1）
├── src/data/books.js             [已落地 64f93ac] 后续加书遵守 §2.1/§2.2
├── src/data/idioms.js            [#6 改] +40 条
├── src/data/etymology.js         [#6 增] 字源数据（懒加载）
├── src/data/etymology-index.js   [#6 增] 轻量字集（主包）
├── src/data/compounds.js         [#7 增] 拼字拆分表
├── src/components/EtymologyPlayer.vue  [#6 增]
├── src/views/Game{Maze,Match,Build}View.vue  [#7 增]
├── src/views/CharDetailView.vue  [#6 改] intro 加「字的故事」按钮（小改）
├── src/views/HomeView.vue        [#7 改] 游戏乐园分区
├── src/stores/progress.js        [#7 改] games 字段 + recordGameRound + migrate
├── src/router/index.js           [#7 改] 3 条路由
├── scripts/gen-charset.mjs       [#4 增]
├── scripts/gen-etymology.mjs     [#6 增]
├── scripts/check-data.mjs        [#4/#6/#7 改] 各自分区块追加断言（绘本断言已在）
└── scripts/smoke.mjs             [#7 改] ROUTES + 交互断言
shared/data/common-hanzi.json     [#4 改] 500→1000
shared/data/idioms.json           [#6 改] 候选扩充
shared/data/etymology-source.json [#6 增] 字源底稿
NOTICES                            [#6 改] makemeahanzi 条目
```

冲突提示：三个在途子代理在 `check-data.mjs` 都要加断言——**各自新增独立的分区块
（追加式），不改别人的断言**；`characters.js` 只有 #4 动；`CharDetailView.vue` 只有
#6 动（intro 内小改，与 R4 状态机文件集重叠处以 R4 契约为准）；`progress.js` 只有
#7 动。绘本已合入且只用 u1–u33 字集，成语/字源/游戏同样只依赖稳定 500 字，
与 #4 的合并顺序任意。
