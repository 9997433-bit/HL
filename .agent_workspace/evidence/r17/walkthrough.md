# Round 17 主路径走查证据包

> 日期：2026-08-28 · 预览：识字 `http://127.0.0.1:4173/` · 数学 `http://127.0.0.1:4174/`  
> 路由为 **hash history**（`#/learn/...`）；先前人工走查误用 path URL 导致白屏。

## 场景与截图

| 场景 | 结果 | 证据 |
|---|---|---|
| **认步**（无字源「牙」· IntroFallback） | ✅ 认一认已挂回退舞台 | `evidence/r17/walkthrough/01-intro-fallback.png` |
| 玩步（同字） | ✅ 玩舞台可进 | `evidence/r17/walkthrough/02-char-play.png` |
| **学演示**（演示中心 27 技能） | ✅ 实物→图形→算式入口可见 | `evidence/r17/walkthrough/03-learn-demo.png` |
| **剖析**（生活行星应用题） | ✅ 剖析面板 + 老师讲法 | `evidence/r17/walkthrough/04-wp-analysis.png` |
| **周报**（家长中心本周一句话） | ✅ 弱项判定 + 建议练习 | `evidence/r17/walkthrough/05-weekly-report.png` |

## 说明

- 截图由编排机无头 Chrome（puppeteer-core）实拍，单张均 >200B。
- 家长中心需算术门闩；脚本自动作答后进入周报卡。
- UI 走查代理曾因未使用 hash 路由记为阻塞；本包以可复核截图为准。

## 补充实拍（走查机 · hash 路由）

| 场景 | 文件 |
|---|---|
| 认步·部首 | `evidence/r17/walkthrough/r17-literacy-intro-fallback-radical.png` |
| 认步·组词 | `evidence/r17/walkthrough/r17-literacy-intro-fallback-word.png` |
| 学演示·弹层 | `evidence/r17/walkthrough/r17-math-learn-demo-overlay.png` |
| 学演示·算式 | `evidence/r17/walkthrough/r17-math-learn-demo-equation.png` |
| 学演示·降动效 | `evidence/r17/walkthrough/r17-math-learn-demo-reduced-motion.png` |
| 剖析 | `evidence/r17/walkthrough/r17-math-wp-analysis.png` |
| 周报·识字 | `evidence/r17/walkthrough/r17-literacy-parent-weekly.png` |
| 周报·数学 | `evidence/r17/walkthrough/r17-math-parent-weekly.png` |

