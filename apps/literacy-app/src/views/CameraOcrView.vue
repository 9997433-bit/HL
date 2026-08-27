<script setup>
/**
 * 拍照识字 —— 把生活里遇到的字拍下来，当场认出来。
 *
 * 交互只有一步：给一张图，剩下的全自动。给图有三条路——
 *   拍一张   手机 / 平板直接调后置摄像头（capture="environment"）
 *   相册选   电脑上没有摄像头，或者想认之前拍过的照片
 *   试一试   内置示例图，没有相机权限也能完整走一遍，第一次用也知道会发生什么
 * 三条路都落到同一个 <input type="file">：比 getUserMedia 少一层权限弹窗，
 * 而且 Android WebView 里的表现和浏览器一致。
 *
 * 认出来的字分两堆摆：字库里有的可以点进单字页看拼音、释义、笔顺；
 * 字库里没有的如实列出来，不硬编一段释义糊弄孩子。
 *
 * 引擎近 6 MB，只有真的给了图才 import()，进这一页本身不下载任何 wasm。
 */
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import MascotCompanion from '@/components/MascotCompanion.vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { useOcr } from '@/composables/useOcr.js'
import { loadCharacter } from '@/data/characters.js'
import { ocrAssetUrl, OCR_PACK } from '@/utils/ocr.js'
import { sfx } from '@/utils/sfx.js'
import { speak } from '@/utils/speech.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const { busy, checkPack, hint, pack, packMb, phase, progress, reset, result, run } = useOcr()
const { line: coachLine, mood: coachMood, next: coachNext } = useMascotCoach('learn')

const cameraInput = ref(null)
const albumInput = ref(null)
const photoUrl = ref('')
const photoName = ref('')
/** 认出来的字 → 讲解，按需从单元详情包里取。 */
const lessons = shallowRef(new Map())

const percent = computed(() => Math.round(progress.value * 100))
const known = computed(() => result.value?.known ?? [])
const unknown = computed(() => result.value?.unknown ?? [])

const STEPS = [
  { icon: '📷', text: '对准书本、路牌或者包装袋上的字，拍清楚一点' },
  { icon: '🔍', text: '等它认几秒钟，第一次要先把认字引擎装好' },
  { icon: '📖', text: '认出字库里的字就能点进去，看拼音、听读音、写笔顺' }
]

onMounted(checkPack)

function pick(input) {
  sfx.tap()
  input?.click()
}

async function useFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  photoName.value = file.name || '刚拍的照片'
  await start(file)
}

async function useSample() {
  sfx.tap()
  photoName.value = '示例照片'
  await start(ocrAssetUrl(OCR_PACK.sample))
}

async function start(source) {
  if (busy.value) return
  if (photoUrl.value.startsWith('blob:')) URL.revokeObjectURL(photoUrl.value)
  photoUrl.value = typeof source === 'string' ? source : URL.createObjectURL(source)
  lessons.value = new Map()
  const data = await run(source)
  if (data?.known.length) sfx.correct()
}

function again() {
  sfx.tap()
  if (photoUrl.value.startsWith('blob:')) URL.revokeObjectURL(photoUrl.value)
  photoUrl.value = ''
  photoName.value = ''
  lessons.value = new Map()
  reset()
}

/** 讲解在详情包里，认出哪个字才下哪一包，不为了一张照片把整本课文拉下来。 */
watch(known, async (chars) => {
  if (!chars.length) return
  const packs = await Promise.all(chars.map((char) => loadCharacter(char)))
  const next = new Map()
  packs.forEach((entry, i) => entry && next.set(chars[i], entry))
  lessons.value = next
})

function say(char) {
  sfx.tap()
  speak(char)
}
</script>

