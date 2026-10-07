# ==========================================================================
# 学思践悟 — Whisper 语音转写引擎
#
# 特性：
#   1. 支持按需选择模型精度（tiny / base / small / medium / large-v3），
#      首次使用时由前端「模型监测面板」引导选择并下载
#   2. 模型懒加载：只有真正需要转写时才载入，避免拖慢后端启动
#   3. 内置本地中文标点还原引擎（core.punctuation），
#      不依赖任何外部 API 即可为 Whisper 输出补全标点与断句
# ==========================================================================

import os
import threading
from typing import Callable, Dict, List, Optional

import torch
import whisper

from core.punctuation import punctuation_restorer

# --------------------------------------------------------------------------
# 支持的模型规格（与前端 app/data/modelCatalog.ts 保持一致）
# --------------------------------------------------------------------------
SUPPORTED_MODELS: Dict[str, dict] = {
    "tiny":     {"name": "Tiny",     "size": "75 MB",  "params": "39 M"},
    "base":     {"name": "Base",     "size": "142 MB", "params": "74 M"},
    "small":    {"name": "Small",    "size": "466 MB", "params": "244 M"},
    "medium":   {"name": "Medium",   "size": "1.5 GB", "params": "769 M"},
    "large-v3": {"name": "Large V3", "size": "2.9 GB", "params": "1.55 B"},
}

DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "base")

# Whisper 官方权重下载源
WHISPER_DOWNLOAD_BASE = "https://openaipublic.azureedge.net/main/whisper/models"


