# Round 5 架构契约 · 数学内容与教具（M-M3 / M-M8 / M-M5 / M-M13 / M-M11）

> 面向实现子代理 #8（母题 100）的**实现契约**，并对已合入的 #9 成果
> （数形演示 + 七巧板 + 分与合 + 竖式，commits fda49c3 / 804df86）做**契约固化**。
> 本文只定义数据 schema、注册表、路由与门禁口径；题面文案、画面与交互手感由实现方自由发挥。
> 基线：`cursor/openmoji-integration-9f67` @ aacd996（撰写时集成分支已推进至 804df86，
> 「已落地」标注以 804df86 实测为准）· App：`apps/math-app/`
> 关联：`SURPASS-HONGEN-MASTER-PLAN.md` §3、`ROUND5-BRIEF.md`、
> `round4-math-adaptive-wrongbook.md`（questionId / 错题本 / adaptive 的既定口径）

---

## 0. 现状与目标差距

| 模块 | 现状（804df86 实测） | Round 5 目标 |
|---|---|---|
| M-M3 母题 | `data/wordProblems.js` **38** 个母题（id/skill/tag/steps/emoji/scene/make），`check:content` 下限 25 | **≥100** 个母题（未落地，§1） |
| M-M8 数形演示 | ✅ **已合入**：`data/visualDemos.js` 8 类 + `VisualMathDemo.vue` + `/visual-demos` 展馆 + 模块首屏入口 + check:content 结构断言 | 契约固化 + 补强（§2） |
| M-M5 七巧板 | ✅ **已合入**：`modules/geometry/TangramView.vue`，路由 `/tangram`，记 `tangram-basic` | 契约固化 + 补强（§3） |
| M-M13 分与合 | ✅ **已合入**：`modules/number-sense/ComposeTenView.vue`，路由 `/compose-ten`，记 `compose-ten` | 契约固化 + 补强（§4） |
| M-M11 竖式 | ✅ **已合入**：`modules/arithmetic/ColumnArithmeticView.vue`，路由 `/column-arithmetic`，进位/借位双道 | 契约固化 + **错因专练入口补强**（§5） |

**既有基建（Round 4 落地，直接复用、不重做）**：
- `utils/random.js`：`hashSeed / mulberry32 / createRng(seed)`（返回带 `.int/.sample` 的 rng）、
  `questionId(templateId, seed)`（格式 `templateId:seed`）、`parseQuestionId`、`reseed(seed)`
  （全局环境随机源可重置）、`numericOptions({ rng })`。
- 日冒险种子约定 `dailySeed = 'YYYY-MM-DD#slot'`；错题本 `progress.wrongBook` + `WrongBook.vue`；
  自适应 `core/engine/adaptive.js`；错因词典 `data/errorTags.js`（已含 `carry/borrow/off-by-ten`）。

**不变式**：
- `WORD_PROBLEMS` 条目对外形状不变（`id/skill/tag/steps/emoji/scene/make()`），只加不改；
  `WORD_PROBLEM_TIERS / problemsOfTier / WORD_PROBLEM_TAGS / WORD_PROBLEM_COUNT` 导出不变。
- `QuizShell` 题目协议、`progress.recordAnswer` 两种签名、localStorage 只增字段（`mergeState` 回落）。
- `visualDemos.js` 的路径与导出名（`VISUAL_DEMOS` / `VISUAL_DEMO_MAP`）已被
  `check:round5` 探针与 check:content 锁定，**不得移动/改名**。
- push 前 `npm test`（= check:content + build + smoke）全绿；`check:round5` 数学两项达标。

---

## 1. M-M3 · 应用题母题 38 → 100（子代理 #8，本轮数学侧唯一未落地 P0）

### 1.1 扩展策略：语义模板 × 场景皮肤

**计数口径**：`check:round5` 数的是 `WORD_PROBLEMS.length`，所以 100 指注册表条目数。
条目 = 「语义结构 × 参数档位」，**场景皮肤不单独成条**——同一语义换皮肤靠共享皮肤池
在 `make()` 内随机化，避免 100 条里 30 条是换了名词的同一道题。

新文件 `src/data/wpSkins.js`（皮肤池，供所有母题 import）：

```js
export const NAMES = [...]                     // 现有 8 个人名池迁入并扩到 ≥12
export const SKINS = {
  orchard:  { scene: '果园',   items: [{ n: '苹果', e: '🍎', u: '个' }, ...] },
  market:   { scene: '菜市场', items: [...] },
  // ≥15 个场景，每场景 ≥3 种物品（名词/emoji/量词绑定，量词跟物品走避免「3 条苹果」）
}
export const pickSkin = (sceneId, rng?) => {}  // 取物品 + 人名组合；rng 缺省走环境随机源
```

