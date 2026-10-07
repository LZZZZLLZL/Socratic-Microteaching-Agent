// ==========================================================================
// 学思践悟 — Type Definitions
// ==========================================================================

/** 时间轴分段 */
export interface TimelineSegment {
  start: number
  end: number
  text: string
  back: boolean
  gesture: number
}

/** 教态预警 */
export interface VisionAlert {
  level: 'error' | 'warning' | 'info' | 'success'
  msg: string
}

/** 教态分析数据 */
export interface VisionAnalysis {
  back_ratio: number
  gesture_intensity: number
  gesture_level: string
  hand_balance: number
  both_hands_ratio: number
  is_stiff: boolean
  /** 每分钟位移路径长度（单位：画面宽度/分钟），已按时长归一化 */
  movement_range: number
  /** 全程位移路径总长（画面宽度），仅用于追溯 */
  movement_total?: number
  /** movement_range 的单位说明 */
  movement_unit?: string
  total_duration: number
  timeline: VisionTimelineEvent[]
  alerts: VisionAlert[]
}

/** 视觉时间轴采样点 */
export interface VisionTimelineEvent {
  t: number
  back: boolean
  gesture: boolean
}

/** 评分维度 */
export interface ScoreItem {
  name: string
  score: number
  comment: string
}

/** 分析结果 */
export interface AnalysisResult {
  session_id: string
  transcription: string
  /** Whisper 原始输出（未还原标点），仅完整模式返回 */
  raw_transcription?: string
  vision_analysis: VisionAnalysis
  socratic_feedback: string
  referenced_standards: string[]
  timeline: TimelineSegment[]
  video_url: string
  scoring_card: ScoreItem[]
  /** 本次转写使用的 Whisper 模型精度 */
  whisper_model?: string
  /** 是否由本地规则引擎还原了标点 */
  punctuation_restored?: boolean
}

/** 聊天消息 */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** SSE 进度事件 */
export interface SSEProgress {
  p: number
  s: string
}

/** SSE 完成事件 */
export interface SSEDone {
  done: true
  result: AnalysisResult
}

/** SSE 错误事件 */
export interface SSEError {
  error: string
}

/** SSE 流式文本 */
export interface SSEText {
  text: string
  done?: boolean
}

export type SSEEvent = SSEProgress | SSEDone | SSEError | SSEText
