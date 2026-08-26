# Round 4 Lighthouse / axe / 构建验收记录

记录日期：2026-08-26  
分支：`cursor/r4-lighthouse-regression-9f67`  
环境：Node.js v22.14.0、npm 10.9.7、Google Chrome 148.0.7778.96、Lighthouse 12.8.2

## 门禁与结论

执行命令：`npm run test:acceptance`

| 门禁 | 阈值 | 结论 |
| --- | --- | --- |
| 单 App 构建时间 | ≤ 60 秒 | PASS |
| 首屏入口 JS gzip | < 256,000 bytes | PASS |
| Lighthouse Performance / Accessibility / Best Practices | 各 ≥ 90 | PASS |
| axe 路由扫描 | critical = 0、serious = 0 | PASS |
| axe 识字交互态扫描 | critical = 0、serious = 0 | PASS |

## 实测数据

### 构建与首屏入口

| App | 构建耗时 | 首屏 JS raw | 首屏 JS gzip |
| --- | ---: | ---: | ---: |
| 识字 App | 1,778 ms | 301,638 bytes | 101,140 bytes |
| 数学 App | 1,497 ms | 277,013 bytes | 98,175 bytes |

### Lighthouse（mobile / simulated throttling）

| App | Performance | Accessibility | Best Practices |
| --- | ---: | ---: | ---: |
| 识字 App | 99 | 100 | 100 |
| 数学 App | 97 | 100 | 100 |

### axe-core

- 路由扫描：20/20 页面完成（识字 11、数学 9），`critical=0`、`serious=0`。
- 识字状态扫描：3 套主题 × 14 个状态 = 42 次，`critical=0`、`serious=0`、运行失败 0。

## 回归与修复

初始基线的 Lighthouse 实测为：

| App | Performance | Accessibility | Best Practices |
| --- | ---: | ---: | ---: |
| 识字 App | 85 | 100 | 100 |
| 数学 App | 91 | 100 | 100 |

识字首屏把 GSAP 动画运行时打入入口包，入口 gzip 为 132,175 bytes。修复后：

- 简单进度环和首页进场动画改用 CSS；
- 仅在庆祝层或休息提醒实际出现时异步加载动画组件；
- 验收静态服务器按生产交付方式提供 gzip；
- Lighthouse 默认门槛与 Round 4 简报的过渡门槛统一为 90。

识字首屏入口 gzip 降至 101,140 bytes（减少 31,035 bytes，约 23.5%），
Performance 从 85 提升到 99。

## `build:all` 发布包

执行命令：`npm run build:all`

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `dist/hongen-literacy-app.zip` | 600,056 bytes | `d2738b0eaad69e80c836e64c6b1d22c7ee3a3a2a81391361df83d6036a0695f6` |
| `dist/hongen-math-app.zip` | 190,051 bytes | `94400eeaf3d23a1c5814e84e83b0ba549376065ef273f0595279a7b24dc68d5f` |

## Round 3 全量回归

最终执行 `npm run test:round3`，退出码为 0。该次全量复跑中的 Lighthouse
Performance 为识字 98、数学 98，Accessibility 与 Best Practices 均为 100；
axe 路由与交互态仍为 `critical=0`、`serious=0`。

结论：Round 4 Lighthouse、axe、gzip 与发布包构建门禁全部通过。
