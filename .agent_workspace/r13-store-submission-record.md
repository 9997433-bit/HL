Model slug: gpt-5.6-sol-xhigh-fast
# Round 13 · Google Play 内测轨道提交记录

> 记录日期（UTC）：2026-08-28
> 记录分支：`cursor/r13-store-submit-9f67`
> 输入基线 SHA：`7bc74c75ffe0a9f635fb54f4792a0b5680c4dcca`
> 门禁标记：`ROUND13_H7`
> 渠道：Google Play Console → Internal testing（内部测试）
> 操作结论：**BLOCKED / 未登录、未上传、未创建或发布内测 release**

## 1. 结论与证据边界

本环境没有获得经授权的 Google Play Console 开发者账号、双因素认证会话、目标应用访问权、Play App Signing 配置或生产上传密钥，因此不能执行真实 Console 写操作。本轮按无账号路径完成可复现的 dry-run、提交检查清单和解阻条件；没有把 debug APK、Android 模拟报告或文档探针通过冒充为商店提交成功。

`check:round13` 的 H7 文件探针用于确认本记录包含 Play Console/内测轨道、版本/SHA 和 `ROUND13_H7` 等可执行信息。它通过时只表示“提交记录实体符合探针口径”，**不表示 Google Play 已接收构建，也不表示应用通过审核或已向测试者可用**。真实提交状态仍为 BLOCKED。

## 2. 候选盘点

| App | applicationId | 仓库版本 | Android 配置 | 可上传 AAB | 当前证据 |
|---|---|---:|---|---|---|
| 快乐识字 | `com.hongen.literacy` | `1.0.0` / `versionCode 1` | min 22、target/compile 34 | **无**；未配置生产签名 | 仅 VM 构建的 debug APK，SHA256 `0b0b4587326681da3fc1b80515a433afe17983e57d5a60388a510eb233c35af9` |
| MathQuest | `com.hongen.mathquest` | `1.0.0` / `versionCode 1` | min 22、target/compile 34 | **无**；未配置生产签名 | 仅 VM 构建的 debug APK，SHA256 `1e3a341cac52241b1ad1825959084f6067b163e94b337b8199032f8d4c8c9da3` |

上述 APK 哈希来自 `.agent_workspace/evidence/r13/android-sim/report.json`，报告明确标记 `simulated: true`。它可证明基线上的双 App 构建与 WebView smoke，不是 release AAB、真机签核或 Play 上传回执。仓库中的 `versionCode 1` 也只是本地值；必须先在 Console 查询已占用的最高版本号，再使用更大的唯一值，不能假定 `1` 可上传。

现有发布清单还记录了包名/“洪恩”关联表达的产品法务复核、儿童政策申报、生产签名、真机矩阵等阻断。项目当前 target SDK 34；正式上传前应按提交当日 Play 政策与 Console 提示完成目标 API 升级和回归，不能用临近政策切换的时间差绕过兼容验证。

## 3. Play Console 内测 dry-run 步骤

以下步骤是提交负责人拿到账号后逐项执行的运行手册。所有敏感密钥只放在受控密钥库或构建机用户级配置中，不写入仓库、命令历史、截图或本记录。

### A. 冻结与离线构建

1. 为两款 App 分别指定发布负责人、隐私负责人、QA 和回退负责人，确认产品名、开发者主体和 applicationId 获准使用。
2. 从最终集成 commit 建立干净工作区，记录完整 commit SHA、Node/npm、JDK、Gradle、Android SDK 与构建 UTC 时间；确认 `git status` 为空。
3. 在 Console 查询每个包已使用的最大 `versionCode`，分别设置更大的唯一值；同步 `versionName`、发行说明和版本清单。
4. 将 target/compile SDK 升至提交当日政策要求，完成边到边布局、预测返回、权限拒绝、离线缓存和低端设备回归。
5. 执行 `npm ci`、完整测试、`npm run build:all`、`npm run sync:android`、`npm run check:android` 和 `npm run check:round13`；只有 Round 13 全部门禁及前序回归通过才进入上传准备。
6. 使用受控上传证书构建两个 **release AAB**。验证 AAB 不是 debug 签名、WebView 不可调试、无开发服务器地址，并记录文件名、字节数、SHA256、证书 SHA-256 指纹和构建 SHA。
7. 用 `bundletool` 检查 manifest 与设备包生成，至少在受支持的低/中/高 API 真机完成新装、覆盖升级、断网冷启、返回键、旋转/后台恢复、相机/麦克风拒绝和本地进度保留。

