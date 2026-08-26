# 洪恩式教育应用全局总结报告

## Round 3 实测数据（2026-08-26）

测试基线：`99e61972ffdac27c351128f155158bc49d8859b9`。完整命令、环境、
逐项结果和归档校验值见
[`acceptance-log-round3.md`](./acceptance-log-round3.md)。

| 指标 | 识字 App | 数学 App | 终验状态 |
| --- | ---: | ---: | --- |
| 构建耗时（≤60s） | 1.952s | 1.273s | ✅ |
| 首屏 JS gzip（<256,000B） | 101,499B | 79,444B | ✅ |
| Lighthouse Performance（≥95） | 92 | 95 | ❌ |
| Lighthouse Accessibility（≥95） | 87 | 93 | ❌ |
| Lighthouse Best Practices（≥90） | 100 | 100 | ✅ |
| axe critical | 1 | 3 | ❌（合计 4） |
| axe serious | 58 | 5 | ❌（合计 63） |
| 解压后断网启动 | PASS | PASS | ✅ |

最终归档均通过 CRC 完整性检查：

- `hongen-literacy-app.zip`：397,924 bytes，249 文件，
  SHA-256 `e49fab8db292989abb672bc668deae2dbf391da21ac9a64d64b9034f806582a4`
- `hongen-math-app.zip`：141,235 bytes，29 文件，
  SHA-256 `da8676e2d25d8db9b5db75201a61d5f1ded2ecc5073c3d453ba478480236653f`

### 终验判定

构建、打包、zip 解压和离线启动均通过；但 Lighthouse 与 axe 无障碍硬门槛
未通过，`scripts/acceptance.sh` 退出码为 `1`。当前状态为
**产物可完整运行，但 Round 3 最终验收失败，不应标记为可发布**。
