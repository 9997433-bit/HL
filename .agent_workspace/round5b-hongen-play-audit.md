Model slug: fable

# Round 5B · 洪恩「好玩度」对标审计（Play Layer fresh walk）

> 审计人：Round 5B 子代理 #2（fable）· 分支 `cursor/r5b-module-audit-9f67`
> 审计基线：`cursor/openmoji-integration-9f67` @ `3cf37eb`（Round 5 闭合点，`check:round5` 12/12）
> 审计日期：2026-08-27
> 方法：在**独立 worktree**（`git worktree add`，锚定 `3cf37eb`）逐文件走读两 App 的首页 / 地图 / 游戏 / 吉祥物 / 反馈层源码，每条状态附文件路径与行级事实；洪恩「好玩度」能力以公开资料核实（洪恩官网、小米应用商店、百度百科、第三方体验报告），不引用臆测。

---

## 0. ⚠️ 审计环境警告：主工作区正被并行子代理实时修改

走读期间实测到 `/workspace` 主工作树在**分钟级**发生漂移（Round 5B 各执行子代理与本审计共用一台 VM）：

| 漂移物 | 归属 | 对审计的影响 |
|---|---|---|
| `apps/literacy-app/src/components/DailyAdventure.vue`、`src/stores/dailyQuest.js`（未跟踪）+ `HomeView.vue`（M） | #4 每日冒险（P1） | **不是基线能力**，本表按基线记 ❌ |
| `apps/literacy-app/src/components/MascotCompanion.vue`（M, +37/-6）+ `styles/base.css`（M） | #5 吉祥物陪跑（P2） | 同上 |
| `shared/composables/useFeedback.js`（整个 `shared/composables/` 目录未跟踪） | #6 统一反馈（P3） | 同上——**基线里不存在 shared 版 useFeedback** |
| 识字 `utils/audio.js` 出现 `STREAK_CHORDS`、数学 `sound.js` 出现 `STREAK_CUES`、QuizShell 出现 `streak: progress.combo`（后被移回其 worktree） | #9 音效节奏（P6，`664b7fe` 已在其分支上） | 同上——基线答对音是**固定谱面** |

**判定原则**：下文所有「基线状态」一律以 `3cf37eb` 的提交内容为准（在只读 worktree 里核对），并行中的工作只写进「进行中」列。后续轮次的审计代理请沿用「先开 worktree 再走读」的做法，直接读主工作树会把在飞改动误判成基线能力。

另请集成方注意分支纠缠：`cursor/r5b-arch-contracts-9f67` 上混入了 P1（`317bad7` 今日冒险三件事）与 P5（`03e8f93` 街机化）的 feature 提交；`cursor/r5b-use-feedback-9f67` 包含 #9 的音效提交（`664b7fe`）。合并时需去重。

---

## 1. 洪恩「好玩度」公开能力基准（本轮对标的靶子）

**洪恩识字**（官方商店文案 / 百科 / 体验报告交叉核实）：

1. **AI 学伴「川川」全程陪伴**：聪明贴心、鼓励互动，「让孩子学习动力满满」——吉祥物不是弹窗装饰，是常驻陪跑。
2. **每字「玩·认·读·练·写·测」六环节全游戏化**：800+ 基于字源字形的原创互动，每个环节都是小玩法。
3. **每日关卡节奏**：每天固定 5 字进阶关卡，**次日才自动开启下一关**；支持每日任务提醒、跳字与环节设置。
4. **汉字乐园**：上百个益智小游戏（拼图、赛车、切食物…）+ **离线/在线对战**亲子 PK。
5. **部编版学习地图** + 动画、儿歌、休息模式（约 10 分钟强制休息）。

**洪恩数学**（官方/商店文案核实）：

