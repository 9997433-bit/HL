# 绘本社区投稿格式规范 · BOOK COMMUNITY SUBMISSION

> 适用仓库：`hongen-edu-apps` / `apps/literacy-app`
> 对应交付：Round 9 · L-M5（探针 `npm run check:round9` H5）
> 状态：规范生效；JSON → 种子的自动转换脚本见文末「尚未落地的部分」。

---

## 一、这份规范要解决的问题

分级绘本是识字 App 里最耗人力、也最容易被社区帮上忙的一块内容：目前 132 本书
（L1 25 本 / L2 25 本 / L3 23 本 / L4 21 本 / L5 20 本 / L6 18 本）里，只有最早的
30 本是逐句手写手工注音的语感基准（`src/data/books/core.js`），其余一百多本都由
`scripts/gen-books.mjs` 从种子文件生成。也就是说，**一个外部投稿人真正需要写的
只有「书名 + 一页一句正文」，拼音、重点字、封面配色、分级名全部是算出来的**。

但正因为门槛低，投稿最容易在三件事上翻车，而这三件事恰好都是自动化能拦住的：

1. **用超纲字。** 分级绘本的全部价值就在「只用孩子学过的字」。正文里混进一个
   字表外的字，孩子读到那一页就卡住，而且这是静默失败——页面照样渲染，只是那个字
   没有详情页可点。`verifyBookCoverage()` 和 `npm run check:data` 把它变成红灯。
2. **多音字注错音。** 逐字注音只能拿到字表登记的本音，可儿童读物里全是轻声词和
   多音字：「妈妈」不念 mā mā，「长大」不念 cháng dà。生成器按词典最长匹配切词，
   切不中就退回本音；`STRICT` 名单里的字（长/种/数/只/还/教/转/发/便/曲/角）
   如果没有被词条覆盖，直接报错退出，不允许蒙混过关。
3. **分级名不副实。** L1 写成了 L4 的句长，书架上那一级就废了。

所以投稿格式的设计原则是：**投稿人只填人类判断得出的东西，机器算得出来的一律不许填。**
配色、拼音、`newChars`、`levelName`、`id` 都由流水线生成，投稿 JSON 里出现这些字段
一律视为格式错误——不是因为它们有害，而是因为一旦允许手填，它们迟早和生成结果分叉。

---

## 二、一次投稿的生命周期

| 阶段 | 谁做 | 产出 / 判据 |
|---|---|---|
| S1 撰写 | 投稿人 | 一个 `submission.json`（本文档第三节的 schema） |
| S2 自检 | 投稿人 | 本地跑第五节的三条命令，全绿才提 PR |
| S3 机检 | CI | `check:submissions`（ajv）+ `gen:books` + `check:data`，任一红灯自动打回 |
| S4 人审 | 维护者 | 第四节 B 类规则（教学性、语感、价值观），只看机器看不出来的 |
| S5 合入 | 维护者 | 一条 `npm run import:book -- <文件>`：归档 JSON、追加种子、重跑生成器 |

S3 之前不占用任何人工时间，这是整个流程能规模化的前提。S4 只看四件事：
句子读起来像不像话、情节有没有起承转合、有没有说教味、有没有价值观问题。

---

## 三、投稿 JSON schema

### 3.1 顶层结构

一个文件投一本书。文件名建议 `submission-<拼音书名>.json`，UTF-8 无 BOM，两空格缩进。

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `schema` | string | 是 | 固定 `"hongen-book/1"` | 版本号，将来格式演进靠它区分 |
| `level` | integer | 是 | 1–6 | 分级，见 3.3 的判据表 |
| `title` | string | 是 | 2–10 个汉字，全仓库唯一 | 书名，也必须只用字表内的字 |
| `sub` | string | 是 | 4–12 字 | 分级副标题，会拼成 `第 N 级 · <sub>` |
| `cover` | string | 是 | 单个 emoji | 书架封面图标 |
| `summary` | string | 是 | 15–40 字 | 一句话简介，给家长看，可以用超纲字 |
| `pages` | array | 是 | 长度见 3.3 | 正文，一页一句 |
| `pages[].emoji` | string | 是 | 单个 emoji | 这一页的插图 |
| `pages[].text` | string | 是 | 见 3.2 | 这一页的正文 |
| `contributor` | object | 是 | 见 3.4 | 署名与授权声明 |
| `notes` | string | 否 | ≤200 字 | 给评审看的话，不进产物 |

