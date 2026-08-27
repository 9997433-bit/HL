<script setup>
/**
 * 成就徽章展示架。
 *
 * 首页用 `mode="compact"`：只摆已点亮的，外加最接近的三枚，别把首页压垮；
 * 家长中心用 `mode="full"`：整面墙都摆出来，每枚都带进度条和解锁日期。
 *
 * 徽章不做「神秘成就」：没拿到的也照样显示名字、条件和差多少，
 * 孩子才知道往哪儿使劲，家长也能拿它当这周的小目标。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import gsap from 'gsap'
import { BADGE_TIERS } from '@/data/badges.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'

const props = defineProps({
  mode: { type: String, default: 'compact' },
  title: { type: String, default: '成就徽章' }
})

const progress = useProgressStore()
const settings = useSettingsStore()

const gridRef = ref(null)

const newIds = computed(() => new Set(progress.recentBadges.map((b) => b.id)))

const shown = computed(() => {
  const all = progress.badges
  if (props.mode === 'full') return all
  const unlocked = all.filter((b) => b.unlocked)
  const nearest = all
    .filter((b) => !b.unlocked)
    .sort((a, b) => b.percent - a.percent || a.goal - b.goal)
    .slice(0, 3)
  return [...unlocked, ...nearest]
})

const tierColor = (badge) => BADGE_TIERS[badge.tier]?.color ?? BADGE_TIERS.bronze.color

const dateOf = (ts) => (ts ? new Date(ts).toLocaleDateString('zh-CN') : '')

const summary = computed(
  () => `已点亮 ${progress.badgeCount} / ${progress.totalBadges} 枚徽章`
)

function pop(selector) {
  if (settings.reduceMotion) return
  const nodes = gridRef.value?.querySelectorAll(selector)
  if (!nodes?.length) return
  gsap.fromTo(
    nodes,
    { scale: 0.7, autoAlpha: 0 },
    {
      scale: 1,
      autoAlpha: 1,
      duration: 0.5,
      stagger: 0.06,
      ease: 'back.out(2)',
      clearProps: 'opacity,visibility,transform'
    }
  )
}

onMounted(() => pop('.badge'))

watch(
  () => progress.recentBadges.length,
  async (n) => {
    if (!n) return
    await nextTick()
    pop('.badge.is-new')
  }
)
</script>

<template>
  <section class="card stack">
    <h3 class="section-title">
      <span class="section-title__emoji" aria-hidden="true">🎖️</span>
      {{ title }}
      <span class="badges__count pill">{{ progress.badgeCount }} / {{ progress.totalBadges }}</span>
    </h3>
    <p class="sr-only">{{ summary }}</p>

    <div ref="gridRef" class="badges" :class="`badges--${mode}`">
      <article
        v-for="b in shown"
        :key="b.id"
        class="badge"
        :class="{ 'is-locked': !b.unlocked, 'is-new': newIds.has(b.id) }"
        :style="{ '--badge-color': tierColor(b) }"
        :data-badge="b.id"
        :data-unlocked="b.unlocked ? 'true' : 'false'"
      >
        <span class="badge__medal" aria-hidden="true">{{ b.unlocked ? b.emoji : '🔒' }}</span>
        <div class="badge__body">
          <strong class="badge__name">
            {{ b.name }}
            <small v-if="newIds.has(b.id)" class="badge__new">新</small>
          </strong>
          <small class="badge__desc muted">{{ b.desc }}</small>
          <span v-if="b.unlocked" class="badge__meta muted">
            {{ dateOf(b.unlockedAt) ? `${dateOf(b.unlockedAt)} 点亮` : '已点亮' }}
          </span>
          <template v-else>
            <span class="badge__bar" aria-hidden="true">
              <span class="badge__fill" :style="{ width: `${b.percent}%` }" />
            </span>
            <span class="badge__meta muted">{{ b.value }} / {{ b.goal }} {{ b.unit }}</span>
          </template>
        </div>
      </article>
    </div>

    <p v-if="mode === 'compact'" class="muted badges__foot">
      还差一点点的三枚也摆在这里，凑够就会自动点亮。
    </p>
  </section>
</template>

<style scoped>
.badges__count {
  margin-left: auto;
  font-size: 0.78rem;
}

.badges {
  display: grid;
  gap: var(--gap-sm);
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}

.badge {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--badge-color) 18%, var(--surface-sunken));
  border: 2px solid color-mix(in srgb, var(--badge-color) 55%, transparent);
}

.badge.is-locked {
  background: var(--surface-sunken);
  border-color: var(--stroke-hint);
  border-style: dashed;
}

.badge.is-new {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--star) 70%, transparent);
}

.badge__medal {
  flex: none;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: var(--surface-strong);
  font-size: 1.4rem;
  box-shadow: var(--shadow-sm);
}

.badge.is-locked .badge__medal {
  opacity: 0.6;
  filter: grayscale(0.7);
}

.badge__body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.badge__name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.98rem;
  font-weight: 800;
  color: var(--text-strong);
}

.badge__new {
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  background: var(--star);
  color: var(--text-strong);
  font-size: 0.66rem;
  font-weight: 800;
}

.badge__desc {
  font-size: 0.76rem;
  line-height: 1.5;
}

.badge__meta {
  font-size: 0.72rem;
  font-weight: 700;
}

.badge__bar {
  height: 6px;
  border-radius: 3px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.badge__fill {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: var(--badge-color);
  transition: width var(--dur-slow) var(--ease-pop);
}
</style>
