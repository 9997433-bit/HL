# Round 19 架构 · 全库富 Play + 舞台精美度 + 剖析视频级

> 岗位：r19-arch-contracts（子代理 #1 · fable 规划岗）
> 分支：`cursor/r19-arch-contracts-9f67`（基于 `cursor/r19-orchestration-9f67` @ `2624e06`）
> 本文是 H2 / H3 / H4 / H5 各实现岗的共同契约。改契约先改本文档。
> 本岗只定协议不做 UI；数字均在编排分支上实测，不是抄简报。

## 0. 一页话总览（本岗实测基线）

| 维度 | 实测现状（2624e06） | R19 目标 | 归属 |
|---|---|---|---|
| 富 Play | `RICH_PLAY_MANIFEST.plays` = **1240**（分片 u1–u70；seed 1241 行有效条目）；`RICH_UNIT_LIMIT=70` | **≥1820** 条、narration 去重 **≥1600**；seed 续 **u71–u99** | H2 |
| 分片管线 | `play-rich/uN.js` + `index.js` 懒加载（ROUND18_H3）已落地；禁止整包 | **保持**分片；禁止恢复 `char-play-rich.js` 整包同步 import | H2（数据）/ H3（Stage 不碰生成器落盘） |
| 舞台精美度 | CharPlayStage：六种 kind + 基础 GSAP（命中缩放、帧切换、下落）；有 `reduced` 短路，但无多拍节 timeline / 强化命中层 / 主题氛围层 | ≥**3** 类可感知升级 + reduced-motion 可跳过/降级 | H3 |
| 剖析形态 | WpAnalysisPanel：静态「shown 步进」；无 play/pause/progress/auto-advance | 「讲解播放」状态机：播/暂停/进度/自动推进；程序化时间轴，**非强制 MP4** | H4 |
| 手写剖析 | `EXPLAIN_COUNT` = **85**（34 手写母题 + 16 语义 + 35 皮肤专写） | 登记 **≥150**；去重中文讲解句 **≥400**；steps 与 `buildAnalysis` 步数对齐（R18 红线续守） | H5 |

四块延续既有纪律：**数据层同步纯函数、永不 null、Node 可跑；UI 层可跳过、
reduced-motion 完整可用**。所有 `ROUND19_H*` 标记必须落在**可执行代码**里
（探针剥注释后再扫，写在注释里等于没写）。

---

## 1. H2 · seed u71–u99 → 全库 1820 富脚本（r19-play-rich-full 岗）

### 1.1 只改 seed 与生成器阈值，不改运行时形状 / 不分片回退

流水线不动：

`apps/literacy-app/scripts/data/char-play-seed.txt`
（五段式 `字|主题|模板|旁白|道具`）
→ `node apps/literacy-app/scripts/gen-char-play-rich.mjs`
→ `apps/literacy-app/src/data/play-rich/{uN.js,index.js}`

条目形状（char/unit/theme/template/interaction/narration/props/templateFallback:false）
**一个字段不加不减**。

**禁止**：

- 恢复已删除的 `char-play-rich.js` 整包，或任何「为了方便」把多单元拼回单文件同步 import。
- 把 `RICH_PLAY_UNIT_LOADERS` 改成字符串拼接动态 import（会退化成整目录一块）。
- UI / `src/**/*.vue` 调用 `loadAllRichPlays()`（仅 scripts / 探针 / 单测）。

### 1.2 单元范围与配额

- 字库全量 **1820** 字 / **99** 单元；R18 已富写 **u1–u70 = 1240**。
- 本轮 seed **必须续写 u71–u99**，使生成器产出覆盖全库：
  `countRichPlays()`（`await loadAllRichPlays()` 后）**≥ 1820**。
- 建议：seed 对 u71–u99 一字一条写满；若个别单元字数与早期单元一样非整齐 20，
  以字表为准——生成器按 `character-index` 的 unit 归属过滤，
  `RICH_UNIT_LIMIT` 提到 **99** 后，超出单元的 seed 行才会被警告丢弃。

`gen-char-play-rich.mjs` 参数改动（一处一行，全部有既有变量）：

