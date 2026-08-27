Model slug: gpt-5.6-sol-xhigh-fast
# Android 双 App 真机走查清单

> 本清单记录人工真机终验步骤，不代表尚未执行的项目已经通过。每个设备、每个 App
> 必须逐项勾选并附证据；模拟器不能替代真机签核。
>
> Round 10 把 Cursor Cloud VM 可执行项与必须上真机的 owner 项分开记录；VM 结果不能
> 冒充真机签核。自动化证据归档于 `evidence/r10/`，真机证据由 Android QA 补入
> `evidence/r10/android/`。

## 1. 测试记录

| 字段 | 低档机 / 旧系统 | 中高档机 / 新系统 |
|---|---|---|
| 测试日期、测试人 | 未执行；Owner: Android QA（真机到位后记录） | 未执行；Owner: Android QA（真机到位后记录） |
| 品牌、型号 | Owner: Android QA；要求一台仍受支持的低档旧机 | Owner: Android QA；要求一台 Android 13+ 中高档机 |
| SoC / RAM / 可用存储 | Owner: Android QA；从系统页与 `adb shell` 双重记录 | Owner: Android QA；从系统页与 `adb shell` 双重记录 |
| Android 版本 / API | Owner: Android QA；目标 Android 8–10 | Owner: Android QA；目标 Android 13+ |
| Android System WebView 版本 | Owner: Android QA；从应用详情页记录完整版本 | Owner: Android QA；从应用详情页记录完整版本 |
| 屏幕尺寸、分辨率、DPI | Owner: Android QA；记录物理尺寸与 `wm size/density` | Owner: Android QA；记录物理尺寸与 `wm size/density` |
| App commit / APK SHA-256 | VM 测量 commit `5ea1a6f`；APK 由 Android Build 出包后冻结 SHA-256 | VM 测量 commit `5ea1a6f`；使用同一组冻结 APK |
| 识字 / 数学版本号 | 当前 package 版本均为 `0.1.0`；Owner: Release 冻结 Android versionName/code | 当前 package 版本均为 `0.1.0`；Owner: Release 冻结 Android versionName/code |

### 1.1 Cursor Cloud VM 能力与实测边界

VM：Linux x86_64、4 vCPU、15 GiB RAM；Node `v22.14.0`、npm `10.9.7`、
Google Chrome `148.0.7778.96`、OpenJDK `21.0.10`。仓库内双 App Gradle wrapper
存在，但 VM 无 `adb`、系统 Gradle、`ANDROID_HOME` / `ANDROID_SDK_ROOT`，也未连接
Android 设备。因此 Web 构建、Capacitor 同步、静态 Android 门禁与 desktop Lighthouse
可在 VM 实测；APK 编译、安装、WebView、权限、触控、音频、温升和内存只能由真机 owner
签核。

| VM 可执行项（2026-08-27 UTC） | 结果 | 证据 / 实测值 |
|---|---|---|
| `npm ci` | PASS（exit 0） | 安装 380 packages；Node/npm 版本见上 |
| `npm run build:all` | PASS（exit 0） | 双 App production build 完成 |
| `npm run sync:android` | PASS（exit 0） | 双 App `cap copy + cap sync` 完成 |
| `npm run check:android` | PASS（exit 0） | **26/26** 静态 Android 门禁通过 |
| `npm run test:lighthouse:desktop` | PASS（exit 0） | 识字、数学 P/A/BP 均 **100/100/100**；`formFactor=desktop`、`screenEmulation.mobile=false` |
| desktop 同轮 axe | PASS | 双 App 22/22 路由；识字 4 主题 × 24 状态；critical=0、serious=0 |
| APK / adb / 真机项 | BLOCKED（非产品失败） | VM 无 Android SDK、`adb` 和实体设备；Owner: Android Build / Android QA |

## 2. 出包与安装前置

- [x] VM / Owner: Performance：在 commit `5ea1a6f` 执行 `npm ci && npm run build:all`，均 exit 0。
- [x] VM / Owner: Performance：执行 `npm run sync:android && npm run check:android`，后者 **26/26**。
- [SKIP owner: Android Build — VM 无 Android SDK/Gradle，需真机出包机执行] Owner: Android Build：分别在 `apps/literacy-app/android`、`apps/math-app/android` 执行
      `./gradlew assembleDebug`，保存构建日志与 APK SHA-256。
- [SKIP owner: Android QA — VM 无 adb/实体设备] Owner: Android QA：用 `adb install -r <apk>` 安装；记录
      `adb shell dumpsys package <appId>` 版本信息。
- [SKIP owner: Android QA — VM 无 adb/实体设备] Owner: Android QA：先清除旧数据冷启一次，再保留数据覆盖安装一次；两种路径均不得白屏或崩溃。
- [SKIP owner: Android QA — VM 无 adb/实体设备] Owner: Android QA：安装后打开飞行模式冷启，确认壳层不依赖开发服务器或第三方 CDN。

App ID：识字 `com.hongen.literacy`；数学 `com.hongen.mathquest`。

## 3. 双 App 通用项（每台设备各执行一次）

> Owner: Android QA。以下均依赖实体 Android 设备；保持未勾选，直至两台设备分别附证。