1. **剧情世界观**：小魔法师麦斯「战魔王、救伙伴」，探索—进阶—挑战三环节的剧情式游玩。
2. **10 大主题场景 / 400 学习场景**：糖果乐园、积木王国、发条迷城、寒冰世界……横版关卡、收集金币、打关底 boss。
3. **卡片收集成就系统**：学习过程持续掉落收集物，制造获得感。
4. **动画讲解 + 语音配音**：魔法师爷爷讲解，测练小游戏逐关配套。
5. **无需陪同的自主探索**：兴趣驱动 + 及时反馈，「让孩子用得开心」。

图例：✅ 达标 / ◐ 有 MVP 但缺洪恩级的「好玩」浓度 / ❌ 未实现。

---

## 2. 识字 App 好玩度对标（L-P1 … L-P8）

| # | 洪恩能力 | 状态 | 实测证据（基线 `3cf37eb`） | R5B 映射 | 进行中 |
|---|---|---|---|---|---|
| L-P1 | 每日任务/关卡节奏（每天 5 字关卡 + 次日开启 + 任务提醒） | ❌ | 首页无任务清单：`apps/literacy-app/src/views/HomeView.vue` hero 只有状态 pill（L114-122：🔥连续天数 / 今日分钟 / 今日新字 n/limit），**没有可勾选的「今日 N 件事」，没有完成庆祝**。素材其实齐了：`stores/progress.js` 已有 `streakDays`（L277）、`dailyGoal`/`dailyNewLimit`（L77-85）、按天记账 `state.daily`（L111/475）——缺的是任务清单 store + 首页组件 + 完成庆祝的一层组装 | **P1（主靶）** | #4：`317bad7` 已在 arch-contracts 分支（DailyAdventure.vue + dailyQuest store） |
| L-P2 | 学伴全程陪跑（川川式常驻鼓励） | ◐ | 组件能力是满配的：`components/MascotCompanion.vue`——6 种 mood 表情表（L36-43）、GSAP 呼吸/眨眼/mood 反应三层动画（L59-117）、**点触即朗读气泡**（L96-100 `onTap→speak`）、气泡左右位可配。但**全站只挂了 1 处**：`App.vue` L149 护眼休息弹窗（`mood="sleep"`）——恰是简报点名的「仅弹窗」反模式。核心路由（首页/学字/写字/游戏/绘本）0 常驻 | **P2（主靶）** | #5：`cdaa468`（五条核心路由常驻 + 点触换鼓励语） |
| L-P3 | 每字环节全游戏化（玩认读练写测） | ✅ | `views/CharDetailView.vue` 五步状态机 `intro→trace→listen→quiz→reward`（L57-62），reward 步当场摆出顺带解锁的徽章（L350-362）+ StarBurst（L522）；`components/HanziStrokeBox.vue` 逐笔判定 + 错 3 笔自动示范；**每写完一笔音高按笔序递进**（`utils/audio.js` L55-57 `sfx.stroke(index)`，480+40×index Hz）——「玩着写完一个字」的洪恩式体验已成立 | P3/P6 的现成接线点 | 维护 |
| L-P4 | 小游戏体量与大厅（汉字乐园上百款 + 对战） | ◐ | 4 款游戏注册表 `data/games.js`（listen/maze/memory/spot，带 skill 标签）；大厅 `views/GamesView.vue`：**每卡已有一句话玩法**（L24/32/40/48 desc）+「练什么」能力标签（trains，L79）——P5 的一半已达标。但布局是**纵向列表**（L104-111 `flex-direction: column`）非网格，无街机风标题/霓虹边框；对战/PK 通道为 0 | **P5（主靶）** | #8：`03e8f93` 已在 arch-contracts 分支（网格 + 霓虹边） |
| L-P5 | 学习地图叙事（部编版地图 / 场景剧情） | ◐ | `views/HomeView.vue` 学习地图：8 站左右蜿蜒 + 虚线路径（L149-179）、锁定站灰显（`.is-locked` L320-328 `opacity .6 + grayscale`）+ 锁定原因一句话（L40 `lockHint: '先学会 4 个字就能玩'`）、进场错落动画（`station-enter`，`map--quiet`/系统 reduced-motion 双降级 L290-298）。差距：lockHint 是**功能文案不是剧情**；`stores/progress.js` L234-237 单元 60% 解锁是纯 computed，**解锁瞬间无过渡动画、无庆祝、无剧情钩子**——孩子感知不到「我打开了新地方」 | **P4（主靶）** | #7：分支尚无提交（截至走读时） |
| L-P6 | 即时正反馈基建（星星/彩带/里程碑） | ◐ | 三件套齐但**各自为政**：`components/StarBurst.vue`（GSAP 星星爆，挂在 7 个视图）、`components/CelebrationOverlay.vue`（规范级：主体 ≤1.2s + 三种跳过方式 + reduced-motion 降级为静态卡 + live region 播报，L1-160）、`CelebrationLayer.vue` 全局里程碑（升级/掌握/读完绘本走 store `celebrate()`，progress.js L492/519/598/656）。**没有统一 composable、没有震动通道**，答对反馈手感与数学 App 不一致 | **P3** | #6（shared 草稿在主工作区，未提交） |
| L-P7 | 答对音效节奏（连对递进） | ❌ | `utils/audio.js` L58-62：`sfx.correct()` 是**固定三连音**（660→880→1180Hz），与连对次数无关；`views/ListenGameView.vue` 明明已维护 `streak/bestStreak` 状态（L281-283）且写进 `recordGameRound({ streak })`，答对却仍播固定音（L284）——状态在、音效不在，是**最后一公里缺口**。反证引擎能力足够：写字的 `sfx.stroke` 已做逐笔音高递进 | **P6（主靶）** | #9：`664b7fe`（STREAK_CHORDS 七档已在其分支） |
| L-P8 | 动画儿歌 / IP 剧情内容 | ❌ | 全库无儿歌、无 IP 剧情动画；唯一「内容动画”是 `components/EtymologyStage.vue` 字源演变（Round 5 交付，算部分补偿但不是儿歌/IP）。洪恩此项靠专业动画产能，开源侧短期不可复制 | R5B 未列 | 建议记入 R6 议题（低优先） |

