# Round 16 简报 · 体验密度反超（认步补全 · 数学「学」 · 人格与可解释）

> 基线：`cursor/r15-orchestration-9f67`（`check:round15` **8/8**，玩认练写说已通）
> 编排分支：`cursor/r16-orchestration-9f67`
> 模型 SOP（永久）：**fable ×3 + opus-fast ×5 + gpt-sol ×2**  
> 目标：把「功能对齐」推进到「体验密度与可解释性超过洪恩精选付费课」——不抄 IP，用全覆盖 + 算理演示 + 人格 + 家长可懂报告反超

## 为何 Round 16

网上对标结论（见对话审计）：

| 洪恩强项 | R15 后我们 | R16 要翻的牌 |
|---|---|---|
| 精美一字一动画 | 玩步全库有，**无字源字认步仍偏文字** | **认步默认动画（无字源也播）** |
| 精选 800 互动「哇」感 | 富脚本 **272** + 模板 | **富 Play ≥500**（前段手感接近洪恩） |
| 数学「学」动画课 | 星球刷题强，**学演示弱** | **技能 实物→图形→算式** |
| 应用题视频剖析 | 母题有提示，缺剖析壳 | **母题剖析页** |
| AI 学伴川川 | 墨墨有，人格薄 | **阶段化人格剧本** |
| 家长报告 | 有统计 | **弱项一句话 + 建议 3 题** |

真机 ASR/OCR/商店仍依赖外部供给 → **本轮不作为硬绿门槛**（记入审计 BLOCKED 台账，不阻塞 8/8）。

## 硬门槛（`check-round16.mjs`，启动预期 0–1/8）

| 探针 | 阈值 |
|---|---|
| **H1** 双 App 体验总表 | `.agent_workspace/round16-hongen-gap-audit.md` 含识字+数学模块表，每项 ✅/◐/❌ + R16 归属 |
| **H2** 无字源认步动画 | 无 etymology 的字在 `intro` **默认**挂载讲解舞台（部首/零件/组词情境三选一），标记 `ROUND16_H2`；抽查冷门字非空白 |
| **H3** 富 Play ≥500 | `countRichPlays()≥500` 或等价；`templateFallback≠true`；narration 去重达标（沿用 R15 v1.1 精神） |
| **H4** 数学「学」演示 | ≥**12** 个技能点有「实物→图形→算式」可跳过演示（组件或路由），`ROUND16_H4` |
| **H5** 应用题剖析壳 | 应用题作答前/中可打开剖析（图示+分步+变式入口），`ROUND16_H5` |
| **H6** 学伴人格 | 墨墨（+数学吉祥物若有）≥**40** 条阶段台词（新字/连对/复习/疲劳等），非仅占位 |
| **H7** 家长可解释周报 | 家长中心展示「本周弱项一句话 + 建议练习 ≤3」，可本地生成 |
| **H8** 往轮不退化 | `check:round15` **8/8** |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r16-arch-contracts-9f67` | R16 架构：认步舞台契约、数学 LearnDemo 协议、周报数据契约 |
| 2 | fable | `cursor/r16-hongen-gap-audit-9f67` | 双 App 洪恩差距总表（体验口径，非仅工程） |
| 3 | fable | `cursor/r16-acceptance-spec-9f67` | ROUND16-ACCEPTANCE + check-round16 v1.0 + log 模板 |
| 4 | opus-fast | `cursor/r16-literacy-intro-fallback-9f67` | 无字源认步默认动画（H2） |
| 5 | opus-fast | `cursor/r16-play-rich-500-9f67` | 富 Play 扩到 ≥500（优先 u21–u40） |
| 6 | opus-fast | `cursor/r16-math-learn-demo-9f67` | 技能学演示 ×≥12（H4） |
| 7 | opus-fast | `cursor/r16-math-wp-analysis-9f67` | 应用题剖析壳（H5） |
| 8 | opus-fast | `cursor/r16-mascot-parent-week-9f67` | 学伴人格剧本（H6）+ 家长周报（H7） |
| 9 | gpt-sol | `cursor/r16-smoke-tests-9f67` | smoke/单测覆盖 H2–H7 关键路径 |
| 10 | gpt-sol | `cursor/r16-regression-gate-9f67` | 往轮探针 + evidence 回填 + 集成说明 |

## 规则

- 分支 `cursor/<task>-9f67`；worktree 开发；合入本编排分支再视情况进 openmoji-integration
- 不复制洪恩 IP/美术；OpenMoji + GSAP/程序化
- reduced-motion / 可跳过必须保留
- 证据：`.agent_workspace/evidence/r16/`
- **缺了立马补**（同模型同职责重开）

## 成功体验（比探针严）

1. 点开无字源冷门字：认步仍有动画/互动讲解，不是一行释义  
2. 前 500 高频字玩关「能讲出和字义的关系」  
3. 数学任一已覆盖技能：能先看 20 秒演示再刷题  
4. 应用题卡壳时剖析页能看懂「为什么这样列式」  
5. 家长打开周报：不用看懂图表也能知道「这周练什么」
