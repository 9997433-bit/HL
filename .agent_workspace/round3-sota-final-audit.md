# Round 3 SOTA 终验审计与差距闭合计划

> 审计执行：Round 3 fable 子代理（claude-fable-5-thinking-xhigh），2026-08-26
> 审计方法：**全部结论来自本轮实测，不引用 Round 2 旧报告的声称值。**
> 测量环境：Node 22.14.0 / Chrome 148.0.7778.96 headless / Lighthouse 12.8.2（mobile 模拟节流）/ axe-core 4.13.0
> 复现方式：`git worktree add <dir> <commit> && npm ci && npm i -D lighthouse && npm run test:acceptance`

## 0. 审计基线与并发说明

本轮 10 个子代理在**同一工作区并发提交**，代码是移动目标。为得到可复现的数字，
审计在两个用 `git worktree` 固定的提交快照上执行：

| 快照 | 提交 | 含义 |
|---|---|---|
| S1 | `99e6197` | Round 3 起点（= Round 2 合并终态） |
| S2 | `12a4192` | 本审计执行时可测的最新提交（含字库 200、数学家长中心、axe 清零修复） |

审计期间观察到 S2 之后仍在推进的 in-flight 提交：设计令牌迁移（3 个 tokens 提交）、
`THIRD_PARTY_NOTICES.md`、数学 settings/动效工具改造。这些**未计入 S2 分数**，在表中以
🔄 标注。最终出包前须按 §4 的门禁在合并终态重测一次。

**Round 2 简报纠偏**：ROUND2-BRIEF 声称「axe critical=0、53 serious 待修」。S1 实测为
**critical=4、serious=63**（识字字表 aria-required-children ×1、数独 aria-required-children ×1、
成就墙 button-name ×2）。该差距已被本轮 axe 修复代理在 S2 闭合（实测 0/0），但说明
**轮次简报的声称值必须以脚本重测为准**。

## 1. 实测数据汇总

### 1.1 自动化门禁（`npm run test:acceptance` 等）

| 指标 | S1 `99e6197` | S2 `12a4192` | Round 3 终值门槛 | 判定 |
|---|---|---|---|---|
| npm test（FSRS 8/8 + check:data + smoke + 构建） | ✅ 全绿 | ❌ 识字 smoke 1 项失败（见 §4-A） | 全绿 | ❌ |
| check:data 字库 | 106 字 | **200 字**（12 单元） | ≥200 | ✅ |
| 绘本 / 成语 | 3 本 / 8 条 | **5 本 / 20 条** | ≥5 或 ≥20 | ✅ |
| 构建时间 | 识字 1.9s / 数学 1.6s | 识字 2.6s / 数学 2.1s | ≤60s | ✅ |
| 首屏 JS gzip | 识字 101.5KB / 数学 79.4KB | 识字 **115.4KB** / 数学 81.5KB | <250KB | ✅（识字 +14KB，见 §4-C） |
| Lighthouse Perf | 识字 91 / 数学 94 | 识字 **86–89** / 数学 **90–93** | ≥95（过渡 ≥90） | ❌ 识字连过渡值都不稳 |
| Lighthouse A11y | 识字 87 / 数学 93 | 识字 **92** / 数学 **93** | ≥95 | ❌（唯一失分项 = meta-viewport，见 §4-B） |
| Lighthouse BP | 100 / 100 | 100 / 100 | ≥90 | ✅ |
| axe critical / serious | **4 / 63** | **0 / 0**（20/20 页面） | 0 / 0 | ✅ 已闭合 |
| test:offline 断网冷启动 | ✅（预缓存 249/29 项） | ✅（预缓存 367/32 项） | 通过 | ✅ |

### 1.2 Lighthouse 核心指标明细（S2，本地静态服务无 gzip——见 §4-C 的测量伪影说明）