**禁止出现的字段**（出现即退回）：`id`、`pinyin`、`p`、`palette`、`levelName`、
`newChars`。这些全部由 `scripts/gen-books.mjs` 生成。

### 3.2 正文 `pages[].text` 的字符集

正文只允许两类字符：

- **汉字**：必须收录在 `apps/literacy-app/src/data/char-index.js`（1800 字）里；
- **标点**：只允许 `，` `。` `！` `？` `：` `、` `；` `…` `—` 这九个全角符号。

注意 `「」` `《》` 虽然在阅读器的标点白名单里，但生成器的注音表 `PUNCT` 不认，
所以**投稿正文里不要用引号和书名号**——需要对话时用「谁谁说：句子。」的形式即可。
数字一律写汉字（写「三」不写「3」），字母、空格、换行、半角标点都不允许。

单句长度建议：L1 ≤ 10 字，L2 ≤ 14 字，L3 ≤ 18 字，L4–L6 ≤ 24 字。这不是硬约束，
但超出会在 S4 被要求拆句。

### 3.3 分级判据与页数下限

| 级 | 页数下限 | 句式 | 情节 |
|---|---|---|---|
| L1 | 5 | 一句一行，同一句式换词重复 | 不讲情节，靠图能猜出意思 |
| L2 | 6 | 出现对话 | 两三个场景并列 |
| L3 | 7 | 复句开始出现 | 有完整的一天 |
| L4 | 8 | 长短句交替 | 有起承转合 |
| L5 | 9 | 段落感 | 多角色 |
| L6 | 10 | 接近书面语 | 接近小小章节书 |

页数下限来自生成器里的 `MIN_PAGES`，是硬约束；上限没有，但超过 14 页会被建议拆成两本。

### 3.4 `contributor` 与授权

```json
"contributor": {
  "name": "张三",
  "contact": "zhangsan@example.com",
  "license": "CC0-1.0",
  "original": true
}
```

- `license` 只接受 `CC0-1.0` 或 `CC-BY-4.0`。选 `CC-BY-4.0` 时署名会写进
  `THIRD_PARTY_NOTICES.md`；选 `CC0-1.0` 则只在 PR 记录里留痕。
- `original` 必须为 `true`：正文必须是投稿人原创。**改写自现有出版物、教材、
  他人绘本的一律不收**，哪怕改得很多——这是法律风险，不是质量问题。
  取材于公共领域的民间故事、成语、古诗可以，但要在 `notes` 里注明出处。