**识字小计：✅ 1 / ◐ 4 / ❌ 3（共 8 项）**

---

## 3. 数学 App 好玩度对标（M-P1 … M-P8）

| # | 洪恩能力 | 状态 | 实测证据（基线 `3cf37eb`） | R5B 映射 | 进行中 |
|---|---|---|---|---|---|
| M-P1 | 剧情世界观（麦斯战魔王救伙伴） | ◐ | 有世界观外壳无剧情内核：「星际数学冒险」+ 6 星球各有一句话 blurb（`data/modules.js` L15/30/45…「把小星星拖进货舱」），但**没有角色、事件、boss、收集物**；锁定星球只显示 `需 {{ p.starsToUnlock }} ⭐`（`modules/home/HomeView.vue` L214）——是价格标签不是剧情钩子 | **P4** | #7：无提交 |
| M-P2 | 地图关卡解锁体验（横版关卡/解锁惊喜） | ◐ | 地图观感在线：SVG 轨道路径描画动画（HomeView L95 `strokeDashoffset` 2.2s）、星球 bob 浮动（L475-486）、锁定灰显（L510-513 `saturate(0.4)` + 🔒）、**推荐星球呼吸光晕 + reduced-motion 退化为常亮描边**（L516-537/674-685，a11y 兜底教科书级）。但解锁是被动跨阈值（`stores/progress.js` L285-287 `stars >= starsToUnlock` 纯 computed），**没有解锁瞬间的过渡动画/庆祝事件**——攒够星星时孩子毫无知觉 | **P4（主靶）** | #7：无提交 |
| M-P3 | 吉祥物陪跑 | ◐ | **覆盖面已过 P2 数量线**：`components/MascotBot.vue` 被 9 处引用——Home hero（L135）、QuizShell（L448，随其覆盖 `/arithmetic` `/daily` `/word-problems`）、数量星云/比大小、几何、规律、数独、成就墙、RoundSummary，且 mood 随答题实时切换（idle/happy/sad/think/cheer 五态 + 独立 CSS 动画）。**硬伤：纯展示 SVG**——无 click 处理、无语音、无鼓励气泡（对照识字墨墨的 `onTap→speak`），孩子拍它没反应 | **P2** | #5：`cdaa468` 只覆盖识字侧；数学侧交互缺口待确认归属 |
| M-P4 | 微反馈系统（答对的爽感） | ✅ | App 内已统一：`composables/useFeedback.js` 7 函数（pop/correct/wrong/burst/flyStar/enter/countTo），null 安全 + reduced-motion 全体降级；`components/QuizShell.vue` 接线成套（L205-207）：绿光弹跳 + **粒子数随连击加量**（`16 + min(10, combo*2)`）+ **星星飞到顶栏计数器**（flyStar→`[data-star-counter]`，到站还弹一下）。这就是 P3 想要的形态——只是「App 内统一」而非「双 App 共享」（见 S-P1） | **P3（半成品范本）** | #6 |
| M-P5 | 答对音效节奏（连对递进） | ❌ | `utils/sound.js` L28-39：5 个**固定** CUES（click/correct/wrong/star/combo），`correct` 恒为 C5-E5-G5 琶音；combo 连击只影响星星加成、文案与粒子数量，**不影响音高/节拍**。`wrong` 音「柔和下行小二度，不刺耳，保护低龄挫败感」（L33-34）值得在改造时保留 | **P6（主靶）** | #9：`664b7fe`（STREAK_CUES 七档 + gap 递紧已在其分支） |
| M-P6 | 连击与奖励爽感（卡片收集/成就激励） | ✅ | `stores/progress.js` 会话级 `combo`（L207-208/483-484）；`ArithmeticView.vue` 连击加成**画出来**（L284-291「🔥 连击 n ×2⭐/×3⭐」+ 本轮最佳）；QuizShell 连击文案「n 连击，火力全开 🔥」（L212-213）；16 个成就 + `AchievementToast` 全局弹报（App.vue L48）；`RoundSummary.vue` 奖牌三档 + 吉祥物 mood 分档 + 分档鼓励语 + ≥60 分彩带 burst（L20-41）。洪恩的「卡片收集」无直接对应，但成就体系是等价 MVP | 维护 | — |
| M-P7 | 每日打卡节奏 | ✅ | `modules/daily/DailyView.vue` + store：每天固定 5 题、完成打卡、**连续天数 streak/bestStreak + 加成星**（progress.js L400-416）；首页 CTA 三态文案 + pip 进度点（HomeView L40-50/124-133）。**这正是识字 P1 缺的模式，可整套移植** | P1 的参考实现 | — |
| M-P8 | 场景多样性（10 主题场景/400 学习场景） | ◐ | 全 App 单一星空主题（`StarField.vue` 背景 + cosmos 色板）；对照识字听音已有 3 套皮肤（`ListenGameView.vue` L32 SKINS：fish/mole 等，换皮不碰计分逻辑）。数学各模块场景固定，无一处可换装 | R5B 未列 | 建议 R6（识字 SKINS 模式可平移） |