| 指标 | 识字 | 数学 | 阈值 | 判定 |
|---|---|---|---|---|
| FCP | 2.8s | 2.2s | <1.0s | ❌ 双 App |
| LCP | 3.0s | 2.5s | <1.5s | ❌ 双 App |
| TTI | 3.1s | 2.7s | <2.0s | ❌ 双 App |
| TBT | 120ms | 100–270ms | <150ms | ✅ 识字 / ⚠️ 数学波动 |
| CLS | 0.002 | 0 | <0.05 | ✅ 双 App |

LH 失分归因（audits 明细）：双 App A11y 唯一失分审计 = `meta-viewport`
（index.html 带 `user-scalable=no, maximum-scale=1.0`）；Perf 三大机会 =
`uses-text-compression`（识字 207KB/数学 136KB，**测量服务器不支持 gzip 的伪影**）、
`render-blocking-resources`（识字 300ms）、`unused-javascript`（约 72–78KB，识字主要是
200 字的 `characters.js` 全量打进首屏入口 chunk）。

## 2. SOTA 清单逐项复评（S2 实态）

评分口径：✅=1，◐=0.5（部分满足），❌=0（未做或未实测）。证据均为本轮代码走查/脚本实测。

### 2.1 识字 App

**功能 P0（7.0/9 = 78%）**

| # | 项 | 分 | 证据 |
|---|---|---|---|
| L-F1 | 字库 200 字 | ✅ | check:data 通过：200 字/12 单元，拼音/释义/例词/笔顺齐 |
| L-F2 | 认→写→测闭环 | ◐ | 认+写在单字页；「测」是独立路由（/listen），无环节自动衔接 |
| L-F3 | 笔顺书写 | ◐ | 演示可重播、逐笔判定 ✓；**错 3 次自动示范该笔 ✗**（HanziStrokeBox 仅提示重试） |
| L-F4 | 听音识字 | ✅ | 2×2 选项、温和反馈（aria-live）、可重试，smoke 实测 3 题 |
| L-F5 | FSRS 复习 | ◐ | FSRS 接线 + 首页复习入口 ✓；smoke 实测**到期卡在队列中不可打开**（回归，§4-A） |
| L-F7 | 奖励系统 | ◐ | 星星 ✓、庆祝可跳过 ✓（smoke 实测）；无徽章体系、回看页弱 |
| L-F8 | 家长面板 | ✅ | 两位数加法门 + 热力图 + 主题/字号/音量/动效/时长设置，smoke 实测切主题持久化 |
| L-F9 | 进度持久化 | ✅ | localStorage + 导出/导入 JSON 均有，smoke 实测刷新无损 |
| L-F10 | 防沉迷 | ✅ | 默认 20min 护眼休息提醒 + 休息完成回执（App.vue） |

**性能 P0（2/7 = 29%）**：L-P3 ✅（CLS 0.002/TBT 120ms）、L-P4 ✅（115KB gzip；单字笔顺
文件最大 <30KB，公共 hanzi-data 218 个文件共 884KB 按字懒加载）。L-P1 ❌（86–89）、
L-P2 ❌（FCP/LCP/TTI 全超）、L-P5/P6/P7 ❌**未实测**（帧率/音效延迟/内存，无测量记录）。

**无障碍 P0（4/6 = 67%）**：L-A6 ✅（prefers-reduced-motion + 家长开关）、L-A7 ✅。
L-A1 ◐（axe 0/0 ✓ 但 LH 92<95，卡在 meta-viewport）、L-A2 ◐（--tap-min:56px 令牌存在，
未做全页走查记录）、L-A3 ◐（axe 默认主题对比度已清零；care/night 主题未逐一抽查，第 4
主题未交付）、L-A4 ◐（按钮/卡片可 Tab；**描红无键盘替代**）。

**离线 P0（3/4 = 75%）**：L-O1 ✅（实测断网冷启动 + 367 项预缓存）、L-O2 ✅（笔顺/字体/
音效全本地；jsDelivr CDN 仅作离线索引未命中时的回退，200 字全部有本地数据）、
L-O4 ✅（hash 路由 + 相对 base）。L-O3 ❌（懒加载失败无角色化重试 UI）。

**识字 P0 合计：16/26 ≈ 62%**（其中 3 项是「未实测手动项」；剔除后 16/23 ≈ 70%）