### 3.5 JSON Schema（draft 2020-12，供 CI 直接使用）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://hongen-edu-apps/schemas/book-submission-1.json",
  "title": "分级绘本投稿",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema", "level", "title", "sub", "cover", "summary", "pages", "contributor"],
  "properties": {
    "schema": { "const": "hongen-book/1" },
    "level": { "type": "integer", "minimum": 1, "maximum": 6 },
    "title": { "type": "string", "minLength": 2, "maxLength": 10 },
    "sub": { "type": "string", "minLength": 4, "maxLength": 12 },
    "cover": { "type": "string", "minLength": 1, "maxLength": 8 },
    "summary": { "type": "string", "minLength": 15, "maxLength": 40 },
    "pages": {
      "type": "array",
      "minItems": 5,
      "maxItems": 14,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["emoji", "text"],
        "properties": {
          "emoji": { "type": "string", "minLength": 1, "maxLength": 8 },
          "text": {
            "type": "string",
            "minLength": 2,
            "maxLength": 28,
            "pattern": "^[\\u4e00-\\u9fa5，。！？：、；…—]+$"
          }
        }
      }
    },
    "contributor": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "license", "original"],
      "properties": {
        "name": { "type": "string", "minLength": 1 },
        "contact": { "type": "string" },
        "license": { "enum": ["CC0-1.0", "CC-BY-4.0"] },
        "original": { "const": true }
      }
    },
    "notes": { "type": "string", "maxLength": 200 }
  },
  "allOf": [
    { "if": { "properties": { "level": { "const": 2 } }, "required": ["level"] },
      "then": { "properties": { "pages": { "minItems": 6 } } } },
    { "if": { "properties": { "level": { "const": 3 } }, "required": ["level"] },
      "then": { "properties": { "pages": { "minItems": 7 } } } },
    { "if": { "properties": { "level": { "const": 4 } }, "required": ["level"] },
      "then": { "properties": { "pages": { "minItems": 8 } } } },
    { "if": { "properties": { "level": { "const": 5 } }, "required": ["level"] },
      "then": { "properties": { "pages": { "minItems": 9 } } } },
    { "if": { "properties": { "level": { "const": 6 } }, "required": ["level"] },
      "then": { "properties": { "pages": { "minItems": 10 } } } }
  ]
}
```

JSON Schema 只管得住形状。真正的内容约束（用字越界、多音字、书名撞车）
必须靠仓库里已有的生成器和自检脚本，见下一节。

---

## 四、校验规则

规则分两类：**A 类由机器判定，红灯即退回，不接受申辩**；**B 类由人评审**。

### A 类 · 机器硬拦截

| 编号 | 规则 | 由谁执行 | 失败表现 |
|---|---|---|---|
| A-1 | JSON 通过 3.5 的 schema | `import-book-submission.mjs`（ajv） | 字段缺失 / 多字段 / 正文含非法字符 |
| A-2 | 正文每个汉字都在 `char-index.js` 里 | 导入器 + `gen-books.mjs`（同一份 `book-text.mjs`） | `「囧」不在字表里` |
| A-3 | `STRICT` 多音字被 `book-pinyin.mjs` 词条覆盖 | 同上 | `多音字「长」没有词条定音` |
| A-4 | 书名在 132 本里唯一 | 导入器 + `gen-books.mjs` + `check-data.mjs` | `书名重复` |
| A-5 | 页数 ≥ 该级下限 | 导入器 + `gen-books.mjs` 的 `MIN_PAGES` | `第 3 级要 ≥ 7 页，只有 6 页` |
| A-6 | 书名本身也只用字表内的字 | 导入器 + `gen-books.mjs` 给书名注音时 | 同 A-2 |
| A-7 | 每页都有 emoji 和正文 | `check-data.mjs` | `每页都有插图和正文` 变红 |
| A-8 | 生成后 `newChars` 全在字表里 | `check-data.mjs` | `绘本的重点字都在字表里` 变红 |
| A-9 | 合入后每一级仍 ≥ 12 本、总数 ≥ 130 | `check-data.mjs` | 只在删书时才可能红 |
| A-10 | 轻量索引与书目一致 | `check-data.mjs` | 忘了提交 `book-index.js` 时红 |

A-3 有一个投稿人需要知道的例外：如果你的正文用到了一个词典里没有的多音词
（比如「转身」），流水线不会帮你猜，你需要在 PR 里同时给
`scripts/data/book-pinyin.mjs` 加一条词条。这是唯一允许投稿人碰生成器输入之外文件的情况。

### B 类 · 人工评审

| 编号 | 看什么 | 常见退回理由 |
|---|---|---|
| B-1 | 读起来像不像人话 | 为了避开超纲字把句子写拧了，是最高频的退回原因 |
| B-2 | 情节是否匹配分级 | L4 投了个 L1 的重复句式 |
| B-3 | 有没有说教味 | 结尾硬贴一句「我们要爱护环境」 |
| B-4 | 价值观 | 性别刻板印象、比较心（谁比谁聪明）、恐吓式管教 |
| B-5 | 与现有书目的重复度 | 已经有五本讲小兔子过桥了 |
| B-6 | emoji 与正文是否对得上 | 正文说蝴蝶，图放了蜜蜂 |

B-1 值得单独说一句：受字表限制写出来的句子很容易带一股「填空感」——
每句都是「X 上有 Y，Y 很 Z」。评审时的判据是**把拼音遮住念一遍，
如果连着三句能猜到下一句的骨架，就退回重写**。宁可少一本，不要多一本模板书。

---

## 五、投稿人本地怎么自检

```bash
# 0. 一次性准备
npm install

# 1. 只校验，不改仓库：A 类十条规则一次把全部反馈给齐
node scripts/import-book-submission.mjs submission-xxx.json --dry-run

