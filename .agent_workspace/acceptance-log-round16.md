# Round 16 验收回填日志

> 编排启动基线：功能未合入时 `check:round16` 预期红  
> 目标：H1–H8 全绿；`check:round15` 保持 8/8

## 启动基线（v1.1 探针，2026-08-28，干净 worktree）

```
Round 16 check (ROUND16-v1.1): 0/8

✗ H1 缺少 round16-hongen-gap-audit.md 或内容过薄
✗ H2 无字源认步仍可能空白（缺可执行 ROUND16_H2 或回退舞台未接 intro）
✗ H3 富 Play 不足：rich=272(需≥500)，narration去重=272(需≥400)（apps/literacy-app/src/data/char-play.js）
✗ H4 数学学演示不足（可执行标记=false，三态=false，可跳过=false，代码计数=0，登记表仅参考 0）
✗ H5 缺应用题剖析壳：需可执行 ROUND16_H5 且含 剖析+分步+变式
✗ H6 学伴人格不足（可执行标记=false，去重台词=0(需≥40)，阶段场景=0(需≥3)）
✗ H7 缺家长周报：需可执行 ROUND16_H7 且含 弱项+建议+周报
✗ H8 check:round15 7/8（需 8/8；干净环境先 npm run android:sim 重建双 APK）
```

- 预期启动基线约 1/8（H8 绿）；本 VM 无 Android SDK（`ANDROID_HOME` 空、APK 未落盘），
  round13 H6 → round15 H8 连锁红，故记 0/8。带 SDK 环境跑 `npm run android:sim` 后 H8 即绿。
- H3 现值 272（富脚本存量），距 500 缺 228，narration 去重 272/400。
- 防误绿自测（写临时文件→跑探针→已还原）：
  - H4 标记只写在注释 + 12 个 skillId → 红（可执行标记=false）✓
  - H4 可执行标记 + 三态词 + skip + 12 skillId → 绿 ✓
  - H6 同一句台词复制 45 遍 → 去重计 1，红 ✓；44 条各异 + 4 类场景键 → 绿 ✓
  - H7 标记在块注释 → 红；可执行标记 + 弱项/建议/周报 → 绿 ✓

| 探针 | 状态 | 证据 | Owner |
|---|---|---|---|
| H1 双 App 体验总表 | ⬜ | | r16-hongen-gap-audit |
| H2 无字源认步动画 | ⬜ | | r16-literacy-intro-fallback |
| H3 富 Play ≥500 | ⬜ | | r16-play-rich-500 |
| H4 数学学演示 ≥12 | ⬜ | | r16-math-learn-demo |
| H5 应用题剖析壳 | ⬜ | | r16-math-wp-analysis |
| H6 学伴人格 ≥40 | ⬜ | | r16-mascot-parent-week |
| H7 家长可解释周报 | ⬜ | | r16-mascot-parent-week |
| H8 往轮 round15 | ⬜ | | r16-regression-gate |

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-28 | v1.0 编排启动，十路发射 |
| 2026-08-28 | v1.1 堵误绿：H4 只认可执行标记文件（空目录/登记表不算）；H2/H5/H6/H7 标记剥注释后判；H3 去种子 txt 近路 + narration 去重 ≥400；H6 台词去重计数 + 阶段场景 ≥3；回填启动基线 0/8（H8 环境依赖） |

## 十路子代理

| # | 模型 | 分支 |
|---|---|---|
| 1 | fable | r16-arch-contracts |
| 2 | fable | r16-hongen-gap-audit |
| 3 | fable | r16-acceptance-spec |
| 4 | opus-fast | r16-literacy-intro-fallback |
| 5 | opus-fast | r16-play-rich-500 |
| 6 | opus-fast | r16-math-learn-demo |
| 7 | opus-fast | r16-math-wp-analysis |
| 8 | opus-fast | r16-mascot-parent-week |
| 9 | gpt-sol | r16-smoke-tests |
| 10 | gpt-sol | r16-regression-gate |
