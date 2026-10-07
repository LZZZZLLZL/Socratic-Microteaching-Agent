// ==========================================================================
// 学思践悟 — Whisper 模型目录
// 完整版首次进入时用于「模型监测 → 选择精度 → 下载」流程
// ==========================================================================

export interface WhisperModelOption {
  /** 后端使用的模型标识 */
  id: string
  /** 展示名称 */
  name: string
  /** 参数量描述 */
  params: string
  /** 磁盘占用 */
  size: string
  /** 相对速度（1x 为基准） */
  speed: string
  /** 中文准确度评级 */
  accuracy: number
  /** 适用场景 */
  scene: string
  /** 是否推荐 */
  recommended?: boolean
  /** 显存/内存占用粗略估算 */
  vram: string
}

export const WHISPER_MODELS: WhisperModelOption[] = [
  {
    id: 'tiny',
    name: 'Tiny',
    params: '39 M',
    size: '75 MB',
    speed: '约 32x',
    accuracy: 3,
    scene: '仅做流程演示，中文识别准确率较低，断句与错字较多',
    vram: '约 1 GB',
  },
  {
    id: 'base',
    name: 'Base',
    params: '74 M',
    size: '142 MB',
    speed: '约 16x',
    accuracy: 5,
    scene: '轻量级方案，适合课堂短片段快速试跑',
    vram: '约 1 GB',
  },
  {
    id: 'small',
    name: 'Small',
    params: '244 M',
    size: '466 MB',
    speed: '约 6x',
    accuracy: 7,
    scene: '中文教学场景的均衡之选，准确率与速度兼顾',
    recommended: true,
    vram: '约 2 GB',
  },
  {
    id: 'medium',
    name: 'Medium',
    params: '769 M',
    size: '1.5 GB',
    speed: '约 2x',
    accuracy: 9,
    scene: '高精度识别，适合正式评课与教研分析，耗时较长',
    vram: '约 5 GB',
  },
  {
    id: 'large-v3',
    name: 'Large V3',
    params: '1.55 B',
    size: '2.9 GB',
    speed: '约 1x',
    accuracy: 10,
    scene: '最高精度，中文识别与标点表现最好，需独立显卡',
    vram: '约 10 GB',
  },
]

export const DEFAULT_WHISPER_MODEL = 'base'

export function findWhisperModel(id: string): WhisperModelOption {
  return WHISPER_MODELS.find((m) => m.id === id) || WHISPER_MODELS[1]!
}

// ==========================================================================
// YOLOv8 姿态模型信息（模型监测面板展示）
// ==========================================================================
export const VISION_MODEL_INFO = {
  id: 'yolov8n-pose',
  name: 'YOLOv8n-Pose',
  params: '3.3 M',
  size: '12.6 MB',
  scene: '17 关键点人体姿态估计，用于背对检测、手势频次与站位分析',
  note: '项目已内置，无需下载',
}

/** 后端运行时信息（RAG / LLM 等附属组件） */
export const RUNTIME_COMPONENTS = [
  {
    id: 'text2vec',
    name: 'Text2Vec-Base-Chinese',
    role: '课标检索向量模型',
    size: '约 400 MB',
    note: '用于 RAG 检索课程标准条目',
  },
  {
    id: 'llm',
    name: 'DeepSeek-Chat',
    role: '苏格拉底对话与点评',
    size: '云端 API',
    note: '需在 backend/.env 中配置 DEEPSEEK_API_KEY',
  },
]
