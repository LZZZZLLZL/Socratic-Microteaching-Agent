<template>
  <section class="ecard" :class="{ 'ecard--hover': hover }">
    <header v-if="title || $slots.head" class="ecard__head">
      <slot name="head">
        <h2 class="ecard__title">
          <span v-if="index" class="ecard__index">{{ index }}</span>
          <span>{{ title }}</span>
        </h2>
      </slot>
      <slot name="aside">
        <span v-if="hint" class="ecard__hint">{{ hint }}</span>
      </slot>
    </header>
    <div class="ecard__body" :class="{ 'ecard__body--flush': flush }">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
/** EditorialCard — 1px 边框编辑风格卡片 */
withDefaults(
  defineProps<{
    /** 卡片标题（等宽大写标签风格） */
    title?: string
    /** 左上角序号，如 "01" */
    index?: string
    /** 右上角提示文案 */
    hint?: string
    /** 悬停时切换为白色背景 */
    hover?: boolean
    /** 去掉内边距（用于表格类内容） */
    flush?: boolean
  }>(),
  { hover: false, flush: false }
)
</script>

<style scoped>
.ecard {
  border: 1px solid var(--border);
  background: var(--bg);
  position: relative;
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.ecard--hover:hover {
  background: var(--surface);
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

.ecard__body {
  padding: var(--space-6);
}

.ecard__body--flush {
  padding: 0;
}

.ecard__hint {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  color: var(--muted);
  text-transform: uppercase;
}
</style>
