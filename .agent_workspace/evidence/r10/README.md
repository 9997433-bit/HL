Model slug: gpt-5.6-sol
# Round 10 desktop Lighthouse 原始证据

生成命令：

```bash
npm ci
npm run test:lighthouse:desktop
```

测量 commit：`5ea1a6f`（`cursor/r10-perf-device-desktop-9f67`）。固定口径：
Lighthouse `12.8.2`、desktop preset、simulate throttling、gzip 静态服务；
Performance `>= 0.95`，Accessibility / Best Practices `>= 0.90`。

| App | 原始报告 | P / A / BP | formFactor / mobile emulation | fetchTime | benchmarkIndex |
|---|---|---|---|---|---:|
| 识字 | `lighthouse-literacy-app-desktop.json` | **100 / 100 / 100** | `desktop` / `false` | `2026-08-27T14:39:06.300Z` | 3740.5 |
| 数学 | `lighthouse-math-app-desktop.json` | **100 / 100 / 100** | `desktop` / `false` | `2026-08-27T14:39:17.505Z` | 3315.5 |

SHA-256：

```text
65ac0cb567027e988a1d3d31efb3c1c662e128092eb4b2c6d3e7f32c7bdcb73a  lighthouse-literacy-app-desktop.json
f64ce49c8621297cc174a1060ccab37fd57382c62e7d13af05f434df7768df1c  lighthouse-math-app-desktop.json
```

同轮验收还通过双 App 构建、首屏 JS gzip、22 路由 axe 与 4 主题 × 24 状态
axe。Round 9 的两份 mobile 原始报告保留在 `../r9/`，与本目录的 desktop
报告组成 Web 双档；Android 实体设备档的能力边界和 owner 项见
`../../ANDROID-DEVICE-CHECKLIST.md`。

报告由固定版本工具直接生成；不得手写或仅保留分数摘要。