### 1.2 语义谱系与数量分布（验收口径）

| steps | 语义 tag（受控词表，维护在文件内 `WP_TAGS_EXPECTED`） | 条目下限 |
|---|---|---|
| 1 步 | 合并 / 剩余 / 比多少 / 序数排队 / 钱币 / 长度 / 凑整 | **≥40** |
| 2 步 | 两步 / 时间 / 倍数 / 平均分 / 间隔·植树 / 余数分组 / 购物找零 | **≥35** |
| ≥3 步 | 和差 / 鸡兔同笼 / 相遇 / 归一 / 年龄 / 重叠 | **≥15** |

- tag 总数 ≥20 类、scene ≥15 个（`check:content` 数 `WORD_PROBLEM_TAGS` 与 scenes 集合）。
- 新语义如需新技能点，在 `data/curriculum.js` 追加并接 `skill-mapping.js`：
  本轮预注册两个：`wp-position`（L2，序数与排队，deps: count-to-20）、
  `wp-money`（L3，钱币购物，deps: add-within-100）。其余语义复用现有 `wp-*` 六技能。
  **`skill` 必须过 `isKnownSkill`**（check:content 既有断言）。

### 1.3 参数域硬约束（每条 make() 必须满足，门禁 2000 次采样）

1. `answer` 为非负整数；1 步题答案 ≤ 20（L2 技能）或 ≤ 100（L3+），多步题 ≤ 200。
2. `text` 不含 `NaN/undefined/{`（既有断言）且长度 ≤ 70 字；`equation/unit/hint` 必填。
3. 中间量不为负、不出现「0 个」这类退化叙事（参数域下限 ≥1）。
4. `visual`（可选）沿用 `{ icon, groups, strike? }` 形状，QuizShell 已会渲染。
5. **随机源纪律**：`make()` 只用 `utils/random.js` 的环境函数（randInt/sample）或传入 rng，
   禁止直接 `Math.random()`——保证 `reseed(seed)` 后整库可复现（§1.5 门禁靠它）。

### 1.4 id 命名与皮肤去重

- `id` 延续 kebab：`<语义>-<变体>`（如 `money-change`、`queue-between`、`interval-trees`），
  与现有 38 个不冲突；语义相同仅参数档不同时用尾缀（`money-change-100`）。
- 同 tag 内任意两条目的 `text` 模板骨架不得完全相同（防「复制换名词凑数」）：
  check:content 对每 tag 取各模板一次生成，比对去掉数字/人名/物品后的骨架串，重复即失败。

### 1.5 门禁增量（`scripts/check-content.mjs`，追加分区块，不动 #9 已落地断言）

```
✓ MIN_TEMPLATES 25 → 100
✓ tag 集合 ⊆ WP_TAGS_EXPECTED 且 ≥20；scenes ≥15；steps 桶下限 40/35/15
✓ 既有逐题 2000 次采样断言保留（整数/非负/NaN/单位）
✓ 可复现探针：reseed(hashSeed(tpl.id)) 后 make() 两跑 JSON 深等（抓 Math.random 夹带）
✓ 骨架去重（§1.4）
```

`check:round5` 读 `WORD_PROBLEMS.length ≥ 100`，已就绪不改。

### 1.6 错题本联通（P1，不阻塞验收）

`WordProblemsView` 出题时为每题生成 `seed = hashSeed(uid())`、`reseed(seed)` 后调 `make()`，
并盖 `id: questionId('wp.' + tpl.id, seed)` + `snapshot`——应用题即进入 R4 错题本的
可复现重练体系。母题库本身不感知此事（视图层两行改动）。

---

## 2. M-M8 · 数形结合演示（已落地，契约固化）

### 2.1 落地形态（冻结，新增演示条目照此登记）

**路径与导出**：`src/data/visualDemos.js` → `VISUAL_DEMOS`（数组，现 8 类）+ `VISUAL_DEMO_MAP`。
条目 schema（三段契约「实物 → 图形 → 算式」）：

```js
{
  id: 'compose-ten',            // 唯一，kebab
  module: 'number-sense' | 'arithmetic' | 'geometry',  // 玩法语义分组（视图筛选用）
  skill: 'compose-ten',         // 必须过 isKnownSkill（check:content 已断言）
  title, subtitle,
  object:  { emoji, count, groups?, removed?, label },   // 第一幕：实物
  visual:  { groups, label, crossedGroup?, fraction? },  // 第二幕：圆点/十格/圈组模型
  equation: '6 + 4 = 10',       // 第三幕：算式
  narration: [s1, s2, s3],      // 恰 3 句，一幕一句（check:content 已断言）
}
```

