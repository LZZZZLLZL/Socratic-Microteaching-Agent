# 🍎 Socratic-Microteaching-Agent (学思践悟)

> **基于多智能体（Multi-Agent）与 RAG 技术的智慧教育实训复盘系统**

---

## 🧠 技术架构 (Technical Stack)

| 维度 | 技术选型 | 备注 |
| :--- | :--- | :--- |
| **前端 (Frontend)** | **Nuxt 4 (Vue 3)** | SSR/CSR 混合渲染，Pinia 状态管理 |
| **后端 (Backend)** | **FastAPI (Python)** | 高性能异步框架，适配 Nuxt useFetch |
| **核心 AI** | **DeepSeek-V3 / R1** | 大语言模型推理 (API 接入) |
| **本地多模态** | **OpenAI Whisper + Mediapipe** | 语音转写与姿态分析 (针对 3070 Ti 优化) |
| **向量数据库** | **FAISS** | 本地 RAG 知识库检索 |

## 📂 目录结构 (Directory Structure)

```text
.
├── frontend/                # Nuxt 4 前端项目
│   ├── pages/               # 页面逻辑
│   ├── stores/              # Pinia 状态管理
│   └── components/          # Nuxt UI 组件
├── backend/                 # FastAPI 后端项目
│   ├── core/                # RAG 与 Multi-Agent 逻辑
│   ├── api/                 # RESTful 接口定义
│   └── main.py              # 服务入口
├── data/                    # 原始 PDF 教材/大纲 (本地)
├── .env                     # API 密钥管理 (不上传)
└── requirements.txt         # 后端依赖

```

## 🚀 核心亮点 (Technical Highlights)

* **全栈异步流式架构**：采用 Nuxt 4 + FastAPI 组合，支持 **SSE (Server-Sent Events)** 实现 AI 评价逐字响应。
* **分时显存优化技术**：针对 **RTX 3070 Ti (8GB VRAM)** 显存瓶颈，实现 Whisper 与推理任务的显存动态复用。
* **苏格拉底式启发反馈**：Multi-Agent 协同，由“模拟学生”提问，引导师范生自主发现教学盲点。
* **本地 RAG 知识引擎**：依托 **32GB RAM** 建立高性能 FAISS 向量索引，确保反馈具备专业理论支撑。

## ⚡ 快速开始 (Quick Start)

### 1. 后端部署 (Backend)

```bash
cd backend
pip install -r requirements.txt
python main.py

```

### 2. 前端部署 (Frontend)

```bash
cd frontend
npm install
npm run dev

```

## 🤝 团队分工 (Teamwork)

| 角色 | 成员 | 核心职责 |
| --- | --- | --- |
| **后端负责人** | **@LZZZZLLZL** | **架构总师**。负责 FastAPI 框架、Whisper 解析、RAG 构建。 |
| **前端负责人** | **@ph、@yjb** | **交互总师**。负责 Nuxt 4 架构、Pinia 状态、数据可视化。 |
