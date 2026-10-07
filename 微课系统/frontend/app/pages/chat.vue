<template>
  <div class="page">
    <!-- 顶部条 -->
    <div class="chat-header">
      <div class="chat-header__inner container-wide">
        <NuxtLink to="/" class="back-link">
          <span aria-hidden="true">←</span>
          <span>返回分析</span>
        </NuxtLink>

        <div class="chat-header__title">
          <span class="mono-label mono-label--strong">SOCRATIC DIALOGUE</span>
          <span class="chat-header__sep" aria-hidden="true" />
          <span class="mono-label">苏格拉底式对话</span>
        </div>

        <div class="chat-header__right">
          <span class="ebadge" :class="{ 'ebadge--solid': isPreview }">
            <span v-if="isPreview" class="pulse-dot" aria-hidden="true" />
            {{ isPreview ? 'PREVIEW / 脚本模式' : 'FULL / 模型驱动' }}
          </span>
          <button
            v-if="!isPreview"
            class="api-entry mono-label"
            type="button"
            :class="{ 'is-bad': !apiConfigured }"
            @click="showApiPanel = !showApiPanel"
          >
            <span class="api-entry__dot" aria-hidden="true" />
            {{ apiConfigured ? 'API 已配置' : '未配置 API' }}
          </button>
        </div>
      </div>
      <ScanLineProgress
        v-if="isPreview"
        :percent="previewProgress"
        :active="!previewFinished"
      />
    </div>

    <!-- API 配置抽屉（完整模式） -->
    <div v-if="showApiPanel && !isPreview" class="api-drawer">
      <EditorialCard index="00">
        <template #head>
          <h2 class="ecard__title">
            <span class="ecard__index">00</span>
            <span>API 设置</span>
          </h2>
          <button class="api-drawer__close mono-label" type="button" @click="showApiPanel = false">
            关闭 ×
          </button>
        </template>
        <ApiConfigPanel @updated="onApiUpdated" />
      </EditorialCard>
    </div>

    <!-- 对话区 -->
    <div class="chat-container container-narrow">
      <!-- 预览模式：轮次指示 -->
      <div v-if="isPreview" class="rounds" role="status">
        <div
          v-for="n in 4"
          :key="n"
          class="rounds__item"
          :class="{
            'is-done': round > n,
            'is-active': round === n && !previewFinished,
          }"
        >
          <span class="rounds__num mono-label">{{ String(n).padStart(2, '0') }}</span>
          <span class="rounds__dot" aria-hidden="true" />
        </div>
        <span class="rounds__label mono-label">
          {{ previewFinished ? 'DEMO COMPLETE / 演示完成' : `ROUND ${round} / 4` }}
        </span>
      </div>

      <div ref="messagesRef" class="messages" @scroll="onScroll">
        <!-- 空状态 -->
        <div v-if="messages.length === 0 && !loading" class="empty-state">
          <span class="empty-state__code mono-label">
            {{ sessionId ? 'READY' : 'NO SESSION' }}
          </span>
          <h2 class="empty-state__title">
            {{ sessionId ? 'AI 导师已准备就绪' : '请先上传视频开始分析' }}
          </h2>
          <p class="empty-state__desc">
            {{
              sessionId
                ? '视频分析已完成。请开始向 AI 导师提问，反思您的教学。'
                : '前往首页上传微课视频，获取 AI 苏格拉底式点评后再来对话。'
            }}
          </p>
          <div v-if="sessionId" class="empty-state__actions">
            <NuxtLink v-if="!sessionId" to="/" class="btn btn--primary">
              <span>前往上传视频</span>
            </NuxtLink>
          </div>
        </div>

        <!-- 消息列表 -->
        <TransitionGroup name="msg">
          <div
            v-for="(msg, idx) in messages"
            :key="`${idx}-${msg.role}`"
            :class="['message-row', msg.role]"
          >
            <div class="message-avatar mono-label" aria-hidden="true">
              {{ msg.role === 'user' ? 'YOU' : 'AI' }}
            </div>
            <div class="message-bubble">
              <div class="message-content" v-html="renderMessage(msg.content)" />
              <button
                v-if="msg.role === 'assistant' && msg.content"
                class="copy-btn mono-label"
                type="button"
                title="复制消息"
                @click="copyMessage(msg.content)"
              >
                COPY
              </button>
            </div>
          </div>
        </TransitionGroup>

        <div v-if="loading" class="typing-indicator">
          <span class="typing-cursor" aria-hidden="true">|</span>
          <span class="mono-label">AI 导师正在思考</span>
        </div>
      </div>

      <!-- ══════ 交互区 ══════ -->
      <div class="composer">
        <!-- 预览模式：选项式 -->
        <template v-if="isPreview">
          <!-- 收尾提示 -->
          <div v-if="previewFinished" class="upsell">
            <div class="upsell__head">
              <span class="upsell__tag mono-label">DEMO END</span>
              <h3 class="upsell__title">{{ DEMO_UPSELL_TITLE }}</h3>
              <p class="upsell__text">
                快速预览到此结束。完整版会接入真实模型，针对你的视频生成无可复制的追问。
              </p>
            </div>
            <ul class="upsell__list">
              <li v-for="item in DEMO_UPSELL_ITEMS" :key="item" class="upsell__item">
                <span class="upsell__tick" aria-hidden="true">—</span>{{ item }}
              </li>
            </ul>
            <div class="upsell__actions">
              <button class="btn btn--primary btn--with-shadow" type="button" @click="switchToFull">
                <span>切换到完整模式</span>
              </button>
              <button class="btn btn--quiet" type="button" @click="restartPreview">
                <span>重新演示一遍</span>
              </button>
            </div>
          </div>

          <!-- 当前轮次选项 -->
          <div v-else-if="currentTurn" class="choices">
            <div class="choices__prompt">
              <span class="choices__index mono-label">ROUND {{ currentTurn.round }}</span>
              <p class="choices__question">{{ currentTurn.prompt }}</p>
              <p v-if="currentTurn.hint" class="choices__hint mono-label">{{ currentTurn.hint }}</p>
            </div>

            <div class="choices__list">
              <button
                v-for="c in currentTurn.choices"
                :key="c.label"
                class="choice"
                type="button"
                :disabled="loading"
                @click="pickChoice(c)"
              >
                <span class="choice__label">{{ c.label }}</span>
                <span class="choice__arrow" aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        </template>

        <!-- 完整模式：自由输入 -->
        <template v-else>
          <div class="input-wrapper">
            <textarea
              v-model="inputMessage"
              class="input-area"
              rows="2"
              placeholder="输入你的问题或反思，AI 导师会引导你深入思考…"
              :disabled="loading"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.escape="blurInput"
            />
            <div class="input-actions">
              <span class="mono-label">ENTER 发送 · SHIFT+ENTER 换行</span>
              <div class="buttons">
                <button class="btn btn--quiet btn--sm" type="button" :disabled="loading" @click="clearChat">
                  <span>清除</span>
                </button>
                <button
                  class="btn btn--primary btn--sm"
                  type="button"
                  :disabled="loading || !inputMessage.trim()"
                  @click="sendMessage"
                >
                  <span>{{ loading ? '发送中' : '发送' }}</span>
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '~/types'
import {
  DEMO_SCRIPT,
  DEMO_CHAT_INITIAL,
  DEMO_CLOSING,
  DEMO_UPSELL_TITLE,
  DEMO_UPSELL_ITEMS,
  DEMO_SESSION_ID,
} from '~/data/previewData'
import type { ScriptChoice } from '~/data/previewData'

