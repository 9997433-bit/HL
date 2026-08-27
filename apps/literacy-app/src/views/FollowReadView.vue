<script setup>
/**
 * 跟读评测的独立入口。
 *
 * 和《古诗详情》里的「跟着读」是同一个面板，区别是这里可以直接换一首诗，
 * 适合「今天就想练跟读」的场景；家长也能把这条路由直接收藏起来。
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import FollowReadPanel from '@/components/FollowReadPanel.vue'
import MascotCompanion from '@/components/MascotCompanion.vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { POEMS, getPoem, poemNewChars } from '@/data/poems.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({
  id: { type: String, default: '' }
})

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const { line: coachLine, mood: coachMood, next: coachNext } = useMascotCoach('poems')

/** 没指定读哪首就挑生字最少的那一首，跟读第一次不该从《江雪》开始。 */
const easiest = computed(
  () => [...POEMS].sort((a, b) => poemNewChars(a).length - poemNewChars(b).length)[0]
)

const picked = ref(props.id && getPoem(props.id) ? props.id : easiest.value.id)

const poem = computed(() => getPoem(picked.value) ?? easiest.value)

const record = computed(() => progress.state.poems?.[poem.value.id] ?? null)

watch(
  () => props.id,
  (value) => {
    if (value && getPoem(value)) picked.value = value
  }
)

function choose(event) {
  sfx.tap()
  const id = event.target.value
  picked.value = id
  router.replace(`/follow-read/${id}`)
}

function onScored(payload) {
  progress.recordFollowRead(poem.value.id, payload)
}
</script>

<template>
  <div class="page follow-read">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🎤</span>
          跟读评测
        </h2>
        <p class="muted">
          先听一遍范读，再自己大声读出来。设备能听清就逐字给你标出来，
          听不清就把你读的录下来放给你听——两种都不会把声音传到别的地方。
        </p>
      </div>
      <span v-if="record?.follows" class="pill">已跟读 {{ record.follows }} 次</span>
    </section>

    <label class="picker card card--flat">
      <span class="picker__label">今天读哪一首</span>
      <select class="picker__select" :value="poem.id" @change="choose">
        <option v-for="p in POEMS" :key="p.id" :value="p.id">
          {{ p.title }} · {{ p.dynasty }}{{ p.author }}（生字 {{ poemNewChars(p).length }}）
        </option>
      </select>
    </label>

    <section class="card preview">
      <h3 class="preview__title">
        {{ poem.title }}
        <small>{{ poem.dynasty }} · {{ poem.author }}</small>
      </h3>
      <p class="preview__body">{{ poem.lines.map((l) => l.text).join('') }}</p>
      <RouterLink class="btn" :to="`/poems/${poem.id}`" @click="sfx.tap()">
        📖 先看看这首诗讲什么
      </RouterLink>
    </section>

    <FollowReadPanel
      :key="poem.id"
      :lines="poem.lines"
      :title="poem.title"
      :speech-enabled="settings.speechEnabled !== false"
      @scored="onScored"
    />

    <MascotCompanion
      class="mascot-dock"
      :mood="coachMood"
      :say="coachLine"
      :size="70"
      :speak-on-tap="false"
      tap-hint="点我，换一句悄悄话"
      @tap="coachNext"
    />
  </div>
</template>

<style scoped>
.intro {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.intro__text {
  flex: 1;
  min-width: 0;
}

.intro__text .muted {
  margin-top: 4px;
  font-size: 0.86rem;
  line-height: 1.7;
}

.picker {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  flex-wrap: wrap;
}

.picker__label {
  font-weight: 800;
}

.picker__select {
  flex: 1;
  min-width: 200px;
  min-height: 44px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--surface-border);
  background: var(--surface);
  color: var(--text-strong);
  font-size: 0.9rem;
}

.preview {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  align-items: flex-start;
}

.preview__title {
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.preview__title small {
  margin-left: 8px;
  font-size: 0.78rem;
  font-weight: 700;
  font-family: inherit;
  color: var(--text-soft);
}

.preview__body {
  font-size: 1.02rem;
  line-height: 1.9;
  letter-spacing: 0.06em;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

@media (max-width: 560px) {
  .intro {
    flex-direction: column;
    align-items: stretch;
  }
  .intro .pill {
    align-self: flex-start;
  }
}
</style>
