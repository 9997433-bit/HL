# Round 15 集成说明

> 目标分支：`cursor/openmoji-integration-9f67`  
> 集成方式：按下列顺序 cherry-pick 各功能提交；每步保持工作树干净。

## 合并顺序

1. **arch** — `cursor/r15-arch-contracts-9f67`
2. **engine** — `cursor/r15-play-engine-9f67`
3. **autofill** — `cursor/r15-play-autofill-9f67`
4. **rich** — `cursor/r15-play-catalog-rich-9f67`
5. **phase** — `cursor/r15-phase-remap-9f67`
6. **write** — `cursor/r15-write-guide-9f67`
7. **smoke** — `cursor/r15-play-smoke-tests-9f67`
8. **spec** — `cursor/r15-acceptance-spec-9f67`
9. **audit** — `cursor/r15-hongen-play-audit-9f67`
10. **gate** — `cursor/r15-regression-gate-9f67`

依赖理由：engine 先落实 arch 契约；autofill 建立全库 fallback 后，rich 只覆盖富脚本；
phase 再消费稳定的 `getCharPlay`/舞台 API；write 在五步阶段机上接示范；smoke 最后覆盖最终
UI；spec、audit、gate 在功能稳定后回填，gate 最后保留实跑证据和往轮策略。

## 冲突处理

- `char-play*` / 索引冲突：保留 engine 的公开 API，保留 autofill 的
  `templateFallback: true` 全库兜底，保留 rich 的 `templateFallback: false` 富脚本。富脚本
  合入后重新运行生成器，以生成结果为准，不手工拼接生成文件。
- `CharDetailView.vue` 冲突：phase 拥有五步顺序和 Play/Etymology 接线；write 只拥有
  「进写步先示范、可跳过、再描红」逻辑；engine 的 `CharPlayStage` props/events 契约不得
  在冲突解决时改名。最终默认顺序必须是玩→认→练→写→说。
- literacy `smoke.mjs` 冲突：追加 `ROUND15_H7` 场景，不删除 R11–R14 既有探针；
  reduced-motion 和跳过路径都要保留。
- `package.json` / `check-round15.mjs` 冲突：保留所有既有 npm scripts；以 spec 的 H1–H7
  契约为基础，保留 gate 的 H8 精确判定和固定八项输出。
- `acceptance-log-round15.md` 冲突：保留 spec 的 H1–H8 表格结构，并保留 gate 写入的基线
  分数、H8 环境说明和 `evidence/r15/baseline-check.txt` 链接；功能线不得预填未实跑的绿灯。
- `.agent_workspace/evidence/r15/**` 按文件合并，禁止用 R13 模拟结果冒充 R14 真机证据。

发生冲突时先 `git checkout --conflict=merge <file>` 查看两侧语义，手工解决后运行对应生成器
和 smoke；不得用整文件 ours/theirs 覆盖跨轮探针。

## H8 往轮策略

`check:round15` 调用 `check:round13 --json`，要求 **H1–H6 与 H8 全绿**；只允许 H7 因
外部 Play Console 账号阻断继续红。因此正常批准基线是 Round 13 **7/8**，Round 13
若达到 8/8 也通过。不能只比较总分：H7 后续翻绿时，任一其他项退化仍必须使 H8 失败。

Round 13 H6 依赖不入库的双 APK。干净集成环境若显示 6/8（H6+H7 红），先运行
`npm run android:sim` 重建产物，再复跑；缺 SDK/JDK 或 APK 是环境红灯，不得降低 H8
阈值。`check:round14` 的 4/8 无真机收口分数用于旁证，不作为替代门槛，避免新增 R14
得分掩盖 R13 退化。

## 每步验证

每次 cherry-pick 后至少运行：

```bash
npm run check:round13
npm run check:round15
```

engine/autofill/rich 合入后加跑数据检查；phase/write/smoke 合入后加跑 literacy test/smoke。
最终以 `check:round15` 8/8、Round 13 必绿项全绿及人工走查 W1–W6 为收口条件。
