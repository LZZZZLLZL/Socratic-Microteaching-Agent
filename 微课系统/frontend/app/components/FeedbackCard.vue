<template>
  <section class="ecard animate-fade-in-up delay-2" aria-labelledby="feedback-heading">
    <header class="ecard__head">
      <h2 class="ecard__title" id="feedback-heading">
        <span class="ecard__index">03</span>
        <span>AI 点评</span>
      </h2>
      <span v-if="isPreview" class="ebadge ebadge--solid">PREVIEW / 演示数据</span>
      <span v-else class="ecard__hint">苏格拉底式引导</span>
    </header>
    <div class="ecard__body">
      <div class="feedback-content">{{ feedback || '（暂无点评内容）' }}</div>
      <div class="action-buttons">
        <button type="button" class="btn btn--primary" @click="$emit('go-chat')">
          <span>开始对话</span>
          <span aria-hidden="true">→</span>
        </button>
        <button type="button" class="btn btn--ghost" @click="$emit('export-report')">
          <span>导出报告</span>
        </button>
        <button type="button" class="btn btn--quiet" @click="$emit('reset')">
          <span>分析新视频</span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    feedback: string
    sessionId: string
    isPreview?: boolean
  }>(),
  { isPreview: false }
)

defineEmits<{
  'go-chat': []
  'export-report': []
  'reset': []
}>()
</script>

<style scoped>
.feedback-content {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  line-height: var(--leading-relaxed);
  color: var(--text-primary);
  white-space: pre-wrap;
  margin-bottom: var(--space-8);
}

.action-buttons {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding-top: var(--space-6);
  border-top: 1px solid var(--border);
}
</style>
