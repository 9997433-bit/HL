Model slug: gpt-5.6-sol
# Round 10 证据索引

## Desktop Lighthouse

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

Round 9 的两份 mobile 原始报告保留在 `../r9/`，与本目录的 desktop
报告组成 Web 双档；Android 实体设备档的能力边界和 owner 项见
`../../ANDROID-DEVICE-CHECKLIST.md`。

## SOTA C-6 Chrome 实测

本目录保存 SOTA 共同验收项 C-6 的 Chrome 实测切片。自动化从双 App 生产构建首页
点击全局页脚的「隐私政策」，分别以桌面和移动视口验证：

- `/privacy` 路由可达，页面标题与 `document.title` 正确；
- 页面展示版本 `1.0.0`、零账号声明及至少六个政策分节；
- 控制台与页面异常为零；
- 页面加载期间没有非本机来源请求；
- 四个视口各保存一张全页截图。

复现命令：

```bash
npm run build:all
npm run test:c6:chrome
```

机读结果写入 `browser-matrix-chrome.json`，截图命名为
`browser-matrix-{literacy|math}-{desktop|mobile}.png`。这里仅声称 Chrome 的实际
结果；Edge、Firefox、macOS/iPadOS Safari 不在当前 Linux 环境内，未伪造为已测。

报告由固定版本工具直接生成；不得手写或仅保留分数摘要。