| 常量 | 现状 | R19 |
|---|---|---|
| `RICH_UNIT_LIMIT` | 70 | **99** |
| `MIN_RICH_PLAYS` | 1200 | **1820** |
| `MIN_DISTINCT_NARRATION` | 960 | **1600** |
| 新门槛标记 | — | `PROBE_MARK_R19 = 'ROUND19_H2'`（可执行） |
| `PROBE_HISTORY` | `['ROUND15_H3','ROUND16_H3','ROUND17_H2','ROUND18_H2']` | **追加** `'ROUND19_H2'`；历轮一枚都不许删 |
| `RICH_PLAY_THRESHOLDS` | `{ plays: 1200, narrations: 960 }` | `{ plays: 1820, narrations: 1600 }` |

`RICH_SPLIT_PROBE` 继续输出 `'ROUND18_H3'`（拆包契约仍属 R18；本轮 H2 不改分片形状）。
若生成器要同时自报 R19 条数门槛，用独立常量 `RICH_PLAY_PROBE_ROUND19 = 'ROUND19_H2'`，
**不要**覆盖 `RICH_PLAY_PROBE_ROUND18`。

### 1.3 narration 去重（全库口径）

- 生成器现有两道闸不许放松：一字不差撞句判错 + `narrationKey()` 近似撞句
  （只差标点/语气词）判错；`distinctNarrationKeys !== rows.length` 时拒绝落盘的纪律保持
  （或至少 `distinct ≥ MIN_DISTINCT_NARRATION` 且与条数对账——以生成器现闸为准，**阈值只升不降**）。
- **新写的 u71–u99 要和已有 u1–u70 的 1240 句一起去重**——禁止抄前 70 单元成句改两字应付。
- 旁白照字义写，≤26 字口语，能讲出这个字是什么；主题/模板从既有
  `PLAY_THEMES` / `PLAY_TEMPLATES` 里选，不发明舞台不认识的 template 名。

### 1.4 分片落盘契约（保持 play-rich，禁止整包）

生成器继续输出：

```
apps/literacy-app/src/data/play-rich/
  u1.js … u99.js     每单元一片：export const UNIT_RICH_PLAYS = [ … ]
  index.js           manifest（轻量，可进同步包）
```

`index.js` 必须继续导出：

- `RICH_PLAY_UNIT_LOADERS`：字面量 `() => import('./uN.js')` 表（扩到 u99）
- `RICH_PLAY_MANIFEST`：`{ plays, narrations, units, perUnit }`——**不含** narration/props 正文
- `RICH_PLAY_PROBE` / `RICH_PLAY_PROBE_ROUND18` / **`RICH_PLAY_PROBE_ROUND19 = 'ROUND19_H2'`**
- `RICH_PLAY_PROBE_HISTORY`、`RICH_PLAY_THRESHOLDS`、`RICH_SPLIT_PROBE`

运行时 API（`char-play.js`）**形状不变**：`ensurePlayUnit` / `getCharPlayAsync` /
`loadAllRichPlays` / `countRichPlays` 等按 R18 §2.3。H2 岗若发现 loader 表缺 u71–u99，
是生成器没跑或 `RICH_UNIT_LIMIT` 没改——修生成器与 seed，不改 API。

### 1.5 ROUND19_H2 落点与探针口径

可执行标记（至少一处，建议两处）：

1. `play-rich/index.js`：`export const RICH_PLAY_PROBE_ROUND19 = 'ROUND19_H2'`
2. `gen-char-play-rich.mjs`：`const PROBE_MARK_R19 = 'ROUND19_H2'`（scripts 在扫描范围）

探针（给 acceptance-spec 岗）：

1. 源码可执行串含 `ROUND19_H2`；
2. `await loadAllRichPlays()` 后 `countRichPlays() ≥ 1820`；
3. 全库 narration 去重 ≥ 1600（与 manifest.narrations / 生成器闸一致）；
4. manifest.plays 与实测注册条数一致（manifest 说谎即红）；
5. 仍存在 ≥90 个 play-rich 单元 chunk 路径 / loader 键（u1–u99）；
   **同步闭包不含** rich 正文指纹（沿用 R18 check:bundle 思路）。

---

## 2. H3 · CharPlayStage ≥3 类精美升级（r19-play-polish 岗）

### 2.1 范围边界（与 H2 的硬分工）