<template>
  <div class="page ocr" :data-phase="phase">
    <section class="card card--strong ocr__intro">
      <p class="ocr__eyebrow">拍照识字</p>
      <h2 class="ocr__title">看到不认识的字，拍下来问我</h2>
      <p class="ocr__desc">
        认字全部在这台设备上完成，照片不会传到任何地方，断网也照样能认。
      </p>

      <ol class="ocr__steps">
        <li v-for="s in STEPS" :key="s.text" class="ocr__step">
          <OpenMojiIcon class="ocr__step-icon" :emoji="s.icon" :size="26" />
          <span>{{ s.text }}</span>
        </li>
      </ol>

      <p class="ocr__pack" :data-ready="pack.ready === true">
        <template v-if="pack.ready === true">
          🧳 离线识字包 {{ packMb }} MB，第一次认字时下载，之后一直留在这台设备上。
        </template>
        <template v-else-if="pack.ready === false">
          ⚠️ 识字包没装上，重新构建一次 App 就会自动备好。
        </template>
        <template v-else>🧳 正在看识字包在不在…</template>
      </p>
    </section>

    <section class="card ocr__deck">
      <div class="ocr__acts">
        <button class="btn btn--primary btn--lg" :disabled="busy" @click="pick(cameraInput)">
          📷 拍一张
        </button>
        <button class="btn btn--lg" :disabled="busy" @click="pick(albumInput)">
          🖼️ 相册选一张
        </button>
        <button class="btn btn--lg" :disabled="busy" @click="useSample">
          ✨ 试一张示例
        </button>
        <button v-if="phase !== 'idle'" class="btn btn--lg" :disabled="busy" @click="again">
          ↩️ 换一张
        </button>
      </div>

      <!-- 两个 input 分开：拍照那个要 capture，相册那个不能带，否则安卓直接跳相机 -->
      <input
        ref="cameraInput"
        class="sr-only"
        type="file"
        accept="image/*"
        capture="environment"
        aria-label="用摄像头拍一张照片"
        @change="useFile"
      />
      <input
        ref="albumInput"
        class="sr-only"
        type="file"
        accept="image/*"
        aria-label="从相册里选一张照片"
        @change="useFile"
      />

      <figure v-if="photoUrl" class="ocr__shot">
        <img class="ocr__photo" :src="photoUrl" :alt="`要认字的照片：${photoName}`" />
        <figcaption class="ocr__shot-cap">{{ photoName }}</figcaption>
      </figure>

      <p class="ocr__hint">{{ hint }}</p>
      <div
        v-if="busy"
        class="ocr__bar"
        role="progressbar"
        aria-label="认字进度"
        :aria-valuenow="percent"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <span class="ocr__bar-fill" :style="{ width: `${percent}%` }" />
      </div>
      <p class="sr-only ocr__live" aria-live="polite">{{ hint }}</p>
    </section>

    <section v-if="phase === 'done'" class="stack ocr__out">
      <h3 class="section-title">
        <OpenMojiIcon class="section-title__emoji" name="open-book" :size="22" />
        认出来的字
      </h3>

      <ul v-if="known.length" class="ocr__hits">
        <li v-for="char in known" :key="char">
          <RouterLink
            class="ocr__hit card--tap"
            :data-char="char"
            :to="`/learn/${encodeURIComponent(char)}`"
            @click="sfx.tap()"
          >
            <strong class="ocr__hit-char">{{ char }}</strong>
            <span class="ocr__hit-body">
              <span class="ocr__hit-pinyin">{{ lessons.get(char)?.pinyin ?? '…' }}</span>
              <span class="ocr__hit-meaning">
                {{ lessons.get(char)?.meaning ?? '正在翻讲解…' }}
              </span>
              <span v-if="lessons.get(char)?.words?.length" class="ocr__hit-words">
                {{ lessons.get(char).words.slice(0, 3).map((w) => w.w).join('　') }}
              </span>
            </span>
            <span class="ocr__hit-go">去学 →</span>
          </RouterLink>
          <button class="ocr__say" :aria-label="`听「${char}」怎么读`" @click.stop="say(char)">
            🔊
          </button>
        </li>
      </ul>

      <p v-else class="card card--sunken ocr__empty">
        这张照片里没认出字库里的字。把镜头凑近一点、让字更大更清楚，再拍一次试试。
      </p>

      <p v-if="unknown.length" class="card card--sunken ocr__miss">
        还认出了 <strong>{{ unknown.join('　') }}</strong>，这些字还没进字库，
        暂时讲不了；等字表长大就能查到啦。
      </p>

      <p class="ocr__stat muted">
        用时 {{ (result.ms / 1000).toFixed(1) }} 秒 · 把握 {{ result.confidence }} 分
      </p>
    </section>

    <MascotCompanion
      class="mascot-dock"
      :mood="coachMood"
      :say="coachLine"
      :size="72"
      :speak-on-tap="false"
      tap-hint="点我，换一句悄悄话"
      @tap="coachNext"
    />
  </div>
