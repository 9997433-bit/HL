<script setup>
/**
 * 应用外壳：背景层 + 顶栏 + 路由视图 + 底部导航 + 两个全局浮层
 * （庆祝彩带、护眼休息提醒）。
 *
 * 学习计时也放在这里：只在页面可见时走秒，切到后台就暂停，
 * 免得家长在报表里看到孩子「学了 3 小时」其实是忘了关标签页。
 */
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import NavBar from '@/components/NavBar.vue'
import EyeCareToggle from '@/components/EyeCareToggle.vue'
import ProgressRing from '@/components/ProgressRing.vue'

import { useProgressStore } from '@/stores/progress.js'
import { cancelSpeech, sfx } from '@/utils/audio.js'

const CelebrationLayer = defineAsyncComponent(() => import('@/components/CelebrationLayer.vue'))
const MascotCompanion = defineAsyncComponent(() => import('@/components/MascotCompanion.vue'))

const progress = useProgressStore()
const route = useRoute()

const isHome = computed(() => route.name === 'home')

let ticker = null

function startTicker() {
  if (ticker) return
  ticker = window.setInterval(() => {
    if (document.visibilityState === 'visible') progress.tickSecond()
  }, 1000)
}

function onVisibilityChange() {
  // 切到后台时把没读完的语音掐掉，否则回来还在念
  if (document.visibilityState !== 'visible') cancelSpeech()
}

onMounted(() => {
  progress.applyAppearance()
  startTicker()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  if (ticker) clearInterval(ticker)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  cancelSpeech()
})

/* ----------------------------------------------------------- 护眼休息提醒 */

const restMinutes = ref(0)

function takeRest() {
  sfx.tap()
  restMinutes.value = Math.floor(progress.sessionSeconds / 60)
  progress.acknowledgeRest()
}

/* ------------------------------------------------------------- 家长入口 */

const parentGateOpen = ref(false)
const gateAnswer = ref('')
const gateError = ref(false)

/** 一道随机两位数加法，挡住学龄前的孩子就够了，不必做真正的密码。 */
const gateQuestion = ref({ a: 0, b: 0 })

function openParentGate() {
  sfx.tap()
  gateQuestion.value = {
    a: 11 + Math.floor(Math.random() * 40),
    b: 11 + Math.floor(Math.random() * 40)
  }
  gateAnswer.value = ''
  gateError.value = false
  parentGateOpen.value = true
}

const gateOk = computed(
  () => Number(gateAnswer.value) === gateQuestion.value.a + gateQuestion.value.b
)
</script>

<template>
  <div class="shell">
    <!-- 背景：三团缓慢漂浮的色块，给页面一点纵深，不抢内容 -->
    <div class="shell__bg" aria-hidden="true">
      <span class="shell__blob shell__blob--a"></span>
      <span class="shell__blob shell__blob--b"></span>
      <span class="shell__blob shell__blob--c"></span>
    </div>

    <header class="topbar">
      <RouterLink v-if="!isHome" to="/" class="topbar__back" aria-label="回到乐园首页">
        <span aria-hidden="true">‹</span>
      </RouterLink>

      <div class="topbar__id">
        <span class="topbar__avatar" aria-hidden="true">{{ progress.state.avatar }}</span>
        <div class="topbar__meta">
          <strong>{{ progress.state.childName }}</strong>
          <small>Lv.{{ progress.state.level }} · ⭐ {{ progress.state.stars }}</small>
        </div>
      </div>

      <div class="topbar__actions">
        <ProgressRing
          :value="progress.levelProgress"
          :size="46"
          :thickness="6"
          color="var(--accent)"
        >
          <small class="topbar__ring">{{ progress.learnedCount }}</small>
        </ProgressRing>

        <EyeCareToggle />

        <button
          class="topbar__parent"
          type="button"
          aria-label="家长中心"
          @click="openParentGate"
        >
          👨‍👩‍👧
        </button>
      </div>
    </header>

    <main class="shell__main">
      <RouterView v-slot="{ Component }">
        <Transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
      <footer class="shell__footer">
        <span>快乐识字 v1.0.0 · 学习记录保存在本机</span>
        <RouterLink to="/privacy">隐私政策</RouterLink>
      </footer>
    </main>

    <NavBar />

    <CelebrationLayer v-if="progress.pendingCelebration" />

    <!-- 护眼休息提醒 -->
    <Transition name="fade-slide">
      <div v-if="progress.restDue" class="modal" role="dialog" aria-modal="true">
        <div class="modal__card card">
          <MascotCompanion mood="sleep" :size="88" say="看了好一会儿啦，我们一起看看窗外吧！" />
          <h2 class="section-title">
            <span class="section-title__emoji">🌿</span>
            该休息一下眼睛啦
          </h2>
          <p class="muted">
            已经连续学习 {{ Math.floor(progress.sessionSeconds / 60) }} 分钟。
            请把目光望向 6 米外的地方，慢慢眨眼 20 次。
          </p>
          <button class="btn btn--primary btn--block" type="button" @click="takeRest">
            好，我休息一下 🍃
          </button>
        </div>
      </div>
    </Transition>

    <!-- 家长入口验证 -->
    <Transition name="fade-slide">
      <div v-if="parentGateOpen" class="modal" role="dialog" aria-modal="true">
        <div class="modal__card card">
          <h2 class="section-title">
            <span class="section-title__emoji">🔒</span>
            请家长回答
          </h2>
          <p class="muted">这道题是为了确认现在操作的是大人。</p>
          <p class="gate__q">{{ gateQuestion.a }} + {{ gateQuestion.b }} = ?</p>
          <input
            v-model="gateAnswer"
            class="gate__input"
            type="number"
            inputmode="numeric"
            placeholder="输入答案"
            aria-label="计算结果"
            @keydown.enter="gateError = !gateOk"
          />
          <p v-if="gateError" class="gate__err">再算一次试试 🙂</p>
          <div class="row" style="justify-content: flex-end">
            <button class="btn btn--ghost" type="button" @click="parentGateOpen = false">
              取消
            </button>
            <RouterLink
              v-if="gateOk"
              class="btn btn--primary"
              to="/parent"
              @click="parentGateOpen = false"
            >
              进入家长中心
            </RouterLink>
            <button v-else class="btn btn--primary" type="button" @click="gateError = true">
              确定
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 休息完成的小提示 -->
    <Transition name="fade-slide">
      <p v-if="restMinutes > 0" class="rest-toast" @click="restMinutes = 0">
        🍃 休息好了，刚才学了 {{ restMinutes }} 分钟，真棒！
      </p>
    </Transition>
  </div>
