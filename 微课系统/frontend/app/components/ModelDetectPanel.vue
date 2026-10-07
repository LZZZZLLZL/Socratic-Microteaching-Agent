<template>
  <div class="model-check">
    <!-- 检测中 -->
    <div v-if="phase === 'scanning'" class="model-check__scanning">
      <div class="model-check__scan-head">
        <span class="pulse-dot" aria-hidden="true" />
        <span class="mono-label mono-label--strong">正在检测本地模型环境</span>
      </div>
      <ScanLineProgress :percent="scanPercent" active />
      <ul class="model-check__scan-log">
        <li v-for="(line, i) in scanLog" :key="i" class="model-check__scan-line">
          <span class="model-check__scan-tick">✓</span>{{ line }}
        </li>
      </ul>
    </div>

    <!-- 检测结果 + 模型选择 -->
    <template v-else>
      <!-- 运行时环境 -->
      <div class="model-check__runtime">
        <span class="mono-label">RUNTIME / 运行环境</span>
        <div class="model-check__runtime-grid">
          <div class="model-check__runtime-item">
            <span class="mono-label">设备</span>
            <span class="mono-value">{{ runtime.device || '未知' }}</span>
          </div>
          <div class="model-check__runtime-item">
            <span class="mono-label">PyTorch</span>
            <span class="mono-value">{{ runtime.torch || '—' }}</span>
          </div>
          <div class="model-check__runtime-item">
            <span class="mono-label">加速</span>
            <span class="mono-value">{{ runtime.gpu || (runtime.cuda ? 'CUDA' : 'CPU') }}</span>
          </div>
          <div class="model-check__runtime-item">
            <span class="mono-label">已装模型</span>
            <span class="mono-value">{{ installedCount }} / {{ WHISPER_MODELS.length }}</span>
          </div>
        </div>
        <p v-if="!runtime.cuda" class="model-check__warn">
          未检测到 CUDA 设备，将使用 CPU 推理。Medium 及以上模型在 CPU 上可能非常缓慢，建议选择 Small。
        </p>
      </div>

      <!-- Whisper 精度选择 -->
      <div class="model-check__picker">
        <div class="model-check__picker-head">
          <span class="mono-label mono-label--strong">WHISPER / 语音识别模型精度</span>
          <span class="mono-label">标注为磁盘占用大小</span>
        </div>

        <div class="model-grid">
          <button
            v-for="m in WHISPER_MODELS"
            :key="m.id"
            type="button"
            class="model-card"
            :class="{
              'is-selected': selected === m.id,
              'is-installed': isInstalled(m.id),
            }"
            :aria-pressed="selected === m.id"
            @click="$emit('update:selected', m.id)"
          >
            <div class="model-card__top">
              <span class="model-card__name">{{ m.name }}</span>
              <span v-if="m.recommended" class="model-card__rec mono-label">推荐</span>
              <span v-else-if="isInstalled(m.id)" class="model-card__installed mono-label">已下载</span>
            </div>

            <div class="model-card__size">
              <span class="model-card__size-value">{{ m.size }}</span>
              <span class="model-card__size-label mono-label">{{ m.params }} 参数</span>
            </div>

            <div class="model-card__acc">
              <span class="mono-label">中文准确度</span>
              <span class="model-card__acc-bars" aria-hidden="true">
                <i
                  v-for="n in 10"
                  :key="n"
                  class="model-card__acc-bar"
                  :class="{ 'is-on': n <= m.accuracy }"
                />
              </span>
            </div>

            <dl class="model-card__meta">
              <div><dt class="mono-label">速度</dt><dd class="mono-value">{{ m.speed }}</dd></div>
              <div><dt class="mono-label">显存</dt><dd class="mono-value">{{ m.vram }}</dd></div>
            </dl>

            <p class="model-card__scene">{{ m.scene }}</p>
          </button>
        </div>
      </div>

      <!-- 附属组件 -->
      <div class="model-check__extras">
        <span class="mono-label">其他组件</span>
        <div class="extra-row">
          <span class="extra-row__name">{{ VISION_MODEL_INFO.name }}</span>
          <span class="mono-label">{{ VISION_MODEL_INFO.size }}</span>
          <span class="extra-row__note">{{ VISION_MODEL_INFO.note }}</span>
        </div>
        <div v-for="c in RUNTIME_COMPONENTS" :key="c.id" class="extra-row">
          <span class="extra-row__name">{{ c.name }}</span>
          <span class="mono-label">{{ c.size }}</span>
          <span class="extra-row__note">{{ c.role }} · {{ c.note }}</span>
        </div>
      </div>

      <!-- 操作 -->
      <div class="model-check__actions">
        <div class="model-check__actions-info">
          <span class="mono-label">已选模型</span>
          <span class="mono-value model-check__selected-name">{{ selectedModel.name }} · {{ selectedModel.size }}</span>
        </div>
        <div class="model-check__actions-btns">
          <button
            v-if="!isInstalled(selected)"
            class="btn btn--ghost"
            type="button"
            :disabled="downloading"
            @click="downloadSelected"
          >
            <span>{{ downloading ? '下载中…' : `下载 ${selectedModel.size}` }}</span>
          </button>
          <button class="btn btn--primary btn--with-shadow" type="button" :disabled="downloading" @click="$emit('confirm')">
            <span>{{ isInstalled(selected) ? '使用该模型，进入分析' : '稍后下载，先进入分析' }}</span>
          </button>
        </div>
      </div>

      <div v-if="downloading || downloadMsg" class="model-check__download">
        <ScanLineProgress :percent="downloadPercent" :active="downloading" variant="blue" />
        <span class="mono-label">{{ downloadMsg }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import {
  WHISPER_MODELS,
  VISION_MODEL_INFO,
  RUNTIME_COMPONENTS,
  findWhisperModel,
} from '~/data/modelCatalog'

const props = defineProps<{
  /** 已选中的 Whisper 模型 id */
  selected: string
  /** 后端探测到的运行时信息 */
  runtime: {
    device?: string
    torch?: string
    cuda?: boolean
    gpu?: string | null
    installed?: string[]
  }
  /** 后端是否可达 */
  online: boolean
}>()

const emit = defineEmits<{
  'update:selected': [id: string]
  confirm: []
}>()

const phase = ref<'scanning' | 'ready'>('scanning')
const scanPercent = ref(0)
const scanLog = ref<string[]>([])

const downloading = ref(false)
const downloadPercent = ref(0)
const downloadMsg = ref('')
const localInstalled = ref<string[]>([])

const selectedModel = computed(() => findWhisperModel(props.selected))

const installedList = computed(() => {
  const fromServer = props.runtime?.installed || []
  return Array.from(new Set([...fromServer, ...localInstalled.value]))
})

const installedCount = computed(() => installedList.value.length)

const isInstalled = (id: string) => installedList.value.includes(id)

// --- 扫描动画：逐条点亮检测项 ---
const SCAN_STEPS = [
  '扫描本地模型缓存目录 ~/.cache/whisper',
  `探测计算设备（${props.runtime?.device || 'CPU'}）`,
  '校验 YOLOv8n-Pose 姿态模型',
  '检查 ffmpeg 音视频解码链',
  '检查课标向量检索模型',
]

let scanTimer: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  let i = 0
  // 后端运行时数据可能异步到达，扫描过程给一个稳定时长，避免闪烁
  scanTimer = setInterval(() => {
    if (i < SCAN_STEPS.length) {
      scanLog.value.push(SCAN_STEPS[i]!)
      scanPercent.value = Math.round(((i + 1) / SCAN_STEPS.length) * 100)
      i++
    } else {
      if (scanTimer) clearInterval(scanTimer)
      scanPercent.value = 100
      setTimeout(() => {
        phase.value = 'ready'
      }, 260)
    }
  }, 260)
})

