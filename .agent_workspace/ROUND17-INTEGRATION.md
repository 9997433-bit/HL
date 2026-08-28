# Round 17 集成说明

> 目标分支：`cursor/r17-orchestration-9f67`
> 合入顺序：arch → audit → play-rich → learn-demo-plus → wp-explain → mascot-wire → walkthrough → smoke → spec → gate

## 冲突处理

- `char-play-rich.js` / seed：保留更高条数一侧；narration 撞句以生成器校验为准。
- `learn-demos.js`：按 skillId 合并，禁止重复 skillId。
- `wpAnalysis` / 母题 explain：手写链优先于公式兜底。
- `check-round17.mjs`：以 acceptance-spec 最终口径为准。
- 走查证据只追加，不覆盖伪造。

## 每步验证

```bash
npm run check:round17
npm run check:round16
```

`gate` 分支必须保留两条命令的真实退出码与完整摘要到
`.agent_workspace/evidence/r17/baseline-check.txt`。最终收口要求为 Round 17 **8/8**，
并保持 Round 16 **8/8**；功能线未合入前的红灯不得人工改绿。

## H7 设备证据

运行 `npm run android:sim`。成功时把 APK、WebView smoke 与 OCR A 段结果记录到
`.agent_workspace/evidence/r17/android-sim-report.md`，并明确模拟结果不等价于真机签核；
若环境或设备链路失败，则写入 `.agent_workspace/evidence/r17/device-blocked.md`，必须包含
`BLOCKED`、失败原因和复现命令。
