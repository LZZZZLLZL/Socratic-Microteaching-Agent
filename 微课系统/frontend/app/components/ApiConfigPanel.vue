<template>
  <div class="api-config">
    <!-- 当前状态条 -->
    <div class="api-config__status" :class="statusClass">
      <span class="api-config__dot" aria-hidden="true" />
      <span class="mono-label mono-label--strong">{{ statusText }}</span>
      <span v-if="config.configured" class="api-config__masked mono-value">
        {{ config.api_key_masked }}
      </span>
      <span class="api-config__spacer" />
      <span class="mono-label">SOURCE / {{ sourceLabel }}</span>
    </div>

    <div class="api-config__body">
      <!-- 快捷服务商 -->
      <div class="field">
        <label class="field__label mono-label">服务商预设</label>
        <div class="presets">
          <button
            v-for="p in config.presets"
            :key="p.value"
            type="button"
            class="preset"
            :class="{ 'is-active': form.base_url === p.value }"
            @click="applyPreset(p.value)"
          >
            {{ p.label }}
          </button>
        </div>
      </div>

      <!-- API Key -->
      <div class="field">
        <label class="field__label mono-label" for="api-key">
          API Key
          <span v-if="config.configured" class="field__hint">已配置，留空则保持不变</span>
        </label>
        <div class="field__row">
          <input
            id="api-key"
            v-model="form.api_key"
            class="field__input"
            :type="showKey ? 'text' : 'password'"
            :placeholder="config.configured ? '••••••••（留空不修改）' : 'sk-...'"
            autocomplete="off"
            spellcheck="false"
            @keydown.enter="save"
          />
          <button class="icon-btn mono-label" type="button" @click="showKey = !showKey">
            {{ showKey ? 'HIDE' : 'SHOW' }}
          </button>
        </div>
      </div>

      <!-- 服务地址 -->
      <div class="field">
        <label class="field__label mono-label" for="base-url">服务地址 (Base URL)</label>
        <input
          id="base-url"
          v-model="form.base_url"
          class="field__input"
          type="text"
          placeholder="https://api.deepseek.com"
          autocomplete="off"
          spellcheck="false"
        />
      </div>

      <!-- 模型名 -->
      <div class="field">
        <label class="field__label mono-label" for="model">模型名</label>
        <input
          id="model"
          v-model="form.model"
          class="field__input"
          type="text"
          list="model-suggestions"
          placeholder="deepseek-chat"
          autocomplete="off"
          spellcheck="false"
        />
        <datalist id="model-suggestions">
          <option v-for="m in config.model_suggestions" :key="m" :value="m" />
        </datalist>
      </div>

      <!-- 测试结果 -->
      <div v-if="testResult" class="api-config__result" :class="testResult.ok ? 'is-ok' : 'is-bad'">
        <span class="api-config__result-icon" aria-hidden="true">{{ testResult.ok ? '✓' : '✗' }}</span>
        <span class="api-config__result-text">{{ testResult.message }}</span>
      </div>

      <!-- 操作 -->
      <div class="api-config__actions">
        <button
          class="btn btn--ghost btn--sm"
          type="button"
          :disabled="testing || saving"
          @click="test"
        >
          <span>{{ testing ? '测试中…' : '测试连接' }}</span>
        </button>
        <button
          class="btn btn--primary btn--sm"
          type="button"
          :disabled="saving || testing || !dirty"
          @click="save"
        >
          <span>{{ saving ? '保存中…' : '保存并生效' }}</span>
        </button>
        <button
          v-if="config.configured"
          class="btn btn--quiet btn--sm"
          type="button"
          :disabled="saving || testing"
          @click="clear"
        >
          <span>清除</span>
        </button>
      </div>

      <!-- 保存后的扫描线反馈 -->
      <div v-if="saving || justSaved" class="api-config__scan">
        <ScanLineProgress :percent="saving ? 60 : 100" :active="saving" />
      </div>

      <p class="api-config__note">
        密钥仅保存在本机后端 <code>backend/data/runtime_config.json</code>（权限 600），
        保存后立即生效，无需重启。查询接口只返回掩码，不回传明文。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ApiConfigPanel — 完整模式的 API 配置面板
 * 支持填写 API Key / 服务地址 / 模型名，并做真实连通性测试
 */

