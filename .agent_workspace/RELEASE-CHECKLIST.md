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
- [ ] 从干净 checkout 按顺序运行 `npm test`、`npm run test:round3`、`npm run build:all`、`npm run sync:android`、`npm run check:android`、`npm run check:round8`。
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
