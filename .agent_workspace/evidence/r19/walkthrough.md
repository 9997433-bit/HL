# Round 19 · H6 走查证据包

> 分支 `cursor/r19-walkthrough-bundle-9f67`，走查的树 = 本分支 tip
> （已 merge `origin/cursor/r19-orchestration-9f67`，含 H4 讲解播放器），
> 在 `/tmp/wt-r19-walk` 独立 worktree 里跑。
> 截图机 `scripts/walkthrough-shots-r19.mjs`；本包接 preview
> 识字 `:4173` + 本 worktree 重建后的数学 `:4194`（带 ROUND19_H4），
> 真 Chrome 148.0.7778.96 headless / Node v22.14.0。
> 原始清单：`evidence/r19/walkthrough-shots.json`。

## 这份包拍的是哪棵树

编排启动后 H4 已合入，H2 / H3 / H5 仍在路上。本包四类场景都用真页面拍：
齐的写绿，未齐的在图注和正文里写清楚，不伪造。

| 场景 | R19 目标 | 本包实测 | 齐？ |
| --- | --- | --- | --- |
| 全库富玩抽查 | H2 ≥1820 手写关 | 1240 / 1820，抽「驰」`fallback=false` | **未齐**（差 580） |
| 精美舞台 | H3 精美度升级 | 基线 `swipe-motion`，已往右 1/3 | **未齐** |
| 剖析播放器 | H4 讲解时间轴 | `data-lesson-player` + 播放中 progress=30 | **已齐** |
| 周报 / 学伴 | 读真存档 | 周报「做了 8 道题」；学伴气泡可读 | 基线可用 |

## 怎么产生的

识字侧用已起的 vite preview；数学侧对本 worktree `npm run build --workspace=apps/math-app`
后挂 `:4194`（旧的 `:4174` 还是合入前的 dist，拍不到 H4）。脚本用 puppeteer-core
挂真 Chrome，从 hash 路由一路点进去落 PNG——不是组件单渲，也不是设计稿导出。

覆盖率那张（`r19-02`）是本进程 `import` 字表 + `loadAllRichPlays()` 后当场数出来的
实测面板。家长周报故意排在剖析之后：剖析幕答的 8 道题落进同一浏览器上下文的
localStorage，周报读的就是这份存档。

## 四类场景

### ① 全库富玩抽查

走法：装齐 70 个富脚本分片，按 `hasRichPlay()` 取靠后单元的手写关，进
`/#/learn/驰`，清存档重载，点到「玩一玩」。

![全库富玩抽查：手写关「驰」](r19-01-rich-spot.png)

「驰」：`data-play-template=swipe-motion`、**`data-fallback=false`**，旁白
「骏马撒开腿，飞驰起来。」——往右推 3 下马才跑起来，玩法在讲字义。

![全库富玩覆盖率实测面板](r19-02-rich-coverage.png)

当场量出来：**1240 条手写 / 1820 字表，旁白去重 1240，模板回填缺口 580**。
R19 H2 阈值是 ≥1820，**差 580，功能未齐**——这张表就是 H2 要翻掉的账本，
不是失败截图。

### ② 精美舞台

走法：同一关把玩关面板滚到视口中央，点一次「往右推一下」，进度到「已往右 1 / 3」
再拍舞台面板。

![精美舞台基线：「驰」玩关](r19-03-polish-stage.png)

舞台上是马头道具、橙色主按钮、可跳过、墨墨旁白——编排启动时的基线外观。
**R19 H3「精美度升级」尚未合入**；合入后应重跑本幕对照动效与材质，
本包只证明「舞台现在长这样」。

### ③ 剖析播放器

走法：进 `/#/word-problems`，开「🔍 剖析」，点面板上的播放键，等时间轴走到
图示段再拍（`data-wp-player-state=playing`）。

![剖析播放器：讲解时间轴](r19-04-analysis-player.png)

