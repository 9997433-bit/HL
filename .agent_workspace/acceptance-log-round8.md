Model slug: claude-fable-5-thinking-xhigh
# Round 8 验收记录

> 状态：**探针契约就绪（v1.1 强化口径），功能分支并发交付中**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ `a8b21b3`（Round 7 闭合：check:round7 8/8 · check:round6 7/7）
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`（探针细则 §2、smoke 建议 §3、回填格式 §4.2/§7）
> 验收规范分支：`cursor/r8-acceptance-spec-9f67`

## 0. 基线门禁总览

| # | 门禁 | 命令 | 基线实测 | 备注 |
|---|---|---|---|---|
| G1 | 全量单测 | `npm test` | `[待编排器回填]` | Round 7 闭合时全绿 |
| G2 | R7 不退化 | `npm run check:round7` | **8/8 PASS** | H8 子进程实测 |
| G3 | R6 不退化 | `npm run check:round6` | `[待编排器回填]` | Round 7 闭合时 7/7 |
| G4 | Round 8 硬门槛 | `npm run check:round8` | **1/8（有意红灯）** | 明细见 §1，本分支实测 |
| G5 | Round 3 全链 | `npm run test:round3` | `[待编排器回填]` | 含离线 + acceptance |
| G6 | 出包 + Android | `build:all` + `sync:android` + `check:android` | `[基线体积待回填]` | check:android 26/26 |
| G7 | Lighthouse | `npm run test:acceptance` | R7 终态：识字 97-100-100 · 数学 94-100-100 | R8 要求 P ≥ 95，见 §2.1 |

## 1. `check:round8` 基线明细（@ a8b21b3，v1.1 强化探针口径）

```
  ✓ H8 Round 7 门禁 8/8 无退化

  ✗ H1 字源动画 525/800 字 —— 由 r8-literacy-etymology 交付
  ✗ H2 单元剧情/儿歌未闭环：STORIES=58/99，u59–u99 兜底/缺失=u59、u60、u61、u62、u63…，儿歌=0/3，儿歌路由=缺失 —— 由 r8-literacy-stories 交付
  ✗ H3 技能图谱未闭环：路由=缺失，视图=缺失，数据=缺失，视图联动=缺失 —— 由 r8-math-skillgraph 交付
  ✗ H4 OCR/测验未闭环：精度脚本=缺失，CharDetailView 形近池=有 —— 由 r8-literacy-ocr-quality 交付
  ✗ H5 跟读 v2 未闭环：v2 能力=缺失，smoke=缺失 —— 由 r8-literacy-followread 交付
  ✗ H6 Perf 未达标：识字 P/A/BP=未回填，数学 P/A/BP=未回填（要求 P ≥ 95、A/BP ≥ 90，按 log §2.1 表格行回填），evidence/r8 JSON=0/2 —— 由 r8-perf-lighthouse 交付
  ✗ H7 全局报告未终验：Round8=缺失，❌=0，占位=0，evidence/r8 索引=缺失 —— 由 r8-global-report 交付

