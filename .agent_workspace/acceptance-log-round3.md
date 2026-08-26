# Round 3 最终自动化验收记录

记录日期：2026-08-26  
被测提交：`99e61972ffdac27c351128f155158bc49d8859b9`  
执行入口：`npm run build:all`、`scripts/acceptance.sh`、`npm run test:offline`

## 测试环境

- Node.js `v22.22.2`，npm `10.9.7`
- Google Chrome `148.0.7778.96`
- Lighthouse `13.4.1`
- Lighthouse 参数：mobile、simulate throttling、headless Chrome

## `scripts/acceptance.sh` 实测

| App | 构建耗时 | 首屏 JS gzip | Performance | Accessibility | Best Practices |
| --- | ---: | ---: | ---: | ---: | ---: |
| 识字 App | 1,952 ms ✅ | 101,499 B ✅ | 92 ❌（阈值 95） | 87 ❌（阈值 95） | 100 ✅ |
| 数学 App | 1,273 ms ✅ | 79,444 B ✅ | 95 ✅ | 93 ❌（阈值 95） | 100 ✅ |

构建阈值为单 App ≤ 60 秒，首屏 JS 阈值为 < 256,000 bytes gzip，
Best Practices 阈值为 ≥ 90。两个 App 的 Performance 均达到 Round 3 简报中的
≥ 90 过渡值，但识字 App 未达到脚本配置的 95 终值。

axe-core 完成 19/19 页面扫描：

| App | critical | serious | 主要未达标项 |
| --- | ---: | ---: | --- |
| 识字 App | 1 | 58 | 字表 toolbar 缺少必需 ARIA 子角色；导航、拼音、偏旁文字对比度 |
| 数学 App | 3 | 5 | 数独 board 缺少必需 ARIA 子角色；成就墙按钮无可辨识名称；答题进度 ARIA 属性不合法 |
| 合计 | 4 | 63 | hard gate 要求 critical=0，未达到 |

因此 `scripts/acceptance.sh` 退出码为 `1`，最终自动化验收状态为
**FAIL**。不得将本次数据解释为终验通过。

## 最终 zip 完整性与离线冒烟

`npm run build:all` 成功生成两个压缩包。逐包执行 `zip -T` 后解压到各 App
的 `dist` 目录，再从解压内容执行离线冒烟：

| 产物 | 大小 | 文件数 | SHA-256 | `zip -T` | 解压后离线启动 |
| --- | ---: | ---: | --- | --- | --- |
| `dist/hongen-literacy-app.zip` | 397,924 B | 249 | `e49fab8db292989abb672bc668deae2dbf391da21ac9a64d64b9034f806582a4` | OK | PASS；服务关闭后 `/#/learn/日` 启动，预缓存 249 项 |
| `dist/hongen-math-app.zip` | 141,235 B | 29 | `da8676e2d25d8db9b5db75201a61d5f1ded2ecc5073c3d453ba478480236653f` | OK | PASS；服务关闭后 `/#/sudoku` 启动，预缓存 29 项 |

两个归档均包含 `index.html` 与 `sw.js`。`npm run test:offline` 退出码为 `0`，
确认测试的是从最终 zip 重新解压的内容，而不是构建目录中的残留文件。

## 结论

- 构建、打包、归档完整性和双 App 离线启动：**PASS**
- 首屏 JS、构建时长、Best Practices：**PASS**
- Lighthouse Performance：数学达到 95；识字 92，未达到 95
- Lighthouse Accessibility：识字 87、数学 93，均未达到 95
- axe hard gate：4 个 critical，**FAIL**
- Round 3 最终自动化验收总状态：**FAIL**
