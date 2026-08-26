# Round 2 SOTA 差距审计（对照 sota-acceptance-criteria.md）

> 审计日期：2026-08-26
> 审计基线：分支 `cursor/hongen-edu-apps-9f67`，提交 `9824ddb`（含 Round 1 全部产出 + Round 2 已合入的验收自动化）。
> 说明：Round 2 有 10 个子代理并行施工，审计时工作区存在**在途未提交**工作（`public/sw.js`、`QuizShell.vue`、`errorTags.js`、FSRS 接线改动等）。本报告以**已提交代码**评分，在途工作单独标注为「🚧 在途」，不计入完成度。

**图例**：✅ 达标 · 🟡 部分达标（计 0.5）· ❌ 未达标 · ❓ 未测量（有脚本无实测数据，计 0）· 🚧 本轮在途

---

## 1. 识字 App（literacy-app）

### 1.1 功能

| # | 优先级 | 状态 | 实测证据 / 量化差距 | 分配 |
|---|---|---|---|---|
| L-F1 字库规模 | P0 | ❌ | **40 字**（`data/characters.js`），Round 2 门槛 100 字，差 **-60**；笔顺离线数据 133 字/256KB（≈1.9KB/字，懒加载余量充足） | Round 2 |
| L-F2 单字学习闭环 | P0 | 🟡 | 认（CharDetailView 大字卡+读音）、写（HanziWriter 描红）、测（quiz-complete 事件已接）三环节都在；「环节间自动衔接」编排未验证 | Round 2 |
| L-F3 笔顺书写 | P0 | 🟡 | 演示动画与逐笔描红判定有；「错 3 次自动示范该笔」「完成后整字回放」未实现（源码无对应逻辑） | Round 3 |
| L-F4 听音识字 | P0 | ✅ | 播报 + 4 选项（1 正确 + 3 干扰，2×2 布局），无惩罚流 | — |
| L-F5 复习系统 | P0 | ❌ | `utils/srs.js` FSRS-lite 契约完整且已有单测（`scripts/test-srs.mjs`），但**零文件 import**，复习队列未进首页 | Round 2 🚧 |
| L-F6 成语/绘本 | P1 | ❌ | 成语 **8/20**（40%）；绘本 **3/5**（60%，共 16 页）；逐句朗读高亮未实现；绘本无解锁拦截 | Round 3 |
| L-F7 奖励系统 | P0 | 🟡 | 星星即时发放 + CelebrationLayer 可跳过 ✅；「徽章 + 进度页回看」未成体系 | Round 3 |
| L-F8 家长面板 | P0 | 🟡 | 家长门（口算验证）、主题/字号/动效/时长提醒 ✅；「音量三总线」缺（现仅音效/语音开关 + 语速） | Round 3 |
| L-F9 进度持久化 | P0 | ✅ | localStorage 持久化 + **JSON 导出/导入已实现**（P1 部分提前完成） | — |
| L-F10 防沉迷 | P0 | ✅ | `restReminderMin` + `breakReminder`，App.vue 全局接入 | — |

**功能 P0 小计（9 项）：✅3 🟡4 ❌2 → 完成度 ≈ 56%**

### 1.2 性能（P0 × 7）

| # | 状态 | 实测证据 / 量化差距 |
|---|---|---|
| L-P1 Lighthouse ≥95 | ❓ | `scripts/acceptance.sh` 已合入（阈值 0.95），**实测数据 0 份**（acceptance-log-round2 待填） |
| L-P2 FCP/LCP/TTI | ❓ | 未测量 |
| L-P3 CLS/TBT | ❓ | 未测量 |
| L-P4 首屏 JS <250KB gzip | ✅ | 入口 `index-*.js` gzip **90,825B**（36% 配额）；单字笔顺 ≈1.9KB « 30KB |
| L-P5 帧率 ≥55fps | ❓ | 未测量（手动项，stress-test 仅测 DOM 规模） |
| L-P6 音效延迟 <100ms | ❓ | WebAudio 预解码路径在，无测量记录 |
| L-P7 内存 30min | ❓ | 未测量 |

**性能 P0 小计：✅1 ❓6 → 完成度 ≈ 14%（瓶颈是「测量执行」而非实现）**

### 1.3 无障碍

