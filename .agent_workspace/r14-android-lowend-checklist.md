Model slug: gpt-sol
# Round 14-3 低档 Android 真机 30 分钟回归清单

标记：`ROUND14_H6`　档位：`low-end-old`　Owner：Android QA

## 当前结论

本轮没有连接实体 Android 设备，以下项目均为 **SKIP / 未执行**，不构成 PASS 或
`device-signoff.json`。当前台账见
[`evidence/r14/android/lowend-skip.json`](evidence/r14/android/lowend-skip.json)。

本清单只适用于仍受支持的 Android 8–10（API 26–29）实体低档旧机。模拟器、桌面
Chrome、mobile Lighthouse、WebView UA 注入和 R13 `simulated:true` 证据均不能代签。
以下 30 分钟流程须对识字、数学两个 App **分别完整执行一次**（每 App 30 分钟）。

## 1. 开始计时前

- [ ] 冻结同一 commit 及双 App APK，记录 SHA-256、versionName、versionCode。
- [ ] 设备在 `adb devices -l` 中为 `device`；记录型号、SoC、RAM、可用存储、Android/API、
      安全补丁、分辨率、DPI、WebView provider。仓库只保留 adb serial 的 SHA-256。
- [ ] 电量 ≥30%，拔掉充电线并静置至温度稳定；关闭省电模式，记录初始电量和温度。
- [ ] 先联网打开一次双方明确要求预缓存的内容，再启用飞行模式；确认 Wi-Fi 和移动数据均断开。
- [ ] 清空 logcat，然后用 harness 采集安装、启动、截图和基线 meminfo：

  ```bash
  npm run android:device:qa -- capture \
    --serial <adb-serial> \
    --install \
    --literacy-apk <literacy.apk> \
    --math-apk <math.apk>
  ```

Harness 输出必须是该实体设备的 `CAPTURED/PENDING`；exit 2 是 SKIP，不是通过。把生成的
`qa-result.template.json` 复制为 `qa-result.json` 之前，先完成下面的人工步骤并附证。

## 2. 每 App 30 分钟离线流程

识字使用 `com.hongen.literacy`，数学使用 `com.hongen.mathquest`。每个 App 单独清空
logcat、记录 UTC 起止时间，并在 0、15、30 分钟保存 `dumpsys meminfo <app-id>` 与
`dumpsys battery`。全程保持飞行模式并录屏；系统不支持的 thermal 命令应在记录中明确
写 `unsupported`，不可留空或补造数值。

| 时间 | 操作 | 必须观察并记录 |
|---|---|---|
| 00:00–03:00 | 强杀后冷启动；连续按系统返回再重新进入 | 首个可操作控件时间；无白屏、闪退、开发地址、证书警告或返回死循环 |
| 03:00–10:00 | 完成该 App 的核心学习闭环 | 识字：地图→单字→描红→反馈；数学：地图→点击/拖拽/输入题→反馈；离线资源不无限加载 |
| 10:00–17:00 | 快速连点、边缘滑动、长按、前后台切换 30 秒、音量/静音切换 | 无重复提交、卡死、音频叠播、计时器残留或进度回退；记录可复现卡顿 |
| 17:00–23:00 | 强杀进程后离线重启，继续刚才内容；再切换至少 5 个页面/题型 | 进度和家长设置按约定恢复；无网络时有可理解的降级，不出现持续白屏 |
| 23:00–28:00 | 执行 App 专项压力路径 | 识字：儿歌/绘本/游戏及 OCR、麦克风拒绝后的降级；数学：数量、算术、几何、规律、数独、应用题快速进出 |
| 28:00–30:00 | 回到首页，再做一次后台→前台与系统返回；保持操作到计时结束 | 无 crash、ANR、WebView crash、明显热降频或内存杀进程；保存末次截图、温度、电量、meminfo、logcat |

完成识字 30 分钟后让设备温度恢复到接近初始值，再以同样步骤执行数学 30 分钟。不得把
两个 App 各 15 分钟合并写成“双 App 30 分钟”。

## 3. 证据与判定

每 App 至少保留下列脱敏证据：起止 UTC 时间、飞行模式状态、过程录像、0/15/30 分钟
meminfo、电量/温度快照、末次截图、完整 logcat、操作范围及缺陷号。筛查：

```text
FATAL EXCEPTION
ANR
chromium / WebView crash
Capacitor bridge error
low memory kill
```

- **PASS 候选**：两个 App 均各满 30 分钟，全部要求有证据，且无 crash、ANR、持续白屏、
  核心离线失败、进度丢失、权限拒绝后不可恢复或儿童隐私外发。
- **FAIL / NO-GO**：出现任一上述阻断项；记录复现步骤、时间戳、缺陷号与 owner。
- **SKIP / PENDING**：没有合格实体设备、设备未授权/offline、只有模拟器、任一 App 未跑满
  30 分钟、缺证据或未完成隐私复核。SKIP 不得改写为 PASS。

证据目录：

```text
.agent_workspace/evidence/r14/android/<device-slug>/
  capture.json
  device-info.json
  qa-result.json
  literacy/<30min evidence>
  math/<30min evidence>
```

入库前遮盖儿童姓名、相册、账号、通知、定位和原始 adb serial。完成本清单只满足低档机
这一腿；H6 最终签核仍须同一组 APK 的 Android 13+ `modern` 真机、完整矩阵项、隐私复核、
QA Lead 与 Release Manager 双签名，再执行 `npm run android:device:qa -- finalize`。
