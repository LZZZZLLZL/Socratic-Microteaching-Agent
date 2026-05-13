import os
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# 1. 导入自定义模块
from core.whisper_engine import transcriber
from core.agent_logic import ai_assistant
from core.rag_engine import rag_engine
from core.vision_engine import vision_analyzer  # 导入你刚写好的视觉引擎

app = FastAPI(title="学思践悟 AI 多模态实训后端")

# --- 2. 启动初始化：万能路径加载课标至内存 ---
def init_standards():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(current_dir, "data", "it_standard.txt"),      # backend/data/
        os.path.join(os.path.dirname(current_dir), "data", "it_standard.txt") # 根目录/data/
    ]
    
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            rag_engine.load_local_standards(path)
            print(f"✅ RAG 课标库已成功加载: {path}")
            found = True
            break
    if not found:
        print(f"❌ 找不到课标文件，请确认 it_standard.txt 位置")

init_standards()

# --- 3. 跨域配置 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. 核心 API 接口 ---
@app.post("/api/v1/analyze")
async def analyze_video(file: UploadFile = File(...)):
    # A. 准备临时文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(current_dir, "data", "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    
    # 保存上传的文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # B. 语音分析 (RTX 3070 Ti 加速)
        print(f"🎙️ 正在转写语音: {file.filename}...")
        text_result = transcriber.transcribe(file_path)
        
        # C. 视觉动作分析 (RTX 3070 Ti 加速)
        print(f"👁️ 正在识别动作特征...")
        vision_data = vision_analyzer.analyze_video(file_path)
        
        # D. RAG 检索：基于语音内容查找最相关的课标
        print(f"🔍 正在检索课标依据...")
        related_standards = rag_engine.query_related_standard(text_result, top_k=2)
        
        # E. 构造多模态上下文，请求 DeepSeek 点评
        # 我们把视觉数据转化为文字描述，让 AI 能“看”懂
        multimodal_context = f"""
        【教学表现原始数据】
        1. 语音内容："{text_result}"
        2. 视觉动作：
           - 背对学生时间占比：{vision_data['back_ratio'] * 100}%
           - 手势互动强度：{vision_data['gesture_intensity']} 次
           - 课堂位移状态：{'站位灵活' if not vision_data['is_stiff'] else '站位较为固定'}
        """
        
        print("🤖 请求 DeepSeek 进行多模态深度点评...")
        ai_response = ai_assistant.analyze_with_rag(multimodal_context, related_standards)
        
        # 拼接流式输出
        full_feedback = ""
        for chunk in ai_response:
            if chunk.choices[0].delta.content:
                full_feedback += chunk.choices[0].delta.content
        
        # F. 返回综合分析结果
        return {
            "status": "success",
            "transcription": text_result,
            "vision_analysis": vision_data,    # 包含 back_ratio, gesture_intensity 等
            "socratic_feedback": full_feedback,
            "referenced_standards": related_standards
        }
        
    except Exception as e:
        print(f"❌ 流程处理失败: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        # 清理上传的临时视频文件
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    # 启动服务
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)