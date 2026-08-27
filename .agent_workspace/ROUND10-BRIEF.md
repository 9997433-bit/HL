# Round 10 简报 · 洪恩深度对标与发布终态

> 基线：`cursor/openmoji-integration-9f67` @ R9 闭合（`check:round9` 8/8 · 31/31 模块探针 ✅）
> 集成分支：`cursor/openmoji-integration-9f67`
> 目标：主计划三层 **A 工程 SOTA + B 洪恩深度 + C 差异化** 全部可演示、可测量、可发布

## 为何还要 Round 10

R9 在**探针层**已 31/31 ✅，但 R9 审计自列 10 条深度债——洪恩级体验与公开发布仍差最后一程：

| 深度债 | 现状 | R10 目标 |
|---|---|---|
| L-M9 跟读 | 评估文档 + 纯函数 PoC | **离线 ASR Worker 接线**（sherpa-onnx spike，三档降级不退化） |
| L-M10 OCR | 程序合成基准图 100% | **真实拍摄样张** tier + WebView 实测记录 |
| L-M11 儿歌 | 合成音高动画 | **开源/录制旋律资产**（≥3 首可听 mp3/ogg） |
| M-M1 推荐 | 只读 suggest | **推荐 → 每日冒险/错题本** 一键开练 |
| L-M5 社区 | 投稿规范文档 | **import-book-submission.mjs + ajv CI** |
| 工程 | mobile LH 98；真机未跑 | **桌面档 LH + 真机清单回填** |
| 发布 | 无 LICENSE | **MIT LICENSE + 隐私页 + 版本 1.0.0 统一** |
| SOTA P1 | C-5/C-6 等未留档 | **设计走查 + 浏览器矩阵证据** |

## 硬门槛（`check-round10.mjs` 基线 1/8，仅 H8 绿）

| 探针 | 阈值 |
|---|---|
| H1 跟读 v3 | 离线 ASR Worker 接线 + `ROUND10_H1` smoke |
| H2 OCR 真样张 | ≥2 张 `real-*` 命名样张 + `ROUND10_H2` tier |
| H3 推荐闭环 | 推荐项可跳转 daily/wrongBook + `ROUND10_H3_SMOKE` |
| H4 投稿 CI | `import-book-submission.mjs` + ajv 进 test 链 |
| H5 儿歌旋律 | ≥3 首含真实音频资产 + `ROUND10_H5` |
| H6 双档 Perf | `evidence/r10/` 含 desktop JSON + 设备清单非全 `[待填]` |
| H7 发布就绪 | 根 `LICENSE` + `/privacy` 路由 + 版本统一 |
| H8 往轮不退化 | `check:round9` 8/8 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r10-arch-contracts-9f67` | Round 10 深度对标架构契约 |
| 2 | fable | `cursor/r10-module-audit-9f67` | 洪恩**深度**对标审计（体验杆上移） |
| 3 | fable | `cursor/r10-acceptance-spec-9f67` | ROUND10-ACCEPTANCE + check-round10 v1.1 |
| 4 | opus-fast | `cursor/r10-literacy-followread-v3-9f67` | 跟读 v3 sherpa Worker + UI |
| 5 | opus-fast | `cursor/r10-literacy-ocr-real-9f67` | OCR 真实样张 tier |
| 6 | opus-fast | `cursor/r10-math-reco-daily-9f67` | 推荐 × 日冒险/错题本闭环 |
| 7 | opus-fast | `cursor/r10-book-import-ci-9f67` | 投稿 import + ajv CI |
| 8 | gpt-sol | `cursor/r10-literacy-songs-melody-9f67` | 儿歌真实旋律资产 |
| 9 | gpt-sol | `cursor/r10-perf-device-desktop-9f67` | 桌面 LH + 真机清单回填 |
| 10 | gpt-sol | `cursor/r10-global-release-9f67` | LICENSE + 隐私页 + P1 SOTA 终验 |

## 规则

- 首行 Model slug；分支 `cursor/<name>-9f67`
- worktree 开发；cherry-pick 合入；合并前 `check:round9` 8/8 不退化
- 参考：`.agent_workspace/round9-hongen-audit.md` §5 R10 归属备忘
