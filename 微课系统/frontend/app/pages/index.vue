<template>
  <div class="page">
    <!-- ════════════════ HERO ════════════════ -->
    <section class="hero">
      <div class="container-wide hero__inner">
        <span class="ebadge hero__badge">
          <span class="pulse-dot" aria-hidden="true" />
          {{ isPreview ? 'PREVIEW MODE ACTIVE · 零依赖演示' : 'FULL MODE · 本地模型就绪' }}
        </span>

        <h1 class="hero__title">
          学<span class="hero__title-em">思</span>践悟
        </h1>

        <p class="hero__sub mono-label">
          MICRO-LECTURE ANALYSIS SYSTEM / 微课智能分析系统
        </p>

        <p class="hero__lede">
          上传一段微课视频。语音转写看清你说了什么，姿态识别看清你怎么站的，
          课标检索看清标准怎么要求的，最后由 AI 导师用苏格拉底式提问，
          带你走完一轮「学—思—践—悟」。
        </p>

        <div class="hero__actions">
          <NuxtLink to="/workspace" class="btn btn--primary btn--with-shadow">
            <span>{{ isPreview ? '开始快速预览' : '开始分析' }}</span>
          </NuxtLink>
          <NuxtLink
            v-if="sessionId"
            :to="`/chat?session=${sessionId}`"
            class="btn btn--ghost"
          >
            <span>继续上次对话</span>
          </NuxtLink>
          <NuxtLink v-if="hasResult" to="/workspace#results" class="btn btn--ghost">
            <span>查看上次分析</span>
          </NuxtLink>
          <NuxtLink to="/about" class="btn btn--quiet">
            <span>了解系统</span>
          </NuxtLink>
        </div>

        <div class="hero__meta">
          <span class="mono-label">SESSION / {{ sessionId || 'NEW' }}</span>
          <span class="hero__meta-sep" aria-hidden="true" />
          <span class="mono-label">{{ isPreview ? 'LOCAL / 无模型调用' : 'CUDA / 本地推理' }}</span>
        </div>
      </div>
    </section>

    <!-- ════════════════ STATISTICS GRID ════════════════ -->
    <section class="section section--flush">
      <div class="container-wide">
        <div class="section__head">
          <h2 class="section__title">系统的四个维度</h2>
          <span class="mono-label">FIGURES / 01—04</span>
        </div>

        <div class="datagrid datagrid--3">
          <article v-for="(stat, i) in STATS" :key="stat.label" class="datagrid__cell">
            <div class="datagrid__icon" aria-hidden="true">
              <component :is="stat.icon" />
            </div>
            <div class="datagrid__num">{{ stat.value }}</div>
            <div class="datagrid__label">{{ stat.label }}</div>
            <p class="datagrid__desc">{{ stat.desc }}</p>
            <span class="datagrid__index mono-label">{{ String(i + 1).padStart(2, '0') }}</span>
          </article>
        </div>
      </div>
    </section>

    <!-- ════════════════ TEXT REVEAL ════════════════ -->
    <section ref="revealSection" class="section reveal">
      <div class="container-narrow">
        <p class="reveal-text" aria-label="系统的设计理念">
          <span
            v-for="(word, i) in REVEAL_WORDS"
            :key="i"
            :class="{ 'is-on': i <= revealIndex }"
          >{{ word }}<br v-if="REVEAL_BREAKS.includes(i)" /></span>
        </p>
        <div class="reveal__foot">
          <span class="mono-label">DESIGN NOTE / 设计理念</span>
        </div>
      </div>
    </section>

    <!-- ════════════════ 入口卡 ════════════════ -->
    <section class="section section--flush">
      <div class="container-wide">
        <div class="entry">
          <div class="entry__copy">
            <span class="mono-label">WORKSPACE / 下一步</span>
            <h2 class="entry__title">分析工作台</h2>
            <p class="entry__desc">
              上传视频、选择模型精度、查看转写与教态分析结果。当前为
              <strong>{{ isPreview ? '快速预览模式（零安装、零配置）' : '完整模式（本地真实推理）' }}</strong>。
            </p>
          </div>

          <div class="entry__actions">
            <NuxtLink to="/workspace" class="btn btn--primary btn--with-shadow">
              <span>进入分析工作台</span>
            </NuxtLink>
            <span class="entry__hint mono-label">
              首次使用需在「API 设置」中填写 API Key 以启用 AI 对话与点评
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- ════════════════ 模式对比 TABS ════════════════ -->
    <section class="section">
      <div class="container-wide">
        <div class="section__head">
          <h2 class="section__title">两种运行模式</h2>
          <span class="mono-label">MODES / 对比</span>
        </div>

        <div class="tabs" role="tablist" aria-label="运行模式对比">
          <button
            v-for="t in MODE_TABS"
            :key="t.id"
            class="tabs__btn"
            :class="{ 'is-active': activeTab === t.id }"
            role="tab"
            :aria-selected="activeTab === t.id"
            type="button"
            @click="activeTab = t.id"
          >
            {{ t.label }}
          </button>
        </div>

        <div class="mode-panel">
          <svg class="ghost-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="0.4" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2v20M2 12h20" />
          </svg>

          <div class="mode-panel__head">
            <h3 class="mode-panel__title">{{ currentTab.title }}</h3>
            <p class="mode-panel__desc">{{ currentTab.desc }}</p>
          </div>

          <div class="mode-panel__grid">
            <div v-for="b in currentTab.benefits" :key="b.label" class="mode-panel__item">
              <span class="mono-label">{{ b.label }}</span>
              <p class="mode-panel__item-text">{{ b.text }}</p>
            </div>
          </div>

          <div class="mode-panel__actions">
            <button class="btn btn--primary" type="button" @click="switchTo(currentTab.id)">
              <span>{{ currentTab.cta }}</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * / — 首页（介绍页）
 *
 * 分析工作台已拆到独立页面 `/workspace`，首页只保留介绍性内容：
 * Hero、系统的四个维度、设计理念、入口卡、两种运行模式对比。
 * 所有「开始分析」类动作都改为导航到工作台，不再做页内滚动。
 */