| 岗 | 主战场 | 不许越界 |
|---|---|---|
| H2 | seed、生成器阈值、分片产物数量 | 不改 CharPlayStage 动效语义 |
| H3 | `CharPlayStage.vue`（及必要时极薄的 stage 辅助 composable / CSS） | **不改** seed 文案、不改 `gen-char-play-rich` 落盘、不把 rich 整包拉回 |

冲突裁决（简报原话落地）：**Stage 以 H3 为准、数据以 H2 为准**。
H3 若需读 theme/template，只消费既有字段（`scene.theme` / `scene.kind` / props），
不新增强制 seed 字段；若想要可选增强字段，必须 default-safe（缺省 = 现状行为）。

### 2.2 三类可感知升级（最低交付集）

实现岗至少落地下面 **3** 类，每类必须在「非 reduced-motion」下肉眼可辨，
并在走查证据里各有一张图/一段录屏对应：

#### A. 多拍节 timeline（multi-beat）

- 用 GSAP `timeline()`（或等价）把进场 → 互动提示 → 成功收束打成 **≥2 拍**：
  例如 watch 帧切换带间隔拍、catch 开场道具错落入场后再可点、assemble 零件依次亮起。
- 通关条件与 kind 语义不变；拍节只加「层次」，不改 goal 计数。
- 可执行标记附近应能定位到 timeline 创建/编排函数（禁止只加 CSS transition 冒充多拍）。

#### B. 道具命中反馈增强（hit feedback）

- 在现有 scale/透明度消失之上，增加一层可感知反馈，至少覆盖 tap/catch/pick 主路径：
  例如短闪描边、粒子/碎屑（OpenMoji 或纯 CSS）、命中音与微震动已有则强化时序对齐。
- 点错（miss）与点中（hit）必须可区分；miss 不得误触发通关。
- 不引入新的网络资源包；禁止位图大图。

#### C. 主题氛围层（theme ambience）

- 按 `scene.theme`（或 `PLAY_THEMES`）映射一层轻量氛围：背景渐变/点缀色/前景轻飘带
  （天气主题细雨丝、自然主题叶片等），**不得压过道具可点热区**。
- 氛围是装饰层：`pointer-events: none`；无 theme 时走中性默认，不空白不报错。

### 2.3 reduced-motion 契约

- 现有 `reduced` 计算（settings.reduceMotion + `prefers-reduced-motion`）保留。
- `reduced === true` 时：
  - **不创建** GSAP timeline / 氛围动画 / 命中粒子循环；
  - 多拍节改为瞬时就位或单帧展示；
  - 互动规则与通关条件与动态模式一致；
  - 跳过按钮始终可用（R15 底线）。
- 探针除扫 `ROUND19_H3` 外，应能静态或单测断言：reduced 分支存在且跳过 timeline 启动。

### 2.4 ROUND19_H3 落点

- `CharPlayStage.vue` script 顶层：
  `export const ROUND19_H3 = 'char-play-stage-polish'`（或同文件内
  `const ROUND19_H3 = '…'` 被模板 `:data-polish="ROUND19_H3"` 引用——必须是可执行引用）。
- 三类升级的实现函数/块附近可用细分常量（可选）：
  `POLISH_BEATS` / `POLISH_HIT` / `POLISH_AMBIENCE`，值含 `ROUND19_H3` 或由其派生，
  方便探针证明「≥3 类」不是空标。

探针口径（给 spec 岗）：

1. 可执行标记 `ROUND19_H3`；
2. 源码侧能识别三类升级的独立实现（函数名/data 属性/测试钩子三选一，契约不锁死命名，
   但 acceptance 文档必须写明认定方式）；
3. reduced-motion 路径单测或 DOM 类名 `play--static` 下无 timeline 副作用。

---

## 3. H4 · WpAnalysis「讲解播放」状态机（r19-wp-video-player 岗）

### 3.1 产品定义（视频级 ≠ MP4）

「视频级」= **程序化讲解播放器**：GSAP/CSS 时间轴 + 可选 TTS，把已有
图示 + 分步 + 手写 why 按时间推进，体感像 20–40 秒短课。

**非目标**：不为每道题制作/托管 MP4；不把大视频文件塞进仓库或 CDN 强依赖。
若将来有可选 MP4 插槽，必须是 progressive enhancement，缺省路径仍是程序化时间轴。

### 3.2 状态机契约

在 `WpAnalysisPanel.vue`（或抽离的 `useWpLessonPlayer` composable，由 Panel 唯一消费）
实现以下状态与动作：

