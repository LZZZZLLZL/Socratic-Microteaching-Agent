// ==========================================================================
// 学思践悟 — Analysis Composable
// 双模式：preview（本地演示，零依赖） / full（真实后端 + 模型）
//
// 状态提升为模块级单例（与 useAppMode 同构）：分析工作台已拆分为独立页面
// `/workspace`，若状态仍留在函数内部，路由跳转（去对话页再回来）会把结果、
// 进度与会话 ID 全部丢掉。单例让「上传 → 分析 → 去对话 → 回来」保持连续。
// ==========================================================================
import type { AnalysisResult } from '~/types'
import { DEMO_STEPS, DEMO_RESULT } from '~/data/previewData'
import type { WhisperModelOption } from '~/data/modelCatalog'

// --- 模块级共享状态 ---
const selectedFile = ref<File | null>(null)
const analyzing = ref(false)
const progress = ref(0)
const statusText = ref('')
const result = ref<AnalysisResult | null>(null)
const sessionId = ref('')

/** 模型监测面板是否展示（完整模式首次进入） */
const showModelPanel = ref(false)
/** 后端探测到的运行时环境 */
const modelRuntime = ref<{
  device?: string
  torch?: string
  cuda?: boolean
  gpu?: string | null
  installed?: string[]
}>({})
const modelRuntimeOnline = ref(false)
/** 本次分析使用的模型（结果页展示用） */
const usedModel = ref<WhisperModelOption | null>(null)

/** 预览演示计时器：挂在模块级，避免路由跳转后计时器泄漏 */
let previewTimer: ReturnType<typeof setInterval> | null = null

function clearPreviewTimer() {
  if (previewTimer !== null) {
    clearInterval(previewTimer)
    previewTimer = null
  }
}

export function useAnalysis() {
  const { isPreview, whisperModel } = useAppMode()

  // --- File handling ---
  const handleFileChange = (rawFile: File) => {
    selectedFile.value = rawFile
  }

  // --- SSE stream reader with line buffering ---
  const readSSEStream = async (
    response: Response,
    onEvent: (data: Record<string, any>) => void
  ) => {
    const reader = response.body?.getReader()
    if (!reader) throw new Error('无法读取响应流')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            onEvent(JSON.parse(line.slice(6)))
          } catch {
            /* 非 JSON 行，跳过 */
          }
        }
      }
    }
  }

  // --- 探测后端模型环境 ---
  const detectModels = async () => {
    try {
      const res = await fetch('/api/v1/models', { method: 'GET' })
      if (!res.ok) throw new Error(String(res.status))
      modelRuntime.value = await res.json()
      modelRuntimeOnline.value = true
    } catch {
      modelRuntimeOnline.value = false
      modelRuntime.value = {}
    }
    return modelRuntime.value
  }

  // --- 完整模式：上传前先做模型监测 ---
  const requestAnalysis = async () => {
    if (isPreview.value) {
      startPreview()
      return
    }
    showModelPanel.value = true
    await detectModels()
  }

  /** 模型面板确认后真正开始分析 */
  const confirmModelAndStart = async () => {
    showModelPanel.value = false
    await startAnalysis()
  }

  const cancelModelPanel = () => {
    showModelPanel.value = false
  }

  // --- Real analysis via SSE ---
  const startAnalysis = async () => {
    if (!selectedFile.value) {
      ElMessage.warning('请先选择视频文件')
      return
    }

    analyzing.value = true
    progress.value = 0
    statusText.value = '准备上传...'
    result.value = null
    showModelPanel.value = false

    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('whisper_model', whisperModel.value)

    try {
      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`服务器响应异常 (${response.status})`)
      }

      await readSSEStream(response, (data) => {
        if (data.error) {
          ElMessage.error(data.error)
          return
        }
        if (data.p !== undefined) {
          progress.value = data.p
          statusText.value = data.s
        }
        if (data.done && data.result) {
          result.value = data.result
          sessionId.value = data.result.session_id
        }
      })
    } catch (error) {
      const msg = error instanceof Error ? error.message : '分析失败，请重试'
      ElMessage.error(msg)
      console.error('Analysis error:', error)
    } finally {
      analyzing.value = false
    }
  }

  // --- Preview mode：纯本地演示，零依赖 ---
  const startPreview = () => {
    // 重入保护：旧计时器必须先清掉，否则连点会叠加多个 interval
    clearPreviewTimer()

    analyzing.value = true
    progress.value = 0
    statusText.value = '模拟演示模式...'
    result.value = null

    let i = 0
    previewTimer = setInterval(() => {
      if (i < DEMO_STEPS.length) {
        progress.value = DEMO_STEPS[i]!.p
        statusText.value = DEMO_STEPS[i]!.s
        i++
      } else {
        clearPreviewTimer()
        analyzing.value = false
        result.value = DEMO_RESULT
        sessionId.value = DEMO_RESULT.session_id
      }
    }, 380)
  }

  // --- Reset ---
  const reset = () => {
    clearPreviewTimer()
    analyzing.value = false
    selectedFile.value = null
    result.value = null
    sessionId.value = ''
    progress.value = 0
    statusText.value = ''
    showModelPanel.value = false
  }

  return {
    analyzing,
    progress,
    statusText,
    result,
    sessionId,
    selectedFile,
    showModelPanel,
    modelRuntime,
    modelRuntimeOnline,
    usedModel,
    handleFileChange,
    detectModels,
    requestAnalysis,
    confirmModelAndStart,
    cancelModelPanel,
    startAnalysis,
    startPreview,
    reset,
  }
}