**数学小计：✅ 3 / ◐ 4 / ❌ 1（共 8 项）**

---

## 4. 跨 App 统一层（S-P1 … S-P3）

| # | 能力 | 状态 | 实测证据 | R5B 映射 |
|---|---|---|---|---|
| S-P1 | 统一 `useFeedback`（识字+数学共用） | ❌ | 基线 `shared/` 只有 `components/`（OpenMoji 两件）与 `utils/`（openmoji/sounds/animations，**零引用方**）；`shared/composables/` 不存在。现状是三套并行：识字 StarBurst+sfx 直调、数学本地 `useFeedback`+sound、shared/utils/sounds.js 死代码。**震动（navigator.vibrate）全库零命中**。主工作区已见 #6 的未提交草稿（音效钩子注入 + HAPTIC_PATTERNS 逐级降级 + WAAPI 粒子，接口形态合理），但尚未落分支 | **P3（主靶）** |
| S-P2 | 庆祝可跳过 + 低龄挫败保护 | ✅ | 识字 `CelebrationOverlay.vue`：主体 ≤1.2s 预算、点浮层/按钮/Esc·回车·空格三路跳过、跳过与播完终态一致、reduced-motion 降为静态卡（L1-12 注释即规范）；数学 `wrong` 音刻意柔和（sound.js L33）+ 动效总开关经 `motion.setEnabled` 全局降级（App.vue L27-31）。**R5B 规则明令保留，改造 P4/P5/P6 时不得回退** | 门禁保持项 |
| S-P3 | 音效引擎可扩展性（P6 的地基） | ✅ | 两侧都是零素材 WebAudio 合成 + 语义化出口（识字 `utils/audio.js` `sfx.*`，数学 `utils/sound.js` CUES 谱面表 + `sfx` 别名层）；P6 只需替换谱面/加 `streak(count)` 入口，**调用方无需大改**——这解释了 #9 为何能先行完成 | P6 |