```
states: idle | playing | paused | ended

events:
  play        idle|paused → playing
  pause       playing → paused
  seek(p)     any → playing|paused（保持原播放/暂停意图，进度跳到 p）
  tick        playing 时按时间轴推进 shown / 高亮步
  end         进度到 1 → ended
  reset       换题 → idle（shown 回到约定起点）
```

UI 最低控件：

| 控件 | 行为 |
|---|---|
| 播放 / 暂停 | 切换 playing ↔ paused；idle 下播放从当前进度继续 |
| 进度 | 可展示 0–1（条或步序「第 i/n 步」）；允许点击/拖动 seek（至少可点步） |
| 自动推进 | playing 时按时间轴自动增加可见步 / 高亮当前步 |
| 跳过剖析 | 既有 skip 保留，打断播放并 emit |

与现有 `shown` 步进的关系：

- 手动「下一步 / 全部展开」仍可用；手动操作时若正在 playing，应 **pause** 或与手动同步
  （推荐：手动下一步 → pause，避免抢控）。
- `reveal === true`（判题后）可自动展开全部，同时 player → ended 或停在末步。
- 换题 watch 必须 `reset`（与现有清空 variant 同一时机）。

### 3.3 时间轴内容绑定（吃 H5 文案）

播放器消费 `buildAnalysis(question)` 的产出，不另起数据源：

1. 可选序章：图示块 + `explain.caption` / `analysis.why`（若有）短停顿；
2. 正序每一步：高亮 step i，朗读/展示 `step.why`（手写优先，公式兜底）；
3. 末步：遵守 **判题前盖答案**——播放器文案层同样不得念出 asked 步得数。

步与步默认间隔建议 2.5–5s（可按字数微调），总时长体感 20–40s；
具体数值实现岗自定，但需可被单测假时钟推进。

### 3.4 reduced-motion / 无障碍

- `prefers-reduced-motion` 或设置项为真时：**降级为手动点步**（现状），隐藏自动播放或
  play 按钮变为「显示下一步」等价物；不得自动推进。
- 键盘可操作播放/暂停；`aria-label` 标明「讲解播放」。

### 3.5 ROUND19_H4 落点

- `WpAnalysisPanel.vue` 或 composable：
  `export const ROUND19_H4 = 'wp-lesson-player'`（可执行）；
- 模板根节点：`:data-lesson-player="ROUND19_H4"`（或等价 data 属性）。
- 与历轮标记共存：`ROUND16_H5` / `ROUND17_H4` / `ROUND18_H5` **不许删**。

探针口径：

1. 可执行 `ROUND19_H4`；
2. 行为烟测：挂载后面板能 play → 可见步自动增加 → pause 停止增加 → 再 play 继续；
3. reduced-motion 下不自动推进；
4. **不**要求仓库内存在 `.mp4` 剖析资源。

---

## 4. H5 · 手写剖析 ≥150 + 步数对齐红线（r19-wp-explain-150 岗）

### 4.1 现状与目标

- 登记条数：`EXPLAIN_COUNT = 85`（34 + 16 + 35），同文件
  `apps/math-app/src/data/word-problem-explains.js` 续写。
- 目标：`EXPLAIN_COUNT ≥ 150`；去重中文讲解句 **≥ 400**
  （headline + caption + 各 step 函数产出句，运行时对 `handwritten === true` 的分析收集去重）。
- 新标记：`export const ROUND19_H5 = 'crafted-explain-chain-150'`，与
  `ROUND17_H4` / `ROUND18_H5` 并存，历轮不删。

### 4.2 续写协议

- 条目形状不变：`{ id, headline?, caption?, steps: [fn…] }`。
- 优先补 **皮肤专写**（具体组合 id，可点名道姓）与尚未专写的高频语义缺口；
  语义共享条仍禁止具体名词串皮肤。
- 增量约 ≥65 条净增（85→150）；允许更高以留探针余量。
- 查表两趟规则不动：显式 id 胜出语义展开。

### 4.3 步数对齐红线（R18 续守，本轮加重）

H4 播放器按 `buildAnalysis().steps` 推进；H5 的 `steps[]` 长度必须与之相等，否则：

- `applyExplain` 只能部分覆盖 → `handwritten` 招牌挂不上（`written === steps.length`）；
- 播放器会出现「有画面无老师句」或错位高亮。

