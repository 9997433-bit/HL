Model slug: claude-opus-5-thinking-high-fast
# Round 8 · H4 验收片段：拍照识字精度 + 考一考形近池

> 分支：`cursor/r8-literacy-ocr-quality-9f67`（基线 `cursor/openmoji-integration-9f67` @ `a8b21b3`）
> 探针：`npm run check:round8` → **H4 PASS**
> 复跑：`npm --prefix apps/literacy-app run test:ocr:accuracy`（约 1 秒，已挂在 `npm test` 上）
> 机读：同一命令加 `--json`，输出带 `marker: "ROUND8_H4"`

## 1. 基准集

五张固定图，一个字节都不许变；`scripts/fixtures/ocr/*.png` 由
`npm --prefix apps/literacy-app run gen:ocr:benchmark` 生成后入库，
刻意不放 `public/`（只测试用，进了 public 就要跟着离线包发给每个孩子）。

| 基准图 | 版面 | 图上的字 | 考什么 |
|---|---|---|---|
| `public/ocr/sample-photo.png` | 白底字卡 96px 黑体 | 日月山水 | 「试一张示例」这条路的下限 |
| `scripts/fixtures/ocr/book-page.png` | 绘本内页 52px 两行 | 白云青山绿水花草鱼鸟人家 | 小字号下的召回 |
| `scripts/fixtures/ocr/warm-light.png` | 暖光偏黄、低对比、歪 1.6° | 上下左右 | 预处理该救回来的那一类 |
| `scripts/fixtures/ocr/blackboard.png` | 深底白字（黑板 / 夜间） | 天地人和 | 反色版面不整页丢字 |
| `scripts/fixtures/ocr/blurry-note.png` | 便签 34px + 失焦 2px | 今天我们一起读书写字画 | 手抖拍糊的下限 |

## 2. 实测（Node 22.14 · tesseract.js 7.0.0 + core 7.0.0 · chi_sim 4.0.0_fast）

| 基准图 | 召回 | 识别率 | 丢字 | 误检 | 置信度 | 耗时 |
|---|---:|---:|---|---|---:|---:|
| 示例字卡 日月山水 | 4/4 | 100% | 无 | 无 | 95 | 87 ms |
| 绘本内页 小字两行 | 12/12 | 100% | 无 | 无 | 86 | 72 ms |
| 暖光字卡 偏黄低对比 | 4/4 | 100% | 无 | 无 | 60 | 54 ms |
| 黑板 深底白字 | 4/4 | 100% | 无 | 无 | 93 | 44 ms |
| 便签 拍糊的小字 | 11/11 | 100% | 无 | 无 | 88 | 54 ms |
| **合计** | **35/35** | **100.0%** | — | — | — | 约 0.8 s（含建 worker） |

门禁阈值（留了余量，掉下去就是真退化，不是抖动）：
总召回 ≥ 90%；单图 ≥ 70%–100%（越难的图给得越松）；
每张图的关键字（如「日月山水」「青山绿水」「读书」）一个都不许丢；
误检 ≤ 2 字；置信度分档下限 45–80。

## 3. 三段覆盖

| 段 | 断言数 | 内容 |
|---|---:|---|
| 引擎跑分 | 6 | 逐图召回率 / 关键字 / 误检 / 置信度 + 总召回率；基准字必须全在字库里（认出来就讲得了） |
| 预处理 | 4 | `preprocess()` 在 canvas 替身上跑：长边缩到 1280、短边放大到 640、区间内不重采样；灰阶拉满 0–255；近纯色不拉伸（不放大噪点）；空图报「照片是空的」 |
| 形近复核 | 4 | `CharDetailView` 的 `buildListen` / `buildQuiz` 都走 `@/utils/distractors.js`；35 个基准字的干扰项全部来自形近库且最像的那个固定在场；形近库为空时退回同部首 / 笔画相近；`buildOptions` 出四个不重样的选项 |

合计 14 项，实测 **14/14 通过**。

## 4. 与既有测试的分工

- `scripts/test-ocr.mjs`：取字规则（标点/拼音/去重/24 字上限/字库切分），不碰引擎。
- **`scripts/test-ocr-accuracy.mjs`（本次新增）**：引擎精度 + 预处理算法 + 形近池接线，纯 Node，约 1 秒。
- `scripts/smoke.mjs`：真浏览器整链（懒加载不下引擎、Service Worker 兜底、认出的字点得进单字页）。

## 5. 回归口径

- 换语言包、升 `tesseract.js`、改 `preprocess()`：先跑 `test:ocr:accuracy --json`，
  识别率不得低于本表；确有提升再把阈值往上抬。
- 换基准图：必须同时更新 `gen-ocr-benchmark.mjs`、本片段的实测表和脚本里的阈值。
- `CharDetailView` 的选项若改回随机池，第 3 段第 1 条当场红灯（`check:round8` H4 同步转红）。
