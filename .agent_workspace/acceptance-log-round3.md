# Round 3 axe 无障碍验收记录

记录日期：2026-08-26  
扫描范围：识字 App 11 个路由、数学 App 8 个路由  
执行命令：`npm run build && node scripts/axe-check.mjs`

## 修复前基线

实测基线为 19/19 页面完成、`critical=4`、`serious=63`，高于任务描述中的
53 个 serious 节点。完整分布如下：

| App | 页面 | axe 规则 | critical | serious |
| --- | --- | --- | ---: | ---: |
| 识字 | 首页地图 | `color-contrast` | 0 | 1 |
| 识字 | 字表 | `aria-required-children`、`color-contrast` | 1 | 14 |
| 识字 | 单字详情 | — | 0 | 0 |
| 识字 | 听音识字 | — | 0 | 0 |
| 识字 | 偏旁部首 | `color-contrast` | 0 | 22 |
| 识字 | 偏旁详情 | `color-contrast` | 0 | 19 |
| 识字 | 绘本书架 | `color-contrast` | 0 | 1 |
| 识字 | 绘本详情 | — | 0 | 0 |
| 识字 | 成语列表 | `color-contrast` | 0 | 1 |
| 识字 | 成语详情 | — | 0 | 0 |
| 识字 | 家长中心 | — | 0 | 0 |
| 数学 | 学习地图 | — | 0 | 0 |
| 数学 | 数量星云 | `aria-prohibited-attr` | 0 | 1 |
| 数学 | 算术恒星 | `aria-prohibited-attr` | 0 | 1 |
| 数学 | 形状卫星 | `aria-prohibited-attr` | 0 | 1 |
| 数学 | 规律环带 | `aria-prohibited-attr` | 0 | 1 |
| 数学 | 数独空间站 | `aria-required-children` | 1 | 0 |
| 数学 | 生活行星 | `aria-prohibited-attr` | 0 | 1 |
| 数学 | 成就墙 | `button-name` | 2 | 0 |

## 修复内容

- 提高识字 App 三套主题的次要文字对比度，并让底部导航选中项使用高对比文字色。
- 将字表筛选从不完整的 `tablist` 改为带 `aria-pressed` 状态的按钮组。
- 将数学答题圆点声明为具有数值范围的 `progressbar`，消除普通 `div` 上的禁用 ARIA 属性。
- 将数独棋盘声明为按钮组，避免无 `row` 子元素的不完整 ARIA grid。
- 为音效与护眼开关补充稳定的可访问名称和 `aria-pressed` 状态。

## 复验结果

`axe-check.mjs` 完整扫描 19/19 页面，所有页面均为：

```text
critical=0, serious=0
```

最终汇总：

```text
axe 汇总：19/19 页面完成，critical=0, serious=0。
```

结论：**PASS**。Round 3 双 App axe serious 与 critical 均已清零。
