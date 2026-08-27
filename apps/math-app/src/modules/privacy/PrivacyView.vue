<script setup>
const APP_VERSION = '1.0.0'
const EFFECTIVE_DATE = '2026-08-27'
</script>

<template>
  <main class="page stack privacy-page" data-privacy-page="math">
    <header class="card privacy-hero">
      <div aria-hidden="true" class="privacy-hero__icon">🛡️</div>
      <div>
        <p class="kicker">给家长的说明</p>
        <h1 class="page-title">MathQuest 隐私政策</h1>
        <p class="dim">版本 {{ APP_VERSION }} · 生效日期 {{ EFFECTIVE_DATE }}</p>
      </div>
    </header>

    <section class="card policy-section" aria-labelledby="math-summary">
      <h2 id="math-summary">先说结论</h2>
      <p>
        MathQuest 不要求注册账号，不接入广告、行为分析或遥测 SDK，也不向项目维护者
        上传学习记录。孩子的答题进度和家长设置默认只保存在当前设备上。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="math-local-data">
      <h2 id="math-local-data">保存在设备上的数据</h2>
      <ul>
        <li>答题与学习进度：掌握度、错题、错因、连胜、徽章和每日冒险记录；</li>
        <li>家长设置：年龄档、每日时长、显示主题、音效和减少动效偏好；</li>
        <li>离线缓存：应用代码和课程资源。</li>
      </ul>
      <p>
        数据通过浏览器本地存储保留，不会由本项目建立远端副本。清除站点数据或卸载
        App 可能删除本机记录；家长可以先在家长中心导出 JSON 备份，也可以在那里清空记录。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="math-permissions">
      <h2 id="math-permissions">设备权限</h2>
      <p>
        数学课程不需要相机、麦克风、通讯录或精确位置权限。音效由设备本地生成；
        关闭音效或减少动效不会影响答题、错题复习和学习报告。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="math-network">
      <h2 id="math-network">网络访问与第三方</h2>
      <p>
        应用安装或首次加载后可以离线学习，运行时不需要第三方账号，也不会把答题记录
        发送给广告商、分析服务或项目维护者。发布者用于分发网页或安装包的托管平台
        可能按其自身政策记录常规访问日志。
      </p>
      <p>
        应用使用的开源代码和图标的来源与许可见发行包内的
        <code>THIRD_PARTY_NOTICES.md</code>。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="math-children">
      <h2 id="math-children">儿童隐私与家长控制</h2>
      <p>
        本应用面向儿童数学学习，但不向项目维护者收集姓名、联系方式、精确位置、
        广告标识符或学习画像。数据导出、清空、年龄档和使用时长等设置集中在家长中心，
        并由家长验证题保护。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="math-contact">
      <h2 id="math-contact">政策更新与联系</h2>
      <p>
        隐私行为发生实质变化时，本页会更新生效日期和版本说明。若要反馈隐私问题，
        请通过本项目代码仓库的问题反馈渠道联系维护者。
      </p>
      <div class="policy-actions">
        <RouterLink class="btn btn--primary" to="/parent">打开家长中心</RouterLink>
        <RouterLink class="btn btn--ghost" to="/">返回数学首页</RouterLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
.privacy-page {
  max-width: 860px;
}

.privacy-hero {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
}

.privacy-hero__icon {
  display: grid;
  place-items: center;
  flex: none;
  width: var(--tap-hero);
  height: var(--tap-hero);
  border-radius: var(--radius-lg);
  background: var(--accent-soft);
  font-size: var(--fs-display);
}

.privacy-hero .page-title {
  margin: var(--gap-2xs) 0;
  font-size: var(--fs-2xl);
  line-height: var(--lh-tight);
}

.policy-section {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.policy-section h2 {
  font-size: var(--fs-xl);
}

.policy-section p,
.policy-section li {
  line-height: var(--lh-loose);
}

.policy-section ul {
  display: grid;
  gap: var(--gap-xs);
  padding-left: var(--gap-lg);
  list-style: disc;
}

.policy-section code {
  font-family: ui-monospace, monospace;
  overflow-wrap: anywhere;
}

.policy-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
  margin-top: var(--gap-xs);
}

@media (max-width: 480px) {
  .privacy-hero {
    align-items: flex-start;
  }

  .privacy-hero__icon {
    width: var(--tap-comfy);
    height: var(--tap-comfy);
  }

  .policy-actions > * {
    width: 100%;
  }
}
</style>
