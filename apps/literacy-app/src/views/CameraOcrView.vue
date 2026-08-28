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
 * 认不出来的时候（ROUND11_H2）：这套离线引擎在手写体、艺术字、断笔喷漆字上
 * 会稳定地失手，基准集里那张喷漆「小心地滑」到今天也只认得出 3 个字。
 * 所以「没认出来」不是异常分支，是常态的一半。界面在这半边不能只丢一句
 * 「没认出来」把锅甩回给孩子——RETRY_TIPS 那三条对应现场真正改得动的三件事：
 * 光线、取景、换一张。低置信度也单独说一声，免得孩子把「认错了」当成「就是这个字」。
 *
 * ROUND12_H2 把这一半再拆细：同样是「认不出」，太暗、拍糊和取景里根本没有成行的字，
 * 该做的事完全不同，一组通用话术等于每条都只说对三分之一。preprocess() 顺手量出的
 * 曝光与锐度（result.photo）够分辨这三种，于是 reason 一分岔，话术、标题和
 * data-trouble 跟着一起分岔。
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

/**
 * 认不出时给的三条路，按「改了最可能有用」排：
 * 先调光线（暗和反光是最常见的原因），再调取景，最后承认换一张更快。
 * 第三条特意把边界说破——手写体和艺术字它现在真的认不出来，
 * 让孩子在同一张照片上反复重拍才是真的耽误时间。
 *
 * 这三条是兜底：说不清这次到底是暗还是糊的时候，它们永远给得出。
 */
const RETRY_TIPS = [
  { icon: '💡', text: '换个亮一点的地方，别让手影或者灯的反光压在字上' },
  { icon: '🔍', text: '把镜头凑近，让那几个字占满大半个画面，端稳一秒再拍' },
  { icon: '↩️', text: '还认不出就换一张：手写体、艺术字和褪色的招牌，它现在确实认不了' }
]

/**
 * 按失败原因分岔的话术（ROUND12_H2）。
 *
 * 兜底那三条对着「所有失败」讲，代价是每一条都只说了三分之一有用的话：
 * 照片黑得看不见笔画时让人「凑近一点」是废话，糊成一团时让人「找个亮地方」也一样。
 * utils/ocr.js 的 preprocess() 顺手量了曝光和锐度（result.photo），
 * 有这两个数就能说得具体些——每一组仍然保留「换一张 + 认不了哪一类字」那条出口，
 * 免得孩子对着同一张手写照片一遍遍重拍。
 */
const REASON_TIPS = {
  dim: [
    { icon: '🌙', text: '这张太暗了，笔画糊进背景里。开个灯，或者走到窗边再拍一张' },
    { icon: '🙌', text: '低头拍的时候手和身体常常正好挡住光，换个方向站' },
    { icon: '↩️', text: '实在补不了光就换一张：太暗的照片它认不出来，不是你的错' }
  ],
  blurry: [
    { icon: '💫', text: '字的边缘糊掉了。双手端住手机，先等画面停稳一秒再按' },
    { icon: '👆', text: '离得太近反而对不上焦——退开一点，点一下屏幕上的字再拍' },
    { icon: '↩️', text: '还是糊就换一张：拍糊的照片和褪色的招牌，它现在确实认不了' }
  ],
  blank: [
    { icon: '🔎', text: '画面里没找到成行的字。让那几个字占满大半个画面，别把整面墙都拍进来' },
    { icon: '📐', text: '把手机摆正，跟字面平行，字歪着或者斜着它就连不成一行' },
    { icon: '↩️', text: '换一张也行：手写体、艺术字和褪色的招牌，它现在确实认不了' }
  ]
}

/** 认得出但把握不大：分数低于这条线就先提醒一句，别让孩子把认错的字当真。 */
const SHAKY_CONFIDENCE = 60

/**
 * 判「暗」和「糊」的三条线，都是拿 scripts/fixtures/ocr 那二十张基准图量出来的
 * （实测表见 .agent_workspace/r12-ocr-matrix.md §4）。定线的原则只有一条：
 * **宁可退回兜底话术，也不要对着一张其实没问题的照片说「你拍糊了」。**
 * 所以每条线都压在二十张里最极端那张之外——这二十张全都认得出，
 * 谁也不该被这套分支挑出毛病。
 *
 * DIM_LUMA / DIM_SPAN：光看平均亮度会冤枉黑板。低光字卡的均值只有 29、
 * 黑板粉笔落款 31，可它们的灰阶跨度都在 110 以上——画面是暗的，笔画不是，
 * 而且两张都认得出四个字。所以「暗」要两条同时踩中：整体压暗（<60）
 * 且灰度全挤在一小段里（<100）。二十张里没有一张同时满足。
 *
 * BLUR_SHARPNESS：二十张的锐度（拉伸后横向梯度的 99 分位）落在 6–53，
 * 最软的是暖光字卡的 6，其次是斜拍字卡和拍糊的便签，都是 13。线放在 6，
 * 取严格小于——比基准集里最软的那张还软，才敢说这是糊了。
 */
const DIM_LUMA = 60
const DIM_SPAN = 100
const BLUR_SHARPNESS = 6

/** 引擎跑完了，一个字都没落进结果里——最需要那三条话术的就是这一格。 */
const blank = computed(
  () => phase.value === 'done' && !known.value.length && !unknown.value.length
)

/** 认出了字，但置信度不高：照片多半太暗、太糊或者字太小。 */
const shaky = computed(
  () =>
    phase.value === 'done' &&
    Boolean(known.value.length || unknown.value.length) &&
    (result.value?.confidence ?? 100) < SHAKY_CONFIDENCE
)