### 2.2 数学 App

**功能 P0（5.5/10 = 55%）**

| # | 项 | 分 | 证据 |
|---|---|---|---|
| M-F1 | 知识覆盖 + 题库 | ◐ | 7 类玩法齐 ✓（数感/算术/几何/逻辑/数独/应用题/比较）；38 个母题生成器但 **无种子、无可复现题目 ID、未达「≥300 题」口径** |
| M-F2 | 剧情关卡 | ◐ | 星球按星星数解锁 ✓；非线性关卡地图，无「当前关呼吸高亮」粒度 |
| M-F3 | 互动教具 ≥3 | ◐ | 拖拽计数（数量星云）+ 数轴（算术 20 以内）= 2 种；分与合缺、**拖拽无点选替代** |
| M-F4 | 数形结合演示 | ❌ | 无「实物→图形→算式」演示动画 |
| M-F5 | 难度自适应 | ❌ | mastery EMA 只记录不驱动；无连对升档/连错降档 |
| M-F6 | 错题本 | ❌ | 仅 errorTagCounts 错因统计；**无按题目 ID 的错题记录与重练移出** |
| M-F7 | 奖励系统 | ✅ | 星星评级 + 章节徽章（achievements）+ 庆祝可跳过 |
| M-F8 | 家长面板 | ✅ | 本轮新合入：口算门 + 技能雷达 + 错因统计 + 时长提醒 + JSON 导出（smoke/axe 已覆盖该页） |
| M-F9 | 进度持久化 | ✅ | localStorage + exportReport；导入为 P1 |
| M-F10 | 防沉迷 | ✅ | dailyLimitMinutes（默认 20）+ 前台 15s 采样，超时提醒 |

**性能 P0（1.5/9 = 17%）**：M-P4 ✅（81.5KB gzip）、M-P3 ◐（CLS 0 ✓、TBT 100–270ms 波动）。
M-P1 ❌（90–93）、M-P2 ❌、M-P5/P6/P7/P8 ❌未实测、**M-P9 ❌（`utils/random.js` 纯
Math.random，无 seed，同题不可复现）**。

**无障碍 P0（5.5/8 = 69%）**：M-A6 ✅、M-A7 ✅、M-A8 ✅（cosmos 主题 axe 对比度零违规）。
M-A1 ◐（axe 0/0 ✓、LH 93 卡 meta-viewport）、M-A2/A3 ◐（同识字）、M-A4 ◐（QuizShell/
数独有键盘，拖拽教具无）、M-A9 ◐（数独 ✓、数量星云拖拽 ✗）。

**离线 P0（3/4 = 75%）**：M-O1/O2/O4 ✅（实测），M-O3 ❌。

**数学 P0 合计：15.5/31 = 50%**（剔除 4 项未实测手动项后 15.5/27 ≈ 57%）

### 2.3 共同项

| # | 项 | 分 | 证据 |
|---|---|---|---|
| C-1 隐私（P0） | ◐ | 零遥测/广告/SDK ✓；hanziData.js 保留 jsDelivr **CDN 回退分支**——正常运行零外域，但严格「无任何外部域名请求」口径下该分支应被证明不可达或移除 |
| C-2 合规（P0） | ❌→🔄 | S2 无 THIRD_PARTY_NOTICES；审计期间已见 `THIRD_PARTY_NOTICES.md` 合入（in-flight），需终态确认四项署名 + 随 zip 分发 |
| C-3 打包（P0） | ◐ | build:all/zip 脚本 ✓、双 zip 产物在；但 npm test 有 1 失败项，zip 未按终态重打包 |
| C-4 设计令牌（P1） | ❌→🔄 | S2 双 App 均未引入 shared/design-tokens.css（识字自带 theme.css，数学 main.css 硬编码 21 处色值）；in-flight tokens 提交正在迁移 + check-tokens.mjs 门禁 |
| C-5 设计走查（P1） | ❌ | 无 §12 清单留档 |
| C-6 浏览器矩阵（P1） | ❌ | 无走查记录（本环境只有 Chrome） |
| C-7 差异化（P2） | ✅ | 3 主题/护眼、JSON 导出、庆祝可跳过、离线全功能、零付费墙——多项超越洪恩证据成立 |

