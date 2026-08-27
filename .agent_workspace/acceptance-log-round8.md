Model slug: gpt-5.6-sol-xhigh-fast
# Round 8 验收记录

> 状态：**7/8 已绿，H3 待合入**（2026-08-27）
> 集成线：`cursor/openmoji-integration-9f67`
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`

## 0. 门禁总览

| # | 门禁 | 集成实测 |
|---|---|---|
| G2 | `check:round7` | 8/8 PASS |
| G3 | `check:round6` | 7/7 PASS |
| G4 | `check:round8` | **7/8**（缺 H3） |
| G6 | build + android | zip 见 §3.1 · android 26/26 |
| G7 | Lighthouse | 识字 98/100/100 · 数学 99/100/100 |

## 1. `check:round8` 集成明细

```
  ✓ H1 字源动画 808 字
  ✓ H2 单元剧情 99 条 + 儿歌 7 首
  ✓ H4 OCR 精度基准脚本与 CharDetailView 形近测验均已接线
  ✓ H5 跟读 v2 与 smoke 已接线
  ✓ H6 Lighthouse 98/100/100 · 99/100/100 + 证据包
  ✓ H7 GLOBAL-SUMMARY-REPORT Round 8
  ✓ H8 Round 7 8/8 无退化
  ✗ H3 技能图谱未闭环
```

## 2. Lighthouse（H6）

| App | P / A / BP | 判定 |
|---|---|---|
| 识字 | 98 / 100 / 100 | PASS |
| 数学 | 99 / 100 / 100 | PASS |

## 2.3 H4 拍照识字精度

见 `.agent_workspace/acceptance-log-round8-h4.md`：五张固定基准图总召回 **35/35（100%）**；
复跑 `npm --prefix apps/literacy-app run test:ocr:accuracy`。

## 3. 终验回归

| 命令 | 结果 |
|---|---|
| `check:round6` | 7/7 PASS |
| `check:round7` | 8/8 PASS |
| `check:round8` | 7/8（H3 待合入） |
| `build:all` | PASS |
| `check:android` | 26/26 PASS |

### 3.1 Web zip

| 包 | 字节 | SHA256 |
|---|---:|---|
| `hongen-literacy-app.zip` | 6,228,970 | `089de11f5fbd71f5650672ca920aff784bbe3e3fdc6579e901abbe11d15ec2e9` |
| `hongen-math-app.zip` | 455,047 | `a42124e8976f0195e14ca7157de6d6256d3c069b084fcd9e9297486b810a53a6` |

## 4. 待合入

| 项 | 分支 |
|---|---|
| H3 | r8-math-skillgraph |

## 5. 结论

`Round 8 深度门禁进行中（7/8）；仅技能图谱待闭合。`