Round 8 深度门禁：1/8 项通过，7 项失败。 → 退出码 1
```

| 项 | 基线实测 | 待合入能力（契约见标准 §2 对应小节） | 责任分支 |
|---|---|---|---|
| H1 | FAIL：525/800 字 | 字源 pipeline 扩到 800+（无重复、全汉字、TOTAL 一致） | r8-literacy-etymology |
| H2 | FAIL：STORIES 58/99、儿歌 0/3、路由缺失 | u59–u99 手写剧情（功能探针非兜底）+ `songs.js` ≥ 3 首 + `/songs` 真路由 | r8-literacy-stories |
| H3 | FAIL：路由/视图/数据/联动全缺 | `/skill-map` + 视图 + `skill-graph.js`（≥ 10 节点含边）+ 进度/年龄档联动 | r8-math-skillgraph |
| H4 | FAIL：精度脚本缺失（形近池存量绿） | `test-ocr-accuracy.mjs`（识别 + accuracy + 阈值断言三重信号） | r8-literacy-ocr-quality |
| H5 | FAIL：v2 能力 + smoke 均缺 | 音素/声调评分或学伴对话面 + `ROUND8_H5_SMOKE`（写法见标准 §2.5） | r8-literacy-followread |
| H6 | FAIL：分数未回填、evidence/r8 0/2 | 双 App P ≥ 95 回填 §2.1 + LH 原始 JSON ≥ 2 份归档 | r8-perf-lighthouse |
| H7 | FAIL：报告仍是 Round 7 | GLOBAL-SUMMARY-REPORT 刷新 Round 8 + `evidence/r8` 索引 | r8-global-report |
| H8 | **PASS**：check:round7 8/8 | 各分支合并时保持不退化 | 全部分支 |

结论：1/8 是功能分支未合并时的**预期红灯**，不表示门禁自身异常。v1.1 探针已做绿灯路径预验证（以最小伪造交付物模拟集成实测 8/8 → 退出码 0，随后回滚），按标准 §2 契约接线必然点绿；模板 §2.1 回填路径亦实测可翻绿 H6。

## 2. 集成回填模板

> 回填触发：所有 Round 8 功能分支合入集成分支
> 集成提交：`[SHA 待回填]`
> 回填日期：`[待回填]`
> 回填人：父代理编排器

### 2.1 Lighthouse Perf ≥ 95（**H6 探针读此表**）

> 回填格式（探针按行首 `|` + 第一格 App 名 + 第二格数字斜杠锚定解析）：
> 第二格必须写成 `96 / 100 / 100` 这样的 **P / A / BP 单格斜杠格式，数字打头**；
> 拆成三个单元格、写在正文里、或数字前加文字，探针都不认。

| App | P / A / BP（单格斜杠，数字打头） | 判定 |
|---|---|---|
| 识字 | 待回填 | |
| 数学 | 待回填 | |

证据归档（H6 探针递归数 `.json` ≥ 2）：

| 文件 | 路径 |
|---|---|
| 识字 LH 原始报告 | `.agent_workspace/evidence/r8/lighthouse-literacy.json`（`[待归档]`） |
| 数学 LH 原始报告 | `.agent_workspace/evidence/r8/lighthouse-math.json`（`[待归档]`） |
| axe 输出 | `.agent_workspace/evidence/r8/`（`[待归档]`） |

### 2.2 OCR 精度基准（H4 配套量化值）

| 指标 | 实测 |
|---|---|
| 基准图集规模 | `[N 张，生成方式]` |
| 整体正确率 | `[NN%，阈值 NN%]` |
| 命令 | `node apps/literacy-app/scripts/test-ocr-accuracy.mjs` 输出粘贴于此 |

### 2.3 八项实测总览（粘贴 `check:round8` 8/8 全文并填计数）

| 项 | 期望 | 集成实测 |
|---|---|---|
| H1 字源 | ≥ 800 字无重复全汉字 | `[N 字]` |
| H2 剧情 + 儿歌 | u59–u99 非兜底 + ≥ 3 首 + 真路由 | `[N 条 / N 首 / 路由]` |
| H3 技能图谱 | 路由 + 视图 + ≥ 10 节点含边 + 联动 | `[路由 / N 节点]` |
| H4 OCR 精度 + quiz | 三重信号脚本 + 形近池不退化 | `[脚本 / 正确率]` |
| H5 跟读 v2 | v2 能力 + ROUND8_H5_SMOKE | `[能力 / smoke]` |
| H6 Lighthouse | 双 App P ≥ 95、A/BP ≥ 90 + 证据 ≥ 2 JSON | 见 §2.1 |
| H7 全局报告 | Round 8 零 ❌ 零占位 + evidence/r8 索引 | `[勾选]` |
| H8 R7 不退化 | check:round7 8/8 | `[勾选]` |

### 2.4 体积（gzip 预算 + zip 记录）

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| 识字首屏 JS gzip | < 420 KB（R7：108,112 B） | `[待回填]` | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB（R7：77,058 B） | `[待回填]` | `[P/F]` |
| literacy-app.zip | R7：2,891,785 B | `[待回填]`（Δ`[±]`，注明来源：儿歌音频/字源数据等） | 记录 |
| math-app.zip | R7：435,723 B | `[待回填]`（Δ`[±]`，注明来源：图谱等） | 记录 |

### 2.5 手动走查（W1–W6，见标准 §5）

| # | 走查项 | 结果 |
|---|---|---|
| W1 | 字源新增抽查 5 字（含 reduced-motion 静帧） | `[勾选/问题]` |
| W2 | u59–u99 抽 5 站文案 + 儿歌 3 首可播 | `[勾选/问题]` |
| W3 | 技能图谱解锁/先修提示 + 键盘可达 | `[勾选/问题]` |
| W4 | OCR 精度报告复核 + 实拍闭环 | `[勾选/问题]` |
| W5 | 跟读 v2 读对/读错反馈 + 拒麦克风降级 | `[勾选/问题]` |
| W6 | 硬性红线抽查（触控/键盘/庆祝/对比度） | `[勾选/问题]` |

## 3. 未达标处理（无则写「无」）

| 项 | 现状 | 责任分支 | 计划 |
|---|---|---|---|
| `[无]` | | | |

## 4. 结论（集成回填后填写）

`Round 8 深度门禁 [PASS/FAIL]（[N]/8）；Round 7/6 回归 [无/有] 退化；Lighthouse 识字 [P/A/BP] / 数学 [P/A/BP]；OCR 精度 [NN%]；zip 体积见 §2.4。`
