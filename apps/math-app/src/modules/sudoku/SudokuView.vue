<script setup>
import { computed, ref } from 'vue'
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
import { generateSudoku, isValidPlacement } from '@/core/engine/sudoku.js'
import { sound } from '@/core/audio/sound.js'
import { useProgressStore } from '@/stores/progress.js'

const progress = useProgressStore()
const game = ref(generateSudoku(4))
const board = ref([...game.value.puzzle])
const selected = ref(null)
const message = ref('')

const spec = computed(() => game.value.spec)
const size = computed(() => spec.value.size)

function cellClass(idx) {
  return {
    fixed: game.value.puzzle[idx] !== 0,
    selected: selected.value === idx,
    wrong: board.value[idx] && !isValidPlacement(board.value, spec.value, idx, board.value[idx])
  }
}

function pick(idx) {
  if (game.value.puzzle[idx]) return
  selected.value = idx
  sound.click()
}

function fill(n) {
  if (selected.value == null) return
  board.value[selected.value] = n
  if (board.value.every((v, i) => v === game.value.solution[i])) {
    message.value = '🎉 太棒了，数独完成！'
    sound.correct()
    progress.stars += 3
    progress.persist()
  } else if (!isValidPlacement(board.value, spec.value, selected.value, n)) {
    message.value = '这里不对哦，再想想~'
    sound.wrong()
  } else {
    message.value = ''
    sound.click()
  }
}

function newGame() {
  game.value = generateSudoku(4)
  board.value = [...game.value.puzzle]
  selected.value = null
  message.value = ''
  sound.click()
}
</script>

<template>
  <ModulePlaceholder
    module-id="sudoku"
    icon="🔢"
    title="数独空间站"
    subtitle="4×4 入门 · 唯一解验证"
    :gameplays="['4×4 儿童入门', '6×6 进阶', '9×9 经典', '提示与撤销']"
  >
    <section class="demo">
      <div class="grid" :style="{ gridTemplateColumns: `repeat(${size}, 1fr)` }">
        <button
          v-for="(v, idx) in board"
          :key="idx"
          class="cell"
          :class="cellClass(idx)"
          @click="pick(idx)"
        >
          {{ v || '' }}
        </button>
      </div>
      <div class="pad">
        <button v-for="n in size" :key="n" @click="fill(n)">{{ n }}</button>
        <button class="clear" @click="fill(0)">清除</button>
      </div>
      <p class="msg">{{ message }}&nbsp;</p>
      <button class="new" @click="newGame">换一题</button>
    </section>
  </ModulePlaceholder>
</template>

<style scoped>
.demo { background: var(--bg-card); border-radius: var(--radius-card); padding: 18px; }
.grid { display: grid; gap: 4px; max-width: 280px; margin: 0 auto 12px; }
.cell {
  aspect-ratio: 1;
  font-size: 22px;
  border-radius: 8px;
  border: 2px solid #334;
  background: #1a2744;
  color: #fff;
  cursor: pointer;
}
.cell.fixed { background: #0f1a30; color: var(--star-gold); }
.cell.selected { outline: 3px solid var(--star-gold); }
.cell.wrong { background: #4a1a1a; }
.pad { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
.pad button { min-width: 44px; padding: 10px; border-radius: 10px; cursor: pointer; }
.msg { text-align: center; min-height: 24px; margin-top: 10px; }
.new { display: block; margin: 8px auto 0; padding: 8px 16px; border-radius: 999px; cursor: pointer; }
</style>
