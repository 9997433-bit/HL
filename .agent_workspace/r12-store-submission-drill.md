Model slug: gpt-5.6-sol-xhigh-fast
# Round 12 商店提交演练 checklist

> 演练日期：2026-08-28  
> App：快乐识字（Android/PWA；iOS 清单预演）  
> 版本：`1.0.0`，Android `versionCode 1`  
> applicationId：`com.hongen.literacy`  
> 输入集成线 SHA：`7c2e6e7`  
> H7 候选提交 SHA：`待首次提交后回填`  
> 门禁：`ROUND12_H7`

本次只做“材料、构建、内测轨道、回退”桌面演练，不使用生产签名、不登录 Google Play Console 或 App Store Connect，也不代表已经送审。演练目的是让正式发布负责人拿到一张可以逐项执行和签名的清单，并提前暴露 TTS 合规、版本号、包体与反馈响应的阻断项。

## 1. 冻结与责任

- [x] 冻结日期、版本、applicationId 与输入 SHA。
- [x] `package.json`、`capacitor.config.json`、Android `build.gradle` 的版本信息一致（`1.0.0` / code `1`）。
- [x] H7 试点资产有稳定 ID、来源 revision、逐文件 SHA256 和 Apache-2.0 模型卡链接。
- [x] 明确模型权重和推理运行时不进入安装包；只有约 33 KB Ogg/Opus 进入 `public`。
- [ ] 发布负责人：`[姓名]`；隐私负责人：`[姓名]`；内容/普通话审校：`[姓名]`。
- [ ] 正式候选冻结后回填分支 HEAD SHA、AAB/IPA SHA256、构建机和构建时间。

## 2. 通用发布前 checklist

- [x] 商店标题、短描述、年龄段与儿童教育定位不包含“真人老师”等误导表述。
- [x] TTS 页面明确标记“离线范读试点”，播放失败会回退，关闭朗读后不强制播放。
- [x] 核心课程离线可用；TTS 试点没有运行时网络请求，不上传儿童文本或声音。
- [x] 反馈流程禁止姓名、生日、原始麦克风录音等儿童数据，并有 P0/P1 运行级 SLA。
- [ ] 普通话教师两人确认四句 20 个关键字无错音，并在试点记录签名。
- [ ] 完整执行 `npm test`、`npm run test:offline`、`npm run check:round12`；H1–H8 合流后必须 8/8。
- [ ] 在低端 Android 真机完成冷启动、飞行模式、来电/切后台、耳机插拔和连续播放回归。
- [ ] 对最终构建执行 SBOM、恶意软件、密钥泄漏、第三方许可与隐私声明复核。
- [ ] 更新截图、功能图、内容分级、支持网址、隐私政策网址和版本说明，并由产品签字。

## 3. Google Play 内测轨道演练

- [x] 目标轨道设为 **Internal testing**，首轮不直接进入 production。
- [x] 包名核对为 `com.hongen.literacy`，预期上传 AAB，`versionCode` 必须比线上现值大。
- [ ] 用正式 JDK/Gradle 环境执行 Capacitor 同步和 release AAB 构建；不得使用 debug keystore 冒充候选。
- [ ] 通过 Play App Signing 账户核对上传证书指纹；双人确认后上传。
- [ ] 完成 Data safety、Families Policy、广告/账号/数据删除、内容分级与目标 API 问卷。
- [ ] 查看 pre-launch report 的崩溃、ANR、无障碍和设备兼容结果；P0/P1 为 0 才可推进。
- [ ] 从 Play 内测链接在一台未安装设备上安装，再用上一正式版验证覆盖升级和进度保留。
- [ ] 记录 AAB SHA256、Play 处理后的版本号、审核状态、测试名单与回退负责人。

## 4. App Store / TestFlight 演练

仓库当前没有已确认的 iOS 原生工程和签名产物，因此这一段是缺口演练，不能勾成“已提交”。

- [x] 计划先走 **App Store Connect / TestFlight internal testing**，再决定外部测试与正式审核。
- [ ] 创建并核对唯一 bundle ID、SKU、Marketing Version 与 Build Number；不得照抄 Android versionCode。
- [ ] 在受控 Xcode/macOS 构建机完成 Capacitor iOS 同步、Archive、签名和导出验证。
- [ ] 填写 App Privacy、Kids Category、年龄分级、加密出口合规、麦克风/相机用途说明与审核备注。
- [ ] 在审核备注中说明离线范读是预生成合成语音、无儿童语音上传，并给出《静夜思》入口路径。
- [ ] 上传后检查 processing、缺失合规项和 TestFlight 安装；至少一台受支持 iPhone/iPad 冷安装通过。
- [ ] 记录 IPA/archive SHA256、证书/描述文件到期日、Build Number 与回退构建。

## 5. 运行、停发与回退演练

1. 发布负责人在提交前查询 `FEEDBACK-LOOP.md` 看板：P0/P1 未关闭必须为 `0/0`。
2. 若试点出现关键错音、崩溃、无声死路或隐私意外，按 P0/P1 SLA 建 issue，立即暂停该轨道扩量。
3. 代码级首选回退是移除 `jingyesi` 白名单映射，让页面恢复系统 TTS；坏资产不得阻断古诗正文和字幕。
4. 已上传但未发布：撤回候选并上传递增版本号的新构建；已发布：按商店能力停止分阶段发布并提交修复版，不能复用旧 versionCode/Build Number。
5. 回退后在原故障设备复测，再验证离线、系统无中文 voice、朗读关闭、切后台四条路径，issue 才能转 `Verified`。

## 6. 演练结论

流程清单与回退路径 **PASS**；真实商店提交 **NO-GO**。当前明确阻断为：普通话双人审校未签字、生产签名/账号未使用、最终 AAB/IPA 及哈希未生成、Android 真机和 TestFlight 未执行、全分支 Round 12 8/8 尚待合流。上述未勾项必须由正式发布负责人在候选 SHA 上补齐，不能把本演练文档当作已审核或已上架证据。
