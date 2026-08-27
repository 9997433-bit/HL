# 洪恩式教育软件项目进度

## 项目目标
构建两个超越洪恩识字/洪恩数学的开源教育 Web 应用，最终打包为两个独立压缩包。

## 竞品分析摘要（洪恩优势）
### 洪恩识字
- 1800常用字 + 130本分级绘本
- AI学伴、拍照识字、记忆曲线个性化
- 800+字源互动、50+成语国学
- 动画/儿歌/创意互动三位一体

### 洪恩数学
- 3-12岁一站式：启蒙200+课、1000+互动
- 应用题母题185道、计算专题、数独/逻辑专项
- 剧情化演绎、碎片化学习

## 全面超越洪恩
- **主计划**：`.agent_workspace/SURPASS-HONGEN-MASTER-PLAN.md`（模块对标表 + Round 4–7 路线）
- **当前差距**：内容体量约 10–20% 洪恩；工程 SOTA P0 约 60–70%；需 4 轮并发攻坚
1. **完全开源** + 离线可用 + 无订阅墙
2. **Web技术栈**：Vue3 + GSAP动画 + HanziWriter + Tone.js
3. **开源资源**：hanzi-study、HanziWriter、makemeahanzi、OpenMoji、Lottie
4. **差异化**：家长仪表盘、护眼模式、多终端进度同步、开源可定制

## 3轮循环状态
| Round | 状态 | 说明 |
|-------|------|------|
| Round 1 | ✅ 完成 | 双 App 构建通过；zip 已打包 |
| Round 2 | ✅ 完成 | 10子代理合并；识字106字+FSRS；数学QuizShell+瘦身；离线SW |
| Round 3 | 🔄 收尾中 | SOTA 打磨；200字/家长中心/axe0/a11y/NOTICES/tokens/OpenMoji |
| Round 4 | ✅ **已闭合** | 500字+状态机+错题本+自适应+Lighthouse；check:round4 全绿 |
| Round 5 | ✅ **已闭合** | 1000字/30绘本/60成语/118母题/字源65/教具/3小游戏；check:round5 12/12 |
| Round 5B | 🔄 **进行中** | Play Layer：每日冒险/吉祥物/useFeedback/街机大厅（见 ROUND5B-BRIEF.md） |
| Round 6 | 🔄 **进行中** | 1800字/130绘本/古诗20/跟读/185母题（见 ROUND6-BRIEF.md） |

## 并发规则（已更新）
**每轮固定 10 个子代理并发，缺了立马补。**

## Round 1 子代理任务（10个）
- fable×3: 架构规划、SOTA审计、UI/UX设计规范
- opus-fast×4: 识字核心、数学核心、识字视图完善、数学视图完善
- gpt-sol×3: 开源资源探针、测试打包脚本、动画音效集成与性能基准

## Round 1 交付记录
- [x] fable·识字架构: `.agent_workspace/literacy-architecture.md`（…）；`src/utils/srs.js` FSRS-lite 契约。
- [x] fable·数学架构: `.agent_workspace/math-architecture.md`（参数化生成器降维、core 引擎层、题目协议全链路）；`apps/math-app/src/core/engine/*` 已冒烟通过。
- [x] fable·UI/UX: `ui-ux-design-spec.md`、`sota-acceptance-criteria.md`
- [x] gpt-sol·资源/探针: 100字/85题/42成语；`verify-resources.sh` / `benchmark.sh` / `stress-test.js`
- [x] opus-fast·双 App MVP + 打包: `dist/hongen-literacy-app.zip`（271KB）、`dist/hongen-math-app.zip`（143KB）

## Round 3 子代理任务（10个，进行中）
- fable×3: 终验审计、令牌迁移验收、文档与 NOTICES 对齐
- opus-fast×4: 识字200字+内容、识字a11y、数学家长面板、设计令牌落地
- gpt-sol×3: axe serious清零、Lighthouse终验打包、全量E2E回归

## Round 2 首要清理项
- **math-app**：`modules/*` 视图（路由生效） vs 未引用的 `core/engine/*`、`src/views/*`；数独/应用题/生成器各存两套，需收敛；Tone.js 包体可换轻量 WebAudio。
- **literacy-app**：`HomeView/LearnView/...`（路由生效） vs `HomeMap/Books/Idioms/...`（未引用）；同上归并。