</template>

<style scoped>
.shell {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
  background-attachment: fixed;
}

.shell__bg {
  position: fixed;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.shell__blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  animation: float-y 12s ease-in-out infinite;
}

.shell__blob--a {
  width: 42vmax;
  height: 42vmax;
  top: -14vmax;
  left: -10vmax;
  background: var(--bg-blob-a);
}

.shell__blob--b {
  width: 34vmax;
  height: 34vmax;
  bottom: -10vmax;
  right: -8vmax;
  background: var(--bg-blob-b);
  animation-delay: -4s;
  animation-duration: 15s;
}

.shell__blob--c {
  width: 26vmax;
  height: 26vmax;
  top: 38%;
  right: 22%;
  background: var(--bg-blob-c);
  animation-delay: -8s;
  animation-duration: 18s;
}

/* ------------------------------------------------------------------ 顶栏 */

.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 10px max(12px, env(safe-area-inset-left)) 10px max(12px, env(safe-area-inset-right));
  background: color-mix(in srgb, var(--bg-page-solid) 82%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--surface-border);
}

.topbar__back {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  flex: none;
  font-size: 1.9rem;
  font-weight: 800;
  line-height: 1;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
  color: var(--text-strong);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.topbar__back:active {
  transform: scale(0.9);
}

.topbar__id {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.topbar__avatar {
  font-size: 1.75rem;
  line-height: 1;
}

.topbar__meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
}

.topbar__meta strong {
  color: var(--text-strong);
  font-size: 0.98rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar__meta small {
  color: var(--text-soft);
  font-size: 0.76rem;
}

.topbar__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.topbar__ring {
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--text-strong);
}

.topbar__parent {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
  box-shadow: var(--shadow-sm);
  font-size: 1.25rem;
  transition: transform var(--dur-fast) var(--ease-pop);
}

.topbar__parent:active {
  transform: scale(0.92);
}

/* ----------------------------------------------------------------- 主体 */

.shell__main {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.shell__footer {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--gap-sm);
  width: min(1080px, calc(100% - 2 * var(--gap-md)));
  margin: auto auto 96px;
  color: var(--text-soft);
  font-size: var(--fs-sm);
  text-align: center;
}

.shell__footer a {
  display: inline-flex;
  align-items: center;
  min-height: var(--tap-min);
  padding-inline: var(--gap-md);
  border-radius: var(--radius-pill);
  color: var(--accent);
  font-weight: var(--fw-bold);
  text-decoration: underline;
  text-underline-offset: var(--gap-2xs);
}

/* ----------------------------------------------------------------- 浮层 */

.modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: var(--gap-md);
  background: rgba(20, 14, 6, 0.42);
  backdrop-filter: blur(4px);
}

.modal__card {
  width: min(420px, 100%);
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  align-items: stretch;
}

.gate__q {
  font-size: 2rem;
  font-weight: 900;
  color: var(--text-strong);
  text-align: center;
}

.gate__input {
  width: 100%;
  min-height: var(--tap-min);
  padding: 0 18px;
  border-radius: var(--radius-md);
  border: 2px solid var(--surface-border);
  background: var(--surface-sunken);
  font-size: 1.2rem;
  text-align: center;
}

.gate__err {
  color: var(--danger);
  text-align: center;
  font-weight: 700;
}

.rest-toast {
  position: fixed;
  left: 50%;
  bottom: 96px;
  transform: translateX(-50%);
  z-index: 70;
  padding: 12px 22px;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
  box-shadow: var(--shadow-lg);
  font-weight: 700;
  color: var(--text-strong);
  cursor: pointer;
  white-space: nowrap;
}

@media (max-width: 420px) {
  .topbar__meta small {
    font-size: 0.7rem;
  }
}
</style>