interface ApiConfigStatus {
  configured: boolean
  api_key_masked: string
  base_url: string
  model: string
  source: string
  presets: { label: string; value: string }[]
  model_suggestions: string[]
  defaults: { base_url: string; model: string }
}

const emit = defineEmits<{ updated: [configured: boolean] }>()

const config = ref<ApiConfigStatus>({
  configured: false,
  api_key_masked: '',
  base_url: 'https://api.deepseek.com',
  model: 'deepseek-chat',
  source: 'none',
  presets: [],
  model_suggestions: [],
  defaults: { base_url: 'https://api.deepseek.com', model: 'deepseek-chat' },
})

const form = reactive({ api_key: '', base_url: '', model: '' })
const showKey = ref(false)
const testing = ref(false)
const saving = ref(false)
const justSaved = ref(false)
const loading = ref(true)
const testResult = ref<{ ok: boolean; message: string } | null>(null)

// --- 派生状态 ---
const statusText = computed(() => {
  if (loading.value) return '正在读取配置…'
  return config.value.configured ? 'API 已配置' : 'API 未配置'
})

const sourceLabel = computed(() => {
  const map: Record<string, string> = {
    ui: '界面填写',
    file: '本地保存',
    env: '.env 文件',
    none: '未设置',
  }
  return map[config.value.source] || config.value.source
})

const statusClass = computed(() => ({
  'is-ok': !loading.value && config.value.configured,
  'is-bad': !loading.value && !config.value.configured,
}))

/** 表单是否与已保存配置不同（Key 留空视为未改） */
const dirty = computed(() => {
  if (form.api_key.trim()) return true
  if (form.base_url.trim() !== config.value.base_url) return true
  if (form.model.trim() !== config.value.model) return true
  return false
})

// --- 读取 ---
const load = async () => {
  loading.value = true
  try {
    const res = await fetch('/api/v1/config')
    if (!res.ok) throw new Error(String(res.status))
    const data: ApiConfigStatus = await res.json()
    config.value = data
    form.base_url = data.base_url
    form.model = data.model
    form.api_key = ''
    emit('updated', data.configured)
  } catch {
    ElMessage.error('无法读取 API 配置，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

// --- 预设 ---
const applyPreset = (url: string) => {
  form.base_url = url
  testResult.value = null
}

// --- 测试连接 ---
const test = async () => {
  testing.value = true
  testResult.value = null
  try {
    const res = await fetch('/api/v1/config/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        // 未填写新 Key 时传空，后端回退到已保存的配置
        api_key: form.api_key.trim() || undefined,
        base_url: form.base_url.trim() || undefined,
        model: form.model.trim() || undefined,
      }),
    })
    const data = await res.json()
    testResult.value = { ok: !!data.ok, message: data.message || '未知结果' }
  } catch {
    testResult.value = { ok: false, message: '无法连接后端服务' }
  } finally {
    testing.value = false
  }
}

