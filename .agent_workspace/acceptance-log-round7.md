Model slug: claude-fable-5
# Round 7 验收记录

> 状态：**探针契约就绪，功能分支并发交付中**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ `46759f3`（Round 6 闭合：check:round6 7/7 · 古诗导入修复 · 1820 字）
> 判定标准：`.agent_workspace/ROUND7-ACCEPTANCE.md`（探针细则 §2、smoke 建议 §3、Lighthouse/浏览器矩阵模板 §4）
> 验收规范分支：`cursor/r7-acceptance-spec-9f67`

## 0. 基线门禁总览

| # | 门禁 | 命令 | 基线实测 | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测 | `npm test` | `[待编排器回填]` | Round 6 闭合时全绿 |
| G2 | 往轮不退化 | `npm run check:round6` | `[待编排器回填]` | Round 6 闭合时 7/7 |
| G3 | Round 7 硬门槛 | `npm run check:round7` | **0/8（有意红灯）** | 明细见 §1，本分支实测 |
| G4 | Round 3 全链 | `npm run test:round3` | `[待编排器回填]` | 含离线 + acceptance |
| G5 | 出包 + Android | `npm run build:all` + `sync:android` + `check:android` | `[基线体积待回填]` | check:android 26/26 |
| G6 | Lighthouse | `npm run test:acceptance` | `[待回填]` | 双 App P/A/BP ≥ 90 |

## 1. `check:round7` 基线明细（@ 46759f3，强化探针口径）

```
  ✗ H1 拍照识字未闭环：路由=缺失，pipeline=缺失，tesseract 依赖=缺失，识别调用=缺失，拍照/选图降级=缺失，smoke=缺失 —— 由 r7-literacy-ocr 交付
  ✗ H2 形近字库未接线（缺 similar-chars.js、distractors.js）—— 由 r7-literacy-distractors 交付
  ✗ H2 干扰项接线不全：听音识字=纯随机，单字测验=纯随机（须 import @/utils/distractors 并调用 buildOptions/similarDistractors）—— 由 r7-literacy-distractors 交付
  ✗ H3 字源动画 65/200 字
  ✗ H4 年龄档联动 1/5 模块；未接线：NumberSenseView、GeometryView、LogicView、WordProblemsView、SudokuView —— 由 r7-math-ageband 交付
  ✗ H5 逻辑小游戏未闭环：已接线路由=缺失，smoke=缺失 —— 由 r7-math-logic-games 交付
  ✗ H6 第 4 主题未闭环：aurora tokens=0（要求 ≥ 5），识字 THEMES=缺失（3 款，要求 ≥ 4），数学注册=缺失 —— 由 r7-theme-aurora 交付
  ✗ H7 GLOBAL-SUMMARY-REPORT 未终验：未更新到 Round 7；❌ 3 行；⬜ 待实测 73 行 —— 由 r7-global-report 交付

Round 7 终验门禁：0/8 项通过，8 项失败。 → 退出码 1
```

| 项 | 基线实测 | 待合入能力 | 责任分支 |
| --- | --- | --- | --- |
| H1 | FAIL：路由/pipeline/依赖/smoke 全缺 | Tesseract.js 拍照识字（`/ocr` + `useOcr`/`ocr.js` + `public/ocr/`） | r7-literacy-ocr |
| H2.data | FAIL：`similar-chars.js`、`distractors.js` 缺失 | 形近字库 + `similarDistractors`/`buildOptions` | r7-literacy-distractors |
| H2.wiring | FAIL：听音/测验均纯随机 | 两视图接 `@/utils/distractors` | r7-literacy-distractors |
| H3 | FAIL：65/200 字 | 字源 pipeline 批量扩到 200+ | r7-literacy-distractors |
| H4 | FAIL：1/5 模块（仅 Arithmetic 存量） | `ageBand` 全模块联动 | r7-math-ageband |
| H5 | FAIL：无配对/迷宫路由 | `/memory-pairs` + `/maze` + smoke | r7-math-logic-games |
| H6 | FAIL：aurora tokens/THEMES/数学注册全缺 | 第 4 主题 aurora | r7-theme-aurora |
| H7 | FAIL：Round 3 旧骨架（❌ 3 行、⬜ 73 行） | 全局报告终验重写 + 证据索引 | r7-global-report |

结论：0/8 是功能分支未合并时的**预期红灯**，不表示门禁自身异常。探针已逐分支预验证（各功能分支工作区快照上，本探针恰好点绿其负责结果：H1 三重接线 `/ocr`、H2.data 1817 组 + 功能探针、H2.wiring 双视图、H4 6/6、H5 `/memory-pairs`+`/maze`、H6 tokens 32 项 / THEMES 4 款 / 数学已注册），集成后 8/8 可达；H3/H7 交付时点绿。