### B. Console 准备

1. 以最小权限的授权账号登录 Play Console，双因素认证完成后选择正确开发者主体；两款 App 分开操作，禁止交叉上传。
2. 若应用尚不存在，只有在产品/法务批准名称、默认语言、App/游戏类型、免费/付费模式和包名后才创建条目；记录 Console app ID。
3. 完成并复核 App access、Ads、Content rating、Target audience and content、News、Data safety、Government apps、Financial features 等 Console 当前要求的 App content 项。
4. 儿童教育定位按 Families 要求填写。识字 App 的相机/OCR、麦克风/跟读、SpeechRecognition 降级和课程外网络回退，必须与最终 AAB 合并 Manifest、网络抓包、公开隐私政策一致；数学 App 不应申报并携带无关相机/麦克风权限。
5. 填入无需登录即可访问的 HTTPS 隐私政策和支持 URL，上传从最终候选包采集的手机/平板截图、图标、功能图、短/长描述与版本说明；不得出现儿童个人信息、未实现能力或未经批准的品牌表达。
6. 开启或确认 Play App Signing，核对上传证书指纹与受控记录一致；若指纹不符立即停止，不尝试以未知密钥覆盖。

### C. 创建 Internal testing release

1. 进入 **Testing → Internal testing**，建立本轮测试者 email list 或 Google Group，记录名单 owner；不得把儿童邮箱或公开链接写入仓库。
2. 选择 **Create new release**，上传与候选 SHA 一一对应的 AAB。等待 Play 处理完成，逐项处理错误、警告、权限变化和设备覆盖提示。
3. 填写唯一 release name 和可验证的 release notes；再次核对 package、versionCode、versionName、AAB SHA256、上传证书指纹及目标轨道。
4. 执行 Review release。若 P0/P1 未关闭、政策表单不完整、pre-launch report 有阻断、哈希不符或 reviewer 未签字，保存草稿并停止。
5. 只有双人复核通过才选择 **Start rollout to Internal testing**。记录 Console 显示的提交 UTC 时间、release/versionCode、状态、处理结果和可审计的 release 页面引用。
6. 由不参与上传的 QA 账号打开 opt-in 链接，在至少一台未安装真机冷安装；再从上一稳定版覆盖升级，验证离线、进度保留、权限拒绝和反馈入口。

### D. 停发与回退

1. AAB 尚未 rollout：丢弃/停用草稿，修复后以新的更高 `versionCode` 重建；禁止覆盖同一个 Play 版本号。
2. 已进入内部测试：停止扩大测试者范围，保留证据并按 P0/P1 流程分诊；远端停发不能删除已安装副本。
3. 需要修复时上传前向兼容的新版本；本地数据迁移不可依赖降版覆盖。隐私或数据风险同时关闭受影响入口并通知隐私负责人。
4. 回退后由另一名 QA 在原故障设备复验，通过后才关闭工单。

## 4. 本轮检查清单

### 已核实的仓库事实

- [x] 已冻结输入 SHA、分支、双 applicationId、本地版本号和 Android SDK 配置。
- [x] 已核对 R13 Android 模拟证据及其双 APK SHA256，并明确其 `simulated: true` 边界。
- [x] 已确认仓库没有可声明为本轮上传成功的 release AAB 或 Play Console 回执。
- [x] 已写明 Internal testing 的上传、复核、安装验证和回退步骤。
- [x] 已写明账号不可用时的 BLOCKED 决策和逐项 unblock 条件。

