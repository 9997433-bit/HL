# 洪恩式教育双 App

仓库包含识字 App 与数学 App。两者都是纯前端 Vite 应用，学习进度只保存在浏览器本机。

## 构建与离线使用

```bash
npm install
npm run build
npm run test:offline
```

生产构建会为每个 App 生成 `dist/sw.js`，并把 `index.html`、全部 Vite 哈希资源和公开资源写入版本化预缓存。识字 App 还会预缓存完整的 `hanzi-data` 笔顺数据。

把 `apps/literacy-app/dist` 和 `apps/math-app/dist` 分别部署到 HTTPS 静态站点（本机可用 `localhost`）。首次联网访问完成 Service Worker 安装后，刷新、重新打开页面及访问懒加载路由均可断网运行。Service Worker 不支持 `file://`，因此不要直接双击 `index.html` 来启用离线缓存。

`npm run test:offline` 会先在线安装两个 App 的 Service Worker，再彻底关闭测试 HTTP 服务，并从新页面打开识字详情与数独路由，同时校验识字笔顺 JSON 可离线读取。运行前需先完成构建。
