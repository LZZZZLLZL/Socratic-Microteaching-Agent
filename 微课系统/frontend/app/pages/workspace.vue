<template>
  <div class="page">
    <!-- ════════════════ 页头 ════════════════ -->
    <section class="whead">
      <div class="container-wide">
        <NuxtLink to="/" class="whead__back mono-label">
          <span aria-hidden="true">←</span> 返回首页
        </NuxtLink>

        <div class="whead__row">
          <div>
            <h1 class="whead__title">分析工作台</h1>
            <p class="whead__sub mono-label">
              WORKSPACE / {{ isPreview ? 'PREVIEW · 演示数据' : 'FULL · 真实推理' }}
            </p>
          </div>

          <div class="whead__status">
            <span class="ebadge" :class="{ 'ebadge--live': !isPreview }">
              <span class="pulse-dot" aria-hidden="true" />
              {{ isPreview ? 'PREVIEW MODE' : 'FULL MODE' }}
            </span>
            <span v-if="apiState.loading" class="mono-label">检查 API…</span>
            <span v-else-if="apiState.offline" class="mono-label whead__api whead__api--warn">
              后端未连接
            </span>
            <span v-else-if="apiState.configured" class="mono-label whead__api whead__api--ok">
              API 已配置
            </span>
            <span v-else class="mono-label whead__api whead__api--warn">
              API 未配置
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- ════════════════ WORKSPACE ════════════════ -->
    <section id="workspace" class="section section--tight">
      <div class="container-wide">
        <div class="workspace">
          <!-- 左：操作区 -->
          <div class="workspace__main">
            <!-- 预览模式说明条 -->
            <div v-if="isPreview" class="notice">
              <span class="notice__tag mono-label">预览模式</span>
              <p class="notice__text">
                当前为<strong>快速预览模式</strong>：不需要安装 Whisper / YOLOv8，不需要配置 API Key。
                点击下方按钮即可用内置演示课程完整走一遍分析流程。
              </p>
            </div>

            <!-- 完整模式引导 -->
            <div v-else class="notice notice--full">
              <span class="notice__tag mono-label">完整模式</span>
              <p class="notice__text">
                完整模式会在上传后<strong>自动监测本地模型环境</strong>，并允许你选择 Whisper 识别精度。
                首次使用需要下载所选模型。<strong>AI 点评与对话需要配置 API Key</strong>，可直接在下方填写。
              </p>
            </div>

            <!-- API 配置面板（完整模式） -->
            <EditorialCard
              v-if="!isPreview"
              id="api-setup"
              class="workspace__api"
              index="00"
            >
              <template #head>
                <h2 class="ecard__title">
                  <span class="ecard__index">00</span>
                  <span>API 设置</span>
                </h2>
                <span class="ecard__hint">
                  {{ apiState.configured ? '已配置 · 可用于 AI 点评与对话' : '未配置 · AI 点评与对话不可用' }}
                </span>
              </template>

              <ApiConfigPanel @updated="onApiUpdated" />
            </EditorialCard>

            <!-- 上传 / 操作 -->
            <VideoUploader
              :analyzing="analyzing"
              :has-result="!!result"
              :is-preview="isPreview"
              @file-change="handleFileChange"
              @start-analysis="requestAnalysis"
              @start-preview="startPreview"
            />

            <!-- 模型监测面板（完整模式） -->
            <EditorialCard
              v-if="showModelPanel"
              class="workspace__model"
              title="模型监测与选择"
              index="01"
              :hint="modelRuntimeOnline ? '后端已连接' : '后端不可达'"
            >
              <template #head>
                <h2 class="ecard__title">
                  <span class="ecard__index">01</span>
                  <span>模型监测与选择</span>
                </h2>
                <span class="ecard__hint">{{ modelRuntimeOnline ? '后端已连接' : '后端不可达 · 将使用默认配置' }}</span>
              </template>

              <ModelDetectPanel
                v-model:selected="whisperModel"
                :runtime="modelRuntime"
                :online="modelRuntimeOnline"
                @confirm="confirmModelAndStart"
              />

              <template #aside />
            </EditorialCard>

            <!-- 分析进度 -->
            <div v-if="analyzing" class="progress-block">
              <div class="progress-block__head">
                <span class="mono-label mono-label--strong">ANALYZING</span>
                <span class="mono-value">{{ progress }}%</span>
              </div>
              <ScanLineProgress :percent="progress" active />
              <p class="progress-block__status">{{ statusText }}</p>
            </div>
          </div>

          <!-- 右：说明卡（粘性） -->
          <aside class="workspace__aside">
            <div class="sticky-card">
              <div class="sticky-card__media">
                <div class="sticky-card__media-inner" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <rect x="2" y="4" width="20" height="16" />
                    <path d="M10 9l5 3-5 3V9z" />
                  </svg>
                </div>
                <div class="sticky-card__scan">
                  <div class="scanline scanline--blue" aria-hidden="true">
                    <div class="scanline__bar" :style="{ width: analyzing ? `${progress}%` : '0%' }" />
                    <div class="scanline__scan" />
                  </div>
                </div>
              </div>

              <dl class="sticky-card__meta">
                <div><dt class="mono-label">流程</dt><dd class="mono-value">04 阶段</dd></div>
                <div><dt class="mono-label">语音</dt><dd class="mono-value">{{ isPreview ? '演示文稿' : `Whisper ${whisperModel}` }}</dd></div>
                <div><dt class="mono-label">视觉</dt><dd class="mono-value">YOLOv8n-Pose</dd></div>
                <div><dt class="mono-label">检索</dt><dd class="mono-value">Text2Vec + FAISS</dd></div>
              </dl>

              <NuxtLink v-if="sessionId" :to="`/chat?session=${sessionId}`" class="btn btn--ghost btn--block">
                <span>进入苏格拉底对话</span>
              </NuxtLink>
            </div>
          </aside>
        </div>

        <!-- 分析结果 -->
        <div v-if="result" id="results" class="result-section">
          <div class="result-section__head">
            <span class="mono-label mono-label--strong">ANALYSIS RESULT</span>
            <span class="mono-label">SESSION / {{ result.session_id }}</span>
          </div>

          <VideoTimeline
            :video-url="result.video_url"
            :timeline="result.timeline"
            :duration="result.vision_analysis?.total_duration"
          />

          <TranscriptionCard :text="result.transcription" />

          <StandardsCard :standards="result.referenced_standards" />

          <FeedbackCard
            :feedback="result.socratic_feedback"
            :session-id="result.session_id"
            :is-preview="isPreview"
            @go-chat="goToChat"
            @export-report="exportReport"
            @reset="reset"
          />

          <ScoringCard :scores="result.scoring_card" />

          <VisionAlerts :alerts="result.vision_analysis?.alerts || []" />

          <VisionData :vision-data="result.vision_analysis" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * /workspace — 分析工作台
 *
 * 原先内嵌在首页 `index.vue` 里，现独立成页，使首页回归「介绍页」。
 * 分析状态来自 useAnalysis 的模块级单例，因此从对话页返回时结果仍在；
 * 也可以在地址栏直接用 /workspace#api-setup 深链到 API 配置面板。
 */
