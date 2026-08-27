Model slug: gpt-5.6-sol-xhigh-fast
# Round 8 验收记录

> 状态：**H7 报告与证据索引已交付；基线 smoke 有未闭合项**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ `a8b21b3`（Round 7 闭合：
> `check:round7` 8/8 · `check:round6` 7/7）
> 报告分支：`cursor/r8-global-report-9f67`
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`

## 0. Round 8 起点基线

`a8b21b3` 新增 H1–H8 探针时，功能分支尚未合入，因此基线定义为 **1/8**：
仅 H8（Round 7 8/8 不退化）通过。该红灯是并发施工起点，不是放宽终验标准。

| 项 | `a8b21b3` 起点状态 | 收口分支 |
|---|---|---|
| H1 字源 800 | 525/800 | `r8-literacy-etymology` |
| H2 剧情/儿歌 | 58/99，u59–u99 与儿歌专题未接线 | `r8-literacy-stories` |
| H3 技能图谱 | 路由、视图、专用图谱数据未接线 | `r8-math-skillgraph` |
| H4 OCR 质量 | OCR v1 已在，固定精度基准脚本未接线 | `r8-literacy-ocr-quality` |
| H5 跟读 v2 | 跟读 v1 已在，v2 能力与 smoke 未接线 | `r8-literacy-followread` |
| H6 Perf 95 | 沿用 R7 性能结果，数学仍低于 R8 阈值；R8 原始证据目录未建 | `r8-perf-lighthouse` |
| H7 全局报告 | 仍是 Round 7 快照，尚无 R8 证据索引 | `r8-global-report` |
| H8 R7 回归 | 8/8 PASS | 全部分支共同维护 |

## 1. H7 报告分支交付

- `.agent_workspace/GLOBAL-SUMMARY-REPORT.md` 已刷新到 Round 8，保留 31/31 模块行；
  24 项达到当前口径，7 项明确标记对应 R8 功能子代理。
- `.agent_workspace/evidence/r8/README.md` 固定 Lighthouse 双 App 与 axe 三个扫描面的
  原始 JSON 路径；路径本身不冒充性能通过。
- `check:round7` 的报告状态解析兼容 R8 在途标记，避免文档进入新轮次后反向破坏
  Round 7 的 H7。
- 本分支 `check:round8` 实测 **2/8**（H7 + H8）；其余六项必须等功能分支真实合入，
  最终仍要求 8/8。

### 1.1 H7 / H8 探针输出

```text
  ✓ H7 GLOBAL-SUMMARY-REPORT Round 8 终验 + 证据包索引
  ✓ H8 Round 7 门禁 8/8 无退化

  ✗ H1 字源动画 525/800 字
  ✗ H2 单元剧情/儿歌：STORIES=58/99，缺 u59–u99，儿歌=0/3，路由缺失
  ✗ H3 技能图谱：路由、视图、数据均缺失
  ✗ H4 OCR/测验：精度脚本缺失，CharDetailView 形近池已在
  ✗ H5 跟读 v2：v2 能力与 smoke 均缺失
  ✗ H6 Perf：双 App 分数未回填，证据索引已在

Round 8 深度门禁：2/8 项通过，6 项失败。退出码 1（功能分支合入前的预期红灯）。
```

## 2. R8 全合入后的性能回填区

### 2.1 Lighthouse Perf ≥ 95

| App | P | A | BP | 判定 |
|---|---:|---:|---:|---|
| 识字 | `[待回填]` | `[待回填]` | `[待回填]` | |
| 数学 | `[待回填]` | `[待回填]` | `[待回填]` | |

### 2.2 zip 体积

| 包 | 集成实测 |
|---|---|
| literacy-app.zip | `[待回填]` |
| math-app.zip | `[待回填]` |

## 3. 本分支终验回归

> 实测提交：`6c5e439`。依赖由仓库锁文件执行 `npm ci` 后运行。

| 命令 | 结果 | 摘要 |
|---|---|---|
| `npm test` | **FAIL（退出码 1）** | feedback 全绿；识字内容 61/61、构建与 162/162 路由通过，但学伴按钮命中区实测 43px，小于 smoke 的 44px 门槛；因 `&&` 短路未进入数学套件 |
| `npm run test:math`（补跑诊断） | **FAIL（退出码 1）** | 内容探针与构建全绿，18/18 路由通过；31 个交互中数形演示首段状态为 `visual`，smoke 期望 `concrete` |
| `npm run check:round6` | **7/7 PASS** | 1820 字、132 本绘本、24 首古诗、跟读、5 款游戏、214 母题均达线 |
| `npm run check:round7` | **8/8 PASS** | H7 识别 31/31 模块：24 项当前口径达标、7 项 R8 在途 |
| `npm run check:round8` | **2/8（预期红）** | 本分支 H7、H8 通过；H1–H6 等待功能分支 |
| `npm run build:all` | **PASS** | 双 App 构建、zip 创建及 CRC 校验完成 |
| `npm run sync:android` | **PASS** | 双 App `cap copy` + `cap sync` 完成 |
| `npm run check:android` | **26/26 PASS** | 配置、图标、manifest、Gradle 与权限门禁全绿 |

### 3.1 Web zip

| 包 | 字节 | SHA256 |
|---|---:|---|
| `hongen-literacy-app.zip` | 6,228,970 | `089de11f5fbd71f5650672ca920aff784bbe3e3fdc6579e901abbe11d15ec2e9` |
| `hongen-math-app.zip` | 455,047 | `a42124e8976f0195e14ca7157de6d6256d3c069b084fcd9e9297486b810a53a6` |

### 3.2 复跑判定

`npm test` 共执行两次。第一次在高并发浏览器负载下除命中区外还出现首字徽章时序失败；
降低并发后第二次徽章通过，命中区仍稳定为 43px，因此只把命中区列为复现项。
数学套件补跑发现独立的数形演示初始阶段断言失败。两项均在给定基线源码中，报告分支只改
Markdown 与 `check-round7.mjs` 的报告状态解析，没有修改对应产品组件或 smoke 断言。

`acceptance-log-round6.md` 已复核：7/7、全链回归、zip、Android 26/26 与未闭合项均有
记录，无缺项需要改写历史日志。

## 4. 结论

**H7 报告与证据索引 PASS；Round 7 8/8、Round 6 7/7、构建与 Android 26/26
无退化。** Round 8 功能门禁在全分支合入前按设计为 2/8；本基线的两个 smoke 断言
仍使 `npm test` 退出 1，故本记录不声明全链终验通过。
