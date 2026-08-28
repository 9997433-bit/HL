# Round 18 集成说明

> 目标分支：`cursor/r18-orchestration-9f67`
> 集成方式：按下列顺序 cherry-pick；每步保持工作树干净，并以真实命令退出码为准。

## 建议合入顺序

1. **acceptance** — `cursor/r18-acceptance-spec-9f67`
2. **arch / audit** — `cursor/r18-arch-contracts-9f67`、`cursor/r18-hongen-gap-audit-9f67`
3. **play-rich** — `cursor/r18-play-rich-1200-9f67`
4. **codesplit** — `cursor/r18-play-codesplit-9f67`
5. **wp-steps** — `cursor/r18-wp-steps-align-9f67`
6. **explains** — `cursor/r18-wp-explain-80-9f67`
7. **walkthrough** — `cursor/r18-walkthrough-bundle-9f67`
8. **smoke** — `cursor/r18-smoke-tests-9f67`
9. **gate** — `cursor/r18-regression-gate-9f67`

acceptance 先固定 H1–H8 口径；arch 与 audit 随后提供契约及差距基准。富 Play 数据先落地，
codesplit 再围绕最终数据形态建立分片与懒加载。应用题步数对齐先稳定分析结构，精品讲解随后
扩充内容。walkthrough 与 smoke 在功能稳定后记录真实行为，gate 最后回填 Android 模拟台账
和往轮回归结果。

## 冲突处理

- `package.json` 与 `scripts/check-round18.mjs`：保留全部既有 scripts，以 acceptance 的最终
  H1–H8 口径为准；不得弱化 H8 的 Round 17 8/8 要求。
- `char-play-rich*`：先保留 play-rich 的完整数据，再应用 codesplit 的索引、分片与异步 API；
  冲突后重新运行生成器和 bundle 检查，不手工删减富脚本。
- 应用题分析文件：wp-steps 拥有步数契约，explains 拥有手写讲解内容；两者都需保留，且最终
  `template.steps` 与分析步数一致率不得回退。
- `.agent_workspace/evidence/r18/**` 按文件合并，只追加真实证据。Android 报告中的 APK
  SHA-256 必须与同次 `npm run android:sim` 生成的盘上 APK 一致。

## 每步验证

```bash
npm run check:round15
npm run check:round16
npm run check:round17
```

最终 gate 还应运行 `npm run android:sim`。若环境无法执行，必须提交包含字面 `BLOCKED`、
失败原因及复现命令的 `evidence/r18/device-blocked.md`，不得用旧报告冒充本轮结果。
