Model slug: claude-fable-5-thinking-xhigh
# Round 8 验收记录

> 状态：**v1.1 探针已合入，Perf 已回填，其余功能分支交付中**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ `a8b21b3`（Round 7 闭合：check:round7 8/8 · check:round6 7/7）
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`（探针细则 §2、smoke 建议 §3、回填格式 §4.2/§7）
> 验收规范分支：`cursor/r8-acceptance-spec-9f67`

## 0. 基线门禁总览

| # | 门禁 | 命令 | 基线实测 | 备注 |
|---|---|---|---|---|
| G1 | 全量单测 | `npm test` | `[待编排器回填]` | Round 7 闭合时全绿 |
| G2 | R7 不退化 | `npm run check:round7` | **8/8 PASS** | H8 子进程实测 |
| G3 | R6 不退化 | `npm run check:round6` | `[待编排器回填]` | Round 7 闭合时 7/7 |
| G4 | Round 8 硬门槛 | `npm run check:round8` | **2/8**（H6+H8 已绿） | 明细见 §1 |
| G5 | Round 3 全链 | `npm run test:round3` | `[待编排器回填]` | 含离线 + acceptance |
| G6 | 出包 + Android | `build:all` + `sync:android` + `check:android` | `[基线体积待回填]` | check:android 26/26 |
| G7 | Lighthouse | `npm run test:acceptance` | **识字 98/100/100 · 数学 99/100/100** | R8 P ≥ 95 已达标，见 §2.1 |

## 1. `check:round8` 集成明细（v1.1 强化探针口径）

```
  ✓ H6 Lighthouse Perf 识字 98 / 数学 99（均 ≥ 95）+ 证据包
  ✓ H8 Round 7 门禁 8/8 无退化

  ✗ H1 字源动画 525/800 字 —— 由 r8-literacy-etymology 交付
  ✗ H2 单元剧情/儿歌未闭环 —— 由 r8-literacy-stories 交付
  ✗ H3 技能图谱未闭环 —— 由 r8-math-skillgraph 交付
  ✗ H4 OCR/测验未闭环：精度脚本=缺失 —— 由 r8-literacy-ocr-quality 交付
  ✗ H5 跟读 v2 未闭环 —— 由 r8-literacy-followread 交付
  ✗ H7 全局报告未终验 —— 由 r8-global-report 交付

Round 8 深度门禁：2/8 项通过，6 项失败。
```

| 项 | 集成实测 | 责任分支 |
|---|---|---|
| H1 | FAIL：525/800 | r8-literacy-etymology |
| H2 | FAIL | r8-literacy-stories |
| H3 | FAIL | r8-math-skillgraph |
| H4 | FAIL：精度脚本缺失 | r8-literacy-ocr-quality |
| H5 | FAIL | r8-literacy-followread |
| H6 | **PASS**：98/100/100 · 99/100/100 + evidence/r8 JSON 2/2 | r8-perf-lighthouse ✅ |
| H7 | FAIL：Round 8 报告 | r8-global-report |
| H8 | **PASS** | — |

## 2. 集成回填模板

> 集成提交：`da2ed2c`（Perf）+ `[待 R8 全闭合 SHA]`
> 回填日期：`2026-08-27`

### 2.1 Lighthouse Perf ≥ 95（**H6 探针读此表**）

| App | P / A / BP（单格斜杠，数字打头） | 判定 |
|---|---|---|
| 识字 | 98 / 100 / 100 | PASS |
| 数学 | 99 / 100 / 100 | PASS |

证据归档（H6 探针递归数 `.json` ≥ 2）：

| 文件 | 路径 |
|---|---|
| 识字 LH 原始报告 | `.agent_workspace/evidence/r8/lighthouse-literacy-app.json` |
| 数学 LH 原始报告 | `.agent_workspace/evidence/r8/lighthouse-math-app.json` |
| acceptance 输出 | `.agent_workspace/evidence/r8/acceptance-output.txt` |

### 2.2 OCR 精度基准（H4 配套量化值）

| 指标 | 实测 |
|---|---|
| 基准图集规模 | `[待 r8-literacy-ocr-quality 回填]` |
| 整体正确率 | `[待回填]` |

### 2.3 八项实测总览

| 项 | 集成实测 |
|---|---|
| H1 字源 | 525/800 |
| H2 剧情 + 儿歌 | 58/99 · 儿歌 0/3 |
| H3 技能图谱 | 未接线 |
| H4 OCR 精度 | 脚本缺失 |
| H5 跟读 v2 | 未接线 |
| H6 Lighthouse | 见 §2.1 ✅ |
| H7 全局报告 | Round 8 待刷新 |
| H8 R7 不退化 | ✅ 8/8 |

### 2.4 体积

| 指标 | 集成实测 |
|---|---|
| literacy-app.zip | `[待 build:all 回填]` |
| math-app.zip | `[待 build:all 回填]` |

## 3. 未达标处理

| 项 | 责任分支 | 计划 |
|---|---|---|
| H1–H5、H7 | #4–#8、#10 | cherry-pick 合入后复跑 check:round8 |

## 4. 结论

`Round 8 深度门禁进行中（2/8）；Lighthouse 识字 98/100/100 / 数学 99/100/100 已达标。`
