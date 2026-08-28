<script setup>
/**
 * 错题本 — 答错的题会自动进来，重做答对就把它放出去。
 *
 * 每条错题存的是答错当时的题面快照（题干 / 选项 / 答案 / 提示），
 * 所以重做不需要回到原玩法重新抽题，也不会抽到「另一道同类题」。
 * 重做只调 progress.retryWrong()：更新掌握度、答对移出错题本，
 * 不动总题数与正确率——复盘不该把主统计冲淡。
 *
 * skill 是可选的技能点筛选：技能图谱的推荐位跳进来时（/progress?wrong=<技能点>）
 * 只列这一个技能欠着的题，孩子不用在几十条里自己找。筛选只影响这个列表，
 * 不改错题本本身，清掉筛选就又是全部。
 */
import { computed, ref, watch } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import { errorTagInfo } from '@/data/errorTags.js'
import { MODULE_MAP } from '@/data/modules.js'
import { SKILLS, SKILL_MAP } from '@/data/curriculum.js'
import { weakestSkills } from '@/core/engine/adaptive.js'
import { shuffle } from '@/utils/random'
import { sound } from '@/utils/sound'

const props = defineProps({
  /** 只看这个技能点的错题；空串表示不筛选。 */
  skill: { type: String, default: '' },
})

const emit = defineEmits(['clear-skill'])

const progress = useProgressStore()

const SORTS = [
  { id: 'recent', label: '最近错的' },
  { id: 'most', label: '错得最多' },
]

const sortBy = ref('recent')
const activeId = ref(null)
const answered = ref(null)
const typed = ref('')
const confirmClear = ref(false)
/** 重做时的选项顺序：只在打开这道题时洗一次，点错一个不会整排乱跳。 */
const shuffled = ref([])
/** 这次重做已经试错过的答案，禁掉避免连点同一个把 attempts 刷上天。 */
const tried = ref([])

/** 筛选中的技能点：认不出的 id 一律当没筛，否则页面会变成一片空白。 */
const focusSkill = computed(() => (SKILL_MAP[props.skill] ? props.skill : ''))
const focusName = computed(() => SKILL_MAP[focusSkill.value]?.name ?? '')

const items = computed(() => {
  const all = progress.wrongList
  const list = focusSkill.value ? all.filter((e) => e.skill === focusSkill.value) : all
  return sortBy.value === 'most'
    ? [...list].sort((a, b) => b.attempts - a.attempts || b.lastAt - a.lastAt)
    : list
})

/** 筛选的技能一换就收起展开的那道题，免得停留在已经被筛掉的条目上。 */
watch(focusSkill, () => close())

const active = computed(() => items.value.find((e) => e.id === activeId.value) ?? null)

/** 引擎按掌握度 EMA + 错题欠账排出的「最该补的技能点」。 */
const advice = computed(() =>
  weakestSkills(SKILLS, { mastery: progress.state.mastery, wrongBook: progress.state.wrongBook }, 3),
)

const skillName = (id) => SKILL_MAP[id]?.name ?? '综合练习'
const moduleName = (id) => MODULE_MAP[id]?.name ?? '练习'
const moduleIcon = (id) => MODULE_MAP[id]?.icon ?? '📕'
const tagLabel = (id) => errorTagInfo(id).label

