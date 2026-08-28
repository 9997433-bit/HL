# Round 16 验收标准 · 体验密度反超

> 版本：v1.0 · 简报：`ROUND16-BRIEF.md` · 探针：`npm run check:round16`

## G 总则

- **G1** 不复制洪恩 IP；OpenMoji + 程序化动画。
- **G2** 无字源字认步不得空白（H2）。
- **G3** 富脚本计数：`templateFallback≠true`，按 char 去重。
- **G4** 数学演示与剖析均可跳过；reduced-motion 可完成。
- **G5** `check:round15` 必须保持 8/8（H8）。
- **G6** 真机 ASR/OCR/商店不作为本轮硬绿（可记 BLOCKED）。

## H1–H8

见 ROUND16-BRIEF 硬门槛表。回填时粘贴探针原话到 `acceptance-log-round16.md`。

## 红线

- 禁止用注释骗过 `ROUND16_H*` 探针（标记须在可执行代码）。
- 禁止把 templateFallback 条目算进 H3。
- 禁止为过 H4 只写空壳组件无「实物/图形/算式」三态。
