<template>
  <section v-if="alerts?.length" class="ecard animate-fade-in-up delay-3" aria-labelledby="alerts-heading">
    <header class="ecard__head">
      <h2 class="ecard__title" id="alerts-heading">
        <span class="ecard__index">05</span>
        <span>教态智能预警</span>
      </h2>
      <span class="ecard__hint">基于阈值自动分析</span>
    </header>
    <div class="ecard__body">
      <div class="alerts-list" role="status" aria-labelledby="alerts-heading">
        <div
          v-for="(alert, idx) in alerts"
          :key="idx"
          :class="['alert-item', `alert-${alert.level}`]"
          :role="alert.level === 'error' ? 'alert' : 'status'"
        >
          <span class="mono-label alert-level">{{ levelTag(alert.level) }}</span>
          <span class="alert-msg">{{ alert.msg }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { VisionAlert } from '~/types'

defineProps<{
  alerts: VisionAlert[]
}>()

const levelTag = (level: string): string => {
  const tags: Record<string, string> = { error: 'ERROR', warning: 'WARN', info: 'INFO', success: 'PASS' }
  return tags[level] || 'INFO'
}
</script>

<style scoped>
.alerts-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border-left: 2px solid var(--border);
  border-radius: 0;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.alert-error {
  border-left-color: var(--color-error);
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.alert-warning {
  border-left-color: var(--color-warning);
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.alert-info {
  border-left-color: var(--color-info);
  background: var(--color-info-bg);
  color: var(--color-info-text);
}

.alert-success {
  border-left-color: var(--color-success);
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.alert-level {
  flex-shrink: 0;
  padding-top: 3px;
  color: currentColor;
  opacity: 0.85;
}

.alert-msg {
  flex: 1;
}
</style>
