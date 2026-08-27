# R9 H3 证据 · 技能图谱推荐下一步

分支 `cursor/r9-math-graph-reco-9f67`。两张图都取自 `apps/math-app` 的生产构建
（`npm run build` 后用无头 Chrome 打开 `/#/skill-graph`），存档与档位是喂进 localStorage 的：

```json
{ "mastery": { "count-to-5": 0.95, "count-to-10": 0.9, "add-within-10": 0.4, "shape-2d": 0.86 },
  "ageBand": "L3" }
```

| 文件 | 看点 |
| --- | --- |
| `skill-graph-reco-l3.png` | 推荐位：序号 + 理由标签（差一点 / 补基础）+ 一句话说明 + 去练入口；下方是「本档目标 100以内减法，还差 4 步」的补课路线；右上角标明「只读建议 · 不写进度」 |
| `skill-graph-canvas-l3.png` | 同一份推荐在图上的样子：四个推荐位描了圈并标上 1–4，和列表序号一一对应 |

复现门禁：

```bash
npm --prefix apps/math-app run check:content   # 推荐纯函数断言（排序 / 路线拓扑 / 不写回存档）
npm --prefix apps/math-app run build && node apps/math-app/scripts/smoke.mjs   # ROUND9_H3_SMOKE
node scripts/check-round9.mjs                  # H3
```
