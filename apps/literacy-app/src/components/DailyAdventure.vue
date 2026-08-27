<script setup>
/**
 * 首页的「今日冒险」卡：今天的三件小事，做完一件当场庆祝一下。
 *
 * 任务本身与判定都在 stores/dailyQuest.js 里，这里只管两件事：
 *  1. 把三件事摆成可勾选的清单——自动完成的会自己打勾，孩子也能自己勾；
 *  2. 每完成一件放一次微庆祝（星星 + 一声脆响 + 墨墨的一句话）。
 *
 * 庆祝一律是「锦上添花」：关掉动效只留文字与播报，进度照记不误。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import StarBurst from '@/components/StarBurst.vue'
import { useDailyQuestStore } from '@/stores/dailyQuest.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const quest = useDailyQuestStore()
const settings = useSettingsStore()

const root = ref(null)
const burstLayer = ref(null)
const cheer = ref('')
const announce = ref('')
let cheerTimer = null

const CHEERS = [
  '这一件搞定啦！',
  '厉害，再来一件？',
  '墨墨给你鼓掌 👏',
  '又前进了一步！',
  '记下了，今天你很棒'
]

const lead = computed(() => {
  if (quest.allDone) return '三件都做完了，今天的冒险圆满收工 🏅'
  const left = quest.tasks.length - quest.completedCount
  return `还剩 ${left} 件，做完一件就勾一个勾`
})

/** 星星从被完成的那一条上炸开，比从卡片正中炸开更像是「这件事」的奖励。 */
function originOf(id) {
  const host = root.value
  const item = host?.querySelector(`[data-quest="${id}"]`)
  if (!host || !item) return null
  const a = host.getBoundingClientRect()
  const b = item.getBoundingClientRect()
  return { x: b.left - a.left + b.width / 2, y: b.top - a.top + b.height / 2 }
}

function onToggle(task) {
  const done = quest.toggle(task.id)
  if (!done) {
    sfx.tap()
    announce.value = `「${task.title}」取消了勾选`
  }
}

watch(
  () => quest.justCompleted,
  (event) => {
    if (!event) return
    announce.value = `「${event.title}」完成啦，今日冒险 ${quest.completedCount} / ${quest.tasks.length}`
    sfx.star()
    if (!settings.reduceMotion) burstLayer.value?.burst(originOf(event.id))
    cheer.value = CHEERS[Math.floor(Math.random() * CHEERS.length)]
    if (cheerTimer) clearTimeout(cheerTimer)
    cheerTimer = window.setTimeout(() => {
      cheer.value = ''
    }, 2600)
  }
)

/** 页面开着过了一夜，回来时该换成新一天的任务。 */
function onVisible() {
  if (!document.hidden) quest.refresh()
}

onMounted(() => {
  quest.refresh()
  document.addEventListener('visibilitychange', onVisible)
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisible)
  if (cheerTimer) clearTimeout(cheerTimer)
})
</script>

<template>
  <section
    ref="root"
    class="card stack quest"
    :class="{ 'quest--done': quest.allDone }"
    data-daily-quest="true"
  >
    <h3 class="section-title">
      <OpenMojiIcon class="section-title__emoji" emoji="🗺️" :size="22" />
      今日冒险
      <span class="quest__count pill">{{ quest.completedCount }} / {{ quest.tasks.length }}</span>
    </h3>

    <p class="quest__lead muted">{{ lead }}</p>

    <ul class="quest__list">
      <li
        v-for="t in quest.tasks"
        :key="t.id"
        class="quest__item"
        :class="{ 'is-done': t.done }"
        :data-quest="t.id"
        :data-done="t.done ? 'true' : 'false'"
      >
        <button
          class="quest__check"
          type="button"
          role="checkbox"
          :aria-checked="t.done"
          :aria-labelledby="`quest-label-${t.id}`"
          @click="onToggle(t)"
        >
          <span class="quest__tick" aria-hidden="true">{{ t.done ? '✓' : '' }}</span>
        </button>

        <div class="quest__body">
          <p :id="`quest-label-${t.id}`" class="quest__title">
            <OpenMojiIcon :emoji="t.emoji" :size="20" />
            {{ t.title }}
          </p>
          <p class="quest__desc muted">{{ t.desc }}</p>
          <span class="quest__meter">
            <span class="quest__bar" aria-hidden="true">
              <span class="quest__fill" :style="{ width: `${t.percent}%` }" />
            </span>
            <small>{{ t.value }} / {{ t.goal }} {{ t.unit }}</small>
          </span>
        </div>

        <RouterLink v-if="!t.done" class="btn quest__go" :to="t.to" @click="sfx.tap()">
          {{ t.cta }}
        </RouterLink>
        <span v-else class="quest__stamp" aria-hidden="true">🎉</span>
      </li>
    </ul>

    <p v-if="cheer" class="quest__cheer">{{ cheer }}</p>
    <p class="sr-only" aria-live="polite">{{ announce }}</p>

    <StarBurst ref="burstLayer" />
  </section>
</template>

<style scoped>
.quest {
  position: relative;
}

.quest__count {
  margin-left: auto;
  font-size: 0.78rem;
}

.quest__lead {
  font-size: 0.85rem;
}

.quest__list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  list-style: none;
  margin: 0;
  padding: 0;
}

.quest__item {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid var(--surface-border);
  transition: background var(--dur-fast) ease, border-color var(--dur-fast) ease;
}

.quest__item.is-done {
  background: color-mix(in srgb, var(--mint-400) 20%, var(--surface-sunken));
  border-color: color-mix(in srgb, var(--mint-400) 55%, transparent);
}

.quest__check {
  flex: none;
  display: grid;
  place-items: center;
  width: var(--tap-min);
  height: var(--tap-min);
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  border: 3px solid var(--stroke-hint);
  color: var(--text-strong);
  font-size: 1.5rem;
  font-weight: 800;
  line-height: 1;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.quest__check:active {
  transform: scale(0.92);
}

.quest__check:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.is-done .quest__check {
  background: var(--mint-400);
  border-color: color-mix(in srgb, var(--mint-400) 70%, var(--stroke-ink));
}

.quest__body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.quest__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 1rem;
  font-weight: 800;
  color: var(--text-strong);
}

.is-done .quest__title {
  text-decoration: line-through;
  text-decoration-thickness: 2px;
  color: var(--text-soft);
}

.quest__desc {
  font-size: 0.78rem;
  line-height: 1.5;
}

.quest__meter {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.quest__bar {
  flex: 1;
  min-width: 60px;
  max-width: 160px;
  height: 8px;
  border-radius: 4px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.quest__fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: var(--brand);
  transition: width var(--dur-slow) var(--ease-pop);
}

.is-done .quest__fill {
  background: var(--mint-400);
}

.quest__meter small {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-soft);
  white-space: nowrap;
}

.quest__go {
  flex: none;
}

.quest__stamp {
  flex: none;
  font-size: 1.4rem;
  line-height: 1;
}

.quest__cheer {
  align-self: flex-start;
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  background: var(--accent-soft);
  color: var(--text-strong);
  font-size: 0.85rem;
  font-weight: 700;
  animation: quest-cheer 0.4s var(--ease-pop) backwards;
}

@keyframes quest-cheer {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.9);
  }
}

@media (max-width: 560px) {
  .quest__item {
    flex-wrap: wrap;
  }
  .quest__go {
    width: 100%;
  }
}
</style>
