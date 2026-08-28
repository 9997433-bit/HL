Model slug: gpt-5.6-sol-xhigh-fast
# Round 8 验收记录

> 状态：**终验通过（全链 PASS，2026-08-27）**
> 验证分支：`cursor/r9-global-release-9f67`
> 源码基线：`ec733bb` · 验证提交：`ab2ad8d`
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`

## 0. 门禁总览

| # | 命令 / 门禁 | 集成实测 |
|---|---|---|
| G1 | `npm test` | **PASS**（退出码 0） |
| G2 | `check:round7` | 8/8 PASS |
| G3 | `check:round6` | 7/7 PASS |
| G4 | `check:round8` | **8/8 PASS** |
| G5 | `npm run test:round3` | **PASS**（退出码 0；离线与 acceptance 均通过） |
| G6 | `build:all` → `sync:android` → `check:android` | **PASS**；zip 见 §4；Android 26/26 |
| G7 | Lighthouse | 识字 98/100/100 · 数学 99/100/100 |

## 1. `check:round8` 集成明细

```text
  ✓ H1 字源动画 808 字（要求 ≥ 800，无重复，全汉字）
  ✓ H2 单元剧情 99 条（u59–u99 手写全覆盖）+ 儿歌 7 首（路由 /songs/:id?）
  ✓ H3 技能图谱已接线（/skill-graph + skill-graph.js：34 节点 / 30 边，视图联动进度/年龄档）
  ✓ H4 OCR 精度基准脚本与 CharDetailView 形近测验均已接线
  ✓ H5 跟读 v2 与 smoke 已接线
  ✓ H6 Lighthouse 识字 98/100/100 / 数学 99/100/100 + 证据包 2 份 JSON
  ✓ H7 GLOBAL-SUMMARY-REPORT Round 8 终验 + evidence/r8 证据索引
  ✓ H8 Round 7 8/8 无退化

Round 8 深度门禁：8/8 项通过，0 项失败。
```

## 2. Round 8 实测水位

| 能力 | 实测 | 判定 / 证据 |
|---|---:|---|
| 字源 | 808 字 | PASS；无重复、全汉字 |
| 单元剧情 | 99 条 | PASS；u59–u99 手写覆盖、零兜底 |
| 儿歌 | 7 首 | PASS；数据、路由和视图已接线 |
| 技能图谱 | 34 节点 / 30 边 / 6 泳道 | PASS；联动年龄档和真实进度 |
| OCR 固定基准集 | 35/35（100%） | PASS；5 张图、14/14 断言 |
| 跟读 v2 | 12/12 单测 | PASS；三档与离线学伴 smoke 通过 |

### 2.1 Lighthouse（H6）

| App | P / A / BP | 判定 |
|---|---|---|
| 识字 | 98 / 100 / 100 | PASS |
| 数学 | 99 / 100 / 100 | PASS |

原始报告为 `.agent_workspace/evidence/r8/lighthouse-literacy-app.json` 与
`.agent_workspace/evidence/r8/lighthouse-math-app.json`。本轮 `test:round3` 的
acceptance 脚本因环境未同时检测到 Lighthouse CLI 与 Chrome 而明确 **SKIP**
Lighthouse；未伪造重跑分数，H6 读取上述冻结报告并保持 2/2 JSON。

### 2.2 H4 拍照识字精度

见 `.agent_workspace/acceptance-log-round8-h4.md`：五张固定基准图总召回 **35/35（100%）**；
本轮 `npm test` 与 `test:round3` 均实际复跑，结果 **14/14 PASS**。

## 3. 终验回归

命令按要求顺序执行；额外复跑往轮门禁，所有退出码均为 0：

| 顺序 | 命令 | 结果 |
|---:|---|---|
| 1 | `npm test` | **PASS** |
| 2 | `npm run test:round3` | **PASS** |
| 3 | `npm run build:all` | **PASS** |
| 4 | `npm run sync:android` | **PASS**（双 App `cap copy` + `cap sync`） |
| 5 | `npm run check:android` | **26/26 PASS** |
| 6 | `npm run check:round8` | **8/8 PASS** |
| 补充 | `npm run check:round6` | **7/7 PASS** |
| 补充 | `npm run check:round7` | **8/8 PASS** |

`npm test` 摘要：共用反馈测试全过；FSRS 8/8、跟读 12/12、OCR 取字 7/7、
OCR 精度 14/14、识字内容 71/71；识字 smoke **163 条路由 + 33 项交互**、
数学 smoke **19 条路由 + 32 项交互**，均为 0 问题。数学内容门禁同时确认
214 个应用题母题和 34 节点 / 30 边技能图谱。

`test:round3` 摘要：内部再次执行 `npm test`；随后识字在服务关闭后从
`/#/learn/日` 断网启动（预缓存 2086 项），数学从 `/#/sudoku` 断网启动
（预缓存 59 项）；基础 axe 22/22 页面及 4 主题 × 24 状态均为
critical=0、serious=0、运行失败=0。

## 4. Web zip 冻结

以下哈希来自本轮 `npm run build:all` 产物：

| 包 | 字节 | SHA256 |
|---|---:|---|
| `hongen-literacy-app.zip` | 6,252,719 | `1d2cff37aa69a04ec0a8fef5857973977bcf7e97474a8db4ab4cbda200d2c40b` |
| `hongen-math-app.zip` | 458,315 | `e338a685f6d79b6c842a2cf59ea9ebece763b03d23dbba318c1206a931b33acc` |

## 5. 结论

`Round 8 深度门禁终验通过：31/31 模块全 ✅，H1–H8 为 8/8，全链 0 FAIL。`

Android 本轮完成 Web 资产同步和 26 项静态壳层门禁；未把该结果表述为 APK 编译或
实体设备走查。Android 真机安装、升级、返回键和权限拒绝流程列入 Round 9 发布门。
