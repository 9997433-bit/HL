# Round 13 Android 模拟工程记录

> 标记：`ROUND13_H6`
> 分支：`cursor/r13-android-sim-harness-9f67`
> 执行环境：Linux VM + Chrome/Puppeteer + Android SDK/Gradle

## 结论

本记录对应 `.agent_workspace/evidence/r13/android-sim/report.json` 的最近一次完整执行。
只有 `npm run android:sim` 以零状态退出、双 App 的 Gradle 步骤均为 PASS、APK
SHA-256 非空、双 smoke 实际观察到的 `navigator.userAgent` 与所注入 Android
WebView UA 完全相同，且 smoke 问题数为 0 时，才判定本轮 **Android 模拟工程验证
PASS**。具体时间、测量 commit、耗时、字节数和哈希以机读报告为准，避免文档抄数
与自动化结果漂移。

该 PASS 是 `simulated: true` 的 VM 结果，不等价真机验证，不代表 Android QA 或
商店发布签核通过。实体设备上的相机/麦克风权限弹窗、系统返回键、WebView provider
版本差异、离线冷启动、安装升级、音频策略和低端机性能仍是独立发布阻断项。

## 验证面

| 验证项 | 判定依据 | 归档 |
|---|---|---|
| Web 生产构建 | `build:all` 退出 0 | `report.json` steps |
| Capacitor 同步 | `sync:android` 退出 0 | `report.json` steps |
| Android 静态门禁 | `check:android` 退出 0 | `report.json` steps |
| 识字 APK | `:app:assembleDebug`、APK 落盘与 SHA-256 | `gradle-literacy.log` |
| 数学 APK | `:app:assembleDebug`、APK 落盘与 SHA-256 | `gradle-math.log` |
| WebView UA | 双 App 注入值等于页面实际 `navigator.userAgent` | 两份 smoke 日志 |
| 路由/交互 | smoke 进程退出 0、问题数为 0 | 两份 smoke 日志 |
| OCR A 段 | device harness 进程退出 0 | `ocr-device-a.log` |

WebView smoke 不是仅向子进程声明一个未使用的环境变量：两个 smoke harness 都读取
`ANDROID_SIM_UA`，在新建页面导航前调用 `page.setUserAgent()`，再从页面上下文读取
实际值进行逐字断言。日志必须出现 `ROUND13_H6 WebView UA smoke PASS` 结果，主
harness 还会解析该值并写入报告；未观察到值、值不相等或 smoke 非零退出都会让总
命令失败。

## 证据完整性

`scripts/android-sim.mjs` 为每个 Gradle/smoke/OCR 子进程保存命令、相对工作目录、
开始时间、耗时、退出码以及完整 stdout/stderr。`report.json` 保存日志路径、字节数和
SHA-256，并保存双 APK SHA-256。Gradle 日志必须同时看到 `:app:assembleDebug` 和
`BUILD SUCCESSFUL`；只有旧报告、手写摘要或缺失日志均不能构成闭环。

复跑命令与各文件说明见
`.agent_workspace/evidence/r13/android-sim/README.md`。`--skip-apk` 只供快速开发
smoke 使用，不能生成 H6 的完整双 APK 证据。
