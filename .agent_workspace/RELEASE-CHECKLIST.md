Model slug: gpt-5.6-sol
# Round 10 发布清单

> 发布候选：`1.0.0`（根 `package.json` 当前版本）
> 基线：`d89c455` · 发布分支：`cursor/r10-global-release-9f67`
> 原则：所有“阻断”项清零后才能公开发布；本清单不替代法律审查、应用商店审核或真机验收。

## 1. LICENSE 与第三方义务

| 检查项 | 当前状态 | 发布动作 |
|---|---|---|
| 项目根 `LICENSE` | ✅ | 原创程序代码与技术文档采用 MIT；课程内容与数据边界另见 `CONTENT_LICENSE.md` |
| 双 App 隐私政策 | ✅ | 两款 App 均注册 `/privacy`，并从全局页脚可达；识字页单列相机、麦克风与在线语音识别边界 |
| 第三方声明 | ✅ | `THIRD_PARTY_NOTICES.md` 随双 zip 分发；发布前复跑 `bash scripts/verify-resources.sh` |
| OpenMoji | ✅ | 保留界面署名及 `shared/assets/openmoji/LICENSE.txt`；衍生 SVG 继续 CC BY-SA 4.0 |
| 笔顺数据 | ✅ | 两处 `ARPHICPL.TXT` 随 APL 数据分发并保留裁剪/修改说明 |
| OCR 运行时与模型 | ✅ | 保留 Tesseract/Leptonica/`chi_sim` 的 Apache/BSD 声明与 NOTICE 信息 |
| GSAP | ✅，发布前复核 | 核对锁定版本对应的 Standard License，产品不得成为竞争性动画工具 |

## 2. 版本号与可追溯性

- [x] 公开版本采用 `1.0.0`；根/双 App `package.json`、lockfile与双 Android `versionName` 已统一。
- [ ] 以最终发布 commit 创建不可变 tag `v1.0.0`，记录 commit SHA、构建机 Node/npm 版本与 UTC 时间。
- [ ] 如版本改变，同步根/双 App `package.json`、lockfile、发行说明、zip 文件名或 manifest；禁止只改展示文案。
- [x] 2026-08-27 在本分支运行 `npm test`、`npm run test:round3` 与
  `npm run build:all`，三项退出码均为 0；`test:round3` 内含离线与完整 acceptance。
- [x] `npm run check:round9` 为 8/8；`check:round10` 的 H7（发布就绪）与
  H8（Round 9 不退化）均 PASS。其余 H1–H6 由对应 Round 10 功能分支集成后统一验收。
- [ ] 最终集成分支继续运行 `npm run sync:android`、`npm run check:android` 与完整
  `npm run check:round10` 8/8。
- [ ] 校验两个 zip 可解压、CRC 正常、单包低于 10 MiB，并在发行说明中登记字节数和 SHA256。

## 3. 对外声明草案

> 本项目提供两款本地优先的儿童学习应用：识字 App 与 MathQuest 数学 App。核心学习
> 进度默认保存在设备本地，无广告、无订阅、无需账号；家长可导入和导出进度。应用支持
> 离线学习、键盘操作、减少动态效果以及多主题显示。项目独立开发，与“洪恩”品牌及其
> 权利人不存在隶属、授权或合作关系；报告中的对标描述只用于公开功能比较，不包含或复制
> 对方受保护的角色、美术、音频和课程内容。第三方代码、模型、字形数据与图标分别依其
> 许可证使用，完整归属和再分发义务见随包提供的 `THIRD_PARTY_NOTICES.md`。

发布前必须由产品/法务复核产品名、截图、商标用语、儿童隐私声明和支持渠道。若启用笔顺
缺字网络回退，不能对外宣称“任何情况下零网络请求”；应表述为“内置课程正常使用无需
第三方请求，缺字回退可能访问声明中的数据源”。

## 4. Round 8 证据冻结

以下文件以基线内容冻结；任何重跑导致内容变化时都要更新 SHA，并说明工具版本和原因：

| 证据 | SHA256 |
|---|---|
| `evidence/r8/lighthouse-literacy-app.json` | `e64239191d47f3482b7c07f1451e915ef25d39f86a98ee91de700be36bd5984e` |
| `evidence/r8/lighthouse-math-app.json` | `d88ca304ed733df965b6f95225f56d0f5859ee39fd80cc39e547f0eb8607bbbd` |
| `evidence/r8/acceptance-output.txt` | `373d9fc5a1666bf85b606195a9861c503dab4b7c2d3ee40f3e2420dc8313f064` |

- [ ] 冻结 `.agent_workspace/acceptance-log-round8.md` 中的全链结果、OCR 35/35、
  Lighthouse 98/100/100 与 99/100/100、Android 26/26、zip 字节数和 SHA256。
- [ ] Round 9 Lighthouse 证据进入独立的 `evidence/r9/`，不得覆盖 Round 8 原始 JSON。
- [ ] 发布资产旁附 SHA256 清单；抽查下载后的 zip 哈希与清单一致。

## 5. SOTA C-6 Chrome 实测

