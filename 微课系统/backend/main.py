import os
import json
import uuid
import subprocess
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.whisper_engine import transcriber
from core.agent_logic import ai_assistant
from core.rag_engine import rag_engine
from core.vision_engine import vision_analyzer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="学思践悟 AI 多模态实训后端")

# --- 静态文件服务（挂载在 /static 下，不会劫持 /api/*）---
frontend_dir = os.path.join(os.path.dirname(BASE_DIR), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend")

# --- 初始化 ---
def init_standards():
    standard_files = [
        "it_standard.txt",
        "微课大赛_评价标准.txt",
    ]
    possible_dirs = [
        os.path.join(BASE_DIR, "data"),
        os.path.join(os.path.dirname(BASE_DIR), "data"),
    ]
    loaded_any = False
    for fname in standard_files:
        for d in possible_dirs:
            path = os.path.join(d, fname)
            if os.path.exists(path):
                rag_engine.load_local_standards(path)
                print(f"RAG ok: {path}")
                loaded_any = True
                break  # 找到该文件就停止搜索目录
    if not loaded_any:
        print("cannot find any standard files")

init_standards()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = os.path.join(BASE_DIR, "data", "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)


def has_audio_stream(video_path: str) -> bool:
    """用 ffprobe 检测视频是否包含音频轨道"""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    return bool(r.stdout.strip())


def extract_audio(video_path: str, audio_path: str):
    """用 ffmpeg 提取音频，Whisper 直接处理音频比视频快得多"""
    subprocess.run(
        ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
         "-ar", "16000", "-ac", "1", "-y", audio_path],
        capture_output=True, check=True
    )


# --- 分析接口（SSE 流式返回进度）---
@app.post("/api/v1/analyze")
async def analyze_video(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    video_path = os.path.join(TEMP_DIR, f"{file_id}{ext}")
    audio_path = os.path.join(TEMP_DIR, f"{file_id}.wav")

    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    async def generate():
        try:
            # 1. 检测并提取音频 (0-15%)
            yield f"data: {json.dumps({'p': 5, 's': '检测视频音频轨道...'})}\n\n"
            if has_audio_stream(video_path):
                extract_audio(video_path, audio_path)
                yield f"data: {json.dumps({'p': 15, 's': '音频提取完成'})}\n\n"

                # 2. 语音转写 (15-45%)
                yield f"data: {json.dumps({'p': 18, 's': '语音转写中（Whisper GPU 加速）...'})}\n\n"
                text_result = transcriber.transcribe(audio_path)
                yield f"data: {json.dumps({'p': 45, 's': '语音转写完成'})}\n\n"
            else:
                yield f"data: {json.dumps({'p': 15, 's': '视频无音频轨道，跳过语音转写'})}\n\n"
                text_result = ""

            # 3. 视觉分析 (45-75%)
            yield f"data: {json.dumps({'p': 48, 's': '视觉动作分析中（YOLOv8 GPU 加速）...'})}\n\n"
            vision_data = vision_analyzer.analyze_video(video_path)
            yield f"data: {json.dumps({'p': 70, 's': '视觉分析完成'})}\n\n"

            # 4. RAG 检索 (75-85%) — 无音频时跳过课标匹配
            yield f"data: {json.dumps({'p': 73, 's': '课标检索中...'})}\n\n"
            if text_result:
                related_standards = rag_engine.query_related_standard(text_result, top_k=2)
            else:
                related_standards = []
            yield f"data: {json.dumps({'p': 85, 's': '课标检索完成'})}\n\n"

            # 5. AI 点评 (85-100%)
            # 教学内容——首轮分析的核心依据
            teaching_content = text_result if text_result else "（未检测到语音内容）"
            # 教态数据——仅做后台记录，AI 首轮不参考
            gesture_level = vision_data.get('gesture_level', '—')
            hand_balance = vision_data.get('hand_balance', 50)
            bal_desc = '均衡' if hand_balance >= 40 else ('偏侧' if hand_balance >= 20 else '单侧')
            both_desc = '较多' if vision_data.get('both_hands_ratio', 0) > 0.3 else '较少'
            gesture_data = f"""【教态数据（仅后台参考，不要在分析中主动提及）】
- 背对学生时间占比：{vision_data['back_ratio'] * 100}%
- 手势频次：{vision_data['gesture_intensity']} 次
- 手势幅度评级：{gesture_level}
- 左右手均衡度：{bal_desc}（左手使用占比 {hand_balance}%）
- 双手并用：{both_desc}
- 位移幅度：{vision_data['movement_range']}
- 课堂位移状态：{'站位灵活' if not vision_data['is_stiff'] else '站位较为固定'}
- 视频总时长：{vision_data['total_duration']} 秒
"""
            session_id = str(uuid.uuid4())
            ai_assistant.init_chat_session(session_id, teaching_content, gesture_data, related_standards)

            yield f"data: {json.dumps({'p': 88, 's': 'AI 深度点评中...'})}\n\n"
            full_feedback = ""
            for chunk in ai_assistant.chat_stream(session_id):
                full_feedback += chunk
            yield f"data: {json.dumps({'p': 100, 's': '分析完成'})}\n\n"

            # 发送最终结果
            result = {
                "session_id": session_id,
                "transcription": text_result,
                "vision_analysis": vision_data,
                "socratic_feedback": full_feedback,
                "referenced_standards": related_standards
            }
            yield f"data: {json.dumps({'done': True, 'result': result})}\n\n"

        except Exception as e:
            print(f"error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            for p in [video_path, audio_path]:
                if os.path.exists(p):
                    os.remove(p)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# --- 多轮对话 SSE 接口 ---
@app.post("/api/v1/chat")
async def chat_stream(data: dict):
    session_id = data.get("session_id")
    user_message = data.get("message", "")

    if not session_id:
        return {"status": "error", "message": "no session_id"}

    def generate():
        try:
            for text_chunk in ai_assistant.chat_stream(session_id, user_message):
                yield f"data: {json.dumps({'text': text_chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# --- 清除对话历史 ---
@app.post("/api/v1/chat/clear")
async def clear_chat(data: dict):
    session_id = data.get("session_id")
    if not session_id:
        return {"status": "error", "message": "no session_id"}
    ai_assistant.clear_session(session_id)
    return {"status": "ok", "message": f"session {session_id} cleared"}


# ── 前端页面路由（放在最后，确保不覆盖 API 路由）──
if os.path.exists(frontend_dir):
    @app.get("/")
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str = ""):
        file_path = os.path.join(frontend_dir, full_path or "index.html")
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        fallback = os.path.join(frontend_dir, "index.html")
        if os.path.exists(fallback):
            return FileResponse(fallback)
        return {"status": "error", "message": "not found"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