const route = useRoute()
const { isPreview, setMode, hydrate } = useAppMode()

const sessionId = computed(() => (route.query.session as string) || '')

// --- API 配置状态（完整模式）---
const showApiPanel = ref(false)
const apiConfigured = ref(false)

const onApiUpdated = (configured: boolean) => {
  apiConfigured.value = configured
  // 刚配置好 API 时，如果还没有 AI 回复，自动补一次初始点评
  if (configured && messages.value.length === 0) {
    fetchAIInitial()
  }
}

/** 查询后端 API 配置状态（用于顶栏提示） */
const loadApiStatus = async () => {
  try {
    const res = await fetch('/api/v1/config')
    if (!res.ok) return
    const data = await res.json()
    apiConfigured.value = !!data.configured
  } catch {
    /* 后端不可达时保持默认 */
  }
}

const inputMessage = ref('')
const loading = ref(false)
const messages = ref<ChatMessage[]>([])
const messagesRef = ref<HTMLElement>()

// --- 预览模式状态 ---
const round = ref(1)
const previewFinished = ref(false)
const isDemoSession = computed(() => sessionId.value === DEMO_SESSION_ID)

const currentTurn = computed(() => DEMO_SCRIPT.find((t) => t.round === round.value))
const previewProgress = computed(() => {
  if (previewFinished.value) return 100
  return Math.round(((round.value - 1) / DEMO_SCRIPT.length) * 100)
})

