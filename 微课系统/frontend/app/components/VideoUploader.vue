<template>
  <div v-if="!analyzing && !hasResult" class="uploader">
    <!-- 预览模式：演示课程卡 -->
    <template v-if="isPreview">
      <div class="demo-course">
        <div class="demo-course__head">
          <span class="mono-label mono-label--strong">DEMO LECTURE / 内置演示课程</span>
          <span class="ebadge">无需上传文件</span>
        </div>

        <h3 class="demo-course__title">{{ DEMO_COURSE.title }}</h3>

        <dl class="demo-course__meta">
          <div><dt class="mono-label">学科</dt><dd class="mono-value">{{ DEMO_COURSE.subject }}</dd></div>
          <div><dt class="mono-label">学段</dt><dd class="mono-value">{{ DEMO_COURSE.grade }}</dd></div>
          <div><dt class="mono-label">时长</dt><dd class="mono-value">{{ DEMO_COURSE.duration }}</dd></div>
          <div><dt class="mono-label">文件</dt><dd class="mono-value">{{ DEMO_COURSE.fileLabel }}</dd></div>
        </dl>
      </div>

      <button class="btn btn--primary btn--with-shadow uploader__cta" type="button" @click="$emit('start-preview')">
        <span>开始演示分析</span>
      </button>

      <p class="uploader__note mono-label">
        预览模式不调用任何模型与接口 · 结果来自内置演示数据
      </p>
    </template>

    <!-- 完整模式：真实上传 -->
    <template v-else>
      <div
        class="dropzone"
        :class="{ 'is-dragging': dragging, 'has-file': !!localFile }"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
        @click="openPicker"
      >
        <input
          ref="fileInput"
          type="file"
          accept="video/*"
          class="dropzone__input"
          @change="onPick"
        />

        <template v-if="!localFile">
          <svg class="dropzone__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">
            <path d="M12 16V4M7 9l5-5 5 5" />
            <path d="M4 16v3h16v-3" />
          </svg>
          <p class="dropzone__title">拖拽微课视频到此处</p>
          <p class="dropzone__hint mono-label">或点击选择文件 · 支持 MP4 / MOV / AVI</p>
        </template>

        <template v-else>
          <svg class="dropzone__icon dropzone__icon--ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">
            <path d="M5 13l4 4L19 7" />
          </svg>
          <p class="dropzone__title dropzone__title--file">{{ localFile.name }}</p>
          <p class="dropzone__hint mono-label">{{ formatSize(localFile.size) }} · 点击可重新选择</p>
        </template>
      </div>

      <button
        class="btn btn--primary btn--with-shadow uploader__cta"
        type="button"
        :disabled="!localFile"
        @click="$emit('start-analysis')"
      >
        <span>开始分析</span>
      </button>

      <p class="uploader__note mono-label">
        首次分析前将自动监测本地模型环境并允许选择识别精度
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { DEMO_COURSE } from '~/data/previewData'

withDefaults(
  defineProps<{
    analyzing: boolean
    hasResult: boolean
    isPreview?: boolean
  }>(),
  { isPreview: true }
)

const emit = defineEmits<{
  'file-change': [file: File]
  'start-analysis': []
  'start-preview': []
}>()

const fileInput = ref<HTMLInputElement>()
const localFile = ref<File | null>(null)
const dragging = ref(false)

const openPicker = () => fileInput.value?.click()

const accept = (file: File) => {
  localFile.value = file
  emit('file-change', file)
}

const onPick = (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) accept(file)
}

const onDrop = (e: DragEvent) => {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) accept(file)
}

const formatSize = (bytes: number) => {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}
</script>

<style scoped>
.uploader {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* ══════════ Demo course ══════════ */
.demo-course {
  border: 1px solid var(--border);
  background: var(--surface-alt);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  animation: fade-in-up var(--transition-slow) var(--ease-editorial) both;
}

.demo-course__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.demo-course__title {
  font-family: var(--font-serif);
  font-size: clamp(1.5rem, 3vw, 2rem);
  font-weight: var(--font-light);
  line-height: var(--leading-snug);
}

.demo-course__meta {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-5);
  border-top: 1px solid var(--border);
  padding-top: var(--space-5);
}

.demo-course__meta div {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.demo-course__meta dd { margin: 0; }

/* ══════════ Dropzone ══════════ */
.dropzone {
  position: relative;
  border: 1px solid var(--border);
  background: transparent;
  padding: var(--space-16) var(--space-8);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  cursor: pointer;
  text-align: center;
  transition:
    background-color var(--transition-base) var(--ease-editorial),
    border-color var(--transition-base) var(--ease-editorial);
}

.dropzone:hover,
.dropzone.is-dragging {
  background: var(--surface);
  border-color: var(--primary);
}

.dropzone.has-file {
  border-color: var(--primary);
  background: var(--primary-tint);
}

.dropzone__input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.dropzone__icon {
  width: 40px;
  height: 40px;
  color: var(--primary);
}

.dropzone__icon--ok { color: var(--primary); }

.dropzone__title {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: var(--font-normal);
  color: var(--fg);
}

.dropzone__title--file {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  letter-spacing: 0.05em;
  word-break: break-all;
  max-width: 32rem;
}

.dropzone__hint {
  color: var(--muted-deep);
}

/* ══════════ CTA ══════════ */
.uploader__cta {
  align-self: flex-start;
  min-width: 220px;
}

.uploader__note {
  color: var(--muted);
}

/* ══════════ Responsive ══════════ */
@media (max-width: 768px) {
  .demo-course__meta { grid-template-columns: repeat(2, 1fr); }
  .dropzone { padding: var(--space-10) var(--space-4); }
  .uploader__cta { width: 100%; align-self: stretch; }
}
</style>