# 2. 全绿之后真的合入：归档 JSON + 追加种子 + 重跑 gen:books（任一步失败整体回滚）
npm run import:book -- submission-xxx.json

# 3. 内容自检（必须全绿）
cd apps/literacy-app && npm run check:data

# 4. 回到仓库根，确认没有踩到别的门禁
cd ../.. && npm run test:literacy
```

第 1 步和第 2 步用的是同一套判据（`apps/literacy-app/scripts/book-text.mjs`，
和生成器共用），所以 `--dry-run` 说能过，`gen:books` 就不会翻脸。导入器在有任何
一条 A 类红灯时**不写任何文件**，落盘中途出错也会把已改的文件还原，
失败不会污染工作区。第 3 步末尾会打一行统计，把书本数、总页数、不重复用字数
一起报出来，方便在 PR 描述里贴。

PR 需要包含：投稿 JSON（导入器会自动放到 `apps/literacy-app/scripts/data/submissions/`）、
改动后的种子文件、以及**重跑生成器产生的全部生成物**（`src/data/books/l*.js`、
`src/data/books/extended.js`、`src/data/book-index.js`）。生成物不提交会让 CI 红。
选 `CC-BY-4.0` 的投稿还会多一行 `THIRD_PARTY_NOTICES.md` 署名，一并提交。

---

## 六、完整示例

### 6.1 一份合格的投稿（L2）

这份就是导入器的正向自检夹具
（`apps/literacy-app/scripts/fixtures/submissions/valid-l2-xiaomaoheyueliang.json`），
A 类十条规则全绿：

```json
{
  "schema": "hongen-book/1",
  "level": 2,
  "title": "小猫和月亮",
  "sub": "云走了它就回来",
  "cover": "🌙",
  "summary": "小猫夜里坐在门口看月亮，云把月亮盖住了，它一直等到月亮回来。",
  "pages": [
    { "emoji": "🌙", "text": "夜里，小猫在门口看月亮。" },
    { "emoji": "🌕", "text": "月亮圆圆的，很白很大。" },
    { "emoji": "🐱", "text": "小猫问：月亮，你冷不冷？" },
    { "emoji": "☁️", "text": "风来了，云把月亮盖住了。" },
    { "emoji": "😿", "text": "小猫坐在门口，一直等。" },
    { "emoji": "🌙", "text": "云走了，月亮回来了。" },
    { "emoji": "🏠", "text": "妈妈叫小猫回家睡觉。" },
    { "emoji": "💤", "text": "小猫说：月亮，明天见。" }
  ],
  "contributor": {
    "name": "示例投稿人",
    "contact": "submissions@example.com",
    "license": "CC0-1.0",
    "original": true
  },
  "notes": "想让孩子自己数出月亮被云盖住的那几页，所以没有写「影子」「遮」这类字。"
}
```

导入器翻出来的种子条目长这样（投稿人也可以直接照这个格式提）：

```js
{
  t: '小猫和月亮',
  sub: '云走了它就回来',
  cover: '🌙',
  summary: '小猫夜里坐在门口看月亮，云把月亮盖住了，它一直等到月亮回来。',
  pages: [
    ['🌙', '夜里，小猫在门口看月亮。'],
    ['🌕', '月亮圆圆的，很白很大。'],
    ['🐱', '小猫问：月亮，你冷不冷？'],
    ['☁️', '风来了，云把月亮盖住了。'],
    ['😿', '小猫坐在门口，一直等。'],
    ['🌙', '云走了，月亮回来了。'],
    ['🏠', '妈妈叫小猫回家睡觉。'],
    ['💤', '小猫说：月亮，明天见。']
  ]
}
```

生成器会补上 `id: 'bx103'`、逐页拼音、`levelName: '第 2 级 · 云走了它就回来'`、
按序号取的两色渐变，以及从正文里挑出来的 `newChars`。

顺带一句字表的坑：1820 字是一份课程表，不是常用字全集——`出`、`着`、`得`、`谁`、
`跟`、`掉` 这些看着最普通的字都不在里面。写之前先跑一次 `--dry-run`，比照着感觉写完
再回头改省事得多。

### 6.2 一份会被退回的投稿及报错

```json
{
  "schema": "hongen-book/1",
  "level": 3,
  "title": "大大小小",
  "sub": "长短高低",
  "cover": "📏",
  "summary": "比一比谁大谁小，谁长谁短。",
  "id": "bx200",
  "pages": [
    { "emoji": "🐘", "text": "大象很大，它的鼻子很长。" },
    { "emoji": "🐜", "text": "蚂蚁很小，小得像一个点。" },
    { "emoji": "📏", "text": "我用尺子量一量：1 米。" },
    { "emoji": "🌳", "text": "草有三种，高的矮的都有。" },
    { "emoji": "🙋", "text": "我长大了也会很高。" },
    { "emoji": "😊", "text": "小朋友们要好好学习，天天向上！" }
  ],
  "contributor": { "name": "王五", "license": "MIT", "original": true }
}
```

这份 JSON 就是导入器的反面自检夹具（`apps/literacy-app/scripts/fixtures/submissions/rejected-l3-dadaxiaoxiao.json`），
`node scripts/import-book-submission.mjs <文件> --dry-run` 逐字打出：

```
A-1  ✗ pages 至少要 7 项
A-1  ✗ 多了不允许的字段 id —— 这些字段由 gen-books.mjs 生成
A-1  ✗ summary 长度要求 ≥ 15
A-1  ✗ pages.2.text 含非法字符：正文只能用字表汉字和 ，。！？：、；…— 九个全角标点
A-1  ✗ contributor.license 只接受 CC0-1.0 / CC-BY-4.0
A-2  ✗ 《大大小小》第 2 页：「得」不在字表里（蚂蚁很小，小得像一个点。）
A-2  ✗ 《大大小小》第 3 页：「1」不在字表里（我用尺子量一量：1 米。）
A-2  ✗ 《大大小小》第 4 页：「矮」不在字表里（草有三种，高的矮的都有。）
A-3  ✗ 《大大小小》第 4 页：多音字「种」没有词条定音（草有三种，高的矮的都有。）
A-4  ✗ 书名重复：《大大小小》已经被现有书目占用
A-5  ✗ 第 3 级要 ≥ 7 页，只有 6 页
```

人审还会补一条 `B-3`：末页「要好好学习，天天向上」是贴上去的口号，与前文无关。

其中 A-3 的修法是给 `book-pinyin.mjs` 加 `三种: ['sān', 'zhǒng']` 词条
（`很长`、`长大` 这类常用多音词词典里已经有了，所以那两句反而不报错）；
A-2 的「得 / 像 / 矮」只能换字，A-4 只能改书名。

---

## 七、自动化落地情况（Round 10）

规范初版留了两个手工缺口，Round 10 都已经补上：

1. **`scripts/import-book-submission.mjs`** —— 读一个 `submission.json`，按 3.5 校验
   形状，再自动归档 JSON、追加到对应的 `book-seed-l{N}.mjs`、写 CC-BY 署名、
   调用 `gen:books`。S5 的手工翻写没有了。
2. **CI 上的 ajv 校验步** —— `npm run check:submissions` 已挂进 `scripts/test-literacy.sh`，
   也就是 `npm test` 的必经之路。A-1 由 ajv 判，A-2 ~ A-6 复用生成器同一套
   `book-text.mjs`，A-7 ~ A-10 仍由 `check:data` 守，S3 全自动。

两条实现上的取舍值得记一笔：

- **schema 不在代码里抄第二份。** 导入器启动时从本文件 3.5 那个 `json` 代码块里
  把 schema 抠出来喂给 ajv，抠不到就直接报错退出。这样「文档改了、CI 还按老规矩
  收稿」这种分叉根本没有存在的余地。
- **门禁自己有看门狗。** 只校验 `scripts/data/submissions/` 下的存量投稿的话，
  目录空着时这道门禁会一直绿，校验器什么时候悄悄坏掉都没人知道。所以
  `--check-all` 还会跑 `apps/literacy-app/scripts/fixtures/submissions/` 下的两份夹具：
  6.1 那本必须全绿，6.2 那本必须踩中 A-1/A-2/A-3/A-4/A-5，少踩一条就红。

投稿人直接按 6.1 的种子格式提 PR 也一样受理——JSON 只是给自动化留的接口，
不是给人为难的关卡。
