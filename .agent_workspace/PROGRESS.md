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
| Round 5B | ✅ **已闭合** | Play Layer：每日冒险/吉祥物/useFeedback/街机大厅（check:round5b 全绿） |
| Round 6 | ✅ **已闭合** | 1800字/130绘本/古诗20/跟读/185母题（check:round6 全绿） |
| Round 7–12 | ✅ **已闭合** | 各轮 check:round{N} 全绿；简报/验收见 ROUND{N}-BRIEF / acceptance-log-round{N} |
| Round 13 | ✅ **工程闭合** | `check:round13` **7/8**（H7 BLOCKED）；体验 ◐6 见 round13-hongen-audit |
| Round 14 | 🔄 **编排启动** | 洪恩体验对齐；`check:round14` 基线 1/8；见 ROUND14-BRIEF |

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

---

## R13 集成状态（2026-08-28 · cursor/openmoji-integration-9f67）

> 合规审计：`.agent_workspace/ORCHESTRATION-COMPLIANCE-AUDIT.md`
> 当前模式：**集成线 cherry-pick + 探针复验**（单代理收尾，非 3-Round Loop——已在审计 G4 明示）
> 分支映射：SOP 的 `agent/<task-name>` → 平台强制 `cursor/<task>-9f67`；R13 十路子代理分支见 ROUND13-BRIEF §子代理分工

### 探针分数（check:round13 v1.1）

| 时点 | 分数 | 红灯 |
|---|---|---|
| R12 闭合基线（9f7ae90） | 1/8 | H1–H7（功能未合入，预期红） |
| origin b846ecd（本 VM 检出即测） | 5/8 | H2（reflux/harness 缺 ROUND13_H2 实体）、H6（APK 未落盘，report 陈旧）、H7（BLOCKED） |
| 本轮修复后 | 7/8 | 仅 H7（BLOCKED，预期红——见下） |

### H7 阻断原因

无经授权的 Google Play Console 账号/上传密钥/Play App Signing 配置，真实内测提交无法执行；
v1.1 探针封死 dry-run 冒充路径，H7 红灯是诚实信号。解阻两条路（真提交 / 用户签字接受 7/8 终态）
见审计报告 §3；在此之前 **保持 BLOCKED，禁止伪造 SUBMITTED**。

### 复验纪律（换环境必读）

H6/H2 的 sim 腿对账本机构建产物（APK sha256、证据日志），新环境复验前必须先：
`npm install` → 装 Android SDK 34 + JDK17 → `ANDROID_HOME=$HOME/android-sdk npm run android:sim`，
再跑 `npm run check:round13`。直接跑探针必然 H6 红，不是退化。

### 建议 Round 3 六路分工（2 fable + 2 opus-fast + 2 gpt-sol）

| # | 模型 | 任务 | 出口判据 |
|---|---|---|---|
| 1 | fable | H7 解阻材料包：Play Console 提交运行手册终稿 + 「洪恩」命名法务复核清单 + Secrets 需求清单 | 用户可按单执行的解阻包 |
| 2 | fable | R13 终验审计 + R14 是否开轮的 Go/No-Go 论证 | 审计文档 + 明确建议 |
| 3 | opus-fast | ASR available flip 预备：冻结集实录补录方案 + RTF 真机复算口径 | r13-followread-release.md 放行腿可判 |
| 4 | opus-fast | OCR 回流机制首批演练：用 fixtures 现有样张走一遍采集→标注→复现→闭环账本 | r13-ocr-regression-loop.md §1.4 账本非零 |
| 5 | gpt-sol | 真机 QA 执行包：test-ocr-device B 段 + ANDROID-DEVICE-CHECKLIST 合并为单页可执行清单 | QA 拿设备即跑 |
| 6 | gpt-sol | 性能回归：双 App 首屏 gzip 预算复测 + Lighthouse CI 趋势回填 acceptance-log §2.3 | 预算表全填、无超支 |

---

## R14 Loop 状态（2026-08-28 · 洪恩体验对齐）

> 简报：`.agent_workspace/ROUND14-BRIEF.md`
> 验收：`.agent_workspace/ROUND14-ACCEPTANCE.md` + `scripts/check-round14.mjs`
> 基线：`check:round14` **1/8**（仅 H8 绿）

| 轮次 | 状态 | 目标 |
|---|---|---|
| Round 14-1 | ✅ **已合入** | 6/6 路合入集成线 @ `6004e70` 区域；H2 app=40/41 |
| Round 14-2 | ⏳ | ASR 300 条 + device RTF + 范唱 13/13 |
| Round 14-3 | ⏳ | W1–W6 + H7 内测 + 体验 ◐ 清零 |

体验 flip 目标：L-M9/L-M10/L-M11/L-M15/M-M16 → ✅；L-M5 大幅收窄（400+ scene）。
