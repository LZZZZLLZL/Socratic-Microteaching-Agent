# 🍎 Socratic-Microteaching-Agent (学思践悟)
> **基于多智能体（Multi-Agent）与 RAG 技术的智慧教育实训复盘系统**
> **A Professional Micro-teaching Feedback System for Pre-service Teachers**

---

## 🌟 项目愿景 (Project Vision)
本系统专为师范生微格教学实训设计。通过 **DeepSeek-V3/R1** 作为逻辑大脑，结合本地 **RAG (检索增强生成)** 技术与多模态分析，实现对微课视频的深度解构，为师范生提供“苏格拉底式”的启发性教学反馈。

## 🧠 核心架构 (Core Architecture)

### 1. 多智能体协作 (Multi-Agent System)
- **Agent A: 模拟学生 (Mock Student)** - 模拟基础薄弱但思维活跃的学情，提出挑战性问题。
- **Agent B: 教学设计专家 (Pedagogy Expert)** - 基于建构主义与 ADDIE 模型，评审教学逻辑并提供诊断建议。
- **Agent C: 语态数据分析官 (Data Analyst)** - 量化分析语速、停顿及关键性指标，并结合视觉算法分析教态。

### 2. 技术栈 (Technical Stack)
| 维度 | 技术选型 | 备注 |
| :--- | :--- | :--- |
| **前端 (Frontend)** | **Nuxt 4 (Vue 3)** | SSR/CSR 混合渲染，Pinia 状态管理 |
| **UI 框架** | **Tailwind CSS + Nuxt UI** | 响应式设计，极速交互体验 |
| **后端 (Backend)** | **FastAPI (Python)** | 高性能异步框架，适配 Nuxt `useFetch` |
| **核心 AI** | **DeepSeek-V3 / R1** | 大语言模型推理 (API) |
| **本地多模态** | **OpenAI Whisper + Mediapipe** | 语音转写与姿态分析 (GPU 加速) |
| **向量数据库** | **FAISS** | 本地 RAG 知识库检索 |

## 📂 目录结构 (Directory Structure)
```text
.
├── frontend/                # Nuxt 4 前端项目
│   ├── pages/               # SSR/CSR 页面逻辑
│   ├── stores/              # Pinia 状态管理
│   └── components/          # Nuxt UI 组件封装
├── backend/                 # FastAPI 后端项目
│   ├── core/                # RAG 与 Multi-Agent 逻辑
│   ├── api/                 # RESTful 接口定义
│   └── main.py              # 服务入口
├── data/                    # 原始 PDF 教材/大纲 (本地)
├── .env                     # API 密钥管理
└── requirements.txt         # 后端依赖
