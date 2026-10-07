// ==========================================================================
// 学思践悟 — App Mode Store
// 双模式：preview（快速预览，纯前端零依赖） / full（完整版，真模型）
// ==========================================================================

export type AppMode = 'preview' | 'full'

const MODE_KEY = 'xssw-mode'
const WHISPER_KEY = 'xssw-whisper-model'
const DETECT_KEY = 'xssw-model-check-done'

/** 全局共享的响应式状态（模块级单例，SSR 下由 client 端水合） */
const mode = ref<AppMode>('preview')
const whisperModel = ref<string>('base')
const modelCheckDone = ref(false)
const hydrated = ref(false)

export function useAppMode() {
  const hydrate = () => {
    if (import.meta.server || hydrated.value) return
    hydrated.value = true
    try {
      const savedMode = localStorage.getItem(MODE_KEY)
      if (savedMode === 'full' || savedMode === 'preview') {
        mode.value = savedMode
      }
      const savedModel = localStorage.getItem(WHISPER_KEY)
      if (savedModel) whisperModel.value = savedModel
      modelCheckDone.value = localStorage.getItem(DETECT_KEY) === '1'
    } catch {
      /* localStorage 不可用时静默降级为默认值 */
    }
  }

  const setMode = (next: AppMode) => {
    mode.value = next
    if (import.meta.client) {
      try {
        localStorage.setItem(MODE_KEY, next)
      } catch { /* ignore */ }
    }
  }

  const setWhisperModel = (next: string) => {
    whisperModel.value = next
    if (import.meta.client) {
      try {
        localStorage.setItem(WHISPER_KEY, next)
      } catch { /* ignore */ }
    }
  }

  const markModelCheckDone = () => {
    modelCheckDone.value = true
    if (import.meta.client) {
      try {
        localStorage.setItem(DETECT_KEY, '1')
      } catch { /* ignore */ }
    }
  }

  const isPreview = computed(() => mode.value === 'preview')
  const isFull = computed(() => mode.value === 'full')

  return {
    mode,
    isPreview,
    isFull,
    whisperModel,
    modelCheckDone,
    hydrate,
    setMode,
    setWhisperModel,
    markModelCheckDone,
  }
}
