# Round 10 · SOTA C-6 Chrome 实测

本目录保存 SOTA 共同验收项 C-6 的 Chrome 实测切片。自动化从双 App 生产构建首页
点击全局页脚的“隐私政策”，分别以桌面和移动视口验证：

- `/privacy` 路由可达，页面标题与 `document.title` 正确；
- 页面展示版本 `1.0.0`、零账号声明及至少六个政策分节；
- 控制台与页面异常为零；
- 页面加载期间没有非本机来源请求；
- 四个视口各保存一张全页截图。

复现命令：

```bash
npm run build:all
npm run test:c6:chrome
```

机读结果写入 `browser-matrix-chrome.json`，截图命名为
`browser-matrix-{literacy|math}-{desktop|mobile}.png`。这里仅声称 Chrome 的实际
结果；Edge、Firefox、macOS/iPadOS Safari 不在当前 Linux 环境内，未伪造为已测。

## 本次结果

- UTC：2026-08-27T14:42:06.769Z
- 浏览器：Chrome 148.0.7778.96（Linux x86_64）
- 结果：快乐识字 / MathQuest × desktop / mobile，共 **4/4 PASS**
- 四个页面：控制台错误 0，跨来源 HTTP(S) 请求 0