**红线**：

1. 每条手写 `steps.length === buildAnalysis({ ...make(), id }).steps.length`；
2. 禁止为挂招牌而在 analyzeEquation 生造非计算步；禁止把 steps 改成动态
   `buildAnalysis` 同义反复（R18 §3.5）；
3. asked 步文案禁止出现得数（泄题兜底不是许可）；
4. H5 扩写时若发现某母题声明 steps 与剖析不一致，**移交/联修数据声明或分析器**，
   不得只在手写链里凑长度；本轮以「对齐」为准，不接受「播放器跳过空步」糊弄。

H4↔H5 交接：H5 可先于或并行于 H4 合入，但 H4 合入时必须已能吃到手写 why；
任一方破坏步数对齐，两边探针都可判红。

### 4.4 ROUND19_H5 落点与探针

- `word-problem-explains.js`：`ROUND19_H5` 可执行导出；Panel 的
  `data-explain-chain` 可升级为优先展示 R19 标记（或同时绑定），但不得移除 R18 标记扫描路径
  ——acceptance 岗写明：往轮扫 R18、本轮扫 R19，或 history 数组两者都在。
- 探针：`EXPLAIN_COUNT ≥ 150`；去重讲解句 ≥ 400；抽检手写题
  `handwritten === true` 且步数对齐率 100%（对 EXPLAIN_MAP 命中且 steps 写满的条目）。

---

## 5. 岗间冲突边界（总表）

| 冲突面 | 裁决 |
|---|---|
| H2 seed/生成物 vs H3 Stage | **数据 H2、Stage H3**；H3 不得改生成器落盘与阈值 |
| H2 分片 vs 「图省事整包」 | **禁止整包**；任何恢复 `char-play-rich.js` 或静态 import 全量 rich 的 PR 拒合 |
| H3 动效 vs reduced-motion | 动效让路；reduced 下降级，通关语义不变 |
| H4 播放器 vs H5 文案 | 播放器只读 `buildAnalysis`；文案步数必须对齐；错位时修 H5/数据，不修播放器去「猜步」 |
| H4 视频级 vs MP4 资产 | 程序化时间轴为必达；MP4 非门槛 |
| H5 扩写 vs R18 步数对齐 | R18 红线继续有效；扩写不得回退一致率 |
| 本轮探针 vs 往轮探针 | `ROUND19_H*` 只追加；`PROBE_HISTORY` / 历轮 export 不许删；H8 要求 `check:round18` 8/8 |
| 标记方式 | 禁止注释骗标；必须 export 常量或模板可执行绑定 |

---

## 6. 全局红线（所有岗）

1. **禁止注释骗标**：`ROUND19_H2/H3/H4/H5` 全部落在可执行代码。
2. **禁止恢复 rich 整包同步 import**；`loadAllRichPlays()` 仅 scripts/探针/单测。
3. **禁止**用 MP4 大文件冒充 H4 完成，同时却没有 play/pause/progress/auto-advance 状态机。
4. **禁止**手写链 steps 与 `buildAnalysis` 步数错位仍宣称 handwritten 精品。
5. 数据层保持同步纯函数、永不 null；异步仅分片加载层；加载失败退 generated/emergency。
6. 不复制洪恩 IP；视觉继续 OpenMoji + 程序化动效。

## 7. 各岗交接顺序建议

1. **H2**（seed u71–u99 + 生成器阈值 + 重生分片）可独立先行；
2. **H3** 可与 H2 并行（只碰 Stage）；合入冲突时 Stage 听 H3、manifest 听 H2；
3. **H5** 手写扩写可与 **H4** 并行，但 H4 烟测需至少一条 handwritten 长链题；
4. H4 合入后 walkthrough 必须拍到播放中的进度与暂停；
5. regression-gate 最后锁 H8（`check:round18` 8/8）与 r19 全门禁。

## 8. 成功体验（契约验收语）

1. 任意字（含 u99）玩关都是手写旁白，不再模板脸；
2. 玩关能感到拍节与命中反馈，氛围不抢操作；
3. 应用题「播放讲解」像 20–40 秒短课，可暂停、有进度；
4. ≥150 道手写讲解读起来像老师，且步序与面板一致；
5. 以上均有可执行探针与走查图，不是只骗标记。