import { useRouter } from 'vue-router'
import { useAnalysis } from '~/composables/useAnalysis'
import { useReportExport } from '~/composables/useReportExport'

const router = useRouter()
const route = useRoute()
const { isPreview, whisperModel, hydrate } = useAppMode()

const {
  analyzing,
  progress,
  statusText,
  result,
  sessionId,
  showModelPanel,
  modelRuntime,
  modelRuntimeOnline,
  handleFileChange,
  requestAnalysis,
  confirmModelAndStart,
  startPreview,
  reset,
} = useAnalysis()

const { exportReport: doExport } = useReportExport()
const apiState = useApiConfig()

/** API 面板状态变化 → 同步全局提醒条 */
const onApiUpdated = (isConfigured: boolean) => {
  apiState.markConfigured(isConfigured)
}

const exportReport = () => {
  if (result.value) {
    doExport(result.value)
    ElMessage.success('报告已下载')
  }
}

const goToChat = () => {
  router.push(`/chat?session=${sessionId.value}`)
}

/** 支持 /workspace#api-setup 深链：挂载后滚动到 API 面板 */
const scrollToHashTarget = () => {
  if (route.hash !== '#api-setup') return
  requestAnimationFrame(() => {
    const el = document.getElementById('api-setup')
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

onMounted(() => {
  hydrate()
  apiState.hydrate()
  void apiState.refreshApiConfig()
  scrollToHashTarget()
})
</script>

<style scoped>
.page {
  padding-bottom: var(--space-16);
}

/* ══════════ 页头 ══════════ */
.whead {
  padding: var(--space-10) 0 var(--space-6);
  border-bottom: 1px solid var(--border);
}

.whead__back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--muted);
  text-decoration: none;
  margin-bottom: var(--space-6);
}

.whead__back:hover {
  color: var(--text-primary);
}

.whead__row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  flex-wrap: wrap;
}

