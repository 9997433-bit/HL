Model slug: gpt-sol
# Round 14 Android 真机 QA 清单

标记：`ROUND14_H6`

本清单只能由实体 Android 设备执行。模拟器、WebView UA 注入、mobile Lighthouse、
截图模板和静态 Android 门禁都不是真机签核。未执行项保持 `PENDING`；有任一阻断项时
写 `FAIL / NO-GO`。禁止为了点亮门禁把待测项填写为 `PASS`。

## 1. 矩阵与冻结构建

同一 commit、同一组 APK 必须覆盖两档设备：

| 档位 | 硬要求 | 设备 / Android / API / WebView | 执行人 / 日期 |
|---|---|---|---|
| `low-end-old` | 仍受支持的 Android 8–10（API 26–29）低档旧机 | `PENDING` | `PENDING` |
| `modern` | Android 13+（API 33+）中高档机 | `PENDING` | `PENDING` |

每台设备记录厂商、型号、SoC、RAM、可用存储、系统/API、安全补丁、分辨率、DPI 和
当前 WebView provider。仓库证据仅保留 adb serial 的 SHA-256，不保存原始 serial。

| 冻结项 | 记录 |
|---|---|
| Git commit（40 位） | `PENDING` |
| 识字 APK `com.hongen.literacy` SHA-256 / versionName / versionCode | `PENDING` |
| 数学 APK `com.hongen.mathquest` SHA-256 / versionName / versionCode | `PENDING` |
| 构建 owner / 时间 | `PENDING` |

## 2. Harness 工作流

1. 完成双 App 构建；USB 调试设备须处于 `adb devices -l` 的 `device` 状态。
2. 每次只选一台设备时执行：

   ```bash
   npm run android:device:qa -- capture \
     --serial <adb-serial> \
     --install \
     --literacy-apk <literacy.apk> \
     --math-apk <math.apk>
   ```

3. Harness 会拒绝 `emulator-*`、`ro.kernel.qemu=1`、goldfish/ranchu、offline 和
   unauthorized 设备。无合格真机时必须输出 `SKIP` 并以 **2** 退出。
4. `capture` 只生成真实设备信息、双 App 安装/启动快照、截图、logcat、meminfo 及
   `qa-result.template.json`；其状态固定为 `CAPTURED/PENDING`，不是 PASS。
5. 人工走查后，将模板复制为同目录 `qa-result.json`。逐项填写 `PASS` 或 `FAIL`，
   每项至少引用一个该设备目录内、≥100 B 的证据文件；不得引用另一设备或仓库外文件。
6. 两档设备都完成后，在
   `.agent_workspace/evidence/r14/android/release-approval.json` 填写 QA Lead 与
   Release Manager 签名，再执行：

   ```bash
   npm run android:device:qa -- finalize
   ```

只有两档设备、同组 APK、24 项 `PASS`、零阻断缺陷、隐私复核和双签名全部成立时，
`finalize` 才会生成 `device-signoff.json`。还须另行形成 GO 决策文档；单个 JSON
不能代替发布责任人定案。

## 3. 安装与通用检查（每台设备 × 每个 App）

以下 ID 对应 `qa-result.json.checks`。两个 App 共用的项目应分别执行，可引用各自证据：

- [ ] `common.clean-install`：卸载/清数据后安装，首次冷启无白屏、闪退、开发地址或证书警告。
- [ ] `common.upgrade-install`：保留旧数据覆盖安装，学习进度和家长设置符合迁移预期。
- [ ] `common.cold-start`：连续 3 次强杀冷启；录像包含计时参照，首个可操作控件均出现。
- [ ] `common.background-resume`：前台→后台 30 秒→返回，页面、声音、计时和进度正确。
- [ ] `common.system-back`：系统返回键逐级返回；首页无死循环、黑屏或意外退出。
- [ ] `common.touch-and-gestures`：快速连点、拖拽、边缘滑动、长按无重复提交或卡死。
- [ ] `common.font-scale-130`：系统字体 100%/130%，关键操作不遮挡、不截断。
- [ ] `common.talkback`：控件名称、选中态、答题反馈和焦点顺序可用。
- [ ] `common.four-themes`：sunny、care、night、aurora 的关键页面可读。
- [ ] `common.audio-routing`：音量键、静音、扬声器和蓝牙耳机切换无爆音、叠播或失控。
- [ ] `common.offline-cold-start`：飞行模式强杀冷启，核心已安装内容不依赖开发服务器/CDN。
- [ ] `common.progress-recovery`：强杀、重启、覆盖安装后进度按产品约定保留。
- [ ] `common.offline-stability-30min`：飞行模式持续操作每个 App **30 分钟**，记录温升、掉帧和内存。
- [ ] `common.no-crash-anr-white-screen`：全过程 logcat 无 FATAL EXCEPTION、ANR、WebView crash 或持续白屏。