- [x] Chrome 148.0.7778.96（Linux）访问双 App `/privacy`，桌面/移动视口共
  4/4 PASS，控制台错误 0、跨来源 HTTP(S) 请求 0。
- [x] 机读 JSON 与四张全页截图已冻结在
  [`evidence/r10/`](evidence/r10/README.md)。
- [ ] Edge、Firefox、macOS/iPadOS Safari 仍需在对应平台补齐；本分支不把未执行项
  标为通过。

## 6. 发布批准门

- **工程门**：`check:round8` 8/8 不退化；Round 9 计划正式发布时还须 `check:round9` 8/8。
- **内容门**：字源、剧情、儿歌、OCR、图谱抽查无版权混入、占位内容或明显模板错误。
- **设备门**：Web 离线冷启动、Android 至少一台真机的安装/升级/返回键/权限拒绝流程通过。
- **安全与隐私门**：无账号、广告、遥测或意外第三方请求；依赖漏洞与 CSP/权限声明已复核。
- **最终批准**：根 `LICENSE` 已落实；正式发布仍须完成工程、内容、产品/法务签名以及
  本清单中尚未勾选的 tag、真机与发行资产冻结项。

## 7. Round 11 商店与分发清单

> 规则核对日期：2026-08-27。商店政策会变化，提交当天须重查官方条款。以下未勾选项
> 都是待执行项，不因写入清单而视为通过。

### 7.1 当前阻断与渠道决策

- [ ] **阻断：升级 Android SDK。** 双 App 当前 `compileSdkVersion` /
  `targetSdkVersion` 均为 **34**。Google Play 自 **2026-08-31** 起要求普通手机/
  平板的新 App 和更新以 Android 16 / API 36 或以上为目标；正式提交前升级并回归
  边到边布局、预测返回、权限拒绝、离线缓存与低档真机。只升级 `compileSdk` 不算满足。
- [ ] **阻断：发布身份与商标复核。** 冻结公开产品名、开发者名、图标、包名与支持主体；
  `com.hongen.literacy` / `com.hongen.mathquest` 和“洪恩式”描述可能造成来源联想，
  必须经产品/法务确认。包名发布后很难迁移，不得先占位上线再随意更换。
- [ ] **阻断：签名与账号。** 由发布负责人创建 Play/App Store 账号、组织资料、税务/
  联系信息和双人保护的签名密钥；密钥、服务账号 JSON、证书和 provisioning profile
  不进入 Git 仓库或反馈附件。记录恢复负责人和轮换流程。
- [ ] **App Store 当前不可提交。** 仓库只有 Capacitor Android 工程，没有 iOS 工程、
  Xcode archive、Bundle ID/entitlements、签名与 iPhone/iPad 真机证据。若本轮只发
  PWA/Android，应明确写“App Store 不在本次发行范围”，不得用 Web zip 冒充 iOS 产物。
- [ ] 冻结本次渠道：`[Web/PWA] [GitHub/自托管 zip] [Google Play 内测] [Google Play 正式] [App Store]`；
  每个渠道指定负责人、回滚方式、支持 URL 和最低系统版本。