.whead__title {
  font-family: var(--font-serif);
  font-size: var(--text-3xl);
  font-weight: var(--font-light);
  letter-spacing: -0.02em;
  margin: 0 0 var(--space-2);
}

.whead__sub {
  margin: 0;
}

.whead__status {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.whead__api--ok { color: var(--primary); }
.whead__api--warn { color: var(--muted); }

.section--tight {
  padding-top: var(--space-8);
}

/* ══════════ WORKSPACE ══════════ */
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20rem;
  gap: var(--space-6);
  align-items: start;
}

.workspace__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}

.workspace__aside {
  position: relative;
}

.notice {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: var(--surface-2);
  border: 1px solid var(--border);
}

.notice--full {
  border-color: var(--border-strong);
}

.notice__tag {
  flex: none;
  padding-top: 2px;
  color: var(--muted);
}

.notice--full .notice__tag {
  color: var(--primary);
}

.notice__text {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}

.notice__text strong {
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

/* API 面板定位锚点：滚动到此处时留出固定导航的高度 */
#api-setup,
.workspace__api {
  scroll-margin-top: 104px;
}

.workspace__model {
  scroll-margin-top: 104px;
}

/* ══════════ PROGRESS ══════════ */
.progress-block {
  padding: var(--space-5);
  background: var(--surface-2);
  border: 1px solid var(--border);
}

.progress-block__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.progress-block__status {
  margin: var(--space-3) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* ══════════ STICKY CARD ══════════ */
.sticky-card {
  position: sticky;
  top: 104px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  padding: var(--space-5);
}

.sticky-card__media {
  position: relative;
  aspect-ratio: 16 / 9;
  background: var(--surface-3);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-5);
  overflow: hidden;
}

.sticky-card__media-inner {
  width: 42%;
  color: var(--muted);
  opacity: 0.5;
}

.sticky-card__media-inner svg {
  width: 100%;
  height: auto;
  display: block;
}

.sticky-card__scan {
  position: absolute;
  inset: auto 0 0 0;
}

.sticky-card__meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0 0 var(--space-5);
}

.sticky-card__meta div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
}

.sticky-card__meta dd {
  margin: 0;
}

.sticky-card :deep(.btn--block) {
  width: 100%;
  justify-content: center;
}

/* ══════════ RESULT ══════════ */
.result-section {
  margin-top: var(--space-10);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.result-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border);
}

/* ══════════ RESPONSIVE ══════════ */
@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .sticky-card {
    position: static;
  }
}

@media (max-width: 768px) {
  .notice {
    flex-direction: column;
    gap: var(--space-2);
  }

  .whead {
    padding: var(--space-8) 0 var(--space-5);
  }

  .whead__row {
    align-items: flex-start;
  }
}
</style>
