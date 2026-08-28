<script setup>
const APP_VERSION = '1.0.0'
const EFFECTIVE_DATE = '2026-08-27'
</script>

<template>
  <div class="page privacy-page" data-privacy-page="literacy">
    <header class="card privacy-hero">
      <div aria-hidden="true" class="privacy-hero__icon">🛡️</div>
      <div>
        <p class="privacy-hero__eyebrow">给家长的说明</p>
        <h1>快乐识字隐私政策</h1>
        <p class="muted">
          版本 {{ APP_VERSION }} · 生效日期 {{ EFFECTIVE_DATE }}
        </p>
      </div>
    </header>

    <section class="card policy-section" aria-labelledby="literacy-summary">
      <h2 id="literacy-summary">先说结论</h2>
      <p>
        快乐识字不要求注册账号，不接入广告、行为分析或遥测 SDK，也不向项目维护者
        上传学习记录。孩子的课程进度和家长设置默认只保存在当前设备的浏览器存储中。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="literacy-local-data">
      <h2 id="literacy-local-data">保存在设备上的数据</h2>
      <ul>
        <li>学习进度：认识的字、练习结果、复习安排、徽章和阅读记录；</li>
        <li>家长设置：每日学习目标、显示主题、音效、动效和语音偏好；</li>
        <li>离线缓存：应用代码、课程资源、笔顺数据和 OCR 模型。</li>
      </ul>
      <p>
        这些数据不会由本项目建立远端副本。清除浏览器站点数据或卸载 App 可能同时
        删除本机记录；家长可以先在家长中心导出 JSON 备份，也可以在那里清空记录。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="literacy-permissions">
      <h2 id="literacy-permissions">相机、麦克风与语音</h2>
      <ul>
        <li>
          <strong>相机 / 图片：</strong>仅在家长或孩子主动使用“拍照识字”时读取，
          图像由设备上的 Tesseract OCR 处理，本项目不上传或保存原图。
        </li>
        <li>
          <strong>麦克风：</strong>仅在主动开始跟读时使用。录音回放与离线评测不上传，
          离开页面后不作为课程档案保存。
        </li>
        <li>
          <strong>浏览器逐字识别：</strong>默认关闭。家长显式开启后，浏览器提供商的
          SpeechRecognition 实现可能使用在线服务，并受该提供商自己的隐私条款约束。
        </li>
        <li>
          <strong>朗读：</strong>使用设备或浏览器提供的语音合成功能；应用不采集孩子的声音。
        </li>
      </ul>
      <p>拒绝相机或麦克风权限不影响字表、绘本、小游戏等其他功能。</p>
    </section>

    <section class="card policy-section" aria-labelledby="literacy-network">
      <h2 id="literacy-network">网络访问与第三方</h2>
      <p>
        内置课程可离线使用，正常学习不需要第三方账号。课程字表之外的笔顺数据若本地
        缺失，应用可能向 jsDelivr 请求对应的 Hanzi Writer Data 文件；该请求会让网络
        服务提供方接触常规连接信息（例如 IP 地址）。应用不会在该请求中发送学习记录。
      </p>
      <p>
        应用使用的开源代码、字形数据、OCR 模型与图标的来源和许可见发行包内的
        <code>THIRD_PARTY_NOTICES.md</code>。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="literacy-children">
      <h2 id="literacy-children">儿童隐私与家长控制</h2>
      <p>
        本应用面向儿童学习场景，但不向项目维护者收集姓名、联系方式、精确位置、
        广告标识符或学习画像。涉及数据导出、清空、在线语音识别和使用时长的设置集中在
        家长中心，并由家长验证题保护。
      </p>
    </section>

    <section class="card policy-section" aria-labelledby="literacy-contact">
      <h2 id="literacy-contact">政策更新与联系</h2>
      <p>
        隐私行为发生实质变化时，本页会更新生效日期和版本说明。若要反馈隐私问题，
        请通过本项目代码仓库的问题反馈渠道联系维护者。
      </p>
      <div class="policy-actions">
        <RouterLink class="btn btn--primary" to="/parent">打开家长中心</RouterLink>
        <RouterLink class="btn btn--ghost" to="/">返回识字首页</RouterLink>
      </div>
    </section>
  </div>
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

.privacy-hero__eyebrow {
  color: var(--accent);
  font-size: var(--fs-sm);
  font-weight: var(--fw-heavy);
}

.privacy-hero h1 {
  margin: var(--gap-2xs) 0;
  color: var(--text-strong);
  font-size: var(--fs-2xl);
  line-height: var(--lh-tight);
}

.policy-section {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.policy-section h2 {
  color: var(--text-strong);
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