官方依据：[Google Play target API 要求](https://support.google.com/googleplay/android-developer/answer/11926878)；
[Google Play Families 政策](https://support.google.com/googleplay/android-developer/answer/17122218)；
[Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)。

### 7.2 构建、版本、签名与可追溯

- [ ] 根/双 App `package.json`、Android `versionName`、发行说明和隐私页版本一致；
  每次 Play 上传递增且不复用 `versionCode`，iOS 未来建立独立递增 build number。
- [ ] 从干净 commit 运行 `npm ci`、`npm test`、`npm run check:round11`、
  `npm run build:all`、`npm run sync:android`、`npm run check:android`，归档 Node/npm/
  JDK/Gradle/Android SDK 版本与完整输出。
- [ ] 生成 **release AAB**（Play）和渠道所需 APK；确认不是 debug 签名、无调试 WebView、
  无明文流量、无测试菜单、无开发服务器地址。Play App Signing 的上传钥匙与应用签名
  钥匙责任分开记录。
- [ ] 对 zip/AAB/APK/未来 IPA 分别记录文件名、字节数、SHA256、commit、签名证书指纹、
  构建 UTC 时间；下载后再次校验，不只校验构建机本地副本。
- [ ] 生成 SBOM/依赖清单并跑依赖漏洞检查；将 `LICENSE`、`CONTENT_LICENSE.md`、
  `THIRD_PARTY_NOTICES.md` 和资产/模型许可证随适用产物分发。
- [ ] 执行“新装、覆盖升级、卸载重装、磁盘不足、断网冷启、系统返回、旋转/后台恢复”
  矩阵；验证升级不损坏本地学习记录，卸载会删除本机数据的提示与实际一致。

### 7.3 商店元数据与素材

- [ ] 每款 App 单独准备名称、短/长描述、分类、关键词、支持 URL、隐私政策 **公开 HTTPS
  URL**、版权主体、版本说明和审核联系信息；页面必须无需登录且与包内 `/privacy` 一致。
- [ ] 截图覆盖商店要求的手机/平板尺寸，来自最终候选包；不得展示竞品商标、未经授权角色、
  虚构评分、未实现功能、儿童姓名/头像或调试数据。宣传视频的音乐、字体、配音也纳入授权表。
- [ ] 填写内容分级/IARC 问卷，答案与儿童学习、相机、麦克风、网络回退和无广告现状一致；
  不通过模糊年龄描述规避 Families/Kids 规则。
- [ ] 决定 Apple Kids Category 年龄段（5 岁及以下、6–8、9–11）或不进入该分类；
  若文案/截图使用 “For Kids/儿童专用” 等暗示，必须与所选分类及 Guideline 2.3.8 一致。
- [ ] 检查图标、启动图、应用内名称、状态栏颜色、本地化和无障碍标签；小屏、平板、
  深色/高对比/减少动态及系统字体放大均走查。
- [ ] 审核说明向审核员给出家长门进入方法、相机/OCR、麦克风/跟读、离线模式、
  清空/导出和没有账号/IAP 的事实；需要测试凭据时只提供专用最小权限账号。

### 7.4 儿童隐私、权限与 Data Safety

- [ ] 以最终 **AAB/APK 的合并 Manifest、网络抓包和 SDK 清单**填写 Play Data safety/
  Families 声明及 Apple App Privacy，不凭产品印象填写“未收集数据”。托管下载日志、
  崩溃 SDK、WebView、SpeechRecognition 和 CDN 回退都要判定是否构成收集/共享。
- [ ] 当前承诺保持无广告、无第三方分析、无遥测、无需账号；若构建依赖带入采集能力，
  必须移除或先更新同意、隐私政策与商店申报，不能静默上线。
- [ ] 识字 App 仅在用户主动进入对应功能时请求相机/麦克风，系统权限说明明确用途；
  拒绝、永久拒绝、撤销和仅一次授权都有字幕/手动输入/家长读等可用降级。数学 App
  不应出现相机或麦克风权限。
- [ ] 在线 `SpeechRecognition` 默认关闭并位于家长控制后；实机抓包确认离线 OCR、
  录音回放和本地评测不上传图片/声音。课程外笔顺 CDN 回退与隐私页声明一致。
- [ ] 家长中心的外链、导出、清空、权限请求与未来购买均由有效家长门保护；Apple Kids
  Category 的家长门是成人级任务，但**不能**把它误当作法律意义的家长同意。
- [ ] 提供数据删除路径和支持联系人。虽然当前无服务端账号/副本，也要明确“清除站点数据/
  卸载会删除本机记录”和导出备份方式；收到隐私请求时不得反向索要儿童敏感信息。
- [ ] 若启用 TTS 模型或分批录音，按
  [`r11-tts-evaluation.md`](r11-tts-evaluation.md) 冻结引擎/模型/演播授权、许可证和 SHA；
  不上传儿童试用录音训练模型，模型下载行为同步更新 Data safety 与隐私页。

### 7.5 质量、兼容与发布节奏

- [ ] 真机至少覆盖 API 最低档、主流中档和 Android 16/API 36；记录安装、升级、
  首次启动、低内存恢复、音频并发、相机/麦克风拒绝、TalkBack 和完全离线结果。
- [ ] Web/PWA 在 Chrome、Edge、Firefox、Safari 的当前支持版本验证安装、Service Worker
  更新、缓存迁移与子路径部署；服务端配置正确 MIME、HTTPS、缓存头和 SPA/相对路径。
- [ ] 先走内部/封闭测试轨道，小比例分阶段发布；每个阶段冻结等待窗口、P0/P1 阈值、
  崩溃/ANR 来源和人工反馈负责人。没有合规的儿童遥测时，以商店技术指标、主持试用和
  家长主动反馈为证据，不能为追指标临时接 SDK。
- [ ] 按 [`FEEDBACK-LOOP.md`](FEEDBACK-LOOP.md) 完成 T0–T3，P0/P1 未关闭数为 0；
  反馈附件去标识，儿童原始录音/照片不进入 issue、仓库或公开商店回复。
- [ ] 准备回滚：保留上一稳定包与签名材料；远端下架不能撤回已安装版本，因此严重隐私/
  数据问题要有禁用受影响入口或快速修复版策略。数据库/本地存储迁移必须向前兼容，
  不以降版覆盖作为唯一回滚。

### 7.6 发布签字

| 角色 | 核对范围 | 姓名 / 日期 / 结论 |
|---|---|---|
| 工程 | 干净构建、签名、API 36、门禁、升级/回滚 | `[待填]` |
| QA/设备 | 浏览器/真机矩阵、离线、权限、无障碍 | `[待填]` |
| 内容/普通话审校 | 课程、截图、TTS/录音准确与权利来源 | `[待填]` |
| 隐私/安全 | Data safety、Kids/Families、抓包、删除路径 | `[待填]` |
| 产品/法务 | 名称/商标、年龄段、商店声明、最终批准 | `[待填]` |

只有五方结论均为“通过”、所有阻断项清零、最终产物 SHA 与被测产物一致时，才可把候选
提升为公开发布。内测通过不自动等于 Google Play 或 App Store 审核通过。