| # | 优先级 | 状态 | 实测证据 / 量化差距 | 分配 |
|---|---|---|---|---|
| L-A1 LH A11y ≥95 + axe | P0 | ❓ | `axe-check.mjs` 已合入（11 条路由全覆盖），实测 0 份 | Round 2 |
| L-A2 触控 ≥56px | P0 | 🟡 | 令牌已定义（`--tap-min:56px`/`--tap-gap-min:8px`），但**两 App 均未 import design-tokens.css**，逐组件抽查未做 | Round 2 |
| L-A3 对比度 + 主题 | P0 | 🟡 | 主题 **3/4**（sunny/care/night，缺第 4 个）；字号 **4/4 档** ✅；逐主题对比度抽查未做 | Round 3 |
| L-A4 键盘全流程 | P0 | 🟡 | App/BookRead/Celebration 有键盘处理；**描红环节无键盘替代/跳过通道**，闭环走不通 | Round 3 |
| L-A5 读屏 | P1 | ❌ | 全仓 aria-live 仅 **2 处**（庆祝层/成就 toast），答题结果未通报 | Round 3 |
| L-A6 动效降级 | P0 | ✅ | CSS `prefers-reduced-motion` + 家长动效开关（`motion:'reduced'`）双通道 | — |
| L-A7 光敏红线 | P0 | ❓ | 未走查（无已知高频闪烁动画，风险低） | Round 3 |

**无障碍 P0 小计（6 项）：✅1 🟡3 ❓2 → 完成度 ≈ 42%**

### 1.4 离线（P0 × 4）

| # | 状态 | 实测证据 / 量化差距 | 分配 |
|---|---|---|---|
| L-O1 断网冷启动 | ❌ | **无 Service Worker**（`sw.js` + `vite-offline-plugin.mjs` 🚧 在途未提交） | Round 2 🚧 |
| L-O2 资产本地化 | ✅ | index.html 零外链、字体系统栈、笔顺 JSON 包内；**残留风险**：TTS 依赖系统语音，无中文嗓音时静默失败 | Round 3（TTS 兜底） |
| L-O3 弱网降级 | 🟡 | `hanziData.js` 有 catch 容错不崩溃，但无「角色化提示 + 重试」UI | Round 3 |
| L-O4 静态可部署 | ✅ | `base:'./'` + hash 路由，zip 解压即用（277KB） | — |

**离线 P0 小计：✅2 🟡1 ❌1 → 完成度 ≈ 63%**

---

## 2. 数学 App（math-app）

### 2.1 功能

| # | 优先级 | 状态 | 实测证据 / 量化差距 | 分配 |
|---|---|---|---|---|
| M-F1 知识覆盖 ≥7 类 | P0 | 🟡 | 玩法落地 **6 类**（数感/加减/几何/找规律/数独/应用题）；**比较、乘法入门**仅存在于 `curriculum.js` 技能定义（compare-to-10、mul-table），无玩法入口；题库 = 16 应用题母题 + 运行时随机生成，**无题目 ID 不可复现** | 玩法 Round 2 · 300 题 Round 3 |
| M-F2 剧情关卡 | P0 | ✅ | 太空星图 + `starsToUnlock`（0/3/6/10/14/18）线性解锁已接进度 store | —（呼吸高亮走查 Round 3） |
| M-F3 互动教具 ≥3 | P0 | ❌ | 直接操作教具仅 **1/3**（数感拖拽 `usePointerDrag`）；数轴、分与合缺；「点选+点放」替代缺 | Round 2 🚧（QuizShell 在途） |
| M-F4 数形结合演示 | P0 | ❌ | 「实物→图形→算式」同步动画 + 旁白：源码无对应实现 | Round 3 |
| M-F5 难度自适应 | P0 | 🟡 | EMA 掌握度模型 + `pickNextSkill`（70/20/10 调度）已接线（视图回传技能点）；「连错给教具提示」「计时/生命值家长可开」缺 | Round 3 |
| M-F6 错题本 | P0 | ❌ | 无错题记录/重练（`errorTags.js` 🚧 在途） | Round 2 🚧 |
| M-F7 奖励系统 | P0 | 🟡 | 成就墙 + AchievementToast ✅；「星星×3 关卡评级」未实现 | Round 3 |
| M-F8 家长面板 | P0 | ❌ | **完全缺失**：无路由、无家长门、无报表；settings 仅 soundOn/eyeCare/ageBand/dailyGoal | Round 2 |
| M-F9 进度持久化 | P0 | 🟡 | localStorage ✅；JSON 导出/导入缺（识字侧已有实现可移植） | Round 2 |
| M-F10 防沉迷 | P0 | ❌ | 无时长提醒（识字侧模式可复用） | Round 2 |

**功能 P0 小计（10 项）：✅1 🟡4 ❌5 → 完成度 ≈ 30%**

### 2.2 性能（P0 × 9）