已覆盖 8 类：点数 / 加法 / 减法 / 分与合 / 比大小 / 乘法 / 除法 / 分数起步，
横跨 number-sense×3、arithmetic×4、geometry×1。

**播放链路**：`components/VisualMathDemo.vue`（统一播放器）+
`modules/visual-demos/VisualDemosView.vue`（`/visual-demos` 展馆路由）+
Home / NumberSense / Arithmetic / Geometry 各视图首屏入口。

### 2.2 已落地门禁（check:content，不得回退）

```
✓ VISUAL_DEMOS ≥7；id 唯一；object/visual/equation 三段齐全
✓ narration 恰 3 段；skill 全过 isKnownSkill
```

### 2.3 补强项（P1）

1. 播放器行为验收明确化：可跳过（跳过后直达末幕）、`data-motion="reduced"` 时不建
   timeline 而静态展示三幕、每幕 narration 写 `role="status"` live region——已实现的部分
   由收尾子代理 #10 在 smoke 中固化断言（smoke 已有 demo equation 断言，804df86）。
2. 建议补第 9 类 `carry`（进位十格演示，module: arithmetic, skill: add-carry-20），
   与 `/column-arithmetic` 视图头部互链，「先看演示再练竖式」。
3. `module` 字段当前是语义分组（`number-sense` 不是 `moduleInfo` 的 id `counting`）——
   保持现状即可，但新增条目**必须**沿用现有三个取值之一或同步扩展 VisualDemosView 的分组文案。

---

## 3. M-M5 · 七巧板（已落地，契约固化）

### 3.1 落地形态（冻结）

- 视图 `modules/geometry/TangramView.vue`（自绘 Canvas，无第三方库），路由 `/tangram`，
  GeometryView（图形星球）首屏入口 + Home 工具卡。
- 完成记账：`recordAnswer('geometry', true, { skill: 'tangram-basic', stars: 3, xp: 24 })`
  ——挂靠 geometry 星球模块 id，**不新增 SIDE_MODULES**（教具归属星球，成就历史不冒裸 id）。

### 3.2 行为契约（后续改动不得回退的口径）

- 交互双通道：指针拖拽 + 选中态旋转/翻转控件；键盘可达（Tab 选块、方向键平移、旋转/放下有键）。
- 吸附判定容差固定（位置 + 角度），全部块吸附 = 完成 → 星星 + 庆祝（可跳过）。
- 提示阶梯：卡住可请求高亮目标位（不倒扣，教具不罚站）。

### 3.3 补强项（P1）

1. 块与图案定义目前内嵌视图——抽出 `src/data/tangrams.js`
   （`TANGRAM_PIECES` 7 块 + `TANGRAM_PUZZLES ≥6`），check:content 加结构断言：
   7 块面积和 ≈ 大正方形（±1e-6）、每图案 solution 恰用每块一次。
2. smoke：`/tangram` 可达 + 选块旋转一次零报错（若 804df86 的 smoke 未覆盖则补）。

---

## 4. M-M13 · 分与合教具（已落地，契约固化）

### 4.1 落地形态（冻结）

- 视图 `modules/number-sense/ComposeTenView.vue`，路由 `/compose-ten`，
  NumberSenseView（数感星球）首屏「开始分弹珠」入口 + Home 工具卡。
- 记账：`recordAnswer('counting', correct, { skill: 'compose-ten' })`——挂靠数感星球
  模块 id `counting`，`compose-ten` 技能点接线达成（brief P0 口径）。

### 4.2 行为契约

- 一轮 = 把 N 颗弹珠分进两碗得到分法（`a + b = N，a,b ≥ 1`）；点选与拖拽同权。
- 分法确认时展示两种算式写法（`a + b = N` 与 `N = a + b`）并朗读；
  「分法收集册」清单激励集齐（N=10 的凑十段是技能核心）。
- 纯函数（分法枚举/判定）保持可单测；`splitsOf(10)` 恰 9 种、无 0 分法。

### 4.3 补强项（P1）

视图头部接 visualDemos 的 `compose-ten` 条目（「🎬 看演示」→ VisualMathDemo 浮层），
演示与动手教具形成「看 → 做」闭环。

---

## 5. M-M11 · 竖式专题（已落地，契约固化 + 错因入口补强）

### 5.1 落地形态（冻结）

