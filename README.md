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

## 🚀 核心亮点 (Technical Highlights)

* **全栈异步流式架构**：采用 Nuxt 4 (Frontend) + FastAPI (Backend) 组合，原生支持 **SSE (Server-Sent Events)**，实现 AI 评价反馈的流式逐字显示，极大地提升了交互体验。
* **分时显存优化技术**：针对 **RTX 3070 Ti (8GB VRAM)** 显存瓶颈，后端通过显存动态管理策略，在 Whisper 转写、Mediapipe 分析与 RAG 检索间实现无缝切换，避免 OOM 报错。
* **苏格拉底式启发反馈**：不同于传统的评分系统，本系统通过 **Multi-Agent 协同**，由“学生智能体”进行启发式提问，引导师范生自主发现教学盲点，而非被动接受结论。
* **本地 RAG 知识引擎**：依托 **32GB RAM** 建立高性能 FAISS 向量索引，离线存储教育学经典理论与多版本教材，确保所有反馈均具备严谨的理论支撑与合规性。

## ⚡ 快速开始 (Quick Start)

> **注意**：项目采用前后端分离目录结构，请确保已安装 Python 3.10+ 与 Node.js 18+。

### 1. 后端部署 (Backend)
```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
echo "DEEPSEEK_API_KEY=你的SK_KEY" > .env

# 启动 FastAPI 服务
python main.py

# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动 Nuxt 4 开发服务器
npm run dev

## 🤝 团队分工 (Teamwork)

| 角色 | 成员 | 核心职责 |
| :--- | :--- | :--- |
| **后端负责人** | **@LZZZZLLZL** | **架构总师**。负责 FastAPI 异步框架、Whisper 语音解析、FAISS 向量库构建、Multi-Agent 逻辑调度及 API 接口定义。 |
| **前端负责人** | **ph、yjb** | **交互总师**。负责 Nuxt 4 项目架构、Pinia 状态流转、Tailwind CSS 样式封装及教学诊断数据可视化（Echarts）。 |
