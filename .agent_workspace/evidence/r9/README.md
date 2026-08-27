Model slug: gpt-5.6-sol-xhigh-fast
# Round 9 Lighthouse 原始证据

生成命令：

```bash
npm ci
npm run test:lighthouse:ci
```

固定口径：Lighthouse `12.8.2`、mobile form factor、simulate throttling、gzip 静态服务；
Performance `>= 0.95`，Accessibility / Best Practices `>= 0.90`。

| App | 原始报告 | P / A / BP | final URL | fetchTime |
|---|---|---|---|---|
| 识字 | `lighthouse-literacy-app.json` | **98 / 100 / 100** | `http://127.0.0.1:43171/#/` | `2026-08-27T11:18:19.677Z` |
| 数学 | `lighthouse-math-app.json` | **98 / 100 / 100** | `http://127.0.0.1:43172/#/` | `2026-08-27T11:18:31.018Z` |

测量 commit：`e1cdced`（`cursor/r9-perf-ci-device-9f67`）。主机 benchmarkIndex
分别为 `3698.5` / `3782.5`。`acceptance-output.txt` 保存同轮完整输出；构建、双 App
首屏 gzip、Lighthouse、22 路由 axe 和 4 主题 × 24 状态 axe 均通过。

报告由固定版本工具直接生成，不得手写或仅保留分数摘要。
