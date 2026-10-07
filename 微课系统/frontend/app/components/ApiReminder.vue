<template>
  <Transition name="api-remind">
    <div v-if="visible" class="api-remind" role="status" aria-live="polite">
      <div class="api-remind__inner container-wide">
        <span class="api-remind__tag mono-label">SETUP / 一步配置</span>

        <p class="api-remind__text">
          进入系统后，请在
          <NuxtLink to="/workspace" class="api-remind__link">分析工作台</NuxtLink>
          的「API 设置」里填写 API Key，<strong>AI 对话与点评</strong>才会启用。
          本地能力（语音转写 / 姿态分析 / 课标检索）不受影响。
        </p>

        <div class="api-remind__actions">
          <button class="btn btn--primary btn--sm" type="button" @click="goConfigure">
            <span>{{ onWorkspace ? '立即配置' : '去配置' }}</span>
          </button>
          <button class="btn btn--quiet btn--sm" type="button" @click="dismiss">
            <span>不再提醒</span>
          </button>
        </div>

        <button
          class="api-remind__close"
          type="button"
          aria-label="关闭提示"
          @click="dismiss"
        >
          ×
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
/**
 * ApiReminder — 未配置 API Key 时的全局提醒条
 *
 * 可关闭、可「不再提醒」，且在后端离线时不显示（避免把用户引向无效操作）。
 * 在工作台页点击「立即配置」滚动到 API 面板；在其他页则跳转过去。
 */
const route = useRoute()
const { shouldRemind, hydrate, dismiss } = useApiConfig()
const { refreshApiConfig } = useApiConfig()

const onWorkspace = computed(() => route.path === '/workspace')

/** 关闭态动画期间先隐藏，避免闪回 */
const hidden = ref(false)
const visible = computed(() => shouldRemind.value && !hidden.value)

const scrollToApiPanel = () => {
  const el = document.getElementById('api-setup')
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const goConfigure = () => {
  if (onWorkspace.value) {
    scrollToApiPanel()
  } else {
    navigateTo('/workspace#api-setup')
  }
}

const dismissBanner = () => {
  hidden.value = true
  dismiss()
}

onMounted(() => {
  hydrate()
  // 初次进入时拉一次真实状态；失败也不阻塞渲染
  void refreshApiConfig()
})

defineExpose({ scrollToApiPanel })
</script>

<style scoped>
.api-remind {
  position: relative;
  z-index: 40;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-strong);
}

.api-remind__inner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) 0;
  flex-wrap: wrap;
}

.api-remind__tag {
  flex: none;
  color: var(--muted);
  border: 1px solid var(--border-strong);
  padding: 2px 8px;
}

.api-remind__text {
  flex: 1 1 22rem;
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}

.api-remind__text strong {
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.api-remind__link {
  color: var(--primary);
  text-decoration: none;
  border-bottom: 1px solid currentColor;
}

.api-remind__actions {
  display: flex;
  gap: var(--space-2);
  flex: none;
}

.api-remind__close {
  flex: none;
  background: none;
  border: 0;
  color: var(--muted);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 var(--space-1);
}

.api-remind__close:hover {
  color: var(--text-primary);
}

.api-remind-enter-active,
.api-remind-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.api-remind-enter-from,
.api-remind-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 640px) {
  .api-remind__actions {
    width: 100%;
  }
}
</style>
