<template>
  <div class="app-container">
    <NuxtRouteAnnouncer />

    <!-- 固定背景网格层 -->
    <div class="bg-grid-layer" aria-hidden="true">
      <div class="bg-grid-layer__guide" style="left: 25%" />
      <div class="bg-grid-layer__guide" style="left: 50%" />
      <div class="bg-grid-layer__guide" style="left: 75%" />
      <div class="bg-grid-layer__squares" />
    </div>

    <NuxtLoadingIndicator color="#3d7068" :height="2" />

    <NuxtErrorBoundary>
      <div class="app-content">
        <NuxtLayout>
          <NuxtPage />
        </NuxtLayout>
      </div>
      <template #error="{ error }">
        <div class="error-boundary">
          <div class="error-content">
            <span class="error-code mono-label">ERROR / 页面加载出错</span>
            <h2 class="error-title">这个页面没有渲染成功</h2>
            <p class="error-desc">请刷新页面重试。若问题持续存在，请检查后端服务是否已启动。</p>
            <button class="btn btn--primary" type="button" @click="error?.clear">
              <span>重试</span>
            </button>
          </div>
        </div>
      </template>
    </NuxtErrorBoundary>
  </div>
</template>

<script setup lang="ts">
// App root — 背景网格 + NuxtLayout + NuxtPage
</script>

<style>
.app-container {
  min-height: 100vh;
  background-color: var(--bg);
  color: var(--fg);
  position: relative;
}

.app-content {
  position: relative;
  z-index: 1;
}

/* --- Error boundary fallback --- */
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--space-10);
}

.error-content {
  text-align: center;
  max-width: 420px;
}

.error-code {
  display: block;
  margin-bottom: var(--space-6);
}

.error-title {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: var(--font-light);
  margin-bottom: var(--space-4);
}

.error-desc {
  font-size: var(--text-base);
  color: var(--text-secondary);
  margin-bottom: var(--space-8);
  line-height: var(--leading-relaxed);
}
</style>