| 检查项 | 识字 | 数学 | 证据 / 缺陷号 |
|---|:---:|:---:|---|
| 冷启动进入首页，无白屏、闪退、开发地址或证书警告 | [ ] | [ ] | |
| 首页首个可操作控件出现时间已录像并记录；连续冷启 3 次无明显退化 | [ ] | [ ] | |
| 前台 → 后台 30 秒 → 返回，页面、声音和进度状态正确 | [ ] | [ ] | |
| 系统返回键逐级返回；首页返回不产生死循环或黑屏 | [ ] | [ ] | |
| 快速连点、边缘滑动、长按不触发重复提交或卡死 | [ ] | [ ] | |
| 触控目标易点中；全面屏手势区、刘海和状态栏不遮挡操作 | [ ] | [ ] | |
| 系统字体 100% / 130% 下关键文案不截断，横竖屏切换不丢状态 | [ ] | [ ] | |
| TalkBack 可读出按钮名称、选中态、答题反馈；焦点顺序可用 | [ ] | [ ] | |
| sunny / care / night / aurora 四主题关键页面可读、无低对比文本 | [ ] | [ ] | |
| 音量键、静音模式、蓝牙耳机切换行为合理，无爆音或音频叠播 | [ ] | [ ] | |
| 弱网、断网、网络恢复各走一轮；核心离线内容可用且无无限加载 | [ ] | [ ] | |
| 强杀重启与覆盖安装后，学习进度和家长设置按预期保留 | [ ] | [ ] | |
| 连续操作 15 分钟，无持续升温、明显掉帧、ANR 或内存杀进程 | [ ] | [ ] | |

## 4. 识字 App 专项

> Owner: Literacy QA + Android QA；相机、麦克风、WebView 与触控项不得用桌面浏览器代签。

- [ ] 首页地图 → 字表 → 单字详情 → 描红 → 完成反馈闭环；新增高单元字也可进入。
- [ ] 听音识字正确/错误各答一次，语音、动画、震动不重叠，复习记录正确。
- [ ] 儿歌播放、暂停、切歌和歌词同步正常；锁屏/后台后不会继续异常叠播。
- [ ] 绘本书架、阅读翻页、成语与字源馆均能打开；大资源加载时有可理解的状态。
- [ ] OCR 首次授权、拒绝授权、永久拒绝三条路径都有可恢复 UI；选图识别可作为降级。
- [ ] OCR 拍照方向正确，低光/手写失败时有提示，不上传未明确授权的图片。
- [ ] 跟读在麦克风允许/拒绝、系统无语音能力和断网情况下均走到明确结果或降级。
- [ ] 游戏大厅至少完成迷宫、配对、找不同、拼字各一局，庆祝层可关闭且不挡返回。
- [ ] 飞行模式强杀后重启，已缓存课程、笔顺、绘本及 OCR 离线包按产品约定可用。

## 5. 数学 App 专项

> Owner: Math QA + Android QA；拖拽、高 DPI、系统返回键与进程恢复必须在实体设备执行。

- [ ] 学习地图、每日任务、数量、算术、几何、规律、数独、应用题路由均可进入和返回。
- [ ] 点击、拖拽、键盘输入类题目各完成一题；错误反馈后可重试且答案不会提前泄露。
- [ ] 数形演示、分与合、竖式、七巧板在窄屏和高 DPI 下不溢出，拖拽跟手。
- [ ] 连续完成一轮题目后，星级、进度、错题与推荐路径一致；重启后仍保留。
- [ ] 家长中心解锁、统计与清除/重置流程符合确认设计，儿童误触不能直接清数据。
- [ ] 快速切换不同题型 20 次，无旧题音效、计时器或动画残留。
- [ ] 飞行模式强杀后重启，已安装题库和进度链路可正常使用。

## 6. 性能与诊断留档

> Owner: Android Performance QA。desktop Lighthouse 只覆盖 Web 档，不替代以下设备档证据。

- [ ] 每台设备保存双 App 冷启动录像各 1 份，画面含系统时间或计时器。
- [ ] 保存 `adb logcat` 冷启动与 15 分钟走查片段；筛查 `FATAL EXCEPTION`、`ANR`、
      `chromium` 崩溃和 Capacitor bridge 错误。
- [ ] 保存 `adb shell dumpsys meminfo <appId>` 的冷启动后与 15 分钟后快照。
- [ ] 记录明显卡顿场景、复现步骤、设备/WebView 版本；不得只写“低端机卡”。
- [ ] 截图/录像中遮盖儿童姓名、相册、账号、通知和设备序列号。

建议归档：

```text
.agent_workspace/evidence/r10/android/
  <device-slug>/
    device-info.txt
    literacy-cold-start.mp4
    math-cold-start.mp4
    literacy-logcat.txt
    math-logcat.txt
    meminfo.txt
    checklist-result.md
```

## 7. 放行判定

- **阻断发布**：崩溃/ANR、冷启白屏、核心离线链路不可用、进度丢失、权限拒绝后不可恢复、
  儿童隐私数据外发、关键操作 TalkBack 不可达。
- **必须建单跟踪**：可稳定复现的明显卡顿、布局遮挡、音画错位、非核心页面降级异常。
- [SKIP owner: Android QA Lead — 真机签核待 Android QA 到位] Owner: Android QA Lead：两档真机 × 双 App 全部阻断项清零；遗留项已有缺陷号、责任人和复验结论。
- [SKIP owner: Release Manager — 真机签核后发布复核] Owner: Android QA Lead 完成测试签名；Owner: Release Manager 完成发布复核签名。