// --- 消息渲染（轻量 Markdown） ---
const renderMessage = (text: string): string => {
  if (!text) return ''
  const esc = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return esc
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\n/g, '<br>')
}

// --- 滚动 ---
const isNearBottom = ref(true)

const onScroll = () => {
  if (!messagesRef.value) return
  const { scrollTop, scrollHeight, clientHeight } = messagesRef.value
  isNearBottom.value = scrollHeight - scrollTop - clientHeight < 120
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value && isNearBottom.value) {
      messagesRef.value.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
    }
  })
}

// --- 复制 ---
const copyMessage = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

const blurInput = () => {
  ;(document.activeElement as HTMLElement)?.blur()
}

// ==========================================================================
// 预览模式：选项式脚本对话
// ==========================================================================
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/** 逐字/逐段输出 AI 回复，制造流式感 */
const streamScriptedReply = async (paragraphs: string[]) => {
  messages.value.push({ role: 'assistant', content: '' })
  const idx = messages.value.length - 1
  let acc = ''

  for (const para of paragraphs) {
    // 逐段之间留出停顿，模拟思考
    await sleep(320)
    const tokens = para.match(/.{1,6}/g) || [para]
    for (const tk of tokens) {
      acc += tk
      if (messages.value[idx]) messages.value[idx]!.content = acc
      scrollToBottom()
      await sleep(22)
    }
    acc += '\n\n'
    if (messages.value[idx]) messages.value[idx]!.content = acc.trimEnd()
    scrollToBottom()
  }
  return acc.trimEnd()
}

/** 用户点击选项 → 作为用户发言入列 → 流式输出对应 AI 回复 → 推进轮次 */
const pickChoice = async (choice: ScriptChoice) => {
  if (loading.value) return

  messages.value.push({ role: 'user', content: choice.message })
  loading.value = true
  scrollToBottom()

  await streamScriptedReply(choice.reply)

  loading.value = false
  scrollToBottom()

  if (round.value < DEMO_SCRIPT.length) {
    round.value += 1
    // 新一轮的引导语作为 AI 追问出现
    const next = DEMO_SCRIPT.find((t) => t.round === round.value)
    if (next) {
      await sleep(420)
      messages.value.push({ role: 'assistant', content: next.prompt })
      scrollToBottom()
    }
  } else {
    previewFinished.value = true
    await sleep(560)
    messages.value.push(DEMO_CLOSING)
    scrollToBottom()
  }
}

/** 预览模式：初始化开场白 */
const initPreview = async () => {
  loading.value = true
  await sleep(420)
  await streamScriptedReply([DEMO_CHAT_INITIAL])
  loading.value = false
  scrollToBottom()
}

/** 重新演示 */
const restartPreview = () => {
  messages.value = []
  round.value = 1
  previewFinished.value = false
  initPreview()
}

const switchToFull = () => {
  setMode('full')
  navigateTo('/')
}

// ==========================================================================
// 完整模式：真实后端对话
// ==========================================================================
const streamResponse = async (response: Response) => {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('无法读取响应流')

  const decoder = new TextDecoder()
  let fullContent = ''
  let buffer = ''

  messages.value.push({ role: 'assistant', content: '' })
  const msgIndex = messages.value.length - 1

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
        if (data.error) {
          ElMessage.error(data.error)
          return
        }
        if (data.text) {
          fullContent += data.text
          if (messages.value[msgIndex]) messages.value[msgIndex]!.content = fullContent
          scrollToBottom()
        }
      } catch {
        /* 忽略解析碎片 */
      }
    }
  }
}

const postChat = async (message: string) => {
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId.value, message }),
  })
  if (!response.ok) throw new Error(`服务器响应异常 (${response.status})`)
  await streamResponse(response)
}

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || loading.value) return

  inputMessage.value = ''
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  scrollToBottom()

  try {
    await postChat(text)
  } catch (error) {
    const msg = error instanceof Error ? error.message : '发送失败，请重试'
    ElMessage.error(msg)
    console.error('Chat error:', error)
  } finally {
    loading.value = false
  }
}

const clearChat = async () => {
  try {
    if (sessionId.value) {
      await fetch('/api/v1/chat/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId.value }),
      })
    }
    messages.value = []
    ElMessage.success('对话已清除')
  } catch (error) {
    ElMessage.error('清除失败')
    console.error('Clear error:', error)
  }
}

/** 完整模式：拉取 AI 初始点评 */
const fetchAIInitial = async () => {
  if (!sessionId.value) return
  loading.value = true
  try {
    await postChat('')
  } catch (error) {
    const msg = error instanceof Error ? error.message : '获取 AI 点评失败'
    ElMessage.error(msg)
    console.error('Initial fetch error:', error)
  } finally {
    loading.value = false
  }
}

