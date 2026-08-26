<script setup>
/**
 * 小游戏大厅。
 *
 * 四款玩法各练一种能力：听音辨形、空间寻字、字音配对、字形辨别。
 * 卡片上写清楚「练什么」，家长扫一眼就知道该让孩子玩哪个。
 *
 * 所有小游戏都只出已学过的字，学的字越多，能玩的题目越多——
 * 大厅顶部的那句话就是在讲这件事。
 */
import { computed } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/sfx.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const progress = useProgressStore()

const GAMES = [
  {
    to: '/listen',
    emoji: '🎧',
    name: '听音识字',
    trains: '听音辨形',
    desc: '听一个字的读音，从四个里选出来',
    color: 'var(--mint-400)'
  },
  {
    to: '/games/maze',
    emoji: '🧭',
    name: '字迷宫',
    trains: '空间寻字',
    desc: '在迷宫里走到那个字上面，方向键就能玩',
    color: 'var(--sky-400)'
  },
  {
    to: '/games/memory',
    emoji: '🃏',
    name: '配对记忆',
    trains: '字音配对',
    desc: '翻开汉字卡和拼音卡，配成一对',
    color: 'var(--grape-400)'
  },
  {
    to: '/games/spot',
    emoji: '🔍',
    name: '找不同',
    trains: '字形辨别',
    desc: '一堆形近字里，找出不一样的那个',
    color: 'var(--mango-400)'
  }
]

const learned = computed(() => progress.learnedCount)
</script>

<template>
  <div class="page games">
    <section class="card games__intro">
      <h2 class="games__title">识字小游戏</h2>
      <p class="games__desc">
        四款游戏都只出<strong>你学过的字</strong>，现在能出题的有
        <strong>{{ learned }}</strong> 个字。多学几个字，游戏就更热闹啦。
      </p>
    </section>

    <ul class="games__list">
      <li v-for="g in GAMES" :key="g.to">
        <RouterLink
          class="gcard card card--tap"
          :to="g.to"
          :style="{ '--game-color': g.color }"
          @click="sfx.tap()"
        >
          <OpenMojiIcon class="gcard__icon" :emoji="g.emoji" :size="40" />
          <span class="gcard__body">
            <strong class="gcard__name">{{ g.name }}</strong>
            <span class="gcard__desc">{{ g.desc }}</span>
          </span>
          <span class="gcard__tag">{{ g.trains }}</span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.games__intro {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.games__title {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-strong);
}

.games__desc {
  line-height: 1.8;
  color: var(--text);
}

.games__list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  list-style: none;
  padding: 0;
  margin: 0;
}

.gcard {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--gap-sm);
  min-height: var(--tap-min);
  border-left: 6px solid var(--game-color);
}

.gcard__icon {
  flex: none;
}

.gcard__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.gcard__name {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--text-strong);
}

.gcard__desc {
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--text-soft);
}

.gcard__tag {
  flex: none;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--text-strong);
}
</style>