// --- 保存 ---
const save = async () => {
  saving.value = true
  testResult.value = null
  try {
    const payload: Record<string, string> = {
      base_url: form.base_url.trim(),
      model: form.model.trim(),
    }
    // 只在用户填了新 Key 时才提交，避免把已保存的密钥覆盖成空
    if (form.api_key.trim()) payload.api_key = form.api_key.trim()

    const res = await fetch('/api/v1/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()

    if (data.status !== 'ok') {
      ElMessage.error(data.message || '保存失败')
      return
    }

    config.value = data
    form.api_key = ''
    justSaved.value = true
    setTimeout(() => (justSaved.value = false), 1800)
    emit('updated', data.configured)
    ElMessage.success('配置已保存并生效')
  } catch {
    ElMessage.error('保存失败，请检查后端服务')
  } finally {
    saving.value = false
  }
}

// --- 清除 ---
const clear = async () => {
  saving.value = true
  try {
    const res = await fetch('/api/v1/config/clear', { method: 'POST' })
    const data = await res.json()
    config.value = data
    form.api_key = ''
    form.base_url = data.base_url || config.value.defaults.base_url
    form.model = data.model || config.value.defaults.model
    testResult.value = null
    emit('updated', data.configured)
    ElMessage.success('已清除 API 配置')
  } catch {
    ElMessage.error('清除失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)

defineExpose({ reload: load })
</script>

<style scoped>
.api-config {
  display: flex;
  flex-direction: column;
}

/* ══════════ 状态条 ══════════ */
.api-config__status {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border);
  background: var(--surface-alt);
  flex-wrap: wrap;
}

.api-config__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--muted);
  flex-shrink: 0;
}

.api-config__status.is-ok .api-config__dot {
  background: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-tint);
}

.api-config__status.is-bad .api-config__dot {
  background: var(--color-warning);
}

.api-config__status.is-ok .mono-label--strong { color: var(--primary); }
.api-config__status.is-bad .mono-label--strong { color: var(--color-warning-text); }

.api-config__masked {
  font-size: var(--text-xs);
  color: var(--muted-deep);
}

.api-config__spacer { flex: 1; }

/* ══════════ 表单 ══════════ */
.api-config__body {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field__label {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  color: var(--fg);
}

.field__hint {
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--muted);
  text-transform: none;
}

.field__row {
  display: flex;
  gap: var(--space-2);
}

.field__input {
  flex: 1;
  width: 100%;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  background: var(--surface);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  letter-spacing: 0.04em;
  color: var(--fg);
  outline: none;
  transition: border-color var(--transition-fast) var(--ease-editorial);
}

.field__input:focus {
  border-color: var(--primary);
}

.field__input::placeholder {
  color: var(--muted);
}

.icon-btn {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted-deep);
  cursor: pointer;
  transition:
    color var(--transition-fast) var(--ease-editorial),
    border-color var(--transition-fast) var(--ease-editorial);
}

.icon-btn:hover {
  color: var(--primary);
  border-color: var(--primary);
}

/* ══════════ 预设 ══════════ */
.presets {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.preset {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted-deep);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  cursor: pointer;
  transition:
    color var(--transition-fast) var(--ease-editorial),
    border-color var(--transition-fast) var(--ease-editorial),
    background-color var(--transition-fast) var(--ease-editorial);
}

.preset:hover {
  color: var(--fg);
  border-color: var(--border-strong);
}

.preset.is-active {
  background: var(--primary-tint);
  border-color: var(--primary);
  color: var(--primary);
}

/* ══════════ 测试结果 ══════════ */
.api-config__result {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
}

.api-config__result.is-ok {
  background: var(--color-success-bg);
  border-color: rgba(61, 112, 104, 0.3);
  color: var(--color-success-text);
}

.api-config__result.is-bad {
  background: var(--color-error-bg);
  border-color: rgba(156, 59, 48, 0.3);
  color: var(--color-error-text);
}

.api-config__result-icon {
  flex-shrink: 0;
  font-family: var(--font-mono);
}

/* ══════════ 操作 ══════════ */
.api-config__actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding-top: var(--space-2);
  border-top: 1px solid var(--border);
}

.api-config__scan {
  margin-top: var(--space-1);
}

.api-config__note {
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  color: var(--muted-deep);
}

.api-config__note code {
  font-family: var(--font-mono);
  font-size: 0.92em;
  background: var(--primary-tint);
  color: var(--primary);
  padding: 1px 5px;
}

/* ══════════ 响应式 ══════════ */
@media (max-width: 640px) {
  .api-config__body { padding: var(--space-4); }
  .api-config__actions :deep(.btn) { width: 100%; }
}
</style>
