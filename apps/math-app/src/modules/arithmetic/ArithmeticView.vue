<script setup>
import { ref } from 'vue'
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
import { genAdd } from '@/core/engine/generator.js'
import { sound } from '@/core/audio/sound.js'
import { useProgressStore } from '@/stores/progress.js'

// 引擎冒烟演示:生成器 → 答题 → 掌握度上报 全链路已通
const progress = useProgressStore()
const question = ref(genAdd({ max: 20 }))
const feedback = ref('')

function answer(choice) {
  const correct = choice === question.value.answer
  progress.recordAnswer(question.value, correct)
  if (correct) {
    sound.correct()
    feedback.value = '⭐ 答对啦!'
    setTimeout(() => {
      question.value = genAdd({ max: 20 })
      feedback.value = ''
    }, 900)
  } else {
    sound.wrong()
    feedback.value = '再想一想~'
  }
}
</script>

<template>
  <ModulePlaceholder
    module-id="arithmetic"
    icon="➕"
    title="计算星球"
    subtitle="加减乘除 · L2-L5 · 对标洪恩计算专题"
    :gameplays="[
      '口算流星雨:限时连击(Canvas 粒子)',
      '竖式工坊:逐位填空,进/退位高亮',
      '乘法口诀消消乐',
      '除法分披萨:等分动画',
      '错因归因:干扰项按典型错误构造(忘进位/忘退位)'
    ]"
  >
    <section class="demo">
      <h2>引擎冒烟演示(生成器→判定→掌握度全链路)</h2>
      <p class="q">{{ question.prompt.text }}</p>
      <div class="choices">
        <button v-for="c in question.choices" :key="c" class="choice" @click="answer(c)">
          {{ c }}
        </button>
      </div>
      <p class="fb">{{ feedback }}&nbsp;</p>
    </section>
  </ModulePlaceholder>
</template>

<style scoped>
.demo {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 18px 20px;
}
h2 {
  font-size: 16px;
  margin-bottom: 10px;
  color: var(--star-gold);
}
.q {
  font-size: 32px;
  text-align: center;
  margin: 12px 0;
}
.choices {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
.choice {
  min-width: 72px;
  padding: 14px 20px;
  font-size: 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-main);
  transition: transform 0.12s ease, background 0.12s ease;
}
.choice:hover {
  transform: scale(1.08);
  background: #42a5f5;
}
.fb {
  text-align: center;
  margin-top: 12px;
  font-size: 18px;
  color: var(--star-gold);
}
</style>
