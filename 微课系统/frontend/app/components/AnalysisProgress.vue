<template>
  <div v-if="analyzing" class="analysis-progress animate-fade-in delay-1" role="status" aria-live="polite">
    <div class="analysis-progress__head">
      <span class="mono-label mono-label--strong">ANALYZING</span>
      <span class="mono-value">{{ progress }}%</span>
    </div>
    <ScanLineProgress :percent="progress" :active="analyzing" />
    <p class="analysis-progress__status">{{ statusText }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  progress: number
  statusText: string
  analyzing: boolean
}>()
</script>

<style scoped>
.analysis-progress {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-6);
  border: 1px solid var(--border);
  background: var(--surface-alt);
}

.analysis-progress__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.analysis-progress__status {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}
</style>
