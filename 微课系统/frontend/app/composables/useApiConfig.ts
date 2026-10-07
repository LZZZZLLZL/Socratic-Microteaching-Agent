// ==========================================================================
// 学思践悟 — API Config Store
//
// 全局共享「AI 是否已配置」状态，供多处消费：
//   - 顶部提示条（未配置时提醒进入系统后去配置）
//   - 工作台 API 设置面板（读写后端 /api/v1/config）
//   - 工作台结果页（决定 AI 点评是否可用）
//
// 模块级单例：与 useAppMode / useAnalysis 同构，跨路由保持一致。
// 后端地址一律走相对路径 /api/v1/*，由 Nuxt 代理到 FastAPI。
// ==========================================================================

export interface ApiConfigStatus {
  configured: boolean
  api_key_masked: string
  base_url: string
  model: string
  source: string
  presets: { label: string; value: string }[]
  model_suggestions: string[]
  defaults: { base_url: string; model: string }
}

/** 「不再提醒」的本地存储键 */
const DISMISS_KEY = 'xssw-api-reminder-dismissed'

// --- 模块级共享状态 ---
const configured = ref(false)
const loading = ref(true)
/** 后端不可达时为 true（与「未配置」区分：后者可配置，前者要启动后端） */
const offline = ref(false)
const apiKeyMasked = ref('')
const dismissed = ref(false)
const hydrated = ref(false)

/** 拉取一次后端配置状态；失败时标记 offline 而不是谎报「已配置」。 */
async function refreshApiConfig(): Promise<boolean> {
  loading.value = true
  try {
    const res = await fetch('/api/v1/config', { method: 'GET' })
    if (!res.ok) throw new Error(String(res.status))
    const data = (await res.json()) as ApiConfigStatus
    configured.value = Boolean(data.configured)
    apiKeyMasked.value = data.api_key_masked || ''
    offline.value = false
  } catch {
    // 后端没起来 ≠ 未配置：不要把用户引到填 Key 的死路上
    configured.value = false
    apiKeyMasked.value = ''
    offline.value = true
  } finally {
    loading.value = false
    return configured.value
  }
}

export function useApiConfig() {
  /** 读取一次 localStorage 的「不再提醒」标记（仅客户端）。 */
  const hydrate = () => {
    if (import.meta.server || hydrated.value) return
    hydrated.value = true
    try {
      dismissed.value = localStorage.getItem(DISMISS_KEY) === '1'
    } catch {
      /* localStorage 不可用时保持默认（提醒可见） */
    }
  }

  /** 用户点了「不再提醒」。 */
  const dismiss = () => {
    dismissed.value = true
    if (import.meta.client) {
      try {
        localStorage.setItem(DISMISS_KEY, '1')
      } catch {
        /* ignore */
      }
    }
  }

  /** 配置面板保存成功后调用，同步全局状态。 */
  const markConfigured = (isConfigured: boolean) => {
    configured.value = isConfigured
    offline.value = false
  }

  /** 是否应展示提醒：未配置、未忽略、且不是后端离线。 */
  const shouldRemind = computed(
    () => !loading.value && !offline.value && !configured.value && !dismissed.value
  )

  return {
    configured,
    loading,
    offline,
    apiKeyMasked,
    dismissed,
    shouldRemind,
    hydrate,
    dismiss,
    markConfigured,
    refreshApiConfig,
  }
}