---

## 5. P1–P6 硬门槛差距总表（核心输出）

| # | 验收要求 | 基线状态 | 一句话差距 | 可复用底座 | 责任分支（进展） |
|---|---|---|---|---|---|
| P1 | 识字首页今日 3 件事，可勾选+完成庆祝 | ❌ | 首页只有状态 pill，无任务清单 | 数学 dailyQuest 整套模式（M-P7）；识字 `state.daily` 记账 + CelebrationOverlay | #4 `r5b-daily-adventure`（`317bad7` 已在 arch-contracts 分支，注意归位） |
| P2 | 吉祥物 ≥5 核心路由常驻，可点触语音/鼓励 | ◐ | 识字：组件满配但只挂 1 个弹窗；数学：挂了 ~9 路由但**不可点、无语音** | 墨墨 `onTap→speak`（MascotCompanion L96-100）可作数学侧交互范本 | #5 `r5b-mascot-companion`（`cdaa468` 识字侧已交；**数学 MascotBot 交互缺口无人认领**⚠️） |
| P3 | 统一 useFeedback（粒子/震动降级/音效钩子），Quiz/游戏/写字各接 1 处 | ◐ | 数学 App 内已统一成型（QuizShell 接线是范本）；**跨 App 共享 ❌、震动 ❌、识字侧未收编** | 数学 `composables/useFeedback.js` + QuizShell L205-207；识字接入点现成：CharDetail quiz（L294/302）、四款游戏、HanziStrokeBox | #6 `r5b-use-feedback`（shared 草稿未提交；其分支上目前只有 #9 的提交，注意纠缠） |
| P4 | 地图叙事解锁：灰显+一句话剧情；解锁过渡动画 | ◐ | 灰显两侧都有✅；**剧情文案与解锁瞬间动画双缺**（识字 lockHint 功能性、数学「需 X ⭐」价格标签；两侧解锁都是无声的 computed 翻转） | 识字 station 地图 + 数学 orbit/breathe/reduced-motion 退化；CelebrationOverlay 可复用作解锁庆祝 | #7 `r5b-map-narrative`（**截至走读时零提交，是 P0 里进度最落后的一项**⚠️） |
| P5 | GamesView 网格+街机风+一句话玩法 | ◐ | 一句话玩法+能力标签已达标；纵向列表非网格、无街机视觉 | GamesView desc/trains 数据结构不用动，纯视觉层改造 | #8 `r5b-games-arcade`（`03e8f93` 已在 arch-contracts 分支，注意归位） |
| P6 | 连对音高递进/节拍强化，两 App 各 ≥1 条链路 | ❌ | 两侧答对音全是固定谱面；识字 Listen 有 streak 状态没接音、数学 combo 有状态没接音——**都只差最后一公里**；讽刺的是识字**笔顺**链路反而已有音高递进（sfx.stroke） | 两侧 WebAudio 引擎 + 语义化出口（S-P3）；链路现成：ListenGame L281-284、QuizShell correct | #9 `r5b-sfx-rhythm`（`664b7fe` 双侧七档谱面已在飞，**最接近完成**） |