import { useAnalysis } from '~/composables/useAnalysis'

const { isPreview, hydrate, setMode } = useAppMode()
const { result, sessionId } = useAnalysis()

const hasResult = computed(() => Boolean(result.value))

// --- 统计网格 ---
const STATS = [
  {
    value: '01',
    label: 'SPEECH / 语音转写',
    desc: 'Whisper 本地推理，自动还原中文标点，五档精度可选。',
    icon: h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.2' }, [
      h('path', { d: 'M12 3v10' }),
      h('path', { d: 'M8 13a4 4 0 008 0' }),
      h('path', { d: 'M5 11v2a7 7 0 0014 0v-2' }),
      h('path', { d: 'M12 20v2' }),
    ]),
  },
  {
    value: '02',
    label: 'VISION / 教态识别',
    desc: 'YOLOv8 姿态估计，量化背对时长、手势频次与课堂走位。',
    icon: h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.2' }, [
      h('circle', { cx: '12', cy: '5', r: '2.4' }),
      h('path', { d: 'M12 7.5v6M12 13.5l-4 6M12 13.5l4 6M7 10h10' }),
    ]),
  },
  {
    value: '03',
    label: 'RAG / 课标检索',
    desc: '中文向量模型 + FAISS，从课程标准中检索出可引用的依据。',
    icon: h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.2' }, [
      h('path', { d: 'M4 5h7v14H4zM13 5h7v14h-7z' }),
      h('path', { d: 'M11 12h2' }),
    ]),
  },
  {
    value: '04',
    label: 'SOCRATIC / 苏格拉底对话',
    desc: '不给答案，只给问题。用连续追问把反思推到可执行的改课方案。',
    icon: h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.2' }, [
      h('path', { d: 'M21 12a8 8 0 01-8 8H8l-5 3 1.5-5A8 8 0 1113 4a8 8 0 018 8z' }),
      h('path', { d: 'M9.5 11a2.5 2.5 0 115 0c0 1.5-2.5 2-2.5 3.5' }),
    ]),
  },
]

