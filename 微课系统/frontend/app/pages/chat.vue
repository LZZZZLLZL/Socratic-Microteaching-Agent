<template>
  <div class="page">
    <!-- 顶部导航 -->
    <div class="chat-header">
      <NuxtLink to="/" class="back-link">
        <el-icon><ArrowLeft /></el-icon>
        返回分析
      </NuxtLink>
      <div class="session-info">
        <span class="session-label">苏格拉底式对话</span>
      </div>
    </div>

    <!-- 消息区域 -->
    <div class="chat-container">
      <div class="messages" ref="messagesRef">
        <!-- 空状态 -->
        <div v-if="messages.length === 0 && !loading" class="empty-state">
          <div class="empty-icon">🤖</div>
          <p class="empty-title">AI 导师已准备就绪</p>
          <p class="empty-desc">请在左侧上传视频开始分析，或输入您的问题开始对话</p>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading && messages.length === 0" class="loading-state">
          <div class="loading-dots">
            <span></span><span></span><span></span>
          </div>
          <p>AI 导师正在思考...</p>
        </div>

        <!-- 消息列表 -->
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['message-row', msg.role]"
        >
          <div class="message-avatar">
            {{ msg.role === 'user' ? '👤' : '🧑‍🏫' }}
          </div>
          <div class="message-bubble">
            <div class="message-content" v-html="formatMessage(msg.content)"></div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-section">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="输入您的问题或反思，AI 导师将引导您深入思考..."
            :disabled="loading"
            @keydown.enter.ctrl="sendMessage"
            @keydown.enter.shift="inputMessage += '\n'"
          />
          <div class="input-actions">
            <span class="input-hint">Enter 发送，Shift+Enter 换行</span>
            <div class="buttons">
              <el-button
                size="small"
                :disabled="loading"
                @click="clearChat"
              >
                清除
              </el-button>
              <el-button
                type="primary"
                :loading="loading"
                :disabled="!inputMessage.trim()"
                @click="sendMessage"
              >
                发送
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'

const route = useRoute()
const sessionId = ref('')
const inputMessage = ref('')
const loading = ref(false)
const messages = ref<{ role: string; content: string }[]>([])
const messagesRef = ref<HTMLElement>()

onMounted(async () => {
  sessionId.value = route.query.session as string

  if (sessionId.value) {
    await fetchAIInitial()
  }
})

const formatMessage = (text: string) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

const fetchAIInitial = async () => {
  if (!sessionId.value) return

  loading.value = true

  try {
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, message: '' }),
    })

    await streamResponse(response)
  } catch (error) {
    ElMessage.error('获取 AI 点评失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  messages.value.push({ role: 'user', content: userMessage })
  loading.value = true
  scrollToBottom()

  try {
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, message: userMessage }),
    })

    await streamResponse(response)
  } catch (error) {
    ElMessage.error('发送失败，请重试')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const streamResponse = async (response: Response) => {
  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  let fullContent = ''

  messages.value.push({ role: 'assistant', content: '' })
  const msgIndex = messages.value.length - 1

  while (reader) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))

          if (data.error) {
            ElMessage.error(data.error)
            break
          }

          if (data.text) {
            fullContent += data.text
            if (messages.value[msgIndex]) {
              messages.value[msgIndex].content = fullContent
            }
            scrollToBottom()
          }
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
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
    console.error(error)
  }
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  padding: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
}

.back-link {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 14px;
  text-decoration: none;
  transition: color 0.2s;
}

.back-link:hover {
  color: var(--accent-blue);
}

.session-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.8;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-muted);
  max-width: 300px;
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.loading-dots {
  display: flex;
  gap: 6px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: var(--accent-blue);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.loading-state p {
  color: var(--text-secondary);
  font-size: 14px;
}

.message-row {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-row.assistant {
  align-self: flex-start;
}

.message-avatar {
  font-size: 32px;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-input);
  border-radius: 50%;
}

.message-row.user .message-avatar {
  background: var(--accent-blue);
}

.message-bubble {
  flex: 1;
  min-width: 0;
}

.message-content {
  padding: 16px 20px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-row.user .message-content {
  background: var(--accent-blue);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-row.assistant .message-content {
  background: var(--bg-input);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

.input-section {
  padding: 20px 24px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-subtle);
}

.input-wrapper {
  max-width: 900px;
  margin: 0 auto;
}

.input-wrapper :deep(.el-textarea__inner) {
  background: var(--bg-input) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 15px;
  resize: none;
}

.input-wrapper :deep(.el-textarea__inner:focus) {
  border-color: var(--accent-blue) !important;
}

.input-wrapper :deep(.el-textarea__inner::placeholder) {
  color: var(--text-muted) !important;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.input-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.buttons {
  display: flex;
  gap: 8px;
}

.buttons .el-button--primary {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
}

.buttons .el-button--primary:hover {
  background: var(--accent-blue-light);
  border-color: var(--accent-blue-light);
}

.buttons .el-button:not(.el-button--primary) {
  background: var(--bg-input);
  border-color: var(--border-subtle);
  color: var(--text-secondary);
}

.buttons .el-button:not(.el-button--primary):hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}
</style>