onUnmounted(() => {
  if (scanTimer) clearInterval(scanTimer)
})

// --- 模型下载 ---
const downloadSelected = async () => {
  const id = props.selected
  downloading.value = true
  downloadPercent.value = 0
  downloadMsg.value = `正在准备下载 ${selectedModel.value.name}…`

  try {
    const res = await fetch('/api/v1/models/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: id }),
    })

    if (!res.ok || !res.body) {
      throw new Error(`下载接口响应异常 (${res.status})`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.p !== undefined) downloadPercent.value = data.p
          if (data.msg) downloadMsg.value = data.msg
          if (data.error) {
            downloadMsg.value = `下载失败：${data.error}`
            ElMessage.error(`下载失败：${data.error}`)
          }
          if (data.done) {
            localInstalled.value = Array.from(new Set([...localInstalled.value, id]))
            downloadMsg.value = `${selectedModel.value.name} 下载完成`
            ElMessage.success(`${selectedModel.value.name} 模型已就绪`)
          }
        } catch {
          /* 忽略不完整的 SSE 分片 */
        }
      }
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : '下载失败'
    downloadMsg.value = msg
    ElMessage.error(msg)
  } finally {
    downloading.value = false
  }
}
</script>

<style scoped>
.model-check {
  display: flex;
  flex-direction: column;
}