**总盘子：19 项 = ✅ 6（31.6%）/ ◐ 8（42.1%）/ ❌ 5（26.3%）。**
P0 六项按基线计：**0 达标 / 4 半程 / 2 空白（P1、P6）**；按在飞进展预测，P4 与数学侧 P2 交互是最可能漏交付的两处。

---

## 6. 给 #3（验收探针）与 #10（回归门禁）的建议

1. **P1 探针**：断言 `apps/literacy-app/src/stores/dailyQuest.js` 存在且任务数 = 3、勾选状态跨刷新持久化（localStorage key）、三件全勾触发一次庆祝（CelebrationOverlay/Layer 打开断言）。
2. **P2 探针**：`rg -l MascotCompanion apps/literacy-app/src/views | wc -l ≥ 5`（views 级挂载而非 App.vue 弹窗）；数学侧补「MascotBot 有 click/keydown 处理或语音调用」的源码断言，否则 P2 的「可点触」只有半边达标。
3. **P3 探针**：断言识字与数学**都** import `shared/composables/useFeedback`（或 `@shared` 别名）；HAPTIC 降级逻辑（不支持→跳过、reduced→单段轻震）写成 Node 可跑的单测——#6 草稿的 WAAPI 粒子设计本就支持无 DOM 测试。
4. **P4 探针**：锁定站/星球渲染出非空 `story`（或等价剧情字段）且不同于解锁态文案；解锁瞬间存在过渡（class 切换或 unlock 事件）且 reduced-motion 下有静态等价物——沿用数学呼吸灯的退化模式（HomeView L674-685）。
5. **P5 探针**：GamesView 根列表为 grid 布局 + 每卡 desc 非空（后者基线已满足，防回退）。
6. **P6 探针**：断言两侧音效模块导出 `streak(count)` 且谱面表**性质**成立（档位 ≥5、各档收尾音严格递增、封顶不越界）——`664b7fe` 已在飞，探针写性质别写死频率数值，否则 #9 调音就打红门禁。
7. **回归保持**：CelebrationOverlay 三路跳过与 quiet 降级、数学 wrong 音的柔和谱面、呼吸灯 reduced-motion 退化，都要有防回退断言（R5B 规则明令）。
8. **合并防呆**：arch-contracts 分支混入了 #4/#8 的 feature 提交、use-feedback 分支混入了 #9 的提交——#10 收口时先做 `git log 3cf37eb..<branch>` 的归属核对再合并，避免同一改动从两条分支进两次。

---

## 7. 审计方法备注

- 走读环境：`git worktree add /tmp/wt-r5b-audit cursor/r5b-module-audit-9f67`（= `3cf37eb`），全部证据行号以该快照为准；主工作树因并行子代理写入（见 §0）**不可作为基线依据**。
- 功能有无：逐文件读 HomeView/LearnView/GamesView/四游戏/CharDetailView/App.vue（识字）与 HomeView/QuizShell/MascotBot/RoundSummary/DailyView/sound/useFeedback/modules/progress（数学）+ 定向 grep（streak/combo/vibrate/unlock/celebrate/skin/MascotCompanion/MascotBot/useFeedback 全库扫描）。
- 洪恩能力：2026-08 检索官网 ihuman.com、小米应用商店、百度百科与第三方体验报告，仅采信多源一致的表述；「上百小游戏」「10 主题场景」等数字为宣传口径，对标时只取能力有无不取数值。
- 本轮**未重跑** `npm test`/Lighthouse：审计范围是玩法层代码走读，且共享 VM 上并行子代理正在改源码，此时实跑产出的数字不可归因；基线测试水位引用 Round 5 审计（`round5-hongen-module-audit.md` §0，72 项冒烟全绿）。收口重测归 #10。
- 在飞分支进展快照截至 2026-08-27 01:10 UTC（`git log 3cf37eb..cursor/r5b-*-9f67`），此后进展以各分支为准。