## 4. 识字 App 专项

- [ ] `literacy.learning-loop`：地图→字表→单字→描红→反馈闭环，听音正确/错误各一次。
- [ ] `literacy.ocr-permissions-and-camera`：相机允许、拒绝、永久拒绝均可恢复；拍照方向与低光提示正确。
- [ ] `literacy.follow-read-microphone`：麦克风允许/拒绝、离线/无语音能力均有明确结果或降级。
- [ ] `literacy.songs-and-books`：儿歌播放/暂停/切歌/后台恢复；绘本翻页、大资源状态正常。
- [ ] `literacy.games`：迷宫、配对、找不同、拼字各完成一局，庆祝层可关闭且不挡返回。

OCR 日常场景和 ASR 实时评分的专项数据分别进入对应 R14 OCR/ASR 证据目录；这里仍须
保留权限、相机、麦克风和 WebView 在真机上的交互录像。

## 5. 数学 App 专项

- [ ] `math.routes-and-back`：地图、每日任务、数量、算术、几何、规律、数独、应用题均可进出。
- [ ] `math.answer-interactions`：点击、拖拽、键盘输入各完成一题，错误可重试且不泄露答案。
- [ ] `math.manipulatives`：数形、分与合、竖式、七巧板在窄屏/高 DPI 下不溢出且拖拽跟手。
- [ ] `math.progress-and-wrongbook`：星级、进度、错题与推荐一致，重启后保留。
- [ ] `math.parent-controls`：家长解锁、统计、清除/重置有确认，儿童误触不能直接清数据。

## 6. 每项证据最低要求

每台设备目录至少包含：

```text
.agent_workspace/evidence/r14/android/<device-slug>/
  device-info.json
  capture.json
  qa-result.json
  literacy/
    install.txt
    launch.txt
    launch.png
    logcat.txt
    meminfo.txt
  math/
    install.txt
    launch.txt
    launch.png
    logcat.txt
    meminfo.txt
  <人工录像、截图或检查记录>
```

30 分钟走查须有起止时间、飞行模式状态、操作范围及过程录像/日志；只写“跑了 30 分钟”
不构成证据。截图、录像和日志入库前必须遮盖儿童姓名、相册、账号、通知、定位、设备
serial 和其他个人数据。原始敏感证据应进入批准的受控存储，仓库只保留脱敏副本。

## 7. 阻断和签名

下列任一项维持 `NO-GO`：崩溃/ANR、冷启白屏、核心离线失败、进度丢失、权限拒绝后
不可恢复、儿童隐私外发、关键操作 TalkBack 不可达、冻结构建哈希不一致、缺少一档设备、
缺证据或缺签名。非阻断缺陷也必须记录缺陷号、owner、复验日期和结论。

每台 `qa-result.json` 的 tester attestation 必须逐字为：

```text
I executed every listed check on this physical device and linked the supporting evidence.
```

`release-approval.json` 示例（示例不是已签名证据，不得原样提交）：

```json
{
  "marker": "ROUND14_H6",
  "verdict": "NO-GO",
  "qaLead": {
    "name": "",
    "signedAt": "",
    "attestation": "I reviewed both physical-device records, blocking defects, build hashes, and approve Android GO."
  },
  "releaseManager": {
    "name": "",
    "signedAt": "",
    "attestation": "I reviewed both physical-device records, blocking defects, build hashes, and approve Android GO."
  }
}
```

执行完成前，本清单所有项目均为 `PENDING`，Round 14 H6 不通过。
