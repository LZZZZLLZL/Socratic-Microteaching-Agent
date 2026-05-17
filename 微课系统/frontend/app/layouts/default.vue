<template>
  <div class="layout">
    <header class="header">
      <div class="header-content">
        <NuxtLink to="/" class="logo">
          <span class="logo-icon">🍎</span>
          <span class="logo-text">学思践悟</span>
        </NuxtLink>
        <nav class="nav">
          <NuxtLink to="/" class="nav-link" :class="{ active: route.path === '/' }">
            视频分析
          </NuxtLink>
          <NuxtLink v-if="sessionId" :to="`/chat?session=${sessionId}`" class="nav-link" :class="{ active: route.path === '/chat' }">
            苏格拉底对话
          </NuxtLink>
        </nav>
      </div>
    </header>
    <main class="main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const sessionId = ref('')

onMounted(() => {
  sessionId.value = route.query.session as string || ''
})
</script>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(15, 15, 15, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-subtle);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 18px;
}

.logo:hover {
  color: var(--text-primary);
}

.logo-icon {
  font-size: 24px;
}

.nav {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  transition: all 0.2s;
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-card);
}

.nav-link.active {
  color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.1);
}

.main {
  flex: 1;
  padding: 32px 24px;
}
</style>
