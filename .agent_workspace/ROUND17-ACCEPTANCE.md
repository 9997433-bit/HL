# Round 17 验收标准 · 覆盖加深 + 精品讲解

> 版本：v1.0 · 简报：`ROUND17-BRIEF.md` · 探针：`npm run check:round17`

## G 总则

- **G1** 不复制洪恩 IP；OpenMoji + 程序化动画。
- **G2** 富 Play 计数：`templateFallback≠true`，按 char 去重；narration 去重 ≥ 80%。
- **G3** 学演示延续 R16 三态 + 可跳过；只认可执行标记文件。
- **G4** 精品剖析必须可跳过；reduced-motion 可完成。
- **G5** `check:round16` 必须保持 8/8（H8）。
- **G6** 真机外网密钥不作硬绿；无设备须诚实 BLOCKED + 复现命令。

## H1–H8

见 ROUND17-BRIEF 硬门槛表。回填时粘贴探针原话到 `acceptance-log-round17.md`。

## 红线

- 禁止用注释骗过 `ROUND17_H*` / 复用的 `ROUND16_H4` 探针。
- 禁止把模板 Play 算进 H2。
- 禁止为凑 H4 只写空 `explain()` 返回空数组。
- 禁止伪造走查截图路径。
