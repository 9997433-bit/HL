<script setup>
/**
 * ROUND16_H4 学演示壳 —— 播放一条「实物 → 图形 → 算式」。
 *
 * 数据在 data/learn-demos.js，这里只管怎么放：
 *
 *   · 自动播放三段，每段 1.5 秒，随时能「跳过演示」直接看算式；
 *   · 「下一步」手动推进，「重播」回到实物段；
 *   · reduced-motion（系统偏好或家长关了动效）下不播了 —— 三段同时铺开、
 *     三句旁白一次列全，静止状态下也读得懂整条推理链，而不是停在第一段空等。
 *
 * 这是 VisualMathDemo 的接任者：同一套 data-demo-* 钩子，加上静态三态与技能标注。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LEARN_DEMO_STAGES, objectTiles, ROUND16_H4 } from '@/data/learn-demos.js'
import { reducedMotion } from '@/utils/motion.js'

const props = defineProps({
  demo: { type: Object, required: true },
  autoPlay: { type: Boolean, default: true },
  /** 技能点中文名，练习入口里弹出时用来点明「正在讲哪一点」。 */
  skillName: { type: String, default: '' },
  /** 嵌在弹层里时给一个关闭入口，独立成页时不给。 */
  dismissLabel: { type: String, default: '' },
})

const emit = defineEmits(['complete', 'dismiss'])

const stages = LEARN_DEMO_STAGES
const last = stages.length - 1
const stage = ref(0)
/** 静态三态：不播动画，三段一起给。 */
const still = ref(false)
let timer = null

const tiles = computed(() => objectTiles(props.demo.object))
const groupLabels = computed(() => props.demo.visual.groupLabels ?? [])
const frameClass = computed(() =>
  props.demo.visual.frame ? `frame-${props.demo.visual.frame}` : '',
)
/** 静态模式下三段全亮；播放模式下按进度亮。 */
const shown = (index) => still.value || stage.value >= index
const narration = computed(
  () => props.demo.narration?.[stage.value] ?? props.demo.narration?.at(-1) ?? '',
)

function clearTimer() {
  if (timer) clearTimeout(timer)
  timer = null
}

function schedule() {
  clearTimer()
  if (still.value || !props.autoPlay || stage.value >= last) return
  timer = setTimeout(() => {
    stage.value += 1
    if (stage.value === last) emit('complete', props.demo.id)
    schedule()
  }, 1500)
}

function replay() {
  if (still.value) return
  stage.value = 0
  schedule()
}

function skip() {
  stage.value = last
  clearTimer()
  emit('complete', props.demo.id)
}

function next() {
  if (stage.value >= last) return
  stage.value += 1
  if (stage.value === last) emit('complete', props.demo.id)
  schedule()
}

/**
 * 静态模式是「一进来就已经讲完了」：stage 直接停在算式段，
 * data-demo-stage 也就一直是 equation，外部（含验收）读到的状态和画面一致。
 */
function applyMotionPreference() {
  const reduce = reducedMotion()
  still.value = reduce
  if (!reduce) return
  clearTimer()
  stage.value = last
  emit('complete', props.demo.id)
}

let media = null
const onMediaChange = () => applyMotionPreference()

watch(
  () => props.demo.id,
  () => (still.value ? applyMotionPreference() : replay()),
)

onMounted(() => {
  applyMotionPreference()
  if (!still.value) schedule()
  media = window.matchMedia?.('(prefers-reduced-motion: reduce)')
  media?.addEventListener?.('change', onMediaChange)
})

onBeforeUnmount(() => {
  clearTimer()
  media?.removeEventListener?.('change', onMediaChange)
})
</script>

