<template>
  <section class="ecard animate-fade-in-up delay-1" aria-labelledby="transcription-heading">
    <header class="ecard__head">
      <h2 class="ecard__title" id="transcription-heading">
        <span class="ecard__index">01</span>
        <span>教学内容 / 语音转写</span>
      </h2>
      <span class="ecard__hint">{{ text.length }} 字</span>
    </header>
    <div class="ecard__body">
      <div class="transcription" role="region" aria-labelledby="transcription-heading">
        {{ text || '（未检测到语音内容）' }}
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  text: string
}>()
</script>

<style scoped>
.transcription {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
  white-space: pre-wrap;
}
</style>
