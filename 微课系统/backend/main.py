import os
import json
import time
import uuid
import asyncio
import subprocess
import shutil
import uvicorn
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.whisper_engine import transcriber, SUPPORTED_MODELS, DEFAULT_MODEL
from core.agent_logic import ai_assistant
from core.rag_engine import rag_engine
from core.vision_engine import vision_analyzer
from core.runtime_config import (
    runtime_config,
    normalize_base_url,
    validate_base_url,
)

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
VIDEO_DIR = os.path.join(BASE_DIR, "data", "videos")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)


def cleanup_temp_files(max_age_seconds: int = 3600):
    """清理临时目录中超过指定时间的残留文件"""
    for directory in [TEMP_DIR, VIDEO_DIR]:
        if not os.path.exists(directory):
            continue
        now = time.time()
        cleaned = 0
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            try:
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                    os.remove(fpath)
                    cleaned += 1
            except OSError:
                pass
        if cleaned:
            print(f"[Cleanup] 已清理 {directory} 中 {cleaned} 个过期文件")


# 启动时清理上次遗留的临时文件
cleanup_temp_files(max_age_seconds=60)


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
async def analyze_video(
    file: UploadFile = File(...),
    whisper_model: Optional[str] = Form(None),
):
    file_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    video_path = os.path.join(TEMP_DIR, f"{file_id}{ext}")
    audio_path = os.path.join(TEMP_DIR, f"{file_id}.wav")
    saved_video_path = os.path.join(VIDEO_DIR, f"{file_id}{ext}")

    # 前端模型监测面板选定的精度，缺省时用后端默认值
    chosen_model = whisper_model if whisper_model in SUPPORTED_MODELS else DEFAULT_MODEL

    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    async def generate():
        # 转写元信息，供最终结果回传前端（无音频轨时保持默认值）
        transcribe_result: dict = {}

        try:
            # 1. 检测并提取音频 (0-15%)
            yield f"data: {json.dumps({'p': 5, 's': '检测视频音频轨道...'})}\n\n"
            if has_audio_stream(video_path):
                extract_audio(video_path, audio_path)
                yield f"data: {json.dumps({'p': 15, 's': '音频提取完成'})}\n\n"

                # 2. 语音转写 (15-45%) — 返回 {full_text, segments}
                yield f"data: {json.dumps({'p': 18, 's': f'语音转写中（Whisper {chosen_model}）...'})}\n\n"
                # 转写与标点还原是阻塞操作，放到线程池避免卡住事件循环
                transcribe_result = await asyncio.to_thread(
                    transcriber.transcribe, audio_path, chosen_model, True
                )
                text_result = transcribe_result["full_text"]
                whisper_segments = transcribe_result["segments"]
                yield f"data: {json.dumps({'p': 45, 's': '语音转写完成（已还原标点）'})}\n\n"
            else:
                yield f"data: {json.dumps({'p': 15, 's': '视频无音频轨道，跳过语音转写'})}\n\n"
                text_result = ""
                whisper_segments = []

            # 3. 视觉分析 (45-75%)
            yield f"data: {json.dumps({'p': 48, 's': '视觉动作分析中（YOLOv8 GPU 加速）...'})}\n\n"
            vision_data = vision_analyzer.analyze_video(video_path)
            yield f"data: {json.dumps({'p': 70, 's': '视觉分析完成'})}\n\n"

            # 4. RAG 检索 (75-85%)
            yield f"data: {json.dumps({'p': 73, 's': '课标检索中...'})}\n\n"
            if text_result:
                related_standards = rag_engine.query_related_standard(text_result, top_k=2)
            else:
                related_standards = []
            yield f"data: {json.dumps({'p': 85, 's': '课标检索完成'})}\n\n"

            # 5. AI 点评 (85-100%)
            teaching_content = text_result if text_result else "（未检测到语音内容）"
            gesture_level = vision_data.get('gesture_level', '—')
            hand_balance = vision_data.get('hand_balance', 50)
            bal_desc = '均衡' if hand_balance >= 40 else ('偏侧' if hand_balance >= 20 else '单侧')
            both_desc = '较多' if vision_data.get('both_hands_ratio', 0) > 0.3 else '较少'
            gesture_data = f"""【教态数据（仅后台参考，不要在分析中主动提及）】
- 背对学生时间占比：{round(vision_data['back_ratio'] * 100, 1)}%
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

            # 5b. 多维评分卡 (88-95%)
            yield f"data: {json.dumps({'p': 92, 's': '生成多维度评分卡...'})}\n\n"
            scoring_card = ai_assistant.get_scoring_card(teaching_content)
            yield f"data: {json.dumps({'p': 100, 's': '分析完成'})}\n\n"

            # 6. 构建统一时间轴：合并 Whisper 分段 + 视觉事件
            timeline = _build_timeline(whisper_segments, vision_data.get("timeline", []))

            # 7. 持久化视频（供前端播放器回放）
            shutil.copy2(video_path, saved_video_path)
            ai_assistant.sessions_meta.setdefault(session_id, {})["video_path"] = saved_video_path

            # 发送最终结果
            result = {
                "session_id": session_id,
                "transcription": text_result,
                "raw_transcription": transcribe_result.get("raw_text", ""),
                "vision_analysis": vision_data,
                "socratic_feedback": full_feedback,
                "referenced_standards": related_standards,
                "timeline": timeline,
                "video_url": f"/api/v1/video/{file_id}{ext}",
                "scoring_card": scoring_card.get("scores", []),
                "whisper_model": chosen_model,
                "punctuation_restored": transcribe_result.get("punctuation_restored", False),
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


# ==========================================================================
# 模型管理接口（完整模式首次进入时的模型监测流程）
# ==========================================================================
@app.get("/api/v1/models")
async def list_models():
    """
    探测本地模型环境，返回设备信息与已下载模型列表。
    前端据此渲染「模型监测面板」并标注每个模型的磁盘大小。
    """
    try:
        info = transcriber.runtime_info()
    except Exception as e:  # noqa: BLE001
        print(f"[Models] 运行时探测失败: {e}")
        info = {
            "device": "unknown",
            "torch": None,
            "cuda": False,
            "gpu": None,
            "installed": [],
            "cache_dir": None,
            "default_model": DEFAULT_MODEL,
            "supported": SUPPORTED_MODELS,
        }

    return {
        "status": "ok",
        "vision_model": {
            "id": "yolov8n-pose",
            "name": "YOLOv8n-Pose",
            "size": "12.6 MB",
            "installed": os.path.exists(os.path.join(BASE_DIR, "yolov8n-pose.pt")),
        },
        **info,
    }


@app.post("/api/v1/models/download")
async def download_model(data: dict):
    """
    下载指定 Whisper 模型权重，SSE 流式返回进度。

    Body: {"model": "small"}
    """
    model_id = (data or {}).get("model", DEFAULT_MODEL)

    if model_id not in SUPPORTED_MODELS:
        async def _invalid():
            yield f"data: {json.dumps({'error': f'不支持的模型: {model_id}'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(_invalid(), media_type="text/event-stream")

    async def generate():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_progress(percent: int, message: str):
            # 从工作线程安全地投递进度
            loop.call_soon_threadsafe(queue.put_nowait, {"p": percent, "msg": message})

        async def run_download():
            try:
                await asyncio.to_thread(transcriber.download_model, model_id, on_progress)
                await queue.put({"done": True, "msg": f"{model_id} 已就绪"})
            except Exception as e:  # noqa: BLE001
                await queue.put({"error": str(e)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_download())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

        await task

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==========================================================================
# API 配置接口（完整模式下由前端填写 API Key / 服务地址 / 模型名）
# ==========================================================================
@app.get("/api/v1/config")
async def get_api_config():
    """
    查询当前 API 配置状态。

    出于安全考虑**不回传明文密钥**，只返回掩码与来源标记。
    """
    return {"status": "ok", **runtime_config.status()}


@app.post("/api/v1/config")
async def update_api_config(data: dict):
    """
    保存 API 配置（立即生效，无需重启后端）。

    Body:
        api_key:  新密钥；传空字符串表示清除；不传表示保持不变
        base_url: 服务地址（可选）
        model:    模型名（可选）
    """
    data = data or {}

    # --- 校验服务地址 ---
    base_url = data.get("base_url")
    if base_url is not None:
        ok, err = validate_base_url(base_url)
        if not ok:
            return {"status": "error", "message": err}
        base_url = normalize_base_url(base_url)

    # --- 校验密钥格式（仅在提供了非空新值时）---
    api_key = data.get("api_key")
    if api_key is not None:
        api_key = api_key.strip()
        if api_key and not runtime_config.is_valid_key(api_key):
            return {
                "status": "error",
                "message": "API Key 格式不正确（长度至少 8 位，且不能是占位符）",
            }

    status = runtime_config.update(
        api_key=api_key,
        base_url=base_url,
        model=data.get("model"),
    )
    print(f"[Config] API 配置已更新 (base_url={status['base_url']}, "
          f"model={status['model']}, configured={status['configured']})")
    return {"status": "ok", "message": "配置已保存并生效", **status}


@app.post("/api/v1/config/test")
async def test_api_config(data: dict):
    """
    测试 API 连通性。

    直接发起一次极小的对话请求，验证「地址 + 密钥 + 模型名」三者
    是否真的可用。未提供参数时，使用当前已保存的配置。

    Body（均可选）:
        api_key / base_url / model —— 用于「保存前先测试」
    """
    data = data or {}

    api_key = (data.get("api_key") or "").strip() or runtime_config.api_key
    base_url = normalize_base_url(data.get("base_url") or runtime_config.base_url)
    model = (data.get("model") or "").strip() or runtime_config.model

    if not runtime_config.is_valid_key(api_key):
        return {"status": "error", "ok": False, "message": "请先填写 API Key"}

    ok, err = validate_base_url(base_url)
    if not ok:
        return {"status": "error", "ok": False, "message": err}

    def _probe():
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=20.0)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=4,
            temperature=0,
        )
        # 能拿到 choices 即视为连通
        return bool(resp.choices)

    try:
        started = time.time()
        ok_flag = await asyncio.to_thread(_probe)
        elapsed = int((time.time() - started) * 1000)

        if ok_flag:
            return {
                "status": "ok",
                "ok": True,
                "message": f"连接成功（{elapsed} ms）",
                "latency_ms": elapsed,
                "model": model,
                "base_url": base_url,
            }
        return {"status": "error", "ok": False, "message": "接口无响应内容"}

    except Exception as e:  # noqa: BLE001
        msg = str(e)
        # 把常见错误翻译成可操作的中文提示
        hint = msg
        low = msg.lower()
        if "401" in msg or "invalid_api_key" in low or "authentication" in low:
            hint = "API Key 无效或已过期，请检查密钥是否填写正确"
        elif "404" in msg or "model_not_found" in low or "does not exist" in low:
            hint = f"模型「{model}」在该服务地址下不存在，请检查模型名"
        elif "403" in msg:
            hint = "该密钥无权访问此模型，或账户余额不足"
        elif "429" in msg:
            hint = "请求过于频繁或额度已用尽，请稍后重试"
        elif "connect" in low or "timeout" in low or "timed out" in low:
            hint = f"无法连接到 {base_url}，请检查服务地址与网络"
        elif "ssl" in low:
            hint = "SSL 握手失败，请检查服务地址是否正确"

        print(f"[Config] 连通性测试失败: {msg}")
        return {"status": "error", "ok": False, "message": hint, "detail": msg}


@app.post("/api/v1/config/clear")
async def clear_api_config():
    """清除运行时配置（回到 .env / 未配置状态）"""
    status = runtime_config.clear()
    print("[Config] 运行时 API 配置已清除")
    return {"status": "ok", "message": "已清除配置", **status}


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


def _build_timeline(whisper_segments: list, vision_timeline: list) -> list:
    """
    将 Whisper 分段和视觉事件合并为统一时间轴。
    返回: [{"start": 0.0, "end": 5.2, "text": "...", "back": False, "gesture": 3}, ...]
    """
    if not whisper_segments:
        return []

    # 将视觉数据按时间索引，方便快速查找
    vision_by_time = {}
    for evt in vision_timeline:
        t = evt["t"]
        vision_by_time[t] = evt

    timeline = []
    for seg in whisper_segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_mid = (seg_start + seg_end) / 2

        # 查找该时间段内最接近的视觉采样点
        back_count = 0
        gesture_count = 0
        total_vision_samples = 0

        for evt in vision_timeline:
            if seg_start <= evt["t"] <= seg_end:
                total_vision_samples += 1
                if evt["back"]:
                    back_count += 1
                if evt["gesture"]:
                    gesture_count += 1

        # 如果段内没有视觉采样点，用最近的一个采样点
        if total_vision_samples == 0 and vision_timeline:
            closest = min(vision_timeline, key=lambda e: abs(e["t"] - seg_mid))
            total_vision_samples = 1
            back_count = 1 if closest["back"] else 0
            gesture_count = 1 if closest["gesture"] else 0

        timeline.append({
            "start": seg_start,
            "end": seg_end,
            "text": seg["text"],
            "back": back_count > total_vision_samples * 0.5,  # 超过一半时间背对
            "gesture": gesture_count
        })

    return timeline


# --- 视频文件服务 ---
@app.get("/api/v1/video/{filename}")
async def serve_video(filename: str):
    """提供已分析视频的播放服务"""
    video_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(video_path):
        return {"status": "error", "message": "视频不存在或已过期"}
    return FileResponse(video_path, media_type="video/mp4")


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
