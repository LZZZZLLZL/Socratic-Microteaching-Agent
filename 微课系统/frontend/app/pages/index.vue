<template>
  <div class="page">
    <div class="container">
      <h1 class="title">微课视频分析</h1>
      <p class="subtitle">上传您的微课视频，AI 将提供苏格拉底式点评</p>

      <!-- 上传区域 -->
      <div v-if="!analyzing && !result" class="upload-section">
        <el-upload
          ref="uploadRef"
          class="upload"
          drag
          :auto-upload="false"
          :limit="1"
          accept="video/*"
          :on-change="handleFileChange"
          :file-list="fileList"
        >
          <div class="upload-content">
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              <span class="upload-title">拖拽视频文件到此处</span>
              <span class="upload-hint">或点击选择文件，支持 MP4、MOV 等格式</span>
            </div>
          </div>
        </el-upload>
        <el-button
          v-if="selectedFile"
          type="primary"
          size="large"
          class="analyze-btn"
          :loading="analyzing"
          @click="startAnalysis"
        >
          开始分析
        </el-button>
        <el-button
          size="large"
          class="demo-btn"
          @click="startDemo"
        >
          演示模式（不上传视频）
        </el-button>
      </div>

      <!-- 分析进度 -->
      <div v-if="analyzing" class="progress-section">
        <el-progress
          :percentage="progress"
          :stroke-width="12"
          :format="formatProgress"
        />
        <p class="progress-status">{{ statusText }}</p>
      </div>

      <!-- 分析结果 -->
      <div v-if="result" class="result-section">
        <!-- 教学内容 -->
        <el-card v-if="result.transcription" class="result-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">📝 教学内容（语音转写）</span>
            </div>
          </template>
          <div class="transcription">{{ result.transcription }}</div>
        </el-card>

        <!-- 引用课标 -->
        <el-card v-if="result.referenced_standards?.length" class="result-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">📚 引用课标</span>
            </div>
          </template>
          <ul class="standards-list">
            <li v-for="(standard, idx) in result.referenced_standards" :key="idx">
              {{ standard }}
            </li>
          </ul>
        </el-card>

        <!-- AI 点评 -->
        <el-card class="result-card feedback-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">🤖 AI 点评</span>
              <span class="ai-badge">苏格拉底式引导</span>
            </div>
          </template>
          <div class="feedback-content" v-html="formatFeedback(result.socratic_feedback)"></div>
          <div class="action-buttons">
            <el-button type="primary" @click="goToChat">
              开始对话
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
            <el-button @click="reset">分析新视频</el-button>
          </div>
        </el-card>

        <!-- 教态数据 -->
        <el-card v-if="result.vision_analysis" class="result-card vision-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">🎭 教态数据</span>
              <span class="hint-text">（仅后台参考，对话中不会主动提及）</span>
            </div>
          </template>
          <div class="vision-grid">
            <div class="vision-item">
              <span class="vision-label">背对学生时间</span>
              <span class="vision-value">{{ (result.vision_analysis.back_ratio * 100).toFixed(1) }}%</span>
            </div>
            <div class="vision-item">
              <span class="vision-label">手势频次</span>
              <span class="vision-value">{{ result.vision_analysis.gesture_intensity }} 次</span>
            </div>
            <div class="vision-item">
              <span class="vision-label">手势幅度</span>
              <span class="vision-value">{{ result.vision_analysis.gesture_level }}</span>
            </div>
            <div class="vision-item">
              <span class="vision-label">左右均衡度</span>
              <span class="vision-value">{{ result.vision_analysis.hand_balance }}%</span>
            </div>
            <div class="vision-item">
              <span class="vision-label">位移幅度</span>
              <span class="vision-value">{{ result.vision_analysis.movement_range }}</span>
            </div>
            <div class="vision-item">
              <span class="vision-label">站位状态</span>
              <span class="vision-value">{{ result.vision_analysis.is_stiff ? '较为固定' : '灵活' }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { UploadFilled, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()

const uploadRef = ref()
const selectedFile = ref<File | null>(null)
const fileList = ref<any[]>([])
const analyzing = ref(false)
const progress = ref(0)
const statusText = ref('')
const result = ref<any>(null)
const sessionId = ref('')

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
  fileList.value = [file]
}

const formatProgress = (percentage: number) => `${percentage}%`

const startAnalysis = async () => {
  if (!selectedFile.value) return

  analyzing.value = true
  progress.value = 0
  statusText.value = '准备上传...'
  result.value = null

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await fetch('/api/v1/analyze', {
      method: 'POST',
      body: formData,
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

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

            if (data.p !== undefined) {
              progress.value = data.p
              statusText.value = data.s
            }

            if (data.done && data.result) {
              result.value = data.result
              sessionId.value = data.result.session_id
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
  } catch (error) {
    ElMessage.error('分析失败，请重试')
    console.error(error)
  } finally {
    analyzing.value = false
  }
}

const formatFeedback = (text: string) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

const startDemo = () => {
  analyzing.value = true
  progress.value = 0
  statusText.value = '模拟演示模式...'

  // 模拟分析进度
  const steps = [
    { p: 15, s: '检测视频音频轨道...' },
    { p: 30, s: '音频提取完成' },
    { p: 45, s: '语音转写中（Whisper GPU 加速）...' },
    { p: 60, s: '语音转写完成' },
    { p: 70, s: '视觉动作分析中（YOLOv8 GPU 加速）...' },
    { p: 80, s: '视觉分析完成' },
    { p: 85, s: '课标检索中...' },
    { p: 95, s: '课标检索完成' },
    { p: 100, s: '分析完成' },
  ]

  let i = 0
  const interval = setInterval(() => {
    if (i < steps.length) {
      progress.value = steps[i].p
      statusText.value = steps[i].s
      i++
    } else {
      clearInterval(interval)
      analyzing.value = false
      // 模拟结果
      result.value = {
        session_id: 'demo-session-001',
        transcription: '各位同学好，今天我们来学习信息技术的基本概念。首先，什么是信息？信息是客观世界各种事物的特征的反映，它可以通过数据、图像、声音等方式来表现。接下来，我们一起来看看信息技术的定义。信息技术是指在计算机和通信技术的支持下，用于获取、加工、存储、传输和展示信息的所有技术的总称。',
        referenced_standards: [
          '《中小学信息技术课程标准》指出：信息技术课程旨在培养学生的信息素养，包括信息的获取、加工、表达和交流的能力。',
          '教学应注重理论与实践相结合，引导学生在真实情境中理解和应用信息技术。'
        ],
        socratic_feedback: '我注意到您在导入环节用了"各位同学好"这样的开场白，整体教学思路比较清晰，先讲信息概念，再引出信息技术定义。\n\n我想请教您一个问题：您认为学生之前对"信息"这个概念有多少前置认知？在引入"信息"定义之前，是否可以先让学生举例说说他们生活中接触到的"信息"？\n\n这样可能会有助于学生从具体到抽象地建构概念。您觉得呢？',
        vision_analysis: {
          back_ratio: 0.12,
          gesture_intensity: 28,
          gesture_level: '活跃',
          hand_balance: 65,
          both_hands_ratio: 0.35,
          is_stiff: false,
          movement_range: 156.3,
          total_duration: 180
        }
      }
      sessionId.value = 'demo-session-001'
    }
  }, 400)
}

const goToChat = () => {
  router.push(`/chat?session=${sessionId.value}`)
}

const reset = () => {
  selectedFile.value = null
  fileList.value = []
  result.value = null
  progress.value = 0
  statusText.value = ''
}
</script>

<style scoped>
.page {
  padding: 40px 0;
}

.container {
  max-width: 900px;
  margin: 0 auto;
}

.title {
  font-size: 32px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.subtitle {
  text-align: center;
  color: var(--text-secondary);
  font-size: 16px;
  margin-bottom: 40px;
}

.upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.upload {
  width: 100%;
}

.upload-content {
  padding: 40px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon {
  font-size: 48px;
  color: var(--accent-blue);
}

.upload-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-title {
  font-size: 16px;
  color: var(--text-primary);
}

.upload-hint {
  font-size: 14px;
  color: var(--text-muted);
}

.analyze-btn {
  width: 200px;
}

.demo-btn {
  margin-top: 8px;
  background: var(--bg-input);
  border-color: var(--border-subtle);
  color: var(--text-secondary);
}

.demo-btn:hover {
  background: var(--bg-card-hover);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.progress-section {
  max-width: 600px;
  margin: 60px auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.progress-status {
  color: var(--text-secondary);
  font-size: 14px;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-top: 32px;
}

.result-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.ai-badge {
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
  border-radius: 4px;
}

.hint-text {
  font-size: 12px;
  color: var(--text-muted);
}

.transcription {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.standards-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.standards-list li {
  padding: 12px 16px;
  background: var(--bg-input);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  border-left: 3px solid var(--accent-blue);
}

.feedback-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
  margin-bottom: 24px;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.action-buttons .el-button--primary {
  background-color: var(--accent-blue);
  border-color: var(--accent-blue);
  color: white;
}

.action-buttons .el-button--primary:hover {
  background-color: var(--accent-blue-light);
  border-color: var(--accent-blue-light);
}

.action-buttons .el-button:not(.el-button--primary) {
  background-color: var(--bg-input);
  border-color: var(--border-subtle);
  color: var(--text-secondary);
}

.action-buttons .el-button:not(.el-button--primary):hover {
  background-color: var(--bg-card-hover);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.vision-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.vision-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--bg-input);
  border-radius: 8px;
}

.vision-label {
  font-size: 12px;
  color: var(--text-muted);
}

.vision-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-blue);
}

@media (max-width: 640px) {
  .vision-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
