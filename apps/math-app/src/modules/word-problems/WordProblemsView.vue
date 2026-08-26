<script setup>
import { ref } from 'vue'
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
import { instantiate } from '@/core/engine/wordproblem.js'
import { WP_TEMPLATES } from '@/data/word-problems.js'
import { sound } from '@/core/audio/sound.js'
import { useProgressStore } from '@/stores/progress.js'

const progress = useProgressStore()
const question = ref(instantiate(WP_TEMPLATES[0]))
const input = ref('')
const feedback = ref('')

function submit() {
  const ans = Number(input.value)
  const correct = ans === question.value.answer
  progress.recordAnswer(question.value, correct)
  if (correct) {
    feedback.value = '⭐ 答对啦！'
    sound.correct()
    setTimeout(next, 900)
  } else {
    feedback.value = `再想想，答案是 ${question.value.answer}`
    sound.wrong()
  }
}

function next() {
  const t = WP_TEMPLATES[Math.floor(Math.random() * WP_TEMPLATES.length)]
  question.value = instantiate(t)
  input.value = ''
  feedback.value = ''
}
</script>

<template>
  <ModulePlaceholder
    module-id="word-problems"
    icon="🌍"
    title="生活行星"
    subtitle="应用题母题 · 场景皮肤"
    :gameplays="['合并剩余', '比较差', '倍数关系', '分步引导']"
  >
    <section class="demo">
      <p class="story">{{ question.prompt.text }}</p>
      <input v-model="input" type="number" class="ans" placeholder="?" @keyup.enter="submit" />
      <button class="go" @click="submit">提交</button>
      <p class="fb">{{ feedback }}&nbsp;</p>
      <button class="skip" @click="next">换一题</button>
    </section>
  </ModulePlaceholder>
</template>

<style scoped>
.demo { background: var(--bg-card); border-radius: var(--radius-card); padding: 20px; text-align: center; }
.story { font-size: 18px; line-height: 1.7; margin-bottom: 16px; }
.ans {
  width: 100px;
  font-size: 28px;
  text-align: center;
  padding: 8px;
  border-radius: 12px;
  border: 2px solid var(--star-gold);
  margin-right: 8px;
}
.go, .skip { padding: 10px 18px; border-radius: 999px; cursor: pointer; margin: 8px 4px; }
.fb { min-height: 24px; margin-top: 10px; color: var(--star-gold); }
</style>