/* --- Scanning --- */
.model-check__scanning {
  padding: var(--space-10) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.model-check__scan-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.model-check__scan-log {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.model-check__scan-line {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--muted-deep);
  animation: fade-in 400ms var(--ease-editorial) both;
}

.model-check__scan-tick {
  color: var(--primary);
}

/* --- Runtime --- */
.model-check__runtime {
  padding: var(--space-6);
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.model-check__runtime-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.model-check__runtime-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.model-check__warn {
  font-size: var(--text-sm);
  color: var(--color-warning-text);
  background: var(--color-warning-bg);
  border: 1px solid rgba(168, 128, 47, 0.25);
  padding: var(--space-3) var(--space-4);
  line-height: var(--leading-normal);
}

/* --- Picker --- */
.model-check__picker {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.model-check__picker-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0;
  border: 1px solid var(--border);
}

.model-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-4);
  background: transparent;
  border: 0;
  border-right: 1px solid var(--border);
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  color: inherit;
  position: relative;
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.model-card:last-child { border-right: 0; }

.model-card:hover { background: var(--surface); }

.model-card.is-selected {
  background: var(--primary-tint);
  box-shadow: inset 0 0 0 1px var(--primary);
}

.model-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.model-card__name {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: var(--font-normal);
}

.model-card__rec {
  color: var(--primary);
}

.model-card__installed {
  color: var(--muted-deep);
}

.model-card__size {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.model-card__size-value {
  font-family: var(--font-mono);
  font-size: var(--text-md);
  color: var(--fg);
  letter-spacing: 0.02em;
}

.model-card__size-label {
  color: var(--muted);
}

.model-card__acc {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.model-card__acc-bars {
  display: flex;
  gap: 2px;
}

.model-card__acc-bar {
  width: 3px;
  height: 12px;
  background: var(--border);
}

.model-card__acc-bar.is-on { background: var(--primary); }

.model-card__meta {
  display: flex;
  gap: var(--space-4);
  margin: 0;
}

.model-card__meta div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.model-card__meta dd { margin: 0; }

.model-card__scene {
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  color: var(--text-secondary);
}

/* --- Extras --- */
.model-check__extras {
  padding: var(--space-5) var(--space-6);
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.extra-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding-bottom: var(--space-2);
  border-bottom: 1px dashed var(--border);
}

.extra-row:last-child { border-bottom: 0; padding-bottom: 0; }

.extra-row__name {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--fg);
  min-width: 180px;
}

.extra-row__note {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* --- Actions --- */
.model-check__actions {
  padding: var(--space-5) var(--space-6);
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  background: var(--surface-alt);
}

.model-check__actions-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.model-check__selected-name {
  color: var(--primary);
}

.model-check__actions-btns {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.model-check__download {
  padding: var(--space-4) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  border-top: 1px solid var(--border);
}

/* --- Responsive --- */
@media (max-width: 1100px) {
  .model-grid { grid-template-columns: repeat(3, 1fr); }
  .model-card:nth-child(3n) { border-right: 0; }
  .model-card { border-bottom: 1px solid var(--border); }
}

@media (max-width: 700px) {
  .model-check__runtime-grid { grid-template-columns: repeat(2, 1fr); }
  .model-grid { grid-template-columns: 1fr; }
  .model-card { border-right: 0; }
}
</style>
