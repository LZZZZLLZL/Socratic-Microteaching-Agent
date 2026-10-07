<template>
  <section v-if="standards?.length" class="ecard animate-fade-in-up delay-2" aria-labelledby="standards-heading">
    <header class="ecard__head">
      <h2 class="ecard__title" id="standards-heading">
        <span class="ecard__index">02</span>
        <span>引用课标依据</span>
      </h2>
      <span class="ecard__hint">{{ standards.length }} 条</span>
    </header>
    <div class="ecard__body">
      <ul class="standards-list" role="list" aria-labelledby="standards-heading">
        <li v-for="(standard, idx) in standards" :key="idx" class="standards-list__item" role="listitem">
          <span class="mono-label standards-list__index" aria-hidden="true">[{{ String(idx + 1).padStart(2, '0') }}]</span>
          <span class="standards-list__text">{{ standard }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  standards: string[]
}>()
</script>

<style scoped>
.standards-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}

.standards-list__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border);
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.standards-list__item:first-child {
  border-top: 1px solid var(--border);
}

.standards-list__item:hover {
  background: var(--surface);
}

.standards-list__index {
  flex-shrink: 0;
  padding-top: 2px;
}

.standards-list__text {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}
</style>
