Model slug: gpt-sol
# Round 7 Lighthouse / 首屏性能实测

> 日期：2026-08-27  
> 分支：`cursor/r7-perf-lighthouse-9f67`  
> 基线：`cursor/openmoji-integration-9f67` @ `46759f3`  
> 性能实现：`33f01f2`  
> 工具：Lighthouse `12.8.2`，mobile / simulate，gzip 静态服务器

## Lighthouse 硬门槛

命令：

```bash
LIGHTHOUSE_BIN=/home/ubuntu/.npm/_npx/0f94ee7615faf582/node_modules/.bin/lighthouse \
ACCEPTANCE_MIN_LH_PERFORMANCE=0.90 \
ACCEPTANCE_MIN_LH_ACCESSIBILITY=1 \
ACCEPTANCE_MIN_LH_BEST_PRACTICES=1 \
npm run test:acceptance
```

| App | Performance | Accessibility | Best Practices | 判定 |
| --- | ---: | ---: | ---: | --- |
| 识字 | **97** | **100** | **100** | PASS |
| 数学 | **94** | **100** | **100** | PASS |

`test:acceptance` 同轮实测还通过：

- 首屏入口 JS gzip：识字 `108,112 B`，数学 `77,058 B`（均 `< 256,000 B`）。
- axe 路由扫描：双 App `20/20`，`critical=0, serious=0`。
- 识字状态扫描：3 套主题 × 24 状态，`critical=0, serious=0`。

## 优化与回归证据

- 双 App 把 GSAP 从首页同步依赖移到真正需要它的懒加载路由；识字星爆、徽章、学伴和数学首页反馈改用原生 Web Animations。
- 数学入口 gzip 从基线 `105,114 B` 降至 `77,058 B`（`-28,056 B / -26.7%`）。
- 双 App 统一内联入口关键 CSS；SW 安装/完整离线预缓存延后到首屏稳定后，避免和首次渲染争抢资源。
- 数学锁定卡片不再用父级透明度降低全部文字对比度，Lighthouse A11y `95 → 100`，首页 axe `serious 5 → 0`。
- `npm --prefix apps/literacy-app test`：PASS（161 路由 + 30 交互）。
- `npm --prefix apps/math-app test`：PASS（16 路由 + 26 交互）。
- 最终 `npm --prefix apps/literacy-app run smoke`：PASS（161 路由 + 30 交互）。
- `npm run test:offline`：PASS（识字 2076 项、数学 56 项预缓存，关服后均可启动）。
- `npm run check:round6`：7/7 PASS。

结论：双 App Lighthouse Performance 均 ≥ 90，Accessibility / Best Practices 均保持 100；功能 smoke 与完整离线能力无退化。