</template>

<style scoped>
.ocr {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.ocr__intro {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.ocr__eyebrow {
  font-size: var(--fs-sm);
  font-weight: var(--fw-heavy);
  letter-spacing: 0.24em;
  color: var(--text-soft);
}

.ocr__title {
  font-size: var(--fs-xl);
  font-weight: var(--fw-black);
  color: var(--text-strong);
}

.ocr__desc {
  line-height: var(--lh-loose);
  color: var(--text);
}

.ocr__steps {
  display: flex;
  flex-direction: column;
  gap: var(--gap-2xs);
  margin: var(--gap-2xs) 0 0;
  padding: 0;
  list-style: none;
  counter-reset: ocr-step;
}

.ocr__step {
  display: flex;
  align-items: flex-start;
  gap: var(--gap-xs);
  line-height: var(--lh-base);
  color: var(--text);
}

.ocr__step::before {
  counter-increment: ocr-step;
  content: counter(ocr-step);
  flex: none;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--text-strong);
  font-family: var(--font-num);
  font-size: 0.74rem;
  font-weight: var(--fw-black);
}

.ocr__step-icon {
  flex: none;
}

.ocr__pack {
  margin-top: var(--gap-2xs);
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border-left: 4px solid var(--brand);
  font-size: 0.86rem;
  line-height: var(--lh-base);
  color: var(--text);
}

.ocr__pack[data-ready='false'] {
  border-left-color: var(--coral-400);
}

/* ------------------------------------------------------------------ 取图 */

.ocr__deck {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.ocr__acts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-xs);
}

.ocr__shot {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--gap-2xs);
}

.ocr__photo {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 1px solid var(--surface-border);
}

.ocr__shot-cap {
  font-size: 0.78rem;
  color: var(--text-soft);
}

.ocr__hint {
  font-weight: var(--fw-bold);
  line-height: var(--lh-base);
  color: var(--text-strong);
}

.ocr__bar {
  height: 10px;
  border-radius: var(--radius-pill);
  background: var(--stroke-hint);
  overflow: hidden;
}

.ocr__bar-fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--brand);
  transition: width var(--dur-mid) ease;
}

@media (prefers-reduced-motion: reduce) {
  .ocr__bar-fill {
    transition: none;
  }
}

/* ------------------------------------------------------------------ 结果 */

.ocr__out {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.ocr__hits {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
  list-style: none;
  padding: 0;
  margin: 0;
}

.ocr__hits li {
  display: flex;
  align-items: stretch;
  gap: var(--gap-2xs);
}

.ocr__hit {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  min-height: var(--tap-min);
  padding: var(--gap-sm) var(--gap-md);
  border-radius: var(--radius-md);
  border: 2px solid var(--surface-border);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  color: var(--text);
}

.ocr__hit-char {
  flex: none;
  display: grid;
  place-items: center;
  width: 62px;
  height: 62px;
  border-radius: var(--radius-md);
  background: var(--brand-soft);
  font-family: var(--font-hanzi);
  font-size: 2.1rem;
  font-weight: var(--fw-black);
  color: var(--text-strong);
}

.ocr__hit-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.ocr__hit-pinyin {
  font-size: 0.92rem;
  font-weight: var(--fw-heavy);
  color: var(--brand-strong);
}

.ocr__hit-meaning {
  font-size: 0.88rem;
  line-height: var(--lh-base);
  color: var(--text);
}

.ocr__hit-words {
  font-size: 0.8rem;
  color: var(--text-soft);
}

.ocr__hit-go {
  margin-left: auto;
  flex: none;
  font-size: 0.82rem;
  font-weight: var(--fw-heavy);
  color: var(--text-strong);
}

.ocr__say {
  flex: none;
  width: var(--tap-min);
  border-radius: var(--radius-md);
  border: 2px solid var(--surface-border);
  background: var(--surface-sunken);
  font-size: 1.2rem;
}

.ocr__empty,
.ocr__miss {
  line-height: var(--lh-loose);
  color: var(--text);
}

.ocr__miss strong {
  font-size: 1.15rem;
  color: var(--text-strong);
}

.ocr__stat {
  font-size: 0.78rem;
}

@media (max-width: 420px) {
  .ocr__hit-go {
    display: none;
  }
}
</style>
