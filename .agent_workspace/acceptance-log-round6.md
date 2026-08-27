Model slug: claude-fable-5
# Round 6 验收记录

> 状态：**探针契约就绪，10 子代理并发交付中**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ `90663c1`（Round 5 12/12 · Round 5B 6/6 · Android 同步）
> 判定标准：`.agent_workspace/ROUND6-ACCEPTANCE.md`（探针细则 §2、smoke 建议 §3、Perf/体积模板 §4.2）
> 验收规范分支：`cursor/r6-acceptance-spec-9f67`

## 0. 基线门禁总览

| # | 门禁 | 命令 | 基线实测 | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测 | `npm test` | **PASS** | 编排器 @ fc6b511 实测 |
| G2 | 往轮不退化 | `npm run check:round5` + `check:round5b` | **12/12 + 6/6** | Round 5/5B 全绿 |
| G3 | Round 6 硬门槛 | `npm run check:round6` | **1/7（有意红灯）** | 明细见 §1 |
| G4 | Round 3 全链 | `npm run test:round3` | **PASS** | 编排器 @ fc6b511 实测 |
| G5 | 出包 | `npm run build:all` | `[基线体积待回填]` | literacy-app.zip / math-app.zip |

## 1. `check:round6` 基线明细（@ 90663c1，强化探针口径）

```
  ✓ H2 verifyBookCoverage 零越界

  ✗ H1 字库 1000/1800 字
  ✗ H2 绘本 30/130 本
  ✗ H3 古诗未接线（要求 ≥ 20 首）
  ✗ H4 跟读评测未闭环：路由=缺失，composable=缺失，识别/录音降级=缺失，smoke=缺失
  ✗ H5 识字小游戏 3/5 款（不含 listen）
  ✗ H6 应用题母题 118/185 个

Round 6 内容门禁：1/7 项通过，6 项失败。 → 退出码 1
```

| 项 | 基线实测 | 待合入能力 | 责任分支 |
| --- | --- | --- | --- |
| H1 | FAIL：1000/1800 字 | 脚本化扩充字库 | r6-literacy-1800chars |
| H2 | FAIL：30/130 本（零越界保持绿） | 绘本扩量 + 覆盖校验 | r6-literacy-books-130 |
| H3 | FAIL：`poems.js` 缺失 | 古诗 20 首（朗读+点字+拼音） | r6-literacy-poems-speech |
| H4 | FAIL：路由/composable/识别+录音降级/smoke 全缺 | 跟读评测 v1（含 `ROUND6_H4_SMOKE`） | r6-literacy-poems-speech |
| H5 | FAIL：3/5 款（存量精确接线正常） | 再增 2 款小游戏 | r6-literacy-minigames |
| H6 | FAIL：118/185 个 | 母题语义模板 × 场景皮肤 | r6-math-problems-185 |

结论：1/7 是功能分支未合并时的**预期红灯**，不表示门禁自身异常；H2.coverage 与 H5 存量接线为基线存量能力，集成后必须保持。

## 2. 集成回填模板

> 回填触发：所有 Round 6 功能分支合入集成分支
> 集成提交：`[待回填 SHA]`
> 回填日期：`[YYYY-MM-DD]`
> 回填人：`[分支/代理]`

### 2.1 门禁总览

| # | 门禁 | 期望 | 集成实测 |
| --- | --- | --- | --- |
| G1 | `npm test` | PASS | `[待回填]` |
| G2 | `npm run check:round5` + `check:round5b` | 12/12 + 6/6 | `[待回填]` |
| G3 | `npm run check:round6` | **7/7** PASS | `[待回填，附全文输出]` |
| G4 | `npm run test:round3` | PASS | `[待回填]` |
| G5 | `npm run build:all` | zip 产出 | `[待回填]` |

### 2.2 六项实测（粘贴 `check:round6` 输出并填计数）

| 项 | 期望 | 集成实测 |
| --- | --- | --- |
| H1 字库 | ≥ 1800 | `[N 字]` |
| H2 绘本 | ≥ 130 且零越界 | `[N 本 / 越界 N]` |
| H3 古诗 | ≥ 20 | `[N 首]` |
| H4 跟读 | 路由+composable+smoke 三重接线 | `[路由 path / pipeline 文件 / smoke 标记]` |
| H5 小游戏 | ≥ 5（不含 listen）全部精确接线 | `[N 款 / 未接线 N]` |
| H6 母题 | ≥ 185 | `[N 个]` |

### 2.3 Perf / 体积

| 指标 | 预算/基线 | 集成实测 | 判定 |
| --- | --- | --- | --- |
| 识字首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| Lighthouse 识字 | P ≥ 90 / A ≥ 90 / BP ≥ 90 | `[P/A/BP]` | `[P/F]` |
| Lighthouse 数学 | P ≥ 90 / A ≥ 90 / BP ≥ 90 | `[P/A/BP]` | `[P/F]` |
| literacy-app.zip | `[基线 MB]` | `[MB]`（Δ `[±MB]`） | 记录 + 解释来源 |
| math-app.zip | `[基线 MB]` | `[MB]`（Δ `[±MB]`） | 记录 + 解释来源 |
| 识字 smoke 总耗时 | 基线 `[待回填]` | `[待回填]`（130 本全量后） | 记录即可 |

### 2.4 手动走查（W1–W6，见标准 §5）

| # | 走查项 | 结果 |
| --- | --- | --- |
| W1 | 古诗三件套 | `[勾选/问题]` |
| W2 | 跟读评测闭环（含拒麦降级） | `[勾选/问题]` |
| W3 | 新小游戏可玩闭环 | `[勾选/问题]` |
| W4 | 绘本扩量抽查 5 本 | `[勾选/问题]` |
| W5 | 数学专题入口 + 地图叙事 | `[勾选/问题]` |
| W6 | 硬性红线抽查 | `[勾选/问题]` |

## 3. 未达标处理（无则写「无」）

| 项 | 现象 | 责任分支 | 计划 |
| --- | --- | --- | --- |
| `[H?]` | `[实测输出]` | `[分支]` | `[修复计划]` |

## 4. 结论（集成回填后填写）

`Round 6 内容门禁 [PASS/FAIL]（[N]/7）；Round 5/5B 与 Round 3 回归 [无/有] 退化；zip 体积 识字 [N] MB / 数学 [N] MB（Δ [±]）。`
