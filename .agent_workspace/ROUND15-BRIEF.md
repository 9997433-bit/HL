# Round 15 简报 · 一字一动画（玩·认·练·写·说）

> 基线：`cursor/openmoji-integration-9f67` @ Round 14-3（`check:round14` **4/8**；体验缺「洪恩式进字动画」）
> 编排分支：`cursor/r15-orchestration-9f67`
> 集成分支：`cursor/openmoji-integration-9f67`（功能分支 cherry-pick 合入）
> 目标：**每个字进学习时都是动画/互动闯关**；缺内容**自动模板补齐**；开源离线全库覆盖，体验密度 ≥ 洪恩

## 为何还要 Round 15

网上核对洪恩识字玩法（官网 / App Store / 体验报告）确认：

| 洪恩环节 | 做法 | 咱们 R14 现状 | R15 目标 |
|---|---|---|---|
| **玩** | 进字前情境小游戏（~1min） | ❌ 无；游戏在街机厅 | **每字必有 Play 场景** |
| **认** | **按字源字义定制动画**（象形演变/组词） | ◐ 字源 808 字可选按钮，非默认主路径 | **认步自动播字源/叙事动画** |
| **练** | 听音找字等互动 | ✅ listen 步 | 保留并接入统一反馈 |
| **写** | 动画引导 + AI 纠错 | ◐ hanzi-writer 工具型 | **写前动画示范引导** |
| **说/测** | 读测过关 | ✅ quiz + reward | 标签对齐「说」 |

洪恩卖点原文：「根据字源、字义设计每一个汉字动画」「800+ 趣味互动」。  
开源差异化（**做得更好**）：

1. **1820 字 100% 有 Play 场景**（洪恩是精选互动，不是全库同密度）——缺定制脚本时 **模板自动补**
2. 完全离线、无订阅墙、reduced-motion / 可跳过
3. 程序化 DSL + OpenMoji，新字入库即有玩法，不靠手搓美术 IP

## 硬门槛（`check-round15.mjs`，基线预期 0–1/8）

| 探针 | 阈值 | 说明 |
|---|---|---|
| **H1** 五步对齐 | `CharDetailView` 步骤含 **玩→认→练→写→说**（或等价 id：`play/intro/listen/trace/speak`）且默认从玩开始 | 流程对齐洪恩 |
| **H2** Play 引擎 | 存在 `CharPlayStage`（或等价）+ `getCharPlay(char)`；**CHARACTERS 全库 resolve 非空** | 缺了自动补的契约 |
| **H3** 富脚本批次 | ≥**200** 条非 `templateFallback:true` 的定制/半定制 play 脚本（优先 u1–u20） | 对标洪恩「一字一互动」密度入口 |
| **H4** 认步字源默认播 | 有字源的字在「认」步 **自动展开/播放** EtymologyStage（非仅角落按钮） | 认 = 动画学 |
| **H5** 自动补齐管道 | `gen-char-play.mjs`（或等价）+ seed；未手写字走 radical/emoji/theme 模板；`check:data` 或 H2 断言 0 空洞 | 「缺了自动补」 |
| **H6** 写步引导动画 | 进入「写」步先播笔顺示范（可跳过），再进描红测验 | 对齐洪恩写环节 |
| **H7** 回归不伤玩 | literacy smoke 覆盖 play 流；`reduceMotion` 下可完成；庆祝可跳过 | a11y |
| **H8** 往轮不退化 | `check:round14` 不降于编排时基线 **或** `check:round13` ≥7/8 | 链式兜底 |

## 子代理分工（10，固定并发；缺了立马补）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r15-arch-contracts-9f67` | Play 数据契约、阶段机、包体边界、自动补齐策略 |
| 2 | fable | `cursor/r15-hongen-play-audit-9f67` | 洪恩玩法对标表 + 咱们逐字体验差距（◐→✅） |
| 3 | fable | `cursor/r15-acceptance-spec-9f67` | `ROUND15-ACCEPTANCE.md` + `check-round15.mjs` v1.0 + acceptance-log 模板 |
| 4 | opus-fast | `cursor/r15-play-engine-9f67` | `CharPlayStage` + 模板运行时（GSAP/OpenMoji）；`getCharPlay` |
| 5 | opus-fast | `cursor/r15-phase-remap-9f67` | `CharDetailView` 改五步玩认练写说；接 Play / 字源默认播 / 写前示范 |
| 6 | opus-fast | `cursor/r15-play-catalog-rich-9f67` | u1–u20（或前 200 字）富互动脚本 seed |
| 7 | opus-fast | `cursor/r15-play-autofill-9f67` | `gen-char-play.mjs`：全库模板回填 + index；空洞为 0 |
| 8 | opus-fast | `cursor/r15-write-guide-9f67` | 写步引导动画（示范→描红）与反馈接线 |
| 9 | gpt-sol | `cursor/r15-play-smoke-tests-9f67` | smoke / vitest：全库 getCharPlay、五步流、reduced-motion |
| 10 | gpt-sol | `cursor/r15-regression-gate-9f67` | `check:round15` 接线 npm + 往轮探针 + acceptance-log 回填 |

## 数据契约（架构岗细化，实现岗遵守）

```ts
// 概念草稿 —— 以 arch 文档为准
type CharPlay = {
  char: string
  theme: string           // nature | body | family | action | ...
  template: string        // morph-story | tap-reveal | drag-parts | emoji-hunt | rain-catch | ...
  narration: string       // 孩子能听懂的一句
  props?: Record<string, unknown>
  templateFallback?: boolean  // true = 自动补齐；false/缺省 = 富脚本
}
```

- **禁止**伪造洪恩 IP / 抄美术；只用 OpenMoji + 程序化 SVG/GSAP
- **禁止**为过探针写死假 `getCharPlay` 对未知字返回占位却 UI 空白——舞台必须可玩完（≥1 次有效交互或可跳过完成）
- 字源语料继续走现有 `etymology-*`；本轮不强制扩到 1820 字源，但 **Play 覆盖必须 1820/1820**

## 规则

- 分支名：`cursor/<descriptive>-9f67`；worktree 开发，避免抢 `/workspace`
- 首提交注明 Model slug；合入 `cursor/openmoji-integration-9f67` 用 cherry-pick
- 合并前：`npm run check:round15` + literacy 相关 test/smoke
- reduced-motion / 「跳过这一步」必须保留（WCAG）
- 证据目录：`.agent_workspace/evidence/r15/`

## 成功体验（比探针更严）

孩子点开任意一字：先出现 **和这个字意思相关的小动画/小互动（玩）** → 再看字源或字形讲解动画（认）→ 听音练（练）→ 看示范再描红（写）→ 答题领星星（说）。  
抽查 20 个无富脚本的冷门字，仍能玩完，且不是同一张空白卡。