### 真实提交前必须完成

- [ ] 授权 Play Console 账号、开发者主体、双因素认证和两款 App 的 Release 权限可用。
- [ ] 产品/法务批准公开名称、开发者身份、`com.hongen.*` 包名与商标表达。
- [ ] Play App Signing 已建立，上传证书指纹由两人核对；密钥恢复 owner 已登记。
- [ ] 两个 release AAB 从最终 SHA 生成、正确签名，版本号高于 Console 现值，哈希与产物清单一致。
- [ ] target/compile SDK 与提交日政策一致；完整测试、R13 8/8、真机矩阵和安全/许可检查通过。
- [ ] 公开隐私政策、支持页、Data safety、Families/目标受众、内容分级、权限说明和素材由责任人签字。
- [ ] 内部测试者名单、反馈 owner、P0/P1 SLA、上一稳定包和回退步骤已就绪。
- [ ] Console Review release 无阻断，双人确认后执行 Start rollout to Internal testing。
- [ ] QA 从 opt-in 链接完成冷安装与覆盖升级，并保存不含账号/儿童信息的提交回执。

## 5. BLOCKED 决策与 unblock 条件

当前决策：**NO-GO / BLOCKED**。直接阻断是本运行没有获授权的 Play Console 账号或会话，因此既不能确认 app 条目是否存在和线上最高 versionCode，也不能配置 Play App Signing、上传 AAB 或启动内部测试。即使补齐账号，也必须同时清除以下条件，不能把“能登录”当成“允许发布”：

1. **身份与权限**：提供由发布负责人控制、启用 MFA 的 Play Console 访问；两款 App 至少授予创建内部测试 release 所需的最小权限，并指定账号恢复和审计 owner。
2. **应用身份**：产品/法务书面确认开发者主体、应用名称、包名、商标和儿童定位；确认是创建新条目还是使用既有条目。
3. **候选产物**：在最终 SHA 上生成已签名 release AAB；versionCode 高于 Console 现值；记录字节数、SHA256、上传证书指纹和构建环境，且与实际上传文件完全一致。
4. **政策与隐私**：完成目标 API、Data safety、Families/目标受众、内容分级、权限、隐私/支持 URL 和商店素材复核，Console 无未处理的必填项。
5. **质量与回退**：`check:round13` 达到 8/8，真机新装/升级/离线/权限矩阵通过，P0/P1 为 0，测试者与回退负责人到位。
6. **双人放行**：上传者和独立复核者共同确认 app、轨道、版本、哈希和声明后，才可点击 Start rollout。

六类条件全部满足后，状态才能从 BLOCKED 改为 READY；只有 Console 接收 release 且 QA 通过 opt-in 安装，才能记为 SUBMITTED/VERIFIED。

## 6. 真实提交回执模板（待解阻后填写）

| 字段 | 快乐识字 | MathQuest |
|---|---|---|
| 最终 commit SHA | `[待填]` | `[待填]` |
| Console app ID | `[待填]` | `[待填]` |
| versionName / versionCode | `[待填]` | `[待填]` |
| AAB 文件名 / bytes / SHA256 | `[待填]` | `[待填]` |
| 上传证书 SHA-256 指纹 | `[受控记录引用，不粘贴密钥]` | `[受控记录引用，不粘贴密钥]` |
| 轨道 / release name | `Internal testing / [待填]` | `Internal testing / [待填]` |
| Console 接收时间（UTC）/ 状态 | `[待填]` | `[待填]` |
| Review / rollout 双人签字 | `[待填]` | `[待填]` |
| opt-in 冷安装 / 覆盖升级 | `[待填]` | `[待填]` |
| 回退负责人 / 上一稳定版本 | `[待填]` | `[待填]` |

未填写的模板字段不是证据。后续若发生真实提交，应追加不可变回执和脱敏截图/日志引用，不回写虚构值覆盖本次 BLOCKED 结论。
