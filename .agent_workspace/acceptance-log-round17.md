# Round 17 验收回填日志

> 编排启动基线：功能未合入时 `check:round17` 预期红  
> 目标：H1–H8 全绿；`check:round16` 保持 8/8

## 启动基线

| 门禁 | 实测 | 证据 |
|---|---|---|
| `npm run check:round17`（v1.0，编排 VM） | **2/8**（H7 继承 r13 报告 + H8） | `evidence/r17/baseline-check.txt` |
| `npm run check:round17`（v1.1，干净 VM） | **0/8**（H7 改认 r17 台账；H8 干净 VM 无双 APK 连锁红，编排 VM 应绿 → 1/8） | `evidence/r17/baseline-check-v1.1.txt` |
| `npm run check:round16` | 编排 VM 8/8；干净 VM 7/8（r13 H6 需先 `npm run android:sim` 重建双 APK） | `evidence/r17/baseline-check.txt` |

### 启动基线探针原话（v1.0 · 编排 VM）

```
Round 17 check (ROUND17-v1.0): 2/8

✓ H7 真机/模拟闭环或诚实 BLOCKED 台账就位
✓ H8 check:round16 8/8
✗ H1 缺少 round17-hongen-gap-audit.md 或内容过薄
✗ H2 富 Play 不足：rich=640(需≥900)，narration去重=640(需≥720)，标记=false
✗ H3 学演示不足（标记=true，三态=true，可跳过=true，计数=21）
✗ H4 精品剖析不足（标记=false，计数=0）
✗ H5 缺学伴关键接线（ROUND17_H5）
✗ H6 走查证据不足（doc=0，引用=0，落盘=0）
```

### v1.1 复跑原话（干净 VM，2026-08-28）

```
Round 17 check (ROUND17-v1.1): 0/8

✗ H1 缺少 round17-hongen-gap-audit.md 或内容过薄
✗ H2 富 Play 不足：rich=640(需≥900)，narration去重=640(需≥720)，可执行标记=false
✗ H3 学演示不足（标记=true，三态=true，可跳过=true，计数=21）
✗ H4 精品剖析不足（可执行标记=false，母题=0(需≥20)，中文讲解句=0(需≥60)，分步=false，可跳过=true）
✗ H5 缺学伴关键接线（需可执行 ROUND17_H5 + 接线点 + 学伴词证）
✗ H6 走查证据不足（doc=0，引用=0，落盘=0(需≥4)，场景=0(需4)）
✗ H7 缺 r17 台账：需 evidence/r17/android-sim-report.md（可引用重跑的 report.json）或 device-blocked.md（BLOCKED+复现命令）；仅继承 r13 旧报告不算
✗ H8 check:round16 7/8（需 8/8；干净环境先 npm run android:sim 重建双 APK）
```

> v1.0 → v1.1 基线差异说明：H7 由绿转红是**探针收紧**（不再继承 r13 旧报告，
> 须由 r17-regression-gate 产出本轮台账）；H8 红是**环境因素**（干净 VM 无双
> APK，r13→r15→r16 连锁），代码未退化，编排 VM 上仍为 8/8。

| 探针 | 状态 | Owner |
|---|---|---|
| H1 差距续表 | ⬜ | r17-hongen-gap-audit |
| H2 富 Play ≥900 | ⬜ | r17-play-rich-900 |
| H3 学演示 ≥27 | ⬜ | r17-math-learn-demo-plus |
| H4 精品剖析 ≥20 | ⬜ | r17-wp-explain-hand |
| H5 学伴关键接线 | ⬜ | r17-mascot-wire |
| H6 走查证据包 | ⬜ | r17-walkthrough-bundle |
| H7 真机/模拟闭环 | ⬜ | r17-regression-gate |
| H8 往轮 round16 | ⬜ | r17-regression-gate |

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-28 | v1.0 编排启动，十路发射 |
| 2026-08-28 | v1.1 堵误绿：H4 标记刷次数/撞词不计入条数，改认可执行标记文件内去重母题 id + 去重中文讲解句 ≥60（空壳不算）；H6 截图必须真实落盘 ≥4 个（≥200B）+ 四类场景词齐，只列路径不算；H7 只认 r17 台账，r13 旧报告不再顶数；H2/H5 剥注释扫目录判标。负例（假路径/刷标记）自测红、正例（真文件/真内容）自测绿。 |

## 十路子代理

| # | 模型 | 分支 |
|---|---|---|
| 1 | fable | r17-arch-contracts |
| 2 | fable | r17-hongen-gap-audit |
| 3 | fable | r17-acceptance-spec |
| 4 | opus-fast | r17-play-rich-900 |
| 5 | opus-fast | r17-math-learn-demo-plus |
| 6 | opus-fast | r17-wp-explain-hand |
| 7 | opus-fast | r17-mascot-wire |
| 8 | opus-fast | r17-walkthrough-bundle |
| 9 | gpt-sol | r17-smoke-tests |
| 10 | gpt-sol | r17-regression-gate |
| 2026-08-28 | 走查截图实拍入库；**check:round17 v1.1 → 8/8** |