**共同 P0 合计：1/3 ≈ 33%**（in-flight NOTICES 落地后 2/3）

## 3. P0 / P1 完成度百分比（S2 实测口径）

| 维度 | 识字 | 数学 | 共同 | 加权合计 |
|---|---|---|---|---|
| 功能 P0 | 78% (7/9) | 55% (5.5/10) | — | 66% |
| 性能 P0 | 29% (2/7) | 17% (1.5/9) | — | 22% |
| 无障碍 P0 | 67% (4/6) | 69% (5.5/8) | — | 68% |
| 离线 P0 | 75% (3/4) | 75% (3/4) | — | 75% |
| 共同 P0 | — | — | 33% (1/3) | 33% |
| **P0 总体** | **62% (16/26)** | **50% (15.5/31)** | 33% | **≈54% (32.5/60)** |
| P0（剔除 7 项未实测手动项） | 70% | 57% | 33% | **≈61% (32.5/53)** |
| **P1 总体**（L-F6、L-F9 导入、L-A5、C-4、C-5、C-6） | — | — | — | **≈42% (2.5/6)** |

计入审计期间观察到的 in-flight 提交（NOTICES、tokens）后，P0 约 **57%**、P1 约 **58%**。

对照 ROUND2-BRIEF 的 Round 3 攻坚清单：

| Brief 攻坚项 | 状态 |
|---|---|
| P0-1 axe serious→0 | ✅ 已闭合（实测 0/0，20 页） |
| P0-2 设计令牌迁移 | 🔄 in-flight（S2 后 3 个提交） |
| P0-3 字库 200 + 绘本 5 + 成语 20 | ✅ 已闭合（实测） |
| P0-4 数学家长面板 | ✅ 已闭合（含防沉迷/导出/报表） |
| P0-5 Lighthouse ≥90 + acceptance-log-round3 | ❌ 识字 Perf 86–89；log 未创建 |
| P1-6 描红键盘 / aria-live 播报 / 错 3 次示范 | ❌ 三项均未做 |
| P1-7 NOTICES / README / zip 重打包 | 🔄 NOTICES in-flight；zip 未重打包 |

## 4. Round 3 必须闭合项（按投入产出排序）

**A. 修复 FSRS 复习队列回归（P0，npm test 全绿的前提）**
smoke 实测：到期卡「日」进入复习队列但 `card.click()` 不可打开（`aria-disabled` 或选中了
字表分页中的同名禁用卡）。200 字分页/单元锁定与复习队列的交互引入的回归。
验证：`npm --prefix apps/literacy-app run smoke` 12/12 交互全绿。

**B. meta-viewport 解锁缩放（两 App 各一行，LH A11y 92/93 → ≥95 的唯一障碍）**
两个 index.html 移除 `maximum-scale=1.0, user-scalable=no`；若需防儿童误双击缩放，改用
CSS `touch-action: manipulation`。验证：LH Accessibility ≥95 双 App。

**C. Lighthouse Performance：识字 86–89 → ≥90（过渡）→ 95（终值）**
1. `characters.js`（200 字数据，首屏 unused-JS 主因，S1→S2 首屏 +14KB gzip）移出入口
   chunk：动态 import 或 Vite manualChunks + 路由级懒加载；
2. `scripts/acceptance.sh` 内置静态服务器加 gzip（`uses-text-compression` 罚了识字 207KB/
   数学 136KB——真实部署都有压缩，当前是测量伪影，修掉预计双 App +3~5 分）；
3. 识字 render-blocking CSS 300ms：关键 CSS 内联或拆分首屏样式。
验证：`npm run test:acceptance` Perf 双 App ≥90（终值冲 95），S2 数值随附于 log。

**D. acceptance-log-round3.md 回填实测 + 终态重测重打包（P0 出包门槛）**
本文件 §1 的数据可直接作为底稿；合并终态跑 `npm run test:round3`（本轮已加）后重打
两个 zip（build-all 需包含 THIRD_PARTY_NOTICES）。

