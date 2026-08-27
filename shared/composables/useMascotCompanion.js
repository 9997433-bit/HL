/**
 * 吉祥物陪跑的共用行为。
 *
 * 识字的墨墨和数学的小算长得完全不一样，但「陪着孩子」这件事是一样的：
 * 身边常驻一句鼓励语，点一下换下一句并读出来，换句时做个开心的表情。
 * 这里只管这套行为，台词和朗读实现由各 App 自己传进来——
 * 这样两个 App 的陪跑节奏一致，又不必共用音频层。
 */
import { computed, onBeforeUnmount, ref, unref, watch } from 'vue'

/** 换句之后维持「开心」表情的时长。 */
const CHEER_MS = 1600

/**
 * @param {object}   options
 * @param {import('vue').Ref<string[]>|(() => string[])} options.lines 当前场景的台词
 * @param {(text: string) => void} [options.speak] 读出一句话（含点击音效）
 * @param {string} [options.restMood='idle']  平时的表情
 * @param {string} [options.cheerMood='cheer'] 刚被点过的表情
 */
export function useMascotCompanion({
  lines,
  speak,
  restMood = 'idle',
  cheerMood = 'cheer'
} = {}) {
  // 随机起点：每次进页面第一句话不一样，孩子不会觉得吉祥物在复读。
  const cursor = ref(Math.floor(Math.random() * 997))
  const mood = ref(restMood)
  let cheerTimer = null

  const pool = computed(() => {
    const list = typeof lines === 'function' ? lines() : unref(lines)
    if (!Array.isArray(list)) return []
    return list.filter((text) => typeof text === 'string' && text.trim())
  })

  const line = computed(() =>
    pool.value.length ? pool.value[cursor.value % pool.value.length] : ''
  )

  function clearCheer() {
    if (cheerTimer) {
      clearTimeout(cheerTimer)
      cheerTimer = null
    }
  }

  /** 做一个短暂的开心表情，然后回到平时的样子。 */
  function cheer() {
    mood.value = cheerMood
    clearCheer()
    cheerTimer = setTimeout(() => {
      mood.value = restMood
      cheerTimer = null
    }, CHEER_MS)
  }

  /** 点一下吉祥物：换下一句并读出来，返回这句话。 */
  function next() {
    if (!pool.value.length) return ''
    cursor.value += 1
    cheer()
    const text = line.value
    speak?.(text)
    return text
  }

  // 台词跟着学习进度重算，条数会变；光标越界时按长度取模，保留轮换的相对位置。
  watch(pool, (list) => {
    if (!list.length) cursor.value = 0
    else if (cursor.value >= list.length) cursor.value %= list.length
  })

  onBeforeUnmount(clearCheer)

  return { line, lines: pool, mood, next, cheer }
}
