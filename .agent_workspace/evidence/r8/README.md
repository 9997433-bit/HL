Model slug: gpt-5.6-sol-xhigh-fast
# Round 8 证据包索引

本目录只保存可复核的原始输出。索引中的保留路径不是通过证明；负责子代理必须在同一次
验收中写入真实 JSON，并把命令、工具版本、集成 SHA 与分数回填到
`.agent_workspace/acceptance-log-round8.md`。禁止用手写分数文件替代工具输出。

## 保留路径

| 类别 | App / 扫描面 | 归档路径 | 当前状态 | 责任 |
|---|---|---|---|---|
| Lighthouse | 识字 | `lighthouse/literacy.report.json` | ⏳ 原始 JSON 待归档 | R8 #9 |
| Lighthouse | 数学 | `lighthouse/math.report.json` | ⏳ 原始 JSON 待归档 | R8 #9 |
| axe | 识字路由 | `axe/literacy-routes.json` | ⏳ 原始输出待归档 | R8 #9 |
| axe | 识字四主题状态 | `axe/literacy-states.json` | ⏳ 原始输出待归档 | R8 #9 |
| axe | 数学路由 / 四主题 | `axe/math-routes.json` | ⏳ 原始输出待归档 | R8 #9 |

## 取证约束

1. Lighthouse 报告必须保留 `lighthouseVersion`、`fetchTime`、三项 category score 与
   final URL；双 App Performance 均须至少 0.95，Accessibility / Best Practices
   均须至少 0.90。
2. axe 输出必须能追溯扫描 URL、主题/状态、critical 与 serious 数量；最终 serious
   余项必须在验收日志逐条解释或清零。
3. JSON 写入后检查可解析性，再运行 `npm run check:round8`；H6 还会交叉读取验收日志。
4. 若工具输出过大，可保留完整 JSON 并在日志中只摘录摘要，不得反向只留摘要。
