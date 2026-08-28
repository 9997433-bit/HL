# Round 16 验收标准 · 体验密度反超

> 版本：v1.1 · 简报：`ROUND16-BRIEF.md` · 探针：`npm run check:round16`

## G 总则

- **G1** 不复制洪恩 IP；OpenMoji + 程序化动画。
- **G2** 无字源字认步不得空白（H2）。
- **G3** 富脚本计数：`templateFallback≠true`，按 char 去重，narration 去重 ≥400。
- **G4** 数学演示与剖析均可跳过；reduced-motion 可完成。
- **G5** `check:round15` 必须保持 8/8（H8）。干净环境需先 `npm run android:sim` 重建双 APK，否则 round13 H6 连锁红。
- **G6** 真机 ASR/OCR/商店不作为本轮硬绿（可记 BLOCKED）。

## H1–H8

见 ROUND16-BRIEF 硬门槛表。回填时粘贴探针原话到 `acceptance-log-round16.md`。

v1.1 探针口径（比 v1.0 严，先读再写代码）：

| 探针 | v1.1 口径 |
|---|---|
| H2 | `ROUND16_H2` 剥注释后仍在 literacy src 内；标记文件 + CharDetailView 合并后须见 intro 门控与回退舞台词证 |
| H3 | 只认运行时 `countRichPlays()≥500` 且 `listRichPlays()` narration 去重 ≥400；种子 txt 行数不算 |
| H4 | 三态（实物/图形/算式）、可跳过、技能 id 去重计数 ≥12，全部只从「剥注释后含 `ROUND16_H4` 的文件」里取；`evidence/r16/learn-demo-registry.md` 仅作参考展示 |
| H5 | `ROUND16_H5` 可执行 + 剖析 + 分步 + 变式三词证同时在标记文件内 |
| H6 | `ROUND16_H6` 可执行；台词按去重中文串计数 ≥40（同句复制不算）；新字/连对/复习/疲劳 四类场景词至少命中 3 类 |
| H7 | `ROUND16_H7` 可执行 + 弱项 + 建议 + 周报三词证同时在标记文件内 |

## 红线

- 禁止用注释骗过 `ROUND16_H*` 探针（标记须在可执行代码——v1.1 已剥注释后再判）。
- 禁止把 templateFallback 条目算进 H3；禁止用种子字表 txt 顶富 Play 计数。
- 禁止为过 H4 只写空壳组件无「实物/图形/算式」三态；空目录 / evidence 登记表不再计入 hit。
- 禁止 H6 用同一句台词复制凑数（探针按去重串计）。

## v1.0 → v1.1 修订说明（堵误绿）

1. **H4 空目录误绿**：v1.0 `demoFiles.some(exists)` 只要目录存在即 hit=true，且 markdown 登记表行数可顶替代码计数。v1.1 全部信号只认带可执行标记的源码文件。
2. **H6/H7 注释骗标**：v1.0 直接对原文 `test(/ROUND16_H6/)`，注释里写标记即可过。v1.1 先剥 HTML/块/行注释再判，H5/H2 同步收紧。
3. **H7 无标记 OR 分支**：v1.0 允许「弱项+周报词证」绕过标记；v1.1 必须标记 + 词证同时成立。
4. **H3 种子 txt 抄近路**：v1.0 seed 行数 ≥500 即计入；v1.1 只认运行时口径并加 narration 去重 ≥400（沿用 R15 v1.1 精神，80% 比例）。
5. 防误绿自测已做：注释标记→红、复制台词 45 遍→计 1 条红、真实可执行标记 + 实内容→绿（见 acceptance-log 基线段）。