**E. C-2 / C-4 收尾（in-flight 已在推进，需终态确认）**
NOTICES 四项署名（HanziWriter MIT、hanzi-writer-data APL+ARPHICPL、OpenMoji CC BY-SA、
字体 OFL）齐全且随 zip；tokens 迁移后 `check-tokens.mjs` 纳入 npm test。

**F. C-1 严格化：CDN 回退不可达证明（小改动）**
在 `check:data` 里断言「字表 ⊆ public/hanzi-data/index.json」，使 jsDelivr 分支运行时
不可达；或直接删除回退分支。验证：断网走查全流程 Network 零外域请求。

**G. P1 三小件（brief 明确列入 Round 3，工程量小）**
① 数学 QuizShell 答题结果 aria-live 播报（识字已有多处，数学仅 AchievementToast）；
② 笔顺错 3 次自动示范该笔（HanziStrokeBox onMistake 计数 ≥3 时调 animateStroke）；
③ 描红键盘替代最小实现（按键逐笔演示+确认，满足 L-A4「闭环可纯键盘完成」）。

**H.（若本轮要宣称 SOTA 达标则必闭合，否则转 §5 并在总结报告降级声明）**
- M-F6 错题本：progress store 增 `wrongBook[questionId]`，重练答对移出（错因统计已有，
  仅缺按题记录+重练入口）；
- M-P9 + M-F1：`random.js` 换可种子 PRNG（mulberry32 一类），题目 ID = 母题 id+seed，
  38 母题 × 参数域即满足「≥300 可复现」口径。

## 5. 可延期项（Round 4 / 记录在案不阻塞出包）

| 项 | 理由 |
|---|---|
| M-F4 数形结合演示动画 | 工程量大（动画+旁白+跳过/重播），不影响现有玩法正确性 |
| M-F5 难度自适应闭环 | mastery 数据已积累，缺调度器；可与 M-F6 错题本一起做 |
| M-F3 第 3 种教具（分与合）+ 拖拽点选替代 + M-A9 教具键盘 | 依赖新交互组件；数独/Quiz 键盘已可用 |
| L-F2 三环节自动衔接、徽章体系 | 现有页面均可达，属体验增强 |
| L-O3 / M-O3 弱网角色化重试 UI | 离线冷启动已全绿，仅剩边缘弱网场景 |
| 第 4 主题 + 四主题对比度抽查 | Round 2 已允许 3 主题；axe 默认主题对比度已清零 |
| L-P5/P7/M-P8 帧率、内存、拖拽跟手实测 | 需人工 DevTools 走查；本环境无法自动化，出包时在 log 中标注「未实测」 |
| L-P6 音效延迟测量 | 播放路径已本地预解码，仅缺测量记录；可加 performance.now 打点脚本后补 |
| C-5 设计走查留档、C-6 浏览器矩阵 | 需 Safari/Firefox/iPad 真机环境 |
| L-F9 IndexedDB 升级 | localStorage 容量对当前数据量足够 |

## 6. 风险与协调提示

1. **并发提交风险**：10 代理共用分支，S2 之后 HEAD 已再前进（tokens/NOTICES/settings）。
   §4-D 的终态重测必须在所有闭合项合并后执行，且以 `test:round3` 为唯一门禁入口。
2. **测量方法一致性**：acceptance 的 LH 分数受静态服务器无 gzip 影响被系统性低估
   （§4-C-2）。修复后历史分数不可直接对比，log 中注明测量方法变更。
3. **数学 TBT 波动**（100↔270ms）：headless 环境噪声，终测建议取 3 次中位数。
4. **SOTA 宣称口径**：若 §4-H 不闭合，最终总结报告应写「SOTA 关键差异化项全部达成
   （C-7），完整 P0/P1 清零尚余 M-F4/M-F5/M-F6/M-P9 与手动实测项」，不得笼统宣称
   「全部 P0 清零」——Round 2 简报的声称/实测偏差（axe 0 vs 4 critical）是前车之鉴。
