# Round 18 验收回填日志

> 编排启动基线：功能未合入时 `check:round18` 预期红  
> 目标：H1–H8 全绿；`check:round17` 保持 8/8  
> 标准细则与红线：`.agent_workspace/ROUND18-ACCEPTANCE.md`（v1.0）  
> 探针：`npm run check:round18`（ROUND18-v1.0，`--json` 机读）

## 启动说明（r18-acceptance-spec 已交付）

- 探针继承 round17 v1.1 全部防误绿手法：`ROUND18_H*` 标记剥注释后判定、
  H6 截图必须真实落盘 ≥4 个且每个 ≥200B、H7 只认 `evidence/r18/` 本轮台账。
- 本轮新增锁：H3 拆包四道锁（可执行标记+动态加载词证 / 全 src 无整包静态
  import / 分片 ≥5 / 分片合计 ≥100KB）；H4 运行时全量跑
  `buildAnalysis(make())` 且题库 ≥200 防删题凑比例；H5 运行时逐条验
  `WORD_PROBLEM_EXPLAINS` 的 steps 全是函数（空壳不计）。
- 接口契约（见 ACCEPTANCE G2–G4）：`countRichPlays`/`listRichPlays`
  允许同步或返回 Promise；`char-play.js` 须仍可被 Node import；
  `WORD_PROBLEMS`/`buildAnalysis`/`WORD_PROBLEM_EXPLAINS` 导出名不许改。
- H8 链条提示：干净环境先 `npm run android:sim` 重建双 APK，否则
  r17→r16→r15→r13 连锁红。

## 启动基线

| 门禁 | 实测 | 证据 |
|---|---|---|
| `npm run check:round17` | **8/8**（openmoji @ 08f13a0） | 编排启动前复测 |
| `npm run check:round18` | **1/8**（编排 @ 19cb7cc，探针合入后首跑；H1 绿=gap-audit 已合） | r18-acceptance-spec 干净 worktree 实测 |

启动首跑探针原话（干净 worktree，功能未合入，预期多数红）：

```text
Round 18 check (ROUND18-v1.0): 1/8

✓ H1 Round18 差距续表就位（双基线 + 本轮归属）
✗ H2 富 Play 不足：rich=940(需≥1200)，narration去重=940(需≥960)，可执行标记=false
✗ H3 拆包未达标（标记=false，loader=false，整包静态import=2处[apps/literacy-app/src/data/char-intro.js, apps/literacy-app/src/data/char-play.js]，分片=0(需≥5)，分片体量=0KB(需≥100KB)）
✗ H4 步数未对齐：158/214 = 73.8%(需≥90%)，题库=214(需≥200)，可执行标记=false
✗ H5 精品剖析不足（可执行标记=false，母题=50(需≥80，空壳不计)，中文讲解句=0(需≥200)）
✗ H6 走查证据不足（doc=0，引用=0，落盘=0(需≥4)，场景=0(需4)）
✗ H7 缺 r18 台账：需 evidence/r18/android-sim-report.md（可引用重跑的 report.json）或 device-blocked.md（BLOCKED+复现命令）；仅继承 r13/r17 旧报告不算
✗ H8 check:round17 7/8（需 8/8；干净环境先 npm run android:sim 重建双 APK）
```

各红项实测值即真实基线（rich=940、步数一致率 73.8%、手写母题 50），
与 BRIEF 差距表逐项对得上——探针口径无虚高。H8 红为链条性：干净
worktree 缺 gitignored 的 android-sim 产物与 OCR/hanzi 生成资产，
重建归 r18-regression-gate。

| 探针 | 状态 | Owner |
|---|---|---|
| H1 差距续表 | ⬜ | r18-hongen-gap-audit |
| H2 富 Play ≥1200 | ⬜ | r18-play-rich-1200 |
| H3 富脚本拆包 | ⬜ | r18-play-codesplit |
| H4 剖析步数对齐 ≥90% | ⬜ | r18-wp-steps-align |
| H5 精品剖析 ≥80 | ⬜ | r18-wp-explain-80 |
| H6 走查证据包 | ⬜ | r18-walkthrough-bundle |
| H7 真机/模拟台账 | ⬜ | r18-regression-gate |
| H8 往轮 round17 | ⬜ | r18-regression-gate |

## 十路子代理

| # | 模型 | 分支 |
|---|---|---|
| 1 | fable | r18-arch-contracts |
| 2 | fable | r18-hongen-gap-audit |
| 3 | fable | r18-acceptance-spec |
| 4 | opus-fast | r18-play-rich-1200 |
| 5 | opus-fast | r18-play-codesplit |
| 6 | opus-fast | r18-wp-steps-align |
| 7 | opus-fast | r18-wp-explain-80 |
| 8 | opus-fast | r18-walkthrough-bundle |
| 9 | gpt-sol | r18-smoke-tests |
| 10 | gpt-sol | r18-regression-gate |

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-28 | v1.0 编排启动，十路发射 |
| 2026-08-28 | r18-acceptance-spec：ACCEPTANCE v1.0 + check-round18.mjs（ROUND18-v1.0）合入，启动实测 1/8 |
