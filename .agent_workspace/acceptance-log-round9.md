Model slug: claude-fable-5-thinking-xhigh
# Round 9 验收记录

> 状态：**集成终验闭合**（2026-08-27）
> 集成线：`cursor/openmoji-integration-9f67` @ `fa875cf`
> 判定标准：`.agent_workspace/ROUND9-ACCEPTANCE.md`（探针 `scripts/check-round9.mjs` v1.1）

## 0. 基线

| 门禁 | 基线实测（`ec733bb` + 探针 v1.1） | 集成终验（`fa875cf`） |
|---|---|---|
| `check:round8` | 8/8 PASS | 8/8 PASS |
| `check:round9` | 1/8（有意红灯，仅 H8 绿） | **8/8 PASS** |

## 1. H1–H8 回填（集成分支逐项落数）

| ID | 交付物 | 集成实测 | 判定 |
|---|---|---|---|
| H1 | 儿歌 v2 | **13 首**合规；`SongsView.vue` `data-song-sync=v2` + `pitchOfNote()`；`smoke.mjs` `ROUND9_H1_SMOKE` 常量 + 交互断言 | **P** |
| H2 | OCR 扩样 | **9 张**有效 PNG（handwriting **2** 张：`handwriting.png`、`handwriting-daily.png`）；`test-ocr-accuracy.mjs` 含 `ROUND9_H2` + 逐 tier；总召回 **55/55（100%）** | **P** |
| H3 | 图谱推荐 | `skill-graph.js` `recommendPath()` / `recommend()`；`SkillGraphView.vue` 推荐位 + 路线区；`smoke.mjs` `const ROUND9_H3_SMOKE = '/skill-graph'` | **P** |
| H4 | 跟读路线 | `r9-followread-asr-evaluation.md` **15171 字符**；PoC：`speechEval.js` `phonemeMarks` / `similarityV2` + `test-speech-eval.mjs` | **P** |
| H5 | 绘本投稿 | `BOOK-COMMUNITY-SUBMISSION.md` **16789 字符**；draft-2020-12 schema + A/B 校验规则 + 收退稿示例 | **P** |
| H6 | LH CI 锁 | `scripts/lighthouse-ci.mjs` 锁 **12.8.2** + 阈值断言；`evidence/r9/lighthouse-literacy-app.json`、`lighthouse-math-app.json` | **P** |
| H7 | 发布清单 | `GLOBAL-SUMMARY-REPORT.md` 31/31 ✅、§7 全 ✅、含 `evidence/r9`；`RELEASE-CHECKLIST.md` **4539 字符** | **P** |
| H8 | R8 不退化 | `check:round8` **8/8** 项通过，0 项失败 | **P** |

## 2. 性能与质量量化

### 2.1 Lighthouse（H6/G6）

| App | P / A / BP | LH 版本 | 原始 JSON | 判定 |
|---|---|---|---|---|
| 识字 | **98 / 100 / 100** | 12.8.2 | `evidence/r9/lighthouse-literacy-app.json` | **P** |
| 数学 | **98 / 100 / 100** | 12.8.2 | `evidence/r9/lighthouse-math-app.json` | **P** |

### 2.2 OCR 逐 tier 精度（`npm run test:ocr:accuracy` @ fa875cf）

| tier | 图数 | 精度（召回） | 判定 |
|---|---|---|---|
| 印刷体 | 2 | 16/16（100%） | P |
| 暖光 | 1 | 4/4（100%） | P |
| 反色 | 1 | 4/4（100%） | P |
| 失焦 | 1 | 11/11（100%） | P |
| handwriting | 2 | 8/8（100%） | P |
| 低光 | 1 | 4/4（100%） | P |
| 复杂背景 | 1 | 4/4（100%） | P |
| 斜拍 | 1 | 4/4（100%） | P |

### 2.3 体积

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| 识字首屏 JS gzip | < 420 KB | **322 KB**（1 块） | P |
| 数学首屏 JS gzip | < 250 KB | **88,729 B** | P |
| literacy zip | R8：6,228,970 B | 见 `acceptance-log-round8.md` / #10 回归记录 | 记录 |
| math zip | R8：455,047 B | 见 `acceptance-log-round8.md` / #10 回归记录 | 记录 |

## 3. 未达标表

| 项 | 现状与差距 | 责任 | 计划 |
|---|---|---|---|
| 根 `LICENSE` | 发布清单标为**阻断** | 产品/权利人 | 发布前新增，不阻塞 R9 探针 |
| 真机 WebView OCR/LH | CI 用冻结 JSON；环境无 LH CLI 时 `[SKIP]` | R10 | Android 真机走查清单已落 `ANDROID-DEVICE-CHECKLIST.md` |

## 4. 手动走查勾选

- [x] W1 儿歌 v2（13 首、smoke `ROUND9_H1` 绿）
- [x] W2 OCR tier（逐 tier 100% 召回）
- [x] W3 图谱推荐（smoke 只读无写回）
- [x] W4 跟读路线（评估文档 + PoC 单测 14/14）
- [x] W5 投稿文档（schema + 示例完整）
- [ ] W6 发布走查（LICENSE 待权利人；清单可执行）

## 5. 集成终验

- 集成 SHA：`fa875cf`
- `check:round9`：**8/8 项通过，0 项失败**

| 命令 | 结果 |
|---|---|
| `npm test` | **PASS**（exit 0，~10 min） |
| `check:round9` | **8/8** |
| `check:round8` | **8/8** |
| `check:round7` | **8/8** |
| `test:round3` | **PASS**（exit 0，axe 4×24 状态 0/0） |
| `build:all` + `sync:android` + `check:android` | #10 回归记录 26/26 |

### 结论

**Round 9 深度门禁 P（8/8）；Round 8/7 回归无退化。** 发布阻断仅剩根 `LICENSE`（清单 §1）。
