<template>
  <div class="layout">
    <a href="#main-content" class="skip-to-content">跳到主要内容</a>

    <!-- 导航：初始浮动 → 滚动后固定 + 背景模糊 -->
    <header class="nav" :class="{ 'nav--pinned': scrolled }" role="banner">
      <div class="nav__inner container-wide">
        <!-- 品牌 -->
        <NuxtLink to="/" class="brand" aria-label="学思践悟 首页">
          <span class="brand__bar brand__bar--short" aria-hidden="true" />
          <span class="brand__name">学思践悟</span>
          <span class="brand__bar brand__bar--long" aria-hidden="true" />
        </NuxtLink>

        <!-- 主链接 -->
        <nav class="nav__links" aria-label="主导航">
          <NuxtLink to="/" class="nav__link" :class="{ 'is-active': route.path === '/' }">
            01 / 视频分析
          </NuxtLink>
          <NuxtLink
            to="/workspace"
            class="nav__link"
            :class="{ 'is-active': route.path === '/workspace' }"
          >
            02 / 分析工作台
          </NuxtLink>
          <NuxtLink
            v-if="sessionId"
            :to="`/chat?session=${sessionId}`"
            class="nav__link"
            :class="{ 'is-active': route.path === '/chat' }"
          >
            03 / 苏格拉底对话
          </NuxtLink>
          <NuxtLink to="/about" class="nav__link" :class="{ 'is-active': route.path === '/about' }">
            {{ sessionId ? '04' : '03' }} / 关于系统
          </NuxtLink>
        </nav>

        <!-- 模式开关 -->
        <div class="nav__mode">
          <span class="nav__mode-label mono-label" :class="{ 'is-on': isFull }">
            {{ isFull ? 'FULL / 完整版' : 'PREVIEW / 快速预览' }}
          </span>
          <button
            class="mode-toggle"
            type="button"
            role="switch"
            :aria-checked="isFull"
            aria-label="切换完整模式与快速预览模式"
            @click="toggleMode"
          >
            <span class="mode-toggle__knob" />
          </button>
        </div>
      </div>

      <!-- 固定条底部的滚动进度扫描线 -->
      <div v-show="scrolled" class="nav__scanline scanline scanline--idle" aria-hidden="true">
        <div class="scanline__scan" />
      </div>
    </header>

    <!-- 未配置 API Key 的全局提醒：可关闭 / 可「不再提醒」，后端离线时不显示 -->
    <ApiReminder />

    <main id="main-content" class="main" role="main" tabindex="-1">
      <slot />
    </main>

    <footer class="footer" role="contentinfo">
      <div class="footer__inner container-wide">
        <div class="footer__col">
          <span class="footer__brand">学思践悟</span>
          <span class="mono-label">AI 多模态师范生实训系统</span>
        </div>
        <div class="footer__col footer__col--right">
          <span class="mono-label">MODE / {{ isFull ? 'FULL' : 'PREVIEW' }}</span>
          <span class="footer__note">仅用于教学研究，AI 点评仅供参考</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { isFull, setMode, hydrate } = useAppMode()

const sessionId = computed(() => (route.query.session as string) || '')
const scrolled = ref(false)

const onScroll = () => {
  scrolled.value = window.scrollY > 24
}

const toggleMode = () => {
  setMode(isFull.value ? 'preview' : 'full')
}

onMounted(() => {
  hydrate()
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* --- Skip link --- */
.skip-to-content {
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 200;
  padding: var(--space-3) var(--space-6);
  background: var(--primary);
  color: #fff;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  text-decoration: none;
}

.skip-to-content:focus {
  left: 0;
}

/* --- Nav --- */
.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  padding-top: 32px;
  background: transparent;
  border-bottom: 1px solid transparent;
  transition:
    padding var(--transition-base) var(--ease-editorial),
    background-color var(--transition-base) var(--ease-editorial),
    border-color var(--transition-base) var(--ease-editorial);
}

.nav--pinned {
  padding-top: 0;
  background: rgba(247, 246, 242, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom-color: var(--border);
}

.nav__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  height: 64px;
}

/* --- Brand --- */
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
  color: var(--fg);
  flex-shrink: 0;
}

.brand__bar {
  height: 1px;
  background: var(--primary);
  transition: width var(--transition-base) var(--ease-editorial);
}

.brand__bar--short { width: 24px; }
.brand__bar--long  { width: 32px; }

.brand:hover .brand__bar--short { width: 32px; }
.brand:hover .brand__bar--long  { width: 24px; }

.brand__name {
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: var(--font-normal);
  letter-spacing: -0.01em;
  line-height: 1;
}

/* --- Links --- */
.nav__links {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  flex-wrap: wrap;
}

.nav__link {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  color: var(--muted-deep);
  text-decoration: none;
  padding-bottom: 2px;
  border-bottom: 1px solid transparent;
  transition:
    color var(--transition-fast) var(--ease-editorial),
    letter-spacing var(--transition-base) var(--ease-editorial),
    border-color var(--transition-fast) var(--ease-editorial);
}

.nav__link:hover {
  color: var(--fg);
  letter-spacing: var(--tracking-widest);
}

.nav__link.is-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

/* --- Mode switch --- */
.nav__mode {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.nav__mode-label {
  transition: color var(--transition-fast) var(--ease-editorial);
}

.nav__mode-label.is-on {
  color: var(--primary);
}

.mode-toggle {
  width: 40px;
  height: 18px;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  position: relative;
  cursor: pointer;
  padding: 0;
  transition: border-color var(--transition-fast) var(--ease-editorial);
}

.mode-toggle:hover {
  border-color: var(--primary);
}

.mode-toggle__knob {
  position: absolute;
  top: 1px;
  left: 1px;
  width: 14px;
  height: 14px;
  background: var(--muted);
  transition:
    transform var(--transition-base) var(--ease-editorial),
    background-color var(--transition-fast) var(--ease-editorial);
}

.mode-toggle[aria-checked='true'] .mode-toggle__knob {
  transform: translateX(21px);
  background: var(--primary);
}

/* --- Scanline under pinned bar --- */
.nav__scanline {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  opacity: 0.6;
}

/* --- Main --- */
.main {
  flex: 1;
  padding-top: 96px;
}

/* --- Footer --- */
.footer {
  border-top: 1px solid var(--border);
  padding: var(--space-8) 0;
  margin-top: var(--space-24);
}

.footer__inner {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  flex-wrap: wrap;
}

.footer__col {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.footer__col--right {
  align-items: flex-end;
}

.footer__brand {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: var(--font-light);
}

.footer__note {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
  color: var(--muted);
}

/* --- Responsive --- */
@media (max-width: 900px) {
  .nav__links { gap: var(--space-4); }
  .nav__mode-label { display: none; }
}

@media (max-width: 640px) {
  .nav__links { display: none; }
  .main { padding-top: 88px; }
  .footer__col--right { align-items: flex-start; }
}
</style>
