# Round 16 集成说明

> 目标分支：`cursor/r16-orchestration-9f67`
> 集成方式：按下列顺序 cherry-pick 各功能提交；每步保持工作树干净。

## 合入顺序

1. **arch** — `cursor/r16-arch-contracts-9f67`
2. **audit** — `cursor/r16-hongen-gap-audit-9f67`
3. **intro** — `cursor/r16-literacy-intro-fallback-9f67`
4. **rich** — `cursor/r16-play-rich-500-9f67`
5. **learn-demo** — `cursor/r16-math-learn-demo-9f67`
6. **wp** — `cursor/r16-math-wp-analysis-9f67`
7. **mascot** — `cursor/r16-mascot-parent-week-9f67`
8. **smoke** — `cursor/r16-smoke-tests-9f67`
9. **spec** — `cursor/r16-acceptance-spec-9f67`
10. **gate** — `cursor/r16-regression-gate-9f67`

依赖理由：arch 先固定契约，audit 随后提供双 App 缺口基准；intro 与 rich 再补齐识字体验，
learn-demo 与 wp 补齐数学体验，mascot 为双 App 周报提供统一人格与解释层。smoke 在功能稳定后
覆盖最终行为，spec 固化验收口径，gate 最后回填真实基线和集成顺序。

## 冲突处理

- `package.json` 与 `scripts/check-round16.mjs`：保留已有所有 scripts；以 spec 的最终 H1–H8
  口径为准，同时保留 gate 的 `check:round15` 往轮判定。
- `acceptance-log-round16.md`：保留 spec 的验收结构和 gate 的实跑基线；功能线未复验前不得把
  红灯手工改绿。
- `CharDetailView.vue`：保留 Round 15 的玩→认→练→写→说阶段顺序，仅把 intro 的无字源
  回退舞台接入认步，不得回退 play 舞台与写步示范。
- mascot 涉及双 App 家长页时，保留两个 App 原有统计数据源；共享的是文案/解释契约，不用
  任一 App 的实现整文件覆盖另一侧。
- `.agent_workspace/evidence/r16/**` 按文件合并；实跑输出不得由人工摘要替换。

## 每步验证

每次 cherry-pick 后至少运行：

```bash
npm run check:round16
npm run check:round15
```

intro、rich 合入后加跑 literacy 测试；learn-demo、wp、mascot 合入后运行对应 App smoke。
干净环境中若 Round 15 仅 H8 因 Round 13 H6 失败，先运行 `npm run android:sim` 生成双 APK
再复验。最终收口条件为 `check:round16` 8/8 且 `check:round15` 8/8。