本轮抽到「25 只瓢虫平均分给 5 个小朋友」：顶栏出现 **讲解播放条**——
「⏸ 暂停」、勾选「朗读 why」、进度条停在「图示理解」、旁白写着
「讲解播放按图示 → 分步自动推进（约 6 秒）」。面板挂着
`data-lesson-player=wp-lesson-player`（ROUND19_H4），cues=2、progress≈30。
图示五条等分条已亮；分步区提示「正在讲图示，下一步会摊开算式……」。
右上角「跳过 ✕」全程在。看完（或跳过）后接着答了 8 题，链路没被播放器卡住。

### ④ 周报与学伴

![数学家长周报](r19-05-math-parent-weekly.png)

进 `/#/parent`，过口算门。`data-weakness="thin"`：
「这周来了 1 天 · 共 0 分钟 · **做了 8 道题** · 弱项判定：来的天数太少」——
8 道就是第 ③ 幕答的，周报读的是真存档。卡底写着按本机存档现算、没有联网对比。

![识字学伴](r19-06-literacy-mascot.png)

识字首页点学伴，气泡「学累了就歇一会儿，我在这里等你。」——台词随存档变，
不是写死的一句。

## 走查里诚实记下来的

1. **H2 全库还差 580。** 1240 是 R18 收口线；缺口字仍吃模板回填。
2. **H3 精美度还没影子。** 舞台仍是基线皮肤；本幕拍的是「未升级」对照。
3. **H4 讲解播放器已可点。** 不是真 MP4，是程序化时间轴（图示 → 分步 why），
   可暂停、可朗读、可跳过——和 `wpExplainPlayer.js` / 面板 `data-lesson-player`
   对得上。
4. **单场走查只能打出 `thin` 周报分支。** 其它分支靠 `npm run test:mascot`
   构造存档，不在本包。
5. **周报「共 0 分钟」。** 8 道短会话时长仍归零，记在这里备查。

## 边界

- 全程 headless Chrome + 本地 preview，**不是真机**（真机归 H7）。
- `--mute-audio`：旁白 TTS、音效未验（勾了「朗读 why」但不听声）。
- 富玩抽查一个字，证明「手写关契约还在」；全库数走 `countRichPlays()` /
  `check:round19` H2。
- 应用题抽哪道、学伴说哪句会随题序和存档变；路径与 `data-*` 契约固定。

## 复现

```bash
npm run build --workspace=apps/math-app
# 数学 dist 挂到任意端口，例如 4194；识字可用已有 :4173
PREVIEW_LITERACY=http://127.0.0.1:4173 PREVIEW_MATH=http://127.0.0.1:4194 \
  npm run walkthrough:shots:r19
```

## 探针

走查当天在这棵树上跑 `npm run check:round19` 的 H6 口径：
文档 >400 字、四类场景词（全库富玩 / 精美舞台 / 剖析播放器 / 周报或学伴）、
引用落盘 ≥4 且每张 ≥200B。本包 6 张均过线。

## 文件清单

| 文件 | 覆盖 | 字节 |
| --- | --- | --- |
| `evidence/r19/r19-01-rich-spot.png` | ① 全库富玩抽查·手写关「驰」 | 126,905 |
| `evidence/r19/r19-02-rich-coverage.png` | ① 全库富玩覆盖率实测（1240/1820，差 580） | 124,210 |
| `evidence/r19/r19-03-polish-stage.png` | ② 精美舞台基线（已往右 1/3，H3 未齐） | 125,640 |
| `evidence/r19/r19-04-analysis-player.png` | ③ 剖析播放器·讲解时间轴播放中（H4 已齐） | 819,855 |
| `evidence/r19/r19-05-math-parent-weekly.png` | ④ 周报·做了 8 道题 | 590,397 |
| `evidence/r19/r19-06-literacy-mascot.png` | ④ 学伴气泡 | 37,423 |
| `evidence/r19/walkthrough-shots.json` | 每张图说明、字节与实测 meta | — |
| `scripts/walkthrough-shots-r19.mjs` | 截图机 | — |
