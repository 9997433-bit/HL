<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  demo: { type: Object, required: true },
  autoPlay: { type: Boolean, default: true },
})

const emit = defineEmits(['complete'])
const stage = ref(0)
let timer = null

const stages = [
  { id: 'object', label: '实物', icon: '🧺' },
  { id: 'visual', label: '图形', icon: '●' },
  { id: 'equation', label: '算式', icon: '=' },
]

const narration = computed(
  () => props.demo.narration?.[stage.value] ?? props.demo.narration?.at(-1) ?? '',
)

function clearTimer() {
  if (timer) clearTimeout(timer)
  timer = null
}

function schedule() {
  clearTimer()
  if (!props.autoPlay || stage.value >= stages.length - 1) return
  timer = setTimeout(() => {
    stage.value += 1
    if (stage.value === stages.length - 1) emit('complete', props.demo.id)
    schedule()
  }, 1500)
}

function replay() {
  stage.value = 0
  schedule()
}

function skip() {
  stage.value = stages.length - 1
  clearTimer()
  emit('complete', props.demo.id)
}

function next() {
  if (stage.value >= stages.length - 1) return
  stage.value += 1
  if (stage.value === stages.length - 1) emit('complete', props.demo.id)
  schedule()
}

function objectGroups() {
  return props.demo.object.groups ?? [props.demo.object.count ?? 1]
}

watch(
  () => props.demo.id,
  () => replay(),
)

onMounted(schedule)
onBeforeUnmount(clearTimer)
</script>

<template>
  <section
    class="visual-demo card"
    :data-demo-id="demo.id"
    :data-demo-stage="stages[stage].id"
    :aria-label="`${demo.title}数形演示`"
  >
    <header class="demo-head">
      <div>
        <p class="kicker">实物 → 图形 → 算式</p>
        <h2>{{ demo.title }}</h2>
        <p class="muted">{{ demo.subtitle }}</p>
      </div>
      <div class="demo-actions">
        <button class="btn btn--ghost btn--sm" data-demo-replay @click="replay">↻ 重播</button>
        <button class="btn btn--ghost btn--sm" data-demo-skip @click="skip">跳过演示</button>
      </div>
    </header>

    <ol class="stage-track" aria-label="演示进度">
      <li
        v-for="(item, index) in stages"
        :key="item.id"
        :class="{ on: index <= stage, current: index === stage }"
        :aria-current="index === stage ? 'step' : undefined"
      >
        <span>{{ item.icon }}</span>
        {{ item.label }}
      </li>
    </ol>

    <div class="demo-flow">
      <article class="demo-panel object-panel" :class="{ revealed: stage >= 0 }">
        <span class="panel-tag">① 实物</span>
        <div class="object-groups" :aria-label="demo.object.label">
          <div v-for="(count, group) in objectGroups()" :key="group" class="object-group">
            <span
              v-for="n in count"
              :key="n"
              class="object"
              :class="{ removed: demo.object.removed && n > (demo.object.count - demo.object.removed) }"
            >
              {{ demo.object.emoji }}
            </span>
          </div>
        </div>
        <strong>{{ demo.object.label }}</strong>
      </article>

      <span class="flow-arrow" :class="{ revealed: stage >= 1 }" aria-hidden="true">→</span>

      <article class="demo-panel visual-panel" :class="{ revealed: stage >= 1 }">
        <span class="panel-tag">② 图形</span>
        <div class="dot-groups" :class="{ fraction: demo.visual.fraction }">
          <div
            v-for="(count, group) in demo.visual.groups"
            :key="group"
            class="dot-group"
            :class="{ crossed: demo.visual.crossedGroup === group }"
          >
            <span v-for="n in count" :key="n" class="dot" />
          </div>
        </div>
        <strong>{{ demo.visual.label }}</strong>
      </article>

      <span class="flow-arrow" :class="{ revealed: stage >= 2 }" aria-hidden="true">→</span>

      <article class="demo-panel equation-panel" :class="{ revealed: stage >= 2 }">
        <span class="panel-tag">③ 算式</span>
        <strong class="equation">{{ demo.equation }}</strong>
        <span class="complete-chip">抽象成功 ✨</span>
      </article>
    </div>

    <footer class="narration" aria-live="polite">
      <span class="speaker" aria-hidden="true">🔊</span>
      <p>{{ narration }}</p>
      <button
        v-if="stage < stages.length - 1"
        class="btn btn--primary btn--sm"
        data-demo-next
        @click="next"
      >
        下一步
      </button>
    </footer>
  </section>
</template>

<style scoped>
.visual-demo {
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
  justify-content: flex-end;
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
  align-items: center;
  justify-content: center;
  gap: 5px;
  flex-wrap: wrap;
  max-width: 112px;
  padding: 7px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
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

.dot-group.crossed {
  opacity: 0.42;
  background: linear-gradient(
    to top right,
    transparent 47%,
    var(--danger) 48% 52%,
    transparent 53%
  );
}

.dot-groups.fraction .dot-group {
  width: 62px;
  height: 72px;
  border: 2px solid var(--brand);
  border-radius: 62px 0 0 62px;
}

.dot-groups.fraction .dot-group + .dot-group {
  margin-left: -12px;
  border-radius: 0 62px 62px 0;
  opacity: 0.3;
}

.equation-panel {
  background: radial-gradient(circle, rgba(155, 140, 255, 0.18), rgba(6, 9, 30, 0.5));
}

.equation {
  font-size: clamp(30px, 5vw, 46px);
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

.speaker {
  font-size: 22px;
}

@keyframes object-in {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.7);
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