// --- 文本揭示 ---
const REVEAL_WORDS = [
  '我们把', '一节课', '拆成', '两条', '证据链：',
  '你说了什么，', '和你', '怎么站的。',
  '但真正的', '改进，', '从来不是', '来自', '别人给出的', '结论，',
  '而是来自', '你自己', '被一个', '好问题', '卡住的那一刻。',
]
const REVEAL_BREAKS = [4, 7, 13]

const revealSection = ref<HTMLElement>()
const revealIndex = ref(-1)

const onRevealScroll = () => {
  const el = revealSection.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const vh = window.innerHeight || 1
  // 从元素进入视口 85% 处开始，到元素顶部到视口 25% 处结束
  const start = vh * 0.85
  const end = vh * 0.25
  const raw = (start - rect.top) / Math.max(start - end, 1)
  const p = Math.min(Math.max(raw, 0), 1)
  revealIndex.value = Math.floor(p * REVEAL_WORDS.length) - 1
}

// --- 模式对比 Tabs ---
const activeTab = ref<'preview' | 'full'>('preview')

const MODE_TABS = [
  { id: 'preview' as const, label: '快速预览模式' },
  { id: 'full' as const, label: '完整模式' },
]

const TAB_CONTENT = {
  preview: {
    title: '快速预览模式',
    desc: '为评委与初次体验者准备。不安装任何模型、不配置任何 API Key，打开浏览器即可完整走通流程。',
    benefits: [
      { label: 'ZERO SETUP / 零安装', text: '无需 Whisper、无需 YOLOv8、无需 Python 后端，纯前端运行。' },
      { label: 'SCRIPTED CHAT / 固定脚本', text: '苏格拉底对话以选项形式呈现，四轮固定追问，演示稳定不冷场。' },
      { label: 'INSTANT / 即时反馈', text: '内置演示课程与分析结果，三秒完成一次完整分析演示。' },
    ],
    cta: '切换到快速预览模式',
  },
  full: {
    title: '完整模式',
    desc: '为实际教研使用准备。上传你自己的微课视频，本地模型真实推理，AI 导师即兴追问。',
    benefits: [
      { label: 'REAL INFERENCE / 真实推理', text: 'Whisper 语音转写 + YOLOv8 姿态识别，全部在本地完成。' },
      { label: 'MODEL CHOICE / 精度可选', text: '首次进入自动监测环境，五档 Whisper 精度按磁盘大小与准确度自由选择。' },
      { label: 'OPEN DIALOGUE / 开放对话', text: '对话不设轮次上限，AI 依据你的真实转写文稿层层追问。' },
    ],
    cta: '切换到完整模式',
  },
}

const currentTab = computed(() => TAB_CONTENT[activeTab.value])

/** 切换模式后跳转到工作台，用户可立刻开始分析 */
const switchTo = (id: 'preview' | 'full') => {
  setMode(id)
  navigateTo('/workspace')
}

onMounted(() => {
  hydrate()
  onRevealScroll()
  window.addEventListener('scroll', onRevealScroll, { passive: true })
  window.addEventListener('resize', onRevealScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onRevealScroll)
  window.removeEventListener('resize', onRevealScroll)
})
</script>

<style scoped>
.page {
  padding-bottom: var(--space-16);
}

/* ══════════ HERO ══════════ */
.hero {
  padding: var(--space-16) 0 var(--space-24);
  text-align: center;
}

.hero__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-6);
}

.hero__badge {
  margin-bottom: var(--space-4);
}

.hero__title {
  font-family: var(--font-serif);
  font-size: var(--text-hero);
  font-weight: var(--font-light);
  line-height: 0.98;
  letter-spacing: -0.03em;
  text-transform: uppercase;
  margin: 0;
}

