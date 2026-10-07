<template>
  <section v-if="visionData" class="ecard vision-card">
    <header class="ecard__head">
      <h2 class="ecard__title" id="vision-heading">
        <span class="ecard__index">06</span>
        <span>教态数据</span>
      </h2>
      <span class="ecard__hint">仅后台参考，对话中不会主动提及</span>
    </header>

    <div
      class="vision-grid"
      role="region"
      aria-labelledby="vision-heading"
    >
      <div class="vision-item">
        <span class="vision-label">背对学生时间</span>
        <span class="vision-value">{{ (visionData.back_ratio * 100).toFixed(1) }}%</span>
      </div>
      <div class="vision-item">
        <span class="vision-label">手势频次</span>
        <span class="vision-value">{{ visionData.gesture_intensity }} 次</span>
      </div>
      <div class="vision-item">
        <span class="vision-label">手势幅度</span>
        <span class="vision-value">{{ visionData.gesture_level }}</span>
      </div>
      <div class="vision-item">
        <span class="vision-label">左右均衡度</span>
        <span class="vision-value">{{ visionData.hand_balance }}%</span>
      </div>
      <div class="vision-item">
        <span class="vision-label">位移幅度</span>
        <span class="vision-value">
          {{ visionData.movement_range }}
          <small class="vision-unit">画面宽/分钟</small>
        </span>
      </div>
      <div class="vision-item">
        <span class="vision-label">站位状态</span>
        <span class="vision-value">{{ visionData.is_stiff ? '较为固定' : '灵活' }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { VisionAnalysis } from '~/types'

defineProps<{
  visionData: VisionAnalysis
}>()
</script>

<style scoped>
.vision-card {
  animation: fade-in-up 400ms var(--ease-editorial) both;
  animation-delay: 300ms;
}

.ecard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.ecard__title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  color: var(--fg);
  font-weight: var(--font-normal);
  margin: 0;
}

.ecard__index {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  color: var(--muted);
  border: 1px solid var(--border);
  padding: 2px 6px;
  line-height: 1;
}

.ecard__hint {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  color: var(--muted);
  text-transform: uppercase;
}

/* --- Data grid --- */
.vision-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  border-top: 1px solid var(--border);
}

.vision-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-5) var(--space-4);
  border-right: 1px solid var(--border);
  background: transparent;
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.vision-item:last-child {
  border-right: 0;
}

.vision-item:hover {
  background: var(--surface);
}

.vision-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--muted-deep);
  line-height: 1;
}

.vision-value {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: var(--font-light);
  color: var(--fg);
  line-height: var(--leading-tight);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

/* 单位标注：等宽小字，避免与主数值混淆 */
.vision-unit {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
  color: var(--muted-deep);
  text-transform: uppercase;
}

@media (max-width: 900px) {
  .vision-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .vision-item:nth-child(3n) {
    border-right: 0;
  }

  .vision-item:nth-child(n + 4) {
    border-top: 1px solid var(--border);
  }
}

@media (max-width: 640px) {
  .vision-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .vision-item {
    padding: var(--space-4);
  }

  .vision-item:nth-child(3n) {
    border-right: 1px solid var(--border);
  }

  .vision-item:nth-child(2n) {
    border-right: 0;
  }

  .vision-item:nth-child(n + 3) {
    border-top: 1px solid var(--border);
  }
}
</style>