class TranscriptionEngine:
    """Whisper 转写引擎（支持多模型精度切换 + 本地标点还原）"""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._models: Dict[str, "whisper.Whisper"] = {}
        self._lock = threading.Lock()
        self._loading: Dict[str, bool] = {}
        print(f"[Whisper] 引擎已就绪 | 运行设备: {self.device}")
        print(f"[Whisper] 默认模型: {DEFAULT_MODEL}（首次转写时载入）")

    # ==================================================================
    # 模型管理
    # ==================================================================
    def _cache_dir(self) -> str:
        """Whisper 权重缓存目录"""
        return os.path.join(os.path.expanduser("~"), ".cache", "whisper")

    def installed_models(self) -> List[str]:
        """扫描缓存目录，返回已下载的模型 id 列表"""
        cache = self._cache_dir()
        installed: List[str] = []
        if not os.path.isdir(cache):
            return installed
        for fname in os.listdir(cache):
            if not fname.endswith(".pt"):
                continue
            # 文件名形如 base.pt / small.pt / large-v3.pt
            model_id = fname[:-3]
            if model_id in SUPPORTED_MODELS:
                installed.append(model_id)
        return sorted(installed)

    def is_installed(self, model_id: str) -> bool:
        return model_id in self.installed_models()

    def runtime_info(self) -> dict:
        """返回运行时环境信息，供前端模型监测面板展示"""
        gpu = None
        if torch.cuda.is_available():
            try:
                gpu = torch.cuda.get_device_name(0)
            except Exception:
                gpu = "CUDA 设备"
        return {
            "device": self.device,
            "torch": torch.__version__,
            "cuda": torch.cuda.is_available(),
            "gpu": gpu,
            "installed": self.installed_models(),
            "cache_dir": self._cache_dir(),
            "default_model": DEFAULT_MODEL,
            "supported": SUPPORTED_MODELS,
        }

    def get_model(self, model_id: str):
        """按 id 获取模型，必要时载入（线程安全）"""
        if model_id not in SUPPORTED_MODELS:
            print(f"[Whisper] 未知模型 {model_id}，回退到 {DEFAULT_MODEL}")
            model_id = DEFAULT_MODEL

        with self._lock:
            if model_id in self._models:
                return self._models[model_id]

            print(f"[Whisper] 载入模型 {model_id} …")
            model = whisper.load_model(model_id, device=self.device)
            self._models[model_id] = model
            print(f"[Whisper] 模型 {model_id} 载入完成")
            return model

    def download_model(self, model_id: str, on_progress: Optional[Callable[[int, str], None]] = None):
        """
        下载指定模型权重。

        Whisper 的 load_model 在权重缺失时会自动下载，
        这里通过调用它来触发下载，并把过程反馈给调用方。

        Args:
            model_id: 模型 id
            on_progress: 回调 (percent, message)
        """
        if model_id not in SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model_id}")

        spec = SUPPORTED_MODELS[model_id]

        def report(p: int, msg: str):
            if on_progress:
                on_progress(p, msg)

        if self.is_installed(model_id):
            report(100, f"{spec['name']} 模型已存在，无需下载")
            self.get_model(model_id)
            return

        report(5, f"准备下载 {spec['name']}（{spec['size']}）…")

        # 分阶段反馈：Whisper 内部下载无法得知字节进度，
        # 这里给出阶段性的确定性提示，避免前端进度条长时间不动。
        report(15, f"正在连接模型源，获取 {spec['name']} 权重…")

        def _run():
            # 触发下载（阻塞）
            self.get_model(model_id)

        # 在下载线程中执行，主协程通过队列感知完成
        done = threading.Event()
        error: List[Exception] = []

        def _worker():
            try:
                _run()
            except Exception as e:  # noqa: BLE001
                error.append(e)
            finally:
                done.set()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        # 轮询等待，同时给出进度心跳
        heartbeat = 20
        while not done.wait(timeout=2.0):
            heartbeat = min(heartbeat + 6, 92)
            report(heartbeat, f"下载中… {spec['name']} ({spec['size']})")

        if error:
            raise error[0]

        report(100, f"{spec['name']} 下载完成")

    # ==================================================================
    # 转写
    # ==================================================================
    def transcribe(
        self,
        file_path: str,
        model_id: Optional[str] = None,
        add_punctuation: bool = True,
    ) -> dict:
        """
        语音转文字。

        Args:
            file_path: 音频文件路径
            model_id: 使用的模型精度，缺省用 DEFAULT_MODEL
            add_punctuation: 是否用本地规则引擎还原中文标点

        Returns:
            {
              "full_text": "带标点的完整转写文本",
              "raw_text":  "Whisper 原始输出（无标点）",
              "segments": [{"start","end","text"}, ...],
              "model": "small",
              "punctuation_restored": True
            }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到音频文件: {file_path}")

        model_id = model_id or DEFAULT_MODEL
        model = self.get_model(model_id)

        print(f"[Whisper] 转写中 ({model_id}) : {os.path.basename(file_path)}")

        result = model.transcribe(
            file_path,
            fp16=(self.device == "cuda"),
            language="zh",
            initial_prompt="以下是普通话的句子，请使用简体中文并加上标点。",
        )

        # --- 分段信息 ---
        raw_segments = result.get("segments", [])
        timed_segments: List[dict] = []
        for seg in raw_segments:
            timed_segments.append({
                "start": round(seg["start"], 1),
                "end": round(seg["end"], 1),
                "text": (seg.get("text") or "").strip(),
            })

        if timed_segments:
            raw_text = "".join(s["text"] for s in timed_segments)
        else:
            raw_text = (result.get("text") or "").strip()

        # --- 本地后处理：同音错字纠正 + 标点还原（零 API 消耗）---
        full_text = raw_text
        restored = False
        corrections: List[str] = []

        if add_punctuation and raw_text:
            print("[Whisper] 本地纠错与标点还原中…")
            try:
                full_text = punctuation_restorer.restore(
                    raw_text, segments=timed_segments or None
                )
                restored = full_text != raw_text
                corrections = punctuation_restorer.diff_corrections(raw_text, full_text)
                if corrections:
                    print(f"[Whisper] 已纠正 {len(corrections)} 处识别错误: "
                          f"{'、'.join(corrections[:6])}")
                print("[Whisper] 纠错与标点还原完成")
            except Exception as e:  # noqa: BLE001
                print(f"[Whisper] 后处理失败，返回原始文本: {e}")
                full_text = raw_text

        return {
            "full_text": full_text,
            "raw_text": raw_text,
            "segments": timed_segments,
            "model": model_id,
            "punctuation_restored": restored,
            "corrections": corrections,
        }


# 实例化，方便 main.py 直接调用
transcriber = TranscriptionEngine()
