<script setup>
/**
 * 成语书架。详情在 IdiomDetailView，这里只负责挑选与进度展示。
 */
import { computed, onMounted, ref } from 'vue'
import gsap from 'gsap'
import { IDIOMS } from '@/data/idioms.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()
const settings = useSettingsStore()

const shelfRef = ref(null)

const list = computed(() =>
  IDIOMS.map((i) => {
    const record = progress.idioms[i.id]
    return {
      ...i,
      seen: Boolean(record?.seen),
      quizRight: record?.quizRight ?? 0
    }
  })
)

/** 优先推荐还没看过的；全看完了就推荐还没答对过小测的。 */
const suggestion = computed(
  () => list.value.find((i) => !i.seen) ?? list.value.find((i) => !i.quizRight) ?? null
)

onMounted(() => {
  if (settings.reduceMotion) return
  const cards = shelfRef.value?.querySelectorAll('.idiom')
  if (!cards?.length) return
  gsap.from(cards, {
    opacity: 0,
    y: 24,
    scale: 0.93,
    duration: 0.4,
    ease: 'back.out(1.6)',
    stagger: 0.05
  })
})
</script>

<template>
  <div class="page">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🏮</span>
          成语启蒙
        </h2>
        <p class="muted">
          每条成语都配一个三格小故事。听完故事再做一道情景题，孩子就真的懂了。
        </p>
        <RouterLink
          v-if="suggestion"
          class="btn btn--primary intro__cta"
          :to="`/idioms/${suggestion.id}`"
          @click="sfx.tap()"
        >
          {{ suggestion.seen ? '再挑战' : '开始学' }}「{{ suggestion.word }}」 →
        </RouterLink>
      </div>
      <span class="pill">学过 {{ progress.idiomsSeen }} / {{ IDIOMS.length }}</span>
    </section>

    <section ref="shelfRef" class="shelf">
      <RouterLink
        v-for="i in list"
        :key="i.id"
        class="idiom"
        :to="`/idioms/${i.id}`"
        :style="{ '--c1': i.palette[0], '--c2': i.palette[1] }"
        @click="sfx.tap()"
      >
        <span class="idiom__emoji" aria-hidden="true">{{ i.emoji }}</span>
        <strong class="idiom__word">{{ i.word }}</strong>
        <span class="idiom__pinyin">{{ i.pinyin }}</span>
        <span class="idiom__meaning">{{ i.meaning }}</span>
        <span v-if="i.quizRight" class="idiom__badge" title="小测答对过">🏅</span>
        <span v-else-if="i.seen" class="idiom__badge" title="已经学过">✓</span>
      </RouterLink>
    </section>
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
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.intro__text .muted {
  font-size: 0.88rem;
}

.intro__cta {
  align-self: flex-start;
  margin-top: 4px;
}

.shelf {
  display: grid;
  gap: var(--gap-md);
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
}

.idiom {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: var(--gap-lg) var(--gap-md);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--c1) 0%, var(--c2) 100%);
  box-shadow: var(--shadow-md);
  text-align: center;
  color: #3d2f1f;
  transition: transform var(--dur-fast) var(--ease-pop), box-shadow var(--dur-fast) ease;
}

.idiom:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.idiom:active {
  transform: translateY(0) scale(0.97);
}

.idiom__emoji {
  font-size: 2.4rem;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.12));
}

.idiom__word {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.idiom__pinyin {
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  color: rgba(61, 47, 31, 0.72);
}

.idiom__meaning {
  margin-top: 4px;
  font-size: 0.8rem;
  line-height: 1.6;
  color: rgba(61, 47, 31, 0.85);
}

.idiom__badge {
  position: absolute;
  top: 10px;
  right: 12px;
  display: grid;
  place-items: center;
  min-width: 26px;
  height: 26px;
  padding: 0 7px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.78);
  font-size: 0.85rem;
  font-weight: 800;
}

@media (max-width: 560px) {
  .intro {
    flex-direction: column;
    align-items: stretch;
  }
  .intro .pill {
    align-self: flex-start;
  }
  .intro__cta {
    align-self: stretch;
  }
}
</style>
