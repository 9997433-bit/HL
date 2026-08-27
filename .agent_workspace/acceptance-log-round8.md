Model slug: gpt-5.6-sol-xhigh-fast
# Round 8 验收记录

> 状态：**5/8 已绿，H1/H3/H4 待合入**（2026-08-27）
> 集成线：`cursor/openmoji-integration-9f67`
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`

## 0. 门禁总览

| # | 门禁 | 集成实测 |
|---|---|---|
| G2 | `check:round7` | 8/8 PASS |
| G3 | `check:round6` | 7/7 PASS |
| G4 | `check:round8` | **5/8**（H2/H5/H6/H7/H8） |
| G6 | build + android | zip 见 §3.1 · android 26/26 |
| G7 | Lighthouse | 识字 98/100/100 · 数学 99/100/100 |

## 1. `check:round8` 集成明细

```
  ✓ H2 单元剧情 99 条（u59–u99 手写全覆盖）+ 儿歌 7 首（路由 /songs/:id?）
  ✓ H5 跟读 v2（音素/声调或学伴对话）与 smoke 已接线
  ✓ H6 Lighthouse 识字 98/100/100 / 数学 99/100/100（P ≥ 95，A/BP ≥ 90）+ 证据包 2 份 JSON
  ✓ H7 GLOBAL-SUMMARY-REPORT Round 8 终验 + evidence/r8 证据索引
  ✓ H8 Round 7 门禁 8/8 无退化
  ✗ H1 字源动画 525/800 字
  ✗ H3 技能图谱未闭环
  ✗ H4 OCR 精度脚本缺失
```

## 2. Lighthouse（H6）

| App | P / A / BP | 判定 |
|---|---|---|
| 识字 | 98 / 100 / 100 | PASS |
| 数学 | 99 / 100 / 100 | PASS |

证据：`.agent_workspace/evidence/r8/lighthouse-literacy-app.json`、
`lighthouse-math-app.json`、`acceptance-output.txt`

## 3. 终验回归（r8-global-report @ cdae355，集成态更新）

| 命令 | 结果 |
|---|---|
| `check:round6` | 7/7 PASS |
| `check:round7` | 8/8 PASS |
| `check:round8` | 5/8（H1/H3/H4 待合入） |
| `build:all` | PASS |
| `sync:android` + `check:android` | 26/26 PASS |
| `npm test` | 待 R8 全合入后复跑（基线曾报学伴 43px / 数形演示断言） |

### 3.1 Web zip（@ cdae355 实测）

| 包 | 字节 | SHA256 |
|---|---:|---|
| `hongen-literacy-app.zip` | 6,228,970 | `089de11f5fbd71f5650672ca920aff784bbe3e3fdc6579e901abbe11d15ec2e9` |
| `hongen-math-app.zip` | 455,047 | `a42124e8976f0195e14ca7157de6d6256d3c069b084fcd9e9297486b810a53a6` |

## 4. 待合入

| 项 | 分支 |
|---|---|
| H1 | r8-literacy-etymology |
| H3 | r8-math-skillgraph |
| H4 | r8-literacy-ocr-quality |

## 5. 结论

`Round 8 深度门禁进行中（5/8）；剧情/儿歌/跟读v2/Perf/全局报告已闭合。`