/** 三种失败摆同一张降级卡：认了一场空、认得不准、引擎自己出错。 */
const troubled = computed(() => blank.value || shaky.value || phase.value === 'error')

/**
 * 这次到底是哪一种失败。
 *
 * 顺序有讲究：引擎自己崩了先说崩了；曝光排在锐度前面，因为照片一暗，
 * 边缘本来就软，两条线会同时踩中，而这时候该做的是补光而不是端稳。
 */
const reason = computed(() => {
  if (phase.value === 'error') return 'error'
  if (!troubled.value) return ''
  const stats = result.value?.photo
  if (stats && stats.luma < DIM_LUMA && stats.span < DIM_SPAN) return 'dim'
  if (stats && stats.sharpness < BLUR_SHARPNESS) return 'blurry'
  return blank.value ? 'blank' : 'shaky'
})

/** 说得清原因就给对得上现场的那一组，说不清就回到兜底三条。 */
const tips = computed(() => REASON_TIPS[reason.value] ?? RETRY_TIPS)

const troubleTitle = computed(() => {
  if (reason.value === 'error') return '这次没认成'
  if (reason.value === 'dim') return '这张照片太暗了'
  if (reason.value === 'blurry') return '这张照片糊了'
  if (blank.value) return '这张照片里一个字都没认出来'
  return '认出来了，但把握不大'
})

const troubleDesc = computed(() => {
  if (reason.value === 'error') return hint.value
  if (reason.value === 'dim') return '光太少，笔画和背景混在一起了。先把光补上：'
  if (reason.value === 'blurry') return '笔画的边缘糊成一片，它分不出这是哪个字。先让画面稳下来：'
  if (blank.value) return '不是你拍得不好——光线、角度和字体它都挑。试试下面三条：'
  return `把握只有 ${result.value?.confidence ?? 0} 分，下面这几个字可能认错了。想更准一点：`
})

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
          <OpenMojiIcon name="camera" :size="22" /> 拍一张
        </button>
        <button class="btn btn--lg" :disabled="busy" @click="pick(albumInput)">
          <span aria-hidden="true">🖼️</span> 相册选一张
        </button>
        <button class="btn btn--lg" :disabled="busy" @click="useSample">
          <span aria-hidden="true">✨</span> 试一张示例
        </button>
        <button v-if="phase !== 'idle'" class="btn btn--lg" :disabled="busy" @click="again">
          <span aria-hidden="true">↩️</span> 换一张
        </button>
      </div>

      <!--
        两个 input 分开：拍照那个要 capture，相册那个不能带，否则安卓直接跳相机。
        它们都从无障碍树里摘掉——真正的控件是上面那排按钮，
        再让读屏念一遍「选择文件」只是重复。
      -->
      <input
        ref="cameraInput"
        class="sr-only"
        type="file"
        accept="image/*"
        capture="environment"
        tabindex="-1"
        aria-hidden="true"
        @change="useFile"
      />
      <input
        ref="albumInput"
        class="sr-only"
        type="file"
        accept="image/*"
        tabindex="-1"
        aria-hidden="true"
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

    <!--
      认不出的那一半。所有失败共用一张卡，但卡里的话按原因分岔：
      太暗、糊了、一个字都没有、认得不准、引擎出错。data-trouble 直接写 reason，
      smoke 与读屏都靠它定位到具体是哪一种。
      话术之外还要给出口，所以卡底下坐着「再拍一张」和「试一张示例」——
      示例那条是给「是不是这台设备坏了」留的自证路径。
    -->
    <section
      v-if="troubled"
      class="card card--sunken ocr__trouble"
      :data-trouble="reason"
      role="status"
    >
      <h3 class="ocr__trouble-title">
        <span aria-hidden="true">🤔</span> {{ troubleTitle }}
      </h3>
      <p class="ocr__trouble-desc">{{ troubleDesc }}</p>
      <ul class="ocr__tips">
        <li v-for="tip in tips" :key="tip.text" class="ocr__tip">
          <span class="ocr__tip-icon" aria-hidden="true">{{ tip.icon }}</span>
          <span>{{ tip.text }}</span>
        </li>
      </ul>
      <div class="ocr__trouble-acts">
        <button class="btn btn--primary" :disabled="busy" @click="pick(cameraInput)">
          再拍一张
        </button>
        <button class="btn" :disabled="busy" @click="useSample">试一张示例</button>
      </div>
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
            :data-ready="lessons.has(char)"
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

      <p v-else-if="unknown.length" class="card card--sunken ocr__empty">
        认出来的字都还没进字库，暂时讲不了。换一张有常用字的照片试试，比如书本或者路牌。
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

/* -------------------------------------------------------------- 认不出时 */

.ocr__trouble {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
  border-left: 4px solid var(--coral-400);
}

.ocr__trouble-title {
  font-size: var(--fs-md);
  font-weight: var(--fw-black);
  color: var(--text-strong);
}

.ocr__trouble-desc {
  line-height: var(--lh-loose);
  color: var(--text);
}

.ocr__tips {
  display: flex;
  flex-direction: column;
  gap: var(--gap-2xs);
  margin: 0;
  padding: 0;
  list-style: none;
}

.ocr__tip {
  display: flex;
  align-items: flex-start;
  gap: var(--gap-xs);
  line-height: var(--lh-base);
  color: var(--text);
}

.ocr__tip-icon {
  flex: none;
  font-size: 1.1rem;
  line-height: 1.4;
}

.ocr__trouble-acts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-xs);
  margin-top: var(--gap-2xs);
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