<template>
  <section
    class="learn-demo card"
    :class="{ still }"
    :data-round16="ROUND16_H4"
    :data-demo-id="demo.id"
    :data-demo-skill="demo.skill"
    :data-demo-stage="stages[stage].id"
    :data-demo-motion="still ? 'static' : 'play'"
    :aria-label="`${demo.title}学演示`"
  >
    <header class="demo-head">
      <div>
        <p class="kicker">实物 → 图形 → 算式</p>
        <h2>{{ demo.title }}</h2>
        <p class="muted">{{ demo.subtitle }}</p>
      </div>
      <div class="demo-actions">
        <span v-if="skillName" class="skill-chip" data-demo-skill-name>🎯 {{ skillName }}</span>
        <button v-if="!still" class="btn btn--ghost btn--sm" data-demo-replay @click="replay">
          ↻ 重播
        </button>
        <button class="btn btn--ghost btn--sm" data-demo-skip @click="skip">跳过演示</button>
        <button
          v-if="dismissLabel"
          class="btn btn--ghost btn--sm"
          data-demo-dismiss
          @click="emit('dismiss')"
        >
          {{ dismissLabel }}
        </button>
      </div>
    </header>

    <ol class="stage-track" aria-label="演示进度">
      <li
        v-for="(item, index) in stages"
        :key="item.id"
        :class="{ on: shown(index), current: !still && index === stage }"
        :aria-current="!still && index === stage ? 'step' : undefined"
      >
        <span>{{ item.icon }}</span>
        {{ item.label }}
      </li>
    </ol>

    <div class="demo-flow">
      <article class="demo-panel object-panel" :class="{ revealed: shown(0) }">
        <span class="panel-tag">① 实物</span>
        <div class="object-groups" :aria-label="demo.object.label">
          <div v-for="(tile, group) in tiles" :key="group" class="object-group">
            <span class="tile-items">
              <span
                v-for="(glyph, n) in tile.items"
                :key="n"
                class="object"
                :class="{ removed: n >= tile.crossedFrom }"
              >
                {{ glyph }}
              </span>
            </span>
            <small v-if="tile.caption" class="tile-caption">{{ tile.caption }}</small>
          </div>
        </div>
        <strong>{{ demo.object.label }}</strong>
      </article>

      <span class="flow-arrow" :class="{ revealed: shown(1) }" aria-hidden="true">→</span>

      <article class="demo-panel visual-panel" :class="{ revealed: shown(1) }">
        <span class="panel-tag">② 图形</span>
        <div class="dot-groups" :class="frameClass">
          <div
            v-for="(count, group) in demo.visual.groups"
            :key="group"
            class="dot-group"
            :class="{
              crossed: demo.visual.crossedGroup === group,
              lit: demo.visual.highlightGroup === group,
            }"
          >
            <span class="dot-cells">
              <span v-for="n in count" :key="n" class="dot" />
            </span>
            <small v-if="groupLabels[group]" class="dot-caption">{{ groupLabels[group] }}</small>
          </div>
        </div>
        <strong>{{ demo.visual.label }}</strong>
      </article>

      <span class="flow-arrow" :class="{ revealed: shown(2) }" aria-hidden="true">→</span>

      <article class="demo-panel equation-panel" :class="{ revealed: shown(2) }">
        <span class="panel-tag">③ 算式</span>
        <strong class="equation">{{ demo.equation }}</strong>
        <span class="complete-chip">抽象成功 ✨</span>
      </article>
    </div>

    <!--
      静态三态：动画关掉后，一句一句念的旁白就没人替孩子翻页了，
      所以三句一次全列出来，序号对上三个面板。
    -->
    <footer v-if="still" class="narration narration--all" data-demo-narration="all">
      <span class="speaker" aria-hidden="true">🔊</span>
      <ol>
        <li v-for="(line, index) in demo.narration" :key="index">
          <span class="line-tag">{{ stages[index]?.tag ?? '·' }}</span>
          {{ line }}
        </li>
      </ol>
    </footer>

    <footer v-else class="narration" aria-live="polite" data-demo-narration="step">
      <span class="speaker" aria-hidden="true">🔊</span>
      <p>{{ narration }}</p>
      <button v-if="stage < last" class="btn btn--primary btn--sm" data-demo-next @click="next">
        下一步
      </button>
    </footer>
  </section>
</template>

<style scoped>
.learn-demo {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.demo-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.demo-head h2 {
  margin: 3px 0;
  font-size: clamp(22px, 5vw, 30px);
}

.kicker {
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.demo-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
}

.skill-chip {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  color: var(--star);
  background: rgba(255, 206, 77, 0.12);
  border: 1px solid rgba(255, 206, 77, 0.34);
}

.stage-track {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stage-track li {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  border-radius: 999px;
  color: var(--text-soft);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 13px;
  font-weight: 800;
}

.stage-track li.on {
  color: var(--text-strong);
  border-color: rgba(94, 231, 255, 0.45);
}

.stage-track li.current {
  background: linear-gradient(135deg, rgba(94, 231, 255, 0.24), rgba(155, 140, 255, 0.24));
  box-shadow: 0 0 18px rgba(94, 231, 255, 0.18);
}

.demo-flow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 10px;
  align-items: stretch;
}

.demo-panel {
  min-height: 190px;
  padding: 16px;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  text-align: center;
  opacity: 0.2;
  filter: grayscale(0.7);
  transform: translateY(8px) scale(0.97);
  background: rgba(6, 9, 30, 0.5);
  border: 1px dashed rgba(255, 255, 255, 0.18);
  transition: opacity 0.35s ease, transform 0.35s ease, filter 0.35s ease;
}

.demo-panel.revealed {
  opacity: 1;
  filter: none;
  transform: none;
  border-style: solid;
  border-color: rgba(94, 231, 255, 0.32);
}

.panel-tag {
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
}

.object-groups,
.dot-groups {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 72px;
  flex-wrap: wrap;
}

.object-group,
.dot-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  max-width: 128px;
  padding: 7px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
}

.tile-items,
.dot-cells {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  flex-wrap: wrap;
}