- 视图 `modules/arithmetic/ColumnArithmeticView.vue`，路由 `/column-arithmetic`，
  ArithmeticView 首屏「进入专题」入口 + Home 工具卡。
- 双道案例库：`kind: 'carry'`（进位加）/ `kind: 'borrow'`（退位减），`mode` 状态切道；
  逐位作答（个位 → 进/借位标记 → 十位），错时
  `recordAnswer('arithmetic', false, { errorTags: [q.tag, 'off-by-ten'] })`，
  对时按整题记正向事件——错因直通 R4 错题本/家长报表体系。

### 5.2 补强项（P0 收尾，brief 的「错因专练入口」还差最后一截）

1. **深链契约**：支持 `/column-arithmetic?mode=carry | borrow` 预选分道
   （query 名对齐视图内既有 `mode` 状态；非法值回落默认 `carry`）。
2. **入口 ≥2 处**（`errorTagCounts` 中 `carry` 或 `borrow` ≥3 时出现，带 mode 参数）：
   - `WrongBook` / 家长报表错因分区：「去竖式计算室专练 →」按钮；
   - Home 推荐位：同阈值触发推荐 chip。
3. smoke：`?mode=borrow` 深链可达且预选借位道。

### 5.3 Round 6 预告（本轮不做，立此存照）

固定案例库换参数化出题器（`makeVerticalProblem(kind, level, rng)` 纯函数，保证必进位/
必借位），进 check:content 采样断言；三位数进阶档。

---

## 6. 验收清单（供子代理 #3 acceptance-log-round5 引用）

| # | 验收项 | 验证方式 |
|---|---|---|
| M1 | 母题 ≥100、tag ≥20、scene ≥15、steps 桶 40/35/15 | `check:content` + `check:round5` |
| M2 | 母题库 reseed 可复现，无 Math.random 夹带 | `check:content` 双跑深等探针 |
| M3 | visualDemos ≥7 类、三段/旁白/技能断言全过（已落地不回退） | `check:content` + `check:round5` |
| M4 | 每类 demo 有首屏入口；播放可跳过；reduceMotion 静态降级 | smoke + 人工走查 |
| M5 | `/tangram` 可拼完成、双通道交互、完成记 tangram-basic | smoke + 人工走查 |
| M6 | `/compose-ten` 分法玩法完整、记 compose-ten | smoke |
| M7 | `/column-arithmetic` 双道 + 逐位错因 + `?mode=` 深链 | smoke |
| M8 | carry/borrow ≥3 时 WrongBook/Home 出现专练入口 | smoke（预置 errorTagCounts） |
| M9 | 教具挂靠星球模块 id 记账（成就历史无裸 id）；老档 mergeState 不炸 | 单测 |
| M10 | `npm test` 全绿 → `check:round5` 数学两项全过 | CI 链 |

## 7. 文件清单与并行冲突

```
apps/math-app/
├── src/data/wordProblems.js      [#8 改] 38→100+ 条目
├── src/data/wpSkins.js           [#8 增] 场景皮肤池
├── src/data/curriculum.js        [#8 改] +wp-position/wp-money（追加式）
├── src/data/skill-mapping.js     [#8 改] 新技能映射（如需）
├── src/data/visualDemos.js       [已落地] 新增条目照 §2.1 schema
├── src/data/tangrams.js          [P1 增] 七巧板数据抽出（§3.3）
├── src/components/VisualMathDemo.vue          [已落地]
├── src/modules/visual-demos/VisualDemosView.vue [已落地]
├── src/modules/geometry/TangramView.vue         [已落地]
├── src/modules/number-sense/ComposeTenView.vue  [已落地]
├── src/modules/arithmetic/ColumnArithmeticView.vue [已落地；P0 补 ?mode= 深链（§5.2）]
├── src/components/WrongBook.vue  [收尾改] 专练入口（§5.2）
├── src/modules/home/HomeView.vue [收尾改] 推荐 chip（§5.2）
└── scripts/check-content.mjs     [#8 改] 追加分区块（勿动 #9 已落地断言）
scripts/check-round5.mjs           [已就绪，勿改探针路径/导出名]
```

冲突提示：#8 与已落地的 #9 成果唯一共触文件是 `check-content.mjs`——**#8 只追加
自己的分区块**。`curriculum.js` 为追加式改动。§5.2 错因入口补强建议由收尾子代理
#10 承接（与其 smoke/验收回填天然同路）。两侧都不动 `utils/random.js` 与
`stores/progress.js`（R4 契约封板，字段以 `round4-math-adaptive-wrongbook.md` 为准）。
