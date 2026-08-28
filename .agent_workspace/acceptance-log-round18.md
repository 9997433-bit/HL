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
| `npm run check:round18` | 探针合入后启动实测见下方回填区 | r18-acceptance-spec 分支本地跑 |

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