.tile-caption,
.dot-caption {
  color: var(--text-soft);
  font-size: 11px;
  font-weight: 800;
  line-height: 1.25;
}

.object {
  font-size: 26px;
  animation: object-in 0.38s ease-out both;
}

.object.removed {
  opacity: 0.35;
  text-decoration: line-through 3px var(--danger);
}

.dot {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 9px rgba(94, 231, 255, 0.45);
}

.dot-group:nth-child(2n) .dot {
  background: var(--neon-pink);
  box-shadow: 0 0 9px rgba(255, 122, 198, 0.45);
}

.dot-group.lit {
  border: 1px solid rgba(255, 206, 77, 0.6);
  background: rgba(255, 206, 77, 0.12);
}

.dot-group.crossed {
  opacity: 0.42;
  background: linear-gradient(
    to top right,
    transparent 47%,
    var(--danger) 48% 52%,
    transparent 53%
  );
}

/* 十格框：固定五列，两整行就是一个十，一眼看出「满没满十」 */
.dot-groups.frame-ten .dot-cells {
  display: grid;
  grid-template-columns: repeat(5, 16px);
  gap: 4px;
  padding: 5px;
  border: 2px solid rgba(94, 231, 255, 0.5);
  border-radius: 8px;
}

.dot-groups.frame-ten .dot {
  width: 16px;
  height: 16px;
}

.dot-groups.frame-fraction .dot-group {
  width: 62px;
  height: 72px;
  justify-content: center;
  border: 2px solid var(--brand);
  border-radius: 62px 0 0 62px;
}

.dot-groups.frame-fraction .dot-group + .dot-group {
  margin-left: -12px;
  border-radius: 0 62px 62px 0;
  opacity: 0.3;
}

/* 展开图：这里的一个点代表立体图形的一个面，所以画成方块而不是圆点 */
.dot-groups.frame-net .dot,
.dot-groups.frame-net .dot-group:nth-child(2n) .dot {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 2px solid rgba(94, 231, 255, 0.7);
  background: rgba(94, 231, 255, 0.16);
  box-shadow: none;
}

/* 对称：两组之间画出那条对称轴 */
.dot-groups.frame-mirror {
  gap: 0;
}

.dot-groups.frame-mirror .dot-group + .dot-group {
  border-left: 2px dashed var(--star);
  border-radius: 0 12px 12px 0;
}

/* 对称的两半必须长得一样，不能被隔组换色的规则拆成两种颜色 */
.dot-groups.frame-mirror .dot-group:nth-child(2n) .dot {
  background: var(--brand);
  box-shadow: 0 0 9px rgba(94, 231, 255, 0.45);
}

.equation-panel {
  background: radial-gradient(circle, rgba(155, 140, 255, 0.18), rgba(6, 9, 30, 0.5));
}

.equation {
  font-size: clamp(26px, 4.5vw, 42px);
  color: var(--star);
  white-space: nowrap;
}

.complete-chip {
  color: var(--success);
  font-size: 13px;
  font-weight: 800;
}

.flow-arrow {
  align-self: center;
  color: var(--brand);
  font-size: 28px;
  opacity: 0.15;
  transform: translateX(-6px);
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.flow-arrow.revealed {
  opacity: 1;
  transform: none;
}

.narration {
  min-height: 58px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: var(--radius-sm);
  background: rgba(255, 206, 77, 0.1);
  border: 1px solid rgba(255, 206, 77, 0.28);
}

.narration p {
  flex: 1;
  font-weight: 700;
}

.narration--all {
  align-items: flex-start;
}

.narration--all ol {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.narration--all li {
  display: flex;
  gap: 8px;
  font-weight: 700;
  line-height: 1.5;
}

.line-tag {
  flex: none;
  color: var(--brand);
  font-weight: 900;
}

.speaker {
  font-size: 22px;
}

/* 静态三态：面板不再靠动画依次亮起，一进来就全是可读的成品 */
.learn-demo.still .demo-panel,
.learn-demo.still .flow-arrow {
  opacity: 1;
  filter: none;
  transform: none;
  transition: none;
}

.learn-demo.still .demo-panel {
  border-style: solid;
  border-color: rgba(94, 231, 255, 0.32);
}

.learn-demo.still .object {
  animation: none;
}

@keyframes object-in {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.7);
  }
}

@media (prefers-reduced-motion: reduce) {
  .object {
    animation: none;
  }
}

@media (max-width: 760px) {
  .demo-head {
    flex-direction: column;
  }

  .demo-actions {
    justify-content: flex-start;
  }

  .demo-flow {
    grid-template-columns: 1fr;
  }

  .demo-panel {
    min-height: 145px;
  }

  .flow-arrow {
    transform: rotate(90deg);
  }

  .flow-arrow.revealed {
    transform: rotate(90deg);
  }
}
</style>
