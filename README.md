# 🍎 Socratic-Microteaching-Agent (学思践悟)
> **基于多智能体（Multi-Agent）与 RAG 技术的智慧教育实训复盘系统**

---

## 🌟 项目愿景 (Project Vision)
本系统专为师范生微格教学设计。通过 **DeepSeek-V3/R1** 作为逻辑大脑，结合本地 **RAG (检索增强生成)** 技术与多模态分析，实现对微课视频的深度解构，为师范生提供“苏格拉底式”的启发性教学反馈，助力数字化教研能力提升。

## 🧠 核心功能：多智能体协作 (Multi-Agent System)
系统后端由三个核心智能体协同工作，从不同维度“复盘”教学过程：
1. **Agent A: 模拟学生 (Mock Student)** - **人格设定**：基础薄弱但思维活跃的初中生。  
   - **任务**：针对教学片段提出“扎心”提问，测试师范生的课堂应变与知识讲解清晰度。
2. **Agent B: 教学设计专家 (Pedagogy Expert)** - **理论支撑**：基于建构主义与 ADDIE 模型。  
   - **任务**：评审教学环节逻辑，诊断是否存在“满堂灌”现象，并给出改进建议。
3. **Agent C: 语态数据分析官 (Data Analyst)** - **任务**：量化分析。统计语速、停顿、鼓励性话语占比，并结合视觉算法分析教态。

## 🛠 技术栈 (Technical Stack)
- **大语言模型**: DeepSeek-V3 / R1 (via API)
- **多模态处理**:
    - **音频转写**: OpenAI Whisper (本地部署)
    - **视觉分析**: Mediapipe / YOLOv8-pose (教师姿态识别)
- **向量数据库**: FAISS (基于 32GB RAM 高效检索)
- **前端框架**: Streamlit
- **后端框架**: LangChain / Python 3.10+

## 📂 目录结构 (Directory Structure)
```text
.
├── main.py              # Streamlit 前端主程序
├── core/                # 后端逻辑核心
│   ├── engine.py        # RAG 检索引擎
│   ├── audio_proc.py    # Whisper 语音处理
│   └── prompts.py       # Agent 提示词库
├── data/                # 原始 PDF 教材/教学大纲 (本地)
├── vector_db/           # 生成的向量数据库索引 (本地)
├── requirements.txt     # 项目依赖
└── .env                 # API 密钥 (不上传至仓库)