function fmtDate(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function open(entry) {
  sound.click()
  if (activeId.value === entry.id) {
    close()
    return
  }
  activeId.value = entry.id
  answered.value = null
  typed.value = ''
  tried.value = []
  shuffled.value =
    Array.isArray(entry.options) && entry.options.length > 1 ? shuffle(entry.options) : []
}

function close() {
  activeId.value = null
  answered.value = null
  typed.value = ''
  tried.value = []
  shuffled.value = []
}

/** 判一道重做：答对移出错题本并奖 1 颗星，答错留下、试过的选项禁掉再试。 */
function check(value) {
  const entry = active.value
  if (!entry || tried.value.some((v) => String(v) === String(value))) return
  const right = String(value) === String(entry.answer)
  progress.retryWrong(entry.id, right)
  answered.value = { right, value, answer: entry.answer, unit: entry.unit, hint: entry.hint }
  if (!right) {
    tried.value.push(value)
    typed.value = ''
    sound.wrong()
    return
  }
  sound.star()
  activeId.value = null
  typed.value = ''
  tried.value = []
  shuffled.value = []
}

function submitTyped() {
  if (typed.value === '') return
  check(Number(typed.value))
}

function drop(entry) {
  sound.click()
  progress.clearWrong(entry.id)
  if (activeId.value === entry.id) close()
}

function clearAll() {
  progress.clearWrongBook()
  confirmClear.value = false
  close()
  sound.click()
}

function clearFilter() {
  sound.click()
  emit('clear-skill')
}
</script>

<template>
  <section id="wrong-book" class="card wrong-book" data-wrong-book>
    <header class="wb-head">
      <h3 class="panel-title">📕 错题本</h3>
      <span class="chip">{{ progress.wrongCount }} 道待攻克</span>
      <div class="spacer" />
      <div v-if="progress.wrongCount > 1" class="seg" role="group" aria-label="错题排序">
        <button
          v-for="s in SORTS"
          :key="s.id"
          class="seg-btn"
          :class="{ on: sortBy === s.id }"
          :aria-pressed="sortBy === s.id"
          @click="sortBy = s.id"
        >
          {{ s.label }}
        </button>
      </div>
      <template v-if="progress.wrongCount">
        <button v-if="!confirmClear" class="btn btn--ghost btn--sm" @click="confirmClear = true">
          🧹 清空错题本
        </button>
        <template v-else>
          <button class="btn btn--ghost btn--sm" @click="confirmClear = false">取消</button>
          <button class="btn btn--sm wb-danger" @click="clearAll">确定清空</button>
        </template>
      </template>
    </header>

    <p
      v-if="focusSkill"
      class="wb-filter"
      :data-wrong-filter="focusSkill"
      :data-wrong-filter-count="items.length"
    >
      <span class="chip tiny">🎯 只看「{{ focusName }}」· {{ items.length }} 道</span>
      <button
        v-if="items.length && activeId === null"
        class="btn btn--primary btn--sm"
        data-wrong-retry-first
        @click="open(items[0])"
      >
        🔁 从第一道开始重练
      </button>
      <button class="btn btn--ghost btn--sm" data-wrong-filter-clear @click="clearFilter">
        显示全部
      </button>
    </p>

    <p v-if="!progress.wrongCount" class="muted wb-empty">
      错题本是空的，答错的题会自动收进来，重做答对就放它走 ✨
    </p>

    <p v-else-if="!items.length" class="muted wb-empty">
      「{{ focusName }}」这一点已经没有欠着的错题了，去技能图谱看看下一步练什么 ✨
    </p>

    <template v-else>
      <p v-if="advice.length" class="dim wb-advice">
        🎯 建议重点练：{{ advice.map((s) => s.name).join(' · ') }}
      </p>

      <ul class="wb-list">
        <li v-for="e in items" :key="e.id" class="wb-item" :class="{ on: activeId === e.id }">
          <div class="wb-row">
            <span class="wb-icon" aria-hidden="true">{{ moduleIcon(e.module) }}</span>
            <div class="wb-body">
              <strong class="wb-title">{{ e.title || skillName(e.skill) }}</strong>
              <div class="wb-meta">
                <span class="chip tiny">{{ moduleName(e.module) }}</span>
                <span class="chip tiny">{{ skillName(e.skill) }}</span>
                <span class="chip tiny warn">{{ tagLabel(e.errorTag) }}</span>
                <span class="dim tiny">错 {{ e.attempts }} 次 · {{ fmtDate(e.lastAt) }}</span>
              </div>
            </div>
            <button
              class="btn btn--primary btn--sm"
              :aria-expanded="activeId === e.id"
              @click="open(e)"
            >
              {{ activeId === e.id ? '收起' : '🔁 重做' }}
            </button>
            <button
              class="btn btn--ghost btn--sm"
              :aria-label="`把「${e.title || skillName(e.skill)}」移出错题本`"
              @click="drop(e)"
            >
              移出
            </button>
          </div>

          <div v-if="activeId === e.id" class="wb-retry">
            <p class="wb-ask">{{ e.title || skillName(e.skill) }}</p>
            <div v-if="shuffled.length" class="wb-opts">
              <button
                v-for="o in shuffled"
                :key="o"
                class="wb-opt"
                :class="{ tried: tried.includes(o) }"
                :disabled="tried.includes(o)"
                @click="check(o)"
              >
                {{ o }}<small v-if="e.unit">{{ e.unit }}</small>
              </button>
            </div>
            <div v-else class="wb-typein">
              <label class="dim tiny" :for="`wb-input-${e.id}`">写出答案</label>
              <input
                :id="`wb-input-${e.id}`"
                v-model="typed"
                class="wb-input"
                type="number"
                inputmode="numeric"
                @keyup.enter="submitTyped"
              />
              <button class="btn btn--primary btn--sm" :disabled="typed === ''" @click="submitTyped">
                对答案
              </button>
            </div>
            <p v-if="e.hint" class="dim tiny">💡 {{ e.hint }}</p>
          </div>
        </li>
      </ul>
    </template>

    <p v-if="answered" class="wb-verdict" :class="{ good: answered.right }" role="status">
      <template v-if="answered.right">
        答对啦！这道题已经从错题本里飞走 ⭐
      </template>
      <template v-else>
        还差一点：正确答案是 {{ answered.answer }}{{ answered.unit }}，先看提示再试一次。
      </template>
    </p>
  </section>
</template>

<style scoped>
.wrong-book {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wb-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.seg {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.seg-btn {
  padding: 6px 13px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  color: var(--ink-soft);
  white-space: nowrap;
  transition: all 0.16s ease;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--cyan), var(--violet));
  color: #08122b;
}

.wb-empty,
.wb-advice {
  font-size: 14px;
}

.wb-filter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.wb-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wb-item {
  padding: 10px 12px;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.wb-item.on {
  border-color: rgba(94, 231, 255, 0.5);
  background: rgba(94, 231, 255, 0.08);
}

.wb-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.wb-icon {
  font-size: 24px;
  flex: none;
}

.wb-body {
  flex: 1;
  min-width: 180px;
}

.wb-title {
  display: block;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.4;
}

.wb-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 5px;
}

.tiny {
  font-size: 11px;
}

.chip.tiny {
  padding: 3px 10px;
}

.chip.warn {
  background: rgba(255, 107, 125, 0.18);
  border-color: rgba(255, 107, 125, 0.45);
}

.wb-retry {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(255, 255, 255, 0.16);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wb-ask {
  font-size: 17px;
  font-weight: 800;
}

.wb-opts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 10px;
}

.wb-opt {
  padding: 14px 8px;
  font-size: 22px;
  font-weight: 900;
  border-radius: var(--radius-s);
  background: linear-gradient(160deg, rgba(94, 231, 255, 0.16), rgba(155, 140, 255, 0.14));
  border: 2px solid rgba(94, 231, 255, 0.4);
  transition: transform 0.14s ease;
}

.wb-opt:hover:not(:disabled) {
  transform: translateY(-3px);
}

.wb-opt.tried {
  background: rgba(255, 107, 125, 0.2);
  border-color: rgba(255, 107, 125, 0.5);
  opacity: 0.6;
}

.wb-opt small {
  font-size: 12px;
  color: var(--ink-soft);
  margin-left: 2px;
}

.wb-typein {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.wb-input {
  width: 120px;
  padding: 8px 14px;
  border-radius: var(--radius-s);
  font-family: inherit;
  font-size: 18px;
  font-weight: 800;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.24);
  outline: none;
}

.wb-verdict {
  padding: 10px 14px;
  border-radius: var(--radius-s);
  font-size: 14px;
  font-weight: 700;
  background: rgba(255, 107, 125, 0.14);
  border: 1px solid rgba(255, 107, 125, 0.42);
}

.wb-verdict.good {
  background: rgba(85, 230, 165, 0.16);
  border-color: rgba(85, 230, 165, 0.5);
}

.wb-danger {
  background: rgba(255, 107, 125, 0.22);
  border-color: var(--red);
  color: #ffd3d9;
}
</style>
