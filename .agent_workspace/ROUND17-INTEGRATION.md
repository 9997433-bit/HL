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
