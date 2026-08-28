Model slug: gpt-sol
# Round 14 Android 真机矩阵工程记录

标记：`ROUND14_H6`

分支：`cursor/r14-android-device-matrix-9f67`

## 当前结论

本轮交付的是真机 QA harness、证据约束与人工清单，不是真机签核。当前仓库没有
`.agent_workspace/evidence/r14/android/device-signoff.json`，也没有两档实体设备的
执行记录，因此发布结论保持 **NO-GO**，Round 14 H6 保持预期红灯。

模拟器、R13 的 `simulated:true` 结果、mobile Lighthouse、桌面 Chrome 和
`check:android` 都不等价模拟以外的真机证据，不能复制到 `evidence/r14/android/`
冒充 `onDevice:true`。本分支不会手写 `pass:true` 的签核 JSON，也不会把未执行的清单
预先勾选。

## 交付面

| 交付 | 作用 | 是否构成 H6 PASS |
|---|---|---|
| `scripts/android-device-matrix.mjs` | 枚举并排除模拟器；采集设备、APK、启动、截图、logcat、meminfo；校验最终矩阵 | 否 |
| `npm run android:device:qa -- capture` | 真机在线时生成单设备 `CAPTURED/PENDING` 证据和人工结果模板 | 否 |
| `npm run android:device:qa -- finalize` | 校验两档设备、同组构建、逐项证据、隐私复核与双签名 | 仅校验全过后生成 signoff |
| `ANDROID-DEVICE-QA-CHECKLIST.md` | 两设备 × 双 App × 离线 30 分钟的人工执行规范 | 否 |

Harness 的退出码具有固定语义：

- `0`：采集成功，或完整签核校验成功；采集成功只表示 `CAPTURED`，不是 QA PASS。
- `1`：adb 操作、安装/启动、证据绑定、矩阵、检查项或签名校验失败。
- `2`：`SKIP`；adb 不存在、没有设备、设备未授权/offline，或只有模拟器。此时不创建
  `device-signoff.json`，输出会明确说明未产生 PASS。

## 反伪造约束

真实设备候选必须在 `adb devices -l` 中为 `device`，且不得是 `emulator-*`，不得有
`ro.kernel.qemu=1` / `ro.boot.qemu=1`，硬件不得为 goldfish/ranchu。仓库不保存原始
adb serial，只保存 SHA-256；设备信息保存 `onDevice:true`、`simulated:false` 和
QEMU 探测结果。

`capture.json` 固定写入 `status: CAPTURED`、`qaVerdict: PENDING`、`pass:false`。
最终人工结果必须与 capture 文件哈希、40 位 commit、识字 APK SHA-256 和数学 APK
SHA-256 绑定。每个清单项都须为 `PASS` 并引用同一设备目录内至少 100 B 的证据；
任一阻断缺陷、缺证据、缺少隐私复核或缺少 tester attestation 都会使 finalize 失败。

最终矩阵必须包含两个不同 serial 哈希：

1. `low-end-old`：Android 8–10 / API 26–29；
2. `modern`：Android 13+ / API 33+。

两台设备必须测试同一 commit 和同一组双 App APK。QA Lead 与 Release Manager 还须在
`release-approval.json` 中分别实名、记录 ISO 时间并使用清单规定的精确 attestation。
只有全部验证成立，脚本才生成
`.agent_workspace/evidence/r14/android/device-signoff.json`，其中才允许
`pass:true`。之后仍要单独形成带 `ROUND14_H6` 的 GO 决策文档，机器 signoff 不能替代
发布责任人。

## 证据目录

真机运行时由 harness 创建：

```text
.agent_workspace/evidence/r14/android/
  <manufacturer-model-serialhash12>/
    device-info.json
    capture.json
    qa-result.template.json
    qa-result.json                 # 仅人工执行后创建
    literacy/{install,launch,logcat,meminfo}.txt
    literacy/launch.png
    math/{install,launch,logcat,meminfo}.txt
    math/launch.png
    <人工走查证据>
  release-approval.json            # 仅完成两档复核后创建
  device-signoff.json              # 仅 finalize 全绿后生成
```

截图、录像和日志入库前须完成儿童信息、相册、账号、通知、定位和设备 serial 脱敏。
Harness 会从文本自动遮盖当前 adb serial，但这不能替代人工隐私复核。

## 本分支验证记录

实现提交后执行以下检查并回填，不以文档预判代替命令结果：

| 命令 | 预期 | 实测 |
|---|---|---|
| `node --check scripts/android-device-matrix.mjs` | 脚本语法有效 | `PENDING` |
| `npm run android:device:qa -- --help` | 用法与退出码可见，exit 0 | `PENDING` |
| `npm run android:device:qa` | 无真机环境 exit 2 `SKIP`，不生成 signoff | `PENDING` |
| `npm run check:round14 -- --json` | H6 仍 FAIL，不把脚手架当签核 | `PENDING` |

## 解锁条件

Android QA 按清单在两档真机上完成双 App 安装、功能、权限、无障碍、离线冷启和每 App
30 分钟飞行模式稳定性；所有阻断项清零，非阻断项有缺陷号和复验结论；QA Lead 与
Release Manager 完成证据复核与 GO 签名。缺少其中任何一项，都必须继续报告
`SKIP`、`PENDING`、`FAIL` 或 `NO-GO`，禁止报告 PASS。
