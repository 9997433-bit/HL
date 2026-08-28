# R18 H3 · 富 play 脚本按单元拆片懒加载

> 岗位：r18-play-codesplit（子代理 #5）
> 分支：`cursor/r18-play-codesplit-9f67`（基于 `cursor/r18-orchestration-9f67` @ `10e199e`）
> 契约：`.agent_workspace/round18-architecture.md` §2，本文逐条对账。

## 1. 问题

拆之前单字详情的同步链是：

```
CharDetailView.vue →(静态)→ CharPlayStage.vue →(静态)→ char-play.js
                                              →(静态)→ char-play-rich.js（源码 262KB / 940 条）
char-intro.js →(静态)→ char-play-rich.js
```

孩子点开「雨」，先下载另外 939 个字的剧本。可孩子一次只玩一个字，同一分钟里
最多用到同单元的十几条，其余九百多条是白下的。

## 2. 落点

| 文件 | 状态 |
|---|---|
| `src/data/play-rich/uN.js` ×55 | 新增。一单元一片，`UNIT_RICH_PLAYS` 是完整条目，形状与拆包前一字不差 |
| `src/data/play-rich/index.js` | 新增。manifest + 每单元一个 `() => import()`；唯一允许被同步 import 的文件，6.2KB，体积 O(单元数) |
| `src/data/char-play-rich.js` | **删除**（不留薄壳） |
| `scripts/gen-char-play-rich.mjs` | 落盘改为分片 + manifest；顺手清理陈旧分片与旧单体文件 |
| `src/data/char-play.js` | 顶层 rich import 拆掉，补齐契约 §2.3 的五个口 |
| `src/data/char-intro.js` | 改用 `peekRichPlay()` |
| `src/components/CharPlayStage.vue` | 走 `getCharPlayAsync()` + 竞态 / 打断防护 |
| `src/views/CharDetailView.vue` | 换字时与课文包一起 `ensurePlayUnit()` |
| `src/views/LearnView.vue` | 翻到某一站时预热该单元（连引擎本身也动态取，不给字表页加重） |
| `vite.config.js` | `manualChunks` 给分片命名 `play-rich-uN` |
| `scripts/check-bundle.mjs` | 新增 3 条断言（见 §5） |
| `scripts/test-char-play.mjs` | 新增「冷启动也玩得成」一节；全库断言前 `loadAllRichPlays()` |
| `scripts/check-round15/16/17/18.mjs` | 各一行加载适配（契约 §2.7 主案），阈值一个字没动 |

## 3. API 契约对账（§2.3）

| API | 实测 |
|---|---|
| `ensurePlayUnit(unitId)` | ✅ 幂等（缓存 Promise）；未知单元 / 加载失败静默 resolve |
| `preloadPlayUnits(ids)` | ✅ |
| `loadAllRichPlays()` | ✅ 返回注册条数 940；`src/**/*.vue` 里零引用 |
| `getCharPlay(char)` | ✅ 同步、永不 null；未加载时 `getCharPlay('雨').source === 'generated'` |
| `getCharPlayAsync(char)` | ✅ `await getCharPlayAsync('雨')` → `source === 'rich'`、`template === 'rain-catch'` |
| `peekRichPlay(char)` | ✅ 未加载返回 null，不触发加载 |
| `countRichPlays()` / `listRichPlays()` / `hasRichPlay()` | ✅ 已注册口径（诚实口径）；`loadAllRichPlays()` 后 940 / 旁白去重 940 |
| `richPlayCoverage()` | ✅ 带 `manifest`，装全后 `plays === manifest.plays === 940` |

## 4. dist 实测

| 块 | 拆前 | 拆后 |
|---|---|---|
| 入口 `index-*.js`（同步闭包） | 325 KB | **325 KB**（预算 420 KB，未放宽） |
| `CharDetailView-*.js` | 335.3 KB（gzip 113.4） | **84.6 KB**（gzip 30.3） |
| 共用 `char-play-*.js`（详情 / 字表都用） | —（并在详情块里） | 86.6 KB（gzip 42.9） |
| 单字详情同步下载量合计 | 335.3 KB | **171.2 KB（-49%）** |
| `play-rich-uN-*.js` ×55 | — | 每片 0.6–2.4 KB，玩到才下 |

## 5. 门禁

```
npm run check:bundle --workspace=literacy-app
  ✓ 每个单元都切出了自己的课文块（99 / 99）
  ✓ 首屏没有同步加载课文包
  ✓ 首屏 JS 里没有夹带字义
  ✓ 首屏 JS 325 KB（预算 420 KB，共 1 个块）
  ✓ 每个单元的手写剧本都切出了自己的块（55 / 55）
  ✓ dist 里找到单字详情块
  ✓ 首屏同步闭包里没有手写剧本正文
  ✓ 单字详情同步闭包里没有手写剧本正文
  8 项通过，0 项失败
```

后三条按**内容指纹**判（拿 u1 第一条旁白当指纹），不按文件名判：改块名骗得过
文件名，骗不过原文那句旁白。拆包最怕的不是没拆，是拆完过两周被一行静态 import 缝回去。

其余：

- `check:round18`：**H3 ✓**（分片 56 ≥ 5，合计 294KB ≥ 100KB，无整包静态 import）
- `check:round15` 7/8、`check:round16` 7/8、`check:round17` 7/8 —— 富 Play 各项全绿，
  仅 H8 红，是干净检出下缺双 APK 产物的既有环境红（与本轮改动无关，`npm run android:sim` 重建即可）
- `test:play` 1820 字零空洞；`test:play:guard` 撞句负例仍在生成期被拦、manifest 与实测对账一致
- `check:data` 80 项通过

## 6. 两个设计取舍，写在这儿免得下一个人再想一遍

**为什么冷启动不返回 rich。** 让 `getCharPlay()` 在分片没到时也报 `source: 'rich'`
（把旁白留在同步索引里）是能做到的，我先写过一版。但那样「轻量索引」会随 seed
一起长：940 条旁白就是 35KB，扩到 1340 条就是 50KB，等于把拆掉的东西按比例又
搬回同步路径。所以照契约走诚实口径——片没到就是自动补齐层那一版，它覆盖全库，
一样玩得完。

**为什么舞台不 await 到底。** 「玩」是五步的第一步，`await` 一次网络就是一次白屏。
所以舞台先用同步那一版开演，`getCharPlayAsync()` 回来再换成手写版；换关时两道
防护：字翻走了就丢弃结果，孩子已经动过手或已经玩完就这一次不换。配合
CharDetailView / LearnView 的预取，实际路径上片通常在舞台首帧之前就到了。