## 2. 集成回填模板

> 回填触发：所有 Round 7 功能分支合入集成分支
> 集成提交：`[待回填 SHA]`
> 回填日期：`[YYYY-MM-DD]`
> 回填人：`[分支/代理]`

### 2.1 门禁总览

| # | 门禁 | 期望 | 集成实测 |
| --- | --- | --- | --- |
| G1 | `npm test` | PASS | `[待回填]` |
| G2 | `npm run check:round6` | 7/7 | `[待回填]` |
| G3 | `npm run check:round7` | **8/8** PASS | `[待回填，附全文输出]` |
| G4 | `npm run test:round3` | PASS | `[待回填]` |
| G5 | `build:all` + `sync:android` + `check:android` | zip + 26/26 | `[待回填]` |
| G6 | Lighthouse 双 App | P/A/BP ≥ 90 | `[待回填，见 2.3]` |

### 2.2 八项实测（粘贴 `check:round7` 输出并填计数）

| 项 | 期望 | 集成实测 |
| --- | --- | --- |
| H1 拍照识字 | 路由+pipeline+smoke 三重接线 | `[路由 path / pipeline 文件 / smoke 断言]` |
| H2.data 形近字库 | ≥ 100 组 + 功能探针 | `[N 组]` |
| H2.wiring 干扰项 | 听音+测验双接线 | `[勾选]` |
| H3 字源 | ≥ 200 字无重复 | `[N 字]` |
| H4 年龄档 | ≥ 5/6 模块 | `[N/6 模块]` |
| H5 逻辑游戏 | 路由 + smoke | `[路由列表]` |
| H6 aurora | tokens+双 App 注册 | `[tokens N 项 / THEMES N 款]` |
| H7 全局报告 | 零 ❌ 零 ⬜ + 证据索引 | `[勾选]` |

### 2.3 Lighthouse / Perf / 体积（标准 §4.2）

| 指标 | 预算/基线 | 集成实测 | 判定 |
| --- | --- | --- | --- |
| Lighthouse 识字 | P ≥ 90 / A ≥ 90 / BP ≥ 90 | `[P/A/BP]` | `[P/F]` |
| Lighthouse 数学 | P ≥ 90 / A ≥ 90 / BP ≥ 90 | `[P/A/BP]` | `[P/F]` |
| 识字首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| OCR 资产（懒加载块 + public/ocr） | 只在 `/ocr` 加载 | `[KB / 时机]` | `[P/F]` |
| literacy-app.zip | `[基线 MB]` | `[MB]`（Δ `[±MB]`） | 记录 + 解释来源 |
| math-app.zip | `[基线 MB]` | `[MB]`（Δ `[±MB]`） | 记录 + 解释来源 |

### 2.4 浏览器矩阵 C-6（标准 §4.3）

| 检查项 | Chrome | Firefox | Safari/WebKit |
| --- | --- | --- | --- |
| 识字：冷启动 + 学字闭环 | `[P/F]` | `[P/F]` | `[P/F]` |
| 识字：拍照识字（含拒权限降级） | `[P/F]` | `[P/F]` | `[P/F]` |
| 数学：冷启动 + 答题 + 逻辑游戏 | `[P/F]` | `[P/F]` | `[P/F]` |
| 双 App：aurora 渲染 | `[P/F]` | `[P/F]` | `[P/F]` |
| 双 App：断网冷启动 | `[P/F]` | `[P/F]` | `[P/F]` |

### 2.5 手动走查（W1–W7，见标准 §5）

| # | 走查项 | 结果 |
| --- | --- | --- |
| W1 | 拍照识字闭环（含拒权限降级） | `[勾选/问题]` |
| W2 | 形近干扰观感（听音 + 测验各 10 题） | `[勾选/问题]` |
| W3 | 字源动画抽查 5 字（含 reduced-motion） | `[勾选/问题]` |
| W4 | 逻辑配对/迷宫闭环（键盘 + 降级） | `[勾选/问题]` |
| W5 | 年龄档 L1/L3/L5 难度可辨 + 持久化 | `[勾选/问题]` |
| W6 | 四主题对比度 + 焦点环 | `[勾选/问题]` |
| W7 | 硬性红线抽查 | `[勾选/问题]` |

## 3. 未达标处理（无则写「无」）

| 项 | 现象 | 责任分支 | 计划 |
| --- | --- | --- | --- |
| `[H?]` | `[实测输出]` | `[分支]` | `[修复计划]` |

## 4. 结论（集成回填后填写）

`Round 7 终验门禁 [PASS/FAIL]（[N]/8）；Round 6 与 Round 3 回归 [无/有] 退化；Lighthouse 识字 [P/A/BP] / 数学 [P/A/BP]；zip 体积 识字 [N] MB / 数学 [N] MB（Δ [±]）。`
