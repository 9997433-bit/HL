# Round 19 集成说明

> 目标分支：`cursor/r19-orchestration-9f67`
> 集成方式：按下列顺序 cherry-pick；每步保持工作树干净，并以真实命令退出码为准。

## 建议合入顺序

1. **acceptance** — `cursor/r19-acceptance-spec-9f67`
2. **arch / audit** — `cursor/r19-arch-contracts-9f67`、`cursor/r19-hongen-gap-audit-9f67`
3. **play-rich** — `cursor/r19-play-rich-full-9f67`
4. **polish** — `cursor/r19-play-polish-9f67`
5. **wp-player** — `cursor/r19-wp-video-player-9f67`
6. **explains** — `cursor/r19-wp-explain-150-9f67`
7. **walkthrough** — `cursor/r19-walkthrough-bundle-9f67`
8. **smoke** — `cursor/r19-smoke-tests-9f67`
9. **gate** — `cursor/r19-regression-gate-9f67`

acceptance 先固定 H1–H8 口径；arch 与 audit 随后提供全库 seed / 精美度舞台 / 剖析播放器契约
及差距基准。全库富 Play 数据先落地并重生分片，polish 再围绕最终数据形态升级 CharPlayStage。
剖析播放器（H4）先吃现有手写步文案，explains（H5）再扩到 ≥150 母题，且不得回退
`template.steps` 与 `buildAnalysis` 步数对齐（R18 红线）。walkthrough 与 smoke 在功能稳定后
记录真实行为，gate 最后回填 Android 模拟台账和往轮 `check:round18` 结果。

## 冲突处理

- `package.json` 与 `scripts/check-round19.mjs`：保留全部既有 scripts，以 acceptance 的最终
  H1–H8 口径为准；不得弱化 H8 的 Round 18 8/8 要求。
- `char-play-rich*` / seed / 分片：先保留 play-rich-full 的完整数据与按单元懒加载管线，再应用
  polish 的舞台表现；冲突后重新运行生成器和 bundle 检查，不手工删减富脚本。
- CharPlayStage：H3（polish）拥有多拍节 / 道具反馈 / 氛围层；H2 只负责数据覆盖。冲突时
  Stage UI 以 H3 为准、数据以 H2 为准。
- 应用题剖析：wp-video-player 拥有播放时间轴状态机，explains 拥有手写讲解内容；两者都需保留，
  且最终步数一致率不得回退；reduced-motion 必须可降级为手动点步。
- `.agent_workspace/evidence/r19/**` 按文件合并，只追加真实证据。Android 报告中的 APK
  SHA-256 必须与同次 `npm run android:sim` 生成的盘上 APK 一致。

## 每步验证

```bash
npm run check:round18
```

有 `check:round19` 后加跑：

```bash
npm run check:round19
```

最终 gate 还应运行 `npm run android:sim`。若环境无法得到全绿模拟结果，必须提交包含字面
`BLOCKED`、失败原因及复现命令的 `evidence/r19/device-blocked.md`，不得用 r13/r17/r18 旧报告
冒充本轮结果。
