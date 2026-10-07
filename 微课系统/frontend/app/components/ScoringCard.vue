<template>
  <section v-if="scores?.length" class="ecard animate-fade-in-up delay-3" aria-labelledby="scoring-heading">
    <header class="ecard__head">
      <h2 class="ecard__title" id="scoring-heading">
        <span class="ecard__index">04</span>
        <span>多维评分卡</span>
      </h2>
      <button
        type="button"
        class="btn btn--quiet btn--sm"
        :aria-expanded="showScoring"
        aria-controls="scoring-content"
        @click="showScoring = !showScoring"
      >
        <span aria-hidden="true">{{ showScoring ? '−' : '+' }}</span>
        <span>{{ showScoring ? '收起评分卡' : '展开评分卡' }}</span>
      </button>
    </header>
    <div class="ecard__body">
      <div v-show="showScoring" id="scoring-content" class="scoring-grid" role="region" aria-labelledby="scoring-heading">
        <div v-for="item in scores" :key="item.name" class="score-row">
          <div class="score-info">
            <span class="mono-label mono-label--strong score-name">{{ item.name }}</span>
            <span class="score-comment">{{ item.comment }}</span>
          </div>
          <div class="score-bar-wrap">
            <div
              class="score-bar"
              :style="{ width: `${item.score}%`, background: scoreColor(item.score) }"
              role="progressbar"
              :aria-valuenow="item.score"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="`${item.name} ${item.score}分`"
            />
          </div>
          <span class="score-num" :style="{ color: scoreColor(item.score) }">{{ item.score }}</span>
        </div>

        <div class="score-row score-total">
          <span class="mono-label mono-label--strong">综合平均</span>
          <span class="total-score">{{ avgScore }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ScoreItem } from '~/types'

const props = defineProps<{
  scores: ScoreItem[]
}>()

const showScoring = ref(false)

const scoreColor = (score: number): string => {
  if (score >= 85) return 'var(--color-success)'
  if (score >= 70) return 'var(--color-warning)'
  return 'var(--color-error)'
}

const avgScore = computed(() => {
  if (!props.scores?.length) return '—'
  return Math.round(props.scores.reduce((sum, s) => sum + s.score, 0) / props.scores.length)
})
</script>

<style scoped>
.scoring-grid {
  display: flex;
  flex-direction: column;
}

.score-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) 0;
}

.score-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.score-name {
  white-space: nowrap;
  width: 96px;
  flex-shrink: 0;
}

.score-comment {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  color: var(--muted-deep);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 扁平无圆角 8px 轨道 */
.score-bar-wrap {
  width: 140px;
  height: 8px;
  background: var(--border);
  border-radius: 0;
  overflow: hidden;
  flex-shrink: 0;
}

.score-bar {
  height: 100%;
  border-radius: 0;
  transition: width var(--transition-base) var(--ease-editorial);
}

.score-num {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  width: 36px;
  text-align: right;
  flex-shrink: 0;
}

.score-total {
  margin-top: var(--space-3);
  padding-top: var(--space-5);
  border-top: 1px solid var(--border);
  justify-content: space-between;
  align-items: baseline;
}

.total-score {
  font-family: var(--font-serif);
  font-size: var(--text-3xl);
  font-weight: var(--font-light);
  line-height: 1;
  color: var(--primary);
}

@media (max-width: 640px) {
  .score-bar-wrap {
    width: 80px;
  }

  .score-comment {
    display: none;
  }
}
</style>