| # | 状态 | 实测证据 / 量化差距 | 分配 |
|---|---|---|---|
| M-P1–P7（同识字） | ❓×6 ✅1 | 主包 gzip **138,003B** <250KB ✅ 但 raw **432,649B**（Tone.js 占大头）拖累 TTI/解析；其余未测量 | 瘦身 Round 2（P1 项）· 测量 Round 2 |
| M-P8 拖拽跟手 | ❓ | 未测量（手动项） | Round 3 |
| M-P9 题目生成可复现 | ❌ | 全仓 seed 仅 StarField 视觉用；同 seed 同题**未实现** | Round 2 |

**性能 P0 小计：✅1 ❌1 ❓7 → 完成度 ≈ 11%**

### 2.3 无障碍（P0 × 8，A5 为 P1）

| # | 状态 | 实测证据 / 量化差距 | 分配 |
|---|---|---|---|
| M-A1 LH/axe | ❓ | 脚本已合入，实测 0 份 | Round 2 |
| M-A2 触控 56px | 🟡 | 同 L-A2：令牌未接线 | Round 2 |
| M-A3 对比度 | ❓ | 未抽查 | Round 3 |
| M-A4 键盘 | 🟡 | 数独/算术/应用题有 keydown；地图与几何未验证 | Round 3 |
| M-A6 动效降级 | ✅ | `useFeedback` + main.css 均支持 reduced-motion | — |
| M-A7 光敏 | ❓ | 未走查（StarField 需确认） | Round 3 |
| M-A8 cosmos 对比 | 🟡 | `--ice-100`(#f2f5ff) 对 `--cosmos-1`(#0b1030) ≈17:1 ✅；霓虹强调色（#5ee7ff 等）对深底未逐一核验 | Round 3 |
| M-A9 教具键盘替代 | ❌ | `usePointerDrag` **无键盘路径**（数独有，拖拽教具没有） | Round 3 |

**无障碍 P0 小计（8 项）：✅1 🟡3 ❌1 ❓3 → 完成度 ≈ 31%**

### 2.4 离线（P0 × 4）

| # | 状态 | 证据 | 分配 |
|---|---|---|---|
| M-O1 断网冷启动 | ❌ | 无 SW（🚧 在途，`public/` 目录刚建） | Round 2 🚧 |
| M-O2 资产本地化 | ✅ | Tone.js 已打包本地、零外域、题库本地生成 | — |
| M-O3 弱网降级 | ✅ | 无运行时懒加载数据请求（题库随包），天然满足 | — |
| M-O4 静态可部署 | ✅ | `base:'./'` + hash 路由（zip 146KB） | — |

**离线 P0 小计：✅3 ❌1 → 完成度 ≈ 75%**

---

## 3. 共同验收项

| # | 优先级 | 状态 | 证据 / 差距 | 分配 |
|---|---|---|---|---|
| C-1 隐私零外请求 | P0 | ✅ | 源码与 dist 均无外部域名；运行时 Network 全程核验留 Round 3 走查 | — |
| C-2 合规 NOTICES | P0 | ❌ | **`THIRD_PARTY_NOTICES` 文件不存在**（HanziWriter/hanzi-writer-data/OpenMoji/字体署名全缺）；`verify-resources.sh` 只验资源格式不验署名 | Round 2 |
| C-3 打包 | P0 | ✅ | `npm test` + `build:all` 通过（Round 1 实测：识字 162 文件/277KB zip，数学 21 文件/146KB zip） | — |
| C-4 设计令牌 | P1 | ❌ | `shared/styles/design-tokens.css` 完备（含 56px 触控/cosmos 主题），但 **0/2 App 引入**；识字仍用自带 theme.css | Round 2 |
| C-5 设计走查 | P1 | ❌ | 未执行、无留档 | Round 3 |
| C-6 浏览器矩阵 | P1 | ❌ | 未执行 | Round 3 |
| C-7 差异化加分 | P2 | 🟡 | 识字侧已集齐 4 项证据中的 3 项（三主题/护眼 ✅、进度导出 ✅、可跳过奖励 ✅、读屏 ❌）；数学侧仅护眼滤镜 | Round 3 |

---

## 4. 量化汇总

| 维度 | 识字 P0 | 数学 P0 | 共同 P0 | P1 全部 | P2 |
|---|---|---|---|---|---|
| 完成度（✅=1，🟡=0.5，❌/❓=0） | **11/26 ≈ 42%** | **10.5/31 ≈ 34%** | **2/3 ≈ 67%** | **≈ 8%**（仅 L-F9 导出提前完成） | ≈ 50% |

**三大结构性短板**（决定 Round 2 成败）：

1. **测量真空**：性能/无障碍 17 个 P0 指标里 15 个 ❓——脚本（acceptance.sh/axe-check.mjs）本轮已合入，但一份实测数据都没有。先出数、再优化。
2. **数学 App 家长侧整体缺位**：M-F8/M-F10/导出导入全缺，而识字侧三者齐备——直接移植成本最低、P0 收益最大。
3. **离线 = 0**：两 App 均无 SW（在途），L-O1/M-O1 是 Round 2 出包门槛。

**死代码负债**（不阻塞验收但拖累后两轮效率）：`core/engine/{generator,sudoku,wordproblem}.js` 零引用、`data/word-problems.js`（4 题旧版）与 `wordProblems.js`（16 题现用）并存、`utils/sound.js` 与 `core/audio/sound.js` 双份。

---

## 5. Round 2 / Round 3 分配

### Round 2 必须清零（出包门槛，按投入产出排序）

| 序 | 任务 | 对应验收项 | 量化目标 |
|---|---|---|---|
| R2-1 | 跑通验收自动化并填 acceptance-log-round2 实测 | L/M-P1–P4、L/M-A1 | Lighthouse Perf/A11y 实测 ≥90（过渡阈值）、axe critical = 0 |
| R2-2 | SW 离线预缓存两 App（🚧 在途收口） | L-O1/M-O1 | 断网冷启动完成 1 个学习闭环 |
| R2-3 | 字库扩容 | L-F1 | 40 → **≥100 字**（拼音/释义/例词/笔顺齐） |
| R2-4 | FSRS 接线 + 首页复习队列（🚧 在途收口） | L-F5 | srs.js 被 import、队列首页可见 |
| R2-5 | 数学家长面板 + 防沉迷 + 导出导入（移植识字实现） | M-F8/M-F10/M-F9 | 家长门 + 正确率/耗时报表 + 20min 提醒 |
| R2-6 | 错题本（🚧 errorTags 在途收口） | M-F6 | 按题目 ID 记录、重练答对移出 |
| R2-7 | 种子化题目生成 | M-P9/M-F1 | 同 seed 同题、生成 <16ms、题目 ID 可复现 |
| R2-8 | 教具补齐（QuizShell 🚧 在途） | M-F3 | ≥3 种教具 + 点选替代 |
| R2-9 | 乘法入门/比较进玩法 | M-F1 | curriculum 已有技能接玩法入口，7 类齐 |
| R2-10 | THIRD_PARTY_NOTICES | C-2 | 4 项署名齐 + verify-resources 通过 |
| R2-11 | 设计令牌接线 | C-4/L-A2/M-A2 | 2 App import design-tokens.css，抽查 10 组件无硬编码 |
| R2-12 | 死代码归并 | 工程负债 | 上述 3 组双份实现删至单份 |
| R2-13 | Tone.js → 轻量 WebAudio（P1 可选） | M-P2/TTI | 主包 raw 432KB → <200KB |

### Round 3 收尾（P0 剩余 + P1 清零）

| 序 | 任务 | 对应验收项 |
|---|---|---|
| R3-1 | 字库 100→200、成语 8→20、绘本 3→5 + 逐句朗读高亮 + 解锁拦截 | L-F1/L-F6 |
| R3-2 | 数学题库 ≥300 题 + 数形结合演示（实物→图形→算式） | M-F1/M-F4 |
| R3-3 | 笔顺「错 3 次示范 + 整字回放」；听写闭环键盘替代/跳过通道 | L-F3/L-A4 |
| R3-4 | 读屏与 aria-live 全覆盖 + 教具键盘替代 | L-A5/M-A9 |
| R3-5 | 第 4 主题 + 四主题对比度/触控逐项抽查 + 光敏走查 | L-A3/A7/M-A3/A8 |
| R3-6 | 性能手动项实测：帧率/音效延迟/内存/拖拽跟手；Lighthouse 提至 ≥95 | L-P5–P7/M-P8 |
| R3-7 | 自适应补全：连错教具提示、计时/生命值家长开关；星星×3 评级；徽章回看 | M-F5/M-F7/L-F7 |
| R3-8 | TTS 兜底（无中文嗓音检测提示或预录音频）+ 弱网角色化重试 UI | L-O2/L-O3 |
| R3-9 | 设计走查留档 + 浏览器矩阵 + 运行时零外域核验 | C-5/C-6/C-1 |
| R3-10 | 音量三总线（音乐/音效/语音分控） | L-F8 |

### 风险与依赖

- **并发冲突**：R2-2/R2-4/R2-6/R2-8 已有在途实现，后续代理先 `git pull --rebase` 再动工，避免重复造轮子（Round 1 双套实现的教训）。
- **测量环境**：Lighthouse 需要本机 Chrome/Chromium；acceptance.sh 已做 SKIP 降级，但 Round 2 门槛要求至少一台环境出真实分数。
- **字库扩容**牵连绘本用字校验（`verifyBookCoverage`）与听音识字干扰项池，扩容后需重跑 `check:data`。
