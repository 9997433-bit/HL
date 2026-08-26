# Round 1 动画、音效与性能探针基线

记录时间：2026-08-26 07:19 UTC  
环境：Linux 6.12.94+ x86_64、Node.js v22.14.0、npm 10.9.7

## 资源校验

命令：

```bash
bash scripts/verify-resources.sh
```

结果：**PASS**

```text
Resource verification passed: 100 hanzi, 85 math problems, 42 idioms,
6 SVG icons, 3 stroke fixtures, 3 WAV effects, and 1 Lottie animation.
```

JSON 数据满足当前校验基线：汉字不少于 50 字、数学题覆盖 9 类题型、成语无重复，
并声明相应许可信息。

## 边界压力测试

命令：

```bash
node scripts/stress-test.js
```

结果：**PASS**（固定种子 `20260826`，单次冷运行）

| 探针 | 规模 | 耗时 | 内存/产物 | 完整性 |
| --- | ---: | ---: | ---: | --- |
| 汉字卡片标记生成 | 20,000 张 | 35.33 ms | 堆增量 12.64 MiB；HTML 2.55 MiB | PASS |
| 数学题生成 | 100,000 题 | 9.11 ms | 堆增量 7.44 MiB；约 10,971,709 题/秒 | 0 无效题 |

静态数据输入为 100 个汉字、85 道数学题和 9 类题型。该测试测量 Node.js 中的
数据与 HTML 标记构造，不包含浏览器样式计算、布局、绘制和动画帧率。

## 构建与 Lighthouse 探针

命令：

```bash
bash scripts/benchmark.sh
```

结果：**BLOCKED**（脚本正确返回非零，并保留双应用报告）

| 应用 | 状态 | 失败前耗时 | 包体积 | 阻断项 |
| --- | --- | ---: | ---: | --- |
| 识字 App | FAIL | 568 ms | 不可得 | 路由引用缺失的 `src/views/ListenGame.vue` |
| 数学 App | FAIL | 425 ms | 不可得 | 路由引用缺失的 `src/views/LogicView.vue` |

本机未安装 Lighthouse；且两个生产构建均未完成，因此 Performance、LCP、TBT 和
CLS 均记录为 `SKIP`，不能把缺失值当作 0 分或通过。补齐视图并提供本地
`lighthouse` 可执行文件（或设置 `LIGHTHOUSE_BIN`）后，可由同一脚本重测构建时间、
原始/gzip 估算包体积及 Lighthouse 指标。

## 已发现的边界问题

1. 当前两个 App 的路由均可引用尚未落盘的视图，生产构建缺少前置完整性检查；建议在
   CI 中把 `npm run build:all` 设为必过门禁。
2. 20,000 张汉字卡片仅标记字符串已达 2.55 MiB；真实 DOM 同时挂载还会产生明显更高的
   节点、布局与绘制成本，应采用分页或虚拟列表。
3. 数学题库同时包含选择题和无 `choices` 的自由作答题；消费端和测试工具不能假定每题
   都有选项。
4. Web Audio 首次播放受浏览器自动播放策略约束，必须在点击/触摸手势中调用
   `unlockAudio()`；关闭声音及 reduced-motion 偏好也需要由 UI 层接入。
5. Node 压力探针不代表浏览器渲染帧率；构建恢复后仍需用 Lighthouse 和浏览器性能面板
   补齐真机渲染基线。