// ==========================================================================
// 生命周期
// ==========================================================================
onMounted(async () => {
  hydrate()

  // 完整模式：先读一次 API 配置状态，便于顶栏提示与失败引导
  if (!isPreview.value) {
    await loadApiStatus()
  }

  if (!sessionId.value) return

  if (isPreview.value) {
    await initPreview()
  } else {
    await fetchAIInitial()
  }
})

watch(
  () => route.query.session,
  (newId) => {
    if (newId && messages.value.length === 0) {
      if (isPreview.value) initPreview()
      else fetchAIInitial()
    }
  }
)
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 96px);
}

/* ══════════ HEADER ══════════ */
.chat-header {
  position: sticky;
  top: 64px;
  z-index: 50;
  background: rgba(247, 246, 242, 0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}

.chat-header__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  height: 56px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--muted-deep);
  text-decoration: none;
  transition:
    color var(--transition-fast) var(--ease-editorial),
    gap var(--transition-base) var(--ease-editorial);
}

.back-link:hover {
  color: var(--primary);
  gap: var(--space-4);
}

.chat-header__title {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.chat-header__sep {
  width: 24px;
  height: 1px;
  background: var(--border-strong);
}

.chat-header__right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* ══════════ API 入口 ══════════ */
.api-entry {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  transition:
    border-color var(--transition-fast) var(--ease-editorial),
    color var(--transition-fast) var(--ease-editorial),
    letter-spacing var(--transition-base) var(--ease-editorial);
}

.api-entry:hover {
  border-color: var(--primary);
  letter-spacing: var(--tracking-wider);
}

.api-entry.is-bad {
  color: var(--color-warning-text);
  border-color: rgba(168, 128, 47, 0.4);
}

.api-entry__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

/* ══════════ API 抽屉 ══════════ */
.api-drawer {
  position: fixed;
  top: 96px;
  right: var(--space-6);
  width: min(560px, calc(100vw - var(--space-8)));
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  z-index: 90;
  background: var(--bg);
  box-shadow: 0 24px 60px -30px rgba(28, 28, 28, 0.55);
  animation: fade-in-up 500ms var(--ease-editorial) both;
}

.api-drawer__close {
  border: 0;
  background: none;
  color: var(--muted-deep);
  cursor: pointer;
  transition: color var(--transition-fast) var(--ease-editorial);
}

.api-drawer__close:hover {
  color: var(--primary);
}

@media (max-width: 640px) {
  .api-drawer {
    top: 88px;
    right: var(--space-3);
    left: var(--space-3);
    width: auto;
  }
}

/* ══════════ CONTAINER ══════════ */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: var(--space-8);
  padding-bottom: var(--space-6);
  min-height: 0;
}

/* ══════════ ROUNDS ══════════ */
.rounds {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
}

.rounds__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  opacity: 0.4;
  transition: opacity var(--transition-base) var(--ease-editorial);
}

.rounds__item.is-done { opacity: 1; }
.rounds__item.is-active { opacity: 1; }

.rounds__dot {
  width: 6px;
  height: 6px;
  border: 1px solid var(--border-strong);
  transition:
    background-color var(--transition-fast) var(--ease-editorial),
    border-color var(--transition-fast) var(--ease-editorial);
}

.rounds__item.is-done .rounds__dot {
  background: var(--primary);
  border-color: var(--primary);
}

.rounds__item.is-active .rounds__dot {
  background: var(--primary);
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-tint);
}

.rounds__num {
  color: var(--muted-deep);
}

.rounds__label {
  margin-left: auto;
  color: var(--muted-deep);
}

/* ══════════ MESSAGES ══════════ */
.messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  overflow-y: auto;
  padding-right: var(--space-2);
  min-height: 40vh;
  max-height: 56vh;
  scrollbar-width: thin;
  scrollbar-color: var(--border-strong) transparent;
}

.messages::-webkit-scrollbar { width: 4px; }
.messages::-webkit-scrollbar-track { background: transparent; }
.messages::-webkit-scrollbar-thumb { background: var(--border-strong); }

.empty-state {
  margin: auto;
  text-align: center;
  padding: var(--space-16) var(--space-6);
  max-width: 32rem;
}

.empty-state__code {
  display: block;
  margin-bottom: var(--space-6);
}

.empty-state__title {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: var(--font-light);
  margin-bottom: var(--space-4);
}

.empty-state__desc {
  font-size: var(--text-md);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-8);
}