.hero__title-em {
  font-style: italic;
  color: var(--muted);
}

.hero__sub {
  margin-top: var(--space-2);
}

.hero__lede {
  max-width: 44rem;
  font-size: var(--text-md);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}

.hero__actions {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
  justify-content: center;
  margin-top: var(--space-4);
}

.hero__meta {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-top: var(--space-8);
}

.hero__meta-sep {
  width: 24px;
  height: 1px;
  background: var(--border-strong);
}

/* ══════════ SECTION TWEAKS ══════════ */
.section--flush {
  border-top: 1px solid var(--border);
}

.datagrid__cell {
  position: relative;
}

.datagrid__index {
  position: absolute;
  top: var(--space-6);
  right: var(--space-6);
  color: var(--muted);
}

/* ══════════ REVEAL ══════════ */
.reveal {
  min-height: 70vh;
  display: flex;
  align-items: center;
}

.reveal__foot {
  margin-top: var(--space-12);
  display: flex;
  justify-content: flex-end;
}

/* ══════════ 入口卡 ══════════ */
.entry {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-8);
  align-items: center;
  padding: var(--space-8) var(--space-10);
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  position: relative;
  overflow: hidden;
}

.entry__copy {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
}

.entry__title {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: var(--font-light);
  margin: 0;
}

.entry__desc {
  margin: 0;
  max-width: 38rem;
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}

.entry__desc strong {
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.entry__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-3);
  text-align: right;
}

.entry__hint {
  max-width: 18rem;
  color: var(--muted);
  line-height: var(--leading-relaxed);
}

/* ══════════ TABS ══════════ */
.tabs {
  display: flex;
  gap: var(--space-2);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--space-8);
}

.tabs__btn {
  background: none;
  border: 0;
  border-bottom: 2px solid transparent;
  padding: var(--space-3) var(--space-5);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  letter-spacing: 0.06em;
  color: var(--muted);
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.tabs__btn:hover {
  color: var(--text-primary);
}

.tabs__btn.is-active {
  color: var(--text-primary);
  border-bottom-color: var(--primary);
}

.mode-panel {
  position: relative;
  padding: var(--space-10);
  background: var(--surface-2);
  border: 1px solid var(--border);
  overflow: hidden;
}

.mode-panel__head {
  position: relative;
  z-index: 1;
  margin-bottom: var(--space-8);
}

.mode-panel__title {
  font-family: var(--font-serif);
  font-size: var(--text-xl);
  font-weight: var(--font-light);
  margin: 0 0 var(--space-3);
}

.mode-panel__desc {
  margin: 0;
  max-width: 42rem;
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}

.mode-panel__grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}

.mode-panel__item {
  padding-right: var(--space-6);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.mode-panel__item:last-child { border-right: 0; }

.mode-panel__item-text {
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}

.mode-panel__actions {
  margin-top: var(--space-10);
  position: relative;
  z-index: 1;
}

/* ══════════ RESPONSIVE ══════════ */
@media (max-width: 1024px) {
  .entry {
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }

  .entry__actions {
    align-items: flex-start;
    text-align: left;
  }
}

@media (max-width: 768px) {
  .hero {
    padding: var(--space-10) 0 var(--space-16);
  }

  .hero__lede {
    font-size: var(--text-base);
  }

  .hero__actions {
    width: 100%;
    flex-direction: column;
  }

  .hero__actions :deep(.btn) {
    width: 100%;
  }

  .entry {
    padding: var(--space-6);
  }

  .mode-panel {
    padding: var(--space-6);
  }

  .mode-panel__grid {
    grid-template-columns: 1fr;
  }

  .mode-panel__item {
    border-right: 0;
    border-bottom: 1px solid var(--border);
    padding: var(--space-5) 0;
  }

  .mode-panel__item:last-child { border-bottom: 0; }
}
</style>
