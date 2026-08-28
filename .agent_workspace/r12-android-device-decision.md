Model slug: gpt-5.6-sol-xhigh-fast
# Round 12 Android 真机通道三选一定案

标记：`ROUND12_H6`

定案日期：2026-08-28 UTC

适用基线：`7c2e6e7` 及其后的 R12 集成提交

## 定案

三选一结论：**选择 3「显式发布决策」**。在实体设备或合格云真机完成双 App
签核之前，Android 生产发布状态固定为 **NO-GO / 阻断发布**；不得用 mobile
Lighthouse、桌面浏览器、模拟器或静态 Android 门禁代签。

这不是把真机项继续滚入下一轮。它把“没有真机证据”的后果变成不可绕过的发布
决策：Release Manager 只能在 Android QA Lead 完成下述证据与签名后把状态改为
GO。Web 侧开发、构建和内部预览可以继续，但 APK 不得进入生产商店、正式分发或
面向儿童的灰度渠道。

当前状态：

- `[SKIP owner: Android QA — 当前 Cursor Cloud VM 无实体设备、adb 与 Android SDK；
  此 SKIP 明确等于 Android 发布 NO-GO，不等于测试通过]`
- mobile Lighthouse 已在 `.agent_workspace/evidence/r12/` 留下识字、数学各一份
  `formFactor=mobile` 原始 JSON；分数为识字 `97/100/100`、数学 `95/100/100`
  （P/A/BP）。它们只证明 Web 仿真档达到自动门槛。
- 真机证据目录 `.agent_workspace/evidence/r12/android/` 当前没有签核材料，因此
  发布阻断保持生效。

## 三个候选的取舍

| 候选 | 本轮决定 | 依据 |
|---|---|---|
| 1. 自有实体设备 | 未选为当前已开通通道 | VM 没有已连接设备，也没有可核验的设备保管人、两档机型和 APK 安装记录。不能在文档里虚构“设备到位”。实体设备仍是解除 NO-GO 的首选执行方式。 |
| 2. 云真机 | 未选 | 当前没有已批准供应商、账号/额度、数据地域与儿童隐私评审，也没有验证相机、麦克风、蓝牙音频和 15 分钟温升是否可测。未经采购与隐私批准不能把第三方云设备写成已落地通道。 |
| 3. 显式发布决策 | **选定** | 仓库现有证据能确定 VM 边界，却不能完成触控、WebView、权限、音频、温升和进程恢复。最诚实且可执行的决策是把缺证直接绑定发布 NO-GO，并定义唯一解锁条件与 owner。 |

若团队之后先开通候选 1 或候选 2，不需要重写本决策的风险结论；只需按同一清单
补齐证据。云真机只有在 Android QA Lead 书面确认能覆盖对应检查项时才可替代其中
一台设备；相机、麦克风、蓝牙、温升等云端无法真实复现的项目仍必须由实体设备补测。

## 解锁 Android 发布的唯一条件

以下条件全部完成后，Android QA Lead 才能建议 GO，Release Manager 才能解除阻断：

1. **冻结构建** — Android Build 分别为 `com.hongen.literacy` 与
   `com.hongen.mathquest` 生成 APK/AAB，记录 commit、versionName/versionCode 和
   SHA-256；使用同一组冻结产物完成所有设备测试。
2. **两档设备** — Android QA 至少覆盖一台仍受支持的 Android 8–10 低档旧机，
   以及一台 Android 13+ 中高档新机；记录型号、SoC/RAM、存储、API、WebView、
   分辨率与 DPI。
3. **双 App 全清单** — 两台设备上的两个 App 均完成冷启/覆盖安装/飞行模式、
   前后台恢复、系统返回、触控、130% 字体、TalkBack、四主题、音频、弱网/离线、
   强杀恢复与 15 分钟稳定性；再完成识字与数学专项链路。
4. **性能诊断** — 每设备每 App 保存冷启动录像、logcat，以及冷启动后和
   15 分钟后的 meminfo；任何崩溃、ANR、白屏、核心离线失败、进度丢失、
   权限不可恢复、隐私外发或 TalkBack 不可达均维持 NO-GO。
5. **签名复核** — Android QA Lead 确认所有阻断项为零；非阻断遗留必须有缺陷号、
   owner 和复验结论。Release Manager 核对证据索引、构建哈希和 QA 签名后记录
   GO，不接受口头豁免。

上述口径直接引用
[`ANDROID-DEVICE-CHECKLIST.md`](./ANDROID-DEVICE-CHECKLIST.md)：

- [§1 测试记录](./ANDROID-DEVICE-CHECKLIST.md#1-测试记录) 定义两档设备与环境字段；
- [§2 出包与安装前置](./ANDROID-DEVICE-CHECKLIST.md#2-出包与安装前置) 定义冻结
  APK、安装、清数据、覆盖安装和飞行模式路径；
- [§3 双 App 通用项](./ANDROID-DEVICE-CHECKLIST.md#3-双-app-通用项)、
  [§4 识字专项](./ANDROID-DEVICE-CHECKLIST.md#4-识字-app-专项)、
  [§5 数学专项](./ANDROID-DEVICE-CHECKLIST.md#5-数学-app-专项) 是功能签核范围；
- [§6 性能与诊断留档](./ANDROID-DEVICE-CHECKLIST.md#6-性能与诊断留档) 要求录像、
  logcat、meminfo 和隐私遮盖；
- [§7 放行判定](./ANDROID-DEVICE-CHECKLIST.md#7-放行判定) 是最终阻断与签名准则。

## Owner 与证据落点

| 工作 | Accountable | Responsible | 交付物 |
|---|---|---|---|
| 冻结 Android 构建 | Release Manager | Android Build | 双 App APK/AAB、版本与 SHA-256 |
| 设备/云真机准备及隐私确认 | Android QA Lead | Android QA / Security | 设备信息或云供应商批准记录 |
| 双档设备 × 双 App 执行 | Android QA Lead | Android QA、Literacy QA、Math QA | checklist-result、录像、logcat、meminfo |
| 缺陷分级与复验 | Android QA Lead | 对应模块 owner | 缺陷号、修复提交、复验结论 |
| 最终 GO/NO-GO | Release Manager | Android QA Lead 提供签核 | 带日期、构建哈希和签名的发布决定 |

证据必须进入以下结构；截图和日志先遮盖儿童姓名、相册、账号、通知及设备序列号：

```text
.agent_workspace/evidence/r12/android/
  <device-slug>/
    device-info.txt
    literacy-cold-start.mp4
    math-cold-start.mp4
    literacy-logcat.txt
    math-logcat.txt
    meminfo.txt
    checklist-result.md
  release-decision.md
```

`release-decision.md` 必须引用两个设备目录、双 App 构建 SHA-256、未关闭缺陷和
Android QA Lead 签名。目录或任一签名缺失时，机器门禁即使全绿，Android 生产
发布仍为 NO-GO。

## 本轮可复核结果

- `node scripts/lighthouse-ci.mjs` 的归档轮：双 App build、首屏 bundle、mobile
  Lighthouse 与 axe 全通过；原始 JSON 在 `evidence/r12/`。
- 数学 route-budget 在 R11 `53d125b` 与 R12 `7c2e6e7` 独立构建均为 18/18，
  逐路由变化 `0 B`；详见 `r12-perf-budget-trend.md`。
- 上述 Web/构建结果不会改变本定案：在真机证据与签名补齐前，Android 发布
  **NO-GO**。