.message-row {
  display: flex;
  gap: var(--space-4);
  animation: fade-in-up 700ms var(--ease-editorial) both;
}

.message-row.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted-deep);
  background: var(--surface-alt);
}

.message-row.assistant .message-avatar {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-tint);
}

.message-bubble {
  position: relative;
  max-width: 80%;
  padding: var(--space-5) var(--space-6);
  border: 1px solid var(--border);
  background: var(--bg);
}

.message-row.user .message-bubble {
  background: var(--surface);
  border-color: var(--border-strong);
}

.message-content {
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--text-primary);
  word-break: break-word;
}

.message-content :deep(strong) {
  font-weight: var(--font-medium);
  color: var(--primary);
}

.message-content :deep(.inline-code) {
  font-family: var(--font-mono);
  font-size: 0.92em;
  background: var(--primary-tint);
  color: var(--primary);
  padding: 1px 5px;
}

.copy-btn {
  position: absolute;
  top: var(--space-2);
  right: var(--space-3);
  border: 0;
  background: none;
  color: var(--muted);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--transition-fast) var(--ease-editorial);
}

.message-bubble:hover .copy-btn { opacity: 1; }

.copy-btn:hover { color: var(--primary); }

.typing-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-left: 56px;
}

.typing-cursor {
  font-family: var(--font-mono);
  color: var(--primary);
  animation: caret-blink 900ms step-end infinite;
}

/* ══════════ COMPOSER ══════════ */
.composer {
  margin-top: var(--space-6);
  border-top: 1px solid var(--border);
  padding-top: var(--space-6);
}

/* --- Choices --- */
.choices {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  animation: fade-in-up 700ms var(--ease-editorial) both;
}

.choices__prompt {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.choices__index {
  color: var(--primary);
}

.choices__question {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: var(--font-light);
  line-height: var(--leading-snug);
  color: var(--fg);
}

.choices__hint {
  color: var(--muted);
}

.choices__list {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid var(--border);
}

.choice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6);
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--border);
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  color: inherit;
  position: relative;
  overflow: hidden;
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.choice:last-child { border-bottom: 0; }

.choice::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--primary);
  transform: scaleY(0);
  transform-origin: top;
  transition: transform var(--transition-base) var(--ease-editorial);
}

.choice:hover:not(:disabled) {
  background: var(--surface);
}

.choice:hover:not(:disabled)::before {
  transform: scaleY(1);
}

.choice:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.choice__label {
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--text-primary);
}

.choice__arrow {
  flex-shrink: 0;
  font-family: var(--font-mono);
  color: var(--muted);
  transition:
    transform var(--transition-base) var(--ease-editorial),
    color var(--transition-fast) var(--ease-editorial);
}

.choice:hover:not(:disabled) .choice__arrow {
  transform: translateX(6px);
  color: var(--primary);
}

/* --- Upsell --- */
.upsell {
  border: 1px solid var(--border);
  border-left: 2px solid var(--primary);
  background: var(--surface-alt);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  animation: fade-in-up 900ms var(--ease-editorial) both;
}

.upsell__head {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.upsell__tag { color: var(--primary); }

.upsell__title {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: var(--font-light);
}

.upsell__text {
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
  max-width: 40rem;
}

.upsell__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  border-top: 1px solid var(--border);
  padding-top: var(--space-5);
}

.upsell__item {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  color: var(--text-secondary);
}

.upsell__tick {
  color: var(--primary);
  flex-shrink: 0;
}

.upsell__actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

/* --- Text input (full mode) --- */
.input-wrapper {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: var(--space-4);
}

.input-area {
  width: 100%;
  border: 0;
  background: transparent;
  resize: none;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--fg);
  outline: none;
}

.input-area::placeholder {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
  color: var(--muted);
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-top: var(--space-3);
  flex-wrap: wrap;
}

.buttons {
  display: flex;
  gap: var(--space-2);
}

/* ══════════ TRANSITIONS ══════════ */
.msg-enter-active { transition: all 700ms var(--ease-editorial); }
.msg-leave-active { transition: all 300ms var(--ease-editorial); }
.msg-enter-from { opacity: 0; transform: translateY(16px); }
.msg-leave-to { opacity: 0; }

/* ══════════ RESPONSIVE ══════════ */
@media (max-width: 768px) {
  .chat-header__title { display: none; }
  .rounds__label { margin-left: 0; width: 100%; }
  .message-bubble { max-width: 92%; }
  .messages { max-height: none; }
  .upsell__list { grid-template-columns: 1fr; }
  .upsell { padding: var(--space-6); }
}
</style>
