<script setup>
/**
 * 字源馆。
 *
 * 一屏之内回答两个问题：这个字当初是照着什么画的？后来怎么变成今天这样的？
 * 左边挑字，右边（窄屏是上面）演变。演变本身在 EtymologyStage 里，
 * 那个组件连同 GSAP 时间线是点进来之后才加载的。
 *
 * 分类按「六书」里的四类分：象形、指事、会意、形声。分类不是为了考孩子，
 * 是为了让「原来这一类字都长这样」这件事自己浮出来——看完五个三点水的字，
 * 不用讲他也知道下一个带「氵」的字八成和水有关。
 */
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ETYMOLOGY, ETYMOLOGY_KINDS, getEtymology } from '@/data/etymology.js'
import { getCharacter } from '@/data/characters.js'
import { speak } from '@/utils/speech.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

/**
 * 演变舞台按需加载：字源馆的字表和分类是纯文本，先让它们出来；
 * GSAP 时间线、笔顺数据这些重家伙等孩子真的选中一个字再说。
 */
const EtymologyStage = defineAsyncComponent(() => import('@/components/EtymologyStage.vue'))

const props = defineProps({ char: { type: String, default: '' } })

const router = useRouter()
const settings = useSettingsStore()

const filter = ref('all')

const decoded = computed(() => (props.char ? decodeURIComponent(props.char) : ''))
const picked = computed(() => (getEtymology(decoded.value) ? decoded.value : ETYMOLOGY[0].c))
const entry = computed(() => getEtymology(picked.value))
const pickedInfo = computed(() => getCharacter(picked.value))

const groups = computed(() =>
  ETYMOLOGY_KINDS.map((k) => ({
    ...k,
    chars: ETYMOLOGY.filter((e) => e.kind === k.id).map((e) => e.c)
  })).filter((g) => g.chars.length)
)

const shown = computed(() =>
  filter.value === 'all' ? groups.value : groups.value.filter((g) => g.id === filter.value)
)

function pick(char) {
  sfx.tap()
  router.replace(`/etymology/${encodeURIComponent(char)}`)
}

function setFilter(id) {
  sfx.tap()
  filter.value = id
}

function readAloud() {
  if (!entry.value) return
  sfx.tap()
  speak(`${picked.value}。${entry.value.origin}${entry.value.evolve}`, {
    rate: settings.speechRate - 0.05
  })
}

// 选中的字换了，就把这个字读一遍标题，让读屏用户知道右边换内容了
const heading = computed(() =>
  entry.value ? `「${picked.value}」的来历` : '字源馆'
)

watch(picked, () => window.scrollTo?.({ top: 0, behavior: 'auto' }))
</script>

<template>
  <div class="page ety-page">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🏺</span>
          字源馆
        </h2>
        <p class="muted">
          汉字大多不是凭空造出来的。这里的 {{ ETYMOLOGY.length }} 个字，
          每个都能看见它从一张小图变成今天写法的过程。
        </p>
        <p class="intro__note">
          说明：左边那张图是我们<strong>照着字源的意思画的示意图</strong>，
          不是甲骨文拓片。右边的字形和笔顺来自公开的汉字笔顺数据。
        </p>
      </div>
      <span class="pill">共 {{ ETYMOLOGY.length }} 个字</span>
    </section>

    <!-- 演变舞台 -->
    <section class="card stack stage" :aria-label="heading">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">✨</span>
        {{ heading }}
        <button class="btn btn--ghost btn--sm stage__say" type="button" @click="readAloud">
          🔊 读一读
        </button>
      </h3>

      <EtymologyStage :key="picked" :char="picked" :size="200" />

      <div class="stage__links">
        <RouterLink
          class="btn btn--ghost btn--sm"
          :to="`/learn/${encodeURIComponent(picked)}`"
          @click="sfx.tap()"
        >
          ✍️ 去写一写「{{ picked }}」
        </RouterLink>
        <span v-if="pickedInfo" class="pill">{{ pickedInfo.pinyin }} · {{ pickedInfo.strokes }} 画</span>
      </div>
    </section>

    <!-- 挑一个字 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🔎</span>
        挑一个字看看
      </h3>

      <div class="filters" role="group" aria-label="按字源分类筛选">
        <button
          class="chip"
          :class="{ 'is-on': filter === 'all' }"
          type="button"
          :aria-pressed="filter === 'all'"
          @click="setFilter('all')"
        >
          全部
        </button>
        <button
          v-for="k in groups"
          :key="k.id"
          class="chip"
          :class="{ 'is-on': filter === k.id }"
          type="button"
          :aria-pressed="filter === k.id"
          @click="setFilter(k.id)"
        >
          <span aria-hidden="true">{{ k.emoji }}</span>
          {{ k.name }} {{ k.chars.length }}
        </button>
      </div>

      <div v-for="g in shown" :key="g.id" class="group">
        <p class="group__title">
          <span aria-hidden="true">{{ g.emoji }}</span>
          <strong>{{ g.name }}</strong>
          <span class="muted">{{ g.desc }}</span>
        </p>
        <ul class="grid">
          <li v-for="c in g.chars" :key="c">
            <button
              class="glyphbtn"
              :class="{ 'is-on': c === picked }"
              type="button"
              :aria-current="c === picked ? 'true' : undefined"
              :aria-label="`看「${c}」的来历`"
              @click="pick(c)"
            >
              {{ c }}
            </button>
          </li>
        </ul>
      </div>
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
  line-height: 1.7;
}

.intro__note {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  font-size: 0.76rem;
  line-height: 1.6;
  color: var(--text-soft);
}

.stage__say {
  margin-left: auto;
}

.stage__links {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  min-height: 38px;
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--text);
  transition: border-color var(--dur-fast) ease, background var(--dur-fast) ease;
}

.chip.is-on {
  background: var(--brand-soft);
  border-color: var(--brand);
  color: var(--text-strong);
}

.group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group__title {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 0.9rem;
}

.group__title strong {
  color: var(--text-strong);
}

.group__title .muted {
  font-size: 0.76rem;
}

.grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fill, minmax(56px, 1fr));
  list-style: none;
  margin: 0;
  padding: 0;
}

.glyphbtn {
  width: 100%;
  min-height: 56px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  font-size: 1.7rem;
  line-height: 1;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease,
    background var(--dur-fast) ease;
}

.glyphbtn:hover {
  border-color: color-mix(in srgb, var(--brand) 45%, transparent);
}

.glyphbtn:active {
  transform: scale(0.94);
}

.glyphbtn.is-on {
  background: var(--accent-soft);
  border-color: var(--brand);
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
