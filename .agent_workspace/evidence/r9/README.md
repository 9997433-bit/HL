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
| 识字 | `lighthouse-literacy-app.json` | `[运行后回填]` | `[运行后回填]` | `[运行后回填]` |
| 数学 | `lighthouse-math-app.json` | `[运行后回填]` | `[运行后回填]` | `[运行后回填]` |

报告必须由固定版本工具直接生成，不得手写或仅保留分数摘要。
