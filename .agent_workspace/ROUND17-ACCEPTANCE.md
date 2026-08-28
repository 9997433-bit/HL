# Round 17 验收标准 · 覆盖加深 + 精品讲解

> 版本：v1.1 · 简报：`ROUND17-BRIEF.md` · 探针：`npm run check:round17`

## G 总则

- **G1** 不复制洪恩 IP；OpenMoji + 程序化动画。
- **G2** 富 Play 计数：`templateFallback≠true`，按 char 去重；narration 去重 ≥ 80%。
- **G3** 学演示延续 R16 三态 + 可跳过；只认可执行标记文件。
- **G4** 精品剖析必须可跳过；reduced-motion 可完成。
- **G5** `check:round16` 必须保持 8/8（H8）。
- **G6** 真机外网密钥不作硬绿；无设备须诚实 BLOCKED + 复现命令。

## H1–H8

见 ROUND17-BRIEF 硬门槛表。回填时粘贴探针原话到 `acceptance-log-round17.md`。

v1.1 收紧口径（对照 v1.0）：

- **H4** 只认剥注释后带可执行 `ROUND17_H4` 的文件；条数按去重母题 id
  （`masterId`/`problemId`，兜底 `id`）计，且要求去重中文讲解句 ≥60
  （约 ≥3 句/题）+ 分步 + 可跳过。标记出现次数、`explain:`/`steps:[`
  撞词一律不计入条数。
- **H6** 截图/录屏必须真实落盘：walkthrough.md 里引用的
  `evidence/r17/*.png|jpg|webp|gif|mp4|webm` 至少 4 个存在于
  `.agent_workspace/` 下且每个 ≥200 字节；认步/学演示/剖析/周报
  四类场景词都要出现。只在 doc 里列路径不落盘不算。
- **H7** 必须是 r17 自己的台账：`evidence/r17/android-sim-report.md`
  （可引用重跑的 report.json）或 `evidence/r17/device-blocked.md`
  （BLOCKED + 复现命令）。仅继承 r13 旧 report 不算。
- **H2/H5** 标记判定统一为「剥注释后扫描目录」；H5 场景词去掉裸
  `stage`，须命中接线点（CharDetail/QuizShell/recentWrong 等）+
  学伴词证（mascot/学伴/台词）。

## 红线

- 禁止用注释骗过 `ROUND17_H*` / 复用的 `ROUND16_H4` 探针（探针剥注释后判标）。
- 禁止把模板 Play 算进 H2。
- 禁止为凑 H4 只写空 `explain()` 返回空数组（v1.1 以去重中文讲解句 ≥60 堵死）。
- 禁止伪造走查截图路径（v1.1 要求文件真实落盘且 ≥200B）。
- 禁止用 r13 旧 android 报告顶替 r17 台账（v1.1 只认 `evidence/r17/` 下的台账）。
