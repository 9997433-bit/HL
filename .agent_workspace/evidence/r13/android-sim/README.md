Model slug: gpt-5.6-sol-xhigh-fast
# Round 13 Android 模拟证据

> 本目录只记录 Linux VM 中的 Android 工程构建和 Chrome WebView 配置模拟，
> `report.json` 固定写入 `simulated: true`。它不等价于 Android 实体设备、模拟器或
> Android QA 签核，不能解除商店发布前的真机阻断。

## 复跑

准备 Node/npm、`/usr/local/bin/google-chrome`、可用的 Android SDK，并让
`ANDROID_HOME` 指向 SDK 根目录。首次构建还需要 Gradle 能下载依赖且 SDK licenses
已经接受。然后从仓库根目录运行：

```bash
npm run android:sim
```

该命令可重复执行，并覆盖本目录的机读报告和日志。开发时可用
`npm run android:sim -- --skip-apk` 跳过 APK，但这种结果没有双 APK 哈希，不满足
Round 13 H6 证据要求。

## 执行链

1. 构建双 App，执行 Capacitor Android 同步和 26 项静态 Android 检查。
2. 在两个 Android 工程中运行 `./gradlew --console=plain assembleDebug`。
3. 对识字和数学全部 smoke 页面调用 Puppeteer `page.setUserAgent()`，注入带
   `; wv` 的 Android WebView UA；页面内读取 `navigator.userAgent` 并与请求值逐字
   比对。移动视口和 touch emulation 同时启用。
4. 执行 OCR device harness A 段。
5. 汇总进程退出码、路由数、问题数、APK SHA-256，以及每份日志的路径、字节数和
   SHA-256 到 `report.json`。任一必选步骤失败时命令以非零状态退出。

## 归档清单

| 文件 | 内容 |
|---|---|
| `report.json` | 总结果、实际观察到的双 App UA、APK 与日志哈希 |
| `gradle-literacy.log` | 识字 Android `assembleDebug` 完整标准输出/错误 |
| `gradle-math.log` | 数学 Android `assembleDebug` 完整标准输出/错误 |
| `smoke-literacy.log` | 识字全路由、交互与 WebView UA smoke |
| `smoke-math.log` | 数学全路由、交互与 WebView UA smoke |
| `ocr-device-a.log` | OCR device harness A 段 |

每份日志头包含命令、仓库相对工作目录、开始时间、耗时和退出码。Gradle 日志中的
`BUILD SUCCESSFUL` 与 `:app:assembleDebug` 只能证明 debug APK 在当前 VM 成功产出；
APK 本体属于构建产物，不提交到 Git，真实性由报告 SHA-256 与本地落盘文件交叉校验。

## 能力边界

UA 注入验证的是应用在 Android WebView UA、移动视口和触控能力声明下不会发生路由/
交互回归；底层仍是 Linux Chrome。相机权限系统弹窗、硬件麦克风、WebView provider
差异、返回键、低端机性能、安装升级和断网重启仍由 Android QA 按真机清单执行。
